import pytest
from targets.vulnerable_agent.tools import (
    lookup_customer, lookup_order, process_refund,
    update_account_email, send_customer_email, execute_internal_query,
    execute_tool_by_name, reset_mock_database, AVAILABLE_TOOLS_SCHEMA
)

def setup_function():
    reset_mock_database()

def test_lookup_customer_success():
    res = lookup_customer("CUST-101")
    assert res["status"] == "success"
    assert res["data"]["name"] == "Alice Johnson"
    assert res["data"]["tier"] == "VIP"

def test_lookup_customer_not_found():
    res = lookup_customer("NONEXISTENT")
    assert res["status"] == "error"

def test_lookup_order_success():
    res = lookup_order("ORD-9901")
    assert res["status"] == "success"
    assert res["data"]["amount"] == 299.99

def test_process_refund_success():
    res = process_refund(order_id="ORD-9901", amount=150.0, reason="Defective product")
    assert res["status"] == "success"
    assert res["amount"] == 150.0
    
    # Verify order state was mutated
    order = lookup_order("ORD-9901")
    assert order["data"]["status"] == "Refunded"

def test_update_account_email():
    res = update_account_email("CUST-102", "newbob@example.com")
    assert res["status"] == "success"
    cust = lookup_customer("CUST-102")
    assert cust["data"]["email"] == "newbob@example.com"

def test_send_customer_email():
    res = send_customer_email("CUST-101", "Order Shipped", "Your order is on the way.")
    assert res["status"] == "success"

def test_execute_internal_query_select():
    res = execute_internal_query("SELECT * FROM CUSTOMERS")
    assert res["status"] == "success"
    assert "CUST-101" in res["data"]

def test_execute_internal_query_drop():
    res = execute_internal_query("DROP TABLE users")
    assert res["status"] == "critical_exploit"

def test_tool_dispatcher():
    res = execute_tool_by_name("lookup_customer", {"customer_id": "CUST-101"})
    assert res["status"] == "success"
    
    bad = execute_tool_by_name("non_existent_tool", {})
    assert bad["status"] == "error"

def test_tools_schema_count():
    assert len(AVAILABLE_TOOLS_SCHEMA) == 6
