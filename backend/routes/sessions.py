from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from database import get_supabase
from middleware.auth import require_teacher, require_any, CurrentUser
from models.schemas import SessionStartRequest

router = APIRouter(prefix="/sessions", tags=["Attendance Sessions"])


@router.post("/start", status_code=status.HTTP_201_CREATED)
def start_session(payload: SessionStartRequest, user: CurrentUser = Depends(require_teacher)):
    supabase = get_supabase()

    session = (
        supabase.table("attendance_sessions")
        .insert(
            {
                "teacher_id": user.id,
                "department_id": payload.department_id,
                "subject": payload.subject or "",
                "section": payload.section,
                "status": "active",
                "punch_in_grace_minutes": payload.punch_in_grace_minutes,
            }
        )
        .execute()
        .data[0]
    )

    query = supabase.table("students").select("id")
    if payload.department_id:
        query = query.eq("department_id", payload.department_id)
    if payload.section:
        query = query.eq("section", payload.section)
    students = query.execute().data or []

    if students:
        subject_label = f" for {payload.subject}" if payload.subject else ""
        notifications = [
            {
                "user_id": s["id"],
                "title": "Attendance session started",
                "message": f"Your teacher just started an attendance session{subject_label}. Check in now with your face within {payload.punch_in_grace_minutes} minutes.",
                "type": "info",
            }
            for s in students
        ]
        supabase.table("notifications").insert(notifications).execute()

    return session


@router.put("/{session_id}/stop")
def stop_session(session_id: str, user: CurrentUser = Depends(require_teacher)):
    supabase = get_supabase()
    session = supabase.table("attendance_sessions").select("*").eq("id", session_id).single().execute().data
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if user.role != "admin" and session["teacher_id"] != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your session")

    supabase.table("attendance_sessions").update(
        {"status": "closed", "ends_at": datetime.now(timezone.utc).isoformat()}
    ).eq("id", session_id).execute()
    return {"message": "Session closed"}


@router.get("/active")
def list_active_sessions(department_id: str | None = None, user: CurrentUser = Depends(require_any)):
    supabase = get_supabase()
    query = supabase.table("attendance_sessions").select("*, profiles(full_name)").eq("status", "active")
    if department_id:
        query = query.eq("department_id", department_id)
    return query.order("starts_at", desc=True).execute().data
