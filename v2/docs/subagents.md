# Sub-Agent Architecture

This document describes the sub-agent architecture used in the system.

## Overview

The system uses a supervisor-sub-agent architecture to handle user requests. The `Supervisor` agent is responsible for orchestrating the flow of data between a series of sub-agents. Each sub-agent is responsible for a specific task in the overall process.

## Supervisor

The `Supervisor` is the main entry point for handling user requests. It is responsible for:

- Creating and managing the lifecycle of the sub-agents.
- Running the sub-agents in the correct order.
- Passing data between the sub-agents.
- Providing real-time updates to the user via WebSockets.

## Sub-Agents

Each sub-agent is a `BaseSubAgent` and has a `run` method that takes the input data and returns the processed data. The following sub-agents are currently implemented:

- **`TriageSubAgent`**: This agent triages the user request and categorizes it.
- **`DataSubAgent`**: This agent gathers and enriches data based on the triage result.
- **`OptimizationsCoreSubAgent`**: This agent formulates optimization strategies based on the gathered data.
- **`ActionsToMeetGoalsSubAgent`**: This agent creates a plan of action based on the optimization strategies.
- **`ReportingSubAgent`**: This agent generates a final report based on the action plan.

## Tool Dispatcher

The `ToolDispatcher` is responsible for providing tools to the sub-agents. Sub-agents can request tools from the `ToolDispatcher` and use them to perform their tasks. This allows for a more modular and extensible system, where new tools can be added without modifying the sub-agents themselves.

## Creating a New Sub-Agent

To create a new sub-agent, you need to:

1.  Create a new class that inherits from `BaseSubAgent`.
2.  Implement the `run` method.
3.  Add the new sub-agent to the `sub_agents` list in the `Supervisor` class.