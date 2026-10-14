import re

import pytest

import database.db
from app import app
from database.db import create_user, get_db, init_db, seed_db
from database.queries import delete_expense, insert_expense


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
    return insert_expense(owner_id, 50.0, "Food", "2026-03-20", "Lunch")


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


def row_exists(expense_id):
    conn = get_db()
    try:
        return conn.execute(
            "SELECT 1 FROM expenses WHERE id = ?", (expense_id,)
        ).fetchone() is not None
    finally:
        conn.close()


def total_expense_count():
    conn = get_db()
    try:
        return conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
    finally:
        conn.close()


# ------------------------------------------------------------------ #
# delete_expense                                                      #
# ------------------------------------------------------------------ #

def test_delete_expense_owner(owner_id, expense_id):
    assert delete_expense(expense_id, owner_id) == 1
    assert not row_exists(expense_id)


def test_delete_expense_wrong_user(other_id, expense_id):
    assert delete_expense(expense_id, other_id) == 0
    assert row_exists(expense_id)


def test_delete_expense_missing(owner_id, expense_id):
    before = total_expense_count()
    assert delete_expense(9999, owner_id) == 0
    assert total_expense_count() == before


# ------------------------------------------------------------------ #
# POST /expenses/<id>/delete                                          #
# ------------------------------------------------------------------ #

def test_post_delete_unauthenticated_redirects(client, expense_id):
    response = client.post(f"/expenses/{expense_id}/delete")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")
    assert row_exists(expense_id)


def test_post_delete_own_expense(auth_client, expense_id):
    response = auth_client.post(f"/expenses/{expense_id}/delete")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/profile")
    assert not row_exists(expense_id)


def test_post_delete_other_users_expense_404(auth_client, other_expense_id):
    response = auth_client.post(f"/expenses/{other_expense_id}/delete")
    assert response.status_code == 404
    assert row_exists(other_expense_id)


def test_post_delete_missing_expense_404(auth_client, expense_id):
    before = total_expense_count()
    assert auth_client.post("/expenses/9999/delete").status_code == 404
    assert total_expense_count() == before


def test_post_delete_ignores_form_ids(auth_client, expense_id, other_id, other_expense_id):
    data = {"id": str(other_expense_id), "user_id": str(other_id)}
    auth_client.post(f"/expenses/{expense_id}/delete", data=data)
    assert not row_exists(expense_id)
    assert row_exists(other_expense_id)


# ------------------------------------------------------------------ #
# GET /expenses/<id>/delete                                           #
# ------------------------------------------------------------------ #

def test_get_delete_unauthenticated_405(client, expense_id):
    assert client.get(f"/expenses/{expense_id}/delete").status_code == 405
    assert row_exists(expense_id)


def test_get_delete_authenticated_405(auth_client, expense_id):
    assert auth_client.get(f"/expenses/{expense_id}/delete").status_code == 405
    assert row_exists(expense_id)


# ------------------------------------------------------------------ #
# Profile page                                                        #
# ------------------------------------------------------------------ #

def test_profile_rows_have_edit_and_delete(auth_client, owner_id, expense_id):
    second_id = insert_expense(owner_id, 10.0, "Other", "2026-03-25", "Snacks")
    html = auth_client.get("/profile").get_data(as_text=True)
    expected = sorted([expense_id, second_id])

    edit_ids = re.findall(r'href="/expenses/(\d+)/edit"', html)
    delete_ids = re.findall(r'<form method="POST" action="/expenses/(\d+)/delete"', html)
    assert sorted(map(int, edit_ids)) == expected
    assert sorted(map(int, delete_ids)) == expected
    assert html.count("return confirm('Delete this expense?')") == 2
    assert html.count('class="btn-delete"') == 2


def test_profile_updates_after_delete(auth_client, owner_id, expense_id):
    insert_expense(owner_id, 10.0, "Other", "2026-03-25", "Snacks")
    auth_client.post(f"/expenses/{expense_id}/delete")

    html = auth_client.get("/profile").get_data(as_text=True)
    assert "Lunch" not in html
    assert "Snacks" in html
    assert "₹10.00" in html
    assert "₹60.00" not in html
