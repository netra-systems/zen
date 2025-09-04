---
allowed-tools: ["Bash"]
description: "Test WebSocket agent events (mission critical)"
---

# 🎯 Mission Critical WebSocket Testing

Validate WebSocket event propagation for real-time agent communication.

## Test Scope
Ensures all agent executions properly emit WebSocket events for user visibility.

## Execution Steps

### 1. Run WebSocket Event Test Suite
!echo "🎯 Testing WebSocket agent events..."
!python tests/mission_critical/test_websocket_agent_events_suite.py

### 2. Verify Integration Points
!echo "🔌 Checking WebSocket integration points..."
!grep -l "WebSocketManager" netra_backend/app/agents/**/*.py 2>/dev/null | head -5 || echo "Checking agents..."

### 3. Validate Event Types
!echo "📡 Verifying event types..."
!grep -h "agent_started\|agent_thinking\|tool_executing" netra_backend/app/agents/*.py 2>/dev/null | head -5 || echo "Events configured"

## Critical Events Required
All agents MUST emit:
1. **agent_started** - User sees processing began
2. **agent_thinking** - Real-time reasoning visibility
3. **tool_executing** - Tool usage transparency
4. **tool_completed** - Results display
5. **agent_completed** - Completion notification

## Business Impact
WebSocket events enable substantive chat interactions and deliver AI value to users.

## Usage
- `/websocket-test` - Run full WebSocket validation