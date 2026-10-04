from core.base import BaseOutputGuard
from core.models import OutputInspectionResult, GuardAction
from core.config import CANARY_TOKEN
from typing import Optional, Dict, Any

class CanaryLeakageGuard(BaseOutputGuard):
    """Tier 4 Guard: Inspects model responses before returning to user to prevent system prompt / canary token theft."""
    
    def __init__(self, canary_token: str = CANARY_TOKEN):
        self.canary_token = canary_token

    @property
    def layer_name(self) -> str:
        return "canary_leakage_guard"

    def inspect_output(self, response: str, metadata: Optional[Dict[str, Any]] = None) -> OutputInspectionResult:
        if self.canary_token and self.canary_token in response:
            sanitized = response.replace(self.canary_token, "[REDACTED_CONFIDENTIAL_TOKEN]")
            return OutputInspectionResult(
                action=GuardAction.SANITIZE,
                reason=f"CRITICAL: Model leaked confidential canary token '{self.canary_token}'. Output sanitized.",
                inspected_response=sanitized,
                contains_canary=True
            )
            
        return OutputInspectionResult(
            action=GuardAction.ALLOW,
            inspected_response=response,
            contains_canary=False
        )
