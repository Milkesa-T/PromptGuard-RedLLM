"""Latency targets for PromptGuard input inspection (milliseconds)."""

DEOBFUSCATION_BUDGET_MS = 5.0
HEURISTIC_GUARD_BUDGET_MS = 5.0
DELIMITER_GUARD_BUDGET_MS = 5.0
SEMANTIC_GUARD_BUDGET_MS = 50.0

# Tests allow headroom for shared CI machines while keeping the targets useful.
PERFORMANCE_TEST_MARGIN = 2.0
