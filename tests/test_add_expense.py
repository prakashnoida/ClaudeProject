import pytest

import database.db
from app import app
from database.db import create_user, get_db, init_db, seed_db
from database.queries import insert_expense

CATEGORIES = ["Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"]

VALID_FORM = {
    "amount": "50.0",
    "category": "Food",
    "date": "2026-03-20",
    "description": "Lunch",
}


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(database.db, "DB_PATH", str(tmp_path / "test.db"))
    init_db()
    seed_db()


@pytest.fixture
def user_id(temp_db):
    return create_user("Test User", "test@example.com", "password123")


@pytest.fixture
def client(temp_db):
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def auth_client(client, user_id):
    client.post("/login", data={"email": "test@example.com", "password": "password123"})
    return client


def expenses_for(user_id):
    conn = get_db()
    try:
        return conn.execute(
            "SELECT user_id, amount, category, date, description FROM expenses "
            "WHERE user_id = ? ORDER BY id",
            (user_id,),
        ).fetchall()
    finally:
        conn.close()


def total_expense_count():
    conn = get_db()
    try:
        return conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
    finally:
        conn.close()


# ------------------------------------------------------------------ #
# insert_expense                                                      #
# ------------------------------------------------------------------ #

def test_insert_expense_with_description(user_id):
    expense_id = insert_expense(user_id, 50.0, "Food", "2026-03-20", "Lunch")
    assert isinstance(expense_id, int)

    rows = expenses_for(user_id)
    assert len(rows) == 1
    assert dict(rows[0]) == {
        "user_id": user_id,
        "amount": 50.0,
        "category": "Food",
        "date": "2026-03-20",
        "description": "Lunch",
    }


def test_insert_expense_without_description(user_id):
    insert_expense(user_id, 50.0, "Food", "2026-03-20", None)
    rows = expenses_for(user_id)
    assert len(rows) == 1
    assert rows[0]["description"] is None


# ------------------------------------------------------------------ #
# GET /expenses/add                                                   #
# ------------------------------------------------------------------ #

def test_get_add_expense_unauthenticated_redirects(client):
    response = client.get("/expenses/add")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_get_add_expense_authenticated_shows_form(auth_client):
    response = auth_client.get("/expenses/add")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert '<form method="POST"' in html
    assert 'action="/expenses/add"' in html
    assert '<select id="category" name="category"' in html
    for cat in CATEGORIES:
        assert f'<option value="{cat}"' in html
    assert html.count("<option ") == len(CATEGORIES)
    assert "₹" in html


def test_navbar_link_only_when_logged_in(client, user_id):
    assert "Add Expense" not in client.get("/").get_data(as_text=True)
    client.post("/login", data={"email": "test@example.com", "password": "password123"})
    assert 'href="/expenses/add"' in client.get("/").get_data(as_text=True)


def test_profile_has_add_expense_button(auth_client):
    html = auth_client.get("/profile").get_data(as_text=True)
    assert 'class="btn-add"' in html
    assert 'href="/expenses/add"' in html


# ------------------------------------------------------------------ #
# POST /expenses/add                                                  #
# ------------------------------------------------------------------ #

def test_post_add_expense_unauthenticated_redirects(client):
    before = total_expense_count()
    response = client.post("/expenses/add", data=VALID_FORM)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")
    assert total_expense_count() == before


def test_post_add_expense_valid(auth_client, user_id):
    response = auth_client.post("/expenses/add", data=VALID_FORM)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/profile")

    rows = expenses_for(user_id)
    assert len(rows) == 1
    assert rows[0]["amount"] == 50.0
    assert rows[0]["category"] == "Food"
    assert rows[0]["date"] == "2026-03-20"
    assert rows[0]["description"] == "Lunch"


def test_post_add_expense_appears_on_profile(auth_client):
    auth_client.post("/expenses/add", data=VALID_FORM)
    html = auth_client.get("/profile").get_data(as_text=True)
    assert "Lunch" in html
    assert "₹50.00" in html


def test_post_add_expense_no_description(auth_client, user_id):
    data = {**VALID_FORM, "description": "   "}
    response = auth_client.post("/expenses/add", data=data)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/profile")

    rows = expenses_for(user_id)
    assert len(rows) == 1
    assert rows[0]["description"] is None


def test_post_add_expense_rounds_amount(auth_client, user_id):
    auth_client.post("/expenses/add", data={**VALID_FORM, "amount": "12.345"})
    assert expenses_for(user_id)[0]["amount"] == 12.35


def test_post_add_expense_ignores_form_user_id(auth_client, user_id):
    auth_client.post("/expenses/add", data={**VALID_FORM, "user_id": "1"})
    assert len(expenses_for(user_id)) == 1
    assert len(expenses_for(1)) == 8  # seeded demo user untouched


@pytest.mark.parametrize(
    "overrides, expected_values",
    [
        ({"amount": ""}, ['value="2026-03-20"', 'value="Lunch"', '<option value="Food" selected>']),
        ({"amount": "0"}, ['value="0"', 'value="2026-03-20"', 'value="Lunch"']),
        ({"amount": "-5"}, ['value="-5"', 'value="2026-03-20"']),
        ({"amount": "abc"}, ['value="abc"', 'value="2026-03-20"', 'value="Lunch"']),
        ({"amount": "nan"}, ['value="nan"', 'value="Lunch"']),
        ({"amount": "inf"}, ['value="inf"', 'value="Lunch"']),
        ({"category": "Crypto"}, ['value="50.0"', 'value="2026-03-20"', 'value="Lunch"']),
        ({"category": ""}, ['value="50.0"', 'value="2026-03-20"']),
        ({"date": "20-03-2026"}, ['value="50.0"', 'value="20-03-2026"', '<option value="Food" selected>']),
        ({"date": "2026-02-30"}, ['value="50.0"', 'value="2026-02-30"']),
        ({"date": ""}, ['value="50.0"', 'value="Lunch"']),
        ({"description": "x" * 201}, ['value="50.0"', 'value="2026-03-20"']),
    ],
    ids=[
        "missing-amount", "zero-amount", "negative-amount", "non-numeric-amount",
        "nan-amount", "inf-amount", "invalid-category", "missing-category",
        "bad-date-format", "impossible-date", "missing-date", "long-description",
    ],
)
def test_post_add_expense_validation_errors(auth_client, user_id, overrides, expected_values):
    before = total_expense_count()
    response = auth_client.post("/expenses/add", data={**VALID_FORM, **overrides})

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'class="auth-error"' in html
    for snippet in expected_values:
        assert snippet in html
    assert expenses_for(user_id) == []
    assert total_expense_count() == before
