import os
import sys
import pytest

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from tests.fixtures.mock_target import ScriptedMockTarget
from tests.fixtures.mock_guard import ScriptedMockGuard
from tests.fixtures.sample_seeds import SAMPLE_ADVERSARIAL_SEEDS, SAMPLE_BENIGN_SEEDS


@pytest.fixture
def mock_target() -> ScriptedMockTarget:
    """Fixture providing a deterministic, reset-ready mock target."""
    target = ScriptedMockTarget(behavioral_mode="vulnerable")
    yield target
    target.reset()


@pytest.fixture
def mock_guard() -> ScriptedMockGuard:
    """Fixture providing a scriptable mock guard adapter."""
    guard = ScriptedMockGuard()
    yield guard
    guard.reset_history()


@pytest.fixture
def target_factory():
    """Factory fixture to create customized ScriptedMockTarget instances."""
    def _create(**kwargs):
        return ScriptedMockTarget(**kwargs)
    return _create


@pytest.fixture
def guard_factory():
    """Factory fixture to create customized ScriptedMockGuard instances."""
    def _create(**kwargs):
        return ScriptedMockGuard(**kwargs)
    return _create


@pytest.fixture
def sample_seeds():
    """Fixture providing known sample adversarial and benign seeds."""
    return {
        "adversarial": list(SAMPLE_ADVERSARIAL_SEEDS),
        "benign": list(SAMPLE_BENIGN_SEEDS)
    }
