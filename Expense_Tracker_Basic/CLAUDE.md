# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

"Spendly" is a personal expense tracker built with **Flask + raw SQLite (stdlib `sqlite3`) + Jinja2**. There is no ORM, no frontend framework, and no build step — templates are server-rendered Jinja2, styling is a single plain CSS file, and JS is vanilla.

The repo is currently an early-stage scaffold: `app.py` only has placeholder routes and `database/db.py` is a stub with docstring comments describing what to implement. The project is meant to be built incrementally, one feature at a time, following the spec-driven workflow below.

## Spec-driven development workflow

The root-level `Spec_NN_*_prompt.md` files (01 through 09) are **not specs themselves** — each one is a prompt whose job is to *generate* a detailed spec document, to be saved under `.claude/specs/NN-name.md`. The intended sequence is:

1. `Spec_01_database_setup_prompt.md` → generates `.claude/specs/01-database-setup.md`
2. `Spec_02_Registration.prompt.md` → `.claude/specs/02-registration.md`
3. `Spec_03_login_logout_prompt.md` → `.claude/specs/03-login_logout.md`
4. `Spec_04_Profilepage_prompt.md` → `.claude/specs/04-profile.md`
5. `Spec_05-backend-routes-for-profile-page_prompt.md` → `.claude/specs/05-backend-routes-for-profile-page.md`
6. `Spec_06-date-filter-profile_prompt.md` → `.claude/specs/06-date-filter-profile.md`
7. `Spec_07-add-expense_prompt.md` → `.claude/specs/07-add-expense.md`
8. `Spec_08-edit-expense_prompt.md` → `.claude/specs/08-edit-expense.md`
9. `Spec_09-delete-expense_prompt.md` → `.claude/specs/09-delete-expense.md`

Each generated spec (per the prompt templates) follows the same shape: Overview, Depends on, Routes, Database changes, Templates, Files to change/create, New dependencies, Rules for implementation, Tests to write, Definition of done. When asked to "do step N" or implement a feature described in one of these prompt files, first produce (or read, if it already exists) the corresponding spec under `.claude/specs/`, then implement strictly against it — don't skip ahead to later steps' functionality.

Each step's prompt file also documents the *expected file tree at that point*, which is a reliable way to check how far the project has progressed (e.g. whether `database/queries.py` or `tests/` exist yet).

## Commands

```powershell
# Setup (Windows, PowerShell) — .venv already exists in this checkout
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Run the app (serves on http://localhost:5001)
python app.py

# Run tests
pytest
pytest tests/test_add_expense.py       # single file, once it exists
pytest tests/test_add_expense.py -k valid_data   # single test by keyword
```

There is no lint/format tooling configured in this repo.

## Architecture

- **`app.py`** — single-file Flask app; all routes are defined directly on `app` (no blueprints). `init_db()`/`seed_db()` must be called inside `app.app_context()` at startup so the DB is ready before any route is served.
- **`database/db.py`** — raw `sqlite3` access layer: `get_db()` (opens the DB file in the project root, `row_factory = sqlite3.Row`, `PRAGMA foreign_keys = ON`), `init_db()` (idempotent `CREATE TABLE IF NOT EXISTS`), `seed_db()` (idempotent demo-data seeding), plus per-feature helpers such as `create_user()` / `get_user_by_email()` added in later steps.
- **`database/queries.py`** (created in step 5/7) — read/write query helpers for expenses and profile data (e.g. `get_summary_stats()`, `get_recent_transactions()`, `get_category_breakdown()`, `insert_expense()`), kept separate from `database/db.py`'s connection/schema management.
- **`templates/base.html`** — layout shell every page extends; defines `title`, `head`, `content`, `scripts` blocks, a shared navbar (shows different links depending on `session.user_id`) and footer.
- **`static/css/style.css`** — single global stylesheet; page-specific stylesheets (e.g. `profile.css`) are added per-step and included via each template's `head` block.
- **Auth** — plain Flask `session` (no Flask-Login): logged-in state is `session["user_id"]` (an integer), set on successful login, cleared with `session.clear()` on logout.

## Conventions enforced across every step's spec

These rules recur in every `Spec_*_prompt.md` file and should be treated as standing constraints for any new code in this repo, not just per-feature suggestions:

- No ORM/SQLAlchemy — raw `sqlite3` only, always through `database/db.py`'s `get_db()`.
- Parameterized queries only — never string-format or f-string values into SQL.
- `PRAGMA foreign_keys = ON` must be enabled on every connection.
- Passwords are hashed/verified with `werkzeug.security.generate_password_hash` / `check_password_hash`.
- `amount` is stored as `REAL`; `date` columns are always `YYYY-MM-DD` strings (parse/validate with `datetime.strptime`).
- Expense `category` must be one of exactly 7 fixed values: `Food, Transport, Bills, Health, Entertainment, Shopping, Other`.
- Currency is always displayed as `₹` — never `£` or `$`.
- All templates extend `base.html`; use CSS variables (no hardcoded hex colors) and no inline styles.
- Use `url_for()` for every internal link — never hardcode paths.
- DB helper functions live in `database/db.py` / `database/queries.py`, never inline in route handlers.
- On validation errors, re-render the form with the error message and previously submitted values pre-filled rather than losing input.

## Known inconsistency to check

`.gitignore` ignores `expense_tracker.db`, but the spec-generation prompts (step 1) specify the SQLite file should be `spendly.db` in the project root. Confirm which filename `database/db.py` actually uses once implemented, and keep `.gitignore` in sync.
