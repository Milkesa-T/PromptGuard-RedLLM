from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

from redllm.strategies.crescendo import (
    CrescendoStrategy,
    CrescendoObjective,
    CrescendoObjectiveType,
    get_default_crescendo_objectives,
    get_crescendo_objective_by_type
)

router = APIRouter(prefix="/api/crescendo", tags=["Crescendo Multi-Turn Evaluation"])

strategy = CrescendoStrategy()

class CrescendoRunRequest(BaseModel):
    objective_type: Optional[CrescendoObjectiveType] = Field(
        None,
        description="Specific objective type to run, or None for all"
    )
    enable_guard: bool = Field(True, description="Enable PromptGuard firewall during multi-turn testing")
    max_turns: int = Field(5, ge=1, le=10)
    max_backtracks: int = Field(2, ge=0, le=5)

class CrescendoBatchRequest(BaseModel):
    repetitions: int = Field(1, ge=1, le=10, description="Repetitions per test objective")
    enable_guard: bool = Field(True, description="Enable PromptGuard firewall")
    objective_types: Optional[List[CrescendoObjectiveType]] = None

@router.get("/objectives")
async def list_crescendo_objectives():
    """List all available Crescendo multi-turn test objectives."""
    objs = get_default_crescendo_objectives()
    return {"objectives": [o.model_dump() for o in objs]}

@router.post("/run")
async def run_crescendo_single(req: CrescendoRunRequest):
    """Execute a single Crescendo multi-turn evaluation run."""
    obj = None
    if req.objective_type:
        obj = get_crescendo_objective_by_type(req.objective_type)
    if not obj:
        obj = get_default_crescendo_objectives()[0]

    obj.max_turns = req.max_turns
    obj.max_backtracks_per_turn = req.max_backtracks

    result = strategy.run_evaluation(obj, enable_guard=req.enable_guard)
    return result.model_dump()

@router.post("/batch")
async def run_crescendo_batch(req: CrescendoBatchRequest):
    """Execute Crescendo multi-turn evaluation across a batch of objectives with repetitions."""
    target_objs = []
    if req.objective_types:
        for ot in req.objective_types:
            found = get_crescendo_objective_by_type(ot)
            if found:
                target_objs.append(found)
    else:
        target_objs = get_default_crescendo_objectives()

    summary = strategy.run_batch(
        objectives=target_objs,
        repetitions=req.repetitions,
        enable_guard=req.enable_guard
    )
    return summary.model_dump()

@router.get("/benign")
async def evaluate_benign_conversations():
    """Evaluate long benign multi-turn conversation suite to measure false positive rate."""
    summary = strategy.evaluate_benign()
    return summary.model_dump()
