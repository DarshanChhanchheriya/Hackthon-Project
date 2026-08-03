from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from database import get_supabase
from middleware.auth import require_student, require_teacher, require_any, CurrentUser
from models.schemas import LeaveCreateRequest, LeaveReviewRequest

router = APIRouter(prefix="/leave", tags=["Leave Management"])


@router.post("", status_code=status.HTTP_201_CREATED)
def apply_leave(payload: LeaveCreateRequest, user: CurrentUser = Depends(require_student)):
    supabase = get_supabase()
    row = (
        supabase.table("leave_requests")
        .insert(
            {
                "student_id": user.id,
                "reason": payload.reason,
                "start_date": payload.start_date.isoformat(),
                "end_date": payload.end_date.isoformat(),
                "status": "pending",
            }
        )
        .execute()
        .data[0]
    )
    return row


@router.get("")
def list_leaves(
    status_filter: str | None = None,
    student_id: str | None = None,
    page: int = 1,
    page_size: int = 20,
    user: CurrentUser = Depends(require_any),
):
    supabase = get_supabase()
    query = supabase.table("leave_requests").select(
        "*, students(roll_number, profiles(full_name))", count="exact"
    )

    if user.role == "student":
        query = query.eq("student_id", user.id)
    elif student_id:
        query = query.eq("student_id", student_id)
    if status_filter:
        query = query.eq("status", status_filter)

    start = (page - 1) * page_size
    res = query.order("created_at", desc=True).range(start, start + page_size - 1).execute()
    return {"data": res.data, "total": res.count, "page": page, "page_size": page_size}


@router.put("/{leave_id}/review")
def review_leave(leave_id: str, payload: LeaveReviewRequest, user: CurrentUser = Depends(require_teacher)):
    supabase = get_supabase()
    leave = supabase.table("leave_requests").select("*").eq("id", leave_id).single().execute().data
    if not leave:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Leave request not found")

    supabase.table("leave_requests").update(
        {
            "status": payload.status,
            "review_note": payload.review_note,
            "reviewed_by": user.id,
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
        }
    ).eq("id", leave_id).execute()

    if payload.status == "approved":
        d = date.fromisoformat(leave["start_date"])
        end = date.fromisoformat(leave["end_date"])
        leave_rows = []
        while d <= end:
            leave_rows.append(
                {
                    "student_id": leave["student_id"],
                    "status": "leave",
                    "method": "manual",
                    "date": d.isoformat(),
                }
            )
            d += timedelta(days=1)
        supabase.table("attendance").upsert(leave_rows, on_conflict="student_id,date,subject").execute()

    supabase.table("notifications").insert(
        {
            "user_id": leave["student_id"],
            "title": f"Leave request {payload.status}",
            "message": payload.review_note or f"Your leave request has been {payload.status}.",
            "type": "success" if payload.status == "approved" else "warning",
        }
    ).execute()

    return {"message": f"Leave request {payload.status}"}
