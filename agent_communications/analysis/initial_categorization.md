# Agent System Categorization and Naming Convention Status

## Date: 2025-08-18
## Status: In Progress

## Analysis Complete

### Current Agent Categories Identified:

#### 1. Core SubAgents (KEEP "Agent" suffix - LLM-based workflow agents)
**Location:** Main agents directory
- `triage_sub_agent.py` → Keep as TriageSubAgent
- `data_sub_agent/agent.py` → Keep as DataSubAgent  
- `optimizations_core_sub_agent.py` → Keep as OptimizationsCoreSubAgent
- `actions_to_meet_goals_sub_agent.py` → Keep as ActionsToMeetGoalsSubAgent
- `reporting_sub_agent.py` → Keep as ReportingSubAgent
- `synthetic_data_sub_agent.py` → Keep as SyntheticDataSubAgent
- `corpus_admin_sub_agent.py` → Keep as CorpusAdminSubAgent
- `supply_researcher_sub_agent.py` → Keep as SupplyResearcherSubAgent

**Supervisor (Special Case - Keep "Agent"):**
- `supervisor_consolidated.py` → Keep as SupervisorAgent (orchestrator)

#### 2. Execution Agents (RENAME to Executors/Managers)
**Infrastructure pattern implementations:**
- WebSocket broadcast components → Rename to BroadcastExecutor/Manager
- MCP integration components → Rename to MCPExecutor/Manager

#### 3. Service Agents (RENAME to Services)
**Specialized processing units:**
- `github_analyzer/` → Rename to GitHubAnalyzerService
- `demo_agent.py` → Rename to DemoService

#### 4. Helper/Utility "Agents" (RENAME appropriately)
**Misnamed utility modules:**
- `tool_dispatcher.py` → Rename to ToolDispatcher (remove "agent" references)
- `admin_tool_dispatcher/` → Rename to AdminToolDispatcher modules
- State management components → Rename to StateManager
- Error handlers → Keep as ErrorHandler
- Validators → Keep as Validator

## Next Steps:
1. Update XML documentation
2. Update Claude.md
3. Begin systematic renaming using spawned agents
4. Verify tests after each category rename

## Tracking:
- Total Components to Rename: ~50+ files
- Categories Clarified: 4
- Documentation Updates Needed: XML specs, Claude.md