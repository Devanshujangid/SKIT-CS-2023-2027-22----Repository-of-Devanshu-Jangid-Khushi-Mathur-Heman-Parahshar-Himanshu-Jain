
from unittest.mock import MagicMock

import pytest

from services import recommendation_service as service_module


@pytest.fixture
def service():
    return service_module.RecommendationService()


@pytest.fixture
def mock_supabase(monkeypatch):
    """Mock Supabase resource retrieval."""

    resources = [
        {
            "id": "admin-1",
            "title": "Quantum Computing Fundamentals",
            "description": "Learn quantum algorithms and qubits",
            "url": "https://example.com/quantum",
            "category": "Course",
            "subject": "Computer Science",
            "tags": ["quantum", "algorithms"],
            "is_active": True,
        },
        {
            "id": "admin-2",
            "title": "Advanced Python Programming",
            "description": "Python programming and software development",
            "url": "https://example.com/python",
            "category": "Tutorial",
            "subject": "Programming",
            "tags": ["python", "coding"],
            "is_active": True,
        },
    ]

    db = MagicMock()
    query = db.table.return_value
    query.select.return_value = query
    query.eq.return_value = query
    query.execute.return_value.data = resources

    monkeypatch.setattr(
        service_module,
        "get_db",
        lambda: db,
    )

    return db


def test_empty_query_returns_empty_list(service):
    assert service.recommend_courses("") == []
    assert service.recommend_courses("   ") == []


def test_invalid_top_n_returns_empty_list(service):
    assert service.recommend_courses("python", 0) == []
    assert service.recommend_courses("python", -1) == []
    assert service.recommend_courses("python", True) == []


def test_admin_resources_are_included(
    service,
    mock_supabase,
):
    results = service.recommend_courses(
        "quantum algorithms qubits",
        top_n=5,
    )

    assert any(
        item["source"] == "admin"
        and item["course_name"] == "Quantum Computing Fundamentals"
        for item in results
    )

    mock_supabase.table.assert_called_with(
        "learning_resources"
    )


def test_only_active_resources_are_requested(
    service,
    mock_supabase,
):
    service.recommend_courses("python programming")

    mock_supabase.table.return_value.select.return_value.eq.assert_called_with(
        "is_active",
        True,
    )


def test_admin_resource_fields_are_preserved(
    service,
    mock_supabase,
):
    results = service.recommend_courses(
        "quantum algorithms",
    )

    admin_results = [
        item for item in results
        if item["source"] == "admin"
    ]

    assert admin_results

    resource = admin_results[0]

    assert resource["resource_id"] == "admin-1"
    assert resource["course_url"] == "https://example.com/quantum"
    assert resource["subject"] == "Computer Science"


def test_coursera_search_works_when_database_is_unavailable(
    service,
    monkeypatch,
):
    monkeypatch.setattr(
        service_module,
        "get_db",
        lambda: None,
    )

    results = service.recommend_courses(
        "python programming",
        top_n=5,
    )

    assert isinstance(results, list)
    assert all(
        item["source"] == "coursera"
        for item in results
    )


def test_recommendation_limit_is_respected(
    service,
    mock_supabase,
):
    results = service.recommend_courses(
        "python programming",
        top_n=2,
    )

    assert len(results) <= 2


def test_unknown_query_returns_empty_list(
    service,
    mock_supabase,
):
    results = service.recommend_courses(
        "xyzqwerty nonexistenttopic",
    )

    assert results == []
