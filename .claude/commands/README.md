# Claude Code Custom Slash Commands Documentation

> 📖 **📋 For comprehensive command documentation with cross-references, see:**  
> **[`docs/COMMAND_INDEX.md`](../../docs/COMMAND_INDEX.md)** - Complete indexed command reference with usage patterns and integration links

> 📝 **Maintenance Note**: When creating new slash commands, please update this README.md to include:
> - Command name and purpose in the "Available Commands" section
> - Usage examples
> - Any new categories or patterns introduced
> - **ALSO update the comprehensive index at `docs/COMMAND_INDEX.md`**
> 
> This ensures all team members can discover and use available commands effectively.

## Overview

This directory contains **25 custom slash commands** for the Netra Apex project. These commands automate repetitive tasks and enforce project standards, particularly the **NO MOCKS** policy and real service testing requirements.

**Command Categories:**
- **12 Core Commands** - Development workflow and debugging
- **2 Mission Critical** - Long-running validation and monitoring (8-20 hours)
- **8 Testing & Development** - Comprehensive test creation and execution
- **3 Analysis & Architecture** - SSOT compliance and system diagnostics

## Command Structure

### Location
- **Project Commands**: `.claude/commands/` (this directory)
- **Personal Commands**: `~/.claude/commands/` (user-specific, cross-project)

### Command Format
```yaml
---
allowed-tools: ["Tool1", "Tool2"]  # Tools the command can use
description: "Brief description"    # Shown in help
argument-hint: "<arg1> [arg2]"      # Expected arguments
---

# Command content (Markdown)
!bash command                        # Execute bash
@file.txt                           # Reference files
$1, $2, $ARGUMENTS                  # Use arguments
```

## Available Commands

### 1. `/tdd <feature-name> <module-name>`
**Purpose**: Execute complete Test-Driven Development workflow  
**Key Features**:
- Enforces REAL services only (NO MOCKS)
- Spawns multiple agents with reviewers
- 6-step TDD process: Write tests → Verify failure → Commit → Implement → Refactor → Merge
- Uses real PostgreSQL, Redis, ClickHouse, Gemini API

**Example**:
```bash
/tdd user-authentication auth_service
```

### 2. `/docker-rebuild [service-name]`
**Purpose**: Rebuild Docker containers from scratch  
**Key Features**:
- Stops all containers
- Rebuilds without cache
- Restarts and verifies health
- Can target specific service or all

**Example**:
```bash
/docker-rebuild          # Rebuild all
/docker-rebuild backend  # Rebuild backend only
```

### 3. `/test-real [category]`
**Purpose**: Run tests with real services and LLM  
**Key Features**:
- Ensures Docker services are running
- Uses real databases and APIs
- Categories: unit, integration, e2e, smoke, api

**Example**:
```bash
/test-real              # Run integration tests (default)
/test-real e2e          # Run end-to-end tests
```

### 4. `/agent-test <agent-name>`
**Purpose**: Test specific agent implementation  
**Key Features**:
- Runs agent-specific tests
- Verifies WebSocket events
- Uses real LLM connections

**Example**:
```bash
/agent-test data_analyst
/agent-test optimization
```

### 5. `/compliance`
**Purpose**: Check architecture compliance  
**Key Features**:
- Runs architecture compliance scripts
- Checks import rules (no relative imports)
- Validates string literals
- Verifies folder structure

**Example**:
```bash
/compliance
```

### 6. `/websocket-test`
**Purpose**: Test mission-critical WebSocket events  
**Key Features**:
- Tests agent event propagation
- Verifies all required events: agent_started, agent_thinking, tool_executing, tool_completed, agent_completed
- Checks integration points

**Example**:
```bash
/websocket-test
```

### 7. `/pre-commit [scope]`
**Purpose**: Complete CLAUDE.md compliance check before committing  
**Key Features**:
- Validates all CLAUDE.md requirements
- Checks mission-critical values
- Runs tests for changed modules
- Generates compliance report
- Groups checks by commit scope

**Example**:
```bash
/pre-commit              # Full check
/pre-commit backend      # Backend-focused check
/pre-commit agents       # Agent-specific check
```

### 8. `/audit-docker-logs [service] [lines]`
**Purpose**: Audit Docker logs for errors and performance issues  
**Key Features**:
- Comprehensive error pattern detection
- Performance indicator analysis
- Connection and network issue detection
- Structured audit summary
- Optional deep analysis with Task agent

**Example**:
```bash
/audit-docker-logs                  # Audit all services
/audit-docker-logs backend 500      # Backend last 500 lines
/audit-docker-logs auth             # Auth service audit
```

### 9. `/deploy-gcp <environment> [options]`
**Purpose**: Deploy to GCP following project standards  
**Key Features**:
- Mandatory authentication check with prompt
- Pre-deployment compliance verification
- Automated smoke tests before deploy
- Service health validation
- Rollback instructions included

**Example**:
```bash
/deploy-gcp                          # Deploy to staging
/deploy-gcp staging netra-staging   # Explicit staging
/deploy-gcp production netra-prod   # Production deploy
```

### 10. `/audit-gcp-logs <service> [hours]`
**Purpose**: Audit GCP Cloud Run logs for staging services  
**Key Features**:
- Real-time Cloud Run log analysis
- Error severity categorization
- Performance metrics (latency, 5xx codes)
- Cold start detection
- Security/auth failure tracking

**Example**:
```bash
/audit-gcp-logs                      # All services, last hour
/audit-gcp-logs backend-staging 24  # Backend last 24 hours
/audit-gcp-logs auth-staging 3      # Auth last 3 hours
```

### 11. `/analyze-repository <action> [num-agents]`
**Purpose**: Parallel repository analysis with N agents  
**Key Features**:
- Divides repository into non-overlapping sections
- Sequential agent spawning to prevent crashes
- Synthesizes findings from all agents
- Executes action based on combined intelligence
- Supports audit, document, refactor, security-scan

**Example**:
```bash
/analyze-repository audit           # 5 agents audit codebase
/analyze-repository security-scan 8 # 8 agents security scan
/analyze-repository document 3      # 3 agents generate docs
```

### 12. `/debug-error <error-description> [num-agents]`
**Purpose**: Five Whys-driven intelligent debugging with agent consensus  
**Key Features**:
- **FOUNDATION**: Uses Five Whys methodology for systematic root cause analysis
- Requires (n-1)/n agents consensus before fixes
- Cascade failure prevention with validation
- Automatic revert if issues detected
- Only commits when execution is flawless
- Conservative approach with human fallback

**Example**:
```bash
/debug-error "IndentationError in service.py" 5
/debug-error "Connection refused to PostgreSQL" 7
/debug-error "WebSocket events not firing" 3
```

## Mission Critical Commands

### 13. `/ultimate-test-deploy-loop [focus-area]`
**Purpose**: **CRITICAL** - Ultimate staging validation that runs until ALL tests pass  
**Key Features**:
- Runs 1000+ comprehensive e2e tests continuously
- Real staging environment testing
- Loops until EVERY test passes or 100 cycles completed
- Comprehensive deployment validation
- **Time Expectation**: Runs for hours until success

**Example**:
```bash
/ultimate-test-deploy-loop          # Full system validation
/ultimate-test-deploy-loop auth     # Focus on auth system
```

### 14. `/audit-gcp-logs-loop <service> [hours]`
**Purpose**: **CRITICAL** - Continuous GCP monitoring with auto-debug  
**Key Features**:
- Runs 100 continuous audit cycles
- Auto-triggers debugging for critical errors
- Production monitoring all night
- Uses Five Whys methodology automatically
- **Time Expectation**: Runs indefinitely (8+ hours)

**Example**:
```bash
/audit-gcp-logs-loop                    # All services, 100 cycles
/audit-gcp-logs-loop backend-staging 4  # Backend last 4 hours, loop
```

## Testing & Development Commands

### 15. `/run-integration-tests [focus-area]`
**Purpose**: Run non-Docker integration tests with multi-agent remediation  
**Key Features**:
- Integration tests without Docker overhead
- Multi-agent remediation for failures
- Focus area targeting available
- Real service connections

**Example**:
```bash
/run-integration-tests              # All integration tests
/run-integration-tests auth         # Auth-focused integration
```

### 16. `/run-unit-tests`
**Purpose**: Run all unit tests with multi-agent remediation  
**Key Features**:
- Complete unit test suite
- Multi-agent debugging for failures
- Fast feedback loop
- SSOT compliance checking

**Example**:
```bash
/run-unit-tests
```

### 17. `/run-unit-frontend-tests`
**Purpose**: Run all frontend tests with Five Whys bug fixing  
**Key Features**:
- Complete frontend test suite
- Five Whys methodology for failures
- React/TypeScript test coverage
- Integration with backend APIs

**Example**:
```bash
/run-unit-frontend-tests
```

### 18. `/test-create [tests-to-be-created]`
**Purpose**: Create tests following TEST_CREATION_GUIDE.md standards  
**Key Features**:
- SSOT compliant test creation
- Real services only (NO MOCKS)
- Follows project test architecture
- Automatic documentation updates

**Example**:
```bash
/test-create "auth flow tests"
/test-create "WebSocket agent events"
```

### 19. `/test-create-integration [focus-area]`
**Purpose**: Create 100+ high-quality integration tests  
**Key Features**:
- **Time Expectation**: 20-hour process
- Creates comprehensive integration test suite
- Real service testing only
- SSOT methodology compliance
- Multi-agent test generation

**Example**:
```bash
/test-create-integration            # Full integration suite
/test-create-integration agents     # Agent-focused integration
```

### 20. `/test-create-unit-coverage [focus-area]`
**Purpose**: Create unit tests for 100% coverage in SSOT classes  
**Key Features**:
- **Time Expectation**: 8+ hours
- 100% coverage targeting
- SSOT class focus
- Real dependencies where possible
- Coverage reporting integration

**Example**:
```bash
/test-create-unit-coverage              # All SSOT classes
/test-create-unit-coverage executors    # Execution engine coverage
```

### 21. `/test-update-e2e-fix-fakes`
**Purpose**: Fix fake/cheating tests to use real services  
**Key Features**:
- Identifies mock/fake patterns
- Converts to real service usage
- Maintains test functionality
- CLAUDE.md compliance enforcement

**Example**:
```bash
/test-update-e2e-fix-fakes
```

### 22. `/priority-test-create`
**Purpose**: Create tests based on priority script analysis  
**Key Features**:
- Uses coverage analysis for prioritization
- Intelligent test gap identification
- High-impact test creation
- Resource optimization

**Example**:
```bash
/priority-test-create
```

## Analysis & Architecture Commands

### 23. `/scope-work`
**Purpose**: Create 5 detailed parallel prompts for P0 SSOT refactoring  
**Key Features**:
- SSOT refactoring planning
- Parallel work distribution
- P0 priority focus
- Architecture compliance planning

**Example**:
```bash
/scope-work
```

### 24. `/ssot-regression-check <agent-name>`
**Purpose**: Multi-agent audit of last 40 commits for missing SSOT implementations  
**Key Features**:
- Historical commit analysis
- SSOT compliance verification
- Regression identification
- Multi-agent consensus

**Example**:
```bash
/ssot-regression-check data-agent
/ssot-regression-check optimization
```

### 25. `/canary`
**Purpose**: Standardized Load Factor Canary diagnostic tasks  
**Key Features**:
- System health diagnostics
- Load factor analysis
- Performance monitoring
- Canary deployment validation

**Example**:
```bash
/canary
```

## Project Standards Enforced

### NO MOCKS Policy
All test commands enforce the **NO MOCKS** policy from CLAUDE.md:
- ❌ **FORBIDDEN**: Mock objects, fake databases, stubbed APIs, simulated events
- ✅ **REQUIRED**: Real PostgreSQL, Redis, ClickHouse, Gemini API, WebSocket connections

### Architecture Principles
- Single Source of Truth (SSOT)
- Single Responsibility Principle (SRP)
- Real Everything: E2E > Integration > Unit
- Business Value > System Purity

### Testing Hierarchy
1. **Real Everything E2E**: Full system with real LLM and services
2. **E2E**: End-to-end with real services
3. **Integration**: Service integration tests
4. **Unit**: Isolated unit tests (minimal)

## Creating New Commands

### Template
```markdown
---
allowed-tools: ["Bash", "Read", "Edit", "Task"]
description: "Your command description"
argument-hint: "<required> [optional]"
---

# Command Title

Brief description of what this command does.

## Configuration/Parameters
- **Parameter 1:** Description
- **Parameter 2:** Description

## Execution Steps

### 1. Step Name
!echo "Status message..."
!command to execute

### 2. Another Step
!another command

## Usage Examples
- `/command-name arg1` - Description
- `/command-name arg1 arg2` - Description
```

### Best Practices
1. **Use real services**: Always include `--real-services` flag
2. **Add logging**: Include echo statements for clarity
3. **Check prerequisites**: Verify Docker, API keys, etc.
4. **Handle errors**: Add error checking and recovery
5. **Document arguments**: Use clear argument-hint
6. **Format for humans**: Use headers, sections, and clear structure
7. **Update README**: Add your new command to this documentation

## Troubleshooting

### Command Not Found
- Ensure file is in `.claude/commands/`
- File must have `.md` extension
- Check file permissions

### Docker Issues
- Run `/docker-rebuild` to refresh containers
- Check `docker compose ps` for health status
- Verify environment variables in `.env`

### Test Failures
- Ensure Docker services are running
- Check API keys (especially GEMINI_API_KEY)
- Verify database connections
- Run `/compliance` to check architecture

## Related Documentation
- [`CLAUDE.md`](../../CLAUDE.md) - Project directives and standards
- [`TEST_ARCHITECTURE_VISUAL_OVERVIEW.md`](../../tests/TEST_ARCHITECTURE_VISUAL_OVERVIEW.md) - Test infrastructure
- [`SPEC/`](../../SPEC/) - Architecture specifications
- [`docs/`](../../docs/) - Additional documentation

## Quick Reference Card

```bash
# Development Workflow
/docker-rebuild             # Fresh start
/compliance                 # Check standards
/tdd feature module        # New feature with TDD
/test-real                 # Run tests
/pre-commit                # Before committing

# Mission Critical (Long-Running)
/ultimate-test-deploy-loop  # CRITICAL: Run until all 1000+ tests pass (hours)
/audit-gcp-logs-loop        # CRITICAL: 100-cycle monitoring all night
/test-create-integration    # Create 100+ integration tests (20 hours)
/test-create-unit-coverage  # 100% coverage creation (8+ hours)

# Testing Suite
/run-unit-tests            # All unit tests with multi-agent fixes
/run-integration-tests     # Integration tests without Docker
/run-unit-frontend-tests   # Frontend tests with Five Whys
/test-create "description" # Create SSOT-compliant tests
/test-update-e2e-fix-fakes # Fix fake tests to real services
/priority-test-create      # Smart test prioritization

# Debugging & Analysis (Five Whys Method)
/debug-error "error msg" 5 # FOUNDATION: Five Whys debugging
/agent-test agent_name     # Test specific agent
/websocket-test            # Check events
/test-real e2e             # Full system test
/audit-docker-logs         # Audit Docker logs with auto-debug

# Architecture & SSOT
/scope-work                # P0 SSOT refactoring planning  
/ssot-regression-check agent # Audit commits for SSOT violations
/canary                    # System health diagnostics

# Deployment & Monitoring
/deploy-gcp staging        # Deploy to GCP
/audit-gcp-logs            # Audit Cloud Run logs

# Advanced Analysis
/analyze-repository audit 5    # Repository audit with 5 agents
/analyze-repository security 8 # Security scan with 8 agents
```

## Time Expectations

**⏱️ Quick Commands (< 5 minutes)**
- `/docker-rebuild`, `/compliance`, `/test-real`, `/websocket-test`, `/canary`

**🕐 Standard Commands (5-30 minutes)**  
- `/tdd`, `/agent-test`, `/pre-commit`, `/deploy-gcp`, `/debug-error`

**🕓 Long Commands (1-4 hours)**
- `/analyze-repository`, `/run-*-tests`, `/audit-*-logs`, `/test-create`

**🌙 Mission Critical (8-20 hours)**
- `/ultimate-test-deploy-loop`, `/audit-gcp-logs-loop`, `/test-create-integration`, `/test-create-unit-coverage`