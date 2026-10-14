# Spec 04 — Profile Page (Hardcoded UI)

## Overview

- This step replaces the `/profile` stub with a fully designed profile page that shows static, hardcoded data.
- The goal is to build the complete UI layout before real DB queries are connected in Step 05.
- The page has four sections: a user info card, summary stats, a transaction history table, and a category breakdown.
- Building the UI first lets the team check the design on its own and means the template is ready for Step 05, which only needs to swap in real values.
- This step also updates the shared navbar so logged-in users see their name and a logout link instead of the guest links.

## Depends on

- Step 01 — Database setup (schema must exist)
- Step 02 — Registration (user accounts must be creatable)
- Step 03 — Login + Logout:
  - `session["user_id"]` is set on successful login and cleared on logout
  - `/profile` must be a protected route, reachable only when that session key is present

## Routes

- `GET /profile` — shows the profile page — logged-in only
  - If `session.get("user_id")` is missing, redirect to `url_for("login")`

## Database changes

- No database changes
- The existing `users` and `expenses` tables are sufficient
- No DB queries in this step; all page data is hardcoded

## Templates

- Create `templates/profile.html`, a full profile page that extends `base.html`
  - Pulls in its page stylesheet through the `head` block with `url_for('static', filename='css/profile.css')`
  - Fills the `title` block with a page title (e.g. "Profile — Spendly")
- The page must contain these four sections, in order:
  1. User info card — a circle with the user's initials (taken from the name in the template), the name, the email, and a member-since date (all hardcoded)
  2. Summary stats row — total spent, number of transactions, and top category (all hardcoded), with amounts shown as `₹`
  3. Transaction history table — recent expenses with columns for date, description, category badge, and amount (at least 3 hardcoded rows)
     - Dates are `YYYY-MM-DD` strings in the data
     - Amounts are shown with `₹` and two decimal places
     - Each category badge uses a shared `badge` class plus a per-category modifier class (e.g. `badge-food`, `badge-transport`)
  4. Category breakdown — a progress-bar row per category showing the category name and total (at least 3 hardcoded categories)
     - Bar widths use preset CSS classes (e.g. width steps in 10% increments), not inline `style` widths
- Modify `templates/base.html` navbar:
  - When `session.user_id` is set: show the user's name linking to `url_for('profile')`, plus a "Log out" link to `url_for('logout')`
  - When no one is logged in: keep the existing "Sign in" and "Get started" links unchanged

## Files to change

- `app.py`
  - Replace the `/profile` stub with a real view function that:
    - redirects unauthenticated users to `url_for("login")`
    - passes hardcoded context variables to `profile.html`:
      - `user` — a dict with `name`, `email`, `member_since`
      - `stats` — a dict with `total_spent`, `transaction_count`, `top_category`
      - `expenses` — a list of dicts with `date`, `description`, `category`, `amount`
      - `category_breakdown` — a list of dicts with `category`, `total`, `percent`
  - In `login()`, also store the user's name in `session["user_name"]` on successful login, so the navbar can show it without a DB query
- `templates/base.html`
  - Make the navbar change depending on whether someone is logged in, as described under Templates

## Files to create

- `templates/profile.html`
- `static/css/profile.css` — page-specific styles for the four sections, the badges, and the progress bars

## New dependencies

- None

## Rules for implementation

- No SQLAlchemy or ORMs — use raw `sqlite3` via `get_db()` if any DB call is ever needed
- Parameterized queries only — never string-format SQL
- Authentication guard: check `session.get("user_id")`; if it is missing, `redirect(url_for("login"))`
- All data passed to the template must be hardcoded Python dicts/lists in `app.py`; no DB queries in this step
- Hardcoded categories must come from the fixed list: Food, Transport, Bills, Health, Entertainment, Shopping, Other
- Hardcoded amounts are floats; currency is always shown as `₹`, never `£` or `$`
- Use CSS variables from `style.css` — never hardcode hex values in `profile.css` or `profile.html`
  - If new colours are needed (e.g. per-category badge colours), define them as new variables in the `:root` block of `style.css` and reference them
- No inline styles anywhere in `profile.html` (including progress-bar widths)
- All templates must extend `base.html`
- Category badges must use a CSS class, not inline colour styles
- Use `url_for()` for every internal link and stylesheet — never hardcode paths
- Keep context variable names and shapes stable, because Step 05 replaces their values with real query results

## Definition of done

- [ ] Visiting `/profile` without being logged in redirects to `/login`
- [ ] Visiting `/profile` while logged in returns HTTP 200
- [ ] The page shows a user info card with initials, name, email, and member-since date
- [ ] The page shows at least three summary stat values (total spent, transaction count, top category)
- [ ] The page shows a transaction history table with at least three hardcoded rows, each with a category badge
- [ ] The page shows a category breakdown section with at least three categories
- [ ] All amounts are shown with `₹`
- [ ] The navbar shows the logged-in state (username + logout link) and the guest links when logged out
- [ ] No hex colour values appear in `profile.html` or `profile.css`; only CSS variables are used
- [ ] No inline `style` attributes appear in `profile.html`
