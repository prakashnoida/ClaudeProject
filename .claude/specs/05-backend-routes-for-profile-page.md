# Spec 05 — Backend Routes for Profile Page

## Overview

- Step 05 replaces all hardcoded data in the `/profile` route with live queries against the SQLite database
- The profile page currently renders a static demo user, fixed summary stats, a hand-typed transaction list, and a hardcoded category breakdown
- This step wires those four sections to real data so every logged-in user sees their own expenses
- Three parallel subagents handle the three independent data concerns before being integrated into the single `/profile` route:
  - Subagent 1 — transaction history (`get_recent_transactions()`)
  - Subagent 2 — summary stats (`get_summary_stats()`)
  - Subagent 3 — category breakdown (`get_category_breakdown()`)
  - Integration — `get_user_by_id()` plus wiring all four helpers into `profile()` in `app.py`

## Depends on

- Step 01 — Database setup (tables and `get_db()` exist)
- Step 02 — Registration (users are stored in the database)
- Step 03 — Login / Logout (`session["user_id"]` is set on login)
- Step 04 — Profile page static UI (template already renders all four sections)

## Routes

- No new routes
- The existing `GET /profile` route is modified in place
  - Remains logged-in only — if `session.get("user_id")` is missing, redirect to `url_for("login")`
  - If `get_user_by_id()` returns `None` for the session's `user_id` (stale session), clear the session and redirect to `url_for("login")`

## Database changes

- No database changes
- The `users` and `expenses` tables already have all required columns:
  - `users` — `id`, `name`, `email`, `created_at`
  - `expenses` — `user_id`, `amount`, `category`, `date`, `description`, `created_at`

## Templates

- Modify: `templates/profile.html`
  - Amounts must be rendered with the `₹` symbol (Indian Rupee) — never `£` or `$`
  - Amounts are formatted to two decimal places (e.g. `₹346.24`, `₹0.00`)
  - All four dynamic sections are already present in the template — no structural changes needed, only the Jinja variables they consume are now real
  - Category breakdown rows read the helper's keys `name`, `amount`, `pct` (update any Step 04 references to `category`, `total`, `percent` accordingly)
  - Progress-bar widths continue to use the preset width classes from Step 04, selected from `pct` — no inline `style` widths
  - The transaction table and category breakdown must render an empty-state message when their lists are empty, rather than an empty table or broken layout

## Files to change

- `app.py`
  - Import `get_user_by_id`, `get_summary_stats`, `get_recent_transactions`, `get_category_breakdown` from `database.queries`
  - Replace hardcoded data in the `profile()` view with calls to those helpers, passing `session["user_id"]`
  - Keep the Step 04 context variable names stable: `user`, `stats`, `expenses`, `category_breakdown`
  - No SQL or query logic inline in the route handler
- `templates/profile.html`
  - Confirm `₹` symbol is used for all currency display
  - Consume the live data shapes described under Templates

## Files to create

- `database/queries.py` — pure query helpers with no Flask imports; one function per data concern:
  - `get_user_by_id(user_id)`
    - → dict with `name`, `email`, `member_since`
    - → `None` if no user with that id exists
  - `get_summary_stats(user_id)`
    - → dict with `total_spent`, `transaction_count`, `top_category`
    - → `total_spent` is a float rounded to 2 decimal places
    - → `top_category` is the category with the highest summed amount; `"—"` when there are no expenses
  - `get_recent_transactions(user_id, limit=10)`
    - → list of dicts, each with `date`, `description`, `category`, `amount`
    - → ordered newest-first (by `date` descending, then `id` descending as a tie-breaker)
  - `get_category_breakdown(user_id)`
    - → list of dicts, each with `name`, `amount`, `pct`
    - → `pct` is percentage of total rounded to nearest int
    - → ordered by `amount` descending
- `tests/test_backend_connection.py` — unit and route tests listed under Tests to write

## New dependencies

- None

## Rules for implementation

- No SQLAlchemy or ORMs — raw `sqlite3` only via `get_db()`
- Parameterised queries only — never string-format values into SQL
- `PRAGMA foreign_keys = ON` must be enabled on every connection (already handled in `get_db()`)
- Currency must always display as `₹` — never `£` or `$`
- `member_since` must be derived from `users.created_at` and formatted as `"Month YYYY"` (e.g. `"January 2026"`)
- `pct` values in category breakdown must sum to 100; use integer rounding and adjust the largest category to absorb any rounding remainder
- If a user has no expenses, all helpers must return zeros and empty lists — never raise exceptions
- All helpers in `database/queries.py` must call `get_db()` internally and close the connection before returning
- Helpers return plain dicts / lists of dicts — never raw `sqlite3.Row` objects
- `database/queries.py` must not import Flask or access `session`
- Every query must filter by `user_id` so a user can never see another user's expenses
- Use CSS variables — never hardcode hex values
- No inline styles
- All templates extend `base.html`

## Tests to write

- File: `tests/test_backend_connection.py`
- Tests use an isolated temporary database (not the real `spendly.db`), initialised with `init_db()` and `seed_db()`
- Unit tests:

| Function | Input | Expected output |
|---|---|---|
| `get_user_by_id` | Valid seed `user_id` | Dict with `name` = `"Demo User"`, `email` = `"demo@spendly.com"`, `member_since` in `"Month YYYY"` format |
| `get_user_by_id` | Non-existent id (e.g. `9999`) | `None` |
| `get_summary_stats` | `user_id` with expenses (seed user) | `total_spent` = `346.24`, `transaction_count` = `8`, `top_category` = `"Bills"` |
| `get_summary_stats` | `user_id` with no expenses | `{"total_spent": 0, "transaction_count": 0, "top_category": "—"}` |
| `get_recent_transactions` | `user_id` with expenses (seed user) | List ordered newest-first; each item has `date`, `description`, `category`, `amount` |
| `get_recent_transactions` | `user_id` with no expenses | `[]` |
| `get_category_breakdown` | `user_id` with expenses (seed user) | List ordered by `amount` desc; `pct` values are integers summing to 100 |
| `get_category_breakdown` | `user_id` with no expenses | `[]` |

- Route tests:
  - `GET /profile` unauthenticated → redirects to `/login` (302)
  - `GET /profile` authenticated as seed user:
    - returns 200
    - response contains `"Demo User"`
    - response contains `"demo@spendly.com"`
    - response contains `₹` symbol
    - `total_spent` matches sum of all seed expenses (`346.24`)
    - `transaction_count` is `8`
    - `top_category` is `"Bills"` (highest single-category total)
    - transaction list appears in newest-first order
    - category breakdown contains all 7 categories

## Definition of done

- [ ] Logging in as `demo@spendly.com` / `demo123` shows "Demo User" and "demo@spendly.com" on the profile page — not the hardcoded strings
- [ ] Total spent displayed on the profile page equals ₹346.24
- [ ] Transaction count displayed is 8
- [ ] Top category displayed is "Bills"
- [ ] Transaction list shows 8 rows ordered newest date first
- [ ] Category breakdown shows 7 categories with percentages that add up to 100%
- [ ] All amounts on the page display the ₹ symbol
- [ ] Registering a brand-new user and visiting `/profile` shows ₹0.00 total spent, 0 transactions, and an empty category breakdown — no errors
- [ ] `database/queries.py` contains no Flask imports and no string-formatted SQL
- [ ] `pytest tests/test_backend_connection.py` passes
