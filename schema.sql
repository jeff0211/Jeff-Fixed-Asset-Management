-- Supabase public schema reference for Jeff Fixed Asset Management
-- Source: dump provided by user 2026-04-29
-- WARNING: This is for context only — do not run this file as-is. Constraints/order may not be valid for execution.

CREATE TABLE public.assets (
  id integer NOT NULL DEFAULT nextval('assets_id_seq'::regclass),
  asset_tag text,                              -- 2026-04-29: dropped NOT NULL + UNIQUE (see migrations below)
  name text NOT NULL,
  category_id integer,
  location_id integer,
  purchase_date date NOT NULL,
  purchase_cost numeric NOT NULL,
  status text DEFAULT 'Active'::text,
  depreciation_rate double precision,
  remarks text,
  disposal_date date,                          -- legacy / unused; superseded by disposals table
  disposal_year numeric,                       -- legacy / unused
  sales_proceed numeric,                       -- legacy / unused
  purchase_year numeric,
  quantity integer DEFAULT 1,                  -- 2026-04-29: added
  unit_cost numeric(12,2) DEFAULT 0,           -- 2026-04-29: added
  CONSTRAINT assets_pkey PRIMARY KEY (id),
  CONSTRAINT assets_category_id_fkey FOREIGN KEY (category_id) REFERENCES public.categories(id),
  CONSTRAINT assets_location_id_fkey FOREIGN KEY (location_id) REFERENCES public.locations(id)
);

-- Migrations applied 2026-04-29:
--   ALTER TABLE assets ALTER COLUMN asset_tag DROP NOT NULL;
--   ALTER TABLE assets DROP CONSTRAINT assets_asset_tag_key;
--   ALTER TABLE assets ADD COLUMN quantity INTEGER DEFAULT 1;
--   ALTER TABLE assets ADD COLUMN unit_cost NUMERIC(12,2) DEFAULT 0;

CREATE TABLE public.categories (
  id integer NOT NULL DEFAULT nextval('categories_id_seq'::regclass),
  name text NOT NULL,
  CONSTRAINT categories_pkey PRIMARY KEY (id)
);

CREATE TABLE public.depreciation_rates (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  rate_name text NOT NULL,
  percentage double precision NOT NULL,
  CONSTRAINT depreciation_rates_pkey PRIMARY KEY (id)
);

CREATE TABLE public.disposals (
  id bigint NOT NULL DEFAULT nextval('disposals_id_seq'::regclass),
  created_at timestamp with time zone DEFAULT now(),
  asset_id bigint,
  name text,
  remarks text,
  category_id bigint,
  location_id bigint,
  sales_proceed numeric DEFAULT 0,
  quantity_disposed integer NOT NULL DEFAULT 1,
  unit_cost numeric DEFAULT 0,
  total_disposal_cost numeric DEFAULT 0,
  disposal_date date,
  disposal_year integer,
  status text DEFAULT 'Disposed'::text,
  CONSTRAINT disposals_pkey PRIMARY KEY (id),
  CONSTRAINT disposals_asset_id_fkey FOREIGN KEY (asset_id) REFERENCES public.assets(id),
  CONSTRAINT disposals_category_id_fkey FOREIGN KEY (category_id) REFERENCES public.categories(id),
  CONSTRAINT disposals_location_id_fkey FOREIGN KEY (location_id) REFERENCES public.locations(id)
);

CREATE TABLE public.locations (
  id integer NOT NULL DEFAULT nextval('locations_id_seq'::regclass),
  name text NOT NULL,
  CONSTRAINT locations_pkey PRIMARY KEY (id)
);
