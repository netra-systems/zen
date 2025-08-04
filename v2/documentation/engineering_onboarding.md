
# Engineering Onboarding: Netra AI Workload Optimization Platform

## 1. High-Level Overview

Welcome to the Netra AI Workload Optimization Platform. This document provides a comprehensive overview of the project, its architecture, and how to get started.

**What is this project?**

This project is a sophisticated platform for optimizing AI workloads. It acts as an intelligent intermediary between applications that need AI models and the various available AI model providers (both commercial APIs and self-hosted models). Its core purpose is to route AI requests to the most suitable model based on a multi-objective analysis of cost, performance (latency), and risk/quality.

**Core Technologies:**

*   **Backend:** Python with the **FastAPI** framework.
*   **Frontend:** TypeScript with the **Next.js** (React) framework.
*   **Databases:**
    *   **PostgreSQL:** Used for storing persistent application data like user accounts, analysis run records, and the supply catalog configuration.
    *   **ClickHouse:** A high-performance columnar database used for storing and analyzing large volumes of log data, including AI workload events and performance metrics.
*   **AI/ML:**
    *   **DeepAgents:** A custom-built framework (located in the `deepagents` directory) that uses a graph-based approach with language models to perform complex analysis and decision-making.
    *   **Sentence-Transformers:** Used for creating semantic vector embeddings of text prompts.

## 2. Architecture and Data Flow

The system is composed of several key components that work together to provide its core functionality.

![Architecture Diagram](https://i.imgur.com/your-diagram-image.png)  <!-- Placeholder for a diagram -->

### 2.1. Key Components

1.  **Frontend (`/frontend`)**
    *   A Next.js single-page application (SPA) that provides the user interface for interacting with the platform.
    *   Users can log in, view the supply catalog, trigger analysis runs, and see the results.
    *   It communicates with the backend via a REST API.

2.  **Backend API (`/app`)**
    *   The core of the application, built with FastAPI.
    *   **`main.py`:** The main entry point of the application. It initializes the FastAPI app, sets up middleware (CORS, sessions), and includes the API routers.
    *   **`routes/`:** This directory contains the API endpoints, logically separated by function (e.g., `auth.py`, `supply.py`, `analysis.py`).
    *   **`services/`:** Contains the business logic for various features. For example, `generation_service.py` handles the creation of synthetic data, and `analysis_runner.py` orchestrates the analysis pipeline.
    *   **`db/`:** Manages database connections and data models.
        *   `postgres.py` and `models_postgres.py`: Handle the connection and SQLAlchemy models for PostgreSQL.
        *   `clickhouse.py` and `models_clickhouse.py`: Handle the connection and table schemas for ClickHouse.

3.  **The Sentient Fabric (Core Logic in `app/core/`)**
    *   This is the "brain" of the platform, a conceptual framework for the intelligent routing and optimization process. It consists of several interconnected components:
    *   **Demand Analyzer (`demand_analyzer.py`):** Ingests raw requests (a prompt and metadata) and enriches them into a structured **Workload Profile**. This profile captures the semantic meaning, performance requirements (SLOs), and risk factors of the request.
    *   **Supply Catalog (`supply_catalog.py`):** A dynamic, in-memory registry of all available AI models (supply options). It stores their technical specs, cost, and, most importantly, real-time performance and quality data.
    *   **Multi-Objective Controller (`controller.py`):** The decision-making core. It takes a Workload Profile and the current state of the Supply Catalog and identifies the best-fit models. It doesn't just find one "best" model but rather a set of "Pareto-optimal" solutions, making the trade-offs between cost, latency, and quality explicit.
    *   **Execution Fabric (`execution_fabric.py`):** Takes the decision from the Controller and executes the workload on the chosen model. It then captures the real-world performance metrics from this execution.
    *   **Observability Plane (`observability.py`):** This component "closes the loop." It receives the results from the Execution Fabric, runs quality checks (e.g., using an LLM-as-a-judge), and feeds the updated performance and quality data back into the Supply Catalog. This ensures the system learns and adapts over time.

4.  **DeepAgents (`/deepagents`)**
    *   A more advanced analysis engine that uses a graph of interconnected, tool-using AI agents to perform a deep analysis of workload patterns and recommend optimization strategies. This is used for more complex, offline analysis runs.

### 2.2. Data Flow Example: A Single AI Request

1.  A user interacts with the **Frontend**, submitting a prompt to be processed.
2.  The Frontend sends a request to the **Backend API** (e.g., to an endpoint in `app/routes/v3.py`).
3.  The **Demand Analyzer** receives the raw prompt and creates a detailed `WorkloadProfile`.
4.  The **Multi-Objective Controller** takes this profile and queries the **Supply Catalog** for all suitable, certified models.
5.  The Controller predicts the cost, latency, and risk for the workload on each viable model and identifies the optimal choices.
6.  Based on a predefined utility function (e.g., "I care most about cost"), the Controller selects a single model.
7.  The **Execution Fabric** sends the prompt to the selected model's actual endpoint (or a mock in simulation).
8.  The model returns a response. The Execution Fabric records how long it took (TTFT, TPOT).
9.  The response and the performance metrics are sent to the **Observability Plane**.
10. The Observability Plane's "Automated Quality Judge" assesses the response for things like hallucinations or toxicity.
11. The Observability Plane updates the **Supply Catalog** with the newly observed latency and quality scores for that model.
12. The final response is sent back through the API to the **Frontend** and displayed to the user.

## 3. Codebase Hierarchy

This is a breakdown of the most important directories and files:

```
.
├── app/                  # Main FastAPI backend application
│   ├── core/             # The "Sentient Fabric" - core optimization logic
│   ├── data/             # Data ingestion and synthetic data generation scripts
│   ├── db/               # Database models and connection logic
│   ├── deepagents/       # The DeepAgents analysis framework
│   ├── routes/           # API endpoint definitions
│   ├── services/         # Business logic for API endpoints
│   ├── __init__.py
│   ├── main.py           # FastAPI application entrypoint
│   └── ...
├── config.yaml           # Configuration for synthetic data generation
├── create_db.py          # Script to create the initial PostgreSQL database
├── documentation/        # Project documentation (you are here!)
│   └── engineering_onboarding.md
├── frontend/             # Next.js frontend application
│   ├── app/              # Main application pages and components
│   ├── public/           # Static assets (images, etc.)
│   ├── package.json      # Frontend dependencies
│   └── ...
├── manual/               # Manual scripts for testing and data ingestion
├── run_migrations.py     # Script to run database schema migrations (Alembic)
├── tests/                # Backend tests
└── ...
```

## 4. Mature vs. Developing Areas

*   **Mature & Stable:**
    *   **User Authentication (`app/routes/auth.py`, `app/services/security_service.py`):** The user login and session management system is well-defined and robust.
    *   **Supply Catalog (`app/routes/supply.py`, `app/services/supply_catalog_service.py`):** The basic CRUD operations for managing the list of AI models are stable.
    *   **Core FastAPI Application (`app/main.py`):** The application setup, middleware, and basic structure are well-established.
    *   **Database Setup (`create_db.py`, `run_migrations.py`):** The process for initializing the database is standardized.

*   **Under Active Development:**
    *   **The Sentient Fabric (`app/core/`):** This is the core innovation of the project and is constantly being refined. The predictive models and optimization algorithms are subject to change and improvement. The `v3_simulation.py` file represents the latest thinking in this area.
    *   **DeepAgents (`app/deepagents/`, `app/services/engine_deepagents_v2.py`):** This is an advanced, experimental feature. The structure of the agent graph, the tools they use, and the prompts that define them are all evolving.
    *   **Data Generation & Ingestion (`app/services/generation_service.py`, `app/data/`):** As the analysis capabilities become more sophisticated, the requirements for the synthetic data used for testing and validation will also change.
    *   **Frontend UI/UX (`frontend/`):** The frontend is functional but will continue to evolve to better visualize the complex data and analysis results produced by the backend.

## 5. Getting Started: Local Development Setup

Follow these steps to get the project running on your local machine.

### 5.1. Prerequisites

*   **Python** (version 3.10 or higher)
*   **Node.js** (version 18 or higher)
*   **PostgreSQL:** A running PostgreSQL server.
*   **Docker** (Optional, but recommended for running ClickHouse)

### 5.2. Backend Setup

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd <repository-directory>
    ```

2.  **Set up a Python virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3.  **Install Python dependencies:**
    *The project's dependencies are not explicitly listed in a single `requirements.txt` in the root. You will need to install them as you encounter import errors, starting with the main ones.*
    ```bash
    pip install fastapi "uvicorn[standard]" sqlalchemy psycopg2-binary pydantic-settings python-jose[cryptography] passlib[bcrypt] alembic clickhouse-driver pandas
    ```

4.  **Configure Environment Variables:**
    *   Create a file named `.env` in the `app/` directory (`app/.env`).
    *   Add the following required variables. You will need to get the Google credentials from the Google Cloud Console.
    ```
    GEMINI_API_KEY="your-gemini-api-key"
    GOOGLE_CLIENT_ID="your-google-client-id.apps.googleusercontent.com"
    GOOGLE_CLIENT_SECRET="your-google-client-secret"
    ```

5.  **Set up the Databases:**
    *   **PostgreSQL:**
        *   Make sure your PostgreSQL server is running.
        *   Run the `create_db.py` script to create the `netra` database:
            ```bash
            python create_db.py
            ```
        *   Run the database migrations to create the tables:
            ```bash
            python run_migrations.py
            ```
    *   **ClickHouse:**
        *   The easiest way to run ClickHouse is with Docker.
            ```bash
            docker run -d -p 8123:8123 -p 9000:9000 --name netra-clickhouse --ulimit nofile=262144:262144 yandex/clickhouse-server
            ```

6.  **Run the Backend Server:**
    ```bash
    uvicorn app.main:app --reload --port 8000
    ```
    The backend API should now be running at `http://localhost:8000`.

### 5.3. Frontend Setup

1.  **Navigate to the frontend directory:**
    ```bash
    cd frontend
    ```

2.  **Install Node.js dependencies:**
    ```bash
    npm install
    ```

3.  **Run the Frontend Development Server:**
    ```bash
    npm run dev
    ```
    The frontend application should now be running at `http://localhost:3000`.

### 5.4. Running Tests

To run the backend tests, use `pytest`:

```bash
pytest
```

This will discover and run all the tests in the `tests/` directory.

---
This document should provide a solid foundation for any new engineer joining the team. As the project evolves, please feel free to update this guide.
