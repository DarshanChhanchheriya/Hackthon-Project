import re

from fastapi import APIRouter, HTTPException, status, Depends
from postgrest.exceptions import APIError

from config import get_settings
from database import get_supabase, get_supabase_anon
from middleware.auth import get_current_user, CurrentUser
from models.schemas import (
    RegisterRequest,
    LoginRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    OTPRequestModel,
    OTPVerifyResetRequest,
)
from utils.logger import logger

router = APIRouter(prefix="/auth", tags=["Auth"])


def _friendly_db_error(exc: APIError) -> str:
    """Turn a raw Postgres constraint violation into something a user can act on."""
    message = exc.message or ""
    if exc.code == "23505":  # unique_violation
        if "roll_number" in message:
            return "This roll number is already registered. Please use a different one."
        if "employee_id" in message:
            return "This employee ID is already registered. Please use a different one."
        return "One of your details is already registered. Please double-check and try again."
    if exc.code == "23502":  # not_null_violation
        match = re.search(r'column "(\w+)"', message)
        field = match.group(1) if match else "a required field"
        return f"Missing required field: {field}. Please fill in all fields for your role."
    return "Registration failed while saving your details. Please try again."


@router.get("/departments")
def list_departments():
    """Public, unauthenticated list of departments — used by the registration form
    before the user has a session, so it must not depend on RLS letting anon reads through."""
    supabase = get_supabase()
    res = supabase.table("departments").select("id, name").order("name").execute()
    return res.data


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest):
    if payload.role in ("teacher", "admin"):
        settings = get_settings()
        required_code = settings.TEACHER_SIGNUP_CODE if payload.role == "teacher" else settings.ADMIN_SIGNUP_CODE
        if not required_code:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"{payload.role.capitalize()} self-registration is not configured yet. Contact your administrator.",
            )
        if not payload.access_code or payload.access_code != required_code:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Invalid or missing access code for {payload.role} registration.",
            )

    supabase_anon = get_supabase_anon()
    supabase = get_supabase()

    try:
        auth_res = supabase_anon.auth.sign_up(
            {
                "email": payload.email,
                "password": payload.password,
                "options": {"data": {"full_name": payload.full_name, "role": payload.role}},
            }
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    user = auth_res.user
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Registration failed")

    try:
        supabase.table("profiles").insert(
            {
                "id": user.id,
                "email": payload.email,
                "full_name": payload.full_name,
                "role": payload.role,
                "phone": payload.phone,
            }
        ).execute()

        if payload.role == "student":
            supabase.table("students").insert(
                {
                    "id": user.id,
                    "roll_number": payload.roll_number,
                    "department_id": payload.department_id,
                    "semester": payload.semester or 1,
                    "section": payload.section,
                }
            ).execute()
        elif payload.role == "teacher":
            supabase.table("teachers").insert(
                {
                    "id": user.id,
                    "employee_id": payload.employee_id,
                    "department_id": payload.department_id,
                }
            ).execute()
        elif payload.role == "admin":
            supabase.table("admins").insert({"id": user.id, "employee_id": payload.employee_id}).execute()
    except APIError as exc:
        # Registration failed partway through (e.g. duplicate roll number/employee
        # ID) — clean up the auth user and any partial profile row so we never
        # leave a "ghost" account behind: a real login with no matching
        # student/teacher/admin data, which breaks the rest of the app for them.
        supabase.table("profiles").delete().eq("id", user.id).execute()
        try:
            supabase.auth.admin.delete_user(user.id)
        except Exception:  # noqa: BLE001
            logger.warning(f"Failed to clean up orphaned auth user {user.id} after registration error")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=_friendly_db_error(exc)) from exc

    logger.info(f"Registered new {payload.role}: {payload.email}")
    return {"message": "Registration successful. Please verify your email.", "user_id": user.id}


@router.post("/login")
def login(payload: LoginRequest):
    supabase_anon = get_supabase_anon()
    try:
        res = supabase_anon.auth.sign_in_with_password(
            {"email": payload.email, "password": payload.password}
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password") from exc

    if not res.session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    supabase = get_supabase()
    profile = supabase.table("profiles").select("*").eq("id", res.user.id).single().execute().data

    return {
        "access_token": res.session.access_token,
        "refresh_token": res.session.refresh_token,
        "expires_in": res.session.expires_in,
        "user": profile,
    }


@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordRequest):
    supabase_anon = get_supabase_anon()
    supabase_anon.auth.reset_password_for_email(payload.email)
    return {"message": "If that email exists, a password reset link has been sent."}


@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest):
    supabase = get_supabase()
    try:
        supabase.auth.admin.update_user_by_id(payload.access_token, {"password": payload.new_password})
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"message": "Password updated successfully."}


@router.post("/otp/request")
def request_otp(payload: OTPRequestModel):
    """Sends a 6-digit email OTP for password reset, for any of the 3 roles.
    Always returns the same message regardless of whether the email exists,
    to avoid leaking which addresses are registered.
    """
    supabase = get_supabase()
    supabase_anon = get_supabase_anon()

    existing = supabase.table("profiles").select("id").eq("email", payload.email).execute().data
    if existing:
        try:
            supabase_anon.auth.sign_in_with_otp({"email": payload.email, "options": {"should_create_user": False}})
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"OTP send failed for {payload.email}: {exc}")

    return {"message": "If that email exists, a verification code has been sent."}


@router.post("/otp/verify-reset")
def verify_otp_reset(payload: OTPVerifyResetRequest):
    supabase_anon = get_supabase_anon()
    supabase = get_supabase()

    try:
        res = supabase_anon.auth.verify_otp({"email": payload.email, "token": payload.otp, "type": "email"})
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired code") from exc

    if not res.user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired code")

    supabase.auth.admin.update_user_by_id(res.user.id, {"password": payload.new_password})
    logger.info(f"Password reset via OTP for {payload.email}")
    return {"message": "Password reset successful. Please log in with your new password."}


@router.get("/me")
def me(user: CurrentUser = Depends(get_current_user)):
    supabase = get_supabase()
    profile = supabase.table("profiles").select("*").eq("id", user.id).single().execute().data
    return profile


@router.post("/logout")
def logout(user: CurrentUser = Depends(get_current_user)):
    return {"message": "Logged out. Discard the token client-side."}
