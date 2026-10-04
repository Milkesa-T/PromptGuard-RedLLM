from core.base import BaseOutputGuard
from core.models import ToolCallResult, OutputInspectionResult, GuardAction
from typing import Dict, Any, List, Optional

class ToolExecutionPolicyGuard:
    """Validates and enforces security policies on tool/function arguments before and after agent execution."""
    
    # Maximum allowed refund without human approval
    MAX_REFUND_LIMIT = 500.0
    
    # Disallowed dangerous SQL commands
    FORBIDDEN_SQL_OPERATIONS = ["DROP", "DELETE", "ALTER", "TRUNCATE", "INSERT INTO", "UPDATE"]

    @classmethod
    def validate_tool_call(cls, tool_name: str, arguments: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Check whether the agent's tool call parameters violate security policies."""
        if tool_name == "process_refund":
            amount = float(arguments.get("amount", 0.0))
            if amount > cls.MAX_REFUND_LIMIT:
                return False, f"Refund amount ${amount:.2f} exceeds strict policy limit (${cls.MAX_REFUND_LIMIT:.2f}). Blocked."
        
        elif tool_name == "execute_internal_query":
            query = arguments.get("sql_query", "").upper()
            for forbidden in cls.FORBIDDEN_SQL_OPERATIONS:
                if forbidden in query:
                    return False, f"Dangerous SQL keyword '{forbidden}' detected in tool execution query. Blocked."
                    
        return True, None
