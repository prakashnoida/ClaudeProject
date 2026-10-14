import re

import pytest

import database.db
from app import app
from database.db import create_user, get_db, init_db, seed_db
from database.queries import (
    get_expense_by_id,
    get_recent_transactions,
    insert_expense,
    update_expense,
)

VALID_FORM = {
    "amount": "99.0",
    "category": "Bills",
    "date": "2026-04-15",
    "description": "Internet bill",
}

ORIGINAL = {
    "amount": 50.0,
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
def owner_id(temp_db):
    return create_user("Owner", "owner@example.com", "password123")


@pytest.fixture
def other_id(temp_db):
    return create_user("Other", "other@example.com", "password123")


@pytest.fixture
def expense_id(owner_id):
    return insert_expense(owner_id, *ORIGINAL.values())


@pytest.fixture
def other_expense_id(other_id):
    return insert_expense(other_id, 75.0, "Shopping", "2026-03-21", "Shoes")


@pytest.fixture
def client(temp_db):
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def auth_client(client, owner_id):
    client.post("/login", data={"email": "owner@example.com", "password": "password123"})
    return client


def fetch_row(expense_id):
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT user_id, amount, category, date, description, created_at "
            "FROM expenses WHERE id = ?",
            (expense_id,),
        ).fetchone()
    finally:
        conn.close()
    return dict(row) if row else None


# ------------------------------------------------------------------ #
# get_expense_by_id                                                   #
# ------------------------------------------------------------------ #

def test_get_expense_by_id_own(owner_id, expense_id):
    assert get_expense_by_id(expense_id, owner_id) == {"id": expense_id, **ORIGINAL}


def test_get_expense_by_id_wrong_user(other_id, expense_id):
    assert get_expense_by_id(expense_id, other_id) is None


def test_get_expense_by_id_missing(owner_id):
    assert get_expense_by_id(9999, owner_id) is None


# ------------------------------------------------------------------ #
# update_expense                                                      #
# ------------------------------------------------------------------ #

def test_update_expense_owner(owner_id, expense_id):
    created_at = fetch_row(expense_id)["created_at"]
    assert update_expense(expense_id, owner_id, 99.0, "Food", "2026-03-20", "Lunch") == 1

    row = fetch_row(expense_id)
    assert row["amount"] == 99.0
    assert row["created_at"] == created_at


def test_update_expense_wrong_user(other_id, expense_id):
    before = fetch_row(expense_id)
    assert update_expense(expense_id, other_id, 99.0, "Bills", "2026-04-15", "x") == 0
    assert fetch_row(expense_id) == before


# ------------------------------------------------------------------ #
# get_recent_transactions                                             #
# ------------------------------------------------------------------ #

def test_get_recent_transactions_includes_id(owner_id, expense_id):
    second_id = insert_expense(owner_id, 10.0, "Other", "2026-03-25", None)
    txns = get_recent_transactions(owner_id)
    assert [t["id"] for t in txns] == [second_id, expense_id]
    for txn in txns:
        assert fetch_row(txn["id"])["date"] == txn["date"]


# ------------------------------------------------------------------ #
# GET /expenses/<id>/edit                                             #
# ------------------------------------------------------------------ #

def test_get_edit_unauthenticated_redirects(client, expense_id):
    response = client.get(f"/expenses/{expense_id}/edit")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_get_edit_own_expense_prefilled(auth_client, expense_id):
    response = auth_client.get(f"/expenses/{expense_id}/edit")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert '<form method="POST"' in html
    assert f'action="/expenses/{expense_id}/edit"' in html
    assert 'value="50.00"' in html
    assert 'value="2026-03-20"' in html
    assert 'value="Lunch"' in html
    assert '<option value="Food" selected>' in html
    assert html.count(" selected>") == 1
    assert "Save Changes" in html
    assert "₹" in html


def test_get_edit_null_description_renders_empty(auth_client, owner_id):
    expense_id = insert_expense(owner_id, 10.0, "Other", "2026-03-25", None)
    html = auth_client.get(f"/expenses/{expense_id}/edit").get_data(as_text=True)
    assert 'name="description"' in html
    assert "None" not in html


def test_get_edit_other_users_expense_404(auth_client, other_expense_id):
    assert auth_client.get(f"/expenses/{other_expense_id}/edit").status_code == 404


def test_get_edit_missing_expense_404(auth_client):
    assert auth_client.get("/expenses/9999/edit").status_code == 404


# ------------------------------------------------------------------ #
# POST /expenses/<id>/edit                                            #
# ------------------------------------------------------------------ #

def test_post_edit_unauthenticated_redirects(client, expense_id):
    before = fetch_row(expense_id)
    response = client.post(f"/expenses/{expense_id}/edit", data=VALID_FORM)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")
    assert fetch_row(expense_id) == before


def test_post_edit_valid(auth_client, owner_id, expense_id):
    response = auth_client.post(f"/expenses/{expense_id}/edit", data=VALID_FORM)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/profile")

    row = fetch_row(expense_id)
    assert row["user_id"] == owner_id
    assert row["amount"] == 99.0
    assert row["category"] == "Bills"
    assert row["date"] == "2026-04-15"
    assert row["description"] == "Internet bill"


def test_post_edit_reflected_on_profile(auth_client, expense_id):
    auth_client.post(f"/expenses/{expense_id}/edit", data=VALID_FORM)
    html = auth_client.get("/profile").get_data(as_text=True)
    assert "Internet bill" in html
    assert "₹99.00" in html
    assert "Lunch" not in html


def test_post_edit_other_users_expense_404(auth_client, other_expense_id):
    before = fetch_row(other_expense_id)
    response = auth_client.post(f"/expenses/{other_expense_id}/edit", data=VALID_FORM)
    assert response.status_code == 404
    assert fetch_row(other_expense_id) == before


def test_post_edit_missing_expense_404(auth_client):
    assert auth_client.post("/expenses/9999/edit", data=VALID_FORM).status_code == 404


def test_post_edit_ignores_form_ids(auth_client, owner_id, expense_id, other_id, other_expense_id):
    other_before = fetch_row(other_expense_id)
    data = {**VALID_FORM, "id": str(other_expense_id), "user_id": str(other_id)}
    auth_client.post(f"/expenses/{expense_id}/edit", data=data)

    row = fetch_row(expense_id)
    assert row["user_id"] == owner_id
    assert row["amount"] == 99.0
    assert fetch_row(other_expense_id) == other_before


def test_post_edit_no_description(auth_client, expense_id):
    response = auth_client.post(
        f"/expenses/{expense_id}/edit", data={**VALID_FORM, "description": "  "}
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/profile")
    assert fetch_row(expense_id)["description"] is None


@pytest.mark.parametrize(
    "overrides, expected_values",
    [
        ({"amount": ""}, ['value="2026-04-15"', 'value="Internet bill"', '<option value="Bills" selected>']),
        ({"amount": "0"}, ['value="0"', 'value="2026-04-15"', 'value="Internet bill"']),
        ({"amount": "abc"}, ['value="abc"', 'value="2026-04-15"', 'value="Internet bill"']),
        ({"category": "Crypto"}, ['value="99.0"', 'value="2026-04-15"', 'value="Internet bill"']),
        ({"date": "15-04-2026"}, ['value="99.0"', 'value="15-04-2026"', '<option value="Bills" selected>']),
        ({"description": "x" * 201}, ['value="99.0"', 'value="2026-04-15"']),
    ],
    ids=[
        "missing-amount", "zero-amount", "non-numeric-amount",
        "invalid-category", "invalid-date", "long-description",
    ],
)
def test_post_edit_validation_errors(auth_client, expense_id, overrides, expected_values):
    before = fetch_row(expense_id)
    response = auth_client.post(
        f"/expenses/{expense_id}/edit", data={**VALID_FORM, **overrides}
    )

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'class="auth-error"' in html
    for snippet in expected_values:
        assert snippet in html
    # Submitted values are shown, not the original ones.
    assert 'value="Lunch"' not in html
    assert 'value="2026-03-20"' not in html
    assert fetch_row(expense_id) == before


# ------------------------------------------------------------------ #
# Profile edit links                                                  #
# ------------------------------------------------------------------ #

def test_profile_rows_have_edit_links(auth_client, owner_id, expense_id):
    second_id = insert_expense(owner_id, 10.0, "Other", "2026-03-25", None)
    html = auth_client.get("/profile").get_data(as_text=True)

    assert "<th class=\"txn-actions\">Actions</th>" in html
    links = re.findall(r'href="/expenses/(\d+)/edit"', html)
    assert sorted(int(i) for i in links) == sorted([expense_id, second_id])
    assert "None" not in html
