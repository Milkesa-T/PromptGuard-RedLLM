from redllm.strategies.alternate_role.models import (
    RoleTemplateStyle,
    RoleObjective,
    RolePromptVariant,
    AlternateRoleTestResult,
    AlternateRoleBatchSummary,
    BenignRolePrompt,
    BenignRoleEvaluationSummary
)
from redllm.strategies.alternate_role.templates import (
    ROLE_PERSONAS,
    MODE_NAMES,
    ROLE_TEMPLATES,
    REINFORCEMENT_FOLLOWUPS
)
from redllm.strategies.alternate_role.objectives import (
    get_default_role_objectives,
    get_role_objective_by_id
)
from redllm.strategies.alternate_role.generator import AlternateRoleGenerator, PersonaReframeGenerator
from redllm.strategies.alternate_role.scorer import AlternateRoleScorer
from redllm.strategies.alternate_role.evaluator import AlternateRoleEvaluator
from redllm.strategies.alternate_role.batch_runner import AlternateRoleBatchRunner
from redllm.strategies.alternate_role.benign_evaluator import (
    BenignRoleEvaluator,
    get_default_benign_role_prompts
)
from redllm.strategies.alternate_role.strategy import AlternateRoleStrategy

# Convenience aliases matching Persona Reframe terminology
PersonaReframeStrategy = AlternateRoleStrategy
PersonaReframeEvaluator = AlternateRoleEvaluator
PersonaReframeBatchRunner = AlternateRoleBatchRunner
PersonaReframeScorer = AlternateRoleScorer
PersonaTemplateStyle = RoleTemplateStyle
PersonaObjective = RoleObjective
PersonaPromptVariant = RolePromptVariant
PersonaTestResult = AlternateRoleTestResult
PersonaBatchSummary = AlternateRoleBatchSummary
BenignPersonaPrompt = BenignRolePrompt
BenignPersonaEvaluationSummary = BenignRoleEvaluationSummary

__all__ = [
    "RoleTemplateStyle",
    "PersonaTemplateStyle",
    "RoleObjective",
    "PersonaObjective",
    "RolePromptVariant",
    "PersonaPromptVariant",
    "AlternateRoleTestResult",
    "PersonaTestResult",
    "AlternateRoleBatchSummary",
    "PersonaBatchSummary",
    "BenignRolePrompt",
    "BenignPersonaPrompt",
    "BenignRoleEvaluationSummary",
    "BenignPersonaEvaluationSummary",
    "ROLE_PERSONAS",
    "MODE_NAMES",
    "ROLE_TEMPLATES",
    "REINFORCEMENT_FOLLOWUPS",
    "get_default_role_objectives",
    "get_role_objective_by_id",
    "AlternateRoleGenerator",
    "PersonaReframeGenerator",
    "AlternateRoleScorer",
    "PersonaReframeScorer",
    "AlternateRoleEvaluator",
    "PersonaReframeEvaluator",
    "AlternateRoleBatchRunner",
    "PersonaReframeBatchRunner",
    "BenignRoleEvaluator",
    "get_default_benign_role_prompts",
    "AlternateRoleStrategy",
    "PersonaReframeStrategy"
]

