from fastapi import APIRouter, Depends

from database import get_supabase
from middleware.auth import get_current_user, CurrentUser

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("")
def list_notifications(unread_only: bool = False, user: CurrentUser = Depends(get_current_user)):
    supabase = get_supabase()
    query = supabase.table("notifications").select("*").eq("user_id", user.id)
    if unread_only:
        query = query.eq("is_read", False)
    res = query.order("created_at", desc=True).limit(50).execute()
    return res.data


@router.put("/{notification_id}/read")
def mark_read(notification_id: str, user: CurrentUser = Depends(get_current_user)):
    supabase = get_supabase()
    supabase.table("notifications").update({"is_read": True}).eq("id", notification_id).eq("user_id", user.id).execute()
    return {"message": "Marked as read"}


@router.put("/read-all")
def mark_all_read(user: CurrentUser = Depends(get_current_user)):
    supabase = get_supabase()
    supabase.table("notifications").update({"is_read": True}).eq("user_id", user.id).execute()
    return {"message": "All notifications marked as read"}
