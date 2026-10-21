
-- 1. Allow multiple study plan versions per user.
ALTER TABLE public.study_plans
DROP CONSTRAINT IF EXISTS unique_user_study_plan;

-- 2. Enforce at most one active plan per user.
CREATE UNIQUE INDEX IF NOT EXISTS idx_study_plans_one_active_per_user
ON public.study_plans (user_id)
WHERE is_active = TRUE;

-- 3. Atomically create and activate a new plan version.
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
