try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

import pytest
import json
from unittest.mock import MagicMock
from core.config import OPENAI_CHAT_KEY
from targets.vulnerable_agent.agent import (
    VulnerableSupportAgent,
    parse_tool_arguments,
    dispatch_tool
)

is_real_llm_configured = bool(
    OPENAI_CHAT_KEY and not OPENAI_CHAT_KEY.startswith("gsk_your_") and OPENAI_CHAT_KEY != "no-key-needed"
)

skip_if_no_llm_key = pytest.mark.skipif(
    not is_real_llm_configured,
    reason="Valid OPENAI_CHAT_KEY is not configured in .env"
)


# =========================================================================
# NO-LLM UNIT TESTS
# =========================================================================

def test_parse_tool_arguments_invalid_json():
    """e) invalid JSON arguments -> handled, error returned"""
    parsed = parse_tool_arguments("{not a valid json syntax")
    assert isinstance(parsed, dict)
    assert "error" in parsed
    res = dispatch_tool("lookup_order", parsed)
    assert isinstance(res, dict)
    assert res.get("status") == "error"


def test_parse_tool_arguments_valid():
    """Verify parse_tool_arguments handles string dict, raw dict, and empty values."""
    assert parse_tool_arguments('{"order_id": "ORD-9901"}') == {"order_id": "ORD-9901"}
    assert parse_tool_arguments({"order_id": "ORD-9901"}) == {"order_id": "ORD-9901"}
    assert parse_tool_arguments("") == {}
    assert parse_tool_arguments(None) == {}


def test_dispatch_tool_unknown_name():
    """f) unknown tool name -> handled, error returned"""
    res = dispatch_tool("nonexistent_tool_xyz", {"param": "val"})
    assert isinstance(res, dict)
    assert res.get("status") == "error"
    assert "unknown tool" in res.get("message", "").lower()


def test_max_tool_rounds_respected():
    """g) max_tool_rounds is respected"""
    agent = VulnerableSupportAgent(enable_rag=False, max_tool_rounds=2)

    # Mock LLM to simulate continuous tool calls without returning plain text
    mock_llm = MagicMock()
    mock_llm.send_chat_with_tools.return_value = {
        "content": "",
        "tool_calls": [
            {
                "id": "call_mock_1",
                "type": "function",
                "function": {
                    "name": "lookup_order",
                    "arguments": '{"order_id": "ORD-9901"}'
                }
            }
        ]
    }
    agent.llm = mock_llm

    ans, tools, _ = agent.handle_message("Where is order ORD-9901?")
    assert "maximum tool call rounds" in ans.lower()
    assert mock_llm.send_chat_with_tools.call_count == 2
    assert any(s["type"] == "final_answer" for s in agent.last_trace)


# =========================================================================
# REAL LLM INTEGRATION TESTS
# =========================================================================

@pytest.mark.llm
@skip_if_no_llm_key
def test_llm_order_lookup_trace():
    """a) 'Where is order ORD-9901?' -> a lookup_order call with order_id 'ORD-9901' appears in trace, final answer non-empty text."""
    agent = VulnerableSupportAgent(enable_rag=False)
    final_answer, executed_tools, _ = agent.handle_message("Where is order ORD-9901?")

    assert isinstance(final_answer, str)
    assert len(final_answer.strip()) > 0

    lookup_calls = [
        s for s in agent.last_trace
        if s["type"] == "tool_call" and s["data"].get("tool_name") == "lookup_order"
    ]
    assert len(lookup_calls) >= 1
    call_args = lookup_calls[0]["data"].get("arguments", {})
    assert call_args.get("order_id") == "ORD-9901"
    assert any(t.tool_name == "lookup_order" for t in executed_tools)


@pytest.mark.llm
@skip_if_no_llm_key
def test_llm_tool_results_role_and_id_format():
    """b) Tool results are appended to history with role 'tool' and a tool_call_id matching the request."""
    agent = VulnerableSupportAgent(enable_rag=False)
    agent.handle_message("Where is order ORD-9901?")

    assistant_msgs = [
        m for m in agent.conversation_history
        if m.get("role") == "assistant" and "tool_calls" in m and len(m["tool_calls"]) > 0
    ]
    assert len(assistant_msgs) >= 1
    requested_id = assistant_msgs[0]["tool_calls"][0]["id"]

    tool_msgs = [m for m in agent.conversation_history if m.get("role") == "tool"]
    assert len(tool_msgs) >= 1
    assert tool_msgs[0].get("tool_call_id") == requested_id
    assert isinstance(tool_msgs[0].get("content"), str)
    assert not any(m.get("role") == "function" for m in agent.conversation_history)


@pytest.mark.llm
@skip_if_no_llm_key
def test_llm_plain_conversation_no_tools():
    """c) 'Hello' -> text answer, no tool calls."""
    agent = VulnerableSupportAgent(enable_rag=False)
    final_answer, executed_tools, _ = agent.handle_message("Hello")

    assert isinstance(final_answer, str)
    assert len(final_answer.strip()) > 0
    assert len(executed_tools) == 0
    assert not any(s["type"] == "tool_call" for s in agent.last_trace)
    assert any(s["type"] == "final_answer" for s in agent.last_trace)


@pytest.mark.llm
@skip_if_no_llm_key
def test_llm_tool_call_filter_blocks_execution():
    """d) tool_call_filter returning False -> the tool is NOT executed."""
    agent = VulnerableSupportAgent(
        enable_rag=False,
        tool_call_filter=lambda name, args: False
    )
    final_answer, executed_tools, _ = agent.handle_message("Where is order ORD-9901?")

    assert len(executed_tools) >= 1
    blocked_tool = executed_tools[0]
    assert blocked_tool.was_blocked is True
    assert blocked_tool.output.get("status") == "error"

    trace_tool_results = [s for s in agent.last_trace if s["type"] == "tool_result"]
    assert len(trace_tool_results) >= 1
    assert trace_tool_results[0]["data"].get("was_blocked") is True
