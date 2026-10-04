import base64
import codecs

class Base64Converter:
    @staticmethod
    def encode(text: str) -> str:
        return base64.b64encode(text.encode("utf-8")).decode("utf-8")
    
    @staticmethod
    def decode(encoded_text: str) -> str:
        try:
            return base64.b64decode(encoded_text.encode("utf-8")).decode("utf-8")
        except Exception:
            return encoded_text

class ROT13Converter:
    @staticmethod
    def encode(text: str) -> str:
        return codecs.encode(text, "rot_13")
    
    @staticmethod
    def decode(encoded_text: str) -> str:
        return codecs.decode(encoded_text, "rot_13")

class LeetSpeakConverter:
    LEET_MAP = {'a': '4', 'e': '3', 'i': '1', 'o': '0', 's': '5', 't': '7'}
    
    @classmethod
    def encode(cls, text: str) -> str:
        return "".join(cls.LEET_MAP.get(c.lower(), c) for c in text)
