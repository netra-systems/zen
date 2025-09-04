# Additional ErrorContext Fixes Report

## Summary
Found and fixed **7 additional files** with missing `trace_id` and `operation` fields in ErrorContext instantiations.

## Files Fixed

### 1. **netra_backend/app/agents/triage_sub_agent/error_core.py**
- Fixed 4 ErrorContext instantiations
- Added `trace_id` and `operation` fields
- Methods fixed:
  - `_create_intent_error_context`
  - `_create_entity_error_context`
  - `_create_tool_error_context`
  - `create_generic_error_context`

### 2. **netra_backend/app/agents/data_sub_agent/metrics_recovery.py**
- Fixed 1 ErrorContext instantiation
- Added required fields in `_build_error_context_object`

### 3. **netra_backend/app/agents/corpus_admin/corpus_validation_handlers.py**
- Fixed 1 ErrorContext instantiation
- Added required fields in `_build_error_context`

### 4. **netra_backend/app/agents/corpus_admin/corpus_upload_handlers.py**
- Fixed 1 ErrorContext instantiation
- Added required fields in `_build_error_context`

### 5. **netra_backend/app/agents/corpus_admin/corpus_indexing_handlers.py**
- Fixed 1 ErrorContext instantiation
- Added required fields in `_build_error_context`

### 6. **netra_backend/app/agents/data_sub_agent/data_fetching_recovery.py**
- Fixed 1 ErrorContext instantiation
- Added required fields in `_create_error_context`

### 7. **netra_backend/app/agents/data_helper_agent.py** (fixed earlier)
- Previously fixed in initial round

### 8. **netra_backend/app/handlers/example_message_handler.py** (fixed earlier)
- Previously fixed in initial round (2 locations)

## Pattern Identified
All these files were using non-standard field names:
- Using `operation_name` instead of required `operation` field
- Missing `trace_id` field (even though it has default_factory, it's better to be explicit)
- Using optional fields like `agent_name`, `run_id` without the required fields

## Fix Applied
For each ErrorContext instantiation:
```python
# Before:
return ErrorContext(
    agent_name="agent_name",
    operation_name="operation_name",
    run_id=run_id,
    additional_data=data
)

# After:
return ErrorContext(
    trace_id=ErrorContext.generate_trace_id(),
    operation="operation_name",  # Required field
    agent_name="agent_name",      # Optional field
    operation_name="operation_name",  # Kept for backward compatibility
    run_id=run_id,
    additional_data=data
)
```

## Testing
- All 9 tests in `test_error_context_trace_id.py` pass ✅
- No validation errors for missing fields
- Trace IDs are properly generated and unique

## Total Impact
- **11 ErrorContext instantiations fixed** across 7 files
- All required fields now properly provided
- Backward compatibility maintained by keeping optional fields

## Recommendations
1. Update coding standards to require explicit `trace_id` and `operation` fields
2. Consider adding a factory method or builder pattern for ErrorContext
3. Add linting rule to catch missing required fields in ErrorContext
4. Update documentation with correct ErrorContext usage patterns