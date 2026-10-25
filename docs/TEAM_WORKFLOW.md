# 👥 Team Workflow & Development Guide
**PromptGuard / RedLLM — 6-Person Engineering Team**

Welcome to the team! This repository contains the complete production-grade architecture, baseline modules, and interactive web application for our automated red-teaming and LLM defense framework.

---

## 🌳 Branching Strategy & PR Workflow

To keep our codebase clean, avoid regression breaks, and prevent merge conflicts, we follow a strict **Feature Branch & Pull Request (PR)** model:

### 1. Main Branches:
- `main`: **Production / Submission Ready**. Protected branch containing stable, thoroughly tested code.
- `develop`: **Main Integration Branch**. All feature branches branch off and merge back into `develop`.

### 2. Feature Branch Naming:
Each member creates their own feature branch named according to their assigned area:
- Member 1 (Backend & Agent Sandbox): `feature/m1-backend-agent`
- Member 2 (Direct Attacks & Seeds): `feature/m2-redllm-strategies`
- Member 3 (Converters & Tool Exploits): `feature/m3-redllm-converters-tools`
- Member 4 (Input Firewall & Vector Defense): `feature/m4-promptguard-firewall`
- Member 5 (Output Guards & RAG Defense): `feature/m5-output-rag-defense`
- Member 6 (React Frontend & Benchmark Suite): `feature/m6-react-benchmark-ui`

---

## 👥 Module Ownership & Task Assignments

| Member | Assigned Role | Primary Folders Owned | Key Responsibilities & Deliverables |
| :--- | :--- | :--- | :--- |
| **Member 1 (Lead)** | System Architect & Agent Engine | `core/`, `backend/`, `targets/` | Maintain FastAPI REST endpoints, OpenAI/Groq API client integrations, tool execution engine, and vulnerable customer support agent (`NovaSupportAgent`). |
| **Member 2** | RedLLM: Direct & Injections | `redllm/strategies/`, `evaluation/datasets/` | Implement core jailbreak engines (PAIR, Crescendo, DAN, Developer Mode, Roleplay), maintain prompt injection taxonomies, and curate seed attack datasets. |
| **Member 3** | RedLLM: Obfuscators & Tool Payloads | `redllm/converters/`, `redllm/tool_attacks/` | Build multi-layer evasion converters (Base64, ROT13, Leetspeak, Hex, Zero-width steganography) and exploit payloads targeting SQLi, excessive refund issuance, and canary exfiltration. |
| **Member 4** | PromptGuard: Input Layer Shield | `promptguard/input_guards/`, `promptguard/firewall.py` | Engineer multi-tier input firewall: encoding decoders, regex heuristic scanners, semantic vector embedding guardrails, and rapid block/sanitize actions. |
| **Member 5** | PromptGuard: Output & RAG Defense | `promptguard/output_guards/`, `targets/rag/` | Implement output leak detectors (PII, regex, canary tokens), tool parameter bounds validation, indirect RAG document injection sandbox, and poisoned chunk quarantine filters. |
| **Member 6** | Frontend & Evaluation Lead | `frontend/`, `database/`, `evaluation/` | Build the modern React + Vite dashboard (5 operational views, Tailwind styling, Lucide icons), manage SQLite audit logging, and maintain automated ASR benchmark scoring. |

---

## 🛠️ Local Development Setup

### Prerequisites
- Python 3.10+
- Node.js 18+ & npm
- Valid Groq API Key or OpenAI API Key

### Backend Setup
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

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Set up environment file
cp .env.example .env
# Edit .env and supply your GROQ_API_KEY or OPENAI_API_KEY

# 5. Run test suite
pytest

# 6. Start FastAPI Backend (Port 8000)
python run_server.py
```

### Frontend Setup (React + Vite)
```bash
# From workspace root:
cd frontend
npm install
npm run dev
# Dashboard launches at http://localhost:5173
```

---

## 📝 Pull Request Checklist Before Merging:
1. `pytest` passes with 0 failures or regressions.
2. Code adheres to existing Pydantic data schemas in `core/models.py`.
3. All UI API calls route to FastAPI endpoints (`/api/...`) with graceful error handling.
4. Added or updated docstrings and type annotations for all new classes and methods.
5. Assigned at least 1 teammate to review the PR before merging into `develop`.

