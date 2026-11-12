
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
    status VARCHAR(20) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'suspended', 'pending')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.users ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'active';


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
    goal_status VARCHAR(50) NOT NULL DEFAULT 'on_track' CHECK (goal_status IN ('ahead', 'on_track', 'behind', 'completed', 'paused')),
    onboarding_completed BOOLEAN DEFAULT TRUE
);

-- Migration for existing databases
ALTER TABLE public.student_profiles
ADD COLUMN IF NOT EXISTS subjects TEXT[] NOT NULL DEFAULT '{}';

ALTER TABLE public.student_profiles
ADD COLUMN IF NOT EXISTS goal_status VARCHAR(50) NOT NULL DEFAULT 'on_track';


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
ADD COLUMN IF NOT EXISTS is_completed BOOLEAN NOT NULL DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS scheduled_date DATE,
ADD COLUMN IF NOT EXISTS plan_session_key TEXT,
ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

CREATE INDEX IF NOT EXISTS idx_tasks_user_created
ON public.tasks(user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_tasks_user_scheduled
ON public.tasks(user_id, scheduled_date);

CREATE INDEX IF NOT EXISTS idx_tasks_user_id_completed
ON public.tasks(user_id, is_completed);

CREATE INDEX IF NOT EXISTS idx_tasks_user_completed_at
ON public.tasks(user_id, completed_at);



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


-- ============================================================
-- NOTIFICATIONS TABLE
-- ============================================================

CREATE TABLE IF NOT EXISTS public.notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL
        REFERENCES public.users(id) ON DELETE CASCADE,
    type TEXT NOT NULL DEFAULT 'system',
    title TEXT,
    message TEXT NOT NULL,
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    read_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_notifications_user_created
ON public.notifications(user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_notifications_user_unread
ON public.notifications(user_id, is_read)
WHERE is_read = FALSE;


-- ============================================================
-- ROW LEVEL SECURITY - NOTIFICATIONS
-- ============================================================

ALTER TABLE public.notifications ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Students can view their own notifications"
ON public.notifications;

CREATE POLICY "Students can view their own notifications"
ON public.notifications
FOR SELECT
TO authenticated
USING (
    EXISTS (
        SELECT 1
        FROM public.users
        WHERE users.id = notifications.user_id
          AND users.clerk_id = (SELECT auth.jwt() ->> 'sub')
    )
);

DROP POLICY IF EXISTS "Students can insert their own notifications"
ON public.notifications;

CREATE POLICY "Students can insert their own notifications"
ON public.notifications
FOR INSERT
TO authenticated
WITH CHECK (
    EXISTS (
        SELECT 1
        FROM public.users
        WHERE users.id = notifications.user_id
          AND users.clerk_id = (SELECT auth.jwt() ->> 'sub')
    )
);

DROP POLICY IF EXISTS "Students can update their own notifications"
ON public.notifications;

CREATE POLICY "Students can update their own notifications"
ON public.notifications
FOR UPDATE
TO authenticated
USING (
    EXISTS (
        SELECT 1
        FROM public.users
        WHERE users.id = notifications.user_id
          AND users.clerk_id = (SELECT auth.jwt() ->> 'sub')
    )
)
WITH CHECK (
    EXISTS (
        SELECT 1
        FROM public.users
        WHERE users.id = notifications.user_id
          AND users.clerk_id = (SELECT auth.jwt() ->> 'sub')
    )
);

DROP POLICY IF EXISTS "Students can delete their own notifications"
ON public.notifications;

CREATE POLICY "Students can delete their own notifications"
ON public.notifications
FOR DELETE
TO authenticated
USING (
    EXISTS (
        SELECT 1
        FROM public.users
        WHERE users.id = notifications.user_id
          AND users.clerk_id = (SELECT auth.jwt() ->> 'sub')
    )
);


-- ============================================================
-- LEADERBOARD & GOAL STATUS AGGREGATION VIEW & FUNCTIONS
-- ============================================================

CREATE OR REPLACE VIEW public.v_student_leaderboard AS
WITH student_stats AS (
    SELECT 
        u.id AS user_id,
        u.email,
        CASE 
            WHEN POSITION('@' IN u.email) > 3 THEN
                CONCAT(SUBSTRING(SPLIT_PART(u.email, '@', 1), 1, 3), '***@', SPLIT_PART(u.email, '@', 2))
            ELSE 
                CONCAT(SUBSTRING(u.email, 1, 1), '***')
        END AS display_name,
        COALESCE(sp.semester, 1) AS semester,
        COALESCE(sp.study_hours_per_day, 2.0) AS target_hours_per_day,
        COALESCE(sp.goal_status, 'on_track') AS goal_status,
        COALESCE(sp.goals, ARRAY[]::TEXT[]) AS primary_goals,
        COUNT(t.id) AS total_tasks,
        COUNT(t.id) FILTER (WHERE t.completed_at IS NOT NULL) AS completed_tasks,
        ROUND(COALESCE(SUM(
            COALESCE(
                NULLIF(REGEXP_REPLACE(t.description, '.*Duration: ([0-9.]+) hours.*', '\1'), t.description)::NUMERIC,
                1.0
            )
        ), 0), 1) AS planned_study_hours,
        ROUND(COALESCE(SUM(
            CASE 
                WHEN t.completed_at IS NOT NULL THEN 
                    COALESCE(
                        NULLIF(REGEXP_REPLACE(t.description, '.*Duration: ([0-9.]+) hours.*', '\1'), t.description)::NUMERIC,
                        1.0
                    )
                ELSE 0 
            END
        ), 0), 1) AS actual_study_hours,
        ROUND(
            COALESCE(
                COUNT(t.id) FILTER (WHERE t.completed_at IS NOT NULL)::NUMERIC / NULLIF(COUNT(t.id), 0) * 100,
                0
            ), 
            1
        ) AS completion_rate
    FROM public.users u
    LEFT JOIN public.student_profiles sp ON u.id = sp.user_id
    LEFT JOIN public.tasks t ON u.id = t.user_id
    WHERE u.role = 'student'
    GROUP BY u.id, u.email, sp.semester, sp.study_hours_per_day, sp.goal_status, sp.goals
)
SELECT 
    DENSE_RANK() OVER (
        ORDER BY 
            s.actual_study_hours DESC,
            s.completion_rate DESC,
            s.completed_tasks DESC
    ) AS rank,
    s.user_id,
    s.display_name,
    s.semester,
    s.target_hours_per_day,
    s.goal_status,
    CASE
        WHEN s.total_tasks = 0 THEN 'not_started'
        WHEN s.completion_rate >= 80.0 THEN 'ahead'
        WHEN s.completion_rate >= 50.0 THEN 'on_track'
        ELSE 'behind'
    END AS calculated_goal_status,
    s.primary_goals,
    s.total_tasks,
    s.completed_tasks,
    s.planned_study_hours,
    s.actual_study_hours,
    s.completion_rate
FROM student_stats s;

CREATE OR REPLACE FUNCTION public.get_student_leaderboard(
    p_limit INT DEFAULT 50,
    p_offset INT DEFAULT 0,
    p_semester INT DEFAULT NULL
)
RETURNS TABLE (
    rank BIGINT,
    user_id UUID,
    display_name TEXT,
    semester INT,
    target_hours_per_day DOUBLE PRECISION,
    goal_status VARCHAR(50),
    calculated_goal_status TEXT,
    primary_goals TEXT[],
    total_tasks BIGINT,
    completed_tasks BIGINT,
    planned_study_hours NUMERIC,
    actual_study_hours NUMERIC,
    completion_rate NUMERIC
)
LANGUAGE sql
STABLE
SECURITY DEFINER
AS $$
    SELECT 
        l.rank,
        l.user_id,
        l.display_name,
        l.semester,
        l.target_hours_per_day,
        l.goal_status,
        l.calculated_goal_status,
        l.primary_goals,
        l.total_tasks,
        l.completed_tasks,
        l.planned_study_hours,
        l.actual_study_hours,
        l.completion_rate
    FROM public.v_student_leaderboard l
    WHERE (p_semester IS NULL OR l.semester = p_semester)
    ORDER BY l.rank ASC
    LIMIT GREATEST(1, LEAST(p_limit, 100))
    OFFSET GREATEST(0, p_offset);
$$;

GRANT SELECT ON public.v_student_leaderboard TO authenticated, anon;
GRANT EXECUTE ON FUNCTION public.get_student_leaderboard(INT, INT, INT) TO authenticated, anon;


-- ============================================================
-- LEARNING RESOURCES TABLE (ADMIN MANAGED CATALOG)
-- ============================================================

CREATE TABLE IF NOT EXISTS public.learning_resources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    description TEXT,
    url TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'course',
    subject TEXT,
    provider TEXT,
    difficulty TEXT DEFAULT 'intermediate',
    rating NUMERIC(3, 2),
    tags TEXT[] DEFAULT '{}',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_by UUID REFERENCES public.users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_learning_resources_category ON public.learning_resources(category);
CREATE INDEX IF NOT EXISTS idx_learning_resources_subject ON public.learning_resources(subject);
CREATE INDEX IF NOT EXISTS idx_learning_resources_is_active ON public.learning_resources(is_active);

ALTER TABLE public.learning_resources ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Public can view active learning resources" ON public.learning_resources;
CREATE POLICY "Public can view active learning resources"
ON public.learning_resources
FOR SELECT
TO authenticated, anon
USING (is_active = TRUE);

DROP POLICY IF EXISTS "Admins have full access to learning resources" ON public.learning_resources;
CREATE POLICY "Admins have full access to learning resources"
ON public.learning_resources
FOR ALL
TO authenticated
USING (
    EXISTS (
        SELECT 1 FROM public.users
        WHERE users.clerk_id = (SELECT auth.jwt() ->> 'sub')
          AND users.role = 'admin'
    )
)
WITH CHECK (
    EXISTS (
        SELECT 1 FROM public.users
        WHERE users.clerk_id = (SELECT auth.jwt() ->> 'sub')
          AND users.role = 'admin'
    )
);


-- ============================================================
-- GLOBAL SUBJECTS CATALOG TABLE
-- ============================================================

CREATE TABLE IF NOT EXISTS public.subjects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    semester INT NOT NULL CHECK (semester BETWEEN 1 AND 8),
    department TEXT NOT NULL DEFAULT 'Computer Science',
    credits NUMERIC(3, 1) NOT NULL DEFAULT 3.0,
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_subjects_semester ON public.subjects(semester);
CREATE INDEX IF NOT EXISTS idx_subjects_department ON public.subjects(department);
CREATE INDEX IF NOT EXISTS idx_subjects_is_active ON public.subjects(is_active);

ALTER TABLE public.subjects ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Public can view active subjects" ON public.subjects;
CREATE POLICY "Public can view active subjects"
ON public.subjects
FOR SELECT
TO authenticated, anon
USING (is_active = TRUE);

DROP POLICY IF EXISTS "Admins have full access to subjects" ON public.subjects;
CREATE POLICY "Admins have full access to subjects"
ON public.subjects
FOR ALL
TO authenticated
USING (
    EXISTS (
        SELECT 1 FROM public.users
        WHERE users.clerk_id = (SELECT auth.jwt() ->> 'sub')
          AND users.role = 'admin'
    )
)
WITH CHECK (
    EXISTS (
        SELECT 1 FROM public.users
        WHERE users.clerk_id = (SELECT auth.jwt() ->> 'sub')
          AND users.role = 'admin'
    )
);


-- ============================================================
-- STUDY SESSIONS & LEADERBOARD ACCELERATION INDEXES
-- ============================================================

CREATE TABLE IF NOT EXISTS public.study_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    task_id UUID REFERENCES public.tasks(id) ON DELETE CASCADE,
    subject TEXT NOT NULL DEFAULT 'General Study',
    duration_minutes INT NOT NULL DEFAULT 60,
    session_date DATE NOT NULL DEFAULT CURRENT_DATE,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Ensure columns exist if study_sessions pre-existed
ALTER TABLE public.study_sessions
ADD COLUMN IF NOT EXISTS session_date DATE NOT NULL DEFAULT CURRENT_DATE;

ALTER TABLE public.study_sessions
ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ;

ALTER TABLE public.study_sessions
ADD COLUMN IF NOT EXISTS subject TEXT NOT NULL DEFAULT 'General Study';

ALTER TABLE public.study_sessions
ADD COLUMN IF NOT EXISTS is_completed BOOLEAN NOT NULL DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS idx_users_role_status ON public.users(role, status);
CREATE INDEX IF NOT EXISTS idx_users_created_at ON public.users(created_at);

CREATE INDEX IF NOT EXISTS idx_tasks_user_completed_at ON public.tasks(user_id, completed_at);
CREATE INDEX IF NOT EXISTS idx_tasks_scheduled_date ON public.tasks(scheduled_date);
CREATE INDEX IF NOT EXISTS idx_tasks_user_scheduled ON public.tasks(user_id, scheduled_date);

CREATE INDEX IF NOT EXISTS idx_study_sessions_user_id ON public.study_sessions(user_id);

DO $$
BEGIN
    EXECUTE 'CREATE INDEX IF NOT EXISTS idx_study_sessions_session_date ON public.study_sessions(session_date)';
    EXECUTE 'CREATE INDEX IF NOT EXISTS idx_study_sessions_completed ON public.study_sessions(completed_at)';
EXCEPTION
    WHEN OTHERS THEN NULL;
END $$;


-- ============================================================
-- CACHED LEADERBOARD TABLE & REFRESH PROCEDURE
-- ============================================================

CREATE TABLE IF NOT EXISTS public.leaderboard_ranks (
    user_id UUID PRIMARY KEY REFERENCES public.users(id) ON DELETE CASCADE,
    rank BIGINT NOT NULL,
    display_name TEXT NOT NULL,
    semester INT NOT NULL,
    target_hours_per_day DOUBLE PRECISION NOT NULL DEFAULT 2.0,
    goal_status VARCHAR(50) NOT NULL DEFAULT 'on_track',
    calculated_goal_status TEXT NOT NULL DEFAULT 'on_track',
    primary_goals TEXT[] DEFAULT '{}',
    total_tasks BIGINT NOT NULL DEFAULT 0,
    completed_tasks BIGINT NOT NULL DEFAULT 0,
    planned_study_hours NUMERIC NOT NULL DEFAULT 0.0,
    actual_study_hours NUMERIC NOT NULL DEFAULT 0.0,
    completion_rate NUMERIC NOT NULL DEFAULT 0.0,
    last_evaluated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Safely remove unmasked email column if table pre-existed with email
ALTER TABLE public.leaderboard_ranks DROP COLUMN IF EXISTS email;

CREATE INDEX IF NOT EXISTS idx_leaderboard_ranks_rank ON public.leaderboard_ranks(rank ASC);
CREATE INDEX IF NOT EXISTS idx_leaderboard_ranks_semester ON public.leaderboard_ranks(semester);

-- Enable Row Level Security (RLS) on cached leaderboard
ALTER TABLE public.leaderboard_ranks ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Public can view leaderboard rankings" ON public.leaderboard_ranks;
CREATE POLICY "Public can view leaderboard rankings"
ON public.leaderboard_ranks
FOR SELECT
TO authenticated, anon
USING (TRUE);

CREATE OR REPLACE FUNCTION public.refresh_leaderboard_rankings()
RETURNS INT
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_rows_inserted INT := 0;
BEGIN
    TRUNCATE TABLE public.leaderboard_ranks;

    INSERT INTO public.leaderboard_ranks (
        user_id,
        rank,
        display_name,
        semester,
        target_hours_per_day,
        goal_status,
        calculated_goal_status,
        primary_goals,
        total_tasks,
        completed_tasks,
        planned_study_hours,
        actual_study_hours,
        completion_rate,
        last_evaluated_at
    )
    SELECT 
        l.user_id,
        l.rank,
        l.display_name,
        l.semester,
        l.target_hours_per_day,
        l.goal_status,
        l.calculated_goal_status,
        l.primary_goals,
        l.total_tasks,
        l.completed_tasks,
        l.planned_study_hours,
        l.actual_study_hours,
        l.completion_rate,
        NOW()
    FROM public.v_student_leaderboard l
    JOIN public.users u ON l.user_id = u.id
    WHERE u.status = 'active';

    GET DIAGNOSTICS v_rows_inserted = ROW_COUNT;
    RETURN v_rows_inserted;
END;
$$;

-- Security Hardening: Revoke execution from PUBLIC, authenticated, and anon
REVOKE ALL ON FUNCTION public.refresh_leaderboard_rankings() FROM PUBLIC;
REVOKE ALL ON FUNCTION public.refresh_leaderboard_rankings() FROM authenticated;
REVOKE ALL ON FUNCTION public.refresh_leaderboard_rankings() FROM anon;

-- Grant execution ONLY to service_role (for pg_cron and backend admin cron worker)
GRANT EXECUTE ON FUNCTION public.refresh_leaderboard_rankings() TO service_role;


