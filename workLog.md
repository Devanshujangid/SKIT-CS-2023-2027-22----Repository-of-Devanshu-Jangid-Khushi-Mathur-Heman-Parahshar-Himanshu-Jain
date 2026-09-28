# Heman Parashar – Backend & Database Work Log

## Project
Smart Learning Planner

## Role
Backend & Database

---

## Task 1 – Optimize GET /api/v1/plans Database Query

### Work Done

- Optimized the FastAPI `GET /api/v1/plans` endpoint for faster study-plan retrieval when the dashboard loads.
- Optimized the authenticated user lookup using the user's Clerk ID.
- Added `.limit(1)` to the users query because `clerk_id` is unique.
- Reduced unnecessary database response data by selecting only the required study-plan fields.
- Verified the endpoint locally using FastAPI Swagger documentation.
- Confirmed that the optimized endpoint returned a successful HTTP 200 response.

### Technical Changes

- Optimized the Supabase query for the `users` table.
- Optimized the Supabase query for the `study_plans` table.
- Reduced unnecessary fields returned to the frontend.
- Verified Python syntax and backend functionality.

---

## Task 2 – Verify Supabase Cascade Delete Constraints

### Work Done

- Verified the Supabase foreign-key relationships between `users`, `student_profiles`, and `study_plans`.
- Verified that `student_profiles.user_id` references `users.id`.
- Verified that `study_plans.user_id` references `users.id`.
- Confirmed that both relationships use `ON DELETE CASCADE`.
- Tested the database constraints using Supabase SQL queries.
- Verified that dependent profile and study-plan records are configured to be automatically deleted when the associated user is deleted.

### Database Constraints Verified

```text
users
  |
  ├── student_profiles
  │       ON DELETE CASCADE
  │
  └── study_plans
          ON DELETE CASCADE