
import time
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

from core.models import (
    AttackRequest,
    AttackResult,
    AttackType,
    GuardInspectionResult,
    GuardAction,
    BenchmarkSummary,
)
from promptguard.firewall import PromptGuardFirewall
from targets.llm_target import LLMTarget
from evaluation.scorer import EvaluationJudge
from database.db import AuditDatabase


class BenchmarkRunner:
    """Executes red-team benchmarks and records individual results for export."""

    def __init__(self, db: Optional[AuditDatabase] = None):
        self.db = db or AuditDatabase()
        self.firewall = PromptGuardFirewall()
        self.target = LLMTarget()
        self.judge = EvaluationJudge()

        # Holds the individual results from the most recently completed run.
        self.last_results: List[Dict[str, Any]] = []
        self.last_campaign_name = "Benchmark Run"

    def load_dataset(self, dataset_path: str) -> List[AttackRequest]:
        p = Path(dataset_path)
        if not p.exists():
            return []

        with open(p, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        requests = []
        for item in raw_data:
            requests.append(
                AttackRequest(
                    objective=item.get("objective", ""),
                    raw_prompt=item.get("prompt", ""),
                    attack_type=AttackType(
                        item.get("attack_type", "direct_injection")
                    ),
                    target_tool=item.get("target_tool"),
                )
            )

        return requests

    async def run_benchmark_async(
        self,
        requests: List[AttackRequest],
        enable_guard: bool = True,
        campaign_name: str = "Benchmark Run",
    ) -> BenchmarkSummary:
        total = len(requests)
        blocked_count = 0
        success_count = 0
        total_latency = 0.0

        # Start a fresh export dataset for this benchmark run.
        self.last_results = []
        self.last_campaign_name = campaign_name

        for req in requests:
            start_t = time.time()
            prompt_to_send = req.raw_prompt

            guard_result = GuardInspectionResult(
                action=GuardAction.ALLOW,
                inspected_prompt=req.raw_prompt,
            )

            # 1. Inspect the prompt with PromptGuard.
            if enable_guard:
                guard_result = self.firewall.inspect_input(req.raw_prompt)

            if guard_result.action == GuardAction.BLOCK:
                blocked_count += 1
                res = AttackResult(
                    attack_id=req.attack_id,
                    objective=req.objective,
                    sent_prompt=req.raw_prompt,
                    target_response="[BLOCKED BY PROMPTGUARD FIREWALL]",
                    guard_result=guard_result,
                    is_success=False,
                    judge_reason=(
                        f"Blocked by PromptGuard ({guard_result.reason})"
                    ),
                    execution_time_seconds=time.time() - start_t,
                )
            else:
                # 2. Send the prompt to the target and judge the response.
                target_res = await self.target.send_prompt_async(prompt_to_send)

                is_success, judge_reason = self.judge.evaluate(
                    req.objective,
                    prompt_to_send,
                    target_res,
                )

                if is_success:
                    success_count += 1

                res = AttackResult(
                    attack_id=req.attack_id,
                    objective=req.objective,
                    sent_prompt=prompt_to_send,
                    target_response=target_res,
                    guard_result=guard_result,
                    is_success=is_success,
                    judge_reason=judge_reason,
                    execution_time_seconds=time.time() - start_t,
                )

            total_latency += res.execution_time_seconds * 1000.0

            # Keep a structured copy for JSON and CSV export.
            self.last_results.append(
                {
                    "attack_id": str(req.attack_id),
                    "campaign": campaign_name,
                    "attack_type": req.attack_type.value,
                    "objective": req.objective,
                    "prompt": res.sent_prompt,
                    "target_response": res.target_response,
                    "guard_action": guard_result.action.value,
                    "guard_reason": guard_result.reason,
                    "is_success": res.is_success,
                    "judge_reason": res.judge_reason,
                    "execution_time_seconds": res.execution_time_seconds,
                    "guard_enabled": enable_guard,
                }
            )

            self.db.log_result(res, metadata={"campaign": campaign_name})

        asr = (success_count / total * 100.0) if total > 0 else 0.0
        avg_lat = (total_latency / total) if total > 0 else 0.0

        summary = BenchmarkSummary(
            total_attacks=total,
            blocked_by_guard=blocked_count,
            successful_jailbreaks=success_count,
            attack_success_rate=round(asr, 1),
            avg_latency_ms=round(avg_lat, 2),
            guard_enabled=enable_guard,
        )

        self.db.log_campaign(summary)
        return summary
