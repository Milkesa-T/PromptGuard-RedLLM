from openai import AsyncOpenAI
from core.config import OPENAI_CHAT_ENDPOINT, OPENAI_CHAT_KEY, OPENAI_CHAT_MODEL

class LLMTarget:
    """Connects to OpenAI / Groq / Ollama target models."""
    
    def __init__(self, endpoint: str = OPENAI_CHAT_ENDPOINT, api_key: str = OPENAI_CHAT_KEY, model: str = OPENAI_CHAT_MODEL):
        self.client = AsyncOpenAI(base_url=endpoint, api_key=api_key)
        self.model = model
        
    async def send_prompt_async(self, prompt: str, system_prompt: str = "You are a helpful and secure AI assistant.") -> str:
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            return f"[Target Connection Error]: {str(e)}"
