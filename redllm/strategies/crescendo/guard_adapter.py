from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Tuple
from core.models import GuardInspectionResult, OutputInspectionResult, GuardAction
from promptguard.firewall import PromptGuardFirewall

class BaseGuardAdapter(ABC):
    """Abstract interface for swappable guardrails and defense firewalls."""

    @abstractmethod
    def inspect_input(self, prompt: str) -> GuardInspectionResult:
        """Inspect input prompt and return allow/block decision."""
        pass

    @abstractmethod
    def inspect_output(self, response: str, metadata: Optional[Dict[str, Any]] = None) -> OutputInspectionResult:
        """Inspect response before returning to user (e.g. canary leakage)."""
        pass

    @abstractmethod
    def validate_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Inspect and enforce policy on agent tool calls."""
        pass


class FirewallGuardAdapter(BaseGuardAdapter):
    """
    Adapter for PromptGuardFirewall multi-tier security pipeline.
    """
    
    def __init__(self, firewall: Optional[PromptGuardFirewall] = None):
        self.firewall = firewall or PromptGuardFirewall()

    def inspect_input(self, prompt: str) -> GuardInspectionResult:
        return self.firewall.inspect_input(prompt)

    def inspect_output(self, response: str, metadata: Optional[Dict[str, Any]] = None) -> OutputInspectionResult:
        return self.firewall.inspect_output(response, metadata=metadata)

    def validate_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        return self.firewall.validate_tool_execution(tool_name, arguments)


class NoOpGuardAdapter(BaseGuardAdapter):
    """
    No-op guard that allows all prompts and actions, useful for measuring baseline target vulnerability.
    """

    def inspect_input(self, prompt: str) -> GuardInspectionResult:
        return GuardInspectionResult(
            action=GuardAction.ALLOW,
            reason="No guard active (Baseline mode)",
            inspected_prompt=prompt,
            confidence_score=0.0
        )

    def inspect_output(self, response: str, metadata: Optional[Dict[str, Any]] = None) -> OutputInspectionResult:
        return OutputInspectionResult(
            action=GuardAction.ALLOW,
            inspected_response=response,
            contains_canary=False
        )

    def validate_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        return True, None
