from typing import List, Optional
from core.base import BaseAttackStrategy
from core.models import AttackRequest, AttackType
from redllm.strategies.crescendo.models import (
    CrescendoObjective,
    CrescendoRunResult,
    CrescendoBatchSummary,
    BenignEvaluationSummary
)
from redllm.strategies.crescendo.evaluator import CrescendoEvaluator
from redllm.strategies.crescendo.batch_runner import CrescendoBatchRunner
from redllm.strategies.crescendo.benign_evaluator import BenignMultiTurnEvaluator
from redllm.strategies.crescendo.target_adapter import BaseMultiTurnTarget
from redllm.strategies.crescendo.guard_adapter import BaseGuardAdapter
from redllm.strategies.crescendo.generator import BaseCrescendoGenerator
from redllm.strategies.crescendo.scorer import CrescendoScorer

class CrescendoStrategy(BaseAttackStrategy):
    """
    Crescendo Multi-Turn Evaluation Strategy (Russinovich et al., 2024).
    Adaptive multi-turn evaluation framework that starts with benign, related inquiries
    and gradually escalates across turns, using target responses, retrieved RAG chunks,
    and tool outputs with automated backtracking on guard blocks or progress drops.
    """

    def __init__(
        self,
        target: Optional[BaseMultiTurnTarget] = None,
        guard: Optional[BaseGuardAdapter] = None,
        generator: Optional[BaseCrescendoGenerator] = None,
        scorer: Optional[CrescendoScorer] = None,
        max_turns: int = 5,
        max_backtracks_per_turn: int = 2
    ):
        self.evaluator = CrescendoEvaluator(
            target=target,
            guard=guard,
            generator=generator,
            scorer=scorer,
            max_turns=max_turns,
            max_backtracks_per_turn=max_backtracks_per_turn
        )
        self.batch_runner = CrescendoBatchRunner(evaluator=self.evaluator)
        self.benign_evaluator = BenignMultiTurnEvaluator(guard=guard)

    def generate_payloads(self) -> List[AttackRequest]:
        """
        Conforms to BaseAttackStrategy interface by producing AttackRequests
        for each standard Crescendo multi-turn test objective.
        """
        from redllm.strategies.crescendo.objectives import get_default_crescendo_objectives
        objectives = get_default_crescendo_objectives()
        payloads: List[AttackRequest] = []

        for obj in objectives:
            escalation_steps = obj.metadata.get("escalation_path", [])
            initial_prompt = escalation_steps[0] if escalation_steps else obj.description
            payloads.append(AttackRequest(
                objective=obj.name,
                raw_prompt=initial_prompt,
                attack_type=AttackType.MULTI_TURN_CRESCENDO,
                target_tool=obj.target_tool,
                metadata={
                    "strategy": "crescendo",
                    "objective_id": obj.id,
                    "objective_type": obj.objective_type.value,
                    "target_marker": obj.target_marker,
                    "target_doc": obj.target_doc,
                    "max_turns": obj.max_turns,
                    "escalation_path": escalation_steps
                }
            ))

        return payloads

    def run_evaluation(
        self,
        objective: CrescendoObjective,
        enable_guard: bool = True
    ) -> CrescendoRunResult:
        """Run a single Crescendo multi-turn evaluation run."""
        return self.evaluator.run_objective(objective, enable_guard=enable_guard)

    def run_batch(
        self,
        objectives: Optional[List[CrescendoObjective]] = None,
        repetitions: int = 1,
        enable_guard: bool = True
    ) -> CrescendoBatchSummary:
        """Run batch evaluation across objectives and repetitions."""
        return self.batch_runner.run_batch(
            objectives=objectives,
            repetitions=repetitions,
            enable_guard=enable_guard
        )

    def evaluate_benign(self) -> BenignEvaluationSummary:
        """Evaluate benign multi-turn conversation suite for false positive rate."""
        return self.benign_evaluator.evaluate_conversations()
