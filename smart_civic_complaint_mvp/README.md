# CivicPulse — Smart Civic Complaint Triage (SC-01)

A working hackathon MVP built with Python/Flask, SQLite, HTML, CSS and JavaScript.

## Features
- Submit civic reports with title, description, location, optional coordinates and photo.
- Rule-based category detection for road damage, streetlights, garbage/sanitation, water leakage and other.
- Transparent rule-based priority suggestion (High / Medium / Low).
- Heuristic possible-duplicate flag based on similar report text and location.
- Complaint tracking by ID without exposing reporter details.
- Password-protected demo admin dashboard to filter, reprioritize, update status, add a public note and upload resolution evidence.
- Dashboard metrics: total, open, high-priority and resolved reports.
- SQLite persistence and seeded sample complaints.

## Requirements
- Python 3.10 or newer recommended
- Internet is not required to run the app. Google Fonts are optional and only affect typography if online.

## Setup — Windows (PowerShell)
```powershell
cd smart_civic_complaint_mvp
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```
If PowerShell blocks activation, run:
```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```
Then open http://127.0.0.1:5000

## Setup — macOS / Linux
```bash
cd smart_civic_complaint_mvp
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000

## Demo admin login
- Open http://127.0.0.1:5000/admin
- Password: `demo123`

Set a different password before demo/deployment:
- Windows PowerShell: `$env:ADMIN_PASSWORD="your-password"`
- macOS/Linux: `export ADMIN_PASSWORD="your-password"`

For production, also set a strong `SECRET_KEY`, enable HTTPS, add proper role-based accounts/CSRF protection, validate and scan uploaded images, and review privacy/legal requirements. This MVP uses a demo password and is not production-ready.

## Demo flow (3–5 minutes)
1. Open the public homepage and point out the four steps.
2. Submit: Title `Pothole outside the school`; description `A deep pothole is dangerous for motorcycles near the school`; location `Main Road, near City School`; optional photo.
3. Show the generated tracking ID and auto-detected category/priority.
4. Submit another similar pothole report at the same location to demonstrate the possible-duplicate flag (the matching heuristic is approximate).
5. Open `/admin`, sign in with `demo123`, and show priority-sorted reports and metrics.
6. Change the report to `In progress`, add a public note such as `Road maintenance team assigned for inspection`, then click Save update.
7. Return to the public page, track the report by ID and show the status/note.
8. In admin, mark it `Resolved`, add a short resolution note, and optionally upload a resolution photo. Track again.
9. Explain the algorithm transparently: categories and priority use keyword rules; duplicate detection is a similarity heuristic, so staff review all flags.

## Sample report inputs
| Field | Example |
|---|---|
| Title | Streetlight not working near bus stop |
| Description | The street light has been off for three nights and the footpath is dark |
| Location | Block B, Park Street |
| Expected category | Streetlight |
| Expected priority | Medium |

| Field | Example |
|---|---|
| Title | Water pipe leaking beside school |
| Description | A pipe is leaking continuously and water is spreading across the road |
| Location | Market Road near City School |
| Expected category | Water leakage |
| Expected priority | High |

## API endpoints
- `GET /api/meta` — categories and statuses
- `POST /api/complaints` — submit multipart form fields and optional `photo`
- `GET /api/complaints/<id>` — public tracking summary
- `GET /api/admin/stats` — admin-only dashboard metrics
- `GET /api/admin/complaints` — admin-only list; optional `status` and `category` filters
- `PATCH /api/admin/complaints/<id>` — admin-only JSON: `status`, `priority`, `admin_note`
- `POST /api/admin/complaints/<id>/resolution` — admin-only multipart field `evidence`

## Notes and limitations
- Seeded records are fictional demonstration data.
- This app does not connect to a municipal authority or send real notifications.
- Location is manually entered; latitude/longitude fields are optional and are not currently used to calculate route distance.
- Category, priority and duplicate matching are intentionally simple explainable baselines, not AI or official triage.
- For a real deployment, add authentication for each staff member, audit logs, rate limiting, CSRF protection, privacy controls, backups, moderation and official department integration.
