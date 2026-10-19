import sys
from guards.pii_redaction import PIIRedactionGuard
from guards.sql_policy_guard import ToolParameterEnforcer
from guards.canary_guard import CanaryGuard


def run_all_assigned_tests():
    print("=" * 70)
    print("RUNNING COMPLETE SECURITY GUARD VERIFICATION SUITE")
    print("=" * 70)

    total_checks = 0
    passed_checks = 0

    # -----------------------------------------------------------------
    # TASK 1: PII Redaction Guard Verification
    # -----------------------------------------------------------------
    print("\n--- [TASK 1: PII Redaction Guard] ---")
    pii = PIIRedactionGuard()

    pii_samples = [
        {
            "name": "Credit Card Masking",
            "input": "Customer card number is 4532-1234-5678-9010 on file.",
            "expected_substr": "[REDACTED_CC]",
            "forbidden_substr": "4532-1234-5678-9010",
        },
        {
            "name": "SSN Masking",
            "input": "Account verification SSN: 123-45-6789.",
            "expected_substr": "[REDACTED_SSN]",
            "forbidden_substr": "123-45-6789",
        },
        {
            "name": "Email Masking (u***@domain.com)",
            "input": "Send invoices to alex.turner@company.org please.",
            "expected_substr": "a***@company.org",
            "forbidden_substr": "alex.turner@company.org",
        },
    ]

    for item in pii_samples:
        total_checks += 1
        redacted_text, stats = pii.redact(item["input"])
        has_expected = item["expected_substr"] in redacted_text
        has_no_secret = item["forbidden_substr"] not in redacted_text

        if has_expected and has_no_secret:
            passed_checks += 1
            print(f"[PASS] {item['name']}")
            print(f"       Cleaned: {redacted_text.strip()}")
        else:
            print(f"[FAIL] {item['name']}")
            print(f"       Result : {redacted_text.strip()}")

    # -----------------------------------------------------------------
    # TASK 2: Strict Tool Parameter Enforcer (SQL & Refund)
    # -----------------------------------------------------------------
    print("\n--- [TASK 2: Tool Parameter Enforcer] ---")
    tool_cases = [
        # SQL Injection checks
        ("SQL: DROP TABLE blocked", "execute_internal_query", {"query": "DROP TABLE users;"}, False),
        ("SQL: UNION SELECT blocked", "execute_internal_query", {"query": "SELECT * FROM orders UNION SELECT token FROM creds"}, False),
        ("SQL: OR 1=1 blocked", "execute_internal_query", {"query": "SELECT * FROM logs WHERE 1=1 OR 1=1"}, False),
        ("SQL: Comment (--) blocked", "execute_internal_query", {"query": "SELECT name FROM items WHERE id=2 -- skip"}, False),
        ("SQL: Semicolon (;) blocked", "execute_internal_query", {"query": "SELECT 1; SHUTDOWN;"}, False),
        ("SQL: Clean query allowed", "execute_internal_query", {"query": "SELECT id, price FROM orders WHERE id='ORD-1'"}, True),
        # Refund limits ($0 < amount <= $100.00)
        ("Refund: > $100 blocked", "process_refund", {"amount": 100.01}, False),
        ("Refund: <= $0 (Zero) blocked", "process_refund", {"amount": 0.0}, False),
        ("Refund: Negative blocked", "process_refund", {"amount": -10.0}, False),
        ("Refund: Upper bound ($100.00) allowed", "process_refund", {"amount": 100.00}, True),
        ("Refund: Valid ($35.50) allowed", "process_refund", {"amount": 35.50}, True),
    ]

    for name, tool_name, args, should_allow in tool_cases:
        total_checks += 1
        allowed, reason = ToolParameterEnforcer.validate_tool_call(tool_name, args)
        if allowed == should_allow:
            passed_checks += 1
            print(f"[PASS] {name} -> ({'ALLOWED' if allowed else 'BLOCKED'})")
        else:
            print(f"[FAIL] {name} -> Expected allowed={should_allow}, got allowed={allowed} ({reason})")

    # -----------------------------------------------------------------
    # TASK 3: Multi-Token Canary Leakage Protection
    # -----------------------------------------------------------------
    print("\n--- [TASK 3: Multi-Token Canary Leakage Protection] ---")
    canary = CanaryGuard(["PWNED_SYSTEM_OVERRIDE", "CANARY_SEC_TOKEN"])

    canary_cases = [
        ("Exact match leak caught", "Secret token is PWNED_SYSTEM_OVERRIDE", True),
        ("Spaced-out token caught", "Token revealed: P W N E D _ S Y S T E M _ O V E R R I D E", True),
        ("Punctuation-separated token caught", "Token revealed: P.W.N.E.D_S.Y.S.T.E.M_O.V.E.R.R.I.D.E", True),
        ("Mixed delimiters caught", "Secret: C-A-N-A-R-Y_S-E-C_T-O-K-E-N", True),
        ("Legitimate response allowed", "Order ORD-9921 has been marked as shipped.", False),
    ]

    for name, text_input, should_leak in canary_cases:
        total_checks += 1
        detected, details = canary.inspect(text_input)
        if detected == should_leak:
            passed_checks += 1
            status = "LEAK BLOCKED" if detected else "OUTPUT ALLOWED"
            print(f"[PASS] {name} -> ({status})")
        else:
            print(f"[FAIL] {name} -> Expected detected={should_leak}, got detected={detected}")

    # -----------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------
    print("\n" + "=" * 70)
    print(f"VERIFICATION SUMMARY: {passed_checks}/{total_checks} CHECKS PASSED")
    print("=" * 70)

    if passed_checks == total_checks:
        print("STATUS: ALL 3 ASSIGNED TASKS OPERATING CORRECTLY.")
        return 0
    else:
        print("STATUS: FIXES REQUIRED BEFORE SUBMISSION.")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_assigned_tests())