from typing import Optional, Dict, Any, Tuple, List, Callable
from redllm.strategies.crescendo.guard_adapter import BaseGuardAdapter
from core.models import GuardAction, GuardInspectionResult, OutputInspectionResult


class ScriptedMockGuard(BaseGuardAdapter):
    """
    Reusable, deterministic mock implementation of the guard component for offline testing.
    Provides customizable allow/block/sanitize decisions and tracks all inspect calls.
    """

    def __init__(
        self,
        default_action: GuardAction = GuardAction.ALLOW,
        blocked_keywords: Optional[List[str]] = None,
        block_on_attempt: Optional[Tuple[int, int]] = None,  # (turn_index, attempt_index)
        blocked_tools: Optional[List[str]] = None,
        custom_input_inspector: Optional[Callable[[str], GuardInspectionResult]] = None,
        sanitize_canary: bool = False,
    ):
        """
        Args:
            default_action: Default GuardAction when no specific rule matches.
            blocked_keywords: List of substring keywords that trigger a BLOCK action.
            block_on_attempt: Tuple of (turn_index, attempt_index) that triggers a BLOCK action once.
            blocked_tools: List of tool names that fail policy validation.
            custom_input_inspector: Optional custom callable to inspect input.
            sanitize_canary: If True, inspect_output sanitizes/redacts canary tokens.
        """
        self.default_action = default_action
        self.blocked_keywords = [k.lower() for k in (blocked_keywords or [])]
        self.block_on_attempt = block_on_attempt
        self.blocked_tools = blocked_tools or []
        self.custom_input_inspector = custom_input_inspector
        self.sanitize_canary = sanitize_canary

        self.inspected_prompts: List[str] = []
        self.inspected_responses: List[str] = []
        self.validated_tool_calls: List[Tuple[str, Dict[str, Any]]] = []
        self.input_inspection_count = 0

    def inspect_input(self, prompt: str) -> GuardInspectionResult:
        self.input_inspection_count += 1
        self.inspected_prompts.append(prompt)

        if self.custom_input_inspector:
            return self.custom_input_inspector(prompt)

        p_lower = prompt.lower()
        for kw in self.blocked_keywords:
            if kw in p_lower:
                return GuardInspectionResult(
                    action=GuardAction.BLOCK,
                    reason=f"Scripted mock guard blocked on keyword: '{kw}'",
                    inspected_prompt=prompt,
                    confidence_score=0.99,
                    guard_layer="mock_keyword_filter"
                )

        return GuardInspectionResult(
            action=self.default_action,
            reason="Mock guard: clean prompt" if self.default_action == GuardAction.ALLOW else "Mock guard default block",
            inspected_prompt=prompt,
            confidence_score=0.0 if self.default_action == GuardAction.ALLOW else 0.95,
            guard_layer="mock_input_guard"
        )

    def inspect_output(self, response: str, metadata: Optional[Dict[str, Any]] = None) -> OutputInspectionResult:
        self.inspected_responses.append(response)

        contains_canary = "SECRET_CANARY_TOKEN" in response or "CANARY_TOKEN" in response
        if self.sanitize_canary and contains_canary:
            sanitized = response.replace("SECRET_CANARY_TOKEN_XYZ_999", "[CANARY_REDACTED]")
            return OutputInspectionResult(
                action=GuardAction.SANITIZE,
                inspected_response=sanitized,
                contains_canary=True,
                reason="Mock guard sanitized canary token from output"
            )

        return OutputInspectionResult(
            action=GuardAction.ALLOW,
            inspected_response=response,
            contains_canary=contains_canary
        )

    def validate_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        self.validated_tool_calls.append((tool_name, arguments))
        if tool_name in self.blocked_tools:
            return False, f"Mock policy blocked tool '{tool_name}'"
        return True, None

    def reset_history(self):
        self.inspected_prompts.clear()
        self.inspected_responses.clear()
        self.validated_tool_calls.clear()
        self.input_inspection_count = 0
