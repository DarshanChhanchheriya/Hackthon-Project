from fastapi import APIRouter, Depends

from middleware.auth import require_teacher, require_any, CurrentUser
from services.analytics import analytics_service

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/overview")
def overview(user: CurrentUser = Depends(require_teacher)):
    return analytics_service.overview_stats()


@router.get("/trend")
def trend(period: str = "monthly", department_id: str | None = None, user: CurrentUser = Depends(require_teacher)):
    return analytics_service.trend(period, department_id)


@router.get("/departments")
def departments(user: CurrentUser = Depends(require_teacher)):
    return analytics_service.department_breakdown()


@router.get("/heatmap")
def heatmap(student_id: str, year: int, month: int, user: CurrentUser = Depends(require_any)):
    return analytics_service.heatmap_calendar(student_id, year, month)
