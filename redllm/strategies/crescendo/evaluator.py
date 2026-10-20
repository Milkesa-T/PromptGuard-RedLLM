import time
import uuid
from typing import Optional, List, Dict, Any
from redllm.strategies.crescendo.models import (
    CrescendoObjective,
    CrescendoTurnRecord,
    CrescendoRunResult
)
from redllm.strategies.crescendo.target_adapter import (
    BaseMultiTurnTarget,
    AgentTargetAdapter
)
from redllm.strategies.crescendo.guard_adapter import (
    BaseGuardAdapter,
    FirewallGuardAdapter
)
from redllm.strategies.crescendo.generator import (
    BaseCrescendoGenerator,
    HybridCrescendoGenerator
)
from redllm.strategies.crescendo.scorer import CrescendoScorer
from core.models import GuardAction, GuardInspectionResult

class CrescendoEvaluator:
    """
    Executes an adaptive, multi-turn Crescendo evaluation run against a target system.
    Orchestrates turn generation, guardrail inspection, score calculation, and
    automatic backtracking when blocked or when progress drops.
    """

    def __init__(
        self,
        target: Optional[BaseMultiTurnTarget] = None,
        guard: Optional[BaseGuardAdapter] = None,
        generator: Optional[BaseCrescendoGenerator] = None,
        scorer: Optional[CrescendoScorer] = None,
        max_turns: int = 5,
        max_backtracks_per_turn: int = 2,
        use_llm_generator: bool = False
    ):
        self.target = target or AgentTargetAdapter()
        self.guard = guard or FirewallGuardAdapter()
        self.generator = generator or HybridCrescendoGenerator(use_llm=use_llm_generator)
        self.scorer = scorer or CrescendoScorer()
        self.max_turns = max_turns
        self.max_backtracks_per_turn = max_backtracks_per_turn

    def run_objective(
        self,
        objective: CrescendoObjective,
        enable_guard: bool = True
    ) -> CrescendoRunResult:
        """
        Execute full Crescendo multi-turn evaluation for a given objective.
        """
        start_time = time.time()
        run_id = f"crescendo_{uuid.uuid4().hex[:10]}"
        max_turns = min(self.max_turns, objective.max_turns)
        max_backtracks = min(self.max_backtracks_per_turn, objective.max_backtracks_per_turn)

        # Reset target state before starting run
        self.target.reset()

        transcript: List[CrescendoTurnRecord] = []
        progress_scores: List[float] = []
        guard_interventions: List[Dict[str, Any]] = []
        all_surfaced_content: List[str] = []
        all_surfaced_actions: List[Dict[str, Any]] = []

        backtrack_count = 0
        consecutive_stagnant_turns = 0
        is_success = False
        stopping_reason = "in_progress"

        current_step = 1
        last_response: Optional[str] = None
        last_retrieved: Optional[List[Dict[str, Any]]] = None
        last_tools: Optional[List[Dict[str, Any]]] = None

        while current_step <= max_turns:
            step_prev_score = progress_scores[-1] if progress_scores else 0.0
            turn_accepted = False

            # Prompt generation for current step
            current_prompt = self.generator.generate_turn(
                objective=objective,
                turn_index=current_step,
                history=transcript,
                last_response=last_response,
                last_retrieved=last_retrieved,
                last_tools=last_tools,
                is_backtrack=False
            )

            # Backtracking retry loop for this step
            for attempt_idx in range(max_backtracks + 1):
                is_backtrack_attempt = (attempt_idx > 0)
                guard_result: Optional[GuardInspectionResult] = None

                # 1. Guard Input Inspection (if enabled)
                if enable_guard:
                    guard_result = self.guard.inspect_input(current_prompt)
                    if guard_result.action == GuardAction.BLOCK:
                        # Guard blocked this turn
                        intervention = {
                            "turn": current_step,
                            "attempt": attempt_idx,
                            "type": "input_block",
                            "guard_layer": guard_result.guard_layer,
                            "reason": guard_result.reason,
                            "blocked_prompt": current_prompt
                        }
                        guard_interventions.append(intervention)

                        # Check if we can backtrack
                        if attempt_idx < max_backtracks:
                            backtrack_count += 1
                            # Generate alternate softer phrasing
                            current_prompt = self.generator.generate_turn(
                                objective=objective,
                                turn_index=current_step,
                                history=transcript,
                                last_response=last_response,
                                last_retrieved=last_retrieved,
                                last_tools=last_tools,
                                is_backtrack=True,
                                backtrack_reason=f"Blocked: {guard_result.reason}",
                                backtrack_attempt=attempt_idx + 1
                            )
                            continue
                        else:
                            # Retries exhausted on guard block
                            record = CrescendoTurnRecord(
                                turn_index=current_step,
                                prompt=current_prompt,
                                response="[BLOCKED BY GUARD]",
                                guard_action="block",
                                guard_reason=guard_result.reason,
                                progress_score=0.0,
                                is_backtrack=is_backtrack_attempt,
                                backtrack_attempt=attempt_idx,
                                notes="Step blocked by guard; retries exhausted."
                            )
                            transcript.append(record)
                            progress_scores.append(0.0)
                            consecutive_stagnant_turns += 1
                            turn_accepted = True
                            break

                # 2. Forward to Target System
                resp_text, tool_calls, retrieved_chunks = self.target.send_turn(current_prompt)

                # 3. Guard Output Inspection
                out_guard_res = None
                if enable_guard:
                    out_guard_res = self.guard.inspect_output(resp_text)
                    if out_guard_res.action == GuardAction.SANITIZE:
                        guard_interventions.append({
                            "turn": current_step,
                            "type": "output_sanitized",
                            "reason": out_guard_res.reason
                        })
                    resp_text = out_guard_res.inspected_response

                # 4. Score the turn
                score, turn_success, surfaced_c, surfaced_a, score_reason = self.scorer.score_turn(
                    objective=objective,
                    turn_index=current_step,
                    prompt=current_prompt,
                    response=resp_text,
                    retrieved_chunks=retrieved_chunks,
                    tool_calls=tool_calls,
                    guard_result=guard_result,
                    output_guard_result=out_guard_res
                )

                all_surfaced_content.extend(surfaced_c)
                all_surfaced_actions.extend(surfaced_a)

                # 5. Check Backtrack on Progress Drop
                # If score dropped significantly compared to previous turn and we have retries left
                if score < step_prev_score and attempt_idx < max_backtracks and not turn_success:
                    # Roll back target history checkpoint
                    self.target.rollback_last_turn()
                    backtrack_count += 1
                    guard_interventions.append({
                        "turn": current_step,
                        "attempt": attempt_idx,
                        "type": "progress_drop_backtrack",
                        "prev_score": step_prev_score,
                        "dropped_score": score
                    })
                    # Request alternate less direct version
                    current_prompt = self.generator.generate_turn(
                        objective=objective,
                        turn_index=current_step,
                        history=transcript,
                        last_response=last_response,
                        last_retrieved=last_retrieved,
                        last_tools=last_tools,
                        is_backtrack=True,
                        backtrack_reason="progress_dropped",
                        backtrack_attempt=attempt_idx + 1
                    )
                    continue

                # Turn successfully executed and accepted
                record = CrescendoTurnRecord(
                    turn_index=current_step,
                    prompt=current_prompt,
                    response=resp_text,
                    retrieved_chunks=retrieved_chunks,
                    tool_calls=tool_calls,
                    guard_action="allow" if not guard_result else guard_result.action.value,
                    guard_reason=guard_result.reason if guard_result else None,
                    progress_score=round(score, 3),
                    is_backtrack=is_backtrack_attempt,
                    backtrack_attempt=attempt_idx,
                    notes=score_reason
                )
                transcript.append(record)
                progress_scores.append(round(score, 3))

                last_response = resp_text
                last_retrieved = retrieved_chunks
                last_tools = tool_calls

                # Check if objective is reached
                if turn_success or score >= 1.0:
                    is_success = True
                    stopping_reason = "objective_achieved"
                    turn_accepted = True
                    break

                # Stagnation tracking (score did not improve)
                if score <= step_prev_score:
                    consecutive_stagnant_turns += 1
                else:
                    consecutive_stagnant_turns = 0

                turn_accepted = True
                break

            # Check immediate stop condition: success
            if is_success:
                break

            # Check stop condition: exhausted retries with no progress for 2 turns in a row
            if consecutive_stagnant_turns >= 2:
                stopping_reason = "retries_exhausted_no_progress_stagnation"
                break

            current_step += 1

        if not is_success and stopping_reason == "in_progress":
            stopping_reason = "max_turns_reached"

        exec_time = time.time() - start_time

        # Deduplicate surfaced items
        dedup_content = list(dict.fromkeys(all_surfaced_content))
        dedup_actions = []
        seen_acts = set()
        for a in all_surfaced_actions:
            key = f"{a.get('tool_name')}_{str(a.get('arguments'))}"
            if key not in seen_acts:
                seen_acts.add(key)
                dedup_actions.append(a)

        return CrescendoRunResult(
            run_id=run_id,
            objective_id=objective.id,
            objective_type=objective.objective_type.value,
            objective_description=objective.description,
            is_success=is_success,
            turns_used=len(transcript),
            transcript=transcript,
            progress_scores=progress_scores,
            guard_interventions=guard_interventions,
            backtrack_count=backtrack_count,
            surfaced_restricted_content=dedup_content,
            surfaced_actions=dedup_actions,
            stopping_reason=stopping_reason,
            execution_time_seconds=round(exec_time, 2)
        )
