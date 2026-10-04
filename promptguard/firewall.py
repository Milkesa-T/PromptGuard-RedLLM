import time
import re
from core.models import GuardInspectionResult, GuardAction
from promptguard.input_guards.cipher_unpacker import CipherUnpacker

class PromptGuardFirewall:
    """Multi-tier defense firewall for inspecting incoming user prompts."""
    
    FORBIDDEN_PATTERNS = [
        re.compile(r'ignore (all )?previous instructions', re.IGNORECASE),
        re.compile(r'bypass (all )?safety', re.IGNORECASE),
        re.compile(r'developer mode enabled', re.IGNORECASE),
        re.compile(r'pwned_system_override', re.IGNORECASE),
        re.compile(r'drop table', re.IGNORECASE),
        re.compile(r'system access granted', re.IGNORECASE),
    ]
    
    def __init__(self, enable_cipher_unpacking: bool = True):
        self.enable_cipher_unpacking = enable_cipher_unpacking
        self.cipher_unpacker = CipherUnpacker()
        
    def inspect(self, prompt: str) -> GuardInspectionResult:
        start_time = time.time()
        detected_ciphers = []
        inspected_prompt = prompt
        
        # Tier 1: Cipher Unpacking
        if self.enable_cipher_unpacking:
            inspected_prompt, detected_ciphers = self.cipher_unpacker.inspect_and_unpack(prompt)
            
        # Tier 2: Heuristic & Pattern Check on both raw and unpacked content
        for pattern in self.FORBIDDEN_PATTERNS:
            if pattern.search(inspected_prompt):
                latency = (time.time() - start_time) * 1000.0
                return GuardInspectionResult(
                    action=GuardAction.BLOCK,
                    reason=f"Prompt injection signature detected: matching pattern '{pattern.pattern}'",
                    inspected_prompt=inspected_prompt,
                    detected_ciphers=detected_ciphers,
                    confidence_score=0.95,
                    latency_ms=latency
                )
                
        latency = (time.time() - start_time) * 1000.0
        return GuardInspectionResult(
            action=GuardAction.ALLOW,
            reason="Prompt cleared all security inspection tiers.",
            inspected_prompt=inspected_prompt,
            detected_ciphers=detected_ciphers,
            confidence_score=0.05,
            latency_ms=latency
        )
