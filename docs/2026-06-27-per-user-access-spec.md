# Per-user page access + user settings — implementation spec

**Builds on** the merged user/access feature (roles admin/instructor/viewer).
**Decisions (2026-06-27, Olsen):**
1. Page visibility is **per-user**, with roles as **presets** (the source of truth is each user's own allowed-page set; picking a role pre-fills it, then admin fine-tunes).
2. **Sensitive capabilities stay admin-only** — managing users, uploading FSP data, and editing flight overrides are NOT per-page toggles (prevents handing a viewer destructive power).

## Model

- **Toggleable pages:** `overview`, `ratings`, `students`, `instructors`, `flights`.
  - `transparency` is always public (no toggle). "Users / settings management" is an admin *capability*, not a page toggle.
- Each user gets a **`pages`** set (stored as a CSV/JSON column on `users`). Defaults from role at creation:
  - **admin** → all five pages
  - **instructor** → overview, ratings, students, instructors
  - **viewer** → overview, ratings, students, instructors
  - Admin can then tweak any user's checkboxes.
- **Capabilities** derive from role: `is_admin` (role == `admin`) → manage users + upload + flight overrides + Flights page. (Flights stays admin because it's the override surface.)

## Backend

- `auth/users.py`: add `pages TEXT` column; idempotent migration backfilling existing users from role; helpers `default_pages_for_role(role)`, `get_pages`, `set_pages`. `create_user` seeds pages from role.
- `GET /api/auth/me`: include `pages` and `is_admin` so the frontend can gate.
- `routers/users.py` (admin-only): `GET`/`POST` include `pages`; `PATCH /api/users/{id}` accepts `role`, `is_active`, and **`pages`**. Setting `role` re-applies that role's preset unless `pages` is also supplied.
- **Admin password reset:** `PATCH /api/users/{id}` accepts `new_password` (admin sets a temp one, min 8) — distinct from the existing self-service `/api/auth/change-password`.

### Enforcement — HARD (server-side), per Olsen ("most concrete end product")
Page access is a real security boundary, enforced at the API, not just hidden in the UI.

- A `require_page(*pages)` FastAPI dependency: allows the request iff the user is admin OR holds at least one of the listed pages. Applied per data router:
  - `meta` → no page gate (the app shell always needs it; any authenticated user).
  - `kpis` + `heatmap` → `require_page("overview")`
  - `ratings` → `require_page("overview", "ratings")`
  - `students` → `require_page("overview", "students")`
  - `instructors` → `require_page("instructors")`
  - `flights`, `upload`, `users` → admin-only (unchanged).
- Frontend gating (nav + route guards) mirrors this so the UI never shows a page the API would 403.

**Honest caveat (call out in the PR):** the dashboards overlap in the data they surface — e.g. the Overview page's client table shows per-student cost, so a user who can see Overview can see some student-level numbers even without the Student page. Page access controls *which pages/endpoints* a user can reach, not a per-field data wall. True per-field isolation would require redesigning what each page exposes (out of scope). `meta` stays open to all authenticated users by necessity.

## Frontend

- `AuthContext`: expose `pages` (from `/me`) + `canSee(page)` helper.
- `Sidebar` NAV: filter by the user's `pages` (admin still gets the Users link via capability).
- `App` routes: guard each dashboard route with `canSee`; redirect to the user's first allowed page otherwise.
- **Users admin screen → per-user settings:** expand each user (row detail / panel) with: role-preset dropdown (pre-fills the boxes), **page checkboxes**, active toggle, and a **reset-password** field. Save via `PATCH /api/users/{id}`.
- Self-service change-password already shipped (the "Password" button) — unchanged.

## Tests

- Backend: `default_pages_for_role`; PATCH `pages` persists + shows in `/me`; admin reset-password works and non-admin gets 403; role preset re-application; migration backfills existing rows.
- Frontend: nav shows only allowed pages; a viewer with a custom page set; route-guard redirect; admin settings panel edits role/pages/active/password.

## v1 scope

- **In:** per-user `pages`, role presets, admin reset-password, the per-user settings UI.
- **Deferred (not in v1):** display name, default landing page, force-change-password-on-first-login, hard backend per-page enforcement of read APIs, audit/last-login. (Easy add-ons later.)
