# Fixed Asset Register — Static (GitHub Pages build)

A GitHub-Pages-friendly rewrite of the NiceGUI Python app. Same Supabase
database, no backend, no build step. Feature-complete: Dashboard, Add
new asset, Add to existing asset (parent + child), Disposal, Reports
with year-end Excel export, Master data CRUD.

## What's in this folder

| File | Purpose |
|---|---|
| `index.html` | Page skeleton, header, tabs, modals |
| `app.js` | Alpine.js state, all data + form logic, Excel generator |
| `styles.css` | Tab indicator, section banner, table, modal styles |
| `config.example.js` | Template for Supabase credentials |
| `config.js` | Your Supabase URL + anon key (already filled in for local) |
| `favicon.svg` | Red ledger mark used as both browser icon and header logo |
| `README.md` | This file |

## One-time setup before going public

### 1. Enable RLS on Supabase

Open Supabase → SQL Editor → run [`../rls_policies.sql`](../rls_policies.sql).
**This is mandatory.** Without it, anyone who finds the deployed URL can
read AND modify your data via the exposed anon key.

### 2. Confirm `config.js` has your project values

`docs/config.js` should already have your `SUPABASE_URL` and the anon
public key. To deploy to a different Supabase project, edit those two
values.

> The anon key is **public** by design — Supabase intends it for client-side
> use, paired with RLS policies. Do NOT paste the `service_role` key here.

## Local preview

```bash
python -m http.server -d docs 8000
# → open http://localhost:8000
```

## Deploy to GitHub Pages

```bash
# 1. Init repo (if you haven't already)
git init
git add .
git commit -m "Static fixed asset register"

# 2. Push to GitHub
git branch -M main
git remote add origin https://github.com/<you>/fixed-asset-register.git
git push -u origin main
```

Then in the GitHub repo: **Settings → Pages**
- Source: `Deploy from a branch`
- Branch: `main` · folder: `/docs`
- Save

Your app goes live at `https://<you>.github.io/fixed-asset-register/`
in about a minute.

## Tightening security later

When you're ready to add login (Supabase Auth — email/password):

1. Supabase dashboard → Authentication → enable Email provider.
2. Replace the public-write RLS policies (see `../rls_policies.sql` TIGHTENING
   section) with `TO authenticated` versions.
3. Add a login form to `index.html` that calls
   `supabase.auth.signInWithPassword(...)`. The Sign Out button in the
   header is already wired in (calls `supabase.auth.signOut()`).

Optional — switch from `<select>` parent picker to a searchable
combobox, add charts to the Dashboard, build per-category reports, etc.

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
- Addition cascade-disposal: when a parent reaches qty=0, its additions
  are virtually disposed on the parent's last disposal date (no manual
  step required).
- The Excel layout (column V REMARKS, indented addition sub-rows,
  parent subtotals, frozen panes) mirrors the original Python report.
