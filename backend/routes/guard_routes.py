from fastapi import APIRouter, HTTPException, Query, Body
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import logging

from database.db import AuditDatabase
from promptguard.input_guards.semantic_guard import SemanticSimilarityGuard

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/guard", tags=["PromptGuard & Adaptive Exemplars"])
db = AuditDatabase()


class AddExemplarRequest(BaseModel):
    phrase: str = Field(..., description="Malicious or jailbreak prompt exemplar to learn")
    category: str = Field("adaptive_defense", description="Threat category (e.g., prompt_injection, system_leak)")
    source: str = Field("manual_analyst", description="Origin of exemplar (e.g., red_team_feedback, manual_analyst)")


class AdaptFeedbackRequest(BaseModel):
    prompts: Optional[List[str]] = Field(None, description="Optional explicit list of evasion prompts to adapt against. If empty, auto-fetches recent unblocked attacks from audit logs.")
    category: str = Field("closed_loop_feedback", description="Category for learned exemplars")


@router.get("/exemplars")
async def list_exemplars() -> Dict[str, Any]:
    """Retrieve all active seed and dynamically learned jailbreak exemplars."""
    guard = SemanticSimilarityGuard()
    stats = guard.get_exemplar_stats()
    db_exemplars = db.get_guard_exemplars()
    
    return {
        "status": "success",
        "seed_count": stats["seed_count"],
        "dynamic_count": len(db_exemplars),
        "total_active_vectors": stats["total_active_vectors"],
        "threshold": stats["threshold"],
        "dynamic_exemplars": db_exemplars
    }


@router.post("/exemplars")
async def add_single_exemplar(req: AddExemplarRequest) -> Dict[str, Any]:
    """Manually add an exemplar to the vector defense index and persistent database."""
    phrase = req.phrase.strip()
    if not phrase:
        raise HTTPException(status_code=400, detail="Phrase cannot be empty")
        
    guard = SemanticSimilarityGuard()
    added_count = guard.add_exemplars([phrase], category=req.category, source=req.source, persist=True)
    
    return {
        "status": "success" if added_count > 0 else "already_exists",
        "added": added_count,
        "message": f"Successfully ingested exemplar into active defense index." if added_count > 0 else "Phrase already indexed in active vectors.",
        "stats": guard.get_exemplar_stats()
    }


@router.post("/exemplars/adapt")
async def trigger_closed_loop_adaptation(req: AdaptFeedbackRequest = Body(...)) -> Dict[str, Any]:
    """
    Closed-Loop Adaptive Defense Trigger:
    Ingests successful jailbreaks/evasions from a campaign or query stream,
    synthesizes embeddings, and dynamically reinforces PromptGuard.
    """
    prompts_to_adapt = req.prompts or []
    
    # If no explicit prompts passed, auto-mine recent successful attacks from audit_logs
    if not prompts_to_adapt:
        recent_logs = db.get_recent_logs(limit=100)
        # Find attacks that succeeded (is_success == 1) or were allowed through
        for log in recent_logs:
            if log.get("is_success") == 1 or log.get("guard_action") == "allow":
                sent = log.get("sent_prompt", "").strip()
                if sent and len(sent) > 10 and sent not in prompts_to_adapt:
                    prompts_to_adapt.append(sent)

    if not prompts_to_adapt:
        return {
            "status": "no_evasions_found",
            "ingested_count": 0,
            "message": "No unblocked evasions or successful jailbreaks found to adapt against."
        }

    guard = SemanticSimilarityGuard()
    ingested = guard.add_exemplars(
        prompts_to_adapt,
        category=req.category,
        source="closed_loop_feedback",
        persist=True
    )
    
    return {
        "status": "adapted",
        "ingested_count": ingested,
        "total_evaluated": len(prompts_to_adapt),
        "message": f"PromptGuard successfully adapted! Learned {ingested} new evasion patterns.",
        "stats": guard.get_exemplar_stats()
    }


@router.delete("/exemplars/{exemplar_id}")
async def remove_exemplar(exemplar_id: int) -> Dict[str, Any]:
    """Remove a dynamic exemplar and reload baseline seeds + remaining dynamic items."""
    success = db.delete_guard_exemplar(exemplar_id)
    if not success:
        raise HTTPException(status_code=404, detail="Exemplar ID not found")
        
    guard = SemanticSimilarityGuard()
    guard.reset_to_seeds(clear_db=False)
    # Re-trigger ensure_model so it re-reads remaining exemplars from database
    guard._seed_embeddings = None
    guard._ensure_model()
    
    return {
        "status": "deleted",
        "exemplar_id": exemplar_id,
        "stats": guard.get_exemplar_stats()
    }


@router.post("/exemplars/reset")
async def reset_exemplars_to_baseline() -> Dict[str, Any]:
    """Reset the adaptive defense layer back to the baseline 32 seed phrases."""
    cleared = db.clear_guard_exemplars()
    guard = SemanticSimilarityGuard()
    guard.reset_to_seeds(clear_db=True)
    
    return {
        "status": "reset",
        "cleared_count": cleared,
        "message": "PromptGuard semantic vectors reset to baseline 32 seeds.",
        "stats": guard.get_exemplar_stats()
    }
