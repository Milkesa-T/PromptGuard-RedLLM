import re
from typing import List, Tuple, Dict, Any


class CanaryGuard:
    def __init__(self, canary_tokens: List[str] = None):
        self.canary_tokens = canary_tokens or ["PWNED_SYSTEM_OVERRIDE", "CANARY_SEC_TOKEN"]

    @staticmethod
    def _normalize(text: str) -> str:
        return re.sub(r"[\s\-_.,:;|/\\*~`'\"+=]+", "", text).upper()

    def inspect(self, response_text: str) -> Tuple[bool, Dict[str, Any]]:
        normalized_response = self._normalize(response_text)
        raw_upper = response_text.upper()

        for token in self.canary_tokens:
            norm_token = self._normalize(token)

            if token.upper() in raw_upper:
                return True, {"leaked": True, "token": token, "type": "exact"}

            if norm_token and norm_token in normalized_response:
                return True, {"leaked": True, "token": token, "type": "obfuscated"}

        return False, {"leaked": False, "token": None}


if __name__ == "__main__":
    guard = CanaryGuard(["PWNED_SYSTEM_OVERRIDE"])
    print("=== Canary Guard Self-Test ===")
    # Tests spaces between letters
    spaced = "System says: P W N E D _ S Y S T E M _ O V E R R I D E"
    print("Spaced canary caught:", guard.inspect(spaced))
    # Tests punctuation separation
    punctuated = "Token is P.W.N.E.D_S.Y.S.T.E.M_O.V.E.R.R.I.D.E"
    print("Punctuated canary caught:", guard.inspect(punctuated))
    # Clean text
    clean = "Here is your requested shipping label."
    print("Clean text allowed:", guard.inspect(clean))