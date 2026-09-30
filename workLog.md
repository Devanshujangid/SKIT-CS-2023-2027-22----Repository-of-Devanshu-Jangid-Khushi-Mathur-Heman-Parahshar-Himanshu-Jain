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



---

## Task 4 – Implement Supabase Row Level Security (RLS) for Study Plans

### Work Done

- Enabled Row Level Security (RLS) on the `study_plans` table in Supabase.
- Created an RLS policy to allow students to SELECT only their own study plans.
- Created an RLS policy to allow students to INSERT only study plans matching their own `user_id`.
- Created an RLS policy to allow students to UPDATE only their own study plans.
- Configured the UPDATE policy with both `USING` and `WITH CHECK` conditions to prevent unauthorized ownership changes.
- Verified that all three RLS policies were successfully created.
- Verified that Row Level Security is enabled on the `study_plans` table.

### RLS Policies

```sql
-- SELECT
CREATE POLICY "Students can view their own study plans"
ON public.study_plans
FOR SELECT
TO authenticated
USING (
    auth.uid() = user_id
);

-- INSERT
CREATE POLICY "Students can insert their own study plans"
ON public.study_plans
FOR INSERT
TO authenticated
WITH CHECK (
    auth.uid() = user_id
);

-- UPDATE
CREATE POLICY "Students can update their own study plans"
ON public.study_plans
FOR UPDATE
TO authenticated
USING (
    auth.uid() = user_id
)
WITH CHECK (
    auth.uid() = user_id
);

RLS Enabled: true

Policies Verified:
- SELECT → auth.uid() = user_id
- INSERT → auth.uid() = user_id
- UPDATE → auth.uid() = user_id



---

## Task 5 – Apply and Verify RLS Policies on Student Profiles

### Work Done

- Enabled Row Level Security (RLS) on the `student_profiles` table.
- Implemented a SELECT policy to allow students to access only their own profile.
- Implemented an INSERT policy to allow students to create only their own profile.
- Implemented an UPDATE policy to allow students to modify only their own profile.
- Used the Clerk user identity from the authenticated JWT to identify the corresponding application user.
- Enforced ownership through the relationship:
  `Clerk sub → users.clerk_id → users.id → student_profiles.user_id`.
- Configured the UPDATE policy with both `USING` and `WITH CHECK` conditions to prevent unauthorized ownership changes.
- Verified all three RLS policies using PostgreSQL policy metadata.
- Verified that RLS is enabled on the `student_profiles` table.

### RLS Policies

```sql
-- SELECT
CREATE POLICY "Students can view their own profile"
ON public.student_profiles
FOR SELECT
TO authenticated
USING (
    EXISTS (
        SELECT 1
        FROM public.users
        WHERE users.id = student_profiles.user_id
          AND users.clerk_id = (SELECT auth.jwt() ->> 'sub')
    )
);

-- INSERT
CREATE POLICY "Students can insert their own profile"
ON public.student_profiles
FOR INSERT
TO authenticated
WITH CHECK (
    EXISTS (
        SELECT 1
        FROM public.users
        WHERE users.id = student_profiles.user_id
          AND users.clerk_id = (SELECT auth.jwt() ->> 'sub')
    )
);

-- UPDATE
CREATE POLICY "Students can update their own profile"
ON public.student_profiles
FOR UPDATE
TO authenticated
USING (
    EXISTS (
        SELECT 1
        FROM public.users
        WHERE users.id = student_profiles.user_id
          AND users.clerk_id = (SELECT auth.jwt() ->> 'sub')
    )
)
WITH CHECK (
    EXISTS (
        SELECT 1
        FROM public.users
        WHERE users.id = student_profiles.user_id
          AND users.clerk_id = (SELECT auth.jwt() ->> 'sub')
    )
);



RLS Enabled: true

Policies Verified:
- SELECT → own profile only
- INSERT → own profile only
- UPDATE → own profile only