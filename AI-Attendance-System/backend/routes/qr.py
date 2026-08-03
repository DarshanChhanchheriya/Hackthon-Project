from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from database import get_supabase
from middleware.auth import require_teacher, require_student, require_any, CurrentUser
from models.schemas import QRGenerateRequest, QRScanRequest, StudentPersonalQRCheckinRequest
from services.qr.qr_service import generate_qr_session, validate_and_consume_qr, generate_personal_qr, verify_student_token

router = APIRouter(prefix="/qr", tags=["QR Attendance"])


@router.post("/generate")
def generate(payload: QRGenerateRequest, user: CurrentUser = Depends(require_teacher)):
    return generate_qr_session(payload.teacher_id, payload.subject, payload.section, payload.department_id)


@router.post("/scan")
def scan(payload: QRScanRequest, user: CurrentUser = Depends(require_student)):
    if user.role == "student" and user.id != payload.student_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot mark attendance for another student")

    result = validate_and_consume_qr(payload.token, payload.student_id)
    if not result["valid"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["message"])

    session = result["session"]
    supabase = get_supabase()
    today = date.today().isoformat()

    supabase.table("attendance").insert(
        {
            "student_id": payload.student_id,
            "teacher_id": session["teacher_id"],
            "department_id": session.get("department_id"),
            "subject": session.get("subject") or "",
            "status": "present",
            "method": "qr",
            "qr_session_id": session["id"],
            "date": today,
            "marked_at": datetime.now(timezone.utc).isoformat(),
        }
    ).execute()
    supabase.table("attendance_logs").insert(
        {"student_id": payload.student_id, "event": "qr_scan", "detail": {"session_id": session["id"]}}
    ).execute()

    return {"message": "Attendance marked successfully via QR code", "subject": session.get("subject")}


@router.post("/close/{session_id}")
def close_session(session_id: str, user: CurrentUser = Depends(require_teacher)):
    supabase = get_supabase()
    supabase.table("qr_sessions").update({"status": "closed"}).eq("id", session_id).execute()
    return {"message": "QR session closed"}


@router.get("/my-id")
def my_personal_qr(user: CurrentUser = Depends(require_student)):
    """A student's permanent personal ID-QR — never expires, but only
    redeemable while a teacher has an active attendance session open.
    """
    return {"qr_image_base64": generate_personal_qr(user.id)}


@router.post("/personal-checkin")
def personal_checkin(payload: StudentPersonalQRCheckinRequest, user: CurrentUser = Depends(require_teacher)):
    """Teacher scans a student's personal ID-QR during an active session."""
    supabase = get_supabase()

    student_id = verify_student_token(payload.student_token)
    if not student_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or tampered student QR code")

    session = supabase.table("attendance_sessions").select("*").eq("id", payload.session_id).single().execute().data
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if session["status"] != "active":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This session is no longer active")

    today = date.today().isoformat()
    existing = (
        supabase.table("attendance")
        .select("id")
        .eq("student_id", student_id)
        .eq("date", today)
        .eq("subject", session.get("subject") or "")
        .execute()
        .data
    )
    if existing:
        return {"status": "already_marked", "message": "Attendance already marked for today"}

    starts_at = datetime.fromisoformat(session["starts_at"].replace("Z", "+00:00"))
    grace = timedelta(minutes=session.get("punch_in_grace_minutes", 10))
    is_late = datetime.now(timezone.utc) > starts_at + grace
    if is_late:
        return {"status": "late", "message": "Check-in window has passed — mark this student present manually if valid"}

    student = (
        supabase.table("students")
        .select("roll_number, profiles(full_name)")
        .eq("id", student_id)
        .single()
        .execute()
        .data
    )

    supabase.table("attendance").insert(
        {
            "student_id": student_id,
            "teacher_id": session["teacher_id"],
            "department_id": session.get("department_id"),
            "subject": session.get("subject") or "",
            "status": "present",
            "method": "qr",
            "session_id": session["id"],
            "date": today,
            "marked_at": datetime.now(timezone.utc).isoformat(),
        }
    ).execute()

    return {
        "status": "marked",
        "message": "Attendance marked via personal QR",
        "full_name": (student or {}).get("profiles", {}).get("full_name"),
        "roll_number": (student or {}).get("roll_number"),
    }
