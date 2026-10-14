import calendar
import math
import sqlite3
from datetime import date, datetime

from flask import Flask, render_template, request, redirect, url_for, flash, abort, session
from werkzeug.security import check_password_hash

from database.db import get_db, init_db, seed_db, create_user, get_user_by_email
from database.queries import (
    get_user_by_id,
    get_summary_stats,
    get_recent_transactions,
    get_category_breakdown,
    insert_expense,
    get_expense_by_id,
    update_expense,
    # Aliased so the delete_expense view below doesn't shadow it.
    delete_expense as delete_expense_row,
)

app = Flask(__name__)
app.secret_key = "spendly-dev-secret-key"

CATEGORIES = ["Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"]
DESCRIPTION_MAX_LENGTH = 200

with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Date filter helpers                                                 #
# ------------------------------------------------------------------ #

def parse_iso_date(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def months_ago(day, months):
    month_index = day.year * 12 + (day.month - 1) - months
    year, month = divmod(month_index, 12)
    month += 1
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(day.day, last_day))


def build_date_presets(today):
    ranges = [
        ("this_month", "This Month", today.replace(day=1), today),
        ("last_3_months", "Last 3 Months", months_ago(today, 3), today),
        ("last_6_months", "Last 6 Months", months_ago(today, 6), today),
    ]
    presets = [
        {
            "key": key,
            "label": label,
            "date_from": start,
            "date_to": end,
            "url": url_for("profile", date_from=start.isoformat(), date_to=end.isoformat()),
        }
        for key, label, start, end in ranges
    ]
    presets.append({
        "key": "all_time",
        "label": "All Time",
        "date_from": None,
        "date_to": None,
        "url": url_for("profile"),
    })
    return presets


# ------------------------------------------------------------------ #
# Expense form helpers                                                #
# ------------------------------------------------------------------ #

def validate_expense_form(form):
    """Return (values, cleaned, error) for a submitted expense form.

    `values` holds the raw submitted strings for re-populating the form;
    `cleaned` is ready for insert_expense() and is None when `error` is set.
    """
    values = {
        "amount": form.get("amount", "").strip(),
        "category": form.get("category", "").strip(),
        "date": form.get("date", "").strip(),
        "description": form.get("description", "").strip(),
    }

    if not values["amount"]:
        return values, None, "Amount is required."
    try:
        amount = float(values["amount"])
    except ValueError:
        return values, None, "Amount must be a number."
    if not math.isfinite(amount) or amount <= 0:
        return values, None, "Amount must be greater than 0."

    if values["category"] not in CATEGORIES:
        return values, None, "Please choose a valid category."

    if parse_iso_date(values["date"]) is None:
        return values, None, "Please enter a valid date (YYYY-MM-DD)."

    if len(values["description"]) > DESCRIPTION_MAX_LENGTH:
        return values, None, f"Description must be {DESCRIPTION_MAX_LENGTH} characters or fewer."

    cleaned = {
        "amount": round(amount, 2),
        "category": values["category"],
        "date": values["date"],
        "description": values["description"] or None,
    }
    return values, cleaned, None


# ------------------------------------------------------------------ #
# Routes                                                            #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")
    if request.method != "POST":
        abort(405)

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")

    if not name or not email or not password or not confirm_password:
        flash("All fields are required", "error")
        return render_template("register.html", name=name, email=email)

    if password != confirm_password:
        flash("Passwords do not match", "error")
        return render_template("register.html", name=name, email=email)

    try:
        create_user(name, email, password)
    except sqlite3.IntegrityError:
        flash("Email already registered", "error")
        return render_template("register.html", name=name, email=email)

    flash("Account created — please sign in", "success")
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")

    user = get_user_by_email(email) if email and password else None
    if user is None or not check_password_hash(user["password_hash"], password):
        flash("Invalid email or password.", "error")
        return render_template("login.html", email=email)

    session.clear()
    session["user_id"] = user["id"]
    session["user_name"] = user["name"]
    return redirect(url_for("landing"))


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


@app.route("/profile")
def profile():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    user = get_user_by_id(user_id)
    if user is None:
        session.clear()
        return redirect(url_for("login"))

    date_from = parse_iso_date(request.args.get("date_from"))
    date_to = parse_iso_date(request.args.get("date_to"))
    if date_from is None or date_to is None:
        date_from = date_to = None
    elif date_from > date_to:
        flash("Start date must be before end date.", "error")
        date_from = date_to = None

    presets = build_date_presets(date.today())
    active_preset = next(
        (p["key"] for p in presets
         if p["date_from"] == date_from and p["date_to"] == date_to),
        None,
    )

    from_str = date_from.isoformat() if date_from else None
    to_str = date_to.isoformat() if date_to else None

    return render_template(
        "profile.html",
        user=user,
        stats=get_summary_stats(user_id, date_from=from_str, date_to=to_str),
        expenses=get_recent_transactions(user_id, date_from=from_str, date_to=to_str),
        category_breakdown=get_category_breakdown(user_id, date_from=from_str, date_to=to_str),
        date_from=from_str,
        date_to=to_str,
        presets=presets,
        active_preset=active_preset,
    )


@app.route("/expenses/add", methods=["GET", "POST"])
def add_expense():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    today = date.today().isoformat()

    if request.method == "GET":
        return render_template(
            "add_expense.html", categories=CATEGORIES, today=today, form={"date": today}
        )

    values, cleaned, error = validate_expense_form(request.form)
    if error:
        flash(error, "error")
        return render_template(
            "add_expense.html", categories=CATEGORIES, today=today, form=values
        )

    insert_expense(
        user_id,
        cleaned["amount"],
        cleaned["category"],
        cleaned["date"],
        cleaned["description"],
    )
    return redirect(url_for("profile"))


@app.route("/expenses/<int:id>/edit", methods=["GET", "POST"])
def edit_expense(id):
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    expense = get_expense_by_id(id, user_id)
    if expense is None:
        abort(404)

    if request.method == "GET":
        form = {
            "amount": "{:.2f}".format(expense["amount"]),
            "category": expense["category"],
            "date": expense["date"],
            "description": expense["description"] or "",
        }
        return render_template(
            "edit_expense.html", expense=expense, categories=CATEGORIES, form=form
        )

    values, cleaned, error = validate_expense_form(request.form)
    if error:
        flash(error, "error")
        return render_template(
            "edit_expense.html", expense=expense, categories=CATEGORIES, form=values
        )

    update_expense(
        id,
        user_id,
        cleaned["amount"],
        cleaned["category"],
        cleaned["date"],
        cleaned["description"],
    )
    return redirect(url_for("profile"))


@app.route("/expenses/<int:id>/delete", methods=["POST"])
def delete_expense(id):
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    if get_expense_by_id(id, user_id) is None:
        abort(404)

    delete_expense_row(id, user_id)
    return redirect(url_for("profile"))


if __name__ == "__main__":
    app.run(debug=True, port=5001)
