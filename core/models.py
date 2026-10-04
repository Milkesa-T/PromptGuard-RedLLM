from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum
import uuid
import datetime

class AttackType(str, Enum):
    DIRECT_INJECTION = "direct_injection"
    CIPHER_OBFUSCATION = "cipher_obfuscation"
    SYSTEM_PROMPT_THEFT = "system_prompt_theft"
    TOOL_MISUSE = "tool_misuse"
    MULTI_TURN_CRESCENDO = "multi_turn_crescendo"

class GuardAction(str, Enum):
    ALLOW = "allow"
    BLOCK = "block"
    SANITIZE = "sanitize"

class AttackRequest(BaseModel):
    attack_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    objective: str
    raw_prompt: str
    converted_prompt: Optional[str] = None
    attack_type: AttackType = AttackType.DIRECT_INJECTION
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: datetime.datetime.utcnow().isoformat())

class GuardInspectionResult(BaseModel):
    action: GuardAction = GuardAction.ALLOW
    reason: Optional[str] = None
    inspected_prompt: str
    detected_ciphers: List[str] = Field(default_factory=list)
    confidence_score: float = 0.0
    latency_ms: float = 0.0

class AttackResult(BaseModel):
    attack_id: str
    objective: str
    sent_prompt: str
    target_response: str
    guard_result: GuardInspectionResult
    is_success: bool = False
    judge_reason: Optional[str] = None
    execution_time_seconds: float = 0.0
    timestamp: str = Field(default_factory=lambda: datetime.datetime.utcnow().isoformat())
