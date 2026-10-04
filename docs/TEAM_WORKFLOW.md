# 👥 Team Workflow & Development Guide
**PromptGuard / RedLLM — 6-Person Graduation Project**

Welcome to the team! This repository contains the complete core architecture and baseline modules for our automated red-teaming and defense framework.

---

## 🌳 Branching Strategy & PR Workflow

To keep our codebase clean and prevent merge conflicts, we follow a strict **Feature Branch & Pull Request (PR)** model:

### 1. Main Branches:
- `main`: **Production / Submission Ready**. Protected branch containing stable, tested code.
- `develop`: **Main Development Branch**. All feature branches branch off and merge back into `develop`.

### 2. Feature Branch Naming:
Each member creates their own feature branch named according to their assigned area:
- Member 1: `feature/m1-sandbox-agent`
- Member 2: `feature/m2-redllm-strategies`
- Member 3: `feature/m3-redllm-converters-tools`
- Member 4: `feature/m4-promptguard-input`
- Member 5: `feature/m5-promptguard-output-policy`
- Member 6: `feature/m6-benchmark-ui`

---

## 👥 Module Ownership & Task Assignments

| Member | Assigned Role | Primary Folders Owned | Key Responsibilities |
| :--- | :--- | :--- | :--- |
| **Member 1 (Lead)** | System Architect & Sandbox Agent | `core/`, `backend/`, `targets/` | Maintain FastAPI endpoints, LLM API client, and enhance the vulnerable agent sandbox. |
| **Member 2** | RedLLM: Direct & Injections | `redllm/strategies/`, `evaluation/datasets/` | Implement new jailbreak techniques (PAIR, Crescendo, DAN variants) & curate seed datasets. |
| **Member 3** | RedLLM: Obfuscators & Tool Attacks | `redllm/converters/`, `redllm/tool_attacks/` | Add Unicode homoglyphs, multi-language translation converters, and SQLi / privilege escalation tool payloads. |
| **Member 4** | PromptGuard: Input Layer Shield | `promptguard/input_guards/`, `promptguard/firewall.py` | Add semantic vector similarity guard (cosine distance from jailbreak embeddings) & enhance regex patterns. |
| **Member 5** | PromptGuard: Output & Tool Policy | `promptguard/output_guards/` | Build PII redaction, canary exfiltration blockers, and strict tool-parameter enforcement rules. |
| **Member 6** | Evaluation, Scorer & Web UI | `evaluation/`, `database/`, `frontend/` | Enhance LLM-as-a-Judge scoring accuracy, generate comparative ASR charts, and build UI components. |

---

## 🛠️ Local Development Setup

```bash
# 1. Clone repository
git clone https://github.com/Milkesa-T/PromptGuard-RedLLM.git
cd PromptGuard-RedLLM

# 2. Create and activate virtual environment
python -m venv .venv
# On Windows:
.venv\Scripts\Activate.ps1
# On Linux/macOS:
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment file
cp .env.example .env
# (Edit .env with your Groq or OpenAI API key)

# 5. Run tests
pytest

# 6. Start Web Dashboard & API Server
python run_server.py
```

---

## 📝 Pull Request Checklist Before Merging:
1. `pytest` passes with 0 failures.
2. Code follows clean typing (Pydantic models in `core/models.py`).
3. Added or updated docstrings for new functions.
4. Assigned at least 1 teammate to review the PR before merging into `develop`.
