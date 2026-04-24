-- ============================================================
-- Morning Pulse - Supabase schema setup
-- Run this in: Supabase Dashboard -> SQL Editor -> New Query
-- ============================================================

CREATE TABLE IF NOT EXISTS public.market_intelligence (
    id           BIGSERIAL PRIMARY KEY,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    title        TEXT,
    url          TEXT,
    source       TEXT,
    category     TEXT,
    summary      TEXT
);

ALTER TABLE public.market_intelligence ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Authenticated users can read" ON public.market_intelligence;
DROP POLICY IF EXISTS "Authenticated users can insert" ON public.market_intelligence;
DROP POLICY IF EXISTS "Service role can insert" ON public.market_intelligence;

CREATE POLICY "Authenticated users can read"
    ON public.market_intelligence
    FOR SELECT
    TO authenticated
    USING (true);

CREATE POLICY "Authenticated users can insert"
    ON public.market_intelligence
    FOR INSERT
    TO authenticated
    WITH CHECK (true);

CREATE POLICY "Service role can insert"
    ON public.market_intelligence
    FOR INSERT
    TO service_role
    WITH CHECK (true);

SELECT 'market_intelligence table created successfully' AS status;
