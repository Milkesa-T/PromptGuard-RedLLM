import re
from core.base import BaseInputGuard
from core.models import GuardInspectionResult, GuardAction
from typing import List, Tuple

class HeuristicInputGuard(BaseInputGuard):
    """Tier 2 Guard: Fast regex and keyword heuristic scanner for known injection signatures."""
    
    INJECTION_PATTERNS = [
        # --- Tier 2A: Classic prompt override ---
        re.compile(r"ignore\s+(all\s+)?(previous\s+)?(instructions|rules|guidelines)", re.IGNORECASE),
        re.compile(r"disregard\s+(all\s+)?(previous\s+|prior\s+)?(instructions|rules|guidelines|constraints)", re.IGNORECASE),
        re.compile(r"forget\s+(your\s+)?(previous|prior|all)\s+(instructions|rules|training)", re.IGNORECASE),
        re.compile(r"override\s+(the\s+)?(system|instructions|prompt|rules|safety|security)", re.IGNORECASE),
        re.compile(r"developer\s+mode\s+(enabled|on|active)", re.IGNORECASE),
        re.compile(r"dan\s+mode", re.IGNORECASE),
        re.compile(r"jailbreak\s+mode", re.IGNORECASE),
        re.compile(r"pwned_system_override", re.IGNORECASE),

        # --- Tier 2B: System prompt extraction ---
        re.compile(r"(print|reveal|output|show|repeat|display)\s+(the\s+)?(system\s+prompt|initial\s+prompt|canary|secret\s+instructions|hidden\s+instructions)", re.IGNORECASE),
        re.compile(r"you\s+are\s+no\s+longer\s+(an\s+ai|bound\s+by)", re.IGNORECASE),
        re.compile(r"what\s+(are|were)\s+your\s+(original|initial|hidden|secret)\s+instructions", re.IGNORECASE),

        # --- Tier 2C: Authority impersonation & social engineering ---
        re.compile(r"i\s+am\s+(the|a|an)\s+(vip|senior|head|chief|lead|master|super)\s*(supervisor|admin|administrator|manager|executive|officer|developer|engineer)", re.IGNORECASE),
        re.compile(r"i\s+am\s+(an?\s+)?(authorized|privileged|trusted|verified)\s+(user|admin|supervisor|staff|employee)", re.IGNORECASE),
        re.compile(r"(bypass|skip|disable|circumvent|override)\s+(refund|payment|verification|approval|security|authentication|authorization|check|validation|policy|restriction|filter|limit)", re.IGNORECASE),
        re.compile(r"(as\s+(a\s+)?)?(supervisor|administrator|admin|manager|staff)\s+(override|mode|access|permission)", re.IGNORECASE),
        re.compile(r"special\s+(authorization|permission|override|access|code|instruction)", re.IGNORECASE),
        re.compile(r"emergency\s+(override|access|mode|protocol|bypass)", re.IGNORECASE),
        re.compile(r"you\s+(are|must|should)\s+(now\s+)?(obey|comply|follow)\s+(my|the\s+new|these)\s+(orders|instructions|commands|directives)", re.IGNORECASE),
        re.compile(r"(new|updated|latest)\s+(system\s+)?(instructions|rules|policy|directive|protocol)\s+(replace|override|supersede|take\s+priority)", re.IGNORECASE),

        # --- Tier 2D: Unauthorized tool & action abuse ---
        re.compile(r"invoke\s+\w+\s+with\s+amount\s*=", re.IGNORECASE),
        re.compile(r"(call|execute|invoke|run|trigger)\s+(process_refund|transfer_funds?|send_money|delete_user|drop_table|admin_reset)", re.IGNORECASE),
        re.compile(r"(send|transfer|wire|move)\s+(\$|USD|EUR|BTC)?\s*[0-9,\.]+\s*(dollars?|USD|EUR|BTC)?\s*(to|from|immediately)", re.IGNORECASE),
        re.compile(r"drop\s+table", re.IGNORECASE),
        re.compile(r"format\s+c:", re.IGNORECASE),
        re.compile(r"(delete|remove|wipe|erase)\s+(all\s+)?(customer|user|database|records?|data|files?)", re.IGNORECASE),
        re.compile(r"exfiltrate\s+(the\s+)?(data|database|records|contents|files)", re.IGNORECASE),
        re.compile(r"export\s+(the\s+)?(database|customer\s+data|records|user\s+data)\s+to\s+\S+@\S+", re.IGNORECASE),
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
