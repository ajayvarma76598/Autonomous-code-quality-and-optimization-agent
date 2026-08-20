# Autonomous Code Quality & Optimization Intelligence System

An advanced, AI-driven multi-agent platform designed to analyze source code repositories, identify architectural and performance bottlenecks, and generate intelligent refactoring and documentation suggestions.

## 🌟 Key Features

*   **Multi-Agent Orchestration**: Utilizes a supervisor-worker architecture (powered by LangGraph) to dynamically route tasks to specialized analysis agents.
*   **Deep Repository Analysis**: Employs semantic Vector Search (RAG) and Abstract Syntax Tree (AST) parsing via Tree-sitter for context-aware code understanding.
*   **Automated Quality & Performance Metrics**: Integrates with industry-standard tools (Radon, Scalene, SonarQube) to surface Cyclomatic Complexity, Memory leaks, and CPU bottlenecks.
*   **Intelligent Documentation Generation**: Automatically generates and updates docstrings and inline documentation while safely parsing and reconstructing code.
*   **Built-in Guardrails & Safety**: Implements strict data privacy (PII scrubbing) and validation checks before returning code suggestions.
*   **Interactive Dashboards**: Features a modern React/Vite frontend with role-based access (Manager vs Developer views) integrated with Auth0.

## 🏗️ System Architecture

The system is split into two core layers:
1.  **Frontend**: A React application bootstrapped with Vite, styled with Tailwind CSS, providing visual dashboards.
2.  **Backend API & Services**: A Python FastAPI application that handles REST endpoints, orchestrates the LLM-powered Multi-Agent system, and manages database interactions (SQL/Vector).

For a detailed view of the multi-agent workflow and component structure, see the architecture diagram in the documentation present in /docs.

### Tech Stack
*   **Backend Core**: Python 3.12+, FastAPI, Uvicorn, SQLAlchemy, Alembic
*   **AI / Agents**: LangGraph, LangChain, OpenAI, HuggingFace (SentenceTransformers)
*   **Parsing & Analysis**: Tree-sitter, Radon, Scalene
*   **Databases**: PostgreSQL with `pgvector`, Redis (for caching)
*   **Frontend**: React 19, Vite, Tailwind CSS, Recharts, Auth0

---

## 🚀 Getting Started

### Prerequisites
*   [Python 3.12+](https://www.python.org/)
*   [Node.js 20+](https://nodejs.org/)
*   [uv](https://github.com/astral-sh/uv) (Extremely fast Python package installer and resolver)
*   PostgreSQL (with `pgvector` extension)
*   Redis (Running locally or via Docker)

### 1. Clone the Repository
```bash
git clone <your-repository-url>
cd "Project-5-Autonomous Code Quality & Optimization System"
```

### 2. Backend Setup
The backend utilizes `uv` for lightning-fast dependency management.

```bash
# Sync dependencies and create a virtual environment automatically
uv sync

# Activate the virtual environment
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

# Set up environment variables
cp .env.example .env
# Edit .env and provide your OPENAI_API_KEY, Database URLs, and Redis URLs.

# Run database migrations
alembic upgrade head

# Start the FastAPI Development Server
uvicorn backend.main:app --reload --port 8000
```
*The API will be accessible at `http://localhost:8000` and Swagger docs at `http://localhost:8000/docs`.*

### 3. Frontend Setup
```bash
# Navigate to the frontend directory
cd frontend

# Install JavaScript dependencies
npm install

# Configure Auth0 and API Endpoints
cp .env.example .env
# Ensure VITE_API_URL is pointed to your backend (e.g., http://localhost:8000)

# Start the Vite development server
npm run dev
```
*The application UI will be accessible at `http://localhost:5173`.*

---

## 🛠️ Usage & Workflows

1. **Upload / Select Repository**: Through the frontend dashboard, you can connect a Git repository or analyze the currently tracked codebase.
2. **Submit a Query**: Ask the system an open-ended question like:
   > *"Analyze `backend/services/` for performance bottlenecks and suggest refactoring."*
3. **Agentic Orchestration**: The `ManagerAgent` intercepts the query, determines it requires a `parallel_analysis` workflow, and dispatches the **Performance**, **Coverage**, and **Architecture** agents simultaneously.
4. **Review Suggestions**: Once the Evaluation Agent validates the output, the frontend renders actionable code snippets, architecture metrics, and direct links to the flagged files.

## 🧪 Running Tests & Quality Checks
```bash
# Run pytest test suite
uv run pytest tests/

# Run static complexity analysis using Radon
uv run radon cc backend/ -a -s

# Profile performance using Scalene (e.g., profiling the main entry point)
uv run scalene --html --outfile scalene_report.html backend/main.py
```

## 🔐 Security & Compliance
*   **Authentication**: Secured by Auth0 with Role-Based Access Control (RBAC). Admin/Manager accounts have distinct visualization privileges from standard Developer accounts.
*   **PII Filtering**: A Guardrail agent intercepts all payloads utilizing `presidio-analyzer` to ensure zero accidental PII leakage in LLM API calls. 

---
*This project was developed as a comprehensive Capstone focusing on Agentic AI workflows, semantic retrieval, and software intelligence.*


**For complete documentation and other details regarding the codebase please check the /docs folder**