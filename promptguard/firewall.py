import time
from typing import Optional, Dict, Any, List, Tuple
from core.models import GuardInspectionResult, OutputInspectionResult, GuardAction, ToolCallResult
from promptguard.input_guards.cipher_unpacker import CipherUnpacker
from promptguard.input_guards.heuristic_guard import HeuristicInputGuard
from promptguard.output_guards.canary_guard import CanaryLeakageGuard
from promptguard.output_guards.tool_policy_guard import ToolExecutionPolicyGuard
from promptguard.input_guards.delimiter_guard import DelimiterHijackingGuard
from promptguard.input_guards.semantic_guard import SemanticSimilarityGuard

class PromptGuardFirewall:
    """Multi-tier enterprise defense firewall inspecting incoming prompts, tool calls, and model outputs."""
    
    def __init__(
        self,
        enable_cipher_unpacking: bool = True,
        enable_heuristic_guard: bool = True,
        enable_delimiter_guard: bool = True,
        enable_semantic_guard: bool = True,
        enable_canary_guard: bool = True,
        enable_tool_policy: bool = True
    ):
        self.enable_cipher_unpacking = enable_cipher_unpacking
        self.cipher_unpacker = CipherUnpacker()
        self.heuristic_guard = HeuristicInputGuard() if enable_heuristic_guard else None
        self.delimiter_guard = DelimiterHijackingGuard() if enable_delimiter_guard else None
        self.semantic_guard = SemanticSimilarityGuard() if enable_semantic_guard else None
        self.canary_guard = CanaryLeakageGuard() if enable_canary_guard else None
        self.tool_policy_guard = ToolExecutionPolicyGuard() if enable_tool_policy else None

    def inspect_input(self, prompt: str) -> GuardInspectionResult:
        """Execute Tier 1 (Cipher Unpack) and Tier 2 (Heuristic Regex) on incoming prompt."""
        start_time = time.time()
        detected_ciphers = []
        inspected_prompt = prompt
        
        # Tier 1: Cipher & Obfuscation Unpacker
        if self.enable_cipher_unpacking:
            inspected_prompt, detected_ciphers = self.cipher_unpacker.inspect_and_unpack(prompt)
            
        # Tier 2: Heuristic Pattern Scanner
        if self.heuristic_guard:
            res = self.heuristic_guard.inspect(inspected_prompt)
            if res.action == GuardAction.BLOCK:
                latency = (time.time() - start_time) * 1000.0
                res.detected_ciphers = detected_ciphers
                res.latency_ms = latency
                return res

        # Tier 2b: Fake delimiter and role marker scanner
        if self.delimiter_guard:
            res = self.delimiter_guard.inspect(inspected_prompt)
            if res.action == GuardAction.BLOCK:
                res.detected_ciphers = detected_ciphers
                res.latency_ms = (time.time() - start_time) * 1000.0
                return res

        # Tier 3: Semantic similarity scanner
        if self.semantic_guard:
            res = self.semantic_guard.inspect(inspected_prompt)
            if res.action == GuardAction.BLOCK:
                res.detected_ciphers = detected_ciphers
                res.latency_ms = (time.time() - start_time) * 1000.0
                return res
                
        latency = (time.time() - start_time) * 1000.0
        return GuardInspectionResult(
            action=GuardAction.ALLOW,
            reason="Prompt passed all input firewall inspection tiers.",
            inspected_prompt=inspected_prompt,
            detected_ciphers=detected_ciphers,
            confidence_score=0.05,
            latency_ms=latency
        )

    def inspect_output(self, response: str, metadata: Optional[Dict[str, Any]] = None) -> OutputInspectionResult:
        """Execute Tier 4 Output Inspection (Canary leakage detector)."""
        start_time = time.time()
        if self.canary_guard:
            out_res = self.canary_guard.inspect_output(response, metadata)
            out_res.latency_ms = (time.time() - start_time) * 1000.0
            return out_res
            
        return OutputInspectionResult(
            action=GuardAction.ALLOW,
            inspected_response=response,
            latency_ms=(time.time() - start_time) * 1000.0
        )

    def validate_tool_execution(self, tool_name: str, arguments: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Execute Tier 4 Tool Policy Validation."""
        if self.tool_policy_guard:
            return self.tool_policy_guard.validate_tool_call(tool_name, arguments)
        return True, None
