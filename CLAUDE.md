# CLAUDE.md

Guidance for Claude Code when working with the Netra AI Optimization Platform.

## Core Principles

### 1. Think Deeply by Default
- Ultra deep think: Analyze problems thoroughly before implementing solutions
- Consider edge cases, performance implications, and system-wide impacts
- Use ultra-thinking capabilities when available for complex problems

### 2. Document Learnings to Prevent Regression
- Update this file or relevant specs when discovering patterns
- Document gotchas, workarounds, and non-obvious behaviors  
- Create new specs for complex domains rather than bloating this file

### 3. Specs are Source of Truth
- Specs in `SPEC/*.xml` contain detailed requirements and patterns
- Update specs BEFORE implementing changes
- Reference specs for detailed guidelines

### 4. Efficient Feature Implementation
- **IMMEDIATE EXECUTION**: Launch parallel Tasks for multi-part features
- **MINIMAL CHANGES**: Preserve existing patterns and structures
- **PARALLEL BY DEFAULT**: Use concurrent task execution for efficiency
- **CONTEXT OPTIMIZATION**: Strip comments when analyzing code to reduce context usage

## Project Overview

**Netra AI Optimization Platform** - Enterprise-grade system for optimizing AI workloads with multi-agent architecture, real-time WebSocket communication, and glassmorphic UI design.

## Quick Start

```bash
# Start development environment
python dev_launcher.py --dynamic --no-backend-reload --load-secrets

# Quick validation before changes (< 30 seconds)
python test_runner.py --level smoke
```

## Specification Map

### 🔴 Critical Specs (Always Consult)
| Spec | Purpose |
|------|---------|
| [`code_changes.xml`](SPEC/code_changes.xml) | **MANDATORY** checklist for any code modification |
| [`anti_regression.xml`](SPEC/anti_regression.xml) | Patterns to prevent common regressions |
| [`no_test_stubs.xml`](SPEC/no_test_stubs.xml) | **CRITICAL** - Prevents test stubs in production |
| [`conventions.xml`](SPEC/conventions.xml) | Coding standards and patterns |
| [`instructions.xml`](SPEC/instructions.xml) | General development guidelines |

### 📚 Domain Specs
| Domain | Specs |
|--------|-------|
| **Testing** | [`testing.xml`](SPEC/testing.xml), [`coverage_requirements.xml`](SPEC/coverage_requirements.xml), [`test_update_spec.xml`](SPEC/test_update_spec.xml) |
| **Architecture** | [`architecture.xml`](SPEC/architecture.xml), [`core.xml`](SPEC/core.xml), [`services.xml`](SPEC/services.xml) |
| **Database** | [`database.xml`](SPEC/database.xml), [`clickhouse.xml`](SPEC/clickhouse.xml), [`postgres.xml`](SPEC/postgres.xml) |
| **UI/UX** | [`unified_chat_ui_ux.xml`](SPEC/unified_chat_ui_ux.xml), [`ui_ux_master.xml`](SPEC/ui_ux_master.xml), [`frontend_layout.xml`](SPEC/frontend_layout.xml) |
| **Agents** | [`subagents.xml`](SPEC/subagents.xml), [`agent_tracking.xml`](SPEC/agent_tracking.xml), [`agent_pagerank.xml`](SPEC/agent_pagerank.xml) |
| **WebSocket** | [`websockets.xml`](SPEC/websockets.xml), [`websocket_communication.xml`](SPEC/websocket_communication.xml), [`ui_ux_websocket.xml`](SPEC/ui_ux_websocket.xml) |
| **LLM** | [`llm.xml`](SPEC/llm.xml) - Configuration, providers, structured generation |
| **Security** | [`security.xml`](SPEC/security.xml), [`tool_auth_system.xml`](SPEC/tool_auth_system.xml), [`PRODUCTION_SECRETS_ISOLATION.xml`](SPEC/PRODUCTION_SECRETS_ISOLATION.xml) |
| **Troubleshooting** | [`learnings.xml`](SPEC/learnings.xml) - Historical fixes and common gotchas |

### 🧹 Maintenance Specs
- [`documentation_maintenance.xml`](SPEC/documentation_maintenance.xml) - Rules for updating CLAUDE.md and docs
- [`LEGACY_CODE_CLEANUP.xml`](SPEC/LEGACY_CODE_CLEANUP.xml) - Legacy code identification
- [`failing_test_management.xml`](SPEC/failing_test_management.xml) - Test failure handling
- [`missing_tests.xml`](SPEC/missing_tests.xml) - Test coverage gaps

## Critical Rules

### Before Any Code Change
1. ✅ Consult [`SPEC/code_changes.xml`](SPEC/code_changes.xml)
2. ✅ Run smoke tests: `python test_runner.py --level smoke`
3. ✅ Update import tests when adding dependencies
4. ✅ Update relevant specs with learnings
5. ✅ Check [`SPEC/no_test_stubs.xml`](SPEC/no_test_stubs.xml) - NO test stubs in production

### After Any Code Change
**MANDATORY**: After implementing code changes, automatically:
1. 🔍 Run the `code-quality-reviewer` agent to check for quality, conventions, and regression risks
2. 🧪 Run the `test-debug-expert` agent to verify tests pass and coverage is maintained
3. 📋 Address any issues identified by either agent before considering the task complete

This automated review process ensures all changes meet project standards and don't introduce regressions.

### Key Development Patterns
- **Async First**: Use async/await for all I/O operations
- **Type Safety**: Pydantic models (backend), TypeScript types (frontend)
- **Repository Pattern**: All database access through repositories
- **Error Handling**: Use NetraException with proper context
- **Unique IDs**: Use `generateUniqueId()` from `@/lib/utils` in React
- **UI Design**: Glassmorphic design, NO blue gradient bars
- **File Organization**: ALWAYS create new files in appropriate folders - keep top directory clean
- **NO Test Stubs**: NEVER add test implementations in production services - real code only
- **Preserve Patterns**: Follow project's established architecture and component patterns
- **Reuse Utilities**: Use existing utility functions, avoid duplicating functionality

## Testing Strategy

```bash
# Unified test runner with 5 levels
python test_runner.py --level smoke         # < 30s - Pre-commit validation
python test_runner.py --level unit          # 1-2 min - Component testing
python test_runner.py --level integration   # 3-5 min - Feature validation
python test_runner.py --level comprehensive # 10-15 min - Full coverage (97% target)
python test_runner.py --level critical      # 1-2 min - Essential paths

# Fallback if runner has issues
python test_runner.py --simple
```

**Focus Testing On:**
- Netra-specific business logic
- Complex integrations (database, Redis, ClickHouse, LLM)
- Agent orchestration and WebSocket communication
- API endpoints with auth
- Critical data flows and error handling
- Performance and concurrency edge cases

**Avoid Testing:**
- Basic Python functions
- Simple getters/setters
- Trivial utilities

## Quick Reference

### Directory Structure
```
app/
├── routes/          # API endpoints
├── schemas/         # Pydantic models
├── services/        # Business logic
│   └── database/    # Repository pattern
├── agents/          # Multi-agent system
├── ws_manager.py    # WebSocket handling
└── llm/            # LLM management

frontend/
├── components/chat/ # UI components (glassmorphic)
├── store/          # Zustand state management
└── lib/utils       # Utilities (generateUniqueId)
```

### Common Operations

| Task | Command/Location |
|------|-----------------|
| Add API endpoint | `app/routes/` → `app/schemas/` → `app/services/` |
| Modify agents | `app/agents/supervisor.py`, `app/services/agent_service.py` |
| Fix WebSocket | `app/ws_manager.py`, `app/services/websocket/message_handler.py` |
| Update UI | `frontend/components/chat/` (NO blue gradients) |
| State management | `frontend/store/unified-chat.ts` |
| Database access | `app/services/database/` repositories |
| Authentication | `app/auth/`, `app/services/security_service.py` |

### Environment Variables
```bash
DATABASE_URL=postgresql://user:pass@localhost/netra
CLICKHOUSE_URL=clickhouse://localhost:9000/default
REDIS_URL=redis://localhost:6379
SECRET_KEY=your-secret-key
ANTHROPIC_API_KEY=your-anthropic-key  # Or other LLM keys
```

See `.env.example` for complete list.

## Feature Implementation Workflow

### For Complex Features (3+ components)
1. **Component**: Create main component file
2. **Styles**: Create component styles/CSS
3. **Tests**: Create test files  
4. **Types**: Create type definitions
5. **Hooks**: Create custom hooks/utilities
6. **Integration**: Update routing, imports, exports
7. **Configuration**: Update package.json, documentation, config files
8. **Validation**: Run tests, verify build, check for conflicts

### Implementation Guidelines
- Launch parallel Tasks immediately for multi-part features
- Each task handles ONLY specified files or file types
- Combine small config/doc updates to prevent over-splitting
- Skip clarification questions unless absolutely critical

## Common Gotchas

### Quick Fixes
- **React duplicate keys**: Use `generateUniqueId('prefix')` not `Date.now()`
- **WebSocket test failures**: Wrap tests with `WebSocketProvider`
- **ClickHouse array errors**: Use `arrayElement()` not direct indexing - see [`clickhouse.xml`](SPEC/clickhouse.xml)
- **Import test failures**: Update `app/tests/test_internal_imports.py` and `test_external_imports.py`
- **Test runner issues**: Fix runner FIRST before running tests (Unicode, parallel args)
- **Test stubs in services**: Remove immediately - see [`no_test_stubs.xml`](SPEC/no_test_stubs.xml)

For detailed troubleshooting and historical fixes, see [`SPEC/learnings.xml`](SPEC/learnings.xml).

## Recent Updates

- **2025-08-12**: Reorganized CLAUDE.md, created [`learnings.xml`](SPEC/learnings.xml) for historical fixes
- **2025-08-11**: Unified test runner with 5 levels, comprehensive E2E test coverage
- **2025-01-11**: LLM configuration centralized, spec organization improved

---

**Remember**: When in doubt, consult the specs. They are the source of truth. Always ultra think deeply.