-- ============================================================
-- MIGRATION: NOTIFICATIONS TABLE & ROW LEVEL SECURITY
-- ============================================================
-- Table: public.notifications
-- Columns:
--   - id: UUID Primary Key (gen_random_uuid())
--   - user_id: UUID Foreign Key -> public.users(id) ON DELETE CASCADE
--   - type: TEXT ('system', 'reminder', 'alert', 'rebalance', 'achievement')
--   - message: TEXT Notification body
--   - is_read: BOOLEAN Default FALSE
--   - read_at: TIMESTAMPTZ Timestamp when read
--   - created_at: TIMESTAMPTZ Default NOW()
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

-- Ensure fast lookup for user notifications ordered by recency
CREATE INDEX IF NOT EXISTS idx_notifications_user_created
ON public.notifications(user_id, created_at DESC);

-- Ensure fast lookup for unread notifications counter
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

