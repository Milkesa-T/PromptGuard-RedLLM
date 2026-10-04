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
    
    stats = db.get_aggregate_stats()
    assert stats["total_attacks"] == 1
    assert stats["successful_attacks"] == 1
    assert stats["attack_success_rate"] == 100.0
