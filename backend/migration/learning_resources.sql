-- ============================================================
-- SMART LEARNING PLANNER - LEARNING RESOURCES MIGRATION
-- ============================================================
-- Feature: Admin Managed Learning Resources Catalog
-- Author: Heman Parashar (Backend & Database)
-- Date: 2026-11-12
-- ============================================================

CREATE TABLE IF NOT EXISTS public.learning_resources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    description TEXT,
    url TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'course', -- course, video, book, documentation, tool
    subject TEXT,                            -- e.g. Operating Systems, Computer Networks, DBMS
    provider TEXT,                           -- e.g. Coursera, NPTEL, YouTube, MIT OCW, edX
    difficulty TEXT DEFAULT 'intermediate',  -- beginner, intermediate, advanced
    rating NUMERIC(3, 2),                    -- 0.00 to 5.00
    tags TEXT[] DEFAULT '{}',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_by UUID REFERENCES public.users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for high-speed catalog lookup and filtering
CREATE INDEX IF NOT EXISTS idx_learning_resources_category ON public.learning_resources(category);
CREATE INDEX IF NOT EXISTS idx_learning_resources_subject ON public.learning_resources(subject);
CREATE INDEX IF NOT EXISTS idx_learning_resources_is_active ON public.learning_resources(is_active);

-- Row Level Security
ALTER TABLE public.learning_resources ENABLE ROW LEVEL SECURITY;

-- Policy 1: Students and anonymous clients can read active resources
DROP POLICY IF EXISTS "Public can view active learning resources" ON public.learning_resources;
CREATE POLICY "Public can view active learning resources"
ON public.learning_resources
FOR SELECT
TO authenticated, anon
USING (is_active = TRUE);

-- Policy 2: Administrators have full CRUD access
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

