# Claude Test Context Window Snapshot

## Current Conversation

### User Request
save everything in your context window too claude_test_context.md

### System Context

#### Environment Information
- Working directory: C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1
- Is directory a git repo: Yes
- Platform: win32
- Today's date: 2025-08-19
- Model: Claude Opus 4.1 (claude-opus-4-1-20250805)
- Knowledge cutoff: January 2025

#### Git Status at Start
- Current branch: 8-18-25-PM
- Main branch: main
- Modified files:
  - .dev_launcher_cache/startup_cache.json
  - SPEC/learnings/auth.xml
  - app/agents/state.py
  - app/websocket/connection.py
  - app/websocket/connection_executor.py
  - auth_service/auth_core/routes/auth_routes.py
- Untracked files:
  - SPEC/websocket_ideal_state.xml
  - app/tests/critical/test_websocket_execution_engine.py
  - app/tests/integration/test_websocket_end_to_end.py
  - nul
- Recent commits:
  - d085b2e9 a
  - df5a28a7 a
  - e0b8de3d a
  - c03d6ab9 a
  - ab3e834e a

## CLAUDE.md Instructions (Project Context)

### 🔴 Business CRITICAL
- Must make money via shipping Netra Apex
- Apex must be something people want
- Target: customers spending on AI, LLM, Agent, and AI related items
- Value creation must be significant percent of customer AI spend
- Customer segments: Free, Early, Mid, Enterprise
- Business goals > Engineering goals
- Every code addition must consider: Business value, Customer segment, Value relative to AI spend

### Revenue-Driven Development: Business Value Justification (BVJ)
Every engineering task must include:
1. **Segment**: Target customer segment
2. **Business Goal**: Specific value creation
3. **Value Impact**: Estimated savings/improvements
4. **Revenue Impact**: Monetization potential

### 🔴 Engineering CRITICAL: MODULE-BASED ARCHITECTURE
**MANDATORY**: 
- Every file ≤300 lines
- ALL functions ≤8 lines
- Plan module boundaries BEFORE coding
- Each module = single responsibility, clear interface, testable unit
- Composable design for reuse
- STABLE BY DEFAULT - flag breaking changes
- Atomic code changes
- Update docs/xmls after work

### Core Principles

#### 1. ULTRA DEEP THINK (Required 3x)
- FIRST: Deep think BEFORE implementation
- SECOND: Think about edge cases, performance, impacts
- THIRD: Complex problems require masterpiece thinking

#### 2. Specs are Law
- SPEC/*.xml = Source of truth
- Update specs BEFORE AND AFTER code changes
- Document learnings to prevent regression

#### 3. ARCHITECTURE
- Stay within existing system bounds unless requested
- Keep complexity limited
- Find elegant, simple solutions
- Modular code ALWAYS
- No duplicate files with suffixes (_enhanced, _fixed, etc.)

### 🔴 MICROSERVICE INDEPENDENCE (MANDATORY)
- All microservices 100% independent
- Use unique module names
- Keep imports independent - APIs only
- Test independence: cd service_name && python main.py

### 🔴 AGENT NAMING CONVENTIONS (MANDATORY)
1. **"Agent" suffix**: ONLY for LLM-based SubAgents
2. **"Executor/Manager" suffix**: Infrastructure patterns
3. **"Service" suffix**: Specialized processors
4. **Utility naming**: Descriptive names without "Agent"

### Project Overview
**Netra Apex AI Optimization Platform** - Enterprise AI workload optimization with multi-agent architecture

### Key Development Commands
```bash
python scripts/dev_launcher.py # Start dev
python test_runner.py --level integration --no-coverage --fast-fail # DEFAULT tests
```

### Deployment (GCP Staging)
- Quick Deploy: python deploy_staging_reliable.py
- Auth Issues: python setup_staging_auth.py --force-new-key

### Critical Specs to Always Consult
1. learnings/index.xml - Master index
2. type_safety.xml - Type safety
3. conventions.xml - Standards, 300-line limit
4. code_changes.xml - Change checklist
5. no_test_stubs.xml - No test stubs in production
6. anti_regression.xml - Prevent regressions
7. independent_services.xml - Microservice independence

### Testing Requirements
- DEFAULT: python test_runner.py --level integration --no-coverage --fast-fail
- AGENT CHANGES: python test_runner.py --level agents --real-llm
- BEFORE RELEASES: python test_runner.py --level integration --real-llm

### Critical Rules
- 300-LINE MODULES & 8-LINE FUNCTIONS (MANDATORY)
- REAL CODE ALWAYS - no placeholders
- Type safety first (Pydantic/TypeScript)
- Async/await for ALL I/O
- Repository pattern for database
- NetraException for errors

### Tool Usage Permissions
Various Bash commands are pre-approved including:
- python, find, ls, rm, npm test, pytest
- pip/npm install, curl, npm run dev
- Git operations, linting, type checking
- Environment and virtualenv operations

### Security Reminders
- Assist with defensive security tasks only
- Never create malicious code
- Allow security analysis and defensive tools
- Never expose or log secrets
- Never commit secrets to repository

## Current Todo List Status
- Todo list is currently empty

## Additional Context Notes
- Claude Code is the official CLI for Claude
- Interactive CLI tool for software engineering tasks
- Should be concise, direct, and minimize output tokens
- Can use GitHub-flavored markdown for formatting
- Should follow existing code conventions when making changes
- Proactive task management with TodoWrite tool encouraged
- Hooks may be configured for tool calls - treat feedback as from user