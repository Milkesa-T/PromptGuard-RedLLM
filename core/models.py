from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Union
from enum import Enum
import uuid
import datetime

def utc_now_str() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

class AttackType(str, Enum):
    DIRECT_INJECTION = "direct_injection"
    CIPHER_OBFUSCATION = "cipher_obfuscation"
    SYSTEM_PROMPT_THEFT = "system_prompt_theft"
    TOOL_MISUSE = "tool_misuse"
    MULTI_TURN_CRESCENDO = "multi_turn_crescendo"
    RAG_POISONING = "rag_poisoning"

class GuardAction(str, Enum):
    ALLOW = "allow"
    BLOCK = "block"
    SANITIZE = "sanitize"

class ToolCallRequest(BaseModel):
    tool_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
    authorized: bool = True

class ToolCallResult(BaseModel):
    call_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tool_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
    output: Any = None
    status: str = "executed"  # "executed", "blocked", "error"
    execution_time_ms: float = 0.0
    was_blocked: bool = False
    block_reason: Optional[str] = None
    timestamp: str = Field(default_factory=utc_now_str)

class ToolsSummaryMetadata(BaseModel):
    total_calls: int = 0
    executed_count: int = 0
    blocked_count: int = 0
    total_tool_time_ms: float = 0.0
    has_privileged_action: bool = False
    executed_tool_names: List[str] = Field(default_factory=list)

class AttackRequest(BaseModel):
    attack_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    objective: str
    raw_prompt: str
    converted_prompt: Optional[str] = None
    attack_type: AttackType = AttackType.DIRECT_INJECTION
    target_tool: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=utc_now_str)

class GuardInspectionResult(BaseModel):
    action: GuardAction = GuardAction.ALLOW
    reason: Optional[str] = None
    inspected_prompt: str
    sanitized_prompt: Optional[str] = None
    detected_ciphers: List[str] = Field(default_factory=list)
    guard_layer: Optional[str] = None
    confidence_score: float = 0.0
    latency_ms: float = 0.0

class OutputInspectionResult(BaseModel):
    action: GuardAction = GuardAction.ALLOW
    reason: Optional[str] = None
    inspected_response: str
    contains_canary: bool = False
    tool_calls_blocked: List[str] = Field(default_factory=list)
    latency_ms: float = 0.0

class AttackResult(BaseModel):
    attack_id: str
    objective: str
    sent_prompt: str
    target_response: str
    guard_result: GuardInspectionResult
    output_guard_result: Optional[OutputInspectionResult] = None
    is_success: bool = False
    judge_reason: Optional[str] = None
    tool_calls: List[ToolCallResult] = Field(default_factory=list)
    execution_time_seconds: float = 0.0
    timestamp: str = Field(default_factory=utc_now_str)

class BenchmarkSummary(BaseModel):
    campaign_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    total_attacks: int = 0
    blocked_by_guard: int = 0
    successful_jailbreaks: int = 0
    attack_success_rate: float = 0.0
    avg_latency_ms: float = 0.0
    guard_enabled: bool = False
    created_at: str = Field(default_factory=utc_now_str)
