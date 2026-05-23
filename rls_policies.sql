-- ===================================================================
-- Row Level Security policies for the static GitHub Pages app.
-- Run this in Supabase → SQL Editor BEFORE deploying.
--
-- The static app uses the PUBLIC anon key, which is visible to anyone
-- who views the page source. RLS is the only thing standing between
-- your data and the open internet.
--
-- Phase 1 policy set: PUBLIC READ + PUBLIC WRITE on app tables.
-- This is appropriate while the app is on testing data and the URL
-- is not widely shared. Tighten before going live (see "TIGHTENING"
-- section at the bottom).
-- ===================================================================

-- ----- Enable RLS on every app table -----
ALTER TABLE public.assets             ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.asset_additions    ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.disposals          ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.categories         ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.locations          ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.depreciation_rates ENABLE ROW LEVEL SECURITY;

-- ----- Drop pre-existing policies (idempotent re-runs) -----
DO $$
DECLARE r record;
BEGIN
  FOR r IN
    SELECT schemaname, tablename, policyname
    FROM pg_policies
    WHERE schemaname = 'public'
      AND tablename IN ('assets','asset_additions','disposals','categories','locations','depreciation_rates')
  LOOP
    EXECUTE format('DROP POLICY IF EXISTS %I ON %I.%I', r.policyname, r.schemaname, r.tablename);
  END LOOP;
END $$;

-- ----- Public read + write policies -----
-- Read everything
CREATE POLICY "anon read assets"             ON public.assets             FOR SELECT TO anon USING (true);
CREATE POLICY "anon read asset_additions"    ON public.asset_additions    FOR SELECT TO anon USING (true);
CREATE POLICY "anon read disposals"          ON public.disposals          FOR SELECT TO anon USING (true);
CREATE POLICY "anon read categories"         ON public.categories         FOR SELECT TO anon USING (true);
CREATE POLICY "anon read locations"          ON public.locations          FOR SELECT TO anon USING (true);
CREATE POLICY "anon read depreciation_rates" ON public.depreciation_rates FOR SELECT TO anon USING (true);

-- Write everything (insert/update/delete)
CREATE POLICY "anon write assets"             ON public.assets             FOR ALL TO anon USING (true) WITH CHECK (true);
CREATE POLICY "anon write asset_additions"    ON public.asset_additions    FOR ALL TO anon USING (true) WITH CHECK (true);
CREATE POLICY "anon write disposals"          ON public.disposals          FOR ALL TO anon USING (true) WITH CHECK (true);
CREATE POLICY "anon write categories"         ON public.categories         FOR ALL TO anon USING (true) WITH CHECK (true);
CREATE POLICY "anon write locations"          ON public.locations          FOR ALL TO anon USING (true) WITH CHECK (true);
CREATE POLICY "anon write depreciation_rates" ON public.depreciation_rates FOR ALL TO anon USING (true) WITH CHECK (true);

-- ===================================================================
-- TIGHTENING — when you add Supabase Auth (Phase 7), replace the
-- public policies above with `TO authenticated` versions:
--
--   DROP POLICY "anon write assets" ON public.assets;
--   CREATE POLICY "auth write assets" ON public.assets
--     FOR ALL TO authenticated USING (true) WITH CHECK (true);
--
-- and keep `TO anon … SELECT … USING (false)` (or no policy) to block
-- unauthenticated reads.
-- ===================================================================
