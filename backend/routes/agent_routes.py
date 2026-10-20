import asyncio
import datetime
import json
import time
import uuid
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from guards.pii_redaction import PIIRedactionGuard
from guards.sql_policy_guard import ToolParameterEnforcer
from guards.canary_guard import CanaryGuard

pii_guard = PIIRedactionGuard()
canary_guard = CanaryGuard()

from targets.vulnerable_agent.agent import VulnerableSupportAgent
from targets.vulnerable_agent.tools import AVAILABLE_TOOLS_SCHEMA, reset_mock_database
from targets.rag.injection_sandbox import (
    RAGInjectionSandbox,
    INDIRECT_INJECTION_PRESETS,
    indirect_rag_guard_filter
)
from promptguard.firewall import PromptGuardFirewall
from promptguard.output_guards.tool_policy_guard import ToolExecutionPolicyGuard
from core.models import ToolsSummaryMetadata
from database.db import AuditDatabase

router = APIRouter(prefix="/api", tags=["Agent & RAG Sandbox"])

# Singletons
agent = VulnerableSupportAgent(enable_rag=True)
firewall = PromptGuardFirewall()
db = AuditDatabase()
rag_sandbox = RAGInjectionSandbox()


class AgentChatRequest(BaseModel):
    message: str = Field(..., description="User message or prompt")
    session_id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    enable_promptguard: bool = Field(True, description="Toggle PromptGuard defense firewall")


class RAGSearchRequest(BaseModel):
    query: str = Field(..., description="Query to search against RAG knowledge base")
    top_k: int = Field(3, ge=1, le=10)


class IndirectInjectionTestRequest(BaseModel):
    query: str = Field(..., description="User query directed to agent")
    poisoned_title: str = Field(..., description="Title of the poisoned document")
    poisoned_content: str = Field(..., description="Adversarial content injected into RAG")
    enable_defense: bool = Field(True, description="Enable PromptGuard indirect injection checkpoint defense")


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

    # 3. PromptGuard Output Guard (Canary token leakage check & PII Redaction)
    if req.enable_promptguard:
        out_res = firewall.inspect_output(bot_text)
        bot_text = out_res.inspected_response

        # Catch obfuscated canary leaks (spaces, punctuation)
        is_leaked, canary_info = canary_guard.inspect(bot_text)
        if is_leaked:
            bot_text = "🛡️ [SECURITY INTERVENTION]: Outgoing response blocked due to detected canary token leakage."

        # Redact credit cards, SSNs, and emails
        bot_text, _ = pii_guard.redact(bot_text)

    latency = (time.time() - start_time) * 1000.0
    tools_data = [t.model_dump() for t in tools_executed]

    # Validate tool arguments against SQL & Refund policies
    if req.enable_promptguard:
        for tool in tools_data:
            tool_name = tool.get("tool_name") or tool.get("name")
            tool_args = tool.get("parameters") or tool.get("args") or {}
            is_valid, reason = ToolParameterEnforcer.validate_tool_call(tool_name, tool_args)
            if not is_valid:
                tool["status"] = "blocked"
                tool["policy_violation"] = reason

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


def _format_sse(event_name: str, data: Dict[str, Any]) -> str:
    """Format SSE frame with event and json data."""
    return f"event: {event_name}\ndata: {json.dumps(data)}\n\n"


async def generate_agent_stream(
    message: str,
    session_id: str,
    enable_promptguard: bool
):
    """Asynchronous generator yielding live Server-Sent Events for agent execution lifecycle."""
    start_time = time.time()
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    interaction_id = str(uuid.uuid4())

    # Step 1: Input Guard Inspection
    yield _format_sse("status", {"phase": "guard_check", "message": "🔍 PromptGuard inspecting incoming prompt..."})
    await asyncio.sleep(0.01)

    guard_res = None
    if enable_promptguard:
        guard_res = firewall.inspect_input(message)
        if guard_res.action.value == "block":
            latency = (time.time() - start_time) * 1000.0
            bot_text = f"🛡️ [SECURITY INTERVENTION]: Blocked by PromptGuard Firewall ({guard_res.reason})."
            
            yield _format_sse("guard_decision", {
                "blocked": True,
                "reason": guard_res.reason,
                "detected_ciphers": guard_res.detected_ciphers,
                "latency_ms": round(guard_res.latency_ms, 2)
            })

            # Redact/log
            db.log_agent_interaction(
                interaction_id=interaction_id,
                session_id=session_id,
                timestamp=timestamp,
                user_prompt=message,
                bot_response=bot_text,
                tools_executed=[],
                guard_blocked=True,
                latency_ms=latency
            )

            yield _format_sse("done", {
                "interaction_id": interaction_id,
                "session_id": session_id,
                "blocked": True,
                "response": bot_text,
                "tools_executed": [],
                "retrieved_chunks": [],
                "latency_ms": round(latency, 2)
            })
            return

    yield _format_sse("guard_decision", {
        "blocked": False,
        "reason": "Prompt passed all input firewall inspection tiers.",
        "detected_ciphers": guard_res.detected_ciphers if guard_res else [],
        "latency_ms": round(guard_res.latency_ms, 2) if guard_res else 0.0
    })

    # Step 2: RAG Retrieval
    yield _format_sse("status", {"phase": "rag_retrieval", "message": "📚 Retrieving enterprise grounding context..."})
    retrieved_chunks = []
    if agent.enable_rag and agent.rag:
        retrieved_chunks = agent.rag.retrieve(message, top_k=2)
        yield _format_sse("rag_context", {
            "chunks_count": len(retrieved_chunks),
            "chunks": [
                {
                    "source": c.get("source") or c.get("doc_name"),
                    "text": c.get("text", "")[:180] + "...",
                    "similarity_score": c.get("similarity_score", 1.0)
                }
                for c in retrieved_chunks
            ]
        })

    # Step 3: Agent Reasoning & Tool Calls
    yield _format_sse("status", {"phase": "agent_reasoning", "message": "🤖 NovaSupport AI evaluating request..."})
    
    # Run agent execution turn
    bot_text, tools_executed, _, tools_summary = agent.handle_message(
        message,
        enable_policy_guard=enable_promptguard,
        return_summary=True
    )

    tools_data = [t.model_dump() for t in tools_executed]

    # Stream tool execution events
    for tool in tools_data:
        tool_name = tool.get("tool_name") or tool.get("name")
        tool_args = tool.get("parameters") or tool.get("args") or {}
        if enable_promptguard:
            is_valid, reason = ToolParameterEnforcer.validate_tool_call(tool_name, tool_args)
            if not is_valid:
                tool["status"] = "blocked"
                tool["policy_violation"] = reason

        yield _format_sse("tool_event", {
            "tool_name": tool_name,
            "status": tool.get("status", "success"),
            "parameters": tool_args,
            "result": tool.get("result", {}),
            "policy_violation": tool.get("policy_violation")
        })

    # Step 4: Output Guard Enforcement
    if enable_promptguard:
        out_res = firewall.inspect_output(bot_text)
        bot_text = out_res.inspected_response

        is_leaked, canary_info = canary_guard.inspect(bot_text)
        if is_leaked:
            bot_text = "🛡️ [SECURITY INTERVENTION]: Outgoing response blocked due to detected canary token leakage."
            yield _format_sse("output_guard", {"canary_leak_intercepted": True})

        bot_text, pii_stats = pii_guard.redact(bot_text)
        if isinstance(pii_stats, dict) and pii_stats.get("redacted"):
            yield _format_sse("output_guard", {"pii_redacted": pii_stats})


    # Step 5: Stream token response chunks
    words = bot_text.split(" ")
    for idx, word in enumerate(words):
        chunk_text = word if idx == len(words) - 1 else (word + " ")
        yield _format_sse("token", {"chunk": chunk_text})
        await asyncio.sleep(0.01)

    latency = (time.time() - start_time) * 1000.0

    # Log to DB
    db.log_agent_interaction(
        interaction_id=interaction_id,
        session_id=session_id,
        timestamp=timestamp,
        user_prompt=message,
        bot_response=bot_text,
        tools_executed=tools_data,
        guard_blocked=False,
        latency_ms=latency
    )

    yield _format_sse("done", {
        "interaction_id": interaction_id,
        "session_id": session_id,
        "blocked": False,
        "response": bot_text,
        "tools_executed": tools_data,
        "tools_summary": tools_summary.model_dump(),
        "retrieved_chunks": retrieved_chunks,
        "latency_ms": round(latency, 2)
    })


@router.post("/agent/chat/stream")
async def chat_with_agent_stream(req: AgentChatRequest):
    """Live SSE Streaming endpoint for interactive Agent turns."""
    return StreamingResponse(
        generate_agent_stream(
            message=req.message,
            session_id=req.session_id or str(uuid.uuid4()),
            enable_promptguard=req.enable_promptguard
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/agent/chat/stream")
async def chat_with_agent_stream_get(
    message: str = Query(..., description="User message"),
    session_id: Optional[str] = Query(None, description="Session ID"),
    enable_promptguard: bool = Query(True, description="Toggle PromptGuard")
):
    """GET SSE Streaming endpoint for browser EventSource client support."""
    return StreamingResponse(
        generate_agent_stream(
            message=message,
            session_id=session_id or str(uuid.uuid4()),
            enable_promptguard=enable_promptguard
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


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


# =========================================================================
# Indirect RAG Prompt Injection Sandbox Endpoints
# =========================================================================

@router.get("/rag/injection-presets")
async def get_indirect_injection_presets():
    """Retrieve curated Indirect RAG Prompt Injection attack vector presets."""
    return {
        "total": len(INDIRECT_INJECTION_PRESETS),
        "presets": INDIRECT_INJECTION_PRESETS
    }


@router.post("/rag/inject-test")
async def test_indirect_rag_injection(req: IndirectInjectionTestRequest):
    """
    Execute an isolated Indirect Prompt Injection simulation:
    Grounds agent on transiently poisoned RAG document and tests defense checkpoint.
    """
    result = rag_sandbox.simulate_attack(
        query=req.query,
        poisoned_title=req.poisoned_title,
        poisoned_content=req.poisoned_content,
        enable_defense=req.enable_defense
    )
    return result


@router.get("/rag/sandbox/status")
async def get_rag_sandbox_status():
    """Inspect active status of RAG Injection Sandbox."""
    return {
        "status": "ready",
        "pristine_chunks_count": len(rag_sandbox.pristine_chunks),
        "active_chunks_count": len(rag_sandbox.retriever.chunks),
        "poisoned_documents_count": len(rag_sandbox.poisoned_docs),
        "poisoned_documents": rag_sandbox.poisoned_docs
    }


@router.post("/rag/sandbox/reset")
async def reset_rag_sandbox():
    """Reset RAG Injection Sandbox back to clean baseline."""
    rag_sandbox.reset()
    return {"status": "success", "message": "RAG Sandbox knowledge base restored to pristine baseline."}
