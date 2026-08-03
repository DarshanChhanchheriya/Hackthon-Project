import base64
import hashlib
import hmac
import io
import secrets
from datetime import datetime, timedelta, timezone

import qrcode

from config import get_settings
from database import get_supabase

settings = get_settings()


# ---------------------------------------------------------------------------
# Permanent personal student ID-QR. The QR image itself never expires (it's
# effectively a digital ID badge); security instead comes from requiring an
# ACTIVE teacher session to redeem it, and one redemption per session.
# ---------------------------------------------------------------------------
def _sign_student_token(student_id: str) -> str:
    signature = hmac.new(settings.SUPABASE_JWT_SECRET.encode(), student_id.encode(), hashlib.sha256).hexdigest()[:16]
    return f"{student_id}.{signature}"


def verify_student_token(token: str) -> str | None:
    try:
        student_id, signature = token.rsplit(".", 1)
    except ValueError:
        return None
    expected = hmac.new(settings.SUPABASE_JWT_SECRET.encode(), student_id.encode(), hashlib.sha256).hexdigest()[:16]
    if not hmac.compare_digest(signature, expected):
        return None
    return student_id


def generate_personal_qr(student_id: str) -> str:
    token = _sign_student_token(student_id)
    qr_img = qrcode.make(token)
    buf = io.BytesIO()
    qr_img.save(buf, format="PNG")
    qr_base64 = base64.b64encode(buf.getvalue()).decode()
    return f"data:image/png;base64,{qr_base64}"


def generate_qr_session(teacher_id: str, subject: str | None, section: str | None, department_id: str | None) -> dict:
    supabase = get_supabase()
    token = secrets.token_urlsafe(24)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=settings.QR_EXPIRY_SECONDS)

    row = (
        supabase.table("qr_sessions")
        .insert(
            {
                "teacher_id": teacher_id,
                "subject": subject,
                "section": section,
                "department_id": department_id,
                "token": token,
                "status": "active",
                "expires_at": expires_at.isoformat(),
            }
        )
        .execute()
        .data[0]
    )

    qr_img = qrcode.make(token)
    buf = io.BytesIO()
    qr_img.save(buf, format="PNG")
    qr_base64 = base64.b64encode(buf.getvalue()).decode()

    return {
        "session_id": row["id"],
        "token": token,
        "qr_image_base64": f"data:image/png;base64,{qr_base64}",
        "expires_at": expires_at.isoformat(),
        "expires_in_seconds": settings.QR_EXPIRY_SECONDS,
    }


def validate_and_consume_qr(token: str, student_id: str) -> dict:
    supabase = get_supabase()
    session_res = supabase.table("qr_sessions").select("*").eq("token", token).single().execute()
    session = session_res.data
    if not session:
        return {"valid": False, "message": "Invalid QR code"}

    expires_at = datetime.fromisoformat(session["expires_at"].replace("Z", "+00:00"))
    if session["status"] != "active" or expires_at < datetime.now(timezone.utc):
        supabase.table("qr_sessions").update({"status": "expired"}).eq("id", session["id"]).execute()
        return {"valid": False, "message": "QR code has expired"}

    existing = (
        supabase.table("attendance")
        .select("id")
        .eq("student_id", student_id)
        .eq("date", datetime.now(timezone.utc).date().isoformat())
        .eq("subject", session.get("subject") or "")
        .execute()
        .data
    )
    if existing:
        return {"valid": False, "message": "Attendance already marked for today"}

    return {"valid": True, "session": session}
