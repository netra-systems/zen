# Netra Core Documentation Index
**Last Updated:** 2025-01-17 | **System Health:** ✅ EXCELLENT (95% - Issue #1116 SSOT Agent Factory Migration Complete, System Stability Validated, Enterprise User Isolation Implemented)

## 🎯 Quick Navigation

### 🏗️ Core Architecture (Start Here)

**Recent Major Achievement (2025-01-17)**: Issue #1176 (test infrastructure crisis) and Issue #1294 (secret loading failures) RESOLVED. Issue #1296 CLOSED (AuthTicketManager implementation complete), Issue #1309 RESOLVED (SQLAlchemy compliance), Issue #1312 RESOLVED (Redis health check). Documentation infrastructure refreshed and maintained current. Issue #1116 SSOT Agent Factory Migration COMPLETE - Enterprise-grade user isolation implemented with singleton elimination.

- **[🎯 Golden Path Documentation Index](./GOLDEN_PATH_DOCUMENTATION_INDEX.md)** 🚀 - **MASTER HUB**: Complete index and cross-reference for all Golden Path documentation, implementation reports, and validation evidence ($500K+ ARR protection with enterprise-grade user isolation)
- **[📚 Master Documentation Index](../reports/LLM_MASTER_INDEX.md)** 🗂️ - **NAVIGATION GUIDE**: Complete cross-system navigation with health metrics, documentation archive, and quick reference patterns
- **[🚀 Golden Path User Flow Analysis](./GOLDEN_PATH_USER_FLOW_COMPLETE.md)** 🎯 - **MISSION CRITICAL**: Complete user journey analysis from connection to response delivery, identifies critical race conditions and WebSocket event requirements ($500K+ ARR dependency)
- **[⚡ Claude Code Command Index](./COMMAND_INDEX.md)** 🛠️ - **ESSENTIAL**: Complete index of 39 Claude Code slash commands for development automation, testing, deployment, and debugging with Five Whys methodology (Updated 2025-01-17)
- **[SSOT Index](../reports/ssot-compliance/SSOT_INDEX.md)** 🚨 - **ULTRA-CRITICAL**: Master index of all Single Source of Truth components ranked by criticality (87.2% compliance in production code - improved through Issue #1116)
- **[SSOT Import Registry](./SSOT_IMPORT_REGISTRY.md)** 📋 - **AUTHORITATIVE**: Complete import mappings for all services with verified paths and compatibility layers (Updated 2025-01-17)
- **[User Context Architecture](../reports/archived/USER_CONTEXT_ARCHITECTURE.md)** ⭐ - **CRITICAL DOCUMENT**: Comprehensive guide to the Factory-based user isolation architecture with detailed diagrams including child context hierarchies
- **[UVS Triage Architecture Transition](./UVS_TRIAGE_ARCHITECTURE_TRANSITION.md)** 🆕 - **NEW**: Unified Validation System with intelligent data sufficiency states and 2-agent model
- **[Agent Architecture Disambiguation Guide](./AGENT_ARCHITECTURE_DISAMBIGUATION_GUIDE.md)** 🎯 - **ESSENTIAL**: Clarifies agent workflow architecture, relationships between components, and common confusion points
- [Agent System Architecture](./AGENT_SYSTEM_ARCHITECTURE.md) - Complete agent execution pipeline documentation
- [Agent Architecture Diagrams](./agent_architecture_mermaid.md) - Visual architecture representations

### 🔄 Migration Guides

- **[SSOT Consolidation Stability Report](../reports/SSOT_CONSOLIDATION_STABILITY_VALIDATION_REPORT.md)** ⭐ - **COMPLETE**: SSOT consolidations stability validation - Issue #1116 Agent Factory SSOT adds enterprise user isolation
- **[Tool Dispatcher Migration Guide](../reports/archived/TOOL_DISPATCHER_DEDUPLICATION_REPORT.md)** - Migrate from singleton to request-scoped dispatchers
- [Tool Dispatcher Consolidation Complete](../reports/tools/TOOL_DISPATCHER_CONSOLIDATION_COMPLETE.md) - Tool dispatcher SSOT success
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
- **[Test Execution Guide](../reports/TEST_EXECUTION_GUIDE.md)** 📖 - **COMPREHENSIVE**: Complete methodology for test execution, discovery, and coverage metrics (16,000+ tests, Issue #798 resolved) (Current as of 2025-01-17)
- **[Test Creation Guide](../reports/testing/TEST_CREATION_GUIDE.md)** 🆕 - **AUTHORITATIVE**: Complete guide for creating tests with SSOT patterns
- **[Test Architecture Visual Overview](../tests/TEST_ARCHITECTURE_VISUAL_OVERVIEW.md)** - Complete test infrastructure guide
- **[⚡ Claude Code Command Index](./COMMAND_INDEX.md)** 🛠️ - **TESTING COMMANDS**: 15+ testing commands including TDD, unit tests, integration tests, and mission critical validation (Current as of 2025-01-17)
- [Docker Orchestration](./docker_orchestration.md) - Docker management and Alpine containers
- **[Docker Architecture Diagrams](./docker_architecture_diagrams.md)** 🐳 - **NEW**: Comprehensive Docker build, caching, and deployment diagrams
- [Unified Test Runner](../tests/unified_test_runner.py) - Central test execution

### 🔒 Security & Compliance

- **[Critical Security Implementation](../reports/archived/CRITICAL_SECURITY_IMPLEMENTATION_SUMMARY.md)** - Security boundaries and isolation
- [API Dual Channel Explanation](./API_DUAL_CHANNEL_EXPLANATION.md) - API security patterns
- [Go-Live Acceptance Criteria](./ACCEPTANCE_CRITERIA_GO_LIVE_CHECKLIST.md) - Production readiness

### 🚀 Deployment & Demo

- **[Staging Demo Setup Guide](./STAGING_DEMO_SETUP.md)** 🆕 - **QUICK START**: Complete guide for launching staging demo with automated setup
- **[⚡ /run-demo Command](./COMMAND_INDEX.md#run-demo)** 🚀 - **INSTANT DEMO**: One-command staging demo launch with flexible frontend options
- [Deployment Guide](./DEPLOYMENT_GUIDE.md) - Full deployment documentation

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

### 🤖 Services & Automation

#### Orchestration Services
- **[Zen Orchestrator Service](../zen/README.md)** 🎛️ - **STANDALONE SERVICE**: Multi-instance Claude Code orchestration with scheduling, monitoring, and metrics collection
- **[Orchestrator Documentation Hub](../zen/docs/)** 📖 - Service overview, quick start, and usage patterns
- **[Orchestrator Test Suite](../zen/tests/)** 🧪 - Complete test infrastructure for orchestration validation
- **[CloudSQL Integration Guide](../scripts/ORCHESTRATOR_CLOUDSQL_INTEGRATION.md)** 💾 - Database persistence and metrics tracking

#### Main System Services
- **[Main Backend](../netra_backend/)** 🏗️ - Core Netra system with agent execution and WebSocket management
- **[Auth Service](../auth_service/)** 🔐 - Authentication and authorization service
- **[Frontend](../frontend/)** 🌐 - User interface and client application
- **[Shared Libraries](../shared/)** 📚 - Common utilities and cross-service components

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

1. **[🎯 Golden Path Documentation Index](./GOLDEN_PATH_DOCUMENTATION_INDEX.md)** - **START HERE**: Master hub with complete navigation to all Golden Path documentation and recent infrastructure enhancements
2. **[🚀 Golden Path User Flow Analysis](./GOLDEN_PATH_USER_FLOW_COMPLETE.md)** - Complete user journey with critical issues and business impact ($500K+ ARR protection)
3. **[User Context Architecture](../reports/archived/USER_CONTEXT_ARCHITECTURE.md)** - Factory-based system overview including child context patterns and multi-user isolation
4. **[Agent Architecture Disambiguation Guide](./AGENT_ARCHITECTURE_DISAMBIGUATION_GUIDE.md)** - Clarify component relationships with recent testing infrastructure improvements
5. **[Golden Agent Index](./GOLDEN_AGENT_INDEX.md)** - Definitive agent implementation patterns with comprehensive test coverage achievements
6. **[⚡ Claude Code Command Index](./COMMAND_INDEX.md)** - Complete development automation with 39 commands including new repository maintenance tools
7. **[Test Execution Guide](../reports/TEST_EXECUTION_GUIDE.md)** - Enhanced testing methodology with SSOT compliance and infrastructure improvements
8. [Agent System Architecture](./AGENT_SYSTEM_ARCHITECTURE.md) - Understand agent execution with recent testing enhancements
9. [WebSocket Modernization Report](../reports/archived/WEBSOCKET_MODERNIZATION_REPORT.md) - Event delivery system with SSOT bridge migration
10. [Learnings Index](../SPEC/learnings/index.xml) - Critical patterns and recent infrastructure achievements

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