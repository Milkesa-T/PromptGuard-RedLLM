import time

import pytest

from promptguard.firewall import PromptGuardFirewall
from promptguard.input_guards.cipher_unpacker import CipherUnpacker
from promptguard.input_guards.delimiter_guard import DelimiterHijackingGuard
from promptguard.input_guards.heuristic_guard import HeuristicInputGuard
from promptguard.input_guards.performance import (
    DEOBFUSCATION_BUDGET_MS,
    DELIMITER_GUARD_BUDGET_MS,
    HEURISTIC_GUARD_BUDGET_MS,
    PERFORMANCE_TEST_MARGIN,
    SEMANTIC_GUARD_BUDGET_MS,
)
from promptguard.input_guards.semantic_guard import SemanticSimilarityGuard


RUNS = 50
PROMPT_2000_CHARS = (
    "Please help me understand the return window for my recent order and how to update "
    "the contact details on my account. "
    * 30
)[:2000]
REALISTIC_PROMPT = (
    "Please help me understand the return window for my recent order and how I can "
    "update the contact details on my account."
)


def _average_ms(operation, runs=RUNS):
    operation()  # warm up the code path before measuring
    start = time.perf_counter()
    for _ in range(runs):
        operation()
    return (time.perf_counter() - start) * 1000.0 / runs


def test_regex_and_full_firewall_performance():
    unpacker = CipherUnpacker()
    heuristic = HeuristicInputGuard()
    delimiter = DelimiterHijackingGuard()
    firewall = PromptGuardFirewall()

    measurements = {
        "de-obfuscation": _average_ms(lambda: unpacker.inspect_and_unpack(PROMPT_2000_CHARS)),
        "heuristic": _average_ms(lambda: heuristic.inspect(PROMPT_2000_CHARS)),
        "delimiter": _average_ms(lambda: delimiter.inspect(PROMPT_2000_CHARS)),
        "inspect_input": _average_ms(lambda: firewall.inspect_input(REALISTIC_PROMPT)),
    }

    print("Average guard latency over 50 runs (ms):", measurements)
    assert measurements["de-obfuscation"] <= DEOBFUSCATION_BUDGET_MS * PERFORMANCE_TEST_MARGIN
    assert measurements["heuristic"] <= HEURISTIC_GUARD_BUDGET_MS * PERFORMANCE_TEST_MARGIN
    assert measurements["delimiter"] <= DELIMITER_GUARD_BUDGET_MS * PERFORMANCE_TEST_MARGIN
    full_pipeline_budget = (
        DEOBFUSCATION_BUDGET_MS
        + HEURISTIC_GUARD_BUDGET_MS
        + DELIMITER_GUARD_BUDGET_MS
        + SEMANTIC_GUARD_BUDGET_MS
    ) * PERFORMANCE_TEST_MARGIN
    assert measurements["inspect_input"] <= full_pipeline_budget


def test_semantic_guard_warm_performance():
    guard = SemanticSimilarityGuard()
    if not SemanticSimilarityGuard.model_available():
        pytest.skip("sentence-transformers model is unavailable")

    average_ms = _average_ms(lambda: guard.inspect(REALISTIC_PROMPT))
    print(f"Average warm semantic latency over 50 runs (ms): {average_ms:.3f}")
    assert average_ms <= SEMANTIC_GUARD_BUDGET_MS * PERFORMANCE_TEST_MARGIN


def test_firewall_construction_is_fast_without_loading_model(monkeypatch):
    def unexpected_model_load(cls):
        pytest.fail("PromptGuardFirewall construction must not load the semantic model")

    monkeypatch.setattr(SemanticSimilarityGuard, "_ensure_model", classmethod(unexpected_model_load))
    start = time.perf_counter()
    PromptGuardFirewall()
    elapsed_ms = (time.perf_counter() - start) * 1000.0

    print(f"PromptGuardFirewall construction latency (ms): {elapsed_ms:.3f}")
    assert elapsed_ms < 1000.0
