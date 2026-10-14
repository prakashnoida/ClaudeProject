import re
from datetime import datetime

import pytest

import database.db
from app import app
from database.db import create_user, init_db, seed_db
from database.queries import (
    get_category_breakdown,
    get_recent_transactions,
    get_summary_stats,
    get_user_by_id,
)

CATEGORIES = {"Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"}


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(database.db, "DB_PATH", str(tmp_path / "test.db"))
    init_db()
    seed_db()


@pytest.fixture
def seed_user_id(temp_db):
    return 1


@pytest.fixture
def empty_user_id(temp_db):
    return create_user("Empty User", "empty@example.com", "password123")


@pytest.fixture
def client(temp_db):
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def login(client, email="demo@spendly.com", password="demo123"):
    return client.post("/login", data={"email": email, "password": password})


# ------------------------------------------------------------------ #
# get_user_by_id                                                      #
# ------------------------------------------------------------------ #

def test_get_user_by_id_valid(seed_user_id):
    user = get_user_by_id(seed_user_id)
    assert user["name"] == "Demo User"
    assert user["email"] == "demo@spendly.com"
    datetime.strptime(user["member_since"], "%B %Y")


def test_get_user_by_id_missing(temp_db):
    assert get_user_by_id(9999) is None


# ------------------------------------------------------------------ #
# get_summary_stats                                                   #
# ------------------------------------------------------------------ #

def test_get_summary_stats_seed_user(seed_user_id):
    stats = get_summary_stats(seed_user_id)
    assert stats["total_spent"] == 346.24
    assert stats["transaction_count"] == 8
    assert stats["top_category"] == "Bills"


def test_get_summary_stats_no_expenses(empty_user_id):
    assert get_summary_stats(empty_user_id) == {
        "total_spent": 0,
        "transaction_count": 0,
        "top_category": "—",
    }


# ------------------------------------------------------------------ #
# get_recent_transactions                                             #
# ------------------------------------------------------------------ #

def test_get_recent_transactions_seed_user(seed_user_id):
    txns = get_recent_transactions(seed_user_id)
    assert len(txns) == 8
    for txn in txns:
        assert set(txn) == {"id", "date", "description", "category", "amount"}
    dates = [txn["date"] for txn in txns]
    assert dates == sorted(dates, reverse=True)


def test_get_recent_transactions_respects_limit(seed_user_id):
    assert len(get_recent_transactions(seed_user_id, limit=3)) == 3


def test_get_recent_transactions_no_expenses(empty_user_id):
    assert get_recent_transactions(empty_user_id) == []


# ------------------------------------------------------------------ #
# get_category_breakdown                                              #
# ------------------------------------------------------------------ #

def test_get_category_breakdown_seed_user(seed_user_id):
    breakdown = get_category_breakdown(seed_user_id)
    amounts = [row["amount"] for row in breakdown]
    assert amounts == sorted(amounts, reverse=True)
    assert {row["name"] for row in breakdown} == CATEGORIES
    assert all(isinstance(row["pct"], int) for row in breakdown)
    assert sum(row["pct"] for row in breakdown) == 100


def test_get_category_breakdown_no_expenses(empty_user_id):
    assert get_category_breakdown(empty_user_id) == []


# ------------------------------------------------------------------ #
# /profile route                                                      #
# ------------------------------------------------------------------ #

def test_profile_requires_login(client):
    response = client.get("/profile")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_profile_seed_user(client):
    login(client)
    response = client.get("/profile")
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert "Demo User" in html
    assert "demo@spendly.com" in html
    assert "₹" in html
    assert "₹346.24" in html
    assert '<span class="stat-value">8</span>' in html
    assert '<span class="stat-value">Bills</span>' in html

    dates = re.findall(r'<td class="txn-date">([\d-]+)</td>', html)
    assert len(dates) == 8
    assert dates == sorted(dates, reverse=True)

    assert html.count('class="breakdown-row"') == 7
    for category in CATEGORIES:
        assert f"bar-{category.lower()} " in html


def test_profile_user_with_no_expenses(client, empty_user_id):
    login(client, "empty@example.com", "password123")
    response = client.get("/profile")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "₹0.00" in html
    assert '<span class="stat-value">0</span>' in html
    assert "No transactions yet." in html
    assert "No spending to break down yet." in html


def test_profile_stale_session_redirects(client):
    with client.session_transaction() as sess:
        sess["user_id"] = 9999
    response = client.get("/profile")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")
    with client.session_transaction() as sess:
        assert "user_id" not in sess
