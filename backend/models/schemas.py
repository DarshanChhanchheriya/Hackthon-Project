from datetime import date, datetime
from typing import Optional, Literal

from pydantic import BaseModel, EmailStr, Field


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str
    role: Literal["student", "teacher", "admin"] = "student"
    phone: Optional[str] = None
    roll_number: Optional[str] = None
    employee_id: Optional[str] = None
    department_id: Optional[str] = None
    semester: Optional[int] = 1
    section: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    access_token: str
    new_password: str = Field(min_length=8)


class OTPRequestModel(BaseModel):
    email: EmailStr


class OTPVerifyResetRequest(BaseModel):
    email: EmailStr
    otp: str = Field(min_length=6, max_length=6)
    new_password: str = Field(min_length=8)


# ---------------------------------------------------------------------------
# Students / Teachers
# ---------------------------------------------------------------------------
class StudentUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    department_id: Optional[str] = None
    semester: Optional[int] = None
    section: Optional[str] = None
    is_active: Optional[bool] = None


class TeacherUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    department_id: Optional[str] = None
    designation: Optional[str] = None
    subjects: Optional[list[str]] = None
    assigned_sections: Optional[list[str]] = None
    primary_subject: Optional[str] = None
    lecture_timing: Optional[str] = None
    punch_in_deadline: Optional[str] = None  # "HH:MM:SS"
    is_active: Optional[bool] = None


# ---------------------------------------------------------------------------
# Face recognition
# ---------------------------------------------------------------------------
class FaceEnrollRequest(BaseModel):
    owner_id: str
    images_base64: list[str] = Field(min_length=3, max_length=8)


class FaceRecognizeRequest(BaseModel):
    image_base64: str
    teacher_id: str
    subject: Optional[str] = None
    department_id: Optional[str] = None
    session_id: Optional[str] = None


class FaceRecognizeResult(BaseModel):
    matched: bool
    student_id: Optional[str] = None
    full_name: Optional[str] = None
    roll_number: Optional[str] = None
    department: Optional[str] = None
    confidence: Optional[float] = None
    status: Optional[str] = None
    message: str


class FaceSelfCheckinRequest(BaseModel):
    session_id: str
    image_base64: str


class TeacherPunchRequest(BaseModel):
    image_base64: str


# ---------------------------------------------------------------------------
# Attendance sessions (live, teacher-started)
# ---------------------------------------------------------------------------
class SessionStartRequest(BaseModel):
    department_id: Optional[str] = None
    subject: Optional[str] = None
    section: Optional[str] = None
    punch_in_grace_minutes: int = 10


# ---------------------------------------------------------------------------
# QR attendance
# ---------------------------------------------------------------------------
class QRGenerateRequest(BaseModel):
    teacher_id: str
    subject: Optional[str] = None
    section: Optional[str] = None
    department_id: Optional[str] = None


class QRScanRequest(BaseModel):
    token: str
    student_id: str


class StudentPersonalQRCheckinRequest(BaseModel):
    """Teacher scans a student's permanent personal ID-QR during an active session."""
    session_id: str
    student_token: str


# ---------------------------------------------------------------------------
# Attendance
# ---------------------------------------------------------------------------
class ManualAttendanceRequest(BaseModel):
    student_id: str
    teacher_id: str
    subject: Optional[str] = None
    status: Literal["present", "absent", "late"] = "present"


# ---------------------------------------------------------------------------
# Leave
# ---------------------------------------------------------------------------
class LeaveCreateRequest(BaseModel):
    reason: str
    start_date: date
    end_date: date


class LeaveReviewRequest(BaseModel):
    status: Literal["approved", "rejected"]
    review_note: Optional[str] = None


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------
class ReportRequest(BaseModel):
    period: Literal["daily", "weekly", "monthly", "semester"]
    department_id: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    export: Literal["pdf", "excel", "csv"] = "pdf"
