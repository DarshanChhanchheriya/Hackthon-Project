# Attendify — AI Attendance System

**HackNova 2026 · Theme: Smart IT Solutions for Real-World Problems**

A production-quality, full-stack attendance platform that replaces manual roll calls with **self-service face recognition check-ins**, real-time session notifications, teacher punch-in/punch-out tracking, and a QR code backup — all backed by live analytics, leave management, and one-click reporting.

![status](https://img.shields.io/badge/status-hackathon--ready-2563eb) ![python](https://img.shields.io/badge/backend-FastAPI-009485) ![db](https://img.shields.io/badge/database-Supabase%20PostgreSQL-3ecf8e)

**Live demo:** [hackthon-project-chi.vercel.app](https://hackthon-project-chi.vercel.app) · **API:** [hackthon-project-ua81.onrender.com](https://hackthon-project-ua81.onrender.com)

---

## ✨ Features

| Area | Capabilities |
|---|---|
| **Attendance Sessions** | Teacher starts a session for their subject (no camera needed on the teacher's side) — every enrolled student in that department gets a real-time notification instantly via Supabase Realtime |
| **Face Recognition Check-in** | Student taps the notification (or visits **Notifications**) and their camera auto-captures and matches against their own enrolled face — no manual "Capture" click required, with a manual fallback if auto-detection times out |
| **Guided Face Enrollment** | 5-pose guided capture flow (look center/left/right/up/down) with a live oval face guide, done once at signup or from **Profile** |
| **Teacher Punch-in / Punch-out** | Teachers mark their own attendance via face recognition, with automatic late detection (IST-aware, Sunday holidays excluded) and minutes-late display |
| **QR Attendance (backup)** | Teacher-generated, time-boxed QR codes as a fallback method when face check-in isn't available |
| **Leave Management** | Student applies for leave (date range) → teacher/admin approves/rejects → automatically reflected in attendance history |
| **Analytics** | Daily/weekly/monthly trends, department & subject breakdowns, live dashboard cards, Chart.js visualizations |
| **Reports** | PDF / Excel / CSV export for any period or department |
| **Auth & Roles** | Supabase Auth (email/password, OTP-based password reset), JWT-protected FastAPI routes (HS256 and ES256/JWKS both supported), Student / Teacher / Admin RBAC, Postgres Row-Level Security |
| **UI/UX** | Tailwind CSS, glassmorphism, light & dark mode, mirrored camera preview, responsive mobile-first layout, password show/hide toggles, toasts, modals, skeleton loaders |

---

## 🧱 Tech Stack

- **Frontend:** HTML5, Tailwind CSS (CDN), Vanilla JS, Chart.js, jsQR
- **Backend:** Python, FastAPI, slowapi (rate limiting), loguru
- **AI:** OpenCV, `face_recognition` (dlib, 128-d encodings) — only enabled where dlib is available; degrades gracefully on hosts without it
- **Database & Auth:** Supabase (PostgreSQL + Auth + Row-Level Security + Realtime)
- **Reports:** ReportLab (PDF), openpyxl/pandas (Excel/CSV)
- **Deployment:** Vercel (frontend), Render (backend), Supabase (database)

---

## 📁 Folder Structure

```
AI-Attendance-System/
├── frontend/
│   ├── assets/
│   │   ├── css/style.css
│   │   └── js/ (config, supabase-client, api, ui, theme, charts, layout,
│   │            session-alerts, guided-face-capture, password-toggle)
│   ├── pages/ (login, register, forgot-password, dashboard, attendance,
│   │            qr, students, teachers, leave, analytics, reports,
│   │            profile, settings, notifications)
│   └── index.html
├── backend/
│   ├── app.py                  # FastAPI entrypoint
│   ├── config.py                # Settings (pydantic-settings)
│   ├── database.py              # Supabase clients + transient-error retry
│   ├── requirements.txt         # full deps (local dev, includes dlib)
│   ├── requirements-cloud.txt   # cloud deps (Render — excludes dlib/face_recognition)
│   ├── routes/                  # auth, students, teachers, attendance, face,
│   │                             # sessions, teacher_attendance, qr, leave,
│   │                             # analytics, reports, notifications
│   ├── models/schemas.py        # Pydantic request/response models
│   ├── services/
│   │   ├── face_recognition/    # encoder.py, recognizer.py
│   │   ├── qr/                  # qr_service.py
│   │   ├── analytics/           # analytics_service.py
│   │   └── reports/             # report_service.py
│   ├── middleware/auth.py       # JWT decode + role guards
│   └── utils/ (security.py — HS256/ES256 JWT verify, logger.py)
├── database/
│   ├── schema.sql                                    # base schema + RLS
│   ├── migration_001_teacher_fk_to_profiles.sql
│   ├── migration_002_fix_attendance_dedup.sql
│   ├── migration_003_sessions_teacher_attendance_qr.sql
│   ├── migration_004_admin_employee_id_optional.sql
│   └── migration_005_public_departments_read.sql
├── vercel.json
├── render.yaml
└── README.md
```

---

## 🚀 Getting Started

### 1. Supabase Setup

1. Create a project at [supabase.com](https://supabase.com).
2. Open the **SQL Editor** and run [`database/schema.sql`](database/schema.sql), then run each `migration_00N_*.sql` file **in order** — they add sessions, teacher punch-in tracking, and fix RLS gaps found after the initial schema shipped.
3. Under **Project Settings → API**, copy:
   - `Project URL` → `SUPABASE_URL`
   - `anon public` key → `SUPABASE_ANON_KEY`
   - `service_role` key → `SUPABASE_SERVICE_ROLE_KEY` (⚠️ never expose this in frontend code)
4. Under **Authentication → Providers**, email/password should be enabled by default.
5. Under **Database → Replication**, make sure the `notifications` table has Realtime enabled (migration_003 does this, but double-check in the dashboard).

### 2. Backend Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # fill in Supabase values
uvicorn app:app --reload
```

API docs available at `http://localhost:8000/docs` (Swagger) and `/redoc`.

> **Note:** `face_recognition` depends on `dlib`, which needs CMake + a C++ compiler to build.
> - Windows: install [Visual Studio Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) and [CMake](https://cmake.org/download/).
> - Linux: `sudo apt-get install -y cmake build-essential`.
> - macOS: `brew install cmake`.
>
> For platforms without compiler access (e.g. Render's free tier), use `requirements-cloud.txt` instead — the backend detects a missing `face_recognition` import and disables only the encoding/matching endpoints, the rest of the API still runs.

### 3. Frontend Setup

The frontend is static HTML/JS — no build step required.

1. Edit `frontend/assets/js/config.js`:
   ```js
   window.APP_CONFIG = {
     SUPABASE_URL: "https://YOUR-PROJECT-REF.supabase.co",
     SUPABASE_ANON_KEY: "YOUR-SUPABASE-ANON-KEY",
     API_BASE_URL: "http://localhost:8000/api/v1",
   };
   ```
2. Serve the folder (e.g. VS Code "Live Server", or `npx serve frontend`) and open `index.html`.

### 4. First-Run Flow

1. Register an **Admin** account on `pages/register.html`.
2. Log in → Admin dashboard → add departments/teachers/students as needed.
3. Everyone enrolls their face once via the guided capture flow (at signup or from **Profile**).
4. A teacher opens **Attendance Session** and hits **Start Session** for their subject — no camera needed on their end.
5. Every student in that department gets an instant notification; tapping it opens their camera, which auto-captures and marks them present. Missed the popup? The **Notifications** page has the same check-in flow.
6. Teachers punch in/out for their own attendance from the **Dashboard** punch-in card (face-based, tracks lateness).
7. QR codes (**QR Attendance** page) remain available as a manual backup method.

---

## 🔑 Environment Variables

**Backend (`backend/.env`)** — see [`backend/.env.example`](backend/.env.example):

| Variable | Description |
|---|---|
| `SUPABASE_URL` | Your Supabase project URL |
| `SUPABASE_ANON_KEY` | Public anon key (safe for client use) |
| `SUPABASE_SERVICE_ROLE_KEY` | Server-only key, bypasses RLS |
| `SUPABASE_JWT_SECRET` | Used for legacy HS256 token verification; ES256/RS256 tokens are verified against Supabase's JWKS endpoint automatically |
| `CORS_ORIGINS` | Comma-separated list of allowed frontend origins |
| `FACE_MATCH_THRESHOLD` | Minimum confidence (0–1) to auto-mark attendance (default `0.70`) |
| `FACE_DISTANCE_TOLERANCE` | Max face-distance considered a match before scoring (default `0.6`) |
| `SCHOOL_TIMEZONE_OFFSET_HOURS` | Offset from UTC used for punch-in deadlines and late detection (default `5.5`, IST) |
| `QR_EXPIRY_SECONDS` | QR session lifetime in seconds (default `120`) |

**Frontend (`frontend/assets/js/config.js`)**: `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `API_BASE_URL`.

---

## ☁️ Deployment

### Frontend → Vercel
`vercel.json` at the repo root serves the `frontend/` directory as static output. Set `API_BASE_URL` in `config.js` to your deployed Render URL before deploying, then either connect the GitHub repo in the Vercel dashboard or run:
```bash
vercel --prod
```

### Backend → Render
1. Push this repo to GitHub.
2. In Render, create a new **Web Service** from the repo — `render.yaml` pre-configures the build (`rootDir: backend`, `pip install -r requirements-cloud.txt`) and start command.
3. Add the Supabase secrets as environment variables in the Render dashboard (marked `sync: false` in `render.yaml`).
4. Set `CORS_ORIGINS` to your exact Vercel domain (including `https://`, no trailing slash).

### Database → Supabase
Already hosted — run `database/schema.sql` followed by all `migration_00N_*.sql` files in order.

---

## 🔐 Security Notes

- Passwords are hashed and managed entirely by Supabase Auth (bcrypt under the hood) — the backend never stores raw passwords.
- All protected API routes require a valid Supabase JWT (`Authorization: Bearer <token>`), verified via HS256 secret or ES256/RS256 JWKS depending on the project's signing key.
- Role-based authorization is enforced both in FastAPI (`require_admin`, `require_teacher`, etc.) and at the database layer via Postgres RLS policies.
- The `service_role` key is used **only** server-side and must never be shipped to the frontend.
- API requests are rate-limited via `slowapi` (default `60/minute`, configurable).
- Duplicate attendance (same student/date/subject) is blocked at both the API and database (`unique` constraint) levels.
- Face check-ins are session-gated — recognition only runs against an active session and only matches the requesting student's own enrolled encodings, not the whole class roster.

---

## 📸 Screenshots

> _Add screenshots/GIFs of the landing page, dashboard, session notification + face check-in, and analytics view here before submission._

| Landing | Dashboard | Face Check-in | Analytics |
|---|---|---|---|
| _placeholder_ | _placeholder_ | _placeholder_ | _placeholder_ |

---

## 📄 License

MIT License — built for HackNova 2026. Free to use and adapt for educational purposes.
