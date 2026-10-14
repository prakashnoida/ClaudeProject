# Spec 01 — Database Setup

## 1. Overview

This step replaces the stub in `database/db.py` with a working SQLite data layer built on Python's standard-library `sqlite3` module. It gives Spendly a persistent database file (`spendly.db`) in the project root, creates the `users` and `expenses` tables, and seeds one demo user with sample expenses so the app has realistic data from its first run.

This is the foundational step of the project. Every later feature depends on it:

- **Authentication** (registration, login, logout) reads and writes the `users` table.
- **Profile page** (summary stats, recent transactions, category breakdown, date filtering) reads from both tables.
- **Expense tracking** (add, edit, delete) writes to the `expenses` table and depends on the foreign key to `users`.

No user-facing behavior changes in this step; it only makes the database available and ready before any route is served.

## 2. Depends on

None. This is the first step and has no prerequisites.

## 3. Routes

- No new routes are added in this step.
- All existing placeholder routes in `app.py` remain unchanged in path, method, and behavior.

## 4. Database Schema

### Table A: `users`

| Column | SQLite Type | Constraints |
|---|---|---|
| `id` | INTEGER | PRIMARY KEY, AUTOINCREMENT |
| `name` | TEXT | NOT NULL |
| `email` | TEXT | NOT NULL, UNIQUE |
| `password_hash` | TEXT | NOT NULL |
| `created_at` | TEXT | NOT NULL, DEFAULT `CURRENT_TIMESTAMP` |

### Table B: `expenses`

| Column | SQLite Type | Constraints |
|---|---|---|
| `id` | INTEGER | PRIMARY KEY, AUTOINCREMENT |
| `user_id` | INTEGER | NOT NULL, FOREIGN KEY → `users(id)` |
| `amount` | REAL | NOT NULL |
| `category` | TEXT | NOT NULL (must be one of the fixed categories in Section 10) |
| `date` | TEXT | NOT NULL — stored strictly in `YYYY-MM-DD` format |
| `description` | TEXT | Nullable (optional free-text note) |
| `created_at` | TEXT | NOT NULL, DEFAULT `CURRENT_TIMESTAMP` |

Notes:

- `expenses.date` must always be a `YYYY-MM-DD` string (e.g. `2026-09-15`) so that string comparison and ordering match chronological order.
- `amount` is stored as `REAL`, never `INTEGER`, to preserve fractional values.

## 5. Functions to Implement (database/db.py)

| Function | Responsibility |
|---|---|
| `get_db()` | Opens a connection to `spendly.db` located in the project root (resolved relative to the project, not the current working directory). Sets `row_factory = sqlite3.Row` so rows are accessible by column name. Executes `PRAGMA foreign_keys = ON`. Returns the connection. |
| `init_db()` | Obtains a connection via `get_db()` and creates the `users` and `expenses` tables using `CREATE TABLE IF NOT EXISTS`, exactly matching the schema in Section 4. Commits and closes the connection. Safe to call any number of times. |
| `seed_db()` | Obtains a connection via `get_db()`. Checks whether the `users` table already contains any rows; if it does, returns immediately without inserting anything. Otherwise inserts one demo user and 8 sample expenses linked to that user, commits, and closes the connection. |

### Seed data requirements

**Demo user**

| Field | Value |
|---|---|
| `name` | Demo User |
| `email` | demo@spendly.com |
| `password_hash` | Hash of `demo123` produced by `werkzeug.security.generate_password_hash` |

**Sample expenses**

- Exactly 8 expense rows, all with `user_id` set to the demo user's generated `id`.
- Together the 8 rows must cover all 7 categories from Section 10 (at least one expense per category; one category appears twice).
- All dates fall within the current calendar month, spread across different days, formatted as `YYYY-MM-DD`, and computed at seed time (not hardcoded to a fixed month).
- Each row has a positive `REAL` amount and a short, realistic description.

## 6. Changes to app.py

- Import `get_db`, `init_db`, and `seed_db` from `database.db`.
- Call `init_db()` followed by `seed_db()` inside a `with app.app_context():` block at module level, after the `app` object is created.
- This startup initialization must run before the app begins serving requests, so the database file and tables exist before any route is hit.
- No existing routes are modified.

## 7. Files to Change

| File | Change |
|---|---|
| `database/db.py` | Replace stub bodies with working implementations of `get_db()`, `init_db()`, and `seed_db()`. |
| `app.py` | Add the import and the startup `init_db()` / `seed_db()` calls inside `app.app_context()`. |

## 8. Files to Create

None. (`spendly.db` is generated at runtime and is not a source file.)

## 9. Dependencies

- No new pip packages are required.
- `sqlite3` — Python standard library.
- `werkzeug.security` — already installed via `requirements.txt`.

## 10. Categories (Fixed List)

- Food
- Transport
- Bills
- Health
- Entertainment
- Shopping
- Other

These seven values are the only valid expense categories, with exactly this spelling and capitalization.

## 11. Rules for Implementation

- No ORM and no SQLAlchemy — use raw `sqlite3` only.
- Parameterized queries only (`?` placeholders) — never use string formatting, concatenation, or f-strings to build SQL with values.
- `PRAGMA foreign_keys = ON` must be executed on every connection returned by `get_db()`.
- Store `amount` as `REAL`, not `INTEGER`.
- Hash passwords with `generate_password_hash` from `werkzeug.security`; never store plaintext passwords.
- `seed_db()` must be idempotent — calling it multiple times must never create duplicate users or expenses.
- `init_db()` must be idempotent — use `CREATE TABLE IF NOT EXISTS`.
- Dates must always be stored as `YYYY-MM-DD` strings.
- All database access goes through `get_db()`; no connections opened elsewhere.
- Connections opened inside `init_db()` and `seed_db()` must be committed and closed before the function returns.

## 12. Expected Behavior

### Function behavior

| Call | Expected Result |
|---|---|
| `get_db()` | Returns an open `sqlite3.Connection` to `spendly.db` in the project root; rows support access by column name; `PRAGMA foreign_keys` returns `1`. Creates the database file if it does not exist. |
| `init_db()` (first call) | Creates `users` and `expenses` tables with the exact columns and constraints in Section 4. |
| `init_db()` (repeat calls) | Completes without error; existing tables and data are untouched. |
| `seed_db()` (empty database) | Inserts 1 demo user and 8 expenses covering all 7 categories, dated within the current month. |
| `seed_db()` (users already exist) | Returns early; row counts in both tables remain unchanged. |
| App startup (`python app.py`) | Database file exists, tables are created, and seed data is present before the first request is handled. |

### Database-level constraint enforcement

- `users.email` is unique — a second user with an existing email is rejected.
- `users.name`, `users.email`, `users.password_hash` cannot be NULL.
- `expenses.user_id` must reference an existing `users.id` — orphan expenses are rejected.
- `expenses.user_id`, `amount`, `category`, and `date` cannot be NULL.
- `created_at` is populated automatically when not supplied.

## 13. Error Handling Expectations

| Scenario | Expected Outcome |
|---|---|
| Inserting a user whose email already exists | `sqlite3.IntegrityError` raised due to the UNIQUE constraint on `users.email`. |
| Inserting an expense with a `user_id` that does not exist in `users` | `sqlite3.IntegrityError` raised due to the FOREIGN KEY constraint (requires `PRAGMA foreign_keys = ON`). |
| Inserting a row with a NULL value in a NOT NULL column | `sqlite3.IntegrityError` raised due to the NOT NULL constraint. |
| Malformed SQL or reference to a nonexistent table/column | `sqlite3.OperationalError` (or other `sqlite3` error) propagates with its original message; errors are not silently swallowed. |
| Failure during `seed_db()` | No partial seed data is left committed; the error propagates so startup fails visibly for debugging. |

## 14. Definition of Done

- [ ] `spendly.db` is created in the project root on app startup
- [ ] `users` and `expenses` tables exist with the correct schema and constraints
- [ ] Demo user (`demo@spendly.com`) exists with a werkzeug-hashed password (not plaintext)
- [ ] 8 sample expenses exist, linked to the demo user, covering all 7 categories, dated in the current month
- [ ] Restarting the app (re-running `seed_db()`) produces no duplicate seed data
- [ ] App starts with `python app.py` without errors and existing placeholder routes still work
- [ ] Foreign key enforcement works — inserting an expense with an invalid `user_id` fails
- [ ] All queries use parameterized SQL with no string formatting of values
