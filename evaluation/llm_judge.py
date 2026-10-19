"""Structured LLM-as-a-judge interface for benchmark evaluations."""
from typing import Any, Dict
from evaluation.scorer import EvaluationJudge


def judge_outcome(
    prompt: str,
    target_response: str,
    tools_executed: Any = None,
    objective: str = "",
) -> Dict[str, Any]:
    """Return a boolean verdict and evidence-based reasoning."""
    judge = EvaluationJudge(use_llm_judge=True)
    is_success, reason = judge.evaluate(
        objective=objective or prompt,
        attack_prompt=prompt,
        target_response=target_response,
        tools_executed=tools_executed or [],
    )
    return {
        "is_success": bool(is_success),
        "reason": str(reason),
        "evidence": {
            "prompt": prompt,
            "target_response": target_response,
            "tools_executed": tools_executed or [],
        },
    }


class LLMJudge:
    """Convenient class interface for the automated judge."""

    def evaluate(self, prompt, target_response, tools_executed=None, objective=""):
        return judge_outcome(prompt, target_response, tools_executed, objective)
