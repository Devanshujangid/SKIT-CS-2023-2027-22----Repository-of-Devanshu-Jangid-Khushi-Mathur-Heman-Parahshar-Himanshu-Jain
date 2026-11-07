-- ============================================================
-- MIGRATION: NOTIFICATION ENGINE STORED PROCEDURE & PG_CRON SETUP
-- ============================================================
-- Description:
--   Automated daily notification engine running directly inside PostgreSQL / Supabase.
--   Pushes daily alerts for:
--     1. "Upcoming Exams" (from scheduled tasks & plan milestones)
--     2. "Unresolved Weak Topics" (from study deficits & priority sessions)
--   Enforces deduplication within 24 hours to prevent notification spam.
-- ============================================================

CREATE OR REPLACE FUNCTION public.dispatch_daily_exam_and_weak_topic_alerts()
RETURNS TABLE (
    user_id UUID,
    alert_type TEXT,
    title TEXT,
    message TEXT
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    rec RECORD;
    v_now TIMESTAMPTZ := NOW();
    v_inserted_count INT := 0;
BEGIN
    -- -------------------------------------------------------------
    -- 1. DETECT UPCOMING EXAMS / ASSESSMENTS (Tasks within 7 days)
    -- -------------------------------------------------------------
    FOR rec IN
        SELECT 
            t.user_id,
            'exam'::TEXT AS notif_type,
            ('Upcoming Assessment in ' || (t.scheduled_date - CURRENT_DATE)::TEXT || ' Day(s)')::TEXT AS notif_title,
            ('Assessment "' || t.title || '" is scheduled for ' || t.scheduled_date::TEXT || '. Complete topic reviews and practice tests.')::TEXT AS notif_msg
        FROM public.tasks t
        WHERE t.is_completed = FALSE
          AND t.scheduled_date >= CURRENT_DATE
          AND t.scheduled_date <= (CURRENT_DATE + INTERVAL '7 days')
          AND (
              LOWER(t.title) ~ '(exam|midterm|test|quiz|assessment|gate|final|evaluation)'
              OR LOWER(COALESCE(t.description, '')) ~ '(exam|midterm|test|quiz|assessment|gate|final|evaluation)'
          )
    LOOP
        -- Check duplicate within 24h or unread matching title
        IF NOT EXISTS (
            SELECT 1 FROM public.notifications n
            WHERE n.user_id = rec.user_id
              AND n.type = rec.notif_type
              AND (
                  n.title = rec.notif_title
                  OR (n.is_read = FALSE AND n.title LIKE 'Upcoming Assessment%')
                  OR (n.created_at >= v_now - INTERVAL '24 hours' AND n.title = rec.notif_title)
              )
        ) THEN
            INSERT INTO public.notifications (user_id, type, title, message, is_read, created_at)
            VALUES (rec.user_id, rec.notif_type, rec.notif_title, rec.notif_msg, FALSE, v_now);

            user_id := rec.user_id;
            alert_type := rec.notif_type;
            title := rec.notif_title;
            message := rec.notif_msg;
            RETURN NEXT;
        END IF;
    END LOOP;

    -- -------------------------------------------------------------
    -- 2. DETECT UPCOMING EXAM MILESTONES (From Active Study Plans)
    -- -------------------------------------------------------------
    FOR rec IN
        SELECT 
            sp.user_id,
            'exam'::TEXT AS notif_type,
            ('Upcoming Exam Milestone: Week ' || (m->>'week'))::TEXT AS notif_title,
            ('Milestone: "' || (m->>'milestone') || '". Target deliverable: "' || (m->>'key_deliverable') || '". Review your prerequisite sessions.')::TEXT AS notif_msg
        FROM public.study_plans sp,
             LATERAL jsonb_array_elements(sp.plan_data->'monthly_milestones') AS m
        WHERE sp.is_active = TRUE
          AND (
              LOWER(m->>'milestone') ~ '(exam|midterm|test|quiz|assessment|gate|final|revision benchmark)'
              OR LOWER(m->>'key_deliverable') ~ '(exam|midterm|test|quiz|assessment|gate|final|revision benchmark)'
          )
    LOOP
        IF NOT EXISTS (
            SELECT 1 FROM public.notifications n
            WHERE n.user_id = rec.user_id
              AND n.type = rec.notif_type
              AND (
                  n.title = rec.notif_title
                  OR (n.is_read = FALSE AND n.title = rec.notif_title)
                  OR (n.created_at >= v_now - INTERVAL '24 hours' AND n.title = rec.notif_title)
              )
        ) THEN
            INSERT INTO public.notifications (user_id, type, title, message, is_read, created_at)
            VALUES (rec.user_id, rec.notif_type, rec.notif_title, rec.notif_msg, FALSE, v_now);

            user_id := rec.user_id;
            alert_type := rec.notif_type;
            title := rec.notif_title;
            message := rec.notif_msg;
            RETURN NEXT;
        END IF;
    END LOOP;

    -- -------------------------------------------------------------
    -- 3. DETECT UNRESOLVED WEAK TOPICS (Incomplete/Missed Sessions)
    -- -------------------------------------------------------------
    FOR rec IN
        SELECT 
            t.user_id,
            'weak_topic'::TEXT AS notif_type,
            ('Unresolved Weak Topic: ' || SPLIT_PART(t.title, ':', 1))::TEXT AS notif_title,
            ('[HIGH PRIORITY] Missed study session in "' || t.title || '". Please review or adapt your schedule.')::TEXT AS notif_msg
        FROM public.tasks t
        WHERE t.is_completed = FALSE
          AND t.scheduled_date < CURRENT_DATE
        GROUP BY t.user_id, SPLIT_PART(t.title, ':', 1), t.title
        HAVING COUNT(t.id) >= 1
    LOOP
        IF NOT EXISTS (
            SELECT 1 FROM public.notifications n
            WHERE n.user_id = rec.user_id
              AND n.type = rec.notif_type
              AND (
                  n.title = rec.notif_title
                  OR (n.is_read = FALSE AND n.title = rec.notif_title)
                  OR (n.created_at >= v_now - INTERVAL '24 hours' AND n.title = rec.notif_title)
              )
        ) THEN
            INSERT INTO public.notifications (user_id, type, title, message, is_read, created_at)
            VALUES (rec.user_id, rec.notif_type, rec.notif_title, rec.notif_msg, FALSE, v_now);

            user_id := rec.user_id;
            alert_type := rec.notif_type;
            title := rec.notif_title;
            message := rec.notif_msg;
            RETURN NEXT;
        END IF;
    END LOOP;

    RETURN;
END;
$$;


-- ============================================================
-- SUPABASE PG_CRON SCHEDULE (Daily at 08:00 AM UTC)
-- ============================================================
-- Note: Enable the pg_cron extension in Supabase Dashboard -> Database -> Extensions
--
-- CREATE EXTENSION IF NOT EXISTS pg_cron;
--
-- SELECT cron.schedule(
--     'daily-notification-dispatch',
--     '0 8 * * *',
--     $$SELECT public.dispatch_daily_exam_and_weak_topic_alerts();$$
-- );

