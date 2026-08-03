-- Migration: allow admins (not just teachers) to generate QR sessions and
-- mark attendance, by pointing teacher_id at profiles(id) instead of the
-- narrower teachers(id). Run this once in the Supabase SQL editor.

alter table qr_sessions drop constraint qr_sessions_teacher_id_fkey;
alter table qr_sessions
  add constraint qr_sessions_teacher_id_fkey
  foreign key (teacher_id) references profiles (id) on delete cascade;

alter table attendance drop constraint attendance_teacher_id_fkey;
alter table attendance
  add constraint attendance_teacher_id_fkey
  foreign key (teacher_id) references profiles (id);
