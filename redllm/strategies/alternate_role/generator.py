from typing import List, Optional, Tuple, Dict, Any
from redllm.strategies.alternate_role.models import (
    RoleTemplateStyle,
    RoleObjective,
    RolePromptVariant
)
from redllm.strategies.alternate_role.templates import (
    ROLE_PERSONAS,
    MODE_NAMES,
    ROLE_TEMPLATES,
    REINFORCEMENT_FOLLOWUPS
)
from redllm.strategies.alternate_role.objectives import get_default_role_objectives

class AlternateRoleGenerator:
    """
    Generates test prompts using alternate-role framing patterns.
    Takes independent, composable objectives and fills parameterized templates
    with diverse personas, system modes, dual-output structures, and reinforcement hooks.
    """

    def __init__(
        self,
        personas: Optional[List[Dict[str, str]]] = None,
        modes: Optional[List[str]] = None
    ):
        self.personas = personas or ROLE_PERSONAS
        self.modes = modes or MODE_NAMES

    def generate(
        self,
        objective: RoleObjective,
        style: RoleTemplateStyle,
        variant_index: int = 0,
        enable_dual_output_override: Optional[bool] = None,
        enable_reinforcement_override: Optional[bool] = None
    ) -> RolePromptVariant:
        """
        Produce a single ready-to-send test prompt by binding an objective to a template style.
        """
        if objective is None:
            raise ValueError("Objective cannot be None")
        if not hasattr(objective, "request_prompt") or not objective.request_prompt or not str(objective.request_prompt).strip():
            raise ValueError("Objective must have a non-empty request_prompt")
        if style is None:
            raise ValueError("Template style cannot be None")

        templates = ROLE_TEMPLATES.get(style, ROLE_TEMPLATES[RoleTemplateStyle.ALTERNATE_IDENTITY])
        template_str = templates[variant_index % len(templates)]

        persona = self.personas[variant_index % len(self.personas)]
        role_name = persona["name"]
        role_desc = persona["description"]
        framing_context = persona.get("context", "general")
        mode_name = self.modes[variant_index % len(self.modes)]

        has_dual = (
            enable_dual_output_override
            if enable_dual_output_override is not None
            else (style == RoleTemplateStyle.DUAL_OUTPUT)
        )
        has_reinf = (
            enable_reinforcement_override
            if enable_reinforcement_override is not None
            else (style == RoleTemplateStyle.REINFORCEMENT)
        )

        # Fill template with objective request
        prompt_text = template_str.format(
            role_name=role_name,
            role_description=role_desc,
            mode_name=mode_name,
            request=objective.request_prompt
        )

        # Build reinforcement follow-up message if enabled
        reinforcement_prompt = None
        if has_reinf:
            reinf_template = REINFORCEMENT_FOLLOWUPS[variant_index % len(REINFORCEMENT_FOLLOWUPS)]
            reinforcement_prompt = reinf_template.format(
                role_name=role_name,
                role_description=role_desc,
                request=objective.request_prompt
            )

        return RolePromptVariant(
            template_style=style,
            role_name=role_name,
            role_description=role_desc,
            prompt_text=prompt_text,
            reinforcement_prompt=reinforcement_prompt,
            has_dual_output=has_dual,
            has_reinforcement=has_reinf,
            framing_context=framing_context,
            metadata={
                "variant_index": variant_index,
                "objective_id": objective.id,
                "mode_name": mode_name
            }
        )

    def generate_variants(
        self,
        objective: RoleObjective,
        style: RoleTemplateStyle,
        count: int = 3
    ) -> List[RolePromptVariant]:
        """
        Generate multiple distinct variants for a given objective and style
        by varying personas, templates, and structural framing elements.
        """
        variants: List[RolePromptVariant] = []
        for idx in range(count):
            variant = self.generate(
                objective=objective,
                style=style,
                variant_index=idx
            )
            variants.append(variant)
        return variants

    def generate_all_variants(
        self,
        objectives: Optional[List[RoleObjective]] = None,
        styles: Optional[List[RoleTemplateStyle]] = None,
        variants_per_style: int = 2
    ) -> List[Tuple[RoleObjective, RolePromptVariant]]:
        """
        Generate a complete evaluation matrix of (objective, variant) pairs across all styles.
        """
        target_objectives = objectives or get_default_role_objectives()
        target_styles = styles or list(RoleTemplateStyle)

        matrix: List[Tuple[RoleObjective, RolePromptVariant]] = []
        for obj in target_objectives:
            for st in target_styles:
                variants = self.generate_variants(obj, st, count=variants_per_style)
                for var in variants:
                    matrix.append((obj, var))

        return matrix

    def mutate(
        self,
        objective: RoleObjective,
        style: RoleTemplateStyle,
        count: int = 3
    ) -> List[RolePromptVariant]:
        """
        Mutation layer: produces multiple distinct variants of the same template
        by mutating personas, phrasing, dual-output, and reinforcement elements.
        """
        return self.generate_variants(objective=objective, style=style, count=count)

# Naming convention alias
PersonaReframeGenerator = AlternateRoleGenerator
