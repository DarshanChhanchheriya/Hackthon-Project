from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from database import get_supabase
from middleware.auth import require_teacher, require_any, CurrentUser
from models.schemas import ManualAttendanceRequest

router = APIRouter(prefix="/attendance", tags=["Attendance"])


@router.get("")
def list_attendance(
    student_id: str | None = None,
    department_id: str | None = None,
    session_id: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    status_filter: str | None = None,
    page: int = 1,
    page_size: int = 25,
    user: CurrentUser = Depends(require_any),
):
    supabase = get_supabase()
    query = supabase.table("attendance").select(
        "*, students(roll_number, profiles(full_name), departments(name))", count="exact"
    )

    if user.role == "student":
        student_id = user.id

    if student_id:
        query = query.eq("student_id", student_id)
    if department_id:
        query = query.eq("department_id", department_id)
    if session_id:
        query = query.eq("session_id", session_id)
    if date_from:
        query = query.gte("date", date_from)
    if date_to:
        query = query.lte("date", date_to)
    if status_filter:
        query = query.eq("status", status_filter)

    start = (page - 1) * page_size
    res = query.order("date", desc=True).range(start, start + page_size - 1).execute()
    return {"data": res.data, "total": res.count, "page": page, "page_size": page_size}


@router.post("/manual", status_code=status.HTTP_201_CREATED)
def mark_manual(payload: ManualAttendanceRequest, user: CurrentUser = Depends(require_teacher)):
    supabase = get_supabase()
    today = date.today().isoformat()

    existing = (
        supabase.table("attendance")
        .select("id")
        .eq("student_id", payload.student_id)
        .eq("date", today)
        .eq("subject", payload.subject or "")
        .execute()
        .data
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Attendance already marked for today")

    row = (
        supabase.table("attendance")
        .insert(
            {
                "student_id": payload.student_id,
                "teacher_id": payload.teacher_id,
                "subject": payload.subject or "",
                "status": payload.status,
                "method": "manual",
                "date": today,
                "marked_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        .execute()
        .data[0]
    )
    return row


@router.get("/today-summary")
def today_summary(user: CurrentUser = Depends(require_teacher)):
    supabase = get_supabase()
    today = date.today().isoformat()
    rows = supabase.table("attendance").select("status").eq("date", today).execute().data or []
    present = sum(1 for r in rows if r["status"] == "present")
    late = sum(1 for r in rows if r["status"] == "late")
    absent = sum(1 for r in rows if r["status"] == "absent")
    return {"present": present, "late": late, "absent": absent, "total_marked": len(rows)}
