from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "AI Attendance System API"
    ENV: str = "development"
    API_PREFIX: str = "/api/v1"

    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str
    SUPABASE_JWT_SECRET: str

    JWT_ALGORITHM: str = "HS256"

    CORS_ORIGINS: str = "http://localhost:5500,http://127.0.0.1:5500,http://localhost:3000"

    FACE_MATCH_THRESHOLD: float = 0.70  # confidence required to auto mark attendance
    FACE_DISTANCE_TOLERANCE: float = 0.6  # face_recognition's standard same-person distance cutoff
    SCHOOL_TIMEZONE_OFFSET_HOURS: float = 5.5  # IST by default — used for punch-in deadline comparisons
    QR_EXPIRY_SECONDS: int = 120

    RATE_LIMIT_DEFAULT: str = "60/minute"

    # Self-registration for these two roles is gated behind a private code so a
    # student can't just pick "Teacher" or "Admin" on the public signup form and
    # get elevated access. Optional (not required) so a deployment that hasn't
    # set these yet fails *closed* (teacher/admin signup blocked, everything
    # else keeps working) instead of crashing the whole app on startup.
    # Share the real values only with real staff — never hardcode them here.
    TEACHER_SIGNUP_CODE: str | None = None
    ADMIN_SIGNUP_CODE: str | None = None

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
