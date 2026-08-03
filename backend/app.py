from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from config import get_settings
from routes import auth, students, teachers, attendance, face, qr, leave, analytics, reports, notifications, sessions, teacher_attendance
from utils.logger import logger

settings = get_settings()
limiter = Limiter(key_func=get_remote_address, default_limits=[settings.RATE_LIMIT_DEFAULT])

app = FastAPI(
    title=settings.APP_NAME,
    description="Production-grade REST API for the AI Attendance System — face recognition, "
    "QR attendance, leave management, analytics and reporting.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled error on {request.method} {request.url.path}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error. Please try again later."},
    )


@app.get("/", tags=["Health"])
def root():
    return {"service": settings.APP_NAME, "status": "online", "docs": "/docs"}


@app.get("/health", tags=["Health"])
def health():
    return {"status": "healthy"}


PREFIX = settings.API_PREFIX
app.include_router(auth.router, prefix=PREFIX)
app.include_router(students.router, prefix=PREFIX)
app.include_router(teachers.router, prefix=PREFIX)
app.include_router(attendance.router, prefix=PREFIX)
app.include_router(face.router, prefix=PREFIX)
app.include_router(qr.router, prefix=PREFIX)
app.include_router(leave.router, prefix=PREFIX)
app.include_router(analytics.router, prefix=PREFIX)
app.include_router(reports.router, prefix=PREFIX)
app.include_router(notifications.router, prefix=PREFIX)
app.include_router(sessions.router, prefix=PREFIX)
app.include_router(teacher_attendance.router, prefix=PREFIX)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=settings.ENV == "development")
