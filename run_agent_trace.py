try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

import sys
import json

# Ensure UTF-8 output encoding on Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

from targets.vulnerable_agent.agent import VulnerableSupportAgent


def main():
    prompt = sys.argv[1] if len(sys.argv) > 1 else "Where is order ORD-9901?"
    print(f"User Query: {prompt}\n")

    agent = VulnerableSupportAgent(enable_rag=True)
    final_answer, executed_tools, retrieved_chunks = agent.handle_message(prompt)

    print("=" * 60)
    print("STEP-BY-STEP AGENT TRACE")
    print("=" * 60)

    for item in agent.last_trace:
        step_num = item.get("step")
        step_type = item.get("type")
        data = item.get("data", {})
        print(f"\n[Step {step_num}] Type: {step_type}")
        print(json.dumps(data, indent=2, ensure_ascii=False))

    print("\n" + "=" * 60)
    print("FINAL ANSWER")
    print("=" * 60)
    print(final_answer)


if __name__ == "__main__":
    main()
