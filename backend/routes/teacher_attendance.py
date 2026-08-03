from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from config import get_settings
from database import get_supabase
from middleware.auth import require_teacher, CurrentUser
from models.schemas import TeacherPunchRequest
from services.face_recognition.recognizer import verify_self

router = APIRouter(prefix="/teacher-attendance", tags=["Teacher Attendance"])
settings = get_settings()


def _school_now() -> datetime:
    """UTC time shifted to the school's local timezone (IST by default) —
    punch-in deadlines are set by admins in local wall-clock time, so
    comparisons must happen in that same timezone, not raw UTC.
    """
    return datetime.now(timezone.utc) + timedelta(hours=settings.SCHOOL_TIMEZONE_OFFSET_HOURS)


def _is_holiday(d: date) -> bool:
    return d.weekday() == 6  # Sunday


@router.post("/punch-in")
def punch_in(payload: TeacherPunchRequest, user: CurrentUser = Depends(require_teacher)):
    supabase = get_supabase()
    local_now = _school_now()
    today = local_now.date()

    if _is_holiday(today):
        return {"status": "holiday", "message": "Today is a holiday (Sunday) — no punch-in required"}

    existing = (
        supabase.table("teacher_attendance").select("*").eq("teacher_id", user.id).eq("date", today.isoformat()).execute().data
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
    deadline_dt = local_now.replace(hour=deadline_hour, minute=deadline_minute, second=0, microsecond=0)

    minutes_late = max(0, int((local_now - deadline_dt).total_seconds() // 60))
    is_late = minutes_late > 0
    punch_status = "late" if is_late else "on_time"

    row = {
        "teacher_id": user.id,
        "date": today.isoformat(),
        "punch_in_at": datetime.now(timezone.utc).isoformat(),
        "punch_in_method": "face",
        "punch_in_confidence": result["confidence"],
        "punch_in_status": punch_status,
    }
    if existing:
        supabase.table("teacher_attendance").update(row).eq("id", existing[0]["id"]).execute()
    else:
        supabase.table("teacher_attendance").insert(row).execute()

    message = f"Punched in — on time ({local_now.strftime('%H:%M')})"
    if is_late:
        message = f"Punched in — {minutes_late} minute{'s' if minutes_late != 1 else ''} late"
        profile = supabase.table("profiles").select("full_name").eq("id", user.id).single().execute().data
        teacher_name = (profile or {}).get("full_name", "A teacher")
        admins = supabase.table("profiles").select("id").eq("role", "admin").execute().data or []
        if admins:
            supabase.table("notifications").insert(
                [
                    {
                        "user_id": a["id"],
                        "title": "Late punch-in",
                        "message": f"{teacher_name} punched in {minutes_late} minute{'s' if minutes_late != 1 else ''} late today (at {local_now.strftime('%H:%M')}, deadline was {deadline_str[:5]}).",
                        "type": "warning",
                    }
                    for a in admins
                ]
            ).execute()

    return {**result, "status": "marked", "punch_status": punch_status, "minutes_late": minutes_late, "message": message}


@router.post("/punch-out")
def punch_out(payload: TeacherPunchRequest, user: CurrentUser = Depends(require_teacher)):
    supabase = get_supabase()
    today = _school_now().date().isoformat()

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
    today = _school_now().date()
    if _is_holiday(today):
        return {"holiday": True, "message": "Today is a holiday (Sunday)"}

    supabase = get_supabase()
    rows = (
        supabase.table("teacher_attendance")
        .select("*")
        .eq("teacher_id", user.id)
        .eq("date", today.isoformat())
        .execute()
        .data
    )
    if not rows:
        return None

    row = rows[0]
    if row.get("punch_in_status") == "late" and row.get("punch_in_at"):
        teacher = supabase.table("teachers").select("punch_in_deadline").eq("id", user.id).single().execute().data
        deadline_str = (teacher or {}).get("punch_in_deadline") or "07:00:00"
        deadline_hour, deadline_minute = int(deadline_str[:2]), int(deadline_str[3:5])
        punch_in_local = datetime.fromisoformat(row["punch_in_at"].replace("Z", "+00:00")) + timedelta(
            hours=settings.SCHOOL_TIMEZONE_OFFSET_HOURS
        )
        deadline_dt = punch_in_local.replace(hour=deadline_hour, minute=deadline_minute, second=0, microsecond=0)
        row["minutes_late"] = max(0, int((punch_in_local - deadline_dt).total_seconds() // 60))

    return row
