# Deleted Test Files Coverage Record

**Date:** 2025-01-06  
**Purpose:** Record of deleted corrupted test files for future test coverage recreation  
**Status:** TODO - Tests need to be recreated fresh

## Summary
Removed 627 test files that were corrupted with "REMOVED_SYNTAX_ERROR" markers and other systematic issues. These files were non-functional and taking up space without providing any test coverage.

## Test Coverage Areas That Need Recreation

### 1. Agent Tests
- **Business Logic Agents**
  - `test_action_feasibility.py` - Action feasibility validation tests
  - `test_adaptive_workflow_flows.py` - Adaptive workflow flow tests
  - `test_data_helper_clarity.py` - Data helper clarity tests
  - `test_optimization_value.py` - Optimization value tests
  - `test_report_completeness.py` - Report completeness validation
  - `test_triage_decisions.py` - Triage decision logic tests

- **Corpus Admin Agents**
  - `test_agent_comprehensive.py` - Comprehensive agent tests
  - `test_corpus_creation_helpers.py` - Corpus creation helper tests
  - `test_corpus_creation_io.py` - Corpus I/O operations
  - `test_corpus_creation_storage.py` - Corpus storage tests
  - `test_corpus_error_types.py` - Error type handling
  - `test_corpus_indexing_handlers.py` - Indexing handler tests
  - `test_corpus_upload_handlers.py` - Upload handler tests
  - `test_corpus_validation_handlers.py` - Validation handler tests
  - `test_create_value_corpus.py` - Value corpus creation
  - `test_models.py` - Model tests
  - `test_operations.py` - General operations
  - `test_operations_analysis.py` - Operations analysis
  - `test_operations_crud.py` - CRUD operations
  - `test_operations_execution.py` - Operations execution
  - `test_operations_handler.py` - Operations handler
  - `test_parsers.py` - Parser tests
  - `test_suggestion_profiles.py` - Suggestion profile tests
  - `test_validators.py` - Validator tests

- **Flow Tests**
  - `test_adaptive_workflow_flows.py` - Adaptive workflow flows
  - `test_flow_transitions_handoffs.py` - Flow transitions and handoffs
  - `test_insufficient_data_flow.py` - Insufficient data flow handling
  - `test_partial_data_flow.py` - Partial data flow handling
  - `test_sufficient_data_flow.py` - Sufficient data flow handling

- **Interaction Tests**
  - `test_agent_handoffs.py` - Agent handoff logic

- **Supervisor Tests**
  - `test_agent_class_registry.py` - Agent class registry

### 2. High Priority Corrupted Files
These files were completely non-functional with all test methods commented out:

1. `test_uvs_requirements_simple.py` - UVS requirements simple tests
2. `test_triage_sub_agent.py` - Triage sub-agent comprehensive tests
3. `test_websocket_agent_communication_enhanced.py` - WebSocket agent communication
4. `test_triage_sub_agent_index.py` - Triage sub-agent index operations
5. `test_triage_sub_agent_comprehensive.py` - Comprehensive triage tests

### 3. Pattern of Corruption
All deleted files contained one or more of these issues:
- `# REMOVED_SYNTAX_ERROR:` markers throughout the code
- Entire test methods commented out
- Malformed docstrings (5 quotes instead of 3)
- Empty test classes with no functional methods
- Broken import statements

## TODO: Recreation Strategy

### Phase 1: Critical Coverage (Priority 1)
- [ ] WebSocket agent communication tests
- [ ] Agent handoff and registry tests
- [ ] Triage decision logic tests
- [ ] Flow transition tests

### Phase 2: Business Logic (Priority 2)
- [ ] Action feasibility tests
- [ ] Optimization value tests
- [ ] Report completeness tests
- [ ] Data helper clarity tests

### Phase 3: Corpus Operations (Priority 3)
- [ ] Corpus creation and validation
- [ ] Upload and indexing handlers
- [ ] CRUD operations
- [ ] Parser and validator tests

## Notes for Recreation
1. All new tests should follow the current test architecture in `tests/TEST_ARCHITECTURE_VISUAL_OVERVIEW.md`
2. Use real services instead of mocks wherever possible
3. Follow the unified test runner patterns
4. Ensure WebSocket event coverage per `SPEC/learnings/websocket_agent_integration_critical.xml`

## File Deletion Command Record
Files were deleted using pattern matching for:
- Files containing "REMOVED_SYNTAX_ERROR"
- Files with malformed docstrings
- Files with all test methods commented out

Total files deleted: 627