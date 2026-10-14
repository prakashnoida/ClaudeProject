# Spec 09 — Delete Expense

## Overview

- Step 09 lets a logged-in user permanently delete one of their own expenses directly from the profile transaction table
- A "Delete" button per row submits a POST request to `/expenses/<id>/delete`
- The handler verifies ownership, removes the row from the database, and redirects back to `/profile`
- There is no separate confirmation page — a browser-side `confirm()` dialog on the delete form is used to prevent accidental deletions
- The existing `get_expense_by_id` helper from Step 08 is reused for ownership verification — no new query lookup functions are needed
- Only one new mutation helper is added: `delete_expense` in `database/queries.py`

## Depends on

- Step 01 — Database setup (`expenses` table exists)
- Step 03 — Login / Logout (`session["user_id"]` is set and enforced)
- Step 05 — Profile page renders transactions (the delete button lives there)
- Step 08 — Edit Expense (`get_expense_by_id` is available; the Actions column already exists in the profile transactions table)

## Routes

- `POST /expenses/<int:id>/delete` — verify ownership, delete the expense row, redirect to `/profile` — logged-in only
- No GET handler — a bare GET to this URL must return 405
- The endpoint name stays `delete_expense` (the existing placeholder view in `app.py`), so templates use `url_for('delete_expense', id=...)`
- Order of checks:
  - Not logged in → redirect to `url_for("login")`
  - Expense not found or not owned by `session["user_id"]` → 404
  - Otherwise → delete and redirect to `url_for("profile")`
- The expense id comes only from the URL and the owner only from the session — nothing in the form body is trusted

## Database changes

- No new tables or columns
- The `expenses` table already has all required columns
- No other table references `expenses`, so deleting a row has no foreign-key side effects

## Templates

- Modify: `templates/profile.html`
  - Inside the existing "Actions" `<td>` per transaction row, add a delete form:
    - `<form>` with `method="POST"` and `action` set via `url_for('delete_expense', id=tx.id)` (renders as `/expenses/<id>/delete`)
    - `style="display:inline"` on the `<form>` tag is the one permitted exception to the no-inline-styles rule — it is a layout-utility value only, not a design value
    - `onsubmit="return confirm('Delete this expense?')"` on the `<form>` tag to provide browser-side confirmation before submission
    - A `<button type="submit">` with `class="btn-delete"` and label "Delete"
  - "Edit" link from Step 08 remains alongside the new "Delete" button
  - No other changes to the profile page; the date filter, summary stats, and category breakdown recalculate naturally after the redirect

## Files to change

- `database/queries.py`
  - Add `delete_expense(expense_id, user_id)`
    - Issues a parameterised `DELETE FROM expenses WHERE id = ? AND user_id = ?`
    - The dual-column `WHERE` clause is the ownership guard
    - Commits and closes the connection before returning
    - Returns the number of rows deleted (1 on success, 0 if not found / not owned) — never raises for a missing or foreign row
- `app.py`
  - Import the query helper from `database.queries` under a name that does not clash with the view function `delete_expense` (e.g. import it with an alias, or import the `queries` module and call `queries.delete_expense`)
    - Importing it bare as `delete_expense` would be shadowed by the view function of the same name, and the view would end up calling itself
  - Replace the GET-only placeholder at `/expenses/<int:id>/delete` with a POST-only handler:
    - Guard: redirect to `/login` if not authenticated
    - Call `get_expense_by_id(id, session["user_id"])`; if `None`, `abort(404)`
    - Call the `delete_expense` query helper with `(id, session["user_id"])`
    - Redirect to `url_for("profile")`
  - Route decorator must be: `@app.route("/expenses/<int:id>/delete", methods=["POST"])`
- `templates/profile.html` — add the delete form inside the existing Actions `<td>`
- `static/css/style.css`
  - Add a `.btn-delete` style using CSS variables for danger colour (e.g. a red-toned CSS variable) — never hardcode hex values
  - If no danger-colour variable exists yet, define one in the `:root` block and reference it
  - Include hover and focus states so the button is clearly interactive and keyboard-accessible

## Files to create

- `tests/test_delete_expense.py`

## New dependencies

- None

## Rules for implementation

- No SQLAlchemy or ORMs — raw `sqlite3` only via `get_db()`
- Parameterised queries only — never string-format values into SQL
- `PRAGMA foreign_keys = ON` must be enabled on every connection (already handled in `get_db()`)
- `delete_expense` must scope its `DELETE` to `id = ? AND user_id = ?` — this is the ownership guard that prevents one user deleting another's expense
- The route must only accept POST — a bare GET to the URL must return 405
- Unauthenticated access must redirect to `/login` (302)
- If the expense does not exist or belongs to another user, return 404
  - The response is the same in both cases, so it never reveals whether another user's expense id exists
- After successful deletion, redirect to `url_for("profile")` — do not render a template
- No SQL inside the route handler — all DB access goes through the query helpers
- The only permitted inline style is `style="display:inline"` on the `<form>` tag — no hex colours or design values may be inlined anywhere
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Currency must always display as `₹` — never `£` or `$`
- Use `url_for()` for every internal link — never hardcode paths (including the delete form `action`)

## Tests to write

- File: `tests/test_delete_expense.py`
- Tests use an isolated temporary database (not the real `spendly.db`) with two users, each owning at least one expense
- Unit tests:

| Function | Input | Expected output |
|---|---|---|
| `delete_expense` | Valid `expense_id`, correct `user_id` | Row removed from DB; returns 1 |
| `delete_expense` | Valid `expense_id`, wrong `user_id` | Row remains in DB; returns 0; no error raised |
| `delete_expense` | Non-existent `expense_id` | Returns 0; no error raised; DB unchanged |

- Route tests:
  - `POST /expenses/<id>/delete` unauthenticated → redirects to `/login` (302); row still exists in the database
  - `POST /expenses/<id>/delete` authenticated, own expense → redirects to `/profile` (302); row no longer exists in the database
  - `POST /expenses/<id>/delete` authenticated, other user's expense → returns 404; row still exists in the database
  - `POST /expenses/<id>/delete` authenticated, non-existent id → returns 404
  - `GET /expenses/<id>/delete` any user (logged in or not) → returns 405 (Method Not Allowed); row still exists in the database
  - `GET /profile` authenticated → each transaction row contains both an Edit link and a delete form posting to `/expenses/<id>/delete` for that row's id

## Definition of done

- [ ] POST `/expenses/<id>/delete` while logged out redirects to `/login`
- [ ] POSTing to `/expenses/<id>/delete` for a non-existent or other user's expense returns 404
- [ ] GET `/expenses/<id>/delete` returns 405
- [ ] Clicking "Delete" on a transaction row and confirming in the browser dialog removes that expense from the database
- [ ] After deletion, the user is redirected to `/profile` and the deleted expense no longer appears in the transaction list
- [ ] Cancelling the browser `confirm()` dialog does not submit the form and leaves the expense intact
- [ ] Each transaction row in the profile table now shows both "Edit" and "Delete" actions
- [ ] Summary stats and category breakdown on `/profile` update to reflect the deletion
- [ ] Another user's expense is never deleted, even when its id is POSTed directly
- [ ] `pytest tests/test_delete_expense.py` passes, and earlier test files still pass
