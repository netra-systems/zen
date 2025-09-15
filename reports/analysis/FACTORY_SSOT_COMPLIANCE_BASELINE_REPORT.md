# Factory SSOT Compliance Baseline Report
**Generated:** True
**Total Factories Analyzed:** 1100

## Executive Summary
- **Compliance Score:** 90.0%
- **Compliant Factories:** 990
- **Violation Count:** 244

## Violation Breakdown by Type
- **Import Fragmentation:** 178
- **Service Boundary:** 14
- **Naming Violation:** 17
- **Duplicate Factory:** 35

## Violation Breakdown by Severity
- **MEDIUM:** 195
- **HIGH:** 49

## Duplicate Factories (SSOT Violations)
- **ExportConfigFactory** (1 instances)
  - netra_backend\tests\helpers\analytics_export_helpers.py
- **TestFactoryInitializationIntegration** (1 instances)
  - netra_backend\tests\integration\test_factory_initialization_integration.py
- **TestFactorySSotValidationIntegration** (1 instances)
  - netra_backend\tests\integration\test_factory_ssot_validation_integration.py
- **TestFactoryPatternInitialization** (1 instances)
  - netra_backend\tests\integration\startup\test_factory_pattern_initialization.py
- **TestFactoryPatternBusinessValue** (1 instances)
  - netra_backend\tests\integration\startup\test_factory_pattern_initialization.py
- **TestFactoryIsolationPatterns** (1 instances)
  - netra_backend\tests\integration\user_context\test_factory_isolation_patterns_comprehensive_integration.py
- **TestFactoryErrorHandlingAndResourceCleanup** (1 instances)
  - netra_backend\tests\integration\uvs\test_error_handling_edge_cases.py
- **TestFactoryMetricsAndPerformanceMonitoring** (1 instances)
  - netra_backend\tests\integration\uvs\test_reporting_context_integration.py
- **TestFactoryBasedResourceManagement** (1 instances)
  - netra_backend\tests\integration\uvs\test_user_isolation_validation_core.py
- **TestFactoryMethods** (1 instances)
  - netra_backend\tests\supervisor\test_user_execution_context.py
- **TestFactoryIntegrationPatterns** (1 instances)
  - netra_backend\tests\unit\test_agent_factory.py
- **TestFactoryPatternsAndMigration** (1 instances)
  - netra_backend\tests\unit\agents\test_execution_engine_comprehensive.py
- **TestFactoryPatternSupport** (1 instances)
  - netra_backend\tests\unit\agents\supervisor\test_agent_registry.py
- **TestFactoryMetrics** (3 instances)
  - netra_backend\tests\unit\agents\supervisor\test_execution_engine_factory_comprehensive.py
  - netra_backend\tests\unit\deprecated\test_websocket_manager_factory.py
  - netra_backend\tests\unit\websocket\test_manager_factory_business_logic.py
- **TestFactoryShutdown** (1 instances)
  - netra_backend\tests\unit\agents\supervisor\test_execution_engine_factory_comprehensive.py
- **TestFactorySingleton** (1 instances)
  - netra_backend\tests\unit\agents\supervisor\test_execution_engine_factory_comprehensive.py
- **TestFactoryAliasMethodsCompatibility** (1 instances)
  - netra_backend\tests\unit\agents\supervisor\test_execution_engine_factory_comprehensive.py
- **TestFactoryPerformanceBenchmarks** (1 instances)
  - netra_backend\tests\unit\agents\supervisor\test_execution_engine_factory_comprehensive.py
- **TestFactoryContextCreationWithValidation** (1 instances)
  - netra_backend\tests\unit\agents\supervisor\test_factory_context_creation_validation.py
- **TestFactoryPerformanceMetricsAndMonitoring** (1 instances)
  - netra_backend\tests\unit\agents\supervisor\test_factory_pattern_user_isolation.py
- **TestFactoryPatternAdvanced** (1 instances)
  - netra_backend\tests\unit\core\managers\test_unified_state_manager_comprehensive.py
- **TestFactoryPatternSecurity** (1 instances)
  - netra_backend\tests\unit\core\tools\test_unified_tool_dispatcher.py
- **MockFactoryValidator** (1 instances)
  - netra_backend\tests\unit\golden_path\test_factory_initialization_logic.py
- **TestFactoryInitializationLogic** (1 instances)
  - netra_backend\tests\unit\golden_path\test_factory_initialization_logic.py
- **TestFactoryUserContextIsolation** (1 instances)
  - netra_backend\tests\unit\user_isolation\test_factory_user_context_isolation.py
- **TestFactoryInitializationError** (1 instances)
  - netra_backend\tests\unit\websocket\test_manager_factory_business_logic.py
- **MockFactory** (1 instances)
  - test_framework\ssot\mocks.py
- **DatabaseMockFactory** (1 instances)
  - test_framework\ssot\mocks.py
- **ServiceMockFactory** (1 instances)
  - test_framework\ssot\mocks.py
- **SSotMockFactory** (1 instances)
  - test_framework\ssot\mock_factory.py
- **TestMockFactory** (1 instances)
  - test_framework\tests\test_ssot_complete.py
- **TestSSotMockFactory** (1 instances)
  - test_framework\tests\test_ssot_framework.py
- **TestFactoryFunctions** (1 instances)
  - test_framework\tests\test_test_context.py

## Import Path Fragmentation
- Non-SSOT import pattern: It enables gradual migration from singleton to factory patterns.
- Non-SSOT import pattern: # REMOVED: Singleton orchestrator import - replaced with per-request factory patterns
- Non-SSOT import pattern: logger.info(" PASS:  SSOT COMPLIANCE: WebSocketManager direct import verified - factory pattern eliminated")
- Non-SSOT import pattern: logger.info(" PASS:  SSOT COMPLIANCE: WebSocket components use direct SSOT import - factory pattern eliminated")
- Non-SSOT import pattern: def _create_from_factory(
- Non-SSOT import pattern: return UnifiedAdminToolDispatcher._create_from_factory(
- Non-SSOT import pattern: # Get dependencies from context (injected by AgentInstanceFactory)
- Non-SSOT import pattern: "Use configure_execution_engine_factory() from supervisor.execution_engine_factory instead."
- Non-SSOT import pattern: def _init_from_factory(cls, tools: List[BaseTool] = None, websocket_bridge: Optional['AgentWebSocketBridge'] = None):
- Non-SSOT import pattern: # Import here to avoid circular imports - now using SSOT factory

## Naming Convention Violations
- ConfigurationManagerFactoryCompatibility: manager_overuse: ConfigurationManagerFactoryCompatibility
- StateManagerFactory: manager_overuse: StateManagerFactory
- _DeprecatedLifecycleManagerFactory: manager_overuse: _DeprecatedLifecycleManagerFactory
- MockWebSocketManagerFactory: manager_overuse: MockWebSocketManagerFactory
- _WebSocketManagerFactory: manager_overuse: _WebSocketManagerFactory
- MockWebSocketManagerFactory: manager_overuse: MockWebSocketManagerFactory
- TestWebSocketManagerFactoryIntegration: manager_overuse: TestWebSocketManagerFactoryIntegration
- FactoryResourceManager: manager_overuse: FactoryResourceManager
- TestLifecycleManagerFactory: manager_overuse: TestLifecycleManagerFactory
- TestUnifiedStateManagerFactoryPattern: manager_overuse: TestUnifiedStateManagerFactoryPattern

## Service Boundary Violations
- Cross-service factory import: from test_framework.ssot.mocks import get_mock_factory
- Cross-service factory import: from test_framework.ssot.mocks import get_mock_factory
- Cross-service factory import: from test_framework.ssot.mock_factory import SSotMockFactory
- Cross-service factory import: from test_framework.ssot.mock_factory import SSotMockFactory
- Cross-service factory import: from test_framework.ssot.mock_factory import SSotMockFactory
- Cross-service factory import: from test_framework.user_execution_context_fixtures import realistic_user_context, multi_user_contexts, concurrent_context_factory, async_context_manager, context_hierarchy_builder, clean_context_registry
- Cross-service factory import: from test_framework.ssot.mocks import MockFactory
- Cross-service factory import: from test_framework.ssot.mocks import get_mock_factory
- Cross-service factory import: from test_framework.ssot.mocks import MockFactory
- Cross-service factory import: from test_framework.ssot.mock_factory import SSotMockFactory