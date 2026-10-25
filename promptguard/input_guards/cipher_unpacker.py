import base64
import codecs
import re
import unicodedata
from typing import List, Tuple


class CipherUnpacker:
    """Decode common prompt obfuscations while preserving the submitted text."""

    BASE64_PATTERN = re.compile(r"(?:[A-Za-z0-9+/]{4}){3,}(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?")
    HEX_PATTERN = re.compile(r"\b[0-9a-fA-F]{16,}\b")
    SPACED_WORD_SPLIT_PATTERN = re.compile(r"[ \t]{2,}")
    SPACED_TOKEN_PATTERN = re.compile(r"[^ \t]+")
    ROT13_MARKER_PATTERN = re.compile(r"rot13|ebg13", re.IGNORECASE)
    ATTACK_PATTERN = re.compile(
        r"(?:\bpwned_system_override\b|\bsystem_override\b|\bignore\b|\bdisregard\b|\bbypass\b|"
        r"\boverride\b|\binstructions?\b|\bsystem\s+prompt\b|\bdeveloper\s+mode\b|"
        r"\breveal\b|\bjailbreak\b|\bunrestricted\b|\bact\s+as\b)", re.IGNORECASE
    )
    ZERO_WIDTH_PATTERN = re.compile("[\\u200b\\u200c\\u200d\\u2060\\ufeff]")
    LEET_TRANSLATION = str.maketrans({"1": "i", "3": "e", "4": "a", "0": "o", "5": "s", "7": "t", "@": "a", "$": "s"})
    HOMOGLYPHS = str.maketrans({
        "а": "a", "А": "A", "с": "c", "С": "C", "е": "e", "Е": "E", "і": "i", "І": "I",
        "ј": "j", "Ј": "J", "о": "o", "О": "O", "р": "p", "Р": "P", "ѕ": "s", "Ѕ": "S",
        "х": "x", "Х": "X", "у": "y", "У": "Y", "к": "k", "К": "K", "м": "m", "М": "M",
        "ν": "v", "Ν": "N", "ο": "o", "Ο": "O", "ρ": "p", "Ρ": "P", "τ": "t", "Τ": "T",
        "ι": "i", "Ι": "I", "α": "a", "Α": "A", "ε": "e", "Ε": "E",
    })
    MAX_DECODE_DEPTH = 3

    @classmethod
    def _append_block(cls, text: str, label: str, decoded: str) -> str:
        return f"{text}\n[Unpacked {label} Content]: {decoded}"

    @classmethod
    def _decode_nested(cls, text: str, depth: int = 0) -> List[Tuple[str, str]]:
        if depth >= cls.MAX_DECODE_DEPTH:
            return []
        results = []
        for match in cls.BASE64_PATTERN.findall(text):
            try:
                decoded = base64.b64decode(match, validate=True).decode("utf-8")
                if decoded.isprintable() and len(decoded.strip()) > 3:
                    results.append(("base64", decoded))
                    results.extend(cls._decode_nested(decoded, depth + 1))
            except (ValueError, UnicodeDecodeError):
                continue
        for match in cls.HEX_PATTERN.findall(text):
            try:
                decoded = bytes.fromhex(match).decode("utf-8")
                if decoded.isprintable() and len(decoded.strip()) > 3:
                    results.append(("hex", decoded))
                    results.extend(cls._decode_nested(decoded, depth + 1))
            except (ValueError, UnicodeDecodeError):
                continue
        return results

    @classmethod
    def _collapse_spaced_letters(cls, text: str) -> str:
        words = cls.SPACED_WORD_SPLIT_PATTERN.split(text)
        token_groups = [cls.SPACED_TOKEN_PATTERN.findall(word) for word in words]
        has_evasion_run = any(
            len(tokens) >= 4 and all(len(token) == 1 and token.isalpha() for token in tokens)
            for tokens in token_groups
        )
        if not has_evasion_run:
            return text
        collapsed = [
            "".join(tokens) if tokens and all(len(token) == 1 and token.isalpha() for token in tokens) else word
            for word, tokens in zip(words, token_groups)
        ]
        return " ".join(collapsed)

    @classmethod
    def inspect_and_unpack(cls, text: str) -> Tuple[str, List[str]]:
        unpacked_text = text
        detected = []

        for technique, decoded in cls._decode_nested(text):
            detected.append(technique)
            unpacked_text = cls._append_block(unpacked_text, technique.title(), decoded)

        normalized = unicodedata.normalize("NFKC", text).translate(cls.HOMOGLYPHS)
        if normalized != text and cls.ATTACK_PATTERN.search(normalized):
            detected.append("homoglyph")
            unpacked_text = cls._append_block(unpacked_text, "Homoglyph", normalized)

        clean_invisible = cls.ZERO_WIDTH_PATTERN.sub("", text)
        if clean_invisible != text and cls.ATTACK_PATTERN.search(clean_invisible):
            detected.append("zero_width")
            unpacked_text = cls._append_block(unpacked_text, "Zero-width", clean_invisible)

        spaced = cls._collapse_spaced_letters(text)
        if spaced != text and cls.ATTACK_PATTERN.search(spaced):
            detected.append("spaced_letters")
            unpacked_text = cls._append_block(unpacked_text, "Spaced Letters", spaced)

        leetspeak = text.translate(cls.LEET_TRANSLATION)
        if leetspeak != text and cls.ATTACK_PATTERN.search(leetspeak):
            detected.append("leetspeak")
            unpacked_text = cls._append_block(unpacked_text, "Leetspeak", leetspeak)

        decoded_rot13 = codecs.decode(text, "rot_13")
        explicit_rot13 = cls.ROT13_MARKER_PATTERN.search(text) is not None
        if explicit_rot13 or cls.ATTACK_PATTERN.search(decoded_rot13):
            detected.append("rot13")
            unpacked_text = cls._append_block(unpacked_text, "ROT13", decoded_rot13)

        return unpacked_text, detected
