-- ============================================================
-- SMART LEARNING PLANNER - ADMIN CONTROLS, INDEXES & MIDNIGHT CRON
-- ============================================================
-- Author: Heman Parashar (Backend & Database)
-- Date: 2026-11-12
--
-- Features:
-- 1. Prerequisites: Ensure required columns exist on users, tasks, profiles.
-- 2. Leaderboard Aggregation View (v_student_leaderboard) using completed_at.
-- 3. Student Account Status ('active', 'suspended') on public.users.
-- 4. Global University Subjects Catalog Table (public.subjects).
-- 5. High-Performance PostgreSQL Indexes on users, tasks, and study_sessions.
-- 6. Cached Leaderboard Table (public.leaderboard_ranks) & Midnight Cron (0 0 * * *).
-- 7. Security Hardening: Restrict refresh procedure to service_role and protect PII.
-- ============================================================

-- ------------------------------------------------------------
-- 1. PREREQUISITES & SCHEMA EVOLUTION (Ensuring columns exist)
-- ------------------------------------------------------------

-- Add required columns to tasks table safely
ALTER TABLE public.tasks
ADD COLUMN IF NOT EXISTS is_completed BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE public.tasks
ADD COLUMN IF NOT EXISTS scheduled_date DATE;

ALTER TABLE public.tasks
ADD COLUMN IF NOT EXISTS plan_session_key TEXT;

ALTER TABLE public.tasks
ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ;

ALTER TABLE public.tasks
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

-- Ensure student_profiles has goal_status
ALTER TABLE public.student_profiles
ADD COLUMN IF NOT EXISTS goal_status VARCHAR(50) NOT NULL DEFAULT 'on_track';

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'chk_student_profiles_goal_status'
    ) THEN
        ALTER TABLE public.student_profiles
        ADD CONSTRAINT chk_student_profiles_goal_status
        CHECK (goal_status IN ('ahead', 'on_track', 'behind', 'completed', 'paused'));
    END IF;
EXCEPTION
    WHEN OTHERS THEN NULL;
END $$;

-- Ensure users has account status
ALTER TABLE public.users
ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'active';

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'chk_users_status'
    ) THEN
        ALTER TABLE public.users
        ADD CONSTRAINT chk_users_status
        CHECK (status IN ('active', 'suspended', 'pending'));
    END IF;
EXCEPTION
    WHEN OTHERS THEN NULL;
END $$;


-- ------------------------------------------------------------
-- 2. LEADERBOARD AGGREGATION VIEW (Base for Rankings)
-- ------------------------------------------------------------
-- Uses t.completed_at IS NOT NULL as the completion indicator

CREATE OR REPLACE VIEW public.v_student_leaderboard AS
WITH student_stats AS (
    SELECT 
        u.id AS user_id,
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

GRANT SELECT ON public.v_student_leaderboard TO authenticated, anon;


-- ------------------------------------------------------------
-- 3. GLOBAL SUBJECTS CATALOG TABLE & RLS
-- ------------------------------------------------------------

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


-- ------------------------------------------------------------
-- 4. STUDY SESSIONS TABLE & HIGH-PERFORMANCE INDEXES
-- ------------------------------------------------------------

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

-- Ensure columns exist if study_sessions was created in an earlier schema
ALTER TABLE public.study_sessions
ADD COLUMN IF NOT EXISTS session_date DATE NOT NULL DEFAULT CURRENT_DATE;

ALTER TABLE public.study_sessions
ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ;

ALTER TABLE public.study_sessions
ADD COLUMN IF NOT EXISTS subject TEXT NOT NULL DEFAULT 'General Study';

ALTER TABLE public.study_sessions
ADD COLUMN IF NOT EXISTS is_completed BOOLEAN NOT NULL DEFAULT FALSE;

-- Comprehensive indexes on users and tasks
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

-- RLS for Study Sessions
ALTER TABLE public.study_sessions ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Students can view and manage their own study sessions" ON public.study_sessions;
CREATE POLICY "Students can view and manage their own study sessions"
ON public.study_sessions
FOR ALL
TO authenticated
USING (
    EXISTS (
        SELECT 1 FROM public.users
        WHERE users.id = study_sessions.user_id
          AND users.clerk_id = (SELECT auth.jwt() ->> 'sub')
    )
)
WITH CHECK (
    EXISTS (
        SELECT 1 FROM public.users
        WHERE users.id = study_sessions.user_id
          AND users.clerk_id = (SELECT auth.jwt() ->> 'sub')
    )
);


-- ------------------------------------------------------------
-- 5. CACHED LEADERBOARD TABLE & MIDNIGHT EVALUATION
-- ------------------------------------------------------------

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

-- Stored Procedure: Evaluates and updates rankings in leaderboard_ranks
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


-- ------------------------------------------------------------
-- 6. SCHEDULED PG_CRON TRIGGER (Every Night at Midnight)
-- ------------------------------------------------------------
-- Schedule: 0 0 * * * (Midnight in UTC / system time)

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_extension WHERE extname = 'pg_cron'
    ) THEN
        PERFORM cron.unschedule('midnight_leaderboard_evaluation');
        PERFORM cron.schedule(
            'midnight_leaderboard_evaluation',
            '0 0 * * *',
            'SELECT public.refresh_leaderboard_rankings();'
        );
    END IF;
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'pg_cron extension not active. Midnight refresh managed by backend cron runner.';
END $$;
