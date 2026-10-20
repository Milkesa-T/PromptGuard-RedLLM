from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum
import uuid
import datetime

def utc_now_str() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

class CrescendoObjectiveType(str, Enum):
    MARKER_EXTRACTION = "marker_extraction"
    SYSTEM_INSTRUCTION_LEAK = "system_instruction_leak"
    INDIRECT_RETRIEVAL = "indirect_retrieval"
    UNAUTHORIZED_ACTION = "unauthorized_action"
    RETRIEVED_INSTRUCTION_FOLLOWING = "retrieved_instruction_following"

class CrescendoObjective(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    objective_type: CrescendoObjectiveType
    name: str
    description: str
    target_marker: Optional[str] = None
    target_doc: Optional[str] = None
    target_tool: Optional[str] = None
    target_instruction_marker: Optional[str] = None
    max_turns: int = 5
    max_backtracks_per_turn: int = 2
    metadata: Dict[str, Any] = Field(default_factory=dict)

class CrescendoTurnRecord(BaseModel):
    turn_index: int
    prompt: str
    response: str = ""
    retrieved_chunks: List[Dict[str, Any]] = Field(default_factory=list)
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    guard_action: str = "allow"
    guard_reason: Optional[str] = None
    progress_score: float = 0.0
    is_backtrack: bool = False
    backtrack_attempt: int = 0
    notes: Optional[str] = None

class CrescendoRunResult(BaseModel):
    run_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    objective_id: str
    objective_type: str
    objective_description: str
    is_success: bool = False
    turns_used: int = 0
    transcript: List[CrescendoTurnRecord] = Field(default_factory=list)
    progress_scores: List[float] = Field(default_factory=list)
    guard_interventions: List[Dict[str, Any]] = Field(default_factory=list)
    backtrack_count: int = 0
    surfaced_restricted_content: List[str] = Field(default_factory=list)
    surfaced_actions: List[Dict[str, Any]] = Field(default_factory=list)
    stopping_reason: str = "running"
    execution_time_seconds: float = 0.0
    timestamp: str = Field(default_factory=utc_now_str)

class CrescendoBatchSummary(BaseModel):
    batch_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    total_runs: int = 0
    successful_runs: int = 0
    success_rate: float = 0.0
    avg_turns_overall: float = 0.0
    avg_turns_successful: float = 0.0
    restricted_content_leak_count: int = 0
    restricted_content_leak_rate: float = 0.0
    restricted_action_count: int = 0
    restricted_action_rate: float = 0.0
    guard_catch_count: int = 0
    guard_catch_rate: float = 0.0
    avg_turn_caught: Optional[float] = None
    total_backtracks: int = 0
    avg_backtracks_per_run: float = 0.0
    objective_breakdown: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    detailed_results: List[CrescendoRunResult] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now_str)

class BenignTurn(BaseModel):
    turn_index: int
    user_message: str
    expected_topic: str = "customer_service"

class BenignConversation(BaseModel):
    conversation_id: str
    title: str
    turns: List[BenignTurn]

class BenignEvaluationSummary(BaseModel):
    total_conversations: int = 0
    total_turns: int = 0
    blocked_turns: int = 0
    blocked_conversations: int = 0
    false_positive_rate_turns: float = 0.0
    false_positive_rate_conversations: float = 0.0
    blocked_turn_details: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now_str)
