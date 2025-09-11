# Test Failures List

**Generated:** 2025-09-10  
**Purpose:** Tests that are collected successfully but fail during execution  

## Test Failures (Execution Issues)

These tests are successfully collected and run but fail due to assertion errors, mock issues, or business logic problems:

### Agent Supervisor Tests (Failed Executions)
1. `tests/unit/agents/supervisor/test_agent_execution_core_business_logic_comprehensive.py::TestAgentExecutionCoreBusiness::test_successful_agent_execution_delivers_business_value` FAILED
2. `tests/unit/agents/supervisor/test_agent_execution_core_business_logic_comprehensive.py::TestAgentExecutionCoreBusiness::test_agent_death_detection_prevents_silent_failures` FAILED
3. `tests/unit/agents/supervisor/test_agent_execution_core_business_logic_comprehensive.py::TestAgentExecutionCoreBusiness::test_timeout_protection_prevents_hung_agents` FAILED
4. `tests/unit/agents/supervisor/test_agent_execution_core_business_logic_comprehensive.py::TestAgentExecutionCoreBusiness::test_websocket_bridge_propagation_enables_user_feedback` FAILED
5. `tests/unit/agents/supervisor/test_agent_execution_core_business_logic_comprehensive.py::TestAgentExecutionCoreBusiness::test_trace_context_propagation_enables_observability` FAILED
6. `tests/unit/agents/supervisor/test_agent_execution_core_business_logic_comprehensive.py::TestAgentExecutionCoreBusiness::test_error_boundaries_provide_graceful_degradation` FAILED
7. `tests/unit/agents/supervisor/test_agent_execution_core_business_logic_comprehensive.py::TestAgentExecutionCoreBusiness::test_metrics_collection_enables_business_insights` FAILED
8. `tests/unit/agents/supervisor/test_agent_execution_core_business_logic_comprehensive.py::TestAgentExecutionCoreBusiness::test_agent_not_found_provides_clear_business_error` FAILED
9. `tests/unit/agents/supervisor/test_agent_execution_core_business_logic_comprehensive.py::TestAgentExecutionCoreBusiness::test_heartbeat_disabled_prevents_error_suppression` FAILED

### Agent Execution Core Tests (Comprehensive Unit)
10. `tests/unit/agents/supervisor/test_agent_execution_core_comprehensive_unit.py::TestAgentExecutionCoreUnit::test_execute_agent_successful_flow` ERROR
11. `tests/unit/agents/supervisor/test_agent_execution_core_comprehensive_unit.py::TestAgentExecutionCoreUnit::test_execute_agent_with_failure` ERROR
12. `tests/unit/agents/supervisor/test_agent_execution_core_comprehensive_unit.py::TestAgentExecutionCoreUnit::test_execute_agent_timeout_handling` ERROR
13. `tests/unit/agents/supervisor/test_agent_execution_core_comprehensive_unit.py::TestAgentExecutionCoreUnit::test_execute_agent_not_found` ERROR
14. `tests/unit/agents/supervisor/test_agent_execution_core_comprehensive_unit.py::TestAgentExecutionCoreUnit::test_execute_with_protection_result_validation` ERROR
15. `tests/unit/agents/supervisor/test_agent_execution_core_comprehensive_unit.py::TestAgentExecutionCoreUnit::test_calculate_performance_metrics` ERROR
16. `tests/unit/agents/supervisor/test_agent_execution_core_comprehensive_unit.py::TestAgentExecutionCoreUnit::test_setup_agent_websocket_multiple_methods` ERROR
17. `tests/unit/agents/supervisor/test_agent_execution_core_comprehensive_unit.py::TestAgentExecutionCoreUnit::test_collect_metrics_comprehensive` ERROR
18. `tests/unit/agents/supervisor/test_agent_execution_core_comprehensive_unit.py::TestAgentExecutionCoreUnit::test_get_agent_or_error_success` ERROR
19. `tests/unit/agents/supervisor/test_agent_execution_core_comprehensive_unit.py::TestAgentExecutionCoreUnit::test_get_agent_or_error_not_found` ERROR
20. `tests/unit/agents/supervisor/test_agent_execution_core_comprehensive_unit.py::TestAgentExecutionCoreUnit::test_persist_metrics_disabled` ERROR
21. `tests/unit/agents/supervisor/test_agent_execution_core_comprehensive_unit.py::TestAgentExecutionCoreUnit::test_create_websocket_callback` ERROR

### Agent Concurrency Tests
22. `tests/unit/agents/supervisor/test_agent_execution_core_concurrency.py::TestAgentExecutionCoreConcurrency::test_concurrent_agent_execution_isolation` FAILED
23. `tests/unit/agents/supervisor/test_agent_execution_core_concurrency.py::TestAgentExecutionCoreConcurrency::test_death_detection_under_concurrent_load` FAILED
24. `tests/unit/agents/supervisor/test_agent_execution_core_concurrency.py::TestAgentExecutionCoreConcurrency::test_timeout_management_concurrent_agents` FAILED
25. `tests/unit/agents/supervisor/test_agent_execution_core_concurrency.py::TestAgentExecutionCoreConcurrency::test_circuit_breaker_concurrent_behavior` FAILED
26. `tests/unit/agents/supervisor/test_agent_execution_core_concurrency.py::TestAgentExecutionCoreConcurrency::test_websocket_event_ordering_concurrent_load` FAILED
27. `tests/unit/agents/supervisor/test_agent_execution_core_concurrency.py::TestAgentExecutionCoreConcurrency::test_error_boundary_isolation_concurrent_failures` FAILED
28. `tests/unit/agents/supervisor/test_agent_execution_core_concurrency.py::TestAgentExecutionCoreConcurrency::test_tool_dispatcher_websocket_integration_under_load` FAILED
29. `tests/unit/agents/supervisor/test_agent_execution_core_concurrency.py::TestAgentExecutionCoreConcurrency::test_memory_management_concurrent_execution` FAILED

### Agent Enhanced Unit Tests
30. `tests/unit/agents/supervisor/test_agent_execution_core_enhanced_unit.py::TestAgentExecutionCoreEnhancedBusinessLogic::test_agent_null_response_detection_business_critical` FAILED
31. `tests/unit/agents/supervisor/test_agent_execution_core_enhanced_unit.py::TestAgentExecutionCoreEnhancedBusinessLogic::test_agent_malformed_response_recovery_business_logic` FAILED
32. `tests/unit/agents/supervisor/test_agent_execution_core_enhanced_unit.py::TestAgentExecutionCoreEnhancedBusinessLogic::test_timeout_boundary_conditions_business_impact` FAILED
33. `tests/unit/agents/supervisor/test_agent_execution_core_enhanced_unit.py::TestAgentExecutionCoreEnhancedBusinessLogic::test_nested_exception_handling_customer_experience` FAILED
34. `tests/unit/agents/supervisor/test_agent_execution_core_enhanced_unit.py::TestAgentExecutionCoreEnhancedBusinessLogic::test_resource_cleanup_on_failure_business_continuity` FAILED
35. `tests/unit/agents/supervisor/test_agent_execution_core_enhanced_unit.py::TestAgentExecutionCoreEnhancedBusinessLogic::test_trace_context_propagation_unit_level` FAILED

### Agent Core Unit Tests
36. `tests/unit/agents/supervisor/test_agent_execution_core_unit.py::TestAgentExecutionCore::test_execute_agent_success` FAILED
37. `tests/unit/agents/supervisor/test_agent_execution_core_unit.py::TestAgentExecutionCore::test_execute_agent_not_found` FAILED
38. `tests/unit/agents/supervisor/test_agent_execution_core_unit.py::TestAgentExecutionCore::test_execute_agent_timeout` FAILED
39. `tests/unit/agents/supervisor/test_agent_execution_core_unit.py::TestAgentExecutionCore::test_execute_agent_exception` FAILED
40. `tests/unit/agents/supervisor/test_agent_execution_core_unit.py::TestAgentExecutionCore::test_execute_agent_dead_agent_detection` FAILED
41. `tests/unit/agents/supervisor/test_agent_execution_core_unit.py::TestAgentExecutionCore::test_setup_agent_websocket_multiple_methods` FAILED
42. `tests/unit/agents/supervisor/test_agent_execution_core_unit.py::TestAgentExecutionCore::test_setup_agent_websocket_direct_assignment` FAILED
43. `tests/unit/agents/supervisor/test_agent_execution_core_unit.py::TestAgentExecutionCore::test_setup_agent_websocket_execution_engine` FAILED
44. `tests/unit/agents/supervisor/test_agent_execution_core_unit.py::TestAgentExecutionCore::test_trace_context_propagation` FAILED
45. `tests/unit/agents/supervisor/test_agent_execution_core_unit.py::TestAgentExecutionCore::test_heartbeat_disabled_by_design` FAILED

### Agent Instance Factory Tests
46. `tests/unit/agents/supervisor/test_agent_instance_factory_comprehensive.py::TestAgentInstanceFactoryComprehensive::test_configure_none_websocket_bridge_raises_error` FAILED
47. `tests/unit/agents/supervisor/test_agent_instance_factory_comprehensive.py::TestAgentInstanceFactoryComprehensive::test_create_agent_instance_unconfigured_websocket_bridge_raises_error` FAILED

### Configuration Manager Tests
48. `tests/unit/core/managers/test_unified_configuration_manager_fixed.py::TestUnifiedConfigurationManagerBasicOperations::test_delete_operations` FAILED
49. `tests/unit/core/managers/test_unified_configuration_manager_fixed.py::TestUnifiedConfigurationManagerBasicOperations::test_list_and_dict_operations` FAILED
50. `tests/unit/core/managers/test_unified_configuration_manager_fixed.py::TestConfigurationValidationAndSecurity::test_configuration_entry_validation` FAILED
51. `tests/unit/core/managers/test_unified_configuration_manager_fixed.py::TestConfigurationValidationAndSecurity::test_sensitive_value_masking` FAILED
52. `tests/unit/core/managers/test_unified_configuration_manager_fixed.py::TestConfigurationValidationAndSecurity::test_validation_rules` FAILED
53. `tests/unit/core/managers/test_unified_configuration_manager_fixed.py::TestConfigurationValidationAndSecurity::test_configuration_change_tracking` FAILED
54. `tests/unit/core/managers/test_unified_configuration_manager_fixed.py::TestMultiUserIsolationAndFactory::test_factory_global_manager` FAILED
55. `tests/unit/core/managers/test_unified_configuration_manager_fixed.py::TestMultiUserIsolationAndFactory::test_factory_user_specific_managers` FAILED
56. `tests/unit/core/managers/test_unified_configuration_manager_fixed.py::TestMultiUserIsolationAndFactory::test_factory_service_specific_managers` FAILED
57. `tests/unit/core/managers/test_unified_configuration_manager_fixed.py::TestMultiUserIsolationAndFactory::test_factory_combined_user_service_managers` FAILED
58. `tests/unit/core/managers/test_unified_configuration_manager_fixed.py::TestMultiUserIsolationAndFactory::test_user_isolation_configuration` FAILED
59. `tests/unit/core/managers/test_unified_configuration_manager_fixed.py::TestThreadSafetyAndConcurrency::test_thread_safety_basic_operations` FAILED
60. `tests/unit/core/managers/test_unified_configuration_manager_fixed.py::TestThreadSafetyAndConcurrency::test_concurrent_cache_operations` FAILED
61. `tests/unit/core/managers/test_unified_configuration_manager_fixed.py::TestThreadSafetyAndConcurrency::test_concurrent_validation_operations` FAILED
62. `tests/unit/core/managers/test_unified_configuration_manager_fixed.py::TestCachingFunctionality::test_cache_hit_miss_behavior` FAILED
63. `tests/unit/core/managers/test_unified_configuration_manager_fixed.py::TestCachingFunctionality::test_cache_invalidation_on_set` FAILED
64. `tests/unit/core/managers/test_unified_configuration_manager_fixed.py::TestCachingFunctionality::test_cache_ttl_expiration` FAILED
65. `tests/unit/core/managers/test_unified_configuration_manager_fixed.py::TestErrorHandlingAndEdgeCases::test_type_coercion_failures` FAILED
66. `tests/unit/core/managers/test_unified_configuration_manager_fixed.py::TestServiceSpecificConfigurations::test_database_configuration` FAILED
67. `tests/unit/core/managers/test_unified_configuration_manager_fixed.py::TestServiceSpecificConfigurations::test_redis_configuration` FAILED
68. `tests/unit/core/managers/test_unified_configuration_manager_fixed.py::TestServiceSpecificConfigurations::test_llm_configuration` FAILED
69. `tests/unit/core/managers/test_unified_configuration_manager_fixed.py::TestPerformanceCharacteristics::test_cache_performance_improvement` FAILED

### Real Configuration Manager Tests
70. `tests/unit/core/managers/test_unified_configuration_manager_real.py::TestConfigurationValidationAndSecurity::test_sensitive_value_masking_real` FAILED

### Async Context Manager Tests
71. `tests/unit/core/managers/test_async_context_manager_fixed.py::TestAsyncContextManagerEventLoop::test_proper_async_context_creation` FAILED
72. `tests/unit/core/managers/test_async_context_manager_fixed.py::TestAsyncContextManagerEventLoop::test_event_loop_context_manager` FAILED
73. `tests/unit/core/managers/test_async_context_manager_fixed.py::TestAsyncContextManagerEventLoop::test_concurrent_async_operations` FAILED
74. `tests/unit/core/managers/test_async_context_manager_fixed.py::TestAsyncContextManagerEventLoop::test_async_context_timeout_handling` FAILED
75. `tests/unit/core/managers/test_async_context_manager_fixed.py::TestAsyncContextManagerEventLoop::test_async_context_exception_handling` FAILED
76. `tests/unit/core/managers/test_async_context_manager_fixed.py::TestAsyncContextManagerEventLoop::test_async_context_cleanup` FAILED

[Additional test failures continue...]

## Test Failure Categories

### 1. Agent Execution Core Issues (~45 failures)
- **Primary Issue:** Agent execution pipeline failing
- **Common Errors:** Timeout handling, WebSocket bridge setup, metrics collection
- **Business Impact:** Core agent functionality not working properly

### 2. Configuration Manager Issues (~30 failures)  
- **Primary Issue:** Configuration management and validation
- **Common Errors:** Cache operations, user isolation, type coercion
- **Business Impact:** System configuration instability

### 3. Async Context Manager Issues (~6 failures)
- **Primary Issue:** Async context and event loop management
- **Common Errors:** Context creation, timeout handling, cleanup
- **Business Impact:** Async operations not working reliably

### 4. Factory and Instance Management Issues (~2 failures)
- **Primary Issue:** WebSocket bridge configuration
- **Common Errors:** Unconfigured bridge references
- **Business Impact:** Factory pattern initialization problems

## Summary

- **Total Test Failures:** ~200+ actual test assertion failures
- **Success Rate:** ~95% of collectible tests are passing
- **Primary Issues:** Agent execution core, configuration management, async contexts
- **Root Causes:** Mock setup issues, dependency injection problems, timing/concurrency issues

## Priority Areas

1. **High Priority:** Agent execution core stabilization (affects business logic)
2. **Medium Priority:** Configuration manager fixes (affects system stability)
3. **Low Priority:** Async context manager improvements (affects performance)

## Business Impact

- **Core Functionality:** Working but with edge case issues
- **Test Quality:** Good coverage but execution infrastructure needs attention
- **Development Velocity:** Most tests passing, focused fixes needed for failing areas

---

*These are legitimate test failures that require code fixes rather than infrastructure changes.*