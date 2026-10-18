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
