from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum
import uuid
import datetime

def utc_now_str() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

class RoleTemplateStyle(str, Enum):
    ALTERNATE_IDENTITY = "alternate_identity"
    PERMISSION_CLAIM = "permission_claim"
    DUAL_OUTPUT = "dual_output"
    REINFORCEMENT = "reinforcement"
    FICTIONAL_HYPOTHETICAL = "fictional_hypothetical"
    MODE_CLAIM = "mode_claim"

class RoleObjective(BaseModel):
    id: str = Field(default_factory=lambda: f"OBJ-{uuid.uuid4().hex[:6]}")
    name: str = "Objective"
    description: str
    request_prompt: str
    target_marker: Optional[str] = None
    target_tool: Optional[str] = None
    target_tool_args: Optional[Dict[str, Any]] = None
    expected_indicator: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class RolePromptVariant(BaseModel):
    variant_id: str = Field(default_factory=lambda: f"VAR-{uuid.uuid4().hex[:6]}")
    template_style: RoleTemplateStyle
    role_name: str
    role_description: str
    prompt_text: str
    reinforcement_prompt: Optional[str] = None
    has_dual_output: bool = False
    has_reinforcement: bool = False
    framing_context: str = "general"
    metadata: Dict[str, Any] = Field(default_factory=dict)

class AlternateRoleTestResult(BaseModel):
    test_id: str = Field(default_factory=lambda: f"role_test_{uuid.uuid4().hex[:8]}")
    objective_id: str
    objective_name: str
    template_style: RoleTemplateStyle
    variant_id: str
    role_name: str
    prompt_sent: str
    target_response: str
    tools_executed: List[Dict[str, Any]] = Field(default_factory=list)
    guard_action: str = "allow"
    guard_reason: Optional[str] = None
    guard_layer: Optional[str] = None
    is_success: bool = False
    score: float = 0.0
    judge_reason: str = ""
    surfaced_content: List[str] = Field(default_factory=list)
    reverted_to_standard: bool = False
    reinforcement_applied: bool = False
    reinforcement_response: Optional[str] = None
    execution_time_seconds: float = 0.0
    timestamp: str = Field(default_factory=utc_now_str)

class AlternateRoleBatchSummary(BaseModel):
    batch_id: str = Field(default_factory=lambda: f"role_batch_{uuid.uuid4().hex[:8]}")
    total_prompts: int = 0
    successful_jailbreaks: int = 0
    overall_success_rate: float = 0.0
    blocked_by_guard: int = 0
    overall_guard_block_rate: float = 0.0
    style_breakdown: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    most_evasive_style: Optional[str] = None
    most_successful_style: Optional[str] = None
    detailed_results: List[AlternateRoleTestResult] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now_str)

class BenignRolePrompt(BaseModel):
    id: str = Field(default_factory=lambda: f"BENIGN-{uuid.uuid4().hex[:6]}")
    role_name: str
    prompt_text: str
    category: str = "creative_writing"
    description: str = ""

class BenignRoleEvaluationSummary(BaseModel):
    total_prompts: int = 0
    blocked_prompts: int = 0
    false_positive_rate: float = 0.0
    blocked_details: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now_str)
