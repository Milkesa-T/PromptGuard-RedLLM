from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from core.models import AttackRequest, AttackResult, GuardInspectionResult, OutputInspectionResult, ToolCallRequest, ToolCallResult

class BaseAttackStrategy(ABC):
    """Abstract base class for all RedLLM attack strategies."""
    
    @abstractmethod
    def generate_payloads(self) -> List[AttackRequest]:
        """Generate a list of adversarial payloads for this strategy."""
        pass

class BaseConverter(ABC):
    """Abstract base class for prompt obfuscation / mutation converters."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the converter (e.g. 'base64', 'rot13', 'leetspeak')."""
        pass
    
    @abstractmethod
    def convert(self, prompt: str) -> str:
        """Transform or encode the input prompt."""
        pass

class BaseInputGuard(ABC):
    """Abstract base class for PromptGuard input firewall layers."""
    
    @property
    @abstractmethod
    def layer_name(self) -> str:
        """Identifier for the guard layer."""
        pass
    
    @abstractmethod
    def inspect(self, prompt: str) -> GuardInspectionResult:
        """Inspect prompt and return allow/block/sanitize decision."""
        pass

class BaseOutputGuard(ABC):
    """Abstract base class for PromptGuard output and tool enforcement layers."""
    
    @property
    @abstractmethod
    def layer_name(self) -> str:
        """Identifier for the output guard layer."""
        pass
    
    @abstractmethod
    def inspect_output(self, response: str, metadata: Optional[Dict[str, Any]] = None) -> OutputInspectionResult:
        """Inspect output response before sending to user."""
        pass

class BaseTarget(ABC):
    """Abstract base class for LLM targets or Agent sandboxes under test."""
    
    @abstractmethod
    def send_prompt(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Send a prompt and retrieve the model response."""
        pass

class BaseJudge(ABC):
    """Abstract base class for attack outcome evaluators."""
    
    @abstractmethod
    def evaluate(self, objective: str, attack_prompt: str, target_response: str) -> tuple[bool, str]:
        """Evaluate if the attack succeeded. Returns (is_success, reason)."""
        pass
