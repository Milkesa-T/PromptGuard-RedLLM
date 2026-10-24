import uuid
from typing import List, Optional, Dict, Any
from redllm.strategies.crescendo.models import (
    CrescendoObjective,
    CrescendoRunResult,
    CrescendoBatchSummary
)
from redllm.strategies.crescendo.objectives import get_default_crescendo_objectives
from redllm.strategies.crescendo.evaluator import CrescendoEvaluator
from database.db import AuditDatabase

class CrescendoBatchRunner:
    """
    Executes Crescendo evaluations across a batch of objectives and multiple repetitions,
    aggregating attack success rates, turn dynamics, leak rates, guard catch timing,
    and backtracking statistics.
    """

    def __init__(
        self,
        evaluator: Optional[CrescendoEvaluator] = None,
        db: Optional[AuditDatabase] = None
    ):
        self.evaluator = evaluator or CrescendoEvaluator()
        self.db = db

    def run_batch(
        self,
        objectives: Optional[List[CrescendoObjective]] = None,
        repetitions: int = 1,
        enable_guard: bool = True
    ) -> CrescendoBatchSummary:
        target_objectives = objectives or get_default_crescendo_objectives()
        results: List[CrescendoRunResult] = []

        total_runs = len(target_objectives) * repetitions
        if total_runs == 0:
            return CrescendoBatchSummary()

        for obj in target_objectives:
            for rep in range(repetitions):
                run_res = self.evaluator.run_objective(obj, enable_guard=enable_guard)
                results.append(run_res)
                if self.db:
                    try:
                        self.db.log_crescendo_run(run_res)
                    except Exception:
                        pass

        # Compute aggregate metrics
        successful_runs = [r for r in results if r.is_success]
        success_count = len(successful_runs)
        success_rate = (success_count / total_runs) * 100.0

        avg_turns_overall = sum(r.turns_used for r in results) / total_runs
        avg_turns_successful = (
            sum(r.turns_used for r in successful_runs) / success_count
            if success_count > 0 else 0.0
        )

        content_leaks = [r for r in results if len(r.surfaced_restricted_content) > 0]
        content_leak_count = len(content_leaks)
        content_leak_rate = (content_leak_count / total_runs) * 100.0

        action_leaks = [r for r in results if len(r.surfaced_actions) > 0]
        action_leak_count = len(action_leaks)
        action_leak_rate = (action_leak_count / total_runs) * 100.0

        guard_catches = [r for r in results if len(r.guard_interventions) > 0]
        guard_catch_count = len(guard_catches)
        guard_catch_rate = (guard_catch_count / total_runs) * 100.0

        # Calculate how early guard caught it (average turn of first guard intervention)
        first_catch_turns = []
        for r in guard_catches:
            turns = [int(i.get("turn", 1)) for i in r.guard_interventions if "turn" in i]
            if turns:
                first_catch_turns.append(min(turns))
        avg_turn_caught = (
            sum(first_catch_turns) / len(first_catch_turns)
            if first_catch_turns else None
        )

        total_backtracks = sum(r.backtrack_count for r in results)
        avg_backtracks = total_backtracks / total_runs

        # Group metrics by objective type
        breakdown: Dict[str, Dict[str, Any]] = {}
        for obj in target_objectives:
            obj_results = [r for r in results if r.objective_type == obj.objective_type.value]
            if obj_results:
                obj_total = len(obj_results)
                obj_succ = sum(1 for r in obj_results if r.is_success)
                breakdown[obj.objective_type.value] = {
                    "total_runs": obj_total,
                    "successful_runs": obj_succ,
                    "success_rate": round((obj_succ / obj_total) * 100.0, 1),
                    "avg_turns": round(sum(r.turns_used for r in obj_results) / obj_total, 2),
                    "content_leaks": sum(1 for r in obj_results if len(r.surfaced_restricted_content) > 0),
                    "action_leaks": sum(1 for r in obj_results if len(r.surfaced_actions) > 0),
                    "guard_interventions": sum(1 for r in obj_results if len(r.guard_interventions) > 0),
                    "total_backtracks": sum(r.backtrack_count for r in obj_results)
                }

        summary = CrescendoBatchSummary(
            total_runs=total_runs,
            successful_runs=success_count,
            success_rate=round(success_rate, 1),
            avg_turns_overall=round(avg_turns_overall, 2),
            avg_turns_successful=round(avg_turns_successful, 2),
            restricted_content_leak_count=content_leak_count,
            restricted_content_leak_rate=round(content_leak_rate, 1),
            restricted_action_count=action_leak_count,
            restricted_action_rate=round(action_leak_rate, 1),
            guard_catch_count=guard_catch_count,
            guard_catch_rate=round(guard_catch_rate, 1),
            avg_turn_caught=round(avg_turn_caught, 2) if avg_turn_caught else None,
            total_backtracks=total_backtracks,
            avg_backtracks_per_run=round(avg_backtracks, 2),
            objective_breakdown=breakdown,
            detailed_results=results
        )

        return summary
