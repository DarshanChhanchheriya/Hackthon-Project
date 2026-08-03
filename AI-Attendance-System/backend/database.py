import time
from functools import lru_cache

import httpx
from postgrest._sync.request_builder import SyncQueryRequestBuilder, SyncSingleRequestBuilder
from postgrest._sync.request_builder import SyncMaybeSingleRequestBuilder
from supabase import create_client, Client

from config import get_settings
from utils.logger import logger

settings = get_settings()

# Under concurrent load, httpx's sync/Windows transport occasionally raises
# a transient "WinError 10035 / non-blocking socket" error when a pooled
# keep-alive connection is reused across worker threads. It's a known flaky
# pattern with httpx on Windows, not a real failure — retrying immediately
# succeeds. We patch it once, centrally, instead of wrapping every callsite.
_TRANSIENT_ERRORS = (httpx.ReadError, httpx.ConnectError, httpx.WriteError, httpx.RemoteProtocolError)


def _patch_execute_with_retry(builder_cls, attempts: int = 3, delay: float = 0.15):
    original_execute = builder_cls.execute

    def execute_with_retry(self):
        last_exc = None
        for attempt in range(attempts):
            try:
                return original_execute(self)
            except _TRANSIENT_ERRORS as exc:
                last_exc = exc
                logger.warning(f"Transient network error on Supabase call (attempt {attempt + 1}/{attempts}): {exc}")
                time.sleep(delay)
        raise last_exc

    builder_cls.execute = execute_with_retry


for _builder_cls in (SyncQueryRequestBuilder, SyncSingleRequestBuilder, SyncMaybeSingleRequestBuilder):
    _patch_execute_with_retry(_builder_cls)


@lru_cache
def get_supabase() -> Client:
    """Service-role client — used server-side only, bypasses RLS.
    Never expose the service role key to the frontend.
    """
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)


@lru_cache
def get_supabase_anon() -> Client:
    """Anon-key client — used for auth flows (sign in/up) that must
    respect Supabase Auth's own rate limiting and email verification.
    """
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
