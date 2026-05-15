# MEMBRA CompanyOS

**The orchestration layer where AI builds, governs, and operates real-world companies through proof, permission, and local execution.**

## Doctrine

> Every apartment is the nearest warehouse.  
> Every person is a possible operator.  
> Every surface is possible media.  
> Every object is possible inventory.  
> Every chat is possible intent.  
> Every intent is possible work.  
> Every work unit requires proof.  
> Every proof can become governance.  
> Every governed flow can become a company function.  
> Every repeated company function can become an autonomous operating layer.

## Architecture

```
MEMBRA OS
├── IntentOS      → Converts human chat into structured objectives
├── TaskOS        → Breaks objectives into executable tasks
├── AgentOS       → Assigns each task to the right agent, human, vendor, or system
├── JobOS         → Turns tasks into paid jobs, bounties, routes, listings, workflows
├── CompanyOS     → Turns repeated workflows into departments, roles, SOPs, KPIs
├── GovernanceOS  → Creates approvals, policies, risk gates, voting, audit trails
├── ProofBook     → Records proof hashes, decisions, events, work evidence
├── SettlementOS  → Tracks payout eligibility and sends settlement instructions
└── WorldBridge    → Connects apartments, vehicles, windows, wearables, tools, people, vendors
```

## Tech Stack

- **Backend:** Python 3.11, FastAPI, SQLAlchemy 2.0, PostgreSQL 15, Redis 7, Celery 5
- **Frontend:** Next.js 14, React, TypeScript, TailwindCSS
- **LLM:** Groq, OpenAI, Anthropic (with deterministic fallback)
- **Blockchain:** Solana, Ethereum (optional settlement rails)
- **Deployment:** Docker, Docker Compose, GitHub Actions, Render, Vercel

## Quick Start

```bash
# Clone
git clone https://github.com/overandor/membra-companyos.git
cd membra-companyos

# Environment
cp .env.example .env
# Edit .env with your keys

# Run with Docker Compose
docker-compose up -d

# Or local development
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## API

| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/health` | Health check |
| `POST /api/v1/intents` | Ingest raw intent |
| `POST /api/v1/intents/{id}/parse` | Parse intent to objective |
| `POST /api/v1/objectives/{id}/tasks` | Create task |
| `POST /api/v1/tasks/{id}/assign` | Assign task |
| `POST /api/v1/agents` | Register agent |
| `POST /api/v1/jobs` | Create job/bounty |
| `POST /api/v1/companies` | Register company |
| `POST /api/v1/assets` | Register WorldBridge asset |
| `GET /api/v1/proofbook` | Query immutable ProofBook |

## Production Boundaries

- No fake payments
- No custody
- No guaranteed profit
- Owner confirmation before visibility
- External settlement rails only
- Proof and governance required for real-world execution

## License

MIT — MEMBRA Autonomous Company Orchestration Layer
