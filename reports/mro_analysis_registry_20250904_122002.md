# Registry Pattern MRO Analysis Report

Generated: 2025-09-04T19:20:02.901286+00:00

## Summary
- Total Registry Classes Found: 48
- Unique File Locations: 42

### Registry Categories:
- Agent Registries: 20
- Tool Registries: 5
- Service Registries: 3
- Other Registries: 20

## Detailed Registry Analysis

### Agent Registries

#### AgentClassRegistry
- **Location**: `netra_backend\app\agents\supervisor\agent_class_registry.py:56`
- **Base Classes**: None
- **Decorators**: None
- **Total Methods**: 16
- **Core Registry Methods**: ['register', 'get', 'list', 'has']
- **Thread Safety**: Unknown
- **Factory Support**: No
- **Key Methods**:
  - `__init__(self)`
  - `register(self, name, agent_class...)`
  - `freeze(self)`
  - `get_agent_class(self, name)`
  - `get_agent_info(self, name)`
  - `list_agent_names(self)`
  - `get_all_agent_classes(self)`
  - `has_agent_class(self, name)`
  - `get_registry_stats(self)`
  - `validate_dependencies(self)`

#### AgentExecutionRegistry
- **Location**: `tests\mission_critical\test_singleton_removal_phase2.py:105`
- **Base Classes**: None
- **Decorators**: None
- **Total Methods**: 1
- **Core Registry Methods**: []
- **Thread Safety**: Unknown
- **Factory Support**: No

#### AgentRecoveryRegistry
- **Location**: `netra_backend\app\core\agent_recovery_registry.py:26`
- **Base Classes**: None
- **Decorators**: None
- **Total Methods**: 24
- **Core Registry Methods**: ['register', 'get', 'list']
- **Thread Safety**: Unknown
- **Factory Support**: Yes
- **Key Methods**:
  - `__init__(self)`
  - `register_strategy(self, agent_type, strategy)`
  - `register_config(self, agent_type, config)`
  - `get_strategy(self, agent_type)`
  - `get_config(self, agent_type)`
  - `list_registered_agents(self)`
  - `get_registry_status(self)`
  - `validate_registry(self)`

#### AgentRegistry
- **Location**: `netra_backend\app\agents\supervisor\agent_registry.py:39`
- **Base Classes**: None
- **Decorators**: None
- **Total Methods**: 32
- **Core Registry Methods**: ['register', 'get', 'list', 'remove']
- **Thread Safety**: Unknown
- **Factory Support**: Yes
- **Key Methods**:
  - `__init__(self, llm_manager, tool_dispatcher)`
  - `register_default_agents(self)`
  - `register(self, name, agent)`
  - `get(self, name)`
  - `get_registry_health(self)`
  - `remove_agent(self, name)`
  - `list_agents(self)`
  - `get_all_agents(self)`
  - `set_websocket_manager(self, websocket_manager)`
  - `set_websocket_bridge(self, bridge)`

#### AgentToolConfigRegistry
- **Location**: `netra_backend\app\services\tool_registry.py:16`
- **Base Classes**: None
- **Decorators**: None
- **Total Methods**: 19
- **Core Registry Methods**: ['register', 'get']
- **Thread Safety**: Unknown
- **Factory Support**: No
- **Key Methods**:
  - `__init__(self, db_session)`
  - `get_tools(self, tool_names)`
  - `get_all_tools(self)`
  - `register_tool(self, category, tool)`
  - `validate_tool_interface(self, tool)`
  - `validate_metadata(self, metadata)`
  - `validate_tool_security(self, tool)`
  - `validate_tool_performance(self, tool)`
  - `measure_tool_performance(self)`
  - `set_compatibility_matrix(self, matrix)`

#### AgentTypeRegistry
- **Location**: `netra_backend\app\schemas\strict_types.py:235`
- **Base Classes**: None
- **Decorators**: None
- **Total Methods**: 2
- **Core Registry Methods**: ['get']
- **Thread Safety**: Unknown
- **Factory Support**: No
- **Key Methods**:
  - `get_result_type(cls, agent_name)`
  - `validate_result_type(cls, agent_name, result)`

#### MockAgentRegistry
- **Location**: `netra_backend\tests\agents\agent_system_test_helpers.py:244`
- **Base Classes**: None
- **Decorators**: None
- **Total Methods**: 1
- **Core Registry Methods**: ['get']
- **Thread Safety**: Unknown
- **Factory Support**: No
- **Key Methods**:
  - `get_agent(self, name)`

#### RegistryTestAgent
- **Location**: `tests\mission_critical\test_websocket_bridge_integration.py:268`
- **Base Classes**: BaseAgent
- **Decorators**: None
- **Total Methods**: 1
- **Core Registry Methods**: []
- **Thread Safety**: Unknown
- **Factory Support**: No
- **Key Methods**:
  - `__init__(self, llm_manager, tool_dispatcher)`

#### TestAgentClassRegistry
- **Location**: `tests\netra_backend\agents\test_agent_isolation.py:76`
- **Base Classes**: None
- **Decorators**: None
- **Total Methods**: 8
- **Core Registry Methods**: []
- **Thread Safety**: Unknown
- **Factory Support**: No
- **Key Methods**:
  - `test_registry_initialization(self)`
  - `test_agent_class_registration(self)`
  - `test_duplicate_registration_same_class(self)`
  - `test_duplicate_registration_different_class(self)`
  - `test_freeze_functionality(self)`
  - `test_thread_safety(self)`
  - `test_dependency_validation(self)`
  - `test_immutability_after_freeze(self)`

#### TestAgentClassRegistryIntegration
- **Location**: `netra_backend\tests\agents\supervisor\test_agent_class_registry.py:404`
- **Base Classes**: None
- **Decorators**: None
- **Total Methods**: 2
- **Core Registry Methods**: []
- **Thread Safety**: Unknown
- **Factory Support**: No
- **Key Methods**:
  - `test_full_lifecycle(self)`
  - `test_error_scenarios(self)`

#### TestAgentClassRegistryIsolation
- **Location**: `tests\integration\test_split_architecture_integration.py:416`
- **Base Classes**: None
- **Decorators**: None
- **Total Methods**: 0
- **Core Registry Methods**: []
- **Thread Safety**: Unknown
- **Factory Support**: No

#### TestAgentClassRegistryPerformance
- **Location**: `netra_backend\tests\agents\supervisor\test_agent_class_registry.py:475`
- **Base Classes**: None
- **Decorators**: None
- **Total Methods**: 2
- **Core Registry Methods**: []
- **Thread Safety**: Unknown
- **Factory Support**: No
- **Key Methods**:
  - `test_large_registry_performance(self)`
  - `test_concurrent_access_performance(self)`

#### TestAgentClassRegistryThreadSafety
- **Location**: `netra_backend\tests\agents\supervisor\test_agent_class_registry.py:288`
- **Base Classes**: None
- **Decorators**: None
- **Total Methods**: 2
- **Core Registry Methods**: []
- **Thread Safety**: Unknown
- **Factory Support**: No
- **Key Methods**:
  - `test_concurrent_reads_after_freeze(self)`
  - `test_registration_thread_safety(self)`

#### TestAgentRegistryAdvancedIntegration
- **Location**: `netra_backend\tests\integration\test_agent_registry_initialization_validation.py:432`
- **Base Classes**: None
- **Decorators**: integration, websocket, database
- **Total Methods**: 0
- **Core Registry Methods**: []
- **Thread Safety**: Unknown
- **Factory Support**: No

#### TestAgentRegistryIdempotency
- **Location**: `netra_backend\tests\unit\test_agent_registry_idempotency.py:15`
- **Base Classes**: None
- **Decorators**: None
- **Total Methods**: 11
- **Core Registry Methods**: ['register', 'get', 'list']
- **Thread Safety**: Unknown
- **Factory Support**: No
- **Key Methods**:
  - `mock_llm_manager(self)`
  - `mock_tool_dispatcher(self)`
  - `agent_registry(self, mock_llm_manager, mock_tool_dispatcher)`
  - `test_register_default_agents_idempotency(self, agent_registry)`
  - `test_register_method_prevents_duplicates(self, agent_registry)`
  - `test_agents_registered_flag(self, agent_registry)`
  - `test_concurrent_registration_safety(self, agent_registry)`
  - `test_websocket_manager_assignment(self, agent_registry)`
  - `test_get_and_list_methods(self, agent_registry)`
  - `test_logging_behavior(self, mock_logger, agent_registry)`

#### TestAgentRegistryInitializationValidation
- **Location**: `netra_backend\tests\integration\test_agent_registry_initialization_validation.py:60`
- **Base Classes**: None
- **Decorators**: integration, agent_registry, websocket
- **Total Methods**: 0
- **Core Registry Methods**: []
- **Thread Safety**: Unknown
- **Factory Support**: No

#### TestAgentRegistryMigration
- **Location**: `tests\netra_backend\agents\test_agent_isolation.py:521`
- **Base Classes**: None
- **Decorators**: None
- **Total Methods**: 4
- **Core Registry Methods**: ['get']
- **Thread Safety**: Unknown
- **Factory Support**: No
- **Key Methods**:
  - `legacy_registry(self)`
  - `test_get_infrastructure_registry(self, legacy_registry)`
  - `test_migration_to_new_architecture(self, legacy_registry)`
  - `test_deprecation_warnings(self)`

#### TestAgentRegistryPlaceholders
- **Location**: `tests\mission_critical\test_eliminate_placeholder_values.py:249`
- **Base Classes**: None
- **Decorators**: None
- **Total Methods**: 1
- **Core Registry Methods**: []
- **Thread Safety**: Unknown
- **Factory Support**: No
- **Key Methods**:
  - `test_scan_agent_registry_source_for_placeholders(self)`

#### TestUnifiedAgentRegistry
- **Location**: `tests\integration\test_agent_consolidation.py:48`
- **Base Classes**: BaseTestCase
- **Decorators**: None
- **Total Methods**: 10
- **Core Registry Methods**: []
- **Thread Safety**: Unknown
- **Factory Support**: Yes
- **Key Methods**:
  - `setUp(self)`
  - `test_agent_class_registration(self)`
  - `test_execution_order_enforcement(self)`
  - `test_validate_execution_order(self)`
  - `test_agent_discovery(self)`
  - `test_category_filtering(self)`
  - `test_registry_freeze(self)`
  - `test_create_agent_instance(self)`
  - `test_thread_safety(self)`
  - `test_global_singleton(self)`

#### UnifiedAgentRegistry
- **Location**: `netra_backend\app\agents\supervisor\unified_agent_registry.py:54`
- **Base Classes**: None
- **Decorators**: None
- **Total Methods**: 13
- **Core Registry Methods**: ['register', 'get']
- **Thread Safety**: Unknown
- **Factory Support**: Yes
- **Key Methods**:
  - `__init__(self)`
  - `register_agent_class(self, agent_type, agent_class...)`
  - `get_agent_class(self, agent_type)`
  - `get_agent_metadata(self, agent_type)`
  - `create_agent_instance(self, agent_type, llm_manager...)`
  - `discover_agents(self, force_refresh)`
  - `get_agents_by_category(self, category)`
  - `get_execution_order(self)`
  - `validate_execution_order(self, agent_sequence)`
  - `freeze(self)`

### Tool Registries

#### TestUnifiedToolRegistry
- **Location**: `netra_backend\tests\unit\test_unified_tool_registry.py:21`
- **Base Classes**: None
- **Decorators**: None
- **Total Methods**: 16
- **Core Registry Methods**: ['register', 'get', 'list', 'clear']
- **Thread Safety**: Unknown
- **Factory Support**: No
- **Key Methods**:
  - `registry(self)`
  - `sample_tool(self)`
  - `sample_handler(self)`
  - `test_register_tool(self, registry, sample_tool)`
  - `test_register_tool_with_handler(self, registry, sample_tool...)`
  - `test_get_tool(self, registry, sample_tool)`
  - `test_get_tool_not_found(self, registry)`
  - `test_list_tools_empty(self, registry)`
  - `test_list_tools_with_category_filter(self, registry)`
  - `test_get_tool_categories_empty(self, registry)`

#### ToolRegistry
- **Location**: `netra_backend\app\agents\tool_dispatcher_registry.py:12`
- **Base Classes**: ToolRegistryInterface
- **Decorators**: None
- **Total Methods**: 15
- **Core Registry Methods**: ['register', 'get', 'list', 'remove', 'has', 'clear']
- **Thread Safety**: Unknown
- **Factory Support**: No
- **Key Methods**:
  - `__init__(self)`
  - `register_tools(self, tools)`
  - `register_tool(self, tool)`
  - `has_tool(self, tool_name)`
  - `get_tool(self, tool_name)`
  - `list_tools(self)`
  - `remove_tool(self, tool_name)`
  - `clear_tools(self)`
  - `get_tool_count(self)`

#### ToolRegistryInterface
- **Location**: `netra_backend\app\schemas\tool.py:123`
- **Base Classes**: ABC
- **Decorators**: None
- **Total Methods**: 2
- **Core Registry Methods**: ['register', 'get']
- **Thread Safety**: Unknown
- **Factory Support**: No
- **Key Methods**:
  - `register_tool(self, tool)`
  - `get_tool(self, name)`

#### ToolRegistrySnapshot
- **Location**: `netra_backend\app\agents\tool_registry_unified.py:510`
- **Base Classes**: None
- **Decorators**: None
- **Total Methods**: 7
- **Core Registry Methods**: ['get', 'list', 'has']
- **Thread Safety**: Unknown
- **Factory Support**: No
- **Key Methods**:
  - `__init__(self, tools, snapshot_time...)`
  - `tools(self)`
  - `has_tool(self, tool_name)`
  - `get_tool(self, tool_name)`
  - `list_tools(self)`
  - `get_tool_count(self)`
  - `to_dict(self)`

#### UnifiedToolRegistry
- **Location**: `netra_backend\app\services\unified_tool_registry\registry.py:18`
- **Base Classes**: None
- **Decorators**: None
- **Total Methods**: 7
- **Core Registry Methods**: ['register', 'get', 'list', 'clear']
- **Thread Safety**: Unknown
- **Factory Support**: No
- **Key Methods**:
  - `__init__(self, permission_service)`
  - `register_tool(self, tool, handler)`
  - `get_tool(self, tool_id)`
  - `list_tools(self, category)`
  - `check_permission(self, tool_id, user_id...)`
  - `clear(self)`
  - `get_tool_categories(self)`

### Service Registries

#### GCPServiceRegistry
- **Location**: `test_framework\gcp_integration\base.py:189`
- **Base Classes**: None
- **Decorators**: None
- **Total Methods**: 1
- **Core Registry Methods**: ['get']
- **Thread Safety**: Unknown
- **Factory Support**: No
- **Key Methods**:
  - `get_service_endpoint(cls, service, project_id...)`

#### MockServiceRegistry
- **Location**: `netra_backend\tests\integration\service_mesh_fixtures.py:46`
- **Base Classes**: None
- **Decorators**: None
- **Total Methods**: 2
- **Core Registry Methods**: ['get']
- **Thread Safety**: Unknown
- **Factory Support**: No
- **Key Methods**:
  - `__init__(self)`
  - `get_all_services(self)`

#### ServiceRegistry
- **Location**: `tests\e2e\test_critical_cold_start_initialization.py:552`
- **Base Classes**: None
- **Decorators**: None
- **Total Methods**: 1
- **Core Registry Methods**: []
- **Thread Safety**: Unknown
- **Factory Support**: No
- **Key Methods**:
  - `__init__(self)`

### Other Registries

#### CompensationRegistry
- **Location**: `netra_backend\app\services\transaction_manager\compensation.py:19`
- **Base Classes**: None
- **Decorators**: None
- **Total Methods**: 3
- **Core Registry Methods**: ['register', 'get']
- **Thread Safety**: Unknown
- **Factory Support**: No
- **Key Methods**:
  - `__init__(self)`
  - `register(self, operation_type, handler)`
  - `get_handler(self, operation_type)`

#### CoordinationTestRegistry
- **Location**: `netra_backend\tests\integration\coordination\shared_fixtures.py:137`
- **Base Classes**: None
- **Decorators**: None
- **Total Methods**: 1
- **Core Registry Methods**: []
- **Thread Safety**: Unknown
- **Factory Support**: No
- **Key Methods**:
  - `__init__(self)`

#### CustomMetricsRegistry
- **Location**: `netra_backend\tests\integration\critical_paths\test_custom_metrics_registration.py:588`
- **Base Classes**: None
- **Decorators**: None
- **Total Methods**: 0
- **Core Registry Methods**: []
- **Thread Safety**: Unknown
- **Factory Support**: No

#### DatabaseRecoveryRegistry
- **Location**: `netra_backend\app\core\database_recovery_strategies.py:512`
- **Base Classes**: None
- **Decorators**: None
- **Total Methods**: 3
- **Core Registry Methods**: ['get']
- **Thread Safety**: Unknown
- **Factory Support**: No
- **Key Methods**:
  - `__init__(self)`
  - `get_manager(self, db_type)`
  - `get_global_status(self)`

#### DependencyRegistry
- **Location**: `netra_backend\tests\integration\critical_paths\test_agent_dependency_resolution.py:118`
- **Base Classes**: None
- **Decorators**: None
- **Total Methods**: 7
- **Core Registry Methods**: ['register', 'get', 'has']
- **Thread Safety**: Unknown
- **Factory Support**: No
- **Key Methods**:
  - `__init__(self)`
  - `register(self, metadata)`
  - `register_alias(self, alias, target)`
  - `get_canonical_name(self, name)`
  - `get_metadata(self, name)`
  - `get_all_dependencies(self)`
  - `has_dependency(self, name)`

#### ExecutionRegistry
- **Location**: `netra_backend\app\agents\execution_tracking\registry.py:80`
- **Base Classes**: None
- **Decorators**: None
- **Total Methods**: 6
- **Core Registry Methods**: []
- **Thread Safety**: Unknown
- **Factory Support**: No
- **Key Methods**:
  - `__init__(self, cleanup_interval_seconds)`

#### HealthRegistry
- **Location**: `netra_backend\app\services\health_registry.py:10`
- **Base Classes**: None
- **Decorators**: None
- **Total Methods**: 5
- **Core Registry Methods**: ['register', 'get']
- **Thread Safety**: Unknown
- **Factory Support**: No
- **Key Methods**:
  - `__init__(self)`
  - `register_service(self, service_name, health_service)`
  - `get_service(self, service_name)`
  - `get_default_service(self)`
  - `get_all_services(self)`

#### MetricRegistry
- **Location**: `netra_backend\app\monitoring\metrics_exporter.py:53`
- **Base Classes**: None
- **Decorators**: None
- **Total Methods**: 8
- **Core Registry Methods**: ['register', 'get', 'clear']
- **Thread Safety**: Unknown
- **Factory Support**: No
- **Key Methods**:
  - `__init__(self, max_samples_per_metric)`
  - `register_metric(self, metric)`
  - `record_value(self, metric_name, value...)`
  - `get_metric_samples(self, metric_name)`
  - `get_latest_value(self, metric_name)`
  - `get_all_metrics(self)`
  - `clear_old_samples(self, retention_seconds)`
  - `get_stats(self)`

#### MockRegistry
- **Location**: `test_framework\ssot\mocks.py:30`
- **Base Classes**: None
- **Decorators**: None
- **Total Methods**: 6
- **Core Registry Methods**: ['register', 'get']
- **Thread Safety**: Unknown
- **Factory Support**: No
- **Key Methods**:
  - `__init__(self)`
  - `register_mock(self, name, mock_obj...)`
  - `get_mock(self, mock_id)`
  - `record_call(self, mock_id, method...)`
  - `get_call_history(self, mock_id)`
  - `cleanup_all(self)`

#### MockRouteRegistry
- **Location**: `test_framework\fixtures\routes.py:336`
- **Base Classes**: None
- **Decorators**: None
- **Total Methods**: 3
- **Core Registry Methods**: []
- **Thread Safety**: Unknown
- **Factory Support**: Yes
- **Key Methods**:
  - `__init__(self)`
  - `create_router(self, prefix)`
  - `add_middleware(self, middleware)`

#### ObservabilityHookRegistry
- **Location**: `netra_backend\app\agents\supervisor\observability_integration.py:18`
- **Base Classes**: None
- **Decorators**: None
- **Total Methods**: 7
- **Core Registry Methods**: ['register', 'get', 'clear']
- **Thread Safety**: Unknown
- **Factory Support**: No
- **Key Methods**:
  - `__init__(self)`
  - `register_hook(self, event_type, hook_func)`
  - `trigger_hooks(self, event_type)`
  - `get_registered_hooks(self)`
  - `clear_hooks(self, event_type)`

#### RegistryAnalyzer
- **Location**: `scripts\generate_registry_mro_report.py:24`
- **Base Classes**: NodeVisitor
- **Decorators**: None
- **Total Methods**: 3
- **Core Registry Methods**: ['get']
- **Thread Safety**: Unknown
- **Factory Support**: No
- **Key Methods**:
  - `__init__(self)`
  - `visit_ClassDef(self, node)`

#### RegistryConfig
- **Location**: `netra_backend\app\services\thread_run_registry.py:49`
- **Base Classes**: None
- **Decorators**: dataclass
- **Total Methods**: 0
- **Core Registry Methods**: []
- **Thread Safety**: Unknown
- **Factory Support**: No

#### TestExecutionRegistry
- **Location**: `tests\unit\test_execution_tracking.py:40`
- **Base Classes**: None
- **Decorators**: None
- **Total Methods**: 0
- **Core Registry Methods**: []
- **Thread Safety**: Unknown
- **Factory Support**: No

#### TestGlobalRegistry
- **Location**: `netra_backend\tests\agents\supervisor\test_agent_class_registry.py:378`
- **Base Classes**: None
- **Decorators**: None
- **Total Methods**: 2
- **Core Registry Methods**: []
- **Thread Safety**: Unknown
- **Factory Support**: Yes
- **Key Methods**:
  - `test_singleton_behavior(self)`
  - `test_create_test_registry(self)`

#### TestRegistryOperations
- **Location**: `tests\mission_critical\test_websocket_bridge_thread_resolution_basic.py:261`
- **Base Classes**: None
- **Decorators**: None
- **Total Methods**: 0
- **Core Registry Methods**: []
- **Thread Safety**: Unknown
- **Factory Support**: No

#### TestThreadRegistryOperations
- **Location**: `tests\mission_critical\test_websocket_bridge_thread_resolution.py:326`
- **Base Classes**: None
- **Decorators**: None
- **Total Methods**: 0
- **Core Registry Methods**: []
- **Thread Safety**: Unknown
- **Factory Support**: No

#### ThreadRunRegistry
- **Location**: `netra_backend\app\services\thread_run_registry.py:68`
- **Base Classes**: None
- **Decorators**: None
- **Total Methods**: 5
- **Core Registry Methods**: []
- **Thread Safety**: Unknown
- **Factory Support**: No
- **Key Methods**:
  - `__init__(self, config)`

#### UnifiedResilienceRegistry
- **Location**: `netra_backend\app\core\resilience\registry.py:51`
- **Base Classes**: None
- **Decorators**: None
- **Total Methods**: 23
- **Core Registry Methods**: ['register', 'get']
- **Thread Safety**: Unknown
- **Factory Support**: Yes
- **Key Methods**:
  - `__init__(self)`
  - `register_service(self, service_name, policy)`
  - `get_service_status(self, service_name)`
  - `get_all_services_status(self)`
  - `update_service_policy(self, service_name, policy_updates)`
  - `enable_service(self, service_name)`
  - `disable_service(self, service_name)`
  - `unregister_service(self, service_name)`
  - `report_metric(self, service_name, metric_name...)`
  - `get_system_health_dashboard(self)`

#### ValidatorRegistry
- **Location**: `netra_backend\app\core\cross_service_validators\validator_framework.py:123`
- **Base Classes**: None
- **Decorators**: None
- **Total Methods**: 5
- **Core Registry Methods**: ['register', 'get', 'list']
- **Thread Safety**: Unknown
- **Factory Support**: No
- **Key Methods**:
  - `__init__(self)`
  - `register(self, validator, category)`
  - `get_validator(self, name)`
  - `get_validators_by_category(self, category)`
  - `list_validators(self)`

## Duplication Analysis

### Common Method Patterns:
- `__init__(self)`: Found in 17 registries
  - ServiceRegistry
  - RegistryAnalyzer
  - ToolRegistry
  - AgentRecoveryRegistry
  - DatabaseRecoveryRegistry
  - ... and 12 more
- `register_tool(self, tool)`: Found in 2 registries
  - ToolRegistry
  - ToolRegistryInterface
- `has_tool(self, tool_name)`: Found in 2 registries
  - ToolRegistry
  - ToolRegistrySnapshot
- `get_tool(self, tool_name)`: Found in 2 registries
  - ToolRegistry
  - ToolRegistrySnapshot
- `list_tools(self)`: Found in 2 registries
  - ToolRegistry
  - ToolRegistrySnapshot
- `get_tool_count(self)`: Found in 2 registries
  - ToolRegistry
  - ToolRegistrySnapshot
- `get_all_services(self)`: Found in 2 registries
  - HealthRegistry
  - MockServiceRegistry
- `freeze(self)`: Found in 2 registries
  - AgentClassRegistry
  - UnifiedAgentRegistry
- `is_frozen(self)`: Found in 2 registries
  - AgentClassRegistry
  - UnifiedAgentRegistry

## Consolidation Opportunities

### Potential Generic Base Class Structure:
```python
class UniversalRegistry[T](Generic[T]):
    def __init__(self, registry_name: str):
        self.name = registry_name
        self._items: Dict[str, T] = {}
        self._factories: Dict[str, Callable] = {}
        self._lock = threading.RLock()
    
    def register(self, key: str, item: T) -> None
    def register_factory(self, key: str, factory: Callable) -> None
    def get(self, key: str, context: Optional[Context] = None) -> T
    def has(self, key: str) -> bool
    def list(self) -> List[str]
    def remove(self, key: str) -> bool
```

### Recommended Consolidation:
1. **Create UniversalRegistry[T]** - Generic base class
2. **AgentRegistry extends UniversalRegistry[BaseAgent]**
3. **ToolRegistry extends UniversalRegistry[BaseTool]**
4. **ServiceRegistry extends UniversalRegistry[Service]**
5. **Remove all duplicate registry implementations**

## SSOT Violations

### Multiple Implementations of Same Concept:

- **ToolRegistry**: 2 implementations
  - UnifiedToolRegistry (`netra_backend\app\services\unified_tool_registry\registry.py`)
  - ToolRegistry (`netra_backend\app\agents\tool_dispatcher_registry.py`)

- **AgentRegistry**: 3 implementations
  - AgentClassRegistry (`netra_backend\app\agents\supervisor\agent_class_registry.py`)
  - AgentRegistry (`netra_backend\app\agents\supervisor\agent_registry.py`)
  - UnifiedAgentRegistry (`netra_backend\app\agents\supervisor\unified_agent_registry.py`)

- **TestAgentRegistry**: 2 implementations
  - TestAgentClassRegistry (`tests\netra_backend\agents\test_agent_isolation.py`)
  - TestUnifiedAgentRegistry (`tests\integration\test_agent_consolidation.py`)