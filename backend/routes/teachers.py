from fastapi import APIRouter, Depends, HTTPException, status

from database import get_supabase
from middleware.auth import require_admin, require_any, CurrentUser
from models.schemas import TeacherUpdate

router = APIRouter(prefix="/teachers", tags=["Teachers"])


@router.get("")
def list_teachers(
    department_id: str | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 20,
    user: CurrentUser = Depends(require_any),
):
    supabase = get_supabase()
    query = supabase.table("teachers").select(
        "*, profiles(full_name, email, phone, avatar_url, is_active), departments(name)", count="exact"
    )
    if department_id:
        query = query.eq("department_id", department_id)
    if search:
        query = query.or_(f"employee_id.ilike.%{search}%")

    start = (page - 1) * page_size
    res = query.range(start, start + page_size - 1).execute()
    return {"data": res.data, "total": res.count, "page": page, "page_size": page_size}


@router.get("/{teacher_id}")
def get_teacher(teacher_id: str, user: CurrentUser = Depends(require_any)):
    supabase = get_supabase()
    res = (
        supabase.table("teachers")
        .select("*, profiles(full_name, email, phone, avatar_url), departments(name)")
        .eq("id", teacher_id)
        .single()
        .execute()
    )
    if not res.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Teacher not found")
    return res.data


@router.put("/{teacher_id}")
def update_teacher(teacher_id: str, payload: TeacherUpdate, user: CurrentUser = Depends(require_admin)):
    supabase = get_supabase()
    profile_fields = {k: v for k, v in payload.model_dump(exclude_unset=True).items() if k in ("full_name", "phone", "is_active")}
    teacher_fields = {
        k: v
        for k, v in payload.model_dump(exclude_unset=True).items()
        if k in ("department_id", "designation", "subjects", "assigned_sections", "primary_subject", "lecture_timing", "punch_in_deadline")
    }

    if profile_fields:
        supabase.table("profiles").update(profile_fields).eq("id", teacher_id).execute()
    if teacher_fields:
        supabase.table("teachers").update(teacher_fields).eq("id", teacher_id).execute()

    return {"message": "Teacher updated successfully"}


@router.delete("/{teacher_id}")
def delete_teacher(teacher_id: str, user: CurrentUser = Depends(require_admin)):
    supabase = get_supabase()
    supabase.table("profiles").delete().eq("id", teacher_id).execute()
    supabase.auth.admin.delete_user(teacher_id)
    return {"message": "Teacher deleted successfully"}
