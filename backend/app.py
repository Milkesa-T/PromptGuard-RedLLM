import time
from pathlib import Path
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

from core.models import (
    AttackRequest, AttackResult, AttackType,
    GuardInspectionResult, GuardAction, BenchmarkSummary
)
from promptguard.firewall import PromptGuardFirewall
from targets.llm_target import LLMTarget
from targets.vulnerable_agent.agent import VulnerableSupportAgent
from evaluation.scorer import EvaluationJudge
from database.db import AuditDatabase
from redllm.orchestrator import RedLLMOrchestrator
from evaluation.benchmark import BenchmarkRunner

app = FastAPI(
    title="PromptGuard / RedLLM Security API",
    description="Automated Red-Teaming & Defense Framework for LLMs & AI Agents",
    version="1.0.0"
)

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Core singletons
db = AuditDatabase()
firewall = PromptGuardFirewall()
target = LLMTarget()
judge = EvaluationJudge()
orchestrator = RedLLMOrchestrator()
benchmark_runner = BenchmarkRunner(db=db)
vulnerable_agent = VulnerableSupportAgent()

class SingleAttackRequest(BaseModel):
    prompt: str
    objective: str = "PWNED_SYSTEM_OVERRIDE"
    enable_promptguard: bool = True
    attack_type: AttackType = AttackType.DIRECT_INJECTION

class InspectRequest(BaseModel):
    prompt: str

class AgentChatRequest(BaseModel):
    message: str
    enable_promptguard: bool = True

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "PromptGuard-RedLLM", "version": "1.0.0"}

@app.get("/api/stats")
async def get_stats():
    """Retrieve aggregate security metrics from SQLite."""
    return db.get_aggregate_stats()

@app.get("/api/logs")
async def get_logs(limit: int = 50):
    """Retrieve recent attack and defense audit logs."""
    return {"logs": db.get_recent_logs(limit=limit)}

@app.post("/api/guard/inspect")
async def inspect_prompt(req: InspectRequest):
    """Inspect a prompt with PromptGuard firewall without sending to target."""
    result = firewall.inspect_input(req.prompt)
    return result

@app.post("/api/attack/run")
async def run_single_attack(req: SingleAttackRequest):
    """Execute a single attack payload against target with or without PromptGuard."""
    start_t = time.time()
    guard_res = GuardInspectionResult(action=GuardAction.ALLOW, inspected_prompt=req.prompt)
    
    # 1. Firewall Check
    if req.enable_promptguard:
        guard_res = firewall.inspect_input(req.prompt)
        
    if guard_res.action == GuardAction.BLOCK:
        res = AttackResult(
            attack_id=str(time.time()),
            objective=req.objective,
            sent_prompt=req.prompt,
            target_response="[BLOCKED BY PROMPTGUARD FIREWALL]",
            guard_result=guard_res,
            is_success=False,
            judge_reason=f"Blocked: {guard_res.reason}",
            execution_time_seconds=time.time() - start_t
        )
    else:
        # 2. Forward to Target
        prompt_to_send = guard_res.inspected_prompt
        bot_response = await target.send_prompt_async(prompt_to_send)
        
        # 3. Output Guard Inspection
        out_guard_res = None
        if req.enable_promptguard:
            out_guard_res = firewall.inspect_output(bot_response)
            bot_response = out_guard_res.inspected_response
            
        # 4. Judge Evaluation
        is_success, judge_reason = judge.evaluate(req.objective, prompt_to_send, bot_response)
        
        res = AttackResult(
            attack_id=str(time.time()),
            objective=req.objective,
            sent_prompt=req.prompt,
            target_response=bot_response,
            guard_result=guard_res,
            output_guard_result=out_guard_res,
            is_success=is_success,
            judge_reason=judge_reason,
            execution_time_seconds=time.time() - start_t
        )
        
    db.log_result(res)
    return res

@app.post("/api/agent/chat")
async def chat_with_agent(req: AgentChatRequest):
    """Interactive chat with vulnerable support agent protected by PromptGuard."""
    start_t = time.time()
    guard_res = GuardInspectionResult(action=GuardAction.ALLOW, inspected_prompt=req.message)
    
    if req.enable_promptguard:
        guard_res = firewall.inspect_input(req.message)
        if guard_res.action == GuardAction.BLOCK:
            return {
                "blocked": True,
                "reason": guard_res.reason,
                "response": "⚠️ Security Alert: Your request was blocked by PromptGuard security policy.",
                "tools_executed": [],
                "latency_ms": (time.time() - start_t) * 1000.0
            }
            
    bot_res, tools = vulnerable_agent.handle_message(req.message)
    
    # Output inspection
    if req.enable_promptguard:
        out_res = firewall.inspect_output(bot_res)
        bot_res = out_res.inspected_response
        
    return {
        "blocked": False,
        "response": bot_res,
        "tools_executed": tools,
        "latency_ms": (time.time() - start_t) * 1000.0
    }

@app.post("/api/benchmark/run")
async def run_benchmark(enable_guard: bool = True):
    """Run full benchmark campaign across generated adversarial suite."""
    campaign = orchestrator.generate_campaign()
    summary = await benchmark_runner.run_benchmark_async(
        requests=campaign,
        enable_guard=enable_guard,
        campaign_name="FastAPI Triggered Benchmark"
    )
    return summary

# Mount static frontend directory if exists
frontend_path = Path(__file__).resolve().parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="frontend")
