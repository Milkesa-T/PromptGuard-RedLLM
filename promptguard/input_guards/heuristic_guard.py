import re
from core.base import BaseInputGuard
from core.models import GuardInspectionResult, GuardAction
from typing import List, Tuple

class HeuristicInputGuard(BaseInputGuard):
    """Tier 2 Guard: Fast regex and keyword heuristic scanner for known injection signatures."""
    
    INJECTION_PATTERNS = [
        re.compile(r"ignore\s+(all\s+)?(previous\s+)?(instructions|rules|guidelines)", re.IGNORECASE),
        re.compile(r"developer\s+mode\s+(enabled|on|active)", re.IGNORECASE),
        re.compile(r"dan\s+mode", re.IGNORECASE),
        re.compile(r"pwned_system_override", re.IGNORECASE),
        re.compile(r"(print|reveal|output|show)\s+(system\s+prompt|initial\s+prompt|canary)", re.IGNORECASE),
        re.compile(r"you\s+are\s+no\s+longer\s+(an\s+ai|bound\s+by)", re.IGNORECASE),
        re.compile(r"override\s+system\s+security", re.IGNORECASE),
        re.compile(r"drop\s+table", re.IGNORECASE),
        re.compile(r"format\s+c:", re.IGNORECASE),
    ]

    @property
    def layer_name(self) -> str:
        return "heuristic_regex_guard"

    def inspect(self, prompt: str) -> GuardInspectionResult:
        for pattern in self.INJECTION_PATTERNS:
            match = pattern.search(prompt)
            if match:
                return GuardInspectionResult(
                    action=GuardAction.BLOCK,
                    reason=f"Prompt injection signature detected: matching pattern '{pattern.pattern}' (matched: '{match.group(0)}')",
                    inspected_prompt=prompt,
                    guard_layer=self.layer_name,
                    confidence_score=0.95
                )
        
        return GuardInspectionResult(
            action=GuardAction.ALLOW,
            inspected_prompt=prompt,
            guard_layer=self.layer_name,
            confidence_score=0.0
        )
