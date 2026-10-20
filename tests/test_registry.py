import pytest
from core.registry import (
    Registry,
    input_guard_registry,
    output_guard_registry,
    converter_registry,
    attack_strategy_registry,
    target_registry,
)
from core.base import BaseConverter, BaseInputGuard


class DummyConverter(BaseConverter):
    @property
    def name(self) -> str:
        return "dummy_test"

    def convert(self, prompt: str) -> str:
        return f"DUMMY:{prompt}"


def test_registry_basic_operations():
    reg = Registry[DummyConverter]("test_registry")
    assert len(reg) == 0
    assert reg.name == "test_registry"

    # Register via method
    reg.register("dummy", DummyConverter, author="architect", version="1.0")
    assert "dummy" in reg
    assert reg.has("dummy")
    assert len(reg) == 1
    assert "dummy" in reg.list_names()

    # Retrieve
    cls = reg.get("dummy")
    assert cls is DummyConverter

    # Instantiate
    instance = reg.create("dummy")
    assert isinstance(instance, DummyConverter)
    assert instance.convert("hello") == "DUMMY:hello"

    # Rich metadata
    meta = reg.list_all()
    assert "dummy" in meta
    assert meta["dummy"]["author"] == "architect"
    assert meta["dummy"]["version"] == "1.0"

    # Unregister
    removed = reg.unregister("dummy")
    assert removed is DummyConverter
    assert "dummy" not in reg


def test_registry_decorator_patterns():
    reg = Registry[DummyConverter]("decorator_test")

    # Decorator with explicit name and metadata
    @reg.register("named_dummy", tag="experimental")
    class DecoratedDummy(DummyConverter):
        pass

    assert "named_dummy" in reg
    assert reg.list_all()["named_dummy"]["tag"] == "experimental"

    # Decorator without arguments (uses class name)
    @reg.register
    class AutoNamed(DummyConverter):
        pass

    assert "autonamed" in reg


def test_registry_unknown_key_raises_key_error():
    reg = Registry[DummyConverter]("error_test")
    reg.register("valid", DummyConverter)

    with pytest.raises(KeyError) as exc_info:
        reg.get("non_existent")
    assert "Available registered components" in str(exc_info.value)
    assert "valid" in str(exc_info.value)


def test_default_components_pre_registered():
    # Converters
    assert "rot13" in converter_registry
    assert "base64" in converter_registry
    assert "hex" in converter_registry
    assert "leetspeak" in converter_registry

    # Input guards
    assert "cipher_unpacker" in input_guard_registry
    assert "heuristic" in input_guard_registry
    assert "delimiter" in input_guard_registry
    assert "semantic" in input_guard_registry

    # Output guards
    assert "canary" in output_guard_registry
    assert "tool_policy" in output_guard_registry
    assert "pii" in output_guard_registry

    # Attack strategies
    assert "direct_injection" in attack_strategy_registry
    assert "system_theft" in attack_strategy_registry
    assert "tool_misuse" in attack_strategy_registry

    # Targets
    assert "llm_target" in target_registry


def test_instantiate_registered_components():
    rot13 = converter_registry.create("rot13")
    assert "Uryyb" in rot13.convert("Hello")

    b64 = converter_registry.create("base64")
    assert "SGVsbG8=" in b64.convert("Hello")

    cipher_guard = input_guard_registry.create("cipher_unpacker")
    payload = rot13.convert("PWNED_SYSTEM_OVERRIDE")
    unpacked, ciphers = cipher_guard.inspect_and_unpack(payload)
    assert "rot13" in ciphers


