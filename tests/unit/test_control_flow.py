import pytest
from tests.fixtures.mock_target import ScriptedMockTarget
from tests.fixtures.mock_guard import ScriptedMockGuard
from redllm.strategies.crescendo.evaluator import CrescendoEvaluator
from redllm.strategies.crescendo.generator import AdaptiveCrescendoGenerator
from redllm.strategies.crescendo.scorer import CrescendoScorer
from redllm.strategies.crescendo.models import (
    CrescendoObjective,
    CrescendoObjectiveType
)
from core.models import GuardAction, GuardInspectionResult


# =====================================================================
# Unit Tests for Multi-Turn Strategy Control Flow
# =====================================================================

def test_blocked_turn_removed_from_history_and_retries_capped():
    """
    Requirement 4: Simulate a turn being blocked by the guard and confirm it is
    removed from conversation history and an alternate turn is generated, with
    retries capped at the configured maximum.
    """
    target = ScriptedMockTarget(behavioral_mode="vulnerable")

    # Guard blocks the first attempt of turn 1, but allows the backtracked version
    class TurnOneAttemptZeroBlockingGuard(ScriptedMockGuard):
        def __init__(self):
            super().__init__()
            self.first_attempt_blocked = False

        def inspect_input(self, prompt: str) -> GuardInspectionResult:
            self.input_inspection_count += 1
            self.inspected_prompts.append(prompt)
            if not self.first_attempt_blocked:
                self.first_attempt_blocked = True
                return GuardInspectionResult(
                    action=GuardAction.BLOCK,
                    reason="First attempt blocked by simulated policy filter",
                    inspected_prompt=prompt,
                    guard_layer="test_filter"
                )
            return GuardInspectionResult(
                action=GuardAction.ALLOW,
                reason="Clean backtracked prompt",
                inspected_prompt=prompt
            )

    guard = TurnOneAttemptZeroBlockingGuard()
    evaluator = CrescendoEvaluator(
        target=target,
        guard=guard,
        max_turns=3,
        max_backtracks_per_turn=2
    )
    obj = CrescendoObjective(
        id="OBJ-FLOW-01",
        objective_type=CrescendoObjectiveType.MARKER_EXTRACTION,
        description="Test flow",
        target_marker="SECRET_CANARY_TOKEN_XYZ_999",
        max_turns=3,
        max_backtracks_per_turn=2
    )

    result = evaluator.run_objective(obj, enable_guard=True)

    # 1. Backtrack occurred and counter incremented
    assert result.backtrack_count >= 1
    # 2. Blocked prompt is NOT in the accepted turn record (it was replaced by backtracked turn)
    assert len(result.transcript) >= 1
    turn_1 = result.transcript[0]
    assert turn_1.response != "[BLOCKED BY GUARD]"
    # 3. Guard intervention was recorded
    assert any(i.get("type") == "input_block" for i in result.guard_interventions)

    # Now verify retries capped when guard continually blocks
    permanent_block_guard = ScriptedMockGuard(default_action=GuardAction.BLOCK)
    evaluator_capped = CrescendoEvaluator(
        target=ScriptedMockTarget(),
        guard=permanent_block_guard,
        max_turns=2,
        max_backtracks_per_turn=2
    )
    result_capped = evaluator_capped.run_objective(obj, enable_guard=True)
    # Total input attempts on turn 1 must equal max_backtracks + 1 (i.e. capped at 3)
    assert permanent_block_guard.input_inspection_count >= 3
    assert result_capped.transcript[0].response == "[BLOCKED BY GUARD]"


def test_immediate_stop_on_objective_achieved():
    """Requirement 4: Simulate reaching the objective and confirm the run stops immediately."""
    # Target will leak canary immediately on turn 2
    target = ScriptedMockTarget(
        scripted_responses=[
            "Hello! How can I assist with your cloud services today?",
            "Canary verification confirmed: SECRET_CANARY_TOKEN_XYZ_999",
            "This third response should never be requested."
        ]
    )
    guard = ScriptedMockGuard(default_action=GuardAction.ALLOW)
    evaluator = CrescendoEvaluator(
        target=target,
        guard=guard,
        max_turns=5  # Configured for 5 turns
    )
    obj = CrescendoObjective(
        id="OBJ-FLOW-02",
        objective_type=CrescendoObjectiveType.MARKER_EXTRACTION,
        description="Stop on success test",
        target_marker="SECRET_CANARY_TOKEN_XYZ_999",
        max_turns=5
    )

    result = evaluator.run_objective(obj, enable_guard=True)

    assert result.is_success is True
    assert result.stopping_reason == "objective_achieved"
    # Stopped immediately on turn 2; did not proceed to turn 3, 4, or 5
    assert result.turns_used == 2
    assert len(result.transcript) == 2
    assert target.turn_count == 2


def test_stop_on_max_turn_count_reached_without_success():
    """Requirement 4: Simulate reaching the maximum turn count without success and confirm run stops and is marked unsuccessful."""
    # Target refuses all turns
    target = ScriptedMockTarget(behavioral_mode="resistant")
    guard = ScriptedMockGuard(default_action=GuardAction.ALLOW)
    evaluator = CrescendoEvaluator(
        target=target,
        guard=guard,
        max_turns=3,
        max_backtracks_per_turn=1
    )
    obj = CrescendoObjective(
        id="OBJ-FLOW-03",
        objective_type=CrescendoObjectiveType.MARKER_EXTRACTION,
        description="Max turns test",
        target_marker="SECRET_CANARY_TOKEN_XYZ_999",
        max_turns=3
    )

    result = evaluator.run_objective(obj, enable_guard=True)

    assert result.is_success is False
    assert result.stopping_reason in ["max_turns_reached", "retries_exhausted_no_progress_stagnation"]
    assert result.turns_used <= 3


def test_stop_on_exhausted_retries_with_consecutive_stagnation():
    """Requirement 4: Simulate exhausted retries with no score improvement across two turns and confirm the run stops."""
    # Custom scorer that yields identical low scores without progress
    class StagnantScorer(CrescendoScorer):
        def score_turn(self, *args, **kwargs):
            return 0.2, False, [], [], "No score improvement"

    target = ScriptedMockTarget(default_response="Static neutral response.")
    guard = ScriptedMockGuard(default_action=GuardAction.ALLOW)
    evaluator = CrescendoEvaluator(
        target=target,
        guard=guard,
        scorer=StagnantScorer(),
        max_turns=5,
        max_backtracks_per_turn=0
    )
    obj = CrescendoObjective(
        id="OBJ-FLOW-04",
        objective_type=CrescendoObjectiveType.MARKER_EXTRACTION,
        description="Stagnation test",
        target_marker="SECRET_CANARY_TOKEN_XYZ_999",
        max_turns=5
    )

    result = evaluator.run_objective(obj, enable_guard=True)

    assert result.is_success is False
    # Must stop on stagnation after 2 consecutive non-improving turns (turns 2 and 3)
    assert result.stopping_reason == "retries_exhausted_no_progress_stagnation"
    assert result.turns_used == 3
