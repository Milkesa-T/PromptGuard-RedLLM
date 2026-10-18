import os
try:
    import truststore; truststore.inject_into_ssl()
except ImportError:
    pass
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(base_url=os.getenv("OPENAI_CHAT_ENDPOINT"),
                api_key=os.getenv("OPENAI_CHAT_KEY"))

tools = [{
    "type": "function",
    "function": {
        "name": "lookup_order",
        "description": "Look up an order by ID.",
        "parameters": {"type": "object",
                       "properties": {"order_id": {"type": "string"}},
                       "required": ["order_id"]},
    },
}]

r = client.chat.completions.create(
    model=os.getenv("OPENAI_CHAT_MODEL"),
    messages=[{"role": "user", "content": "Where is order ORD-9901?"}],
    tools=tools,
)
msg = r.choices[0].message
print("model:", os.getenv("OPENAI_CHAT_MODEL"))
print("tool_calls:", msg.tool_calls)
print("content:", msg.content)
