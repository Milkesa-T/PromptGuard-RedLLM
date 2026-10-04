from openai import OpenAI, AsyncOpenAI
from core.config import OPENAI_CHAT_ENDPOINT, OPENAI_CHAT_KEY, OPENAI_CHAT_MODEL
from typing import Optional, List, Dict, Any

class LLMTarget:
    """Connects to OpenAI / Groq / Ollama target models with tool-calling and sync/async support."""
    
    def __init__(
        self,
        endpoint: str = OPENAI_CHAT_ENDPOINT,
        api_key: str = OPENAI_CHAT_KEY,
        model: str = OPENAI_CHAT_MODEL
    ):
        self.endpoint = endpoint
        self.api_key = api_key or "no-key-needed"
        self.model = model
        self.sync_client = OpenAI(base_url=self.endpoint, api_key=self.api_key)
        self.async_client = AsyncOpenAI(base_url=self.endpoint, api_key=self.api_key)

    def send_prompt(self, prompt: str, system_prompt: str = "You are a helpful and secure AI assistant.") -> str:
        """Send a single turn prompt synchronously."""
        try:
            response = self.sync_client.chat.completions.create(
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

    async def send_prompt_async(self, prompt: str, system_prompt: str = "You are a helpful and secure AI assistant.") -> str:
        """Send a single turn prompt asynchronously."""
        try:
            response = await self.async_client.chat.completions.create(
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

    def send_chat(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Send full conversation messages list synchronously."""
        try:
            response = self.sync_client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.0
            )
            choice = response.choices[0].message
            return {"content": choice.content or "", "tool_calls": []}
        except Exception as e:
            return {"content": f"[Target Error]: {str(e)}", "tool_calls": []}

    def send_chat_with_tools(self, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Send conversation with tool/function calling enabled."""
        try:
            response = self.sync_client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                temperature=0.0
            )
            choice = response.choices[0].message
            tool_calls = []
            if choice.tool_calls:
                for tc in choice.tool_calls:
                    tool_calls.append({
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    })
            return {
                "content": choice.content or "",
                "tool_calls": tool_calls
            }
        except Exception as e:
            # If model does not support tool calling directly, fallback to standard completion
            return {"content": f"[Target Tool Error]: {str(e)}", "tool_calls": []}
