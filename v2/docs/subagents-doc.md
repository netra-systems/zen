# Sub-Agents Documentation

This document provides an overview of the sub-agent architecture used in the Netra application.

## Overview

The sub-agent architecture is designed to break down complex tasks into smaller, manageable steps. Each sub-agent is a specialized LLM-based agent responsible for a specific part of the overall workflow. A central `Supervisor` agent orchestrates the execution of these sub-agents, passing the output of one as the input to the next.

## Sub-Agents

The following sub-agents are currently implemented:

- **TriageSubAgent**: This is the first agent in the workflow. It receives the initial user request and categorizes it into one of the following categories: `Data Analysis`, `Code Optimization`, or `General Inquiry`.

- **DataSubAgent**: This agent takes the categorized request from the `TriageSubAgent` and gathers any necessary data to fulfill the request. This may involve querying databases, calling external APIs, or accessing other data sources.

- **OptimizationsCoreSubAgent**: This agent receives the data from the `DataSubAgent` and uses it to formulate a set of optimization strategies. These strategies are high-level plans for how to address the user's request.

- **ActionsToMeetGoalsSubAgent**: This agent takes the optimization strategies from the `OptimizationsCoreSubAgent` and creates a detailed, step-by-step action plan. This plan outlines the specific actions that need to be taken to implement the optimization strategies.

- **ReportingSubAgent**: This is the final agent in the workflow. It takes the action plan from the `ActionsToMeetGoalsSubAgent` and generates a comprehensive report that summarizes the entire process, from the initial request to the final plan.

## Workflow

The `Supervisor` agent orchestrates the sub-agents in the following order:

1.  `TriageSubAgent`
2.  `DataSubAgent`
3.  `OptimizationsCoreSubAgent`
4.  `ActionsToMeetGoalsSubAgent`
5.  `ReportingSubAgent`

The output of each sub-agent is passed as the input to the next sub-agent in the sequence. This allows for a flexible and extensible workflow that can be easily modified to accommodate new requirements.

## WebSocket Communication

The sub-agent architecture is integrated with a WebSocket manager to provide real-time updates to the client. The `Supervisor` agent sends messages to the client at various points in the workflow, including when a sub-agent starts, when it completes, and when the entire workflow is finished. This allows the client to track the progress of the request and receive the final result as soon as it is available.