# WebSocket Message to Agent Startup Flow

## Complete Function Call Trace

### 1. **WebSocket Connection & Authentication**
```
websocket_endpoint() [websockets.py:169]
└── _execute_websocket_session() [websockets.py:160]
    └── _run_websocket_session() [websockets.py:154]
        └── _establish_websocket_connection() [websockets.py:128]
            ├── _setup_websocket_auth() [websockets.py:111]
            │   ├── accept_websocket_connection() [websocket_helpers.py:26]
            │   ├── extract_app_services() [websocket_helpers.py:32]
            │   └── authenticate_websocket_user() [websocket_helpers.py:90]
            └── _finalize_websocket_connection() [websockets.py:122]
```

### 2. **Message Reception & Routing**
```
_handle_message_loop() [websockets.py:81]
└── _process_message_with_timeout_handling() [websockets.py:72]
    └── _process_single_message() [websockets.py:53]
        ├── receive_message_with_timeout() [websocket_helpers.py:98]
        ├── parse_json_message() [websocket_helpers.py:114]
        └── _handle_parsed_message() [websockets.py:45]
            └── _handle_validated_message() [websockets.py:26]
                ├── validate_and_handle_message() [websocket_helpers.py:145]
                └── _process_valid_message() [websockets.py:21]
                    └── process_agent_message() [websocket_helpers.py:158]
```

### 3. **Agent Service Message Handling**
```
handle_websocket_message() [agent_service_core.py:60]
└── _process_websocket_message() [agent_service_core.py:84]
    └── _route_message_by_type() [agent_service_core.py:98]
        └── _handle_standard_message_types() [agent_service_core.py:105]
```

### 4. **Message Type Dispatch**

#### For `start_agent` message:
```
handle_start_agent() [message_handlers.py:55]
└── _process_agent_request() [message_handlers.py:99]
    ├── _create_user_message() [message_handlers.py:111]
    ├── _create_run() [message_handlers.py:119]
    ├── _configure_supervisor() [message_handlers.py:127]
    └── _execute_supervisor() [message_handlers.py:133]
        └── supervisor.run() [supervisor_consolidated.py:280]
```

#### For `user_message` message:
```
handle_user_message() [message_handlers.py:157]
└── _process_user_message() [message_handlers.py:274]
    └── process_user_message_with_notifications() [message_processing.py]
        └── supervisor.run() [supervisor_consolidated.py:280]
```

### 5. **Agent Startup & Execution**
```
supervisor.run() [supervisor_consolidated.py:280]
└── _execute_workflow_steps() [supervisor_consolidated.py:295]
    └── workflow_executor.execute_workflow_steps() [supervisor/workflow_execution.py]
        ├── Create DeepAgentState
        ├── Load/persist state
        ├── Build pipeline
        ├── Execute agents
        └── Return results via WebSocket
```

## Key Components

### WebSocket Layer
- **WebSocket Manager**: Handles connections, broadcasts, and room management
- **Connection Validation**: Token authentication and user verification
- **Message Parser**: JSON parsing and validation

### Message Processing Layer
- **Agent Service**: Central router for WebSocket messages
- **Message Handlers**: Type-specific message processors
- **Thread Service**: Manages conversation threads and history

### Agent Execution Layer
- **Supervisor Agent**: Orchestrates sub-agents and workflow execution
- **Execution Engine**: Manages agent lifecycle and pipeline execution
- **State Persistence**: Maintains agent state across executions

## Message Flow Summary

1. **User connects** to `/ws` endpoint with authentication token
2. **WebSocket validates** token and establishes connection
3. **Message loop** waits for incoming messages (30s timeout for heartbeat)
4. **Message received** → parsed as JSON → validated
5. **Agent Service routes** message by type (`start_agent`, `user_message`, etc.)
6. **Message Handler** processes the specific message type:
   - Creates thread/run in database
   - Configures supervisor with context
   - Executes supervisor.run()
7. **Supervisor orchestrates** the agent workflow:
   - Builds execution pipeline
   - Executes sub-agents
   - Streams updates back via WebSocket
8. **Results sent** back to user through WebSocket connection

## Critical Integration Points

- **Authentication**: `app/routes/utils/websocket_helpers.py:90`
- **Message Routing**: `app/services/agent_service_core.py:98`
- **Agent Dispatch**: `app/services/message_handlers.py:55,157`
- **Supervisor Entry**: `app/agents/supervisor_consolidated.py:280`
- **WebSocket Updates**: Throughout via `manager.send_message()`