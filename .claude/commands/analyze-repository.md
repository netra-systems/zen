---
allowed-tools: ["Task", "Read", "Glob"]
description: "Spawn N agents to analyze repository in parallel without overlaps"
argument-hint: "<action> [num-agents]"
---

# 🔍 Repository Analysis with Parallel Agents

Spawn multiple agents to analyze the entire codebase in parallel, then combine insights.

## Configuration
- **Action:** $1 (e.g., audit, document, refactor, security-scan)
- **Number of Agents:** ${2:-5}
- **Mode:** Parallel analysis with no overlaps

## Repository Structure Discovery

### 1. Map Repository Structure
@Read: LLM_MASTER_INDEX.md
@Glob: **/*.py
@Glob: **/*.ts
@Glob: **/*.tsx

### 2. Define Agent Assignments (No Overlaps)

Based on ${2:-5} agents, the repository will be divided:

**Agent 1 - Backend Core**
- `/netra_backend/app/core/`
- `/netra_backend/app/models/`
- `/netra_backend/app/database/`

**Agent 2 - Backend Services & Routes**
- `/netra_backend/app/services/`
- `/netra_backend/app/routes/`
- `/netra_backend/app/websocket/`

**Agent 3 - Agents & AI**
- `/netra_backend/app/agents/`
- `/netra_backend/app/llm/`
- `/netra_backend/app/tools/`

**Agent 4 - Frontend & Auth**
- `/frontend/`
- `/auth_service/`

**Agent 5 - Infrastructure & Tests**
- `/tests/`
- `/scripts/`
- `/docker/`
- `/SPEC/`
- Configuration files

## Parallel Agent Execution

### 3. Spawn Agent 1 - Backend Core
@Task: Analyze Backend Core for $1
Agent 1 Assignment:
- **Folders:** /netra_backend/app/core/, /netra_backend/app/models/, /netra_backend/app/database/
- **Task:** Perform $1 analysis on backend core components
- **Focus:** Database models, core factories, app initialization
- **Output:** Detailed report on core architecture and any issues found
- **IMPORTANT:** Do NOT analyze folders assigned to other agents

### 4. Spawn Agent 2 - Backend Services
@Task: Analyze Backend Services for $1
Agent 2 Assignment:
- **Folders:** /netra_backend/app/services/, /netra_backend/app/routes/, /netra_backend/app/websocket/
- **Task:** Perform $1 analysis on services and API routes
- **Focus:** Service layer, API endpoints, WebSocket handling
- **Output:** Service architecture report and recommendations
- **IMPORTANT:** Do NOT analyze folders assigned to other agents

### 5. Spawn Agent 3 - AI & Agents
@Task: Analyze AI Systems for $1
Agent 3 Assignment:
- **Folders:** /netra_backend/app/agents/, /netra_backend/app/llm/, /netra_backend/app/tools/
- **Task:** Perform $1 analysis on AI and agent systems
- **Focus:** Agent workflows, LLM integration, tool execution
- **Output:** AI architecture report and optimization opportunities
- **IMPORTANT:** Do NOT analyze folders assigned to other agents

### 6. Spawn Agent 4 - Frontend & Auth
@Task: Analyze Frontend and Auth for $1
Agent 4 Assignment:
- **Folders:** /frontend/, /auth_service/
- **Task:** Perform $1 analysis on frontend and authentication
- **Focus:** React components, auth flows, UI/UX patterns
- **Output:** Frontend architecture and auth security report
- **IMPORTANT:** Do NOT analyze folders assigned to other agents

### 7. Spawn Agent 5 - Infrastructure
@Task: Analyze Infrastructure for $1
Agent 5 Assignment:
- **Folders:** /tests/, /scripts/, /docker/, /SPEC/, root config files
- **Task:** Perform $1 analysis on infrastructure and testing
- **Focus:** Test coverage, deployment scripts, Docker setup, specifications
- **Output:** Infrastructure health report and compliance status
- **IMPORTANT:** Do NOT analyze folders assigned to other agents

## Synthesis & Action

### 8. Combine Agent Reports
@Task: Synthesize findings from all ${2:-5} agents
Combine all agent reports:
- Identify common patterns across modules
- Detect cross-module dependencies and issues
- Prioritize findings by severity
- Create unified action plan

### 9. Execute Action Based on Combined Intelligence
@Task: Execute $1 based on combined analysis
Based on synthesis from all agents:
- **If action is 'audit':** Generate comprehensive audit report
- **If action is 'document':** Create unified documentation
- **If action is 'refactor':** Plan coordinated refactoring strategy
- **If action is 'security-scan':** Compile security vulnerability report
- **If action is 'optimize':** Create optimization roadmap

### 10. Validation
Ensure:
- No folder was analyzed twice (no overlaps)
- All critical folders were covered
- Reports are consistent and non-contradictory
- Action plan is coherent and complete

## Usage Examples
- `/analyze-repository audit` - Audit entire codebase with 5 agents
- `/analyze-repository security-scan 8` - Security scan with 8 agents
- `/analyze-repository document 3` - Generate docs with 3 agents
- `/analyze-repository refactor 10` - Plan refactoring with 10 agents

## Agent Coordination Rules
1. **Sequential Spawning:** Agents spawn one at a time to avoid crashes
2. **No Overlaps:** Each folder assigned to exactly one agent
3. **Clear Boundaries:** Agents respect their assigned directories
4. **Unified Reporting:** All findings consolidated before action
5. **Consensus Required:** Major decisions need agreement from majority

## Notes
- Agents spawn sequentially with small delays to prevent system overload
- Each agent works independently on their assigned folders
- Final synthesis agent has access to all individual reports
- Action is taken only after all agents complete analysis