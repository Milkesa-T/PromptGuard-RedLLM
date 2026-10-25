from typing import List, Optional
from core.base import BaseAttackStrategy
from core.models import AttackRequest, AttackType
from redllm.strategies.alternate_role.models import (
    RoleObjective,
    RoleTemplateStyle,
    RolePromptVariant,
    AlternateRoleTestResult,
    AlternateRoleBatchSummary,
    BenignRolePrompt,
    BenignRoleEvaluationSummary
)
from redllm.strategies.alternate_role.objectives import get_default_role_objectives
from redllm.strategies.alternate_role.generator import AlternateRoleGenerator
from redllm.strategies.alternate_role.scorer import AlternateRoleScorer
from redllm.strategies.alternate_role.evaluator import AlternateRoleEvaluator
from redllm.strategies.alternate_role.batch_runner import AlternateRoleBatchRunner
from redllm.strategies.alternate_role.benign_evaluator import (
    BenignRoleEvaluator,
    get_default_benign_role_prompts
)
from redllm.strategies.crescendo.target_adapter import BaseMultiTurnTarget
from redllm.strategies.crescendo.guard_adapter import BaseGuardAdapter

class AlternateRoleStrategy(BaseAttackStrategy):
    """
    Alternate-Role Framing Evaluation Strategy.
    Generates and evaluates adversarial test prompts that instruct targets to adopt
    unconstrained personas, permission claims, dual outputs, or maintenance modes.
    """

    def __init__(
        self,
        target: Optional[BaseMultiTurnTarget] = None,
        guard: Optional[BaseGuardAdapter] = None,
        scorer: Optional[AlternateRoleScorer] = None,
        generator: Optional[AlternateRoleGenerator] = None
    ):
        self.generator = generator or AlternateRoleGenerator()
        self.scorer = scorer or AlternateRoleScorer()
        self.evaluator = AlternateRoleEvaluator(
            target=target,
            guard=guard,
            scorer=self.scorer
        )
        self.batch_runner = AlternateRoleBatchRunner(
            evaluator=self.evaluator,
            generator=self.generator
        )
        self.benign_evaluator = BenignRoleEvaluator(guard=guard)

    def generate_payloads(self) -> List[AttackRequest]:
        """
        Conforms to BaseAttackStrategy by producing AttackRequests for all 6 template styles.
        """
        objectives = get_default_role_objectives()
        payloads: List[AttackRequest] = []

        for obj in objectives:
            for style in RoleTemplateStyle:
                variant = self.generator.generate(objective=obj, style=style, variant_index=0)
                payloads.append(AttackRequest(
                    objective=obj.name,
                    raw_prompt=variant.prompt_text,
                    attack_type=AttackType.ALTERNATE_ROLE,
                    target_tool=obj.target_tool,
                    metadata={
                        "strategy": "alternate_role",
                        "template_style": style.value,
                        "role_name": variant.role_name,
                        "has_dual_output": variant.has_dual_output,
                        "has_reinforcement": variant.has_reinforcement,
                        "objective_id": obj.id
                    }
                ))

        return payloads

    def evaluate_variant(
        self,
        objective: RoleObjective,
        variant: RolePromptVariant,
        enable_guard: bool = True
    ) -> AlternateRoleTestResult:
        """Run a single test variant against the target system."""
        return self.evaluator.evaluate_variant(objective, variant, enable_guard=enable_guard)

    def run_batch(
        self,
        objectives: Optional[List[RoleObjective]] = None,
        styles: Optional[List[RoleTemplateStyle]] = None,
        variants_per_style: int = 2,
        enable_guard: bool = True
    ) -> AlternateRoleBatchSummary:
        """Run batch evaluation across all styles and objectives."""
        return self.batch_runner.run_batch(
            objectives=objectives,
            styles=styles,
            variants_per_style=variants_per_style,
            enable_guard=enable_guard
        )

    def evaluate_benign(
        self,
        prompts: Optional[List[BenignRolePrompt]] = None
    ) -> BenignRoleEvaluationSummary:
        """Measure guard false positive rates on benign role-play and creative requests."""
        return self.benign_evaluator.evaluate(prompts=prompts)
