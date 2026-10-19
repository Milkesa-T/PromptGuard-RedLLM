import time
import json
from pathlib import Path
import csv
import io
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
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
from evaluation.scorer import EvaluationJudge
from database.db import AuditDatabase
from redllm.orchestrator import RedLLMOrchestrator
from evaluation.benchmark import BenchmarkRunner

# Import modular route handlers
from backend.routes.audit_routes import router as audit_router
from backend.routes.agent_routes import router as agent_router

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

# Register Modular Feature Routers
app.include_router(audit_router)
app.include_router(agent_router)

# Core singletons for Red-Team launcher
db = AuditDatabase()
firewall = PromptGuardFirewall()
target = LLMTarget()
judge = EvaluationJudge()
orchestrator = RedLLMOrchestrator()
benchmark_runner = BenchmarkRunner(db=db)

class SingleAttackRequest(BaseModel):
    prompt: str
    objective: str = "PWNED_SYSTEM_OVERRIDE"
    enable_promptguard: bool = True
    attack_type: AttackType = AttackType.DIRECT_INJECTION

class InspectRequest(BaseModel):
    prompt: str

@app.get("/api/health")
async def health_check():
    """Health check probe."""
    return {"status": "healthy", "service": "PromptGuard-RedLLM", "version": "1.0.0"}

@app.post("/api/guard/inspect")
async def inspect_prompt(req: InspectRequest):
    """Inspect a prompt with PromptGuard firewall without forwarding to LLM."""
    result = firewall.inspect_input(req.prompt)
    return result

@app.get("/api/attack/presets")
async def get_attack_presets():
    """Retrieve dynamic adversarial attack presets from curated dataset files."""
    dataset_dir = Path(__file__).resolve().parent.parent / "evaluation" / "datasets"
    presets = []
    for filename in ["jailbreaks.json", "system_leaks.json", "tool_abuse.json"]:
        file_path = dataset_dir / filename
        if file_path.exists():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    presets.extend(data)
            except Exception:
                pass
    return {"total": len(presets), "presets": presets}

@app.post("/api/attack/run")
async def run_single_attack(req: SingleAttackRequest):
    """Execute a single attack payload against target with or without PromptGuard."""
    start_t = time.time()
    guard_res = GuardInspectionResult(action=GuardAction.ALLOW, inspected_prompt=req.prompt)
    
    # 1. Input Firewall Check
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
        # 2. Forward to Target Model
        prompt_to_send = guard_res.inspected_prompt
        bot_response = await target.send_prompt_async(prompt_to_send)
        
        # 3. Output Guard Inspection (Canary Check)
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



@app.get("/api/benchmark/results")
async def get_benchmark_results():
    """Return individual results from the latest completed benchmark."""
    return {
        "campaign": benchmark_runner.last_campaign_name,
        "total": len(benchmark_runner.last_results),
        "results": benchmark_runner.last_results,
    }


@app.get("/api/benchmark/export")
async def export_benchmark_results(format: str = "json"):
    """Download the latest benchmark telemetry as JSON or CSV."""
    rows = benchmark_runner.last_results
    fmt = format.strip().lower()

    if fmt == "json":
        content = json.dumps({
            "campaign": benchmark_runner.last_campaign_name,
            "total": len(rows),
            "results": rows,
        }, indent=2, ensure_ascii=False)
        return Response(
            content=content,
            media_type="application/json",
            headers={"Content-Disposition": 'attachment; filename="benchmark_results.json"'},
        )

    if fmt == "csv":
        output = io.StringIO()
        fields = list(rows[0].keys()) if rows else [
            "attack_id", "campaign", "attack_type", "objective", "prompt",
            "target_response", "guard_action", "guard_reason", "is_success",
            "judge_reason", "execution_time_seconds", "guard_enabled",
        ]
        writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="benchmark_results.csv"'},
        )

    raise HTTPException(status_code=400, detail="format must be json or csv")

# Mount static frontend directory (React build dist or fallback)
frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
frontend_legacy = Path(__file__).resolve().parent.parent / "frontend"

if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")
elif frontend_legacy.exists():
    app.mount("/", StaticFiles(directory=str(frontend_legacy), html=True), name="frontend")
