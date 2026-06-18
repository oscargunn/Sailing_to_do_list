import streamlit as st
import json
import os
import re
import random
import string
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, date

try:
    from supabase import create_client
    _SUPABASE_PKG = True
    _SUPABASE_IMPORT_ERROR = ""
except Exception as _e:          # ImportError OR a broken dependency on import
    _SUPABASE_PKG = False
    _SUPABASE_IMPORT_ERROR = f"{type(_e).__name__}: {_e}"

st.set_page_config(page_title="Jobs Manager", page_icon=None, layout="wide")

# ── Constants ─────────────────────────────────────────────────────────────────

PRIORITY_STYLES = {
    "Low":    {"bg": "#eff6ff", "color": "#2563eb", "dot": "#3b82f6"},
    "Medium": {"bg": "#fff7ed", "color": "#c2410c", "dot": "#f97316"},
    "High":   {"bg": "#fdf4ff", "color": "#7e22ce", "dot": "#a855f7"},
    "Urgent": {"bg": "#fef2f2", "color": "#b91c1c", "dot": "#ef4444"},
}
STATUS_STYLES = {
    "Pending":     {"bg": "#fdf2f8", "color": "#9d174d", "dot": "#ec4899"},
    "In Progress": {"bg": "#fff7ed", "color": "#c2410c", "dot": "#f97316"},
    "Completed":   {"bg": "#f0fdf4", "color": "#15803d", "dot": "#22c55e"},
    "Archived":    {"bg": "#f8fafc", "color": "#94a3b8", "dot": "#cbd5e1"},
}

DEFAULT_TABS    = ["Europe", "NZ General", "LA Boat", "R1047", "Rigs", "New Boat"]
STORAGE_FILE    = "jobs_data.json"
PRIORITY_LEVELS = ["Low", "Medium", "High", "Urgent"]
PRIORITY_RANK   = {p: i for i, p in enumerate(PRIORITY_LEVELS)}

KNOWN_EMAILS = [
    "0oscargunn0@gmail.com",
    "mattias.coutts1@gmail.com",
    "dgg1000@gmail.com",
]

# Seed contacts — used if the contacts list is empty on first load
DEFAULT_CONTACTS = [
    {"id": "c001", "name": "Oscar",   "email": "0oscargunn0@gmail.com"},
    {"id": "c002", "name": "Mattias", "email": "mattias.coutts1@gmail.com"},
    {"id": "c003", "name": "David",   "email": "dgg1000@gmail.com"},
]

RAW_SEED = [
    ["Fair in bow dent","Europe","Archived","Medium","",""],
    ["Fair in hull scratch","Europe","Archived","Medium","",""],
    ["Mainsheet tail and bridle","Europe","Archived","Medium","",""],
    ["New mainsheet with fineline 6mm","Europe","Archived","Medium","",""],
    ["New kite halyard","Europe","Pending","Medium","",""],
    ["Spare mast","Europe","Archived","Medium","Add the rigging and check setting",""],
    ["New kite sheet","Europe","Archived","Medium","",""],
    ["New jib sheet","Europe","Archived","Medium","",""],
    ["New jib tack ferrel and smooth the fitting","Europe","Archived","Medium","",""],
    ["Tighten up gantrey","Europe","Archived","Medium","",""],
    ["Sticker main","Europe","Archived","Medium","",""],
    ["New tools made","Europe","Pending","Medium","",""],
    ["Bungys under kite blocks","Europe","Archived","Medium","",""],
    ["New kite halyard cleat in the deck","Europe","Archived","Medium","",""],
    ["Glue up breather hole","Europe","Pending","Medium","",""],
    ["Debrief meeting with Hugo","Europe","Archived","Medium","",""],
    ["Recut thread and grease turn buckles","Europe","Archived","Medium","",""],
    ["Enter coach boat","Europe","Archived","Medium","",""],
    ["Decide lead placement","Europe","Archived","Medium","",""],
    ["Foam on tiller bar","Europe","Archived","Medium","",""],
    ["Europe windgear plan","NZ General","In Progress","Medium","","David/Oscar"],
    ["Pelican case for windgear","NZ General","In Progress","Medium","","David"],
    ["Rope jammer update","NZ General","Pending","Medium","",""],
    ["Logistics confirmation with Gabi","NZ General","In Progress","Medium","Shift conversation to David","Oscar"],
    ["Debrief template","NZ General","Pending","Medium","Hugo to work on this",""],
    ["Lock in Pepe","NZ General","Pending","Medium","Reboot the conversation",""],
    ["New jib cleat drawings","NZ General","In Progress","Urgent","Oscar to update drawings","David/Oscar"],
    ["New turn buckle drawings (both styles)","NZ General","Pending","Urgent","Oscar to update drawings","David/Oscar"],
    ["Order turn buckle tools","NZ General","Pending","Urgent","Confirm with china factory","Oscar"],
    ["Update tiller extension jigs","NZ General","Pending","Urgent","Update drawing and reprint","Oscar"],
    ["Print new tiller extension jigs","NZ General","Pending","Urgent","","Oscar"],
    ["Order new jib cleats","NZ General","Pending","Urgent","Confirm with china factory","Oscar"],
    ["New heavy harness bar drawings","NZ General","Pending","Medium","Oscar give bar to David","Oscar/David"],
    ["Order heavy harness bars","NZ General","Pending","Medium","",""],
    ["Sail stickers for new main","NZ General","In Progress","Medium","","Oscar"],
    ["Insurance on airfreight box","NZ General","Pending","Medium","","Mattias"],
    ["Racing insurance on new boat","NZ General","In Progress","Medium","","Mattias"],
    ["Check insurance on palma boat","NZ General","Archived","Medium","","Oscar"],
    ["Windgear pole foot mount","NZ General","In Progress","Medium","","Oscar"],
    ["Packing list for LA","NZ General","Pending","Medium","",""],
    ["List of parts to fly to LA","NZ General","Pending","Medium","",""],
    ["Jobs list for LA boat after we leave","NZ General","Pending","Medium","",""],
    ["Update inventory with full sail locations","NZ General","Pending","Medium","",""],
    ["Anzor order list for LA boat","NZ General","Pending","Medium","",""],
    ["Carbotech parts design and order","NZ General","Pending","Medium","Trap disks and footstrap washers",""],
    ["New trap rings","NZ General","Pending","Medium","",""],
    ["Completed trap cleats","NZ General","Pending","Medium","",""],
    ["List of spares to organise for LA","NZ General","Pending","Medium","",""],
    ["LA Carnet and insurance","NZ General","Pending","Medium","",""],
    ["Prepreg footstrap washers and underside plate","LA Boat","Pending","High","Organise with Carbo tech",""],
    ["Foot strap hardware","LA Boat","In Progress","Medium","Reuse Mattas",""],
    ["Foot straps","LA Boat","In Progress","Medium","Reuse NZL boat",""],
    ["Drill and backfill holes for footstraps","LA Boat","Pending","Medium","Not doing",""],
    ["Threadcert gantry","LA Boat","Archived","Medium","Taken from NZ boat",""],
    ["Cut thread into rudder pin","LA Boat","Archived","Medium","Taken from NZ boat",""],
    ["Drill centre hole in rudder pin and insert grub screw","LA Boat","In Progress","Medium","Update on grub screw",""],
    ["Pack rudder","LA Boat","Pending","Medium","Boat builder",""],
    ["Cut tiller down","LA Boat","Archived","Medium","Taken from NZ boat",""],
    ["Assemble permanent tiller UJs","LA Boat","Archived","Medium","Taken from NZ boat",""],
    ["Turning block with fishing swivel on gantry","LA Boat","Pending","Low","Not doing",""],
    ["Bridle mainsheet combo with high load blocks","LA Boat","Archived","Medium","Bridle made, harken blocks",""],
    ["Tie on kite blocks assembled","LA Boat","Pending","Medium","Taken from NZ boat",""],
    ["Jib cleat backfilled and tapped","LA Boat","Pending","Medium","","David"],
    ["New allen cheek blocks for van/cunno","LA Boat","Pending","Low","Not doing",""],
    ["Vang cunno blocks assembled on mast foot","LA Boat","Pending","Low","Not doing",""],
    ["Centre board packed","LA Boat","Pending","Medium","Boat builder",""],
    ["Drill hole in jib track for down retainer line","LA Boat","Pending","Low","Not doing",""],
    ["4x track pins","LA Boat","Pending","Medium","Get Dad to order a heap of pins",""],
    ["Groove filled in edge of track for kite sock","LA Boat","Pending","Low","Not doing",""],
    ["3x washers packed under kite halyard saddle","LA Boat","Archived","Medium","Not glued underneath",""],
    ["Soft shackle through wing mount for jib tack","LA Boat","Archived","Medium","",""],
    ["Pole tack line made with main bungy inside","LA Boat","Archived","Medium","",""],
    ["Single foot saddle for kite pole","LA Boat","Pending","Low","Not doing",""],
    ["Kite pole sanded smooth","LA Boat","Archived","Medium","Used pole",""],
    ["Jib primary made","LA Boat","Pending","Medium","Taken from NZ boat",""],
    ["Allen block mounted onto jib track car","LA Boat","Pending","Medium","Taken from NZ boat",""],
    ["Black webbing cut off kite sock end piece","LA Boat","Pending","Low","Do in LA",""],
    ["Kite sheet retainer bungys","LA Boat","Pending","Low","Make in LA",""],
    ["Compass mounts glued on under gunwale","LA Boat","Pending","Medium","","David"],
    ["Bow allen blocks backfilled and tapped","LA Boat","Pending","Medium","","David"],
    ["Sikaflex touch ups in kite throat","LA Boat","Pending","Low","Not doing",""],
    ["Backfill and tap kite sock retainer screws","LA Boat","Pending","Medium","","David"],
    ["Custom bow pole cheek block","LA Boat","Pending","Medium","Need to build more blocks",""],
    ["Kite halyard floating block assembly made","LA Boat","Archived","Medium","",""],
    ["Full bungy kit out","LA Boat","Pending","Medium","Will do in LA",""],
    ["Boom blocks replaced with high load","LA Boat","Pending","Low","Not doing",""],
    ["Purchase removed from outhaul and new outhaul rope","LA Boat","Archived","Medium","",""],
    ["New foil handles","LA Boat","Pending","Medium","","David/Mattias"],
    ["Pre preg parts from china","LA Boat","Pending","Medium","Carbo tech",""],
    ["Allen blocks for control lines","LA Boat","Pending","Low","Not doing",""],
    ["Control line ferrel guides","LA Boat","Archived","Medium","",""],
    ["8:1 tack line rope jammer","LA Boat","In Progress","Medium","",""],
    ["Control line take up blocks and bungy","LA Boat","In Progress","Medium","Drill out hole and replace with NZ blocks",""],
    ["Permanent track pins for T6","LA Boat","Pending","Medium","Purchase from Anzor","David"],
    ["Bow ferrel and diamond knot for tack line","LA Boat","Archived","Medium","",""],
    ["Forestay pin","LA Boat","Archived","Medium","",""],
    ["Tiller extension pins","LA Boat","Pending","Medium","Organise with tillers",""],
    ["New jib sheet","R1047","Pending","Medium","",""],
    ["New bridle","R1047","Pending","Medium","",""],
    ["New mainsheet","R1047","Pending","Medium","",""],
    ["New kite sheet","R1047","Pending","Medium","",""],
    ["Update tiller extension system","R1047","Pending","Medium","",""],
    ["8:1 jib tack","R1047","Pending","Medium","",""],
    ["New halyards","Rigs","Pending","Medium","",""],
    ["More spreader loops","Rigs","Pending","Medium","",""],
    ["New halyard adjusters","Rigs","Pending","Medium","",""],
    ["Update mast tenon on C7","Rigs","Pending","Medium","",""],
    ["Post cure","New Boat","Archived","Medium","Teed up with ETNZ",""],
    ["Prepreg footstrap washers and underside plate","New Boat","Archived","High","Home made job",""],
    ["Foot strap hardware","New Boat","Archived","Medium","",""],
    ["Foot straps","New Boat","Archived","High","Organise with Matty",""],
    ["Drill and backfill holes for footstraps","New Boat","Archived","Medium","",""],
    ["Threadcert gantry","New Boat","Archived","High","",""],
    ["Cut thread into rudder pin","New Boat","Archived","High","",""],
    ["Drill centre hole in rudder pin and insert grub screw","New Boat","Archived","High","",""],
    ["Pack rudder","New Boat","Archived","Urgent","",""],
    ["Cut tiller down","New Boat","Archived","Medium","",""],
    ["Assemble permanent tiller UJs","New Boat","Archived","High","Buy brass tube insert",""],
    ["Turning block with fishing swivel on gantry","New Boat","Archived","Medium","Used little ferrel",""],
    ["Bridle mainsheet combo with high load blocks","New Boat","Archived","Medium","",""],
    ["Tie on kite blocks assembled","New Boat","Archived","High","Need to buy harken block",""],
    ["Jib cleat backfilled and tapped","New Boat","Archived","High","Centre holes with a jig",""],
    ["New allen cheek blocks for van/cunno","New Boat","Pending","Low","Not going to do this atm",""],
    ["Vang cunno blocks assembled on mast foot","New Boat","Archived","Medium","",""],
    ["Centre board packed","New Boat","Archived","Medium","",""],
    ["Drill hole centred of jib track","New Boat","Archived","Medium","",""],
    ["4x track pins","New Boat","Pending","Low","",""],
    ["Groove filled in edge of track for kite sock","New Boat","Archived","Low","Got a little line in there instead",""],
    ["3x washers packed under kite halyard saddle","New Boat","Archived","Medium","",""],
    ["Soft shackle through wing mount for jib tack","New Boat","Archived","Medium","",""],
    ["Pole tack line made with main bungy inside","New Boat","Archived","High","",""],
    ["Single foot saddle for kite pole","New Boat","Pending","Medium","Not doing this",""],
    ["Kite pole sanded smooth","New Boat","Archived","Medium","",""],
    ["Jib primary made","New Boat","Archived","High","",""],
    ["Allen block mounted onto jib track car","New Boat","Archived","High","",""],
    ["Black webbing cut off kite sock end piece","New Boat","Archived","Low","",""],
    ["Kite sheet retainer bungys","New Boat","Archived","Low","",""],
    ["Compass mounts glued on under gunwale","New Boat","Archived","High","",""],
    ["Bow allen blocks backfilled and tapped","New Boat","Archived","Medium","",""],
    ["Sikaflex touch ups in kite throat","New Boat","Archived","Medium","",""],
    ["Backfill and tap kite sock retainer screws","New Boat","Archived","Medium","",""],
    ["Custom bow pole cheek block","New Boat","Pending","Low","Can take one off euro boat or make new",""],
    ["Kite halyard floating block assembly made","New Boat","Archived","Medium","",""],
    ["Full bungy kit out","New Boat","Archived","Medium","Need to buy 24m of bungy",""],
    ["Boom blocks replaced with high load","New Boat","Archived","Medium","Sort rivets",""],
    ["Purchase removed from outhaul and new outhaul rope","New Boat","Archived","Medium","",""],
    ["New foil handles","New Boat","Archived","Medium","",""],
    ["Pre preg parts from china","New Boat","Pending","Medium","Not doing this",""],
    ["Allen blocks for control lines","New Boat","Archived","High","Not changing deck blocks",""],
    ["Control line ferrel guides","New Boat","Archived","High","",""],
    ["8:1 tack line rope jammer","New Boat","Archived","High","",""],
    ["Control line take up blocks and bungy","New Boat","Archived","High","",""],
    ["Permanent track pins for T6","New Boat","Archived","High","",""],
    ["Bow ferrel and diamond knot for tack line","New Boat","Archived","Medium","",""],
    ["Forestay pin","New Boat","Pending","High","",""],
    ["Tiller extension pins","New Boat","Pending","Medium","",""],
]

# ── Email ─────────────────────────────────────────────────────────────────────

def send_email(to_addr: str, subject: str, body: str):
    try:
        cfg        = st.secrets["email"]
        recipients = [a.strip() for a in to_addr.split(",") if a.strip()]
        if not recipients:
            return False
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
            s.login(cfg["sender"], cfg["password"])
            for recipient in recipients:
                msg = MIMEText(body)
                msg["Subject"] = subject
                msg["From"]    = cfg["sender"]
                msg["To"]      = recipient
                s.sendmail(cfg["sender"], [recipient], msg.as_string())
        return True
    except Exception as e:
        st.session_state["email_toast_error"] = f"Email failed: {e}"
        return False

def notify_assigned(job: dict) -> bool:
    if not job.get("assignedEmail"):
        return False
    body = (
        f"Hi {job.get('assignedName') or 'there'},\n\n"
        f"You have been assigned a job on the {job['location']} project.\n\n"
        f"Job:      {job['title']}\n"
        f"Priority: {job['priority']}\n"
        f"Status:   {job['status']}\n"
        + (f"Notes:    {job['notes']}\n" if job.get("notes") else "")
        + (f"Due:      {job['dueDate']}\n" if job.get("dueDate") else "")
        + "\nPlease log in to view full details.\n\nRegards,\nJobs Management System"
    )
    return send_email(job["assignedEmail"], f"[Job Assigned] {job['title']}", body)

def send_due_reminders():
    """Send 48-hour due-date reminder emails once per session per job."""
    if st.session_state.get("_reminders_checked"):
        return
    st.session_state["_reminders_checked"] = True
    dirty = False
    for j in st.session_state.jobs:
        if (j.get("reminder_sent_48h") or
                j.get("status") in ("Completed", "Archived") or
                not j.get("assignedEmail") or
                not j.get("dueDate")):
            continue
        try:
            days_left = (date.fromisoformat(j["dueDate"]) - date.today()).days
            if 0 <= days_left <= 2:
                body = (
                    f"Hi {j.get('assignedName') or 'there'},\n\n"
                    f"Reminder: the following job is due soon.\n\n"
                    f"Job:      {j['title']}\n"
                    f"Due:      {j['dueDate']}\n"
                    f"Location: {j['location']}\n"
                    f"Priority: {j['priority']}\n"
                    f"Status:   {j['status']}\n"
                    + (f"Notes:    {j['notes']}\n" if j.get("notes") else "")
                    + "\nRegards,\nJobs Management System"
                )
                label = "today" if days_left == 0 else f"in {days_left}d"
                ok = send_email(j["assignedEmail"], f"[Due {label}] {j['title']}", body)
                if ok:
                    j["reminder_sent_48h"] = True
                    dirty = True
        except ValueError:
            pass
    if dirty:
        save_data()

# ── Supabase client ───────────────────────────────────────────────────────────

@st.cache_resource
def _get_supabase():
    """Return (client, status). status: 'ok' | 'no_package' | 'no_secrets' | 'error: ...'."""
    if not _SUPABASE_PKG:
        return None, "no_package"
    try:
        cfg = st.secrets["supabase"]
    except Exception:
        return None, "no_secrets"
    try:
        return create_client(cfg["url"], cfg["key"]), "ok"
    except Exception as e:
        return None, f"error: {e}"

# ── Data layer ────────────────────────────────────────────────────────────────

def now_ms() -> float:
    return datetime.now().timestamp() * 1000

def fmt_ago(ts) -> str:
    """Human 'time ago' from a ms timestamp."""
    if not ts:
        return ""
    secs = (now_ms() - ts) / 1000
    if secs < 60:
        return "just now"
    mins = secs / 60
    if mins < 60:
        return f"{int(mins)}m ago"
    hrs = mins / 60
    if hrs < 24:
        return f"{int(hrs)}h ago"
    return f"{int(hrs / 24)}d ago"

def gen_id() -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=10))

def effective_priority(job: dict) -> str:
    """Return priority escalated toward Urgent as the due date approaches."""
    rank = PRIORITY_RANK.get(job.get("priority", "Medium"), 1)
    due  = job.get("dueDate", "")
    if due:
        try:
            days_left = (date.fromisoformat(due) - date.today()).days
            if days_left < 0:       # overdue
                rank = 3
            elif days_left == 0:    # due today
                rank = min(rank + 2, 3)
            elif days_left <= 2:    # due in 1-2 days
                rank = min(rank + 2, 3)
            elif days_left <= 5:    # due in 3-5 days
                rank = min(rank + 1, 3)
        except ValueError:
            pass
    return PRIORITY_LEVELS[rank]

def job_assignees(job: dict) -> list:
    """Return list of individual assignee name strings (handles / and , separators)."""
    raw = job.get("assignedName") or ""
    return [n.strip() for n in re.split(r"[,/]", raw) if n.strip()]

def _is_overdue(job: dict) -> bool:
    """True when a non-completed job is past its due date."""
    due = job.get("dueDate")
    if not due or job.get("status") in ("Completed", "Archived"):
        return False
    try:
        return (date.fromisoformat(due) - date.today()).days < 0
    except ValueError:
        return False

def make_seed() -> list:
    ts = now_ms()
    return [
        {
            "id": f"s{i}",
            "title": r[0], "location": r[1], "status": r[2], "priority": r[3],
            "notes": r[4], "assignedName": r[5],
            "assignedEmail": "", "description": "", "dueDate": "",
            "createdAt": ts - random.randint(0, 7 * 86_400_000),
            "completedAt": ts - 50 * 3_600_000 if r[2] == "Archived" else None,
            "comments": [], "subtasks": [], "reminder_sent_48h": False,
        }
        for i, r in enumerate(RAW_SEED)
    ]

def _set_sync(status: str, message: str, last_synced, source: str):
    """Record the live sync state so the header badge can show it.
    status: 'synced' (cloud is current) | 'local' (cloud not reached) | 'error' (cloud failed)."""
    st.session_state["sb_status"]   = status
    st.session_state["sb_message"]  = message
    st.session_state["last_synced"] = last_synced
    st.session_state["sync_source"] = source

def _unpack(d: dict) -> tuple:
    """Turn a stored payload dict into the 4-tuple the app expects."""
    return (
        d.get("jobs", make_seed()),
        d.get("tabs", list(DEFAULT_TABS)),
        d.get("archived_tabs", []),
        d.get("contacts", list(DEFAULT_CONTACTS)),
    )

def _read_local():
    """Return (payload, error_str). payload is dict or None."""
    if os.path.exists(STORAGE_FILE):
        try:
            with open(STORAGE_FILE) as f:
                return json.load(f), None
        except Exception as e:
            return None, str(e)
    return None, None

def _read_supabase(sb):
    """Return (payload, error_str). payload is dict or None (None = reached but empty)."""
    try:
        result = sb.table("app_state").select("data").eq("id", 1).execute()
        if result.data:
            d = result.data[0]["data"]
            if d.get("jobs"):
                return d, None
        return None, None
    except Exception as e:
        return None, str(e)

def load_data() -> tuple:
    sb, sb_state = _get_supabase()
    local, _local_err = _read_local()
    seed = (make_seed(), list(DEFAULT_TABS), [], list(DEFAULT_CONTACTS))

    # ── No Supabase client at all (not configured / package missing) ──
    if sb is None:
        if sb_state == "no_package":
            msg = f"Supabase library failed to load — using local file only. ({_SUPABASE_IMPORT_ERROR})"
        elif sb_state == "no_secrets":
            msg = "Supabase not configured (no [supabase] secret found) — using local file only."
        else:
            msg = f"Supabase connection failed — using local file only. ({sb_state})"
        if local:
            _set_sync("local", msg, local.get("last_synced"), "local")
            return _unpack(local)
        _set_sync("local", msg, None, "seed")
        return seed

    # ── Client exists — try to read the cloud copy ──
    remote, remote_err = _read_supabase(sb)
    if remote_err:
        msg = f"Could not read from Supabase — using local file. ({remote_err})"
        if local:
            _set_sync("error", msg, local.get("last_synced"), "local")
            return _unpack(local)
        _set_sync("error", msg, None, "seed")
        return seed

    # ── Read succeeded. Compare timestamps to detect drift ──
    r_ts = (remote or {}).get("last_synced") or 0
    l_ts = (local  or {}).get("last_synced") or 0

    # Local is strictly newer → a previous cloud save didn't land. Prefer local & re-push.
    if local and l_ts > r_ts:
        _set_sync("synced", "Local had newer changes — re-syncing to Supabase…", l_ts, "local")
        st.session_state["_resync_needed"] = True
        return _unpack(local)

    if remote:
        _set_sync("synced", "Synced with Supabase.", r_ts, "supabase")
        return _unpack(remote)

    # Cloud reachable but empty. Seed it from local if we have one.
    if local:
        _set_sync("synced", "Synced with Supabase.", l_ts, "local")
        st.session_state["_resync_needed"] = True
        return _unpack(local)
    _set_sync("synced", "Connected to Supabase (empty) — starting fresh.", None, "seed")
    return seed

def save_data():
    ts = now_ms()
    payload = {
        "jobs":          st.session_state.jobs,
        "tabs":          st.session_state.tabs_list,
        "archived_tabs": st.session_state.archived_tabs,
        "contacts":      st.session_state.get("contacts", list(DEFAULT_CONTACTS)),
        "last_synced":   ts,
    }

    # 1 — local JSON first (fast, always available)
    local_ok = True
    try:
        with open(STORAGE_FILE, "w") as f:
            json.dump(payload, f, indent=2)
    except Exception:
        local_ok = False

    # 2 — Supabase (cloud, durable)
    sb, sb_state = _get_supabase()
    if sb is None:
        if sb_state == "no_secrets":
            _set_sync("local", "Not connected to Supabase (no [supabase] secret) — saved on this device only.",
                      ts if local_ok else st.session_state.get("last_synced"), "local")
        elif sb_state == "no_package":
            _set_sync("local", f"Supabase library failed to load — saved on this device only. ({_SUPABASE_IMPORT_ERROR})",
                      ts if local_ok else st.session_state.get("last_synced"), "local")
        else:
            _set_sync("error", f"Supabase unavailable — saved on this device only. ({sb_state})",
                      ts if local_ok else st.session_state.get("last_synced"), "local")
        return

    try:
        sb.table("app_state").upsert({"id": 1, "data": payload}).execute()
        _set_sync("synced", "Synced with Supabase.", ts, "supabase")
    except Exception as e:
        _set_sync("error",
                  f"Saved on this device, but the cloud save FAILED — this change is not backed up. ({e})",
                  ts if local_ok else st.session_state.get("last_synced"), "local")

# ── Mutations ─────────────────────────────────────────────────────────────────

def auto_archive():
    ts    = now_ms()
    dirty = False
    for j in st.session_state.jobs:
        if j["status"] == "Completed" and j.get("completedAt") and ts - j["completedAt"] >= 48 * 3_600_000:
            j["status"] = "Archived"
            dirty = True
    if dirty:
        save_data()

def set_status(job_id: str, status: str):
    for j in st.session_state.jobs:
        if j["id"] == job_id:
            j["status"] = status
            if status == "Completed":
                j["completedAt"] = now_ms()
            break
    save_data()

def remove_job(job_id: str):
    st.session_state.jobs = [j for j in st.session_state.jobs if j["id"] != job_id]
    save_data()

def restore_job(job_id: str):
    for j in st.session_state.jobs:
        if j["id"] == job_id:
            j["status"]            = "Pending"
            j["completedAt"]       = None
            j["reminder_sent_48h"] = False   # allow a fresh reminder
            break
    save_data()

def upsert_job(data: dict, job_id: str | None = None):
    is_new = job_id is None
    if job_id:
        for i, j in enumerate(st.session_state.jobs):
            if j["id"] == job_id:
                st.session_state.jobs[i] = {**j, **data}
                saved = st.session_state.jobs[i]
                break
    else:
        new_job = {
            "comments": [], "subtasks": [], "reminder_sent_48h": False,
            **data,
            "id": gen_id(), "createdAt": now_ms(), "completedAt": None,
        }
        st.session_state.jobs.append(new_job)
        saved = new_job
    save_data()
    # Auto-send email on new job creation if email provided
    if is_new and saved.get("assignedEmail"):
        success = notify_assigned(saved)
        if success:
            st.session_state["email_toast"] = f"Notification sent to {saved['assignedEmail']}"
        else:
            st.session_state["email_toast_error"] = f"Email failed — check Streamlit secrets."

# ── Modal card (simplified card for use inside dialogs) ───────────────────────

def render_modal_card(j: dict, mk: str):
    """Compact card for modal views — title opens the job dialog, no inline status select."""
    is_ov = _is_overdue(j)
    with st.container(border=True):
        if is_ov:
            st.markdown(
                '<div style="background:#ef4444;height:3px;margin:-4px -8px 6px;'
                'border-radius:1px 1px 0 0;"></div>', unsafe_allow_html=True,
            )
        if st.button(j["title"], key=f"mc_{mk}_{j['id']}", use_container_width=True):
            # Close any open modal, then open the job dialog
            st.session_state.assignee_modal_open = False
            st.session_state.dlg_job_id          = j["id"]
            st.session_state.dlg_open            = True
            st.rerun()
        eff_p = effective_priority(j)
        meta  = []
        if j.get("dueDate"):
            try:
                dl = (date.fromisoformat(j["dueDate"]) - date.today()).days
                if dl < 0:    meta.append(f"🔴 Overdue {-dl}d")
                elif dl == 0: meta.append("Due today")
                else:         meta.append(f"Due {j['dueDate']}")
            except ValueError:
                pass
        if j.get("assignedName"): meta.append(j["assignedName"])
        meta_html = f"<p style='font-size:11px;color:#94a3b8;margin:2px 0;'>{'  ·  '.join(meta)}</p>" if meta else ""
        st.markdown(
            badge(eff_p, PRIORITY_STYLES[eff_p]) + " " +
            badge(j["status"], STATUS_STYLES[j["status"]]) + meta_html,
            unsafe_allow_html=True,
        )

# ── Contacts dialogs ───────────────────────────────────────────────────────────

@st.dialog("Add Contact", width="small")
def add_contact_dialog():
    st.markdown("Add a new team member. They'll appear in the assignment picker on all job cards.")
    name  = st.text_input("Name *", placeholder="e.g. Hugo")
    email = st.text_input("Email",  placeholder="e.g. hugo@team.com")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Add", type="primary", use_container_width=True):
            n = name.strip()
            if not n:
                st.error("Name is required.")
                return
            if any(c["name"].lower() == n.lower() for c in st.session_state.contacts):
                st.warning(f"'{n}' already exists.")
                return
            st.session_state.contacts.append({"id": gen_id(), "name": n, "email": email.strip()})
            save_data()
            st.session_state.add_contact_open = False
            st.rerun()
    with c2:
        if st.button("Cancel", use_container_width=True):
            st.session_state.add_contact_open = False
            st.rerun()

@st.dialog("Team Member", width="large")
def assignee_jobs_modal():
    name     = st.session_state.get("modal_assignee_name", "")
    contacts = st.session_state.get("contacts", list(DEFAULT_CONTACTS))
    is_unassigned = (name == "__unassigned__")

    if is_unassigned:
        contact = None
        st.markdown("### 👤 Unassigned")
        st.caption("Jobs with no assigned team member")
    else:
        contact = next((c for c in contacts if c["name"] == name), None)
        st.markdown(f"### 👤 {name}")
        if contact and contact.get("email"):
            st.caption(contact["email"])

    # Collect jobs for this person/unassigned bucket
    all_active = [j for j in st.session_state.jobs if j["status"] != "Archived"]
    if is_unassigned:
        jobs = [j for j in all_active if not job_assignees(j)]
    elif contact and contact.get("email"):
        email = contact["email"]
        jobs = [
            j for j in all_active
            if name in job_assignees(j)
            or email in {e.strip() for e in j.get("assignedEmail", "").split(",") if e.strip()}
        ]
    else:
        jobs = [j for j in all_active if name in job_assignees(j)]

    jobs.sort(key=lambda j: (-PRIORITY_RANK[effective_priority(j)], j.get("dueDate") or "9999"))

    st.divider()
    if not jobs:
        st.info("No active jobs here." if is_unassigned else "No active jobs assigned to this person.")
    else:
        st.caption(f"{len(jobs)} active job{'s' if len(jobs) != 1 else ''}")
        cols = st.columns(3)
        for i, j in enumerate(jobs):
            with cols[i % 3]:
                render_modal_card(j, "asgn")

    st.divider()
    if contact and not is_unassigned:
        dc1, dc2 = st.columns([4, 1])
        with dc1:
            st.caption("Remove this contact from the team list (existing job assignments are kept).")
        with dc2:
            if st.button("Remove", key="del_contact_modal", use_container_width=True):
                st.session_state.contacts = [
                    c for c in st.session_state.get("contacts", []) if c["name"] != name
                ]
                save_data()
                st.session_state.assignee_modal_open = False
                st.rerun()
    if st.button("Close", use_container_width=True):
        st.session_state.assignee_modal_open = False
        st.rerun()

# ── Dashboard ─────────────────────────────────────────────────────────────────

def render_dashboard():
    """Programme-wide overview — the app's landing page."""
    all_jobs  = st.session_state.jobs
    active    = [j for j in all_jobs if j["status"] != "Archived"]

    total     = len(active)
    pending   = sum(1 for j in active if j["status"] == "Pending")
    in_prog   = sum(1 for j in active if j["status"] == "In Progress")
    completed = sum(1 for j in active if j["status"] == "Completed")
    n_overdue = sum(1 for j in active if _is_overdue(j))
    n_urgent  = sum(1 for j in active if effective_priority(j) == "Urgent" and not _is_overdue(j))

    # ── Metric tiles — compact, clickable, no separate button ────────
    dash_filter = st.session_state.get("dash_filter")
    metrics = [
        ("Total Active", total,     "total"),
        ("Pending",      pending,   "Pending"),
        ("In Progress",  in_prog,   "In Progress"),
        ("Completed",    completed, "Completed"),
        ("Overdue",      n_overdue, "overdue"),
        ("Urgent",       n_urgent,  "urgent"),
    ]
    cols = st.columns(6)
    for col, (label, count, key) in zip(cols, metrics):
        with col:
            is_active  = dash_filter == key
            active_cls = " mt-active" if is_active else ""
            # onclick walks up to the stVerticalBlock and clicks the hidden backing button
            js = (
                "(function(el){"
                "var v=el.closest('[data-testid=stVerticalBlock]');"
                "if(v){var b=v.querySelector('[data-testid=stButton] button');if(b)b.click();}"
                "})(this)"
            )
            st.markdown(
                f'<div class="metric-tile{active_cls}" onclick="{js}">'
                f'<div class="metric-count">{count}</div>'
                f'<div class="metric-label">{label}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            # Hidden zero-height Streamlit button — receives the click from JS above
            if st.button("", key=f"df_{key}", use_container_width=True):
                st.session_state.dash_filter         = None if is_active else key
                st.session_state.add_contact_open    = False
                st.session_state.assignee_modal_open = False
                st.rerun()

    # ── Pop-out list panel ────────────────────────────────────────
    if dash_filter:
        if dash_filter == "total":
            filtered = list(active)
            heading  = "All Active Jobs"
        elif dash_filter == "overdue":
            filtered = [j for j in active if _is_overdue(j)]
            heading  = "Overdue Jobs"
        elif dash_filter == "urgent":
            filtered = [j for j in active if effective_priority(j) == "Urgent" and not _is_overdue(j)]
            heading  = "Urgent Jobs"
        else:
            filtered = [j for j in active if j["status"] == dash_filter]
            heading  = f"{dash_filter} Jobs"

        filtered.sort(key=lambda j: (-PRIORITY_RANK[effective_priority(j)], j.get("dueDate") or "9999"))

        st.markdown(f"<br>", unsafe_allow_html=True)
        st.markdown(f"##### {heading} &nbsp; `{len(filtered)}`")
        if not filtered:
            st.info("No jobs in this category.")
        else:
            fcols = st.columns(3)
            for idx, j in enumerate(filtered):
                with fcols[idx % 3]:
                    render_active_card(j, "df")

        st.divider()

    # ── Two-column layout: Needs Attention + By Assignee ──────────
    da_col, ab_col = st.columns([3, 2])

    # ── Needs Attention ───────────────────────────────────────────
    with da_col:
        st.markdown("#### 🔴 Needs Attention")
        st.caption("Overdue and urgent jobs across all locations")

        needs = [
            j for j in active
            if _is_overdue(j) or effective_priority(j) == "Urgent"
        ]

        def _attn_sort(j):
            ov        = _is_overdue(j)
            days_past = (date.today() - date.fromisoformat(j["dueDate"])).days if ov and j.get("dueDate") else 0
            return (0 if ov else 1, -days_past, -PRIORITY_RANK[effective_priority(j)])

        needs.sort(key=_attn_sort)

        if not needs:
            st.success("✅ No overdue or urgent jobs — programme on track!")
        else:
            for j in needs:
                with st.container(border=True):
                    if _is_overdue(j):
                        st.markdown(
                            '<div style="background:#ef4444;height:3px;margin:-4px -8px 6px;'
                            'border-radius:1px 1px 0 0;"></div>',
                            unsafe_allow_html=True,
                        )
                    if st.button(j["title"], key=f"dash_open_{j['id']}", use_container_width=True):
                        st.session_state.dlg_job_id = j["id"]
                        st.session_state.dlg_open   = True
                        st.rerun()

                    if _is_overdue(j):
                        days_over = (date.today() - date.fromisoformat(j["dueDate"])).days
                        timing    = f"🔴 Overdue {days_over}d"
                    elif j.get("dueDate"):
                        try:
                            dl     = (date.fromisoformat(j["dueDate"]) - date.today()).days
                            timing = "Due today" if dl == 0 else f"Due in {dl}d"
                        except ValueError:
                            timing = ""
                    else:
                        timing = ""

                    eff_p = effective_priority(j)
                    st.markdown(
                        f"<p style='margin:1px 0;font-size:11px;color:#94a3b8;'>"
                        f"📍 {j['location']}"
                        + (f"  ·  👤 {j['assignedName']}" if j.get("assignedName") else "")
                        + (f"  ·  {timing}" if timing else "")
                        + "</p>",
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        badge(eff_p, PRIORITY_STYLES[eff_p]) + " " +
                        badge(j["status"], STATUS_STYLES[j["status"]]),
                        unsafe_allow_html=True,
                    )

    # ── By Assignee (contacts-based, each card clickable) ─────────
    with ab_col:
        st.markdown("#### 👤 By Assignee")

        contacts = st.session_state.get("contacts", list(DEFAULT_CONTACTS))
        for contact in contacts:
            cname   = contact["name"]
            c_email = contact.get("email", "")
            c_jobs  = [
                j for j in active
                if cname in job_assignees(j)
                or (c_email and c_email in {
                    e.strip() for e in j.get("assignedEmail", "").split(",") if e.strip()
                })
            ]
            ov   = sum(1 for j in c_jobs if _is_overdue(j))
            ug   = sum(1 for j in c_jobs if effective_priority(j) == "Urgent" and not _is_overdue(j))
            pend = sum(1 for j in c_jobs if j["status"] == "Pending")
            inp  = sum(1 for j in c_jobs if j["status"] == "In Progress")

            with st.container(border=True):
                nc1, nc2 = st.columns([3, 1])
                with nc1:
                    if st.button(
                        f"👤  {cname}",
                        key=f"asgn_btn_{contact['id']}",
                        use_container_width=True,
                    ):
                        st.session_state.dlg_open            = False
                        st.session_state.add_contact_open    = False
                        st.session_state.modal_assignee_name = cname
                        st.session_state.assignee_modal_open = True
                        st.rerun()
                    flags = []
                    if ov: flags.append(f"🔴 {ov} overdue")
                    if ug: flags.append(f"⚡ {ug} urgent")
                    if flags:
                        st.caption("  ·  ".join(flags))
                with nc2:
                    st.markdown(
                        f"<p style='font-size:12px;text-align:right;margin:0;padding-top:4px;'>"
                        f"<b>{len(c_jobs)}</b> jobs<br>"
                        f"<span style='color:#94a3b8;font-size:11px;'>{pend}P · {inp}IP</span></p>",
                        unsafe_allow_html=True,
                    )

        # ── Unassigned card ───────────────────────────────────────────
        unassigned_jobs = [j for j in active if not job_assignees(j)]
        if unassigned_jobs:
            ov_u   = sum(1 for j in unassigned_jobs if _is_overdue(j))
            ug_u   = sum(1 for j in unassigned_jobs if effective_priority(j) == "Urgent" and not _is_overdue(j))
            pend_u = sum(1 for j in unassigned_jobs if j["status"] == "Pending")
            inp_u  = sum(1 for j in unassigned_jobs if j["status"] == "In Progress")
            with st.container(border=True):
                nc1, nc2 = st.columns([3, 1])
                with nc1:
                    if st.button(
                        "👤  Unassigned",
                        key="asgn_btn_unassigned",
                        use_container_width=True,
                    ):
                        st.session_state.dlg_open            = False
                        st.session_state.add_contact_open    = False
                        st.session_state.modal_assignee_name = "__unassigned__"
                        st.session_state.assignee_modal_open = True
                        st.rerun()
                    flags_u = []
                    if ov_u: flags_u.append(f"🔴 {ov_u} overdue")
                    if ug_u: flags_u.append(f"⚡ {ug_u} urgent")
                    if flags_u:
                        st.caption("  ·  ".join(flags_u))
                with nc2:
                    st.markdown(
                        f"<p style='font-size:12px;text-align:right;margin:0;padding-top:4px;'>"
                        f"<b>{len(unassigned_jobs)}</b> jobs<br>"
                        f"<span style='color:#94a3b8;font-size:11px;'>{pend_u}P · {inp_u}IP</span></p>",
                        unsafe_allow_html=True,
                    )

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("+ Add Contact", key="dash_add_contact", use_container_width=True):
            st.session_state.dlg_open            = False
            st.session_state.assignee_modal_open = False
            st.session_state.add_contact_open    = True
            st.rerun()

# ── Dialog ────────────────────────────────────────────────────────────────────

@st.dialog("Job Details", width="large")
def job_dialog():
    job_id = st.session_state.get("dlg_job_id")
    job    = next((j for j in st.session_state.jobs if j["id"] == job_id), None) if job_id else None

    # ── Initialise dialog-local state (reset when a different job is opened) ──
    dlg_key = job_id or "new"
    if st.session_state.get("_dlg_key") != dlg_key:
        st.session_state._dlg_key     = dlg_key
        st.session_state.dlg_subtasks = list(job.get("subtasks", []) if job else [])

    title       = st.text_input("Title *", value=job["title"] if job else "")
    description = st.text_area("Description", value=job.get("description", "") if job else "", height=70)

    # ── Comments (always visible, right under Description) ────────
    st.markdown("<p style='font-size:14px;font-weight:500;margin:8px 0 4px;'>💬 Comments</p>", unsafe_allow_html=True)
    existing_comments = sorted(
        job.get("comments", []) if job else [],
        key=lambda c: c.get("ts", 0), reverse=True,
    )
    if existing_comments:
        rows_html = ""
        for c in existing_comments:
            ts_str = datetime.fromtimestamp(c["ts"] / 1000).strftime("%d %b, %H:%M") if c.get("ts") else ""
            rows_html += (
                f"<div style='padding:6px 0;border-bottom:1px solid #f1f5f9;'>"
                f"<p style='margin:0;font-size:12px;font-weight:600;color:#374151;'>"
                f"{c.get('author','Anonymous')}"
                f"<span style='font-weight:400;color:#94a3b8;'> · {ts_str}</span></p>"
                f"<p style='margin:2px 0 0;font-size:13px;color:#374151;'>{c.get('text','')}</p>"
                f"</div>"
            )
        st.markdown(
            f"<div style='max-height:200px;overflow-y:auto;border:1px solid #e2e8f0;"
            f"border-radius:6px;padding:4px 10px;margin-bottom:8px;'>{rows_html}</div>",
            unsafe_allow_html=True,
        )
    else:
        st.caption("No comments yet.")

    comm_c1, comm_c2 = st.columns([2, 3])
    with comm_c1:
        st.text_input("Your name", placeholder="Your name",
                      label_visibility="collapsed", key="dlg_comm_author")
    with comm_c2:
        st.text_input("Comment", placeholder="Write a comment…",
                      label_visibility="collapsed", key="dlg_comm_text")
    st.caption("Saved when you click Save below.")

    PRIORITIES = ["Low", "Medium", "High", "Urgent"]
    STATUSES   = ["Pending", "In Progress", "Completed"]

    c1, c2 = st.columns(2)
    with c1:
        cur_p    = job["priority"] if job else "Medium"
        priority = st.selectbox("Priority", PRIORITIES, index=PRIORITIES.index(cur_p))
    with c2:
        cur_s  = job["status"] if job and job["status"] in STATUSES else "Pending"
        status = st.selectbox("Status", STATUSES, index=STATUSES.index(cur_s))

    all_tabs = st.session_state.tabs_list
    if not job:
        default_loc = st.session_state.get("dlg_location", all_tabs[0])
        loc_idx     = all_tabs.index(default_loc) if default_loc in all_tabs else 0
    else:
        cur_loc  = job["location"] if job["location"] in all_tabs else all_tabs[0]
        loc_idx  = all_tabs.index(cur_loc)
    location = st.selectbox("Location", all_tabs, index=loc_idx)

    c3, c4 = st.columns(2)
    with c3:
        try:
            due_val = date.fromisoformat(job["dueDate"]) if job and job.get("dueDate") else None
        except ValueError:
            due_val = None
        due_date = st.date_input("Due Date", value=due_val)
    with c4:
        # ── Contacts multiselect for assignment ──────────────────────
        contacts    = st.session_state.get("contacts", list(DEFAULT_CONTACTS))
        contact_map = {c["id"]: c for c in contacts}

        # Pre-select contacts that match existing job assignments (by email, then name)
        if job:
            existing_emails = {e.strip() for e in job.get("assignedEmail", "").split(",") if e.strip()}
            existing_names  = set(job_assignees(job))
            preselected_ids = [
                c["id"] for c in contacts
                if (c.get("email") and c["email"] in existing_emails) or c["name"] in existing_names
            ]
        else:
            preselected_ids = []

        selected_ids = st.multiselect(
            "Assigned To",
            options=[c["id"] for c in contacts],
            default=preselected_ids,
            format_func=lambda cid: contact_map[cid]["name"],
            placeholder="Select team members…",
        )
        selected_contacts = [contact_map[cid] for cid in selected_ids]

    # ── Subtasks ──────────────────────────────────────────────────
    n_done  = sum(1 for s in st.session_state.dlg_subtasks if s.get("done"))
    n_total = len(st.session_state.dlg_subtasks)
    sub_label = f"✅ Subtasks ({n_done}/{n_total})" if n_total else "✅ Subtasks"
    with st.expander(sub_label, expanded=bool(n_total)):
        for sub in list(st.session_state.dlg_subtasks):
            sc1, sc2 = st.columns([10, 1])
            with sc1:
                st.checkbox(sub["text"], value=sub.get("done", False), key=f"sub_{sub['id']}")
            with sc2:
                if st.button("×", key=f"del_sub_{sub['id']}", help="Remove subtask"):
                    st.session_state.dlg_subtasks = [
                        s for s in st.session_state.dlg_subtasks if s["id"] != sub["id"]
                    ]
                    st.rerun()

        na1, na2 = st.columns([5, 1])
        with na1:
            new_sub_text = st.text_input(
                "New subtask", placeholder="Add a subtask…",
                label_visibility="collapsed", key="dlg_new_sub_text",
            )
        with na2:
            if st.button("+ Add", key="dlg_add_sub_btn", use_container_width=True):
                t = (st.session_state.get("dlg_new_sub_text") or "").strip()
                if t:
                    st.session_state.dlg_subtasks.append({"id": gen_id(), "text": t, "done": False})
                    st.rerun()

    # ── Save / Cancel ─────────────────────────────────────────────
    sc, cc = st.columns(2)
    with sc:
        save   = st.button("Save", type="primary", use_container_width=True)
    with cc:
        cancel = st.button("Cancel", use_container_width=True)

    if save:
        if not title.strip():
            st.error("Title is required.")
            return

        # Collect subtask done-state from widget session state
        final_subtasks = [
            {**s, "done": st.session_state.get(f"sub_{s['id']}", s.get("done", False))}
            for s in st.session_state.dlg_subtasks
        ]

        # Append new comment if one was typed
        final_comments = list(existing_comments)
        new_text = (st.session_state.get("dlg_comm_text") or "").strip()
        if new_text:
            final_comments.append({
                "id":     gen_id(),
                "text":   new_text,
                "author": (st.session_state.get("dlg_comm_author") or "Anonymous").strip(),
                "ts":     now_ms(),
            })

        assigned_name  = ", ".join(c["name"] for c in selected_contacts)
        assigned_email = ", ".join(c["email"] for c in selected_contacts if c.get("email"))

        upsert_job(
            {
                "title": title.strip(), "description": description, "priority": priority,
                "status": status, "location": location,
                "dueDate": str(due_date) if due_date else "",
                "assignedName": assigned_name, "assignedEmail": assigned_email,
                "subtasks": final_subtasks, "comments": final_comments,
            },
            job_id=job_id,
        )
        st.session_state.dlg_open   = False
        st.session_state.dlg_job_id = None
        st.session_state._dlg_key   = None
        st.rerun()

    if cancel:
        st.session_state.dlg_open   = False
        st.session_state.dlg_job_id = None
        st.session_state._dlg_key   = None
        st.rerun()

# ── Card helpers ──────────────────────────────────────────────────────────────

def badge(text: str, style: dict) -> str:
    cls = "badge badge-" + text.lower().replace(" ", "-")
    return (
        f'<span class="{cls}" style="background:{style["bg"]};color:{style["color"]};'
        f'padding:2px 10px;border-radius:4px;font-size:11px;font-weight:600;'
        f'letter-spacing:0.03em;display:inline-block;margin:2px;">{text.upper()}</span>'
    )

def render_active_card(job: dict, lk: str):
    is_ov = _is_overdue(job)
    with st.container(border=True):
        if is_ov:
            st.markdown(
                '<div style="background:#ef4444;height:3px;'
                'margin:-4px -8px 6px;border-radius:1px 1px 0 0;"></div>',
                unsafe_allow_html=True,
            )

        # Title — full-width button styled as text (CSS targets this direct child)
        if st.button(job["title"], key=f"open_{lk}_{job['id']}", use_container_width=True):
            st.session_state.dlg_job_id = job["id"]
            st.session_state.dlg_open   = True
            st.rerun()

        meta = []
        if job.get("dueDate"):
            try:
                days_left = (date.fromisoformat(job["dueDate"]) - date.today()).days
                if days_left < 0:
                    meta.append(f"Overdue by {-days_left}d")
                elif days_left == 0:
                    meta.append("Due today")
                elif days_left == 1:
                    meta.append("Due tomorrow")
                else:
                    meta.append(f"Due {job['dueDate']}")
            except ValueError:
                meta.append(f"Due {job['dueDate']}")
        if job.get("assignedName"):
            meta.append(f"Assigned to {job['assignedName']}")
        if job["status"] == "Completed" and job.get("completedAt"):
            ms_left = job["completedAt"] + 48 * 3_600_000 - now_ms()
            if ms_left > 0:
                h = int(ms_left / 3_600_000)
                m = int((ms_left % 3_600_000) / 60_000)
                meta.append(f"Archives in {h}h {m}m")
        # Comment count badge
        n_comments = len(job.get("comments", []))
        if n_comments:
            meta.append(f"💬 {n_comments}")

        eff_p     = effective_priority(job)
        meta_html = f"<p style='font-size:11px;color:#94a3b8;margin:1px 0 0;'>{'  ·  '.join(meta)}</p>" if meta else ""
        desc_html = f"<p style='font-size:11px;color:#374151;margin:1px 0 0;'>{job['description']}</p>" if job.get("description") else ""

        st.markdown(
            badge(eff_p, PRIORITY_STYLES[eff_p]) + " " +
            badge(job["status"], STATUS_STYLES[job["status"]]) +
            meta_html + desc_html,
            unsafe_allow_html=True,
        )

        # Status selector + delete in bottom row
        if job["status"] != "Completed":
            bc1, bc2 = st.columns([4, 1])
            with bc1:
                opts = ["Pending", "In Progress", "Completed"]
                cur  = opts.index(job["status"]) if job["status"] in opts else 0
                sel  = st.selectbox(
                    "Status", opts, index=cur,
                    key=f"s_{lk}_{job['id']}", label_visibility="collapsed",
                )
                if sel != job["status"]:
                    set_status(job["id"], sel)
                    st.rerun()
            with bc2:
                if st.button("🗑", key=f"d_{lk}_{job['id']}", help="Delete", use_container_width=True):
                    remove_job(job["id"])
                    st.rerun()
        else:
            _, bc2 = st.columns([5, 1])
            with bc2:
                if st.button("🗑", key=f"d_{lk}_{job['id']}", help="Delete", use_container_width=True):
                    remove_job(job["id"])
                    st.rerun()


def render_archived_card(job: dict, lk: str):
    with st.container(border=True):
        tc, rc = st.columns([4, 1])
        with tc:
            st.markdown(f"**{job['title']}**")
        with rc:
            if st.button("Restore", key=f"r_{lk}_{job['id']}", help="Restore to Pending", use_container_width=True):
                restore_job(job["id"])
                st.rerun()
        st.markdown(
            badge(job["priority"], PRIORITY_STYLES[job["priority"]]) + " " +
            badge("Archived", STATUS_STYLES["Archived"]),
            unsafe_allow_html=True,
        )
        meta = []
        if job.get("assignedName"):
            meta.append(f"Assigned to {job['assignedName']}")
        n_comments = len(job.get("comments", []))
        if n_comments:
            meta.append(f"💬 {n_comments}")
        if meta:
            st.caption("  ·  ".join(meta))


def render_kanban(location: str, view: str):
    lk       = location.replace(" ", "_").lower()
    tab_jobs = [j for j in st.session_state.jobs if j["location"] == location]

    def sort_key(j):
        due = j.get("dueDate") or "9999-99-99"
        return (-PRIORITY_RANK[effective_priority(j)], due, j.get("createdAt", 0))

    if view == "Active":
        pool = [j for j in tab_jobs if j["status"] != "Archived"]
        cols = st.columns(3)
        for i, col_name in enumerate(["Pending", "In Progress", "Completed"]):
            group = sorted([j for j in pool if j["status"] == col_name], key=sort_key)
            with cols[i]:
                st.markdown(f"#### {col_name} &nbsp; `{len(group)}`")
                if not group:
                    st.caption("No jobs")
                for job in group:
                    render_active_card(job, lk)
    else:
        pool = [j for j in tab_jobs if j["status"] == "Archived"]
        st.markdown(f"#### Archived &nbsp; `{len(pool)}`")
        if not pool:
            st.caption("No archived jobs")
        else:
            cols = st.columns(3)
            for idx, job in enumerate(pool):
                with cols[idx % 3]:
                    render_archived_card(job, lk)

# ── Session state init ────────────────────────────────────────────────────────

if "initialized" not in st.session_state:
    jobs, tabs, archived_tabs, contacts = load_data()
    st.session_state.update({
        "jobs":                  jobs,
        "tabs_list":             tabs,
        "archived_tabs":         archived_tabs,
        "contacts":              contacts,
        "dlg_open":              False,
        "dlg_job_id":            None,
        "dlg_location":          tabs[0] if tabs else DEFAULT_TABS[0],
        "assignee_modal_open":   False,
        "modal_assignee_name":   "",
        "add_contact_open":      False,
        "dash_filter":           None,
        "initialized":           True,
    })

# Guard: patch any keys that may be absent in sessions created before these features
if "contacts"             not in st.session_state:
    st.session_state.contacts             = list(DEFAULT_CONTACTS)
if "assignee_modal_open"  not in st.session_state:
    st.session_state.assignee_modal_open  = False
if "modal_assignee_name"  not in st.session_state:
    st.session_state.modal_assignee_name  = ""
if "add_contact_open"     not in st.session_state:
    st.session_state.add_contact_open     = False
if "dash_filter"          not in st.session_state:
    st.session_state.dash_filter          = None

# If load_data found local changes newer than the cloud, push them up now.
if st.session_state.pop("_resync_needed", False):
    save_data()

auto_archive()
send_due_reminders()

# ── Show deferred toasts ──────────────────────────────────────────────────────

if "email_toast" in st.session_state:
    st.toast(st.session_state.pop("email_toast"))
if "email_toast_error" in st.session_state:
    st.error(st.session_state.pop("email_toast_error"))

# ── CSS ───────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap');

html, body, [class*="css"] { font-family: 'DM Sans', sans-serif !important; }
.block-container { padding-top: 5rem !important; max-width: 1400px !important; }
#MainMenu, footer, header { visibility: hidden; }

.app-header { display: flex; align-items: center; gap: 12px; margin-bottom: 0; }
.app-title  { font-family: 'DM Sans', sans-serif; font-size: 20px; font-weight: 600; color: #0f172a; letter-spacing: -0.02em; margin: 0; }
.app-subtitle { font-size: 13px; color: #94a3b8; font-weight: 400; }

hr { border-color: #e2e8f0 !important; margin: 0.75rem 0 !important; }

.stTabs [data-baseweb="tab-list"] { gap: 0; border-bottom: 1px solid #e2e8f0; background: transparent; }
.stTabs [data-baseweb="tab"] {
    font-family: 'DM Sans', sans-serif !important; font-size: 13px !important; font-weight: 500 !important;
    color: #64748b !important; padding: 10px 18px !important; border-radius: 0 !important;
    border-bottom: 2px solid transparent !important;
}
.stTabs [aria-selected="true"] { color: #0f172a !important; border-bottom: 2px solid #0f172a !important; background: transparent !important; }
.stTabs [data-baseweb="tab-highlight"] { display: none !important; }
.stTabs [data-baseweb="tab-border"]    { display: none !important; }

div[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 10px !important;
    border-color: #e8ecf0 !important;
    padding: 0px !important;
    margin-bottom: 8px !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05), 0 1px 2px rgba(0,0,0,0.04) !important;
    transition: box-shadow 0.15s ease, transform 0.15s ease !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:hover {
    box-shadow: 0 4px 12px rgba(0,0,0,0.08), 0 2px 4px rgba(0,0,0,0.05) !important;
    transform: translateY(-1px) !important;
}
div[data-testid="stVerticalBlockBorderWrapper"] > div { padding: 12px 14px !important; }
div[data-testid="stVerticalBlockBorderWrapper"] p { margin: 0 !important; line-height: 1.4 !important; }
div[data-testid="stVerticalBlockBorderWrapper"] .stSelectbox > div { min-height: 28px !important; }
div[data-testid="stVerticalBlockBorderWrapper"] .stSelectbox [data-baseweb="select"] > div {
    padding-top: 2px !important; padding-bottom: 2px !important; min-height: 28px !important; font-size: 11px !important;
}

.stButton button {
    font-family: 'DM Sans', sans-serif !important; font-size: 12px !important; font-weight: 500 !important;
    border-radius: 8px !important; letter-spacing: 0.01em !important;
    padding: 2px 10px !important; height: 30px !important; min-height: 30px !important;
    transition: all 0.12s ease !important;
}
.stButton button[kind="primary"]         { background: #0f172a !important; border: none !important; color: white !important; box-shadow: 0 1px 3px rgba(15,23,42,0.25) !important; }
.stButton button[kind="primary"]:hover   { background: #1e293b !important; box-shadow: 0 3px 8px rgba(15,23,42,0.3) !important; transform: translateY(-1px) !important; }
.stButton button[kind="secondary"]       { background: #f8fafc !important; border: 1px solid #e2e8f0 !important; color: #64748b !important; filter: grayscale(100%) !important; }
.stButton button[kind="secondary"]:hover { background: #f1f5f9 !important; color: #374151 !important; border-color: #cbd5e1 !important; }

.stTextInput input, .stTextArea textarea, .stSelectbox select {
    font-family: 'DM Sans', sans-serif !important; font-size: 13px !important;
    border-radius: 8px !important; border-color: #e2e8f0 !important;
}
.stSelectbox [data-baseweb="select"] { border-radius: 8px !important; }

h4 { font-size: 10px !important; font-weight: 700 !important; color: #94a3b8 !important; text-transform: uppercase !important; letter-spacing: 0.10em !important; margin-bottom: 10px !important; }
/* Pill badges */
.badge { border-radius: 20px !important; }

/* Sync status badge (header) */
.sync-badge {
    display: inline-flex; align-items: center;
    font-size: 11px; font-weight: 600; letter-spacing: 0.02em;
    padding: 4px 12px; border-radius: 20px; white-space: nowrap;
    border: 1px solid transparent;
}
.sync-badge.sync-ok   { background: #ecfdf5; color: #15803d; border-color: #bbf7d0; }
.sync-badge.sync-warn { background: #fffbeb; color: #b45309; border-color: #fde68a; }
.sync-badge.sync-err  { background: #fef2f2; color: #b91c1c; border-color: #fecaca; }
.stCaptionContainer, [data-testid="stCaptionContainer"] { color: #94a3b8 !important; font-size: 12px !important; }
[data-testid="stToast"] { font-family: 'DM Sans', sans-serif !important; font-size: 13px !important; }
.stRadio label { font-family: 'DM Sans', sans-serif !important; font-size: 13px !important; font-weight: 500 !important; }
code { font-family: 'DM Mono', monospace !important; font-size: 11px !important; background: #f1f5f9 !important; color: #475569 !important; border-radius: 4px !important; padding: 1px 6px !important; }

/* ── Card title buttons — look like bold text, not a button ───────── */
/* Broad descendant selector so intermediate wrapper changes don't break it */
div[data-testid="stVerticalBlockBorderWrapper"] .stButton > button {
    background: none !important;
    border: none !important;
    box-shadow: none !important;
    padding: 1px 0 4px !important;
    height: auto !important;
    min-height: auto !important;
    text-align: left !important;
    font-size: 13px !important;
    font-weight: 600 !important;
    color: #0f172a !important;
    width: 100% !important;
    justify-content: flex-start !important;
    letter-spacing: -0.01em !important;
    line-height: 1.4 !important;
    white-space: normal !important;
    word-break: break-word !important;
    transform: none !important;
}
div[data-testid="stVerticalBlockBorderWrapper"] .stButton > button:hover {
    color: #2563eb !important;
    background: none !important;
    text-decoration: underline !important;
    transform: none !important;
}

/* Restore normal button style for ACTION buttons in the bottom row
   (delete 🗑 and any column-nested buttons — they're inside stHorizontalBlock) */
div[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stHorizontalBlock"] .stButton > button {
    background: #f8fafc !important;
    border: 1px solid #e2e8f0 !important;
    box-shadow: none !important;
    height: 30px !important;
    min-height: 30px !important;
    padding: 2px 10px !important;
    text-align: center !important;
    font-size: 12px !important;
    font-weight: 500 !important;
    color: #64748b !important;
    justify-content: center !important;
    letter-spacing: 0.01em !important;
    line-height: normal !important;
    white-space: nowrap !important;
    word-break: normal !important;
    border-radius: 8px !important;
}
div[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stHorizontalBlock"] .stButton > button:hover {
    background: #f1f5f9 !important;
    color: #374151 !important;
    text-decoration: none !important;
    border-color: #cbd5e1 !important;
}

/* ── Metric tiles ────────────────────────────────────────────────── */
.metric-tile {
    text-align: center;
    padding: 10px 6px 8px;
    border-radius: 10px;
    background: #f8fafc;
    border: 1px solid #e8ecf0;
    cursor: pointer;
    user-select: none;
    -webkit-user-select: none;
    transition: box-shadow 0.15s ease, transform 0.15s ease;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.metric-tile:hover {
    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    transform: translateY(-1px);
}
.metric-tile.mt-active {
    border: 2px solid #2563eb;
    background: #eff6ff;
}
.metric-count {
    font-size: 22px;
    font-weight: 700;
    color: #0f172a;
    line-height: 1.1;
}
.metric-label {
    font-size: 10px;
    color: #64748b;
    margin-top: 3px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}

/* Collapse the hidden backing Streamlit buttons for metric tiles */
[data-testid="stVerticalBlock"]:has(.metric-tile) > [data-testid="element-container"] + [data-testid="element-container"] {
    margin: 0 !important;
    padding: 0 !important;
    line-height: 0 !important;
}
[data-testid="stVerticalBlock"]:has(.metric-tile) > [data-testid="element-container"] + [data-testid="element-container"] button {
    height: 0 !important;
    min-height: 0 !important;
    padding: 0 !important;
    margin: 0 !important;
    border: none !important;
    background: transparent !important;
    box-shadow: none !important;
    overflow: hidden !important;
    font-size: 0 !important;
    line-height: 0 !important;
    display: block !important;
    pointer-events: none !important;
}

/* ── Dark mode (mirrors OS preference) ─────────────────────────────── */
@media (prefers-color-scheme: dark) {
    /* Metric tiles */
    .metric-tile { background: #262626; border-color: #2e2e2e; box-shadow: 0 1px 4px rgba(0,0,0,0.3); }
    .metric-tile:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.4); }
    .metric-tile.mt-active { background: #1a2744; border-color: #2563eb; }
    .metric-count { color: #ececec; }
    .metric-label { color: #6b7280; }

    /* App background */
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"],
    section[data-testid="stMain"] > div { background-color: #1e1e1e !important; }

    /* Block container */
    .block-container { background-color: #1e1e1e !important; }

    /* General text */
    html, body, p, span, li, label, div { color: #ececec; }
    [class*="css"] { color: #ececec; }

    /* App header */
    .app-title    { color: #ececec !important; }
    .app-subtitle { color: #9ca3af !important; }

    /* Column headings (Pending / In Progress / Completed / Archived) */
    h4 { color: #9ca3af !important; }

    /* Horizontal rules */
    hr { border-color: #333333 !important; }

    /* Job cards */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-color: #2e2e2e !important;
        background-color: #262626 !important;
        box-shadow: 0 1px 4px rgba(0,0,0,0.3), 0 1px 2px rgba(0,0,0,0.2) !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:hover {
        box-shadow: 0 6px 16px rgba(0,0,0,0.4), 0 2px 6px rgba(0,0,0,0.3) !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] > div { background-color: #262626 !important; }

    /* Priority & status badges — override inline styles so they're readable */
    .badge-low         { background: #1e3a5f !important; color: #93c5fd !important; }
    .badge-medium      { background: #431407 !important; color: #fdba74 !important; }
    .badge-high        { background: #3b0764 !important; color: #d8b4fe !important; }
    .badge-urgent      { background: #450a0a !important; color: #fca5a5 !important; }
    .badge-pending     { background: #4a044e !important; color: #f0abfc !important; }
    .badge-in-progress { background: #431407 !important; color: #fdba74 !important; }
    .badge-completed   { background: #052e16 !important; color: #86efac !important; }
    .badge-archived    { background: #1e293b !important; color: #94a3b8 !important; }

    /* Sync status badge — dark variants */
    .sync-badge.sync-ok   { background: #052e16 !important; color: #86efac !important; border-color: #14532d !important; }
    .sync-badge.sync-warn { background: #451a03 !important; color: #fcd34d !important; border-color: #78350f !important; }
    .sync-badge.sync-err  { background: #450a0a !important; color: #fca5a5 !important; border-color: #7f1d1d !important; }

    /* Card title buttons in dark mode */
    div[data-testid="stVerticalBlockBorderWrapper"] .stButton > button {
        color: #ececec !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] .stButton > button:hover {
        color: #93c5fd !important;
    }
    /* Restore action buttons in dark mode */
    div[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stHorizontalBlock"] .stButton > button {
        background: #2d2d2d !important;
        border: 1px solid #3d3d3d !important;
        color: #9ca3af !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stHorizontalBlock"] .stButton > button:hover {
        background: #333333 !important;
        color: #ececec !important;
        border-color: #4d4d4d !important;
        text-decoration: none !important;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        border-bottom: 1px solid #333333 !important;
        background: transparent !important;
    }
    .stTabs [data-baseweb="tab"]   { color: #9ca3af !important; }
    .stTabs [aria-selected="true"] { color: #ececec !important; border-bottom-color: #ececec !important; }

    /* Text inputs & text areas */
    .stTextInput input, .stTextArea textarea {
        background-color: #2d2d2d !important;
        border-color: #3d3d3d !important;
        color: #ececec !important;
    }
    .stTextInput input::placeholder, .stTextArea textarea::placeholder { color: #6b7280 !important; }

    /* Selectboxes */
    .stSelectbox [data-baseweb="select"] > div,
    [data-baseweb="select"] > div {
        background-color: #2d2d2d !important;
        border-color: #3d3d3d !important;
        color: #ececec !important;
    }
    [data-baseweb="popover"], [data-baseweb="menu"] {
        background-color: #2d2d2d !important;
    }
    [data-baseweb="option"]:hover { background-color: #3d3d3d !important; }

    /* Buttons */
    .stButton button[kind="primary"] {
        background: #2563eb !important;
        border: none !important;
        color: #ffffff !important;
        box-shadow: 0 1px 4px rgba(37,99,235,0.35) !important;
    }
    .stButton button[kind="primary"]:hover  {
        background: #1d4ed8 !important;
        box-shadow: 0 4px 10px rgba(37,99,235,0.4) !important;
    }
    .stButton button[kind="secondary"] {
        background: #2d2d2d !important;
        border: 1px solid #3d3d3d !important;
        color: #9ca3af !important;
        filter: none !important;
    }
    .stButton button[kind="secondary"]:hover {
        background: #333333 !important;
        color: #ececec !important;
        border-color: #4d4d4d !important;
    }

    /* Captions / muted text */
    .stCaptionContainer, [data-testid="stCaptionContainer"] { color: #6b7280 !important; }

    /* Inline code badges */
    code {
        background: #2d2d2d !important;
        color: #a5b4fc !important;
    }

    /* Toast notifications */
    [data-testid="stToast"] {
        background-color: #262626 !important;
        color: #ececec !important;
    }

    /* Dialog / modal */
    [role="dialog"], [data-testid="stDialog"],
    [data-testid="stDialog"] > div,
    [data-testid="stDialog"] [data-testid="stVerticalBlock"] {
        background-color: #262626 !important;
    }
    [data-testid="stDialogDismissButton"] svg { stroke: #9ca3af !important; }

    /* Radio buttons */
    .stRadio label { color: #ececec !important; }

    /* Markdown text */
    [data-testid="stMarkdownContainer"] p,
    [data-testid="stMarkdownContainer"] span { color: #ececec !important; }
    [data-testid="stMarkdownContainer"] strong { color: #f0f0f0 !important; }
}

/* ── Mobile responsive ──────────────────────────────────────────── */
@media (max-width: 768px) {

    /* Tighten page padding */
    .block-container {
        padding: 2.5rem 0.5rem 1rem !important;
        max-width: 100% !important;
    }

    /* Columns: wrap into a 2-wide grid.
       Metric tiles (6 cols) → 3 rows × 2  ✓
       Kanban (3 cols)        → 2 + 1 rows  ✓
       Dashboard side cols    → stacked     ✓  */
    [data-testid="stHorizontalBlock"] {
        flex-wrap: wrap !important;
        gap: 6px !important;
    }
    [data-testid="column"] {
        flex: 1 1 calc(50% - 6px) !important;
        min-width: calc(50% - 6px) !important;
        width: calc(50% - 6px) !important;
    }

    /* Tab bar: allow horizontal scroll, hide the scrollbar */
    .stTabs [data-baseweb="tab-list"] {
        overflow-x: auto !important;
        -webkit-overflow-scrolling: touch !important;
        scrollbar-width: none !important;
        flex-wrap: nowrap !important;
    }
    .stTabs [data-baseweb="tab-list"]::-webkit-scrollbar { display: none !important; }
    .stTabs [data-baseweb="tab"] {
        font-size: 12px !important;
        padding: 8px 12px !important;
        white-space: nowrap !important;
    }

    /* Bigger touch targets for all buttons */
    .stButton button {
        min-height: 44px !important;
        font-size: 14px !important;
        padding: 8px 12px !important;
        height: auto !important;
    }

    /* Card title buttons stay text-like but easier to tap */
    div[data-testid="stVerticalBlockBorderWrapper"] .stButton > button {
        font-size: 14px !important;
        padding: 6px 0 8px !important;
        min-height: 36px !important;
    }
    /* Keep action buttons normal on mobile */
    div[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stHorizontalBlock"] .stButton > button {
        font-size: 13px !important;
        padding: 8px 12px !important;
        min-height: 44px !important;
        height: 44px !important;
        white-space: nowrap !important;
        word-break: normal !important;
        text-align: center !important;
    }

    /* Dialogs: fill the screen width */
    [data-testid="stDialog"] > div {
        max-width: 96vw !important;
        width: 96vw !important;
        margin: 0 auto !important;
    }

    /* Selectboxes: full width, taller hit area */
    .stSelectbox [data-baseweb="select"] > div {
        min-height: 44px !important;
        font-size: 14px !important;
    }

    /* Text inputs: larger on mobile */
    .stTextInput input, .stTextArea textarea {
        font-size: 16px !important; /* prevents iOS zoom-on-focus */
        min-height: 44px !important;
    }

    /* Metric tile numbers: slightly smaller so they fit 2-wide */
    .block-container div[style*="font-size:26px"] {
        font-size: 22px !important;
    }

    /* Kanban column headers */
    h4 { font-size: 11px !important; }
}

/* ── Phone-only — truly tiny screens (≤400px) ───────────────────── */
@media (max-width: 400px) {
    /* Single-column everything */
    [data-testid="column"] {
        flex: 1 1 100% !important;
        min-width: 100% !important;
        width: 100% !important;
    }
}
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────

# Sync status badge (reflects the last load/save against Supabase)
_sb_status = st.session_state.get("sb_status", "local")
_sb_msg    = (st.session_state.get("sb_message", "") or "").replace('"', "'")
_ago       = fmt_ago(st.session_state.get("last_synced"))
if _sb_status == "synced":
    _badge_cls, _badge_icon, _badge_txt = "sync-ok",   "☁", f"Synced{(' · ' + _ago) if _ago else ''}"
elif _sb_status == "error":
    _badge_cls, _badge_icon, _badge_txt = "sync-err",  "⚠", "Cloud save failed — local only"
else:  # local
    _badge_cls, _badge_icon, _badge_txt = "sync-warn", "⚠", "Local only — not in cloud"

st.markdown(
    f"""
<div class="app-header" style="justify-content:space-between;width:100%;">
    <div>
        <div class="app-title">Jobs Manager</div>
        <div class="app-subtitle">NZL 49er Programme</div>
    </div>
    <div class="sync-badge {_badge_cls}" title="{_sb_msg}">
        <span style="font-size:13px;">{_badge_icon}</span>&nbsp;{_badge_txt}
    </div>
</div>
""",
    unsafe_allow_html=True,
)
# Surface a loud message when not fully synced
if _sb_status == "error":
    st.error(_sb_msg)
elif _sb_status == "local" and st.session_state.get("sync_source") != "seed":
    st.warning(_sb_msg)

st.markdown("---")

# ── Location tabs ─────────────────────────────────────────────────────────────

n_overdue_all = sum(1 for j in st.session_state.jobs if _is_overdue(j))
tab_labels = ["Dashboard"]
for loc in st.session_state.tabs_list:
    n = sum(1 for j in st.session_state.jobs if j["location"] == loc and j["status"] != "Archived")
    tab_labels.append(f"{loc}  ({n})")
tab_labels.append("+ New Tab")
archived_count = len(st.session_state.get("archived_tabs", []))
tab_labels.append(f"Archived Tabs  ({archived_count})" if archived_count else "Archived Tabs")

loc_tabs = st.tabs(tab_labels)

# ── Dashboard tab ─────────────────────────────────────────────────────────────
with loc_tabs[0]:
    render_dashboard()

# ── Location tabs (offset +1 for the dashboard tab) ──────────────────────────
for i, tab_ctx in enumerate(loc_tabs[1:-2]):
    with tab_ctx:
        loc = st.session_state.tabs_list[i]

        vc, _, ac, arc, dc = st.columns([2, 2.5, 1.5, 1.5, 1.5])
        with vc:
            view = st.radio(
                "View", ["Active", "Archive"],
                horizontal=True, key=f"view_{loc}", label_visibility="collapsed",
            )
        with ac:
            if st.button("+ Add Job", key=f"add_{loc}", type="primary", use_container_width=True):
                st.session_state.dlg_job_id   = None
                st.session_state.dlg_location = loc
                st.session_state.dlg_open     = True
                st.rerun()
        with arc:
            if st.button("Archive Tab", key=f"arc_tab_{loc}", use_container_width=True):
                for j in st.session_state.jobs:
                    if j["location"] == loc:
                        j["status"] = "Archived"
                st.session_state.tabs_list = [t for t in st.session_state.tabs_list if t != loc]
                st.session_state.archived_tabs.append(loc)
                save_data()
                st.rerun()
        with dc:
            if st.button("Delete Tab", key=f"del_tab_{loc}", use_container_width=True):
                st.session_state.tabs_list = [t for t in st.session_state.tabs_list if t != loc]
                st.session_state.jobs      = [j for j in st.session_state.jobs if j["location"] != loc]
                save_data()
                st.rerun()

        with st.expander("Tab Settings"):
            tabs_list = st.session_state.tabs_list
            idx       = tabs_list.index(loc)

            st.markdown("<p style='font-size:12px;font-weight:600;color:#475569;margin-bottom:2px;'>Rename Tab</p>", unsafe_allow_html=True)
            rc1, rc2 = st.columns([3, 1])
            with rc1:
                new_name_val = st.text_input(
                    "New name", value=loc, key=f"rename_{loc}",
                    label_visibility="collapsed", placeholder="New tab name"
                )
            with rc2:
                if st.button("Save", key=f"rename_save_{loc}", type="primary", use_container_width=True):
                    n = new_name_val.strip()
                    if not n:
                        st.warning("Name cannot be empty.")
                    elif n != loc and n in tabs_list:
                        st.warning(f"'{n}' already exists.")
                    elif n != loc:
                        st.session_state.tabs_list[idx] = n
                        for j in st.session_state.jobs:
                            if j["location"] == loc:
                                j["location"] = n
                        save_data()
                        st.rerun()

            st.markdown("<p style='font-size:12px;font-weight:600;color:#475569;margin:8px 0 2px;'>Reorder Tab</p>", unsafe_allow_html=True)
            oc1, oc2, oc3 = st.columns([1, 1, 4])
            with oc1:
                if st.button("← Left", key=f"move_left_{loc}", use_container_width=True, disabled=(idx == 0)):
                    tabs_list[idx], tabs_list[idx - 1] = tabs_list[idx - 1], tabs_list[idx]
                    save_data()
                    st.rerun()
            with oc2:
                if st.button("Right →", key=f"move_right_{loc}", use_container_width=True, disabled=(idx == len(tabs_list) - 1)):
                    tabs_list[idx], tabs_list[idx + 1] = tabs_list[idx + 1], tabs_list[idx]
                    save_data()
                    st.rerun()
            with oc3:
                st.markdown(
                    f"<p style='font-size:11px;color:#94a3b8;margin:6px 0 0;'>Position {idx + 1} of {len(tabs_list)}</p>",
                    unsafe_allow_html=True,
                )

        st.divider()
        render_kanban(loc, view)

# ── New Tab ───────────────────────────────────────────────────────────────────

with loc_tabs[-2]:
    st.markdown("### Add a new location tab")
    new_name = st.text_input("Tab name", placeholder="e.g. Spare Parts", label_visibility="collapsed", key="new_tab_input")
    if st.button("Create Tab", type="primary"):
        n = new_name.strip()
        if not n:
            st.warning("Enter a tab name.")
        elif n in st.session_state.tabs_list:
            st.warning(f"'{n}' already exists.")
        else:
            st.session_state.tabs_list.append(n)
            save_data()
            st.rerun()

# ── Archived Tabs ─────────────────────────────────────────────────────────────

with loc_tabs[-1]:
    st.markdown("### Archived Tabs")
    archived = st.session_state.get("archived_tabs", [])
    if not archived:
        st.caption("No archived tabs.")
    else:
        for atab in archived:
            job_count = sum(1 for j in st.session_state.jobs if j["location"] == atab)
            ac1, ac2, ac3 = st.columns([4, 1.5, 1.5])
            with ac1:
                st.markdown(f"**{atab}** &nbsp; <span style='font-size:12px;color:#94a3b8;'>{job_count} jobs</span>", unsafe_allow_html=True)
            with ac2:
                if st.button("Restore", key=f"restore_tab_{atab}", type="primary", use_container_width=True):
                    st.session_state.archived_tabs = [t for t in st.session_state.archived_tabs if t != atab]
                    st.session_state.tabs_list.append(atab)
                    save_data()
                    st.rerun()
            with ac3:
                if st.button("Delete", key=f"perm_del_tab_{atab}", use_container_width=True):
                    st.session_state.archived_tabs = [t for t in st.session_state.archived_tabs if t != atab]
                    st.session_state.jobs          = [j for j in st.session_state.jobs if j["location"] != atab]
                    save_data()
                    st.rerun()
            st.divider()

# ── Open dialogs if flagged ───────────────────────────────────────────────────

if st.session_state.get("dlg_open"):
    job_dialog()
elif st.session_state.get("add_contact_open"):
    add_contact_dialog()
elif st.session_state.get("assignee_modal_open"):
    assignee_jobs_modal()
