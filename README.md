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
| `index.html` | Landing / login + signup page (entry URL) |
| `auth.js` | Sign-in / sign-up logic for index.html |
| `home.html` | Main app — header, tabs, modals. Redirects to `index.html` if not logged in |
| `app.js` | Alpine.js state, all data + form logic, Excel generator (ExcelJS) |
| `styles.css` | Tab indicator, section banner, table, modal styles |
| `config.example.js` | Template for Supabase credentials |
| `config.js` | Your Supabase URL + anon key (already filled in for local) |
| `favicon.svg` | Red ledger mark used as both browser icon and header logo |
| `schema.sql` | Reference of Supabase table shapes |
| `rls_policies.sql` | **Two-phase auth + per-owner RLS migration — run in Supabase** |

## One-time setup before going public

The app uses Supabase Auth (email/password). Each user only sees
their own assets/additions/disposals; categories, locations, and
depreciation rates are shared.

### 1. Enable email auth in Supabase

Supabase dashboard → **Authentication → Providers → Email** → enable.
(During testing, uncheck "Confirm email" so signup is instant.)

### 2. Run Phase 1 SQL — BEFORE signing up

Supabase → SQL Editor → run the **Phase 1** block in
[`rls_policies.sql`](rls_policies.sql). This adds the `owner_id`
column and turns on RLS with temporary open policies so the existing
test data is still readable while you sign up.

### 3. Visit the deployed app and sign up

Open `index.html` (or `https://<you>.github.io/<repo>/`), click
**Sign up**, create your account.

### 4. Run Phase 2 SQL — AFTER signing up

Back in Supabase → SQL Editor → run the **Phase 2** block in
[`rls_policies.sql`](rls_policies.sql). This:
- Backfills existing test rows to your user account
- Locks down RLS so each user only sees their own data

Done. New signups will see an empty register; you'll see your data.

### 5. Confirm `config.js` has your project values

`config.js` should already have your `SUPABASE_URL` and the anon
public key. The anon key is **public** by design — Supabase intends
it for client-side use, paired with RLS policies. Do NOT paste the
`service_role` key.

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

## Auth notes

- Sessions persist in localStorage — returning users stay signed in.
- Visiting `home.html` without a session bounces to `index.html`.
- Visiting `index.html` with an active session jumps straight to `home.html`.
- Sign Out clears the session and returns to `index.html`.

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
