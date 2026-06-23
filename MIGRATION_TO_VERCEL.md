# Migration Handoff — Sailing Jobs Manager → Vercel

**Purpose:** Port the entire "NZL 49er Programme — Jobs Manager" app from **Streamlit Community Cloud** into an existing **Vercel** app, preserving all functionality: job management, the dashboard, due-date escalation, email notifications, and Google Calendar sync. This document is written so a developer (or an AI coding agent) with access to the **GitHub repo**, the **Streamlit Cloud** settings, and the **Supabase** project can execute the migration end-to-end.

---

## 0. TL;DR — the key insight that makes this "seamless"

**All persistent data lives in Supabase, not in Streamlit.** The Streamlit app is just a UI over a single Supabase row. Therefore:

- The Vercel app can point at the **same Supabase project and table** and instantly have all existing data — **no data export/import step required**.
- The migration is really a **UI + integrations re-implementation**, not a data migration.
- You can run both apps side-by-side during cutover (they read/write the same row), then retire the Streamlit one.

The work breaks into three buckets:
1. **UI** — rebuild the Streamlit screens as your Vercel framework's components (Streamlit Python cannot run on Vercel).
2. **Business logic** — port ~8 pure functions (priority escalation, overdue, auto-archive, reminder window, calendar reconciliation). These are simple and port cleanly.
3. **Integrations** — Supabase (reuse), Gmail SMTP email, Google Calendar service account, plus two scheduled jobs (reminders, keep-alive) that must move from "runs on page load" to **Vercel Cron**.

---

## 1. Current system overview

| Concern | Current implementation |
|---|---|
| UI / hosting | Streamlit (`app.py`), Streamlit Community Cloud |
| Repo | `github.com/oscargunn/Sailing_to_do_list` (single file `app.py`) |
| Data store | Supabase Postgres, project `tbqefnlqkqdjznvyhmtc`, table `app_state`, **one row id=1**, column `data` (JSONB) holding the entire app state |
| Local fallback | `jobs_data.json` written on every save (ephemeral on Cloud; **drop this on Vercel** — serverless filesystem is read-only/ephemeral) |
| Email | Gmail via `smtplib.SMTP_SSL("smtp.gmail.com", 465)` |
| Calendar | Google Calendar API v3 via a **service account** (`google-api-python-client`) |
| Keep-alive | GitHub Action (`.github/workflows/keep-alive.yml`) pings Supabase every 3 days so the free tier doesn't auto-pause |

> ⚠️ **Streamlit does not run on Vercel.** Vercel hosts JS/TS (Next.js etc.) and serverless functions (incl. Python functions). The UI must be rebuilt. The recommended target is **Next.js (App Router) + `@supabase/supabase-js`**, with API routes for email/calendar and **Vercel Cron** for the scheduled jobs. If your existing Vercel app is Next.js, port into it directly.

---

## 2. Data model (the contract — reproduce exactly)

The Supabase table:

```
table: app_state
  id   int  primary key         -- always 1
  data jsonb                      -- the entire app state
```

`data` shape:

```jsonc
{
  "jobs":          [ Job, ... ],
  "tabs":          ["Europe", "NZ General", "LA Boat", "R1047", "Rigs", "New Boat"],
  "archived_tabs": ["..."],
  "contacts":      [ Contact, ... ],
  "last_synced":   1718800000000   // ms epoch of the last successful save
}
```

**Job:**

```jsonc
{
  "id":            "abc123xyz",     // 10-char [a-z0-9], or "s{n}" for seed rows
  "title":         "New jib cleat drawings",
  "location":      "NZ General",     // must equal one of `tabs`
  "status":        "Pending",        // Pending | In Progress | Completed | Archived
  "priority":      "Medium",         // Low | Medium | High | Urgent  (BASE priority)
  "notes":         "",
  "description":   "",
  "assignedName":  "David/Oscar",    // free text; multiple split on "/" or ","
  "assignedEmail": "a@x.com, b@y.com",// comma-separated
  "dueDate":       "2026-05-29",     // ISO date string, or ""
  "createdAt":     1718000000000,    // ms epoch
  "completedAt":   null,             // ms epoch when marked Completed, else null
  "comments":      [ Comment, ... ],
  "subtasks":      [ Subtask, ... ],
  "reminder_sent_48h": false,        // true once the 48h reminder email has gone out
  "gcal_event_id": null              // Google Calendar event id, or null
}
```

**Comment:** `{ "id": str, "text": str, "author": str, "ts": ms_epoch }`
**Subtask:** `{ "id": str, "text": str, "done": bool }`
**Contact:** `{ "id": str, "name": str, "email": str }`

Seed contacts (used if `contacts` is empty): Oscar `0oscargunn0@gmail.com`, Mattias `mattias.coutts1@gmail.com`, David `dgg1000@gmail.com`.

> **Read/write pattern:** read the whole `data` blob on load; on any change, write the whole blob back via `upsert({id:1, data})`. Set `last_synced` to `Date.now()` on every write.

### Optional later: normalize to relational tables
The single-blob design is simple and fine for this team's scale, but it has **last-write-wins** behaviour (two simultaneous savers overwrite each other's whole blob). If you want concurrency safety in the new app, migrate to a `jobs` table (one row per job) + `contacts` table. **Do this as a phase 2** — for a seamless first cutover, reuse the blob so no data moves. A one-time script can later fan the blob out into rows.

---

## 3. Business logic to port (pure functions — language-agnostic specs)

These have **no I/O**; reimplement them verbatim in TS.

**Priority levels:** `["Low","Medium","High","Urgent"]`, rank = index 0..3.

**`effectivePriority(job)`** — escalates base priority toward Urgent as the due date nears:
```
rank = index of job.priority (default Medium=1)
if job.dueDate:
    d = daysBetween(today, dueDate)        // negative = overdue
    if d < 0:        rank = 3              // overdue → Urgent
    elif d == 0:     rank = min(rank+2, 3) // due today
    elif d <= 2:     rank = min(rank+2, 3) // due in 1–2 days
    elif d <= 5:     rank = min(rank+1, 3) // due in 3–5 days
return levels[rank]
```

**`isOverdue(job)`** → `true` if `dueDate` is in the past **and** status is not Completed/Archived.

**`jobAssignees(job)`** → split `assignedName` on `/` and `,`, trim, drop empties → string[].

**`autoArchive()`** — for each job: if `status == "Completed"` and `completedAt` and `now - completedAt >= 48h` → set `status = "Archived"` (and remove its calendar event — see §5). On Vercel run this in the daily cron (and/or compute "should be archived" on read).

**Sort order (kanban & lists):** by `effectivePriority` desc (Urgent first), then `dueDate` asc (empty last), then `createdAt` asc.

**Dashboard "Needs Attention":** active jobs where `status != "Completed"` AND (`isOverdue` OR `effectivePriority == "Urgent"`). Completed jobs are excluded from Needs Attention and all Urgent counts.

---

## 4. Email notifications (Gmail SMTP)

**Current secret** (`[email]`): `sender`, `password` (a Gmail **App Password**, not the account password).

Two triggers:
1. **On new job creation** with a non-empty `assignedEmail` → send `[Job Assigned] {title}` to each address.
2. **Due reminder** — for jobs with `assignedEmail`, a `dueDate` 0–2 days away, status not Completed/Archived, and `reminder_sent_48h == false` → send `[Due {today|in Nd}] {title}` and set `reminder_sent_48h = true`. **Currently fires once per browser session** — on Vercel this MUST move to a **daily Cron job** (see §6), because there are no long-lived sessions.

**On Vercel:** SMTP from serverless works but is fiddly (cold starts, some providers block it). Two options:
- **Keep Gmail SMTP** via `nodemailer` in an API route — env: `GMAIL_SENDER`, `GMAIL_APP_PASSWORD`. Simplest, reuses existing mailbox.
- **Switch to Resend/Postmark/SendGrid** (recommended for Vercel reliability) — an HTTP API, no SMTP. Requires a verified sender domain.

Email body templates (reproduce):
- Assigned: greeting by `assignedName`, then Job/Priority/Status/(Notes)/(Due), signed "Jobs Management System".
- Reminder: greeting, "Reminder: the following job is due soon.", Job/Due/Location/Priority/Status/(Notes).

---

## 5. Google Calendar sync (service account)

**Current secret** (`[gcp_service_account]`): the full service-account JSON (`type, project_id, private_key_id, private_key, client_email, client_id, auth_uri, token_uri, auth_provider_x509_cert_url, client_x509_cert_url, universe_domain`) **plus** two extra keys the code reads: `calendar_id` (the target calendar — Oscar's) and `timezone`.

**Scope:** `https://www.googleapis.com/auth/calendar.events`.
**Calendar:** all writes go to `calendar_id`. That calendar must be **shared with the service account's `client_email`** with "Make changes to events" permission. (Already done for the existing personal-tasks app, which uses the same service account.)

**Behaviour — "jobs assigned to ME":** "me" is hard-coded to **Oscar** (name `"Oscar"` or email `0oscargunn0@gmail.com`). A job **should have** a calendar event iff: assigned to me **AND** has a `dueDate` **AND** status not Completed/Archived.

**`syncJobCalendar(job)`** reconciler (mutates `job.gcal_event_id`):
- should-have && no event id → `events.insert` → store returned id on the job
- should-have && has id → `events.update`
- !should-have && has id → `events.delete`, clear id

Event body (all-day): `summary = "⛵ " + title`, `description` = Priority/Status/Location/(Assigned)/(Notes)/(Description) joined by newlines, `start = end = { date: dueDate }`.

**Wire-in points:** after creating/editing a job, on status change, on restore, on auto-archive, and a full delete on job deletion. **Order matters:** run the calendar sync *before* persisting to Supabase, so the new `gcal_event_id` is saved in the same write.

**On Vercel:** use `googleapis` (npm). Build a JWT client from the service-account creds (store the JSON as a single env var, e.g. `GCP_SERVICE_ACCOUNT_JSON`, and `CALENDAR_ID`, `CALENDAR_TIMEZONE`). Do calendar calls in a **server-side API route / server action** only — never expose the private key to the browser.

> Generalization (optional): to also push Mattias's/David's assigned jobs to *their* calendars, map each contact → a calendar id and share each calendar with the service account. Replace the single `calendar_id` with a per-assignee lookup.

---

## 6. Scheduled jobs → Vercel Cron

Two things currently piggyback on page loads / GitHub Actions and must become **Vercel Cron** routes (`vercel.json` → `crons`):

1. **Due reminders** — daily (e.g. `0 8 * * *`): run the reminder logic from §4 over all jobs, send emails, set `reminder_sent_48h`, save.
2. **Auto-archive** — daily (can share the same cron): apply §3 auto-archive + calendar cleanup.
3. **Supabase keep-alive** — Supabase free tier still auto-pauses after 7 days idle. Either keep the existing **GitHub Action** (`.github/workflows/keep-alive.yml`, already configured), **or** fold a tiny Supabase read into one of the Vercel crons (simpler — one less system). If you keep the GitHub Action, nothing to do; it already runs every 3 days using repo secrets `SUPABASE_URL`/`SUPABASE_KEY`.

Protect cron routes with a secret header / `CRON_SECRET` so they can't be triggered publicly.

---

## 7. Secrets / environment variables

Copy these out of **Streamlit Cloud → app → Settings → Secrets** (TOML) and into **Vercel → Project → Settings → Environment Variables**.

| Streamlit (TOML) | Vercel env var(s) | Notes |
|---|---|---|
| `[supabase] url`, `key` | `SUPABASE_URL`, `SUPABASE_ANON_KEY` | Anon/public key. (Consider a service-role key for server-only writes.) |
| `[email] sender`, `password` | `GMAIL_SENDER`, `GMAIL_APP_PASSWORD` | Gmail App Password. Or swap for `RESEND_API_KEY` etc. |
| `[gcp_service_account] {full JSON}` | `GCP_SERVICE_ACCOUNT_JSON` | Paste the whole JSON as one value (mind newline escaping in `private_key`). |
| `[gcp_service_account] calendar_id` | `CALENDAR_ID` | Oscar's calendar. |
| `[gcp_service_account] timezone` | `CALENDAR_TIMEZONE` | e.g. `Pacific/Auckland`. |
| (cron protection) | `CRON_SECRET` | New — to guard cron routes. |

> The `private_key` field contains literal `\n` sequences. When loading `GCP_SERVICE_ACCOUNT_JSON`, `JSON.parse` it and, if needed, `key.replace(/\\n/g, "\n")` before constructing the JWT.

---

## 8. UI surface to reproduce (feature checklist)

Rebuild these screens/behaviours. None require Streamlit-specific tricks; they map to standard components.

**Top-level**
- [ ] Header: "Jobs Manager / NZL 49er Programme" + a **sync status badge** (green Synced / amber Local-only / red Cloud-failed). On Vercel "local-only" is largely moot; keep a Saved/Saving/Error indicator.
- [ ] Tab bar: **Dashboard** + one tab per location + "New Tab" + "Archived Tabs". Horizontal-scroll on mobile.

**Dashboard (landing)**
- [ ] 6 compact metric tiles (Total Active, Pending, In Progress, Completed, Overdue, Urgent). Each tile is clickable → toggles a pop-out list of those jobs below the row.
- [ ] **Needs Attention** column: overdue/urgent active jobs (excl. Completed), sorted overdue-first.
- [ ] **By Assignee**: one card per contact (+ an "Unassigned" card) with job counts and overdue/urgent flags; clicking opens a modal listing that person's active jobs. An **"+ Add Contact"** button (name + email).

**Location tab (kanban)**
- [ ] Three columns Pending / In Progress / Completed, cards sorted by effective priority then due date.
- [ ] Card: clickable title (opens job dialog), priority + status **pill badges**, due/assignee/comment-count meta, overdue red top-bar, inline status dropdown, delete button.
- [ ] "+ Add Job", "Archive Tab", "Delete Tab", rename + reorder tab controls. Active/Archive view toggle.

**Job dialog (modal)**
- [ ] Title, Description, **Comments thread** (always visible, newest first, add comment), Priority, Status, Location, Due Date, **Assigned-To multiselect from contacts** (writes both `assignedName` and `assignedEmail`), **Subtasks** checklist (add/remove/toggle). Save/Cancel.
- [ ] On save: persist, send assignment email if new + has email, reconcile calendar event.

**Other tabs**
- [ ] New Tab (create location), Archived Tabs (restore / permanently delete; deleting purges its jobs).

**Cross-cutting**
- [ ] Dark mode mirroring OS preference.
- [ ] Auto-archive Completed → Archived after 48h.

---

## 9. Suggested target architecture (Next.js on Vercel)

```
/app
  /(ui)             React components: Dashboard, KanbanTab, JobDialog, cards, badges
  /api
    /state          GET/PUT the app_state blob (server, uses service-role key)
    /email          POST send (nodemailer or Resend)
    /calendar       POST sync one job  (googleapis, service account)
    /cron/daily     reminders + auto-archive + keep-alive  (guarded by CRON_SECRET)
/lib
  logic.ts          effectivePriority, isOverdue, jobAssignees, sort, autoArchive (pure)
  supabase.ts       client(s)
  calendar.ts       JWT client + reconciler
  mail.ts           send helpers + templates
vercel.json         crons: [{ path: "/api/cron/daily", schedule: "0 8 * * *" }]
```

- **Reads/writes** go through `/api/state` (or server actions) using a **service-role** Supabase key so the browser never holds write credentials. Keep the "whole blob" read/modify/write pattern for cutover parity.
- **Calendar + email** only ever run server-side.
- **Optimistic UI**: update local state immediately, persist in the background, show the sync badge.

---

## 10. Step-by-step migration plan

1. **Access check** — confirm access to: GitHub repo, Streamlit Cloud secrets, Supabase dashboard (`tbqefnlqkqdjznvyhmtc`), the Vercel project, the Google Cloud project / service account, and the Gmail App Password.
2. **Copy secrets** into Vercel env vars (§7). Verify `private_key` newline handling with a one-off test route.
3. **Wire Supabase** in the Vercel app; implement `/api/state` GET/PUT against `app_state` id=1. Confirm you can read the existing blob (you should see all current jobs immediately).
4. **Port pure logic** (§3) into `/lib/logic.ts` with unit tests (a few fixture jobs covering overdue/escalation/auto-archive).
5. **Build the UI** (§8) reading/writing through `/api/state`. Dashboard → tabs → job dialog. Keep the blob contract identical.
6. **Email** (§4) — `/api/email`; hook into job-create; verify a test send.
7. **Calendar** (§5) — `/api/calendar`; implement the reconciler; wire into save/status/delete; verify an event appears on Oscar's calendar for a due-dated job assigned to him.
8. **Cron** (§6) — `/api/cron/daily` for reminders + auto-archive (+ optional keep-alive); add to `vercel.json`; test by invoking with the `CRON_SECRET` header.
9. **Parallel run** — both apps point at the same Supabase row. Sanity-check that edits in the Vercel app appear correctly and the Streamlit app still reads them.
10. **Cutover** — once verified, stop using Streamlit. Optionally keep the GitHub keep-alive (harmless) or remove it if a Vercel cron now pings Supabase.
11. **Decommission** — archive/delete the Streamlit app. Keep the repo (or move `app.py` to a `legacy/` folder for reference).

---

## 11. Gotchas (read before you start)

- **No local filesystem on Vercel.** Drop the `jobs_data.json` fallback entirely. Supabase is the single source of truth; surface errors loudly instead of silently falling back.
- **No long-lived sessions.** Anything that was "once per session" (due reminders) must become a **cron**. Don't tie reminders to page loads.
- **Service-account `private_key` newlines** are the #1 cause of "calendar auth fails on deploy but works locally." `JSON.parse` + `replace(/\\n/g,"\n")`.
- **Supabase still pauses** on the free tier — keep *some* keep-alive (GitHub Action already there, or a Vercel cron read).
- **Single-blob concurrency** — last-write-wins overwrites the whole blob. If two people will edit simultaneously, plan the phase-2 relational migration (§2).
- **Secrets are duplicated**, not moved — the Google service account and Supabase project are **shared** with the existing personal-tasks app. Don't rotate keys without updating every consumer.
- **Calendar sharing** — if events don't appear, 99% of the time the target calendar isn't shared with the service account `client_email`, or `CALENDAR_ID` is wrong.
- **"Me" is hard-coded to Oscar** for calendar routing. Decide whether the Vercel app should generalize to per-user calendars.

---

## 12. Reference — current source

Everything lives in a single file: `app.py` in `github.com/oscargunn/Sailing_to_do_list`. Key sections to read when reimplementing:
- Email: `send_email`, `notify_assigned`, `send_due_reminders`
- Supabase: `_get_supabase`, `load_data`, `save_data` (+ sync-status/drift logic)
- Logic: `effective_priority`, `_is_overdue`, `job_assignees`, `auto_archive`, sort keys
- Calendar: `_gcal_service`, `assigned_to_me`, `_gcal_event_body`, `_should_have_event`, `sync_job_calendar`, `delete_job_calendar`
- UI: `render_dashboard`, `render_kanban`, `render_active_card`, `job_dialog`, the contacts dialogs
- Keep-alive: `.github/workflows/keep-alive.yml`
