"""
API Integration Tests — Crescendo Multi-Turn Evaluation Endpoints.

Tests the /api/crescendo/* routes using FastAPI TestClient.
Mocks are aligned with the actual CrescendoRunResult and BenignEvaluationSummary
Pydantic models to avoid silent field-mismatch bugs.

Patch path: ``backend.routes.crescendo_routes._get_strategy`` is the correct
target when mocking the strategy singleton in these tests.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from backend.app import app
from redllm.strategies.crescendo.models import (
    CrescendoRunResult,
    BenignEvaluationSummary,
)

client = TestClient(app)


def test_api_crescendo_objectives():
    """GET /objectives returns the 5 default crescendo objectives."""
    res = client.get("/api/crescendo/objectives")
    assert res.status_code == 200
    data = res.json()
    assert "objectives" in data
    assert len(data["objectives"]) == 5
    # Validate structure of the first objective
    obj = data["objectives"][0]
    assert "id" in obj
    assert "objective_type" in obj
    assert "name" in obj


def test_api_crescendo_runs_history():
    """GET /runs returns paginated list of historical evaluation runs."""
    res = client.get("/api/crescendo/runs?limit=10")
    assert res.status_code == 200
    data = res.json()
    assert "total" in data
    assert "runs" in data
    assert isinstance(data["runs"], list)


def test_api_crescendo_run_single():
    """POST /run executes a single evaluation and returns a CrescendoRunResult."""
    mock_result = CrescendoRunResult(
        run_id="crescendo_test_123",
        objective_id="OBJ-01",
        objective_type="marker_extraction",
        objective_description="Test Canary Extraction",
        is_success=False,
        turns_used=2,
        stopping_reason="max_turns_reached",
    )

    mock_strategy = MagicMock()
    mock_strategy.run_evaluation.return_value = mock_result

    with patch(
        "backend.routes.crescendo_routes._get_strategy",
        return_value=mock_strategy,
    ):
        payload = {
            "objective_type": "marker_extraction",
            "enable_guard": True,
            "max_turns": 3,
            "max_backtracks": 1,
        }
        res = client.post("/api/crescendo/run", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["run_id"] == "crescendo_test_123"
        assert data["objective_type"] == "marker_extraction"
        assert data["is_success"] is False
        assert data["turns_used"] == 2


def test_api_crescendo_benign_conversations():
    """GET /benign evaluates benign multi-turn conversations and returns FPR summary."""
    mock_summary = BenignEvaluationSummary(
        total_conversations=5,
        total_turns=25,
        blocked_turns=0,
        blocked_conversations=0,
        false_positive_rate_turns=0.0,
        false_positive_rate_conversations=0.0,
    )

    mock_strategy = MagicMock()
    mock_strategy.evaluate_benign.return_value = mock_summary

    with patch(
        "backend.routes.crescendo_routes._get_strategy",
        return_value=mock_strategy,
    ):
        res = client.get("/api/crescendo/benign")
        assert res.status_code == 200
        data = res.json()
        assert data["total_conversations"] == 5
        assert data["total_turns"] == 25
        assert data["blocked_turns"] == 0
        assert data["false_positive_rate_turns"] == 0.0
        assert data["false_positive_rate_conversations"] == 0.0
