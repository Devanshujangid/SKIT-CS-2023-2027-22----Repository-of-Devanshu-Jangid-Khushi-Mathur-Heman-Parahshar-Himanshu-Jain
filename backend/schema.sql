-- ============================================================
-- SMART LEARNING PLANNER - DATABASE SCHEMA
-- ============================================================


-- ============================================================
-- USERS TABLE
-- ============================================================

CREATE TABLE IF NOT EXISTS public.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clerk_id TEXT UNIQUE NOT NULL,
    email TEXT NOT NULL,
    role TEXT DEFAULT 'student',
    created_at TIMESTAMP WITH TIME ZONE
        DEFAULT timezone('utc'::text, now()) NOT NULL
);


-- ============================================================
-- STUDENT PROFILES TABLE
-- ============================================================

CREATE TABLE IF NOT EXISTS public.student_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID UNIQUE
        REFERENCES public.users(id) ON DELETE CASCADE NOT NULL,
    semester INT NOT NULL,
    study_hours_per_day FLOAT NOT NULL,
    goals TEXT[] NOT NULL,
    onboarding_completed BOOLEAN DEFAULT TRUE
);


-- ============================================================
-- STUDY PLANS TABLE
-- ============================================================

CREATE TABLE IF NOT EXISTS public.study_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Multiple study plans can belong to the same user.
    user_id UUID NOT NULL
        REFERENCES public.users(id) ON DELETE CASCADE,

    plan_data JSONB NOT NULL,

    created_at TIMESTAMP WITH TIME ZONE
        DEFAULT timezone('utc'::text, now()) NOT NULL,

    updated_at TIMESTAMP WITH TIME ZONE
        DEFAULT timezone('utc'::text, now()) NOT NULL,

    is_active BOOLEAN NOT NULL DEFAULT TRUE
);


-- ============================================================
-- STUDY PLANS INDEX
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_study_plans_user_active_created
ON public.study_plans(user_id, is_active, created_at DESC);


-- ============================================================
-- ROW LEVEL SECURITY - STUDY PLANS
-- ============================================================

ALTER TABLE public.study_plans
ENABLE ROW LEVEL SECURITY;


CREATE POLICY "Students can view their own study plans"
ON public.study_plans
FOR SELECT
TO authenticated
USING (
    auth.uid() = user_id
);


CREATE POLICY "Students can insert their own study plans"
ON public.study_plans
FOR INSERT
TO authenticated
WITH CHECK (
    auth.uid() = user_id
);


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


-- ============================================================
-- ROW LEVEL SECURITY - STUDENT PROFILES
-- ============================================================

ALTER TABLE public.student_profiles
ENABLE ROW LEVEL SECURITY;


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