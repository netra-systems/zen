# MRO Analysis Report: Data SubAgent Module
Generated: 2025-09-04T12:16:34.326697
Location: netra_backend/app/agents/data_sub_agent/

## Summary Statistics
- Total Python files analyzed: 65
- Total classes found: 88
- Classes with inheritance: 18
- Unique base classes: 9

## Current Class Hierarchy

### Base Classes and Their Children:
- **ABC**
  - analysis_engine.ModernAnalysisEngine (netra_backend\app\agents\data_sub_agent\analysis_engine.py:42)
  - metrics_analyzer.MetricsAnalyzer (netra_backend\app\agents\data_sub_agent\metrics_analyzer.py:41)
  - query_builder.QueryBuilder (netra_backend\app\agents\data_sub_agent\query_builder.py:37)
- **AgentError**
  - error_types.DataSubAgentError (netra_backend\app\agents\data_sub_agent\error_types.py:13)
- **BaseAgent**
  - data_sub_agent.DataSubAgent (netra_backend\app\agents\data_sub_agent\data_sub_agent.py:38)
  - data_sub_agent_old.DataSubAgent (netra_backend\app\agents\data_sub_agent\data_sub_agent_old.py:43)
- **BaseModel**
  - models.BatchProcessingResult (netra_backend\app\agents\data_sub_agent\models.py:32)
  - models.CacheMetrics (netra_backend\app\agents\data_sub_agent\models.py:50)
  - models.DataValidationResult (netra_backend\app\agents\data_sub_agent\models.py:68)
  - models.StreamProcessingMetrics (netra_backend\app\agents\data_sub_agent\models.py:79)
- **DataFetchingCore**
  - data_fetching_operations.DataFetchingOperations (netra_backend\app\agents\data_sub_agent\data_fetching_operations.py:29)
- **DataFetchingOperations**
  - data_fetching_validation.DataFetchingValidation (netra_backend\app\agents\data_sub_agent\data_fetching_validation.py:30)
- **DataFetchingValidation**
  - data_fetching.DataFetching (netra_backend\app\agents\data_sub_agent\data_fetching.py:142)
- **DataSubAgentError**
  - error_types.ClickHouseQueryError (netra_backend\app\agents\data_sub_agent\error_types.py:34)
  - error_types.DataFetchingError (netra_backend\app\agents\data_sub_agent\error_types.py:50)
  - error_types.MetricsCalculationError (netra_backend\app\agents\data_sub_agent\error_types.py:66)
- **Protocol**
  - agent_cache.CacheStorageProtocol (netra_backend\app\agents\data_sub_agent\agent_cache.py:62)
  - clickhouse_operations.RedisManagerProtocol (netra_backend\app\agents\data_sub_agent\clickhouse_operations.py:52)

## ⚠️ DUPLICATE CLASS NAMES FOUND (3 duplicates)
- **CacheMetrics** found in:
  - netra_backend\app\agents\data_sub_agent\agent_cache.py
  - netra_backend\app\agents\data_sub_agent\models.py
- **DataProcessor** found in:
  - netra_backend\app\agents\data_sub_agent\agent_data_processing.py
  - netra_backend\app\agents\data_sub_agent\core\data_processor.py
- **DataSubAgent** found in:
  - netra_backend\app\agents\data_sub_agent\data_sub_agent.py
  - netra_backend\app\agents\data_sub_agent\data_sub_agent_old.py

## 🔍 ExecutionEngine Implementations (3 found)
- **DataFetchingExecutionEngine** in netra_backend\app\agents\data_sub_agent\data_fetching.py:46
  - Inherits from: None
  - Methods: 4 defined
- **DataSubAgentExecutionEngine** in netra_backend\app\agents\data_sub_agent\execution_engine.py:60
  - Inherits from: None
  - Methods: 13 defined
- **ExecutionEngine** in netra_backend\app\agents\data_sub_agent\execution_engine.py:188
  - Inherits from: None
  - Methods: 4 defined

## Method Override Analysis
### Most Overridden Methods:
- **__init__**: overridden in 62 classes
- **get_health_status**: overridden in 16 classes
- **_create_retry_config**: overridden in 9 classes
- **_format_time_range**: overridden in 7 classes
- **_create_circuit_config**: overridden in 5 classes
- **_create_success_result**: overridden in 4 classes
- **_build_anomaly_query**: overridden in 4 classes
- **_create_circuit_breaker_config**: overridden in 4 classes
- **_build_performance_query**: overridden in 4 classes
- **_init_modern_components**: overridden in 3 classes

## Detailed Class Inventory

### netra_backend\app\agents\data_sub_agent\agent_anomaly_processing.py
- **AnomalyProcessor** (line 14)
  - Methods: __init__, convert_anomaly_details, _process_anomaly_item, _create_anomaly_detail, _build_anomaly_detail ... (+10 more)

### netra_backend\app\agents\data_sub_agent\agent_cache.py
- **CacheMetrics** (line 34)
  - Methods: record_hit, record_miss, _update_average_time
- **CacheStorageProtocol** (line 62)
  - Inherits: Protocol
  - Methods: 
- **DataSubAgentCacheManager** (line 70)
  - Methods: __init__, _init_modern_components, _init_reliability_manager, _create_circuit_config, _create_retry_config ... (+18 more)

### netra_backend\app\agents\data_sub_agent\agent_corpus_operations.py
- **CorpusOperations** (line 12)
  - Methods: __init__, _compile_corpus_insights, _generate_corpus_summary, _collect_summary_components

### netra_backend\app\agents\data_sub_agent\agent_data_processing.py
- **DataProcessor** (line 9)
  - Methods: __init__, _validate_data, _create_base_transform_result, _should_parse_json_content, _safe_json_parse

### netra_backend\app\agents\data_sub_agent\agent_execution.py
- **ExecutionManager** (line 25)
  - Methods: __init__, _handle_execution_failure, _create_execution_engine, _create_operation_modules, _create_data_operations ... (+14 more)

### netra_backend\app\agents\data_sub_agent\analysis_engine.py
- **ModernAnalysisEngine** (line 42)
  - Inherits: ABC
  - Methods: __init__, _get_operation_method_map, calculate_statistics, detect_trend, detect_seasonality ... (+2 more)
- **AnalysisEngine** (line 183)
  - Methods: __init__, calculate_statistics, detect_trend, detect_seasonality, identify_outliers ... (+1 more)

### netra_backend\app\agents\data_sub_agent\analysis_engine_helpers.py
- **StatisticsHelpers** (line 15)
  - Methods: _empty_statistics, _compute_comprehensive_stats, _calculate_basic_stats, _calculate_central_tendency, _calculate_spread_measures ... (+2 more)
- **TrendHelpers** (line 80)
  - Methods: _perform_trend_analysis, _compute_trend_parameters, _prepare_trend_data, _convert_to_numeric_arrays, _normalize_time_data ... (+2 more)
- **SeasonalityHelpers** (line 149)
  - Methods: _perform_seasonality_analysis, _validate_and_analyze_seasonality, _group_by_hour, _analyze_seasonality_patterns, _calculate_daily_pattern_metrics ... (+3 more)
- **OutlierHelpers** (line 220)
  - Methods: _has_sufficient_data_for_outliers, _apply_outlier_detection_method, _identify_iqr_outliers, _identify_zscore_outliers

### netra_backend\app\agents\data_sub_agent\analysis_operations.py
- **AnalysisOperations** (line 19)
  - Methods: __init__

### netra_backend\app\agents\data_sub_agent\anomaly_detection.py
- **AnomalyDetectionOperations** (line 9)
  - Methods: __init__, _handle_anomaly_result, _build_anomaly_query, _delegate_anomaly_query_build, _create_anomaly_cache_key ... (+13 more)

### netra_backend\app\agents\data_sub_agent\clickhouse_operations.py
- **QueryContext** (line 37)
  - Methods: __post_init__
- **RedisManagerProtocol** (line 52)
  - Inherits: Protocol
  - Methods: 
- **ModernClickHouseOperations** (line 64)
  - Methods: __init__, _create_reliability_manager, _create_circuit_config, _create_retry_config, _initialize_performance_metrics ... (+27 more)

### netra_backend\app\agents\data_sub_agent\clickhouse_recovery.py
- **ClickHouseRecoveryManager** (line 18)
  - Methods: __init__, _create_error_context, _build_error_data, _create_success_result, _simplify_query ... (+5 more)

### netra_backend\app\agents\data_sub_agent\configuration_manager.py
- **DataSubAgentConfigurationManager** (line 20)
  - Methods: create_legacy_circuit_breaker_config, create_legacy_retry_config, create_modern_reliability_manager, create_modern_circuit_config, create_modern_retry_config ... (+1 more)

### netra_backend\app\agents\data_sub_agent\core\anomaly_detector.py
- **AnomalyDetector** (line 15)
  - Methods: __init__, detect_anomalies, _extract_metric_values, _detect_zscore_anomalies, _detect_iqr_anomalies ... (+11 more)

### netra_backend\app\agents\data_sub_agent\core\data_analysis_core.py
- **DataAnalysisCore** (line 26)
  - Methods: __init__, _build_performance_query, _build_trend_query, _build_anomaly_query, _build_cost_query ... (+10 more)

### netra_backend\app\agents\data_sub_agent\core\data_processor.py
- **DataProcessor** (line 14)
  - Methods: __init__, _validate_analysis_type, _validate_timeframe, _validate_metrics, _validate_filters ... (+5 more)

### netra_backend\app\agents\data_sub_agent\correlation_analysis.py
- **CorrelationAnalysisOperations** (line 9)
  - Methods: __init__, _validate_metrics_for_correlation, _format_pair_correlation_result, _build_correlation_query, _process_correlation_data ... (+20 more)

### netra_backend\app\agents\data_sub_agent\correlation_analyzer.py
- **CorrelationAnalyzer** (line 26)
  - Methods: __init__, _initialize_core_components, _initialize_reliability_manager, _register_health_monitoring, _validate_correlation_params ... (+15 more)

### netra_backend\app\agents\data_sub_agent\cost_optimizer.py
- **CostOptimizer** (line 16)
  - Methods: __init__, _analyze_cost_efficiency, _identify_optimization_opportunities, _get_optimization_strategies, _calculate_savings_potential ... (+2 more)

### netra_backend\app\agents\data_sub_agent\data_fetching.py
- **DataFetchingExecutionEngine** (line 46)
  - Methods: __init__, _create_execution_engine, _create_reliability_manager, _validate_operation_access
- **DataFetching** (line 142)
  - Inherits: DataFetchingValidation
  - Methods: __init__, get_health_status

### netra_backend\app\agents\data_sub_agent\data_fetching_core.py
- **DataFetchingCore** (line 32)
  - Methods: __init__, _init_base_config, _init_redis_connection, _validate_table_name, _format_schema_result ... (+2 more)

### netra_backend\app\agents\data_sub_agent\data_fetching_operations.py
- **DataFetchingOperations** (line 29)
  - Inherits: DataFetchingCore
  - Methods: _build_availability_query, _build_availability_cache_key, _process_availability_result, _build_unavailable_response, _build_available_response ... (+5 more)

### netra_backend\app\agents\data_sub_agent\data_fetching_recovery.py
- **DataFetchingRecoveryManager** (line 16)
  - Methods: __init__, _create_error_context, _calculate_reduced_range, _build_cache_key, _create_daily_data_points ... (+3 more)

### netra_backend\app\agents\data_sub_agent\data_fetching_validation.py
- **DataFetchingValidation** (line 30)
  - Inherits: DataFetchingOperations
  - Methods: _init_validation_result, _add_workload_validation_issues, _add_metrics_validation_issues

### netra_backend\app\agents\data_sub_agent\data_operations.py
- **DataOperations** (line 41)
  - Methods: __init__, _assign_dependencies, _initialize_all_components, _initialize_operation_modules, _initialize_modern_components ... (+11 more)

### netra_backend\app\agents\data_sub_agent\data_processing_operations.py
- **DataProcessingOperations** (line 15)
  - Methods: __init__, _create_no_data_response, _calculate_base_metrics, _create_base_result, _format_time_range ... (+17 more)

### netra_backend\app\agents\data_sub_agent\data_sub_agent.py
- **DataSubAgent** (line 38)
  - Inherits: BaseAgent
  - Methods: __init__, _init_data_analysis_core, _get_tool_name_for_analysis_type, _build_insights_prompt, _prepare_final_result ... (+4 more)

### netra_backend\app\agents\data_sub_agent\data_sub_agent_core.py
- **DataSubAgentCore** (line 34)
  - Methods: __init__, _init_core_components, _init_redis_connection, create_reliability_manager, _create_circuit_breaker_config ... (+6 more)

### netra_backend\app\agents\data_sub_agent\data_sub_agent_helpers.py
- **DataSubAgentHelpers** (line 38)
  - Methods: __init__, _init_component_managers, _init_helper_managers, _init_configuration_managers, clear_cache ... (+5 more)

### netra_backend\app\agents\data_sub_agent\data_sub_agent_old.py
- **DataSubAgent** (line 43)
  - Inherits: BaseAgent
  - Methods: __init__, _init_helper_modules, _extract_analysis_request, _get_tool_name_for_analysis_type, _build_insights_prompt ... (+1 more)

### netra_backend\app\agents\data_sub_agent\data_validator.py
- **DataValidator** (line 16)
  - Methods: __init__, validate_analysis_request, validate_raw_data, validate_analysis_result, _validate_timeframe_format ... (+5 more)

### netra_backend\app\agents\data_sub_agent\delegation.py
- **ModernAgentDelegation** (line 31)
  - Methods: __init__, _initialize_modern_components, _create_circuit_breaker_config, _create_retry_config, _enrich_data_locally ... (+4 more)

### netra_backend\app\agents\data_sub_agent\delegation_helper.py
- **DataSubAgentDelegationHelper** (line 12)
  - Methods: get_delegation_methods, get_process_delegation_methods, get_analysis_delegation_methods, resolve_delegation_method

### netra_backend\app\agents\data_sub_agent\error_types.py
- **DataSubAgentError** (line 13)
  - Inherits: AgentError
  - Methods: __init__
- **ClickHouseQueryError** (line 34)
  - Inherits: DataSubAgentError
  - Methods: __init__
- **DataFetchingError** (line 50)
  - Inherits: DataSubAgentError
  - Methods: __init__
- **MetricsCalculationError** (line 66)
  - Inherits: DataSubAgentError
  - Methods: __init__

### netra_backend\app\agents\data_sub_agent\execution_analysis.py
- **AnalysisRouter** (line 7)
  - Methods: __init__, _has_anomalies

### netra_backend\app\agents\data_sub_agent\execution_core.py
- **ExecutionCore** (line 30)
  - Methods: __init__, _init_modern_components, _init_reliability_manager, _create_circuit_config, _create_retry_config ... (+7 more)

### netra_backend\app\agents\data_sub_agent\execution_engine.py
- **DataSubAgentExecutionEngine** (line 60)
  - Methods: __init__, _init_dependencies, _assign_data_components, _assign_manager_components, _init_modern_execution_components ... (+8 more)
- **ExecutionEngine** (line 188)
  - Methods: __init__, _expose_legacy_components, _create_legacy_execution_context, get_fallback_health_status

### netra_backend\app\agents\data_sub_agent\execution_fallbacks.py
- **ExecutionFallbackHandler** (line 9)
  - Methods: __init__, _init_fallback_handler, _update_fallback_metadata, _create_fallback_base_result, _parse_llm_fallback_response ... (+15 more)

### netra_backend\app\agents\data_sub_agent\execution_parameters.py
- **ParameterProcessor** (line 7)
  - Methods: __init__, extract_analysis_params, _extract_user_intent_dict, _build_analysis_params_dict, _build_params_from_object ... (+7 more)

### netra_backend\app\agents\data_sub_agent\extended_operations.py
- **ExtendedOperations** (line 12)
  - Methods: __init__, _generate_cache_key, _generate_timestamp, _generate_persistence_id, _create_enrichment_metadata ... (+7 more)

### netra_backend\app\agents\data_sub_agent\fallback_helpers.py
- **FallbackDataHelpers** (line 17)
  - Methods: extract_baseline_metrics, create_performance_from_baseline, extract_hourly_distribution, _extract_hour_from_activity, _parse_timestamp_hour ... (+11 more)
- **FallbackSystemIntegrations** (line 162)
  - Methods: _build_baseline_metrics, _build_system_patterns

### netra_backend\app\agents\data_sub_agent\fallback_providers.py
- **ModernFallbackDataProvider** (line 27)
  - Methods: __init__, _initialize_reliability_manager, _create_circuit_breaker_config, _create_retry_config, _get_operation_map ... (+8 more)

### netra_backend\app\agents\data_sub_agent\insights_performance_analyzer.py
- **PerformanceInsightsAnalyzer** (line 12)
  - Methods: __init__, _add_latency_degradation_insight, _create_latency_degradation_insight, _add_performance_recommendation, _add_cost_increase_insight ... (+9 more)

### netra_backend\app\agents\data_sub_agent\insights_recommendations.py
- **InsightsRecommendationsGenerator** (line 12)
  - Methods: _add_all_recommendation_types, _group_insights_by_type, _add_insight_to_group, _add_performance_recommendations, _add_degradation_recommendations ... (+4 more)

### netra_backend\app\agents\data_sub_agent\insights_usage_analyzer.py
- **UsageInsightsAnalyzer** (line 12)
  - Methods: __init__, _is_off_hours, _add_off_hours_insight, _add_scheduling_recommendation, _check_cost_efficiency ... (+5 more)

### netra_backend\app\agents\data_sub_agent\llm_query_detector.py
- **LLMQueryDetector** (line 13)
  - Methods: is_likely_llm_generated, _collect_llm_indicators, _collect_non_builder_patterns, _is_from_query_builder, _get_builder_markers ... (+24 more)

### netra_backend\app\agents\data_sub_agent\metric_comparison_analyzer.py
- **MetricComparisonAnalyzer** (line 9)
  - Methods: __init__, _build_summary_stats_query, _format_summary_stats, _create_comparison_result, _filter_valid_metrics ... (+4 more)

### netra_backend\app\agents\data_sub_agent\metric_distribution_analyzer.py
- **MetricDistributionAnalyzer** (line 9)
  - Methods: __init__, _build_distribution_query, _create_empty_distribution_result, _process_distribution_data, _extract_values ... (+5 more)

### netra_backend\app\agents\data_sub_agent\metric_percentile_analyzer.py
- **MetricPercentileAnalyzer** (line 9)
  - Methods: __init__, _build_percentiles_query, _create_empty_percentiles_result, _format_percentiles_result, _extract_percentile_values ... (+2 more)

### netra_backend\app\agents\data_sub_agent\metric_seasonality_analyzer.py
- **MetricSeasonalityAnalyzer** (line 9)
  - Methods: __init__, _build_seasonality_query, _create_insufficient_seasonality_data_result, _analyze_seasonality_patterns, _extract_timestamps ... (+10 more)

### netra_backend\app\agents\data_sub_agent\metric_trend_analyzer.py
- **MetricTrendAnalyzer** (line 9)
  - Methods: __init__, _build_trend_query, _create_insufficient_trend_data_result, _analyze_trend_patterns, _extract_timestamps ... (+5 more)

### netra_backend\app\agents\data_sub_agent\metrics_analyzer.py
- **MetricsAnalyzer** (line 41)
  - Inherits: ABC
  - Methods: __init__, _init_base_interface, _init_all_components, _initialize_specialized_analyzers, _create_primary_analyzers ... (+21 more)

### netra_backend\app\agents\data_sub_agent\metrics_recovery.py
- **MetricsRecoveryManager** (line 15)
  - Methods: __init__, _create_error_context, _prepare_calculation_error, _add_approximation_metadata, _extract_numeric_values ... (+20 more)

### netra_backend\app\agents\data_sub_agent\models.py
- **BatchProcessingResult** (line 32)
  - Inherits: BaseModel
  - Methods: calculate_success_rate
- **CacheMetrics** (line 50)
  - Inherits: BaseModel
  - Methods: calculate_miss_rate
- **DataValidationResult** (line 68)
  - Inherits: BaseModel
  - Methods: 
- **StreamProcessingMetrics** (line 79)
  - Inherits: BaseModel
  - Methods: 

### netra_backend\app\agents\data_sub_agent\modern_execution_interface.py
- **DataSubAgentModernExecution** (line 18)
  - Methods: __init__, _is_data_related_request, _convert_legacy_result_to_dict

### netra_backend\app\agents\data_sub_agent\performance_analysis.py
- **PerformanceAnalysisOperations** (line 9)
  - Methods: __init__, _build_query_params, _handle_performance_result, _determine_aggregation_level, _calculate_time_difference ... (+10 more)

### netra_backend\app\agents\data_sub_agent\performance_analysis_helpers.py
- **PerformanceAnalysisHelpers** (line 15)
  - Methods: __init__, extract_metric_values, _extract_latency_values, _extract_throughput_values, _extract_error_rate_values ... (+25 more)

### netra_backend\app\agents\data_sub_agent\performance_analysis_validation.py
- **PerformanceAnalysisValidator** (line 17)
  - Methods: __init__, _validate_time_range, _validate_workload_id_format, create_legacy_state, calculate_time_range_hours
- **PerformanceQueryBuilder** (line 95)
  - Methods: __init__, build_performance_query, build_cache_key, determine_aggregation_level
- **PerformanceErrorHandlers** (line 123)
  - Methods: create_no_data_response, create_error_response_from_exception, get_performance_components_health

### netra_backend\app\agents\data_sub_agent\performance_analyzer.py
- **PerformanceAnalysisContext** (line 48)
  - Methods: 
- **ModernPerformanceAnalyzer** (line 57)
  - Methods: __init__, _init_legacy_mode, _create_mock_query_builder, _create_mock_analysis_engine, _create_mock_clickhouse_ops ... (+32 more)

### netra_backend\app\agents\data_sub_agent\performance_data_processor.py
- **PerformanceDataProcessor** (line 7)
  - Methods: __init__, process_performance_data, _extract_metric_values, _add_advanced_analytics, _build_performance_result ... (+8 more)

### netra_backend\app\agents\data_sub_agent\query_builder.py
- **QueryExecutionRequest** (line 20)
  - Methods: 
- **QueryExecutionMetrics** (line 29)
  - Methods: 
- **QueryBuilder** (line 37)
  - Inherits: ABC
  - Methods: __init__, _init_query_registry, _init_performance_tracking, _extract_request_from_context, _validate_query_request ... (+15 more)

### netra_backend\app\agents\data_sub_agent\query_operations.py
- **QueryOperations** (line 7)
  - Methods: build_performance_metrics_query, _get_time_function, _build_workload_filter, _build_performance_select_clause, _build_latency_fields ... (+23 more)

### netra_backend\app\agents\data_sub_agent\schema_cache.py
- **SchemaCache** (line 17)
  - Methods: __init__, _get_default_schema_for_table, _get_default_workload_events_schema, invalidate_cache, is_available ... (+1 more)

### netra_backend\app\agents\data_sub_agent\usage_analysis.py
- **UsageAnalysisOperations** (line 8)
  - Methods: __init__, _handle_usage_result, _build_usage_patterns_query, _process_usage_patterns

### netra_backend\app\agents\data_sub_agent\usage_pattern_analyzer.py
- **UsagePatternAnalyzer** (line 8)
  - Methods: __init__, _build_usage_query, _build_usage_cache_key, _create_no_usage_data_response, _aggregate_usage_patterns ... (+18 more)

### netra_backend\app\agents\data_sub_agent\usage_pattern_processor.py
- **UsagePatternProcessor** (line 24)
  - Methods: __init__, _init_base_interface, _init_modern_components, _extract_data_from_context, _extract_days_back_from_context ... (+4 more)
- **UsagePatternProcessorCore** (line 122)
  - Methods: process_patterns_sync, _aggregate_daily_patterns, _aggregate_hourly_patterns, _create_empty_daily_pattern, _create_empty_hourly_pattern ... (+7 more)

## Consolidation Targets
### High Priority (Duplicate Names):
- Consolidate all CacheMetrics implementations
- Consolidate all DataProcessor implementations
- Consolidate all DataSubAgent implementations

### ExecutionEngine Consolidation:
- Found 3 ExecutionEngine variants - consolidate to ONE
- Canonical target: execution_engine_consolidated.py

### Files with Multiple Classes (Potential Split Targets):
- netra_backend\app\agents\data_sub_agent\analysis_engine_helpers.py: 4 classes
- netra_backend\app\agents\data_sub_agent\error_types.py: 4 classes
- netra_backend\app\agents\data_sub_agent\models.py: 4 classes
- netra_backend\app\agents\data_sub_agent\agent_cache.py: 3 classes
- netra_backend\app\agents\data_sub_agent\clickhouse_operations.py: 3 classes
- netra_backend\app\agents\data_sub_agent\performance_analysis_validation.py: 3 classes
- netra_backend\app\agents\data_sub_agent\query_builder.py: 3 classes
- netra_backend\app\agents\data_sub_agent\analysis_engine.py: 2 classes
- netra_backend\app\agents\data_sub_agent\data_fetching.py: 2 classes
- netra_backend\app\agents\data_sub_agent\execution_engine.py: 2 classes
