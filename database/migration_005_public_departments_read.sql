-- Migration 005: departments must be readable by anyone, including
-- logged-out visitors — the registration form needs to populate its
-- department dropdown BEFORE the user has an account or session, but the
-- existing policy only allowed already-authenticated users to read it,
-- so RLS silently returned zero rows (no error, just an empty list).
drop policy if exists "departments_select" on departments;
create policy "departments_select" on departments for select using (true);
