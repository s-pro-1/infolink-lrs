# Learning Resource Hub

A learning resource sharing platform with personalized recommendations, built as a
final-year project for Infolink University College (initial campus: Hawassa).

**Status:** Increments 1-2 complete (accounts, roles, academic structure, profiles, document upload, validation, malware-scan hook, moderation).
See `docs/ROADMAP.md` for what comes next.

## Stack
Django 5.2 · Bootstrap 5 · PostgreSQL (production) / SQLite (local) · WhiteNoise · Render.
Uploads are stored in a private folder (`private_media/`) for now; private S3-compatible storage (Cloudflare R2) is added at deployment.

## Quick start (local)
```bash
python3 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                  # optional for local dev
python manage.py migrate
python manage.py seed_sample_data                     # optional, clearly labelled [SAMPLE] data
python manage.py createsuperuser
python manage.py runserver
```
Open http://127.0.0.1:8000/ . No cloud account is needed locally.

## Uploads and moderation
1. A verified student or lecturer uploads a file (PDF, DOC, DOCX, PPT, PPTX, TXT, default max 20 MB).
2. The server checks the real file contents, not just the name, then stores it under a random name in `private_media/`.
3. It is scanned with ClamAV if configured. **If no scanner answers, the file is never marked clean.**
4. A moderator (role set by an admin) opens **Review**, checks the file, and approves or rejects with a reason.
5. Only approved files appear in Browse. All downloads go through Django, which checks permissions.

To try it locally: verify a student in `/admin/`, create a second user and set its **Role** to *Moderator*
(and tick Verified), then log in as each. In development mode a moderator may approve a file the scanner
could not check; in production this is off.

Optional ClamAV (Fedora): `sudo dnf install clamd clamav-update`, then set
`RESOURCE_SCANNER=apps.resources.scanning.ClamAVScanner` and `CLAMAV_HOST=127.0.0.1` (or `CLAMAV_UNIX_SOCKET`) in `.env`.

## Tests
```bash
python manage.py test apps
```

## Configuration
All via environment variables (see `.env.example`): secret key, allowed hosts, `DATABASE_URL`,
platform name, institution name and brand colour. Institution branding is configuration, not code.
`manage.py` uses `config.settings.dev`; WSGI/ASGI use `config.settings.prod`.

## Roles
- **Student**: self-registers. Cannot upload until an admin verifies the account.
- **Lecturer**: self-registers as a *request*; an admin verifies it. No admin rights.
- **Moderator / Admin**: only an administrator can assign these (Django admin). Public
  registration cannot create them (covered by tests).

Verify users in Django admin: Users -> select -> "Verify selected users".

## Deployment (Render)
1. Push to GitHub, create a Render Blueprint from `render.yaml` (web service + PostgreSQL).
2. Set `DJANGO_ALLOWED_HOSTS` (your `onrender.com` host) and `CSRF_TRUSTED_ORIGINS` (`https://...`).
3. Health check path: `/health/`.
4. Create the first admin with `python manage.py createsuperuser` in the Render shell.
5. Enable automated database backups on your Render Postgres plan and test a restore before the demo.

## Project layout
```
config/     settings (base/dev/prod), urls, wsgi
apps/
  core/       landing, dashboard, health check, branding
  accounts/   custom User (roles), profiles, auth views, login throttle
  academics/  campus, department, program, course, semester, enrollment
  resources/  upload, validation, scanning, private storage, browse, download
  moderation/ review queue, approve/reject/hide, rules
docs/       architecture, assumptions, roadmap
```
