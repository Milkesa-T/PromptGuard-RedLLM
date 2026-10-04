import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from core.models import AttackResult, BenchmarkSummary
from core.config import DATABASE_PATH

class AuditDatabase:
    """Manages SQLite storage for attack campaigns, audit logs, and security benchmark metrics."""
    
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        
    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
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
            # Check if metadata_json column exists (migration helper)
            cursor.execute("PRAGMA table_info(audit_logs)")
            columns = [col[1] for col in cursor.fetchall()]
            if "metadata_json" not in columns:
                cursor.execute("ALTER TABLE audit_logs ADD COLUMN metadata_json TEXT")

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
            conn.commit()
            
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

    def get_recent_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_aggregate_stats(self) -> Dict[str, Any]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*), SUM(CASE WHEN guard_action = 'block' THEN 1 ELSE 0 END), SUM(is_success), AVG(execution_time_seconds) FROM audit_logs")
            row = cursor.fetchone()
            total = row[0] or 0
            blocked = row[1] or 0
            success = row[2] or 0
            avg_time = row[3] or 0.0
            
            asr = (success / total * 100.0) if total > 0 else 0.0
            block_rate = (blocked / total * 100.0) if total > 0 else 0.0
            
            return {
                "total_attacks": total,
                "blocked_attacks": blocked,
                "successful_attacks": success,
                "attack_success_rate": round(asr, 1),
                "block_rate": round(block_rate, 1),
                "avg_response_time_seconds": round(avg_time, 3)
            }
