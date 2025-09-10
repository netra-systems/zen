# Netra Core Documentation Index

## 🎯 Quick Navigation

### 🏗️ Core Architecture (Start Here)

- **[🎯 Golden Path Documentation Index](./GOLDEN_PATH_DOCUMENTATION_INDEX.md)** 🚀 - **MASTER HUB**: Complete index and cross-reference for all Golden Path documentation, implementation reports, and validation evidence ($120K+ MRR protection)
- **[🚀 Golden Path User Flow Analysis](./GOLDEN_PATH_USER_FLOW_COMPLETE.md)** 🎯 - **MISSION CRITICAL**: Complete user journey analysis from connection to response delivery, identifies critical race conditions and WebSocket event requirements ($500K+ ARR dependency)
- **[⚡ Claude Code Command Index](./COMMAND_INDEX.md)** 🛠️ - **ESSENTIAL**: Complete index of 25 Claude Code slash commands for development automation, testing, deployment, and debugging with Five Whys methodology
- **[SSOT Index](../reports/ssot-compliance/SSOT_INDEX.md)** 🚨 - **ULTRA-CRITICAL**: Master index of all Single Source of Truth components ranked by criticality
- **[User Context Architecture](../reports/archived/USER_CONTEXT_ARCHITECTURE.md)** ⭐ - **CRITICAL DOCUMENT**: Comprehensive guide to the Factory-based user isolation architecture with detailed diagrams including child context hierarchies
- **[UVS Triage Architecture Transition](./UVS_TRIAGE_ARCHITECTURE_TRANSITION.md)** 🆕 - **NEW**: Unified Validation System with intelligent data sufficiency states and 2-agent model
- **[Agent Architecture Disambiguation Guide](./AGENT_ARCHITECTURE_DISAMBIGUATION_GUIDE.md)** 🎯 - **ESSENTIAL**: Clarifies agent workflow architecture, relationships between components, and common confusion points
- [Agent System Architecture](./AGENT_SYSTEM_ARCHITECTURE.md) - Complete agent execution pipeline documentation
- [Agent Architecture Diagrams](./agent_architecture_mermaid.md) - Visual architecture representations

### 🔄 Migration Guides

- **[SSOT Consolidation Status Report](../reports/ssot-compliance/SSOT_CONSOLIDATION_STATUS_20250904.md)** ⭐ - **NEW**: Complete status of SSOT consolidations (91% code reduction)
- **[Tool Dispatcher Migration Guide](../reports/archived/TOOL_DISPATCHER_DEDUPLICATION_REPORT.md)** - Migrate from singleton to request-scoped dispatchers
- [Tool Dispatcher Consolidation Complete](../TOOL_DISPATCHER_CONSOLIDATION_COMPLETE.md) - Tool dispatcher SSOT success
- [WebSocket Modernization Report](../reports/archived/WEBSOCKET_MODERNIZATION_REPORT.md) - WebSocket isolation implementation
- [Agent Registry Split Migration](./AGENT_REGISTRY_SPLIT_MIGRATION_GUIDE.md) - Agent registry refactoring

### 📚 System Components

#### Execution & Isolation
- **[User Context Architecture](../reports/archived/USER_CONTEXT_ARCHITECTURE.md)** - Factory patterns, execution engines, and child context hierarchies
- [3-Tier Persistence Architecture](./3tier_persistence_architecture.md) - Database layer design
- [Agent Golden Pattern Guide](./agent_golden_pattern_guide.md) - Best practices for agent development
- [Critical Bug Fix Documentation](../reports/bug-fixes/) - Documented fixes and audit reports

#### Agents & Tools
- **[Agent Architecture Disambiguation Guide](./AGENT_ARCHITECTURE_DISAMBIGUATION_GUIDE.md)** - Comprehensive disambiguation of agent components
- **[Orchestration Data Handling Patterns](../ORCHESTRATION_DATA_HANDLING_PATTERNS.md)** 🆕 - **CRITICAL**: Patterns for handling partial/insufficient data in agent orchestration
- [Agent System Overview](./agents/AGENT_SYSTEM.md) - High-level agent system design
- [Subagents Documentation](./agents/subagents-doc.md) - Subagent patterns and usage
- [Agent Modernization Plan](./agents/AGENT_MODERNIZATION_PLAN.md) - Future improvements
- [Golden Agent Index](./GOLDEN_AGENT_INDEX.md) - Definitive agent implementation patterns

#### WebSocket & Real-time
- [Actions Agent WebSocket Flow](./actions_agent_websocket_flow.md) - WebSocket event patterns
- [WebSocket Bridge State Handling](../reports/websocket/WEBSOCKET_V2_MIGRATION_GUIDE.md) - State management

#### Frontend Architecture
- **[Frontend Architecture Diagrams](../frontend/docs/FRONTEND_ARCHITECTURE_DIAGRAMS.md)** 📊 - Comprehensive Mermaid diagrams of frontend components, loading flows, and state management
- [Frontend README](../frontend/README.md) - Frontend setup and structure

#### Testing Infrastructure
- **[Test Creation Guide](../reports/testing/TEST_CREATION_GUIDE.md)** 🆕 - **AUTHORITATIVE**: Complete guide for creating tests with SSOT patterns
- **[Test Architecture Visual Overview](../tests/TEST_ARCHITECTURE_VISUAL_OVERVIEW.md)** - Complete test infrastructure guide
- **[⚡ Claude Code Command Index](./COMMAND_INDEX.md)** 🛠️ - **TESTING COMMANDS**: 15+ testing commands including TDD, unit tests, integration tests, and mission critical validation
- [Docker Orchestration](./docker_orchestration.md) - Docker management and Alpine containers
- **[Docker Architecture Diagrams](./docker_architecture_diagrams.md)** 🐳 - **NEW**: Comprehensive Docker build, caching, and deployment diagrams
- [Unified Test Runner](../tests/unified_test_runner.py) - Central test execution

### 🔒 Security & Compliance

- **[Critical Security Implementation](../reports/archived/CRITICAL_SECURITY_IMPLEMENTATION_SUMMARY.md)** - Security boundaries and isolation
- [API Dual Channel Explanation](./API_DUAL_CHANNEL_EXPLANATION.md) - API security patterns
- [Go-Live Acceptance Criteria](./ACCEPTANCE_CRITERIA_GO_LIVE_CHECKLIST.md) - Production readiness

### 🚨 Error Reporting & Monitoring

- **[GCP Error Reporting Architecture](./GCP_ERROR_REPORTING_ARCHITECTURE.md)** 🆕 - **CRITICAL**: Comprehensive GCP error reporting integration for production visibility
- [Configuration Architecture](./configuration_architecture.md) - Environment and configuration management

### 🧪 Testing & Quality

- **[Test Architecture Visual Overview](../tests/TEST_ARCHITECTURE_VISUAL_OVERVIEW.md)** 📊 - **COMPREHENSIVE**: Complete visual guide to test infrastructure, layers, and execution flows
- [Agent Testing Root Cause Summary](./agents/AGENT_TESTING_ROOT_CAUSE_SUMMARY.md)
- [Phase 0 Completion Report](../reports/archived/PHASE_0_COMPLETION_REPORT.md)
- [Docker Backend Five Whys Report](../reports/archived/DOCKER_BACKEND_FIVE_WHYS_BUG_REPORT.md)
- [WebSocket Thread Association Tests](../tests/mission_critical/test_websocket_thread_association.py) - Verification tests for thread routing

### 🚀 Performance & Optimization

- **[Netra Optimization Breakdown](../NETRA_OPTIMIZATION_BREAKDOWN.md)** 🎯 - **CRITICAL**: System optimization architecture breakdown (AI-specific vs general optimization)
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

1. **[🎯 Golden Path Documentation Index](./GOLDEN_PATH_DOCUMENTATION_INDEX.md)** - **START HERE**: Master hub with complete navigation to all Golden Path documentation
2. **[🚀 Golden Path User Flow Analysis](./GOLDEN_PATH_USER_FLOW_COMPLETE.md)** - Complete user journey with critical issues and business impact
3. **[User Context Architecture](../reports/archived/USER_CONTEXT_ARCHITECTURE.md)** - Factory-based system overview including child context patterns
4. **[Agent Architecture Disambiguation Guide](./AGENT_ARCHITECTURE_DISAMBIGUATION_GUIDE.md)** - Clarify component relationships
5. **[Golden Agent Index](./GOLDEN_AGENT_INDEX.md)** - Definitive agent implementation patterns
6. [Agent System Architecture](./AGENT_SYSTEM_ARCHITECTURE.md) - Understand agent execution
7. [Tool Dispatcher Migration Guide](../reports/archived/TOOL_DISPATCHER_DEDUPLICATION_REPORT.md) - Learn isolation patterns
8. [WebSocket Modernization Report](../reports/archived/WEBSOCKET_MODERNIZATION_REPORT.md) - Event delivery system
9. [Learnings Index](../SPEC/learnings/index.xml) - Critical patterns and known issues

## 📚 Documentation Archive

- **[Documentation Archive 2025-09-08](../docs_archive_20250908/MASTER_INDEX_BY_IMPORTANCE.md)** 📁 - **COMPREHENSIVE ARCHIVE**: ~400+ documentation files organized by business importance and technical category

## 🛠️ Development Guidelines

When working with the system:
1. Always use request-scoped instances, never global state
2. Pass `UserExecutionContext` through all layers
3. Use factories to create isolated components
4. Ensure proper cleanup in finally blocks
5. Review the **[User Context Architecture](../reports/archived/USER_CONTEXT_ARCHITECTURE.md)** before making changes

## 📊 Monitoring & Metrics

The system provides comprehensive metrics at each layer:
- Factory creation and cleanup metrics
- Per-user execution tracking
- WebSocket event delivery stats
- Resource utilization monitoring

Access metrics via: `GET /api/metrics`

## 🆘 Getting Help

1. Review the **[User Context Architecture](../reports/archived/USER_CONTEXT_ARCHITECTURE.md)** first
2. Check relevant migration guides
3. Consult the quick reference guides
4. Contact the development team

---

> **Remember**: The **[User Context Architecture](../reports/archived/USER_CONTEXT_ARCHITECTURE.md)** is the authoritative guide for understanding the system's isolation and factory patterns. Always refer to it when working with execution engines, WebSocket events, or tool dispatchers.