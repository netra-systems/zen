# Subagents Architecture

This document provides an overview of the subagent architecture used in the Netra application.

## Overview

The subagent architecture is designed to break down complex tasks into smaller, more manageable steps. Each step is handled by a dedicated subagent, which is responsible for a specific part of the overall process. This approach makes the system more modular, easier to maintain, and less prone to errors.

## Supervisor Agent

The `Supervisor` agent is the orchestrator of the subagents. It is responsible for running the subagents in the correct order and for passing data between them. The `Supervisor` agent also manages the lifecycle of the subagents and provides a single point of entry for the entire process.

## Subagents

The following subagents are currently implemented:

*   **`TriageSubAgent`**: This subagent is responsible for triaging the user request and categorizing it.
*   **`DataSubAgent`**: This subagent is responsible for gathering and enriching data based on the triage result.
*   **`OptimizationsCoreSubAgent`**: This subagent is responsible for formulating optimization strategies based on the enriched data.
*   **`ActionsToMeetGoalsSubAgent`**: This subagent is responsible for creating a plan of action based on the optimization strategies.
*   **`ReportingSubAgent`**: This subagent is responsible for generating a final report based on the action plan.

## Data Flow

The data flow between the subagents is as follows:

1.  The `Supervisor` agent receives a request from the user.
2.  The `Supervisor` agent passes the request to the `TriageSubAgent`.
3.  The `TriageSubAgent` returns a triage result to the `Supervisor` agent.
4.  The `Supervisor` agent passes the triage result to the `DataSubAgent`.
5.  The `DataSubAgent` returns enriched data to the `Supervisor` agent.
6.  The `Supervisor` agent passes the enriched data to the `OptimizationsCoreSubAgent`.
7.  The `OptimizationsCoreSubAgent` returns a list of optimization strategies to the `Supervisor` agent.
8.  The `Supervisor` agent passes the optimization strategies to the `ActionsToMeetGoalsSubAgent`.
9.  The `ActionsToMeetGoalsSubAgent` returns an action plan to the `Supervisor` agent.
10. The `Supervisor` agent passes the action plan to the `ReportingSubAgent`.
11. The `ReportingSubAgent` returns a final report to the `Supervisor` agent.
12. The `Supervisor` agent returns the final report to the user.
