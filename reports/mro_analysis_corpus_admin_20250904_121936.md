# MRO Analysis: Corpus Admin Module
**Generated:** 2025-09-04T12:19:36.814383
**Files Analyzed:** 30
**Classes Found:** 43

## Current Inheritance Hierarchy

- **agent.CorpusAdminSubAgent** (netra_backend\app\agents\corpus_admin\agent.py:48)
- **corpus_creation_storage.CorpusCreationStorage** (netra_backend\app\agents\corpus_admin\corpus_creation_storage.py:9)
- **corpus_creation_validation.SimpleVal** (netra_backend\app\agents\corpus_admin\corpus_creation_validation.py:49)
- **corpus_error_compensation.CorpusCleanupCompensation** (netra_backend\app\agents\corpus_admin\corpus_error_compensation.py:19)
- **corpus_error_types.CorpusAdminError** (netra_backend\app\agents\corpus_admin\corpus_error_types.py:14)
  - **corpus_error_types.DocumentUploadError** (overrides: __init__) (netra_backend\app\agents\corpus_admin\corpus_error_types.py:39)
  - **corpus_error_types.DocumentValidationError** (overrides: __init__) (netra_backend\app\agents\corpus_admin\corpus_error_types.py:69)
  - **corpus_error_types.IndexingError** (overrides: __init__) (netra_backend\app\agents\corpus_admin\corpus_error_types.py:97)
- **corpus_error_types.CorpusErrorTypes** (netra_backend\app\agents\corpus_admin\corpus_error_types.py:125)
- **corpus_error_types.DocumentUploadError** (netra_backend\app\agents\corpus_admin\corpus_error_types.py:39)
- **corpus_error_types.DocumentValidationError** (netra_backend\app\agents\corpus_admin\corpus_error_types.py:69)
- **corpus_error_types.IndexingError** (netra_backend\app\agents\corpus_admin\corpus_error_types.py:97)
- **corpus_handlers_base.CorpusContextHelper** (netra_backend\app\agents\admin_tool_dispatcher\corpus_handlers_base.py:37)
- **corpus_handlers_base.CorpusHandlerBase** (netra_backend\app\agents\admin_tool_dispatcher\corpus_handlers_base.py:24)
  - **corpus_modern_handlers.ModernCorpusCreateHandler** (netra_backend\app\agents\admin_tool_dispatcher\corpus_modern_handlers.py:26)
  - **corpus_modern_handlers.ModernCorpusExportHandler** (netra_backend\app\agents\admin_tool_dispatcher\corpus_modern_handlers.py:175)
  - **corpus_modern_handlers.ModernCorpusOptimizationHandler** (netra_backend\app\agents\admin_tool_dispatcher\corpus_modern_handlers.py:120)
  - **corpus_modern_handlers.ModernCorpusSyntheticHandler** (netra_backend\app\agents\admin_tool_dispatcher\corpus_modern_handlers.py:73)
  - **corpus_modern_handlers.ModernCorpusValidationHandler** (netra_backend\app\agents\admin_tool_dispatcher\corpus_modern_handlers.py:220)
- **corpus_handlers_base.CorpusResponseConverter** (netra_backend\app\agents\admin_tool_dispatcher\corpus_handlers_base.py:82)
- **corpus_indexing_handlers.CorpusIndexingHandlers** (netra_backend\app\agents\corpus_admin\corpus_indexing_handlers.py:389)
- **corpus_indexing_handlers.IndexingErrorHandler** (netra_backend\app\agents\corpus_admin\corpus_indexing_handlers.py:16)
- **corpus_models.CorpusToolRequest** (netra_backend\app\agents\admin_tool_dispatcher\corpus_models.py:26)
- **corpus_models.CorpusToolResponse** (netra_backend\app\agents\admin_tool_dispatcher\corpus_models.py:34)
- **corpus_models.CorpusToolType** (netra_backend\app\agents\admin_tool_dispatcher\corpus_models.py:14)
- **corpus_modern_handlers.ModernCorpusCreateHandler** (netra_backend\app\agents\admin_tool_dispatcher\corpus_modern_handlers.py:26)
- **corpus_modern_handlers.ModernCorpusExportHandler** (netra_backend\app\agents\admin_tool_dispatcher\corpus_modern_handlers.py:175)
- **corpus_modern_handlers.ModernCorpusOptimizationHandler** (netra_backend\app\agents\admin_tool_dispatcher\corpus_modern_handlers.py:120)
- **corpus_modern_handlers.ModernCorpusSyntheticHandler** (netra_backend\app\agents\admin_tool_dispatcher\corpus_modern_handlers.py:73)
- **corpus_modern_handlers.ModernCorpusValidationHandler** (netra_backend\app\agents\admin_tool_dispatcher\corpus_modern_handlers.py:220)
- **corpus_tool_handlers.CorpusToolHandlers** (netra_backend\app\agents\admin_tool_dispatcher\corpus_tool_handlers.py:31)
- **corpus_tools.CorpusAdminTools** (netra_backend\app\agents\admin_tool_dispatcher\corpus_tools.py:32)
- **corpus_upload_handlers.CorpusUploadHandlers** (netra_backend\app\agents\corpus_admin\corpus_upload_handlers.py:289)
- **corpus_upload_handlers.UploadErrorHandler** (netra_backend\app\agents\corpus_admin\corpus_upload_handlers.py:16)
- **corpus_validation_handlers.CorpusValidationHandlers** (netra_backend\app\agents\corpus_admin\corpus_validation_handlers.py:363)
- **corpus_validation_handlers.DocumentValidationErrorHandler** (netra_backend\app\agents\corpus_admin\corpus_validation_handlers.py:18)
- **corpus_validators.CorpusValidators** (netra_backend\app\agents\admin_tool_dispatcher\corpus_validators.py:13)
- **create_value_corpus.CreateValueCorpus** (netra_backend\app\agents\corpus_admin\value_based_corpus\create_value_corpus.py:17)
- **models.CorpusMetadata** (netra_backend\app\agents\corpus_admin\models.py:36)
- **models.CorpusOperation** (netra_backend\app\agents\corpus_admin\models.py:15)
- **models.CorpusOperationRequest** (netra_backend\app\agents\corpus_admin\models.py:51)
- **models.CorpusOperationResult** (netra_backend\app\agents\corpus_admin\models.py:61)
- **models.CorpusStatistics** (netra_backend\app\agents\corpus_admin\models.py:75)
- **models.CorpusType** (netra_backend\app\agents\corpus_admin\models.py:27)
- **operations_analysis.CorpusAnalysisOperations** (netra_backend\app\agents\corpus_admin\operations_analysis.py:24)
- **operations_crud.CorpusCRUDOperations** (netra_backend\app\agents\corpus_admin\operations_crud.py:26)
- **operations_execution.CorpusExecutionHelper** (netra_backend\app\agents\corpus_admin\operations_execution.py:22)
- **operations_handler.CorpusOperationHandler** (netra_backend\app\agents\corpus_admin\operations_handler.py:25)
- **parsers.CorpusRequestParser** (netra_backend\app\agents\corpus_admin\parsers.py:30)
- **validators.CorpusApprovalValidator** (netra_backend\app\agents\corpus_admin\validators.py:17)
- **value_corpus_validation.ValueCorpusValidator** (netra_backend\app\agents\corpus_admin\value_based_corpus\value_corpus_validation.py:19)

## Method Resolution Analysis


### Handlers

- **corpus_handlers_base.CorpusContextHelper**
  - Methods: create_context_from_request, _create_user_context_from_request, _build_execution_context
- **corpus_handlers_base.CorpusHandlerBase**
  - Methods: setup_reliability_components
- **corpus_handlers_base.CorpusResponseConverter**
  - Methods: convert_result_to_response, _create_success_response, _create_error_response
- **corpus_indexing_handlers.CorpusIndexingHandlers**
  - Methods: __init__, process, process_invalid, get_handler
- **corpus_indexing_handlers.IndexingErrorHandler**
  - Methods: __init__, _init_index_alternatives, _create_indexing_error, _create_indexing_error_context, _build_error_context...
- **corpus_modern_handlers.ModernCorpusCreateHandler**
  - Methods: __init__, _validate_corpus_creation_params, _format_creation_result
  - Inherits from: CorpusHandlerBase
- **corpus_modern_handlers.ModernCorpusExportHandler**
  - Methods: __init__, _format_export_result
  - Inherits from: CorpusHandlerBase
- **corpus_modern_handlers.ModernCorpusOptimizationHandler**
  - Methods: __init__, _collect_optimizations, _add_if_enabled, _format_optimization_result
  - Inherits from: CorpusHandlerBase
- **corpus_modern_handlers.ModernCorpusSyntheticHandler**
  - Methods: __init__, _validate_generation_request, _format_generation_result
  - Inherits from: CorpusHandlerBase
- **corpus_modern_handlers.ModernCorpusValidationHandler**
  - Methods: __init__, _perform_integrity_checks, _format_validation_result
  - Inherits from: CorpusHandlerBase
- **corpus_tool_handlers.CorpusToolHandlers**
  - Methods: __init__, _initialize_modern_handlers, _build_delete_response, _build_update_response, _build_analysis_response...
- **corpus_upload_handlers.CorpusUploadHandlers**
  - Methods: __init__, process, process_invalid, get_handler
- **corpus_upload_handlers.UploadErrorHandler**
  - Methods: __init__, _init_file_size_limits, _create_upload_error_context, _build_error_context, _build_upload_error_data...
- **corpus_validation_handlers.CorpusValidationHandlers**
  - Methods: __init__, process, process_invalid, get_handler
- **corpus_validation_handlers.DocumentValidationErrorHandler**
  - Methods: __init__, _prepare_validation_error, _create_error_tuple, _create_validation_error, _create_validation_error_context...
- **operations_handler.CorpusOperationHandler**
  - Methods: __init__, _is_crud_operation, _is_analysis_operation, _handle_operation_error, _create_unsupported_operation_result...

### Validators

- **corpus_validators.CorpusValidators**
  - Methods: get_validator_registry
- **validators.CorpusApprovalValidator**
  - Methods: __init__, generate_approval_message, _is_delete_operation, _has_explicit_approval_request, _is_large_update_operation...
- **value_corpus_validation.ValueCorpusValidator**
  - Methods: validate_entry, validate_metadata
  - Inherits from: BaseValidator

### Operations

- **models.CorpusOperation**
  - Methods: 
  - Inherits from: str, Enum
- **models.CorpusOperationRequest**
  - Methods: 
  - Inherits from: BaseModel
- **models.CorpusOperationResult**
  - Methods: 
  - Inherits from: BaseModel
- **operations_analysis.CorpusAnalysisOperations**
  - Methods: __init__, _get_analysis_operation_mapping, _build_export_result_params, _get_base_export_params, _get_export_data_params...
- **operations_crud.CorpusCRUDOperations**
  - Methods: __init__, _get_operation_mapping, _build_update_result_params, _get_base_update_params, _get_update_operation_params...
- **operations_execution.CorpusExecutionHelper**
  - Methods: __init__, _create_empty_search_result, _create_empty_analysis_result, _get_base_analysis_metrics, _build_tool_parameters...

### Models

- **corpus_models.CorpusToolRequest**
  - Methods: 
  - Inherits from: BaseModel
- **corpus_models.CorpusToolResponse**
  - Methods: 
  - Inherits from: BaseModel
- **corpus_models.CorpusToolType**
  - Methods: 
  - Inherits from: str, Enum
- **models.CorpusMetadata**
  - Methods: 
  - Inherits from: BaseModel
- **models.CorpusStatistics**
  - Methods: 
  - Inherits from: BaseModel
- **models.CorpusType**
  - Methods: 
  - Inherits from: str, Enum

### Others

- **agent.CorpusAdminSubAgent**
  - Methods: __init__, _init_base_agents, _initialize_components, _init_modern_execution_infrastructure, _create_reliability_manager...
  - Inherits from: BaseAgent
- **corpus_creation_storage.CorpusCreationStorage**
  - Methods: __init__, process, process_invalid, set_handler
- **corpus_creation_validation.SimpleVal**
  - Methods: validate_entry
- **corpus_error_compensation.CorpusCleanupCompensation**
  - Methods: __init__, can_compensate
  - Inherits from: CompensationAction
- **corpus_error_types.CorpusAdminError**
  - Methods: __init__, _init_parent_error
  - Inherits from: AgentError
- **corpus_error_types.CorpusErrorTypes**
  - Methods: __init__, process, process_invalid, get_error_class, create_error
- **corpus_error_types.DocumentUploadError**
  - Methods: __init__, _build_upload_resource_info
  - Inherits from: CorpusAdminError
- **corpus_error_types.DocumentValidationError**
  - Methods: __init__, _build_validation_resource_info
  - Inherits from: CorpusAdminError
- **corpus_error_types.IndexingError**
  - Methods: __init__, _build_indexing_resource_info
  - Inherits from: CorpusAdminError
- **corpus_tools.CorpusAdminTools**
  - Methods: __init__, _initialize_tool_registry, _build_tool_mapping, _create_error_response, get_available_tools...
- **create_value_corpus.CreateValueCorpus**
  - Methods: __init__, process, process_invalid, create_entry, save_corpus_data...
- **parsers.CorpusRequestParser**
  - Methods: __init__, _process_llm_response, _build_parsing_prompt, _get_base_prompt_template, _get_schema_section...

## Potential Issues and Refactoring Opportunities


### Multiple Inheritance Detected
- **models.CorpusOperation** inherits from: str, Enum
- **models.CorpusType** inherits from: str, Enum
- **corpus_models.CorpusToolType** inherits from: str, Enum

## Refactoring Impact Analysis

### Breaking Changes Expected
- All imports from `netra_backend.app.agents.corpus_admin.*` will need updating
- All imports from `netra_backend.app.agents.admin_tool_dispatcher.corpus*` will need updating
- Tool registration patterns may need adjustment
- WebSocket event handlers for corpus operations need validation

### Migration Strategy
1. Create `netra_backend/app/admin/corpus/` directory
2. Implement `UnifiedCorpusAdminFactory` with user isolation
3. Consolidate all corpus operations into `UnifiedCorpusAdmin` class
4. Implement factory pattern for multi-user isolation
5. Update all imports across the codebase
6. Remove legacy files after validation

## Files to Consolidate

- `netra_backend\app\agents\admin_tool_dispatcher\corpus_handlers_base.py`
- `netra_backend\app\agents\admin_tool_dispatcher\corpus_models.py`
- `netra_backend\app\agents\admin_tool_dispatcher\corpus_modern_handlers.py`
- `netra_backend\app\agents\admin_tool_dispatcher\corpus_tool_handlers.py`
- `netra_backend\app\agents\admin_tool_dispatcher\corpus_tools.py`
- `netra_backend\app\agents\admin_tool_dispatcher\corpus_validators.py`
- `netra_backend\app\agents\corpus_admin\__init__.py`
- `netra_backend\app\agents\corpus_admin\agent.py`
- `netra_backend\app\agents\corpus_admin\corpus_creation_helpers.py`
- `netra_backend\app\agents\corpus_admin\corpus_creation_io.py`
- `netra_backend\app\agents\corpus_admin\corpus_creation_storage.py`
- `netra_backend\app\agents\corpus_admin\corpus_creation_validation.py`
- `netra_backend\app\agents\corpus_admin\corpus_error_compensation.py`
- `netra_backend\app\agents\corpus_admin\corpus_error_types.py`
- `netra_backend\app\agents\corpus_admin\corpus_indexing_handlers.py`
- `netra_backend\app\agents\corpus_admin\corpus_upload_handlers.py`
- `netra_backend\app\agents\corpus_admin\corpus_validation_handlers.py`
- `netra_backend\app\agents\corpus_admin\models.py`
- `netra_backend\app\agents\corpus_admin\operations.py`
- `netra_backend\app\agents\corpus_admin\operations_analysis.py`
- `netra_backend\app\agents\corpus_admin\operations_crud.py`
- `netra_backend\app\agents\corpus_admin\operations_execution.py`
- `netra_backend\app\agents\corpus_admin\operations_handler.py`
- `netra_backend\app\agents\corpus_admin\parsers.py`
- `netra_backend\app\agents\corpus_admin\suggestion_profiles.py`
- `netra_backend\app\agents\corpus_admin\validators.py`
- `netra_backend\app\agents\corpus_admin\value_based_corpus\create_value_corpus.py`
- `netra_backend\app\agents\corpus_admin\value_based_corpus\value_corpus_to_xml.py`
- `netra_backend\app\agents\corpus_admin\value_based_corpus\value_corpus_validation.py`
- `netra_backend\app\agents\corpus_admin_sub_agent.py`