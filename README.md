# Fixed Asset Register

A static (no-backend) fixed asset register that runs entirely in the
browser. Same Supabase database, no build step, GitHub Pages friendly.

Feature-complete: Dashboard with KPIs, add new asset, add to existing
asset (parent + child), full or partial disposal, search/edit/delete
on both Main Assets and Additional Assets, year-end Excel report
(with parent + indented addition sub-rows, REMARKS column, frozen
panes), and master-data CRUD (categories, locations, depreciation
rates).

## What's in this repo

| File | Purpose |
|---|---|
| `index.html` | Page skeleton, header, tabs, modals |
| `app.js` | Alpine.js state, all data + form logic, Excel generator (ExcelJS) |
| `styles.css` | Tab indicator, section banner, table, modal styles |
| `config.example.js` | Template for Supabase credentials |
| `config.js` | Your Supabase URL + anon key (already filled in for local) |
| `favicon.svg` | Red ledger mark used as both browser icon and header logo |
| `schema.sql` | Reference of Supabase table shapes |
| `rls_policies.sql` | RLS policies — **run this in Supabase before deploying** |

## One-time setup before going public

### 1. Enable RLS on Supabase

Open Supabase → SQL Editor → run [`rls_policies.sql`](rls_policies.sql).
**This is mandatory.** Without it, anyone who finds the deployed URL
can read AND modify your data via the exposed anon key.

### 2. Confirm `config.js` has your project values

`config.js` should already have your `SUPABASE_URL` and the anon
public key. To deploy to a different Supabase project, edit those two
values.

> The anon key is **public** by design — Supabase intends it for
> client-side use, paired with RLS policies. Do NOT paste the
> `service_role` key here.

## Local preview

```bash
python -m http.server 8000
# → open http://localhost:8000
```

Or any other static file server (`npx serve`, `caddy`, etc.).

## Deploy to GitHub Pages

The code is already on GitHub. To turn on Pages:

GitHub → repo → **Settings → Pages**
- Source: `Deploy from a branch`
- Branch: `main` · folder: `/ (root)`
- Save.

Live in ~1 minute at `https://<you>.github.io/<repo>/`.

## Tightening security later

When you're ready to add login (Supabase Auth — email/password):

1. Supabase dashboard → Authentication → enable Email provider.
2. Replace the public-write RLS policies (see `rls_policies.sql`
   TIGHTENING section) with `TO authenticated` versions.
3. Add a login form to `index.html` that calls
   `supabase.auth.signInWithPassword(...)`. The Sign Out button in
   the header is already there.

## Tabs at a glance

| Tab | What it does |
|---|---|
| Dashboard | At-a-glance counts + values, quick links |
| Addition | "New Asset Details" form + "Add to Existing Asset" form |
| Disposal | Record full or partial disposals (decrements qty + cost) |
| Reports | Browse / search / edit Main Assets & Additional Assets, generate year-end Excel |
| Maintenance | CRUD on categories, locations, depreciation rates |

## Notes for future maintainers

- Depreciation calc uses straight-line, allocated by months elapsed.
  NBV is floored at RM 1 for in-service assets (the residual value);
  disposal cleanly takes NBV to 0.
- Addition cascade-disposal: when a parent reaches qty=0, its
  additions are virtually disposed on the parent's last disposal
  date (no manual step required).
- The Excel layout (column V REMARKS, indented addition sub-rows,
  parent subtotals, frozen panes) is preserved from the original
  Python NiceGUI implementation.
