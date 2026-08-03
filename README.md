# AttendifyAI — AI Attendance System

**HackNova 2026 · Theme: Smart IT Solutions for Real-World Problems**

A production-quality, full-stack attendance platform that replaces manual roll calls with **face recognition** and **secure QR check-ins**, backed by real-time analytics, leave management, and one-click reporting.

![status](https://img.shields.io/badge/status-hackathon--ready-2563eb) ![python](https://img.shields.io/badge/backend-FastAPI-009485) ![db](https://img.shields.io/badge/database-Supabase%20PostgreSQL-3ecf8e)

---

## ✨ Features

| Area | Capabilities |
|---|---|
| **Face Recognition** | OpenCV + `face_recognition` (128-d encodings), 5-sample enrollment, blink/liveness check, confidence-scored auto marking (≥90%), duplicate-attendance prevention |
| **QR Attendance** | Secure per-session tokens, 2-minute auto-expiry, one-scan-per-day enforcement |
| **Leave Management** | Student apply → teacher/admin approve/reject → auto-reflected in attendance history |
| **Analytics** | Daily/weekly/monthly trends, department & subject breakdowns, heatmap calendar, live dashboard cards |
| **Reports** | PDF / Excel / CSV export for any period or department |
| **Auth & Roles** | Supabase Auth (email/password, verification, reset), JWT-protected FastAPI routes, Student / Teacher / Admin RBAC, Postgres Row-Level Security |
| **UI/UX** | Tailwind CSS, glassmorphism, light & dark mode, responsive sidebar/topbar shell, toasts, modals, skeleton loaders, Chart.js visualizations |

---

## 🧱 Tech Stack

- **Frontend:** HTML5, Tailwind CSS (CDN), Vanilla JS, Chart.js, jsQR
- **Backend:** Python, FastAPI, slowapi (rate limiting), loguru
- **AI:** OpenCV, `face_recognition`, NumPy
- **Database & Auth:** Supabase (PostgreSQL + Auth + RLS)
- **Reports:** ReportLab (PDF), openpyxl/pandas (Excel/CSV)
- **Deployment:** Vercel (frontend), Render (backend), Supabase (database)

---

## 📁 Folder Structure

```
AI-Attendance-System/
├── frontend/
│   ├── assets/
│   │   ├── css/style.css
│   │   └── js/ (config, supabase-client, api, ui, theme, charts, layout)
│   ├── pages/ (login, register, dashboard, attendance, qr, students,
│   │            teachers, leave, analytics, reports, profile, settings,
│   │            notifications, forgot-password)
│   └── index.html
├── backend/
│   ├── app.py                 # FastAPI entrypoint
│   ├── config.py               # Settings (pydantic-settings)
│   ├── database.py             # Supabase clients
│   ├── requirements.txt
│   ├── routes/                 # auth, students, teachers, attendance,
│   │                            # face, qr, leave, analytics, reports, notifications
│   ├── models/schemas.py       # Pydantic request/response models
│   ├── services/
│   │   ├── face_recognition/   # encoder.py, recognizer.py
│   │   ├── qr/                 # qr_service.py
│   │   ├── analytics/          # analytics_service.py
│   │   └── reports/            # report_service.py
│   ├── middleware/auth.py      # JWT decode + role guards
│   └── utils/ (security.py, logger.py)
├── database/schema.sql         # Full Supabase schema + RLS policies
├── vercel.json
├── render.yaml
└── README.md
```

---

## 🚀 Getting Started

### 1. Supabase Setup

1. Create a project at [supabase.com](https://supabase.com).
2. Open the **SQL Editor** and run [`database/schema.sql`](database/schema.sql) — this creates all tables, enums, triggers, and Row-Level Security policies, and seeds a few departments.
3. Under **Project Settings → API**, copy:
   - `Project URL` → `SUPABASE_URL`
   - `anon public` key → `SUPABASE_ANON_KEY`
   - `service_role` key → `SUPABASE_SERVICE_ROLE_KEY` (⚠️ never expose this in frontend code)
4. Under **Project Settings → API → JWT Settings**, copy the `JWT Secret` → `SUPABASE_JWT_SECRET`.
5. Under **Authentication → Email Templates**, enable email confirmations if desired.

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
2. Verify the email (check Supabase Auth logs in dev if email isn't configured).
3. Log in → Admin dashboard → add departments/teachers/students as needed.
4. Students enroll their face from **Profile → Face Registration** (5 photo captures).
5. Teachers start a session from **Live Camera** or generate a **QR** code.

---

## 🔑 Environment Variables

**Backend (`backend/.env`)** — see [`backend/.env.example`](backend/.env.example):

| Variable | Description |
|---|---|
| `SUPABASE_URL` | Your Supabase project URL |
| `SUPABASE_ANON_KEY` | Public anon key (safe for client use) |
| `SUPABASE_SERVICE_ROLE_KEY` | Server-only key, bypasses RLS |
| `SUPABASE_JWT_SECRET` | Used to verify Supabase-issued access tokens |
| `CORS_ORIGINS` | Comma-separated list of allowed frontend origins |
| `FACE_MATCH_THRESHOLD` | Minimum confidence (0–1) to auto-mark attendance (default `0.90`) |
| `QR_EXPIRY_SECONDS` | QR session lifetime in seconds (default `120`) |

**Frontend (`frontend/assets/js/config.js`)**: `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `API_BASE_URL`.

---

## ☁️ Deployment

### Frontend → Vercel
```bash
vercel --prod
```
`vercel.json` at the repo root serves the `frontend/` directory as static output. Update `API_BASE_URL` in `config.js` to your deployed Render URL before deploying.

### Backend → Render
1. Push this repo to GitHub.
2. In Render, create a new **Web Service** from the repo — `render.yaml` pre-configures the build (`rootDir: backend`, installs CMake for `dlib`) and start commands.
3. Add the Supabase secrets as environment variables in the Render dashboard (marked `sync: false` in `render.yaml`).
4. Update `CORS_ORIGINS` to your Vercel domain.

### Database → Supabase
Already hosted — no extra deployment step beyond running `database/schema.sql`.

---

## 🔐 Security Notes

- Passwords are hashed and managed entirely by Supabase Auth (bcrypt under the hood) — the backend never stores raw passwords.
- All protected API routes require a valid Supabase JWT (`Authorization: Bearer <token>`), verified against `SUPABASE_JWT_SECRET`.
- Role-based authorization is enforced both in FastAPI (`require_admin`, `require_teacher`, etc.) and at the database layer via Postgres RLS policies.
- The `service_role` key is used **only** server-side and must never be shipped to the frontend.
- API requests are rate-limited via `slowapi` (default `60/minute`, configurable).
- Duplicate attendance (same student/date/subject) is blocked at both the API and database (`unique` constraint) levels.

---

## 📸 Screenshots

> _Add screenshots/GIFs of the landing page, dashboard, live face-recognition session, and analytics view here before submission._

| Landing | Dashboard | Live Recognition | Analytics |
|---|---|---|---|
| _placeholder_ | _placeholder_ | _placeholder_ | _placeholder_ |

---

## 📄 License

MIT License — built for HackNova 2026. Free to use and adapt for educational purposes.
