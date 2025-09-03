# Netra Core Documentation Index

## 🎯 Quick Navigation

### 🏗️ Core Architecture (Start Here)

- **[User Context Architecture](../USER_CONTEXT_ARCHITECTURE.md)** ⭐ - **CRITICAL DOCUMENT**: Comprehensive guide to the Factory-based user isolation architecture with detailed diagrams
- **[Agent Architecture Disambiguation Guide](./AGENT_ARCHITECTURE_DISAMBIGUATION_GUIDE.md)** 🎯 - **ESSENTIAL**: Clarifies agent workflow architecture, relationships between components, and common confusion points
- [Agent System Architecture](./AGENT_SYSTEM_ARCHITECTURE.md) - Complete agent execution pipeline documentation
- [Agent Architecture Diagrams](./agent_architecture_mermaid.md) - Visual architecture representations

### 🔄 Migration Guides

- **[Tool Dispatcher Migration Guide](../TOOL_DISPATCHER_MIGRATION_GUIDE.md)** - Migrate from singleton to request-scoped dispatchers
- [WebSocket Modernization Report](../WEBSOCKET_MODERNIZATION_REPORT.md) - WebSocket isolation implementation
- [Agent Registry Split Migration](./AGENT_REGISTRY_SPLIT_MIGRATION_GUIDE.md) - Agent registry refactoring

### 📚 System Components

#### Execution & Isolation
- **[User Context Architecture](../USER_CONTEXT_ARCHITECTURE.md)** - Factory patterns and execution engines
- [3-Tier Persistence Architecture](./3tier_persistence_architecture.md) - Database layer design
- [Agent Golden Pattern Guide](./agent_golden_pattern_guide.md) - Best practices for agent development
- [Critical Bug Fix Documentation](./critical_bug_fixes/) - Documented fixes and audit reports

#### Agents & Tools
- **[Agent Architecture Disambiguation Guide](./AGENT_ARCHITECTURE_DISAMBIGUATION_GUIDE.md)** - Comprehensive disambiguation of agent components
- [Agent System Overview](./agents/AGENT_SYSTEM.md) - High-level agent system design
- [Subagents Documentation](./agents/subagents-doc.md) - Subagent patterns and usage
- [Agent Modernization Plan](./agents/AGENT_MODERNIZATION_PLAN.md) - Future improvements
- [Golden Agent Index](./GOLDEN_AGENT_INDEX.md) - Definitive agent implementation patterns

#### WebSocket & Real-time
- [Actions Agent WebSocket Flow](./actions_agent_websocket_flow.md) - WebSocket event patterns
- [WebSocket Bridge State Handling](./websocket_bridge_state_handling.md) - State management

#### Testing Infrastructure
- **[Test Architecture Visual Overview](../tests/TEST_ARCHITECTURE_VISUAL_OVERVIEW.md)** - Complete test infrastructure guide
- [Docker Orchestration](./docker_orchestration.md) - Docker management and Alpine containers
- [Unified Test Runner](../tests/unified_test_runner.py) - Central test execution

### 🔒 Security & Compliance

- **[Critical Security Implementation](../CRITICAL_SECURITY_IMPLEMENTATION_SUMMARY.md)** - Security boundaries and isolation
- [API Dual Channel Explanation](./API_DUAL_CHANNEL_EXPLANATION.md) - API security patterns
- [Go-Live Acceptance Criteria](./ACCEPTANCE_CRITERIA_GO_LIVE_CHECKLIST.md) - Production readiness

### 🧪 Testing & Quality

- **[Test Architecture Visual Overview](../tests/TEST_ARCHITECTURE_VISUAL_OVERVIEW.md)** 📊 - **COMPREHENSIVE**: Complete visual guide to test infrastructure, layers, and execution flows
- [Agent Testing Root Cause Summary](./agents/AGENT_TESTING_ROOT_CAUSE_SUMMARY.md)
- [Phase 0 Completion Report](../PHASE_0_COMPLETION_REPORT.md)
- [Docker Backend Five Whys Report](../DOCKER_BACKEND_FIVE_WHYS_BUG_REPORT.md)
- [WebSocket Thread Association Tests](../tests/mission_critical/test_websocket_thread_association.py) - Verification tests for thread routing

### 🚀 Performance & Optimization

- **[Performance Metrics User Guide](./PERFORMANCE_METRICS_USER_GUIDE.md)** 📊 - **NEW**: Comprehensive guide to performance timing and metrics collection
- [Agent Performance Dependencies](./AGENT_PERFORMANCE_DEPENDENCIES_EXPLAINED.md)
- [Agent Performance Real Issues](./AGENT_PERFORMANCE_REAL_ISSUES.md)
- [Alpine Containers Guide](./alpine_containers.md) - Container optimization

### 📋 Quick References

- [Agent Quick Reference](./agent_quick_reference.md) - Common agent operations
- [Agent Migration Checklist](./agent_migration_checklist.md) - Migration steps
- [Alpine Migration Guide](./alpine_migration_guide.md) - Container migration

## 🏛️ Architecture Overview

The Netra Core system implements a **Factory-based, request-scoped architecture** that ensures complete user isolation:

```
┌─────────────────────────────────┐
│       User Request              │
└────────────┬────────────────────┘
             ▼
┌─────────────────────────────────┐
│   Authentication & Routing      │
└────────────┬────────────────────┘
             ▼
┌─────────────────────────────────┐
│      Factory Layer              │ ◄── Creates isolated instances
├─────────────────────────────────┤
│ • ExecutionEngineFactory        │
│ • WebSocketBridgeFactory        │
│ • ToolExecutorFactory           │
└────────────┬────────────────────┘
             ▼
┌─────────────────────────────────┐
│    Per-Request Execution        │ ◄── Complete user isolation
├─────────────────────────────────┤
│ • UserExecutionContext          │
│ • IsolatedExecutionEngine       │
│ • UserWebSocketEmitter          │
│ • UnifiedToolDispatcher         │
└────────────┬────────────────────┘
             ▼
┌─────────────────────────────────┐
│   Shared Infrastructure         │ ◄── Immutable, thread-safe
├─────────────────────────────────┤
│ • AgentRegistry                 │
│ • Database Pool                 │
│ • Cache Layer                   │
└─────────────────────────────────┘
```

## 🔑 Key Concepts

### User Isolation
Every request creates isolated execution contexts through factories, ensuring:
- No shared state between users
- Dedicated WebSocket channels per user
- Request-scoped tool dispatchers
- Automatic resource cleanup

### Factory Pattern
The system uses factory patterns extensively:
- **ExecutionEngineFactory**: Creates execution engines per request
- **WebSocketBridgeFactory**: Creates user-specific event emitters
- **ToolExecutorFactory**: Creates isolated tool dispatchers

### Resource Management
- Per-user semaphores (max 5 concurrent operations)
- Memory thresholds (1024MB limit)
- Execution timeouts (30s default)
- Automatic cleanup on request completion

## 📖 Essential Reading Order

1. **[User Context Architecture](../USER_CONTEXT_ARCHITECTURE.md)** - Start here for system overview
2. **[Agent Architecture Disambiguation Guide](./AGENT_ARCHITECTURE_DISAMBIGUATION_GUIDE.md)** - Clarify component relationships
3. **[Golden Agent Index](./GOLDEN_AGENT_INDEX.md)** - Definitive agent implementation patterns
4. [Agent System Architecture](./AGENT_SYSTEM_ARCHITECTURE.md) - Understand agent execution
5. [Tool Dispatcher Migration Guide](../TOOL_DISPATCHER_MIGRATION_GUIDE.md) - Learn isolation patterns
6. [WebSocket Modernization Report](../WEBSOCKET_MODERNIZATION_REPORT.md) - Event delivery system
7. [Learnings Index](../SPEC/learnings/index.xml) - Critical patterns and known issues

## 🛠️ Development Guidelines

When working with the system:
1. Always use request-scoped instances, never global state
2. Pass `UserExecutionContext` through all layers
3. Use factories to create isolated components
4. Ensure proper cleanup in finally blocks
5. Review the **[User Context Architecture](../USER_CONTEXT_ARCHITECTURE.md)** before making changes

## 📊 Monitoring & Metrics

The system provides comprehensive metrics at each layer:
- Factory creation and cleanup metrics
- Per-user execution tracking
- WebSocket event delivery stats
- Resource utilization monitoring

Access metrics via: `GET /api/metrics`

## 🆘 Getting Help

1. Review the **[User Context Architecture](../USER_CONTEXT_ARCHITECTURE.md)** first
2. Check relevant migration guides
3. Consult the quick reference guides
4. Contact the development team

---

> **Remember**: The **[User Context Architecture](../USER_CONTEXT_ARCHITECTURE.md)** is the authoritative guide for understanding the system's isolation and factory patterns. Always refer to it when working with execution engines, WebSocket events, or tool dispatchers.