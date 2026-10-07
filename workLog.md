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


Task: API Authentication & GET /api/v1/plans Verification

1. Worked on the backend authentication flow.
2. Verified the FastAPI backend was running correctly.
3. Opened the FastAPI Swagger documentation.
4. Located the protected GET /api/v1/plans endpoint.
5. Verified that the endpoint requires authentication.
6. Tested the endpoint without an Authorization header.
7. Confirmed that authentication is enforced.
8. Tested the endpoint using Swagger UI.
9. Generated a Clerk session token from the frontend.
10. Used window.Clerk.session.getToken() to obtain the token.
11. Inspected the generated JWT token.
12. Copied the generated token for API testing.
13. Opened the Authorize option in Swagger UI.
14. Supplied the Clerk token as a Bearer token.
15. Executed GET /api/v1/plans.
16. Inspected the generated cURL request.
17. Confirmed that the Authorization header was included.
18. Verified the request URL.
19. Verified the API endpoint path.
20. Checked the HTTP response status.
21. The API returned HTTP 401 Unauthorized.
22. Inspected the response body.
23. The response returned "Invalid Clerk token".
24. Confirmed that the request reached FastAPI.
25. Confirmed that the endpoint route was correct.
26. Confirmed that the issue was not a missing route.
27. Confirmed that the issue was related to token verification.
28. Inspected the backend Clerk authentication configuration.
29. Reviewed the CLERK_ISSUER_URL configuration.
30. Reviewed the JWT verification flow.
31. Checked the Clerk JWKS verification process.
32. Verified that the backend attempts to retrieve Clerk JWKS.
33. Verified that the JWT header is inspected.
34. Verified that the token key ID is checked.
35. Verified that RSA public-key verification is used.
36. Verified that the issuer is validated.
37. Verified that audience verification is disabled in the current implementation.
38. Tested the protected endpoint again.
39. Reproduced the same authentication error.
40. Inspected browser Network requests.
41. Opened Chrome DevTools.
42. Selected the Network tab.
43. Filtered requests using the plans keyword.
44. Verified frontend network activity.
45. Confirmed that no successful /plans request was visible initially.
46. Cleared the Network filter.
47. Reloaded the application.
48. Inspected Fetch/XHR requests.
49. Verified Clerk-related requests.
50. Confirmed that Clerk frontend services were active.
51. Retrieved a fresh Clerk session token.
52. Repeated the Swagger API test.
53. Passed the fresh token through Swagger.
54. Verified the Authorization header format.
55. Confirmed the Bearer prefix was present.
56. Executed the GET /api/v1/plans request.
57. Received HTTP 401 Unauthorized again.
58. Confirmed that the backend rejected the Clerk token.
59. Identified Clerk JWT verification as the remaining issue.
60. Confirmed that the API endpoint itself is reachable.
61. Confirmed that FastAPI is processing the request.
62. Confirmed that authentication dependency is being executed.
63. Confirmed that invalid authentication is correctly rejected.
64. Reviewed the relationship between frontend Clerk authentication and backend authentication.
65. Reviewed the token flow from Clerk to FastAPI.
66. Verified that the frontend can obtain a session token.
67. Verified that the token can be passed to Swagger.
68. Verified that Swagger includes the token in the request.
69. Identified a mismatch in backend token validation.
70. Documented the current authentication failure.
71. No changes were made to the database during this test.
72. No changes were made to the study_plans table during this test.
73. No changes were made to the GET /api/v1/plans query during this test.
74. The existing endpoint remains protected.
75. The endpoint correctly prevents unauthorized access.
76. The test confirmed that authentication security is active.
77. The remaining work is to resolve Clerk token verification.
78. The Clerk issuer configuration requires further verification.
79. The backend JWT verification configuration requires further verification.
80. The Clerk JWKS configuration requires further verification.
81. After authentication is fixed, the endpoint should be tested again.
82. A valid Clerk token should result in successful authentication.
83. The authenticated Clerk user should then be mapped to the database user.
84. The user's internal UUID should be retrieved from the users table.
85. The endpoint should retrieve the user's active study plan.
86. The query should filter by user_id.
87. The query should filter is_active = true.
88. The results should be ordered by created_at descending.
89. The endpoint should return the latest active study plan.
90. The response should contain success = true.
91. The response should contain the plans array.
92. Unauthorized users should continue receiving HTTP 401.
93. Authentication testing was performed using Swagger UI.
94. Browser DevTools was used for network-level verification.
95. Clerk session token generation was tested from the browser console.
96. FastAPI authentication behavior was verified.
97. The current blocker was documented.
98. The API route itself was confirmed to be operational.
99. The remaining task is Clerk JWT verification.
100. Final status: API endpoint reachable; authentication verification requires further debugging.