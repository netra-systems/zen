# Test Overlap Analysis Report

Generated: 2025-08-21T12:10:47.523223

## Executive Summary

- **Total Test Files**: 405
- **Total Test Functions**: 2811
- **Total Similarity Pairs**: 24030

### Similarity Breakdown

- **Exact Duplicates**: 5927 ⚠️
- **Highly Similar**: 645
- **Similar**: 3850
- **Related**: 13608

## Recommendations

1. CRITICAL: Found 5927 exact duplicate test pairs. These should be immediately reviewed and consolidated.
2. WARNING: Found 645 highly similar test pairs. Consider refactoring these using parametrized tests or test utilities.
3. Category 'root' has 261 internal overlaps. Consider reorganizing tests or extracting common test utilities.
4. Category 'agents' has 1072 internal overlaps. Consider reorganizing tests or extracting common test utilities.
5. Category 'clickhouse' has 367 internal overlaps. Consider reorganizing tests or extracting common test utilities.
6. Category 'config' has 94 internal overlaps. Consider reorganizing tests or extracting common test utilities.
7. Category 'core' has 2321 internal overlaps. Consider reorganizing tests or extracting common test utilities.
8. Category 'critical' has 128 internal overlaps. Consider reorganizing tests or extracting common test utilities.
9. Category 'integration' has 4796 internal overlaps. Consider reorganizing tests or extracting common test utilities.
10. Category 'routes' has 2063 internal overlaps. Consider reorganizing tests or extracting common test utilities.
11. Category 'security' has 26 internal overlaps. Consider reorganizing tests or extracting common test utilities.
12. Category 'services' has 2888 internal overlaps. Consider reorganizing tests or extracting common test utilities.
13. Category 'startup' has 423 internal overlaps. Consider reorganizing tests or extracting common test utilities.
14. Category 'unit' has 1431 internal overlaps. Consider reorganizing tests or extracting common test utilities.
15. Category 'websocket' has 120 internal overlaps. Consider reorganizing tests or extracting common test utilities.
16. Categories with very few tests: database, llm, unified_system. Consider consolidating or improving test coverage.
17. Found 1228 cross-category duplicates/highly similar tests. Consider creating shared test utilities or fixtures.

## Category Analysis

### integration

- Tests: 277
- Total Lines: 2993
- Avg Complexity: 1.7
- Internal Overlaps: 4796
- Cross-Category Overlaps: 1371
- Duplicates: 4620
- Highly Similar: 32

**Top Overlaps:**

- `test_users` ↔ `test_users` (similarity: 0.893, type: highly_similar)
- `test_users` ↔ `test_users` (similarity: 0.882, type: highly_similar)
- `test_users` ↔ `test_users` (similarity: 0.88, type: highly_similar)
- `test_users` ↔ `test_users` (similarity: 0.88, type: highly_similar)
- `test_users` ↔ `test_users` (similarity: 0.88, type: highly_similar)

### services

- Tests: 445
- Total Lines: 4829
- Avg Complexity: 1.4
- Internal Overlaps: 2888
- Cross-Category Overlaps: 1857
- Duplicates: 3
- Highly Similar: 174

**Top Overlaps:**

- `test_weighted_score_no_penalties` ↔ `test_weighted_score_all_penalties` (similarity: 0.996, type: highly_similar)
- `test_select_config_openai` ↔ `test_select_config_health` (similarity: 0.988, type: highly_similar)
- `test_select_config_google` ↔ `test_select_config_openai` (similarity: 0.985, type: highly_similar)
- `test_select_config_google` ↔ `test_select_config_health` (similarity: 0.985, type: highly_similar)
- `test_select_config_openai` ↔ `test_select_config_anthropic` (similarity: 0.984, type: highly_similar)

### core

- Tests: 485
- Total Lines: 4493
- Avg Complexity: 1.2
- Internal Overlaps: 2321
- Cross-Category Overlaps: 2852
- Duplicates: 3
- Highly Similar: 56

**Top Overlaps:**

- `test_register_resource_without_callback` ↔ `test_register_resource_during_shutdown` (similarity: 0.98, type: highly_similar)
- `test_register_resource_without_callback` ↔ `test_register_resource_with_callback` (similarity: 0.961, type: highly_similar)
- `test_get_circuit_breaker_config` ↔ `test_get_retry_config` (similarity: 0.959, type: highly_similar)
- `test_secret_rotation` ↔ `test_secret_versioning` (similarity: 0.955, type: highly_similar)
- `test_quality_metrics_retrieval` ↔ `test_quality_metrics_from_multiple_services` (similarity: 0.941, type: highly_similar)

### routes

- Tests: 114
- Total Lines: 3806
- Avg Complexity: 4.1
- Internal Overlaps: 2063
- Cross-Category Overlaps: 258
- Duplicates: 0
- Highly Similar: 32

**Top Overlaps:**

- `test_thread_message_addition` ↔ `test_message_editing` (similarity: 0.937, type: highly_similar)
- `test_message_reactions_and_feedback` ↔ `test_message_threading_and_replies` (similarity: 0.906, type: highly_similar)
- `test_supply_contract_management` ↔ `test_automated_data_refresh` (similarity: 0.871, type: highly_similar)
- `test_supply_sustainability_assessment` ↔ `test_data_comparison_analysis` (similarity: 0.867, type: highly_similar)
- `test_supply_sustainability_assessment` ↔ `test_supply_data_enrichment` (similarity: 0.862, type: highly_similar)

### unit

- Tests: 541
- Total Lines: 4722
- Avg Complexity: 1.2
- Internal Overlaps: 1431
- Cross-Category Overlaps: 2884
- Duplicates: 1
- Highly Similar: 164

**Top Overlaps:**

- `test_adaptive_threshold_decreases_on_slow_calls` ↔ `test_adaptive_threshold_increases_on_fast_calls` (similarity: 1.0, type: highly_similar)
- `test_get_agent_type_enum` ↔ `test_get_agent_type_enum` (similarity: 1.0, type: duplicate)
- `test_grant_permission_creates_structure` ↔ `test_revoke_permission_creates_structure` (similarity: 0.993, type: highly_similar)
- `test_log_agent_start` ↔ `test_log_agent_completion` (similarity: 0.989, type: highly_similar)
- `test_log_agent_start` ↔ `test_log_agent_completion` (similarity: 0.986, type: highly_similar)

### agents

- Tests: 222
- Total Lines: 1982
- Avg Complexity: 1.1
- Internal Overlaps: 1072
- Cross-Category Overlaps: 783
- Duplicates: 28
- Highly Similar: 63

**Top Overlaps:**

- `test_sql_injection_patterns` ↔ `test_command_injection_patterns` (similarity: 1.0, type: highly_similar)
- `test_sql_injection_patterns` ↔ `test_script_injection_patterns` (similarity: 0.99, type: highly_similar)
- `test_script_injection_patterns` ↔ `test_command_injection_patterns` (similarity: 0.99, type: highly_similar)
- `test_request_too_short` ↔ `test_request_too_long` (similarity: 0.957, type: highly_similar)
- `test_request_too_short` ↔ `test_request_too_long` (similarity: 0.957, type: highly_similar)

### startup

- Tests: 104
- Total Lines: 826
- Avg Complexity: 1.1
- Internal Overlaps: 423
- Cross-Category Overlaps: 642
- Duplicates: 27
- Highly Similar: 64

**Top Overlaps:**

- `test_get_check_interval_adaptive` ↔ `test_get_check_interval_stable` (similarity: 0.977, type: highly_similar)
- `test_get_check_interval_adaptive` ↔ `test_get_check_interval_stable` (similarity: 0.977, type: highly_similar)
- `test_get_fallback_action_invalid` ↔ `test_get_fallback_action_stale_interactive` (similarity: 0.971, type: highly_similar)
- `test_get_fallback_action_missing` ↔ `test_get_fallback_action_stale_interactive` (similarity: 0.968, type: highly_similar)
- `test_calculate_stage_warming` ↔ `test_calculate_stage_operational` (similarity: 0.963, type: highly_similar)

### clickhouse

- Tests: 66
- Total Lines: 1878
- Avg Complexity: 1.1
- Internal Overlaps: 367
- Cross-Category Overlaps: 307
- Duplicates: 1
- Highly Similar: 0

**Top Overlaps:**

- `test_prompt_response_length_validation` ↔ `test_prompt_response_length_validation` (similarity: 0.748, type: duplicate)
- `test_resource_utilization_across_sources` ↔ `test_forecast_calculation` (similarity: 0.71, type: similar)
- `test_business_metrics_aggregation` ↔ `test_complex_join_performance` (similarity: 0.7, type: similar)
- `test_outlier_detection_small_dataset` ↔ `test_outlier_detection_methods` (similarity: 0.689, type: similar)
- `test_performance_impact_correlation` ↔ `test_forecast_calculation` (similarity: 0.688, type: similar)

### root

- Tests: 130
- Total Lines: 1958
- Avg Complexity: 2.4
- Internal Overlaps: 261
- Cross-Category Overlaps: 1503
- Duplicates: 5
- Highly Similar: 24

**Top Overlaps:**

- `test_service_injection` ↔ `test_service_injection` (similarity: 1.0, type: duplicate)
- `test_service_initialization` ↔ `test_service_initialization` (similarity: 1.0, type: duplicate)
- `test_mcp_service_creation` ↔ `test_mcp_service_creation` (similarity: 1.0, type: duplicate)
- `test_set_log_table_success` ↔ `test_add_log_table_success` (similarity: 0.996, type: highly_similar)
- `test_set_log_table_not_available` ↔ `test_set_default_log_table_for_context_table_not_available` (similarity: 0.989, type: highly_similar)

### critical

- Tests: 125
- Total Lines: 1988
- Avg Complexity: 2.0
- Internal Overlaps: 128
- Cross-Category Overlaps: 1019
- Duplicates: 3
- Highly Similar: 3

**Top Overlaps:**

- `test_module_import` ↔ `test_module_import` (similarity: 0.85, type: duplicate)
- `test_placeholder` ↔ `test_placeholder` (similarity: 0.85, type: duplicate)
- `test_k_service_staging_detection` ↔ `test_k_service_no_staging_detection` (similarity: 0.834, type: highly_similar)
- `test_broadcast_executor_has_execution_engine` ↔ `test_connection_executor_has_execution_engine` (similarity: 0.821, type: highly_similar)
- `test_critical_vars_mapping_includes_database_vars` ↔ `test_critical_vars_mapping_includes_auth_vars` (similarity: 0.802, type: highly_similar)

## Exact Duplicates ⚠️

These test pairs appear to be exact duplicates and should be consolidated:

1. `netra_backend\tests\test_database_manager_managers.py::test_module_import`
   ↔ `netra_backend\tests\auth_integration\test_real_auth_integration_helpers.py::test_module_import`
   (similarity: 0.85)

1. `netra_backend\tests\test_database_manager_managers.py::test_module_import`
   ↔ `netra_backend\tests\auth_integration\test_real_auth_integration_managers.py::test_module_import`
   (similarity: 0.85)

1. `netra_backend\tests\test_database_manager_managers.py::test_module_import`
   ↔ `netra_backend\tests\auth_integration\test_real_user_session_management_managers.py::test_module_import`
   (similarity: 0.85)

1. `netra_backend\tests\test_database_manager_managers.py::test_module_import`
   ↔ `netra_backend\tests\critical\test_real_auth_integration_critical_helpers.py::test_module_import`
   (similarity: 0.85)

1. `netra_backend\tests\test_database_manager_managers.py::test_module_import`
   ↔ `netra_backend\tests\critical\test_real_auth_integration_critical_managers.py::test_module_import`
   (similarity: 0.85)

1. `netra_backend\tests\test_database_manager_managers.py::test_module_import`
   ↔ `netra_backend\tests\integration\test_auth_service_dependency_resolution_helpers.py::test_module_import`
   (similarity: 0.85)

1. `netra_backend\tests\test_database_manager_managers.py::test_module_import`
   ↔ `netra_backend\tests\integration\test_auth_service_dependency_resolution_services.py::test_module_import`
   (similarity: 0.85)

1. `netra_backend\tests\test_database_manager_managers.py::test_module_import`
   ↔ `netra_backend\tests\integration\test_background_jobs_integration_core.py::test_module_import`
   (similarity: 0.85)

1. `netra_backend\tests\test_database_manager_managers.py::test_module_import`
   ↔ `netra_backend\tests\integration\test_background_jobs_integration_helpers.py::test_module_import`
   (similarity: 0.85)

1. `netra_backend\tests\test_database_manager_managers.py::test_module_import`
   ↔ `netra_backend\tests\integration\test_cache_management_integration_core.py::test_module_import`
   (similarity: 0.85)

1. `netra_backend\tests\test_database_manager_managers.py::test_module_import`
   ↔ `netra_backend\tests\integration\test_cache_management_integration_helpers.py::test_module_import`
   (similarity: 0.85)

1. `netra_backend\tests\test_database_manager_managers.py::test_module_import`
   ↔ `netra_backend\tests\integration\test_circuit_breaker_cascade_core.py::test_module_import`
   (similarity: 0.85)

1. `netra_backend\tests\test_database_manager_managers.py::test_module_import`
   ↔ `netra_backend\tests\integration\test_circuit_breaker_cascade_fixtures.py::test_module_import`
   (similarity: 0.85)

1. `netra_backend\tests\test_database_manager_managers.py::test_module_import`
   ↔ `netra_backend\tests\integration\test_circuit_breaker_cascade_helpers.py::test_module_import`
   (similarity: 0.85)

1. `netra_backend\tests\test_database_manager_managers.py::test_module_import`
   ↔ `netra_backend\tests\integration\test_concurrent_user_auth_load_core.py::test_module_import`
   (similarity: 0.85)

1. `netra_backend\tests\test_database_manager_managers.py::test_module_import`
   ↔ `netra_backend\tests\integration\test_concurrent_user_auth_load_helpers.py::test_module_import`
   (similarity: 0.85)

1. `netra_backend\tests\test_database_manager_managers.py::test_module_import`
   ↔ `netra_backend\tests\integration\test_core_features_integration_core.py::test_module_import`
   (similarity: 0.85)

1. `netra_backend\tests\test_database_manager_managers.py::test_module_import`
   ↔ `netra_backend\tests\integration\test_core_features_integration_helpers.py::test_module_import`
   (similarity: 0.85)

1. `netra_backend\tests\test_database_manager_managers.py::test_module_import`
   ↔ `netra_backend\tests\integration\test_critical_integration_core.py::test_module_import`
   (similarity: 0.85)

1. `netra_backend\tests\test_database_manager_managers.py::test_module_import`
   ↔ `netra_backend\tests\integration\test_database_transaction_coordination_core.py::test_module_import`
   (similarity: 0.85)

## Highly Similar Tests

These test pairs are highly similar and might benefit from refactoring:

- `netra_backend\tests\test_admin.py::test_set_log_table_success`
  ↔ `netra_backend\tests\test_admin.py::test_add_log_table_success`
  (similarity: 0.996)

- `netra_backend\tests\test_admin.py::test_set_log_table_success`
  ↔ `netra_backend\tests\test_admin.py::test_remove_log_table_success`
  (similarity: 0.944)

- `netra_backend\tests\test_admin.py::test_set_log_table_success`
  ↔ `netra_backend\tests\test_admin.py::test_set_default_log_table_for_context_success`
  (similarity: 0.908)

- `netra_backend\tests\test_admin.py::test_set_log_table_not_available`
  ↔ `netra_backend\tests\test_admin.py::test_set_time_period_not_available`
  (similarity: 0.982)

- `netra_backend\tests\test_admin.py::test_set_log_table_not_available`
  ↔ `netra_backend\tests\test_admin.py::test_set_default_log_table_for_context_table_not_available`
  (similarity: 0.989)

- `netra_backend\tests\test_admin.py::test_add_log_table_success`
  ↔ `netra_backend\tests\test_admin.py::test_add_log_table_already_exists`
  (similarity: 0.944)

- `netra_backend\tests\test_admin.py::test_add_log_table_success`
  ↔ `netra_backend\tests\test_admin.py::test_remove_log_table_success`
  (similarity: 0.936)

- `netra_backend\tests\test_admin.py::test_remove_log_table_success`
  ↔ `netra_backend\tests\test_admin.py::test_remove_default_log_table`
  (similarity: 0.902)

- `netra_backend\tests\test_admin.py::test_remove_log_table_success`
  ↔ `netra_backend\tests\test_admin.py::test_remove_default_log_table_for_context_success`
  (similarity: 0.887)

- `netra_backend\tests\test_admin.py::test_remove_log_table_not_found`
  ↔ `netra_backend\tests\test_admin.py::test_remove_default_log_table`
  (similarity: 0.885)

- `netra_backend\tests\test_admin.py::test_remove_log_table_not_found`
  ↔ `netra_backend\tests\test_admin.py::test_remove_default_log_table_for_context_not_found`
  (similarity: 0.977)

- `netra_backend\tests\test_admin.py::test_remove_default_log_table`
  ↔ `netra_backend\tests\test_admin.py::test_remove_default_log_table_for_context_success`
  (similarity: 0.826)

- `netra_backend\tests\test_admin.py::test_remove_default_log_table`
  ↔ `netra_backend\tests\test_admin.py::test_remove_default_log_table_for_context_not_found`
  (similarity: 0.864)

- `netra_backend\tests\test_admin.py::test_set_time_period_success`
  ↔ `netra_backend\tests\test_admin.py::test_set_time_period_not_available`
  (similarity: 0.804)

- `netra_backend\tests\test_admin.py::test_set_default_log_table_for_context_success`
  ↔ `netra_backend\tests\test_admin.py::test_remove_default_log_table_for_context_success`
  (similarity: 0.951)

- `netra_backend\tests\test_admin.py::test_set_default_log_table_for_context_table_not_available`
  ↔ `netra_backend\tests\test_admin.py::test_remove_default_log_table_for_context_not_found`
  (similarity: 0.93)

- `netra_backend\tests\test_config_central_usage.py::test_config_consistency_across_modules`
  ↔ `netra_backend\tests\test_os_environ_violations.py::test_env_access_patterns_consistency`
  (similarity: 0.814)

- `netra_backend\tests\test_config_isolation_patterns.py::test_no_hardcoded_config_values`
  ↔ `netra_backend\tests\test_os_environ_violations.py::test_justified_env_access_has_markers`
  (similarity: 0.822)

- `netra_backend\tests\test_config_isolation_patterns.py::test_no_hardcoded_config_values`
  ↔ `netra_backend\tests\test_os_environ_violations.py::test_env_access_patterns_consistency`
  (similarity: 0.82)

- `netra_backend\tests\test_config_isolation_patterns.py::test_config_initialization_order`
  ↔ `netra_backend\tests\test_os_environ_violations.py::test_justified_env_access_has_markers`
  (similarity: 0.81)
