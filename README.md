# Learning Resource Hub

A learning resource sharing platform with personalized recommendations, built as a
final-year project for Infolink University College (initial campus: Hawassa).

**Status:** Increment 1 complete (foundation, accounts, roles, academic structure, profiles).
See `docs/ROADMAP.md` for what comes next.

## Stack
Django 5.2 · Bootstrap 5 · PostgreSQL (production) / SQLite (local) · WhiteNoise · Render.
Private S3-compatible storage (Cloudflare R2) arrives with uploads in Increment 2.

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
docs/       architecture, assumptions, roadmap
```
