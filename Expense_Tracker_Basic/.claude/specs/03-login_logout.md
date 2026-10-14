# Spec 03 — Login and Logout

## Overview

- This step turns the `/login` stub into a working GET + POST handler that:
  - checks the submitted email and password against the `users` table
  - stores the logged-in user's id in `session["user_id"]`
  - redirects to the landing page, because no dashboard route exists yet
- It also implements `/logout`, which clears the session and redirects to `/`.
- After this step the app can tell logged-in users apart from guests.
- All expense features require this step.

## Depends on

- Step 01 — Database Setup:
  - The `users` table (`id`, `name`, `email`, `password_hash`, `created_at`) must exist
  - `get_db()` must return a connection with `row_factory = sqlite3.Row` and `PRAGMA foreign_keys = ON`
  - The seeded demo user (`demo@spendly.com` / `demo123`) must exist
- Step 02 — Registration:
  - `create_user()` and werkzeug password hashing must be in place, so the stored `password_hash` values can be checked
  - `app.secret_key` must already be set in `app.py`, which both `flash()` and `session` need
  - A registered user must exist to log in with

## Routes

- `GET /login` — shows the login form — public
- `POST /login` — checks the credentials, sets the session, and redirects — public
  - Declared on the same `login()` view function with `methods=["GET", "POST"]`
- `GET /logout` — clears the session and redirects to `/` — public (no login required)

## Database changes

- No schema changes.
- The `users` table from Step 01 already stores `email` and `password_hash`.
- Add one new helper to `database/db.py`:
  - `get_user_by_email(email)`
    - Looks up a row in `users` by `email` with a parameterized query
    - Returns the matching row as a `sqlite3.Row`, or `None` if there is no match
    - Closes the connection it opened through `get_db()` before returning
    - Must live in `database/db.py`, not inline in the route

## Templates

- Modify `templates/login.html`:
  - Keep a POST form with an `email` field (`type="email"`, `name="email"`) and a `password` field (`type="password"`, `name="password"`)
  - Change the form action from the hardcoded `/login` to `url_for('login')`, and keep `method="post"`
  - Replace the existing `{% if error %}` block with a block that shows flashed messages via `get_flashed_messages(with_categories=true)`:
    - Error messages (e.g. "Invalid email or password.") use the existing `auth-error` style
    - Success messages, such as the "Account created" flash from Step 02, are shown in the same place
  - After a failed login, fill the `email` input back in with the submitted value; never fill the password back in
  - Keep the existing "Create one free" link to the registration page, using `url_for('register')`
  - Keep the existing look (classes, layout, copy) unchanged
  - The template must still extend `base.html`

## Files to change

- `app.py`
  - Import `session` from Flask, `check_password_hash` from `werkzeug.security`, and `get_user_by_email` from `database.db`
  - Make `login()` a GET + POST handler with credential checks, session setup, flash, and redirect
  - Make `logout()` clear the session and redirect, replacing the stub string
- `database/db.py`
  - Add the `get_user_by_email()` helper
- `templates/login.html`
  - Point the form action at `url_for('login')`, show flashed messages, and fill the email back in

## Files to create

- None

## New dependencies

- None
- `werkzeug.security.check_password_hash` is already installed
- Uses Flask's built-in `session`, `flash`, `redirect`, `url_for`, `request`, and `get_flashed_messages`

## Rules for implementation

- No SQLAlchemy or ORMs — use raw `sqlite3` via `get_db()` only
- Parameterized queries only (`?` placeholders) — never use f-strings, `%`, or `.format()` in SQL
- Strip leading and trailing whitespace from the submitted email before looking it up
- Check passwords with `werkzeug.security.check_password_hash` against the stored `password_hash`
- The session key for the logged-in user must be `session["user_id"]`, holding the user's integer `id`
- Use `flask.session` — do not build a custom session mechanism
- Call `session.clear()` before setting `session["user_id"]` on a successful login, so no stale data from an earlier session carries over
- Treat empty fields, an unknown email, and a wrong password the same way: flash the generic error "Invalid email or password."
  - Do not reveal which field was wrong
  - Show the login form again (do not redirect) with the email filled back in
- After a successful login, redirect to `url_for("landing")` until a dashboard exists
- `logout()` must call `session.clear()` and then redirect to `url_for("landing")`
- `logout()` works for guests too; visiting it without a session just redirects without an error
- All templates must extend `base.html`
- Use CSS variables — never hardcode hex values — and no inline styles
- Use `url_for()` for every internal link and form action — never hardcode paths
- Do not add login-required protection to other routes in this step

## Definition of done

- [ ] `GET /login` shows the login form with email and password fields
- [ ] Submitting valid credentials (`demo@spendly.com` / `demo123`) sets `session["user_id"]` and redirects to `/`
- [ ] Submitting a wrong password shows the "Invalid email or password." flash and stays on the login page
- [ ] Submitting an unregistered email shows the same generic error flash
- [ ] Submitting with empty fields shows the same generic error flash
- [ ] `GET /logout` clears the session and redirects to `/`
- [ ] After logout, `session["user_id"]` is no longer present
- [ ] The `/logout` route no longer returns the raw stub string
- [ ] The login form action uses `url_for('login')` and no internal URL in the template is hardcoded
