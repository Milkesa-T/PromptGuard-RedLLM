from core.base import BaseConverter

LEET_MAP = {
    'a': '4', 'A': '4',
    'e': '3', 'E': '3',
    'i': '1', 'I': '1',
    'o': '0', 'O': '0',
    's': '5', 'S': '5',
    't': '7', 'T': '7'
}

class LeetspeakConverter(BaseConverter):
    """Converts alphabetic characters to leetspeak numbers to evade simple keyword filters."""
    
    @property
    def name(self) -> str:
        return "leetspeak"

    def convert(self, prompt: str) -> str:
        leet_chars = [LEET_MAP.get(c, c) for c in prompt]
        return "".join(leet_chars)
