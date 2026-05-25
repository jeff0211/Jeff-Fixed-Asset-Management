-- ===================================================================
-- AUTH + PER-OWNER ROW LEVEL SECURITY
--
-- Run this in Supabase → SQL Editor in TWO phases (the second one
-- requires that you've signed up via the app first).
--
-- PRE-REQUISITE: Supabase dashboard → Authentication → Providers →
-- enable "Email" (uncheck "Confirm email" if you don't want the
-- confirmation flow during testing).
-- ===================================================================


-- ===================================================================
-- PHASE 1 — run BEFORE the first signup
-- (adds owner_id column + temporary open policies so the app keeps
-- working while you create your first account)
-- ===================================================================

-- 1a. Add owner_id (nullable for now — will tighten in Phase 2)
ALTER TABLE public.assets
  ADD COLUMN IF NOT EXISTS owner_id uuid REFERENCES auth.users(id);

-- 1b. Enable RLS on every app table
ALTER TABLE public.assets             ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.asset_additions    ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.disposals          ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.categories         ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.locations          ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.depreciation_rates ENABLE ROW LEVEL SECURITY;

-- 1c. Drop any pre-existing policies (idempotent re-runs)
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

-- 1d. Temporary open policies so the existing test data is still
-- readable while you sign up + run Phase 2. Replace in Phase 2.
CREATE POLICY "phase1 open assets"             ON public.assets             FOR ALL TO anon, authenticated USING (true) WITH CHECK (true);
CREATE POLICY "phase1 open asset_additions"    ON public.asset_additions    FOR ALL TO anon, authenticated USING (true) WITH CHECK (true);
CREATE POLICY "phase1 open disposals"          ON public.disposals          FOR ALL TO anon, authenticated USING (true) WITH CHECK (true);
CREATE POLICY "phase1 open categories"         ON public.categories         FOR ALL TO anon, authenticated USING (true) WITH CHECK (true);
CREATE POLICY "phase1 open locations"          ON public.locations          FOR ALL TO anon, authenticated USING (true) WITH CHECK (true);
CREATE POLICY "phase1 open depreciation_rates" ON public.depreciation_rates FOR ALL TO anon, authenticated USING (true) WITH CHECK (true);


-- ===================================================================
-- ↓↓↓ STOP HERE. Open the app, sign up with email + password,
--     then continue with Phase 2 ↓↓↓
-- ===================================================================


-- ===================================================================
-- PHASE 2 — run AFTER you've signed up via the app
-- (backfills existing data to your user, then locks down per-owner)
-- ===================================================================

-- 2a. Find your UUID. After signing up, this should show your email + id.
-- SELECT id, email FROM auth.users;
--
-- Then paste your UUID into the UPDATE below and run it.
-- (Or just run as-is — it'll backfill ALL existing rows to your
--  single user assuming you're the only one signed up so far.)

-- Backfill: assign all orphan assets to the most recently created user.
UPDATE public.assets
SET owner_id = (SELECT id FROM auth.users ORDER BY created_at DESC LIMIT 1)
WHERE owner_id IS NULL;

-- 2b. Make owner_id NOT NULL and default to auth.uid() on insert
ALTER TABLE public.assets
  ALTER COLUMN owner_id SET NOT NULL,
  ALTER COLUMN owner_id SET DEFAULT auth.uid();

-- 2c. Drop Phase 1 open policies
DROP POLICY IF EXISTS "phase1 open assets"             ON public.assets;
DROP POLICY IF EXISTS "phase1 open asset_additions"    ON public.asset_additions;
DROP POLICY IF EXISTS "phase1 open disposals"          ON public.disposals;
DROP POLICY IF EXISTS "phase1 open categories"         ON public.categories;
DROP POLICY IF EXISTS "phase1 open locations"          ON public.locations;
DROP POLICY IF EXISTS "phase1 open depreciation_rates" ON public.depreciation_rates;

-- 2d. Per-owner policies for assets + dependents
CREATE POLICY "owner read assets" ON public.assets
  FOR SELECT TO authenticated
  USING (owner_id = auth.uid());

CREATE POLICY "owner write assets" ON public.assets
  FOR ALL TO authenticated
  USING (owner_id = auth.uid())
  WITH CHECK (owner_id = auth.uid());

-- Additions inherit ownership via parent_asset_id → assets.owner_id
CREATE POLICY "owner read additions" ON public.asset_additions
  FOR SELECT TO authenticated
  USING (EXISTS (
    SELECT 1 FROM public.assets
    WHERE assets.id = asset_additions.parent_asset_id
      AND assets.owner_id = auth.uid()
  ));
CREATE POLICY "owner write additions" ON public.asset_additions
  FOR ALL TO authenticated
  USING (EXISTS (
    SELECT 1 FROM public.assets
    WHERE assets.id = asset_additions.parent_asset_id
      AND assets.owner_id = auth.uid()
  ))
  WITH CHECK (EXISTS (
    SELECT 1 FROM public.assets
    WHERE assets.id = asset_additions.parent_asset_id
      AND assets.owner_id = auth.uid()
  ));

-- Disposals inherit ownership via asset_id → assets.owner_id
CREATE POLICY "owner read disposals" ON public.disposals
  FOR SELECT TO authenticated
  USING (EXISTS (
    SELECT 1 FROM public.assets
    WHERE assets.id = disposals.asset_id
      AND assets.owner_id = auth.uid()
  ));
CREATE POLICY "owner write disposals" ON public.disposals
  FOR ALL TO authenticated
  USING (EXISTS (
    SELECT 1 FROM public.assets
    WHERE assets.id = disposals.asset_id
      AND assets.owner_id = auth.uid()
  ))
  WITH CHECK (EXISTS (
    SELECT 1 FROM public.assets
    WHERE assets.id = disposals.asset_id
      AND assets.owner_id = auth.uid()
  ));

-- 2e. Shared master data (categories / locations / depreciation rates):
-- readable + writable by any authenticated user. Tighten further later
-- if you want only admins to edit master data.
CREATE POLICY "auth read categories"         ON public.categories         FOR SELECT TO authenticated USING (true);
CREATE POLICY "auth write categories"        ON public.categories         FOR ALL    TO authenticated USING (true) WITH CHECK (true);
CREATE POLICY "auth read locations"          ON public.locations          FOR SELECT TO authenticated USING (true);
CREATE POLICY "auth write locations"         ON public.locations          FOR ALL    TO authenticated USING (true) WITH CHECK (true);
CREATE POLICY "auth read depreciation_rates" ON public.depreciation_rates FOR SELECT TO authenticated USING (true);
CREATE POLICY "auth write depreciation_rates" ON public.depreciation_rates FOR ALL    TO authenticated USING (true) WITH CHECK (true);
