-- ============================================================
-- AI Attendance System — Supabase PostgreSQL Schema
-- HackNova 2026
-- Run this in the Supabase SQL editor (or via `supabase db push`)
-- ============================================================

create extension if not exists "uuid-ossp";
create extension if not exists pgcrypto;

-- ------------------------------------------------------------
-- ENUMS
-- ------------------------------------------------------------
create type user_role as enum ('student', 'teacher', 'admin');
create type attendance_status as enum ('present', 'absent', 'late', 'leave');
create type attendance_method as enum ('face', 'qr', 'manual');
create type leave_status as enum ('pending', 'approved', 'rejected');
create type qr_session_status as enum ('active', 'expired', 'closed');

-- ------------------------------------------------------------
-- DEPARTMENTS
-- ------------------------------------------------------------
create table departments (
  id uuid primary key default uuid_generate_v4(),
  name text not null unique,
  code text not null unique,
  created_at timestamptz not null default now()
);

-- ------------------------------------------------------------
-- PROFILES (mirrors auth.users, holds role + shared fields)
-- ------------------------------------------------------------
create table profiles (
  id uuid primary key references auth.users (id) on delete cascade,
  email text not null unique,
  full_name text not null,
  role user_role not null default 'student',
  phone text,
  avatar_url text,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- ------------------------------------------------------------
-- STUDENTS
-- ------------------------------------------------------------
create table students (
  id uuid primary key references profiles (id) on delete cascade,
  roll_number text not null unique,
  department_id uuid references departments (id),
  semester int not null default 1,
  section text,
  admission_year int,
  face_registered boolean not null default false,
  created_at timestamptz not null default now()
);

-- ------------------------------------------------------------
-- TEACHERS
-- ------------------------------------------------------------
create table teachers (
  id uuid primary key references profiles (id) on delete cascade,
  employee_id text not null unique,
  department_id uuid references departments (id),
  designation text,
  subjects text[] default '{}',
  assigned_sections text[] default '{}',
  primary_subject text,
  lecture_timing text,
  punch_in_deadline time not null default '07:00:00',
  created_at timestamptz not null default now()
);

-- ------------------------------------------------------------
-- ADMINS
-- ------------------------------------------------------------
create table admins (
  id uuid primary key references profiles (id) on delete cascade,
  employee_id text unique,
  created_at timestamptz not null default now()
);

-- ------------------------------------------------------------
-- FACE ENCODINGS (128-d face_recognition vectors, base64 float array)
-- ------------------------------------------------------------
create table face_encodings (
  id uuid primary key default uuid_generate_v4(),
  owner_id uuid not null references profiles (id) on delete cascade,
  encoding double precision[] not null,
  sample_index int not null default 1,
  image_url text,
  created_at timestamptz not null default now()
);
create index idx_face_encodings_owner on face_encodings (owner_id);

-- ------------------------------------------------------------
-- QR SESSIONS (teacher-generated, short-lived)
-- ------------------------------------------------------------
create table qr_sessions (
  id uuid primary key default uuid_generate_v4(),
  teacher_id uuid not null references profiles (id) on delete cascade,
  department_id uuid references departments (id),
  subject text,
  section text,
  token text not null unique,
  status qr_session_status not null default 'active',
  expires_at timestamptz not null,
  created_at timestamptz not null default now()
);
create index idx_qr_sessions_token on qr_sessions (token);

-- ------------------------------------------------------------
-- ATTENDANCE SESSIONS — a teacher "opens" a live session (face or
-- personal-QR mode); students are notified in real time and can only
-- self-check-in while it's active.
-- ------------------------------------------------------------
create type session_status as enum ('active', 'closed');

create table attendance_sessions (
  id uuid primary key default uuid_generate_v4(),
  teacher_id uuid not null references profiles (id) on delete cascade,
  department_id uuid references departments (id),
  subject text not null default '',
  section text,
  status session_status not null default 'active',
  punch_in_grace_minutes int not null default 10,
  starts_at timestamptz not null default now(),
  ends_at timestamptz
);
create index idx_attendance_sessions_active on attendance_sessions (status, department_id);

-- ------------------------------------------------------------
-- ATTENDANCE
-- ------------------------------------------------------------
create table attendance (
  id uuid primary key default uuid_generate_v4(),
  student_id uuid not null references students (id) on delete cascade,
  teacher_id uuid references profiles (id),
  department_id uuid references departments (id),
  subject text not null default '',
  status attendance_status not null default 'present',
  method attendance_method not null default 'manual',
  confidence numeric(5, 2),
  qr_session_id uuid references qr_sessions (id),
  session_id uuid references attendance_sessions (id),
  date date not null default current_date,
  marked_at timestamptz not null default now(),
  unique (student_id, date, subject)
);
create index idx_attendance_student_date on attendance (student_id, date);
create index idx_attendance_date on attendance (date);

-- ------------------------------------------------------------
-- TEACHER ATTENDANCE — punch-in / punch-out via face recognition.
-- ------------------------------------------------------------
create table teacher_attendance (
  id uuid primary key default uuid_generate_v4(),
  teacher_id uuid not null references profiles (id) on delete cascade,
  date date not null default current_date,
  punch_in_at timestamptz,
  punch_in_method attendance_method,
  punch_in_confidence numeric(5, 2),
  punch_in_status text, -- 'on_time' | 'late'
  punch_out_at timestamptz,
  punch_out_method attendance_method,
  unique (teacher_id, date)
);

-- ------------------------------------------------------------
-- ATTENDANCE LOGS (raw audit trail incl. rejected/fraud attempts)
-- ------------------------------------------------------------
create table attendance_logs (
  id uuid primary key default uuid_generate_v4(),
  student_id uuid references students (id) on delete set null,
  event text not null, -- e.g. 'face_match', 'face_reject', 'qr_scan', 'duplicate_blocked', 'liveness_fail'
  detail jsonb default '{}',
  ip_address text,
  created_at timestamptz not null default now()
);

-- ------------------------------------------------------------
-- LEAVE REQUESTS
-- ------------------------------------------------------------
create table leave_requests (
  id uuid primary key default uuid_generate_v4(),
  student_id uuid not null references students (id) on delete cascade,
  reviewed_by uuid references profiles (id),
  reason text not null,
  start_date date not null,
  end_date date not null,
  status leave_status not null default 'pending',
  review_note text,
  created_at timestamptz not null default now(),
  reviewed_at timestamptz
);
create index idx_leave_student on leave_requests (student_id);

-- ------------------------------------------------------------
-- NOTIFICATIONS
-- ------------------------------------------------------------
create table notifications (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid not null references profiles (id) on delete cascade,
  title text not null,
  message text not null,
  type text not null default 'info', -- info | success | warning | error
  is_read boolean not null default false,
  created_at timestamptz not null default now()
);
create index idx_notifications_user on notifications (user_id, is_read);

-- ------------------------------------------------------------
-- ANALYTICS (materialized daily rollups, refreshed by backend job)
-- ------------------------------------------------------------
create table analytics (
  id uuid primary key default uuid_generate_v4(),
  scope text not null, -- 'overall' | 'department' | 'subject'
  scope_ref text,       -- department_id or subject name
  date date not null,
  total_present int not null default 0,
  total_absent int not null default 0,
  total_late int not null default 0,
  total_students int not null default 0,
  percentage numeric(5, 2) not null default 0,
  created_at timestamptz not null default now(),
  unique (scope, scope_ref, date)
);

-- ------------------------------------------------------------
-- updated_at trigger helper
-- ------------------------------------------------------------
create or replace function set_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

create trigger trg_profiles_updated_at
before update on profiles
for each row execute function set_updated_at();

-- ============================================================
-- ROW LEVEL SECURITY
-- ============================================================
alter table profiles enable row level security;
alter table students enable row level security;
alter table teachers enable row level security;
alter table admins enable row level security;
alter table face_encodings enable row level security;
alter table qr_sessions enable row level security;
alter table attendance enable row level security;
alter table attendance_logs enable row level security;
alter table leave_requests enable row level security;
alter table notifications enable row level security;
alter table analytics enable row level security;
alter table departments enable row level security;
alter table attendance_sessions enable row level security;
alter table teacher_attendance enable row level security;

-- Helper: current user's role
create or replace function current_role_name()
returns user_role as $$
  select role from profiles where id = auth.uid();
$$ language sql stable security definer;

-- profiles: user reads/updates own row; admin reads all
create policy "profiles_self_select" on profiles for select
  using (id = auth.uid() or current_role_name() in ('admin', 'teacher'));
create policy "profiles_self_update" on profiles for update
  using (id = auth.uid()) with check (id = auth.uid());
create policy "profiles_admin_all" on profiles for all
  using (current_role_name() = 'admin');

-- students: self, own teachers, admin
create policy "students_select" on students for select
  using (id = auth.uid() or current_role_name() in ('admin', 'teacher'));
create policy "students_admin_write" on students for insert with check (current_role_name() = 'admin');
create policy "students_admin_update" on students for update using (current_role_name() = 'admin');
create policy "students_admin_delete" on students for delete using (current_role_name() = 'admin');

-- teachers
create policy "teachers_select" on teachers for select
  using (id = auth.uid() or current_role_name() in ('admin', 'teacher'));
create policy "teachers_admin_write" on teachers for insert with check (current_role_name() = 'admin');
create policy "teachers_admin_update" on teachers for update using (current_role_name() = 'admin');
create policy "teachers_admin_delete" on teachers for delete using (current_role_name() = 'admin');

-- admins
create policy "admins_select" on admins for select using (current_role_name() = 'admin');

-- face_encodings: owner (student or teacher) owns, admin can read for recognition
create policy "face_encodings_select" on face_encodings for select
  using (owner_id = auth.uid() or current_role_name() in ('admin', 'teacher'));
create policy "face_encodings_insert" on face_encodings for insert
  with check (owner_id = auth.uid() or current_role_name() in ('admin', 'teacher'));
create policy "face_encodings_delete" on face_encodings for delete
  using (owner_id = auth.uid() or current_role_name() = 'admin');

-- qr_sessions: teacher owns, student can read active session by token via API (service role)
create policy "qr_sessions_teacher" on qr_sessions for all
  using (teacher_id = auth.uid() or current_role_name() = 'admin');
create policy "qr_sessions_read" on qr_sessions for select using (true);

-- attendance
create policy "attendance_select" on attendance for select
  using (student_id = auth.uid() or current_role_name() in ('admin', 'teacher'));
create policy "attendance_write" on attendance for insert
  with check (current_role_name() in ('admin', 'teacher'));
create policy "attendance_update" on attendance for update
  using (current_role_name() in ('admin', 'teacher'));

-- attendance_logs: admin/teacher only
create policy "attendance_logs_select" on attendance_logs for select
  using (current_role_name() in ('admin', 'teacher'));

-- leave_requests
create policy "leave_select" on leave_requests for select
  using (student_id = auth.uid() or current_role_name() in ('admin', 'teacher'));
create policy "leave_insert" on leave_requests for insert
  with check (student_id = auth.uid());
create policy "leave_update" on leave_requests for update
  using (current_role_name() in ('admin', 'teacher'));

-- notifications
create policy "notifications_select" on notifications for select using (user_id = auth.uid());
create policy "notifications_update" on notifications for update using (user_id = auth.uid());
create policy "notifications_insert" on notifications for insert with check (true);

-- analytics: readable by teacher/admin
create policy "analytics_select" on analytics for select
  using (current_role_name() in ('admin', 'teacher'));

-- departments: readable by everyone authenticated, writable by admin
create policy "departments_select" on departments for select using (auth.role() = 'authenticated');
create policy "departments_admin_write" on departments for all using (current_role_name() = 'admin');

-- attendance_sessions: any authenticated user can see active sessions
-- (students need this to know a session is live); only the owning
-- teacher or an admin can create/close one.
create policy "attendance_sessions_select" on attendance_sessions for select
  using (auth.role() = 'authenticated');
create policy "attendance_sessions_teacher_write" on attendance_sessions for all
  using (teacher_id = auth.uid() or current_role_name() = 'admin');

-- teacher_attendance: teacher sees/manages own punch records, admin sees all
create policy "teacher_attendance_select" on teacher_attendance for select
  using (teacher_id = auth.uid() or current_role_name() = 'admin');
create policy "teacher_attendance_write" on teacher_attendance for all
  using (teacher_id = auth.uid() or current_role_name() = 'admin');

-- ------------------------------------------------------------
-- Realtime: push notification INSERTs to subscribed clients instantly
-- (used for "session started" alerts to students).
-- ------------------------------------------------------------
alter publication supabase_realtime add table notifications;

-- ------------------------------------------------------------
-- Seed a few departments
-- ------------------------------------------------------------
insert into departments (name, code) values
  ('Computer Science', 'CSE'),
  ('Information Technology', 'IT'),
  ('Electronics & Communication', 'ECE'),
  ('Mechanical Engineering', 'MECH')
on conflict do nothing;
