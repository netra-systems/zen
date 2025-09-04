---
allowed-tools: ["Bash", "Read"]
description: "Test specific agent with real LLM"
argument-hint: "<agent-name>"
---

# 🤖 Agent-Specific Testing

Test a specific agent implementation with real services and WebSocket validation.

## Target Agent
**Agent Name:** $1

## Test Execution

### 1. Run Agent-Specific Tests
!echo "🤖 Testing $1 agent with real services..."
!python tests/unified_test_runner.py --real-services --real-llm --pattern "*$1*"

### 2. Validate WebSocket Events
!echo "🔌 Verifying WebSocket events..."
!python tests/mission_critical/test_websocket_agent_events_suite.py

## Required WebSocket Events
The agent MUST emit these events:
- `agent_started` - When processing begins
- `agent_thinking` - During reasoning
- `tool_executing` - Before tool use
- `tool_completed` - After tool execution
- `agent_completed` - When finished

## Usage Examples
- `/agent-test data_analyst` - Test data analyst agent
- `/agent-test optimization` - Test optimization agent
- `/agent-test code_reviewer` - Test code reviewer agent