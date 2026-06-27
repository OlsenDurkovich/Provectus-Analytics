# User & Access Management — implementation spec

**Status:** decisions finalized 2026-06-27; ready to implement. NOT started — holding until the concurrent frontend (dead-buttons/color) session commits and the working tree is clean (sequential, per Olsen).
**Owner:** spinoff session for the P1 "User & access management" backlog item.
**Scope:** multiple logins, per-account credentials, roles/permissions, self-service password change.

---

## Current state (verified against code 2026-06-27)

- `src/provectus_analytics/auth/users.py`
  - `Role = Literal["admin", "boss"]` — to be replaced.
  - `users` table: `user_id, email (UNIQUE NOCASE), hashed_password, is_active, role (DEFAULT 'boss'), created_at`.
  - `create_user(role="boss")`, `seed_initial_admin(role="admin")`, `authenticate`, `get_user_by_id/email`, `count_users`, `ensure_users_table` (idempotent).
- `src/provectus_analytics/auth/deps.py` — `current_active_user`, `current_admin_user` (role=="admin" else 403). **Role scaffolding already exists.**
- `src/provectus_analytics/api/routers/auth.py` — `login`, `refresh`, `logout`, `me`. No user-CRUD, no password-change.
- `src/provectus_analytics/api/main.py` — all data routers gated by `current_active_user`; `upload` + `flights` (mutating) are in that set.
- `src/provectus_analytics/api/routers/upload.py` — docstring already says swap to `current_admin_user` for admin-only.
- Frontend: `frontend/src/auth/` (login + context), `frontend/src/components/` (`UploadDialog`, `OverrideMenu`, `Sidebar`, `Topbar`), `frontend/src/routes/`.

---

## Finalized decisions

1. **Three roles: `admin`, `instructor`, `viewer`.**
   - **admin** — full access: dashboards + Flights/overrides + FSP uploads + user management + change own password.
   - **instructor** — read-only dashboards. **Intended future scope: sees only their own students.** That scoping needs a link from the user account to an FSP instructor identity plus query-level filtering — *not built now*; instructor ships as a plain read-only role initially, flagged for later configuration. (Tracked as a follow-up.)
   - **viewer** — read-only dashboards only.
2. **Flights page (the override surface) is admin-only initially** — not shown to `instructor` or `viewer`. (Answers "viewers see Flights?" → not initially; applied to instructor too for now.)
3. **Self-service password change: build now** — any logged-in user can change their own password (verify current → set new).
4. **Retire `boss`.** `Role = Literal["admin", "instructor", "viewer"]`; `create_user` defaults to `"viewer"`. One-time migration in `ensure_users_table`: `UPDATE users SET role='admin' WHERE role='boss'` (only plausible boss = owner → admin). Seeded prod user is already `admin`, unaffected.
5. **Soft-delete (deactivate), not hard-delete.** Reversible; avoids permanent data deletion.
6. **Last-admin guard.** Refuse anything that would leave zero active admins (demote/deactivate/delete the final admin, including self).

---

## Backend changes

**`users.py`:** update `Role` literal + `create_user` default + `boss→admin` migration. Add `list_users(conn)`, `set_user_role`, `set_user_active`, `count_active_admins`, and `change_password(conn, user_id, current, new)` (verify current via `verify_password`, enforce ≥8 chars, re-hash).

**New `src/provectus_analytics/api/routers/users.py`** — all `Depends(current_admin_user)`:
- `GET /api/users` → list (`UserOut[]`, no hashes).
- `POST /api/users` → create `{email, password, role}`; 409 duplicate, 422 weak password.
- `PATCH /api/users/{user_id}` → set `role` and/or `is_active`; enforce last-admin guard + no self-lockout.

**Auth router (`routers/auth.py`):** add `POST /api/auth/change-password` `{current_password, new_password}`, `Depends(current_active_user)` — for the logged-in user only.

**`main.py` wiring:**
- Register `users_router` with `dependencies=[Depends(current_admin_user)]`.
- Move mutating/admin surfaces to admin-only: `upload_router` → `current_admin_user`; **`flights_router` → `current_admin_user`** (whole Flights surface is admin-only now).
- Read routers stay `current_active_user` so instructor/viewer can read: `meta, kpis, ratings, students, instructors`.

---

## Frontend changes

- Auth context (`frontend/src/auth/`): expose `role`, plus `isAdmin` and `canSeeFlights` (= isAdmin) helpers.
- **Admin → Users screen** (new route `frontend/src/routes/Users.tsx`): user table, add-user form (email/password/role: admin|instructor|viewer), deactivate toggle, role dropdown. Rendered only when `isAdmin`; API enforces regardless.
- **Change-password** UI (in Topbar/user menu) for all logged-in users.
- **Hide for non-admins:** `UploadDialog` trigger, `OverrideMenu`, and the **Flights** nav/route (Sidebar link gated on `isAdmin`).
- Add the Users nav link (admin-only) in `Sidebar.tsx`.

> NOTE: `Topbar.tsx` is also edited by the concurrent dead-buttons/color session. Rebase/merge onto their committed version before editing it here to avoid conflicts.

---

## Tests

- Backend: permission matrix per role — `viewer`/`instructor` get 403 on `POST /api/users`, `/api/upload/fsp`, flights endpoints; `admin` 200. Create-user happy/duplicate(409)/weak-password(422). Change-password happy + wrong-current(401/400). Last-admin guard. `boss→admin` migration on an existing DB.
- Frontend: admin sees Users link + upload/override + Flights; viewer/instructor see none of those; change-password visible to all. Users screen create/deactivate (mocked API).

---

## Follow-ups (out of scope now)

- **Instructor data scoping** — link user ↔ FSP instructor identity and filter `students`/`instructors` queries so an instructor sees only their own students. Add a config surface for the mapping. (This is the "configure down the road" piece.)

---

## Execution order (once tree is clean)

1. `git checkout -b feat/user-access-management` from clean `main`.
2. Backend: roles + migration → `users.py` helpers + `change_password` → `routers/users.py` → auth change-password route → `main.py` wiring + admin-gate upload/flights. Run backend tests.
3. Frontend: auth context roles → Users screen → change-password UI → gate upload/override/Flights → sidebar link. Run frontend tests + `tsc`/`vite build`.
4. Commit incrementally; leave branch for review → push → PR (manual push per project rule).
