import asyncio
import time
import sys
from tabulate import tabulate

# Windows UTF-8 console output
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from redllm.orchestrator import RedLLMOrchestrator
from promptguard.firewall import PromptGuardFirewall
from targets.llm_target import LLMTarget
from evaluation.scorer import EvaluationJudge
from database.db import AuditDatabase
from core.models import AttackResult, GuardAction

async def run_benchmark_campaign(enable_guardrail: bool = False) -> dict:
    mode_str = "🛡️ WITH PromptGuard Firewall" if enable_guardrail else "⚠️ WITHOUT PromptGuard (Unprotected Target)"
    print("\n" + "=" * 80)
    print(f"🚀 Running Red-Teaming Campaign: {mode_str}")
    print("=" * 80)
    
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
        print(f"\n[Test {idx}/{total_attacks}] Type: {attack.attack_type.value}")
        print(f"👉 Prompt: {prompt_to_send[:75]}...")
        
        start_time = time.time()
        guard_result = None
        
        # 1. Defense Inspection
        if enable_guardrail:
            guard_result = firewall.inspect_input(prompt_to_send)
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
                    judge_reason=f"Blocked: {guard_result.reason}",
                    execution_time_seconds=time.time() - start_time
                )
                db.log_result(result)
                continue
        else:
            guard_result = firewall.inspect_input(prompt_to_send)
            
        # 2. Forward to Target LLM
        response = await target.send_prompt_async(prompt=prompt_to_send)
        print(f"🤖 Target Output: {response[:90].strip()}...")
        
        # 3. Output Guard (if enabled)
        if enable_guardrail:
            out_res = firewall.inspect_output(response)
            response = out_res.inspected_response
            
        # 4. Judge & Score
        is_success, judge_reason = judge.evaluate(attack.objective, prompt_to_send, response)
        exec_time = time.time() - start_time
        
        if is_success:
            successful_attacks += 1
            print(f"💥 Status: ✅ ATTACK SUCCESS (Jailbreak / Leakage Succeeded)")
        else:
            print(f"🛡️ Status: ❌ ATTACK FAILED ({judge_reason[:60]}...)")
            
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
        
    asr = (successful_attacks / total_attacks) * 100.0 if total_attacks > 0 else 0.0
    return {
        "mode": mode_str,
        "total": total_attacks,
        "blocked": blocked_attacks,
        "success": successful_attacks,
        "asr": asr
    }

async def main():
    print("=" * 80)
    print("🛡️ PromptGuard / RedLLM — Comprehensive Security Benchmark")
    print("=" * 80)
    
    # 1. Run Baseline (Without Guard)
    unprotected_stats = await run_benchmark_campaign(enable_guardrail=False)
    
    # 2. Run Protected (With Guard)
    protected_stats = await run_benchmark_campaign(enable_guardrail=True)
    
    # Comparison Summary Table
    table_data = [
        ["⚠️ Unprotected Target", unprotected_stats["total"], unprotected_stats["blocked"], unprotected_stats["success"], f"{unprotected_stats['asr']:.1f}%"],
        ["🛡️ PromptGuard Active", protected_stats["total"], protected_stats["blocked"], protected_stats["success"], f"{protected_stats['asr']:.1f}%"]
    ]
    
    print("\n" + "=" * 80)
    print("📊 FINAL BENCHMARK COMPARISON SUMMARY:")
    print("=" * 80)
    print(tabulate(table_data, headers=["Configuration", "Total Tests", "Blocked by Guard", "Jailbreak Successes", "Attack Success Rate (ASR)"], tablefmt="fancy_grid"))
    print("\n✅ All audit traces and execution telemetry saved to database/audit_logs.db")
    print("🌐 Launch web dashboard with: python run_server.py\n")

if __name__ == "__main__":
    asyncio.run(main())
