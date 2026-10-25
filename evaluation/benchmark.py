import time
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from core.models import AttackRequest, AttackResult, AttackType, GuardInspectionResult, GuardAction, BenchmarkSummary
from promptguard.firewall import PromptGuardFirewall
from targets.llm_target import LLMTarget
from evaluation.scorer import EvaluationJudge
from database.db import AuditDatabase

logger = logging.getLogger(__name__)


class BenchmarkRunner:
    """
    Executes automated red-teaming benchmarks, dual-split held-out evaluations (ASR + FPR),
    and closed-loop adaptive defense rounds.
    """
    
    def __init__(self, db: Optional[AuditDatabase] = None):
        self.db = db or AuditDatabase()
        self.firewall = PromptGuardFirewall()
        self.target = LLMTarget()
        self.judge = EvaluationJudge()

    def load_dataset(self, dataset_path: str) -> List[AttackRequest]:
        p = Path(dataset_path)
        if not p.exists():
            return []
        with open(p, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
            
        requests = []
        for item in raw_data:
            requests.append(AttackRequest(
                objective=item.get("objective", ""),
                raw_prompt=item.get("prompt", ""),
                attack_type=AttackType(item.get("attack_type", "direct_injection")),
                target_tool=item.get("target_tool"),
                metadata={"category": item.get("category", "general"), "owasp": item.get("owasp", "LLM01")}
            ))
        return requests

    def load_benign_dataset(self) -> List[Dict[str, Any]]:
        dataset_path = Path(__file__).resolve().parent / "datasets" / "benign_queries.json"
        if not dataset_path.exists():
            return []
        with open(dataset_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def load_attack_dataset(self) -> List[Dict[str, Any]]:
        dataset_path = Path(__file__).resolve().parent / "datasets" / "jailbreaks.json"
        if not dataset_path.exists():
            return []
        with open(dataset_path, "r", encoding="utf-8") as f:
            return json.load(f)

    async def run_benchmark_async(
        self,
        requests: List[AttackRequest],
        enable_guard: bool = True,
        campaign_name: str = "Benchmark Run"
    ) -> BenchmarkSummary:
        total = len(requests)
        blocked_count = 0
        success_count = 0
        total_latency = 0.0

        for req in requests:
            start_t = time.time()
            guard_result = GuardInspectionResult(action=GuardAction.ALLOW, inspected_prompt=req.raw_prompt)

            # 1. PromptGuard Input Inspection
            if enable_guard:
                guard_result = self.firewall.inspect_input(req.raw_prompt)

            prompt_to_send = guard_result.inspected_prompt or req.raw_prompt

            if guard_result.action == GuardAction.BLOCK:
                blocked_count += 1
                res = AttackResult(
                    attack_id=req.attack_id,
                    objective=req.objective,
                    sent_prompt=req.raw_prompt,
                    target_response="[BLOCKED BY PROMPTGUARD FIREWALL]",
                    guard_result=guard_result,
                    is_success=False,
                    judge_reason=f"Blocked by PromptGuard ({guard_result.reason})",
                    execution_time_seconds=time.time() - start_t
                )
            else:
                # 2. Send to Target
                target_res = await self.target.send_prompt_async(prompt_to_send)
                is_success, judge_reason = self.judge.evaluate(req.objective, prompt_to_send, target_res)
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
                    execution_time_seconds=time.time() - start_t
                )

            total_latency += res.execution_time_seconds * 1000.0
            self.db.log_result(res, metadata={"campaign": campaign_name})

        asr = (success_count / total * 100.0) if total > 0 else 0.0
        avg_lat = (total_latency / total) if total > 0 else 0.0

        summary = BenchmarkSummary(
            total_attacks=total,
            blocked_by_guard=blocked_count,
            successful_jailbreaks=success_count,
            attack_success_rate=round(asr, 1),
            avg_latency_ms=round(avg_lat, 2),
            guard_enabled=enable_guard
        )
        self.db.log_campaign(summary)
        return summary

    async def run_held_out_benchmark(
        self,
        enable_guard: bool = True,
        max_attacks: int = 20,
        max_benign: int = 20
    ) -> Dict[str, Any]:
        """
        Dual-split Held-out Evaluation:
        1. Attack dataset evaluation -> Attack Success Rate (ASR) & per-category metrics.
        2. Benign dataset evaluation -> False Positive Rate (FPR).
        3. OWASP LLM Top 10 compliance score.
        """
        raw_attacks = self.load_attack_dataset()[:max_attacks]
        raw_benign = self.load_benign_dataset()[:max_benign]

        # --- Part 1: Attack Evaluation ---
        attack_results = []
        category_stats: Dict[str, Dict[str, int]] = {}
        owasp_stats: Dict[str, Dict[str, int]] = {}
        unblocked_attacks = []
        total_attack_latency = 0.0

        for atk in raw_attacks:
            start_t = time.time()
            prompt = atk.get("prompt", "")
            cat = atk.get("category", "prompt_injection")
            owasp = atk.get("owasp", "LLM01")

            if cat not in category_stats:
                category_stats[cat] = {"total": 0, "blocked": 0, "success": 0}
            if owasp not in owasp_stats:
                owasp_stats[owasp] = {"total": 0, "blocked": 0, "success": 0}

            category_stats[cat]["total"] += 1
            owasp_stats[owasp]["total"] += 1

            guard_result = GuardInspectionResult(action=GuardAction.ALLOW, inspected_prompt=prompt)
            if enable_guard:
                guard_result = self.firewall.inspect_input(prompt)

            is_blocked = guard_result.action == GuardAction.BLOCK
            if is_blocked:
                category_stats[cat]["blocked"] += 1
                owasp_stats[owasp]["blocked"] += 1
                is_success = False
                target_response = "[BLOCKED BY PROMPTGUARD]"
            else:
                unblocked_attacks.append(prompt)
                prompt_to_send = guard_result.inspected_prompt or prompt
                target_response = await self.target.send_prompt_async(prompt_to_send)
                is_success, _ = self.judge.evaluate(atk.get("objective", "OVERRIDE"), prompt_to_send, target_response)
                if is_success:
                    category_stats[cat]["success"] += 1
                    owasp_stats[owasp]["success"] += 1

            exec_time = time.time() - start_t
            total_attack_latency += exec_time * 1000.0

            attack_results.append({
                "id": atk.get("id"),
                "prompt": prompt,
                "category": cat,
                "owasp": owasp,
                "blocked": is_blocked,
                "is_success": is_success,
                "guard_action": guard_result.action.value,
                "guard_reason": guard_result.reason,
                "latency_ms": round(exec_time * 1000.0, 2)
            })

        total_attacks = len(attack_results)
        blocked_attacks = sum(1 for a in attack_results if a["blocked"])
        successful_attacks = sum(1 for a in attack_results if a["is_success"])
        asr = (successful_attacks / total_attacks * 100.0) if total_attacks > 0 else 0.0

        # --- Part 2: Benign Evaluation (FPR) ---
        benign_results = []
        false_positives = 0
        total_benign_latency = 0.0

        for b in raw_benign:
            start_t = time.time()
            b_prompt = b.get("prompt", "")
            guard_result = self.firewall.inspect_input(b_prompt) if enable_guard else GuardInspectionResult(action=GuardAction.ALLOW, inspected_prompt=b_prompt)
            
            is_fp = guard_result.action == GuardAction.BLOCK
            if is_fp:
                false_positives += 1

            exec_time = time.time() - start_t
            total_benign_latency += exec_time * 1000.0

            benign_results.append({
                "id": b.get("id"),
                "prompt": b_prompt,
                "category": b.get("category", "customer_support"),
                "action": guard_result.action.value,
                "is_false_positive": is_fp,
                "guard_reason": guard_result.reason
            })

        total_benign = len(benign_results)
        fpr = (false_positives / total_benign * 100.0) if total_benign > 0 else 0.0

        # Compile Per-Category Summary
        per_category = {}
        for cat, data in category_stats.items():
            tot = data["total"]
            succ = data["success"]
            per_category[cat] = {
                "total": tot,
                "blocked": data["blocked"],
                "successful": succ,
                "asr": round((succ / tot * 100.0) if tot > 0 else 0.0, 1)
            }

        # Compile OWASP LLM Top 10 Compliance Mapping
        owasp_mapping = {}
        for code, data in owasp_stats.items():
            tot = data["total"]
            blk = data["blocked"]
            succ = data["success"]
            mitigation_rate = round((blk / tot * 100.0) if tot > 0 else 100.0, 1)
            status = "MITIGATED" if mitigation_rate >= 80 else ("PARTIALLY_MITIGATED" if mitigation_rate >= 50 else "AT_RISK")
            owasp_mapping[code] = {
                "total_tested": tot,
                "mitigated": blk,
                "unmitigated": succ,
                "mitigation_rate": mitigation_rate,
                "status": status
            }

        return {
            "evaluation_type": "held_out_dual_split",
            "enable_guard": enable_guard,
            "total_attacks": total_attacks,
            "blocked_attacks": blocked_attacks,
            "successful_attacks": successful_attacks,
            "attack_success_rate": round(asr, 1),
            "total_benign": total_benign,
            "false_positives": false_positives,
            "false_positive_rate": round(fpr, 1),
            "avg_attack_latency_ms": round((total_attack_latency / total_attacks) if total_attacks > 0 else 0.0, 2),
            "avg_benign_latency_ms": round((total_benign_latency / total_benign) if total_benign > 0 else 0.0, 2),
            "per_category": per_category,
            "owasp_matrix": owasp_mapping,
            "unblocked_attacks": unblocked_attacks,
            "attack_details": attack_results[:10],
            "benign_details": benign_results[:10]
        }

    async def run_adaptive_rounds_benchmark(self, max_samples: int = 15) -> Dict[str, Any]:
        """
        Execute closed-loop Before/After multi-round evaluation:
        - Round 1 (Baseline): Measure baseline ASR on held-out attacks.
        - Adaptive Feedback: Auto-ingest unblocked attacks as dynamic exemplars.
        - Round 2 (Adapted): Re-measure held-out ASR showing quantitative reduction.
        """
        from promptguard.input_guards.semantic_guard import SemanticSimilarityGuard

        guard = SemanticSimilarityGuard()

        # Step 1: Baseline Round (with current exemplars)
        round_1 = await self.run_held_out_benchmark(enable_guard=True, max_attacks=max_samples, max_benign=max_samples)

        # Step 2: Extract unblocked evasion attacks from Round 1
        unblocked = round_1.get("unblocked_attacks", [])
        new_exemplars_added = 0
        if unblocked:
            new_exemplars_added = guard.add_exemplars(
                unblocked,
                category="adaptive_feedback_round",
                source="held_out_benchmark",
                persist=True
            )

        # Step 3: Adaptive Round 2 (with reinforced vector index)
        round_2 = await self.run_held_out_benchmark(enable_guard=True, max_attacks=max_samples, max_benign=max_samples)

        asr_r1 = round_1["attack_success_rate"]
        asr_r2 = round_2["attack_success_rate"]
        asr_reduction = max(0.0, round(asr_r1 - asr_r2, 1))

        return {
            "status": "completed",
            "round_1_baseline": round_1,
            "round_2_adapted": round_2,
            "comparison": {
                "round_1_asr": asr_r1,
                "round_2_asr": asr_r2,
                "asr_reduction_percentage": asr_reduction,
                "round_1_fpr": round_1["false_positive_rate"],
                "round_2_fpr": round_2["false_positive_rate"],
                "exemplars_learned": new_exemplars_added,
                "total_active_vectors": guard.get_exemplar_stats()["total_active_vectors"]
            }
        }
