import re
from typing import Tuple, Dict, Any


class PIIRedactionGuard:
    CC_PATTERN = re.compile(r"\b(?:\d{4}-){3}\d{4}\b")
    SSN_PATTERN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
    EMAIL_PATTERN = re.compile(r"\b([a-zA-Z0-9_.+-])[a-zA-Z0-9_.+-]*(@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)\b")

    def redact(self, text: str) -> Tuple[str, Dict[str, Any]]:
        redacted_text = text
        stats = {"cc_count": 0, "ssn_count": 0, "email_count": 0, "redacted": False}

        cc_matches = len(self.CC_PATTERN.findall(redacted_text))
        if cc_matches > 0:
            redacted_text = self.CC_PATTERN.sub("[REDACTED_CC]", redacted_text)
            stats["cc_count"] = cc_matches

        ssn_matches = len(self.SSN_PATTERN.findall(redacted_text))
        if ssn_matches > 0:
            redacted_text = self.SSN_PATTERN.sub("[REDACTED_SSN]", redacted_text)
            stats["ssn_count"] = ssn_matches

        email_matches = len(self.EMAIL_PATTERN.findall(redacted_text))
        if email_matches > 0:
            redacted_text = self.EMAIL_PATTERN.sub(r"\1***\2", redacted_text)
            stats["email_count"] = email_matches

        stats["redacted"] = (stats["cc_count"] + stats["ssn_count"] + stats["email_count"]) > 0
        return redacted_text, stats


if __name__ == "__main__":
    guard = PIIRedactionGuard()
    sample = "Contact alice.smith@example.org with SSN 123-45-6789 and Card 1234-5678-9012-3456."
    cleaned, stats = guard.redact(sample)
    print("=== PII Guard Self-Test ===")
    print("Redacted:", cleaned)
    print("Stats:", stats)