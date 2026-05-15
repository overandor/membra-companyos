# MEMBRA CompanyOS — Architecture

## System Overview

MEMBRA is an AI-powered autonomous company orchestration layer. It accepts human intent via natural language, structures it into objectives, breaks objectives into tasks, assigns tasks to agents or humans, tracks proof of completion, enforces governance approvals, and settles payments.

## Core Operating System Layers

```
┌─────────────────────────────────────────────────────────────────┐
│                        MEMBRA CompanyOS                          │
├─────────────────────────────────────────────────────────────────┤
│  IntentOS  →  TaskOS  →  AgentOS  →  JobOS  →  CompanyOS        │
│      ↓           ↓          ↓          ↓           ↓           │
│  Objectives   Tasks     Assignments   Bounties   Departments     │
├─────────────────────────────────────────────────────────────────┤
│  GovernanceOS  →  ProofBook  →  SettlementOS  →  WorldBridge   │
│      ↓              ↓              ↓                ↓           │
│  Approvals      Audit Trail    Payouts         Real Assets       │
└─────────────────────────────────────────────────────────────────┘
```

## Technology Stack

| Layer | Technology |
|-------|-----------|
| API Framework | FastAPI 0.109+ (async) |
| ORM | SQLAlchemy 2.0.25 |
| Database | PostgreSQL 15 |
| Cache / Queue | Redis 7 |
| Background Jobs | Celery 5.3 |
| Frontend | Next.js 14, React, TypeScript, TailwindCSS |
| LLM Providers | Groq, OpenAI, Anthropic (deterministic fallback) |
| Containerization | Docker, Docker Compose |
| CI/CD | GitHub Actions |

## Database Models

| Model | File | Purpose |
|-------|------|---------|
| `Intent` | `models/intent.py` | Raw user intent + parsed structure |
| `Objective` | `models/intent.py` | Structured goal derived from intent |
| `Task` | `models/task.py` | Executable work unit |
| `TaskDependency` | `models/task.py` | DAG edges between tasks |
| `TaskAssignment` | `models/task.py` | Who/what owns a task |
| `TaskProof` | `models/task.py` | Evidence of completion |
| `Agent` | `models/agent.py` | AI/human/vendor registry |
| `AgentTool` | `models/agent.py` | Capabilities per agent |
| `AgentActionLog` | `models/agent.py` | Audit trail of agent actions |
| `Company` | `models/company.py` | Operating unit |
| `Department` | `models/company.py` | Organizational division |
| `KPIRecord` | `models/company.py` | Performance metrics |
| `Job` | `models/job.py` | Paid work / bounty |
| `Settlement` | `models/job.py` | Payout tracking |
| `GovernancePolicy` | `models/governance.py` | Rules & thresholds |
| `ApprovalRequest` | `models/governance.py` | Pending approvals |
| `ProofBookEvent` | `models/proofbook.py` | Immutable hash-chained events |
| `WorldAsset` | `models/worldbridge.py` | Real-world asset registry |
| `AssetListing` | `models/worldbridge.py` | Marketplace listing |

All models inherit from `Base` with ULID primary keys and automatic timestamps.

## LLM Bridge — 6 Novel Patterns

### 1. IntentDrivenUI
**Endpoint:** `POST /api/v1/llm/intent-ui`

Backend LLM parses natural language and returns a JSON patch that the frontend applies directly to React state. Mutations include component visibility, form pre-fill, route hints, and data-fetch triggers.

**Flow:**
```
User: "I want to assign a task"
  → Backend LLM detects "assign" + "task" keywords
  → Returns: { mutations: [{target:"task_panel", prop:"expanded", value:true}], fetch_triggers: [...] }
  → Frontend applies patch immediately
```

### 2. SchemaToComponent
**Endpoint:** `POST /api/v1/llm/schema-component`

Send a SQLAlchemy table name + field definitions. Backend returns a complete TypeScript React component string with props interface, form fields, and display markup.

**Flow:**
```
Input: { table_name: "world_asset", fields: [...] }
  → Backend generates: interface WorldAssetCardProps { ... }
  → Returns complete TSX string
  → Frontend renders dynamically or uses for codegen
```

### 3. PredictiveOrchestration
**Endpoint:** `POST /api/v1/llm/predict`

Analyzes recent user action history, predicts the most likely next 3 actions, pre-fetches relevant data endpoints, and returns UI preload instructions.

**Flow:**
```
Input: { user_id: "usr_001", recent_actions: [{action_type:"intent_created"}] }
  → Backend predicts: "next likely action is parse_intent (60%)"
  → Pre-fetches: /api/v1/intents/{id}/parse
  → Returns: { predicted_next_actions, pre_fetched_data, ui_preload }
```

### 4. ChatGovernance
**Endpoint:** `POST /api/v1/llm/governance-chat`

Conversational governance — users approve, reject, or query approvals via natural chat. The LLM interprets intent, mutates `ApprovalRequest` records, and returns human-friendly replies.

**Flow:**
```
User: "yes approve it"
  → Backend LLM detects approval intent
  → Finds most recent pending ApprovalRequest
  → Sets status = "approved", approver_wallet = user
  → Returns: "Approval granted for job abc123..."
```

### 5. MultimodalProof
**Endpoint:** `POST /api/v1/llm/verify-proof`

Accepts base64-encoded media. Vision-capable LLM analyzes content, checks against task proof requirements, writes `TaskProof` record if verified, and appends to ProofBook.

**Flow:**
```
Input: { task_id: "tsk_001", media_b64: "...", mime_type: "image/png" }
  → Backend: media type check → size check → vision analysis → task alignment
  → If confidence >= 0.7: creates TaskProof, updates task status = "completed"
  → Writes ProofBook entry
  → Returns: { verified: true, confidence: 0.85, checks: [...] }
```

### 6. AgentSwarmProxy
**Endpoint:** `POST /api/v1/llm/swarm`

Single LLM proxy analyzes user intent, selects relevant specialist agents (strategy, finance, compliance, operations, marketing), dispatches them in parallel, and synthesizes a unified response.

**Flow:**
```
User: "What's the budget and is it compliant?"
  → Backend LLM detects: "budget" (finance) + "compliant" (compliance)
  → Dispatches: finance agent + compliance agent in parallel
  → Synthesizes unified reply with both perspectives
  → Returns: { routing_decision, agent_responses, unified_reply }
```

## Services Architecture

```
┌──────────────────────────────────────────┐
│         OrchestratorService              │
│  (Intent → Objective → Task → Job)       │
└─────────────────┬────────────────────────┘
                  │
┌─────────────────┴────────────────────────┐
│         LLMBridgeService                 │
│  (6 patterns: UI, Component, Predict,    │
│   Governance, Vision, Swarm)               │
└──────────────────────────────────────────┘
                  │
┌─────────────────┴────────────────────────┐
│         ProofBook (Immutable)            │
│  SHA-256 hash chain of all events        │
└──────────────────────────────────────────┘
```

## Request Lifecycle

1. **Ingest** — User submits intent via dashboard chat or API
2. **Parse** — LLM Bridge structures intent into objective
3. **Decompose** — Objective broken into tasks with dependencies
4. **Assign** — AgentOS selects best assignee (AI/human/vendor)
5. **Govern** — GovernanceOS checks if approval required
6. **Execute** — Assignee completes task, submits proof
7. **Verify** — MultimodalProof (vision LLM) or human review
8. **Record** — ProofBook writes immutable hash-chained event
9. **Settle** — SettlementOS calculates payout, triggers rails

## Deployment

### Docker Compose (Local)
```bash
docker-compose up -d --build
# Services: app (8000), worker, db (5432), redis (6379), nginx (80)
```

### Production (Render)
1. Connect GitHub repo to Render
2. Set environment variables from `.env.example`
3. Auto-deploy on push to `main`

### Frontend (Vercel)
```bash
cd frontend
npm install
npm run build
# Deploy dist/ to Vercel
```

## Security Boundaries

- No fake payments
- No custody of user funds
- No promises of guaranteed profit
- Owner confirmation before real-world visibility
- External settlement rails only
- Proof and governance required for execution
- JWT tokens with 30-min expiry, refresh tokens with 30-day expiry
- Rate limiting: 5/min auth, 100/min API
- CORS configurable via environment

## File Structure

```
membra-companyos/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes.py          # Core OS endpoints
│   │   │   └── llm.py             # 6 LLM pattern endpoints
│   │   ├── core/
│   │   │   ├── config.py          # Pydantic settings
│   │   │   └── security.py        # JWT, nonces, hashing
│   │   ├── db/
│   │   │   └── database.py        # Async engine + session
│   │   ├── models/
│   │   │   ├── base.py            # ULID + timestamps
│   │   │   ├── intent.py
│   │   │   ├── task.py
│   │   │   ├── agent.py
│   │   │   ├── company.py
│   │   │   ├── job.py
│   │   │   ├── governance.py
│   │   │   ├── proofbook.py
│   │   │   └── worldbridge.py
│   │   ├── services/
│   │   │   ├── orchestrator.py    # Core orchestration
│   │   │   └── llm_bridge.py     # 6 LLM patterns
│   │   └── main.py                # FastAPI app
│   ├── tests/
│   │   └── test_llm_bridge.py    # Pattern tests
│   └── requirements.txt
├── frontend/
│   ├── app/
│   │   ├── page.tsx               # Dashboard
│   │   ├── layout.tsx
│   │   └── globals.css
│   ├── lib/
│   │   └── llm.ts                 # API client
│   └── package.json
├── infra/
│   └── docker/
│       └── nginx.conf
├── docker-compose.yml
├── Dockerfile
├── Makefile
├── .github/
│   └── workflows/
│       └── ci.yml                 # CI/CD pipeline
├── README.md
├── ARCHITECTURE.md
├── PUSH_GUIDE.md
└── .env.example
```

## Status

- ✅ Backend: 9 OS modules + 6 LLM patterns
- ✅ API: 20+ endpoints
- ✅ Frontend: Interactive dashboard with pattern selector
- ✅ Tests: Comprehensive test suite for LLM patterns
- ✅ Docker: Compose orchestration with health checks
- ✅ CI/CD: GitHub Actions workflow
- ⏳ GitHub Push: Blocked — requires fresh personal access token (see `PUSH_GUIDE.md`)
