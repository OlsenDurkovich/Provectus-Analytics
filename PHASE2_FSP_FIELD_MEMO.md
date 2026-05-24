# Phase 2 — FSP Data Discovery Memo

> **Update 2026-05-20:** API path **deferred** (no FSP API subscription). Data path is now **Reporting Hub UI exports**. Also confirmed Provectus does **not** have Training Hub — so the course.name attribution shortcut described below in §4 does NOT apply to Provectus's data. See `ROADMAP.md` and `ALUMNI_DATA_COLLECTION_PLAN.md` for the current plan. The API field-map sections below remain valuable as a reference if API access is ever revisited.

**Status (original):** API confirmed available. Spec-level discovery complete. Live-call validation still required (no API key yet).
**Source:** developer.flightschedulepro.com swagger.json specs for the four published APIs (fetched 2026-05-20).
**Honesty flag:** Everything below is from the OpenAPI specs FSP publishes. Field names and example shapes are quoted from those specs. The Reporting API endpoints return loosely-typed dictionaries with no schema or example in the spec — those field lists will be confirmed only on first live call. Anything I'm guessing is marked **[GUESS]**.

---

## 1. Access mechanics

**API exists and is the right path.** Not export-only.

| Item | Value |
|---|---|
| Portal | https://developer.flightschedulepro.com/ |
| Base URLs | `https://usc-api.flightschedulepro.com/{api}/v1.0` (Core, Training, Reporting use `usc-api`; Scheduling spec lists `https://integration-fsp.flightschedulepro.com/scheduling/v1.0` — looks like a docs typo or staging host, **needs confirmation**) |
| Auth | `x-subscription-key: {api_key}` header (or `subscription-key` query param) |
| Methods | GET on all data endpoints. Docs assert "read-only", but the Core API does expose `POST /operators/{operatorId}/people` — minor inconsistency, doesn't affect us. |
| Throttle | 60 calls / 60 seconds. 429 on overage. |
| Pagination | `limit` + `offset` query params. Max 100/page on most endpoints, 250 on Reservations. |
| Filtering | `field=operator:value` syntax (e.g. `startTime=Gte:2020-01-01T00:00:00`, `tailNumber=Eq:N8877`). |
| Required to get keys | "Can Manage Company Settings" permission **and** an active API subscription. Keys generated at Settings → API Access. OperatorId is at Settings → General → Company → Company Profile ("FSP Company ID"). |

**Action required:** confirm Provectus has API subscription + generate key. See support-email draft.

---

## 2. The four APIs and what they cover

| API | Endpoint count | Useful for us |
|---|---|---|
| Core | 10 paths (11 ops — People has GET+POST) | Aircraft list/details/squawks/maintenance, Instructors, People, Users, Equipment |
| Scheduling | 1 | Reservations list (this is the discovery pivot) |
| Training | 10 | TrainingSession details, Lessons, Lesson tasks, Enrollment lesson statuses, User courses, Alerts |
| Reporting | 20 | Aircraft, Reservations, Flights, FlightSegments, **Invoices** (cost!), Credit/Debit memos, **StudentProgress**, TrainingSessions list, People, MaintenanceReminderStatus, WorkOrders/Items/Logs, AircraftLogbookEntries, Parts, Squawks, StockRecords, TimeEntries, UserDocuments |

---

## 3. Per-event fields available (from spec examples)

### 3a. Reservation (Scheduling API — list endpoint, paginated, filterable)

This is the workhorse. One call returns reservations within a date range with embedded training-session links and aircraft category. From the spec's example payload:

- `reservationId` (uuid), `operatorId`, `startTime`, `endTime`, `startTimeUtc`, `endTimeUtc`
- `reservationType.name` (e.g. `"Dual Flight Training"`), `reservationType.displayTypeId` (0=Standard, 1=Maintenance, 2=Class, 3=Meeting, 10=Instructor Time Off)
- `activityType.name`, `activityType.trackTrainingMismatch` (bool)
- `aircraft.aircraftId`, `tailNumber`, `make.name`, `model.name`, `isSimulator`, `isComplex`, `isHighPerformance`, `isTailWheel`, `engines[]`, `aircraftClass` (`"ASEL"`), `categoryClass.{id, category, class, isSimulator}` (e.g. `"ASEL" / "Airplane" / "Single Engine Land"`), simulator flags
- `pilots[]`: `userId`, `firstName`, `lastName`, `imageUrl`, `phone`, `locations[]`
- `instructor` (same user shape, may be null)
- `training.sessions[]`: `trainingSessionId`, `trainingSessionStatus.{id,name}`, `course.{courseId,name,enrollmentId}`, `lesson.{lessonId,name}`, `trainingSessionDate`
- `reservationStatus.{id,name}` (id 2 = `Completed` in the example)

Filterable on: `startTime`, `endTime`, `startTimeUtc`, `endTimeUtc`, `displayTypeId`, `userId`, `tailNumber`, `reservationTypeName`.

### 3b. TrainingSession detail (Training API — one-at-a-time fetch by ID)

The deep per-event record. Linked from `training.sessions[].trainingSessionId` on a reservation. From the spec example:

- `trainingSessionId`
- `course.{courseId, name, enrollmentId, enrollmentStatus.{id,name}, pinRequirement}`
- `lesson.{lessonId, name, completionStandardHtml, lessonObjectiveHtml, requiredStudyHtml, recommendedStudyHtml, noteForInstructorHtml, lessonGrades[], sessionGrades[], taskHeadings[], times[]}`
  - `times[]` is the structured time-category catalog for that lesson: `{timeId, name, valueType, simulatorTime, aircraftTime, instructorTime}`. Example timeIds in the spec: `DualDayLocal`, `DualDayXC`, `SoloDayLnd`, `InstrSim`, `NonInstrSim`, `PrePost`, `Ground`.
- `lessonGradeId`, `sessionGradeId`
- `students[]`: `{userId, firstName, lastName}`
- `trainingSessionDate`
- `instructor`: `{userId, firstName, lastName}`
- `aircraft`: `{aircraftId, make, model, tailNumber}`
- `reservationNumber`
- `airportCodes[]`
- `instructorComment` (free text)
- `trainingSessionStatus`
- `timeValues[]` — **the actual numeric values logged against each timeId for this session** (spec example shows empty array; live call needed to confirm shape, but the catalog above tells us what categories exist)
- `taskGrades[]`, `customLessonTasks[]`, `previousGrades[]`
- `trainingSessionContinueRepeat`

There's also `GET /trainingSessions/{id}/mismatchStatus` returning `mismatches[]` of `{mismatchTypeId, name, value, description}` for differences between reservation and logged session (e.g., flight time differing).

### 3c. Aircraft (Core API)

`{aircraftId, tailNumber, make.{makeId,name}, model.{modelId,name}, isSimulator, status.{id,name}}` plus `/squawks` and `/maintenanceReminders` sub-endpoints we don't need yet.

### 3d. Users / Instructors / People

- `Users: Fetch User` → `{userId, firstName, lastName, email, phoneNumber, currentBalance, lastFlightDate, externalId, status, createdDate, aircraftCheckouts[]}` — `currentBalance` is interesting for cost-side sanity.
- `Instructors: Fetch List` → user list with `instructorStatus`.
- `People: Fetch List / Fetch Person` → richer profile incl. birth date, gender, roles, peopleGroup ("Students"), labels, externalIds.
- `GET /users/{userId}/courses` → enrollments (list of `{courseId, name, enrollmentId, enrollmentStatus, pinRequirement}`) — **this is how you discover a student's rating enrollments**.

### 3e. Reporting API endpoints

20 paged report endpoints, all returning the generic shape `{totalItems, offset, limit, items[<dict>]}` — the spec defines no per-row schema or example. **Field names will only be known after a live call.** The endpoints exist for:

- aircraft, reservations, flights, flightsegments, **invoices**, **creditdebitmemos**, **studentprogress**, **trainingsessions**, people, maintenancereminderstatus, workorders, workitems, worklogs, aircraftlogbookentries, parts, partsutilization, squawks, stockrecords, timeentries, userdocuments

Filter params per endpoint (date-range + pagination) **are** documented; `flights` additionally filters on `CustomerEmail` and `InstructorId`.

The two endpoints we most need to validate first call on:
- `/reporting/.../invoices` → cost data (assumed; **[GUESS]** until we see actual fields)
- `/reporting/.../flights` → per-flight hours (Hobbs, Tach, etc. — **[GUESS]**)

---

## 4. Implications for Phase 2.5 (rating attribution)

The roadmap framed attribution as the hardest engineering problem because "every training flight is labeled dual flight training" and "PPL/IFR/ASEL COM all billed as primary." **The API exposure changes this materially.** New picture:

1. **`course.name` is on every training session.** The example specs show course names like `"Gleim Private Pilot"` and `"LENOX Private"`. If Provectus's FSP setup uses one course per rating per enrollment (likely — that's the standard FSP training model), **rating attribution is direct from `course.name` and does not need heuristic inference**. This needs to be confirmed against a live response — there's a real chance Provectus's historical data uses generic course names, in which case the heuristics in ROADMAP §2.5 still apply.

2. **`aircraft.categoryClass.class` = `"Single Engine Land"` / `"Multi Engine Land"` / etc.** SE vs ME is structured, not inferred. Solves ASEL-vs-AMEL split outright.

3. **`aircraft.isComplex`, `isHighPerformance`, `isTailWheel`, `isSimulator`** are explicit booleans.

4. **`lesson.times[]`** gives a per-lesson catalog of time categories with `simulatorTime` / `aircraftTime` / `instructorTime` flags. Solo vs dual is structured (`SoloDayLnd` vs `DualDayLocal` vs `DualDayXC`); hood/IFR time is structured (`InstrSim`/`NonInstrSim`); ground is separate from flight. The "all labeled dual flight training" problem is a *reservation-type label* problem, not a *time-recording* problem — the underlying time data is well-structured.

5. **`enrollmentId`** ties every session to a specific student-enrollment, which ties to a specific course, which (per #1) very likely is rating-scoped.

**Net:** if `course.name` does what it appears to do, Phase 2.5 may collapse from "build a heuristic ruleset + validation set" to "map each Provectus course name to a rating, attribute via enrollment." **The alumni survey may also shrink** — if historical enrollments are course-tagged, rating-boundary dates become derivable from `course.{startDate?}` + checkride session date rather than needing recall from former students.

Both of those collapses depend on real data inspection. **Do not lock this in until first live call confirms course naming.**

---

## 5. Gaps and unknowns

- **Cost / billing field shapes** — Invoice and credit/debit endpoint response fields are not in the spec. Live call needed.
- **Endorsements** — no endpoint visible. May not be exposed via API. Worth asking support.
- **Tach/Hobbs per flight** — not visible in Reservation or TrainingSession schemas; presumed to be in Reporting `/flights`. **[GUESS]** — needs live call.
- **Course → Rating mapping** — depends entirely on how Provectus has named courses in their FSP instance.
- **"List all training sessions" without a reservation** — Training API only has fetch-by-ID. Listing requires Reporting `/trainingsessions` (paged) **or** iterating reservations and pulling their session IDs.
- **Bulk export (CSV/XLSX)** — not investigated; API obviates the need.
- **Scheduling base URL discrepancy** — spec says `integration-fsp.flightschedulepro.com` instead of `usc-api`. Could be staging host or doc bug. Test both.
- **API subscription cost / availability** — unknown. Ask support.

---

## 6. Recommended next steps (Phase 2 → Phase 2.5 entry)

1. Generate API key (Settings → API Access) once subscription is confirmed.
2. First live calls to validate spec assumptions:
   - `GET /scheduling/v1.0/operators/{op}/reservations?startTime=Gte:2026-01-01T00:00:00&limit=5` — confirm reservation shape & embedded training sessions.
   - `GET /training/v1.0/operators/{op}/trainingSessions/{id}` — pull the `timeValues[]` and confirm time recording.
   - `GET /reporting/v1.0/operators/{op}/invoices?InvoiceDate=gte:2025-01-01&limit=5` — discover the invoice field shape.
   - `GET /reporting/v1.0/operators/{op}/flights?FlightDate=gte:2025-01-01&limit=5` — discover the flight field shape (Hobbs/Tach?).
3. Enumerate `GET /core/v1.0/operators/{op}/people` for one student we know completed multiple ratings; trace via `/users/{id}/courses` to see how many distinct courses exist and whether names imply rating.
4. **Decide Phase 2.5 scope based on the course-name finding.** If courses map cleanly to ratings, the heuristic ruleset shrinks dramatically.

---

## 7. References

- Portal: https://developer.flightschedulepro.com/
- Documentation: https://developer.flightschedulepro.com/templates/documentation.html
- API Reference: https://developer.flightschedulepro.com/templates/api-reference.html
- Spec files:
  - https://developer.flightschedulepro.com/core/swagger.json
  - https://developer.flightschedulepro.com/scheduling/swagger.json
  - https://developer.flightschedulepro.com/training/swagger.json
  - https://developer.flightschedulepro.com/reporting/swagger.json
- Status: https://status.flightschedulepro.com/
- Support: https://support.flightschedulepro.com/hc/en-us/requests/new
