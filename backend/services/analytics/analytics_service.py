from datetime import date, timedelta
from collections import defaultdict

from database import get_supabase


def _date_range(start: date, end: date):
    days = (end - start).days
    return [start + timedelta(days=i) for i in range(days + 1)]


def overview_stats() -> dict:
    supabase = get_supabase()
    today = date.today().isoformat()

    total_students = supabase.table("students").select("id", count="exact").execute().count or 0
    total_teachers = supabase.table("teachers").select("id", count="exact").execute().count or 0

    today_rows = supabase.table("attendance").select("status").eq("date", today).execute().data or []
    present_today = sum(1 for r in today_rows if r["status"] in ("present", "late"))
    absent_today = max(total_students - present_today, 0)
    percentage = round((present_today / total_students) * 100, 2) if total_students else 0.0

    return {
        "total_students": total_students,
        "total_teachers": total_teachers,
        "present_today": present_today,
        "absent_today": absent_today,
        "attendance_percentage": percentage,
    }


def trend(period: str = "monthly", department_id: str | None = None) -> list[dict]:
    supabase = get_supabase()
    today = date.today()
    start = today - timedelta(days=7 if period == "weekly" else 30)

    query = supabase.table("attendance").select("date, status, department_id").gte("date", start.isoformat())
    if department_id:
        query = query.eq("department_id", department_id)
    rows = query.execute().data or []

    by_day: dict[str, dict[str, int]] = defaultdict(lambda: {"present": 0, "absent": 0, "late": 0})
    for r in rows:
        bucket = by_day[r["date"]]
        bucket[r["status"]] = bucket.get(r["status"], 0) + 1

    result = []
    for d in _date_range(start, today):
        key = d.isoformat()
        counts = by_day.get(key, {"present": 0, "absent": 0, "late": 0})
        result.append({"date": key, **counts})
    return result


def department_breakdown() -> list[dict]:
    supabase = get_supabase()
    today = date.today().isoformat()
    departments = supabase.table("departments").select("id, name").execute().data or []
    rows = supabase.table("attendance").select("department_id, status").eq("date", today).execute().data or []

    counts: dict[str, dict[str, int]] = defaultdict(lambda: {"present": 0, "absent": 0, "late": 0})
    for r in rows:
        dep = r.get("department_id")
        if dep:
            counts[dep][r["status"]] = counts[dep].get(r["status"], 0) + 1

    return [
        {"department": d["name"], **counts.get(d["id"], {"present": 0, "absent": 0, "late": 0})}
        for d in departments
    ]


def heatmap_calendar(student_id: str, year: int, month: int) -> list[dict]:
    supabase = get_supabase()
    start = date(year, month, 1)
    end = date(year, month + 1, 1) - timedelta(days=1) if month < 12 else date(year, 12, 31)
    rows = (
        supabase.table("attendance")
        .select("date, status")
        .eq("student_id", student_id)
        .gte("date", start.isoformat())
        .lte("date", end.isoformat())
        .execute()
        .data
        or []
    )
    return [{"date": r["date"], "status": r["status"]} for r in rows]
