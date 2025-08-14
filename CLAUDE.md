# CLAUDE.md

You are an Elite Engineer.

## 🔴 CRITICAL: MODULE-BASED ARCHITECTURE (300 LINES MAX, 8 LINES PER FUNCTION)
**MANDATORY**: Every file MUST be ≤300 lines. ALL functions MUST be ≤8 lines.
- Files exceeding 300 lines MUST be split into focused modules BEFORE implementation
- Functions exceeding 8 lines MUST be split into smaller functions IMMEDIATELY
- Plan module boundaries BEFORE coding - don't code first then split
- Each module = single responsibility, clear interface, testable unit
- Each function = single task, 8 lines maximum (no exceptions)
- COMPLIANCE STATUS Run: `python scripts/check_architecture_compliance.py` to check current status

## Core Principles

### 1. ULTRA DEEP THINK (Required 3x)
- **FIRST**: Ultra deep think BEFORE any implementation
- **SECOND**: Think deeply about edge cases, performance, system impacts  
- **THIRD**: Ultra thinking required for complex problems - this is your masterpiece. Think deeply while working on code and while testing.

### 2. Specs are Law
- `SPEC/*.xml` = Source of truth.
- Update specs BEFORE AND AFTER code changes
- Document learnings in specs to prevent regression

### 3. 300-LINE MODULE ARCHITECTURE  
**CRITICAL**: No file exceeds 300 lines - enforce through modular design:
- Split by responsibility
- Plan modules during design phase
- Each module must have clear interface and single purpose

## Project Overview
**Netra AI Optimization Platform** - Enterprise AI workload optimization with multi-agent architecture.

## Quick Start
```bash
python dev_launcher.py # Start dev
python test_runner.py --level unit # DEFAULT tests
```

## 🔴 MANDATORY SPECS (Read 3x Before Coding)

### Critical Specs - ALWAYS CONSULT FIRST
| Spec | Purpose | When |
|------|---------|------|
| [`type_safety.xml`](SPEC/type_safety.xml) | **#1 PRIORITY** - Type safety, duplicate-free | BEFORE any code |
| [`conventions.xml`](SPEC/conventions.xml) | **#2 PRIORITY** - Standards, 300-line limit | BEFORE any code |
| [`code_changes.xml`](SPEC/code_changes.xml) | **#3 PRIORITY** - Change checklist | BEFORE changes |
| [`no_test_stubs.xml`](SPEC/no_test_stubs.xml) | **CRITICAL** - No test stubs in production | Always check |
| [`anti_regression.xml`](SPEC/anti_regression.xml) | Prevent regressions | Before commits |

### Domain Specs
| Domain | Key Specs |
|--------|-----------|
| **Testing** | [`testing.xml`](SPEC/testing.xml), [`coverage_requirements.xml`](SPEC/coverage_requirements.xml) |
| **Database** | [`clickhouse.xml`](SPEC/clickhouse.xml), [`postgres.xml`](SPEC/postgres.xml) |
| **WebSocket** | [`websockets.xml`](SPEC/websockets.xml), [`websocket_communication.xml`](SPEC/websocket_communication.xml) |
| **Security** | [`security.xml`](SPEC/security.xml), [`PRODUCTION_SECRETS_ISOLATION.xml`](SPEC/PRODUCTION_SECRETS_ISOLATION.xml) |
| **GitHub Actions** | [`github_actions.xml`](SPEC/github_actions.xml) - **CRITICAL: Check permissions first!** |
| **⚠️ LEARNINGS** | [`learnings.xml`](SPEC/learnings.xml) - **ALWAYS CHECK FIRST - Contains fixes for recurring issues** |

## ⚠️ CRITICAL RULES (Memorize These)

### BEFORE and AFTER Any Code Change:
1. **CHECK** [`learnings.xml`](SPEC/learnings.xml) - SEARCH for related issues/fixes FIRST
2. **READ** [`type_safety.xml`](SPEC/type_safety.xml) - SINGLE STRONGLY TYPED TYPES ONLY.
3. **READ** [`conventions.xml`](SPEC/conventions.xml) - 300-LINE LIMIT  
4. **RUN** `python test_runner.py --level unit` (DEFAULT)
5. UPDATE specs with POSITIVE wording only.

### AFTER Any Code Change (Automatic)
1. **RUN** `code-quality-reviewer`
2. **RUN** `test-debug-expert`  
3. **FIX** all identified issues before proceeding
- **ALWAYS** double check you are updating, creating, editing: SINGLE SOURCES OF TRUTH
- **ALWAYS** extend existing functions with options/parameters

### 300-LINE MODULES & 8-LINE FUNCTIONS (Repeat: This is MANDATORY)
- **PLAN** module boundaries BEFORE coding
- **SPLIT** at 300 lines MAX
- **SPLIT** functions at 8 lines MAX
- **DESIGN** for modularity from the start

### REAL CODE ALWAYS
- **REAL** code only - placeholders-are-bad
- **CHECK** [`no_test_stubs.xml`](SPEC/no_test_stubs.xml) always

## Key Patterns

### Type Safety (REPEAT: TOP PRIORITY)
- Pydantic models (backend)
- TypeScript types (frontend)  
- See [`type_safety.xml`](SPEC/type_safety.xml) FIRST

### Async/Repository Pattern
- async/await for ALL I/O
- Database via repositories only
- NetraException for errors

### UI Standards
- Glassmorphic design
- `generateUniqueId()` for React keys

## Testing (ALWAYS run UNIT tests for noticeable changes)
- Choose a category using test discovery

## 📝 MODULE PLANNING (3rd Reminder: 300 Lines MAX)

### BEFORE Writing Any Code:
1. **ULTRA THINK** - Deep analysis first
2. **PLAN MODULES** - Design boundaries for 300-line limit
3. **CHECK TYPES** - Read [`type_safety.xml`](SPEC/type_safety.xml)
4. **NO DUPLICATES** - Search for existing implementations

### Module Design Checklist:
- [ ] Each file ≤300 lines
- [ ] Each function ≤8 lines (MANDATORY)
- [ ] Strong types - all new params must have strong types.
- [ ] Single responsibility per module
- [ ] Clear interfaces between modules
- [ ] Single source of truth - update existing items.
- [ ] Test coverage maintained
- [ ] Tests pass

# Tools notes
- Use tools like read file, replace_all, etc.

## 🎯 FINAL REMINDERS (Ultra Think 3x)

1. **300-LINE MODULES** - Plan before coding, split at boundaries
2. **8-LINE FUNCTIONS** - Every function ≤8 lines (MANDATORY)
3. **TYPE SAFETY FIRST** - Read [`type_safety.xml`](SPEC/type_safety.xml) 
4. **EXTEND and UPDATE SINGLE SOURCES OF TRUTH.**
5. **UNIT TESTS** - Run before ANY commit (smoke only for most trivial)
6. **ULTRA DEEP THINK** - This is your masterpiece

**Specs = Law. 300 lines = Maximum. 8 lines per function = Maximum. Ultra think = Always.**