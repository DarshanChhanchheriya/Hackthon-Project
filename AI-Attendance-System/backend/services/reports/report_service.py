import io
from datetime import date

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

from database import get_supabase


def _fetch_rows(start: date, end: date, department_id: str | None) -> list[dict]:
    supabase = get_supabase()
    query = (
        supabase.table("attendance")
        .select("date, status, method, confidence, subject, students(roll_number, profiles(full_name), departments(name))")
        .gte("date", start.isoformat())
        .lte("date", end.isoformat())
        .order("date")
    )
    if department_id:
        query = query.eq("department_id", department_id)
    rows = query.execute().data or []

    flat = []
    for r in rows:
        student = r.get("students") or {}
        flat.append(
            {
                "Date": r["date"],
                "Roll No": student.get("roll_number", ""),
                "Name": (student.get("profiles") or {}).get("full_name", ""),
                "Department": (student.get("departments") or {}).get("name", ""),
                "Subject": r.get("subject", ""),
                "Status": r["status"],
                "Method": r["method"],
                "Confidence": r.get("confidence", ""),
            }
        )
    return flat


def build_csv(start: date, end: date, department_id: str | None = None) -> bytes:
    df = pd.DataFrame(_fetch_rows(start, end, department_id))
    return df.to_csv(index=False).encode("utf-8")


def build_excel(start: date, end: date, department_id: str | None = None) -> bytes:
    df = pd.DataFrame(_fetch_rows(start, end, department_id))
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Attendance Report")
    return buf.getvalue()


def build_pdf(start: date, end: date, department_id: str | None = None) -> bytes:
    rows = _fetch_rows(start, end, department_id)
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=20 * mm)
    styles = getSampleStyleSheet()

    elements = [
        Paragraph("AI Attendance System — Report", styles["Title"]),
        Paragraph(f"Period: {start.isoformat()} to {end.isoformat()}", styles["Normal"]),
        Spacer(1, 12),
    ]

    header = ["Date", "Roll No", "Name", "Department", "Subject", "Status", "Method"]
    data = [header] + [[r[h] for h in header] for r in rows]

    table = Table(data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563eb")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e5e7eb")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ]
        )
    )
    elements.append(table)
    doc.build(elements)
    return buf.getvalue()
