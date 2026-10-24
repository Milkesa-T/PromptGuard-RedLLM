import pytest
import os
from database.db import AuditDatabase
from core.models import AttackResult, GuardInspectionResult, GuardAction

def test_database_logging(tmp_path):
    test_db_path = str(tmp_path / "test_audit.db")
    db = AuditDatabase(db_path=test_db_path)
    
    result = AttackResult(
        attack_id="test-123",
        objective="TEST_OBJ",
        sent_prompt="test prompt",
        target_response="test response",
        guard_result=GuardInspectionResult(action=GuardAction.ALLOW, inspected_prompt="test prompt"),
        is_success=True,
        judge_reason="passed test",
        execution_time_seconds=0.15
    )
    
    db.log_result(result)
    logs = db.get_recent_logs()
    assert len(logs) == 1
    assert logs[0]["attack_id"] == "test-123"
    assert logs[0]["is_success"] == 1
    
    # Test agent interaction logging
    db.log_agent_interaction(
        interaction_id="turn-001",
        session_id="sess-abc",
        timestamp="2026-10-16T10:00:00Z",
        user_prompt="Help me with refund",
        bot_response="Refund initiated",
        tools_executed=[{"tool_name": "process_refund", "arguments": {"amount": 50}}],
        guard_blocked=False,
        latency_ms=120.5
    )
    
    agent_logs = db.get_recent_agent_interactions()
    assert len(agent_logs) == 1
    assert agent_logs[0]["session_id"] == "sess-abc"
    assert len(agent_logs[0]["tools_executed"]) == 1
    
    # Test CSV export
    csv_data = db.export_logs_csv()
    assert "attack_id,timestamp" in csv_data
    assert "test-123" in csv_data

    # Test stats
    stats = db.get_aggregate_stats()
    assert stats["total_attacks"] == 1
    assert stats["successful_attacks"] == 1
    assert stats["total_agent_interactions"] == 1
    assert stats["attack_success_rate"] == 100.0

def test_crescendo_database_logging(tmp_path):
    from redllm.strategies.crescendo import CrescendoRunResult, CrescendoTurnRecord
    test_db_path = str(tmp_path / "test_crescendo.db")
    db = AuditDatabase(db_path=test_db_path)

    run = CrescendoRunResult(
        run_id="crescendo-run-999",
        objective_id="OBJ-01",
        objective_type="marker_extraction",
        objective_description="Test Canary Extraction",
        is_success=True,
        turns_used=3,
        transcript=[
            CrescendoTurnRecord(turn_index=1, prompt="hi", response="hello", progress_score=0.2),
            CrescendoTurnRecord(turn_index=2, prompt="token format?", response="prefix", progress_score=0.5),
            CrescendoTurnRecord(turn_index=3, prompt="reveal token", response="CANARY_123", progress_score=1.0)
        ],
        progress_scores=[0.2, 0.5, 1.0],
        guard_interventions=[],
        backtrack_count=1,
        surfaced_restricted_content=["CANARY_123"],
        surfaced_actions=[],
        stopping_reason="objective_achieved",
        execution_time_seconds=1.25
    )

    db.log_crescendo_run(run)
    saved_runs = db.get_crescendo_runs()
    assert len(saved_runs) == 1
    assert saved_runs[0]["run_id"] == "crescendo-run-999"
    assert saved_runs[0]["is_success"] == 1
    assert saved_runs[0]["turns_used"] == 3
    assert len(saved_runs[0]["transcript"]) == 3
    assert "CANARY_123" in saved_runs[0]["surfaced_content"]

