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


## Recent Learnings (Update This Section!)

### 2025-01-11: Spec Organization
- Moved testing details to `SPEC/testing.xml`
- Moved architecture details to `SPEC/architecture.xml`
- Moved ClickHouse troubleshooting to `SPEC/clickhouse.xml`
- Keep CLAUDE.md focused on principles and quick reference

### Add new learnings here to prevent regression...