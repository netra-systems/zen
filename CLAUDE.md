# CLAUDE.md

Guidance for Claude Code when working with the Netra AI Optimization Platform.

## Core Principles

### 1. Think Deeply by Default
- **ALWAYS** analyze problems thoroughly before implementing solutions
- Consider edge cases, performance implications, and system-wide impacts
- Use ultra-thinking capabilities when available for complex problems
- Question assumptions and validate understanding

### 2. Document Learnings to Prevent Regression
- **IMMEDIATELY** update this file or relevant specs when discovering patterns
- Document gotchas, workarounds, and non-obvious behaviors
- Add examples of what works and what doesn't
- Create new specs for complex domains

### 3. Keep Specifications Current
- Specs in `SPEC/*.xml` are the source of truth
- Update specs BEFORE implementing changes
- Reference specs for detailed guidelines
- Create new specs rather than bloating this file

## Project Overview

Netra AI Optimization Platform - Enterprise-grade system for optimizing AI workloads.

## Quick Start

### Development
```bash
# Recommended: Start both backend and frontend
python dev_launcher.py --dynamic --no-backend-reload --load-secrets

# Quick validation before any changes (RECOMMENDED)
python test_runner.py --level smoke
```

### Testing
```bash
# UNIFIED TEST RUNNER - Single entry point for all testing
# Quick smoke tests (< 30 seconds) - Use for pre-commit validation
python test_runner.py --level smoke

# Unit tests during development (1-2 minutes)
python test_runner.py --level unit

# Integration tests for feature validation (3-5 minutes)
python test_runner.py --level integration

# Full comprehensive testing with coverage (10-15 minutes)
python test_runner.py --level comprehensive

# Critical path tests only (1-2 minutes)
python test_runner.py --level critical

# Simple fallback runner (if main runner has issues)
python test_runner.py --simple
```

## Critical Specifications

**ALWAYS CONSULT SPECS FIRST** - They contain the detailed requirements and patterns.

### Primary Specs (Consult for Every Change)
- `SPEC/code_changes.xml` - **MANDATORY** checklist for any code modification
- `SPEC/anti_regression.xml` - **CRITICAL** patterns to prevent common regressions
- `SPEC/conventions.xml` - Coding standards and patterns
- `SPEC/instructions.xml` - General development guidelines

### Domain-Specific Specs
- `SPEC/testing.xml` - Testing strategy, troubleshooting, 97% coverage target
- `SPEC/architecture.xml` - System design, components, workflows
- `SPEC/clickhouse.xml` - ClickHouse configuration and troubleshooting
- `SPEC/unified_chat_ui_ux.xml` - V5 UI requirements (glassmorphic, no blue bars)
- `SPEC/test_update_spec.xml` - Automated test improvement with ultra-thinking
- `SPEC/LEGACY_CODE_CLEANUP.xml` - Legacy code identification procedures




## Critical Development Rules

### MANDATORY for Every Change
1. **Consult `SPEC/code_changes.xml`** - Complete checklist for any modification
2. **Update import tests** when adding new modules/dependencies
3. **Run quick tests** before any commit: `python test_runner.py --level smoke`
4. **Update relevant specs** with learnings and patterns discovered

### Key Patterns
1. **Async First**: Use async/await for all I/O operations
2. **Type Safety**: Pydantic models for API, TypeScript types for frontend
3. **Repository Pattern**: Database access through repositories
4. **Error Handling**: Use NetraException with proper context
5. **Unique IDs**: Use `generateUniqueId()` from `@/lib/utils` in React
6. **UI Design**: Glassmorphic design, NO blue gradient bars

## Common Gotchas and Solutions

### React Duplicate Key Warnings
**Problem**: Using `Date.now()` for keys creates duplicates in rapid renders
**Solution**: Always use `generateUniqueId()` from `@/lib/utils`
```typescript
// ❌ Wrong
key={Date.now()}

// ✅ Correct
key={generateUniqueId('msg')}
```

### WebSocket Test Failures
**Problem**: Hook tests fail without provider
**Solution**: Wrap with WebSocketProvider
```typescript
const wrapper = ({ children }) => (
  <WebSocketProvider>{children}</WebSocketProvider>
);
```

### ClickHouse Nested Array Errors
**Problem**: NO_COMMON_TYPE error (Code 386)
**Solution**: Use `arrayFirstIndex` instead of `indexOf`
See `SPEC/clickhouse.xml` for details

### Import Test Failures
**Problem**: New dependencies not in import tests
**Solution**: Update `app/tests/test_internal_imports.py` and `app/tests/test_external_imports.py`

### Test Runner Reliability Issues
**Problem**: Test runner may fail due to argument parsing or Unicode encoding issues
**Critical Rule**: If test runner fails, fix the runner FIRST before running actual tests
- Unicode emojis cause Windows terminal encoding errors
- Parallel arguments must be properly formatted (--parallel=auto not --parallel auto)
- Frontend test args should avoid Jest-specific options in the unified runner
**Solution**: Fix test_runner.py issues immediately, then run real tests

### Test Focus Strategy
**Avoid**: Testing basic Python functions, simple getters/setters, trivial utilities
**Focus On**: 
- Netra-specific business logic and integrations
- Complex dependency interactions (database, Redis, ClickHouse, LLM providers)
- Agent orchestration and WebSocket communication
- API endpoints with authentication and authorization
- Critical data flows and error handling scenarios
- Performance and concurrency edge cases

## Quick Reference Paths

### When Working On:
- **New API endpoint**: `app/routes/` → `app/schemas/` → `app/services/`
- **Agent changes**: `app/agents/supervisor.py`, `app/services/agent_service.py`
- **WebSocket issues**: `app/ws_manager.py`, `app/services/websocket/message_handler.py`
- **UI components**: `frontend/components/chat/`, ensure NO blue gradients
- **State management**: `frontend/store/unified-chat.ts`
- **Database**: `app/services/database/` for repositories
- **Authentication**: `app/auth/`, `app/services/security_service.py`

## Environment Setup

### Essential Variables
```bash
DATABASE_URL=postgresql://user:pass@localhost/netra
CLICKHOUSE_URL=clickhouse://localhost:9000/default
REDIS_URL=redis://localhost:6379
SECRET_KEY=your-secret-key
ANTHROPIC_API_KEY=your-anthropic-key
```

See `.env.example` for complete list


## LLM Configuration and Usage

### Where LLMs are Used
1. **Central LLM Manager** (`app/llm/llm_manager.py`):
   - Manages all LLM instances and configurations
   - Supports Google (Gemini) and OpenAI providers
   - Handles caching, mocking for dev mode, and streaming

2. **Configuration** (`app/schemas/Config.py:167-197`):
   - LLM configs in `AppConfig.llm_configs` dictionary
   - Each config has: provider, model_name, api_key, generation_config

3. **Agent Contexts**:
   - `triage`: Message classification and routing
   - `data`: Data analysis and processing
   - `optimizations_core`: AI workload optimization
   - `actions_to_meet_goals`: Goal-driven task execution
   - `reporting`: Report generation
   - `analysis`: General analysis tasks

### Adding New LLM Providers (e.g., GPT-4)

1. **Add to Config** (`app/schemas/Config.py`):
```python
llm_configs: Dict[str, LLMConfig] = {
    # Existing configs...
    "gpt4": LLMConfig(
        provider="openai",
        model_name="gpt-4",
        generation_config={"temperature": 0.7, "max_tokens": 4096}
    ),
}
```

2. **Add Secret Reference** (`app/schemas/Config.py:21-32`):
```python
SecretReference(
    name="openai-api-key",
    target_models=["llm_configs.gpt4"],
    target_field="api_key"
)
```

3. **Set Environment Variable**:
```bash
OPENAI_API_KEY=your-api-key
```

4. **Use in Code**:
```python
response = await llm_manager.ask_llm(prompt, "gpt4")
```

## Recent Learnings (Update This Section!)

### 2025-08-11: Documentation Refresh Insights
- **Multi-Agent Architecture**: 7 specialized sub-agents (Triage, Data, OptimizationsCore, ActionsToMeetGoals, Reporting, SyntheticData, CorpusAdmin)
- **Apex Optimizer**: 30+ specialized optimization tools with dynamic routing
- **Test Levels**: Unified test runner with 5 levels (smoke, unit, integration, comprehensive, critical)
- **Frontend V5**: Glassmorphic design, single MainChat component, three-layer response cards
- **WebSocket**: Real-time with heartbeat, connection pooling, event buffering for debugging

### 2025-08-11: Critical Test Runner Updates
- **Unified Test Runner**: Single entry point `test_runner.py` replaces all individual runners
- **Test Levels with Clear Times**:
  - Smoke: < 30s for pre-commit validation
  - Unit: 1-2 min for component testing
  - Integration: 3-5 min for feature validation
  - Comprehensive: 10-15 min with coverage
  - Critical: 1-2 min for essential functionality
- **Automatic Report Generation**: All test results saved to `test_reports/` with JSON summaries
- **Simple Fallback**: Use `--simple` flag if main runner has issues

### 2025-01-11: Spec Organization
- Moved testing details to `SPEC/testing.xml`
- Moved architecture details to `SPEC/architecture.xml`
- Moved ClickHouse troubleshooting to `SPEC/clickhouse.xml`
- Keep CLAUDE.md focused on principles and quick reference

### 2025-01-11: LLM Configuration
- LLM manager supports Google and OpenAI providers out of the box
- All LLM configs centralized in `app/schemas/Config.py`
- Secrets managed via SecretReference system
- Dev mode can disable LLMs with `DEV_MODE_DISABLE_LLM=true`

### 2025-01-11: Startup Check False Warnings Fix
- **Problem**: Services showing as unavailable despite successful connections
- **Root Causes**:
  1. Redis `set()` method parameter mismatch (`expire` vs `ex`)
  2. Missing Redis `delete()` method in RedisManager
  3. Missing `await` for async ClickHouse `execute_query()` method
- **Solution**: Added backward compatibility for both parameters, implemented delete method, added await
- **Prevention**: Always verify method signatures match between caller and implementation
- **Note**: ClickHouse client uses `execute_query()` not `execute()` for async operations

### 2025-01-11: ClickHouse Startup Check Fix
- **Problem**: `'ClickHouseDatabase' object has no attribute 'execute'` error during startup checks
- **Root Cause**: Using wrong method name - should be `execute_query()` not `execute()`
- **Solution**: Updated `app/startup_checks.py` line 287 to use `client.execute_query()`
- **Files Changed**: `app/startup_checks.py:287-290`

### 2025-01-11: Database Schema Migration
- **Problem**: Missing tables and columns causing schema validation errors
- **Tables Added**: `tool_usage_logs`, `ai_supply_items`, `research_sessions`, `supply_update_logs`
- **Columns Added to userbase**: `tool_permissions`, `plan_expires_at`, `feature_flags`, `payment_status`, `auto_renew`, `plan_tier`, `plan_started_at`, `trial_period`
- **Migration Created**: `bb39e1c49e2d_add_missing_tables_and_columns.py`
- **Note**: Some column mismatches remain but app starts successfully

### 2025-08-11: Critical E2E Test Coverage Enhancement
- **Problem**: Demo brittleness despite 60%+ test coverage - tests focused on happy paths, missing real-world scenarios
- **Root Causes Identified**:
  1. WebSocket state desynchronization during reconnections
  2. Race conditions in Zustand store updates
  3. Agent orchestration failures under load
  4. Missing circuit breaker and retry logic tests
  5. No tests for memory leaks or performance degradation
- **Solution**: Implemented 50 critical e2e tests focusing on:
  - WebSocket resilience (connection pooling, heartbeat, network partitions)
  - State synchronization (race conditions, layer data accumulation)
  - Agent orchestration (timeout recovery, parallel execution, error cascades)
  - Error recovery (circuit breakers, exponential backoff, error boundaries)
- **Key Test Patterns Implemented**:
  1. Network partition simulation: `cy.intercept('**/ws**', { forceNetworkError: true })`
  2. Memory leak detection: Track `performance.memory.usedJSHeapSize` across operations
  3. Concurrent update testing: Fire multiple state updates in parallel
  4. Circuit breaker validation: Track failure counts and verify service degradation
- **Test Files Created**:
  - `critical-websocket-resilience.cy.ts` - 15 comprehensive WebSocket tests
  - `critical-state-synchronization.cy.ts` - 10 state management tests
  - `critical-agent-orchestration-recovery.cy.ts` - 10 agent coordination tests
- **Prevention**: Always test failure scenarios, not just success paths. Focus on:
  - Concurrent operations and race conditions
  - Network instability and reconnection scenarios
  - Memory usage over time
  - Error cascade prevention
  - Performance under load

### Add new learnings here to prevent regression...