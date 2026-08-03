from datetime import date, timedelta

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from middleware.auth import require_teacher, CurrentUser
from models.schemas import ReportRequest
from services.reports import report_service

router = APIRouter(prefix="/reports", tags=["Reports"])

MEDIA_TYPES = {
    "pdf": "application/pdf",
    "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "csv": "text/csv",
}
BUILDERS = {
    "pdf": report_service.build_pdf,
    "excel": report_service.build_excel,
    "csv": report_service.build_csv,
}
EXTENSIONS = {"pdf": "pdf", "excel": "xlsx", "csv": "csv"}


def _resolve_period(payload: ReportRequest) -> tuple[date, date]:
    if payload.start_date and payload.end_date:
        return payload.start_date, payload.end_date

    today = date.today()
    if payload.period == "daily":
        return today, today
    if payload.period == "weekly":
        return today - timedelta(days=7), today
    if payload.period == "monthly":
        return today - timedelta(days=30), today
    return today - timedelta(days=180), today  # semester


@router.post("/generate")
def generate_report(payload: ReportRequest, user: CurrentUser = Depends(require_teacher)):
    start, end = _resolve_period(payload)
    content = BUILDERS[payload.export](start, end, payload.department_id)
    filename = f"attendance-report-{payload.period}-{start}-to-{end}.{EXTENSIONS[payload.export]}"

    return Response(
        content=content,
        media_type=MEDIA_TYPES[payload.export],
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
