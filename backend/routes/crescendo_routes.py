"""
Crescendo Multi-Turn Evaluation API Routes.

Exposes endpoints for running Crescendo adversarial multi-turn evaluations,
batch runs across objectives, benign FPR evaluation, and historical run retrieval.

Lazy initialization is used so the heavy ML-backed firewall and agent are only
loaded when the first request arrives — not on every import.
"""
from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from redllm.strategies.crescendo import (
    CrescendoObjectiveType,
    CrescendoStrategy,
    get_crescendo_objective_by_type,
    get_default_crescendo_objectives,
)
from database.db import AuditDatabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/crescendo", tags=["Crescendo Multi-Turn Evaluation"])

# ---------------------------------------------------------------------------
# Lazy singletons — instantiated on first request to avoid loading ML models
# at import/startup time when not needed.
# ---------------------------------------------------------------------------
_strategy: Optional[CrescendoStrategy] = None
_db: Optional[AuditDatabase] = None


def _get_strategy() -> CrescendoStrategy:
    global _strategy
    if _strategy is None:
        _strategy = CrescendoStrategy()
    return _strategy


def _get_db() -> AuditDatabase:
    global _db
    if _db is None:
        _db = AuditDatabase()
    return _db



# ---------------------------------------------------------------------------
# NOTE FOR TESTS: To mock the strategy in tests, patch the module-level
# `_strategy` variable directly:
#
#   import backend.routes.crescendo_routes as cr_mod
#   cr_mod._strategy = mock_strategy
#
# Or patch `_get_strategy` to return a mock:
#
#   with patch("backend.routes.crescendo_routes._get_strategy", return_value=mock_strategy):
#       ...
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Request / Response Schemas
# ---------------------------------------------------------------------------

class CrescendoRunRequest(BaseModel):
    objective_type: Optional[CrescendoObjectiveType] = Field(
        None,
        description="Specific objective type to run. Defaults to the first objective if omitted.",
    )
    enable_guard: bool = Field(
        True,
        description="Enable PromptGuard firewall during multi-turn testing.",
    )
    max_turns: int = Field(5, ge=1, le=10, description="Maximum turns per objective run.")
    max_backtracks: int = Field(2, ge=0, le=5, description="Max backtrack retries per turn.")


class CrescendoBatchRequest(BaseModel):
    repetitions: int = Field(
        1, ge=1, le=10,
        description="Number of repetitions to run per objective.",
    )
    enable_guard: bool = Field(True, description="Enable PromptGuard firewall.")
    objective_types: Optional[List[CrescendoObjectiveType]] = Field(
        None,
        description="Subset of objective types to evaluate. Runs all if omitted.",
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/objectives", summary="List all Crescendo test objectives")
async def list_crescendo_objectives():
    """Return the full list of available Crescendo multi-turn evaluation objectives."""
    objs = get_default_crescendo_objectives()
    return {"objectives": [o.model_dump() for o in objs]}


@router.post("/run", summary="Run a single Crescendo evaluation")
async def run_crescendo_single(req: CrescendoRunRequest):
    """
    Execute one Crescendo multi-turn evaluation run.

    If `objective_type` is supplied the matching objective is used;
    otherwise defaults to the first (MARKER_EXTRACTION) objective.
    """
    obj = None
    if req.objective_type:
        obj = get_crescendo_objective_by_type(req.objective_type)
    if not obj:
        obj = get_default_crescendo_objectives()[0]

    # Override turn / backtrack limits from request
    obj.max_turns = req.max_turns
    obj.max_backtracks_per_turn = req.max_backtracks

    result = _get_strategy().run_evaluation(obj, enable_guard=req.enable_guard)

    # Best-effort DB persistence — never fail a request due to a logging error
    try:
        _get_db().log_crescendo_run(result)
    except Exception as exc:
        logger.warning("Failed to persist crescendo run to DB: %s", exc)

    return result.model_dump()


@router.post("/batch", summary="Run batch Crescendo evaluations")
async def run_crescendo_batch(req: CrescendoBatchRequest):
    """
    Execute Crescendo evaluation across a batch of objectives with multiple repetitions.

    Returns aggregated success rates, content-leak rates, guard catch rates,
    and backtracking statistics.
    """
    target_objs = []
    if req.objective_types:
        for ot in req.objective_types:
            found = get_crescendo_objective_by_type(ot)
            if found:
                target_objs.append(found)
        if not target_objs:
            raise HTTPException(
                status_code=400,
                detail="None of the requested objective_types match known objectives.",
            )
    else:
        target_objs = get_default_crescendo_objectives()

    summary = _get_strategy().run_batch(
        objectives=target_objs,
        repetitions=req.repetitions,
        enable_guard=req.enable_guard,
    )
    return summary.model_dump()


@router.get("/runs", summary="List historical evaluation runs")
async def get_crescendo_runs(limit: int = 50):
    """Retrieve the most recent Crescendo multi-turn evaluation runs from the audit database."""
    runs = _get_db().get_crescendo_runs(limit=limit)
    return {"total": len(runs), "runs": runs}


@router.get("/benign", summary="Evaluate benign conversation false-positive rate")
async def evaluate_benign_conversations():
    """
    Run the benign multi-turn conversation test suite against the active guard.

    Returns false-positive rates at both turn and conversation granularity,
    along with details of any incorrectly blocked turns.
    """
    summary = _get_strategy().evaluate_benign()
    return summary.model_dump()

