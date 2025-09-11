# 🚨 ULTRA THINK DEEPLY ALWAYS. COMPLETE FEATURE FREEZE.

**CRITICAL MISSION:** Get Golden Path working - users login and get AI responses back.

**STABILITY FIRST:** Prove changes maintain system stability and don't introduce breaking changes.

**NON-NEGOTIABLE RULES:**
- SSOT (Single Source of Truth) compliance is mandatory (within each service (5.1)). @SSOT_IMPORT_REGISTRY.md
- This document overrides all other instructions
- No "standalone" or "simple" files
- No bypassing established patterns

**GOLDEN PATH PRIORITY:**
1. Users login and get real AI message responses
2. All else is secondary
3. Staging GCP deployment only (ignore docker)
4. Minimal fixes, zero new features

**BETA GOLDEN PATH**
1. Focus on effective golden path or beta.
2. Ignore smaller isues, like docker issues etc.
3. No philosophical items, practical resolutions for golden path beta working.

**Context Matters: Be accurate and naunced**
1. This is NEW active development beta software for a startup.
2. Rank importance of issue relative to impact and ease of fix (because of dev nature).
3. Avoid making sweeping claims or catastrophizing.
4. Play devils advocate. What is opposite view on spectrum? Then where is the middle ground?
5. Don't be fooled by duplicate names, various classes do have real arhitecture meaning and differences.

**MISSION:** Netra Apex AI Optimization Platform - balance engineering excellence with business goals through multi-agent AI collaboration.

**PROCESS TRACKING:** Log repetitive patterns and sub-optimal solutions. Before repeating approaches, prove new method differs from prior logged mistakes. 

## USE SUB AGENTS (TASKS) EXTENSIVELY

**AGENT MANAGEMENT STRATEGIES:**
1. **Context Rotation:** Spawn new agents for specific tasks with clean contexts
2. **Timeout Controls:** 30s simple tasks, 5min complex tasks
3. **Progressive Scope:** Start minimal, add info only when needed
4. **Fallback Hierarchy:** Precise → Broader → Manual → Human escalation
5. **Anti-Stuck Patterns:** Detect repetition, auto-trigger context reset

**CORE DIRECTIVES:**
- **Explain Reasoning:** Step-by-step analysis mandatory
- **Ship for Value:** Fast time-to-market as startup
- **Think with Nuance:** Balanced, practical decisions
- **No Test Cheating:** Tests must be real and fail properly

## 0. GOLDEN PATH MISSION

**PRIMARY GOAL:** Get GOLDEN_PATH_USER_FLOW_COMPLETE.md working - users login → get AI responses.

**PRIORITIES:**
1. **Business Value:** Working system serves business (Business > System > Tests)
2. **User Experience:** Chat works end-to-end 
3. **Staging Parity:** Staging environment functional
4. **Configuration:** Stable across environments

**RULES:**
- This document overrides existing code conflicts
- Use existing SSOT methods, never create new scripts
- SSOT refactoring only, no new features


## 🏗️ ARCHITECTURE RULES

**MANDATORY READING:** @USER_CONTEXT_ARCHITECTURE.md - Factory-based isolation for multi-user execution.

**CRITICAL AWARENESS:**
1. **Race Conditions:** System has async/websockets - plan for concurrency
2. **95% First:** Nail common cases before edge cases
3. **Multi-User System:** Complete user isolation required
4. **Config Independence:** Each environment (TEST/DEV/STAGING/PROD) needs separate configs
5. **Error Investigation:** Find "error behind the error" - dig 10 levels deep
6. **Business Value Focus:** Minimal scope for startup efficiency
7. **No "Enterprise" Features:** No fallbacks/reliability without explicit request
8. **Real Tests:** E2E auth mandatory, no try/except blocks in tests
9. **SSOT Updates:** Never recreate legacy code to pass old tests

**KEY ARCHITECTURE DOCS:**
- @USER_CONTEXT_ARCHITECTURE.md - Factory isolation patterns
- @MIGRATION_PATHS_CONSOLIDATED.md - Migration coordination
- @AGENT_ARCHITECTURE_DISAMBIGUATION_GUIDE.md - Agent workflows
- @naming_conventions_business_focused.xml - Business naming
- @index.md - Documentation index

**ERROR HANDLING:** Expect failures, log everything loud, no silent errors or undocumented fallbacks.

-----

## 1. BUSINESS MANDATE

**CORE PRINCIPLE:** Netra Apex captures value from customer AI spend.

**BUSINESS RULES:**
- **Product-Market Fit:** Make Apex indispensable for AI infrastructure
- **Customer Tiers:** Free → Early → Mid → Enterprise (conversion focus)
- **MVP/YAGNI:** Every component needs immediate business justification
- **AI Leverage:** Multi-agent workflows as force multipliers
- **Complete Tasks:** Finish jobs fully, use sub-agents extensively
- **Chat is 90% of Value:** Focus on substantive AI-powered interactions

### 1.1. Chat Business Value (90% of Platform)
- **Real Solutions:** Agents solve actual problems with actionable results
- **Responsive UX:** Quality measured by AI response substance
- **Timely Updates:** Real-time progress with meaningful context
- **Complete Flow:** End-to-end agent execution works
- **IP Protection:** Shield implementation secrets from users

### 1.2. Business Value Justification (BVJ)
Every task needs:
1. **Segment:** Free/Early/Mid/Enterprise/Platform
2. **Goal:** Conversion/Expansion/Retention/Stability
3. **Value Impact:** How this improves customer AI operations
4. **Revenue Impact:** Quantifiable benefit to Netra

-----

## 2. ENGINEERING PRINCIPLES

**CORE:** Globally coherent and modular architecture. Globally correct > locally correct.

### 2.1. Architectural Tenets
- **SRP:** One clear purpose per module/function/task
- **SSOT:** One canonical implementation per service (configs are environment-specific exceptions)
- **Search First:** Check existing implementations before creating
- **Atomic Scope:** Complete functional updates only
- **No Random Features:** Minimal changes for specific goals
- **Basics First:** Common flows before edge cases
- **Remove Legacy:** Delete old code during refactors
- **Interface-First:** Define contracts before implementation
- **Stability by Default:** Atomic changes, flag breaking changes

**TEST DISCOVERY:** `python tests/unified_test_runner.py`
Use the test gardner command if test collection issues.
**COMPREHENSIVE TEST GUIDE:** See `TEST_EXECUTION_GUIDE.md` for complete test execution methodology, including how to run all tests without fast-fail and separate collection errors from test failures.
**COMPLIANCE:** Save checklist after every session.

### 2.2. Complexity Management
- **Anti-Over-Engineering:** Finite complexity budget, value > complexity
- **Rule of Two:** Abstract only after 2+ implementations  
- **Code Clarity:** Functions <25 lines, modules <1500 lines (4000 for SSOT mega classes)
- **Task Decomposition:** Use sub-agents for complex tasks

### 2.3. Quality Standards
- **Type Safety:** Follow `SPEC/type_safety.xml`
- **Environment:** Use `IsolatedEnvironment` for all env access
- **Configuration:** Follow `@configuration_architecture.md`
- **Compliance:** Run `python scripts/check_architecture_compliance.py`

### 2.4. Strategic Trade-offs
Propose trade-offs with BVJ justification, risk assessment, and debt mitigation plan.

### 2.5. Observability 
- **Three Pillars:** Logging, metrics, distributed tracing (OpenTelemetry)
- **SLOs:** Service Level Objectives for critical services
- **Error Budgets:** Balance velocity with stability

### 2.6. Pragmatic Rigor
- Apply standards intelligently, not rigidly
- Favor "boring technology" - proven and simple
- Default to functional/permissive state, add strictness only when required

-----

## 3. DEVELOPMENT PROCESS

### 3.1. AI Agent Roles
- **Principal Engineer:** Strategy, architecture, coordination
- **PM Agent:** Requirements, BVJ validation
- **Design Agent:** UX, workflows, API design
- **Implementation Agent:** Focused coding tasks
- **QA/Security Agent:** Test strategy, regression analysis

### 3.2. Pre-Implementation Analysis
- **Phase 0:** Product definition and workflow design
- **Phase 1:** Scenario analysis (happy paths, edge cases, security)
- **Phase 2:** Interface contract verification
- **Phase 3:** Regression impact analysis and test scope

### 3.3. Implementation Strategy
- **Modular:** One module per agent
- **Isolation:** Provide interfaces only, prevent context bleed
- **Testing Priority:** Real Services > E2E > Integration > Unit
- **No Mocks:** Forbidden in E2E/Integration (Unit only if justified)
- **E2E Auth Mandatory:** All tests use real auth except auth validation tests
- **System-Wide Thinking:** Greater good > narrow test success

### 3.4. Multi-Environment Validation
**Pipeline:** Local/CI → Development → Production-like
- **Real Services Required:** No mocks in E2E, use real databases/LLMs
- **E2E Auth Mandatory:** All tests use real auth (JWT/OAuth) except auth validation tests
- **Fail Hard:** Tests designed to fail completely, no bypassing
- **0-Second Rule:** E2E tests taking 0.00s automatically fail (indicates bypassing/mocking)

### 3.5. Bug Fixing Process
**Joint Bug Fix Report Required:**
1. **WHY Analysis:** Five whys method, why tests missed it
2. **Prove It:** Mermaid diagrams (ideal vs failure state) + reproduction test
3. **System-Wide Fix:** Plan all module impacts, deep implications analysis
4. **Verification:** QA review, regression testing until 100% pass 

### 3.6. Complex Refactoring Process
**For inheritance, multiple classes, or SSOT consolidation:**
1. **MRO Analysis:** Generate comprehensive report before refactoring
2. **Dependency Impact:** Trace consumers, document usage, identify breaking changes
3. **Agent Decomposition:** Spawn agents for 5+ file refactors, one inheritance chain per agent
4. **Validation:** MRO paths preserved, no method shadowing, all consumers updated

**GOLDEN PATH PRIORITY:** Users login → get AI responses. Auth can be permissive temporarily.
## 4. KNOWLEDGE MANAGEMENT

**SPEC/*.xml:** Living source of truth for architecture and learnings.
- **Navigation:** Read @LLM_MASTER_INDEX.md first
- **Evolution:** Propose spec improvements when needed
- **Types:** SPEC/*.xml = permanent knowledge, *.md = ephemeral logs

### 4.1. String Literals Index
**CRITICAL:** Prevents config hallucination and cascade failures.
- **Validate:** `python scripts/query_string_literals.py validate "string"`
- **Search:** `python scripts/query_string_literals.py search "keyword"`
- **Health Check:** `python scripts/query_string_literals.py check-env staging`
- **Update:** `python scripts/scan_string_literals.py`

## 5. ARCHITECTURE & CONVENTIONS

### 5.1. Microservice Independence
**100% Independent Services:**
- Main Backend (`/netra_backend/app`)
- Auth Service (`/auth_service`) 
- Frontend (`/frontend`)

**Shared Libraries:** `/shared` utilities allowed (pure infrastructure, no business logic)

### 5.2. Naming Conventions
- **Agent:** LLM-based sub-agents only
- **Executor/Manager:** Infrastructure patterns
- **Service:** Specialized processors
- **Utility:** Descriptive names without suffixes

### 5.3. Directory Organization
- **Service Tests:** Each service has own `tests/` directory
- **E2E Tests:** `/tests/e2e/`
- **Test Framework:** `/test_framework/`

### 5.4. Import Rules
**ABSOLUTE IMPORTS ONLY** - No relative imports (`.` or `..`) anywhere

## 6. WEBSOCKET AGENT EVENTS (CRITICAL)

**PURPOSE:** Enable substantive chat interactions - deliver AI value to users.

### 6.1. Required Events
1. **agent_started** - User sees agent began processing
2. **agent_thinking** - Real-time reasoning visibility  
3. **tool_executing** - Tool usage transparency
4. **tool_completed** - Tool results display
5. **agent_completed** - User knows response is ready

### 6.2. Integration Requirements
- Run `python tests/mission_critical/test_websocket_agent_events_suite.py`
- Verify ALL events sent with real WebSocket connections
- Never bypass WebSocket notifications
- See @websocket_agent_integration_critical.xml, @GOLDEN_AGENT_INDEX.md

## 7. PROJECT TOOLING

### 7.0. Claude Code Commands
**AUTOMATION HUB:** All development commands available through Claude Code slash commands

**Essential Commands:**
- `/tdd feature module` - Complete TDD workflow with real services (NO MOCKS)
- `/test-real [category]` - Run tests with real databases and LLM
- `/debug-error "error" N` - Five Whys root cause analysis with N agents
- `/deploy-gcp [env]` - Deploy to GCP with compliance checks
- `/ultimate-test-deploy-loop` - MISSION CRITICAL: Run until all 1000+ tests pass

**Command Reference:** See `docs/COMMAND_INDEX.md` for all 36 available commands

### 7.1. Docker
**Central Management:** All operations through UnifiedDockerManager

**Testing Integration:**
```bash
python tests/unified_test_runner.py --real-services
```
**TEST ON GCP STAGING** OR RUN NON DOCKER TESTS BY DEFAULT (Not using docker for tests)

**Alpine Options:**
- Default: Alpine containers with rebuild
- `--no-alpine`: Regular containers  
- `--no-rebuild`: Use cached images
- `--rebuild-all`: Rebuild all services

**Service Refresh:**
```bash
python scripts/refresh_dev_services.py refresh --services backend auth
```

### 7.2. Unified Test Runner
**RULES:** Real services required, mocks forbidden (except unit tests), E2E auth mandatory

**Commands:**
- **Fast:** `python tests/unified_test_runner.py --category integration --no-coverage --fast-fail`
- **Real Services:** `python tests/unified_test_runner.py --real-services`
- **E2E:** `python tests/unified_test_runner.py --category e2e`
- **Release:** `python tests/unified_test_runner.py --categories smoke unit integration api --real-llm --env staging`

### 7.3. Deployment (GCP)
```bash
python scripts/deploy_to_gcp.py --project netra-staging --build-local
```
## 8. SPECIFICATIONS REFERENCE

**Key Specs:**
- @MISSION_CRITICAL_NAMED_VALUES_INDEX.xml - Cascade failure prevention
- @index.xml - All learnings index
- @core.xml - System architecture
- @type_safety.xml - Type safety rules
- @mega_class_exceptions.xml - SSOT classes up to 4000 lines
- @git_commit_atomic_units.xml - Commit standards
- @configuration_architecture.md - Environment management

**Environment Access:** Only through service-specific SSOT configs, no direct os.environ

## 9. SYSTEM STATUS TRACKING

SEE GIT ISSUES, GIT PRs.

**Pre-Work Check:**
- @reports/MASTER_WIP_STATUS.md - System health and compliance
- @reports/DEFINITION_OF_DONE_CHECKLIST.md - Module checklists
- @SSOT_IMPORT_REGISTRY.md - Authoritative import reference (Completed)

## 10. EXECUTION CHECKLIST

### For Every Code Change:
1. **Assess Scope:** Determine if specialized agents needed
2. **Check Critical Values:** @MISSION_CRITICAL_NAMED_VALUES_INDEX.xml
3. **Type Safety:** Run `python scripts/type_drift_migration_utility.py --scan`
4. **Review DoD:** @DEFINITION_OF_DONE_CHECKLIST.md for your module
5. **Check Learnings:** @index.xml and recent commits
6. **Verify Strings:** `python scripts/query_string_literals.py validate/search`
7. **Review Specs:** @type_safety.xml and @conventions.xml
8. **Create Tests:** New real test suite (preferably failing tests)
9. **Run Tests:** Local tests with real services
10. **Complete DoD:** All module checklist items
11. **Update Docs:** Specs reflect reality
12. **Refresh Indexes:** String literals if needed
13. **Update Status:** Regenerate reports and learnings
14. **Save Learnings:** @index.xml

### 10.1. Git Standards
**Follow @git_commit_atomic_units.xml:**
- Stay on develop-long-lived branch as current branch.
- ONLY use safe opreations, never filter branch etc.

**FINAL REMINDER:** 
- **GOLDEN PATH PRIORITY:** Users login → get AI responses
- **ULTRA THINK DEEPLY:** Deep analysis required
- **NO TEST CHEATING:** Real tests that fail properly
- **COMPLETE WORK:** Finish tasks fully with self-reflection