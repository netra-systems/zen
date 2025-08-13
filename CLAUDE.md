# CLAUDE.md

## 🔴 CRITICAL: MODULE-BASED ARCHITECTURE (300 LINES MAX, 8 LINES PER FUNCTION)
**MANDATORY**: Every file MUST be ≤300 lines. ALL functions MUST be ≤8 lines.
- Files exceeding 300 lines MUST be split into focused modules BEFORE implementation
- Functions exceeding 8 lines MUST be split into smaller functions IMMEDIATELY
- Plan module boundaries BEFORE coding - don't code first then split
- Each module = single responsibility, clear interface, testable unit
- Each function = single task, 8 lines maximum (no exceptions)

## Core Principles

### 1. ULTRA DEEP THINK (Required 3x)
- **FIRST**: Ultra deep think BEFORE any implementation
- **SECOND**: Think deeply about edge cases, performance, system impacts  
- **THIRD**: Ultra thinking required for complex problems - this is your masterpiece

### 2. Specs are Law
- `SPEC/*.xml` = Source of truth (not suggestions)
- Update specs BEFORE code changes
- Document learnings in specs to prevent regression

### 3. 300-LINE MODULE ARCHITECTURE  
**CRITICAL**: No file exceeds 300 lines - enforce through modular design:
- Split by responsibility, not arbitrary line counts
- Plan modules during design phase
- Each module must have clear interface and single purpose

## Project Overview
**Netra AI Optimization Platform** - Enterprise AI workload optimization with multi-agent architecture and WebSocket communication.

## Quick Start
```bash
python dev_launcher.py --dynamic --no-backend-reload  # Start dev
python test_runner.py --level smoke                   # Validate (<30s)
```

## 🔴 MANDATORY SPECS (Read 3x Before Coding)

### Critical Specs - ALWAYS CONSULT FIRST
| Spec | Purpose | When |
|------|---------|------|
| [`type_safety.xml`](SPEC/type_safety.xml) | **#1 PRIORITY** - Type safety, no duplicates | BEFORE any code |
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
| **Fixes** | [`learnings.xml`](SPEC/learnings.xml) - Common gotchas |

## ⚠️ CRITICAL RULES (Memorize These)

### BEFORE Any Code Change (Non-Negotiable)
1. **READ** [`type_safety.xml`](SPEC/type_safety.xml) - NO DUPLICATES
2. **READ** [`conventions.xml`](SPEC/conventions.xml) - 300-LINE LIMIT  
3. **RUN** `python test_runner.py --level smoke` (<30s validation)
4. **CHECK** No test stubs in production code

### AFTER Any Code Change (Automatic)
1. **RUN** `code-quality-reviewer` agent
2. **RUN** `test-debug-expert` agent  
3. **FIX** all identified issues before proceeding

## 🚫 ANTI-PATTERNS (Never Do These)

### NO DUPLICATION - EVER
- **NEVER** create "enhanced", "v2", "improved" versions
- **NEVER** copy-paste-modify code  
- **ALWAYS** extend existing functions with options/parameters

### 300-LINE MODULES & 8-LINE FUNCTIONS (Repeat: This is MANDATORY)
- **PLAN** module boundaries BEFORE coding
- **SPLIT** at 300 lines MAX (not 301, not 350 - exactly 300)
- **SPLIT** functions at 8 lines MAX (not 9, not 10 - exactly 8)
- **DESIGN** for modularity from the start

### NO TEST STUBS
- **ZERO** test implementations in production services
- **REAL** code only - no placeholders
- **CHECK** [`no_test_stubs.xml`](SPEC/no_test_stubs.xml) always

## Key Patterns

### Type Safety (REPEAT: #1 PRIORITY)
- Pydantic models (backend)
- TypeScript types (frontend)  
- See [`type_safety.xml`](SPEC/type_safety.xml) FIRST

### Async/Repository Pattern
- async/await for ALL I/O
- Database via repositories only
- NetraException for errors

### UI Standards
- Glassmorphic design ONLY
- NO blue gradient bars
- `generateUniqueId()` for React keys

## Testing (Run smoke BEFORE commits)
```bash
python test_runner.py --level smoke         # < 30s MANDATORY
python test_runner.py --level comprehensive # 97% coverage target
```

## Directory Structure
```
app/
├── routes/      # API endpoints
├── schemas/     # Pydantic models (TYPE SAFETY)
├── services/    # Business logic (300 LINES MAX)
├── agents/      # Multi-agent system
└── ws_manager.py

frontend/
├── components/  # UI (glassmorphic, 300 LINES MAX)
├── store/       # Zustand state
└── lib/utils    # generateUniqueId()
```

## Common Operations
| Task | Location |
|------|----------|
| API endpoint | `app/routes/` → `schemas/` → `services/` |
| WebSocket | `app/ws_manager.py` |
| UI | `frontend/components/` (NO blue gradients) |
| Database | `app/services/database/` repositories |

## 📝 MODULE PLANNING (3rd Reminder: 300 Lines MAX)

### BEFORE Writing Any Code:
1. **ULTRA THINK** - Deep analysis first
2. **PLAN MODULES** - Design boundaries for 300-line limit
3. **CHECK TYPES** - Read [`type_safety.xml`](SPEC/type_safety.xml)
4. **NO DUPLICATES** - Search for existing implementations

### Module Design Checklist:
- [ ] Each file ≤300 lines
- [ ] Each function ≤8 lines (MANDATORY)
- [ ] Single responsibility per module
- [ ] Clear interfaces between modules
- [ ] No "enhanced" versions of existing code
- [ ] Test coverage maintained

## Quick Fixes
- **React keys**: `generateUniqueId('prefix')`
- **WebSocket tests**: Wrap with `WebSocketProvider`
- **ClickHouse arrays**: `arrayElement()` not direct indexing
- **Test stubs**: Remove immediately - REAL code only

## 🎯 FINAL REMINDERS (Ultra Think 3x)

1. **300-LINE MODULES** - Plan before coding, split at boundaries
2. **8-LINE FUNCTIONS** - Every function ≤8 lines (MANDATORY)
3. **TYPE SAFETY FIRST** - Read [`type_safety.xml`](SPEC/type_safety.xml) 
4. **NO DUPLICATION** - Extend, don't duplicate
5. **SMOKE TESTS** - Run before ANY commit
6. **ULTRA DEEP THINK** - This is your masterpiece

**Specs = Law. 300 lines = Maximum. 8 lines per function = Maximum. Ultra think = Always.**