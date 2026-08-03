-- Migration 003: live attendance sessions, real-time student notifications,
-- face-based teacher punch-in/out, personal student ID-QR, generalized
-- face_encodings (students AND teachers can now enroll a face).

-- ------------------------------------------------------------
-- 1. Generalize face_encodings: student_id -> owner_id (profiles)
--    so both students and teachers can enroll a face.
-- ------------------------------------------------------------
alter table face_encodings rename column student_id to owner_id;
alter table face_encodings drop constraint face_encodings_student_id_fkey;
alter table face_encodings
  add constraint face_encodings_owner_id_fkey
  foreign key (owner_id) references profiles (id) on delete cascade;

drop index if exists idx_face_encodings_student;
create index idx_face_encodings_owner on face_encodings (owner_id);

drop policy if exists "face_encodings_select" on face_encodings;
drop policy if exists "face_encodings_insert" on face_encodings;
drop policy if exists "face_encodings_delete" on face_encodings;

create policy "face_encodings_select" on face_encodings for select
  using (owner_id = auth.uid() or current_role_name() in ('admin', 'teacher'));
create policy "face_encodings_insert" on face_encodings for insert
  with check (owner_id = auth.uid() or current_role_name() in ('admin', 'teacher'));
create policy "face_encodings_delete" on face_encodings for delete
  using (owner_id = auth.uid() or current_role_name() = 'admin');

-- ------------------------------------------------------------
-- 2. Extra teacher profile fields: subject, lecture timing, and a
--    fixed morning punch-in deadline (default 07:00).
-- ------------------------------------------------------------
alter table teachers add column if not exists primary_subject text;
alter table teachers add column if not exists lecture_timing text;
alter table teachers add column if not exists punch_in_deadline time not null default '07:00:00';

-- ------------------------------------------------------------
-- 3. ATTENDANCE SESSIONS — a teacher "opens" a live session (face or
--    personal-QR mode); students get notified in real time and can only
--    self-check-in while it's active.
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

alter table attendance_sessions enable row level security;
create policy "attendance_sessions_select" on attendance_sessions for select
  using (auth.role() = 'authenticated');
create policy "attendance_sessions_teacher_write" on attendance_sessions for all
  using (teacher_id = auth.uid() or current_role_name() = 'admin');

-- link attendance rows to the session that produced them (nullable — manual
-- marks and leave-generated rows have no session)
alter table attendance add column if not exists session_id uuid references attendance_sessions (id);

-- ------------------------------------------------------------
-- 4. TEACHER ATTENDANCE — punch-in / punch-out via face recognition.
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

alter table teacher_attendance enable row level security;
create policy "teacher_attendance_select" on teacher_attendance for select
  using (teacher_id = auth.uid() or current_role_name() = 'admin');
create policy "teacher_attendance_write" on teacher_attendance for all
  using (teacher_id = auth.uid() or current_role_name() = 'admin');

-- ------------------------------------------------------------
-- 5. Enable Supabase Realtime on notifications so students see a
--    session-started alert the instant it's inserted, no polling.
-- ------------------------------------------------------------
alter publication supabase_realtime add table notifications;
