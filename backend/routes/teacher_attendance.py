from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from database import get_supabase
from middleware.auth import require_teacher, CurrentUser
from models.schemas import TeacherPunchRequest
from services.face_recognition.recognizer import verify_self

router = APIRouter(prefix="/teacher-attendance", tags=["Teacher Attendance"])


@router.post("/punch-in")
def punch_in(payload: TeacherPunchRequest, user: CurrentUser = Depends(require_teacher)):
    supabase = get_supabase()
    today = date.today().isoformat()

    existing = (
        supabase.table("teacher_attendance").select("*").eq("teacher_id", user.id).eq("date", today).execute().data
    )
    if existing and existing[0].get("punch_in_at"):
        return {"status": "already_punched_in", "message": "You've already punched in today", "record": existing[0]}

    try:
        result = verify_self(payload.image_base64, user.id)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    if not result.get("matched"):
        return {**result, "status": "rejected"}

    teacher = supabase.table("teachers").select("punch_in_deadline").eq("id", user.id).single().execute().data
    deadline_str = (teacher or {}).get("punch_in_deadline") or "07:00:00"
    deadline_hour, deadline_minute = int(deadline_str[:2]), int(deadline_str[3:5])

    now = datetime.now(timezone.utc)
    is_late = (now.hour, now.minute) > (deadline_hour, deadline_minute)
    punch_status = "late" if is_late else "on_time"

    row = {
        "teacher_id": user.id,
        "date": today,
        "punch_in_at": now.isoformat(),
        "punch_in_method": "face",
        "punch_in_confidence": result["confidence"],
        "punch_in_status": punch_status,
    }
    if existing:
        supabase.table("teacher_attendance").update(row).eq("id", existing[0]["id"]).execute()
    else:
        supabase.table("teacher_attendance").insert(row).execute()

    if is_late:
        profile = supabase.table("profiles").select("full_name").eq("id", user.id).single().execute().data
        teacher_name = (profile or {}).get("full_name", "A teacher")
        admins = supabase.table("profiles").select("id").eq("role", "admin").execute().data or []
        if admins:
            supabase.table("notifications").insert(
                [
                    {
                        "user_id": a["id"],
                        "title": "Late punch-in",
                        "message": f"{teacher_name} punched in late today ({now.strftime('%H:%M')}, deadline was {deadline_str[:5]}).",
                        "type": "warning",
                    }
                    for a in admins
                ]
            ).execute()

    return {**result, "status": "marked", "punch_status": punch_status, "message": f"Punched in — marked {punch_status.replace('_', ' ')}"}


@router.post("/punch-out")
def punch_out(payload: TeacherPunchRequest, user: CurrentUser = Depends(require_teacher)):
    supabase = get_supabase()
    today = date.today().isoformat()

    existing = (
        supabase.table("teacher_attendance").select("*").eq("teacher_id", user.id).eq("date", today).execute().data
    )
    if not existing or not existing[0].get("punch_in_at"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You haven't punched in yet today")
    if existing[0].get("punch_out_at"):
        return {"status": "already_punched_out", "message": "You've already punched out today"}

    try:
        result = verify_self(payload.image_base64, user.id)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    if not result.get("matched"):
        return {**result, "status": "rejected"}

    supabase.table("teacher_attendance").update(
        {"punch_out_at": datetime.now(timezone.utc).isoformat(), "punch_out_method": "face"}
    ).eq("id", existing[0]["id"]).execute()

    return {**result, "status": "marked", "message": "Punched out — have a good day."}


@router.get("/today")
def today_record(user: CurrentUser = Depends(require_teacher)):
    supabase = get_supabase()
    today = date.today().isoformat()
    row = (
        supabase.table("teacher_attendance")
        .select("*")
        .eq("teacher_id", user.id)
        .eq("date", today)
        .execute()
        .data
    )
    return row[0] if row else None
