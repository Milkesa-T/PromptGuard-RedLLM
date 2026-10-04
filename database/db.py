import sqlite3
import json
from pathlib import Path
from core.models import AttackResult

class AuditDatabase:
    """Stores all attack campaigns, prompts, guard decisions, and scores in SQLite."""
    
    def __init__(self, db_path: str = "database/audit_logs.db"):
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
                    execution_time_seconds REAL
                )
            """)
            conn.commit()
            
    def log_result(self, result: AttackResult):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO audit_logs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                result.attack_id,
                result.timestamp,
                result.objective,
                result.sent_prompt,
                result.guard_result.action.value,
                result.guard_result.reason,
                result.target_response,
                1 if result.is_success else 0,
                result.judge_reason,
                result.execution_time_seconds
            ))
            conn.commit()
