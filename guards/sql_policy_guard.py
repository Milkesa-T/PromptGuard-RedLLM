import re
from typing import Dict, Any, Tuple


class ToolParameterEnforcer:
    SQL_DISALLOWED = [
        re.compile(r"\bDROP\b", re.IGNORECASE),
        re.compile(r"\bUNION\b", re.IGNORECASE),
        re.compile(r"\bOR\s+1\s*=\s*1\b", re.IGNORECASE),
        re.compile(r"--"),
        re.compile(r";")
    ]

    @classmethod
    def validate_tool_call(cls, tool_name: str, tool_args: Dict[str, Any]) -> Tuple[bool, str]:
        if tool_name == "execute_internal_query":
            query = tool_args.get("query", "")
            return cls._validate_sql_query(query)

        elif tool_name == "process_refund":
            amount = tool_args.get("amount")
            return cls._validate_refund_amount(amount)

        return True, "Tool authorized."

    @classmethod
    def _validate_sql_query(cls, query: str) -> Tuple[bool, str]:
        if not isinstance(query, str) or not query.strip():
            return False, "Query must be a non-empty string."

        for pattern in cls.SQL_DISALLOWED:
            if pattern.search(query):
                return False, f"Blocked SQL injection pattern: '{pattern.pattern}'"

        return True, "SQL query passed policy check."

    @classmethod
    def _validate_refund_amount(cls, amount: Any) -> Tuple[bool, str]:
        try:
            val = float(amount)
        except (TypeError, ValueError):
            return False, f"Invalid refund amount: {amount}"

        if val <= 0.0:
            return False, f"Refund must be > $0.00 (received {val})"

        if val > 100.0:
            return False, f"Refund exceeds maximum allowed $100.00 (received {val})"

        return True, f"Refund ${val:.2f} authorized."


if __name__ == "__main__":
    print("=== SQL Policy Self-Test ===")
    # Should be False
    print("DROP test:", ToolParameterEnforcer.validate_tool_call("execute_internal_query", {"query": "DROP TABLE users;"}))
    # Should be False
    print("OR 1=1 test:", ToolParameterEnforcer.validate_tool_call("execute_internal_query", {"query": "SELECT * FROM orders WHERE 1=1 OR 1=1"}))
    # Should be False (exceeds $100)
    print("Refund $150 test:", ToolParameterEnforcer.validate_tool_call("process_refund", {"amount": 150.00}))
    # Should be True
    print("Valid Refund test:", ToolParameterEnforcer.validate_tool_call("process_refund", {"amount": 42.50}))