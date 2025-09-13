# Netra Apex Claude Code Command Index

> 🎯 **Quick Start**: Use `/command-name` syntax in Claude Code conversations to execute these commands. See [Claude Commands Documentation](.claude/commands/README.md) for detailed usage.

## 📋 Overview

This index catalogues all 39 custom Claude Code slash commands available for the Netra Apex project. These commands automate repetitive tasks and enforce project standards, particularly the **NO MOCKS** policy and real service testing requirements.

**Location**: [`.claude/commands/`](../.claude/commands/) directory

## 🎯 Command Categories

### 🚀 Quick Development (< 5 minutes)
- [`/compliance`](#compliance) - Check CLAUDE.md architecture compliance
- [`/docker-rebuild`](#docker-rebuild) - Rebuild Docker containers from scratch  
- [`/test-real`](#test-real) - Run tests with real services
- [`/websocket-test`](#websocket-test) - Test mission-critical WebSocket events
- [`/canary`](#canary) - Standardized system health diagnostics
- [`/run-demo`](#run-demo) - Setup and launch staging demo instantly

### 🔧 Standard Development (5-30 minutes)
- [`/tdd`](#tdd) - Execute complete TDD workflow with real services
- [`/agent-test`](#agent-test) - Test specific agent implementation
- [`/pre-commit`](#pre-commit) - Complete CLAUDE.md compliance check
- [`/deploy-gcp`](#deploy-gcp) - Deploy to GCP following project standards
- [`/debug-error`](#debug-error) - Five Whys-driven intelligent debugging

### 🔍 Analysis & Architecture (1-4 hours)
- [`/analyze-repository`](#analyze-repository) - Parallel repository analysis with N agents
- [`/audit-docker-logs`](#audit-docker-logs) - Audit Docker logs for errors
- [`/audit-gcp-logs`](#audit-gcp-logs) - Audit GCP Cloud Run logs
- [`/run-integration-tests`](#run-integration-tests) - Run non-Docker integration tests
- [`/run-unit-tests`](#run-unit-tests) - Run all unit tests with multi-agent remediation
- [`/run-unit-frontend-tests`](#run-unit-frontend-tests) - Run frontend tests with Five Whys
- [`/test-create`](#test-create) - Create SSOT-compliant tests
- [`/priority-test-create`](#priority-test-create) - Create tests based on priority analysis
- [`/scope-work`](#scope-work) - Create parallel prompts for P0 SSOT refactoring
- [`/ssot-regression-check`](#ssot-regression-check) - Audit commits for SSOT violations

### 🌙 Mission Critical (8-20 hours)
- [`/ultimate-test-deploy-loop`](#ultimate-test-deploy-loop) - **CRITICAL** - Run until ALL 1000+ tests pass
- [`/audit-staging-logs-gcp-loop`](#audit-staging-logs-gcp-loop) - **CRITICAL** - Continuous GCP monitoring
- [`/test-create-integration`](#test-create-integration) - Create 100+ integration tests 
- [`/test-create-unit-coverage`](#test-create-unit-coverage) - Create unit tests for 100% coverage

### 🔧 Repository Maintenance & Long-Running Operations (8-30+ hours)
- [`/ssotgardener`](#ssotgardener) - **CRITICAL** - SSOT violation discovery and remediation
- [`/gitcommitgardener`](#gitcommitgardener) - **CRITICAL** - Safe repository management and cleanup
- [`/gitissueprogressor`](#gitissueprogressor) - **CRITICAL** - Full day GitHub issue workflow
- [`/audit-gcp-error-loop`](#audit-gcp-error-loop) - **CRITICAL** - GCP error monitoring with auto-debug

### 🛠️ Specialized & GitHub Integration Commands
- [`/action`](#action) - Process multiple items with Five Whys analysis
- [`/prmergergit`](#prmergergit) - Safe pull request merging with validation
- [`/test-update-e2e-fix-fakes`](#test-update-e2e-fix-fakes) - Fix fake tests to use real services
- [`/refresh-upate-tests`](#refresh-upate-tests) - Refresh and update test suites (note: typo in filename)
- [`/test-fix-REMOVED_SYNTAX_ERROR`](#test-fix-removed-syntax-error) - Fix tests with REMOVED_SYNTAX_ERROR markings
- [`/e2e-fix-directly`](#e2e-fix-directly) - Real e2e test fix deploy loop
- [`/failingtestsgardener`](#failingtestsgardener) - Collect test issues and create GitHub issues
- [`/gcploggardener`](#gcploggardener) - GCP log issue collector and GitHub issue creator
- [`/testgardener`](#testgardener) - Test management and organization
- [`/run-demo`](#run-demo) - Setup and launch staging demo with flexible frontend

---

## 📖 Detailed Command Reference

### Core Development Commands

#### `/compliance`
**Purpose**: Check CLAUDE.md architecture compliance requirements  
**Usage**: `/compliance`  
**Key Features**:
- Runs architecture compliance scripts  
- Checks import rules (no relative imports)
- Validates string literals index
- Verifies folder structure compliance
- Scans for NO MOCKS policy violations

**Example Output**:
```
✅ SSOT compliance check passed
✅ No relative imports found  
⚠️ 3 files need string literal updates
✅ Mission critical tests available
```

---

#### `/docker-rebuild`
**Purpose**: Rebuild Docker containers from scratch  
**Usage**: `/docker-rebuild [service-name]`  
**Key Features**:
- Stops all containers cleanly
- Rebuilds without cache for fresh start
- Restarts and verifies health status
- Can target specific service or rebuild all

**Examples**:
```bash
/docker-rebuild              # Rebuild all services
/docker-rebuild backend      # Rebuild backend only  
/docker-rebuild auth redis   # Rebuild specific services
```

---

#### `/test-real`
**Purpose**: Run tests with real services and LLM connections  
**Usage**: `/test-real [category]`  
**Key Features**:
- Ensures Docker services are running
- Uses real databases (PostgreSQL, Redis, ClickHouse)  
- Uses real Gemini API calls
- Test categories: unit, integration, e2e, smoke, api

**Examples**:
```bash
/test-real                   # Run integration tests (default)
/test-real e2e              # Run end-to-end tests
/test-real smoke            # Run smoke tests
```

---

#### `/tdd`
**Purpose**: Execute complete Test-Driven Development workflow  
**Usage**: `/tdd <feature-name> <module-name>`  
**Key Features**:
- **CRITICAL**: Enforces REAL services only (NO MOCKS)
- Spawns multiple agents with reviewers
- 6-step TDD process: Write tests → Verify failure → Commit → Implement → Refactor → Merge
- Uses real PostgreSQL, Redis, ClickHouse, Gemini API

**Examples**:
```bash
/tdd user-authentication auth_service
/tdd websocket-events core
/tdd data-analysis agents
```

**Process Flow**:
1. 🔴 Write comprehensive tests against real services
2. ❌ Verify tests fail correctly 
3. 📝 Commit failing tests
4. ✅ Implement feature to pass tests
5. 🔧 Refactor while maintaining real service integration
6. ✨ Final validation and commit

---

#### `/agent-test`
**Purpose**: Test specific agent implementation with real services  
**Usage**: `/agent-test <agent-name>`  
**Key Features**:
- Runs agent-specific tests with real LLM
- Verifies WebSocket events (agent_started, agent_thinking, tool_executing, tool_completed, agent_completed)
- Uses real connections and authentication

**Examples**:
```bash
/agent-test data_analyst     # Test data analyst agent
/agent-test optimization     # Test optimization agent  
/agent-test code_reviewer    # Test code reviewer agent
```

---

### Quality & Compliance Commands

#### `/pre-commit`
**Purpose**: Complete CLAUDE.md compliance check before committing  
**Usage**: `/pre-commit [scope]`  
**Key Features**:
- Validates all CLAUDE.md requirements
- Checks mission-critical named values
- Runs tests for changed modules
- Generates compliance report
- Groups checks by commit scope

**Examples**:
```bash
/pre-commit                  # Full compliance check
/pre-commit backend          # Backend-focused check
/pre-commit agents           # Agent-specific check
```

---

#### `/websocket-test`
**Purpose**: Test mission-critical WebSocket events  
**Usage**: `/websocket-test`  
**Key Features**:
- Tests agent event propagation with real connections
- Verifies all required events: `agent_started`, `agent_thinking`, `tool_executing`, `tool_completed`, `agent_completed`
- Checks integration points and event delivery
- Uses real WebSocket connections (no mocks)

---

### Advanced Debugging Commands

#### `/debug-error`
**Purpose**: **FOUNDATION** - Five Whys-driven intelligent debugging  
**Usage**: `/debug-error <error-description> [num-agents]`  
**Key Features**:
- **CORE PRINCIPLE**: Uses Five Whys methodology for systematic root cause analysis
- Requires (n-1)/n agents consensus before fixes
- Cascade failure prevention with validation
- Automatic revert if issues detected
- Conservative approach with human fallback

**Five Whys Levels**:
1. 🔴 **WHY #1**: Surface symptom analysis
2. 🟠 **WHY #2**: Immediate cause identification  
3. 🟡 **WHY #3**: System failure discovery
4. 🟢 **WHY #4**: Process gap analysis
5. 🔵 **WHY #5**: Root cause determination

**Examples**:
```bash
/debug-error "IndentationError in service.py" 5
/debug-error "Connection refused to PostgreSQL" 7
/debug-error "WebSocket events not firing" 3
```

---

#### `/analyze-repository`
**Purpose**: Parallel repository analysis with N agents  
**Usage**: `/analyze-repository <action> [num-agents]`  
**Key Features**:
- Divides repository into non-overlapping sections
- Sequential agent spawning to prevent crashes
- Synthesizes findings from all agents
- Supports: audit, document, refactor, security-scan

**Agent Assignments** (5 agents default):
- **Agent 1**: Backend Core (`/core/`, `/models/`, `/database/`)
- **Agent 2**: Backend Services (`/services/`, `/routes/`, `/websocket/`)  
- **Agent 3**: AI & Agents (`/agents/`, `/llm/`, `/tools/`)
- **Agent 4**: Frontend & Auth (`/frontend/`, `/auth_service/`)
- **Agent 5**: Infrastructure (`/tests/`, `/scripts/`, `/docker/`, `/SPEC/`)

**Examples**:
```bash
/analyze-repository audit            # 5 agents audit codebase
/analyze-repository security-scan 8  # 8 agents security scan
/analyze-repository document 3       # 3 agents generate docs
```

---

### Testing Commands

#### `/test-create`
**Purpose**: Create tests following TEST_CREATION_GUIDE.md standards  
**Usage**: `/test-create [tests-to-be-created]`  
**Key Features**:
- SSOT compliant test creation
- Real services only (NO MOCKS)
- Follows project test architecture
- Automatic documentation updates

**Examples**:
```bash
/test-create "auth flow tests"
/test-create "WebSocket agent events"
/test-create "database integration tests"
```

---

#### `/run-unit-tests`
**Purpose**: Run all unit tests with multi-agent remediation  
**Usage**: `/run-unit-tests`  
**Key Features**:
- Complete unit test suite execution
- Multi-agent debugging for failures
- Fast feedback loop
- SSOT compliance checking

---

#### `/run-integration-tests`
**Purpose**: Run non-Docker integration tests  
**Usage**: `/run-integration-tests [focus-area]`  
**Key Features**:
- Integration tests without Docker overhead
- Multi-agent remediation for failures
- Focus area targeting available
- Real service connections required

**Examples**:
```bash
/run-integration-tests          # All integration tests
/run-integration-tests auth     # Auth-focused integration
/run-integration-tests agents   # Agent-focused integration
```

---

#### `/run-unit-frontend-tests`
**Purpose**: Run all frontend tests with Five Whys bug fixing  
**Usage**: `/run-unit-frontend-tests`  
**Key Features**:
- Complete frontend test suite
- Five Whys methodology for failures
- React/TypeScript test coverage
- Integration with backend APIs

---

### Monitoring & Audit Commands

#### `/audit-docker-logs`
**Purpose**: Audit Docker logs for errors and performance issues  
**Usage**: `/audit-docker-logs [service] [lines]`  
**Key Features**:
- Comprehensive error pattern detection
- Performance indicator analysis
- Connection and network issue detection
- Structured audit summary
- Optional deep analysis with Task agent

**Examples**:
```bash
/audit-docker-logs                    # Audit all services
/audit-docker-logs backend 500        # Backend last 500 lines
/audit-docker-logs auth               # Auth service audit
```

---

#### `/audit-gcp-logs`
**Purpose**: Audit GCP Cloud Run logs for staging services  
**Usage**: `/audit-gcp-logs <service> [hours]`  
**Key Features**:
- Real-time Cloud Run log analysis
- Error severity categorization  
- Performance metrics (latency, 5xx codes)
- Cold start detection
- Security/auth failure tracking

**Examples**:
```bash
/audit-gcp-logs                       # All services, last hour
/audit-gcp-logs backend-staging 24    # Backend last 24 hours
/audit-gcp-logs auth-staging 3        # Auth last 3 hours
```

---

### Deployment Commands

#### `/deploy-gcp`
**Purpose**: Deploy to GCP following project standards  
**Usage**: `/deploy-gcp <environment> [options]`  
**Key Features**:
- **MANDATORY**: Authentication check with prompt
- Pre-deployment compliance verification
- Automated smoke tests before deploy
- Service health validation
- Rollback instructions included

**Examples**:
```bash
/deploy-gcp                           # Deploy to staging (default)
/deploy-gcp staging netra-staging     # Explicit staging
/deploy-gcp production netra-prod     # Production deploy
```

**Prerequisites**:
1. **MUST** authenticate first: `gcloud auth login`
2. GCP CLI installed  
3. Proper permissions for GCP project
4. Docker running for local builds

---

### Repository Maintenance Commands

#### `/ssotgardener`
**Purpose**: **CRITICAL** - SSOT violation discovery and remediation  
**Usage**: `/ssotgardener [focus-area]`  
**Key Features**:
- Discovers and remediates SSOT violations blocking golden path
- Fixes SSOT issues creating infinite or bad debugging loops
- Addresses legacy issues and incomplete migrations to SSOT
- Spawns sub-agents for each step with safety checks
- **Time Expectation**: 8-30+ hours for complete SSOT remediation

**Safety Features**:
- Repository health monitoring before any changes
- Test validation for all SSOT updates
- Git safety with develop-long-lived branch protection
- GitHub integration following style guide

**Examples**:
```bash
/ssotgardener                    # Full SSOT audit and remediation
/ssotgardener websocket          # Focus on WebSocket SSOT issues
/ssotgardener database           # Focus on database SSOT patterns
```

---

#### `/gitcommitgardener`
**Purpose**: **CRITICAL** - Safe repository management and cleanup  
**Usage**: `/gitcommitgardener`  
**Key Features**:
- Safe repository management with health monitoring
- Git commit optimization and cleanup
- **Time Expectation**: 8-20+ hours for complete repository gardening
- Multi-agent coordination for complex git operations

**Safety Features**:
- Repository damage prevention
- Branch protection (develop-long-lived focus)
- Comprehensive backup validation
- Health checks before and after operations

---

#### `/gitissueprogressor`
**Purpose**: **CRITICAL** - Full day GitHub issue workflow  
**Usage**: `/gitissueprogressor`  
**Key Features**:
- Complete GitHub issue management workflow
- Full day operation with continuous monitoring
- Issue progression with automated debugging
- GitHub integration with proper labeling

**Process Flow**:
1. Issue identification and prioritization
2. Automated investigation and analysis
3. Multi-agent resolution approach
4. Progress tracking and documentation
5. Resolution validation and closure

---

#### `/audit-gcp-error-loop`
**Purpose**: **CRITICAL** - GCP error monitoring with auto-debug  
**Usage**: `/audit-gcp-error-loop <service> [hours]`  
**Key Features**:
- Continuous GCP error monitoring
- Automatic Five Whys debugging for critical errors
- **Time Expectation**: 8+ hours continuous monitoring
- Real-time error pattern detection

**Examples**:
```bash
/audit-gcp-error-loop                     # All services monitoring
/audit-gcp-error-loop backend-staging 12  # Backend 12-hour monitoring
```

---

### Mission Critical Commands

#### `/ultimate-test-deploy-loop`
**Purpose**: **CRITICAL** - Ultimate staging validation  
**Usage**: `/ultimate-test-deploy-loop [focus-area]`  
**Key Features**:
- Runs 1000+ comprehensive e2e tests continuously
- Real staging environment testing  
- Loops until EVERY test passes or 100 cycles completed
- **Time Expectation**: Runs for hours until success (8-20+ hours)

**Process**:
1. Deploy backend service and wait for revision success
2. Choose e2e tests with staging focus
3. Create GitHub issue with "claude-code-generated-issue" label
4. Spawn agents to run real e2e staging tests
5. For failures: Multi-agent Five Whys debugging  
6. SSOT audit and evidence validation
7. Stability verification (no breaking changes)
8. GitHub PR integration with cross-links
9. **REPEAT** until ALL tests pass

**Examples**:
```bash
/ultimate-test-deploy-loop           # Full system validation
/ultimate-test-deploy-loop auth      # Focus on auth system  
/ultimate-test-deploy-loop websocket # Focus on WebSocket events
```

---

#### `/audit-staging-logs-gcp-loop`
**Purpose**: **CRITICAL** - Continuous staging GCP monitoring with auto-debug  
**Usage**: `/audit-staging-logs-gcp-loop <service> [hours]`  
**Key Features**:
- Runs continuous staging audit cycles (8-30+ hours)
- Auto-triggers Five Whys debugging for critical errors
- Staging environment monitoring with error pattern detection
- GitHub integration for issue tracking
- **Time Expectation**: Long-running operations (8-30+ hours)

**Examples**:
```bash
/audit-staging-logs-gcp-loop                     # All services continuous monitoring
/audit-staging-logs-gcp-loop backend-staging 12  # Backend 12-hour focused monitoring
```

---

#### `/test-create-integration`
**Purpose**: Create 100+ high-quality integration tests  
**Usage**: `/test-create-integration [focus-area]`  
**Key Features**:
- **Time Expectation**: 20-hour process
- Creates comprehensive integration test suite
- Real service testing only (NO MOCKS)
- SSOT methodology compliance
- Multi-agent test generation

**Examples**:
```bash
/test-create-integration             # Full integration suite
/test-create-integration agents      # Agent-focused integration  
/test-create-integration websocket   # WebSocket integration tests
```

---

#### `/test-create-unit-coverage`
**Purpose**: Create unit tests for 100% coverage in SSOT classes  
**Usage**: `/test-create-unit-coverage [focus-area]`  
**Key Features**:
- **Time Expectation**: 8+ hours
- 100% coverage targeting
- SSOT class focus
- Real dependencies where possible
- Coverage reporting integration

**Examples**:
```bash
/test-create-unit-coverage              # All SSOT classes
/test-create-unit-coverage executors    # Execution engine coverage
/test-create-unit-coverage websocket    # WebSocket coverage
```

---

### Architecture & SSOT Commands

#### `/scope-work`
**Purpose**: Create 5 detailed parallel prompts for P0 SSOT refactoring  
**Usage**: `/scope-work`  
**Key Features**:
- SSOT refactoring planning
- Parallel work distribution  
- P0 priority focus
- Architecture compliance planning

---

#### `/ssot-regression-check`
**Purpose**: Multi-agent audit of last 40 commits for missing SSOT implementations  
**Usage**: `/ssot-regression-check <agent-name>`  
**Key Features**:
- Historical commit analysis
- SSOT compliance verification
- Regression identification  
- Multi-agent consensus

**Examples**:
```bash
/ssot-regression-check data-agent
/ssot-regression-check optimization
```

---

#### `/canary`
**Purpose**: Standardized Load Factor Canary diagnostic tasks  
**Usage**: `/canary`  
**Key Features**:
- System health diagnostics
- Load factor analysis
- Performance monitoring
- Canary deployment validation

---

### Specialized Commands

#### `/action`
**Purpose**: Process multiple items with Five Whys analysis  
**Usage**: `/action`  
**Key Features**:
- Multi-item processing with systematic analysis
- Five Whys methodology for each action item
- Automated issue resolution workflow
- GitHub integration for tracking

**Process Flow**:
1. Item identification and prioritization
2. Five Whys analysis for each item
3. Resolution planning and execution
4. Progress documentation and tracking

---

#### `/prmergergit`
**Purpose**: Safe pull request merging with validation  
**Usage**: `/prmergergit`  
**Key Features**:
- Safe PR merging with pre-merge validation
- Test execution before merge
- Repository health checks
- Git safety protocols

**Safety Features**:
- Pre-merge test validation
- Conflict resolution assistance
- Branch protection compliance
- Repository state verification

---

#### `/test-fix-REMOVED_SYNTAX_ERROR`
**Purpose**: Fix tests with REMOVED_SYNTAX_ERROR markings  
**Usage**: `/test-fix-REMOVED_SYNTAX_ERROR`  
**Key Features**:
- Identifies tests marked with REMOVED_SYNTAX_ERROR
- Systematic error resolution approach
- Test restoration and validation
- SSOT compliance during fixes

---

#### `/e2e-fix-directly`
**Purpose**: Real e2e test fix deploy loop (backend focused by default)  
**Usage**: `/e2e-fix-directly [focus-area]`  
**Key Features**:
- Runs E2E tests and remediates issues automatically
- Creates PRs for fixes without human intervention
- Backend focused by default
- Continuous remediation until all tests pass
- Repository safety checks before changes

**Examples**:
```bash
/e2e-fix-directly           # Fix all E2E tests
/e2e-fix-directly backend   # Backend-focused E2E fixes
/e2e-fix-directly auth      # Auth-focused E2E fixes
```

---

#### `/failingtestsgardener`
**Purpose**: Collect test issues and create GitHub issues (no remediation)  
**Usage**: `/failingtestsgardener [test-focus-area]`  
**Key Features**:
- Identifies all failing tests across unit, integration, and E2E
- Creates GitHub issues for tracking failures
- Does NOT attempt remediation (use gitissueprogressor for that)
- Comprehensive test coverage analysis
- Follows GitHub style guide for issues

**Examples**:
```bash
/failingtestsgardener       # All test issues
/failingtestsgardener unit  # Unit test issues only
/failingtestsgardener e2e   # E2E test issues only
```

---

#### `/gcploggardener`
**Purpose**: GCP log issue collector and GitHub issue creator  
**Usage**: `/gcploggardener [time-period] [service]`  
**Key Features**:
- Collects GCP log errors not yet in GitHub issues
- Creates GitHub issues for tracking
- Does NOT attempt remediation (use gitissueprogressor for that)
- Comprehensive log analysis across services
- Updates worklogs with findings

**Examples**:
```bash
/gcploggardener                  # Latest GCP log issues
/gcploggardener 24h backend      # Last 24h backend issues
/gcploggardener 1w all          # Last week all services
```

---

#### `/refresh-upate-tests`
**Purpose**: Refresh, update, and align tests for existing areas  
**Usage**: `/refresh-upate-tests [focus-area]`  
**Key Features**:
- Updates existing test suites to latest standards
- Aligns with latest CLAUDE.md best practices
- Creates new tests if gaps identified
- Follows TEST_CREATION_GUIDE.md standards
- Multi-agent planning and execution

**Note**: Command filename has a typo ("upate" instead of "update")

**Examples**:
```bash
/refresh-upate-tests auth        # Refresh auth tests
/refresh-upate-tests agents      # Refresh agent tests
/refresh-upate-tests websocket   # Refresh WebSocket tests
```

---

#### `/run-demo`
**Purpose**: Setup and launch Netra Apex staging demo with flexible frontend deployment  
**Usage**: `/run-demo`  
**Key Features**:
- **Automatic GCP Authentication**: Handles gcloud authentication seamlessly
- **Environment Configuration**: Sets up all required environment variables for staging
- **Secret Manager Access**: Verifies access to JWT, OpenAI API key, database, and Redis secrets
- **Service Health Checks**: Validates backend and frontend Cloud Run services are running
- **Flexible Frontend**: Choose between GCP deployment or local development server
- **Browser Launch**: Automatically opens frontend in default browser after setup
- **Connectivity Testing**: Verifies all services are accessible before launching

**Frontend Modes**:
- **GCP Cloud Run**: Uses deployed frontend-staging service (production-like)
- **Localhost**: Runs frontend locally on port 3000 (for development)

**Process Flow**:
1. Authenticate with gcloud if needed
2. Set GCP project to netra-staging
3. Configure environment variables
4. Check Secret Manager access
5. Validate Cloud Run services status
6. Deploy services if not running (optional)
7. Start local frontend if localhost mode selected
8. Test connectivity to all services
9. Open browser to frontend URL

**Examples**:
```bash
/run-demo    # Interactive prompt for frontend mode selection
```

**Service URLs**:
- Backend: https://backend-staging-906714043974.us-central1.run.app
- Frontend (GCP): https://frontend-staging-906714043974.us-central1.run.app
- Frontend (Local): http://localhost:3000

---

#### `/testgardener`
**Purpose**: Test management and organization  
**Usage**: `/testgardener [focus-area]`  
**Key Features**:
- Comprehensive test organization and health assessment
- Follows GitHub style guide for all operations
- Repository safety focus with damage prevention
- Covers unit, integration, and E2E staging tests
- Progress issues safely through workflow

**Examples**:
```bash
/testgardener              # General test gardening
/testgardener integration  # Integration test focus
/testgardener all          # All test categories
```

---

### Utility Commands

#### `/priority-test-create`
**Purpose**: Create tests based on priority script analysis  
**Usage**: `/priority-test-create`  
**Key Features**:
- Uses coverage analysis for prioritization
- Intelligent test gap identification
- High-impact test creation
- Resource optimization

---

#### `/test-update-e2e-fix-fakes`
**Purpose**: Fix fake/cheating tests to use real services  
**Usage**: `/test-update-e2e-fix-fakes`  
**Key Features**:
- Identifies mock/fake patterns
- Converts to real service usage
- Maintains test functionality
- CLAUDE.md compliance enforcement

---

## 🚫 Project Standards Enforced

### NO MOCKS Policy
All test commands enforce the **NO MOCKS** policy from CLAUDE.md:
- ❌ **FORBIDDEN**: Mock objects, fake databases, stubbed APIs, simulated events
- ✅ **REQUIRED**: Real PostgreSQL, Redis, ClickHouse, Gemini API, WebSocket connections

### Architecture Principles
- **SSOT**: Single Source of Truth for all components
- **SRP**: Single Responsibility Principle  
- **Real Everything**: E2E > Integration > Unit testing hierarchy
- **Business Value > System Purity**

### Testing Hierarchy
1. **Real Everything E2E**: Full system with real LLM and services
2. **E2E**: End-to-end with real services
3. **Integration**: Service integration tests  
4. **Unit**: Isolated unit tests (minimal mocking allowed)

---

## 📚 Related Documentation

### Essential References
- **[Claude Commands Documentation](../.claude/commands/README.md)** 📋 - **AUTHORITATIVE**: Complete command documentation with 25 commands, usage patterns, and best practices
- **[CLAUDE.md](../CLAUDE.md)** 🎯 - **MASTER DIRECTIVE**: Project standards, architectural principles, and NO MOCKS policy
- **[Test Architecture Visual Overview](../tests/TEST_ARCHITECTURE_VISUAL_OVERVIEW.md)** 📊 - Complete test infrastructure guide
- **[Golden Path User Flow Analysis](./GOLDEN_PATH_USER_FLOW_COMPLETE.md)** 🚀 - Critical user journey analysis ($500K+ ARR dependency)

### Claude Code Automation & Orchestration
- **[Claude Instance Orchestrator](../README-claude-orchestrator.md)** 🤖 - **NEW** - Multi-instance Claude Code automation with SDK features
- **[Claude Orchestration Plan](../claude-code-instances-plan.md)** 📋 - Architecture design and implementation strategy for parallel Claude execution
- **[Claude Instance Orchestrator Script](../scripts/claude-instance-orchestrator.py)** ⚙️ - Python orchestrator for running multiple Claude Code instances concurrently

### Cross-Referenced Documentation
- **[Documentation Index](./index.md)** 📖 - Master documentation navigation hub
- **[User Context Architecture](../reports/archived/USER_CONTEXT_ARCHITECTURE.md)** 🏗️ - Factory-based isolation patterns
- **[Agent Architecture Guide](./AGENT_ARCHITECTURE_DISAMBIGUATION_GUIDE.md)** 🤖 - Agent workflow architecture
- **[SPEC Directory](../SPEC/)** 📋 - Architecture specifications and learnings

### Testing & Development Guides
- **[Test Creation Guide](../reports/testing/TEST_CREATION_GUIDE.md)** 🧪 - Authoritative guide for creating SSOT-compliant tests
- **[Docker Architecture Guide](./docker_architecture_diagrams.md)** 🐳 - Container management and deployment
- **[Five Whys Debugging Reports](../reports/five_whys/)** 🔍 - Root cause analysis examples

---

## ⚡ Quick Reference Card

### Daily Development Flow
```bash
/docker-rebuild              # Fresh start
/compliance                  # Check standards  
/run-demo                   # Launch staging demo
/tdd feature module         # New feature with TDD
/test-real                  # Run tests
/pre-commit                 # Before committing
```

### Debugging Workflow
```bash
/debug-error "error msg" 5  # FOUNDATION: Five Whys debugging
/agent-test agent_name      # Test specific agent
/websocket-test             # Check events
/test-real e2e              # Full system test
/audit-docker-logs          # Audit logs with auto-debug
```

### Testing Suite
```bash
/run-unit-tests            # All unit tests with multi-agent fixes
/run-integration-tests     # Integration tests without Docker
/run-unit-frontend-tests   # Frontend tests with Five Whys  
/test-create "description" # Create SSOT-compliant tests
/priority-test-create      # Smart test prioritization
```

### Architecture & Analysis
```bash
/scope-work                       # P0 SSOT refactoring planning
/ssot-regression-check agent      # Audit commits for SSOT violations  
/analyze-repository audit 5       # Repository audit with 5 agents
/canary                          # System health diagnostics
```

### Mission Critical (Long-Running)
```bash
/ultimate-test-deploy-loop        # CRITICAL: Run until all 1000+ tests pass (hours)
/audit-staging-logs-gcp-loop     # CRITICAL: Continuous staging monitoring (8-30+ hours)
/test-create-integration         # Create 100+ integration tests (20 hours)
/test-create-unit-coverage       # 100% coverage creation (8+ hours)
```

### Repository Maintenance (Long-Running)
```bash
/ssotgardener                    # CRITICAL: SSOT violation remediation (8-30+ hours)
/gitcommitgardener              # CRITICAL: Repository cleanup (8-20+ hours)
/gitissueprogressor             # CRITICAL: Full day GitHub workflow
/audit-gcp-error-loop           # CRITICAL: GCP error monitoring with auto-debug
```

### Deployment & Monitoring
```bash
/deploy-gcp staging              # Deploy to GCP
/audit-gcp-logs                 # Audit Cloud Run logs
/audit-gcp-logs-loop            # Continuous monitoring
```

---

## 🕐 Time Expectations

| Duration | Commands | Purpose |
|----------|----------|---------|
| **< 5 min** | `/docker-rebuild`, `/compliance`, `/test-real`, `/websocket-test`, `/canary`, `/run-demo` | Quick checks, rebuilds, and demo launch |
| **5-30 min** | `/tdd`, `/agent-test`, `/pre-commit`, `/deploy-gcp`, `/debug-error` | Standard development tasks |  
| **1-4 hours** | `/analyze-repository`, `/run-*-tests`, `/audit-*-logs`, `/test-create` | Analysis and testing |
| **8-30+ hours** | `/ultimate-test-deploy-loop`, `/audit-staging-logs-gcp-loop`, `/test-create-integration`, `/test-create-unit-coverage`, `/ssotgardener`, `/gitcommitgardener`, `/gitissueprogressor`, `/audit-gcp-error-loop` | **Mission Critical & Repository Maintenance** - Long-running operations |

---

## 🆘 Troubleshooting

### Command Not Found
- Ensure file is in `.claude/commands/` directory
- File must have `.md` extension  
- Check file permissions

### Docker Issues
- Run `/docker-rebuild` to refresh containers
- Check `docker compose ps` for health status
- Verify environment variables in `.env`

### Test Failures
- Ensure Docker services are running
- Check API keys (especially `GEMINI_API_KEY`)
- Verify database connections
- Run `/compliance` to check architecture

### Authentication Issues (GCP)
- Run `gcloud auth login` before deployment commands
- Verify GCP project permissions
- Check `gcloud config list` for active project

---

*Last Updated: 2025-09-12 | Commands: 39 | Categories: 6 | Mission Critical Commands: 8 | Repository Maintenance Commands: 6*