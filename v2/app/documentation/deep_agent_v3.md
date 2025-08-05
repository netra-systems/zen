
# DeepAgentV3 Documentation

## 1. High-Level Overview

DeepAgentV3 is a stateful, step-by-step agent designed for in-depth analysis of LLM usage. Its primary goal is to provide a flexible and extensible framework for identifying optimization opportunities, simulating their impact, and generating actionable reports. The system is built to be interactive, allowing for human-in-the-loop control and monitoring.

The key objectives of DeepAgentV3 are:

*   **Cost Reduction:** Analyze LLM usage to identify and propose cost-saving measures.
*   **Performance Optimization:** Identify and address latency bottlenecks and other performance issues.
*   **Usage Analysis:** Understand and model usage patterns to predict the impact of future growth.
*   **Extensibility:** Provide a modular architecture that allows for the easy addition of new analysis scenarios, tools, and steps.

## 2. System Architecture

DeepAgentV3 follows a pipeline-based architecture, where a series of steps are executed in a predefined order to complete an analysis. The main components of the system are:

*   **DeepAgentV3 (main.py):** The main class that orchestrates the entire analysis process. It initializes the agent, manages its state, and executes the pipeline.
*   **Pipeline (pipeline.py):**  A generic pipeline that takes a list of steps and executes them sequentially. It handles retries and error handling.
*   **State (state.py):** A Pydantic model that represents the agent's state. It stores all the data generated during the analysis, such as logs, patterns, policies, and reports.
*   **ScenarioFinder (scenario_finder.py):**  Determines the appropriate analysis scenario based on the user's request. Scenarios are predefined sequences of steps designed to address specific optimization goals.
*   **Scenarios (scenarios.py):**  A collection of predefined analysis scenarios. Each scenario consists of a name, a description, and a list of steps to be executed.
*   **Steps (steps.py):** A dictionary that maps step names to their corresponding functions. These functions implement the actual analysis logic.
*   **ToolBuilder (tool_builder.py):**  A factory class that creates and provides the tools used by the analysis steps.
*   **Tools:** A collection of classes that provide specific functionalities, such as fetching logs, identifying patterns, and simulating policies.

The following diagram illustrates the high-level data flow:

```
+-----------------+      +-----------------+      +-----------------+
| User Request    |----->| ScenarioFinder  |----->|    Pipeline     |
+-----------------+      +-----------------+      +-----------------+
                                                     |
                                                     |
                                                     v
+-----------------+      +-----------------+      +-----------------+
|      Step 1     |----->|      Step 2     |----->|      Step n     |
+-----------------+      +-----------------+      +-----------------+
       |                      |                      |
       |                      |                      |
       v                      v                      v
+-----------------------------------------------------------------+
|                             State                               |
+-----------------------------------------------------------------+
```

## 3. Component Deep Dive

### 3.1. DeepAgentV3 (main.py)

The `DeepAgentV3` class is the entry point for running an analysis. It is responsible for:

*   **Initialization:**  Initializes the agent's state, Langfuse for tracing, the tools, and the pipeline.
*   **Execution:**  Provides methods for running the entire analysis (`run_full_analysis`) or executing the next step (`run_next_step`).
*   **State Management:**  Manages the agent's state and records the history of each step.
*   **Reporting:** Generates a markdown report of the entire run and saves it to the database.

### 3.2. Pipeline (pipeline.py)

The `Pipeline` class is a generic and reusable component that executes a list of steps in sequence. Its key features are:

*   **Sequential Execution:**  Executes the steps in the order they are provided.
*   **State Management:**  Passes the agent's state to each step, allowing them to access and modify it.
*   **Tool Injection:**  Injects the required tools into each step based on their function signature.
*   **Error Handling:**  Implements a retry mechanism with exponential backoff to handle transient errors.

### 3.3. State (state.py)

The `AgentState` class is a Pydantic model that defines the structure of the agent's state. It is designed to be a single source of truth for all the data generated during the analysis. The state is passed to each step, which can read from and write to it.

The state is divided into several sections, each corresponding to a different stage of the analysis:

*   `request`: The initial analysis request.
*   `raw_logs`: The raw logs fetched from the database.
*   `patterns`: The patterns discovered in the logs.
*   `policies`: The policies proposed to address the discovered patterns.
*   `cost_comparison`: A comparison of the costs before and after applying the proposed policies.
*   `final_report`: The final markdown report of the analysis.

### 3.4. ScenarioFinder (scenario_finder.py) and Scenarios (scenarios.py)

The `ScenarioFinder` is responsible for selecting the most appropriate analysis scenario based on the user's request. It uses a language model to match the user's prompt with the descriptions of the available scenarios.

The `scenarios.py` file defines a collection of predefined scenarios. Each scenario is a dictionary that contains:

*   `name`: The name of the scenario.
*   `description`: A brief description of the scenario's purpose.
*   `steps`: A list of step names to be executed for the scenario.

This architecture allows for the easy addition of new scenarios without modifying the core logic of the agent.

### 3.5. Steps (steps.py) and Tools

The `steps.py` file is a central registry that maps step names to their corresponding functions. These functions are the building blocks of the analysis pipelines. They are designed to be modular and reusable, and they can be combined in different ways to create new scenarios.

The steps use a collection of tools to perform their tasks. The tools are located in the `tools` directory and are organized by their functionality. Some of the key tools include:

*   `LogFetcher`: Fetches logs from ClickHouse.
*   `LogPatternIdentifier`: Identifies patterns in the logs using a language model.
*   `PolicyProposer`: Proposes policies to address the discovered patterns.
*   `PolicySimulator`: Simulates the impact of the proposed policies on cost and performance.
*   `SupplyCatalogSearch`: Searches the supply catalog for available models and their specifications.
*   `CostEstimator`: Estimates the cost of running a given workload.
*   `PerformancePredictor`: Predicts the performance of a given workload.

## 4. Codebase Maturity

The DeepAgentV3 codebase is a mix of mature and developing components.

### 4.1. Mature Components

The following components are considered mature and stable:

*   **Pipeline (pipeline.py):** The pipeline is a generic and well-tested component that can be used to execute any sequence of steps.
*   **State (state.py):** The state model is well-defined and provides a solid foundation for storing and managing the analysis data.
*   **ToolBuilder (tool_builder.py):** The tool builder is a simple and effective way to create and provide the tools used by the steps.

### 4.2. Developing Components

The following components are still under development and may be subject to change:

*   **Scenarios (scenarios.py):** The scenarios are constantly being refined and expanded. New scenarios will be added as new use cases are identified.
*   **Steps (steps.py) and Tools:** The steps and tools are also under active development. New steps and tools will be added to support new analysis capabilities.
*   **ScenarioFinder (scenario_finder.py):** The scenario finder is a new component that is still being tested and improved.

## 5. Onboarding Guide

This guide provides a step-by-step process for new engineers to get started with the DeepAgentV3 codebase.

### 5.1. Prerequisites

*   Familiarity with Python 3.10+
*   Basic understanding of FastAPI and Pydantic
*   Access to a ClickHouse and PostgreSQL database

### 5.2. Setup

1.  **Clone the repository:**
    ```
    git clone <repository_url>
    ```
2.  **Install the dependencies:**
    ```
    pip install -r requirements.txt
    ```
3.  **Configure the environment variables:**
    Create a `.env` file in the root of the project and add the following variables:
    ```
    DATABASE_URL=postgresql://user:password@host:port/database
    CLICKHOUSE_HOST=...
    CLICKHOUSE_PORT=...
    CLICKHOUSE_USER=...
    CLICKHOUSE_PASSWORD=...
    LANGFUSE_SECRET_KEY=...
    LANGFUSE_PUBLIC_KEY=...
    LANGFUSE_HOST=...
    ```

### 5.3. Running the Agent

The agent can be run from the command line using the following command:

```
python -m app.services.apex_optimizer_agent.runner
```

This will start the agent and run the default analysis scenario.

### 5.4. Creating a New Scenario

To create a new scenario, you need to:

1.  **Define the scenario:** Add a new scenario dictionary to the `scenarios.py` file.
2.  **Implement the steps:** Create the new step functions in the `steps` directory.
3.  **Add the steps to the `ALL_STEPS` dictionary:** Add the new step functions to the `ALL_STEPS` dictionary in the `steps.py` file.

### 5.5. Creating a New Tool

To create a new tool, you need to:

1.  **Implement the tool:** Create a new tool class in the `tools` directory.
2.  **Add the tool to the `ToolBuilder`:** Add the new tool to the `ToolBuilder` class in the `tool_builder.py` file.
