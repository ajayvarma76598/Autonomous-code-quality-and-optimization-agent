Autonomous Code Quality & Optimization Intelligence System
An AI-powered, multi-agent software intelligence platform that analyzes source-code repositories, evaluates code quality, identifies architectural and performance issues, and generates grounded recommendations for optimization, documentation, and refactoring.

👨‍💻 Project
Autonomous Code Quality & Optimization Intelligence System

An Agentic AI platform for repository understanding, software-quality analysis, performance optimization, architecture review, documentation generation and evidence-grounded developer assistance.

🚀 Live Demo
Demo Application:
https://autonomous-code-quality-and-optimization-rg5g.onrender.com/

Demo Credentials
These credentials are provided for demonstration purposes only.

Role	User ID	Password
Developer	user@gmail.com	user@123
Manager	admin@gmail.com	admin@123
The application provides different capabilities and dashboards based on the authenticated role.

Developer: repository analysis, queries, code-quality insights, analysis results and execution views.

Manager: management/operational views, quality metrics, system-level monitoring and manager-only functionality.

🎯 Project Overview
The Autonomous Code Quality & Optimization Intelligence System combines traditional static-analysis tools with Retrieval-Augmented Generation (RAG) and agentic AI workflows.

Instead of relying only on an LLM to inspect an entire repository, the system combines:

Repository ingestion and source-code parsing

AST-based analysis using Tree-sitter

Semantic vector retrieval

BM25 keyword retrieval

Hybrid retrieval with Reciprocal Rank Fusion (RRF)

Dependency-graph expansion

LLM-based re-ranking

SonarQube quality metrics

Radon complexity analysis

Scalene performance profiling

Specialized AI agents

LangGraph workflow orchestration

Guardrails and evaluation

Langfuse observability

PostgreSQL + pgvector persistence

Redis-based caching

Auth0 authentication and role-based access control

The goal is to provide an AI software-engineering assistant that produces evidence-grounded code-quality recommendations rather than unsupported LLM opinions.

✨ Key Features
1. Multi-Agent AI Orchestration
The backend uses a LangGraph-based workflow with specialized agents.

User Query
    │
    ▼
Guardrail Agent
    │
    ▼
Manager / Supervisor Agent
    │
    ├── Repository Agent
    ├── Architecture Agent
    ├── Performance Agent
    ├── Test Coverage Agent
    ├── Documentation Agent
    └── Quality Analysis Pipeline
            │
            ├── Repository Parser
            ├── SonarQube Metrics
            ├── Architecture Reviewer
            └── Quality Report Generator
    │
    ▼
Evaluation Agent
    │
    ├── PASS ───────────────► Final Response
    │
    └── FAIL ───────────────► Human Validation / Escalation
The Manager Agent determines the appropriate workflow from the user's request and routes it to the relevant specialist agents.

2. Intelligent Repository Analysis
Repositories can be ingested and analyzed to understand:

Source files

Functions and classes

APIs and routes

Architecture

Configuration

Dependencies

Documentation

Code relationships

Quality metrics

Tree-sitter is used for structured source-code parsing across supported programming languages.

3. Hybrid RAG Retrieval
The retrieval subsystem combines multiple retrieval strategies:

User Query
   │
   ▼
Intent Detection
   │
   ▼
Query Expansion
   │
   ├──────────────► BM25 Keyword Retrieval
   │
   └──────────────► Vector Semantic Retrieval
                         │
                         ▼
                 Dependency Graph Expansion
                         │
                         ▼
                  RRF Result Fusion
                         │
                         ▼
                    Diversification
                         │
                         ▼
                  LLM Re-ranking
                         │
                         ▼
                  Top-K Evidence
This allows the system to retrieve both semantically related code and exact keyword/code-symbol matches.

4. Code Quality Intelligence
The system integrates quality-analysis capabilities including:

SonarQube for code smells, vulnerabilities, complexity and quality metrics

Radon for Python cyclomatic complexity and maintainability analysis

Scalene for Python CPU and memory profiling

Test-coverage analysis

Architecture review

Quality-gate evaluation

5. Evidence-Grounded Reports
The quality pipeline retrieves measurable evidence before generating a report.

The generated response can include:

Quality metrics

Test coverage

Complexity

Code smells

Specific findings

File paths

Line numbers

Architecture observations

Refactoring recommendations

6. Guardrails
A Guardrail Agent runs before the main workflow.

It is designed to identify:

Prompt injection attempts

Malicious requests

Destructive operations

Requests for secrets or credentials

Highly unrelated requests

PII protection is also supported through Microsoft Presidio components.

7. Evaluation and Human Escalation
The Evaluation Agent acts as a quality gate for generated responses.

If an analysis fails validation, the workflow can:

Mark the result as requiring escalation.

Trigger an escalation alert.

Pause before human validation.

Prevent the workflow from continuing indefinitely.

This provides an additional safety layer around autonomous analysis.

8. Observability
Langfuse integration provides visibility into:

Agent execution

Workflow transitions

Query sessions

LLM calls

Agent routing

Execution timing

Evaluation information

🏗️ Architecture
High-Level Architecture
┌─────────────────────────────────────────────────────────────┐
│                     React Frontend                          │
│                  Vite + TypeScript                          │
│                                                             │
│  Login │ Developer Dashboard │ Manager Dashboard            │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           │ REST API
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Backend                           │
│                                                             │
│  Auth │ Repositories │ Sessions │ Queries │ Ingestion       │
│        Executions │ Operational │ Escalation                │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                 LangGraph Workflow Engine                   │
│                                                             │
│ Guardrail → Manager → Specialist Agents → Evaluation        │
│                                                             │
│ Repository │ Architecture │ Performance │ Coverage          │
│ Documentation │ Quality Analysis │ Reporter                 │
└───────────────┬──────────────────────┬──────────────────────┘
                │                      │
                ▼                      ▼
┌────────────────────────┐   ┌───────────────────────────────┐
│ Retrieval / RAG Layer  │   │ External Analysis             │
│                        │   │                               │
│ BM25                   │   │ SonarQube                     │
│ Vector Search          │   │ Radon                         │
│ RRF Fusion             │   │ Scalene                       │
│ Dependency Graph       │   │ Test Coverage                 │
│ LLM Re-ranking         │   │                               │
└────────────┬───────────┘   └───────────────┬───────────────┘
             │                               │
             └──────────────┬────────────────┘
                            ▼
              ┌──────────────────────────┐
              │ PostgreSQL + pgvector    │
              │ Redis Cache              │
              │ Langfuse Observability   │
              └──────────────────────────┘
🧩 Technology Stack
Backend
Python 3.12+

FastAPI

Uvicorn

SQLAlchemy

Alembic

PostgreSQL

pgvector

Redis

Agentic AI
LangGraph

LangChain

OpenAI / Azure OpenAI

LlamaIndex

Sentence Transformers

Structured LLM outputs

Code Intelligence
Tree-sitter

Radon

Scalene

SonarQube

GitPython

Retrieval
BM25

Vector search

Hybrid retrieval

Reciprocal Rank Fusion (RRF)

Dependency graph expansion

LLM re-ranking

Frontend
React 19

TypeScript

Vite

Tailwind CSS

React Router

Recharts

Auth0 React SDK

React Markdown

Security & Observability
Auth0

Role-Based Access Control

Microsoft Presidio

Langfuse

📁 Project Structure
.
├── backend/
│   ├── agents/
│   │   ├── analysis/
│   │   │   ├── architecture_agent.py
│   │   │   ├── coverage_agent.py
│   │   │   ├── performance_agent.py
│   │   │   ├── quality_pipeline.py
│   │   │   └── reporter_agent.py
│   │   ├── documentation/
│   │   ├── evaluation/
│   │   ├── guardrail/
│   │   ├── manager/
│   │   └── repository/
│   │
│   ├── api/
│   │   └── routers/
│   │       ├── escalation.py
│   │       ├── executions.py
│   │       ├── ingestion.py
│   │       ├── operational.py
│   │       ├── query.py
│   │       ├── repositories.py
│   │       └── sessions.py
│   │
│   ├── database/
│   ├── ingestion/
│   ├── models/
│   ├── prompts/
│   ├── repositories/
│   ├── retrieval/
│   ├── schemas/
│   ├── services/
│   ├── tools/
│   ├── utils/
│   ├── workflows/
│   │   ├── graphs/
│   │   ├── nodes/
│   │   ├── intent_classifier.py
│   │   ├── router.py
│   │   └── state.py
│   └── main.py
│
├── frontend/
│   └── src/
│       ├── components/
│       ├── context/
│       ├── pages/
│       │   ├── DeveloperDashboard.tsx
│       │   ├── Login.tsx
│       │   └── ManagerDashboard.tsx
│       ├── App.tsx
│       └── main.tsx
│
├── Documents/
│   ├── 01_Secure_Coding_Code_Quality_Guidelines.pdf
│   ├── 02_Performance_Optimization_Handbook.pdf
│   ├── 03_Software_Architecture_Design_Principles.pdf
│   ├── 04_Static_Code_Analysis_Rulebook.pdf
│   ├── 05_Test_Coverage_Quality_Assurance_Guide.pdf
│   ├── 06_DevOps_Performance_Monitoring_Guide.pdf
│   └── 07_Software_Quality_Management_Framework.pdf
│
├── docs/
│   ├── final_documentation.md
│   ├── project_approach.md
│   └── final_readme.md
│
├── tests/
├── .env.example
├── Dockerfile
├── pyproject.toml
└── README.md
🔐 Authentication and Roles
The frontend uses Auth0 authentication and redirects authenticated users to their role-specific dashboard.

Developer
The Developer role is intended for repository analysis and day-to-day code intelligence workflows.

Typical capabilities include:

Repository interaction

Codebase queries

Analysis execution

Quality insights

Retrieval-based investigation

Viewing generated reports

Manager
The Manager role provides additional operational and management functionality.

Manager-only backend routes are protected by role-based authorization.

🖥️ Using the Demo
Step 1 — Open the application
Open:

https://autonomous-code-quality-and-optimization-rg5g.onrender.com/

Step 2 — Sign in
Use one of the demo accounts.

Developer

User ID: user@gmail.com
Password: user@123
Manager

User ID: admin@gmail.com
Password: admin@123
Step 3 — Explore the dashboard
After authentication, the application routes the user to the dashboard associated with the authenticated role.

Step 4 — Try repository/code queries
Example questions:

Give me an overview of this repository.

Analyze the architecture of the backend.

Identify performance bottlenecks.

What are the major code quality issues?

Analyze test coverage and identify weak areas.

Explain the repository structure.

Generate documentation for the selected code.

Perform a comprehensive architecture, coverage and performance analysis.
⚙️ Local Development
Prerequisites
Install:

Python 3.12+

Node.js 20+

uv

PostgreSQL with pgvector

Redis

Git

SonarQube if local quality scanning is required

Backend Setup
git clone <repository-url>
cd <project-directory>

uv sync
Create the environment file:

cp .env.example .env
On Windows PowerShell:

Copy-Item .env.example .env
Update .env with the required database, Redis, LLM, Auth0, Langfuse, Llama and SonarQube settings.

Run database migrations:

uv run alembic upgrade head
Start the backend:

uv run uvicorn backend.main:app --reload --port 8000
Backend API:

http://localhost:8000
FastAPI Swagger:

http://localhost:8000/docs
🎨 Frontend Setup
cd frontend
npm install
npm run dev
The Vite development server normally runs at:

http://localhost:5173
Configure the frontend environment variables according to the Auth0 and backend API configuration used by the deployment.

🧪 Testing and Code Quality
Run the test suite:

uv run pytest tests/
Run Radon complexity analysis:

uv run radon cc backend/ -a -s
Run Scalene profiling:

uv run scalene --html --outfile scalene_report.html backend/main.py
Run Ruff:

uv run ruff check .
🐳 Docker
The project includes a Dockerfile for containerized backend execution.

Build the image:

docker build -t autonomous-code-quality .
Run the container:

docker run --env-file .env -p 8000:8000 autonomous-code-quality
For production deployments, configure the container with the appropriate database, Redis, LLM, authentication, observability and analysis-service endpoints.

🔄 Typical Analysis Flow
A typical end-to-end request follows this sequence:

1. User authenticates
        ↓
2. User submits a code-analysis query
        ↓
3. FastAPI receives the request
        ↓
4. Guardrail validates the query
        ↓
5. Manager determines the workflow
        ↓
6. Repository context is retrieved
        ↓
7. Specialist agents perform analysis
        ↓
8. External quality tools provide measurable evidence
        ↓
9. Reporter generates a grounded response
        ↓
10. Evaluation Agent validates the result
        ↓
11. Result is returned to the user
For high-impact or failed evaluations:

Evaluation Failure
       ↓
Escalation
       ↓
Human Validation
       ↓
Workflow Termination
This design helps reduce unsupported recommendations and provides an explicit quality-control stage.

📚 Knowledge Base
The Documents/ directory contains reference material used by the system's knowledge and analysis workflows, including:

Secure coding

Performance optimization

Software architecture

Static analysis

Test coverage

DevOps performance monitoring

Software quality management

These documents can be ingested into the system's retrieval layer to provide additional domain-specific context.

🔭 Design Principles
The project follows several core principles:

Evidence Before Generation
LLMs should generate recommendations from retrieved code and measurable analysis results rather than inventing repository facts.

Specialized Agents
Each major responsibility is separated into an agent instead of relying on a single general-purpose prompt.

Deterministic Quality Checks
Where possible, objective tools such as SonarQube, Radon and coverage reports are used to supplement LLM reasoning.

Hybrid Retrieval
Keyword and semantic retrieval are combined to improve recall for both natural-language questions and exact source-code references.

Safety First
Guardrails, validation and escalation are included before allowing analysis results to be treated as final.

Observability
Agent and workflow execution can be traced to make the system easier to debug, evaluate and improve.

📖 Documentation
Additional project documentation is available in the docs/ directory:

docs/final_documentation.md — detailed project documentation

docs/project_approach.md — project approach and implementation details

docs/final_readme.md — previous project overview

Documents/ — domain-specific quality and engineering reference documents

⚠️ Demo Security Notice
The credentials in this README are demo credentials intentionally provided for evaluation/testing.

Do not use these credentials for production systems.

For production deployments:

Use strong unique credentials.

Never commit secrets to Git.

Store credentials in a secure secret manager.

Restrict Auth0 callback/logout URLs.

Restrict backend CORS origins.

Rotate exposed demo credentials when necessary.

Use production-specific database and API credentials.
