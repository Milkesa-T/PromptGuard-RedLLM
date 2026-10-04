# 🏛️ Technical Architecture Specification
**PromptGuard / RedLLM Framework**

---

## 1. System Block Diagram

```mermaid
flowchart TB
    subgraph UI_Layer ["🖥️ Frontend & Dashboard (Static / React)"]
        UI1["Attack Launcher"]
        UI2["Traffic Telemetry"]
        UI3["Agent Chat Sandbox"]
    end

    subgraph Backend_Gateway ["⚡ FastAPI REST & WebSocket Engine"]
        API["Routes: /api/attack, /api/guard, /api/agent, /api/benchmark"]
    end

    subgraph RedLLM_Attacker ["🔴 RedLLM Attack Engine"]
        Strat["Attack Strategies<br/>(Direct, Theft, Multi-turn)"]
        Conv["Converters & Obfuscators<br/>(Base64, ROT13, Leet, Hex)"]
        ToolAtk["Tool Misuse Payloads<br/>(SQLi, Excessive Refund)"]
    end

    subgraph PromptGuard_Defense ["🛡️ PromptGuard Multi-Tier Firewall"]
        direction TB
        L1["Tier 1: Cipher & Encoding Unpacker"]
        L2["Tier 2: Heuristic & Regex Scanner"]
        L3["Tier 3: Guardrail Classifier (LLM Judge)"]
        L4["Tier 4: Canary Leak & Tool Policy Guard"]
    end

    subgraph Target_Layer ["🤖 Target Under Test"]
        T_LLM["LLM Target (Groq / OpenAI / Ollama)"]
        T_Agent["NovaSupport Agent (RAG + Tools Sandbox)"]
    end

    subgraph Storage_Eval ["📊 Evaluation & Audit Trail"]
        Judge["Evaluation Judge (Canary + Regex + LLM Judge)"]
        DB[("SQLite: audit_logs.db")]
    end

    UI_Layer <--> Backend_Gateway
    Backend_Gateway --> RedLLM_Attacker
    RedLLM_Attacker --> PromptGuard_Defense
    PromptGuard_Defense -->|If Clean| Target_Layer
    PromptGuard_Defense -.->|If Blocked| Storage_Eval
    Target_Layer --> PromptGuard_Defense
    PromptGuard_Defense --> Storage_Eval
    Storage_Eval --> Backend_Gateway
```

---

## 2. Core Data Contracts (`core/models.py`)

- `AttackRequest`: Defines `attack_id`, `objective`, `raw_prompt`, `converted_prompt`, `attack_type`, `target_tool`, `metadata`.
- `GuardInspectionResult`: Defines `action` (`ALLOW`, `BLOCK`, `SANITIZE`), `reason`, `inspected_prompt`, `detected_ciphers`, `latency_ms`.
- `OutputInspectionResult`: Defines `action`, `reason`, `inspected_response`, `contains_canary`, `tool_calls_blocked`.
- `AttackResult`: Combined record containing prompt, response, guard action, success score, and execution duration.
- `BenchmarkSummary`: Aggregated campaign metrics (`total_attacks`, `blocked_by_guard`, `attack_success_rate`, `avg_latency_ms`).
