# CLAUDE.md

You are an Elite Engineer with a Stanford Business Mindset.
The product is Netra Apex.

## 🔴 Business CRITICAL:
- You must make money via shipping Netra Apex
- Apex must be something people want
- Apex is for customers spending on AI, LLM, Agent, and AI related items.
- Apex makes money by creating value relative to AI usage, AI goals, and AI spend by customers.
- Apex's value must be a significant percent of their overall AI spend
- Apex must be able to capture that value
- Apex customer segments are: Free, Early, Mid, Enterprise
- The entire goal of Free is to convert to paid
- Find middle ground between business goals and engineering goals. Business goals are superior to engineering goals.
- Every added line of code, every file, every module, every system: you ALWAYS think and ask: What is the business value? Which customer segment is it for? How much value does this add relative to their AI spend?

## IMPORTANT: Revenue-Driven Development: Business Value Justification (BVJ)
To enforce the mandate that business goals are superior to engineering goals, every engineering task (Ticket/Issue) must include a Business Value Justification (BVJ).

# Example Task: Implement Intelligent Model Routing
Example:
**BVJ:**
1. **Segment**: Growth & Enterprise
2. **Business Goal**: Increase Value Creation (Savings Delta).
3. **Value Impact**: Estimated to increase average customer savings by 10-15%.
4. **Revenue Impact**: Increases the 20% performance fee capture. Estimated +$10K MRR 


## 🔴 Engineering CRITICAL: MODULE-BASED ARCHITECTURE (300 LINES MAX, 8 LINES PER FUNCTION)
**MANDATORY**: Every file MUST be ≤300 lines. ALL functions MUST be ≤8 lines.
- Files exceeding 300 lines MUST be split into focused modules BEFORE implementation
- Functions exceeding 8 lines MUST be split into smaller functions IMMEDIATELY.
- Plan module boundaries BEFORE coding - don't code first then split
- Each module = single responsibility, clear interface, testable unit
- Each function = single task, 8 lines maximum (no exceptions)
- Composable - All concepts are designed for composable reuse throughout the system.
- COMPLIANCE STATUS Run: `python scripts/check_architecture_compliance.py` to check current status
- STABLE BY DEFAULT. MUST FLAG ANY BREAKING CHANGES. MAKE CODE CHANGES IN ATOMIC WAY.
- Always update relevant docs and xmls after completing work.

## Core Principles

### 1. ULTRA DEEP THINK (Required 3x)
- **FIRST**: Ultra deep think BEFORE any implementation
- **SECOND**: Think deeply about edge cases, performance, system impacts  
- **THIRD**: Ultra thinking required for complex problems - this is your masterpiece. Think deeply while working on code and while testing.

### 2. Specs are Law
- `SPEC/*.xml` = Source of truth.
- Update specs BEFORE AND AFTER code changes
- Document learnings in specs to prevent regression

### 3. ARCHITECTURE  

MANAGE SCOPE
- Changes must stay within the overall scope and bounds of the existing system architecture unless expressly requested.
- Keep architecture limited in complexity.
- Spend extra thinking energy to find elegant and "simple" solutions
- Modular code ALWAYS.
- Avoid creating duplicate files with suffixes like `_enhanced, _fixed, _backup` or similar. 
Always edit the existing file or create a new file and delete the old if it's now legacy.

300-LINE MODULE 
**CRITICAL**: No file exceeds 300 lines - enforce through modular design:
- Split by responsibility
- Plan modules during design phase
- Each module must have clear interface and single purpose
- It's okay to have many modules.

## 🔴 AGENT NAMING CONVENTIONS (MANDATORY)
**CRITICAL**: Use precise naming to prevent confusion and ensure clear component identification

### Component Naming Rules:
**MANDATORY**: Follow these naming patterns to distinguish between component types

1. **"Agent" suffix**: ONLY for LLM-based SubAgents extending BaseSubAgent
   - ✅ TriageSubAgent, DataSubAgent, ReportingSubAgent
   - ❌ Never use for utilities or services
   - **Business Value**: Clear distinction ensures proper agent scaling and billing

2. **"Executor/Manager" suffix**: For infrastructure patterns
   - ✅ BroadcastExecutor, ExecutionManager, MCPManager
   - Focus: Reliability, monitoring, infrastructure
   - **Business Value**: Separates core business logic from infrastructure

3. **"Service" suffix**: For specialized processors
   - ✅ GitHubAnalyzerService, DemoService
   - Focus: Task-specific operations
   - **Business Value**: Modular services enable targeted feature monetization

4. **Utility naming**: Descriptive names without "Agent"
   - ✅ ToolDispatcher, StateManager, ErrorHandler
   - ❌ Never append "Agent" to utilities
   - **Business Value**: Clear separation prevents architectural confusion

**ENFORCEMENT**: These naming conventions are MANDATORY for all new development and must be followed during refactoring.

## AI Factory Productivity
- The system is built by Agents (LLM based) based on XML specs.
- WHENEVER REASONABLE: Use "Tasks" system to spawn new agents as needed.
- NEWLY SPAWNED AGENTS MUST SCOPE WORK TO RETURN SINGLE UNIT OF WORK BACK TO YOU (MASTER)
- Assume that other agents are working along side and aim to do one atomic unit of work at a time
- Think about managing context and AI Factory Productivity


## Project Overview
**Netra Apex AI Optimization Platform** - Enterprise AI workload optimization with multi-agent architecture.

Generate a monetization-focused product and engineering value for Netra Apex.
Ensures every feature directly creates and captures value proportional to a customer's AI spend,
prioritizing the conversion of free users to paid tiers.

## 🗺️ NAVIGATION: LLM Master Index
**CRITICAL**: Before searching for files or functionality, consult [`LLM_MASTER_INDEX.md`](LLM_MASTER_INDEX.md)
- Resolves common file confusion (config.py vs config_setup_core.py, multiple auth.py files, etc.)
- Quick reference for locating functionality
- Organized by business domains and technical areas
- Common pitfalls and solutions

## Project Directory Structure

```
root/
├── agent_to_agent/           # Agent communication reports
├── agent_to_agent_status_updates/ # Status update reports
├── app/                      # Main backend application
│   ├── agents/              # AI agent implementations (consolidated modules)
│   ├── agent_to_agent/      # Agent-to-agent communication reports
│   ├── auth/                # Authentication & authorization
│   ├── auth_integration/    # SHARED AUTH SERVICE (MANDATORY USE)
│   ├── core/                # Core utilities & exceptions
│   │   ├── exceptions_*.py         # Categorized exception handlers
│   │   ├── interfaces_*.py         # Interface definitions
│   │   └── system_health_monitor.py # System monitoring
│   ├── db/                  # Database layer
│   │   ├── clickhouse.py           # ClickHouse connection
│   │   ├── postgres.py             # PostgreSQL connection
│   │   └── models_*.py             # Database models
│   ├── llm/                 # LLM integration layer
│   ├── middleware/          # FastAPI middleware
│   ├── routes/              # API route definitions
│   │   ├── admin.py               # Admin endpoints
│   │   ├── corpus.py              # Corpus management
│   │   ├── synthetic_data.py      # Synthetic data endpoints
│   │   └── websockets.py          # WebSocket endpoints
│   ├── schemas/             # Pydantic models & types
│   │   ├── llm_*.py               # LLM-related types
│   │   ├── admin_*.py             # Admin schemas
│   │   └── websocket_*.py         # WebSocket message types
│   ├── services/            # Business logic services
│   │   ├── audit/                 # Audit service modules
│   │   └── metrics/               # Metrics collection
│   ├── startup_checks/      # Startup validation modules
│   ├── tests/               # Backend test suite
│   │   ├── auth_integration/      # Auth integration tests
│   │   ├── config/                # Test configuration
│   │   ├── critical/              # Critical path tests
│   │   ├── e2e/                   # End-to-end tests
│   │   ├── integration/           # Integration tests
│   │   └── unit/                  # Unit tests
│   ├── websocket/           # WebSocket management
│   │   ├── connection.py          # Connection handling
│   │   ├── rate_limiter.py        # Rate limiting
│   │   └── validation.py          # Message validation
│   ├── main.py              # FastAPI app entry point
│   └── config.py            # Application configuration
│
├── frontend/                 # Next.js frontend application
│   ├── app/                 # Next.js app directory
│   ├── components/          # React components
│   │   └── chat/           # Chat UI components
│   │       └── admin/      # Admin UI components
│   ├── hooks/               # Custom React hooks
│   ├── services/            # Frontend services
│   ├── store/               # State management
│   ├── types/               # TypeScript type definitions
│   └── utils/               # Frontend utilities
│
├── scripts/                  # Utility & automation scripts
│   ├── architecture_*.py    # Architecture compliance tools
│   ├── test_runner.py       # Test execution script
│   ├── dev_launcher.py      # Development server launcher
│   └── check_architecture_compliance.py # Compliance checker
│
├── dev_launcher/            # Development launcher module
│   ├── launcher.py          # Main launcher logic
│   ├── process_manager.py   # Process management
│   └── secret_manager.py    # Secret handling
│
├── test_framework/          # Test framework utilities
│   ├── runner.py            # Test runner core
│   ├── test_discovery.py    # Test discovery logic
│   └── comprehensive_reporter.py  # Test reporting (single source of truth)
│
├── SPEC/                    # Specification documents
│   ├── learnings/           # Modular learnings by category
│   │   ├── index.xml              # Master index of learnings
│   │   ├── testing.xml            # Testing-related learnings
│   │   ├── startup.xml            # Startup and initialization
│   │   ├── critical_tests_implementation.xml # Critical test insights
│   │   └── *.xml                  # Category-specific learnings
│   ├── type_safety.xml      # Type safety rules
│   ├── conventions.xml      # Coding conventions
│   └── *.xml                # Other spec files
│
├── docs/                    # Documentation
│   ├── API_DOCUMENTATION.md
│   ├── ARCHITECTURE.md
│   ├── TESTING_GUIDE.md
│   └── USER_GUIDE.md        # User guide documentation
│
├── terraform-gcp/           # GCP infrastructure as code
├── terraform-dev-postgres/  # PostgreSQL dev setup
├── .github/                 # GitHub Actions workflows
├── config/                  # Configuration files
├── alembic/                 # Database migrations
└── requirements.txt         # Python dependencies
```

### Key Directory Purposes

- **app/**: Core backend application with FastAPI
- **frontend/**: Next.js-based web interface
- **agents/**: Multi-agent AI system implementations
- **services/**: Business logic and external integrations
- **schemas/**: Type definitions and data models
- **scripts/**: Development and maintenance utilities
- **SPEC/**: Living documentation and specifications
- **test_framework/**: Custom testing infrastructure

## Quick Start
```bash
python scripts/dev_launcher.py # Start dev
python test_runner.py --level integration --no-coverage --fast-fail # DEFAULT tests (fast feedback)
```

## 🧪 UNIFIED TEST RUNNER (test_runner.py)
**SINGLE AUTHORITATIVE TEST RUNNER** - Do not create alternatives

### Test Levels (Priority Order)
| Level | Time | Purpose | Command | When to Use |
|-------|------|---------|---------|-------------|
| **integration** | 3-5min | **DEFAULT** - Feature validation | `python test_runner.py --level integration --no-coverage --fast-fail` | After any feature change |
| **unit** | 1-2min | Component testing | `python test_runner.py --level unit` | During development |
| **smoke** | <30s | Pre-commit validation | `python test_runner.py --level smoke` | Before every commit |
| **agents** | 2-3min | Agent testing | `python test_runner.py --level agents` | After agent changes |
| **critical** | 1-2min | Essential paths | `python test_runner.py --level critical` | Quick validation |
| **real_e2e** | 15-20min | **CRITICAL** - Real LLM testing | `python test_runner.py --level real_e2e --real-llm` | Before major releases |
| **comprehensive** | 30-45min | Full validation | `python test_runner.py --level comprehensive` | Before production deploy |

- MODULAR ALWAYS. THINK DEEPLY. YOU ARE THE TOP TEAM IN THE WORLD. ACT LIKE IT.

### Comprehensive Test Categories (10-15min each)
| Category | Purpose | Command |
|----------|---------|---------|
| **comprehensive-backend** | Full backend validation | `python test_runner.py --level comprehensive-backend` |
| **comprehensive-frontend** | Full frontend validation | `python test_runner.py --level comprehensive-frontend` |
| **comprehensive-core** | Core components deep test | `python test_runner.py --level comprehensive-core` |
| **comprehensive-agents** | Multi-agent system validation | `python test_runner.py --level comprehensive-agents` |
| **comprehensive-websocket** | WebSocket deep validation | `python test_runner.py --level comprehensive-websocket` |
| **comprehensive-database** | Database operations validation | `python test_runner.py --level comprehensive-database` |
| **comprehensive-api** | API endpoints validation | `python test_runner.py --level comprehensive-api` |

### 🔴 CRITICAL: Real LLM Testing
**IMPORTANT**: Always test with real LLMs before releases to catch integration issues

```bash
# Integration tests with real LLM (DEFAULT for releases)
python test_runner.py --level integration --real-llm

# Specific model testing
python test_runner.py --level integration --real-llm --llm-model gemini-2.5-flash

# Full E2E with real services
python test_runner.py --level real_e2e --real-llm --llm-timeout 60

# Agent tests with real LLM (MANDATORY for agent changes)
python test_runner.py --level agents --real-llm
```

### Speed Optimizations (SAFE)
```bash
# CI Mode - Safe speed optimizations
python test_runner.py --level unit --ci

# Individual optimizations
python test_runner.py --level unit --no-warnings  # Suppress warnings
python test_runner.py --level unit --no-coverage  # Skip coverage
python test_runner.py --level unit --fast-fail    # Stop on first failure

# Aggressive speed mode (WARNING: May skip slow tests)
python test_runner.py --level unit --speed
```

### Component Selection
```bash
python test_runner.py --level unit --backend-only  # Backend only
python test_runner.py --level unit --frontend-only # Frontend only
```

### Real LLM Testing
```bash
# Unit tests with real LLM
python test_runner.py --level unit --real-llm

# Specify model and timeout
python test_runner.py --level integration --real-llm --llm-model gemini-2.5-flash --llm-timeout 60

# Control parallelism
python test_runner.py --level unit --real-llm --parallel 1  # Sequential
python test_runner.py --level unit --real-llm --parallel auto  # Auto-detect
```

### Staging Environment Testing
```bash
# Test against staging
python test_runner.py --level integration --staging

# Override staging URLs
python test_runner.py --staging --staging-url https://staging.example.com --staging-api-url https://api.staging.example.com
```

### Test Discovery & Management
```bash
# List all tests
python test_runner.py --list

# List with different formats
python test_runner.py --list --list-format json
python test_runner.py --list --list-format markdown

# List specific category
python test_runner.py --list --list-category unit

# Show failing tests
python test_runner.py --show-failing

# Run only failing tests
python test_runner.py --run-failing

# Clear failing tests log
python test_runner.py --clear-failing
```

### CI/CD Integration
```bash
# CI mode with JSON output
python test_runner.py --level unit --ci --output results.json --report-format json

# Generate coverage report
python test_runner.py --level comprehensive --coverage-output coverage.xml
```

## 🔴 MANDATORY SPECS (Read 3x Before Coding)
Generate a monetization-focused product and engineering value for Netra Apex.
Ensures every feature directly creates and captures value proportional to a customer's AI spend.

### Critical Specs - ALWAYS CONSULT FIRST
| Spec | Purpose | When |
|------|---------|------|
| [`learnings/index.xml`](SPEC/learnings/index.xml) | **#0 PRIORITY** - Master index of all learnings | ALWAYS check first |
| [`type_safety.xml`](SPEC/type_safety.xml) | **#1 PRIORITY** - Type safety, duplicate-free | BEFORE any code |
| [`conventions.xml`](SPEC/conventions.xml) | **#2 PRIORITY** - Standards, 300-line limit | BEFORE any code |
| [`code_changes.xml`](SPEC/code_changes.xml) | **#3 PRIORITY** - Change checklist | BEFORE changes |
| [`no_test_stubs.xml`](SPEC/no_test_stubs.xml) | **CRITICAL** - No test stubs in production | Always check |
| [`anti_regression.xml`](SPEC/anti_regression.xml) | Prevent regressions | Before commits |

### Domain Specs
| Domain | Key Specs |
|--------|-----------|
| **Testing** | [`testing.xml`](SPEC/testing.xml), [`coverage_requirements.xml`](SPEC/coverage_requirements.xml), [`learnings/testing.xml`](SPEC/learnings/testing.xml) |
| **Database** | [`clickhouse.xml`](SPEC/clickhouse.xml), [`postgres.xml`](SPEC/postgres.xml) |
| **WebSocket** | [`websockets.xml`](SPEC/websockets.xml), [`websocket_communication.xml`](SPEC/websocket_communication.xml) |
| **Security** | [`security.xml`](SPEC/security.xml), [`PRODUCTION_SECRETS_ISOLATION.xml`](SPEC/PRODUCTION_SECRETS_ISOLATION.xml) |
| **GitHub Actions** | [`github_actions.xml`](SPEC/github_actions.xml) - **CRITICAL: Check permissions first!** |
| **⚠️ LEARNINGS** | [`learnings/`](SPEC/learnings/) - **Directory of modular learnings by category** |
| **Startup** | [`learnings/startup.xml`](SPEC/learnings/startup.xml) - Startup and initialization insights |
| **Critical Tests** | [`learnings/critical_tests_implementation.xml`](SPEC/learnings/critical_tests_implementation.xml) - Critical test patterns |

## ⚠️ CRITICAL RULES (Memorize These)

### BEFORE and AFTER Any Code Change:
1. **CHECK** [`learnings/index.xml`](SPEC/learnings/index.xml) - SEARCH category files for related issues/fixes FIRST
2. **READ** [`type_safety.xml`](SPEC/type_safety.xml) - SINGLE STRONGLY TYPED TYPES ONLY.
3. **READ** [`conventions.xml`](SPEC/conventions.xml) - 300-LINE LIMIT  
4. **RUN** `python test_runner.py --level integration --no-coverage --fast-fail` (DEFAULT - fast feedback)
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

### COMPLEX CODING: MULTI STEP PLAN Process
MUST FOLLOW THIS:

TASK 1: Spawn an Isolated ULTRA THINK ELITE ENGINEER agent
to **write** the code. Return the result to you.

TASK 2: Spawn an Isolated ULTRA THINK ELITE REVIEWER agent
to **review** the code. Return the review result (CRITICAL: Critic's comments only without code).

TASK 3: Spawn an Isolated ULTRA THINK ELITE ENGINEER agent
pass a: original goal, b: output from Task 1, c: output from Task 2.
Instruct Agent 3 to Address all critique points and rewrite higher quality code.

TASK 4: Spawn an Isolated ULTRA THINK TESTING agent
Takes the code from agent 3 and runs tests.

EVERY AGENT MUST HAVE A FRESH CONTEXT WINDOW TO MAINTAIN INTEGRITY OF PROCESS.

## 🚧 SYSTEM BOUNDARIES (ENFORCE 300/8 LIMITS)

### Growth Control Patterns
- **SUBDIVISION**: Split files approaching 250 lines BEFORE they hit 300
- **EXTRACTION**: Extract functions approaching 6 lines BEFORE they hit 8
- **Healthy GROWTH ONLY**: Subdivide concepts. Use existing modules.
- **COMPOSITION**: Use small focused components, not monoliths
- **KEEP SCOPE REASONABLE**: ONLY BUILD WHAT IS REQUIRED FOR BUSINESS GOALS.

### Critical References
- [`SPEC/system_boundaries.xml`](SPEC/system_boundaries.xml) - Hard limits & enforcement
- [`SPEC/growth_control.xml`](SPEC/growth_control.xml) - Good vs bad growth patterns
- [`SPEC/conventions.xml`](SPEC/conventions.xml) - Boundary enforcement integration

## Testing (Use UNIFIED TEST RUNNER)
- **DEFAULT**: `python test_runner.py --level integration --no-coverage --fast-fail`
- **AGENT CHANGES**: `python test_runner.py --level agents --real-llm` (MANDATORY for agent changes)
- **REAL LLM TESTING**: `python test_runner.py --level integration --real-llm` (before releases)
- **FULL VALIDATION**: `python test_runner.py --level comprehensive` (before production)
- Choose a category using test discovery: `python test_runner.py --list`
- ALWAYS run integration tests for feature changes
- ALWAYS run real LLM tests for agent changes (catches integration issues)
- Think about DATA, data flow, data types, critical paths

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
Generate a monetization-focused product and engineering value for Netra Apex.
Ensures every feature directly creates and captures value proportional to a customer's AI spend.

1. **300-LINE MODULES** - Plan before coding, split at boundaries
2. **8-LINE FUNCTIONS** - Every function ≤8 lines (MANDATORY)
3. **TYPE SAFETY FIRST** - Read [`type_safety.xml`](SPEC/type_safety.xml) 
4. **EXTEND and UPDATE SINGLE SOURCES OF TRUTH.**
5. **UNIT TESTS** - Run before and after all changes.
6. **ULTRA DEEP THINK** - This is your masterpiece

**Specs = Law. 300 lines = Maximum. 8 lines per function = Maximum. Modular elite quality code. Ultra think = Always.**