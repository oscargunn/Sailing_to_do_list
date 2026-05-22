import streamlit as st
import json
import os
import random
import string
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, date

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

DEFAULT_TABS = ["Europe", "NZ General", "LA Boat", "R1047", "Rigs", "New Boat"]
STORAGE_FILE = "jobs_data.json"

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
        cfg = st.secrets["email"]
        # Support multiple comma-separated addresses
        recipients = [a.strip() for a in to_addr.split(",") if a.strip()]
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"]    = cfg["sender"]
        msg["To"]      = ", ".join(recipients)
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
            s.login(cfg["sender"], cfg["password"])
            s.sendmail(cfg["sender"], recipients, msg.as_string())
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

# ── Data layer ────────────────────────────────────────────────────────────────

def now_ms() -> float:
    return datetime.now().timestamp() * 1000

def gen_id() -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=10))

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
        }
        for i, r in enumerate(RAW_SEED)
    ]

def load_data() -> tuple:
    if os.path.exists(STORAGE_FILE):
        try:
            with open(STORAGE_FILE) as f:
                d = json.load(f)
            return d.get("jobs", make_seed()), d.get("tabs", list(DEFAULT_TABS)), d.get("archived_tabs", [])
        except Exception:
            pass
    return make_seed(), list(DEFAULT_TABS), []

def save_data():
    with open(STORAGE_FILE, "w") as f:
        json.dump({
            "jobs": st.session_state.jobs,
            "tabs": st.session_state.tabs_list,
            "archived_tabs": st.session_state.archived_tabs,
        }, f, indent=2)

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
            j["status"]      = "Pending"
            j["completedAt"] = None
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
        new_job = {**data, "id": gen_id(), "createdAt": now_ms(), "completedAt": None}
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

# ── Dialog ────────────────────────────────────────────────────────────────────

@st.dialog("Job Details", width="large")
def job_dialog():
    job_id = st.session_state.get("dlg_job_id")
    job    = next((j for j in st.session_state.jobs if j["id"] == job_id), None) if job_id else None

    title       = st.text_input("Title *", value=job["title"] if job else "")
    description = st.text_area("Description", value=job.get("description", "") if job else "", height=70)

    PRIORITIES = ["Low", "Medium", "High", "Urgent"]
    STATUSES   = ["Pending", "In Progress", "Completed"]

    c1, c2 = st.columns(2)
    with c1:
        cur_p    = job["priority"] if job else "Medium"
        priority = st.selectbox("Priority", PRIORITIES, index=PRIORITIES.index(cur_p))
    with c2:
        cur_s  = job["status"] if job and job["status"] in STATUSES else "Pending"
        status = st.selectbox("Status", STATUSES, index=STATUSES.index(cur_s))

    if not job:
        default_loc = st.session_state.get("dlg_location", st.session_state.tabs_list[0])
        loc_idx     = st.session_state.tabs_list.index(default_loc) if default_loc in st.session_state.tabs_list else 0
        location    = st.selectbox("Location", st.session_state.tabs_list, index=loc_idx)
else:
        all_tabs = st.session_state.tabs_list
        cur_loc  = job["location"] if job["location"] in all_tabs else all_tabs[0]
        location = st.selectbox("Location", all_tabs, index=all_tabs.index(cur_loc))

    c3, c4 = st.columns(2)
    with c3:
        try:
            due_val = date.fromisoformat(job["dueDate"]) if job and job.get("dueDate") else None
        except ValueError:
            due_val = None
        due_date = st.date_input("Due Date", value=due_val)
    with c4:
        assigned_name = st.text_input("Assigned Name", value=job.get("assignedName", "") if job else "")

    assigned_email = st.text_input(
        "Assigned Email",
        value=job.get("assignedEmail", "") if job else "",
        help="An email notification will be sent automatically when a new job is created with an email address.",
    )
    notes = st.text_area("Notes", value=job.get("notes", "") if job else "", height=70)

    sc, cc = st.columns(2)
    with sc:
        save   = st.button("Save", type="primary", use_container_width=True)
    with cc:
        cancel = st.button("Cancel", use_container_width=True)

    if save:
        if not title.strip():
            st.error("Title is required.")
            return
        upsert_job(
            {
                "title": title.strip(), "description": description, "priority": priority,
                "status": status, "location": location,
                "dueDate": str(due_date) if due_date else "",
                "assignedName": assigned_name, "assignedEmail": assigned_email, "notes": notes,
            },
            job_id=job_id,
        )
        st.session_state.dlg_open   = False
        st.session_state.dlg_job_id = None
        st.rerun()

    if cancel:
        st.session_state.dlg_open   = False
        st.session_state.dlg_job_id = None
        st.rerun()

# ── Card helpers ──────────────────────────────────────────────────────────────

def badge(text: str, style: dict) -> str:
    return (
        f'<span style="background:{style["bg"]};color:{style["color"]};'
        f'padding:2px 10px;border-radius:4px;font-size:11px;font-weight:600;'
        f'letter-spacing:0.03em;display:inline-block;margin:2px;">{text.upper()}</span>'
    )

def render_active_card(job: dict, lk: str):
    with st.container(border=True):
        tc, ec, dc = st.columns([5, 1, 1])
        with tc:
            st.markdown(f"<p style='margin:0;font-size:13px;font-weight:600;line-height:1.3;color:#0f172a;'>{job['title']}</p>", unsafe_allow_html=True)
        with ec:
            if st.button("✏", key=f"e_{lk}_{job['id']}", help="Edit", use_container_width=True):
                st.session_state.dlg_job_id = job["id"]
                st.session_state.dlg_open   = True
                st.rerun()
        with dc:
            if st.button("🗑", key=f"d_{lk}_{job['id']}", help="Delete", use_container_width=True):
                remove_job(job["id"])
                st.rerun()

        # Build a single compact info block to minimise Streamlit element overhead
        meta = []
        if job.get("dueDate"):
            meta.append(f"Due {job['dueDate']}")
        if job.get("assignedName"):
            meta.append(f"Assigned to {job['assignedName']}")
        if job["status"] == "Completed" and job.get("completedAt"):
            ms_left = job["completedAt"] + 48 * 3_600_000 - now_ms()
            if ms_left > 0:
                h = int(ms_left / 3_600_000)
                m = int((ms_left % 3_600_000) / 60_000)
                meta.append(f"Archives in {h}h {m}m")

        meta_html = f"<p style='font-size:11px;color:#94a3b8;margin:1px 0 0;'>{'  ·  '.join(meta)}</p>" if meta else ""
        notes_html = f"<p style='font-size:11px;color:#374151;margin:1px 0 0;'>{job['notes']}</p>" if job.get("notes") else ""
        desc_html  = f"<p style='font-size:11px;color:#374151;margin:1px 0 0;'>{job['description']}</p>" if job.get("description") else ""

        st.markdown(
            badge(job["priority"], PRIORITY_STYLES[job["priority"]]) + " " +
            badge(job["status"],   STATUS_STYLES[job["status"]]) +
            meta_html + notes_html + desc_html,
            unsafe_allow_html=True,
        )

        if job["status"] != "Completed":
            opts = ["Pending", "In Progress", "Completed"]
            cur  = opts.index(job["status"]) if job["status"] in opts else 0
            sel  = st.selectbox(
                "Status", opts, index=cur,
                key=f"s_{lk}_{job['id']}", label_visibility="collapsed",
            )
            if sel != job["status"]:
                set_status(job["id"], sel)
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
        if job.get("notes"):
            meta.append(f"Note: {job['notes']}")
        if meta:
            st.caption("  ·  ".join(meta))


def render_kanban(location: str, view: str, search: str, filter_priority: str, filter_status: str):
    lk = location.replace(" ", "_").lower()
    q  = search.strip().lower()

    def matches(j):
        return (
            (not q or q in j["title"].lower() or q in (j.get("assignedName") or "").lower()) and
            (filter_priority == "All" or j["priority"] == filter_priority) and
            (filter_status   == "All" or j["status"]   == filter_status)
        )

    tab_jobs = [j for j in st.session_state.jobs if j["location"] == location]

    if view == "Active":
        pool = [j for j in tab_jobs if j["status"] != "Archived" and matches(j)]
        cols = st.columns(3)
        for i, col_name in enumerate(["Pending", "In Progress", "Completed"]):
            group = [j for j in pool if j["status"] == col_name]
            with cols[i]:
                st.markdown(f"#### {col_name} &nbsp; `{len(group)}`")
                if not group:
                    st.caption("No jobs")
                for job in group:
                    render_active_card(job, lk)
    else:
        pool = [j for j in tab_jobs if j["status"] == "Archived" and matches(j)]
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
    jobs, tabs, archived_tabs = load_data()
    st.session_state.update({
        "jobs":          jobs,
        "tabs_list":     tabs,
        "archived_tabs": archived_tabs,
        "dlg_open":      False,
        "dlg_job_id":    None,
        "dlg_location":  tabs[0] if tabs else DEFAULT_TABS[0],
        "initialized":   True,
    })

auto_archive()

# ── Show deferred toasts ──────────────────────────────────────────────────────
if "email_toast" in st.session_state:
    st.toast(st.session_state.pop("email_toast"))
if "email_toast_error" in st.session_state:
    st.error(st.session_state.pop("email_toast_error"))

# ── CSS ───────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap');

/* Base */
html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif !important;
}
.block-container {
    padding-top: 5rem !important;
    max-width: 1400px !important;
}

/* Hide Streamlit branding */
#MainMenu, footer, header { visibility: hidden; }

/* Custom header bar */
.app-header {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 0;
}
.app-title {
    font-family: 'DM Sans', sans-serif;
    font-size: 20px;
    font-weight: 600;
    color: #0f172a;
    letter-spacing: -0.02em;
    margin: 0;
}
.app-subtitle {
    font-size: 13px;
    color: #94a3b8;
    font-weight: 400;
}

/* Dividers */
hr { border-color: #e2e8f0 !important; margin: 0.75rem 0 !important; }

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 0;
    border-bottom: 1px solid #e2e8f0;
    background: transparent;
}
.stTabs [data-baseweb="tab"] {
    font-family: 'DM Sans', sans-serif !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    color: #64748b !important;
    padding: 10px 18px !important;
    border-radius: 0 !important;
    border-bottom: 2px solid transparent !important;
}
.stTabs [aria-selected="true"] {
    color: #0f172a !important;
    border-bottom: 2px solid #0f172a !important;
    background: transparent !important;
}
.stTabs [data-baseweb="tab-highlight"] { display: none !important; }
.stTabs [data-baseweb="tab-border"]    { display: none !important; }

/* Cards */
div[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 2px !important;
    border-color: #e2e8f0 !important;
    padding: 0px !important;
    margin-bottom: 4px !important;
}
div[data-testid="stVerticalBlockBorderWrapper"] > div {
    padding: 4px 8px !important;
}
/* Tighten all paragraph margins inside cards */
div[data-testid="stVerticalBlockBorderWrapper"] p {
    margin: 0 !important;
    line-height: 1.3 !important;
}
/* Shrink selectbox height in cards */
div[data-testid="stVerticalBlockBorderWrapper"] .stSelectbox > div {
    min-height: 28px !important;
}
div[data-testid="stVerticalBlockBorderWrapper"] .stSelectbox [data-baseweb="select"] > div {
    padding-top: 2px !important;
    padding-bottom: 2px !important;
    min-height: 28px !important;
    font-size: 11px !important;
}

/* Buttons */
.stButton button {
    font-family: 'DM Sans', sans-serif !important;
    font-size: 12px !important;
    font-weight: 500 !important;
    border-radius: 3px !important;
    letter-spacing: 0.01em !important;
    padding: 2px 6px !important;
    height: 28px !important;
    min-height: 28px !important;
}
.stButton button[kind="primary"] {
    background: #0f172a !important;
    border: none !important;
    color: white !important;
}
.stButton button[kind="primary"]:hover {
    background: #1e293b !important;
}
.stButton button[kind="secondary"] {
    background: #f8fafc !important;
    border: 1px solid #e2e8f0 !important;
    color: #64748b !important;
    filter: grayscale(100%) !important;
}
.stButton button[kind="secondary"]:hover {
    background: #f1f5f9 !important;
    color: #374151 !important;
}

/* Inputs */
.stTextInput input, .stTextArea textarea, .stSelectbox select {
    font-family: 'DM Sans', sans-serif !important;
    font-size: 13px !important;
    border-radius: 5px !important;
    border-color: #e2e8f0 !important;
}
.stSelectbox [data-baseweb="select"] {
    border-radius: 5px !important;
}

/* Column headers */
h4 {
    font-size: 13px !important;
    font-weight: 600 !important;
    color: #475569 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
}

/* Caption text */
.stCaptionContainer, [data-testid="stCaptionContainer"] {
    color: #94a3b8 !important;
    font-size: 12px !important;
}

/* Toast */
[data-testid="stToast"] {
    font-family: 'DM Sans', sans-serif !important;
    font-size: 13px !important;
}

/* Radio */
.stRadio label {
    font-family: 'DM Sans', sans-serif !important;
    font-size: 13px !important;
    font-weight: 500 !important;
}

/* Mono for code/badges */
code {
    font-family: 'DM Mono', monospace !important;
    font-size: 11px !important;
    background: #f1f5f9 !important;
    color: #475569 !important;
    border-radius: 4px !important;
    padding: 1px 6px !important;
}
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────

hc1, hc2, hc3, hc4 = st.columns([2, 3.5, 1.5, 1.5])
with hc1:
    st.markdown("""
    <div class="app-header">
        <div>
            <div class="app-title">Jobs Manager</div>
            <div class="app-subtitle">NZL 49er Programme</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
with hc2:
    search = st.text_input("Search", placeholder="Search jobs or assignees", label_visibility="collapsed")
with hc3:
    filter_priority = st.selectbox(
        "Priority", ["All", "Low", "Medium", "High", "Urgent"], label_visibility="collapsed"
    )
with hc4:
    filter_status = st.selectbox(
        "Status", ["All", "Pending", "In Progress", "Completed"], label_visibility="collapsed"
    )

st.markdown("---")

# ── Location tabs ─────────────────────────────────────────────────────────────

tab_labels = []
for loc in st.session_state.tabs_list:
    n = sum(1 for j in st.session_state.jobs if j["location"] == loc and j["status"] != "Archived")
    tab_labels.append(f"{loc}  ({n})")
tab_labels.append("+ New Tab")
archived_count = len(st.session_state.get("archived_tabs", []))
tab_labels.append(f"Archived Tabs  ({archived_count})" if archived_count else "Archived Tabs")

loc_tabs = st.tabs(tab_labels)

for i, tab_ctx in enumerate(loc_tabs[:-2]):
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
                st.session_state.jobs = [j for j in st.session_state.jobs if j["location"] != loc]
                save_data()
                st.rerun()

        # ── Tab Settings expander ──────────────────────────────────────────────
        with st.expander("Tab Settings"):
            tabs_list = st.session_state.tabs_list
            idx = tabs_list.index(loc)

            # Rename
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
                        # Rename tab in list
                        st.session_state.tabs_list[idx] = n
                        # Update all jobs referencing old location
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
                    unsafe_allow_html=True
                )

        st.divider()
        render_kanban(loc, view, search, filter_priority, filter_status)

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
                    st.session_state.jobs = [j for j in st.session_state.jobs if j["location"] != atab]
                    save_data()
                    st.rerun()
            st.divider()

# ── Open dialog if flagged ────────────────────────────────────────────────────

if st.session_state.get("dlg_open"):
    job_dialog()
