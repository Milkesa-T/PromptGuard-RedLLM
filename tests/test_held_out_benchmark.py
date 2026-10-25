import pytest
from evaluation.benchmark import BenchmarkRunner
from database.db import AuditDatabase


@pytest.mark.asyncio
async def test_held_out_benchmark_evaluation(tmp_path):
    test_db_path = str(tmp_path / "test_benchmark_audit.db")
    test_db = AuditDatabase(db_path=test_db_path)
    runner = BenchmarkRunner(db=test_db)

    result = await runner.run_held_out_benchmark(enable_guard=True, max_attacks=6, max_benign=6)

    assert result["evaluation_type"] == "held_out_dual_split"
    assert result["total_attacks"] == 6
    assert result["total_benign"] == 6
    assert isinstance(result["attack_success_rate"], float)
    assert isinstance(result["false_positive_rate"], float)
    assert "per_category" in result
    assert "owasp_matrix" in result
    assert "avg_attack_latency_ms" in result
    assert "avg_benign_latency_ms" in result


@pytest.mark.asyncio
async def test_adaptive_rounds_progression(tmp_path):
    test_db_path = str(tmp_path / "test_adaptive_audit.db")
    test_db = AuditDatabase(db_path=test_db_path)
    runner = BenchmarkRunner(db=test_db)

    result = await runner.run_adaptive_rounds_benchmark(max_samples=4)

    assert result["status"] == "completed"
    assert "round_1_baseline" in result
    assert "round_2_adapted" in result
    assert "comparison" in result
    assert "asr_reduction_percentage" in result["comparison"]
    assert "total_active_vectors" in result["comparison"]
