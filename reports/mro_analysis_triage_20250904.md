# MRO Analysis: Triage Module
**Date:** 2025-09-04
**Module:** netra_backend.app.agents.triage_sub_agent

## Current Hierarchy

### TriageSubAgent
```
TriageSubAgent (Main agent class)
  └── BaseAgent (netra_backend.app.agents.base_agent) 
      └── ABC (abc)
          └── object
```

### TriageCore 
```
TriageCore (Standalone core logic - NO inheritance)
  └── object
```

## Method Resolution Paths

### TriageSubAgent Methods (from BaseAgent):
- `store_metadata_result()` → BaseAgent.store_metadata_result
- `store_metadata_batch()` → BaseAgent.store_metadata_batch  
- `get_metadata_value()` → BaseAgent.get_metadata_value
- `execute()` → TriageSubAgent.execute (overrides BaseAgent)
- `process()` → TriageSubAgent.process (likely custom)

### TriageCore Methods (standalone):
- `_init_core_components()` → TriageCore (local)
- `_init_fallback_categories()` → TriageCore (local)
- `extract_and_validate_json()` → TriageCore (local)
- `generate_request_hash()` → TriageCore (local)
- `create_fallback_result()` → TriageCore (local)

## Current File Structure (28 files in triage_sub_agent/)

### Core Components:
1. `agent.py` - Main TriageSubAgent (inherits BaseAgent)
2. `core.py` - TriageCore logic (standalone)
3. `models.py` - Data models
4. `config.py` - Configuration

### Processing Components:
5. `executor.py` - Execution logic
6. `processing.py` - Request processing
7. `result_processor.py` - Result handling
8. `llm_processor.py` - LLM interaction

### Feature Components:
9. `intent_detector.py` / `intent_detection.py` - Intent analysis
10. `entity_extractor.py` / `entity_extraction.py` - Entity extraction  
11. `tool_recommender.py` / `tool_recommendation.py` - Tool suggestions
12. `validator.py` / `validation.py` - Input validation

### Support Components:
13. `prompt_builder.py` - Prompt construction
14. `cache_utils.py` - Caching utilities
15. `execution_helpers.py` - Execution utilities

### Error Handling:
16. `error_recovery.py` - Recovery logic
17. `error_reporting.py` - Error reporting
18. `error_types.py` - Error definitions  
19. `error_core.py` - Core error handling
20. `fallback.py` - Fallback strategies

### Monitoring:
21. `processing_monitoring.py` - Performance monitoring

### Module Setup:
22. `__init__.py` - Module exports

## Refactoring Impact Analysis

### Breaking Changes Expected:
1. **Import paths**: All consumers importing from `triage_sub_agent/*` 
2. **Class names**: TriageCore + TriageSubAgent → UnifiedTriageAgent
3. **Factory pattern**: New instantiation method required
4. **Metadata access**: Direct assignments must use SSOT methods

### Consumers to Update:
- `workflow_orchestrator.py` - References triage agent
- `agent_registry.py` - Registers triage agent  
- `supervisor_agent_modern.py` - May call triage
- Tests in `tests/agents/test_triage_*`
- Integration tests referencing triage

### Performance Considerations:
- Current: 28 file imports, multiple class instantiations
- Target: 1 file import, single factory instantiation
- Expected improvement: Faster import, cleaner memory

## SSOT Consolidation Strategy

### Target Structure:
```
UnifiedTriageAgent (SSOT implementation)
  └── BaseAgent (inherits metadata methods)
      └── ABC
          └── object

UnifiedTriageAgentFactory (per-request isolation)
  └── object
```

### Methods to Preserve:
All core triage logic from TriageCore and TriageSubAgent

### Methods to Eliminate:
Duplicate implementations across helper files

### Metadata Migration Required:
- Fix direct `context.metadata[key] = value` assignments
- Use `self.store_metadata_result()` instead
- Estimated violations: 6+ in triage files