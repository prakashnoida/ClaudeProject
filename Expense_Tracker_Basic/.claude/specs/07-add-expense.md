# Spec 07 — Add Expense

## Overview

- Step 07 lets a logged-in user submit a new expense through a dedicated form page at `/expenses/add`
- The route already exists as a GET placeholder; this step upgrades it to a full GET + POST handler
- Validated data is inserted into the `expenses` table and the user is redirected back to the profile page on success
- A reusable `insert_expense()` query helper is added to `database/queries.py`
- An "Add Expense" button is added to `profile.html` and a nav link is added to `base.html` so users can navigate to the form

## Depends on

- Step 01 — Database setup (`expenses` table exists with all required columns)
- Step 03 — Login / Logout (`session["user_id"]` is set and checked)
- Step 04 / 05 — Profile page exists and is the natural redirect target after saving

## Routes

- `GET /expenses/add` — render the add-expense form — logged-in only
- `POST /expenses/add` — validate and insert the new expense — logged-in only
- Both methods are served by the existing `add_expense` view function (endpoint name unchanged), now declared with `methods=["GET", "POST"]`
- The expense is always saved for `session["user_id"]` — any `user_id` submitted in the form is ignored

## Database changes

- No database changes
- The `expenses` table already has all required columns: `id`, `user_id`, `amount`, `category`, `date`, `description`, `created_at`
- `created_at` is filled automatically by its column default

## Templates

- Create: `templates/add_expense.html`
  - Extends `base.html`
  - Fills the `title` block (e.g. "Add Expense — Spendly")
  - Form with `method="POST"` and `action` set via `url_for('add_expense')` (renders as `/expenses/add`)
  - Fields:
    - `amount` — number input, `step="0.01"`, `min="0.01"`, required, labelled with `₹`
    - `category` — `<select>` with exactly 7 fixed options: Food, Transport, Bills, Health, Entertainment, Shopping, Other
    - `date` — `<input type="date">`, required, defaults to today's date (value supplied by `app.py`)
    - `description` — text input, optional, `maxlength="200"`
  - Submit button labelled "Save Expense" and a cancel link back to `url_for('profile')`
  - Flash/error message block to display validation errors, re-populating previously submitted values on failure
    - The previously selected category stays selected in the `<select>`
- Modify: `templates/profile.html`
  - Add an "Add Expense" button/link pointing to `url_for('add_expense')`, near the transaction table heading
- Modify: `templates/base.html`
  - Add an "Add Expense" link in the navbar, pointing to `url_for('add_expense')`, visible only when `session.user_id` is set

## Files to change

- `app.py` — replace the GET-only placeholder at `/expenses/add` with a GET + POST handler:
  - GET: render `add_expense.html`; redirect to `url_for("login")` if not authenticated
    - Pass the list of 7 categories and today's date (`YYYY-MM-DD`) as template context
  - POST: read form fields, validate, call `insert_expense()`, redirect to `url_for("profile")` on success
    - On validation failure, re-render `add_expense.html` with the error message and submitted values
  - Keep the 7 categories in a single constant, shared by validation and the template
- `database/queries.py` — add `insert_expense(user_id, amount, category, date, description)`
  - Inserts one row via `get_db()`, commits, and closes the connection before returning
  - Returns the new expense's id
- `templates/profile.html` — add "Add Expense" button
- `templates/base.html` — add "Add Expense" navbar link for logged-in users
- `static/css/profile.css` (or `static/css/style.css` for shared form styles) — style the new button and form using CSS variables only

## Files to create

- `templates/add_expense.html`
- `tests/test_add_expense.py`

## New dependencies

- None

## Rules for implementation

- No SQLAlchemy or ORMs — raw `sqlite3` only via `get_db()`
- Parameterised queries only — never string-format values into SQL
- `PRAGMA foreign_keys = ON` must be enabled on every connection (already handled in `get_db()`)
- Unauthenticated access to both GET and POST `/expenses/add` must redirect to `/login`
- Validation rules for POST:
  - 1. `amount`: required; must be a positive float greater than 0; parse with `float()`, catch `ValueError`
    - Also reject `nan` / `inf` values
    - Round to 2 decimal places before storing
  - 2. `category`: required; must be one of the 7 fixed categories; reject anything else
  - 3. `date`: required; must be a valid `YYYY-MM-DD` date; parse with `datetime.strptime`
  - 4. `description`: optional; strip whitespace; store `None` if blank
    - Reject descriptions longer than 200 characters (server-side, not only via `maxlength`)
- On any validation error, re-render the form with the error message and previously submitted values pre-filled
- After successful insert, redirect to `url_for("profile")` — do NOT render the form again
- No SQL inside the route handler — all DB access goes through `insert_expense()`
- Currency must always display as `₹` — never `£` or `$`
- Use CSS variables — never hardcode hex values
- No inline styles
- All templates extend `base.html`
- Use `url_for()` for every internal link — never hardcode paths (including the form `action`)

## Tests to write

- File: `tests/test_add_expense.py`
- Tests use an isolated temporary database (not the real `spendly.db`) and a test user
- Unit tests:

| Function | Input | Expected output |
|---|---|---|
| `insert_expense` | Valid `user_id`, `amount=50.0`, `category="Food"`, `date="2026-03-20"`, `description="Lunch"` | Row inserted; querying the DB returns the new row with matching `user_id`, `amount`, `category`, `date`, `description` |
| `insert_expense` | Valid `user_id`, `amount=50.0`, `category="Food"`, `date="2026-03-20"`, `description=None` | Row inserted with `description` stored as `NULL` |

- Route tests:
  - `GET /expenses/add` unauthenticated → redirects to `/login` (302)
  - `GET /expenses/add` authenticated → returns 200; response contains the category `<select>` with all 7 options; response contains a form with method POST
  - `POST /expenses/add` unauthenticated → redirects to `/login` (302); no row inserted
  - `POST /expenses/add` authenticated, valid data (`amount=50.0`, `category=Food`, `date=2026-03-20`, `description=Lunch`) → redirects to `/profile` (302); new expense row exists in the DB for the test user
  - `POST /expenses/add` authenticated, missing amount → returns 200; response contains an error message
  - `POST /expenses/add` authenticated, `amount = 0` → returns 200; response contains an error message
  - `POST /expenses/add` authenticated, non-numeric amount → returns 200; response contains an error message
  - `POST /expenses/add` authenticated, invalid category (not in fixed list) → returns 200; response contains an error message
  - `POST /expenses/add` authenticated, invalid date string → returns 200; response contains an error message
  - `POST /expenses/add` authenticated, no description (optional field) → redirects to `/profile` (302); row inserted with `description = NULL`
  - For every validation-error case: no row is inserted and the previously submitted values appear in the re-rendered form

## Definition of done

- [ ] Visiting `/expenses/add` while logged out redirects to `/login`
- [ ] Visiting `/expenses/add` while logged in shows a form with amount, category, date, and description fields
- [ ] The category dropdown contains exactly: Food, Transport, Bills, Health, Entertainment, Shopping, Other
- [ ] Submitting a valid expense redirects to `/profile` and the new expense appears in the transaction list
- [ ] Submitting with a missing or zero amount re-renders the form with an error and previously entered values retained
- [ ] Submitting with an invalid category re-renders the form with an error
- [ ] Submitting with an invalid date re-renders the form with an error
- [ ] Submitting without a description saves the expense with no error
- [ ] The "Add Expense" button on the profile page navigates to `/expenses/add`
- [ ] Navbar shows "Add Expense" link when logged in
- [ ] Navbar does not show "Add Expense" link when logged out
- [ ] `pytest tests/test_add_expense.py` passes, and earlier test files still pass
