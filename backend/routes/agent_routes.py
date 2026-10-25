import asyncio
import datetime
import json
import time
import re
import uuid
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, Query, File, UploadFile, Form
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


class DocumentTextUploadRequest(BaseModel):
    title: str = Field(..., description="Document title or filename (e.g. 'custom_policy.md')")
    content: str = Field(..., description="Document markdown or text content")
    access_level: str = Field("internal", description="Access level: public, internal, confidential, or restricted")
    save_to_disk: bool = Field(True, description="Whether to persist document to data/docs/")



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
            
            # Log blocked turn to telemetry and unified audit trail
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

            db.log_audit_event(
                attack_id=interaction_id,
                timestamp=timestamp,
                objective="Agent Prompt Injection Probe",
                sent_prompt=req.message,
                guard_action="block",
                guard_reason=guard_res.reason,
                target_response=bot_text,
                is_success=False,
                judge_reason=f"Blocked by input firewall: {guard_res.reason}",
                execution_time_seconds=latency / 1000.0,
                metadata={"session_id": req.session_id, "source": "agent_sandbox"}
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

    # 4. Log interaction with rich tool execution metadata to SQLite and audit trail
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

    has_policy_block = any(t.get("status") == "blocked" for t in tools_data)
    db.log_audit_event(
        attack_id=interaction_id,
        timestamp=timestamp,
        objective="Agent Support Query & Tool Use",
        sent_prompt=req.message,
        guard_action="block" if has_policy_block else "allow",
        guard_reason="Tool execution blocked by policy guard" if has_policy_block else "Passed PromptGuard filters",
        target_response=bot_text,
        is_success=False,
        judge_reason="Executed tool actions successfully" if not has_policy_block else "Tool policy violation intercepted",
        execution_time_seconds=latency / 1000.0,
        metadata={"session_id": req.session_id, "tools": tools_data, "source": "agent_sandbox"}
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

            # Redact/log to telemetry and unified audit trail
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

            db.log_audit_event(
                attack_id=interaction_id,
                timestamp=timestamp,
                objective="Agent Prompt Injection Probe",
                sent_prompt=message,
                guard_action="block",
                guard_reason=guard_res.reason,
                target_response=bot_text,
                is_success=False,
                judge_reason=f"Blocked by input firewall: {guard_res.reason}",
                execution_time_seconds=latency / 1000.0,
                metadata={"session_id": session_id, "source": "agent_sandbox_stream"}
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

    # Log to DB and unified audit trail
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

    has_policy_block = any(t.get("status") == "blocked" for t in tools_data)
    db.log_audit_event(
        attack_id=interaction_id,
        timestamp=timestamp,
        objective="Agent Support Query & Tool Use",
        sent_prompt=message,
        guard_action="block" if has_policy_block else "allow",
        guard_reason="Tool execution blocked by policy guard" if has_policy_block else "Passed PromptGuard filters",
        target_response=bot_text,
        is_success=False,
        judge_reason="Executed tool actions successfully" if not has_policy_block else "Tool policy violation intercepted",
        execution_time_seconds=latency / 1000.0,
        metadata={"session_id": session_id, "tools": tools_data, "source": "agent_sandbox_stream"}
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


PROTECTED_CORE_DOCS = {
    "confidential_admin_memo.txt",
    "refund_policy.md",
    "shipping_policy.md",
    "refund_guidelines.txt",
    "shipping_policy.txt",
    "vendor_integration_guide.md"
}


def _sanitize_filename(name: str) -> str:
    """Sanitize filename to prevent directory traversal and invalid characters."""
    cleaned = Path(name).name
    cleaned = re.sub(r"[^a-zA-Z0-9_.-]", "_", cleaned).strip("._ ")
    if not cleaned:
        cleaned = f"doc_{uuid.uuid4().hex[:6]}"
    if not (cleaned.endswith(".md") or cleaned.endswith(".txt") or cleaned.endswith(".json")):
        cleaned += ".md"
    return cleaned


@router.get("/rag/documents")
async def list_rag_documents():
    """List loaded RAG documents, chunk counts, and detailed metadata."""
    if not agent.rag:
        return {"total_chunks": 0, "documents": [], "details": []}

    doc_map: Dict[str, Dict[str, Any]] = {}
    for c in agent.rag.chunks:
        name = c.get("doc_name") or c.get("source") or "unknown"
        if name not in doc_map:
            doc_map[name] = {
                "name": name,
                "chunk_count": 0,
                "access_level": c.get("access_level", "internal"),
                "is_protected": name in PROTECTED_CORE_DOCS
            }
        doc_map[name]["chunk_count"] += 1

    sorted_docs = sorted(doc_map.keys())
    return {
        "total_chunks": len(agent.rag.chunks),
        "documents": sorted_docs,
        "details": [doc_map[k] for k in sorted_docs]
    }


@router.post("/rag/documents/upload")
async def upload_rag_document(
    file: UploadFile = File(...),
    access_level: str = Form("internal"),
    save_to_disk: bool = Form(True)
):
    """
    Upload a .md or .txt file into the active RAG knowledge base.
    Chunks and embeds contents into dense vectors dynamically.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided.")

    allowed_exts = {".md", ".txt", ".json"}
    ext = Path(file.filename).suffix.lower()
    if ext not in allowed_exts:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file extension '{ext}'. Allowed extensions: {', '.join(sorted(allowed_exts))}"
        )

    sanitized_name = _sanitize_filename(file.filename)
    raw_bytes = await file.read()
    try:
        content = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        content = raw_bytes.decode("latin-1", errors="replace")

    if not content.strip():
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # 1. Optionally persist to data/docs/
    project_root = Path(__file__).resolve().parent.parent.parent
    data_docs_dir = project_root / "data" / "docs"
    data_docs_dir.mkdir(parents=True, exist_ok=True)
    if save_to_disk:
        file_path = data_docs_dir / sanitized_name
        file_path.write_text(content, encoding="utf-8")

    # 2. Dynamically index into agent's RAG retriever
    new_chunks = []
    if agent.rag:
        new_chunks = agent.rag.add_document(
            doc_name=sanitized_name,
            content=content,
            access_level=access_level
        )
        rag_sandbox.pristine_chunks = list(agent.rag.chunks)

    return {
        "status": "success",
        "filename": sanitized_name,
        "access_level": access_level,
        "chunks_created": len(new_chunks),
        "total_chunks": len(agent.rag.chunks) if agent.rag else 0,
        "saved_to_disk": save_to_disk,
        "message": f"Successfully indexed '{sanitized_name}' ({len(new_chunks)} chunks)."
    }


@router.post("/rag/documents/text")
async def create_rag_document_from_text(req: DocumentTextUploadRequest):
    """Directly create, chunk, and index a document from raw text input."""
    if not req.title.strip() or not req.content.strip():
        raise HTTPException(status_code=400, detail="Title and content are required.")

    sanitized_name = _sanitize_filename(req.title)

    # 1. Optionally persist to data/docs/
    project_root = Path(__file__).resolve().parent.parent.parent
    data_docs_dir = project_root / "data" / "docs"
    data_docs_dir.mkdir(parents=True, exist_ok=True)
    if req.save_to_disk:
        file_path = data_docs_dir / sanitized_name
        file_path.write_text(req.content, encoding="utf-8")

    # 2. Index into agent RAG retriever
    new_chunks = []
    if agent.rag:
        new_chunks = agent.rag.add_document(
            doc_name=sanitized_name,
            content=req.content,
            access_level=req.access_level
        )
        rag_sandbox.pristine_chunks = list(agent.rag.chunks)

    return {
        "status": "success",
        "filename": sanitized_name,
        "access_level": req.access_level,
        "chunks_created": len(new_chunks),
        "total_chunks": len(agent.rag.chunks) if agent.rag else 0,
        "saved_to_disk": req.save_to_disk,
        "message": f"Successfully created and indexed '{sanitized_name}' ({len(new_chunks)} chunks)."
    }


@router.get("/rag/documents/{doc_name}/content")
async def get_rag_document_content(doc_name: str):
    """Retrieve full text and chunk breakdown for a specific RAG document."""
    sanitized = Path(doc_name).name
    project_root = Path(__file__).resolve().parent.parent.parent

    candidates = [
        project_root / "data" / "docs" / sanitized,
        project_root / "targets" / "rag" / "documents" / sanitized
    ]

    file_content = None
    for p in candidates:
        if p.exists() and p.is_file():
            try:
                file_content = p.read_text(encoding="utf-8")
                break
            except Exception:
                pass

    matching_chunks = []
    if agent.rag:
        matching_chunks = [
            c for c in agent.rag.chunks
            if c.get("doc_name") == sanitized or c.get("source") == sanitized
        ]

    if file_content is None and not matching_chunks:
        raise HTTPException(status_code=404, detail=f"Document '{doc_name}' not found.")

    if file_content is None:
        file_content = "\n\n".join(c.get("text", "") for c in matching_chunks)

    return {
        "filename": sanitized,
        "content": file_content,
        "chunks_count": len(matching_chunks),
        "chunks": matching_chunks
    }


@router.delete("/rag/documents/{doc_name}")
async def delete_rag_document(doc_name: str):
    """Delete a document from data/docs and rebuild the RAG vector index."""
    sanitized = Path(doc_name).name
    if sanitized in PROTECTED_CORE_DOCS:
        raise HTTPException(status_code=403, detail=f"Cannot delete protected core document '{doc_name}'.")

    project_root = Path(__file__).resolve().parent.parent.parent
    data_file = project_root / "data" / "docs" / sanitized
    deleted_from_disk = False
    if data_file.exists() and data_file.is_file():
        try:
            data_file.unlink()
            deleted_from_disk = True
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to delete file from disk: {e}")

    removed_from_memory = False
    if agent.rag:
        removed_from_memory = agent.rag.remove_document(sanitized)
        rag_sandbox.pristine_chunks = list(agent.rag.chunks)

    if not deleted_from_disk and not removed_from_memory:
        raise HTTPException(status_code=404, detail=f"Document '{doc_name}' not found.")

    return {
        "status": "success",
        "filename": sanitized,
        "deleted_from_disk": deleted_from_disk,
        "removed_from_memory": removed_from_memory,
        "remaining_chunks": len(agent.rag.chunks) if agent.rag else 0,
        "message": f"Document '{sanitized}' successfully removed from knowledge base."
    }



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
    start_t = time.time()
    result = rag_sandbox.simulate_attack(
        query=req.query,
        poisoned_title=req.poisoned_title,
        poisoned_content=req.poisoned_content,
        enable_defense=req.enable_defense
    )
    exec_t = time.time() - start_t
    
    is_blocked = bool(result.get("defense_intercepted", False))
    is_success = bool(result.get("compromised", False))
    
    db.log_audit_event(
        attack_id=f"rag_indirect_{uuid.uuid4().hex[:8]}",
        timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        objective=f"Indirect RAG Injection: {req.poisoned_title}",
        sent_prompt=f"[Query]: {req.query}\n[Poisoned Context]: {req.poisoned_content[:280]}",
        guard_action="block" if is_blocked else "allow",
        guard_reason=result.get("defense_reason") or ("Indirect RAG Checkpoint Intercepted" if is_blocked else ("Passed RAG Filter (Vulnerable)" if not req.enable_defense else "Passed RAG Filter")),
        target_response=result.get("agent_response", ""),
        is_success=is_success,
        judge_reason=f"Verdict: {result.get('verdict')} (Compromised: {is_success}, Intercepted: {is_blocked})",
        execution_time_seconds=exec_t,
        metadata={"poisoned_title": req.poisoned_title, "enable_defense": req.enable_defense, "source": "rag_indirect_sandbox"}
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
