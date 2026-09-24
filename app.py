"""Locus outreach tracker - lightweight CRM for founder outreach.
Single-service Flask app, SQLite storage. Built for BuildWithLocus deploy.
"""
import json
import os
import sqlite3
from datetime import datetime, timezone
from functools import wraps

from flask import Flask, request, redirect, url_for, jsonify, Response

DB_PATH = os.environ.get("TRACKER_DB", "/data/tracker.db")
SEED_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "seed_data.json")
PASSWORD = os.environ.get("TRACKER_PASSWORD", "")

STAGES = [
    "sourced", "invite_sent", "invite_accepted", "dm_sent",
    "replied", "meeting", "customer", "dead", "opted_out",
]
STAGE_LABELS = {
    "sourced": "Sourced",
    "invite_sent": "Invite sent",
    "invite_accepted": "Accepted",
    "dm_sent": "DM sent",
    "replied": "Replied",
    "meeting": "Meeting",
    "customer": "Customer",
    "dead": "Dead",
    "opted_out": "Opted out",
}

app = Flask(__name__)


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = db()
    conn.execute(
        """CREATE TABLE IF NOT EXISTS prospects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL, company TEXT, title TEXT, tier TEXT,
            linkedin_url TEXT, email TEXT, stage TEXT DEFAULT 'sourced',
            source TEXT, planned_dm TEXT, notes TEXT,
            created_at TEXT, updated_at TEXT
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS activity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prospect_id INTEGER NOT NULL, at TEXT, kind TEXT, note TEXT,
            FOREIGN KEY(prospect_id) REFERENCES prospects(id)
        )"""
    )
    count = conn.execute("SELECT COUNT(*) FROM prospects").fetchone()[0]
    if count == 0 and os.path.exists(SEED_PATH):
        seed = json.load(open(SEED_PATH))
        now = datetime.now(timezone.utc).isoformat()
        for p in seed:
            cur = conn.execute(
                """INSERT INTO prospects
                   (name, company, title, tier, linkedin_url, email, stage,
                    source, planned_dm, notes, created_at, updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (p.get("name"), p.get("company"), p.get("title"), p.get("tier"),
                 p.get("linkedin_url"), p.get("email"), p.get("stage", "sourced"),
                 p.get("source"), p.get("planned_dm"), p.get("notes"), now, now),
            )
            if p.get("notes"):
                conn.execute(
                    "INSERT INTO activity (prospect_id, at, kind, note) VALUES (?,?,?,?)",
                    (cur.lastrowid, now, "seed", p["notes"]),
                )
        print(f"seeded {len(seed)} prospects")
    conn.commit()
    conn.close()


def require_auth(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if PASSWORD:
            auth = request.authorization
            if not auth or auth.password != PASSWORD:
                return Response("Login required", 401,
                                {"WWW-Authenticate": 'Basic realm="tracker"'})
        return f(*args, **kwargs)
    return wrapper


def log_activity(conn, prospect_id, kind, note):
    conn.execute(
        "INSERT INTO activity (prospect_id, at, kind, note) VALUES (?,?,?,?)",
        (prospect_id, datetime.now(timezone.utc).isoformat(), kind, note),
    )


PAGE_CSS = """
body{font-family:-apple-system,system-ui,sans-serif;max-width:1100px;margin:0 auto;
padding:16px;color:#1a1a1a;background:#fafafa}
h1{font-size:22px;margin:8px 0}
.stats{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0}
.stat{background:#fff;border:1px solid #e3e3e3;border-radius:8px;padding:8px 12px;font-size:13px}
.stat b{font-size:16px}
.filters{margin:12px 0;display:flex;gap:8px;flex-wrap:wrap}
.filters select,.filters input{padding:6px 8px;border:1px solid #ccc;border-radius:6px;font-size:14px}
table{width:100%;border-collapse:collapse;background:#fff;border-radius:8px;overflow:hidden;font-size:14px}
th,td{padding:10px 12px;text-align:left;border-bottom:1px solid #eee}
th{background:#f3f3f3;font-size:12px;text-transform:uppercase;color:#666}
tr:hover td{background:#f9f9f9}
a{color:#0a66c2;text-decoration:none}
.pill{display:inline-block;padding:3px 10px;border-radius:20px;font-size:12px;font-weight:600}
.tier-A{background:#e8f0fe;color:#1a56db}.tier-B{background:#fef3c7;color:#92400e}
.tier-C{background:#f3f4f6;color:#4b5563}
.stage-sourced{background:#f3f4f6;color:#4b5563}.stage-invite_sent{background:#dbeafe;color:#1e40af}
.stage-invite_accepted{background:#e0e7ff;color:#3730a3}.stage-dm_sent{background:#ede9fe;color:#5b21b6}
.stage-replied{background:#d1fae5;color:#065f46}.stage-meeting{background:#a7f3d0;color:#064e3b}
.stage-customer{background:#6ee7b7;color:#064e3b}.stage-dead{background:#fee2e2;color:#991b1b}
.stage-opted_out{background:#fee2e2;color:#991b1b}
select.stage{border:none;font-size:12px;font-weight:600;border-radius:20px;padding:4px 8px;cursor:pointer}
.card{background:#fff;border:1px solid #e3e3e3;border-radius:10px;padding:16px;margin:12px 0}
.dm{white-space:pre-wrap;background:#f6f6f6;border-radius:8px;padding:12px;font-size:14px}
.btn{background:#0a66c2;color:#fff;border:none;border-radius:6px;padding:8px 14px;font-size:14px;cursor:pointer}
.btn-ghost{background:#fff;color:#0a66c2;border:1px solid #0a66c2}
textarea{width:100%;border:1px solid #ccc;border-radius:6px;padding:8px;font-size:14px;box-sizing:border-box}
.timeline{font-size:14px}.timeline div{padding:6px 0;border-bottom:1px solid #f0f0f0}
.muted{color:#777;font-size:13px}
"""


def page(title, body):
    return f"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title><style>{PAGE_CSS}</style></head>
<body>{body}</body></html>"""


@app.route("/")
@require_auth
def index():
    tier = request.args.get("tier", "")
    stage = request.args.get("stage", "")
    q = request.args.get("q", "").strip()
    conn = db()
    where, params = [], []
    if tier:
        where.append("tier=?"); params.append(tier)
    if stage:
        where.append("stage=?"); params.append(stage)
    if q:
        where.append("(name LIKE ? OR company LIKE ?)")
        params += [f"%{q}%", f"%{q}%"]
    sql = "SELECT * FROM prospects"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY CASE tier WHEN 'A' THEN 0 WHEN 'B' THEN 1 ELSE 2 END, company, name"
    rows = conn.execute(sql, params).fetchall()
    counts = conn.execute(
        "SELECT stage, COUNT(*) c FROM prospects GROUP BY stage").fetchall()
    conn.close()
    stat_html = "".join(
        f'<div class="stat"><b>{r["c"]}</b> {STAGE_LABELS.get(r["stage"], r["stage"])}</div>'
        for r in counts)
    tier_opts = "".join(
        f'<option value="{t}"{" selected" if tier==t else ""}>{t}</option>'
        for t in ["", "A", "B", "C"])
    stage_opts = "".join(
        f'<option value="{s}"{" selected" if stage==s else ""}>'
        f'{STAGE_LABELS[s] if s else "All stages"}</option>'
        for s in [""] + STAGES)
    trs = []
    for r in rows:
        li = (f' <a href="{r["linkedin_url"]}" target="_blank">in</a>'
              if r["linkedin_url"] else "")
        opts = "".join(
            f'<option value="{s}"{" selected" if r["stage"]==s else ""}>'
            f'{STAGE_LABELS[s]}</option>' for s in STAGES)
        trs.append(
            f'<tr><td><a href="/prospect/{r["id"]}">{r["name"]}</a>{li}</td>'
            f'<td>{r["company"] or ""}<div class="muted">{r["title"] or ""}</div></td>'
            f'<td><span class="pill tier-{r["tier"]}">{r["tier"]}</span></td>'
            f'<td><form method="post" action="/prospect/{r["id"]}/stage" '
            f'style="margin:0"><select name="stage" class="stage stage-{r["stage"]}" '
            f'onchange="this.form.submit()">{opts}</select></form></td></tr>')
    body = f"""
<h1>Outreach tracker</h1>
<div class="stats">{stat_html}</div>
<form class="filters" method="get">
<select name="tier" onchange="this.form.submit()">{tier_opts}</select>
<select name="stage" onchange="this.form.submit()">{stage_opts}</select>
<input name="q" placeholder="Search name or company" value="{q}">
<button class="btn btn-ghost" type="submit">Filter</button>
</form>
<table><tr><th>Name</th><th>Company</th><th>Tier</th><th>Stage</th></tr>
{"".join(trs)}</table>
<p class="muted">{len(rows)} prospects</p>"""
    return page("Outreach tracker", body)


@app.route("/prospect/<int:pid>")
@require_auth
def detail(pid):
    conn = db()
    r = conn.execute("SELECT * FROM prospects WHERE id=?", (pid,)).fetchone()
    if not r:
        conn.close()
        return "Not found", 404
    acts = conn.execute(
        "SELECT * FROM activity WHERE prospect_id=? ORDER BY id DESC",
        (pid,)).fetchall()
    conn.close()
    li = (f'<p><a href="{r["linkedin_url"]}" target="_blank">LinkedIn profile</a></p>'
          if r["linkedin_url"] else "")
    em = f'<p>Email: <code>{r["email"]}</code></p>' if r["email"] else ""
    dm = (f'<div class="card"><h3>Planned DM</h3><div class="dm">{r["planned_dm"]}'
          f'</div></div>' if r["planned_dm"] else "")
    stage_btns = "".join(
        f'<form method="post" action="/prospect/{pid}/stage" style="display:inline">'
        f'<input type="hidden" name="stage" value="{s}">'
        f'<button class="btn{" btn-ghost" if r["stage"]!=s else ""}" type="submit" '
        f'style="margin:2px">{STAGE_LABELS[s]}</button></form>' for s in STAGES)
    timeline = "".join(
        f'<div><span class="muted">{a["at"][:16].replace("T"," ")} · {a["kind"]}</span><br>'
        f'{a["note"] or ""}</div>' for a in acts)
    body = f"""
<p><a href="/">&larr; All prospects</a></p>
<h1>{r["name"]}</h1>
<div class="card">
<p><b>{r["title"] or ""}</b> at <b>{r["company"] or ""}</b>
<span class="pill tier-{r["tier"]}">{r["tier"]}</span>
<span class="pill stage-{r["stage"]}">{STAGE_LABELS.get(r["stage"], r["stage"])}</span></p>
{li}{em}
<p class="muted">Source: {r["source"] or ""}</p>
</div>
<div class="card"><h3>Set stage</h3>{stage_btns}</div>
{dm}
<div class="card"><h3>Add note</h3>
<form method="post" action="/prospect/{pid}/note">
<textarea name="note" rows="3" placeholder="Call notes, reply summary, next step..."></textarea><br><br>
<button class="btn" type="submit">Add note</button></form></div>
<div class="card"><h3>Activity</h3><div class="timeline">{timeline or "No activity yet."}</div></div>"""
    return page(r["name"], body)


@app.route("/prospect/<int:pid>/stage", methods=["POST"])
@require_auth
def set_stage(pid):
    stage = request.form.get("stage", "")
    if stage not in STAGES:
        return "Bad stage", 400
    conn = db()
    r = conn.execute("SELECT stage FROM prospects WHERE id=?", (pid,)).fetchone()
    if not r:
        conn.close()
        return "Not found", 404
    old = r["stage"]
    conn.execute(
        "UPDATE prospects SET stage=?, updated_at=? WHERE id=?",
        (stage, datetime.now(timezone.utc).isoformat(), pid))
    log_activity(conn, pid, "stage",
                 f"Stage: {STAGE_LABELS.get(old, old)} → {STAGE_LABELS[stage]}")
    conn.commit()
    conn.close()
    return redirect(request.referrer or url_for("detail", pid=pid))


@app.route("/prospect/<int:pid>/note", methods=["POST"])
@require_auth
def add_note(pid):
    note = request.form.get("note", "").strip()
    if not note:
        return redirect(url_for("detail", pid=pid))
    conn = db()
    conn.execute(
        "UPDATE prospects SET notes=CASE WHEN notes IS NULL OR notes='' THEN ? "
        "ELSE notes || '\n\n' || ? END, updated_at=? WHERE id=?",
        (note, note, datetime.now(timezone.utc).isoformat(), pid))
    log_activity(conn, pid, "note", note)
    conn.commit()
    conn.close()
    return redirect(url_for("detail", pid=pid))


@app.route("/api/prospects")
@require_auth
def api_prospects():
    conn = db()
    rows = conn.execute("SELECT * FROM prospects ORDER BY id").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/healthz")
def healthz():
    return "ok"


init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
