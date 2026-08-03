-- Migration 004: admins no longer need an Employee ID at signup — that
-- field only makes practical sense for teachers. Postgres allows multiple
-- NULLs under a UNIQUE constraint (NULLs are never considered equal to
-- each other), so this is safe to relax without touching existing rows.
alter table admins alter column employee_id drop not null;
