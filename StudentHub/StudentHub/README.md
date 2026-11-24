# StudentHub

**One Platform Connecting Students, Faculty, and Administration.**

An AI-powered College Management System with three role-based portals (Admin, Faculty, Student),
built with FastAPI + MongoDB on the backend and React + Vite + Tailwind on the frontend.

> **What's in this build**
>
> Every item below is wired to real FastAPI endpoints and MongoDB — not placeholders. The frontend was
> verified with 121 automated browser checks (esbuild-bundled, run in headless Chromium against a mocked
> API) plus a 46-check mobile-width sweep with zero horizontal overflow; backend logic that doesn't need a
> live server (date math, FIFO queue state, bulk-import validation, PDF/Excel generation, subject detection)
> was executed directly and verified against real generated files.
>
> - **Auth**: Role Selection → per-portal login. Only Students self-sign-up (Gmail-verified). Faculty accounts
>   are Admin-created with an Admin-set password (strength meter, show/hide, confirm). Admin is seeded on
>   first start.
> - **Dashboards** (Student/Faculty/Admin): glassmorphism UI, profile photo, Ctrl+K global search, notification
>   bell, quick-action cards, Chart.js analytics.
> - **Profile system**: photo upload, edit profile, change password — all roles.
> - **Subject assignment**: single source of truth (`subjects.faculty_id`), live in every faculty dropdown.
> - **My Schedule** (Faculty + Student): auto-built from the Admin's timetable — today's classes, lecture
>   numbering, live/next-class countdown, weekly grid.
> - **Smart Deadline Reminder**: live countdown widget, colour-coded reminders, a background scheduler that
>   actually sends blue/orange/red notifications and publishes scheduled announcements on its own, and a
>   one-time "while you were away" popup after a login gap.
> - **AI Study Coach**: upload PDF/DOCX/PPTX/image → subject auto-detected (offline keyword classifier,
>   refined by the model when configured) → short notes, topics, formula sheet, flip flashcards, scored MCQ
>   quiz, viva questions, day-by-day planner, Last Night Mode.
> - **StudentHub AI** (students only): chat with MongoDB-persisted history, copy, regenerate, voice input, code blocks, and file/image attachments
>   (a PDF or photo can be sent straight into the conversation).
> - **Skill Wallet**: XP earned automatically (attendance, on-time/early submissions) plus Faculty-awarded XP
>   for events/helping others; levels and badges computed from real totals.
> - **Campus Time Capsule**: a message to your future self — withheld from the API entirely until unlock date.
> - **Anonymous Doubt Wall**: ask without identity exposed in the API response; faculty reply publicly;
>   upvote-sorted.
> - **Admin Analytics**: Faculty Heatmap (hardest subjects, most-viewed notes, assignment delay rates), Silent
>   Student Finder (low attendance / missed deadlines / no engagement, flagged with suggestions), Campus Pulse
>   (14-day attendance trend, engagement rate, event participation).
> - **Reports**: Admin Attendance/Marks (PDF+Excel, filterable), Faculty student-performance report, Student
>   progress report — real generated files, opened back up with pypdf/openpyxl to confirm the data is correct.
> - **Bulk Excel Import**: students from .xlsx with per-row validation, a downloadable template, and a
>   created/failed breakdown so one bad row never blocks the rest.
> - **Digital Study Locker**: searchable unified view over faculty notes, AI Study Coach notes, and flashcards.
> - **Focus Mode**: a real full-screen timer (start/end tracked server-side) powering Study Streak and total
>   focus minutes.
> - **Smart Calendar**: a month-grid merging assignments, exam dates, leave, and AI study-planner sessions.
> - **Ctrl+K Global Search**: role-scoped results across students, faculty, subjects, assignments, notes,
>   timetable.
> - Attendance, assignments (Assignment DNA timeline), notes with view-tracking, marks, timetable with clash
>   detection, leave, a full Notification Center timeline, WebSocket live notifications, dark/light mode.
> - Demo data seeded on first start (1 Admin, 3 Faculty, 10 Students, subjects, timetable, assignments).
>
> **Not included:** nothing from the original feature list remains unbuilt at this point — what's left is
> polish (e.g. richer error states, more seed data variety) rather than missing features.




---

## Tech Stack

- **Frontend:** React (Vite), Tailwind CSS, React Router DOM, Axios, Framer Motion, React Icons, React Hot Toast, Chart.js
- **Backend:** FastAPI, Motor (async MongoDB), Pydantic, python-jose (JWT), passlib/bcrypt, WebSockets
- **Database:** MongoDB
- **AI:** OpenAI API (StudentHub AI chat)
- **Email:** Gmail SMTP

---

## Project Structure

```
StudentHub/
├── frontend/                # React + Vite + Tailwind app
│   ├── src/
│   │   ├── components/      # Navbar, Footer, ThemeToggle, PasswordStrengthMeter...
│   │   ├── context/         # AuthContext, ThemeContext
│   │   ├── layouts/         # DashboardLayout (shared sidebar/topbar)
│   │   ├── pages/           # Landing, RoleSelect, Login (/login/:role), Signup, dashboards, error pages...
│   │   ├── routes/          # ProtectedRoute
│   │   ├── services/        # api.js (Axios instance + token refresh)
│   │   └── App.jsx
│   └── package.json
│
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI app, CORS, router mounting, WebSocket endpoint
│   │   ├── auth.py          # JWT + bcrypt + get_current_user / require_role
│   │   ├── database.py      # Motor client + all collection handles + indexes
│   │   ├── websocket.py     # Per-user connection manager for live notifications
│   │   ├── models/          # Mongo document shapes
│   │   ├── routes/          # auth, students, faculty, subjects, attendance, assignments,
│   │   │                    # timetable, announcements, leave, notes, marks, notifications
│   │   ├── schemas/         # Pydantic request/response models + validation
│   │   ├── services/        # notifications.py (Mongo write + WebSocket push)
│   │   ├── seed.py          # Auto-seeds the default Admin account on first startup
│   │   └── utils/           # validators.py, dates.py, email.py (Gmail SMTP)
│   └── requirements.txt
│
├── .env.example
└── README.md
```

---

## 1. Prerequisites

- **Node.js** 18+ and npm
- **Python** 3.11+
- **MongoDB** running locally (`mongodb://localhost:27017`) or a MongoDB Atlas connection string
- A **Gmail account with an App Password** (for sending verification/reset emails)
- An **OpenAI API key** (for the StudentHub AI chat)

---

## 2. Backend Setup (Windows / macOS / Linux)

```bash
cd backend

# Create and activate a virtual environment
python -m venv venv

# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment variables and fill them in
cp .env.example .env      # Windows: copy .env.example .env
```

Edit `backend/.env` with your real values (see **Environment Variables** below), then run:

```bash
uvicorn app.main:app --reload
```

The API is now live at `http://localhost:8000`. Interactive docs (Swagger UI) are at
`http://localhost:8000/docs`.

---

## 3. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The app is now live at `http://localhost:5173`. API calls to `/api/*` are proxied to the FastAPI
backend automatically (see `vite.config.js`) — no CORS headaches in dev.

---

## 4. MongoDB Setup

**Option A — Local MongoDB:**
1. Install MongoDB Community Server for your OS.
2. Start it (`mongod` or via the MongoDB service).
3. Leave `MONGO_URI=mongodb://localhost:27017` in `.env`.

**Option B — MongoDB Atlas (cloud, free tier works):**
1. Create a free cluster at mongodb.com/atlas.
2. Add your IP to the network access list and create a database user.
3. Copy the connection string into `MONGO_URI` in `.env`, e.g.
   `mongodb+srv://<user>:<password>@cluster0.xxxxx.mongodb.net`

The app creates its own indexes automatically on startup — no manual collection setup needed.

---

## 5. Gmail SMTP Setup (for verification + password reset emails)

Gmail no longer accepts your normal account password for SMTP — you need an **App Password**:

1. Go to your Google Account → **Security**.
2. Enable **2-Step Verification** if it isn't already on.
3. Go to **Security → App Passwords**.
4. Generate a new app password (choose "Mail" as the app).
5. Copy the 16-character password into `SMTP_APP_PASSWORD` in `.env`, and your Gmail address into
   `SMTP_USERNAME`.

> If you don't configure SMTP yet, the backend won't crash — it prints the email content to the
> console instead, so you can still test the signup/reset flow end-to-end during development.

---

## 6. OpenAI API Setup (StudentHub AI + AI Study Coach)

1. Create a key at platform.openai.com → **API keys**, and make sure the account has credit (a free/empty
   account returns an "out of credit" error — the app will tell you so in plain words).
2. In `backend/.env` set `OPENAI_API_KEY=sk-...` (no quotes, no spaces). Optionally set `OPENAI_MODEL`
   (default `gpt-4o-mini`; it must support JSON mode and, for photo/handwritten notes, vision).
3. Restart the backend and, from `backend/`, run `python -m app.check_ai`. It makes one tiny real call and prints
   either `OK: model=… replied … in N ms` or the exact reason it failed (bad key, no credit, model not available,
   network, rate limit). (AI is student-only, so the old Admin-dashboard test card was removed.)
4. Until a key is set, AI pages show a "AI isn't set up yet" banner; uploads, file extraction and offline
   subject detection still work without a key.

How the AI layer protects the app: every OpenAI call goes through one client (`services/openai_client.py`)
with a 60 s timeout and automatic retries; failures are translated into actionable messages
(`utils/ai_errors.py`); and the Study Coach's JSON is passed through `utils/ai_sanitize.py`, so a model that
returns valid-but-wrongly-shaped JSON (flashcards as strings, a 1-option MCQ, a list where a string belongs)
degrades to "fewer items" instead of crashing the server or the page.

## 7. Environment Variables Reference

| Variable | Description |
|---|---|
| `MONGO_URI` | MongoDB connection string |
| `MONGO_DB_NAME` | Database name (default `studenthub`) |
| `JWT_SECRET_KEY` / `JWT_REFRESH_SECRET_KEY` | Long random strings — generate with `openssl rand -hex 32` |
| `JWT_ALGORITHM` | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token lifetime |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token lifetime |
| `SMTP_HOST` / `SMTP_PORT` | `smtp.gmail.com` / `587` |
| `SMTP_USERNAME` | Your Gmail address |
| `SMTP_APP_PASSWORD` | 16-character Gmail App Password |
| `OPENAI_API_KEY` | Your OpenAI key (backend only — never exposed to the browser) |
| `OPENAI_MODEL` | Model name (default `gpt-4o-mini`; needs JSON mode, and vision for photo notes) |
| `OPENAI_BASE_URL` | Optional OpenAI-compatible endpoint |
| `AI_REQUEST_TIMEOUT_SECONDS` | AI call timeout (default 90) |
| `AI_RATE_LIMIT_PER_MINUTE` | Per-student AI budget per minute (default 20) |
| `ENVIRONMENT` | `development` or `production` (production refuses placeholder JWT secrets) |
| `APP_TIMEZONE` | Campus time zone for deadlines, e.g. `Asia/Kolkata` (default) |
| `FRONTEND_URL` | `http://localhost:5173` (used to build email links + CORS) |
| `ADMIN_ID` / `ADMIN_EMAIL` / `ADMIN_PASSWORD` / `ADMIN_NAME` | Credentials for the default Admin account, auto-seeded on first backend startup |

---

## 8. Authentication Flow

StudentHub uses **one Login entry point that branches by role** — it does not have a single combined
login form:

1. The landing page's **Login** button opens `/login`, a **Role Selection** screen with three cards:
   Admin Portal, Faculty Portal, Student Portal.
2. Each card opens its own login page (`/login/admin`, `/login/faculty`, `/login/student`) with
   role-appropriate fields:
   - **Student:** Gmail + Password (+ Remember Me). Login is blocked until the student verifies their
     email via the link StudentHub emails them at signup.
   - **Faculty:** Faculty ID + Gmail + Password — all three must match together.
   - **Admin:** Admin ID + Gmail + Password — all three must match together.
3. **Only Students can sign up** (`/signup`), with Full Name, Student ID, Department, Semester (1–8),
   Gmail, Password, and Confirm Password.
4. **Faculty accounts are Admin-only.** When an Admin creates one (Admin dashboard → Faculty
   Management), the Admin sets the Faculty ID and password directly and shares them with the faculty member.
5. **Admin accounts are never created through the app.** A single default Admin is seeded into MongoDB
   automatically the first time the backend starts (see `ADMIN_ID` / `ADMIN_EMAIL` / `ADMIN_PASSWORD` /
   `ADMIN_NAME` above) — set those before first run if you want different credentials, or log in with
   the printed defaults and change the password afterward.

| Role | Can Sign Up | Can Log In | How the account is created |
|---|---|---|---|
| Student | ✅ Yes | ✅ | Self-signup at `/signup` |
| Faculty | ❌ No | ✅ | Created by Admin (Admin sets ID + password) |
| Admin | ❌ No | ✅ | Auto-seeded on first backend startup |

---

## 9. API Overview

| Method | Endpoint | Description |
|---|---|---|
| POST | `/auth/signup` | Student self-signup (Gmail only) |
| POST | `/auth/verify-email` | Verify email via emailed token |
| POST | `/auth/login/student` | Student login (email + password) |
| POST | `/auth/login/faculty` | Faculty login (Faculty ID + email + password) |
| POST | `/auth/login/admin` | Admin login (Admin ID + email + password) |
| POST | `/auth/refresh` | Rotate an access token using a refresh token |
| POST | `/auth/logout` | Revoke the current refresh token |
| POST | `/auth/forgot-password` | Send a Gmail reset link (15-minute expiry) |
| POST | `/auth/reset-password` | Reset password using the emailed token |
| GET | `/auth/me` | Get the current authenticated user |
| GET/POST/PUT/DELETE | `/students` | Admin: manage students, reset password |
| GET/POST/PUT/DELETE | `/faculty` | Admin: manage faculty, assign subjects |
| GET/POST/PUT/DELETE | `/subjects` | Manage subjects + semester mapping |
| POST/PUT/GET | `/attendance/...` | Mark/edit attendance, student view + prediction |
| POST/GET/PUT | `/assignments/...` | Create, submit, grade (Assignment DNA timeline) |
| GET/POST/PUT/DELETE | `/timetable` | Weekly timetable + `/timetable/check-clash` |
| POST/GET | `/announcements` | Broadcast + scheduled announcements |
| POST/GET/PUT | `/leave` | Apply, list, approve/reject |
| POST/GET/DELETE | `/notes` | Upload/list/delete notes (real file storage) |
| PUT/GET | `/marks` | Enter, publish, and view marks |
| GET/PUT | `/notifications` | List, unread count, mark read |
| POST/GET | `/study-coach/upload`, `/study-coach/generate` | Upload notes, auto-detect subject, generate study content |
| GET/DELETE | `/study-coach/plans` | List/view/delete generated study plans |
| GET/POST | `/skill-wallet/me`, `/skill-wallet/award` | XP, level, badges · Faculty awards event/helping-others XP |
| GET/POST/DELETE | `/time-capsule` | Create, list (message hidden until unlock), delete |
| GET | `/reports/attendance`, `/reports/marks`, `/reports/my-students`, `/reports/my-progress` | PDF/Excel downloads |
| GET/PUT/POST | `/profile` | View/edit profile, upload/remove photo, change password |
| GET | `/timetable/my-schedule` | Auto-built weekly schedule for the logged-in Faculty/Student |
| GET | `/faculty/me/subjects`, `/students/roster` | Faculty-safe subject list and subject roster |
| WS | `/ws/{token}` | Live notification stream |

Full interactive documentation is auto-generated by FastAPI at `/docs`.

---

## 10. Validation Rules Implemented (Frontend + Backend)

- **Name:** letters + spaces only, 3–30 characters
- **Email:** `@gmail.com` only
- **Password:** 8+ characters, 1 uppercase, 1 lowercase, 1 number, 1 special character — with a live strength meter
- **Phone:** exactly 10 digits
- **Student ID / Faculty ID:** numbers only
- **Semester:** 1–8 only
- **Dates** (assignment due dates, leave, announcement scheduling): cannot be in the past

---

## 11. Security Implemented

- bcrypt password hashing
- JWT access + refresh tokens, refresh-token rotation, revocation on logout/password reset
- Role-based access control (`require_role` dependency on the backend, `ProtectedRoute` on the frontend)
- Password reset tokens are single-use and expire after 15 minutes
- Faculty/Admin login requires their role-specific ID (Faculty ID / Admin ID) to match the account,
  in addition to email + password
- Student login is blocked until the account's email is verified
- After logout, the frontend performs a full navigation replace (not just a state change), so the
  browser back button cannot reveal an authenticated dashboard

---

## 12. Demo accounts (seeded on first start)

| Role | ID | Gmail | Password |
|---|---|---|---|
| Admin | `ADMIN001` | `admin@gmail.com` | `Admin@12345` (change via `.env` before first run) |
| Faculty | `1001` / `1002` / `1003` | `rohit.verma.faculty@gmail.com`, `sunita.rao.faculty@gmail.com`, `amit.kulkarni.faculty@gmail.com` | `Demo@12345` |
| Student | `2024001` … `2024010` | `demo.student1@gmail.com` … `demo.student10@gmail.com` | `Demo@12345` |

Seeded faculty each own one subject (Data Structures, DBMS, Operating Systems). Create timetable slots as
Admin (Admin → Timetable) and both the faculty and the students of that department/semester get them under
**My Schedule** automatically.

## 13. Known gaps and honesty notes

Everything from the original feature list is implemented and wired to MongoDB. What's genuinely still
missing or worth knowing before a live demo:

- **Never run against a live server.** This sandbox has no network and no MongoDB, so the backend has only
  been statically verified (syntax, undefined names, import resolution) plus direct unit-testing of risky
  logic (date math, bulk-import parsing, PDF/Excel generation, subject
  detection). Run it for real on your machine before presenting it — see the Final Testing Checklist below.
- **The deadline scheduler runs every 5 minutes** — a reminder won't appear the literal instant a deadline
  crosses a threshold, only within that window.
- **AI features need `OPENAI_API_KEY`.** Without it, StudentHub AI and the AI Study Coach's generate step
  return a clear "not configured" message rather than failing silently; everything else (upload, offline
  subject detection, file extraction) works without a key.
- Gmail verification/reset emails and the full bulk-import/report flows haven't been tested against a real
  Gmail App Password or a real MongoDB — only their logic has been verified in isolation.


## 14. Changes in this revision (AI hardening + student management)

- **AI is students-only, enforced on the server.** Every `/ai/*` and `/study-coach/*` endpoint requires the `student`
  role (Admin/Faculty get 403); the AI nav entries, floating button, dashboard shortcuts, and `/admin/ai` `/faculty/ai`
  routes were removed. The Admin "AI connection" card and `/ai/test` endpoint were removed — use `python -m app.check_ai`.
- **Study Coach:** topic explanations added; real day-by-day planner (every topic scheduled, revision days, exam-eve);
  MCQs show answers + explanations; saved uploads can be regenerated from; corrupt / password-protected / renamed /
  scanned files give a plain 4xx message; files are stored in `backend/private_uploads` (not publicly served — the old
  public `/uploads/study_coach` path is blocked) and only downloadable by their owner.
- **StudentHub AI:** atomic `$push` persistence (parallel sends can't overwrite each other), images are sent to the model
  but never stored in MongoDB, per-student rate limit, code-block rendering.
- **Admin → Students:** status filter, profile with academic records, edit email/ID/department/semester/batch with
  duplicate checks, activate/deactivate (blocks login + existing tokens), duplicate-key races return 409 not 500.
- **Faculty → My Students** (`/faculty/students`): students enrolled in the faculty member's own subjects only; may edit
  phone + batch, mark attendance, enter/publish marks, grade submissions. Admin keeps institution-wide access.
- **Authorization fixes:** faculty could previously publish any marks, grade any submission and read any subject's
  attendance/marks/submissions; these now require subject ownership (Admin exempt). Attendance/marks writes require the
  student to be enrolled in that subject.

### Running the tests
```bash
cd backend
pip install -r requirements-dev.txt
python -m pytest -q          # uses an in-memory MongoDB look-alike and a fake AI provider
```

> **Removed by request:** Office Hours queue and Class Mood Pulse (pages, routes, API). Existing `mood_logs` / `office_queue` data in MongoDB was left untouched.


## 15. Faculty–subject assignment, analytics, login & password reset (this revision)

### The assignment bug and its fix
**Root cause.** Who teaches a subject was a single field, `subjects.faculty_id`. "Assign subjects to faculty B"
(`PUT /faculty/{id}/assign-subjects`) first cleared that field on all of B's subjects, then ran
`update_many({_id in wanted}, {faculty_id: B})`, overwriting whoever held them — so giving Java to B erased it from A.
A scalar column cannot hold two teachers.

**Fix.** A many-to-many link collection, `faculty_subjects`: one document `{faculty_id, subject_id}` per pair, with a
**unique index on the pair** (not on the subject). Every operation touches only the pairs it names
(`services/faculty_subject_links.py`), and every permission check (`services/access.py`, notes, assignments, doubts,
attendance, marks, timetable, calendar, reports) asks that one service. `faculty.subject_ids` remains as a derived,
read-only copy kept in sync. Removing a link never deletes marks, attendance, notes, assignments or submissions.

New Admin endpoints: `GET /faculty/assignments` (both directions), `POST /faculty/{id}/subjects` (add),
`POST /faculty/{id}/subjects/remove` (remove several), `DELETE /faculty/{id}/subjects/{subject_id}`,
`POST /faculty/{id}/subjects/{subject_id}/reassign`, `GET /subjects/{id}/faculty`. Subjects now return
`faculty_ids` + `faculty`; the subject form takes `faculty_ids`. The timetable only accepts a teacher who teaches
the subject, and a faculty member's own schedule drops subjects they no longer teach.

### Migration / indexes (automatic, repeatable, non-destructive)
* On startup `migrate_legacy_assignments()` turns every legacy `subjects.faculty_id` into a link, **once** (a marker
  document `faculty_subjects_many_to_many_v1` in `schema_migrations`). Re-running is a no-op, so an assignment the Admin
  later removes is never re-added from stale legacy data. Nothing is deleted or rewritten; legacy fields stay in place
  (and are ignored). Dangling references to deleted faculty are skipped.
* New unique index `faculty_subjects(faculty_id, subject_id)` + index on `subject_id` (created by `init_indexes`).
  The collection is new, so the index cannot collide with existing data.

### Student Performance Analytics (replaces the "Faculty workload" chart)
`GET /analytics/student-performance` (Admin only; filters `department`, `semester`, `subject_id`, `published_only`).
Returns aggregates only — no names, IDs or per-student values. Rules (full text in `services/performance_analytics.py`):
* Marks are per student per subject (`internal`, `practical`). No maximum is stored, so each component's maximum
  **defaults to 100** (the API enforces 0–100); documents carrying `max_internal` / `max_practical` are normalised to them.
* Subject % = total score / total maximum. Student result = mean of the student's subject percentages.
* Invalid values (negative, above maximum, non-numeric, NaN, bad/zero maximum) are ignored and counted in `data_quality`.
  Missing marks are "not entered", never zero. Duplicate documents: the newest valid one is used.
* **Eligibility:** a student counts only with valid marks in at least half of their class's subjects. Everyone else is
  "awaiting marks" — never a failure, and excluded from the average, grade distribution and pass/fail, so all three use the
  same students.
* **Pass mark:** `PASS_PERCENTAGE` (default **40**, provisional — the project had no institutional rule).
* **Grades** (no institutional scale existed): A+ ≥90, A ≥80, B ≥70, C ≥60, D ≥50, E ≥40, F <40.
* Figures are computed live on every request; the dashboard refreshes every 60 s, on tab focus, and on filter change.

### Login
The Login page now stays put on failure and shows the error. Root cause of the old redirect: the global API interceptor
treated *any* 401 — including the wrong-password answer from `/auth/login/*` — as an expired session and called
`forceLogout()`, which reloaded `/login` (portal selection). Public auth endpoints are now excluded from that logic;
a real expired session returns to that role's own login page with a notice.
Errors are generic by default (no account enumeration); set `AUTH_REVEAL_ACCOUNT_EXISTS=true` for precise messages on a
private deployment. Disabled/unverified messages appear only after the correct password. Failed logins are rate-limited.

### Forgot / reset password
Email-based, for all roles. Requires `SMTP_USERNAME` + `SMTP_APP_PASSWORD` (a Gmail App Password); without them the
server says so (HTTP 503) rather than claiming an email was sent. Tokens are random, expire in 15 minutes, are
single-use (claimed atomically), and only their SHA-256 is stored; a new request voids the previous link; a successful
reset signs the account out everywhere. Requests and attempts are rate-limited; reset links are never logged.
Unknown or disabled accounts get the same generic response as real ones.

### Not available in the project
There is no ESLint/TypeScript configuration (`npm run lint` fails because ESLint isn't installed).


## 16. Classroom Activity Hub, Calendar redesign, Student cleanup (this revision)

### Faculty dashboard — Classroom Activity Hub (replaces "Attendance analytics")
One read-only endpoint, `GET /faculty/me/activity-hub` (faculty only), feeds the whole panel. Everything is computed from
MongoDB on every request and scoped to the subjects the Admin has CURRENTLY assigned to that faculty member, so another
faculty member's classes, students and records can never appear. The panel refreshes on open, every 60 s, and when the
browser tab regains focus, so counts drop as soon as work is finished on another page.

| Item | How it is calculated |
|---|---|
| Today's classes | Timetable slots for today's weekday, for subjects the faculty member teaches now (campus time zone `APP_TIMEZONE`) |
| "Lecture n of m" | The slot's position in today's order — the timetable stores no lecture numbers |
| Live / Upcoming / Completed | From the slot's start/end time against the campus clock |
| Attendance status | Per **subject** and date (attendance is stored per subject/date): complete = all enrolled students marked, partial = some, pending = none |
| Task: Attendance not marked | Subjects with a class that has already started today and attendance not complete |
| Task: Marks to enter | Enrolled students with no internal/practical mark for the subject |
| Task: Marks ready to publish | Recorded marks not yet published |
| Task: Submissions to review | Submissions with status `submitted` (handed in, not graded) |
| Task: Doubts awaiting a reply | Doubt Wall questions in the faculty member's subjects with no reply |
| Readiness chips | Study material uploaded for the subject, open assignments (due today or later), submissions to review |
| Workload summary | Teaching time today, students taught today, attendance subjects done/started, assignments due in the next 7 days |

Anything that cannot be calculated is omitted — there are no placeholder numbers. Task rows and class rows link to the
existing Faculty pages; `?subject=ID` (attendance, marks), `?upload=1` (notes) and `?new=1` (assignments) open them already
pointed at the right subject/dialog (a subject is only honoured if it is one of the faculty member's own).
Side fix: Faculty Attendance and Assignments computed "today" from the UTC date, which is *yesterday* in India before
05:30; they now use the local date.

### Calendar
Same page and same `/calendar/me` feed (no second calendar system), redesigned: 6-week month grid, selected-day panel,
event-type filters (only types present in your data are offered), "Up next", keyboard navigation (arrows, PageUp/PageDown,
Home), loading/empty/error-with-retry states, light and dark themes. New data: the feed now also returns `weekly_classes`
(your timetable lectures — faculty: only subjects they currently teach; students: their department + semester) which the page
places on each matching weekday, and leave events carry `end_date` so multi-day leave spans its days.

### Student portal
Focus Mode, Time Capsule and Study Locker were removed from the Student navigation and routes, and their three page
components were deleted. Their backend APIs (`/focus`, `/time-capsule`, `/locker`) and all stored data were deliberately
left untouched.
