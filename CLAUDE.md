# 🚨 ULTRA THINK DEEPLY ALWAYS. COMPLETE FEATURE FREEZE.

**CRITICAL MISSION:** Get Golden Path working - users login and get AI responses back.

**STABILITY FIRST:** Prove changes maintain system stability and don't introduce breaking changes.

**NON-NEGOTIABLE RULES:**
- SSOT compliance is mandatory
- This document overrides all other instructions
- No "standalone" or "simple" files
- No bypassing established patterns

**GOLDEN PATH PRIORITY:**
1. Users login and get AI message responses
2. All else is secondary
3. Staging GCP deployment only
4. Minimal fixes, zero new features

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

## 2\. Engineering Principles: Modularity, Clarity, and Cohesion

CRITICAL: Develop a globally coherent and modular architecture. 
**Globally correct is better than locally correct.** Systems must be stable by default.

### 2.1. Architectural Tenets

  * **Single Responsibility Principle (SRP):** Each module, function, and agent task must have one clear purpose.
  * **Single Source of Truth (SSOT):** **CRITICAL:** A concept must have ONE canonical implementation per service. Avoid multiple variations of the same logic; extend existing functions with parameters instead. (Cross-service duplication may be acceptable for independence; see `SPEC/acceptable_duplicates.xml`).
    - **⚠️ CONFIG SSOT WARNING:** SSOT for config is DIFFERENT! See @CONFIG_REGRESSION_PREVENTION_PLAN.md
    - **NEVER blindly consolidate "duplicate" configs** - They may serve different environments/services
    - **Check ConfigDependencyMap BEFORE deleting** - One deletion can break multiple services
    - **Environment isolation is CRITICAL** - Test configs must NOT leak to staging/production
    - **🚨 AUTH VALIDATION REGRESSION PREVENTION:** See @FIVE_WHYS_BACKEND_500_ERROR_20250907.md - Auth validation MUST NOT be overly strict for hex strings or staging environments. **HEX STRINGS ARE VALID SECRETS** (e.g. SERVICE_SECRET from `openssl rand -hex 32`). OAuth redirect mismatches should be warnings in non-prod, not failures.
  * **"Search First, Create Second":** Always check for existing implementations before writing new code.
  * **ATOMIC SCOPE:** Edits must be complete, functional updates. Delegate tasks to sub-agents with scopes you are certain they can handle. Split and divide work appropriately.
  * **Complete Work:** An update is complete only when all relevant parts of the system are updated, integrated, tested, validated, and documented, and all legacy code has been removed.
  * **RANDOM FEATURES ARE FORBIDDEN:** Edits must focus on the most minimal change required to achieve the goal.
  * **BASICS FIRST:** Prioritize basic and expected user flows over exotic edge cases.
  * **LEGACY IS FORBIDDEN:** Always remove ALL related legacy code as part of any refactoring effort.
  * **Evolutionary Architecture:** Design systems to meet *current* needs while allowing for future adaptation (Just-in-Time Architecture).
  * **Operational Simplicity:** Favor architectures with fewer moving parts to reduce maintenance costs.
  * **High Cohesion, Loose Coupling:** Group related logic together while maximizing module independence.
  * **Interface-First Design:** Define clear interfaces and contracts before implementation.
  * **Composability:** Design components for reuse.
  * **Stability by Default:** Changes must be atomic. Explicitly flag any breaking changes.

Use Test Runner to discover tests e.g. `python tests/unified_test_runner.py` (absolute path: `/Users/anthony/Documents/GitHub/netra-apex/tests/unified_test_runner.py`). Read testing xmls.

**A compliance checklist against these tenets MUST be saved after every work session.**

### 2.2. Complexity Management

  * **Architectural Simplicity (Anti-Over-Engineering):** Assume a finite complexity budget. Every new service, queue, or abstraction must provide more value than the complexity it adds. Strive for the fewest possible steps between a request's entry point and the business logic.
    - **⚠️ OVER-ENGINEERING AUDIT:** See @OVER_ENGINEERING_AUDIT_20250908.md - System currently has 18,264 violations requiring consolidation
    - **Current Issues:** 154 manager classes, 78 factory classes, 110 duplicate types - many represent unnecessary abstraction layers
    - **Success Patterns:** Unified managers (Configuration, State, Lifecycle) represent correct SSOT consolidation approach
  * **"Rule of Two":** Do not abstract or generalize a pattern until you have implemented it at least twice.
  * **Code Clarity:** Aim for concise functions (\<25 lines) and focused modules (\<750 lines). Exceeding these is a signal to re-evaluate for SRP adherence.
  * **Mega Class Exceptions:** Central SSOT classes defined in @mega_class_exceptions.xml may extend to 2000 lines with explicit justification. These must be true integration points that cannot be split without violating SSOT principles.
    - **Naming Clarity Initiative:** See @MANAGER_RENAMING_PLAN_20250908.md for business-focused naming of unified SSOT classes
  * **Task Decomposition:** If a task is too large or complex, decompose and delegate it to specialized sub-agents with fresh contexts. ALWAYS carefully manage your own context use and agents context use.

### 2.3. Code Quality Standards

  * **Type Safety:** Adhere strictly to `SPEC/type_safety.xml`.
  * **Environment:** All environment access MUST go through `IsolatedEnvironment` as defined in @unified_environment_management.xml.
  * **Configuration Architecture:** Follow the comprehensive configuration system documented in @configuration_architecture.md.
  * **Compliance Check:** Run `python scripts/check_architecture_compliance.py` to check status.
    - **Over-Engineering Monitoring:** Track progress on reducing 18,264 violations identified in @OVER_ENGINEERING_AUDIT_20250908.md
    - **Naming Convention Validation:** Follow @naming_conventions_business_focused.xml for all new classes

### 2.4. Strategic Trade-offs

You are authorized to propose strategic trade-offs (e.g., accepting temporary complexity to ship a critical feature). Justify these in the BVJ, including the risks and a plan to address the resulting technical debt.

### 2.5. Observability and Data-Driven Operations

  * **The Three Pillars:** Implement comprehensive logging, metrics, and distributed tracing (OpenTelemetry) across all services.
  * **SLOs:** Define Service Level Objectives (SLOs) for all critical services.
  * **Error Budgets:** Use error budgets to balance velocity with stability. If an SLO is breached, development focus MUST shift to restoring stability.

### 2.6. Pragmatic Rigor and Resilience

  * **Pragmatic Rigor:** Apply standards intelligently to ensure correctness, not rigidly for theoretical purity. Avoid architectural overkill.
  * **"Boring Technology":** Favor proven, operationally simple technologies.
  * **Resilience by Default:** Default to a functional, permissive state. Add strictness only where explicitly required (e.g., security). Adhere to Postel's Law: "Be conservative in what you send, liberal in what you accept."

-----

## 3\. The Development Process: Structured Analysis and Agent Utilization

### 3.1. The AI-Augmented "Complete Team"

Leverage specialized AI agents for distinct roles to maximize parallelism and analytical depth.

  * **Principal Engineer:** Strategy, architecture, final synthesis, and coordination.
  * **Product Manager (PM) Agent:** Defines the "Why" and "What." Refines requirements and drafts the BVJ.
  * **Design Agent:** Defines the user experience, workflows, and API ergonomics.
  * **Implementation Agent:** Executes focused coding tasks against a defined interface.
  * **QA/Security Agent:** Defines test strategy, analyzes regressions, and performs security audits.

### 3.2. Structured Analysis Phases (Pre-Implementation)

Before coding, conduct a rigorous analysis.

  * **Phase 0: Product Definition (PM/Design Agent):** If requirements are ambiguous, spawn agents to define user scenarios, validate the BVJ, and design workflows.
  * **Phase 1: Scenario Analysis (Principal/QA Agent):** Analyze happy paths, edge cases, security implications, and system impacts.
  * **Phase 2: Interface Contract Verification (Principal):** Deconstruct and verify the proposed architecture, data structures, and API contracts.
  * **Phase 3: Regression Impact Analysis (QA Agent):** Identify and analyze potential side effects on the unified system and define the testing scope.

### 3.3. Implementation Strategy

  * **Modular Implementation:** Delegate tasks to Implementation Agents one module at a time.
  * **Isolation (The "Firewall" Technique):** **CRITICAL:** When delegating, provide agents ONLY with the necessary interfaces of dependencies, not their full implementation context. This enforces contracts and prevents context bleed.
  * **Testing Focus:** Focuse on as real tests as possible by default. Most tests must assume inter-service nature by default. **Real Everything (LLM, Services) E2E \> E2E \> Integration \> Unit.**
  CRITICAL: Mocks in E2E or Integration = Abomination  (Allowed in Unit tests if needed and not cheating)
  * **🚨 CRITICAL E2E AUTH REQUIREMENT:** ALL e2e tests MUST use authentication except for the small handful that directly test if auth is working itself. This ensures real-world multi-user scenarios are properly tested. See @test_auth_complete_flow.py for auth flow examples.
  * **Test Architecture:** See @TEST_ARCHITECTURE_VISUAL_OVERVIEW.md for complete test infrastructure guide
  * **Integration and Reporting:** You are responsible for integrating all artifacts and reporting on overall success.

ULTRA THINK DEEPLY ALL THE TIME.

CRITICAL: ALWAYS SOLVE FOR THE GREATER GOOD OF THE OVERALL SYSTEM.
NEVER "bypass" a greater good intention for narrow success like passing a single test.

### 3.4. Multi-Environment Validation

Code is not "done" until it is validated in environments that mirror production. Local E2E tests MUST use real services (local databases, shared LLMs). Mocks are forbidden in E2E testing.

**Mandatory Validation Pipeline:**

1.  **Local/CI:** Fast feedback with unit and integration tests.
2.  **Development:** Integration/E2E tests against deployed services.
ALWAYS use real services for testing. If they appear to not be available start or restarting them. If that too fails then hard fail the entire test suite.

**🚨 E2E AUTH MANDATE:** Every E2E test MUST authenticate properly with the system (using real JWT tokens, OAuth flows, etc.) EXCEPT for the specific tests that validate the auth system itself. This requirement ensures:
- Real multi-user isolation is tested
- WebSocket connections use proper auth context
- Agent executions happen within authenticated user sessions
- See @test_auth_complete_flow.py and @e2e_auth_helper.py

CHEATING ON TESTS = ABOMINATION
ALL TESTS MUST BE DESIGNED TO FAIL HARD IN EVERY WAY. ALL ATTEMPTS TO BYPASS THIS WITHIN THE TEST ITSELF ARE BAD.

**🚨 CRITICAL: E2E TESTS WITH 0-SECOND EXECUTION = AUTOMATIC HARD FAILURE**
Any e2e test that returns in 0.00s is automatically failed by the test runner. This indicates:
- Tests are not actually executing (being skipped/mocked)
- Missing async/await handling
- Not connecting to real services
- Authentication is being bypassed
See @STAGING_100_TESTS_REPORT.md for context.
The unified test runner enforces this with `_validate_e2e_test_timing()`.

KEEP CORE SYSTEM AS IS
NO NEW FEATURES, ONLY CRITICAL FIXES and REFACTORS. (feature freeze includes "security" or "enterprise" features)

### 3.5. MANDATORY BUG FIXING PROCESS:

EACH AGENT MUST SAVE THEIR WORK TO A JOINT BUG FIX REPORT for each bug.
The work is only complete when ALL DoD items are complete and the report is updated. SLOW DOWN. Think step by step.

At every opportunity spawn new subagent with dedicated focus mission and context window.
1.  **WHY:** Analyze why the code diverges from requirements. Why did existing tests miss this? MUST USE FIVE WHYS METHOD? Why? Why? Why!!!?
2.  **Prove it:** Write out TWO Mermaid diagrams. One of the ideal working state and one of the current failure state. Save your work the .md file. Write a test that reproduces the bug.
3.  **Plan system wide claude.md compaliant fix**  Think about ALL associated and related modules that must also be updated. Think about cross system impacts of bug. SLOWLY think DEEPLY about the implications. What is the spirit of the problem beyond the literal one-off problem? Plan the fix. Save to the bugfix .md.
4.  **Verification and proof implementation worked** QA review and regression testing. Use fail fast, starting with proving that newly created test suite now passes, then rest of tests related to this issue. repeat until all tests pass or 100 times.

YOU MUST WORK HARD AND COMPLETE ALL OF YOUR WORK. YOU MUST KEEP GOING UNTIL THE WORK IS COMPLETE AND BE PATIENT.
DO THE MINIMAL ACTION TO MAKE GOLDEN PATH WORK! 

### 3.6. MANDATORY COMPLEX REFACTORING PROCESS:

**CRITICAL: For any refactoring involving inheritance, multiple classes, or SSOT consolidation:**
CHEATING ON TESTS = ABOMINATION

**See Also:** 
- @GOLDEN_AGENT_INDEX.md for comprehensive agent implementation patterns and migration guidance.
- @AGENT_ARCHITECTURE_DISAMBIGUATION_GUIDE.md for clarification on agent components and relationships.

1.  **MRO (Method Resolution Order) Analysis:** Generate a comprehensive MRO report BEFORE refactoring

2.  **Dependency Impact Analysis:**
    - Trace all consumers of classes being refactored
    - Document which methods/attributes each consumer uses
    - Identify breaking changes and required adaptations
    - Cross-reference with @ssot_consolidation_20250825.xml

3.  **Agent-Based Decomposition:** For complex refactors spanning 5+ files:
    - Spawn specialized refactoring agents with focused scope
    - Each agent handles ONE inheritance chain or module
    - Provide agents with MRO report and interface contracts only
    - See examples in @unified_agent_testing_implementation.xml

4.  **Validation Checklist:**
    - [ ] All MRO paths documented and preserved or intentionally modified
    - [ ] No unintended method shadowing introduced
    - [ ] All consumers updated to new interfaces
    - [ ] Integration tests pass for all inheritance scenarios
    - [ ] Performance regression tests pass (inheritance lookup overhead)

CHEATING ON TESTS = ABOMINATION
YOU MUST ULTRA THINK DEEPLY


The #1 priority right now is that the users can login and complete getting a message back.
The secondary items are database flows or other features.
Even Auth can be more permissive for now (log issue in git for items temporarily bypassed)
IT MUST allow allow the golden path through!!! (and keep logging errors for future work)

**Cross-Reference Learnings:**
## 4\. Knowledge Management: The Living Source of Truth

The `SPEC/*.xml` files are the **living source of truth** for system architecture and learnings.

  * **Navigation:** Read @LLM_MASTER_INDEX.md before searching for files or functionality.
  * **Iterative Discovery:** Specs must evolve. If analysis reveals a better solution, propose a spec improvement.
  * **Learnings vs. Reports:** Learnings in `SPEC/*.xml` are permanent knowledge. Reports (`*.md`) are ephemeral work logs.

### 4.1. String Literals Index: Preventing Hallucination

This index is the SSOT for all platform-specific constants, paths, and identifiers to prevent LLM errors.

  * **Index File:** `SPEC/generated/string_literals.json`
  * **📚 Complete Documentation:** @string_literals_index.md

**🚨 CRITICAL PROTECTION: mission-critical environment variables + domain configurations cause CASCADE FAILURES if modified incorrectly!**

**Usage Requirements:**

1.  **ALWAYS Validate** literals before use: `python scripts/query_string_literals.py validate "your_string"`
2.  **NEVER Guess** config keys or paths; query the index first with search: `python scripts/query_string_literals.py search "keyword"`
3.  **CHECK Environment Health:** `python scripts/query_string_literals.py check-env staging` (or production)
5.  **UPDATE Index** after adding new constants: `python scripts/scan_string_literals.py`

**Cross-Reference with Step 6 in Execution Checklist below ⬇️**

## 5\. Architecture and Conventions

### 5.1. Microservice Independence

All microservices MUST be 100% independent. See @independent_services.xml.

  * Main Backend (`/netra_backend/app`)
  * Auth Service (`/auth_service`)
  * Frontend (`/frontend`)

**CRITICAL CLARIFICATION - Shared Libraries Pattern:**
Services MAY import from `/shared` for infrastructure libraries (like `shared.isolated_environment`).
These are NOT service boundary violations because they're pure utilities with no business logic - 
think of them as internal pip packages. See @shared_library_pattern.md 
for the simple "pip package test" to determine what belongs in `/shared`.

### 5.2. Naming Conventions

  * **"Agent":** Only for LLM-based sub-agents. **"Executor/Manager":** For infrastructure patterns **"Service":** For specialized processors. **Utility:** Descriptive names without suffixes.

### 5.3. Directory Organization

**Files MUST be placed in their designated locations.**

  * **Service-Specific Tests:** Each service has its own `tests/` directory (e.g., `/netra_backend/tests/`). **NEVER mix tests between services.**
  * **E2E Tests:** End-to-end tests go in `/tests/e2e/`.
  * **Test Framework:** Shared utilities go in `/test_framework/`.
  * **See @folder_structure_rules.md for full guidelines.**

### 5.4. Import Rules

**ABSOLUTE IMPORTS ONLY.**
  * **ALL Python files  use absolute imports** starting from the package root. **NEVER use relative imports (`.` or `..`)** in any Python file, including tests. See @import_management_architecture.xml for details.

-----

CHEATING ON TESTS = ABOMINATION
ULTRA THINK DEEPLY
SOLVE FOR THE GREATER GOOD OF THE OVERALL SYSTEM
IGNORE DOCKER ISSUES FOR NOW (just log them). ONLY GCP STAGING MATTERS FOR HOSTING.

## 6\. MISSION CRITICAL: WebSocket Agent Events (Infrastructure for Chat Value)

**CRITICAL: WebSocket events enable substantive chat interactions - they serve the business goal of delivering AI value to users.**

### 6.1. Required WebSocket Events for Substantive Chat Value

The following events MUST be sent during agent execution to enable meaningful AI interactions:

1. **agent_started** - User must see agent began processing their problem
2. **agent_thinking** - Real-time reasoning visibility (shows AI is working on valuable solutions)
3. **tool_executing** - Tool usage transparency (demonstrates problem-solving approach)
4. **tool_completed** - Tool results display (delivers actionable insights)
5. **agent_completed** - User must know when valuable response is ready

### 6.2. WebSocket Integration Requirements

**CRITICAL: When modifying ANY of these components, you MUST:**
- Run `python tests/mission_critical/test_websocket_agent_events_suite.py`
- Verify ALL event types are sent
- Test with real WebSocket connections
- Never remove or bypass WebSocket notifications

**Key Integration Points:**
- `AgentRegistry.set_websocket_manager()` MUST enhance tool dispatcher
- `ExecutionEngine` MUST have AgentWebSocketBridge initialized
- `EnhancedToolExecutionEngine` MUST wrap tool execution
- See @websocket_agent_integration_critical.xml

**For Complete Agent Implementation Patterns:**
- See @GOLDEN_AGENT_INDEX.md - The definitive guide to agent implementation
- See @AGENT_ARCHITECTURE_DISAMBIGUATION_GUIDE.md - Comprehensive clarification of agent architecture
- See @agent_execution_order_fix_20250904.xml - CRITICAL: Correct agent execution order (Data BEFORE Optimization)

-----
CHEATING ON TESTS = ABOMINATION

## 7\. Project Tooling

### 7.1. Docker

**CRITICAL: All Docker operations go through the central UnifiedDockerManager.** **See @docker_orchestration.md for complete architecture and usage.**

#### Automatic Docker Management is integrated with testing
```bash
python tests/unified_test_runner.py --real-services
```

#### Alpine Container Support
**Usage Examples:**

```bash
# Default behavior - Alpine containers with rebuild
python tests/unified_test_runner.py --real-services
# Automatically uses: use_alpine=True, rebuild_images=True

# Disable Alpine (use regular containers)
python tests/unified_test_runner.py --real-services --no-alpine

# Disable image rebuilding (use cached images)
python tests/unified_test_runner.py --real-services --no-rebuild

# Rebuild all services (not just backend)
python tests/unified_test_runner.py --real-services --rebuild-all
```

**Alpine Compose Files:**
- `docker-compose.alpine-test.yml` - Test environment with named volumes (stable storage)
- `docker-compose.alpine.yml` - Development environment
- Alpine Dockerfiles: `docker/backend.alpine.Dockerfile`, `docker/auth.alpine.Dockerfile`, `docker/frontend.alpine.Dockerfile`

**⚠️ tmpfs Storage Removed**
Docker tmpfs storage has been completely removed from the codebase as it causes system crashes due to RAM exhaustion. Never re-introduce tmpfs mounts - they will crash the system.


#### Development Service Refresh
```bash
# Refresh backend and auth with latest changes
python scripts/refresh_dev_services.py refresh --services backend auth
```

### 7.3. Unified Test Runner

IMPORTANT: Use real services, real llm, docker compose etc. whenever possible for testing.
MOCKS are FORBIDDEN in dev, staging or production.  (Except limited cases for unit tests if you can prove it's needed)
FAKE TESTS ARE BAD

**🚨 E2E AUTH ENFORCEMENT:** ALL e2e tests MUST authenticate with the system using real auth flows (JWT, OAuth, etc.). The ONLY exceptions are tests specifically validating the auth system itself. This is NON-NEGOTIABLE for ensuring proper multi-user isolation and real-world scenarios. Use @e2e_auth_helper.py for SSOT auth patterns.

**See @TEST_CREATION_GUIDE.md for the AUTHORITATIVE guide on creating tests with SSOT patterns.**
**See @TEST_ARCHITECTURE_VISUAL_OVERVIEW.md for complete visual guide to test infrastructure, layers, and execution flows.**

**The test runner automatically starts Docker when needed:**

  * **Default (Fast Feedback):** `python tests/unified_test_runner.py --category integration --no-coverage --fast-fail`
  * **With Real Services:** `python tests/unified_test_runner.py --real-services` (Docker starts automatically)
  * **E2E Tests:** `python tests/unified_test_runner.py --category e2e` (Docker starts automatically)
  * **Before Release:** `python tests/unified_test_runner.py --categories smoke unit integration api --real-llm --env staging`
  * **Mission Critical Tests:** `python tests/mission_critical/test_websocket_agent_events_suite.py`

#### Docker Environment Configuration
- **Test Environment (Default)**: PostgreSQL (5434), Redis (6381), Backend (8000), Auth (8081)
- **Development Environment**: PostgreSQL (5432), Redis (6379), Backend (8000), Auth (8081)
- **Production Environment**: Standard production ports

### 7.4. Deployment (GCP)

**Use ONLY the official deployment script.**
  * **Default:** `python scripts/deploy_to_gcp.py --project netra-staging --build-local`
-----

DO THE RIGHT THING - NOT JUST THE FASTEST THING.

## 8\. Detailed Specifications Reference

This is a non-exhaustive list of mission-critical specs.
| Spec | Purpose |
| :--- | :--- |
| @MISSION_CRITICAL_NAMED_VALUES_INDEX.xml | ** CRITICAL:** Master index of ALL values that cause cascade failures. CHECK FIRST! |
| @index.xml | Index of all learnings. **Check first.** |
| @core.xml | Core system architecture. |
| @type_safety.xml | Type safety and duplication rules. |
| @conventions.xml | Standards and guidelines. |
| @mega_class_exceptions.xml | **CRITICAL:** Approved exceptions for central SSOT classes up to 2000 lines. |
| @git_commit_atomic_units.xml | **CRITICAL:** Git commit standards. |
| @import_management_architecture.xml | **CRITICAL:** Absolute import rules. |
| @configuration_architecture.md | **CRITICAL:** Configuration and environment management architecture with complete diagrams and flows. |

Direct OS.env access is FORBIDDEN except in each services canonical env config SSOT. Applies to ALL tests too. EACH SERVICE MUST MAINTAIN INDEPENDENCE. Import ONLY from the env of the service.

-----
DO THE MINIMAL ACTION TO MAKE GOLDEN PATH WORK! 
YOU DO YOUR BEST WORK.

## 8\. System Status and Compliance Tracking

**CRITICAL: Check the work in progress and current system state BEFORE starting work.**
  * @reports/MASTER_WIP_STATUS.md provides real-time system health, compliance scores, and critical violations.
  * @reports/DEFINITION_OF_DONE_CHECKLIST.md Checklist for all module changes. Review ALL files listed for your module.**
  * Review these reports first and regenerate status after your work is complete.

If you ever have a chance to audit or verify or spawn new subagent, even if 10x as much work to improve 1% chance of overall success do it. Success = Complete work at all costs.


YOU ARE VERY SMART AND PRACTICAL.

## 9\. Execution Checklist

### For Every Code Change:

1.  **Assess Scope:** Determine if specialized agents (PM, Design, QA, etc.) are required.
2.  **🚨 CHECK CRITICAL VALUES:** Open @MISSION_CRITICAL_NAMED_VALUES_INDEX.xml - validate ALL named values!
    - **ATTENTION:** OAuth credentials, JWT keys, database URLs - see @OAUTH_REGRESSION_ANALYSIS_20250905.md
3.  **🔍 TYPE SAFETY VALIDATION:** **CRITICAL** - Check for type drift issues before any changes:
    - **Run Type Audit:** `python scripts/type_drift_migration_utility.py --scan` for affected files
    - **Use SSOT Strongly Typed IDs:** Import from `shared.types` - `UserID`, `ThreadID`, `RunID`, `RequestID`, etc.
    - **See:** @TYPE_DRIFT_AUDIT_REPORT.md for complete remediation guide
4.  **Review DoD Checklist:** Open @DEFINITION_OF_DONE_CHECKLIST.md and identify your module's section.
5.  **Check Learnings:** Search recent @index.xml and recent commit changes.
6.  **Verify Strings:** **MANDATORY STRING LITERAL VALIDATION** - See @STRING_LITERALS_USAGE_GUIDE.md:
    - **NEVER guess string literals** - Always validate: `python scripts/query_string_literals.py validate "your_string"`
    - **Search for existing:** `python scripts/query_string_literals.py search "keyword" --category critical_config`
    - **Check environment health:** `python scripts/query_string_literals.py check-env staging`
    - **🚨 CRITICAL CONFIGS:** 11 env vars + 12 domains cause CASCADE FAILURES - use `show-critical`
7.  **Review Core Specs:** Re-read @type_safety.xml and @conventions.xml.
8.  **Create New Test Suite:** Create a new real test suite of difficult tests idealy failing tests.
9.  **Run Local Tests:** Run relevant tests for the scope of work done. Real services > mock.
10. **Complete DoD Checklist:** Go through EVERY item in your module's checklist section.
11. **Update Documentation:** Ensure specs reflect the implemented reality.
12. **Refresh Indexes:** Update the string literal index if new constants were added.
13. **Update Status:** Regenerate and refresh reports .mds and learnings.
14. **Save new Learnings:** @index.xml.

### 9.1 Git Commit Standards.
**All commits follow @git_commit_atomic_units.xml.**
**Windows Unicode/emoji issues: See @windows_unicode_handling.xml.**
A user asking for "git commit" means: For EACH group of work that's related do a commit. e.g. 1-10 commits as per need.
  * **GROUP CONCEPTS - LIMIT COUNT OF FILES:** Commits must be small, focused, and conceptually similar units.
  * **CONCEPT-BASED:** NEVER bulk commit massive changes without express orders.
  * **REVIEWABLE:** Each commit must be reviewable in under one minute.
  * **REFACTORING COMMITS:** Complex refactors MUST include MRO report reference in commit message

KEEP CORE SYSTEM AS IS
NO NEW FEATURES, ONLY CRITICAL FIXES and REFACTORS
DO THE MINIMAL ACTION TO MAKE GOLDEN PATH WORK!
GOlDEN PATH = MUST WORK

The #1 priority right now is the GOLDEN PATH that the users can login and complete getting a message back.
The secondary items are database flows or other features.
Even Auth can be more permissive for now (log issue in git for items temporarily bypassed)
IT MUST allow allow the golden path through!!! (and keep logging errors for future work)

**Final Reminder:** ULTRA THINK DEEPLY. CHEATING ON TESTS = ABOMINATION. Your mission is to generate monetization-focused value. Prioritize a coherent, unified system that delivers end-to-end value for our customers. YOU MUST ALWAYS SELF-REFLECT ON YOUR WORK AND SAVE IT IN UNIFIED REFLECTION JOURNAL. **Think deeply. YOUR WORK MATTERS. THINK STEP BY STEP AS DEEPLY AS POSSIBLE.**