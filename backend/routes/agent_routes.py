import time
import uuid
import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

from targets.vulnerable_agent.agent import VulnerableSupportAgent
from targets.vulnerable_agent.tools import AVAILABLE_TOOLS_SCHEMA, reset_mock_database
from promptguard.firewall import PromptGuardFirewall
from promptguard.output_guards.tool_policy_guard import ToolExecutionPolicyGuard
from core.models import ToolsSummaryMetadata
from database.db import AuditDatabase

router = APIRouter(prefix="/api", tags=["Agent & RAG Sandbox"])

# Singletons
agent = VulnerableSupportAgent(enable_rag=True)
firewall = PromptGuardFirewall()
db = AuditDatabase()

class AgentChatRequest(BaseModel):
    message: str = Field(..., description="User message or prompt")
    session_id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    enable_promptguard: bool = Field(True, description="Toggle PromptGuard defense firewall")

class RAGSearchRequest(BaseModel):
    query: str = Field(..., description="Query to search against RAG knowledge base")
    top_k: int = Field(3, ge=1, le=10)

@router.post("/agent/chat")
async def chat_with_agent(req: AgentChatRequest):
    """
    Interactive chat turn with the NovaSupport AI Agent.
    Executes RAG context retrieval, promptguard inspection (if enabled), and tool calling with rich execution metadata.
    """
    start_time = time.time()
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    interaction_id = str(uuid.uuid4())

    # 1. PromptGuard Input Inspection
    if req.enable_promptguard:
        guard_res = firewall.inspect_input(req.message)
        if guard_res.action.value == "block":
            latency = (time.time() - start_time) * 1000.0
            bot_text = f"🛡️ [SECURITY INTERVENTION]: Your request was blocked by PromptGuard Firewall ({guard_res.reason})."
            
            # Log blocked turn to telemetry
            db.log_agent_interaction(
                interaction_id=interaction_id,
                session_id=req.session_id,
                timestamp=timestamp,
                user_prompt=req.message,
                bot_response=bot_text,
                tools_executed=[],
                guard_blocked=True,
                latency_ms=latency
            )

            return {
                "interaction_id": interaction_id,
                "session_id": req.session_id,
                "blocked": True,
                "guard_reason": guard_res.reason,
                "detected_ciphers": guard_res.detected_ciphers,
                "response": bot_text,
                "tools_executed": [],
                "tools_summary": ToolsSummaryMetadata().model_dump(),
                "retrieved_chunks": [],
                "latency_ms": round(latency, 2)
            }

    # 2. Agent Execution with RAG & Tool Execution with Policy Guard
    bot_text, tools_executed, retrieved_chunks, tools_summary = agent.handle_message(  # type: ignore[misc]
        req.message,
        enable_policy_guard=req.enable_promptguard,
        return_summary=True
    )

    # 3. PromptGuard Output Guard (Canary token leakage check)
    if req.enable_promptguard:
        out_res = firewall.inspect_output(bot_text)
        bot_text = out_res.inspected_response

    latency = (time.time() - start_time) * 1000.0
    tools_data = [t.model_dump() for t in tools_executed]

    # 4. Log interaction with rich tool execution metadata to SQLite
    db.log_agent_interaction(
        interaction_id=interaction_id,
        session_id=req.session_id,
        timestamp=timestamp,
        user_prompt=req.message,
        bot_response=bot_text,
        tools_executed=tools_data,
        guard_blocked=False,
        latency_ms=latency
    )

    return {
        "interaction_id": interaction_id,
        "session_id": req.session_id,
        "blocked": False,
        "response": bot_text,
        "tools_executed": tools_data,
        "tools_summary": tools_summary.model_dump(),
        "retrieved_chunks": retrieved_chunks,
        "latency_ms": round(latency, 2)
    }

@router.get("/agent/tools")
async def list_available_tools():
    """List all available tools, function schemas, and active security policy thresholds."""
    return {
        "tools": AVAILABLE_TOOLS_SCHEMA,
        "security_policy": {
            "max_refund_limit": ToolExecutionPolicyGuard.MAX_REFUND_LIMIT,
            "forbidden_sql_operations": ToolExecutionPolicyGuard.FORBIDDEN_SQL_OPERATIONS,
            "privileged_tools": ["process_refund", "execute_internal_query", "update_account_email"]
        }
    }

@router.post("/agent/reset")
async def reset_agent_session():
    """Reset agent conversation history and restore mock database to initial state."""
    agent.reset_history()
    reset_mock_database()
    return {"status": "success", "message": "Agent conversation history and mock database successfully reset."}

@router.get("/rag/documents")
async def list_rag_documents():
    """List loaded RAG documents and chunk counts."""
    if agent.rag:
        doc_names = list({c.get("doc_name") or c.get("source") for c in agent.rag.chunks if (c.get("doc_name") or c.get("source"))})
        return {
            "total_chunks": len(agent.rag.chunks),
            "documents": doc_names
        }
    return {"total_chunks": 0, "documents": []}

@router.post("/rag/search")
async def search_rag(req: RAGSearchRequest):
    """Inspect and test raw RAG vector search for any query."""
    if agent.rag:
        results = agent.rag.retrieve(req.query, top_k=req.top_k)
        return {"query": req.query, "matches_found": len(results), "chunks": results}
    return {"query": req.query, "matches_found": 0, "chunks": []}
