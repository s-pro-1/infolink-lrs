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
