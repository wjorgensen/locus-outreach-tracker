# Outreach Tracker

Lightweight CRM for the Locus Pro founder-outreach operation. Deployed on
BuildWithLocus (`locus-outreach-tracker` project, `production` environment).

## What it does

- Prospect table: name, company, title, tier (A/B/C), LinkedIn link, stage.
- Pipeline stages: Sourced → Invite sent → Accepted → DM sent → Replied →
  Meeting → Customer (plus Dead / Opted out).
- Detail page per prospect: planned DM text, notes, stage history timeline.
- JSON API at `/api/prospects` for automation (e.g. the hourly LinkedIn scan).
- Seeded with 25 prospects from `locus_pro_founder_outreach_muse.md` plus live
  LinkedIn state (invites, acceptances, DMs sent, replies) as of 2026-09-24.

## Run locally

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
TRACKER_DB=/tmp/tracker.db PORT=8080 .venv/bin/python app.py
```

## Deploy (BuildWithLocus)

Service is created from the public GitHub repo `locus-outreach-tracker`
(Dockerfile build). Costs $1.50 for the first 30 days, renews until canceled.

```bash
# project + environment already exist:
#   project proj_mufw7jdlh9bege9r / env env_mufw7n122sf6uvtk
locus wrapped metered-pay-per-use-call \
  --provider buildwithlocus --endpoint services.create \
  --idempotency-key bwl-svc-outreach-tracker-1 \
  --body-json '{"environmentId":"env_mufw7n122sf6uvtk","name":"outreach-tracker",
    "source":{"githubRepo":"https://github.com/<owner>/locus-outreach-tracker"}}' \
  --agent
# then set TRACKER_PASSWORD variable and redeploy to launch
```

## Config

- `TRACKER_DB` — SQLite path (default `/data/tracker.db`).
- `TRACKER_PASSWORD` — if set, HTTP Basic auth (`admin` / password) is required.
- `PORT` — listen port (default 8080).
