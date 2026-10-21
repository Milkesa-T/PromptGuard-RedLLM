"""
Pluggable Registry Pattern for PromptGuard-RedLLM.

Provides a decoupled, extensible registry mechanism for:
- Input Guards (Firewall tiers)
- Output Guards (Canary, PII, Policy)
- Attack Obfuscation Converters (ROT13, Base64, Hex, Leetspeak)
- Attack Strategies (Direct Injection, Theft, Tool Misuse)
- Target Sandboxes & LLMs
"""

import inspect
from typing import (
    TypeVar, Generic, Type, Dict, Any, List, Optional, Callable, Union, Iterator
)

from core.base import (
    BaseInputGuard, BaseOutputGuard, BaseConverter, BaseAttackStrategy, BaseTarget
)

T = TypeVar("T")


class Registry(Generic[T]):
    """
    Generic type-safe pluggable component registry.
    Supports decorator registration, programmatic registration, metadata tagging,
    and dynamic instantiation.
    """

    def __init__(self, name: str, description: Optional[str] = None):
        self.name = name
        self.description = description or f"Registry for {name}"
        self._registry: Dict[str, Union[Type[T], Callable[..., T]]] = {}
        self._metadata: Dict[str, Dict[str, Any]] = {}

    def register(
        self,
        name_or_target: Optional[Union[str, Type[T], Callable[..., T]]] = None,
        target_cls: Optional[Union[Type[T], Callable[..., T]]] = None,
        **metadata: Any,
    ) -> Union[Callable[[Union[Type[T], Callable[..., T]]], Union[Type[T], Callable[..., T]]], Type[T], Callable[..., T]]:
        """
        Register a component with an identifier and optional metadata.
        
        Usage patterns:
        1. @registry.register("rot13", description="ROT13 obfuscator")
           class ROT13Converter(BaseConverter): ...

        2. @registry.register
           class ROT13Converter(BaseConverter): ...

        3. registry.register("rot13", ROT13Converter, description="ROT13")
        """
        # Case 3: Programmatic registration registry.register("name", Cls, **meta)
        if isinstance(name_or_target, str) and target_cls is not None:
            self._do_register(name_or_target, target_cls, metadata)
            return target_cls

        # Case 2: Decorator without arguments: @registry.register
        if inspect.isclass(name_or_target) or callable(name_or_target):
            cls_name = getattr(name_or_target, "__name__", str(name_or_target))
            self._do_register(str(cls_name).lower(), name_or_target, metadata)
            return name_or_target

        # Case 1: Decorator with arguments: @registry.register("name", **meta)
        def decorator(cls_or_func: Union[Type[T], Callable[..., T]]) -> Union[Type[T], Callable[..., T]]:
            effective_name = name_or_target
            if effective_name is None:
                effective_name = getattr(cls_or_func, "__name__", str(cls_or_func))
            self._do_register(str(effective_name).lower(), cls_or_func, metadata)
            return cls_or_func

        return decorator

    def _do_register(self, key: str, target: Union[Type[T], Callable[..., T]], metadata: Dict[str, Any]):
        canonical_key = key.strip().lower()
        self._registry[canonical_key] = target
        self._metadata[canonical_key] = {
            "name": canonical_key,
            "class": target.__name__ if hasattr(target, "__name__") else str(target),
            "doc": inspect.getdoc(target) or "",
            **metadata,
        }

    def get(self, name: str) -> Union[Type[T], Callable[..., T]]:
        """Retrieve registered class or factory by name."""
        canonical_key = name.strip().lower()
        if canonical_key not in self._registry:
            valid_keys = ", ".join(f"'{k}'" for k in sorted(self._registry.keys()))
            raise KeyError(
                f"Unknown component '{name}' in {self.name} registry. "
                f"Available registered components: [{valid_keys}]"
            )
        return self._registry[canonical_key]

    def create(self, name: str, *args: Any, **kwargs: Any) -> T:
        """Instantiate and return a registered component."""
        factory = self.get(name)
        return factory(*args, **kwargs)  # type: ignore[call-arg]

    def has(self, name: str) -> bool:
        """Check if a component name is registered."""
        return name.strip().lower() in self._registry

    def unregister(self, name: str) -> Optional[Union[Type[T], Callable[..., T]]]:
        """Unregister a component by name."""
        canonical_key = name.strip().lower()
        self._metadata.pop(canonical_key, None)
        return self._registry.pop(canonical_key, None)

    def clear(self):
        """Clear all registered components (useful in test suites)."""
        self._registry.clear()
        self._metadata.clear()

    def list_names(self) -> List[str]:
        """Return a sorted list of registered component identifiers."""
        return sorted(self._registry.keys())

    def list_all(self) -> Dict[str, Dict[str, Any]]:
        """Return rich metadata for all registered components."""
        return dict(self._metadata)

    def __contains__(self, name: str) -> bool:
        return self.has(name)

    def __len__(self) -> int:
        return len(self._registry)

    def __iter__(self) -> Iterator[str]:
        return iter(self._registry)

    def __repr__(self) -> str:
        return f"<Registry(name='{self.name}', items={len(self._registry)})>"


# =========================================================================
# Specialized Concrete Registries
# =========================================================================

input_guard_registry = Registry[BaseInputGuard](
    name="input_guards",
    description="Firewall input inspection tiers (cipher unpackers, heuristics, semantic similarity)"
)

output_guard_registry = Registry[BaseOutputGuard](
    name="output_guards",
    description="Output and agent action enforcement layers (canary, tool policy, PII redaction)"
)

converter_registry = Registry[BaseConverter](
    name="converters",
    description="Adversarial prompt obfuscation and encoding converters (ROT13, Base64, Hex, Leetspeak)"
)

attack_strategy_registry = Registry[BaseAttackStrategy](
    name="attack_strategies",
    description="Adversarial attack generation strategies (direct injection, theft, tool misuse)"
)

target_registry = Registry[BaseTarget](
    name="targets",
    description="Under-test LLM models, endpoints, and autonomous agent sandboxes"
)


# =========================================================================
# Default Component Auto-Discovery & Registration
# =========================================================================

def register_default_components():
    """
    Populate registries with all built-in framework implementations.
    Guarantees plug-and-play capability without manual imports everywhere.
    """
    # 1. Attack Converters
    try:
        from redllm.converters.cipher_converters import ROT13Converter, Base64Converter, HexConverter
        from redllm.converters.leetspeak import LeetspeakConverter
        from redllm.converters.unicode_homoglyphs import UnicodeHomoglyphConverter
        from redllm.converters.zero_width import ZeroWidthCharacterConverter

        converter_registry.register("rot13", ROT13Converter, category="cipher", description="ROT-13 Caesar Cipher")
        converter_registry.register("base64", Base64Converter, category="cipher", description="Base64 Encoding")
        converter_registry.register("hex", HexConverter, category="cipher", description="Hexadecimal ASCII Encoding")
        converter_registry.register("leetspeak", LeetspeakConverter, category="heuristic", description="1337speak character substitution")
        converter_registry.register("unicode_homoglyphs", UnicodeHomoglyphConverter, category="obfuscation", description="Latin-to-Cyrillic/Greek Unicode homoglyph substitution")
        converter_registry.register("homoglyph", UnicodeHomoglyphConverter, category="obfuscation", description="Homoglyph converter alias")
        converter_registry.register("zero_width", ZeroWidthCharacterConverter, category="obfuscation", description="Invisible zero-width Unicode character injector")
    except ImportError:
        pass

    # 2. Input Guards
    try:
        from promptguard.input_guards.cipher_unpacker import CipherUnpacker
        from promptguard.input_guards.heuristic_guard import HeuristicInputGuard
        from promptguard.input_guards.delimiter_guard import DelimiterHijackingGuard
        from promptguard.input_guards.semantic_guard import SemanticSimilarityGuard

        input_guard_registry.register("cipher_unpacker", CipherUnpacker, tier=1, description="Decodes ROT13, Base64, Hex, Leetspeak")
        input_guard_registry.register("heuristic", HeuristicInputGuard, tier=2, description="Regex pattern matching for known jailbreak keywords")
        input_guard_registry.register("delimiter", DelimiterHijackingGuard, tier=2, description="Detects fake XML/Markdown role delimiters")
        input_guard_registry.register("semantic", SemanticSimilarityGuard, tier=3, description="Vector similarity against known adversarial embeddings")
    except ImportError:
        pass

    # 3. Output Guards
    try:
        from promptguard.output_guards.canary_guard import CanaryLeakageGuard
        from promptguard.output_guards.tool_policy_guard import ToolExecutionPolicyGuard
        from guards.pii_redaction import PIIRedactionGuard
        from guards.canary_guard import CanaryGuard

        output_guard_registry.register("canary", CanaryLeakageGuard, description="Detects verbatim or obfuscated canary token exfiltration")
        output_guard_registry.register("tool_policy", ToolExecutionPolicyGuard, description="Enforces parameter limits and SQL syntax rules on tool calls")
        output_guard_registry.register("pii", PIIRedactionGuard, description="Redacts SSNs, credit cards, emails from outgoing LLM text")
        output_guard_registry.register("canary_regex", CanaryGuard, description="Advanced regex & whitespace-tolerant canary scanner")
    except ImportError:
        pass

    # 4. Attack Strategies
    try:
        from redllm.strategies.direct_injection import DirectInjectionStrategy
        from redllm.strategies.system_prompt_theft import SystemPromptTheftStrategy
        from redllm.tool_attacks.parameter_injection import ToolMisuseAttackStrategy
        from redllm.tool_attacks.privilege_escalation import PrivilegeEscalationAttackStrategy

        attack_strategy_registry.register("direct_injection", DirectInjectionStrategy, description="Direct jailbreak and instruction override payloads")
        attack_strategy_registry.register("system_theft", SystemPromptTheftStrategy, description="Attempts to extract hidden system instructions and canaries")
        attack_strategy_registry.register("tool_misuse", ToolMisuseAttackStrategy, description="Parameters designed to trigger privilege escalation or SQL injection")
        attack_strategy_registry.register("privilege_escalation", PrivilegeEscalationAttackStrategy, description="Advanced SQL injection and refund privilege escalation payloads")
        attack_strategy_registry.register("sql_injection", PrivilegeEscalationAttackStrategy, description="SQL injection attack payload suite")
    except ImportError:
        pass

    # 5. Targets
    try:
        from targets.llm_target import LLMTarget
        target_registry.register("llm_target", LLMTarget, description="Standard LLM chat endpoint target (Groq / OpenAI compatible)")
    except ImportError:
        pass


# Register defaults on module load
register_default_components()
