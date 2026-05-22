# GeneTrace

> An agentic biomedical research tool that turns a gene name or variant into a structured research brief — pulling from ClinVar, PubMed, and UniProt in parallel, synthesizing with GPT-4o-mini, and persisting every trace to PostgreSQL.

![Python](https://img.shields.io/badge/python-3.11-blue) ![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688) ![React](https://img.shields.io/badge/React-18-61DAFB) ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791) ![LangChain](https://img.shields.io/badge/LangChain-0.2-1c3c3c) ![Docker](https://img.shields.io/badge/Docker-compose-2496ED)

---

## What it does

Enter a gene symbol (`BRCA2`), receptor (`EGFR`), or variant id (`rs334`) and GeneTrace will:

1. **Fan out in parallel** to three public biomedical APIs (ClinVar, PubMed, UniProt) via `asyncio.gather`.
2. **Synthesize a structured brief** with an LLM (LangChain + GPT-4o-mini) covering: gene overview, associated conditions, protein function, recent research highlights, and a clinical significance summary.
3. **Score data completeness** transparently on a 0–100 rubric (hit counts + brief length).
4. **Persist every trace** to PostgreSQL and expose a recent-history sidebar.

## Setup

```bash
git clone <this-repo>
cd genetrace
cp backend/.env.example backend/.env
# add your OPENAI_API_KEY to backend/.env
docker-compose up --build
```

- Frontend: <http://localhost:5173>
- Backend API: <http://localhost:8000>
- Health check: <http://localhost:8000/health>

If `OPENAI_API_KEY` is not set, the backend still works — it falls back to a structured brief built directly from the source data (no synthesis).

### Deploy to Railway

1. Push repo to GitHub
2. Create new Railway project
3. Add service from repo → select `backend/` directory
4. Add Postgres plugin — Railway auto-sets `DATABASE_URL`
5. Set env vars on backend service: `OPENAI_API_KEY`, `NCBI_API_KEY`
6. Add second service from repo → select `frontend/` directory
7. Set env var on frontend service: `VITE_API_URL=<your backend Railway URL>`
8. Both services auto-deploy on push

## Project structure

```
genetrace/
├── backend/                 # FastAPI + async SQLAlchemy + LangChain
│   ├── app/
│   │   ├── main.py          # app entrypoint, CORS, lifespan
│   │   ├── database.py      # async engine, QueryRecord model
│   │   ├── agents/
│   │   │   ├── fetcher.py       # parallel ClinVar / PubMed / UniProt
│   │   │   └── synthesizer.py   # LLM synthesis + eval rubric
│   │   ├── models/schemas.py    # Pydantic request/response models
│   │   └── routers/trace.py     # /trace and /history endpoints
│   └── tests/test_trace.py      # pytest + respx integration tests
├── frontend/                # React 18 + Vite, no UI framework
│   └── src/
│       ├── App.jsx
│       ├── components/
│       │   ├── SearchBar.jsx
│       │   ├── ResearchBrief.jsx
│       │   ├── SourceBadges.jsx
│       │   ├── EvalScore.jsx
│       │   └── HistoryPanel.jsx
│       └── hooks/useTrace.js
├── docker-compose.yml       # db + backend + frontend
└── README.md
```

## API

| Method | Path       | Description                                          |
| ------ | ---------- | ---------------------------------------------------- |
| POST   | `/trace`   | `{ "query": "BRCA2" }` → full brief + sources + score |
| GET    | `/history` | Last 20 traces, newest first                          |
| GET    | `/health`  | Liveness probe                                        |

## Eval rubric

```
+30  ClinVar  ≥ 1 hit
+30  PubMed   ≥ 1 hit
+20  UniProt  ≥ 1 reviewed (Swiss-Prot) hit
+20  Brief    ≥ 200 words
---
100  max
```

Surfaced in the UI as a colored progress bar (green ≥ 80 · amber 50–79 · red < 50).

## Tests

```bash
cd backend
pip install -r requirements.txt
pytest
```

The suite covers parallel fetching (mocked with `respx`), the 5-section synthesis contract, score bounds, and the `/trace` endpoint happy + 422 paths.

## Screenshot

> _Add a screenshot of the running app here._

## Mapping to the BMS AI Venture Studio stack

GeneTrace is a deliberately small but architecturally honest slice of the stack you'd use to ship internal agentic tooling for biomedical R&D:

- **Agentic pipelines** — a fetcher agent and a synthesizer agent compose via async orchestration; the fetcher fans out, the synthesizer reduces. Adding a third (e.g. a critic) is one file.
- **Multi-source data integration** — three heterogeneous public APIs (NCBI E-utilities JSON, NCBI XML, UniProt REST) are normalized into a uniform `{source, hits, data}` shape so downstream agents and the UI don't care about provenance differences.
- **LLM synthesis with structure** — LangChain + GPT-4o-mini constrained to a 5-section schema the frontend parses deterministically; the same contract would let you swap in Claude or an internal model.
- **Structured evaluation** — every trace ships with a transparent, deterministic data-completeness score, so you can monitor drift over time without an LLM judge.
- **FastAPI + PostgreSQL on AWS-compatible infra** — async-throughout backend, containerized, no AWS-specific code. The Compose file maps cleanly onto ECS/Fargate + RDS Postgres or EKS.
