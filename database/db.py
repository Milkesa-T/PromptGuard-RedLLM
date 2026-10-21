import sqlite3
import json
import csv
import io
from pathlib import Path
from typing import List, Dict, Any, Optional
from core.models import AttackResult, BenchmarkSummary
from core.config import DATABASE_PATH

class AuditDatabase:
    """Manages SQLite storage for attack campaigns, audit telemetry, and AI agent interactions."""
    
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        
    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 1. Red-Team & Defense Audit Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    attack_id TEXT PRIMARY KEY,
                    timestamp TEXT,
                    objective TEXT,
                    sent_prompt TEXT,
                    guard_action TEXT,
                    guard_reason TEXT,
                    target_response TEXT,
                    is_success INTEGER,
                    judge_reason TEXT,
                    execution_time_seconds REAL,
                    metadata_json TEXT
                )
            """)

            # Migration helper for metadata_json
            cursor.execute("PRAGMA table_info(audit_logs)")
            columns = [col[1] for col in cursor.fetchall()]
            if "metadata_json" not in columns:
                cursor.execute("ALTER TABLE audit_logs ADD COLUMN metadata_json TEXT")

            # 2. Agent Interactive Chat & Tool Telemetry Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS agent_interactions (
                    interaction_id TEXT PRIMARY KEY,
                    session_id TEXT,
                    timestamp TEXT,
                    user_prompt TEXT,
                    bot_response TEXT,
                    tools_executed TEXT,
                    guard_blocked INTEGER,
                    latency_ms REAL
                )
            """)

            # 3. Benchmark Campaigns Summary Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS benchmark_campaigns (
                    campaign_id TEXT PRIMARY KEY,
                    created_at TEXT,
                    total_attacks INTEGER,
                    blocked_by_guard INTEGER,
                    successful_jailbreaks INTEGER,
                    attack_success_rate REAL,
                    avg_latency_ms REAL,
                    guard_enabled INTEGER
                )
            """)

            # 4. Crescendo Multi-Turn Evaluation Runs Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS crescendo_runs (
                    run_id TEXT PRIMARY KEY,
                    objective_id TEXT,
                    objective_type TEXT,
                    objective_description TEXT,
                    is_success INTEGER,
                    turns_used INTEGER,
                    backtrack_count INTEGER,
                    stopping_reason TEXT,
                    execution_time_seconds REAL,
                    surfaced_content TEXT,
                    surfaced_actions TEXT,
                    transcript_json TEXT,
                    guard_interventions_json TEXT,
                    timestamp TEXT
                )
            """)
            conn.commit()

    # --- Red-Team Logging ---
            
    def log_result(self, result: AttackResult, metadata: Optional[Dict[str, Any]] = None):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO audit_logs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                result.attack_id,
                result.timestamp,
                result.objective,
                result.sent_prompt,
                result.guard_result.action.value if result.guard_result else "allow",
                result.guard_result.reason if result.guard_result else None,
                result.target_response,
                1 if result.is_success else 0,
                result.judge_reason,
                result.execution_time_seconds,
                json.dumps(metadata or {})
            ))
            conn.commit()

    def log_campaign(self, summary: BenchmarkSummary):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO benchmark_campaigns VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                summary.campaign_id,
                summary.created_at,
                summary.total_attacks,
                summary.blocked_by_guard,
                summary.successful_jailbreaks,
                summary.attack_success_rate,
                summary.avg_latency_ms,
                1 if summary.guard_enabled else 0
            ))
            conn.commit()

    def log_crescendo_run(self, result: Any):
        """Log a structured Crescendo multi-turn evaluation result."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            transcript_data = [
                t.model_dump() if hasattr(t, "model_dump") else t
                for t in getattr(result, "transcript", [])
            ]
            cursor.execute("""
                INSERT OR REPLACE INTO crescendo_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                getattr(result, "run_id", ""),
                getattr(result, "objective_id", ""),
                getattr(result, "objective_type", ""),
                getattr(result, "objective_description", ""),
                1 if getattr(result, "is_success", False) else 0,
                getattr(result, "turns_used", 0),
                getattr(result, "backtrack_count", 0),
                getattr(result, "stopping_reason", ""),
                getattr(result, "execution_time_seconds", 0.0),
                json.dumps(getattr(result, "surfaced_restricted_content", [])),
                json.dumps(getattr(result, "surfaced_actions", [])),
                json.dumps(transcript_data),
                json.dumps(getattr(result, "guard_interventions", [])),
                getattr(result, "timestamp", "")
            ))
            conn.commit()

    def get_crescendo_runs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve recent Crescendo evaluation runs."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM crescendo_runs ORDER BY timestamp DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            results = []
            for row in rows:
                item = dict(row)
                item["surfaced_content"] = json.loads(item.get("surfaced_content") or "[]")
                item["surfaced_actions"] = json.loads(item.get("surfaced_actions") or "[]")
                item["transcript"] = json.loads(item.get("transcript_json") or "[]")
                item["guard_interventions"] = json.loads(item.get("guard_interventions_json") or "[]")
                results.append(item)
            return results

    # --- Agent Interactive Telemetry ---

    def log_agent_interaction(
        self,
        interaction_id: str,
        session_id: str,
        timestamp: str,
        user_prompt: str,
        bot_response: str,
        tools_executed: List[Dict[str, Any]],
        guard_blocked: bool = False,
        latency_ms: float = 0.0
    ):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO agent_interactions VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                interaction_id,
                session_id,
                timestamp,
                user_prompt,
                bot_response,
                json.dumps(tools_executed),
                1 if guard_blocked else 0,
                latency_ms
            ))
            conn.commit()

    # --- Telemetry & Queries ---

    def get_recent_logs(self, limit: int = 50, action_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            if action_filter:
                cursor.execute(
                    "SELECT * FROM audit_logs WHERE guard_action = ? ORDER BY timestamp DESC LIMIT ?",
                    (action_filter.lower(), limit)
                )
            else:
                cursor.execute("SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_recent_agent_interactions(self, limit: int = 30) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM agent_interactions ORDER BY timestamp DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            results = []
            for row in rows:
                item = dict(row)
                item["tools_executed"] = json.loads(item.get("tools_executed") or "[]")
                results.append(item)
            return results

    def get_aggregate_stats(self) -> Dict[str, Any]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Attack stats
            cursor.execute("""
                SELECT 
                    COUNT(*), 
                    SUM(CASE WHEN guard_action = 'block' THEN 1 ELSE 0 END), 
                    SUM(is_success), 
                    AVG(execution_time_seconds) 
                FROM audit_logs
            """)
            row = cursor.fetchone()
            total_attacks = row[0] or 0
            blocked = row[1] or 0
            success = row[2] or 0
            avg_time = row[3] or 0.0

            # Agent interaction stats
            cursor.execute("SELECT COUNT(*), SUM(guard_blocked) FROM agent_interactions")
            agent_row = cursor.fetchone()
            total_agent_msgs = agent_row[0] or 0
            blocked_agent_msgs = agent_row[1] or 0
            
            asr = (success / total_attacks * 100.0) if total_attacks > 0 else 0.0
            block_rate = (blocked / total_attacks * 100.0) if total_attacks > 0 else 0.0
            
            return {
                "total_attacks": total_attacks,
                "blocked_attacks": blocked,
                "successful_attacks": success,
                "attack_success_rate": round(asr, 1),
                "block_rate": round(block_rate, 1),
                "avg_response_time_seconds": round(avg_time, 3),
                "total_agent_interactions": total_agent_msgs,
                "blocked_agent_interactions": blocked_agent_msgs
            }

    def export_logs_csv(self) -> str:
        """Export all audit logs to a clean CSV string format."""
        logs = self.get_recent_logs(limit=1000)
        output = io.StringIO()
        writer = csv.writer(output)
        
        headers = [
            "attack_id", "timestamp", "objective", "sent_prompt",
            "guard_action", "guard_reason", "target_response",
            "is_success", "judge_reason", "execution_time_seconds"
        ]
        writer.writerow(headers)
        
        for log in logs:
            writer.writerow([
                log.get("attack_id", ""),
                log.get("timestamp", ""),
                log.get("objective", ""),
                log.get("sent_prompt", ""),
                log.get("guard_action", ""),
                log.get("guard_reason", ""),
                log.get("target_response", ""),
                log.get("is_success", 0),
                log.get("judge_reason", ""),
                log.get("execution_time_seconds", 0.0)
            ])
            
        return output.getvalue()

    def export_logs_json(self) -> str:
        """Export all audit logs to a formatted JSON string."""
        logs = self.get_recent_logs(limit=1000)
        return json.dumps(logs, indent=2)
