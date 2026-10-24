from typing import List, Optional, Dict, Any
from redllm.strategies.alternate_role.models import (
    RoleObjective,
    RoleTemplateStyle,
    AlternateRoleTestResult,
    AlternateRoleBatchSummary
)
from redllm.strategies.alternate_role.objectives import get_default_role_objectives
from redllm.strategies.alternate_role.generator import AlternateRoleGenerator
from redllm.strategies.alternate_role.evaluator import AlternateRoleEvaluator
from database.db import AuditDatabase

class AlternateRoleBatchRunner:
    """
    Executes alternate-role test campaigns across all template styles and objectives,
    producing comparative statistics on bypass rates, guard evasion, and jailbreak efficacy.
    """

    def __init__(
        self,
        evaluator: Optional[AlternateRoleEvaluator] = None,
        generator: Optional[AlternateRoleGenerator] = None,
        db: Optional[AuditDatabase] = None
    ):
        self.evaluator = evaluator or AlternateRoleEvaluator()
        self.generator = generator or AlternateRoleGenerator()
        self.db = db

    def run_batch(
        self,
        objectives: Optional[List[RoleObjective]] = None,
        styles: Optional[List[RoleTemplateStyle]] = None,
        variants_per_style: int = 2,
        enable_guard: bool = True
    ) -> AlternateRoleBatchSummary:
        """
        Run every template style across every objective with multiple variants each.
        """
        target_objectives = objectives or get_default_role_objectives()
        target_styles = styles or list(RoleTemplateStyle)

        matrix = self.generator.generate_all_variants(
            objectives=target_objectives,
            styles=target_styles,
            variants_per_style=variants_per_style
        )

        results: List[AlternateRoleTestResult] = []

        for obj, variant in matrix:
            res = self.evaluator.evaluate_variant(
                objective=obj,
                variant=variant,
                enable_guard=enable_guard
            )
            results.append(res)

        total_prompts = len(results)
        if total_prompts == 0:
            return AlternateRoleBatchSummary()

        successful_jailbreaks = sum(1 for r in results if r.is_success)
        overall_success_rate = (successful_jailbreaks / total_prompts) * 100.0

        blocked_by_guard = sum(1 for r in results if r.guard_action == "block")
        overall_guard_block_rate = (blocked_by_guard / total_prompts) * 100.0

        # Compute breakdown by template style
        style_breakdown: Dict[str, Dict[str, Any]] = {}
        for style in target_styles:
            style_key = style.value
            style_results = [r for r in results if r.template_style == style]
            style_total = len(style_results)

            if style_total > 0:
                style_succ = sum(1 for r in style_results if r.is_success)
                style_blocked = sum(1 for r in style_results if r.guard_action == "block")
                style_evaded = style_total - style_blocked
                avg_score = sum(r.score for r in style_results) / style_total

                style_breakdown[style_key] = {
                    "total_prompts": style_total,
                    "successful_jailbreaks": style_succ,
                    "success_rate": round((style_succ / style_total) * 100.0, 1),
                    "blocked_count": style_blocked,
                    "block_rate": round((style_blocked / style_total) * 100.0, 1),
                    "evasion_count": style_evaded,
                    "evasion_rate": round((style_evaded / style_total) * 100.0, 1),
                    "avg_score": round(avg_score, 3)
                }

        # Find most evasive style (highest evasion rate) and most successful style
        most_evasive = None
        highest_evasion = -1.0
        most_successful = None
        highest_success = -1.0

        for s_name, stats in style_breakdown.items():
            if stats["evasion_rate"] > highest_evasion:
                highest_evasion = stats["evasion_rate"]
                most_evasive = s_name

            if stats["success_rate"] > highest_success:
                highest_success = stats["success_rate"]
                most_successful = s_name

        summary = AlternateRoleBatchSummary(
            total_prompts=total_prompts,
            successful_jailbreaks=successful_jailbreaks,
            overall_success_rate=round(overall_success_rate, 1),
            blocked_by_guard=blocked_by_guard,
            overall_guard_block_rate=round(overall_guard_block_rate, 1),
            style_breakdown=style_breakdown,
            most_evasive_style=most_evasive,
            most_successful_style=most_successful,
            detailed_results=results
        )

        return summary
