# Netra Apex Backend: User Chat Through Agent Interaction Flow

## System Overview
This diagram illustrates the primary flow of user chat messages through the Netra Apex backend system, focusing on agent interactions and WebSocket communication.

## Primary Flow Diagram

```mermaid
graph TB
    subgraph "Frontend Client"
        USER[User Chat Interface]
        WS_CLIENT[WebSocket Client]
    end
    
    subgraph "WebSocket Layer"
        WS_ENDPOINT["/ws Endpoint"]
        WS_AUTH[WebSocket Authenticator]
        WS_MANAGER[WebSocket Manager<br/>- Connection lifecycle<br/>- Message routing<br/>- Broadcasting]
        MSG_ROUTER[Message Router]
    end
    
    subgraph "Chat Orchestration"
        CHAT_ORCH[ChatOrchestrator<br/>extends SupervisorAgent]
        INTENT[Intent Classifier]
        CONF_MGR[Confidence Manager]
        PIPELINE[Pipeline Executor]
    end
    
    subgraph "Agent Registry & Execution"
        AGENT_REG[Agent Registry<br/>- Agent lifecycle<br/>- WebSocket integration]
        EXEC_ENGINE[Execution Engine<br/>- Pipeline orchestration<br/>- Fallback management]
        WS_NOTIFIER[WebSocket Notifier<br/>- Real-time events]
    end
    
    subgraph "Tool Execution"
        TOOL_DISP[Tool Dispatcher<br/>Enhanced with WebSocket]
        TOOL_EXEC[Tool Execution Engine]
    end
    
    subgraph "Sub-Agents"
        TRIAGE[Triage SubAgent]
        DATA[Data SubAgent]
        CORPUS[Corpus Admin SubAgent]
        SYNTHETIC[Synthetic Data SubAgent]
        REPORTING[Reporting SubAgent]
        OPTIM[Optimizations SubAgent]
        ACTIONS[Actions to Meet Goals SubAgent]
    end
    
    subgraph "Services Layer"
        LLM_MGR[LLM Manager]
        DB[Database Session]
        CACHE[Cache Manager]
    end

    %% User Flow
    USER -->|1. Send Message| WS_CLIENT
    WS_CLIENT -->|2. WebSocket Connection| WS_ENDPOINT
    WS_ENDPOINT -->|3. Authenticate| WS_AUTH
    WS_AUTH -->|4. Valid JWT| WS_MANAGER
    
    %% Message Processing
    WS_MANAGER -->|5. Route Message| MSG_ROUTER
    MSG_ROUTER -->|6. Chat Message| CHAT_ORCH
    
    %% Chat Orchestration
    CHAT_ORCH -->|7. Classify Intent| INTENT
    INTENT -->|8. Determine Confidence| CONF_MGR
    CONF_MGR -->|9. Plan Execution| PIPELINE
    
    %% Agent Execution
    PIPELINE -->|10. Execute via| EXEC_ENGINE
    EXEC_ENGINE -->|11. Get Agent| AGENT_REG
    EXEC_ENGINE -->|12. Notify Start| WS_NOTIFIER
    
    %% WebSocket Events (Real-time)
    WS_NOTIFIER -.->|agent_started| WS_MANAGER
    WS_NOTIFIER -.->|agent_thinking| WS_MANAGER
    WS_NOTIFIER -.->|tool_executing| WS_MANAGER
    WS_NOTIFIER -.->|tool_completed| WS_MANAGER
    WS_NOTIFIER -.->|partial_result| WS_MANAGER
    WS_NOTIFIER -.->|agent_completed| WS_MANAGER
    
    %% Agent Selection & Execution
    AGENT_REG -->|13. Select Agent| TRIAGE
    TRIAGE -->|14. Route to Specialist| DATA
    TRIAGE -->|14. Route to Specialist| CORPUS
    TRIAGE -->|14. Route to Specialist| SYNTHETIC
    TRIAGE -->|14. Route to Specialist| REPORTING
    TRIAGE -->|14. Route to Specialist| OPTIM
    TRIAGE -->|14. Route to Specialist| ACTIONS
    
    %% Tool Execution
    DATA -->|15. Execute Tools| TOOL_DISP
    CORPUS -->|15. Execute Tools| TOOL_DISP
    SYNTHETIC -->|15. Execute Tools| TOOL_DISP
    TOOL_DISP -->|16. Run Tool| TOOL_EXEC
    TOOL_EXEC -.->|Tool Events| WS_NOTIFIER
    
    %% Service Dependencies
    CHAT_ORCH --> LLM_MGR
    CHAT_ORCH --> DB
    CHAT_ORCH --> CACHE
    DATA --> LLM_MGR
    CORPUS --> LLM_MGR
    SYNTHETIC --> LLM_MGR
    
    %% Response Flow
    TOOL_EXEC -->|17. Tool Results| DATA
    DATA -->|18. Agent Results| EXEC_ENGINE
    EXEC_ENGINE -->|19. Final Report| CHAT_ORCH
    CHAT_ORCH -->|20. Response| WS_MANAGER
    WS_MANAGER -->|21. Send to Client| WS_CLIENT
    WS_CLIENT -->|22. Display| USER
    
    style USER fill:#e1f5fe
    style WS_MANAGER fill:#fff3e0
    style CHAT_ORCH fill:#f3e5f5
    style EXEC_ENGINE fill:#e8f5e9
    style WS_NOTIFIER fill:#ffebee
    style TOOL_DISP fill:#fce4ec
```

## Key Components

### 1. WebSocket Layer
- **Endpoint**: `/ws` - Main authenticated WebSocket endpoint
- **Manager**: Handles connection lifecycle, message routing, and broadcasting
- **Authentication**: JWT-based authentication for secure connections
- **Rate Limiting**: Built-in rate limiting and connection pooling

### 2. Chat Orchestrator
- **Extends**: SupervisorAgent for agent management
- **Intent Classification**: Determines user intent from messages
- **Confidence Management**: Manages confidence levels for responses
- **Pipeline Execution**: Orchestrates multi-step agent workflows

### 3. Agent Registry & Execution
- **Registry**: Manages agent lifecycle and WebSocket integration
- **Execution Engine**: Handles pipeline orchestration with fallback management
- **WebSocket Notifier**: Sends real-time events to frontend

### 4. Critical WebSocket Events
Per `SPEC/learnings/websocket_agent_integration_critical.xml`, these events MUST be sent:
1. **agent_started** - User must see agent began processing
2. **agent_thinking** - Real-time reasoning visibility  
3. **tool_executing** - Tool usage transparency
4. **tool_completed** - Tool results display
5. **agent_completed** - User must know when done

### 5. Sub-Agents
- **Triage**: Routes requests to appropriate specialist agents
- **Data**: Handles data processing and analysis
- **Corpus Admin**: Manages knowledge base operations
- **Synthetic Data**: Generates synthetic data profiles
- **Reporting**: Creates reports and analytics
- **Optimizations**: Handles optimization suggestions
- **Actions to Meet Goals**: Plans and executes goal-oriented actions

### 6. Tool Dispatcher
- **Enhanced**: Automatically enhanced with WebSocket notifications
- **Real-time Events**: Sends tool_executing and tool_completed events
- **Modular**: Clean separation between registry, execution, and validation

## Message Flow Sequence

1. User sends message via chat interface
2. WebSocket client establishes secure connection
3. Authentication validates JWT token
4. WebSocket Manager routes message to Message Router
5. Message Router identifies chat message and sends to ChatOrchestrator
6. ChatOrchestrator classifies intent and determines confidence
7. Pipeline Executor plans multi-agent execution
8. Execution Engine retrieves agents from registry
9. WebSocket Notifier sends agent_started event
10. Triage agent routes to appropriate specialist
11. Specialist agents execute tools via enhanced Tool Dispatcher
12. Tool Dispatcher sends tool_executing events
13. Tool execution completes with results
14. Tool Dispatcher sends tool_completed events
15. Agent results flow back through Execution Engine
16. ChatOrchestrator prepares final response
17. Response sent via WebSocket Manager to client
18. Client displays response to user

## Critical Integration Points

### WebSocket Enhancement
The Tool Dispatcher MUST be enhanced when WebSocket Manager is set:
```python
# In AgentRegistry.set_websocket_manager()
if self.tool_dispatcher and manager:
    enhance_tool_dispatcher_with_notifications(self.tool_dispatcher, manager)
```

### Event Flow Requirements
- All agent events must flow through WebSocketNotifier
- Tool events must flow through enhanced Tool Dispatcher
- Events must be sent in real-time, not batched
- Frontend depends on these events for UI updates

## Performance Considerations

1. **Connection Pooling**: WebSocket Manager uses TTL cache and LRU eviction
2. **Rate Limiting**: Built-in rate limiting prevents abuse
3. **Message Buffering**: Priority-based message buffering for reliability
4. **Heartbeat Management**: Automatic heartbeat for connection health
5. **Resource Monitoring**: Periodic cleanup tasks prevent memory leaks

## Testing Requirements

Per CLAUDE.md, this flow CANNOT regress:
- Run `python tests/mission_critical/test_websocket_agent_events_suite.py`
- Verify ALL event types are sent
- Test with real WebSocket connections
- Never remove or bypass WebSocket notifications