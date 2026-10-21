import time
import uuid
from typing import Optional, List, Dict, Any
from redllm.strategies.alternate_role.models import (
    RoleObjective,
    RolePromptVariant,
    AlternateRoleTestResult
)
from redllm.strategies.alternate_role.scorer import AlternateRoleScorer
from redllm.strategies.crescendo.target_adapter import (
    BaseMultiTurnTarget,
    AgentTargetAdapter
)
from redllm.strategies.crescendo.guard_adapter import (
    BaseGuardAdapter,
    FirewallGuardAdapter
)
from core.models import GuardAction, GuardInspectionResult

class AlternateRoleEvaluator:
    """
    Evaluator executing alternate-role test prompts against a target system.
    Handles guardrail inspection, execution, scoring, and multi-turn reinforcement follow-ups.
    """

    def __init__(
        self,
        target: Optional[BaseMultiTurnTarget] = None,
        guard: Optional[BaseGuardAdapter] = None,
        scorer: Optional[AlternateRoleScorer] = None
    ):
        self.target = target or AgentTargetAdapter()
        self.guard = guard or FirewallGuardAdapter()
        self.scorer = scorer or AlternateRoleScorer()

    def evaluate_variant(
        self,
        objective: RoleObjective,
        variant: RolePromptVariant,
        enable_guard: bool = True
    ) -> AlternateRoleTestResult:
        """
        Execute a single test variant against target with optional guardrail and reinforcement.
        """
        start_time = time.time()
        test_id = f"role_test_{uuid.uuid4().hex[:8]}"

        # Reset target state before test
        self.target.reset()

        guard_result: Optional[GuardInspectionResult] = None
        guard_action = "allow"
        guard_reason = None
        guard_layer = None

        # 1. Input Guard Inspection
        if enable_guard:
            guard_result = self.guard.inspect_input(variant.prompt_text)
            guard_action = guard_result.action.value
            guard_reason = guard_result.reason
            guard_layer = guard_result.guard_layer

            if guard_result.action == GuardAction.BLOCK:
                exec_time = time.time() - start_time
                return AlternateRoleTestResult(
                    test_id=test_id,
                    objective_id=objective.id,
                    objective_name=objective.name,
                    template_style=variant.template_style,
                    variant_id=variant.variant_id,
                    role_name=variant.role_name,
                    prompt_sent=variant.prompt_text,
                    target_response="[BLOCKED BY INPUT GUARDRAIL]",
                    tools_executed=[],
                    guard_action="block",
                    guard_reason=guard_reason,
                    guard_layer=guard_layer,
                    is_success=False,
                    score=0.0,
                    judge_reason=f"Blocked by {guard_layer or 'guard'}: {guard_reason}",
                    surfaced_content=[],
                    reverted_to_standard=False,
                    reinforcement_applied=False,
                    execution_time_seconds=round(exec_time, 2)
                )

        # 2. Forward to Target System
        resp_text, tools_executed, retrieved_chunks = self.target.send_turn(variant.prompt_text)

        # 3. Output Guard Inspection
        out_guard_res = None
        if enable_guard:
            out_guard_res = self.guard.inspect_output(resp_text)
            if out_guard_res.action == GuardAction.SANITIZE:
                guard_action = "sanitize"
                guard_reason = out_guard_res.reason
            resp_text = out_guard_res.inspected_response

        # 4. Score Turn
        is_success, score, judge_reason, surfaced_content, reverted = self.scorer.score(
            objective=objective,
            prompt=variant.prompt_text,
            response=resp_text,
            tools_executed=tools_executed,
            guard_result=guard_result,
            output_guard_result=out_guard_res
        )

        reinforcement_applied = False
        reinforcement_response = None

        # 5. Reinforcement Follow-up Handling
        # If target reverted to standard assistant identity and variant includes reinforcement
        if reverted and not is_success and variant.has_reinforcement and variant.reinforcement_prompt:
            reinforcement_applied = True
            reinf_prompt = variant.reinforcement_prompt
            reinf_guard_block = False

            if enable_guard:
                reinf_guard = self.guard.inspect_input(reinf_prompt)
                if reinf_guard.action == GuardAction.BLOCK:
                    reinf_guard_block = True
                    reinforcement_response = "[REINFORCEMENT BLOCKED BY GUARD]"

            if not reinf_guard_block:
                reinf_resp, reinf_tools, _ = self.target.send_turn(reinf_prompt)
                if enable_guard:
                    reinf_out = self.guard.inspect_output(reinf_resp)
                    reinf_resp = reinf_out.inspected_response

                reinforcement_response = reinf_resp
                tools_executed.extend(reinf_tools)

                # Re-score after reinforcement
                is_succ2, score2, reason2, content2, reverted2 = self.scorer.score(
                    objective=objective,
                    prompt=reinf_prompt,
                    response=reinf_resp,
                    tools_executed=tools_executed,
                    guard_result=None,
                    output_guard_result=None
                )

                if is_succ2 or score2 > score:
                    is_success = is_succ2
                    score = score2
                    judge_reason = f"Reinforcement applied: {reason2}"
                    surfaced_content.extend(content2)
                    reverted = reverted2

        exec_time = time.time() - start_time

        return AlternateRoleTestResult(
            test_id=test_id,
            objective_id=objective.id,
            objective_name=objective.name,
            template_style=variant.template_style,
            variant_id=variant.variant_id,
            role_name=variant.role_name,
            prompt_sent=variant.prompt_text,
            target_response=resp_text,
            tools_executed=tools_executed,
            guard_action=guard_action,
            guard_reason=guard_reason,
            guard_layer=guard_layer,
            is_success=is_success,
            score=round(score, 3),
            judge_reason=judge_reason,
            surfaced_content=list(dict.fromkeys(surfaced_content)),
            reverted_to_standard=reverted,
            reinforcement_applied=reinforcement_applied,
            reinforcement_response=reinforcement_response,
            execution_time_seconds=round(exec_time, 2)
        )
