
-- Sprint 9: Admin Learning Resources
-- Separate migration; frozen schema.sql remains unchanged.

CREATE TABLE IF NOT EXISTS public.learning_resources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    url TEXT NOT NULL,
    category TEXT,
    subject TEXT,
    tags TEXT[] NOT NULL DEFAULT '{}',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_by UUID REFERENCES public.users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_learning_resources_active
ON public.learning_resources(is_active);

CREATE INDEX IF NOT EXISTS idx_learning_resources_subject
ON public.learning_resources(subject);

ALTER TABLE public.learning_resources ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Authenticated users can view active resources"
ON public.learning_resources;

CREATE POLICY "Authenticated users can view active resources"
ON public.learning_resources
FOR SELECT
TO authenticated
USING (is_active = TRUE);

DROP POLICY IF EXISTS "Admins can insert resources"
ON public.learning_resources;

CREATE POLICY "Admins can insert resources"
ON public.learning_resources
FOR INSERT
TO authenticated
WITH CHECK (
    EXISTS (
        SELECT 1
        FROM public.users
        WHERE users.clerk_id = (SELECT auth.jwt() ->> 'sub')
          AND users.role = 'admin'
    )
);

DROP POLICY IF EXISTS "Admins can update resources"
ON public.learning_resources;

CREATE POLICY "Admins can update resources"
ON public.learning_resources
FOR UPDATE
TO authenticated
USING (
    EXISTS (
        SELECT 1
        FROM public.users
        WHERE users.clerk_id = (SELECT auth.jwt() ->> 'sub')
          AND users.role = 'admin'
    )
)
WITH CHECK (
    EXISTS (
        SELECT 1
        FROM public.users
        WHERE users.clerk_id = (SELECT auth.jwt() ->> 'sub')
          AND users.role = 'admin'
    )
);

DROP POLICY IF EXISTS "Admins can delete resources"
ON public.learning_resources;

CREATE POLICY "Admins can delete resources"
ON public.learning_resources
FOR DELETE
TO authenticated
USING (
    EXISTS (
        SELECT 1
        FROM public.users
        WHERE users.clerk_id = (SELECT auth.jwt() ->> 'sub')
          AND users.role = 'admin'
    )
);
