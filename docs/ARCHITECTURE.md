# Architecture

Modular monolith (Django). Each app owns its models, forms, services and templates.

```
Browser -> Django (WhiteNoise static) -> PostgreSQL
                                      -> Object storage (private, from Increment 2)
                                      -> Recommendation module (Increment 4)
```

## Implemented in Increment 1
`accounts` (User, StudentProfile, LecturerProfile), `academics` (Campus, Department,
AcademicProgram, AcademicYear, Semester, Course, StudentCourseEnrollment), `core`.

## Planned ERD (Increments 2-5 shown dashed in the final report)
```mermaid
erDiagram
  Campus ||--o{ Department : has
  Department ||--o{ AcademicProgram : offers
  Department ||--o{ Course : owns
  AcademicProgram }o--o{ Course : includes
  AcademicYear ||--o{ Semester : has
  User ||--o| StudentProfile : has
  User ||--o| LecturerProfile : has
  User ||--o{ StudentCourseEnrollment : makes
  Course ||--o{ StudentCourseEnrollment : receives
  StudentProfile }o--|| Department : in
  StudentProfile }o--|| AcademicProgram : follows
  User ||--o{ Resource : uploads
  Course ||--o{ Resource : covers
  ResourceCategory ||--o{ Resource : classifies
  Resource ||--o{ ResourceDownload : logs
  Resource ||--o{ Bookmark : saved_as
  Resource ||--o{ Rating : rated_by
  Resource ||--o{ ResourceReport : reported_in
  User ||--o{ Notification : receives
```
Design note: documents and videos will share one `Resource` model with a `kind` field,
rather than two near-identical tables.
