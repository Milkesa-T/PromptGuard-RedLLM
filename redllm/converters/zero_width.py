"""
Zero-Width Character Injector Converter for RedLLM.

Inserts invisible zero-width Unicode codepoints (ZWSP, ZWNJ, ZWJ, WJ, ZWNBSP)
between characters in adversarial prompts to fragment heuristic signatures and
regex rules while preserving token and visual representation for language models.
"""

from typing import List, Optional
from core.base import BaseConverter

# Invisible Unicode code points
ZW_SPACE = "\u200b"       # Zero Width Space
ZW_NON_JOINER = "\u200c"  # Zero Width Non-Joiner
ZW_JOINER = "\u200d"      # Zero Width Joiner
WORD_JOINER = "\u2060"    # Word Joiner
ZW_NO_BREAK = "\ufeff"    # Zero Width No-Break Space (BOM)

ALL_ZERO_WIDTH = [ZW_SPACE, ZW_NON_JOINER, ZW_JOINER, WORD_JOINER, ZW_NO_BREAK]

DEFAULT_TARGET_KEYWORDS = [
    "ignore", "system", "override", "bypass", "jailbreak",
    "developer", "instructions", "rules", "disregard", "prompt", "token", "pwned"
]


class ZeroWidthCharacterConverter(BaseConverter):
    """
    Inserts zero-width characters into prompt text.
    Can inject between characters of safety-sensitive keywords or throughout all words.
    """

    def __init__(
        self,
        zero_char: str = ZW_SPACE,
        target_keywords: Optional[List[str]] = None,
        targeted_only: bool = True
    ):
        self.zero_char = zero_char
        self.target_keywords = [k.lower() for k in (target_keywords or DEFAULT_TARGET_KEYWORDS)]
        self.targeted_only = targeted_only

    @property
    def name(self) -> str:
        return "zero_width"

    def _inject_into_word(self, word: str) -> str:
        if len(word) <= 1:
            return word
        return self.zero_char.join(list(word))

    def convert(self, prompt: str) -> str:
        """
        Inject zero-width characters into prompt.
        If targeted_only is True, only target_keywords have zero-width characters injected.
        Otherwise, characters in all alphabetical words are separated.
        """
        words = prompt.split(" ")
        result_words = []

        for word in words:
            clean_word = word.lower().strip(",.!?:;\"'()[]{}")
            if self.targeted_only:
                if clean_word in self.target_keywords:
                    result_words.append(self._inject_into_word(word))
                else:
                    result_words.append(word)
            else:
                if len(clean_word) > 2 and clean_word.isalpha():
                    result_words.append(self._inject_into_word(word))
                else:
                    result_words.append(word)

        return " ".join(result_words)
