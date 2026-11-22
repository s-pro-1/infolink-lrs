# Assumptions and open questions

Nothing here is verified Infolink policy. Items marked **ASK** need a real answer from the institution.

## Decisions made
- Single `User` model with a `role` field (student, lecturer, moderator, admin) plus an `is_verified`
  flag. Simpler to explain and test than separate user tables.
- Public registration can only create students and lecturer *requests*. Privileged roles are
  assigned by administrators only.
- Login throttling uses Django's cache (per-IP, 5 failures / 5 minutes). The default in-memory cache
  is per-process; use a shared cache (e.g. Redis) if you run several workers.
- Academic data is entered through the admin interface. `seed_sample_data` creates placeholder rows
  labelled `[SAMPLE]` and is for development only.
- Hawassa is created as the only campus in the sample data; the schema supports more campuses.
- Dev uses SQLite for zero-setup; production requires PostgreSQL via `DATABASE_URL`.
  **Run the tests against PostgreSQL before the final demo.**
- Bootstrap loads from a CDN in this increment. For low-bandwidth use, vendor it locally later.

## Open questions (ASK)
- How do students and lecturers get verified (student ID list? department head approval?).
- Real list of departments, programs, courses, levels and semester naming (Ethiopian vs Gregorian calendar).
- Official branding, logo and colours (kept configurable until provided).
- Does the university have rules on sharing past exams and lecturer materials?
- Is a university email domain available for automatic verification?
- Who will moderate after the project is handed over?

## Increment 2 decisions
- Files are stored on local disk in `private_media/` (outside the web root and MEDIA_URL) during development.
  At deployment, replace `get_private_storage()` in `apps/resources/storage.py` with a private S3/R2 bucket.
  Note: Render's disk is not persistent on the free tier, so cloud storage is required for production.
- Documents and videos will share the `Resource` model; videos (Increment 3) reuse the same moderation flow.
- Upload checks look at real file bytes (signature, Office package structure, macro/program entries, size).
- Legacy `.doc`/`.ppt` are accepted but can carry macros; they rely on ClamAV and the moderator. Consider
  dropping them if the institution does not need them.
- Antivirus does not detect inappropriate content. Every file needs human approval (no auto-approval).
- Without a configured scanner, files stay "scanner unavailable" and can only be approved in development mode.
- Rejected infected files are deleted from storage; rejected clean files are kept so the uploader can see the reason.
- Per-user upload limit: 20 per hour (configurable). Download counts exclude the uploader's own downloads.
- Not built yet (later increments): notification to the uploader on approve/reject (Increment 4), reporting
  resources (Increment 5), in-browser PDF preview (future).
