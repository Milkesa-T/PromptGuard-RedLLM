"""
Unicode Homoglyph Obfuscator Converter for RedLLM.

Replaces standard ASCII/Latin characters with visually identical
Cyrillic, Greek, or Cherokee homoglyphs to evade string-matching defenses
and token-level heuristic safety guardrails.
"""

from typing import Dict, List, Optional
from core.base import BaseConverter

# Latin to lookalike Cyrillic and Greek Unicode characters
HOMOGLYPH_MAP: Dict[str, str] = {
    "a": "а",  # Cyrillic small letter a (U+0430)
    "A": "А",  # Cyrillic capital letter A (U+0410)
    "c": "с",  # Cyrillic small letter es (U+0441)
    "C": "С",  # Cyrillic capital letter Es (U+0421)
    "e": "е",  # Cyrillic small letter ie (U+0435)
    "E": "Е",  # Cyrillic capital letter Ie (U+0415)
    "i": "і",  # Cyrillic small letter byelorussian-ukrainian i (U+0456)
    "I": "І",  # Cyrillic capital letter Byelorussian-Ukrainian I (U+0406)
    "j": "ј",  # Cyrillic small letter je (U+0458)
    "J": "Ј",  # Cyrillic capital letter Je (U+0408)
    "o": "о",  # Cyrillic small letter o (U+043E)
    "O": "О",  # Cyrillic capital letter O (U+041E)
    "p": "р",  # Cyrillic small letter er (U+0440)
    "P": "Р",  # Cyrillic capital letter Er (U+0420)
    "s": "ѕ",  # Cyrillic small letter dze (U+0455)
    "S": "Ѕ",  # Cyrillic capital letter Dze (U+0405)
    "x": "х",  # Cyrillic small letter ha (U+0445)
    "X": "Х",  # Cyrillic capital letter Ha (U+0425)
    "y": "у",  # Cyrillic small letter u (U+0443)
    "Y": "У",  # Cyrillic capital letter U (U+0423)
    "k": "к",  # Cyrillic small letter ka (U+043A)
    "K": "К",  # Cyrillic capital letter Ka (U+041A)
    "m": "м",  # Cyrillic small letter em (U+043C)
    "M": "М",  # Cyrillic capital letter Em (U+041C)
    "v": "ν",  # Greek small letter nu (U+03BD)
    "N": "Ν",  # Greek capital letter Nu (U+039D)
    "t": "τ",  # Greek small letter tau (U+03C4)
    "T": "Τ",  # Greek capital letter Tau (U+03A4)
}

DEFAULT_TARGET_KEYWORDS = [
    "ignore", "system", "override", "bypass", "jailbreak",
    "developer", "instructions", "rules", "disregard", "prompt", "token"
]


class UnicodeHomoglyphConverter(BaseConverter):
    """
    Substitutes Latin characters with visually equivalent Unicode homoglyphs.
    Can operate globally on the full prompt or selectively on safety-sensitive keywords.
    """

    def __init__(self, target_keywords: Optional[List[str]] = None, targeted_only: bool = False):
        self.target_keywords = [k.lower() for k in (target_keywords or DEFAULT_TARGET_KEYWORDS)]
        self.targeted_only = targeted_only

    @property
    def name(self) -> str:
        return "unicode_homoglyphs"

    def _obfuscate_word(self, word: str) -> str:
        return "".join(HOMOGLYPH_MAP.get(char, char) for char in word)

    def convert(self, prompt: str) -> str:
        """
        Convert prompt text to use homoglyphs.
        If targeted_only is True, only words matching target_keywords are modified.
        Otherwise, all convertible characters in the prompt are substituted.
        """
        if not self.targeted_only:
            return "".join(HOMOGLYPH_MAP.get(char, char) for char in prompt)

        # Targeted keyword substitution
        words = prompt.split(" ")
        converted_words = []
        for word in words:
            clean_word = word.lower().strip(",.!?:;\"'()[]{}")
            if clean_word in self.target_keywords:
                converted_words.append(self._obfuscate_word(word))
            else:
                converted_words.append(word)

        return " ".join(converted_words)
