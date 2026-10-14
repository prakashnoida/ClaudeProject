# Spec 06 — Date Filter on Profile Page

## Overview

- Step 06 adds a date-range filter to the existing `/profile` route so users can narrow the transaction list, summary stats, and category breakdown to a specific period
- The filter is driven entirely by query-string parameters (`date_from` and `date_to`) on `GET /profile` — no new routes required
- A compact filter bar with four quick-select preset buttons ("This Month", "Last 3 Months", "Last 6 Months", "All Time") and two `<input type="date">` fields lets users pick any custom range
- All three data sections (summary stats, recent transactions, category breakdown) must respect the active date filter
- The user info card is not affected by the filter

## Depends on

- Step 01 — Database setup (`expenses` table with `date` column must exist)
- Step 04 — Profile page UI (template with all four sections must exist)
- Step 05 — Backend connection (`get_summary_stats`, `get_recent_transactions`, `get_category_breakdown` in `database/queries.py` must exist and be wired to the `/profile` route)

## Routes

- No new routes
- The existing `GET /profile` route is modified to read two optional query parameters:
  - `date_from` — ISO date string `YYYY-MM-DD`, inclusive lower bound
  - `date_to` — ISO date string `YYYY-MM-DD`, inclusive upper bound
- If either parameter is absent or malformed, the route falls back to an unfiltered "All Time" view — never errors out
- The filter applies only when both parameters are present and valid; a single valid bound on its own is treated as no filter
- The route remains logged-in only — unauthenticated requests still redirect to `url_for("login")`, with or without query params

## Database changes

- No database changes
- The `expenses.date` column (`TEXT`, `YYYY-MM-DD`) already supports `BETWEEN` comparison in SQLite
- `BETWEEN` is inclusive on both ends, so expenses dated exactly on `date_from` or `date_to` are included

## Templates

- Modify: `templates/profile.html`
  - Add a filter bar section above the summary stats row containing:
    - Four quick-select preset buttons: "This Month", "Last 3 Months", "Last 6 Months", "All Time"
      - Each is a link to `/profile` with the appropriate `date_from` / `date_to` query params computed in `app.py`
      - "All Time" passes no query params (clean `/profile` URL)
    - A custom range sub-form with two `<input type="date">` fields (`date_from`, `date_to`) and an "Apply" submit button
      - The form uses `method="get"` and `action="{{ url_for('profile') }}"`
      - Both inputs are pre-filled with the currently active `date_from` / `date_to` when a filter is applied, and empty otherwise
    - The currently active preset or custom range must be visually highlighted with an active state on the button
      - When no filter is active, "All Time" is highlighted
      - When the active range matches no preset, no preset is highlighted and the custom-range fields show the active dates
  - Show flashed messages (e.g. "Start date must be before end date.") near the filter bar, unless `base.html` already renders flashed messages for every page
  - No structural changes to any existing section — only the Jinja variables fed into them change when a filter is active
  - All amounts continue to render with `₹` and two decimal places

## Files to change

- `app.py`
  - In `profile()` view: read `date_from` and `date_to` from `request.args`
  - Validate both values are well-formed ISO dates using `datetime.strptime(value, "%Y-%m-%d")`; on `ValueError` treat as absent
  - If `date_from > date_to` after validation: treat both as absent, flash "Start date must be before end date."
  - Compute preset date ranges in `app.py` — never in the template:
    - "This Month" — `date_from` = first day of the current month, `date_to` = today
    - "Last 3 Months" — `date_from` = today minus 3 calendar months (clamped to the last valid day of that month), `date_to` = today
    - "Last 6 Months" — `date_from` = today minus 6 calendar months (clamped the same way), `date_to` = today
    - "All Time" — no `date_from` / `date_to`
  - Determine which preset (if any) matches the validated range and pass it to the template as the active preset key
  - Pass validated `date_from`, `date_to`, and preset URL params back to the template so the filter bar can reflect the active state
  - Pass `date_from` and `date_to` to each of the three query helpers
  - Ensure `flash` is imported from `flask` and `app.secret_key` is set (required for flashing)
- `database/queries.py`
  - `get_summary_stats(user_id, date_from=None, date_to=None)`
    - When both params are provided add `AND date BETWEEN ? AND ?` to the expenses queries
    - When absent behave identically to Step 05 (unfiltered)
    - The filter applies to `total_spent`, `transaction_count`, and `top_category` alike
  - `get_recent_transactions(user_id, limit=10, date_from=None, date_to=None)`
    - Same pattern; ordering newest-first and limit remain unchanged
  - `get_category_breakdown(user_id, date_from=None, date_to=None)`
    - Same pattern; percentage recalculation logic remains unchanged
    - Percentages are computed against the filtered total, so they still sum to 100
  - Existing callers that pass only `user_id` (and tests from Step 05) must keep working unchanged
- `templates/profile.html` — add filter bar (see Templates section above)
- `static/css/profile.css` — add styles for the filter bar and active-preset button state using CSS variables only
  - The filter bar must wrap cleanly on narrow screens

## Files to create

- None

## New dependencies

- None

## Rules for implementation

- No SQLAlchemy or ORMs — raw `sqlite3` only via `get_db()`
- Parameterised queries only — never string-format dates into SQL; use `?` placeholders even for date-range bounds
- The optional `AND date BETWEEN ? AND ?` clause may be appended conditionally, but only as a fixed SQL fragment — the date values themselves always go in the parameters tuple
- Date validation in `app.py`: use `datetime.strptime(value, "%Y-%m-%d")`; on `ValueError` treat the param as absent (fall back to no filter)
- Only validated dates are passed to the query helpers and back to the template — raw `request.args` values are never echoed into the page
- Preset links must be generated with `url_for("profile", date_from=..., date_to=...)` — never hardcoded URL strings in the template
- When `date_from` and `date_to` are both absent, all three query helpers must behave identically to their Step 05 behaviour (unfiltered)
- If `date_from > date_to` after validation, treat both as absent and flash: "Start date must be before end date."
- "All Time" preset must pass no query params (clean `/profile` URL)
- Preset date calculations must be computed in `app.py`, not in the template
- Currency must always display as `₹` — never `£` or `$`
- Use CSS variables — never hardcode hex values
- No inline styles
- All templates extend `base.html`
- Use `url_for()` for every internal link — never hardcode paths

## Definition of done

- [ ] Visiting `/profile` with no query params returns the same data as Step 05 (unfiltered, all expenses)
- [ ] Clicking "This Month" filters all three sections to the current calendar month only
- [ ] Clicking "Last 3 Months" filters to expenses in the 3-month window ending today
- [ ] Clicking "Last 6 Months" filters to expenses in the 6-month window ending today
- [ ] Clicking "All Time" removes any active filter and shows all expenses
- [ ] Submitting a custom date range with valid `date_from` and `date_to` shows only expenses within that range in all three sections
- [ ] Submitting a range where `date_from > date_to` shows a flash error and falls back to the unfiltered view
- [ ] Submitting a malformed date string (e.g. `date_from=not-a-date`) does not crash the app — it silently falls back to the unfiltered view
- [ ] The active preset button or custom-range fields visually indicate which filter is currently applied
- [ ] All amounts continue to display the ₹ symbol regardless of active filter
- [ ] A user with no expenses in the selected range sees ₹0.00 total spent, 0 transactions, and an empty category breakdown — no errors
- [ ] Expenses dated exactly on `date_from` or `date_to` are included in the results
- [ ] Step 05 tests in `tests/test_backend_connection.py` still pass unchanged
