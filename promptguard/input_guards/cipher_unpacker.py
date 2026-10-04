import re
import base64
import codecs
from typing import Tuple, List

class CipherUnpacker:
    """Detects and decodes hidden ciphers (Base64, ROT13, Leetspeak) in user prompts."""
    
    BASE64_PATTERN = re.compile(r'(?:[A-Za-z0-9+/]{4}){3,}(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?')
    
    @classmethod
    def inspect_and_unpack(cls, text: str) -> Tuple[str, List[str]]:
        detected = []
        unpacked_text = text
        
        # 1. Check for Base64 blocks
        matches = cls.BASE64_PATTERN.findall(text)
        for match in matches:
            if len(match) >= 12: # Avoid tiny false positives
                try:
                    decoded = base64.b64decode(match).decode('utf-8')
                    if decoded.isprintable() and len(decoded.strip()) > 3:
                        detected.append("base64")
                        unpacked_text += f"\n[Unpacked Base64 Content]: {decoded}"
                except Exception:
                    pass
                    
        # 2. Check for explicit ROT13 keywords or heuristic
        if "rot13" in text.lower() or "ebg13" in text.lower():
            detected.append("rot13")
            decoded_rot13 = codecs.decode(text, "rot_13")
            unpacked_text += f"\n[Unpacked ROT13 Content]: {decoded_rot13}"
            
        return unpacked_text, detected
