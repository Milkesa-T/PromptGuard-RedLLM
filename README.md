# 🛡️ PromptGuard / RedLLM
**An Automated Red-Teaming & Defense Framework for LLM-Powered Applications**

---

## 🚀 Overview
**PromptGuard / RedLLM** is an end-to-end security framework designed to:
1. **RedLLM (Attacker Engine)**: Automatically generate and execute prompt injections, cipher obfuscations (Base64, ROT13, Leetspeak), system prompt theft, and agent tool-misuse attacks.
2. **PromptGuard (Defense Firewall)**: Provide a multi-tier firewall (Cipher Unpacker, Heuristic Scanner, Classifier Guard, Canary Token Protection, and Tool Execution Policy).
3. **Evaluation & Benchmarking**: Automatically score attacks (LLM-as-a-judge), record audit traces in SQLite, and calculate **Attack Success Rate (ASR)** metrics.

---

## 👥 Team Work Breakdown (Team of 6)

| Member | Focus Area | Key Folders Owned |
| :--- | :--- | :--- |
| **Member 1 (Lead)** | System Architecture & Vulnerable Agent Sandbox | `core/`, `backend/`, `targets/` |
| **Member 2** | RedLLM: Direct Injections & Multi-turn Attacks | `redllm/strategies/`, `evaluation/datasets/` |
| **Member 3** | RedLLM: Obfuscators & Agent Tool Exploits | `redllm/converters/`, `redllm/tool_attacks/` |
| **Member 4** | PromptGuard: Input Layer Shield | `promptguard/input_guards/`, `promptguard/firewall.py` |
| **Member 5** | PromptGuard: Output & Tool Policy Enforcer | `promptguard/output_guards/` |
| **Member 6** | Scoring, Benchmarking & Web UI | `evaluation/`, `database/`, `frontend/` |

---

## 🛠️ Quick Start

### 1. Setup Virtual Environment
```bash
python -m venv .venv
# On Windows PowerShell:
.venv\Scripts\Activate.ps1
# On Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env` and configure your API keys (Groq, OpenAI, or local Ollama):
```bash
cp .env.example .env
```

### 3. Run the Live Demo Test
```bash
python main.py
```
