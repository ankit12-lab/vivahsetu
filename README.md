# VivahSetu — redesigned Flask wedding marketplace

Premium responsive wedding discovery website with venue search, enquiry flow,
vendor registration, budget planner and the existing admin CRM.

## Run locally
```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
pip install -r requirements.txt
set SECRET_KEY=change-this
set ADMIN_PASSWORD=change-this
python app.py
```

Open http://127.0.0.1:5000

Admin: http://127.0.0.1:5000/admin/login

## Render
Build: `pip install -r requirements.txt`
Start: `gunicorn app:app`

Set `SECRET_KEY` and `ADMIN_PASSWORD` in Render.

Note: SQLite is suitable for demo/small single-instance use. For a serious
marketplace, migrate the database to managed PostgreSQL and add authentication,
backups, rate limiting and persistent media storage.
