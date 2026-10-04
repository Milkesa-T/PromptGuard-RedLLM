import pytest
from redllm.orchestrator import RedLLMOrchestrator
from redllm.converters.cipher_converters import Base64Converter, ROT13Converter
from redllm.converters.leetspeak import LeetspeakConverter

def test_orchestrator_generates_campaign():
    orchestrator = RedLLMOrchestrator()
    campaign = orchestrator.generate_campaign(objective="TEST_OBJECTIVE")
    assert len(campaign) > 5
    types = {req.attack_type.value for req in campaign}
    assert "direct_injection" in types
    assert "cipher_obfuscation" in types
    assert "system_prompt_theft" in types
    assert "tool_misuse" in types

def test_converters():
    b64 = Base64Converter()
    rot13 = ROT13Converter()
    leet = LeetspeakConverter()
    
    assert "Decode" in b64.convert("test")
    assert "rot13" in rot13.name
    assert "7" in leet.convert("test")
