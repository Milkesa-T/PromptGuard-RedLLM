from fastapi import APIRouter, Query, Response
from typing import Optional, Dict, Any
from database.db import AuditDatabase

router = APIRouter(prefix="/api", tags=["Audit & Telemetry"])
db = AuditDatabase()

@router.get("/stats")
async def get_stats() -> Dict[str, Any]:
    """Retrieve aggregated attack, defense, and agent telemetry statistics."""
    return db.get_aggregate_stats()

@router.get("/logs")
async def get_logs(
    limit: int = Query(50, ge=1, le=500, description="Max logs to return"),
    action_filter: Optional[str] = Query(None, description="Filter by guard action ('allow', 'block', 'sanitize')")
) -> Dict[str, Any]:
    """Retrieve recent attack and defense audit records with optional filtering."""
    logs = db.get_recent_logs(limit=limit, action_filter=action_filter)
    return {
        "total_returned": len(logs),
        "limit": limit,
        "action_filter": action_filter,
        "logs": logs
    }

@router.get("/logs/export")
async def export_logs(
    format: str = Query("csv", description="Export format ('csv' or 'json')")
) -> Response:
    """Download full security audit trail formatted as a CSV or JSON file."""
    fmt = format.lower().strip()
    if fmt == "json":
        json_content = db.export_logs_json()
        return Response(
            content=json_content,
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=security_audit_logs.json"}
        )
    csv_content = db.export_logs_csv()
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=security_audit_logs.csv"}
    )

@router.get("/agent/interactions")
async def get_agent_interactions(
    limit: int = Query(30, ge=1, le=200, description="Max chat interactions to return")
) -> Dict[str, Any]:
    """Retrieve recent chat interactions and tool execution telemetry from AI agent sandbox."""
    records = db.get_recent_agent_interactions(limit=limit)
    return {
        "total_returned": len(records),
        "interactions": records
    }
