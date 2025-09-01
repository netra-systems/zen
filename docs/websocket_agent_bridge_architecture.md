# WebSocket Agent Bridge Architecture Documentation

## Executive Summary

The `AgentWebSocketBridge` serves as the **Single Source of Truth (SSOT)** for WebSocket-Agent service integration, providing idempotent initialization, health monitoring, and recovery mechanisms. It acts as the critical bridge enabling 90% of chat functionality value by ensuring reliable real-time communication between agents and users.

## Core Architecture

### 1. Singleton Pattern & Thread Safety

```mermaid
graph TD
    subgraph "Singleton Instance Management"
        A[AgentWebSocketBridge Request] --> B{Instance Exists?}
        B -->|No| C[Create New Instance]
        B -->|Yes| D[Return Existing]
        C --> E[Initialize Components]
        E --> F[Set _initialized Flag]
        F --> D
        D --> G[Bridge Ready]
        
        H[Thread Lock] -.->|Protects| C
    end
```

### 2. Initialization Flow

```mermaid
sequenceDiagram
    participant Client
    participant Bridge as AgentWebSocketBridge
    participant WSM as WebSocketManager
    participant Registry as AgentExecutionRegistry
    participant Health as HealthMonitor
    
    Client->>Bridge: ensure_integration()
    activate Bridge
    
    alt Already Active & !force_reinit
        Bridge-->>Client: Return Success (cached)
    else Need Initialization
        Bridge->>Bridge: Set state = INITIALIZING
        
        Note over Bridge: Initialize WebSocket Manager
        loop Retry 3 times
            Bridge->>WSM: get_websocket_manager()
            alt Success
                WSM-->>Bridge: Return manager instance
                Bridge->>Bridge: Validate required methods
            else Failure
                Bridge->>Bridge: Wait & retry
            end
        end
        
        Note over Bridge: Initialize Registry
        Bridge->>Registry: get_agent_execution_registry()
        Registry-->>Bridge: Return orchestrator
        
        Note over Bridge: Setup Integration
        Bridge->>Registry: set_websocket_manager(WSM)
        Bridge->>Registry: setup_agent_websocket_integration()
        
        Note over Bridge: Verify Integration
        Bridge->>Bridge: _verify_integration()
        Bridge->>Registry: get_metrics()
        Registry-->>Bridge: Metrics dict
        
        Note over Bridge: Start Health Monitoring
        Bridge->>Health: Start monitoring loop
        
        Bridge->>Bridge: Set state = ACTIVE
        Bridge-->>Client: Return Success
    end
    
    deactivate Bridge
```

### 3. Component Dependencies

```mermaid
graph TB
    subgraph "Core Components"
        AWB[AgentWebSocketBridge<br/>SSOT Integration Manager]
        WSM[WebSocketManager<br/>Connection Handler]
        AER[AgentExecutionRegistry<br/>Agent Orchestrator]
    end
    
    subgraph "Optional Components"
        SUP[Supervisor Agent]
        REG[Agent Registry]
    end
    
    subgraph "Monitoring"
        HM[Health Monitor]
        MO[Monitor Observers]
    end
    
    AWB -->|Manages| WSM
    AWB -->|Manages| AER
    AWB -->|Optional| SUP
    AWB -->|Optional| REG
    AWB -->|Creates| HM
    AWB -->|Notifies| MO
    
    AER -->|Uses| WSM
    SUP -.->|Enhanced Integration| AER
    REG -.->|Enhanced Integration| AER
```

### 4. State Machine

```mermaid
stateDiagram-v2
    [*] --> UNINITIALIZED: Creation
    
    UNINITIALIZED --> INITIALIZING: ensure_integration()
    INITIALIZING --> ACTIVE: Success
    INITIALIZING --> FAILED: Error
    
    ACTIVE --> DEGRADED: Health Check Failures
    DEGRADED --> ACTIVE: Recovery Success
    DEGRADED --> FAILED: Recovery Failed
    
    FAILED --> INITIALIZING: force_reinit=True
    
    ACTIVE --> UNINITIALIZED: shutdown()
    DEGRADED --> UNINITIALIZED: shutdown()
    FAILED --> UNINITIALIZED: shutdown()
```

### 5. Health Monitoring Flow

```mermaid
graph LR
    subgraph "Health Check Loop"
        A[Sleep 60s] --> B[Check WebSocket Manager]
        B --> C[Check Registry]
        C --> D[Calculate Uptime]
        D --> E{All Healthy?}
        
        E -->|Yes| F[Reset Failure Count]
        E -->|No| G[Increment Failures]
        
        F --> H[Update State]
        G --> I{Failures >= 3?}
        
        I -->|Yes| J[Trigger Recovery]
        I -->|No| H
        
        H --> K[Notify Observers]
        K --> A
        
        J --> L[Recovery Process]
        L --> H
    end
```

### 6. WebSocket Event Emission Flow

```mermaid
sequenceDiagram
    participant Agent
    participant Bridge as AgentWebSocketBridge
    participant WSM as WebSocketManager
    participant User as User Chat
    
    Note over Agent,User: Crystal Clear Emission Path
    
    Agent->>Bridge: notify_agent_started(run_id, agent_name)
    activate Bridge
    
    Bridge->>Bridge: Check WSM available
    alt WSM Available
        Bridge->>Bridge: Build notification message
        Bridge->>Bridge: _resolve_thread_id_from_run_id()
        
        alt Thread ID Resolved
            Bridge->>WSM: send_to_thread(thread_id, notification)
            WSM->>User: WebSocket Message
            WSM-->>Bridge: Success
            Bridge-->>Agent: Return true
        else Cannot Resolve Thread
            Bridge-->>Agent: Return false
        end
    else WSM Not Available
        Bridge-->>Agent: Return false
    end
    
    deactivate Bridge
```

### 7. Recovery Mechanism

```mermaid
sequenceDiagram
    participant Health as Health Monitor
    participant Bridge as AgentWebSocketBridge
    participant Components as Components
    
    Health->>Bridge: Detect degradation (3+ failures)
    Bridge->>Bridge: acquire recovery_lock
    
    loop Max 3 attempts
        Bridge->>Bridge: Calculate backoff delay
        Note over Bridge: Delay = min(base * 2^attempt, max_delay)
        
        Bridge->>Bridge: Wait backoff period
        Bridge->>Bridge: ensure_integration(force_reinit=True)
        
        alt Success
            Bridge->>Bridge: Update metrics
            Bridge->>Bridge: Set state = ACTIVE
            Bridge-->>Health: Recovery successful
        else Failure
            Bridge->>Bridge: Continue loop
        end
    end
    
    Bridge->>Bridge: Set state = FAILED
    Bridge-->>Health: Recovery failed
```

## Integration Points & Expectations

### 1. WebSocket Manager Requirements

The bridge expects the WebSocket Manager to provide:
- `connections` attribute - Active connection tracking
- `send_to_thread(thread_id, message)` method - Message delivery
- Thread-safe operations
- Idempotent message sending

### 2. Agent Execution Registry Requirements

The registry must provide:
- `set_websocket_manager(manager)` - Accept WebSocket manager
- `setup_agent_websocket_integration(supervisor, registry)` - Enhanced setup
- `get_metrics()` - Return dict of operational metrics
- `get_thread_id_for_run(run_id)` - Thread resolution (optional)
- `shutdown()` - Clean shutdown

### 3. Notification Interface

All notifications follow this pattern:

```mermaid
graph LR
    A[Agent Action] --> B[Bridge Method]
    B --> C{Build Message}
    C --> D[Resolve Thread ID]
    D --> E[Send via WSM]
    E --> F[User Chat]
    
    G[Sanitization] -.->|Applied to| C
```

Critical events that MUST be sent:
1. **agent_started** - User sees AI began processing
2. **agent_thinking** - Real-time reasoning visibility  
3. **tool_executing** - Tool usage transparency
4. **tool_completed** - Tool results display
5. **agent_completed** - Response ready notification

### 4. Monitor Observer Pattern

```mermaid
graph TD
    subgraph "Observer Registration"
        A[Monitor] -->|register_monitor_observer| B[Bridge]
        B --> C[Add to observers list]
    end
    
    subgraph "Health Change Notification"
        D[Health Status Change] --> E[Bridge]
        E --> F{Observers Registered?}
        F -->|Yes| G[Notify Each Observer]
        F -->|No| H[Skip Notification]
        
        G --> I[Observer.on_component_health_change()]
    end
    
    subgraph "Independence"
        J[Bridge Operations] -.->|Continue regardless| K[Observer Failures]
    end
```

## Initialization Scenarios

### Scenario 1: Cold Start

```mermaid
sequenceDiagram
    participant App
    participant Bridge
    participant Components
    
    App->>Bridge: get_agent_websocket_bridge()
    Note over Bridge: First call - create instance
    Bridge->>Bridge: __init__()
    Bridge->>Bridge: Initialize all subsystems
    
    App->>Bridge: ensure_integration()
    Bridge->>Components: Initialize WebSocket Manager
    Bridge->>Components: Initialize Registry
    Bridge->>Components: Setup Integration
    Bridge->>Components: Start Health Monitoring
    Bridge-->>App: Success
```

### Scenario 2: Warm Start (Already Initialized)

```mermaid
sequenceDiagram
    participant App
    participant Bridge
    
    App->>Bridge: get_agent_websocket_bridge()
    Note over Bridge: Instance exists
    Bridge-->>App: Return existing
    
    App->>Bridge: ensure_integration()
    Note over Bridge: Check state = ACTIVE
    Bridge-->>App: Success (immediate)
```

### Scenario 3: Recovery After Failure

```mermaid
sequenceDiagram
    participant Health
    participant Bridge
    participant Components
    
    Health->>Bridge: Detect failures
    Bridge->>Bridge: State = DEGRADED
    
    Health->>Bridge: recover_integration()
    loop Recovery attempts
        Bridge->>Bridge: ensure_integration(force_reinit=True)
        Bridge->>Components: Re-initialize all
        alt Success
            Bridge->>Bridge: State = ACTIVE
        else Failure
            Bridge->>Bridge: Retry with backoff
        end
    end
```

## Configuration & Timeouts

```yaml
IntegrationConfig:
  initialization_timeout_s: 30      # Max time for initialization
  health_check_interval_s: 60       # Health check frequency
  recovery_max_attempts: 3          # Max recovery tries
  recovery_base_delay_s: 1.0        # Initial retry delay
  recovery_max_delay_s: 30.0        # Max retry delay
  integration_verification_timeout_s: 10  # Verification timeout
```

## Metrics & Monitoring

### Key Metrics Tracked

1. **Initialization Metrics**
   - total_initializations
   - successful_initializations
   - failed_initializations
   - success_rate

2. **Recovery Metrics**
   - recovery_attempts
   - successful_recoveries
   - recovery_success_rate

3. **Health Metrics**
   - health_checks_performed
   - consecutive_failures
   - uptime_seconds
   - total_recoveries

4. **Component Availability**
   - websocket_manager_available
   - orchestrator_available
   - supervisor_available
   - registry_available

## Error Handling & Resilience

### Graceful Degradation

```mermaid
graph TD
    A[Component Failure] --> B{Critical?}
    B -->|Yes| C[Mark DEGRADED]
    B -->|No| D[Log & Continue]
    
    C --> E[Attempt Recovery]
    E --> F{Success?}
    F -->|Yes| G[Mark ACTIVE]
    F -->|No| H[Mark FAILED]
    
    D --> I[Continue Operations]
    G --> I
    H --> J[Await Manual Intervention]
```

### Sanitization Pipeline

All user-facing data passes through sanitization:

1. **Parameters**: Redact sensitive keys (password, token, etc.)
2. **Results**: Truncate large data structures
3. **Errors**: Remove file paths and internal details
4. **Progress**: Filter to allowed keys only
5. **Custom Data**: Apply size limits

## Business Value & Impact

### Critical Business Functions Enabled

1. **Real-time User Feedback** (90% of chat value)
   - Immediate agent start confirmation
   - Progress visibility during processing
   - Tool execution transparency
   - Clear completion signals

2. **Trust Building**
   - Visible AI reasoning process
   - Error explanations with recovery guidance
   - Consistent event delivery

3. **System Reliability**
   - Automatic recovery from failures
   - Health monitoring and alerting
   - Graceful degradation
   - Zero-downtime recovery

### Performance Characteristics

- **Initialization**: < 100ms typical, 30s timeout
- **Health Checks**: Every 60 seconds
- **Recovery**: 3 attempts with exponential backoff
- **Event Delivery**: Immediate with retry for critical events
- **Observer Notifications**: Async, non-blocking

## Thread ID Resolution Strategy

```mermaid
graph TD
    A[run_id provided] --> B{Has orchestrator?}
    B -->|Yes| C[Query orchestrator]
    C --> D{Found?}
    D -->|Yes| E[Return thread_id]
    D -->|No| F{Contains 'thread_'?}
    
    B -->|No| F
    F -->|Yes| G[Extract thread_id]
    F -->|No| H{Has registry?}
    
    G --> E
    H -->|Yes| I[Query registry]
    H -->|No| J{Starts with 'thread_'?}
    
    I --> K{Found?}
    K -->|Yes| E
    K -->|No| J
    
    J -->|Yes| L[Use run_id as thread_id]
    J -->|No| M[Return None]
    
    L --> E
```

## Summary

The AgentWebSocketBridge provides:

1. **Single Source of Truth** - One place for all WebSocket-Agent integration
2. **Idempotent Operations** - Safe to call multiple times
3. **Health Monitoring** - Continuous health checks with recovery
4. **Guaranteed Delivery** - Critical events with retry logic
5. **Observer Pattern** - External monitoring without coupling
6. **Graceful Degradation** - Continues operating despite failures
7. **Business Value** - Enables 90% of chat functionality value

The bridge ensures reliable, real-time communication between agents and users, with comprehensive error handling, monitoring, and recovery mechanisms to maintain system stability and user experience.