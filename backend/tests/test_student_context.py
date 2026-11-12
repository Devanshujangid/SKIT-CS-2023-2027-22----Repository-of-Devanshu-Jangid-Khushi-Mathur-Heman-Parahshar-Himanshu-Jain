
from unittest.mock import MagicMock

import pytest

from services import student_context


@pytest.fixture
def mock_db(monkeypatch):
    db = MagicMock()
    monkeypatch.setattr(student_context, "get_db", lambda: db)
    return db


def setup_profile_query(db, user_data, profile_data):
    user_query = db.table.return_value
    user_query.select.return_value = user_query
    user_query.eq.return_value = user_query
    user_query.limit.return_value = user_query

    user_query.execute.side_effect = [
        MagicMock(data=user_data),
        MagicMock(data=profile_data),
    ]


def test_student_context_returns_profile_goals(mock_db):
    setup_profile_query(
        mock_db,
        [{"id": "user-123"}],
        [{"goals": ["Complete DBMS", "Improve DSA"]}],
    )

    result = student_context.get_student_context("clerk-123")

    assert result["goals"] == ["Complete DBMS", "Improve DSA"]
    assert result["leaderboard_rank"] is None
    assert result["goal_status"] == "unknown"


def test_missing_user_returns_safe_defaults(mock_db):
    setup_profile_query(mock_db, [], [])

    result = student_context.get_student_context("clerk-123")

    assert result == {
        "goals": [],
        "leaderboard_rank": None,
        "goal_status": "unknown",
    }


def test_database_unavailable_returns_safe_defaults(monkeypatch):
    monkeypatch.setattr(student_context, "get_db", lambda: None)

    result = student_context.get_student_context("clerk-123")

    assert result["goals"] == []
    assert result["leaderboard_rank"] is None
    assert result["goal_status"] == "unknown"


def test_empty_clerk_id_returns_safe_defaults():
    result = student_context.get_student_context("")

    assert result["goals"] == []
    assert result["leaderboard_rank"] is None
    assert result["goal_status"] == "unknown"


def test_database_error_returns_safe_defaults(monkeypatch):
    db = MagicMock()
    db.table.side_effect = Exception("Database unavailable")

    monkeypatch.setattr(student_context, "get_db", lambda: db)

    result = student_context.get_student_context("clerk-123")

    assert result["goals"] == []
    assert result["leaderboard_rank"] is None
    assert result["goal_status"] == "unknown"
