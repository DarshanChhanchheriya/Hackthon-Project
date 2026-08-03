from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from database import get_supabase
from utils.security import decode_supabase_jwt

bearer_scheme = HTTPBearer(auto_error=True)


class CurrentUser:
    def __init__(self, id: str, email: str, role: str):
        self.id = id
        self.email = email
        self.role = role


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> CurrentUser:
    payload = decode_supabase_jwt(credentials.credentials)
    user_id = payload.get("sub")
    email = payload.get("email", "")

    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")

    supabase = get_supabase()
    profile = (
        supabase.table("profiles").select("id, role, is_active").eq("id", user_id).single().execute()
    )

    if not profile.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    if not profile.data.get("is_active", True):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")

    return CurrentUser(id=user_id, email=email, role=profile.data["role"])


def require_roles(*roles: str):
    async def _guard(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of roles: {', '.join(roles)}",
            )
        return user

    return _guard


require_admin = require_roles("admin")
require_teacher = require_roles("teacher", "admin")
require_student = require_roles("student", "admin")
require_any = require_roles("student", "teacher", "admin")
