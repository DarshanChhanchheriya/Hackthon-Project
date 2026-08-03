-- Migration: fix attendance duplicate-prevention. The unique constraint on
-- (student_id, date, subject) never worked when subject was NULL, because
-- Postgres treats every NULL as distinct in a unique constraint. Backfill
-- NULLs to '', dedupe existing duplicate rows, then make subject NOT NULL
-- so the constraint actually enforces "one row per student per day per
-- subject" going forward.

-- 1. Backfill existing NULL subjects to '' so they can be compared/deduped.
update attendance set subject = '' where subject is null;

-- 2. Remove duplicate rows, keeping the earliest-marked row per
--    (student_id, date, subject).
delete from attendance a
using (
  select id,
         row_number() over (
           partition by student_id, date, subject
           order by marked_at asc
         ) as rn
  from attendance
) dupes
where a.id = dupes.id and dupes.rn > 1;

-- 3. Make subject NOT NULL with a default so future inserts can never
--    reintroduce the bug.
alter table attendance alter column subject set default '';
alter table attendance alter column subject set not null;
