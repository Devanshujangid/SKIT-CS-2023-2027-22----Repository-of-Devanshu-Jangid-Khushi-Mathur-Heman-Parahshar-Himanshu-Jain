-- ============================================================
-- SMART LEARNING PLANNER - LEADERBOARD & GOAL STATUS MIGRATION
-- ============================================================
-- Feature: Student Leaderboard & Academic Engagement Ranking
-- Author: Heman Parashar (Backend & Database)
-- Date: 2026-11-12
--
-- Objectives:
-- 1. Add `goal_status` column to `student_profiles` and `study_plans`.
-- 2. Create high-performance SQL aggregation view for the Leaderboard.
-- 3. Create stored procedure `public.get_student_leaderboard` for paginated RPC calls.
-- 4. Provide RLS policies allowing authenticated students to view rankings.
-- ============================================================

-- ------------------------------------------------------------
-- 1. SCHEMA EVOLUTION: Add required columns
-- ------------------------------------------------------------

-- Ensure public.tasks has completion and schedule columns
ALTER TABLE public.tasks
ADD COLUMN IF NOT EXISTS is_completed BOOLEAN NOT NULL DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS scheduled_date DATE,
ADD COLUMN IF NOT EXISTS plan_session_key TEXT,
ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

-- Add goal_status to public.student_profiles
ALTER TABLE public.student_profiles
ADD COLUMN IF NOT EXISTS goal_status VARCHAR(50) NOT NULL DEFAULT 'on_track';

-- Add check constraint for valid goal statuses
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'chk_student_profiles_goal_status'
    ) THEN
        ALTER TABLE public.student_profiles
        ADD CONSTRAINT chk_student_profiles_goal_status
        CHECK (goal_status IN ('ahead', 'on_track', 'behind', 'completed', 'paused'));
    END IF;
END $$;

-- Add goal_status to public.study_plans for version-specific status tracking
ALTER TABLE public.study_plans
ADD COLUMN IF NOT EXISTS goal_status VARCHAR(50) NOT NULL DEFAULT 'in_progress';

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'chk_study_plans_goal_status'
    ) THEN
        ALTER TABLE public.study_plans
        ADD CONSTRAINT chk_study_plans_goal_status
        CHECK (goal_status IN ('not_started', 'in_progress', 'completed', 'behind', 'ahead'));
    END IF;
END $$;

-- Index for fast status queries
CREATE INDEX IF NOT EXISTS idx_student_profiles_goal_status
ON public.student_profiles(goal_status);


-- ------------------------------------------------------------
-- 2. LEADERBOARD AGGREGATION VIEW
-- ------------------------------------------------------------
-- Aggregates total actual study hours, scheduled study hours, 
-- completed task count, and completion rate per student.
-- Computes deterministic ranks using DENSE_RANK().

CREATE OR REPLACE VIEW public.v_student_leaderboard AS
WITH student_stats AS (
    SELECT 
        u.id AS user_id,
        u.email,
        -- Display name: masked email for peer privacy (e.g. joh***@skit.ac.in)
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
        
        -- Task & session counts
        COUNT(t.id) AS total_tasks,
        COUNT(t.id) FILTER (WHERE t.completed_at IS NOT NULL) AS completed_tasks,
        
        -- Planned study hours
        ROUND(COALESCE(SUM(
            COALESCE(
                NULLIF(REGEXP_REPLACE(t.description, '.*Duration: ([0-9.]+) hours.*', '\1'), t.description)::NUMERIC,
                1.0
            )
        ), 0), 1) AS planned_study_hours,
        
        -- Actual study hours completed
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
        
        -- Completion rate percentage (0.0% to 100.0%)
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
    -- Window rank: 1. Actual study hours DESC, 2. Completion rate DESC, 3. Completed tasks DESC
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
    -- Dynamically derived goal status based on study momentum
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


-- ------------------------------------------------------------
-- 3. STORED PROCEDURE: RPC Function with filtering & pagination
-- ------------------------------------------------------------

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

-- Grant execution permissions
GRANT SELECT ON public.v_student_leaderboard TO authenticated, anon;
GRANT EXECUTE ON FUNCTION public.get_student_leaderboard(INT, INT, INT) TO authenticated, anon;
