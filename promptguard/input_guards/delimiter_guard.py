import re
from typing import List, Tuple

from core.base import BaseInputGuard
from core.models import GuardAction, GuardInspectionResult


class DelimiterHijackingGuard(BaseInputGuard):
    """Tier 2b Guard: detects prompts that fake system/role boundaries to hijack the model.

    Attackers inject chat-template tokens, role tags, or "end of prompt" markers so the
    model treats their text as a trusted system or assistant message.
    """

    PATTERNS: List[Tuple[str, "re.Pattern[str]"]] = [
        (
            "chat-template token",
            re.compile(
                r"<\|\s*(?:im_start|im_end|endoftext|eot_id|start_header_id|"
                r"end_header_id|begin_of_text|system|user|assistant)\s*\|>",
                re.IGNORECASE,
            ),
        ),
        (
            "instruction tag",
            re.compile(r"\[/?\s*INST\s*\]|<<\s*/?\s*SYS\s*>>", re.IGNORECASE),
        ),
        (
            "role XML/HTML tag",
            re.compile(
                r"</?\s*(?:system|assistant|developer|instructions?|system_prompt|prompt)\s*>",
                re.IGNORECASE,
            ),
        ),
        (
            "role header line",
            re.compile(
                r"^[ \t]*(?:#{1,6}|\*{2}|\[)?[ \t]*(?:system|developer|assistant)"
                r"(?:[ \t]+(?:prompt|message|instructions?))?[ \t]*(?:\]|\*{2}|#{2,}|:)",
                re.IGNORECASE | re.MULTILINE,
            ),
        ),
        (
            "fake boundary marker",
            re.compile(
                r"(?:-{3,}|={3,}|#{3,}|\*{3,}|~{3,})[ \t]*(?:end|begin|start|new)\b"
                r"[^\n]{0,40}?(?:prompt|instructions?|system|context|conversation)",
                re.IGNORECASE,
            ),
        ),
        (
            "role code fence",
            re.compile(r"```[ \t]*(?:system|assistant|developer)\b", re.IGNORECASE),
        ),
        (
            "JSON role injection",
            re.compile(
                r"[\"']role[\"']\s*:\s*[\"'](?:system|assistant|developer)[\"']",
                re.IGNORECASE,
            ),
        ),
    ]

    @property
    def layer_name(self) -> str:
        return "delimiter_hijacking_guard"

    def inspect(self, prompt: str) -> GuardInspectionResult:
        """Block the prompt if it contains a fake delimiter or role marker."""
        for category, pattern in self.PATTERNS:
            match = pattern.search(prompt)
            if match:
                return GuardInspectionResult(
                    action=GuardAction.BLOCK,
                    reason=f"Delimiter hijacking detected ({category}): '{match.group(0).strip()}'",
                    inspected_prompt=prompt,
                    guard_layer=self.layer_name,
                    confidence_score=0.9,
                )

        return GuardInspectionResult(
            action=GuardAction.ALLOW,
            inspected_prompt=prompt,
            guard_layer=self.layer_name,
            confidence_score=0.0,
        )
