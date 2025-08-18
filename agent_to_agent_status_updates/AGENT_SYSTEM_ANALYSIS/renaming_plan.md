# Agent System Renaming Plan

## Date: 2025-08-18
## Status: Active

## Categories and Renaming Tasks:

### 1. Core SubAgents (KEEP "Agent" suffix)
**No renaming needed - these are correctly named:**
- TriageSubAgent ✅
- DataSubAgent ✅
- OptimizationsCoreSubAgent ✅
- ActionsToMeetGoalsSubAgent ✅
- ReportingSubAgent ✅
- SyntheticDataSubAgent ✅
- CorpusAdminSubAgent ✅
- SupplyResearcherSubAgent ✅
- SupervisorAgent ✅

**Test files to verify naming consistency:**
- test_triage_sub_agent*.py
- test_data_sub_agent*.py
- test_supply_researcher_agent*.py
- test_subagent_workflow.py

### 2. Execution Components (RENAME to Executor/Manager)
**Files to rename:**
- WebSocket broadcast-related "agents" → BroadcastExecutor
- MCP-related "agents" → MCPExecutor
- Circuit breaker "agents" → CircuitBreakerManager
- Fallback "agents" → FallbackManager

### 3. Service Components (RENAME to Service)
**Files to rename:**
- demo_agent.py → demo_service.py
- github_analyzer/agent.py → github_analyzer/service.py

### 4. Utility Modules (REMOVE "Agent" suffix)
**Files to rename:**
- tool_dispatcher.py (check internal references)
- admin_tool_dispatcher/* (check for "agent" references)
- State management components
- Error handlers
- Validators

### 5. Test Files Updates
**Test renaming pattern:**
- test_*_agent_*.py for non-SubAgents → Update to match new names
- Internal test references → Update imports and class names

## Execution Strategy:
1. Use spawned agents for each category
2. Each agent handles:
   - File renaming
   - Import updates
   - Reference updates
   - Test file updates
3. Verify tests pass after each category
4. Log progress in this directory