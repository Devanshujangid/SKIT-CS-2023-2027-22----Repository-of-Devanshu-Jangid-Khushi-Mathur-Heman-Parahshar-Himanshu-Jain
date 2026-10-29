-- ============================================================
-- SMART LEARNING PLANNER - ANALYTICS AGGREGATION MIGRATION
-- ============================================================
-- Module 8: Academic Progress & Telemetry Analytics
-- Role Separations: 'student' vs 'admin'
-- Aggregations: Actual Study Minutes by Subject, Weekly Performance, Completion Rates
-- ============================================================

-- 1. Subject Study Minutes Aggregation
CREATE OR REPLACE FUNCTION public.get_subject_study_minutes(p_user_id UUID)
RETURNS TABLE (
    subject TEXT,
    total_sessions BIGINT,
    planned_minutes NUMERIC,
    actual_minutes NUMERIC,
    mastery_percentage NUMERIC
)
LANGUAGE sql
STABLE
SECURITY DEFINER
AS $$
    SELECT 
        COALESCE(SPLIT_PART(t.title, ':', 1), 'General Study') AS subject,
        COUNT(*) AS total_sessions,
        ROUND(SUM(
            COALESCE(
                NULLIF(REGEXP_REPLACE(t.description, '.*Duration: ([0-9.]+) hours.*', '\1'), t.description)::NUMERIC * 60,
                60
            )
        ), 0) AS planned_minutes,
        ROUND(SUM(
            CASE 
                WHEN t.is_completed = TRUE THEN 
                    COALESCE(
                        NULLIF(REGEXP_REPLACE(t.description, '.*Duration: ([0-9.]+) hours.*', '\1'), t.description)::NUMERIC * 60,
                        60
                    )
                ELSE 0 
            END
        ), 0) AS actual_minutes,
        ROUND(
            COUNT(*) FILTER (WHERE t.is_completed = TRUE)::NUMERIC / NULLIF(COUNT(*), 0) * 100, 
            1
        ) AS mastery_percentage
    FROM public.tasks t
    WHERE t.user_id = p_user_id
    GROUP BY COALESCE(SPLIT_PART(t.title, ':', 1), 'General Study')
    ORDER BY actual_minutes DESC;
$$;


-- 2. Weekly Performance by Scheduled Day
CREATE OR REPLACE FUNCTION public.get_weekly_performance_by_day(p_user_id UUID)
RETURNS TABLE (
    day_name TEXT,
    day_index DOUBLE PRECISION,
    scheduled_hours NUMERIC,
    actual_hours NUMERIC,
    deficit_hours NUMERIC,
    completion_percentage NUMERIC
)
LANGUAGE sql
STABLE
SECURITY DEFINER
AS $$
    SELECT 
        TO_CHAR(t.scheduled_date, 'Dy') AS day_name,
        EXTRACT(ISODOW FROM t.scheduled_date) AS day_index,
        ROUND(SUM(
            COALESCE(
                NULLIF(REGEXP_REPLACE(t.description, '.*Duration: ([0-9.]+) hours.*', '\1'), t.description)::NUMERIC,
                1.0
            )
        ), 1) AS scheduled_hours,
        ROUND(SUM(
            CASE 
                WHEN t.is_completed = TRUE THEN 
                    COALESCE(
                        NULLIF(REGEXP_REPLACE(t.description, '.*Duration: ([0-9.]+) hours.*', '\1'), t.description)::NUMERIC,
                        1.0
                    )
                ELSE 0 
            END
        ), 1) AS actual_hours,
        ROUND(
            GREATEST(0, 
                SUM(COALESCE(NULLIF(REGEXP_REPLACE(t.description, '.*Duration: ([0-9.]+) hours.*', '\1'), t.description)::NUMERIC, 1.0)) -
                SUM(CASE WHEN t.is_completed = TRUE THEN COALESCE(NULLIF(REGEXP_REPLACE(t.description, '.*Duration: ([0-9.]+) hours.*', '\1'), t.description)::NUMERIC, 1.0) ELSE 0 END)
            ), 1
        ) AS deficit_hours,
        ROUND(
            COUNT(*) FILTER (WHERE t.is_completed = TRUE)::NUMERIC / NULLIF(COUNT(*), 0) * 100,
            0
        ) AS completion_percentage
    FROM public.tasks t
    WHERE t.user_id = p_user_id
      AND t.scheduled_date IS NOT NULL
    GROUP BY TO_CHAR(t.scheduled_date, 'Dy'), EXTRACT(ISODOW FROM t.scheduled_date)
    ORDER BY day_index ASC;
$$;


-- 3. Comprehensive Analytics Summary (RPC Endpoint)
CREATE OR REPLACE FUNCTION public.get_student_study_analytics(p_user_id UUID)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_overview JSONB;
    v_subjects JSONB;
    v_weekly JSONB;
BEGIN
    -- 1. Overview & Completion Rates
    SELECT json_build_object(
        'total_tasks', COUNT(*),
        'completed_tasks', COUNT(*) FILTER (WHERE is_completed = TRUE),
        'missed_tasks', COUNT(*) FILTER (WHERE is_completed = FALSE AND scheduled_date < CURRENT_DATE),
        'completion_rate', ROUND(COUNT(*) FILTER (WHERE is_completed = TRUE)::NUMERIC / NULLIF(COUNT(*), 0) * 100, 1)
    ) INTO v_overview
    FROM public.tasks WHERE user_id = p_user_id;

    -- 2. Subject Distribution
    SELECT json_agg(s) INTO v_subjects FROM (
        SELECT 
            COALESCE(SPLIT_PART(title, ':', 1), 'General Study') AS name,
            COUNT(*) AS sessions_count,
            ROUND(COUNT(*) FILTER (WHERE is_completed = TRUE)::NUMERIC / NULLIF(COUNT(*), 0) * 100, 0) AS mastery
        FROM public.tasks
        WHERE user_id = p_user_id
        GROUP BY COALESCE(SPLIT_PART(title, ':', 1), 'General Study')
        ORDER BY COUNT(*) DESC
    ) s;

    -- 3. Weekly Day-by-Day Breakdown
    SELECT json_agg(w) INTO v_weekly FROM (
        SELECT 
            TO_CHAR(scheduled_date, 'Dy') AS day,
            COUNT(*) AS tasks_scheduled,
            COUNT(*) FILTER (WHERE is_completed = TRUE) AS tasks_completed
        FROM public.tasks
        WHERE user_id = p_user_id AND scheduled_date IS NOT NULL
        GROUP BY TO_CHAR(scheduled_date, 'Dy'), EXTRACT(ISODOW FROM scheduled_date)
        ORDER BY EXTRACT(ISODOW FROM scheduled_date)
    ) w;

    RETURN json_build_object(
        'overview', COALESCE(v_overview, '{}'::JSONB),
        'subject_distribution', COALESCE(v_subjects, '[]'::JSONB),
        'weekly_performance', COALESCE(v_weekly, '[]'::JSONB)
    );
END;
$$;
