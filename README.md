````markdown
# 🚀 Autonomous Code Quality & Optimization Intelligence System

An AI-powered **Agentic Software Engineering platform** that autonomously analyzes software repositories, identifies code-quality and performance issues, evaluates software architecture, analyzes test coverage, and generates evidence-grounded optimization recommendations.

The system combines **Agentic AI, LangGraph, Retrieval-Augmented Generation (RAG), hybrid retrieval, static code analysis, performance profiling, test coverage analysis, and software-quality metrics** to provide developers and engineering managers with an intelligent code-quality assistant.

The core principle of the system is:

> **Analyze → Retrieve Evidence → Reason → Evaluate → Respond**

---

# 🌐 Live Demo

## 🔗 Try the Application

### **[Open Autonomous Code Quality & Optimization System](https://autonomous-code-quality-and-optimization-rg5g.onrender.com/)**

You can directly access the deployed application and explore the system using the demo accounts below.

---

## 🔐 Demo Credentials

### 👨‍💻 Developer Account

```text
User ID:  user@gmail.com
Password: user@123
````

### 👨‍💼 Manager Account

```text
User ID:  admin@gmail.com
Password: admin@123
```

| Role            | User ID           | Password    |
| --------------- | ----------------- | ----------- |
| 👨‍💻 Developer | `user@gmail.com`  | `user@123`  |
| 👨‍💼 Manager   | `admin@gmail.com` | `admin@123` |

> **Note:** These credentials are provided specifically for project demonstration and evaluation.

---

# 🎯 What Does This Project Do?

The system acts as an **AI-powered software engineering assistant** capable of understanding and analyzing a complete software repository.

Instead of simply sending source code to an LLM and asking for an opinion, the platform combines multiple sources of engineering evidence:

* Repository source code
* AST-based code analysis
* Semantic search
* BM25 keyword retrieval
* Dependency relationships
* SonarQube metrics
* Test coverage
* Radon complexity analysis
* Scalene performance profiling
* Software architecture analysis
* Engineering knowledge documents

The retrieved evidence is then provided to specialized AI agents that reason about the repository and generate actionable recommendations.

---

# ⭐ Why This Project?

Traditional code-quality tools provide metrics and static-analysis results, while LLM-based coding assistants provide natural-language reasoning.

This project combines both approaches.

```text
Traditional Software Analysis
            +
Repository Understanding
            +
Hybrid RAG
            +
Agentic AI
            +
Quality Evaluation
            ↓
Evidence-Grounded Code Intelligence
```

The goal is to move beyond simple AI code generation toward **autonomous, evidence-driven software engineering analysis**.

---

# ✨ Key Features

### 🤖 Multi-Agent AI

Specialized agents are responsible for different software-engineering tasks such as:

* Repository analysis
* Architecture analysis
* Performance analysis
* Test coverage analysis
* Documentation
* Code-quality analysis
* Report generation

### 🧠 LangGraph Orchestration

LangGraph is used to coordinate the multi-agent workflow and control the execution path based on the user's request.

### 🔎 Hybrid RAG

The retrieval layer combines:

* Vector semantic search
* BM25 keyword search
* Reciprocal Rank Fusion (RRF)
* Dependency graph expansion
* Result diversification
* LLM-based re-ranking

### 📊 Code Quality Analysis

The platform integrates:

* SonarQube
* Radon
* Scalene
* Test coverage
* Static analysis
* Architecture analysis

### 🛡️ AI Guardrails

Guardrails help detect:

* Prompt injection
* Malicious requests
* Destructive operations
* Requests for secrets
* Unsafe actions
* Irrelevant requests

### ✅ Evaluation Agent

AI-generated analysis is evaluated before being returned as a final result.

### 👤 Human Escalation

When an analysis does not satisfy the evaluation criteria, the system can escalate the result for human validation.

### 🔐 Authentication & RBAC

Auth0 is used for authentication and role-based access.

The system provides separate experiences for:

* Developer
* Manager

### 📈 Observability

Langfuse provides visibility into:

* Agent execution
* LLM calls
* Workflow transitions
* Query sessions
* Execution time
* Evaluation information
* Trace information

---

# 🧠 Agentic AI Workflow

A typical request follows this workflow:

```text
                         User Query
                              │
                              ▼
                    ┌──────────────────┐
                    │  Guardrail Agent │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │  Manager Agent   │
                    └────────┬─────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
        Repository      Architecture    Performance
          Agent            Agent           Agent
              │              │              │
              └──────────────┼──────────────┘
                             │
              ┌──────────────┴──────────────┐
              │                             │
              ▼                             ▼
        Coverage Agent              Documentation Agent
              │                             │
              └──────────────┬──────────────┘
                             │
                             ▼
                  ┌─────────────────────┐
                  │ Quality Analysis    │
                  │ Pipeline            │
                  └──────────┬──────────┘
                             │
                             ▼
                  ┌─────────────────────┐
                  │ Evaluation Agent    │
                  └──────────┬──────────┘
                             │
                    ┌────────┴────────┐
                    │                 │
                   PASS              FAIL
                    │                 │
                    ▼                 ▼
             Final Response      Escalation
                                      │
                                      ▼
                              Human Validation
```

---

# 🔎 Hybrid RAG Architecture

The system uses multiple retrieval strategies to improve repository understanding.

```text
                         User Query
                             │
                             ▼
                    Intent Detection
                             │
                             ▼
                       Query Expansion
                             │
                ┌────────────┴────────────┐
                │                         │
                ▼                         ▼
       BM25 Keyword Search       Vector Semantic Search
                │                         │
                └────────────┬────────────┘
                             │
                             ▼
                  Dependency Graph Expansion
                             │
                             ▼
                       RRF Fusion
                             │
                             ▼
                      Diversification
                             │
                             ▼
                       LLM Re-ranking
                             │
                             ▼
                       Top-K Evidence
                             │
                             ▼
                       Agent Reasoning
```

This approach allows the system to retrieve:

* Relevant source files
* Functions
* Classes
* Exact code symbols
* Related documentation
* Dependencies
* Semantically similar code
* Architecture-related components

---

# 📊 Code Quality & Performance Analysis

## SonarQube

SonarQube is used for:

* Bugs
* Vulnerabilities
* Code smells
* Complexity
* Maintainability
* Quality gates
* Static code analysis

## Radon

Radon is used for Python code-quality metrics such as:

* Cyclomatic complexity
* Maintainability index
* Halstead metrics
* Code complexity

## Scalene

Scalene is used for Python performance profiling:

* CPU usage
* Memory usage
* Line-level performance
* Performance bottlenecks

## Test Coverage

The system can analyze test coverage and identify areas of the repository that require additional testing.

---

# 🛡️ Guardrails & Safety

The Guardrail Agent runs before the main analysis workflow.

The system is designed to identify and prevent:

```text
Prompt Injection
       │
       ▼
Malicious Requests
       │
       ▼
Unsafe Operations
       │
       ▼
Secret / Credential Requests
       │
       ▼
Destructive Actions
```

Additional PII protection capabilities are supported through Microsoft Presidio components.

---

# ✅ Evaluation & Human Escalation

The Evaluation Agent acts as a quality gate.

```text
Agent Analysis
      │
      ▼
Evaluation Agent
      │
      ├──────────────► PASS
      │                 │
      │                 ▼
      │            Final Response
      │
      └──────────────► FAIL
                        │
                        ▼
                   Escalation
                        │
                        ▼
                 Human Validation
```

This helps reduce unsupported or low-quality autonomous recommendations.

---

# 👥 Role-Based Access

## 👨‍💻 Developer

The Developer dashboard is designed for software-development workflows.

Typical capabilities include:

* Repository analysis
* Codebase queries
* Code-quality analysis
* Performance analysis
* Test coverage analysis
* Architecture analysis
* AI-powered repository investigation
* Generated reports

### Developer Demo

```text
User ID:  user@gmail.com
Password: user@123
```

---

## 👨‍💼 Manager

The Manager dashboard provides additional management and operational functionality.

Typical capabilities include:

* Repository overview
* Quality metrics
* Operational monitoring
* Execution monitoring
* System-level insights
* Escalation visibility

### Manager Demo

```text
User ID:  admin@gmail.com
Password: admin@123
```

---

# 🏗️ System Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│                     React Frontend                          │
│                  Vite + TypeScript                          │
│                                                             │
│     Login │ Developer Dashboard │ Manager Dashboard         │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           │ REST API
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Backend                           │
│                                                             │
│ Authentication │ Repository │ Query │ Sessions              │
│ Executions │ Ingestion │ Operational │ Escalation            │
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
              │ Redis                    │
              │ Langfuse                 │
              └──────────────────────────┘
```

---

# 🧩 Technology Stack

## Backend

* Python 3.12+
* FastAPI
* Uvicorn
* SQLAlchemy
* Alembic
* PostgreSQL
* pgvector
* Redis

## Agentic AI

* LangGraph
* LangChain
* OpenAI / Azure OpenAI
* LlamaIndex
* Sentence Transformers
* Structured LLM Outputs

## Code Intelligence

* Tree-sitter
* SonarQube
* Radon
* Scalene
* GitPython

## Retrieval

* BM25
* Vector Search
* Hybrid Retrieval
* Reciprocal Rank Fusion
* Dependency Graph Expansion
* LLM Re-ranking

## Frontend

* React
* TypeScript
* Vite
* Tailwind CSS
* React Router
* Recharts
* Auth0 React SDK
* React Markdown

## Security & Observability

* Auth0
* Role-Based Access Control
* Microsoft Presidio
* Langfuse

---

# 📁 Project Structure

```text
.
├── backend/
│   ├── agents/
│   │   ├── analysis/
│   │   │   ├── architecture_agent.py
│   │   │   ├── coverage_agent.py
│   │   │   ├── performance_agent.py
│   │   │   ├── quality_pipeline.py
│   │   │   └── reporter_agent.py
│   │   │
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
│   │
│   ├── workflows/
│   │   ├── graphs/
│   │   ├── nodes/
│   │   ├── intent_classifier.py
│   │   ├── router.py
│   │   └── state.py
│   │
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
```

---

# 🔄 End-to-End Workflow

A typical analysis request follows this process:

```text
1. User Authentication
        ↓
2. User submits analysis request
        ↓
3. FastAPI receives request
        ↓
4. Guardrail validates request
        ↓
5. Manager determines workflow
        ↓
6. Repository context is retrieved
        ↓
7. Specialist agents perform analysis
        ↓
8. Static-analysis tools provide evidence
        ↓
9. Reporter generates grounded response
        ↓
10. Evaluation Agent validates result
        ↓
11. Final response returned to user
```

---

# 🖥️ Example Queries

After logging into the demo, try questions such as:

```text
Give me an overview of this repository.

Analyze the architecture of the backend.

Identify potential performance bottlenecks.

What are the major code-quality issues?

Analyze test coverage and identify weak areas.

Identify functions with high complexity.

What are the most important SonarQube findings?

Explain the repository structure.

What parts of this codebase should be refactored?

How can the performance of this application be improved?

Perform a comprehensive architecture, coverage and performance analysis.
```

---

# ⚙️ Local Development

## Prerequisites

Install:

* Python 3.12+
* Node.js 20+
* Git
* uv
* PostgreSQL
* pgvector
* Redis
* Docker
* SonarQube (optional for local quality analysis)

---

# 🔧 Backend Setup

Clone the repository:

```bash
git clone <repository-url>
cd <project-directory>
```

Install Python dependencies:

```bash
uv sync
```

Create the environment file.

### Windows PowerShell

```powershell
Copy-Item .env.example .env
```

### Linux / macOS

```bash
cp .env.example .env
```

Configure the required environment variables in `.env`.

Example:

```text
DATABASE_URL=
REDIS_URL=

AUTH0_DOMAIN=
AUTH0_CLIENT_ID=
AUTH0_CLIENT_SECRET=
API_AUDIENCE=

OPENAI_API_KEY=

AZURE_OPENAI_API_KEY=
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_LLM_DEPLOYMENT=

LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
LANGFUSE_HOST=

SONAR_HOST_URL=
SONAR_TOKEN=
```

Run database migrations:

```bash
uv run alembic upgrade head
```

Start the backend:

```bash
uv run uvicorn backend.main:app --reload --port 8000
```

Backend:

```text
http://localhost:8000
```

Swagger API documentation:

```text
http://localhost:8000/docs
```

---

# 🎨 Frontend Setup

Move into the frontend directory:

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

Start the development server:

```bash
npm run dev
```

The frontend will normally be available at:

```text
http://localhost:5173
```

Configure the required frontend environment variables for:

* Backend API
* Auth0 domain
* Auth0 client ID
* API audience
* Redirect URLs

---

# 🐳 Docker

Build the backend image:

```bash
docker build -t autonomous-code-quality .
```

Run the container:

```bash
docker run --env-file .env -p 8000:8000 autonomous-code-quality
```

Docker can also be used to provide isolated environments for language-specific code-analysis workers.

---

# 🧪 Testing & Code Quality

Run the test suite:

```bash
uv run pytest tests/
```

Run Ruff:

```bash
uv run ruff check .
```

Run Radon:

```bash
uv run radon cc backend/ -a -s
```

Run Scalene:

```bash
uv run scalene --html --outfile scalene_report.html backend/main.py
```

---

# 📚 Knowledge Base

The project contains engineering and software-quality reference documents that can be used by the retrieval system.

The knowledge base covers areas including:

* Secure coding
* Code quality
* Performance optimization
* Software architecture
* Static code analysis
* Test coverage
* DevOps performance monitoring
* Software quality management

These documents provide additional domain knowledge for the AI agents.

---

# 📈 Observability

Langfuse is used to provide visibility into the Agentic AI workflow.

Observability can include:

* Agent traces
* LLM calls
* Workflow transitions
* Query sessions
* Execution duration
* Agent routing
* Evaluation results

This allows the system to be monitored and debugged throughout the entire agentic workflow.

---

# 🎯 Design Principles

## Evidence Before Generation

AI-generated recommendations should be grounded in actual repository data, retrieved source code and measurable quality metrics.

## Specialized Agents

Different software-engineering responsibilities are separated into specialized agents rather than relying on one general-purpose AI prompt.

## Deterministic Quality Checks

Traditional engineering tools such as SonarQube, Radon, Scalene and test coverage provide objective evidence alongside LLM reasoning.

## Hybrid Retrieval

Keyword and semantic retrieval are combined to improve accuracy for both natural-language questions and exact source-code references.

## Safety First

Guardrails, evaluation and escalation mechanisms reduce unsafe or unsupported autonomous actions.

## Observability

Agent and workflow execution can be monitored to support debugging, evaluation and continuous improvement.

---

# 📖 Documentation

Additional documentation can be found in the `docs/` directory.

```text
docs/
├── final_documentation.md
├── project_approach.md
└── final_readme.md
```

The `Documents/` directory contains additional software-engineering and code-quality reference material.

---

# 🚀 Future Enhancements

Potential future improvements include:

* Additional programming-language support
* Automated pull-request analysis
* Automated code-fix generation
* GitHub/GitLab integration
* Continuous repository monitoring
* Automated quality-regression detection
* Advanced dependency vulnerability analysis
* Cross-repository architecture analysis
* Advanced performance profiling
* Automated refactoring suggestions
* Human-in-the-loop approval workflows
* CI/CD quality-gate integration

---

# ⚠️ Demo Security Notice

The credentials included in this README are **demo credentials intentionally provided for project evaluation**.

They should **not** be used for production systems.

For production deployments:

* Use strong unique credentials.
* Never commit production secrets to Git.
* Store secrets using a secure secret manager.
* Rotate exposed credentials when necessary.
* Restrict Auth0 callback URLs.
* Restrict Auth0 logout URLs.
* Restrict CORS origins.
* Use production-specific API keys.
* Use production-specific database credentials.
* Enable appropriate monitoring and audit logging.

---

# 🏆 Project Summary

The **Autonomous Code Quality & Optimization Intelligence System** demonstrates how **Agentic AI, RAG, static analysis, performance profiling, software-quality metrics and workflow orchestration** can be combined into a practical software-engineering platform.

The system moves beyond simple AI code generation toward:

> **Autonomous, evidence-driven repository understanding and software-quality optimization.**

---
