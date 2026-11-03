
-- ============================================================
-- SMART LEARNING PLANNER - FROZEN DATABASE SCHEMA SPECIFICATION
-- ============================================================
-- Status: FROZEN / PRODUCTION BASELINE (No DDL modifications without change-order)
-- Schema Version: 1.2.0-FROZEN
-- Checkpoint Milestone: Mid-Term 50% Architecture Evaluation (October 31, 2026)
-- Baseline Git Commit SHA: 80e6f0239e24ea5832c32942398cdd3af8e72e10
-- Core Tables: users, student_profiles, study_plans, tasks
-- Stored Procedures: public.create_study_plan_version()
-- Security: Row Level Security (RLS) enabled on all tables with Clerk JWT auth
-- ============================================================

-- ============================================================
-- USERS TABLE
-- ============================================================

CREATE TABLE IF NOT EXISTS public.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clerk_id TEXT UNIQUE NOT NULL,
    email TEXT NOT NULL,
    role TEXT DEFAULT 'student',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- ============================================================
-- STUDENT PROFILES TABLE
-- ============================================================

CREATE TABLE IF NOT EXISTS public.student_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID UNIQUE NOT NULL
        REFERENCES public.users(id) ON DELETE CASCADE,
    semester INT NOT NULL,
    study_hours_per_day FLOAT NOT NULL,
    goals TEXT[] NOT NULL,
    subjects TEXT[] NOT NULL DEFAULT '{}',
    onboarding_completed BOOLEAN DEFAULT TRUE
);

-- Migration for existing databases
ALTER TABLE public.student_profiles
ADD COLUMN IF NOT EXISTS subjects TEXT[] NOT NULL DEFAULT '{}';


-- ============================================================
-- STUDY PLANS TABLE (WITH ADAPTIVE VERSIONING SUPPORT)
-- ============================================================

CREATE TABLE IF NOT EXISTS public.study_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL
        REFERENCES public.users(id) ON DELETE CASCADE,
    plan_data JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

-- Migration for existing databases: Remove legacy single-plan unique constraint
ALTER TABLE public.study_plans
DROP CONSTRAINT IF EXISTS unique_user_study_plan;

-- Enforce at most one active plan per user (allows immutable historical versions)
CREATE UNIQUE INDEX IF NOT EXISTS idx_study_plans_one_active_per_user
ON public.study_plans (user_id)
WHERE is_active = TRUE;

CREATE INDEX IF NOT EXISTS idx_study_plans_user_active_created
ON public.study_plans(user_id, is_active, created_at DESC);


-- ============================================================
-- STORED PROCEDURE: ATOMIC STUDY PLAN VERSIONING
-- ============================================================

CREATE OR REPLACE FUNCTION public.create_study_plan_version(
    p_user_id UUID,
    p_plan_data JSONB
)
RETURNS SETOF public.study_plans
LANGUAGE plpgsql
AS $$
DECLARE
    new_plan public.study_plans;
BEGIN
    -- Serialize concurrent plan updates for the same user.
    PERFORM pg_advisory_xact_lock(
        hashtextextended(p_user_id::TEXT, 0)
    );

    -- Create the new version as inactive first.
    INSERT INTO public.study_plans (
        user_id,
        plan_data,
        is_active
    )
    VALUES (
        p_user_id,
        p_plan_data,
        FALSE
    )
    RETURNING * INTO new_plan;

    -- Archive the previous active plan.
    UPDATE public.study_plans
    SET is_active = FALSE,
        updated_at = NOW()
    WHERE user_id = p_user_id
      AND is_active = TRUE;

    -- Activate the new version.
    UPDATE public.study_plans
    SET is_active = TRUE,
        updated_at = NOW()
    WHERE id = new_plan.id
    RETURNING * INTO new_plan;

    RETURN NEXT new_plan;
END;
$$;


-- ============================================================
-- TASKS TABLE
-- ============================================================

CREATE TABLE IF NOT EXISTS public.tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL
        REFERENCES public.users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    scheduled_date DATE,
    plan_session_key TEXT,
    is_completed BOOLEAN NOT NULL DEFAULT FALSE,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Migration for existing databases
ALTER TABLE public.tasks
ADD COLUMN IF NOT EXISTS scheduled_date DATE,
ADD COLUMN IF NOT EXISTS plan_session_key TEXT;

CREATE INDEX IF NOT EXISTS idx_tasks_user_created
ON public.tasks(user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_tasks_user_scheduled
ON public.tasks(user_id, scheduled_date);



-- ============================================================
-- ROW LEVEL SECURITY - STUDY PLANS
-- ============================================================

ALTER TABLE public.study_plans ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Students can view their own study plans"
ON public.study_plans;

CREATE POLICY "Students can view their own study plans"
ON public.study_plans
FOR SELECT
TO authenticated
USING (
    EXISTS (
        SELECT 1
        FROM public.users
        WHERE users.id = study_plans.user_id
          AND users.clerk_id = (SELECT auth.jwt() ->> 'sub')
    )
);

DROP POLICY IF EXISTS "Students can insert their own study plans"
ON public.study_plans;

CREATE POLICY "Students can insert their own study plans"
ON public.study_plans
FOR INSERT
TO authenticated
WITH CHECK (
    EXISTS (
        SELECT 1
        FROM public.users
        WHERE users.id = study_plans.user_id
          AND users.clerk_id = (SELECT auth.jwt() ->> 'sub')
    )
);

DROP POLICY IF EXISTS "Students can update their own study plans"
ON public.study_plans;

CREATE POLICY "Students can update their own study plans"
ON public.study_plans
FOR UPDATE
TO authenticated
USING (
    EXISTS (
        SELECT 1
        FROM public.users
        WHERE users.id = study_plans.user_id
          AND users.clerk_id = (SELECT auth.jwt() ->> 'sub')
    )
)
WITH CHECK (
    EXISTS (
        SELECT 1
        FROM public.users
        WHERE users.id = study_plans.user_id
          AND users.clerk_id = (SELECT auth.jwt() ->> 'sub')
    )
);


-- ============================================================
-- ROW LEVEL SECURITY - STUDENT PROFILES
-- ============================================================

ALTER TABLE public.student_profiles ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Students can view their own profile"
ON public.student_profiles;

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

DROP POLICY IF EXISTS "Students can insert their own profile"
ON public.student_profiles;

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

DROP POLICY IF EXISTS "Students can update their own profile"
ON public.student_profiles;

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


-- ============================================================
-- ROW LEVEL SECURITY - TASKS
-- ============================================================

ALTER TABLE public.tasks ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Students can view their own tasks"
ON public.tasks;

CREATE POLICY "Students can view their own tasks"
ON public.tasks
FOR SELECT
TO authenticated
USING (
    EXISTS (
        SELECT 1
        FROM public.users
        WHERE users.id = tasks.user_id
          AND users.clerk_id = (SELECT auth.jwt() ->> 'sub')
    )
);

DROP POLICY IF EXISTS "Students can insert their own tasks"
ON public.tasks;

CREATE POLICY "Students can insert their own tasks"
ON public.tasks
FOR INSERT
TO authenticated
WITH CHECK (
    EXISTS (
        SELECT 1
        FROM public.users
        WHERE users.id = tasks.user_id
          AND users.clerk_id = (SELECT auth.jwt() ->> 'sub')
    )
);

DROP POLICY IF EXISTS "Students can update their own tasks"
ON public.tasks;

CREATE POLICY "Students can update their own tasks"
ON public.tasks
FOR UPDATE
TO authenticated
USING (
    EXISTS (
        SELECT 1
        FROM public.users
        WHERE users.id = tasks.user_id
          AND users.clerk_id = (SELECT auth.jwt() ->> 'sub')
    )
)
WITH CHECK (
    EXISTS (
        SELECT 1
        FROM public.users
        WHERE users.id = tasks.user_id
          AND users.clerk_id = (SELECT auth.jwt() ->> 'sub')
    )
);

DROP POLICY IF EXISTS "Students can delete their own tasks"
ON public.tasks;

CREATE POLICY "Students can delete their own tasks"
ON public.tasks
FOR DELETE
TO authenticated
USING (
    EXISTS (
        SELECT 1
        FROM public.users
        WHERE users.id = tasks.user_id
          AND users.clerk_id = (SELECT auth.jwt() ->> 'sub')
    )
);


-- ============================================================
-- ROW LEVEL SECURITY - USERS
-- ============================================================

ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Students can view their own user record"
ON public.users;

CREATE POLICY "Students can view their own user record"
ON public.users
FOR SELECT
TO authenticated
USING (
    clerk_id = (SELECT auth.jwt() ->> 'sub')
);

