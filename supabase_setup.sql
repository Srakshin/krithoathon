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

-- ============================================================
-- User Preferences Table
-- ============================================================

CREATE TABLE IF NOT EXISTS public.user_preferences (
    user_id           UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    keywords          TEXT,
    industry          TEXT,
    frequency         TEXT,
    categories        JSONB,
    sources           JSONB,
    notifications     JSONB,
    additional_emails TEXT
);

ALTER TABLE public.user_preferences ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can read own preferences" ON public.user_preferences;
DROP POLICY IF EXISTS "Users can insert own preferences" ON public.user_preferences;
DROP POLICY IF EXISTS "Users can update own preferences" ON public.user_preferences;

CREATE POLICY "Users can read own preferences"
    ON public.user_preferences
    FOR SELECT
    TO authenticated
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own preferences"
    ON public.user_preferences
    FOR INSERT
    TO authenticated
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own preferences"
    ON public.user_preferences
    FOR UPDATE
    TO authenticated
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

SELECT 'user_preferences table created successfully' AS status;
