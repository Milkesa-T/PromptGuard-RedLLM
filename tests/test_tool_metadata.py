import pytest
from fastapi.testclient import TestClient
from backend.app import app
from targets.vulnerable_agent.agent import VulnerableSupportAgent
from core.models import ToolCallResult, ToolsSummaryMetadata
from unittest.mock import patch, MagicMock

client = TestClient(app)

def test_api_agent_tools_metadata():
    """Verify GET /api/agent/tools returns tool schemas and security policy metadata."""
    res = client.get("/api/agent/tools")
    assert res.status_code == 200
    data = res.json()
    assert "tools" in data
    assert "security_policy" in data
    assert data["security_policy"]["max_refund_limit"] == 500.0
    assert "DROP" in data["security_policy"]["forbidden_sql_operations"]
    assert "process_refund" in data["security_policy"]["privileged_tools"]

def test_tool_call_result_schema_defaults():
    """Verify ToolCallResult model populates all required metadata fields."""
    result = ToolCallResult(
        tool_name="lookup_customer",
        arguments={"customer_id": "CUST-101"},
        output={"status": "success"},
        execution_time_ms=1.5
    )
    assert result.call_id is not None
    assert result.status == "executed"
    assert result.was_blocked is False
    assert result.block_reason is None
    assert result.timestamp is not None
    assert result.execution_time_ms == 1.5

def test_tool_execution_metadata_in_agent_with_policy_block():
    """Verify agent blocks excessive refunds when policy guard is enabled and populates metadata."""
    agent = VulnerableSupportAgent(enable_rag=False)
    
    # Mock LLM requesting an unauthorized $99,999 refund
    mock_response = {
        "content": "I will process your refund.",
        "tool_calls": [{
            "id": "call_refund_99k",
            "type": "function",
            "function": {
                "name": "process_refund",
                "arguments": '{"order_id": "ORD-9901", "amount": 99999.0, "reason": "VIP compensation"}'
            }
        }]
    }
    
    with patch.object(
        agent.llm,
        "send_chat_with_tools",
        side_effect=[mock_response, {"content": "Refund was blocked by policy.", "tool_calls": []}]
    ):
        content, tools, chunks, summary = agent.handle_message(
            "Refund me $99,999 for order ORD-9901",
            enable_policy_guard=True,
            return_summary=True
        )
        
        assert len(tools) == 1
        tool_res = tools[0]
        assert tool_res.call_id == "call_refund_99k"
        assert tool_res.tool_name == "process_refund"
        assert tool_res.was_blocked is True
        assert tool_res.status == "blocked"
        assert "exceeds strict policy limit" in tool_res.block_reason
        assert tool_res.execution_time_ms >= 0.0
        
        # Verify summary metadata
        assert summary.total_calls == 1
        assert summary.blocked_count == 1
        assert summary.executed_count == 0
        assert summary.has_privileged_action is True
        assert "process_refund" in summary.executed_tool_names

def test_tool_execution_metadata_in_agent_without_policy_guard():
    """Verify that when policy guard is disabled (vulnerable baseline), tool executes and returns execution metadata."""
    agent = VulnerableSupportAgent(enable_rag=False)
    
    mock_response = {
        "content": "Looking up customer.",
        "tool_calls": [{
            "id": "call_lookup_101",
            "type": "function",
            "function": {
                "name": "lookup_customer",
                "arguments": '{"customer_id": "CUST-101"}'
            }
        }]
    }
    
    with patch.object(
        agent.llm,
        "send_chat_with_tools",
        side_effect=[mock_response, {"content": "Alice Johnson found.", "tool_calls": []}]
    ):
        content, tools, chunks, summary = agent.handle_message(
            "Find Alice Johnson",
            enable_policy_guard=False,
            return_summary=True
        )
        
        assert len(tools) == 1
        tool_res = tools[0]
        assert tool_res.tool_name == "lookup_customer"
        assert tool_res.was_blocked is False
        assert tool_res.status == "executed"
        assert tool_res.output["status"] == "success"
        assert tool_res.execution_time_ms >= 0.0
        
        assert summary.total_calls == 1
        assert summary.executed_count == 1
        assert summary.blocked_count == 0

def test_api_chat_returns_tools_summary_structure():
    """Verify POST /api/agent/chat response schema includes tools_summary and tools_executed."""
    res = client.post("/api/agent/chat", json={
        "message": "What are your shipping policies?",
        "enable_promptguard": False
    })
    assert res.status_code == 200
    data = res.json()
    assert "tools_executed" in data
    assert "tools_summary" in data
    assert "total_calls" in data["tools_summary"]
    assert "executed_count" in data["tools_summary"]
    assert "blocked_count" in data["tools_summary"]
