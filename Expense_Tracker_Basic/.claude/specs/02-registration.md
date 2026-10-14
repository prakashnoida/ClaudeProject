# Spec 02 — Registration

## Overview

- This step turns the stub `GET /register` route into a working registration feature that handles both GET and POST.
- The registration form accepts four fields: `name`, `email`, `password`, `confirm_password`.
- GET shows the form. POST checks the input on the server, creates the user in the `users` table, and sends them on.
- On success, the route flashes a success message and redirects to `/login` via `url_for('login')`.
- On failure, the route shows the form again with an error message and the name and email already filled in, so the user doesn't have to retype them.
- Registration is how every user gets into the app, so login, profile, and all expense features depend on it.

## Depends on

- Step 01 — Database setup:
  - The `users` table (`id`, `name`, `email` UNIQUE, `password_hash`, `created_at`)
  - `get_db()` in `database/db.py`, which returns a connection with `row_factory = sqlite3.Row` and `PRAGMA foreign_keys = ON`
  - `init_db()` / `seed_db()` called at startup inside `app.app_context()`

## Routes

- `GET /register` — shows the registration form — public
  - The route already exists as a stub; upgrade it rather than adding a second route
- `POST /register` — reads the form, validates it, creates the user, and redirects to `/login` — public
  - Declared on the same view function with `methods=["GET", "POST"]`

## Database changes

- No new tables or columns.
- The existing `users` table already has everything registration needs.
- Add one new helper to `database/db.py`:
  - `create_user(name, email, password)`
    - Hashes `password` with `werkzeug.security.generate_password_hash`
    - Inserts one row into `users` (`name`, `email`, `password_hash`) using a parameterized query
    - Commits and closes the connection it opened through `get_db()`
    - Returns the new user's `id` (the cursor's `lastrowid`)
    - Raises `sqlite3.IntegrityError` without catching it if the email already exists (UNIQUE constraint), so the route can handle it

## Templates

- Modify `templates/register.html`:
  - Change the form action from the hardcoded `/register` to `url_for('register')`, and keep `method="post"`
  - Make sure every input has a `name` attribute: `name`, `email`, `password`, `confirm_password`
  - Add a new "Confirm password" input (`type="password"`, `id` and `name` set to `confirm_password`), styled with the same `form-group` / `form-input` classes as the other fields
  - Replace the existing `{% if error %}` block with a block that shows flashed messages via `get_flashed_messages(with_categories=true)`:
    - Error messages (e.g. "Email already registered", "Passwords do not match") use the existing `auth-error` style
    - Success messages are not shown here, because they appear on the login page after the redirect
  - After a failed submission, fill the `name` and `email` inputs back in with what the user submitted
  - Never fill `password` or `confirm_password` back in
  - Keep the page's existing look, including its classes, layout, and copy
  - The template must still extend `base.html`

## Files to change

- `app.py`
  - Import `flash`, `redirect`, `url_for`, `request`, `abort` from Flask
  - Import `create_user` from `database.db`
  - Set `app.secret_key` so `flash()` works
  - Upgrade `register()` to accept GET and POST, with validation, flash, and redirect logic
- `database/db.py`
  - Add the `create_user()` helper
- `templates/register.html`
  - Point the form action at `url_for('register')`, add the `confirm_password` field, show flashed messages, and fill submitted values back in

## Files to create

- None

## New dependencies

- None
- Uses `werkzeug.security.generate_password_hash` (already installed)
- Uses Flask's built-in `flash`, `redirect`, `url_for`, `request`, `abort`, and `get_flashed_messages`

## Rules for implementation

- No SQLAlchemy and no ORMs — use raw `sqlite3` through `get_db()` only
- Parameterized queries only (`?` placeholders) — never use f-strings, `%`, or `.format()` in SQL
- Hash passwords with `werkzeug.security.generate_password_hash` — never store plaintext
- The password-hashing and SQL insert logic belongs in `create_user()` in `database/db.py`, not in the route handler
- `app.secret_key` must be set in `app.py` for `flash()` to work (a hardcoded dev string is fine for now)
- Strip leading and trailing whitespace from `name` and `email` before validating
- Server-side validation must run in this order and stop at the first failure:
  1. All four fields are non-empty → otherwise flash "All fields are required"
  2. `password == confirm_password` → otherwise flash "Passwords do not match"
  3. Email is not already registered: call `create_user()` and catch `sqlite3.IntegrityError` → flash "Email already registered"
- On any validation failure, show the form again with the flashed error and the submitted `name` / `email` filled in — do not redirect
- On success, flash a success message (e.g. "Account created — please sign in") and redirect to `url_for('login')`
- Call `abort(405)` if a method other than GET or POST somehow reaches the view
- All templates must extend `base.html`
- Use CSS variables — never hardcode hex values — and no inline styles
- Use `url_for()` for every internal link and form action — never hardcode URLs
- Do not implement login or session handling in this step (that is Step 03)

## Definition of done

- [ ] `GET /register` shows the registration form, including the confirm-password field, without errors
- [ ] Submitting with all valid fields creates a new user in `users` and redirects to `/login`
- [ ] Submitting with mismatched passwords shows the form again with "Passwords do not match" and inserts nothing into the DB
- [ ] Submitting with an already-registered email shows the form again with "Email already registered"
- [ ] Submitting with any empty field shows the form again with a validation error
- [ ] After any failed submission, the name and email fields still hold the submitted values
- [ ] The password is stored as a werkzeug hash, never plaintext, which you can check by inspecting `spendly.db`
- [ ] Submitting the same valid email again does not create a duplicate user
- [ ] The form action uses `url_for('register')` and no internal URL in the template is hardcoded
