from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from database import get_supabase
from middleware.auth import require_teacher, require_any, get_current_user, CurrentUser
from models.schemas import FaceEnrollRequest, FaceRecognizeRequest, FaceSelfCheckinRequest
from services.face_recognition.encoder import extract_multiple_encodings
from services.face_recognition.recognizer import recognize_face, verify_self
from utils.logger import logger

router = APIRouter(prefix="/face", tags=["Face Recognition"])


@router.get("/status")
def face_status(user: CurrentUser = Depends(get_current_user)):
    """Lets the frontend check enrollment before opening the camera, instead of
    only finding out after a doomed scan-and-fail loop."""
    supabase = get_supabase()
    rows = supabase.table("face_encodings").select("id").eq("owner_id", user.id).limit(1).execute().data
    return {"enrolled": bool(rows)}


@router.post("/enroll")
def enroll_face(payload: FaceEnrollRequest, user: CurrentUser = Depends(require_any)):
    if user.role != "admin" and user.id != payload.owner_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot enroll another user's face")

    try:
        encodings = extract_multiple_encodings(payload.images_base64)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    if len(encodings) < 3:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not detect a clear face in at least 3 of the uploaded images. Please retake in good lighting.",
        )

    supabase = get_supabase()
    supabase.table("face_encodings").delete().eq("owner_id", payload.owner_id).execute()
    rows = [
        {"owner_id": payload.owner_id, "encoding": enc, "sample_index": i + 1}
        for i, enc in enumerate(encodings)
    ]
    supabase.table("face_encodings").insert(rows).execute()

    is_student = supabase.table("students").select("id").eq("id", payload.owner_id).execute().data
    if is_student:
        supabase.table("students").update({"face_registered": True}).eq("id", payload.owner_id).execute()

    logger.info(f"Enrolled {len(encodings)} face samples for {payload.owner_id}")
    return {"message": f"Face registered successfully with {len(encodings)} samples", "samples_used": len(encodings)}


@router.post("/recognize")
def recognize(payload: FaceRecognizeRequest, user: CurrentUser = Depends(require_teacher)):
    supabase = get_supabase()

    if payload.session_id:
        session = supabase.table("attendance_sessions").select("status").eq("id", payload.session_id).single().execute().data
        if not session or session["status"] != "active":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This session has ended. Use manual attendance for latecomers.",
            )

    try:
        result = recognize_face(payload.image_base64, payload.department_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    if not result.get("matched"):
        supabase.table("attendance_logs").insert(
            {"event": "face_reject", "detail": {"reason": result.get("message")}}
        ).execute()
        return result

    student_id = result["student_id"]
    today = date.today().isoformat()

    existing = (
        supabase.table("attendance")
        .select("id")
        .eq("student_id", student_id)
        .eq("date", today)
        .eq("subject", payload.subject or "")
        .execute()
        .data
    )
    if existing:
        supabase.table("attendance_logs").insert(
            {"student_id": student_id, "event": "duplicate_blocked", "detail": {"date": today}}
        ).execute()
        result["status"] = "already_marked"
        result["message"] = "Attendance already marked for today"
        return result

    supabase.table("attendance").insert(
        {
            "student_id": student_id,
            "teacher_id": payload.teacher_id,
            "department_id": payload.department_id,
            "subject": payload.subject or "",
            "status": "present",
            "method": "face",
            "confidence": result["confidence"],
            "session_id": payload.session_id,
            "date": today,
            "marked_at": datetime.now(timezone.utc).isoformat(),
        }
    ).execute()
    supabase.table("attendance_logs").insert(
        {"student_id": student_id, "event": "face_match", "detail": {"confidence": result["confidence"]}}
    ).execute()

    result["status"] = "marked"
    return result


@router.post("/self-checkin")
def self_checkin(payload: FaceSelfCheckinRequest, user: CurrentUser = Depends(get_current_user)):
    """Student marks their own attendance during an active teacher session,
    using their own enrolled face. The recognized identity is inherently
    locked to the caller (we only compare against their own encodings), so
    this can't be used to mark someone else present.
    """
    if user.role != "student":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only students can self check-in")

    supabase = get_supabase()
    session = supabase.table("attendance_sessions").select("*").eq("id", payload.session_id).single().execute().data
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if session["status"] != "active":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This session is no longer active")

    today = date.today().isoformat()
    existing = (
        supabase.table("attendance")
        .select("id")
        .eq("student_id", user.id)
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
        return {
            "status": "late",
            "matched": False,
            "message": "You're past the check-in window for this session. Ask your teacher to mark you present.",
        }

    try:
        result = verify_self(payload.image_base64, user.id)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    if not result.get("matched"):
        supabase.table("attendance_logs").insert(
            {"student_id": user.id, "event": "self_checkin_reject", "detail": {"reason": result.get("message")}}
        ).execute()
        return {**result, "status": "rejected"}

    supabase.table("attendance").insert(
        {
            "student_id": user.id,
            "teacher_id": session["teacher_id"],
            "department_id": session.get("department_id"),
            "subject": session.get("subject") or "",
            "status": "present",
            "method": "face",
            "confidence": result["confidence"],
            "session_id": session["id"],
            "date": today,
            "marked_at": datetime.now(timezone.utc).isoformat(),
        }
    ).execute()
    supabase.table("attendance_logs").insert(
        {"student_id": user.id, "event": "self_checkin", "detail": {"confidence": result["confidence"]}}
    ).execute()

    return {**result, "status": "marked", "message": "Attendance marked — you're present."}
