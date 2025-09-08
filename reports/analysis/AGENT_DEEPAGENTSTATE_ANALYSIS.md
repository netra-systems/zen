# DeepAgentState Migration Analysis Report

**Generated:** {
  "timestamp": "auto"
}  
**Status:** ACTIVE MIGRATION REQUIRED

## 🚨 Executive Summary

- **Total Files Analyzed:** 245
- **Files with DeepAgentState Usage:** 50
- **Total Usage Patterns:** 341

### Usage by Type
- **import:** 49 occurrences
- **type_annotation:** 278 occurrences
- **instantiation:** 12 occurrences
- **class_inheritance:** 2 occurrences

## 🎯 Migration Priority Classification

### 🔴 ULTRA CRITICAL (19 files)

- `netra_backend/app/agents\base_agent.py`
- `netra_backend/app/agents\execution_engine_consolidated.py`
- `netra_backend/app/agents\quality_supervisor.py`
- `netra_backend/app/agents\supervisor\agent_execution_core.py`
- `netra_backend/app/agents\supervisor\agent_routing.py`
- `netra_backend/app/agents\supervisor\execution_context.py`
- `netra_backend/app/agents\supervisor\execution_engine.py`
- `netra_backend/app/agents\supervisor\execution_factory.py`
- `netra_backend/app/agents\supervisor\mcp_execution_engine.py`
- `netra_backend/app/agents\supervisor\modern_execution_helpers.py`
- ... and 9 more files

### 🟠 HIGH CRITICAL (11 files)

- `netra_backend/app/agents\data_helper_agent.py`
- `netra_backend/app/agents\demo_service\triage.py`
- `netra_backend/app/agents\reporting_sub_agent.py`
- `netra_backend/app/agents\synthetic_data\approval_flow.py`
- `netra_backend/app/agents\synthetic_data\generation_workflow.py`
- `netra_backend/app/agents\synthetic_data\validation.py`
- `netra_backend/app/agents\synthetic_data_approval_handler.py`
- `netra_backend/app/agents\synthetic_data_metrics_handler.py`
- `netra_backend/app/agents\synthetic_data_sub_agent.py`
- `netra_backend/app/agents\synthetic_data_sub_agent_validation.py`
- ... and 1 more files

### 🟡 MEDIUM CRITICAL (3 files)

- `netra_backend/app/agents\request_scoped_tool_dispatcher.py`
- `netra_backend/app/agents\tool_dispatcher_core.py`
- `netra_backend/app/agents\tool_dispatcher_execution.py`

### 🔵 LOW CRITICAL (17 files)

- `netra_backend/app/agents\_legacy_backup\data_sub_agent_backup_20250904\data_sub_agent_old.py`
- `netra_backend/app/agents\agent_communication.py`
- `netra_backend/app/agents\agent_lifecycle.py`
- `netra_backend/app/agents\artifact_validator.py`
- `netra_backend/app/agents\corpus_admin\agent.py`
- `netra_backend/app/agents\corpus_admin\validators.py`
- `netra_backend/app/agents\data_sub_agent\__init__.py`
- `netra_backend/app/agents\demo_service\core.py`
- `netra_backend/app/agents\demo_service\optimization.py`
- `netra_backend/app/agents\demo_service\reporting.py`
- ... and 7 more files

## 📊 Most Used Files

- `netra_backend/app/agents\supervisor\execution_engine.py` (23 patterns)
- `netra_backend/app/agents\corpus_admin\agent.py` (22 patterns)
- `netra_backend/app/agents\migration\deepagentstate_adapter.py` (22 patterns)
- `netra_backend/app/agents\supervisor\pipeline_executor.py` (21 patterns)
- `netra_backend/app/agents\supervisor\mcp_execution_engine.py` (19 patterns)
- `netra_backend/app/agents\github_analyzer\agent.py` (16 patterns)
- `netra_backend/app/agents\agent_lifecycle.py` (14 patterns)
- `netra_backend/app/agents\artifact_validator.py` (13 patterns)
- `netra_backend/app/agents\state.py` (13 patterns)
- `netra_backend/app/agents\supervisor\pipeline_builder.py` (9 patterns)

## 📋 Detailed Usage Patterns

### `netra_backend/app/agents\_legacy_backup\data_sub_agent_backup_20250904\data_sub_agent_old.py`

- Line 36 (import): `from netra_backend.app.agents.state import DeepAgentState`
- Line 132 (type_annotation): `def _extract_analysis_request(self, state: DeepAgentState) -> Dict[str, Union[str, List[str], Optional[str]]]:`

### `netra_backend/app/agents\agent_communication.py`

- Line 21 (import): `from netra_backend.app.agents.state import DeepAgentState`
- Line 180 (type_annotation): `async def run_in_background(self, state: DeepAgentState, run_id: str, stream_updates: bool) -> None:`

### `netra_backend/app/agents\agent_lifecycle.py`

- Line 12 (import): `from netra_backend.app.agents.state import DeepAgentState`
- Line 23 (type_annotation): `async def _pre_run(self, state: DeepAgentState, run_id: str, stream_updates: bool) -> bool:`
- Line 30 (type_annotation): `async def _post_run(self, state: DeepAgentState, run_id: str, stream_updates: bool, success: bool) -> None:`
- Line 65 (type_annotation): `async def run(self, state: DeepAgentState, run_id: str, stream_updates: bool) -> None:`
- Line 86 (type_annotation): `async def _handle_and_reraise_error(self, e: Exception, state: DeepAgentState, run_id: str, stream_updates: bool) -> None:`
- Line 91 (type_annotation): `async def _handle_entry_conditions(self, state: DeepAgentState, run_id: str, stream_updates: bool) -> bool:`
- Line 109 (type_annotation): `async def _handle_websocket_disconnect(self, e: WebSocketDisconnect, state: DeepAgentState, run_id: str, stream_updates: bool) -> None:`
- Line 114 (type_annotation): `async def _handle_execution_error(self, e: Exception, state: DeepAgentState, run_id: str, stream_updates: bool) -> None:`
- Line 131 (type_annotation): `async def execute(self, state: DeepAgentState, run_id: str, stream_updates: bool) -> None:`
- Line 136 (type_annotation): `async def check_entry_conditions(self, state: DeepAgentState, run_id: str) -> bool:`
- Line 141 (type_annotation): `async def cleanup(self, state: DeepAgentState, run_id: str) -> None:`
- Line 158 (type_annotation): `self, run_id: str, stream_updates: bool, status: str, execution_time: float, state: DeepAgentState`
- Line 174 (type_annotation): `async def _execute_with_conditions(self, state: DeepAgentState, run_id: str, stream_updates: bool) -> bool:`
- Line 182 (type_annotation): `async def _handle_entry_failure(self, run_id: str, stream_updates: bool, state: DeepAgentState) -> None:`

### `netra_backend/app/agents\artifact_validator.py`

- Line 16 (import): `from netra_backend.app.agents.state import DeepAgentState, OptimizationsResult`
- Line 58 (type_annotation): `def validate_triage_artifact(self, state: DeepAgentState,`
- Line 67 (type_annotation): `def validate_data_artifact(self, state: DeepAgentState,`
- Line 76 (type_annotation): `def validate_optimization_artifact(self, state: DeepAgentState,`
- Line 161 (type_annotation): `def validate_pipeline_handoff(self, state: DeepAgentState, from_agent: str,`
- Line 174 (type_annotation): `def _collect_triage_validation_issues(self, state: DeepAgentState) -> tuple[List[str], List[str]]:`
- Line 184 (type_annotation): `def _collect_data_validation_issues(self, state: DeepAgentState) -> tuple[List[str], List[str]]:`
- Line 194 (type_annotation): `def _collect_optimization_validation_issues(self, state: DeepAgentState) -> tuple[List[str], List[str]]:`
- Line 313 (type_annotation): `def _create_handoff_context(self, from_agent: str, run_id: str, state: DeepAgentState) -> ValidationContext:`
- Line 319 (type_annotation): `def _run_agent_specific_validation(self, state: DeepAgentState, context: ValidationContext,`
- Line 331 (type_annotation): `def _validate_triage_handoff(self, state: DeepAgentState, context: ValidationContext) -> ArtifactValidationResult:`
- Line 336 (type_annotation): `def _validate_data_handoff(self, state: DeepAgentState, context: ValidationContext) -> ArtifactValidationResult:`
- Line 341 (type_annotation): `def _validate_optimization_handoff(self, state: DeepAgentState, context: ValidationContext) -> ArtifactValidationResult:`

### `netra_backend/app/agents\base_agent.py`

- Line 19 (type_annotation): `# DEPRECATED: DeepAgentState import for migration compatibility only - will be removed in v3.0.0`
- Line 20 (import): `from netra_backend.app.schemas.agent_models import DeepAgentState`
- Line 643 (type_annotation): `# DEPRECATED: Legacy fallback using execute_core_logic with DeepAgentState bridge`
- Line 647 (type_annotation): `f"🚨 CRITICAL DEPRECATION: Agent '{self.name}' is using legacy DeepAgentState bridge pattern. "`
- Line 663 (type_annotation): `self.logger.critical(f"🚨 AGENT MIGRATION REQUIRED: {self.name} using deprecated DeepAgentState pattern")`
- Line 668 (instantiation): `temp_state = DeepAgentState(`
- Line 1102 (type_annotation): `async def execute_modern(self, state: 'DeepAgentState', run_id: str, stream_updates: bool = False) -> ExecutionResult:`
- Line 1109 (type_annotation): `state: Legacy DeepAgentState object`

### `netra_backend/app/agents\corpus_admin\agent.py`

- Line 20 (import): `from netra_backend.app.agents.state import DeepAgentState`
- Line 42 (type_annotation): `def validate_approval_required(self, request: Any, state: DeepAgentState,`
- Line 89 (type_annotation): `async def check_entry_conditions(self, state: DeepAgentState, run_id: str) -> bool:`
- Line 128 (type_annotation): `async def execute(self, state: DeepAgentState, run_id: str, stream_updates: bool) -> Any:`
- Line 141 (type_annotation): `def _create_execution_context(self, state: DeepAgentState, run_id: str,`
- Line 165 (type_annotation): `state: DeepAgentState, run_id: str, stream_updates: bool):`
- Line 169 (type_annotation): `async def _execute_legacy_workflow(self, state: DeepAgentState, run_id: str, stream_updates: bool):`
- Line 174 (type_annotation): `async def _execute_with_error_handling(self, state: DeepAgentState, run_id: str,`
- Line 183 (type_annotation): `async def _execute_corpus_operation_workflow(self, state: DeepAgentState, run_id: str,`
- Line 195 (type_annotation): `async def _process_operation_with_approval(self, request: Any, state: DeepAgentState,`
- Line 203 (type_annotation): `async def _complete_corpus_operation(self, request: Any, state: DeepAgentState,`
- Line 218 (type_annotation): `async def _run_corpus_admin_workflow(self, state: DeepAgentState, run_id: str,`
- Line 219 (type_annotation): `stream_updates: bool) -> DeepAgentState:`
- Line 224 (type_annotation): `async def _handle_approval_check(self, request: Any, state: DeepAgentState,`
- Line 229 (type_annotation): `async def _finalize_operation_result(self, result: CorpusOperationResult, state: DeepAgentState,`
- Line 245 (type_annotation): `async def _validate_state_requirements(self, state: DeepAgentState):`
- Line 261 (type_annotation): `async def _handle_execution_error(self, error: Exception, state: DeepAgentState,`
- Line 266 (type_annotation): `def _is_admin_mode_request(self, state: DeepAgentState) -> bool:`
- Line 282 (type_annotation): `def _has_corpus_keywords(self, state: DeepAgentState) -> bool:`
- Line 295 (type_annotation): `def _has_valid_result(self, state: DeepAgentState) -> bool:`
- Line 316 (type_annotation): `def _log_final_metrics(self, state: DeepAgentState):`
- Line 322 (type_annotation): `async def cleanup(self, state: DeepAgentState, run_id: str):`

### `netra_backend/app/agents\corpus_admin\validators.py`

- Line 9 (import): `from netra_backend.app.agents.state import DeepAgentState`
- Line 23 (type_annotation): `def validate_approval_required(self, request: Any, state: DeepAgentState,`

### `netra_backend/app/agents\data_helper_agent.py`

- Line 14 (import): `from netra_backend.app.agents.state import DeepAgentState`
- Line 164 (type_annotation): `async def execute(self, state: DeepAgentState, run_id: str, stream_updates: bool = False) -> None:`
- Line 196 (type_annotation): `state: Optional[DeepAgentState] = None`
- Line 197 (type_annotation): `) -> DeepAgentState:`
- Line 216 (instantiation): `state = DeepAgentState()`
- Line 275 (type_annotation): `def _extract_previous_results(self, state: DeepAgentState) -> list:`

### `netra_backend/app/agents\data_sub_agent\__init__.py`

- Line 10 (import): `from netra_backend.app.agents.state import DeepAgentState`
- Line 49 (type_annotation): `def _create_execution_context(self, state: DeepAgentState, run_id: str, stream_updates: bool) -> Any:`
- Line 62 (type_annotation): `async def check_entry_conditions(self, state: DeepAgentState, run_id: str) -> bool:`
- Line 70 (type_annotation): `async def execute(self, state: DeepAgentState, run_id: str, stream_updates: bool) -> Any:`

### `netra_backend/app/agents\demo_service\core.py`

- Line 75 (type_annotation): `async def execute(self, state: 'DeepAgentState', run_id: str, stream_updates: bool) -> None:`
- Line 134 (import): `from netra_backend.app.agents.state import DeepAgentState`
- Line 135 (instantiation): `state = DeepAgentState()`

### `netra_backend/app/agents\demo_service\optimization.py`

- Line 135 (import): `from netra_backend.app.agents.state import DeepAgentState`
- Line 137 (instantiation): `state = DeepAgentState()`

### `netra_backend/app/agents\demo_service\reporting.py`

- Line 43 (type_annotation): `async def execute(self, state: 'DeepAgentState', run_id: str, stream_updates: bool) -> None:`

### `netra_backend/app/agents\demo_service\triage.py`

- Line 65 (type_annotation): `async def execute(self, state: 'DeepAgentState', run_id: str, stream_updates: bool) -> None:`
- Line 218 (import): `from netra_backend.app.agents.state import DeepAgentState`
- Line 220 (instantiation): `state = DeepAgentState(message=message, context=context or {})`

### `netra_backend/app/agents\execution_engine_consolidated.py`

- Line 40 (import): `from netra_backend.app.agents.state import DeepAgentState`
- Line 92 (type_annotation): `state: Optional[DeepAgentState] = None`
- Line 407 (type_annotation): `state: Optional[DeepAgentState] = None,`
- Line 586 (type_annotation): `state: Optional[DeepAgentState] = None`

### `netra_backend/app/agents\github_analyzer\agent.py`

- Line 31 (import): `from netra_backend.app.agents.state import DeepAgentState`
- Line 101 (type_annotation): `state: DeepAgentState,`
- Line 195 (type_annotation): `state: DeepAgentState`
- Line 210 (type_annotation): `state: DeepAgentState`
- Line 220 (type_annotation): `state: DeepAgentState`
- Line 230 (type_annotation): `state: DeepAgentState`
- Line 240 (type_annotation): `state: DeepAgentState`
- Line 250 (type_annotation): `state: DeepAgentState`
- Line 264 (type_annotation): `state: DeepAgentState`
- Line 295 (type_annotation): `state: DeepAgentState`
- Line 303 (type_annotation): `state: DeepAgentState`
- Line 313 (type_annotation): `state: DeepAgentState`
- Line 321 (type_annotation): `state: DeepAgentState`
- Line 329 (type_annotation): `state: DeepAgentState`
- Line 368 (type_annotation): `state: DeepAgentState,`
- Line 441 (instantiation): `return await self.execute(DeepAgentState(), context)`

### `netra_backend/app/agents\input_validation.py`

- Line 7 (import): `from netra_backend.app.agents.state import DeepAgentState`
- Line 16 (type_annotation): `state: DeepAgentState`
- Line 164 (type_annotation): `def validate_execution_input(cls, agent_name: str, state: DeepAgentState, run_id: str, stream_updates: bool = False) -> ValidationResult:`
- Line 174 (type_annotation): `def _create_input_data(cls, state: DeepAgentState, run_id: str, stream_updates: bool) -> dict:`
- Line 228 (type_annotation): `def _execute_validation_flow(cls, agent_name: str, state: DeepAgentState, run_id: str, stream_updates: bool) -> ValidationResult:`
- Line 255 (type_annotation): `def validate_and_raise(cls, agent_name: str, state: DeepAgentState, run_id: str, stream_updates: bool = False) -> AgentExecutionInput:`
- Line 290 (type_annotation): `async def wrapper(self, state: DeepAgentState, run_id: str, stream_updates: bool = False):`
- Line 296 (type_annotation): `def _validate_inputs_with_logging(agent_name: str, state: DeepAgentState, run_id: str, stream_updates: bool) -> None:`

### `netra_backend/app/agents\mcp_integration\mcp_intent_detector.py`

- Line 236 (import): `from netra_backend.app.agents.state import DeepAgentState`
- Line 237 (instantiation): `state = DeepAgentState(agent_name="MCPIntentDetector")`

### `netra_backend/app/agents\migration\deepagentstate_adapter.py`

- Line 31 (import): `from netra_backend.app.agents.state import DeepAgentState`
- Line 42 (class_inheritance): `class DeepAgentStateAdapter:`
- Line 83 (type_annotation): `state: DeepAgentState,`
- Line 96 (type_annotation): `state: The DeepAgentState to convert`
- Line 120 (type_annotation): `f"Migrating DeepAgentState to UserExecutionContext: "`
- Line 144 (type_annotation): `f"Successfully migrated DeepAgentState to UserExecutionContext: "`
- Line 151 (type_annotation): `error_msg = f"Failed to migrate DeepAgentState to UserExecutionContext: {e}"`
- Line 160 (type_annotation): `) -> DeepAgentState:`
- Line 188 (type_annotation): `f"Converting UserExecutionContext to DeepAgentState (TEMPORARY): "`
- Line 197 (instantiation): `state = DeepAgentState(**state_data)`
- Line 200 (type_annotation): `f"Converted UserExecutionContext to DeepAgentState: "`
- Line 207 (type_annotation): `error_msg = f"Failed to convert UserExecutionContext to DeepAgentState: {e}"`
- Line 212 (type_annotation): `def _extract_agent_context(cls, state: DeepAgentState) -> Dict[str, Any]:`
- Line 246 (type_annotation): `state: DeepAgentState,`
- Line 254 (type_annotation): `'migration_source': 'DeepAgentState',`
- Line 314 (type_annotation): `original_state: DeepAgentState,`
- Line 387 (type_annotation): `if 'DeepAgentState' in line_stripped:`
- Line 389 (type_annotation): `'DeepAgentState' in line_stripped):`
- Line 398 (type_annotation): `elif line_stripped.startswith('class') and 'DeepAgentState' in line_stripped:`
- Line 407 (instantiation): `elif 'DeepAgentState(' in line_stripped:`
- Line 416 (type_annotation): `elif ':' in line_stripped and 'DeepAgentState' in line_stripped:`
- Line 451 (type_annotation): `report = f"🚨 Found {len(usage_patterns)} DeepAgentState usage patterns in {len(files_by_usage)} files:\n\n"`

### `netra_backend/app/agents\production_tool.py`

- Line 6 (import): `from netra_backend.app.agents.state import DeepAgentState`
- Line 44 (type_annotation): `state: Optional[DeepAgentState],`
- Line 54 (type_annotation): `self, parameters: Dict[str, Any], state: Optional[DeepAgentState], run_id: Optional[str]`
- Line 73 (type_annotation): `state: Optional[DeepAgentState],`

### `netra_backend/app/agents\quality_checks.py`

- Line 9 (import): `from netra_backend.app.agents.state import DeepAgentState`
- Line 50 (type_annotation): `state: DeepAgentState) -> Optional[ValidationResult]:`
- Line 62 (type_annotation): `context: AgentExecutionContext, state: DeepAgentState) -> ValidationResult:`
- Line 68 (type_annotation): `self, agent_output: str, agent_name: str, context: AgentExecutionContext, state: DeepAgentState`
- Line 87 (type_annotation): `state: DeepAgentState) -> ValidationResult:`
- Line 97 (type_annotation): `state: DeepAgentState,`
- Line 128 (type_annotation): `state: DeepAgentState,`
- Line 136 (type_annotation): `def _extract_agent_output(self, state: DeepAgentState, agent_name: str) -> Optional[str]:`

... and 30 more files with usage patterns.

## ⚡ Recommended Actions

1. **START WITH ULTRA CRITICAL**: Begin migration with user-facing and core execution components
2. **VALIDATE ISOLATION**: Ensure each migrated component maintains proper user isolation  
3. **TEST THOROUGHLY**: Run comprehensive test suites after each migration
4. **MONITOR PROGRESS**: Use this report to track migration completion

**🚨 CRITICAL**: Every day DeepAgentState remains in production increases user data leakage risk.
