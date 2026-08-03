from fastapi import APIRouter, Depends, HTTPException, status

from database import get_supabase
from middleware.auth import require_admin, require_any, CurrentUser
from models.schemas import StudentUpdate

router = APIRouter(prefix="/students", tags=["Students"])


@router.get("")
def list_students(
    department_id: str | None = None,
    semester: int | None = None,
    section: str | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 20,
    user: CurrentUser = Depends(require_any),
):
    supabase = get_supabase()
    query = supabase.table("students").select(
        "*, profiles(full_name, email, phone, avatar_url, is_active), departments(name)", count="exact"
    )
    if department_id:
        query = query.eq("department_id", department_id)
    if semester:
        query = query.eq("semester", semester)
    if section:
        query = query.eq("section", section)
    if search:
        query = query.or_(f"roll_number.ilike.%{search}%")

    start = (page - 1) * page_size
    res = query.range(start, start + page_size - 1).execute()
    return {"data": res.data, "total": res.count, "page": page, "page_size": page_size}


@router.get("/{student_id}")
def get_student(student_id: str, user: CurrentUser = Depends(require_any)):
    supabase = get_supabase()
    res = (
        supabase.table("students")
        .select("*, profiles(full_name, email, phone, avatar_url), departments(name)")
        .eq("id", student_id)
        .single()
        .execute()
    )
    if not res.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")
    return res.data


@router.put("/{student_id}")
def update_student(student_id: str, payload: StudentUpdate, user: CurrentUser = Depends(require_admin)):
    supabase = get_supabase()
    profile_fields = {k: v for k, v in payload.model_dump(exclude_unset=True).items() if k in ("full_name", "phone", "is_active")}
    student_fields = {k: v for k, v in payload.model_dump(exclude_unset=True).items() if k in ("department_id", "semester", "section")}

    if profile_fields:
        supabase.table("profiles").update(profile_fields).eq("id", student_id).execute()
    if student_fields:
        supabase.table("students").update(student_fields).eq("id", student_id).execute()

    return {"message": "Student updated successfully"}


@router.delete("/{student_id}")
def delete_student(student_id: str, user: CurrentUser = Depends(require_admin)):
    supabase = get_supabase()
    supabase.table("profiles").delete().eq("id", student_id).execute()
    supabase.auth.admin.delete_user(student_id)
    return {"message": "Student deleted successfully"}
