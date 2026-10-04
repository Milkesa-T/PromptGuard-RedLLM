import asyncio
import time
import sys

# Windows UTF-8 console output
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from redllm.orchestrator import RedLLMOrchestrator
from promptguard.firewall import PromptGuardFirewall
from targets.llm_target import LLMTarget
from evaluation.scorer import EvaluationJudge
from database.db import AuditDatabase
from core.models import AttackResult, GuardAction

async def run_benchmark_campaign(enable_guardrail: bool = False):
    print("\n" + "=" * 75)
    mode_str = "🛡️ WITH PromptGuard Firewall" if enable_guardrail else "⚠️ WITHOUT PromptGuard (Unprotected Baseline)"
    print(f"🚀 Running Red-Teaming Campaign: {mode_str}")
    print("=" * 75)
    
    orchestrator = RedLLMOrchestrator()
    firewall = PromptGuardFirewall()
    target = LLMTarget()
    judge = EvaluationJudge()
    db = AuditDatabase()
    
    attacks = orchestrator.generate_campaign(objective="PWNED_SYSTEM_OVERRIDE")
    total_attacks = len(attacks)
    successful_attacks = 0
    blocked_attacks = 0
    
    for idx, attack in enumerate(attacks, 1):
        prompt_to_send = attack.converted_prompt or attack.raw_prompt
        print(f"\n[Test {idx}/{total_attacks}] Attack Type: {attack.attack_type.value}")
        print(f"👉 Prompt: {prompt_to_send[:80]}...")
        
        start_time = time.time()
        
        # 1. Defense Inspection (if enabled)
        if enable_guardrail:
            guard_result = firewall.inspect(prompt_to_send)
            if guard_result.action == GuardAction.BLOCK:
                print(f"🛑 [PROMPTGUARD BLOCKED]: {guard_result.reason}")
                blocked_attacks += 1
                result = AttackResult(
                    attack_id=attack.attack_id,
                    objective=attack.objective,
                    sent_prompt=prompt_to_send,
                    target_response="[BLOCKED BY PROMPTGUARD]",
                    guard_result=guard_result,
                    is_success=False,
                    judge_reason="Attack prevented by PromptGuard Firewall.",
                    execution_time_seconds=time.time() - start_time
                )
                db.log_result(result)
                continue
        else:
            guard_result = firewall.inspect(prompt_to_send)
            
        # 2. Forward to Target LLM
        response = await target.send_prompt_async(prompt=prompt_to_send)
        print(f"🤖 Bot Response: {response[:100]}...")
        
        # 3. Judge & Score
        is_success, judge_reason = judge.score_response(response, attack.objective)
        exec_time = time.time() - start_time
        
        if is_success:
            successful_attacks += 1
            print(f"💥 Status: ✅ ATTACK SUCCESS (Jailbreak Succeeded)")
        else:
            print(f"🛡️ Status: ❌ ATTACK FAILED ({judge_reason})")
            
        result = AttackResult(
            attack_id=attack.attack_id,
            objective=attack.objective,
            sent_prompt=prompt_to_send,
            target_response=response,
            guard_result=guard_result,
            is_success=is_success,
            judge_reason=judge_reason,
            execution_time_seconds=exec_time
        )
        db.log_result(result)
        
    asr = (successful_attacks / total_attacks) * 100.0
    print("\n" + "-" * 75)
    print(f"📊 SUMMARY ({mode_str}):")
    print(f"   • Total Attacks: {total_attacks}")
    print(f"   • Blocked by Guard: {blocked_attacks}")
    print(f"   • Successful Jailbreaks: {successful_attacks}")
    print(f"   • Attack Success Rate (ASR): {asr:.1f}%")
    print("-" * 75)

async def main():
    # 1. Run Baseline (Without Guard)
    await run_benchmark_campaign(enable_guardrail=False)
    
    # 2. Run Protected (With Guard)
    await run_benchmark_campaign(enable_guardrail=True)

if __name__ == "__main__":
    asyncio.run(main())
