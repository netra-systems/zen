# Test Size Compliance Report

## Summary

- **Total test files scanned:** 1365
- **Files exceeding 300 line limit:** 569
- **Functions exceeding 8 line limit:** 1888
- **Total violations:** 2457

## Violations

### File Size Violations

| File | Lines | Limit | Fix Suggestion |
|------|-------|-------|----------------|
| tests\unified\e2e\test_oauth_endpoint_validation_real.py | 490 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_backend_frontend_state_synchronization.py | 758 | 300 | Split into 3 focused test modules |
| tests\conftest.py | 305 | 300 | Split into 2 focused test modules |
| tests\e2e\test_spike_recovery.py | 1242 | 300 | Split into 5 focused test modules |
| app\tests\unit\test_agent_lifecycle.py | 462 | 300 | Split into 2 focused test modules |
| tests\unified\websocket\test_websocket_resilience_recovery.py | 868 | 300 | Split into 3 focused test modules |
| tests\unified\e2e\test_websocket_auth_multiservice.py | 545 | 300 | Split into 2 focused test modules |
| app\tests\websocket\test_websocket_integration_performance.py | 316 | 300 | Split into 2 focused test modules |
| tests\integration\test_startup_system.py | 431 | 300 | Split into 2 focused test modules |
| tests\unified\test_supervisor_pattern_compliance.py | 394 | 300 | Split into 2 focused test modules |
| app\tests\clickhouse\test_query_correctness.py | 448 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\staging_test_helpers.py | 327 | 300 | Split into 2 focused test modules |
| tests\unified\websocket\test_concurrent_connections.py | 466 | 300 | Split into 2 focused test modules |
| tests\e2e\websocket_resilience\test_5_backend_service_restart.py | 1047 | 300 | Split into 4 focused test modules |
| test_framework\fake_test_detector.py | 850 | 300 | Split into 3 focused test modules |
| app\tests\integration\test_message_flow_errors.py | 595 | 300 | Split into 2 focused test modules |
| app\tests\test_database_connectivity_improvements.py | 598 | 300 | Split into 2 focused test modules |
| test_framework\test_user_journeys_extended.py | 497 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\session_sync_helpers.py | 488 | 300 | Split into 2 focused test modules |
| app\tests\integration\test_message_flow_performance.py | 527 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_agent_orchestration_runner.py | 369 | 300 | Split into 2 focused test modules |
| test_framework\gcp_integration\log_reader.py | 394 | 300 | Split into 2 focused test modules |
| app\tests\routes\test_synthetic_data_generation.py | 356 | 300 | Split into 2 focused test modules |
| app\tests\integration\staging\test_staging_multi_service_startup_sequence.py | 369 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_session_state_synchronization.py | 800 | 300 | Split into 3 focused test modules |
| tests\unified\e2e\test_error_propagation_real.py | 1356 | 300 | Split into 5 focused test modules |
| app\tests\e2e\thread_test_fixtures.py | 415 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_health_cascade.py | 449 | 300 | Split into 2 focused test modules |
| app\tests\integration\test_service_health_integration.py | 349 | 300 | Split into 2 focused test modules |
| test_framework\test_config.py | 347 | 300 | Split into 2 focused test modules |
| tests\unified\test_fallback_mechanisms.py | 304 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_multi_agent_collaboration_response.py | 744 | 300 | Split into 3 focused test modules |
| tests\unified\e2e\test_cors_configuration.py | 415 | 300 | Split into 2 focused test modules |
| app\tests\helpers\supervisor_test_helpers.py | 451 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_jwt_cross_service.py | 385 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_agent_write_review_refine_integration.py | 381 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_jwt_cross_service_validation.py | 671 | 300 | Split into 3 focused test modules |
| tests\unified\websocket\test_ui_layer_timing.py | 573 | 300 | Split into 2 focused test modules |
| app\tests\services\test_security_service_oauth.py | 336 | 300 | Split into 2 focused test modules |
| app\tests\fixtures\database_test_fixtures.py | 315 | 300 | Split into 2 focused test modules |
| app\tests\database\test_repositories_comprehensive.py | 521 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_websocket_message_guarantee_integration.py | 481 | 300 | Split into 2 focused test modules |
| app\tests\patterns\async_test_isolation_improved.py | 322 | 300 | Split into 2 focused test modules |
| tests\e2e\websocket_resilience\test_7_heartbeat_validation.py | 572 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_websocket_service_discovery.py | 311 | 300 | Split into 2 focused test modules |
| app\tests\integration\test_auth_service_integration.py | 414 | 300 | Split into 2 focused test modules |
| tests\unified\agent_test_harness.py | 308 | 300 | Split into 2 focused test modules |
| app\tests\critical\test_websocket_agent_startup.py | 351 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_staging_websocket_messaging.py | 503 | 300 | Split into 2 focused test modules |
| tests\e2e\test_cors_comprehensive_e2e.py | 310 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_websocket_db_session_handling.py | 700 | 300 | Split into 3 focused test modules |
| tests\unified\e2e\test_real_agent_pipeline.py | 329 | 300 | Split into 2 focused test modules |
| tests\unified\jwt_token_helpers.py | 444 | 300 | Split into 2 focused test modules |
| app\tests\integration\test_transaction_coordination_integration.py | 617 | 300 | Split into 3 focused test modules |
| tests\unified\e2e\test_auth_service_health_check_integration.py | 433 | 300 | Split into 2 focused test modules |
| app\tests\integration\test_websocket_state_recovery.py | 878 | 300 | Split into 3 focused test modules |
| app\tests\clickhouse\test_performance_edge_cases.py | 357 | 300 | Split into 2 focused test modules |
| app\tests\test_websocket_comprehensive.py | 459 | 300 | Split into 2 focused test modules |
| tests\unified\test_thread_management.py | 339 | 300 | Split into 2 focused test modules |
| app\tests\integration\test_configuration_integration.py | 318 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_websocket_jwt_auth_real.py | 510 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_websocket_message_format_validation.py | 454 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_enterprise_sso.py | 301 | 300 | Split into 2 focused test modules |
| tests\e2e\test_soak_testing.py | 929 | 300 | Split into 4 focused test modules |
| tests\unified\e2e\test_llm_quality_gate_integration.py | 346 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_oauth_real_service_flow.py | 417 | 300 | Split into 2 focused test modules |
| app\tests\performance\test_agent_load_stress.py | 335 | 300 | Split into 2 focused test modules |
| tests\integration\test_dev_launcher_errors.py | 620 | 300 | Split into 3 focused test modules |
| app\tests\agents\test_data_sub_agent_consolidated.py | 563 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_session_sync_validation.py | 393 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_quality_gate_response_validation.py | 489 | 300 | Split into 2 focused test modules |
| app\tests\llm\test_llm_integration_real.py | 343 | 300 | Split into 2 focused test modules |
| app\tests\core\test_json_parsing_helpers_and_edge_cases.py | 324 | 300 | Split into 2 focused test modules |
| app\tests\services\test_quality_gate_integration.py | 376 | 300 | Split into 2 focused test modules |
| test_framework\memory_optimized_executor.py | 416 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_health_check_cascade.py | 384 | 300 | Split into 2 focused test modules |
| app\tests\e2e\conftest.py | 668 | 300 | Split into 3 focused test modules |
| app\tests\integration\test_multi_agent_coordination_init.py | 719 | 300 | Split into 3 focused test modules |
| app\tests\integration\test_gcp_monitoring_routes.py | 336 | 300 | Split into 2 focused test modules |
| app\tests\integration\test_first_message_error_recovery.py | 364 | 300 | Split into 2 focused test modules |
| tests\e2e\websocket_resilience\test_3_message_queuing_disconnection.py | 930 | 300 | Split into 4 focused test modules |
| app\tests\test_database_repository_critical.py | 329 | 300 | Split into 2 focused test modules |
| app\tests\integration\user_flows\test_free_tier_onboarding.py | 306 | 300 | Split into 2 focused test modules |
| app\tests\websocket\test_websocket_reliability_fixes.py | 585 | 300 | Split into 2 focused test modules |
| tests\e2e\test_concurrent_tool_conflicts.py | 1030 | 300 | Split into 4 focused test modules |
| app\tests\unit\test_staging_error_monitor.py | 460 | 300 | Split into 2 focused test modules |
| tests\unified\websocket\test_event_structure_consistency.py | 524 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_complete_oauth_chat_journey.py | 621 | 300 | Split into 3 focused test modules |
| tests\unified\e2e\test_auth_websocket_handshake_integration.py | 316 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_multi_agent_websocket_isolation.py | 365 | 300 | Split into 2 focused test modules |
| app\tests\unit\test_security_middleware.py | 400 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_real_rate_limiting.py | 416 | 300 | Split into 2 focused test modules |
| tests\websocket\test_websocket_integration.py | 589 | 300 | Split into 2 focused test modules |
| app\tests\e2e\test_agent_message_flow.py | 632 | 300 | Split into 3 focused test modules |
| tests\unified\e2e\test_jwt_lifecycle_real.py | 620 | 300 | Split into 3 focused test modules |
| tests\unified\e2e\test_session_persistence_complete.py | 702 | 300 | Split into 3 focused test modules |
| tests\unified\test_websocket_auth_handshake.py | 362 | 300 | Split into 2 focused test modules |
| app\tests\services\test_generation_service_comprehensive.py | 301 | 300 | Split into 2 focused test modules |
| app\tests\integration\test_websocket_end_to_end.py | 394 | 300 | Split into 2 focused test modules |
| tests\e2e\test_db_connection_pool.py | 658 | 300 | Split into 3 focused test modules |
| app\tests\core\test_missing_tests_validation.py | 311 | 300 | Split into 2 focused test modules |
| app\tests\integration\test_dev_auth_cold_start_integration.py | 358 | 300 | Split into 2 focused test modules |
| app\tests\websocket\test_websocket_performance_components.py | 376 | 300 | Split into 2 focused test modules |
| tests\integration\test_dev_launcher_real.py | 571 | 300 | Split into 2 focused test modules |
| app\tests\auth_integration\test_auth_core.py | 325 | 300 | Split into 2 focused test modules |
| app\tests\unified_system\test_health_coordination.py | 489 | 300 | Split into 2 focused test modules |
| tests\integration\test_websocket_auth_handshake_complete_flow.py | 366 | 300 | Split into 2 focused test modules |
| auth_service\tests\utils\test_helpers.py | 331 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_example_prompts_e2e_real_llm.py | 458 | 300 | Split into 2 focused test modules |
| app\tests\core\test_async_function_utilities.py | 326 | 300 | Split into 2 focused test modules |
| app\tests\core\test_circuit_breaker.py | 456 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_websocket_reconnection_auth.py | 518 | 300 | Split into 2 focused test modules |
| test_framework\seed_data_manager.py | 720 | 300 | Split into 3 focused test modules |
| tests\unified\e2e\cache_coherence_helpers.py | 340 | 300 | Split into 2 focused test modules |
| tests\e2e\test_startup_comprehensive_e2e.py | 518 | 300 | Split into 2 focused test modules |
| tests\unified\test_auth_backend_database_consistency.py | 384 | 300 | Split into 2 focused test modules |
| app\tests\websocket\test_websocket_bidirectional_types.py | 421 | 300 | Split into 2 focused test modules |
| tests\unified\websocket\test_auth_validation.py | 435 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_authentication_token_flow.py | 615 | 300 | Split into 3 focused test modules |
| tests\unified\e2e\test_cross_service_session_sync.py | 545 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_websocket_event_completeness.py | 840 | 300 | Split into 3 focused test modules |
| tests\unified\e2e\test_database_connections.py | 304 | 300 | Split into 2 focused test modules |
| app\tests\core\test_alert_manager.py | 318 | 300 | Split into 2 focused test modules |
| app\tests\test_api_error_handling_critical.py | 322 | 300 | Split into 2 focused test modules |
| app\tests\critical\test_config_secrets_manager.py | 381 | 300 | Split into 2 focused test modules |
| app\tests\unit\test_new_user_critical_flows.py | 334 | 300 | Split into 2 focused test modules |
| app\tests\agents\test_supervisor_integration.py | 439 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_cold_start_zero_to_response.py | 335 | 300 | Split into 2 focused test modules |
| app\tests\startup\test_config_validation.py | 317 | 300 | Split into 2 focused test modules |
| app\tests\integration\test_first_time_user_comprehensive_critical.py | 825 | 300 | Split into 3 focused test modules |
| test_framework\unified_orchestrator.py | 455 | 300 | Split into 2 focused test modules |
| tests\e2e\websocket_resilience\test_9_network_interface_switching.py | 408 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_real_websocket_auth_integration.py | 465 | 300 | Split into 2 focused test modules |
| app\tests\critical\test_auth_user_persistence_regression.py | 343 | 300 | Split into 2 focused test modules |
| tests\unified\test_llm_integration.py | 311 | 300 | Split into 2 focused test modules |
| tests\unified\test_resource_usage_integration.py | 308 | 300 | Split into 2 focused test modules |
| app\tests\services\test_synthetic_data_validation.py | 465 | 300 | Split into 2 focused test modules |
| app\tests\unified_system\test_oauth_flow.py | 417 | 300 | Split into 2 focused test modules |
| app\tests\e2e\test_middleware_hook_ordering.py | 309 | 300 | Split into 2 focused test modules |
| app\tests\core\test_config_manager.py | 377 | 300 | Split into 2 focused test modules |
| tests\e2e\test_throughput_delivery_guarantees.py | 310 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_websocket_message_structure.py | 505 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_websocket_jwt_complete.py | 594 | 300 | Split into 2 focused test modules |
| app\tests\e2e\test_thread_context.py | 366 | 300 | Split into 2 focused test modules |
| tests\agents\test_supervisor_websocket_integration.py | 346 | 300 | Split into 2 focused test modules |
| app\tests\integration\test_circuit_breaker_cascade.py | 698 | 300 | Split into 3 focused test modules |
| tests\unified\test_session_persistence.py | 330 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_session_persistence_restart_real.py | 753 | 300 | Split into 3 focused test modules |
| app\tests\unified_system\fixtures.py | 309 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_agent_compensation_integration.py | 366 | 300 | Split into 2 focused test modules |
| app\tests\core\test_error_handling.py | 492 | 300 | Split into 2 focused test modules |
| app\tests\integration\staging\test_staging_clickhouse_http_native_ports.py | 504 | 300 | Split into 2 focused test modules |
| tests\unified\harness_complete.py | 405 | 300 | Split into 2 focused test modules |
| app\tests\integration\test_staging_health_check_integration.py | 378 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_response_persistence_recovery.py | 627 | 300 | Split into 3 focused test modules |
| app\tests\integration\test_message_flow_auth.py | 490 | 300 | Split into 2 focused test modules |
| app\tests\core\test_core_infrastructure_11_20.py | 377 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_multi_tab_session_real.py | 485 | 300 | Split into 2 focused test modules |
| auth_service\tests\integration\test_oauth_flows.py | 520 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_websocket_event_structure.py | 335 | 300 | Split into 2 focused test modules |
| tests\unified\websocket\test_connection_cleanup.py | 568 | 300 | Split into 2 focused test modules |
| app\tests\integration\test_database_pool_integration.py | 354 | 300 | Split into 2 focused test modules |
| test_framework\unified\orchestrator.py | 557 | 300 | Split into 2 focused test modules |
| test_framework\unified\base_interfaces.py | 432 | 300 | Split into 2 focused test modules |
| tests\unified\test_websocket_integration.py | 313 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\payment_billing_helpers.py | 370 | 300 | Split into 2 focused test modules |
| app\tests\e2e\test_middleware_validation_security.py | 301 | 300 | Split into 2 focused test modules |
| app\tests\auth_integration\test_real_auth_integration.py | 417 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_websocket_advanced_integration.py | 414 | 300 | Split into 2 focused test modules |
| app\tests\integration\test_enterprise_features_integration.py | 431 | 300 | Split into 2 focused test modules |
| app\tests\integration\test_staging_auth_service_integration.py | 486 | 300 | Split into 2 focused test modules |
| tests\unified\test_jwt_permission_propagation.py | 409 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_error_propagation_unified.py | 784 | 300 | Split into 3 focused test modules |
| tests\unified\e2e\test_agent_orchestration_real_llm.py | 470 | 300 | Split into 2 focused test modules |
| tests\unified\test_harness.py | 364 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_rate_limiting_complete.py | 806 | 300 | Split into 3 focused test modules |
| app\tests\integration\test_operational_systems_integration.py | 797 | 300 | Split into 3 focused test modules |
| app\tests\integration\test_critical_integration.py | 415 | 300 | Split into 2 focused test modules |
| app\tests\integration\user_flows\test_early_tier_flows.py | 325 | 300 | Split into 2 focused test modules |
| tests\unified\websocket\test_websocket_lifecycle_auth.py | 518 | 300 | Split into 2 focused test modules |
| tests\integration\test_dev_environment_initialization.py | 781 | 300 | Split into 3 focused test modules |
| app\tests\integration\test_supply_research_optimization.py | 622 | 300 | Split into 3 focused test modules |
| app\tests\e2e\multi_constraint_test_helpers.py | 333 | 300 | Split into 2 focused test modules |
| tests\unified\test_agent_startup_coverage_validation.py | 447 | 300 | Split into 2 focused test modules |
| app\tests\services\test_repository_basic_transactions.py | 319 | 300 | Split into 2 focused test modules |
| app\tests\unified_system\test_agent_activation.py | 666 | 300 | Split into 3 focused test modules |
| app\tests\integration\test_background_jobs_integration.py | 535 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_multi_service_integration.py | 621 | 300 | Split into 3 focused test modules |
| app\tests\integration\test_revenue_pipeline_integration.py | 377 | 300 | Split into 2 focused test modules |
| app\tests\critical\test_websocket_message_routing_critical.py | 507 | 300 | Split into 2 focused test modules |
| app\tests\unified_system\test_message_pipeline.py | 488 | 300 | Split into 2 focused test modules |
| tests\unified\test_security_integration.py | 358 | 300 | Split into 2 focused test modules |
| app\tests\agents\test_supervisor_corpus_data.py | 325 | 300 | Split into 2 focused test modules |
| test_framework\staging_testing\endpoint_validator.py | 593 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_agent_tool_atomicity_integration.py | 520 | 300 | Split into 2 focused test modules |
| app\tests\websocket\test_websocket_e2e_complete.py | 419 | 300 | Split into 2 focused test modules |
| tests\unified\test_performance_targets.py | 447 | 300 | Split into 2 focused test modules |
| tests\e2e\websocket_resilience\test_6_rapid_reconnection_flapping.py | 378 | 300 | Split into 2 focused test modules |
| tests\e2e\test_concurrency_isolation_ORIGINAL_BACKUP.py | 1501 | 300 | Split into 6 focused test modules |
| app\tests\critical\test_config_environment_detection.py | 335 | 300 | Split into 2 focused test modules |
| app\tests\unit\test_circuit_breaker_core.py | 333 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_agent_pipeline_real.py | 526 | 300 | Split into 2 focused test modules |
| app\tests\integration\test_system_startup_integration.py | 316 | 300 | Split into 2 focused test modules |
| app\tests\unit\test_rate_limiter_unit.py | 594 | 300 | Split into 2 focused test modules |
| tests\unified\test_import_integrity.py | 438 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_agent_context_accumulation.py | 440 | 300 | Split into 2 focused test modules |
| app\tests\integration\test_first_time_user_permissions.py | 362 | 300 | Split into 2 focused test modules |
| app\tests\services\test_corpus_service_comprehensive.py | 432 | 300 | Split into 2 focused test modules |
| app\tests\startup\test_staged_health_monitor.py | 514 | 300 | Split into 2 focused test modules |
| auth_service\tests\utils\test_client.py | 303 | 300 | Split into 2 focused test modules |
| app\tests\critical\test_config_loader_core.py | 403 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\rate_limiting_advanced.py | 333 | 300 | Split into 2 focused test modules |
| app\tests\integration\test_unified_auth_service.py | 520 | 300 | Split into 2 focused test modules |
| tests\e2e\websocket_resilience\test_1_reconnection_preserves_context.py | 814 | 300 | Split into 3 focused test modules |
| tests\e2e\test_rapid_message_succession.py | 1408 | 300 | Split into 5 focused test modules |
| app\tests\core\test_data_validation_comprehensive.py | 343 | 300 | Split into 2 focused test modules |
| app\tests\integration\test_concurrent_user_auth_load.py | 432 | 300 | Split into 2 focused test modules |
| tests\unified\websocket\test_message_ordering.py | 545 | 300 | Split into 2 focused test modules |
| app\tests\e2e\test_validation_summary.py | 339 | 300 | Split into 2 focused test modules |
| app\tests\e2e\test_thread_agent_integration.py | 425 | 300 | Split into 2 focused test modules |
| tests\unified\test_error_recovery.py | 468 | 300 | Split into 2 focused test modules |
| app\tests\unit\test_async_rate_limiter.py | 342 | 300 | Split into 2 focused test modules |
| app\tests\services\test_supply_research_service_price_calculations.py | 305 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\run_all_e2e_tests.py | 341 | 300 | Split into 2 focused test modules |
| app\tests\examples\test_pattern_examples.py | 413 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_microservice_isolation_validation.py | 994 | 300 | Split into 4 focused test modules |
| tests\unified\test_state_persistence.py | 406 | 300 | Split into 2 focused test modules |
| app\tests\integration\test_first_time_user_critical_journey.py | 810 | 300 | Split into 3 focused test modules |
| tests\unified\test_network_resilience.py | 305 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_websocket_event_propagation_unified.py | 392 | 300 | Split into 2 focused test modules |
| app\tests\agents\test_llm_agent_e2e_integration.py | 316 | 300 | Split into 2 focused test modules |
| tests\test_example_message_integration_final.py | 594 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_disaster_recovery.py | 468 | 300 | Split into 2 focused test modules |
| tests\unified\test_frontend_backend_api.py | 839 | 300 | Split into 3 focused test modules |
| tests\unified\e2e\test_rate_limiting_unified_real.py | 659 | 300 | Split into 3 focused test modules |
| app\tests\websocket\test_websocket_server_to_client_types.py | 396 | 300 | Split into 2 focused test modules |
| tests\integration\test_cross_service_config.py | 394 | 300 | Split into 2 focused test modules |
| tests\unified\websocket\test_message_queue_basic.py | 647 | 300 | Split into 3 focused test modules |
| tests\unified\e2e\test_corpus_generation_pipeline_integration.py | 479 | 300 | Split into 2 focused test modules |
| app\tests\integration\test_cache_management_integration.py | 512 | 300 | Split into 2 focused test modules |
| test_framework\docker_testing\compose_manager.py | 401 | 300 | Split into 2 focused test modules |
| tests\e2e\test_error_scenarios_comprehensive_e2e.py | 581 | 300 | Split into 2 focused test modules |
| app\tests\core\test_async_edge_cases_error_handling.py | 396 | 300 | Split into 2 focused test modules |
| auth_service\tests\test_token_validation.py | 486 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_user_message_agent_pipeline.py | 331 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_agent_resource_cleanup_integration.py | 399 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_websocket_comprehensive_e2e.py | 345 | 300 | Split into 2 focused test modules |
| app\tests\integration\test_helpers\user_flow_base.py | 301 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_websocket_auth_integration.py | 695 | 300 | Split into 3 focused test modules |
| app\tests\unified_system\test_thread_management.py | 632 | 300 | Split into 3 focused test modules |
| app\tests\services\test_corpus_audit.py | 358 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\dev_launcher_test_fixtures.py | 313 | 300 | Split into 2 focused test modules |
| app\tests\integration\test_agent_state_persistence_recovery.py | 519 | 300 | Split into 2 focused test modules |
| app\tests\websocket\test_websocket_resilience.py | 462 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_cache_coherence.py | 301 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_performance_sla_validation.py | 312 | 300 | Split into 2 focused test modules |
| app\tests\integration\user_flows\test_mid_tier_flows.py | 311 | 300 | Split into 2 focused test modules |
| app\tests\unified_system\test_circuit_breakers.py | 491 | 300 | Split into 2 focused test modules |
| test_framework\performance_optimizer.py | 521 | 300 | Split into 2 focused test modules |
| app\tests\integration\test_user_session_persistence_restart.py | 469 | 300 | Split into 2 focused test modules |
| test_framework\optimized_executor.py | 660 | 300 | Split into 3 focused test modules |
| tests\unified\e2e\test_websocket_ui_timing.py | 416 | 300 | Split into 2 focused test modules |
| tests\test_example_message_flow_comprehensive.py | 1002 | 300 | Split into 4 focused test modules |
| tests\unified\test_jwt_secret_synchronization.py | 321 | 300 | Split into 2 focused test modules |
| tests\unified\websocket\test_basic_messaging.py | 349 | 300 | Split into 2 focused test modules |
| test_framework\test_parser.py | 408 | 300 | Split into 2 focused test modules |
| app\tests\startup\test_startup_diagnostics.py | 448 | 300 | Split into 2 focused test modules |
| tests\e2e\test_concurrent_agent_startup.py | 1127 | 300 | Split into 4 focused test modules |
| tests\e2e\test_helpers\high_volume_server.py | 513 | 300 | Split into 2 focused test modules |
| tests\e2e\test_message_flow_comprehensive_e2e.py | 521 | 300 | Split into 2 focused test modules |
| app\tests\startup\test_error_aggregator.py | 369 | 300 | Split into 2 focused test modules |
| test_framework\test_environment_setup.py | 458 | 300 | Split into 2 focused test modules |
| app\tests\agents\test_triage_sub_agent.py | 500 | 300 | Split into 2 focused test modules |
| app\tests\example_isolated_test.py | 370 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_agent_workflow_tdd_integration.py | 586 | 300 | Split into 2 focused test modules |
| app\tests\core\test_type_validation_part4.py | 356 | 300 | Split into 2 focused test modules |
| app\tests\integration\test_metrics_pipeline_integration.py | 350 | 300 | Split into 2 focused test modules |
| tests\unified\test_agent_startup_load_e2e.py | 344 | 300 | Split into 2 focused test modules |
| app\tests\unified_system\test_dev_launcher_startup.py | 489 | 300 | Split into 2 focused test modules |
| tests\unified\test_concurrent_agents.py | 332 | 300 | Split into 2 focused test modules |
| tests\websocket\test_secure_websocket.py | 571 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_staging_services.py | 308 | 300 | Split into 2 focused test modules |
| tests\unified\websocket\test_state_sync.py | 900 | 300 | Split into 4 focused test modules |
| app\tests\unit\test_compensation_engine_core.py | 372 | 300 | Split into 2 focused test modules |
| app\tests\integration\staging\test_staging_database_connection_resilience.py | 353 | 300 | Split into 2 focused test modules |
| tests\unified\test_agent_pipeline_real.py | 371 | 300 | Split into 2 focused test modules |
| tests\unified\test_real_user_signup_login_chat.py | 353 | 300 | Split into 2 focused test modules |
| tests\e2e\resource_isolation\test_performance_isolation.py | 334 | 300 | Split into 2 focused test modules |
| app\tests\e2e\test_thread_error_handling.py | 420 | 300 | Split into 2 focused test modules |
| app\tests\e2e\test_websocket_integration.py | 485 | 300 | Split into 2 focused test modules |
| app\tests\integration\test_logging_audit_integration.py | 433 | 300 | Split into 2 focused test modules |
| app\tests\integration\test_message_flow_routing.py | 574 | 300 | Split into 2 focused test modules |
| test_framework\smart_cache.py | 388 | 300 | Split into 2 focused test modules |
| app\tests\core\test_fallback_coordinator_integration.py | 326 | 300 | Split into 2 focused test modules |
| tests\unified\test_latency_targets.py | 319 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_agent_context_isolation_integration.py | 320 | 300 | Split into 2 focused test modules |
| tests\unified\test_resource_usage.py | 322 | 300 | Split into 2 focused test modules |
| app\tests\websocket\test_websocket_client_to_server_types.py | 313 | 300 | Split into 2 focused test modules |
| app\tests\unified_system\test_service_recovery.py | 609 | 300 | Split into 3 focused test modules |
| tests\unified\e2e\dev_mode_integration_utils.py | 669 | 300 | Split into 3 focused test modules |
| app\tests\unified_system\test_jwt_flow.py | 411 | 300 | Split into 2 focused test modules |
| app\tests\unit\test_websocket_ghost_connections.py | 334 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_agent_state_sync_integration.py | 431 | 300 | Split into 2 focused test modules |
| tests\unified\websocket\test_websocket_service_discovery.py | 707 | 300 | Split into 3 focused test modules |
| app\tests\seed_data_manager.py | 490 | 300 | Split into 2 focused test modules |
| tests\unified\test_auth_service_health_check_integration.py | 326 | 300 | Split into 2 focused test modules |
| app\tests\unified_system\test_database_sync.py | 465 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_production_data_e2e_real_llm.py | 568 | 300 | Split into 2 focused test modules |
| app\tests\integration\test_first_message_streaming.py | 339 | 300 | Split into 2 focused test modules |
| tests\test_example_message_performance.py | 575 | 300 | Split into 2 focused test modules |
| app\tests\integration\test_quality_gate_pipeline_integration.py | 495 | 300 | Split into 2 focused test modules |
| test_framework\test_user_journeys.py | 437 | 300 | Split into 2 focused test modules |
| tests\e2e\test_cors_e2e.py | 635 | 300 | Split into 3 focused test modules |
| tests\unified\e2e\test_streaming_auth_validation.py | 633 | 300 | Split into 3 focused test modules |
| tests\unified\test_database_operations.py | 556 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_websocket_concurrent_ordering.py | 548 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_websocket_event_completeness_integration.py | 365 | 300 | Split into 2 focused test modules |
| tests\unified\test_agent_cold_start.py | 359 | 300 | Split into 2 focused test modules |
| app\tests\core\test_error_recovery_scenarios.py | 350 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_complete_user_journey.py | 505 | 300 | Split into 2 focused test modules |
| app\tests\performance\test_concurrent_user_performance.py | 594 | 300 | Split into 2 focused test modules |
| app\tests\integration\test_agent_cold_start.py | 322 | 300 | Split into 2 focused test modules |
| tests\e2e\test_real_services_e2e.py | 1001 | 300 | Split into 4 focused test modules |
| tests\e2e\conftest.py | 366 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_cross_service_auth_sync.py | 499 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_real_database_consistency.py | 572 | 300 | Split into 2 focused test modules |
| app\tests\auth_integration\test_real_user_session_management.py | 374 | 300 | Split into 2 focused test modules |
| app\tests\integration\test_websocket_reconnection.py | 464 | 300 | Split into 2 focused test modules |
| test_framework\bad_test_detector.py | 383 | 300 | Split into 2 focused test modules |
| app\tests\unit\test_batch_message_transactional.py | 348 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_auth_service_recovery.py | 498 | 300 | Split into 2 focused test modules |
| app\tests\integration\test_unified_message_flow.py | 491 | 300 | Split into 2 focused test modules |
| app\tests\performance\test_comprehensive_backend_performance.py | 675 | 300 | Split into 3 focused test modules |
| tests\unified\test_resource_limits.py | 441 | 300 | Split into 2 focused test modules |
| app\tests\integration\helpers\critical_integration_helpers.py | 438 | 300 | Split into 2 focused test modules |
| app\tests\services\test_fallback_response_service.py | 454 | 300 | Split into 2 focused test modules |
| app\tests\integration\test_sub_agent_registry_discovery.py | 496 | 300 | Split into 2 focused test modules |
| tests\unified\test_critical_imports_validation.py | 408 | 300 | Split into 2 focused test modules |
| app\tests\e2e\test_complete_real_pipeline_e2e.py | 355 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_database_sync.py | 318 | 300 | Split into 2 focused test modules |
| app\tests\critical\test_agent_recovery_strategies.py | 355 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\run_critical_unified_tests.py | 431 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_real_billing_pipeline.py | 385 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_websocket_message_streaming.py | 383 | 300 | Split into 2 focused test modules |
| tests\unified\test_isolation.py | 368 | 300 | Split into 2 focused test modules |
| tests\unified\test_dev_launcher_real_startup.py | 436 | 300 | Split into 2 focused test modules |
| app\tests\routes\test_synthetic_data_management.py | 396 | 300 | Split into 2 focused test modules |
| tests\unified\test_environment_config.py | 510 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_real_session_persistence.py | 541 | 300 | Split into 2 focused test modules |
| app\tests\helpers\triage_test_helpers.py | 414 | 300 | Split into 2 focused test modules |
| app\tests\services\test_user_service.py | 305 | 300 | Split into 2 focused test modules |
| app\tests\e2e\test_websocket_thread_integration.py | 375 | 300 | Split into 2 focused test modules |
| app\tests\core\test_system_health_monitor.py | 350 | 300 | Split into 2 focused test modules |
| app\tests\services\test_advanced_orchestration.py | 419 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_staging_complete_e2e.py | 538 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_websocket_missing_events.py | 405 | 300 | Split into 2 focused test modules |
| app\tests\integration\test_staging_database_migration_validation.py | 548 | 300 | Split into 2 focused test modules |
| app\tests\e2e\test_multi_service.py | 551 | 300 | Split into 2 focused test modules |
| tests\e2e\test_agent_message_flow_implementation.py | 349 | 300 | Split into 2 focused test modules |
| app\tests\websocket\test_websocket_frontend_integration.py | 735 | 300 | Split into 3 focused test modules |
| app\tests\clickhouse\test_corpus_generation_coverage.py | 524 | 300 | Split into 2 focused test modules |
| tests\unified\websocket\test_missing_events_implementation.py | 553 | 300 | Split into 2 focused test modules |
| app\tests\unit\test_first_time_user_real_critical.py | 444 | 300 | Split into 2 focused test modules |
| app\tests\integration\test_error_recovery.py | 673 | 300 | Split into 3 focused test modules |
| tests\unified\e2e\test_new_user_complete_real.py | 554 | 300 | Split into 2 focused test modules |
| app\tests\websocket\test_websocket_comprehensive.py | 725 | 300 | Split into 3 focused test modules |
| tests\unified\e2e\test_user_journey_complete_real.py | 433 | 300 | Split into 2 focused test modules |
| tests\e2e\test_helpers\agent_isolation_base.py | 340 | 300 | Split into 2 focused test modules |
| tests\e2e\websocket_resilience\test_8_malformed_payload_handling.py | 534 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_cold_start_to_agent_response.py | 400 | 300 | Split into 2 focused test modules |
| app\tests\integration\test_redis_session_state_sync.py | 839 | 300 | Split into 3 focused test modules |
| app\tests\core\test_fallback_coordinator_core.py | 301 | 300 | Split into 2 focused test modules |
| tests\e2e\websocket_resilience\test_10_token_refresh_websocket.py | 535 | 300 | Split into 2 focused test modules |
| app\tests\test_database_manager.py | 486 | 300 | Split into 2 focused test modules |
| app\tests\mcp\test_mcp_service.py | 405 | 300 | Split into 2 focused test modules |
| app\tests\integration\test_free_tier_value_demonstration_integration.py | 498 | 300 | Split into 2 focused test modules |
| app\tests\unit\test_user_service_auth.py | 465 | 300 | Split into 2 focused test modules |
| app\tests\llm\test_structured_generation.py | 361 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_session_persistence_unified.py | 535 | 300 | Split into 2 focused test modules |
| app\tests\routes\test_thread_messaging.py | 356 | 300 | Split into 2 focused test modules |
| app\tests\services\test_ws_connection_performance.py | 331 | 300 | Split into 2 focused test modules |
| app\tests\config\test_config_environment.py | 385 | 300 | Split into 2 focused test modules |
| app\tests\e2e\test_agent_orchestration_e2e.py | 304 | 300 | Split into 2 focused test modules |
| app\tests\critical\test_websocket_coroutine_regression.py | 337 | 300 | Split into 2 focused test modules |
| app\tests\services\test_clickhouse_service.py | 357 | 300 | Split into 2 focused test modules |
| tests\e2e\websocket_resilience\test_2_midstream_disconnection_recovery.py | 1279 | 300 | Split into 5 focused test modules |
| app\tests\e2e\test_thread_management.py | 304 | 300 | Split into 2 focused test modules |
| app\tests\integration\test_websocket_lifecycle_integration.py | 436 | 300 | Split into 2 focused test modules |
| app\tests\e2e\test_system_startup.py | 378 | 300 | Split into 2 focused test modules |
| tests\unified\test_agent_startup_performance_validation.py | 360 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_websocket_multi_service.py | 467 | 300 | Split into 2 focused test modules |
| app\tests\test_api_agent_generation_critical.py | 429 | 300 | Split into 2 focused test modules |
| tests\unified\test_multi_service_health.py | 448 | 300 | Split into 2 focused test modules |
| app\tests\services\test_tool_orchestration.py | 352 | 300 | Split into 2 focused test modules |
| app\tests\unified_system\test_websocket_state.py | 683 | 300 | Split into 3 focused test modules |
| tests\e2e\resource_isolation\test_quota_enforcement.py | 339 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_real_llm_environment_example.py | 328 | 300 | Split into 2 focused test modules |
| app\tests\startup\test_comprehensive_startup.py | 365 | 300 | Split into 2 focused test modules |
| tests\e2e\test_agent_resource_isolation_ORIGINAL_BACKUP.py | 1640 | 300 | Split into 6 focused test modules |
| tests\unified\agent_startup_test_data.py | 346 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_auth_service_independence.py | 965 | 300 | Split into 4 focused test modules |
| tests\unified\e2e\test_database_user_sync.py | 496 | 300 | Split into 2 focused test modules |
| app\tests\integration\first_time_user_fixtures.py | 376 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_agent_workflow_validation_real_llm.py | 559 | 300 | Split into 2 focused test modules |
| test_framework\intelligent_parallelization.py | 460 | 300 | Split into 2 focused test modules |
| app\tests\integration\test_websocket_auth_token_refresh.py | 807 | 300 | Split into 3 focused test modules |
| tests\unified\test_websocket_lifecycle.py | 346 | 300 | Split into 2 focused test modules |
| app\tests\websocket\test_performance_monitor_coverage.py | 311 | 300 | Split into 2 focused test modules |
| tests\integration\test_cross_service_integration.py | 416 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_workspace_isolation.py | 301 | 300 | Split into 2 focused test modules |
| tests\e2e\test_helpers\performance_base.py | 687 | 300 | Split into 3 focused test modules |
| tests\unified\e2e\test_auth_circuit_breaker.py | 391 | 300 | Split into 2 focused test modules |
| tests\unified\test_service_health_monitoring.py | 570 | 300 | Split into 2 focused test modules |
| tests\integration\test_cors_integration.py | 523 | 300 | Split into 2 focused test modules |
| app\tests\e2e\test_agent_pipeline.py | 586 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_data_export.py | 535 | 300 | Split into 2 focused test modules |
| app\tests\integration\test_payment_webhook_processing.py | 379 | 300 | Split into 2 focused test modules |
| tests\e2e\test_cache_contention.py | 1046 | 300 | Split into 4 focused test modules |
| app\tests\integration\test_team_collaboration_permissions.py | 990 | 300 | Split into 4 focused test modules |
| app\tests\integration\test_first_time_user_workspace.py | 320 | 300 | Split into 2 focused test modules |
| tests\unified\test_observability.py | 351 | 300 | Split into 2 focused test modules |
| app\tests\routes\test_demo.py | 406 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_critical_unified_flows.py | 332 | 300 | Split into 2 focused test modules |
| app\tests\integration\staging\test_staging_websocket_load_balancing.py | 537 | 300 | Split into 2 focused test modules |
| tests\integration\test_multi_agent_orchestration_state_management.py | 546 | 300 | Split into 2 focused test modules |
| test_framework\resource_monitor.py | 569 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_multi_tab_isolation.py | 429 | 300 | Split into 2 focused test modules |
| app\tests\unit\services\test_gcp_error_service.py | 347 | 300 | Split into 2 focused test modules |
| test_framework\test_runners.py | 528 | 300 | Split into 2 focused test modules |
| tests\unified\test_auth_e2e_flow.py | 318 | 300 | Split into 2 focused test modules |
| app\tests\critical\test_auth_integration_core.py | 359 | 300 | Split into 2 focused test modules |
| app\tests\agents\test_llm_agent_integration.py | 390 | 300 | Split into 2 focused test modules |
| app\tests\critical\test_real_auth_integration_critical.py | 380 | 300 | Split into 2 focused test modules |
| tests\e2e\websocket_resilience\test_4_reconnection_expired_token.py | 1344 | 300 | Split into 5 focused test modules |
| app\tests\agents\test_triage_caching_async.py | 322 | 300 | Split into 2 focused test modules |
| app\tests\integration\test_cache_invalidation_chain.py | 1037 | 300 | Split into 4 focused test modules |
| tests\unified\e2e\test_database_sync_complete.py | 938 | 300 | Split into 4 focused test modules |
| tests\unified\websocket\test_heartbeat_basic.py | 472 | 300 | Split into 2 focused test modules |
| app\tests\e2e\test_artifact_validation.py | 328 | 300 | Split into 2 focused test modules |
| app\tests\integration\test_usage_metering_billing.py | 639 | 300 | Split into 3 focused test modules |
| tests\unified\e2e\test_agent_failure_websocket_recovery.py | 716 | 300 | Split into 3 focused test modules |
| tests\unified\e2e\test_jwt_secret_synchronization.py | 383 | 300 | Split into 2 focused test modules |
| app\tests\routes\test_thread_analytics.py | 465 | 300 | Split into 2 focused test modules |
| app\tests\integration\user_flows\test_enterprise_flows.py | 315 | 300 | Split into 2 focused test modules |
| app\tests\e2e\test_cost_optimization_workflows.py | 408 | 300 | Split into 2 focused test modules |
| app\tests\test_comprehensive_database_operations.py | 480 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_thread_management_websocket.py | 726 | 300 | Split into 3 focused test modules |
| app\tests\test_mcp_integration.py | 404 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_error_recovery_complete.py | 627 | 300 | Split into 3 focused test modules |
| app\tests\integration\test_agent_tool_loading_validation.py | 593 | 300 | Split into 2 focused test modules |
| app\tests\integration\test_redis_session_integration.py | 410 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_session_state_websocket_sync.py | 409 | 300 | Split into 2 focused test modules |
| app\tests\agents\test_llm_agent_e2e_flows.py | 322 | 300 | Split into 2 focused test modules |
| auth_service\tests\unified\test_jwt_validation.py | 354 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_service_to_service_auth.py | 348 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_real_concurrent_users.py | 556 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_database_comprehensive_e2e.py | 359 | 300 | Split into 2 focused test modules |
| tests\unified\service_manager.py | 363 | 300 | Split into 2 focused test modules |
| app\tests\e2e\test_error_propagation_workflows.py | 333 | 300 | Split into 2 focused test modules |
| app\tests\services\test_tool_permission_main.py | 348 | 300 | Split into 2 focused test modules |
| app\tests\unit\test_usage_tracker_unit.py | 729 | 300 | Split into 3 focused test modules |
| app\tests\config\test_config_loader.py | 650 | 300 | Split into 3 focused test modules |
| app\tests\services\test_supply_research_scheduler_jobs.py | 549 | 300 | Split into 2 focused test modules |
| app\tests\websocket\test_websocket_resilience_integration.py | 570 | 300 | Split into 2 focused test modules |
| app\tests\integration\test_supervisor_agent_initialization_chain.py | 393 | 300 | Split into 2 focused test modules |
| tests\websocket\test_websocket_auth.py | 305 | 300 | Split into 2 focused test modules |
| app\tests\integration\test_multi_service_health.py | 562 | 300 | Split into 2 focused test modules |
| app\tests\services\test_circuit_breaker_integration.py | 435 | 300 | Split into 2 focused test modules |
| test_framework\decorators.py | 327 | 300 | Split into 2 focused test modules |
| test_framework\real_llm_config.py | 672 | 300 | Split into 3 focused test modules |
| tests\unified\e2e\test_oauth_proxy_staging.py | 448 | 300 | Split into 2 focused test modules |
| app\tests\services\test_tool_permission_business_rate.py | 335 | 300 | Split into 2 focused test modules |
| app\tests\test_api_threads_messages_critical.py | 355 | 300 | Split into 2 focused test modules |
| tests\e2e\test_auth_race_conditions.py | 1094 | 300 | Split into 4 focused test modules |
| tests\unified\test_metrics_collection.py | 492 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_real_oauth_integration.py | 596 | 300 | Split into 2 focused test modules |
| app\tests\integration\test_multi_agent_collaboration.py | 442 | 300 | Split into 2 focused test modules |
| app\tests\core\test_async_processing_locking.py | 387 | 300 | Split into 2 focused test modules |
| app\tests\examples\test_real_functionality_examples.py | 432 | 300 | Split into 2 focused test modules |
| app\tests\core\test_agent_recovery_strategies.py | 530 | 300 | Split into 2 focused test modules |
| app\tests\database\async_transaction_patterns_improved.py | 301 | 300 | Split into 2 focused test modules |
| auth_service\tests\test_session_management.py | 356 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_database_sync_real.py | 633 | 300 | Split into 3 focused test modules |
| app\tests\services\test_demo_service.py | 431 | 300 | Split into 2 focused test modules |
| app\tests\services\test_apex_optimizer_tool_selection_part2.py | 331 | 300 | Split into 2 focused test modules |
| app\tests\unit\test_async_resource_manager.py | 429 | 300 | Split into 2 focused test modules |
| app\tests\integration\test_core_features_integration.py | 567 | 300 | Split into 2 focused test modules |
| test_framework\config\config_manager.py | 433 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_websocket_connection_lifecycle_compliant.py | 487 | 300 | Split into 2 focused test modules |
| app\tests\test_json_extraction.py | 321 | 300 | Split into 2 focused test modules |
| app\tests\unit\test_app_factory.py | 358 | 300 | Split into 2 focused test modules |
| tests\e2e\test_agent_responses_comprehensive_e2e.py | 434 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_websocket_ui_timing_integration.py | 545 | 300 | Split into 2 focused test modules |
| tests\unified\websocket\test_multi_service_websocket_coherence.py | 683 | 300 | Split into 3 focused test modules |
| app\tests\core\test_async_resource_pool_management.py | 359 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_auth_token_cache.py | 390 | 300 | Split into 2 focused test modules |
| app\tests\unified_system\test_dev_mode.py | 498 | 300 | Split into 2 focused test modules |
| app\tests\websocket\test_websocket_production_security.py | 472 | 300 | Split into 2 focused test modules |
| test_framework\test_runner.py | 926 | 300 | Split into 4 focused test modules |
| app\tests\services\security_service_test_mocks.py | 358 | 300 | Split into 2 focused test modules |
| app\tests\routes\test_route_fixtures.py | 343 | 300 | Split into 2 focused test modules |
| test_framework\test_user_journeys_integration.py | 349 | 300 | Split into 2 focused test modules |
| app\tests\unit\test_error_recovery_integration.py | 405 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_thread_management_ui_update.py | 524 | 300 | Split into 2 focused test modules |
| tests\integration\test_cross_service_session_state_synchronization.py | 585 | 300 | Split into 2 focused test modules |
| app\tests\agents\test_supervisor_advanced.py | 302 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_websocket_user_journey_integration.py | 604 | 300 | Split into 3 focused test modules |
| tests\unified\e2e\test_rate_limiting.py | 386 | 300 | Split into 2 focused test modules |
| app\tests\unified_system\test_error_propagation.py | 737 | 300 | Split into 3 focused test modules |
| tests\unified\e2e\test_first_page_load_websocket_integration.py | 470 | 300 | Split into 2 focused test modules |
| tests\unified\websocket\test_basic_error_handling.py | 467 | 300 | Split into 2 focused test modules |
| tests\unified\test_token_expiry_cross_service.py | 315 | 300 | Split into 2 focused test modules |
| app\tests\startup\test_migration_tracker.py | 359 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_multi_session_management.py | 415 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_real_oauth_google_flow.py | 457 | 300 | Split into 2 focused test modules |
| test_framework\report_generators.py | 391 | 300 | Split into 2 focused test modules |
| app\tests\unit\test_real_auth_service_integration.py | 352 | 300 | Split into 2 focused test modules |
| tests\unified\test_token_validation.py | 367 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_service_independence.py | 1262 | 300 | Split into 5 focused test modules |
| app\tests\integration\test_database_transaction_coordination.py | 488 | 300 | Split into 2 focused test modules |
| app\tests\routes\test_supply_management.py | 358 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_agent_failure_cascade_integration.py | 396 | 300 | Split into 2 focused test modules |
| app\tests\services\test_supply_research_service_error_handling.py | 327 | 300 | Split into 2 focused test modules |
| app\tests\integration\test_agent_initialization_integration.py | 301 | 300 | Split into 2 focused test modules |
| tests\unified\test_data_factory.py | 333 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_multi_session_isolation.py | 473 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_real_error_recovery.py | 637 | 300 | Split into 3 focused test modules |
| test_framework\ultra_test_orchestrator.py | 431 | 300 | Split into 2 focused test modules |
| test_framework\test_execution_engine.py | 429 | 300 | Split into 2 focused test modules |
| app\tests\isolated_test_config.py | 429 | 300 | Split into 2 focused test modules |
| app\tests\agents\test_llm_agent_e2e_performance.py | 328 | 300 | Split into 2 focused test modules |
| app\tests\integration\test_agent_response_pipeline_e2e.py | 829 | 300 | Split into 3 focused test modules |
| tests\unified\websocket\test_basic_connection.py | 437 | 300 | Split into 2 focused test modules |
| app\tests\critical\test_execution_context_hashable_regression.py | 347 | 300 | Split into 2 focused test modules |
| app\tests\routes\test_agent_routes.py | 309 | 300 | Split into 2 focused test modules |
| app\tests\integration\test_security_audit_trail.py | 795 | 300 | Split into 3 focused test modules |
| app\tests\integration\test_auth_service_dependency_resolution.py | 434 | 300 | Split into 2 focused test modules |
| app\tests\integration\test_first_time_user_billing.py | 314 | 300 | Split into 2 focused test modules |
| app\tests\integration\test_jwt_token_propagation.py | 429 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_service_startup_health_real.py | 560 | 300 | Split into 2 focused test modules |
| app\tests\critical\test_business_critical_gaps.py | 444 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_payment_billing_accuracy.py | 488 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_websocket_token_expiry_reconnect.py | 511 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_agent_lifecycle_websocket_events.py | 665 | 300 | Split into 3 focused test modules |
| app\tests\integration\test_metrics_aggregation_pipeline.py | 702 | 300 | Split into 3 focused test modules |
| tests\unified\test_service_startup_dependency_chain.py | 445 | 300 | Split into 2 focused test modules |
| app\tests\services\test_permission_service_core.py | 302 | 300 | Split into 2 focused test modules |
| tests\unified\test_websocket_real_connection.py | 618 | 300 | Split into 3 focused test modules |
| tests\unified\test_basic_user_flow_e2e.py | 389 | 300 | Split into 2 focused test modules |
| app\tests\critical\test_websocket_message_regression.py | 569 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_service_health_checks.py | 318 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\run_e2e_tests.py | 531 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\agent_response_test_utilities.py | 308 | 300 | Split into 2 focused test modules |
| app\tests\unit\test_permission_service_unit.py | 502 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_session_persistence_restart.py | 676 | 300 | Split into 3 focused test modules |
| tests\e2e\test_system_resilience.py | 678 | 300 | Split into 3 focused test modules |
| app\tests\agents\agent_system_test_helpers.py | 367 | 300 | Split into 2 focused test modules |
| app\tests\e2e\test_real_llm_workflow.py | 319 | 300 | Split into 2 focused test modules |
| tests\e2e\test_websocket_resilience.py | 508 | 300 | Split into 2 focused test modules |
| auth_service\tests\test_security.py | 520 | 300 | Split into 2 focused test modules |
| app\tests\test_business_value_fixtures.py | 442 | 300 | Split into 2 focused test modules |
| tests\unified\test_auth_backend_integration.py | 395 | 300 | Split into 2 focused test modules |
| app\tests\e2e\test_thread_performance.py | 443 | 300 | Split into 2 focused test modules |
| app\tests\integration\test_reliability_scale_integration.py | 431 | 300 | Split into 2 focused test modules |
| tests\unified\e2e\test_dev_launcher_startup_complete.py | 513 | 300 | Split into 2 focused test modules |
| app\tests\performance\test_sla_compliance.py | 690 | 300 | Split into 3 focused test modules |
| tests\unified\e2e\test_real_unified_signup_login_chat.py | 310 | 300 | Split into 2 focused test modules |
| tests\e2e\test_security_permissions.py | 757 | 300 | Split into 3 focused test modules |
| app\tests\services\test_tool_lifecycle_health.py | 375 | 300 | Split into 2 focused test modules |

### Function Size Violations

| File | Function | Lines | Limit | Fix Suggestion |
|------|----------|-------|-------|----------------|
| tests\conftest.py | mock_redis_manager | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\conftest.py | mock_websocket_manager | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\conftest.py | app | 46 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\clickhouse\test_clickhouse_workload.py | setup_workload_table | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\test_system_startup.py | test_dev_launcher_help | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\test_system_startup.py | test_dev_launcher_list_services | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\test_system_startup.py | test_dev_launcher_minimal_mode | 33 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\test_system_startup.py | test_backend_import | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\test_system_startup.py | test_npm_detection | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\test_system_startup.py | test_redis_connectivity | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\test_system_startup.py | test_database_initialization | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\integration\test_startup_system.py | test_postgresql_connection_success | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\integration\test_startup_system.py | test_url_normalization | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\integration\test_startup_system.py | test_clickhouse_url_building | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\integration\test_startup_system.py | test_redis_url_building | 18 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\integration\test_startup_system.py | test_connection_status_tracking | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\integration\test_startup_system.py | test_validation_with_current_env | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\integration\test_startup_system.py | test_database_url_validation | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\integration\test_startup_system.py | test_secret_key_validation | 19 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\integration\test_startup_system.py | test_environment_validation | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\integration\test_startup_system.py | test_port_conflict_detection | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\integration\test_startup_system.py | test_fix_suggestions | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\integration\test_startup_system.py | test_launcher_initialization | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\integration\test_startup_system.py | test_environment_check_integration | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\integration\test_startup_system.py | test_configuration_loading | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\integration\test_startup_system.py | test_error_handling | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\integration\test_startup_system.py | test_url_building | 22 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\integration\test_startup_system.py | test_environment_validation_real | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\integration\test_startup_system.py | test_startup_constants_consistency | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\unified\test_supervisor_pattern_compliance.py | valid_context | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\unified\test_supervisor_pattern_compliance.py | context | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\unified\test_supervisor_pattern_compliance.py | test_workflow_definition | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\unified\test_supervisor_pattern_compliance.py | test_start_workflow_trace | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\unified\test_supervisor_pattern_compliance.py | test_add_span | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\unified\test_supervisor_pattern_compliance.py | test_complete_workflow_trace | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\unified\test_supervisor_pattern_compliance.py | test_get_health_status | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\clickhouse\test_query_correctness.py | test_performance_metrics_query_structure | 19 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\clickhouse\test_query_correctness.py | test_performance_metrics_without_workload_filter | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\clickhouse\test_query_correctness.py | test_aggregation_level_functions | 18 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\clickhouse\test_query_correctness.py | test_anomaly_detection_query_structure | 25 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\clickhouse\test_query_correctness.py | test_anomaly_baseline_window | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\clickhouse\test_query_correctness.py | test_usage_patterns_query_structure | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\clickhouse\test_query_correctness.py | test_correlation_analysis_query | 19 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\clickhouse\test_query_correctness.py | test_nested_array_access_pattern | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\clickhouse\test_query_correctness.py | test_nested_array_existence_check | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\clickhouse\test_query_correctness.py | test_null_safety_in_calculations | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\test_database_connectivity_improvements.py | clickhouse_manager | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\test_database_connectivity_improvements.py | test_error_classification | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\test_database_connectivity_improvements.py | test_query_performance_tracking | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\test_database_connectivity_improvements.py | test_error_tracking | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\examples\agent_fixtures_usage_examples.py | test_agent_builder_pattern | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\examples\agent_fixtures_usage_examples.py | test_custom_agent_configuration | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\examples\agent_fixtures_usage_examples.py | test_agent_state_management | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\examples\agent_fixtures_usage_examples.py | test_performance_testing_setup | 17 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\performance\test_performance_batching.py | mock_connection_manager | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_subagent_workflow.py | mock_llm_manager | 24 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_synthetic_data_generation.py | test_synthetic_data_generation | 47 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_synthetic_data_generation.py | test_synthetic_data_validation | 49 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_synthetic_data_generation.py | test_synthetic_data_job_status | 29 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_synthetic_data_generation.py | test_data_generation_schemas | 59 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_synthetic_data_generation.py | test_generation_progress_tracking | 29 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_synthetic_data_generation.py | test_generation_parameter_optimization | 60 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_quality_routes.py | test_quality_metrics_retrieval | 23 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_quality_routes.py | test_quality_aggregation | 22 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_quality_routes.py | test_quality_thresholds_configuration | 33 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_quality_routes.py | test_quality_trend_analysis | 40 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_quality_routes.py | test_quality_comparison_analysis | 39 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_quality_routes.py | test_quality_report_generation | 38 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\e2e\fixtures\high_volume_data.py | latency_probe_data | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\e2e\test_admin_corpus_generation.py | admin_corpus_setup | 23 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\examples\test_feature_flag_environment_demo.py | test_environment_override_demo | 23 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\examples\test_feature_flag_environment_demo.py | test_enterprise_sso_when_enabled | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\examples\test_feature_flag_environment_demo.py | test_dynamic_feature_control | 26 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_quality_monitoring_alerts.py | test_create_alert_if_needed_critical | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_quality_monitoring_alerts.py | test_create_alert_if_needed_good_quality | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_quality_monitoring_alerts.py | test_quality_alert_creation | 21 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_quality_monitoring_alerts.py | test_quality_trend_creation | 20 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_quality_monitoring_alerts.py | test_agent_quality_profile_creation | 25 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_websocket_message_queue_integration.py | test_queue_statistics_tracking | 24 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_apex_optimizer_tool_selection_part4.py | performance_tools | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_apex_optimizer_tool_selection_part4.py | test_tool_metrics_and_monitoring | 18 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_apex_optimizer_tool_selection_part1.py | sample_agent_state | 27 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_cost_calculator_service.py | test_cost_tier_optimization_openai | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_cost_calculator_service.py | test_multi_model_cost_aggregation | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_cost_calculator_service.py | test_cost_tier_recommendation_logic | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_cost_calculator_service.py | test_calculate_cost_savings_optimization | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_cost_calculator_service.py | test_model_pricing_key_generation | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_missing_tests_services.py | test_log_rotation_setup | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_missing_tests_services.py | test_log_filtering_by_service | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_missing_tests_services.py | test_secret_rotation | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_missing_tests_services.py | test_secure_secret_storage | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_missing_tests_services.py | test_secret_versioning | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_missing_tests_services.py | test_log_aggregation_from_multiple_sources | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_missing_tests_services.py | test_structured_context_addition | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_missing_tests_services.py | test_log_buffering_and_flushing | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_missing_tests_services.py | test_log_filtering_by_level | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_missing_tests_services.py | test_cross_service_trace_linking | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_missing_tests_services.py | test_service_health_monitoring | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_missing_tests_services.py | test_service_dependency_injection | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_missing_tests_services.py | test_service_configuration_management | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_utilities.py | secured_client | 19 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_health_checkers_core.py | test_create_success_result_structure | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_health_checkers_core.py | test_create_failed_result_structure | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_metrics_value_type_mismatch.py | test_fix_metrics_value_array_syntax | 31 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_metrics_value_type_mismatch.py | test_second_problematic_query_from_issue | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_metrics_value_type_mismatch.py | test_complex_nested_array_access | 20 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_metrics_value_type_mismatch.py | test_query_with_arithmetic_in_index | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_scheduler_jobs_core.py | scheduler | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\e2e\infrastructure\test_llm_test_manager.py | test_environment_config_loading | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\e2e\infrastructure\test_llm_test_manager.py | test_request_validation | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\e2e\infrastructure\test_llm_test_manager.py | test_response_creation | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\e2e\infrastructure\test_llm_test_manager.py | test_cache_hit_flag | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\clickhouse\test_performance_metrics_extraction.py | test_metrics_extraction_with_arrays | 38 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\clickhouse\test_performance_metrics_extraction.py | test_system_resource_metrics | 34 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\clickhouse\test_performance_metrics_extraction.py | test_performance_threshold_monitoring | 50 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\clickhouse\test_performance_metrics_extraction.py | test_performance_correlation_analysis | 32 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\clickhouse\test_performance_metrics_extraction.py | test_performance_baseline_calculation | 41 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_fallback_handler.py | basic_context | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_fallback_handler.py | test_generate_fallback_includes_agent_name | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_fallback_handler.py | test_fallback_with_error_type_agent_error | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_fallback_handler.py | test_fallback_with_error_type_timeout | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_fallback_handler.py | test_fallback_with_error_type_validation | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_fallback_handler.py | test_fallback_with_unknown_error_type | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_fallback_handler.py | test_fallback_context_basic_usage | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\examples\test_tdd_workflow_demo.py | test_cache_hit_optimization | 17 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\examples\test_tdd_workflow_demo.py | test_cache_eviction_policy | 21 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\examples\test_tdd_workflow_demo.py | test_cache_performance_metrics | 17 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\examples\test_tdd_workflow_demo.py | test_cache_integration_with_database | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\examples\test_tdd_workflow_demo.py | test_ml_cache_prediction | 23 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_json_parsing_safe_parse.py | test_parse_deeply_nested_json | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_quality_gate_validation.py | test_quality_metrics_defaults | 23 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_quality_gate_validation.py | test_quality_metrics_custom_values | 20 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_quality_gate_validation.py | test_validation_result_initialization | 17 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_quality_gate_validation.py | test_validation_result_defaults | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_config_routes.py | test_config_retrieval | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_config_routes.py | test_config_update_validation | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_config_routes.py | test_config_validation_rules | 28 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_config_routes.py | test_config_environment_specific | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_config_routes.py | test_config_feature_flags | 29 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_config_routes.py | test_config_security_validation | 26 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_config_routes.py | test_config_real_time_updates | 22 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_config_routes.py | test_config_rollback_mechanism | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\clickhouse\test_performance_edge_cases.py | test_time_window_query_optimization | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\clickhouse\test_performance_edge_cases.py | test_zero_standard_deviation_handling | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\clickhouse\test_performance_edge_cases.py | test_invalid_workload_type_validation | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\clickhouse\test_performance_edge_cases.py | test_statistics_with_single_value | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\clickhouse\test_performance_edge_cases.py | test_correlation_with_constant_values | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\clickhouse\test_performance_edge_cases.py | test_seasonality_insufficient_data | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\clickhouse\test_performance_edge_cases.py | test_outlier_detection_small_dataset | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\clickhouse\test_performance_edge_cases.py | test_outlier_detection_methods | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\examples\test_size_compliance_examples.py | test_complex_workflow_bad | 18 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_service_models.py | test_service_health_creation | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_service_models.py | test_service_metrics_creation | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_query_fix_validator.py | test_validate_and_fix_complex_correlation_query | 17 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_query_fix_validator.py | test_validate_and_fix_all_nested_fields | 17 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_query_fix_validator.py | test_ensure_query_uses_arrayElement | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_query_fix_validator.py | test_fix_simplified_correlation_query | 17 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_query_fix_validator.py | test_fix_arithmetic_in_index | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\integration\test_configuration_integration.py | base_environment_config | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\integration\test_configuration_integration.py | staging_environment_config | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_regression_prevention.py | real_components | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_regression_prevention.py | test_registry_registers_default_agents | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_regression_prevention.py | test_supervisor_initializes_with_agents | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_regression_prevention.py | test_pipeline_executor_initialization | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_regression_prevention.py | test_execution_engine_initialization | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_http_client_manager.py | test_get_client_existing | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\helpers\test_agent_orchestration_pytest_fixtures.py | mock_message_handler | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\helpers\test_agent_orchestration_pytest_fixtures.py | agent_service | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_schema_validation_service.py | test_user_data_schema | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_schema_validation_service.py | test_agent_message_schema | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_data_sub_agent_consolidated.py | sample_workload_data | 31 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_data_sub_agent_consolidated.py | sample_cost_breakdown | 25 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_data_sub_agent_consolidated.py | test_analysis_request_extraction | 20 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_data_sub_agent_consolidated.py | test_analysis_request_defaults | 17 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_data_sub_agent_consolidated.py | test_health_status_check | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_data_sub_agent_consolidated.py | test_analysis_request_validation | 23 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_data_sub_agent_consolidated.py | test_raw_data_validation | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_data_sub_agent_consolidated.py | test_analysis_result_validation | 26 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\clickhouse\test_realistic_log_ingestion.py | test_log_volume_estimation | 20 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\clickhouse\test_realistic_log_ingestion.py | test_log_retention_query | 17 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\clickhouse\test_realistic_log_ingestion.py | test_log_correlation_across_components | 30 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\clickhouse\test_realistic_log_ingestion.py | test_log_sampling_strategy | 19 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\llm\test_llm_integration_real.py | test_llm_config | 18 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\llm\test_llm_integration_real.py | test_markdown_wrapped_json_response | 17 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\llm\test_llm_integration_real.py | test_malformed_json_with_trailing_comma | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\llm\test_llm_integration_real.py | test_partial_response_due_to_token_limit | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\llm\test_llm_integration_real.py | test_string_vs_dict_field_conversion | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\llm\test_llm_integration_real.py | test_deeply_nested_json_strings | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\llm\test_llm_integration_real.py | test_token_usage_calculation | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_json_parsing_helpers_and_edge_cases.py | test_safe_json_parse_logs_parse_errors | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_json_parsing_helpers_and_edge_cases.py | test_parse_dict_field_logs_type_errors | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_json_parsing_helpers_and_edge_cases.py | test_parse_list_field_logs_type_errors | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_json_parsing_helpers_and_edge_cases.py | test_comprehensive_json_fix_logs_fixes | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_json_parsing_helpers_and_edge_cases.py | test_very_large_json_string | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_json_parsing_helpers_and_edge_cases.py | test_deeply_nested_json_structures | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_json_parsing_helpers_and_edge_cases.py | test_unicode_and_special_characters | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_json_parsing_helpers_and_edge_cases.py | test_circular_reference_handling | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_json_parsing_helpers_and_edge_cases.py | test_malformed_json_recovery | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\startup\test_config_core.py | mock_validation_context | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\startup\test_config_core.py | mock_services_config | 17 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\startup\test_config_core.py | test_validation_result_with_data | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\startup\test_config_core.py | test_validation_context_with_overrides | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| auth_service\tests\unit\test_oauth_models.py | test_valid_local_login | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| auth_service\tests\unit\test_oauth_models.py | test_valid_oauth_login | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| auth_service\tests\unit\test_oauth_models.py | test_local_login_requires_password | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| auth_service\tests\unit\test_oauth_models.py | test_valid_login_response | 18 | 8 | Split into multiple focused test functions or extract helper methods |
| auth_service\tests\unit\test_oauth_models.py | test_valid_token_response | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| auth_service\tests\unit\test_oauth_models.py | test_required_endpoints | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| auth_service\tests\unit\test_oauth_models.py | test_optional_endpoints | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| auth_service\tests\unit\test_oauth_models.py | test_full_auth_config | 22 | 8 | Split into multiple focused test functions or extract helper methods |
| auth_service\tests\unit\test_oauth_models.py | test_development_config | 22 | 8 | Split into multiple focused test functions or extract helper methods |
| auth_service\tests\unit\test_oauth_models.py | test_state_parameter_length | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\e2e\conftest.py | test_user_data | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\integration\test_multi_agent_coordination_init.py | coordination_registry | 18 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_websocket_connection_manager.py | test_get_connection_info_detailed | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_websocket_connection_manager.py | test_is_connection_alive | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_websocket_connection_manager.py | test_get_health_status | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_websocket_connection_manager.py | test_connection_info_structure_completeness | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_websocket_connection_manager.py | test_stats_accuracy_with_multiple_users | 25 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_websocket_connection_manager.py | test_connection_registry_consistency | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_websocket_connection_manager.py | test_empty_state_handling | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_websocket_connection_manager.py | test_connection_state_tracking | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\helpers\quality_monitoring_fixtures.py | sample_quality_metrics | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\helpers\quality_monitoring_fixtures.py | poor_quality_metrics | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\helpers\quality_monitoring_fixtures.py | sample_quality_alert | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_llm_structured_output.py | structured_llm_manager | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\integration\test_gcp_monitoring_routes.py | sample_error_response | 22 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\integration\test_gcp_monitoring_routes.py | sample_error_detail | 17 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_reliability_fixes.py | test_message_queue_size_limit | 25 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_reliability_fixes.py | test_timestamp_array_cleanup | 18 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_reliability_fixes.py | test_exponential_backoff_calculation | 23 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_reliability_fixes.py | test_reconnection_delay_cap | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_reliability_fixes.py | test_jitter_prevents_thundering_herd | 18 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_reliability_fixes.py | test_production_https_requirement | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_reliability_fixes.py | test_suspicious_origin_blocking | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_reliability_fixes.py | test_origin_length_validation | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_reliability_fixes.py | test_violation_rate_limiting | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_reliability_fixes.py | test_security_headers_in_production | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_reliability_fixes.py | test_development_environment_more_permissive | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_reliability_fixes.py | test_manual_origin_unblocking | 18 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_reliability_fixes.py | test_security_statistics_tracking | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_staging_error_monitor.py | test_calculate_error_score_mixed_severities | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_staging_error_monitor.py | sample_response | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_staging_error_monitor.py | test_should_fail_deployment_critical_errors_exceed_threshold | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_staging_error_monitor.py | test_should_fail_deployment_error_score_exceeds_threshold | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_staging_error_monitor.py | test_should_fail_deployment_within_acceptable_limits | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_staging_error_monitor.py | test_parse_deployment_time_iso_format | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_staging_error_monitor.py | test_format_console_output_complete_structure | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_staging_error_monitor.py | test_parse_deployment_time_default_fallback | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\unified\test_streaming_response.py | streaming_websocket | 17 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\unified\test_streaming_response.py | mock_unified_manager | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\websocket_test_utilities.py | mock_handler_registry | 19 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_security_middleware.py | test_security_config_headers_present | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_security_middleware.py | test_rate_limit_check_exceeds_limit_blocked | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_security_middleware.py | test_rate_limit_multiple_identifiers_independent | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_security_middleware.py | test_rate_limit_cleanup_old_requests | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_security_middleware.py | test_rate_limit_blocked_ip_remains_blocked | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_security_middleware.py | test_sanitize_headers_removes_dangerous_headers | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_security_middleware.py | test_sanitize_headers_preserves_safe_headers | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_security_middleware.py | mock_request | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_security_middleware.py | test_security_middleware_sensitive_endpoints_configured | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_security_middleware.py | test_security_middleware_validate_headers_normal_size | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\startup\test_health_monitor_lifecycle.py | mock_service_config | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\startup\test_health_monitor_lifecycle.py | test_unregister_service | 17 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\websocket\test_websocket_integration.py | test_secure_websocket_config_endpoint | 17 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\websocket\test_websocket_integration.py | test_secure_websocket_health_endpoint | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\websocket\test_websocket_integration.py | test_cors_allowed_origin | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\websocket\test_websocket_integration.py | test_cors_security_violations_tracking | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_generation_service_comprehensive.py | mock_clickhouse | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_generation_service_comprehensive.py | sample_corpus | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_triage_agent_models.py | test_triage_result_validation | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_triage_agent_models.py | test_key_parameters_model | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_triage_agent_models.py | test_user_intent_model | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_quality_gate_advanced.py | test_get_weights_for_content_types | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_quality_gate_advanced.py | test_check_thresholds_all_content_types | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_quality_gate_advanced.py | test_pattern_compilation_in_init | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_database_basic_transactions.py | mock_session | 19 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_missing_tests_validation.py | mock_config | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_missing_tests_validation.py | test_environment_specific_validation | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_missing_tests_validation.py | test_trace_id_management | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_missing_tests_validation.py | test_context_validation | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_missing_tests_validation.py | test_context_serialization | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_missing_tests_validation.py | test_exception_serialization | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_missing_tests_validation.py | test_validation_exception_details | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_missing_tests_validation.py | test_authentication_exception_details | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_missing_tests_validation.py | test_exception_chaining | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_missing_tests_validation.py | test_exception_severity_levels | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_missing_tests_validation.py | test_input_sanitization | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_subagent_logging.py | test_log_agent_communication_enabled | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_subagent_logging.py | test_log_agent_input | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_subagent_logging.py | test_log_agent_output | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_subagent_logging.py | test_calculate_data_size_exception | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_subagent_logging.py | test_log_input_from_agent | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_subagent_logging.py | test_log_output_to_agent | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| auth_service\tests\integration\test_oauth_flows_sync.py | test_oauth_token_exchange_mocked | 39 | 8 | Split into multiple focused test functions or extract helper methods |
| auth_service\tests\integration\test_oauth_flows_sync.py | test_auth_config_endpoint | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| auth_service\tests\integration\test_oauth_flows_sync.py | test_google_oauth_initiate_redirect | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| auth_service\tests\integration\test_oauth_flows_sync.py | test_oauth_callback_missing_params | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| auth_service\tests\integration\test_oauth_flows_sync.py | test_state_parameter_security | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| auth_service\tests\integration\test_oauth_flows_sync.py | test_oauth_endpoints_configured | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\startup\test_startup_status_manager.py | mock_status_data | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_agent_reliability_mixin_core.py | mock_agent | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_agent_reliability_mixin_core.py | mock_agent | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_agent_reliability_mixin_core.py | test_classify_error_severity | 24 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_agent_reliability_mixin_core.py | test_log_error_different_severities | 17 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_agent_reliability_mixin_core.py | mock_agent | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_circuit_breaker.py | test_config_creation_with_defaults | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_circuit_breaker.py | test_config_creation_with_custom_values | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_circuit_breaker.py | test_get_status | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_circuit_breaker.py | test_success_rate_calculation | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_config_websocket_url.py | admin_client | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_config_websocket_url.py | authenticated_client | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_config_websocket_url.py | test_api_config_includes_ws_url | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_config_websocket_url.py | test_api_config_all_expected_fields | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_config_websocket_url.py | test_websocket_config_endpoint | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_config_websocket_url.py | test_config_consistency | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_corpus_routes.py | client | 20 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_corpus_routes.py | test_corpus_create | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_corpus_routes.py | test_corpus_update | 18 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_corpus_routes.py | test_corpus_delete | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_corpus_routes.py | test_corpus_search_filters | 29 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_corpus_routes.py | test_corpus_metadata_extraction | 27 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_corpus_routes.py | test_corpus_similarity_search | 26 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_corpus_routes.py | test_corpus_indexing_status | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_corpus_routes.py | test_corpus_batch_validation | 30 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_websocket_connection.py | test_extract_app_services | 18 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\clickhouse\log_ingestion_tests.py | generate_realistic_logs | 24 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_clickhouse_array_syntax.py | test_performance_with_large_queries | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\test_database_env_service.py | test_validate_production_database_success | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\test_database_env_service.py | test_validate_production_database_failure_with_test_keyword | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\test_database_env_service.py | test_validate_production_database_failure_with_dev_keyword | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\test_database_env_service.py | test_validate_testing_database_success | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\test_database_env_service.py | test_validate_testing_database_failure_with_prod_keyword | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\test_database_env_service.py | test_validate_development_database_success | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\test_database_env_service.py | test_validate_development_database_warning_with_prod_keyword | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\test_database_env_service.py | test_validate_database_environment_no_url | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_state_checkpoint_session_fix.py | mock_session | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_bidirectional_types.py | test_request_response_pairing | 28 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_bidirectional_types.py | test_message_id_tracking | 17 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_bidirectional_types.py | test_connection_state_transitions | 19 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_bidirectional_types.py | test_round_trip_message_integrity | 33 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_bidirectional_types.py | test_type_consistency_across_modules | 24 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_bidirectional_types.py | test_payload_type_consistency | 22 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_bidirectional_types.py | test_error_propagation_consistency | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_bidirectional_types.py | test_invalid_message_type_handling | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_bidirectional_types.py | test_enum_validation_comprehensive | 24 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_bidirectional_types.py | test_message_factory_consistency | 30 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_bidirectional_types.py | test_bidirectional_message_compatibility | 30 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_websocket_execution_engine.py | test_broadcast_executor_has_execution_engine | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_websocket_execution_engine.py | test_late_import_pattern_works | 23 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\unified\e2e\test_database_connections.py | test_redis_connection | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_alert_manager.py | test_get_recent_alerts | 26 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_alert_manager.py | test_get_active_alerts | 26 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_alert_manager.py | test_resolve_alert | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_alert_manager.py | test_determine_recovery_action | 19 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_supply_research_service_crud.py | sample_supply_item | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_supply_research_service_crud.py | sample_update_log | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_supply_research_service_crud.py | test_create_new_supply_item | 24 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_supply_research_service_crud.py | test_update_existing_item_no_changes | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_supply_research_service_crud.py | test_update_existing_item_single_change | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_supply_research_service_crud.py | test_update_existing_item_multiple_changes | 19 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_supply_research_service_crud.py | test_get_update_logs_no_filters | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_supply_research_service_crud.py | test_get_update_logs_with_supply_item_filter | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_supply_research_service_crud.py | test_get_update_logs_with_user_filter | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_supply_research_service_crud.py | test_get_update_logs_with_date_range | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_supply_research_service_crud.py | test_get_update_logs_with_custom_limit | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_supply_research_service_crud.py | test_successful_transaction_commit | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_cache_routes.py | test_cache_metrics | 22 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_cache_routes.py | test_cache_invalidation | 17 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_cache_routes.py | test_cache_performance_monitoring | 20 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_cache_routes.py | test_cache_size_management | 30 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_cache_routes.py | test_cache_health_check | 24 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_cache_routes.py | test_cache_key_analysis | 35 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_cache_routes.py | test_cache_statistics_aggregation | 33 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_security_service.py | test_create_and_validate_access_token | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_data_sub_agent_reliability.py | test_database_connection_failure | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_config_secrets_manager.py | test_staging_environment_project_id_selection | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_config_secrets_manager.py | test_production_environment_project_id_selection | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_config_secrets_manager.py | test_fallback_project_id_when_no_environment | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_config_secrets_manager.py | test_secrets_loaded_from_google_cloud_secret_manager | 23 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_config_secrets_manager.py | test_fallback_to_environment_variables_when_gcp_fails | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_config_secrets_manager.py | test_empty_secrets_handled_gracefully | 17 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_config_secrets_manager.py | test_secret_decoding_error_handling | 21 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_config_secrets_manager.py | test_secrets_successfully_loaded_into_config | 23 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_config_secrets_manager.py | test_critical_secrets_analysis_and_logging | 19 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_config_secrets_manager.py | test_secret_mapping_application_direct_fields | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_config_secrets_manager.py | test_nested_field_mapping_application | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_config_secrets_manager.py | test_secrets_not_logged_in_plain_text | 18 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_config_secrets_manager.py | test_environment_isolation_between_staging_and_production | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_config_secrets_manager.py | test_secret_loading_error_handling_preserves_security | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_config_secrets_manager.py | test_secret_manager_handles_network_timeouts | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_config_secrets_manager.py | test_secret_manager_handles_authentication_failures | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_config_secrets_manager.py | test_partial_secret_loading_continues_operation | 26 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_config_secrets_manager.py | test_secret_manager_retry_mechanism_for_transient_failures | 27 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_websocket_circular_import_regression.py | test_no_baseexecutionengine_import_in_websocket | 25 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_websocket_circular_import_regression.py | test_import_order_independence | 31 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_websocket_circular_import_regression.py | test_agent_registry_accessible_after_imports | 22 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_websocket_circular_import_regression.py | test_websocket_handler_without_execution_engine | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_websocket_circular_import_regression.py | test_broadcast_executor_without_execution_engine | 20 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_websocket_circular_import_regression.py | test_connection_manager_lazy_initialization | 34 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_websocket_circular_import_regression.py | test_connection_modules_import_independently | 33 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_websocket_circular_import_regression.py | test_connection_backward_compatibility | 34 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\startup\test_health_monitor_adaptive.py | mock_service_config | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\startup\test_health_monitor_adaptive.py | test_count_recent_failures | 18 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\startup\test_health_monitor_adaptive.py | test_get_check_interval_adaptive | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\startup\test_health_monitor_adaptive.py | test_get_check_interval_stable | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\startup\test_health_monitor_adaptive.py | test_get_service_status_existing | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\startup\test_health_monitor_adaptive.py | test_create_url_health_check_success | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\startup\test_health_monitor_adaptive.py | test_create_url_health_check_custom_timeout | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\startup\test_config_validation.py | mock_validation_context | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\startup\test_config_validation.py | mock_services_config | 17 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\startup\test_config_validation.py | test_check_file_age_recent | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\startup\test_config_validation.py | test_check_file_age_stale | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\startup\test_config_validation.py | test_load_config_success | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\startup\test_config_validation.py | test_load_config_failure | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\startup\test_config_validation.py | test_get_service_endpoints_local_clickhouse | 17 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\startup\test_config_validation.py | test_get_service_endpoints_secure_clickhouse | 18 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\security\test_security_middleware.py | mock_request | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\security\test_security_middleware.py | test_url_validation | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\security\test_security_middleware.py | test_client_ip_extraction | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\security\test_security_middleware.py | test_rate_limit_reset | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\security\test_security_middleware.py | test_whitelist_bypass | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\test_admin.py | superuser_client | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\test_admin.py | regular_user_client | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_feature_flags_example.py | test_roi_calculator_basic | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_feature_flags_example.py | test_first_time_user_onboarding | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_feature_flags_example.py | test_authenticated_usage_tracking | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_feature_flags_example.py | test_ml_rate_limiter | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_feature_flags_example.py | test_api_response_time | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_feature_flags_example.py | test_websocket_integration | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_feature_flags_example.py | test_multi_llm_orchestration | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_feature_flags_example.py | test_github_api_integration | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_feature_flags_example.py | test_clickhouse_analytics_pipeline | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_feature_flags_example.py | test_enterprise_sso_flow | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_feature_flags_example.py | test_authenticated_websocket_performance | 21 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\unified\test_llm_integration.py | test_llm_cost_tracking_provider_and_tier_variance | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\ws_manager\test_singleton_and_connection.py | test_singleton_instance | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\ws_manager\test_singleton_and_connection.py | test_singleton_thread_safety | 25 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\ws_manager\test_singleton_and_connection.py | test_singleton_with_different_imports | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_synthetic_data_validation.py | test_enhanced_admin_visibility_section_exists | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_synthetic_data_validation.py | test_data_agent_integration_section_exists | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_synthetic_data_validation.py | test_log_structure_coherence_section_exists | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_synthetic_data_validation.py | test_comprehensive_testing_framework_defined | 24 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_synthetic_data_validation.py | test_version_3_improvements_documented | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_synthetic_data_validation.py | test_admin_prompts_categories_defined | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_synthetic_data_validation.py | test_clustering_algorithms_defined | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_synthetic_data_validation.py | test_alerting_rules_defined | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_synthetic_data_validation.py | test_migration_guide_present | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_synthetic_data_validation.py | test_workload_categories_match_spec | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_synthetic_data_validation.py | test_generation_status_enum_matches_spec | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_synthetic_data_validation.py | test_corpus_service_exists | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_synthetic_data_validation.py | test_synthetic_data_service_has_required_methods | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_synthetic_data_validation.py | test_test_file_created | 18 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_synthetic_data_validation.py | test_spec_xml_is_valid | 35 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_synthetic_data_validation.py | test_corpus_lifecycle_states | 17 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_synthetic_data_validation.py | test_workload_distribution_calculation | 20 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_synthetic_data_validation.py | test_batch_size_optimization_range | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_synthetic_data_validation.py | test_websocket_message_types | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_synthetic_data_validation.py | test_quality_metrics_calculation | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_synthetic_data_validation.py | test_circuit_breaker_configuration | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_synthetic_data_validation.py | test_ingestion_rate_targets | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_synthetic_data_validation.py | test_temporal_pattern_types | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_synthetic_data_validation.py | test_tool_catalog_structure | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_synthetic_data_validation.py | test_admin_dashboard_update_frequency | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unified_system\test_oauth_flow.py | mock_auth_client | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unified_system\test_oauth_flow.py | mock_websocket_manager | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\e2e\test_middleware_hook_ordering.py | test_circuit_breaker_integration | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\e2e\test_middleware_hook_ordering.py | test_metrics_tracking_decoration | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\e2e\test_middleware_hook_ordering.py | test_metrics_context_manager | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\e2e\test_middleware_hook_ordering.py | test_operation_type_detection | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_config_manager.py | test_load_from_environment | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_config_manager.py | test_secret_manager_client_creation_success | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_config_manager.py | test_secret_manager_client_creation_failure | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_config_manager.py | test_load_from_secret_manager_success | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_config_manager.py | test_load_secrets_fallback_to_env | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_config_manager.py | test_validate_database_config_missing_url | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_config_manager.py | test_validate_database_config_invalid_url | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_config_manager.py | test_validate_auth_config_missing_jwt_secret | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_config_manager.py | test_validate_auth_config_production_dev_secret | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_config_manager.py | test_get_validation_report_success | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_config_manager.py | test_get_validation_report_failure | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_config_manager.py | test_get_environment_development | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_config_manager.py | test_get_environment_production | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_config_manager.py | test_load_configuration_success | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_config_manager.py | test_get_config_caching | 17 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_config_manager.py | test_get_config | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_config_manager.py | test_full_configuration_flow | 32 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_config_manager.py | test_configuration_error_handling | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_error_handler_recovery_strategy.py | test_recovery_delay_exponential_backoff | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_error_handler_recovery_strategy.py | test_recovery_delay_consistency | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_error_handler_recovery_strategy.py | test_error_recovery_edge_cases | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_websocket_field_alignment.py | test_user_message_payload_schema_has_content_field | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_websocket_field_alignment.py | test_message_handler_extracts_content_field | 19 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_websocket_field_alignment.py | test_message_handler_supports_legacy_text_field | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_websocket_field_alignment.py | test_content_field_takes_precedence_over_text | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_websocket_field_alignment.py | test_empty_content_falls_back_to_text | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_websocket_field_alignment.py | test_both_fields_missing_returns_empty_string | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_websocket_field_alignment.py | test_frontend_payload_structure_matches_backend_expectations | 21 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\integration\test_circuit_breaker_cascade.py | service_configs | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_agent_reliability_mixin_base.py | test_agent_error_creation | 24 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_agent_reliability_mixin_base.py | test_health_status_creation | 33 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_agent_reliability_mixin_base.py | mock_agent | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_agent_reliability_mixin_base.py | test_initialization | 19 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_agent_reliability_mixin_base.py | test_record_successful_operation | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_agent_reliability_mixin_base.py | test_operation_times_history_limit | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_agent_reliability_mixin_base.py | test_error_history_limit | 23 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\config\test_config_secrets_manager.py | test_load_secrets_into_config_success | 19 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\config\test_config_secrets_manager.py | test_load_secrets_into_config_no_secrets | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\config\test_config_secrets_manager.py | test_load_secrets_into_config_error_handling | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\config\test_config_secrets_manager.py | test_apply_secrets_to_config_with_direct_mapping | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\config\test_config_secrets_manager.py | test_apply_secrets_to_config_with_nested_mapping | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\config\test_config_secrets_manager.py | test_analyze_critical_secrets_all_present | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\config\test_config_secrets_manager.py | test_analyze_critical_secrets_some_missing | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\config\test_config_secrets_manager.py | test_get_secret_mappings | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_quality_gate_dataclasses.py | test_quality_metrics_custom_values_setup | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_quality_gate_dataclasses.py | test_quality_metrics_custom_values_validation | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_quality_gate_dataclasses.py | test_validation_result_initialization_basic | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_quality_gate_dataclasses.py | test_validation_result_initialization_extended | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_unified_tool_registry_management.py | unified_registry | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_unified_tool_registry_management.py | sample_tools | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_unified_tool_registry_management.py | test_registry_addition_and_management | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_unified_tool_registry_management.py | test_tool_orchestration_setup | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_unified_tool_registry_management.py | test_health_monitoring_functionality | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_unified_tool_registry_management.py | test_metrics_collection_system | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_base_service_mixin.py | test_update_metrics_success | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_base_service_mixin.py | test_update_metrics_failure | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_base_service_mixin.py | test_update_metrics_average_calculation | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unified_system\fixtures.py | test_environment_config | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_error_handling.py | test_error_details_creation | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_error_handling.py | test_error_details_with_context | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_error_handling.py | test_error_details_serialization | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_error_handling.py | test_netra_exception_with_code | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_error_handling.py | test_handle_netra_exception | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_error_handling.py | test_handle_pydantic_validation_error | 19 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_error_handling.py | test_handle_sqlalchemy_integrity_error | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_error_handling.py | test_handle_http_exception | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_error_handling.py | test_handle_unknown_exception | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_error_handling.py | test_get_http_status_code_mapping | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_error_handling.py | test_trace_id_context | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_error_handling.py | test_get_all_context | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_error_handling.py | test_clear_context | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_error_handling.py | test_error_context_manager | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_error_handling.py | test_get_enriched_error_context | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_error_handling.py | test_error_response_creation | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_error_handling.py | test_error_response_with_details | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_error_handling.py | test_error_response_serialization | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_permission_service_admin.py | test_is_admin_or_higher | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_permission_service_admin.py | test_is_developer_or_higher | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_permission_service_admin.py | test_has_any_permission | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_permission_service_admin.py | test_has_all_permissions | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_permission_service_admin.py | test_permission_escalation_attempt | 17 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_permission_service_admin.py | test_grant_permission | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_permission_service_admin.py | test_grant_permission_existing_permissions | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_permission_service_admin.py | test_grant_permission_duplicate | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_permission_service_admin.py | test_revoke_permission | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_permission_service_admin.py | test_revoke_permission_existing | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_permission_service_admin.py | test_set_user_role_valid | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_permission_service_admin.py | test_set_user_role_invalid | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_permission_service_admin.py | test_custom_permissions_override_role | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_permission_service_admin.py | test_super_admin_permissions_comprehensive | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_permission_service_admin.py | test_permission_inheritance_chain | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_core_infrastructure_11_20.py | mock_config | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_core_infrastructure_11_20.py | test_context_preservation_across_calls | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_core_infrastructure_11_20.py | test_error_response_structure | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_core_infrastructure_11_20.py | test_netra_exception_structure | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_core_infrastructure_11_20.py | test_structured_logging | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_core_infrastructure_11_20.py | test_migration_safety_checks | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_core_infrastructure_11_20.py | test_secret_encryption | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_core_infrastructure_11_20.py | test_secret_validation | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_core_infrastructure_11_20.py | test_log_correlation | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_core_infrastructure_11_20.py | test_log_aggregation | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| auth_service\tests\integration\test_oauth_flows.py | mock_google_tokens | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| auth_service\tests\integration\test_oauth_flows.py | mock_microsoft_tokens | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| auth_service\tests\integration\test_oauth_flows.py | test_google_oauth_config | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| auth_service\tests\integration\test_oauth_flows.py | test_oauth_endpoints_configuration | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\integration\test_first_time_user_integration.py | test_first_time_user_components | 25 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_health_types.py | test_component_health_creation | 18 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_health_types.py | test_component_health_defaults | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_health_types.py | test_system_alert_creation | 18 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_health_types.py | test_system_alert_defaults | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_health_types.py | test_health_check_result_creation | 17 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_health_types.py | test_health_check_result_failure | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_health_types.py | test_health_check_result_defaults | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_health_types.py | test_system_resource_metrics_creation | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_health_types.py | test_system_resource_metrics_timestamp_default | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\startup\test_config_engine.py | mock_validation_context | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\startup\test_config_engine.py | test_get_fallback_action_stale_ci | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\integration\test_database_pool_integration.py | pool_config | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_synthetic_data_service_fixtures.py | generation_config | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_synthetic_data_service_fixtures.py | full_stack | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\clickhouse\array_operations_tests.py | test_fix_incorrect_array_syntax | 22 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\clickhouse\array_operations_tests.py | test_validate_query_catches_errors | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| auth_service\tests\test_session_cleanup.py | test_cleanup_job_configuration | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| auth_service\tests\test_session_cleanup.py | test_cleanup_job_frequency_calculation | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| auth_service\tests\test_session_cleanup.py | test_cleanup_metrics_collection | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_error_handler_agent_errors.py | test_agent_error_inheritance | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_error_handler_agent_errors.py | test_agent_error_serialization | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_websocket_handler_routing.py | test_handler_registration | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_websocket_handler_routing.py | test_handler_duplicate_registration_prevention | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_websocket_handler_routing.py | test_handler_unregistration | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_llm_cache_routes.py | test_cache_metrics | 17 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_llm_cache_routes.py | test_cache_invalidation | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\integration\test_critical_integration.py | setup_real_database | 26 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\integration\test_critical_integration.py | setup_integration_infrastructure | 18 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\auth_integration\test_jwt_secret_consistency.py | test_both_services_use_same_jwt_secret_key_env_var | 20 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\auth_integration\test_jwt_secret_consistency.py | test_jwt_secret_key_takes_priority_over_jwt_secret | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\auth_integration\test_jwt_secret_consistency.py | test_auth_service_jwt_handler_uses_correct_secret | 19 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\auth_integration\test_jwt_secret_consistency.py | test_token_validation_consistency | 21 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\auth_integration\test_jwt_secret_consistency.py | test_environment_specific_secret_priority | 23 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\auth_integration\test_jwt_secret_consistency.py | test_development_fallback_when_no_secrets | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\auth_integration\test_jwt_secret_consistency.py | test_staging_production_require_secret | 25 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_repository_basic_transactions.py | mock_session | 19 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unified_system\test_agent_activation.py | mock_agent_registry | 19 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_type_validation_part3.py | test_validate_schemas_missing_frontend_schema | 38 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_type_validation_part3.py | test_validate_schemas_missing_backend_field | 34 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_type_validation_part3.py | test_validate_schemas_with_type_mismatch | 43 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_type_validation_part3.py | test_validate_schemas_type_alias_skip | 33 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_type_validation_part3.py | test_validate_schemas_extra_frontend_schema | 33 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_type_validation_part3.py | test_get_backend_field_type_with_ref | 18 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_type_validation_part3.py | test_get_backend_field_type_with_items | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_type_validation_part3.py | test_get_backend_field_type_with_anyof | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\unified\test_real_client_factory.py | test_auth_headers_with_token | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\unified\test_real_client_factory.py | test_message_preparation | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\unified\test_real_client_factory.py | test_ssl_context_creation | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_websocket_message_routing_critical.py | message_processor | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\unified\test_config_validation.py | test_factory_functions | 19 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\unified\test_config_validation.py | test_database_manager | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\unified\test_config_validation.py | test_helper_functions | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\unified\test_config_validation.py | test_token_manager | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\unified\test_config_validation.py | test_configuration_isolation | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_supervisor_consolidated_advanced.py | test_get_stats | 28 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_json_parsing_fix_functions.py | test_fix_data_with_string_fields | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_json_parsing_fix_functions.py | test_fix_data_with_missing_fields | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_json_parsing_fix_functions.py | test_fix_empty_data | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_json_parsing_fix_functions.py | test_fix_data_with_invalid_fields | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_json_parsing_fix_functions.py | test_fix_data_preserves_other_fields | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_json_parsing_fix_functions.py | test_fix_data_with_nested_structures | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_json_parsing_fix_functions.py | test_fix_data_logging_behavior | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_staging_deployment_readiness.py | staging_env_vars | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_staging_deployment_readiness.py | test_staging_secret_mappings_complete | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_staging_deployment_readiness.py | test_staging_cors_configuration | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_staging_deployment_readiness.py | test_staging_resource_limits | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_staging_deployment_readiness.py | test_staging_not_using_default_secrets | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_staging_deployment_readiness.py | test_staging_security_headers_present | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_staging_deployment_readiness.py | test_all_required_env_vars_present | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_staging_deployment_readiness.py | test_staging_deployment_ready | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_llm_load_balancing.py | load_balanced_manager | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_tool_permission_business_requirements.py | test_check_business_requirements_feature_flags_pass | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_tool_permission_business_requirements.py | test_check_business_requirements_feature_flags_fail | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_tool_permission_business_requirements.py | test_check_business_requirements_all_conditions | 17 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_e2e_complete.py | sample_user_message | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_e2e_complete.py | sample_example_message | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\performance\test_large_scale_generation.py | resource_monitor | 30 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_data_sub_agent_core.py | test_initialization_with_defaults | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_data_sub_agent_core.py | test_initialization_with_custom_config | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_data_sub_agent_core.py | test_initialization_with_redis | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_data_sub_agent_core.py | test_validate_required_fields | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_data_sub_agent_core.py | test_validate_missing_fields | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_data_sub_agent_core.py | test_validate_data_types | 21 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_config_environment_detection.py | test_testing_environment_detection_takes_priority | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_config_environment_detection.py | test_cloud_run_environment_detection_staging | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_config_environment_detection.py | test_cloud_run_environment_detection_production | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_config_environment_detection.py | test_fallback_to_environment_variable | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_config_environment_detection.py | test_default_development_environment | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_config_environment_detection.py | test_production_config_creation | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_config_environment_detection.py | test_staging_config_creation | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_config_environment_detection.py | test_testing_config_creation | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_config_environment_detection.py | test_development_config_creation | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_config_environment_detection.py | test_unknown_environment_fallback_to_development | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_config_environment_detection.py | test_websocket_url_updated_with_server_port | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_config_environment_detection.py | test_websocket_url_not_modified_without_server_port | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_config_environment_detection.py | test_websocket_url_logging_when_port_updated | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_config_environment_detection.py | test_cloud_run_staging_detection_with_k_service | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_config_environment_detection.py | test_cloud_run_detection_without_indicators | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_config_environment_detection.py | test_cloud_run_detection_with_pr_number | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_config_environment_detection.py | test_config_classes_mapping_completeness | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_config_environment_detection.py | test_config_classes_point_to_correct_types | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_config_environment_detection.py | test_config_initialization_with_valid_classes | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_config_environment_detection.py | test_environment_detection_with_mixed_case | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_config_environment_detection.py | test_environment_detection_with_whitespace | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_config_environment_detection.py | test_environment_detection_logging | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\integration\test_system_startup_integration.py | minimal_environment | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_rate_limiter_unit.py | free_tier_permission_definitions | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_rate_limiter_unit.py | pro_tier_permission_definitions | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_rate_limiter_unit.py | unlimited_permission_definitions | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_rate_limiter_unit.py | test_get_applicable_rate_limits_single_permission | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_rate_limiter_unit.py | test_get_applicable_rate_limits_multiple_permissions | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_rate_limiter_unit.py | test_build_limit_exceeded_response_structure | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\unified\test_import_integrity.py | test_no_missing_required_packages | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\unified\test_import_integrity.py | test_all_modules_importable | 30 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\unified\test_import_integrity.py | test_performance_requirements | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\unified\test_import_integrity.py | test_minimum_success_rate | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\unified\test_import_integrity.py | test_critical_directories_coverage | 21 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\unified\test_import_integrity.py | test_validation_report_generation | 22 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\unified\test_import_integrity.py | test_import_integrity_summary | 22 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\unified\test_database_data_flow.py | test_user_data | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_corpus_service_comprehensive.py | mock_db | 18 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_corpus_service_comprehensive.py | mock_vector_store | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_corpus_service_comprehensive.py | corpus_service | 51 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_corpus_service_comprehensive.py | test_redis_connection_failure_recovery | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\startup\test_staged_health_monitor.py | mock_service_config | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\startup\test_staged_health_monitor.py | test_health_check_result_creation | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\startup\test_staged_health_monitor.py | test_health_check_result_with_error | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\startup\test_staged_health_monitor.py | test_stage_config_creation | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\startup\test_staged_health_monitor.py | test_service_state_creation | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\startup\test_staged_health_monitor.py | test_init_stage_configs | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\startup\test_staged_health_monitor.py | test_unregister_service | 17 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\startup\test_staged_health_monitor.py | test_count_recent_failures | 18 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\startup\test_staged_health_monitor.py | test_get_check_interval_adaptive | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\startup\test_staged_health_monitor.py | test_get_check_interval_stable | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\startup\test_staged_health_monitor.py | test_get_service_status_existing | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\startup\test_staged_health_monitor.py | test_create_url_health_check_success | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\startup\test_staged_health_monitor.py | test_create_url_health_check_custom_timeout | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_config_loader_core.py | test_load_env_var_success_with_valid_config | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_config_loader_core.py | test_load_env_var_failure_missing_field | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_config_loader_core.py | test_load_env_var_failure_missing_env_var | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_config_loader_core.py | test_load_env_var_logging_on_success | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_config_loader_core.py | test_set_clickhouse_host_updates_both_configs | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_config_loader_core.py | test_set_clickhouse_port_validates_integer | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_config_loader_core.py | test_set_clickhouse_password_security_logging | 17 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_config_loader_core.py | test_set_clickhouse_user_logs_username | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_config_loader_core.py | test_set_gemini_api_key_updates_all_llm_configs | 17 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_config_loader_core.py | test_set_llm_api_key_individual_config | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_config_loader_core.py | test_set_llm_api_key_missing_config_handles_gracefully | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_config_loader_core.py | test_critical_vars_mapping_includes_database_vars | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_config_loader_core.py | test_critical_vars_mapping_includes_auth_vars | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_config_loader_core.py | test_critical_vars_mapping_includes_env_vars | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_config_loader_core.py | test_critical_vars_mapping_completeness | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_config_loader_core.py | test_apply_single_secret_to_nested_config | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_config_loader_core.py | test_navigate_to_parent_object_success | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_config_loader_core.py | test_navigate_to_parent_object_missing_path | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_config_loader_core.py | test_get_attribute_or_none_success | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_config_loader_core.py | test_get_attribute_or_none_missing_attribute | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_config_loader_core.py | test_k_service_staging_detection | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_config_loader_core.py | test_k_service_no_staging_detection | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_config_loader_core.py | test_pr_number_staging_detection | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_config_loader_core.py | test_pr_number_no_staging_detection | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_config_loader_core.py | test_detect_cloud_run_environment_k_service_priority | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_config_loader_core.py | test_detect_cloud_run_environment_fallback_to_pr_number | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\e2e\test_mixins_comprehensive.py | test_state_history_management | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\e2e\test_mixins_comprehensive.py | test_health_status_calculation | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\e2e\test_mixins_comprehensive.py | test_error_context_logging | 18 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\e2e\test_mixins_comprehensive.py | test_operation_cache_tracking | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\e2e\test_mixins_comprehensive.py | test_error_severity_validation | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\e2e\test_mixins_comprehensive.py | test_validation_thresholds | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\e2e\test_mixins_comprehensive.py | test_cache_ttl_behavior | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\e2e\test_mixins_comprehensive.py | test_cache_size_limits | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\e2e\test_mixins_comprehensive.py | test_health_metrics_caching | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\e2e\test_mixins_comprehensive.py | test_cache_invalidation_timing | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_clickhouse_query_interceptor.py | test_interceptor_statistics_tracking | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_clickhouse_query_interceptor.py | test_interceptor_performance_metrics | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_clickhouse_query_interceptor.py | test_query_fixing_consistency | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\performance\test_performance_cache.py | test_read_query_detection | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\performance\test_performance_cache.py | test_cache_ttl_determination | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_data_validation_comprehensive.py | injection_test_data | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_data_validation_comprehensive.py | test_required_fields_presence | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_data_validation_comprehensive.py | test_range_boundary_validation | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_data_validation_comprehensive.py | test_injection_attack_prevention | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_data_validation_comprehensive.py | test_processing_result_structure_compliance | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_data_validation_comprehensive.py | test_forward_compatibility_extra_fields | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_data_validation_comprehensive.py | test_schema_migration_field_renaming | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_data_validation_comprehensive.py | test_deprecation_handling_graceful | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_data_validation_comprehensive.py | test_unicode_character_handling | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_data_validation_comprehensive.py | test_maximum_size_input_boundaries | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_data_validation_comprehensive.py | test_websocket_message_type_validation | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_data_validation_comprehensive.py | test_message_sanitization_comprehensive | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_data_validation_comprehensive.py | test_nested_data_structure_validation | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\test_websocket_type_safety.py | test_complete_type_safety_suite | 25 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\test_websocket_type_safety.py | test_message_factory_functionality | 21 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\test_websocket_type_safety.py | test_validation_error_handling | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\test_websocket_type_safety.py | test_message_size_limits | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\test_websocket_type_safety.py | test_special_characters_in_messages | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\test_websocket_type_safety.py | test_empty_and_null_values | 24 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\test_websocket_type_safety.py | test_numeric_string_conversion | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_permission_service_integration.py | test_full_workflow_integration | 26 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_permission_service_integration.py | test_new_user_onboarding_flow | 21 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_permission_service_integration.py | test_production_environment_security | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_permission_service_integration.py | test_customer_support_workflow | 18 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_permission_service_integration.py | test_developer_debugging_workflow | 22 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_permission_service_integration.py | test_admin_user_management_workflow | 29 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_permission_service_integration.py | test_environment_based_access_control | 24 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_permission_service_integration.py | test_privilege_escalation_prevention | 21 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_permission_service_integration.py | test_role_transition_security | 24 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_permission_service_integration.py | test_custom_permission_security | 30 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_supply_research_service_price_calculations.py | sample_openai_item | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_supply_research_service_price_calculations.py | sample_anthropic_item | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_supply_research_service_price_calculations.py | test_calculate_price_changes_with_increases | 17 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_supply_research_service_price_calculations.py | test_calculate_price_changes_with_decreases | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_supply_research_service_price_calculations.py | test_calculate_price_changes_sorted_by_magnitude | 36 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_supply_research_service_price_calculations.py | test_calculate_price_changes_with_provider_filter | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_supply_research_service_price_calculations.py | test_provider_comparison_with_multiple_providers | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_supply_research_service_price_calculations.py | test_provider_comparison_no_pricing_data | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_supply_research_service_price_calculations.py | test_detect_stale_data_anomalies | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_supply_research_service_price_calculations.py | test_service_functionality_without_redis | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_type_validation_part2.py | test_normalize_backend_type_optional | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_type_validation_part2.py | test_normalize_backend_type_union | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_type_validation_part2.py | test_normalize_backend_type_list | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_type_validation_part2.py | test_normalize_backend_type_dict | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_type_validation_part2.py | test_normalize_frontend_type | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_type_validation_part2.py | test_determine_mismatch_severity_critical | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_type_validation_part2.py | test_determine_mismatch_severity_error | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_type_validation_part2.py | test_determine_mismatch_severity_warning | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_type_validation_part2.py | test_generate_type_suggestion_string_number | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_type_validation_part2.py | test_deeply_nested_optional_types | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_type_validation_part2.py | test_complex_union_types | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_type_validation_part2.py | test_nested_list_types | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_type_validation_part2.py | test_type_mapping_edge_cases | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_type_validation_part2.py | test_array_type_variations | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_type_validation_part2.py | test_object_type_variations | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_type_validation_part2.py | test_special_type_compatibility | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\test_framework\test_coverage_generation.py | test_unit_level_generates_coverage | 28 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\test_framework\test_coverage_generation.py | test_integration_level_generates_coverage | 27 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\test_framework\test_coverage_generation.py | test_critical_level_generates_coverage | 27 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\test_framework\test_coverage_generation.py | test_smoke_level_does_not_generate_coverage | 27 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\test_framework\test_coverage_generation.py | test_no_coverage_flag_overrides_unit_level | 42 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\test_framework\test_coverage_generation.py | test_coverage_in_backend_args_unit_level | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\test_framework\test_coverage_generation.py | test_coverage_in_backend_args_integration_level | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\test_framework\test_coverage_generation.py | test_coverage_in_backend_args_critical_level | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\test_framework\test_coverage_generation.py | test_speed_optimizations_remove_coverage_for_backend_runner | 35 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\examples\test_pattern_examples.py | test_data_factory | 58 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\examples\test_pattern_examples.py | mock_dependencies | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\integration\staging\test_staging_auth_service_sync.py | staging_config | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_supervisor_consolidated_core.py | test_init_base | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_supervisor_consolidated_core.py | test_init_services | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_supervisor_consolidated_core.py | test_init_components | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_supervisor_consolidated_core.py | test_init_hooks | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_supervisor_consolidated_core.py | test_initialization_with_none_values | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_supervisor_consolidated_core.py | test_register_agent | 19 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_supervisor_consolidated_core.py | test_register_hook | 17 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_supervisor_consolidated_core.py | test_register_hook_invalid_event | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_supervisor_consolidated_core.py | test_agents_property | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_supervisor_consolidated_core.py | test_sub_agents_property_getter | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_supervisor_consolidated_core.py | test_sub_agents_property_setter | 20 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_scheduler_retry_logic.py | scheduler_with_redis | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_key_parameters_pydantic_access.py | execution_engine | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_key_parameters_pydantic_access.py | test_build_analysis_params_with_pydantic_model | 21 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_key_parameters_pydantic_access.py | test_build_analysis_params_with_dict | 21 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_key_parameters_pydantic_access.py | test_build_analysis_params_with_empty_dict | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_key_parameters_pydantic_access.py | test_build_analysis_params_with_partial_pydantic | 20 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_key_parameters_pydantic_access.py | test_build_analysis_params_from_state | 36 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_key_parameters_pydantic_access.py | test_build_analysis_params_no_triage_result | 19 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_key_parameters_pydantic_access.py | test_mixed_type_handling_no_errors | 26 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\test_example_message_integration_final.py | mock_dependencies | 27 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\test_example_message_integration_final.py | test_enhanced_api_endpoints | 49 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\test_example_message_integration_final.py | test_circuit_breaker_integration | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\test_example_message_integration_final.py | test_error_handling_integration | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\test_example_message_integration_final.py | test_business_value_integration | 31 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\test_example_message_integration_final.py | test_all_components_initialized | 20 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\test_example_message_integration_final.py | test_error_boundaries_complete | 30 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\test_example_message_integration_final.py | test_resource_cleanup_comprehensive | 27 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\test_example_message_integration_final.py | test_monitoring_and_observability | 18 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\test_example_message_integration_final.py | test_scalability_preparations | 35 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_security_service_authentication.py | sample_users | 17 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_supervisor_flow_logger.py | test_update_todo_state | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_supervisor_flow_logger.py | test_json_log_format_compliance | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_supervisor_flow_logger.py | test_correlation_id_tracking_consistency | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_supervisor_flow_logger.py | test_todo_state_transitions_complete_flow | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_supervisor_flow_logger.py | test_flow_state_tracking_progression | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_supervisor_flow_logger.py | test_build_base_log_entry | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_server_to_client_types.py | test_agent_lifecycle_messages_validation | 17 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_server_to_client_types.py | test_agent_started_message | 20 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_server_to_client_types.py | test_agent_completed_message | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_server_to_client_types.py | test_agent_error_message | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_server_to_client_types.py | test_tool_messages_validation | 17 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_server_to_client_types.py | test_tool_started_message | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_server_to_client_types.py | test_tool_completed_message | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_server_to_client_types.py | test_subagent_messages_validation | 30 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_server_to_client_types.py | test_thread_response_messages_validation | 35 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_server_to_client_types.py | test_streaming_messages_validation | 29 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_server_to_client_types.py | test_error_message_validation | 17 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_server_to_client_types.py | test_connection_established_message | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_server_to_client_types.py | test_server_message_serialization | 18 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_server_to_client_types.py | test_error_severity_validation | 22 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_server_to_client_types.py | test_batch_server_message_validation | 17 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_server_to_client_types.py | test_server_message_timestamp_validation | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_server_to_client_types.py | test_message_id_uniqueness | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\integration\test_cross_service_config.py | temp_project_root | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\integration\test_cross_service_config.py | test_service_discovery | 44 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\integration\test_cross_service_config.py | test_health_monitor | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\integration\test_cross_service_config.py | test_fastapi_app | 25 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\integration\test_cross_service_config.py | test_app_with_cors | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\integration\test_cross_service_config.py | mock_environment_variables | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\integration\test_cross_service_config.py | mock_httpx_responses | 35 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_agent_e2e_critical_setup.py | setup_agent_infrastructure | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\helpers\shared_test_types.py | test_database_connection_failure | 20 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\helpers\shared_test_types.py | test_redis_connection_failure_recovery | 18 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\helpers\shared_test_types.py | test_multi_component_interaction | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\helpers\shared_test_types.py | test_service_initialization | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\helpers\shared_test_types.py | test_basic_operations | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\helpers\shared_test_types.py | test_trace_id_management | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\helpers\shared_test_types.py | test_error_context_preservation | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\helpers\shared_test_types.py | test_error_logging_integration | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\helpers\shared_test_types.py | mock_db | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| auth_service\tests\test_token_validation.py | test_create_access_token_basic | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| auth_service\tests\test_token_validation.py | test_create_access_token_with_permissions | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| auth_service\tests\test_token_validation.py | test_create_refresh_token | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| auth_service\tests\test_token_validation.py | test_create_service_token | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| auth_service\tests\test_token_validation.py | test_validate_valid_access_token | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| auth_service\tests\test_token_validation.py | test_validate_invalid_token_type | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| auth_service\tests\test_token_validation.py | test_validate_token_with_invalid_signature | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| auth_service\tests\test_token_validation.py | test_token_expiry_validation | 19 | 8 | Split into multiple focused test functions or extract helper methods |
| auth_service\tests\test_token_validation.py | test_token_near_expiry_still_valid | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| auth_service\tests\test_token_validation.py | test_successful_token_refresh | 19 | 8 | Split into multiple focused test functions or extract helper methods |
| auth_service\tests\test_token_validation.py | test_extract_standard_claims | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| auth_service\tests\test_token_validation.py | test_extract_user_id_unsafe | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| auth_service\tests\test_token_validation.py | test_valid_signature_verification | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| auth_service\tests\test_token_validation.py | test_tampered_payload_detection | 32 | 8 | Split into multiple focused test functions or extract helper methods |
| auth_service\tests\test_token_validation.py | test_token_blacklist_concept | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| auth_service\tests\test_token_validation.py | test_token_jti_for_revocation | 17 | 8 | Split into multiple focused test functions or extract helper methods |
| auth_service\tests\test_token_validation.py | test_token_validation_with_old_key | 18 | 8 | Split into multiple focused test functions or extract helper methods |
| auth_service\tests\test_token_validation.py | test_graceful_key_transition | 18 | 8 | Split into multiple focused test functions or extract helper methods |
| auth_service\tests\test_token_validation.py | test_header_tampering_detection | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| auth_service\tests\test_token_validation.py | test_none_algorithm_attack_prevention | 29 | 8 | Split into multiple focused test functions or extract helper methods |
| auth_service\tests\test_token_validation.py | test_algorithm_confusion_prevention | 17 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\performance\test_performance_monitoring.py | test_performance_indexes_definition | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\performance\test_performance_monitoring.py | test_query_analysis_for_indexes | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_corpus_audit.py | sample_audit_log | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_corpus_audit.py | test_timer_measures_duration | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\integration\test_agent_state_persistence_recovery.py | redis_manager_mock | 37 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_resilience.py | test_cors_handles_malicious_origin | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_resilience.py | test_cors_wildcard_security | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\integration\test_service_discovery.py | test_config_structure_validation | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\integration\test_service_discovery.py | test_auth_service_endpoint_discovery | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\integration\test_service_discovery.py | test_backend_service_discovery_info | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\integration\test_service_discovery.py | test_websocket_url_consistency | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\integration\test_service_discovery.py | test_config_refresh_mechanism | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\integration\test_service_discovery.py | test_cache_invalidation_on_update | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\integration\test_service_discovery.py | test_multiple_service_endpoint_discovery | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\integration\test_service_discovery.py | test_service_discovery_file_persistence | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\integration\test_service_discovery.py | test_dynamic_configuration_validation | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\integration\test_service_discovery.py | test_websocket_config_schema_validation | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\integration\test_service_discovery.py | test_service_discovery_error_handling | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\integration\test_thread_initialization.py | thread_data | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\test_example_message_flow_comprehensive.py | sample_message | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\test_example_message_flow_comprehensive.py | test_sequence_generation | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\test_example_message_flow_comprehensive.py | test_transactional_message_handling | 25 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\test_example_message_flow_comprehensive.py | test_message_retry_logic | 23 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\test_example_message_flow_comprehensive.py | test_atomic_cleanup | 18 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\test_example_message_flow_comprehensive.py | test_connection_activity_tracking | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\test_example_message_flow_comprehensive.py | test_error_count_management | 24 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\test_example_message_flow_comprehensive.py | test_session_updates | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\test_example_message_flow_comprehensive.py | test_user_session_tracking | 19 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\test_example_message_flow_comprehensive.py | test_session_statistics | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\test_example_message_flow_comprehensive.py | test_message_sequencing_under_failure | 30 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\test_example_message_flow_comprehensive.py | test_memory_usage_under_load | 22 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\test_example_message_flow_comprehensive.py | test_category_routing_logic | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\test_example_message_flow_comprehensive.py | test_complexity_handling | 19 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\test_example_message_flow_comprehensive.py | test_input_validation_comprehensive | 21 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\test_example_message_flow_comprehensive.py | test_input_sanitization | 23 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\test_example_message_flow_comprehensive.py | test_field_validation_constraints | 22 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\test_example_message_flow_comprehensive.py | test_user_id_validation | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\test_example_message_flow_comprehensive.py | test_performance_benchmarks | 26 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\startup\test_startup_diagnostics.py | mock_diagnostic_error | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\startup\test_startup_diagnostics.py | test_generate_recommendations_many_errors | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_tool_registry_validation.py | test_tool_interface_validation | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_tool_registry_validation.py | test_tool_metadata_validation | 20 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_tool_registry_validation.py | test_tool_security_validation | 20 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_tool_registry_validation.py | test_tool_performance_validation | 31 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_tool_registry_validation.py | test_tool_compatibility_validation | 18 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_tool_registry_validation.py | test_tool_dependency_validation | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_tool_registry_validation.py | test_tool_version_compatibility_validation | 19 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_tool_registry_validation.py | test_tool_input_schema_validation | 20 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_tool_registry_validation.py | test_tool_output_validation | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_tool_registry_validation.py | test_bulk_validation | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_tool_registry_validation.py | test_validation_error_reporting | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_health_checkers.py | test_create_success_result | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_health_checkers.py | test_create_failed_result | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_health_checkers.py | test_create_disabled_result | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_health_checkers.py | test_system_resources_success | 22 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_health_checkers.py | test_system_resources_high_usage | 17 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_health_checkers.py | test_system_resources_response_time | 17 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_reference_management.py | test_create_reference | 45 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_reference_management.py | test_get_reference_by_id | 45 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_reference_management.py | test_search_references | 45 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_reference_management.py | test_update_reference | 38 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_reference_management.py | test_delete_reference | 30 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_state_persistence_integration_critical.py | mock_db_session | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_supply_researcher_service.py | test_service_get_supply_items | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_supply_researcher_service.py | test_service_create_supply_item | 17 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_supply_researcher_service.py | test_service_calculate_price_changes | 21 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_supply_researcher_service.py | test_service_provider_comparison | 19 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_supply_researcher_service.py | test_service_detect_anomalies | 22 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_supply_researcher_service.py | test_service_validate_supply_data | 26 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_supply_researcher_service.py | test_invalid_data_validation | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_redis_manager_performance.py | test_metrics_collection_accuracy | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\clickhouse\timeseries_analysis_tests.py | test_moving_average_calculation | 30 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\clickhouse\timeseries_analysis_tests.py | test_anomaly_detection_with_zscore | 43 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\startup\test_error_aggregator.py | sample_error | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\startup\test_error_aggregator.py | sample_errors | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\startup\test_error_aggregator.py | test_row_to_error_conversion | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\startup\test_error_aggregator.py | test_calculate_error_breakdowns | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_quality_monitoring_basic.py | test_initialization_with_dependencies | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_quality_monitoring_basic.py | test_alert_thresholds_exist | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_quality_monitoring_basic.py | test_alert_thresholds_structure | 17 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_quality_monitoring_basic.py | test_alert_threshold_values | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_quality_monitoring_basic.py | test_metric_type_enum_values | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_triage_sub_agent.py | test_initialization_with_redis | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_triage_sub_agent.py | test_extract_numerical_thresholds | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_triage_sub_agent.py | test_triage_result_validation | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_triage_sub_agent.py | test_key_parameters_model | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_triage_sub_agent.py | test_user_intent_model | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_triage_sub_agent.py | test_hash_generation | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_type_validation_part4.py | test_validate_type_consistency | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_type_validation_part4.py | test_typescript_parser_malformed_input | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_type_validation_part4.py | test_empty_schemas | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_type_validation_part4.py | test_special_characters_in_field_names | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\integration\test_admin_agent_integration.py | mock_supervisor | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unified_system\test_dev_launcher_startup.py | launcher_config | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_llm_resource_manager.py | test_pool_creation | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| test_framework\test_unified_orchestrator.py | test_orchestrator_cleanup | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| test_framework\test_unified_orchestrator.py | test_initialization | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| test_framework\test_unified_orchestrator.py | test_service_config_structure | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| test_framework\test_unified_orchestrator.py | test_run_python_tests_success | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| test_framework\test_unified_orchestrator.py | test_run_python_tests_failure | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| test_framework\test_unified_orchestrator.py | test_calculate_summary | 17 | 8 | Split into multiple focused test functions or extract helper methods |
| test_framework\test_unified_orchestrator.py | test_determine_overall_success | 18 | 8 | Split into multiple focused test functions or extract helper methods |
| test_framework\test_unified_orchestrator.py | test_create_failure_result | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| test_framework\test_unified_orchestrator.py | test_run_tests_sequential | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_compensation_engine_core.py | test_handler_registration_priority_ordering | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_compensation_engine_core.py | test_handler_registration_maintains_order_on_multiple_registrations | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_compensation_engine_core.py | test_compensation_status_tracking_accuracy | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_compensation_engine_core.py | test_compensation_cleanup_removes_completed_actions | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_compensation_engine_core.py | test_compensation_cleanup_preserves_active_actions | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_compensation_engine_core.py | test_get_active_compensations_returns_current_list | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\integration\staging\test_staging_startup_configuration_validation.py | staging_env_vars | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\integration\staging\test_staging_startup_configuration_validation.py | test_all_required_staging_environment_variables_present | 19 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\integration\staging\test_staging_startup_configuration_validation.py | test_staging_ssl_requirements_enforced | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\integration\staging\test_staging_startup_configuration_validation.py | test_configuration_loading_from_multiple_sources | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\integration\staging\test_staging_startup_configuration_validation.py | test_staging_specific_settings_override_development_defaults | 17 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\integration\staging\test_staging_startup_configuration_validation.py | test_clickhouse_staging_configuration_validation | 20 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\integration\staging\test_staging_startup_configuration_validation.py | test_fallback_to_default_when_env_missing | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\integration\staging\test_staging_startup_configuration_validation.py | test_configuration_validation_reports_comprehensive_issues | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\integration\staging\test_staging_startup_configuration_validation.py | test_database_summary_reflects_staging_state | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\integration\staging\test_staging_startup_configuration_validation.py | test_localhost_restriction_enforced_in_staging | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_health_checkers_system.py | mock_psutil | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_health_checkers_system.py | test_check_system_resources_success | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_health_checkers_system.py | test_check_system_resources_high_usage | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_health_checkers_system.py | test_check_system_resources_psutil_error | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_health_checkers_system.py | test_health_score_calculation_bounds | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_health_checkers_system.py | test_websocket_health_score_calculation | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_health_checkers_system.py | test_system_metrics_extraction_accuracy | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_health_checkers_system.py | test_system_resources_edge_case_zero_values | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_health_checkers_system.py | test_system_resources_maximum_stress | 17 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_health_checkers_system.py | test_health_score_averaging_algorithm | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_health_checkers_system.py | test_system_resource_metadata_completeness | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_health_checkers_system.py | test_response_time_measurement_accuracy | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\e2e\test_thread_error_handling.py | mock_db_session | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\e2e\test_websocket_integration.py | error_prone_websocket | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_fallback_coordinator_integration.py | coordinator | 28 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_fallback_coordinator_integration.py | full_coordinator | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_secret_manager_core.py | secret_manager | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_secret_manager_core.py | test_rotate_secret_success | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_secret_manager_core.py | test_get_secrets_needing_rotation | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_secret_manager_core.py | test_get_security_metrics | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_secret_manager_core.py | test_cleanup_access_log | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_secret_manager_core.py | test_get_audit_logs_all | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_secret_manager_core.py | test_get_audit_logs_filtered | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_secret_manager_core.py | test_register_secret_with_encryption | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_secret_manager_core.py | test_register_secret_with_expiration | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_secret_manager_core.py | test_secret_metadata_access_recording | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_secret_manager_core.py | test_initialization_with_environment | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_secret_manager_core.py | test_secret_rotation_metadata_update | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_secret_manager_core.py | test_security_metrics_by_access_level | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_secret_manager_core.py | test_audit_log_filtering_accuracy | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_quality_gate_scoring_advanced.py | test_weighted_score_no_penalties | 22 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_quality_gate_scoring_advanced.py | test_weighted_score_all_penalties | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_client_to_server_types.py | test_start_agent_message_validation | 27 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_client_to_server_types.py | test_user_message_validation | 17 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_client_to_server_types.py | test_thread_operations_validation | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_client_to_server_types.py | test_control_messages_validation | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_client_to_server_types.py | test_get_thread_history_validation | 18 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_client_to_server_types.py | test_required_fields_validation | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_client_to_server_types.py | test_optional_fields_validation | 17 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_client_to_server_types.py | test_field_type_validation | 17 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_client_to_server_types.py | test_extra_fields_validation | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_client_to_server_types.py | test_message_serialization_deserialization | 23 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_client_to_server_types.py | test_thread_operation_edge_cases | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_client_to_server_types.py | test_batch_client_message_validation | 17 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_client_to_server_types.py | test_invalid_message_types | 17 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_client_to_server_types.py | test_message_type_string_conversion | 18 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unified_system\test_service_recovery.py | service_config | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unified_system\test_jwt_flow.py | test_jwt_creation_and_signing | 31 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unified_system\test_jwt_flow.py | test_jwt_with_service_claims | 19 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_websocket_ghost_connections.py | failed_connection | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_websocket_ghost_connections.py | stale_closing_connection | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_websocket_ghost_connections.py | test_connection_state_transitions | 21 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_websocket_ghost_connections.py | test_ghost_connection_detection | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_websocket_ghost_connections.py | test_connection_can_be_cleaned_up_logic | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_quality_gate_thresholds_basic.py | test_threshold_all_specific_checks | 21 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_quality_gate_thresholds_basic.py | test_threshold_hallucination_critical_failure | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_quality_gate_thresholds_basic.py | test_suggestions_all_issues | 25 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_quality_gate_thresholds_basic.py | test_suggestions_optimization_specific | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_quality_gate_thresholds_basic.py | test_suggestions_action_plan_specific | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_quality_gate_thresholds_basic.py | test_prompt_adjustments_all_issues | 21 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\security\test_secret_manager.py | test_secret_encryption | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\security\test_secret_manager.py | test_access_control | 23 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\security\test_secret_manager.py | test_secret_rotation | 20 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\security\test_secret_manager.py | test_secret_access_levels | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\security\test_secret_manager.py | test_secret_audit_logging | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\security\test_secret_manager.py | test_secret_expiration | 23 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_threads_routes.py | test_thread_creation | 19 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_threads_routes.py | test_thread_pagination | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\startup\test_health_monitor_core.py | mock_service_config | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\startup\test_health_monitor_core.py | test_health_check_result_creation | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\startup\test_health_monitor_core.py | test_health_check_result_with_error | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\startup\test_health_monitor_core.py | test_stage_config_creation | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\startup\test_health_monitor_core.py | test_service_state_creation | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\startup\test_health_monitor_core.py | test_init_stage_configs | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\test_example_message_performance.py | test_memory_usage_under_load | 38 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\test_example_message_performance.py | test_session_creation_performance | 33 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\test_example_message_performance.py | test_message_sequencer_high_volume | 38 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\test_example_message_performance.py | test_connection_manager_capacity | 38 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\test_example_message_performance.py | test_memory_leak_detection | 38 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\test_example_message_performance.py | test_error_recovery_under_stress | 47 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\test_example_message_performance.py | performance_baseline | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\test_example_message_performance.py | test_session_creation_regression | 29 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\test_example_message_performance.py | test_memory_usage_regression | 33 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\test_example_message_performance.py | test_cleanup_performance_regression | 31 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\ws_manager\test_base.py | fresh_manager | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\e2e\test_cors_e2e.py | dynamic_ports | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\e2e\test_cors_e2e.py | regression_scenarios | 32 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_quality_gate_thresholds_suggestions.py | test_threshold_all_specific_checks | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_quality_gate_thresholds_suggestions.py | test_threshold_hallucination_critical_failure | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_quality_gate_thresholds_suggestions.py | test_suggestions_all_issues | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_quality_gate_thresholds_suggestions.py | test_suggestions_optimization_specific | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_quality_gate_thresholds_suggestions.py | test_suggestions_action_plan_specific | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_quality_gate_thresholds_suggestions.py | test_prompt_adjustments_all_issues | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\integration\test_agent_reliability_integration.py | reliable_agent | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_investor_critical_roi_calculator.py | test_instant_roi_calculation_accuracy | 20 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_investor_critical_roi_calculator.py | test_real_time_calculation_performance | 18 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_investor_critical_roi_calculator.py | test_multiple_model_cost_comparisons | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_investor_critical_roi_calculator.py | test_annual_savings_projections | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_investor_critical_roi_calculator.py | test_tier_specific_percentage_savings | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_investor_critical_roi_calculator.py | test_zero_usage_edge_case | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_investor_critical_roi_calculator.py | test_massive_usage_spike_handling | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_investor_critical_roi_calculator.py | test_negative_value_protection | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_security_service_permissions.py | permission_test_users | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_security_service_permissions.py | test_tool_permission_granularity | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_security_service_permissions.py | test_permission_validation_edge_cases | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_fallback_response_factory.py | test_enhance_response_handles_mixed_types | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\e2e\conftest.py | performance_monitor | 29 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\e2e\conftest.py | e2e_logger | 26 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\unified\test_microservice_isolation_validation.py | test_comprehensive_isolation_report | 28 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_batch_message_transactional.py | test_mark_batch_sending_transitions_state | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_batch_message_transactional.py | test_mark_batch_sent_transitions_correctly | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_batch_message_transactional.py | test_mark_batch_failed_increments_retry_count | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_batch_message_transactional.py | test_revert_batch_to_pending_from_sending | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_batch_message_transactional.py | test_should_retry_within_limit | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_batch_message_transactional.py | test_should_not_retry_exceeded_limit | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_batch_message_transactional.py | test_exponential_backoff_calculation | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_batch_message_transactional.py | test_filter_retryable_messages | 26 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_batch_message_transactional.py | test_remove_sent_messages_keeps_others | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_batch_message_transactional.py | test_queue_metrics_include_state_information | 19 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\unified\test_resource_limits.py | test_token_usage_tracking | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_fallback_response_service.py | sample_quality_metrics | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_fallback_response_service.py | test_fallback_service_initialization | 18 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\integration\test_sub_agent_registry_discovery.py | capability_registry | 23 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\unified\test_critical_imports_validation.py | test_all_dependencies_available | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\unified\test_critical_imports_validation.py | test_all_critical_modules_importable | 21 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\unified\test_critical_imports_validation.py | test_no_circular_dependencies | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\unified\test_critical_imports_validation.py | test_performance_requirement | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\unified\test_critical_imports_validation.py | test_100_percent_success_rate_required | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\unified\test_critical_imports_validation.py | test_critical_services_coverage | 24 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\unified\test_critical_imports_validation.py | test_validation_summary_report | 25 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\clickhouse\clickhouse_test_fixtures.py | setup_workload_table | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\clickhouse\clickhouse_test_fixtures.py | batch_workload_events | 19 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_admin_routes.py | test_admin_role_verification | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_admin_routes.py | test_admin_endpoint_authorization_flow | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_admin_routes.py | test_admin_user_role_update | 23 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_admin_routes.py | test_admin_bulk_operations | 25 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_admin_routes.py | test_admin_system_settings | 30 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_admin_routes.py | test_admin_security_validation | 29 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_supply_routes.py | test_supply_research | 21 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_supply_routes.py | test_supply_data_enrichment | 19 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\unified\test_dev_launcher_real_startup.py | launcher_config | 17 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_auth_integration.py | sample_user | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_auth_integration.py | test_password_hashing_and_verification_success | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_auth_integration.py | test_password_verification_wrong_password_fails | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_auth_integration.py | test_validate_token_jwt_valid_token_success | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_auth_integration.py | test_validate_token_jwt_expired_token_returns_none | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\test_agent_response_serialization.py | test_agent_completed_response_structure | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\test_agent_response_serialization.py | test_agent_completed_complex_result | 17 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\test_agent_response_serialization.py | test_agent_update_response_structure | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\test_agent_response_serialization.py | test_tool_started_response_structure | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\test_agent_response_serialization.py | test_tool_started_complex_args | 18 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\test_agent_response_serialization.py | test_tool_completed_response_structure | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\test_agent_response_serialization.py | test_tool_completed_error_status | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\test_agent_response_serialization.py | test_agent_error_message_structure | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\test_agent_response_serialization.py | test_agent_error_with_details | 17 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\test_agent_response_serialization.py | test_nested_agent_result_serialization | 28 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\test_agent_response_serialization.py | test_tool_response_with_large_output | 27 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_synthetic_data_management.py | test_synthetic_data_export | 42 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_synthetic_data_management.py | test_synthetic_data_quality_analysis | 64 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_synthetic_data_management.py | test_synthetic_data_cleanup | 37 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_synthetic_data_management.py | test_data_format_conversion | 54 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_synthetic_data_management.py | test_data_comparison_analysis | 67 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_synthetic_data_management.py | test_data_versioning_and_lineage | 55 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_synthetic_data_management.py | test_automated_data_refresh | 48 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_mcp_routes.py | test_mcp_message_handling | 23 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_mcp_routes.py | test_mcp_protocol_validation | 20 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_mcp_routes.py | test_mcp_tool_discovery | 38 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_mcp_routes.py | test_mcp_error_handling | 29 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_mcp_routes.py | test_mcp_capabilities_negotiation | 43 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_pr_router_utils.py | test_handle_pr_routing_error_basic | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_pr_router_utils.py | test_handle_pr_routing_error_auth_error | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_pr_router_utils.py | test_get_pr_environment_status_basic | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_pr_router_utils.py | test_route_pr_authentication_login_with_return_url | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_user_service.py | sample_user | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\startup\test_health_monitor_checks.py | mock_service_config | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\e2e\test_websocket_thread_integration.py | mock_websocket_manager | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\e2e\test_websocket_thread_integration.py | mock_thread_service | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\integration\staging\test_staging_secrets_manager_integration.py | staging_secrets | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\integration\staging\test_staging_secrets_manager_integration.py | test_google_secret_manager_client_initialization | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\integration\staging\test_staging_secrets_manager_integration.py | test_secret_retrieval_from_google_secret_manager | 19 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\integration\staging\test_staging_secrets_manager_integration.py | test_fallback_mechanism_local_to_gsm | 27 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\integration\staging\test_staging_secrets_manager_integration.py | test_secret_rotation_without_disruption | 27 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\integration\staging\test_staging_secrets_manager_integration.py | test_secret_caching_mechanism | 22 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\integration\staging\test_staging_secrets_manager_integration.py | test_error_handling_for_unavailable_secrets | 17 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\integration\staging\test_staging_secrets_manager_integration.py | test_secret_validation_against_staging_requirements | 22 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\integration\staging\test_staging_secrets_manager_integration.py | test_local_environment_file_precedence | 30 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\integration\staging\test_staging_secrets_manager_integration.py | test_secret_interpolation_in_staging | 28 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_system_health_monitor.py | test_monitor_initialization | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_system_health_monitor.py | test_convert_legacy_result_dict | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_system_health_monitor.py | test_convert_legacy_result_boolean | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_system_health_monitor.py | test_get_system_overview | 22 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_tool_permission_user_plans.py | test_get_user_permissions_wildcard | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\clickhouse\test_corpus_validation.py | test_prompt_response_length_validation | 17 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\clickhouse\test_corpus_validation.py | test_required_fields_validation | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\database\test_schema_consistency.py | test_user_trial_period_is_integer | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\database\test_schema_consistency.py | test_user_model_types_match_expectations | 28 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\database\test_schema_consistency.py | test_tool_usage_log_types | 26 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\clickhouse\clustering_analysis_tests.py | test_log_clustering_with_similarity | 39 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\clickhouse\clustering_analysis_tests.py | test_error_cascade_detection | 37 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\security\test_input_validation.py | test_sql_injection_detection | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\security\test_input_validation.py | test_xss_detection | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\security\test_input_validation.py | test_path_traversal_detection | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\security\test_input_validation.py | test_command_injection_detection | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\security\test_input_validation.py | test_context_validation | 25 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\security\test_input_validation.py | test_validation_levels | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\security\test_input_validation.py | test_bulk_validation | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\security\test_input_validation.py | test_custom_validation_rules | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\security\test_input_validation.py | test_validation_caching | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\e2e\test_agent_message_flow_implementation.py | test_statistics_tracking | 18 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\e2e\test_kv_cache_audit.py | kv_cache_audit_setup | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_secret_manager_access.py | secret_manager | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_secret_manager_access.py | prod_secret_manager | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_secret_manager_access.py | test_get_secret_success | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_secret_manager_access.py | test_get_secret_expired | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_secret_manager_access.py | test_get_secret_component_blocked | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_secret_manager_access.py | test_get_secret_access_attempts_exceeded | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_secret_manager_access.py | test_access_log_entries_structure | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_secret_manager_access.py | test_multiple_failed_attempts_blocking | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_secret_manager_access.py | test_access_control_validation_order | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_secret_manager_access.py | test_access_log_size_maintenance | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_secret_manager_access.py | test_environment_specific_access_patterns | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_supply_research_service_validation.py | test_validate_supply_data_missing_required_fields | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_supply_research_service_validation.py | test_validate_all_valid_availability_statuses | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_supply_research_service_validation.py | test_validate_context_window_edge_cases | 19 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_supply_research_service_validation.py | test_validate_confidence_score_edge_cases | 20 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_supply_research_service_validation.py | test_pricing_format_validation | 19 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_supply_research_service_validation.py | test_provider_name_validation | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\clickhouse\test_corpus_generation_coverage.py | test_prompt_response_length_validation | 17 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\clickhouse\test_corpus_generation_coverage.py | test_required_fields_validation | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| auth_service\tests\test_setup.py | test_config_in_test_mode | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\clickhouse\test_multi_source_aggregation.py | test_cross_table_correlation | 55 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\clickhouse\test_multi_source_aggregation.py | test_system_health_dashboard_query | 19 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\clickhouse\test_multi_source_aggregation.py | test_resource_utilization_across_sources | 61 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\clickhouse\test_multi_source_aggregation.py | test_business_metrics_aggregation | 62 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\clickhouse\test_multi_source_aggregation.py | test_performance_impact_correlation | 62 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_type_validation_part1.py | test_type_mismatch_creation | 17 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_type_validation_part1.py | test_type_mismatch_without_suggestion | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_type_validation_part1.py | test_parse_typescript_file_with_interface | 36 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_type_validation_part1.py | test_parse_typescript_file_with_type_alias | 23 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_type_validation_part1.py | test_parse_typescript_file_with_nested_objects | 28 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_type_validation_part1.py | test_parse_interface_fields_with_comments | 20 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_type_validation_part1.py | test_parse_typescript_file_error | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_type_validation_part1.py | test_check_field_compatibility_mapped_types | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_type_validation_part1.py | test_check_field_compatibility_mismatch | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_comprehensive.py | test_environment_origins_configuration | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_apex_optimizer_tool_selection_part3.py | optimization_tools | 25 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_apex_optimizer_tool_selection_part3.py | tool_chain | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_unit_of_work_transactions.py | mock_async_session_factory | 19 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_fallback_coordinator_core.py | coordinator | 28 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_fallback_coordinator_core.py | test_initialization | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_fallback_coordinator_core.py | test_register_agent_new | 37 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_fallback_coordinator_core.py | test_register_agent_already_exists | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_fallback_coordinator_core.py | test_register_agent_with_custom_config | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_fallback_coordinator_core.py | test_get_default_fallback_config | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_fallback_coordinator_core.py | test_get_registered_agents | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_fallback_coordinator_core.py | test_multiple_agent_registration | 22 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_fallback_coordinator_core.py | test_coordinator_settings_modification | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_triage_init_validation.py | test_initialization_configuration_values | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_triage_init_validation.py | test_initialization_with_custom_config | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_tool_registry_performance.py | test_tool_discovery_performance | 24 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_tool_registry_performance.py | test_concurrent_tool_access | 34 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_tool_registry_performance.py | test_memory_usage_with_large_registry | 23 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_tool_registry_performance.py | test_tool_search_performance | 26 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_tool_registry_performance.py | test_bulk_operations_performance | 21 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_tool_registry_performance.py | test_cache_performance | 23 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_tool_registry_performance.py | test_stress_test_tool_operations | 25 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\mcp\test_mcp_service.py | test_client_creation | 18 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\mcp\test_mcp_service.py | test_client_defaults | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\mcp\test_mcp_service.py | test_execution_creation | 20 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\mcp\test_mcp_service.py | mock_services | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\mcp\test_mcp_service.py | test_service_initialization | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\mcp\test_mcp_service.py | test_tool_registration | 18 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_synthetic_data_service_integration.py | full_stack | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_websocket_broadcast_mechanisms.py | test_user_subscription | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_websocket_broadcast_mechanisms.py | test_user_unsubscription | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_websocket_broadcast_mechanisms.py | test_broadcast_filtering | 32 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\test_agent_service_critical.py | mock_request_model | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_fixtures.py | mock_tool_dispatcher | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_fixtures.py | supervisor_agent | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_user_service_auth.py | enterprise_user | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_user_service_auth.py | free_user | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_user_service_auth.py | test_argon2_password_hashing_security | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_user_service_auth.py | test_password_verification_timing_attack_resistance | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_user_service_auth.py | test_password_hash_verification_edge_cases | 19 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_user_service_auth.py | test_jwt_token_creation_security | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_user_service_auth.py | test_jwt_token_expiration_security | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_user_service_auth.py | test_jwt_token_tampering_detection | 18 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_user_service_auth.py | test_permission_validation_security | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_user_service_auth.py | test_security_error_handling | 18 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\llm\test_structured_generation.py | test_config | 33 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\llm\test_structured_generation.py | test_get_structured_llm_with_mock | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\llm\test_structured_generation.py | test_get_structured_llm_with_real | 17 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\clickhouse\test_llm_metrics_aggregation.py | test_llm_cost_optimization_query | 47 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\clickhouse\test_llm_metrics_aggregation.py | test_llm_performance_benchmarking | 36 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\clickhouse\test_llm_metrics_aggregation.py | test_llm_token_efficiency_analysis | 24 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\clickhouse\test_llm_metrics_aggregation.py | test_llm_user_behavior_analysis | 33 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\clickhouse\test_llm_metrics_aggregation.py | test_llm_quality_metrics | 22 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_thread_messaging.py | test_thread_pagination | 31 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_thread_messaging.py | test_thread_message_addition | 36 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_thread_messaging.py | test_thread_search | 57 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_thread_messaging.py | test_message_retrieval_with_pagination | 45 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_thread_messaging.py | test_message_editing | 39 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_thread_messaging.py | test_message_search_within_thread | 53 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_thread_messaging.py | test_message_reactions_and_feedback | 29 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_thread_messaging.py | test_message_threading_and_replies | 35 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\config\test_config_environment.py | clean_environment | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\config\test_config_environment.py | test_get_environment_testing | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\config\test_config_environment.py | test_get_environment_cloud_run_detected | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\config\test_config_environment.py | test_get_environment_defaults_to_development | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\config\test_config_environment.py | test_get_environment_explicit_environment_var | 22 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\config\test_config_environment.py | test_testing_environment_takes_precedence | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\config\test_config_environment.py | test_create_config_development | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\config\test_config_environment.py | test_create_config_production | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\config\test_config_environment.py | test_create_config_staging | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\config\test_config_environment.py | test_create_config_testing | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\config\test_config_environment.py | test_create_config_unknown_environment_defaults | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\config\test_config_environment.py | test_validate_environment_valid_environments | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\config\test_config_environment.py | test_environment_config_mapping_completeness | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\config\test_config_environment.py | test_cloud_run_detection_with_k_service | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\config\test_config_environment.py | test_app_engine_detection | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\config\test_config_environment.py | test_google_cloud_project_detection | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\config\test_config_environment.py | test_environment_detection_logging | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\config\test_config_environment.py | test_config_creation_logging | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\config\test_config_environment.py | test_multiple_environment_detections_consistent | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\config\test_config_environment.py | test_config_creation_performance | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\config\test_config_environment.py | test_environment_variable_unicode_handling | 21 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\e2e\test_agent_orchestration_e2e.py | orchestration_setup | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_clickhouse_service.py | real_clickhouse_client | 36 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_clickhouse_service.py | ensure_workload_table | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_synthetic_data_routes.py | test_synthetic_data_generation | 36 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_synthetic_data_routes.py | test_synthetic_data_validation | 24 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\e2e\websocket_resilience\test_2_midstream_disconnection_recovery.py | response_configs | 39 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\e2e\test_system_startup.py | launcher_config | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\security\test_security_configuration.py | test_environment_specific_config | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\security\test_security_configuration.py | test_secret_environment_isolation | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_supervisor_consolidated_execution.py | test_create_run_context | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_triage_agent_caching.py | test_hash_generation | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\integration\test_fixtures_common.py | mock_infrastructure | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\integration\test_cross_service_integration.py | app | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\integration\test_cross_service_integration.py | service_discovery | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\integration\test_cross_service_integration.py | test_cors_middleware_initialization | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\integration\test_cross_service_integration.py | test_service_discovery_origins | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\integration\test_cross_service_integration.py | test_cross_service_auth_token_generation | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\integration\test_cross_service_integration.py | test_service_cors_config | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\integration\test_cross_service_integration.py | test_cross_service_health_status | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\integration\test_cross_service_integration.py | test_cross_service_connectivity_verification | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\integration\test_cross_service_integration.py | test_health_status_cross_service_updates | 17 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\integration\test_cross_service_integration.py | launcher_config | 21 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\integration\test_cross_service_integration.py | test_cors_environment_variable_setup | 24 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\integration\test_cross_service_integration.py | test_cross_service_auth_token_setup | 30 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\clickhouse\test_realistic_data_volumes.py | test_partition_pruning_query | 19 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\clickhouse\test_realistic_data_volumes.py | test_high_cardinality_aggregation | 29 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\clickhouse\test_realistic_data_volumes.py | test_time_series_downsampling | 49 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\clickhouse\test_realistic_data_volumes.py | test_complex_join_performance | 61 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\clickhouse\test_realistic_data_volumes.py | test_streaming_aggregation_simulation | 58 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\mcp\test_request_handler.py | test_validate_request_valid | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\mcp\test_request_handler.py | test_error_response_methods | 27 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\e2e\test_agent_pipeline.py | sample_user_message | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_threads_route_models.py | test_thread_create_model | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_threads_route_models.py | test_thread_update_model | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_threads_route_models.py | test_thread_response_model | 17 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_supply_catalog_service.py | test_get_all_options | 22 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_supply_catalog_service.py | test_get_option_by_id | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_supply_catalog_service.py | test_get_option_by_name | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_supply_catalog_service.py | test_create_option | 22 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_supply_catalog_service.py | test_update_option | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_supply_catalog_service.py | test_delete_option | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_supply_catalog_service.py | test_delete_option_not_found | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_supply_catalog_service.py | test_autofill_catalog_empty | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_supply_catalog_service.py | test_autofill_catalog_existing_data | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_compensation_engine.py | test_get_compensation_status_existing | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_compensation_engine.py | test_cleanup_compensations_with_completed | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_compensation_engine.py | test_register_handler_priority_sorting | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_compensation_engine.py | test_update_action_state_transitions | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_health_route.py | test_basic_import | 24 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_health_route.py | test_health_endpoint_direct | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_health_route.py | test_live_endpoint | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_error_handler_regression.py | test_error_handler_sqlalchemy_logging | 29 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_error_handler_regression.py | test_error_handler_integrity_error | 19 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_error_handler_regression.py | test_error_handler_data_error | 19 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_error_handler_regression.py | test_error_handler_general_sqlalchemy | 25 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_error_handler_regression.py | test_error_handler_complex_parameter_error | 25 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_triage_agent_core.py | test_initialization_with_redis | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_triage_agent_core.py | test_extract_numerical_thresholds | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_agent_forward_references.py | test_model_handles_circular_dependencies | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\services\test_gcp_error_service.py | mock_gcp_config | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\services\test_gcp_error_service.py | sample_gcp_error_stats | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\integration\test_auth_client_cross_service.py | service_discovery | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\integration\test_auth_client_cross_service.py | test_cross_service_auth_token_storage_retrieval | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\integration\test_auth_client_cross_service.py | test_auth_service_cors_metadata_registration | 17 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\integration\test_auth_client_cross_service.py | test_oauth_config_generation_for_cross_service | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\integration\test_auth_client_cross_service.py | test_websocket_validation_with_cross_service_context | 23 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\integration\test_auth_client_cross_service.py | test_websocket_security_prevents_malicious_cross_service_messages | 18 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_llm_agent_integration.py | mock_llm_manager | 51 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_llm_agent_integration.py | mock_websocket_manager | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_llm_agent_integration.py | mock_tool_dispatcher | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_llm_agent_integration.py | supervisor_agent | 24 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\performance\test_benchmark_metrics.py | test_cpu_utilization_monitoring | 24 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\e2e\test_artifact_validation.py | sample_triage_result | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\e2e\test_artifact_validation.py | sample_data_result | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\e2e\test_artifact_validation.py | sample_optimization_result | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\test_websocket_response_serialization.py | test_websocket_message_serialization | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\test_websocket_response_serialization.py | test_websocket_agent_update_message | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\test_websocket_response_serialization.py | test_websocket_tool_completed_message | 17 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\test_websocket_response_serialization.py | test_websocket_error_message | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\test_websocket_response_serialization.py | test_websocket_ping_pong_messages | 17 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\test_websocket_response_serialization.py | test_stream_chunk_structure | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\test_websocket_response_serialization.py | test_streaming_sequence | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\test_websocket_response_serialization.py | test_stream_complete_structure | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\test_websocket_response_serialization.py | test_stream_chunk_with_rich_metadata | 19 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\test_websocket_response_serialization.py | test_stream_error_handling | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\test_websocket_response_serialization.py | test_agent_lifecycle_websocket_flow | 46 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\test_websocket_response_serialization.py | test_streaming_with_websocket_wrapper | 20 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\test_websocket_response_serialization.py | test_concurrent_agent_messages | 18 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_thread_analytics.py | test_thread_statistics | 67 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_thread_analytics.py | test_thread_cleanup_old_threads | 61 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_thread_analytics.py | test_thread_analytics_dashboard | 82 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_thread_analytics.py | test_thread_bulk_operations | 61 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_thread_analytics.py | test_thread_sentiment_analysis | 81 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_thread_analytics.py | test_thread_performance_metrics | 84 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\e2e\test_cost_optimization_workflows.py | cost_optimization_setup | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\test_mcp_integration.py | mock_services | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_supply_researcher_agent_core.py | test_generate_pricing_query | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_supply_researcher_agent_core.py | test_generate_market_overview_query | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_supply_researcher_agent_core.py | test_extract_supply_data | 18 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_supply_researcher_agent_core.py | test_calculate_confidence_score | 19 | 8 | Split into multiple focused test functions or extract helper methods |
| auth_service\tests\unified\test_jwt_validation.py | valid_user_payload | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| auth_service\tests\unified\test_jwt_validation.py | test_jwt_signature_validation | 21 | 8 | Split into multiple focused test functions or extract helper methods |
| auth_service\tests\unified\test_jwt_validation.py | test_algorithm_mismatch_rejected | 22 | 8 | Split into multiple focused test functions or extract helper methods |
| auth_service\tests\unified\test_jwt_validation.py | test_expired_token_rejected | 18 | 8 | Split into multiple focused test functions or extract helper methods |
| auth_service\tests\unified\test_jwt_validation.py | test_jwt_claims_validation | 26 | 8 | Split into multiple focused test functions or extract helper methods |
| auth_service\tests\unified\test_jwt_validation.py | test_missing_required_claims_rejected | 23 | 8 | Split into multiple focused test functions or extract helper methods |
| auth_service\tests\unified\test_jwt_validation.py | test_token_type_validation | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| auth_service\tests\unified\test_jwt_validation.py | test_service_token_claims | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| auth_service\tests\unified\test_jwt_validation.py | test_jwt_revocation | 20 | 8 | Split into multiple focused test functions or extract helper methods |
| auth_service\tests\unified\test_jwt_validation.py | test_revocation_by_user_id | 25 | 8 | Split into multiple focused test functions or extract helper methods |
| auth_service\tests\unified\test_jwt_validation.py | test_cleanup_expired_revocations | 28 | 8 | Split into multiple focused test functions or extract helper methods |
| auth_service\tests\unified\test_jwt_validation.py | test_user_id_extraction | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_tool_registry_discovery.py | sample_tools | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_tool_registry_discovery.py | test_discover_tools_by_category | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_tool_registry_discovery.py | test_discover_tools_by_name_pattern | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_tool_registry_discovery.py | test_discover_tools_by_tags | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_tool_registry_discovery.py | test_discover_tools_by_capability | 20 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_tool_registry_discovery.py | test_discover_compatible_tools | 23 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_tool_registry_discovery.py | test_discover_tools_fuzzy_search | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_tool_registry_discovery.py | test_discover_recently_used_tools | 19 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_tool_registry_discovery.py | test_tool_recommendation_engine | 20 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_mcp_integration.py | mock_mcp_service | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_mcp_integration.py | sample_agent_context | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_clickhouse_regex_patterns.py | test_edge_case_regex_patterns | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_clickhouse_regex_patterns.py | test_nested_array_access_patterns | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_clickhouse_regex_patterns.py | test_caching_functionality | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_clickhouse_regex_patterns.py | test_boundary_condition_patterns | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_tool_permission_main.py | sample_context | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_tool_permission_main.py | admin_context | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_tool_permission_main.py | test_get_upgrade_path_pro_required | 18 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_tool_permission_main.py | test_get_upgrade_path_enterprise_required | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_tool_permission_main.py | test_get_upgrade_path_role_required | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_tool_permission_main.py | test_get_upgrade_path_no_upgrade_needed | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_usage_tracker_unit.py | free_tier_user | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_usage_tracker_unit.py | pro_tier_user | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_usage_tracker_unit.py | enterprise_user | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_usage_tracker_unit.py | heavy_usage_free_user | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_usage_tracker_unit.py | test_plan_limits_hierarchy_consistent | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\clickhouse\test_time_series_analysis.py | test_moving_average_calculation | 30 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\clickhouse\test_time_series_analysis.py | test_anomaly_detection_with_zscore | 43 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\clickhouse\test_time_series_analysis.py | test_seasonal_pattern_detection | 47 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\clickhouse\test_time_series_analysis.py | test_trend_analysis_with_regression | 40 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\clickhouse\test_time_series_analysis.py | test_forecast_calculation | 48 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\clickhouse\test_time_series_analysis.py | test_change_point_detection | 36 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_thread_crud.py | test_thread_creation | 36 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_thread_crud.py | test_thread_retrieval | 34 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_thread_crud.py | test_thread_update | 31 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_thread_crud.py | test_thread_deletion | 19 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_thread_crud.py | test_thread_status_management | 29 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_thread_crud.py | test_thread_metadata_management | 35 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_thread_crud.py | test_thread_duplication | 32 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\config\test_config_loader.py | clean_environment | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\config\test_config_loader.py | test_detect_cloud_run_environment_with_k_service | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\config\test_config_loader.py | test_detect_cloud_run_environment_staging_pattern | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\config\test_config_loader.py | test_detect_app_engine_environment_standard | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\config\test_config_loader.py | test_detect_app_engine_environment_flex | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\config\test_config_loader.py | test_detect_kubernetes_environment | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\config\test_config_loader.py | test_detect_multiple_cloud_environments_precedence | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\config\test_config_loader.py | clean_environment | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\config\test_config_loader.py | test_load_config_from_environment_success | 28 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\config\test_config_loader.py | test_load_config_from_environment_missing_variables | 20 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\config\test_config_loader.py | test_load_config_from_environment_type_conversion | 32 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\config\test_config_loader.py | test_load_config_with_default_values | 24 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\config\test_config_loader.py | test_load_config_environment_override_defaults | 29 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\config\test_config_loader.py | test_validate_required_config_success | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\config\test_config_loader.py | test_validate_required_config_missing_keys | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\config\test_config_loader.py | test_validate_required_config_empty_values | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\config\test_config_loader.py | test_validate_config_with_custom_validators | 24 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\config\test_config_loader.py | test_validate_config_custom_validator_failure | 26 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\config\test_config_loader.py | test_fallback_to_default_configuration | 25 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\config\test_config_loader.py | test_fallback_configuration_hierarchy | 34 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\config\test_config_loader.py | test_graceful_degradation_partial_config_failure | 21 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\config\test_config_loader.py | test_config_load_error_creation | 17 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\config\test_config_loader.py | test_config_loader_type_conversion_errors | 30 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\config\test_config_loader.py | test_config_loader_circular_reference_detection | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\config\test_config_loader.py | test_config_loading_performance_large_environment | 23 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\config\test_config_loader.py | test_config_validation_performance | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\config\test_config_loader.py | test_cloud_environment_detection_caching | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_supply_research_scheduler_jobs.py | scheduler | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_supply_research_scheduler_jobs.py | scheduler_with_redis | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_resilience_integration.py | test_error_logging_production_readiness | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_resilience_integration.py | test_cors_validation_performance | 31 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_resilience_integration.py | test_cors_handler_edge_case_origins | 21 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\integration\test_supervisor_agent_initialization_chain.py | llm_manager_mock | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\integration\test_supervisor_agent_initialization_chain.py | tool_dispatcher_mock | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_circuit_breaker_integration.py | test_health_summary | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_circuit_breaker_integration.py | test_recent_events | 19 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_json_extraction_direct.py | test_extract_json_with_trailing_comma | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_json_extraction_direct.py | test_triage_agent_extract_json | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_websocket_connection_lifecycle.py | test_connection_lifecycle_state_management | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_error_handler_core.py | test_get_error_statistics | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_error_handler_core.py | test_error_handler_memory_usage | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| test_framework\real_llm_config.py | pytest_configure_real_llm | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| test_framework\real_llm_config.py | pytest_unconfigure_real_llm | 20 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\security\test_security_headers.py | test_production_headers | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\security\test_security_headers.py | test_csp_nonce_generation | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\security\test_security_headers.py | test_development_vs_production_headers | 20 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_llm_heartbeat_logging.py | test_elapsed_time_calculation | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_llm_heartbeat_logging.py | test_heartbeat_message_format | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_llm_heartbeat_logging.py | test_heartbeat_configuration_integration | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_llm_heartbeat_logging.py | test_supervisor_heartbeat_message_format | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_tool_permission_business_rate.py | sample_context | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_tool_permission_business_rate.py | developer_context | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_tool_permission_business_rate.py | test_check_business_requirements_plan_tier_pass | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_tool_permission_business_rate.py | test_check_business_requirements_plan_tier_fail | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_tool_permission_business_rate.py | test_check_business_requirements_feature_flags_pass | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_tool_permission_business_rate.py | test_check_business_requirements_feature_flags_fail | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_tool_permission_business_rate.py | test_check_business_requirements_role_pass | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_tool_permission_business_rate.py | test_check_business_requirements_role_fail | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_tool_permission_business_rate.py | test_check_business_requirements_developer_status_pass | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_tool_permission_business_rate.py | test_check_business_requirements_all_conditions | 21 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\e2e\test_auth_race_conditions.py | mock_auth_service | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\examples\test_real_functionality_examples.py | test_example_of_circular_testing_antipattern | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\examples\test_real_functionality_examples.py | test_example_of_excessive_mocking_antipattern | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\examples\test_real_functionality_examples.py | test_example_of_integration_without_integration | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\unified\e2e\test_supervisor_real_llm_integration.py | optimization_request_state | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\unified\e2e\test_supervisor_real_llm_integration.py | test_workflow_definition_compliance | 17 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\unified\e2e\test_supervisor_real_llm_integration.py | test_agent_registry_initialization | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_agent_recovery_strategies.py | test_recovery_context_creation_valid | 20 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_agent_recovery_strategies.py | test_recovery_context_validation_errors | 18 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_agent_recovery_strategies.py | test_recovery_context_metadata_handling | 22 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_agent_recovery_strategies.py | recovery_context | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_agent_recovery_strategies.py | database_error_context | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_agent_recovery_strategies.py | test_strategy_selection_by_agent_type | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_agent_recovery_strategies.py | test_strategy_selection_enterprise_customer_priority | 18 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_supply_research.py | test_supply_research | 49 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_supply_research.py | test_supply_data_enrichment | 53 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_supply_research.py | test_supply_market_analysis | 52 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_supply_research.py | test_supplier_comparison | 71 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_error_handler_enums.py | test_error_category_values | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_error_handler_enums.py | test_error_context_creation | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_error_handler_enums.py | test_error_context_serialization | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_error_handler_enums.py | test_error_context_validation | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_error_handler_enums.py | test_error_context_metadata_operations | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_error_handler_enums.py | test_error_context_immutability | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_error_handler_enums.py | test_error_context_edge_cases | 18 | 8 | Split into multiple focused test functions or extract helper methods |
| auth_service\tests\test_session_management.py | test_create_session_success | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| auth_service\tests\test_session_management.py | test_session_ttl_refresh | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| auth_service\tests\test_session_management.py | test_session_database_model_structure | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| auth_service\tests\test_session_management.py | test_session_database_cleanup_logic | 22 | 8 | Split into multiple focused test functions or extract helper methods |
| auth_service\tests\test_session_management.py | test_session_ip_tracking | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| auth_service\tests\test_session_management.py | test_session_uuid_generation | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_user_plan_schema.py | test_trial_period_accepts_integer_days | 18 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_user_plan_schema.py | test_trial_period_accepts_zero | 18 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_user_plan_schema.py | test_trial_period_defaults_to_zero | 18 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_user_plan_schema.py | test_trial_period_accepts_integer | 20 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_user_plan_schema.py | test_full_plan_creation_with_trial | 31 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_demo_service.py | mock_redis_client | 33 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_demo_service.py | demo_service | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_async_resource_manager.py | test_global_instances_are_singletons | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_async_resource_manager.py | test_resource_manager_weak_references | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\clickhouse\metrics_aggregation_tests.py | test_metrics_extraction_with_arrays | 38 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_tool_permission_integration.py | test_business_requirements_edge_cases | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_error_handler_global.py | test_global_error_handler_shared_state | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_error_handler_global.py | test_global_error_handler_thread_safety | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_token_manager_generation.py | sample_token_claims | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_config_endpoint.py | test_get_public_config | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_config_endpoint.py | test_get_frontend_config | 29 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_config_endpoint.py | test_update_config_authorized | 35 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_config_endpoint.py | test_update_config_unauthorized | 32 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_supply_researcher_scheduler.py | test_scheduler_initialization | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_supply_researcher_scheduler.py | test_schedule_next_run_calculation | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_supply_researcher_scheduler.py | test_schedule_should_run | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_supply_researcher_scheduler.py | test_scheduler_add_remove_schedules | 20 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_supply_researcher_scheduler.py | test_scheduler_enable_disable | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_supply_researcher_scheduler.py | test_scheduler_get_status | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\test_json_extraction.py | test_extract_json_from_markdown | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\test_json_extraction.py | test_extract_json_with_text_before_after | 17 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\test_json_extraction.py | test_extract_json_with_trailing_comma | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\test_json_extraction.py | test_extract_nested_json | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\test_json_extraction.py | test_extract_json_with_comments | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\test_json_extraction.py | test_fix_common_json_errors | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\test_json_extraction.py | test_extract_partial_basic | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\test_json_extraction.py | test_extract_partial_with_required_fields | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\test_json_extraction.py | test_extract_partial_numeric_values | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\test_json_extraction.py | test_extract_partial_boolean_values | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\test_json_extraction.py | test_extract_partial_from_truncated_response | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\test_json_extraction.py | test_handle_truncated_large_response | 17 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_app_factory.py | mock_app | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_app_factory.py | test_setup_security_middleware_calls_all_components | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_app_factory.py | test_setup_request_middleware_calls_all_components | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_app_factory.py | test_import_and_register_routes_process | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_app_factory.py | test_multiple_routes_registration | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_app_factory.py | test_configure_app_handlers_calls_all_setup | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\unified\e2e\test_auth_token_cache.py | test_tokens | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unified_system\test_dev_mode.py | mock_dev_mode_config | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unified_system\test_dev_mode.py | mock_dev_user | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_supply_research_service_basic.py | sample_supply_item | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_supply_research_service_basic.py | test_initialization_with_redis | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_supply_research_service_basic.py | test_initialization_without_redis | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_supply_research_service_basic.py | test_get_supply_items_no_filters | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_supply_research_service_basic.py | test_get_supply_items_with_provider_filter | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_supply_research_service_basic.py | test_get_supply_items_with_availability_filter | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_supply_research_service_basic.py | test_get_supply_items_with_confidence_filter | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_supply_research_service_basic.py | test_get_supply_item_by_id_exists | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_supply_research_service_basic.py | test_get_supply_item_by_id_not_exists | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_supply_research_service_basic.py | test_get_research_sessions_no_filters | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_supply_research_service_basic.py | test_get_research_sessions_with_status_filter | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_supply_research_service_basic.py | test_get_research_session_by_id | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_production_security.py | test_production_environment_detection | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_production_security.py | test_staging_environment_hybrid_config | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_production_security.py | test_custom_origins_from_environment | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_production_security.py | test_origin_deduplication | 17 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_production_security.py | test_ip_address_blocking | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_production_security.py | test_tunnel_service_blocking | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_production_security.py | test_browser_extension_blocking | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_production_security.py | test_unexpected_localhost_ports | 17 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_production_security.py | test_heroku_app_selective_blocking | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_production_security.py | test_pattern_compilation_performance | 28 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_production_security.py | test_violation_tracking | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_production_security.py | test_temporary_blocking_threshold | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_production_security.py | test_blocked_origin_always_denied | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_production_security.py | test_violation_count_reset_on_unblock | 19 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_production_security.py | test_security_statistics_accuracy | 20 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_production_security.py | test_production_security_headers | 17 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_production_security.py | test_development_no_security_headers | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_production_security.py | test_cors_headers_basic_structure | 21 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_production_security.py | test_security_config_structure | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_production_security.py | test_origin_length_enforcement | 17 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_production_security.py | test_https_requirement_in_production | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_production_security.py | test_security_config_can_be_disabled | 18 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_production_security.py | test_many_violations_performance | 19 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_production_security.py | test_blocked_origins_lookup_performance | 20 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\websocket\test_websocket_production_security.py | test_memory_usage_under_attack | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_route_fixtures.py | authenticated_test_client | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_route_fixtures.py | configured_test_client | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_route_fixtures.py | agent_test_client | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_metrics_collector_core.py | test_gather_system_metrics_success | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_metrics_collector_core.py | test_gather_system_metrics_with_none_values | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_metrics_collector_core.py | test_gather_database_metrics_success | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_metrics_collector_core.py | test_record_database_metrics | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_metrics_collector_core.py | test_record_websocket_metrics | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_metrics_collector_core.py | test_gather_memory_metrics | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_metrics_collector_core.py | test_periodic_gc_triggered | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_metrics_collector_core.py | test_cleanup_old_metrics | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_error_recovery_integration.py | test_prepare_error_data | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_error_recovery_integration.py | test_get_recovery_metrics | 20 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_service_registry.py | test_register_service | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_service_registry.py | test_get_all_services | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_service_registry.py | test_global_registry_operations | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_thread_service.py | sample_message | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_thread_service.py | sample_run | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\test_thread_repository.py | mock_db | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_token_manager_operations.py | sample_token_claims | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_token_manager_operations.py | test_decode_token_payload_success | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\startup\test_migration_tracker.py | mock_migration_state | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\startup\test_migration_tracker.py | test_get_alembic_config | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\startup\test_migration_tracker.py | test_should_auto_run_checks | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_metrics_collector_summary.py | test_get_recent_metrics_filtered | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_metrics_collector_summary.py | test_get_metric_summary_with_data | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_metrics_collector_summary.py | test_metric_buffer_size_limits | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_metrics_collector_summary.py | test_summary_statistics_accuracy | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_metrics_collector_summary.py | test_time_based_filtering_edge_cases | 18 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_metrics_collector_summary.py | test_metric_aggregation_performance | 18 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_metrics_collector_summary.py | test_concurrent_metric_access_safety | 19 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_metrics_collector_summary.py | test_metric_cleanup_efficiency | 23 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\clickhouse\test_clickhouse_array_operations.py | test_fix_incorrect_array_syntax | 22 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\clickhouse\test_clickhouse_array_operations.py | test_validate_query_catches_errors | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\clickhouse\test_clickhouse_array_operations.py | test_complex_array_operations_syntax | 18 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\clickhouse\test_clickhouse_array_operations.py | test_nested_array_expressions | 20 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\clickhouse\test_clickhouse_array_operations.py | test_array_operations_with_conditions | 19 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_pr_router_security.py | test_validate_return_url_valid | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_pr_router_security.py | test_validate_return_url_malicious | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_pr_router_security.py | test_validate_pr_number_invalid | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_pr_router_security.py | test_is_valid_url_edge_cases | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_pr_router_security.py | test_is_allowed_return_domain_subdomains | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_pr_router_security.py | test_is_allowed_return_domain_spoofing | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_crud_service.py | crud_service | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\unified\test_token_validation.py | valid_token_payload | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_tool_permission_basic.py | sample_context | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_tool_permission_basic.py | developer_context | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_tool_permission_basic.py | test_permission_definitions_loaded | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_tool_permission_basic.py | test_get_user_permissions_from_plan | 17 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_tool_permission_basic.py | test_has_permission_hierarchy | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_supply_management.py | test_supply_optimization_recommendations | 67 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_supply_management.py | test_supply_performance_tracking | 51 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_supply_management.py | test_supply_contract_management | 44 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_supply_management.py | test_supply_sustainability_assessment | 54 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_supply_research_service_error_handling.py | test_invalid_json_in_update_logs | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_supply_research_service_error_handling.py | test_transaction_rollback_on_error | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_supply_research_service_error_handling.py | test_redis_connection_failure_recovery | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_supply_research_service_error_handling.py | test_memory_pressure_large_datasets | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_supply_research_service_error_handling.py | test_empty_provider_list_comparison | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_supply_research_service_error_handling.py | test_price_changes_with_null_values | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_supply_research_service_error_handling.py | test_very_large_price_changes | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_supply_research_service_error_handling.py | test_zero_old_value_price_changes | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_supply_research_service_error_handling.py | test_concurrent_item_updates | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_supply_research_service_error_handling.py | test_unicode_handling_in_model_names | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_supply_research_service_error_handling.py | test_very_long_field_values | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_supply_research_service_error_handling.py | test_update_log_creation_consistency | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_supply_research_service_error_handling.py | test_timestamp_consistency | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_supply_research_service_error_handling.py | test_large_result_set_handling | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_supply_research_service_error_handling.py | test_custom_result_limits | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_staging_integration_flow.py | staging_environment | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\integration\test_rate_limiting_backpressure.py | test_token_bucket_basic_consumption | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\integration\test_rate_limiting_backpressure.py | test_token_bucket_refill_mechanics | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\integration\test_agent_response_pipeline_e2e.py | llm_manager_mock | 43 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\integration\test_agent_response_pipeline_e2e.py | websocket_mock | 29 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\integration\test_agent_response_pipeline_e2e.py | redis_manager_mock | 20 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\integration\test_agent_response_pipeline_e2e.py | websocket_manager_mock | 29 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_execution_context_hashable_regression.py | execution_context | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_execution_context_hashable_regression.py | test_execution_context_is_hashable | 27 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_execution_context_hashable_regression.py | test_error_handler_cache_fallback_no_hashable_context | 19 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_execution_context_hashable_regression.py | test_execution_monitor_doesnt_use_context_as_key | 25 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_execution_context_hashable_regression.py | test_dataclass_serialization_instead_of_direct_storage | 20 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_execution_context_hashable_regression.py | test_mcp_context_manager_storage | 30 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_execution_context_hashable_regression.py | test_execution_context_to_dict_pattern | 31 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_execution_context_hashable_regression.py | test_avoid_storing_dataclass_directly | 24 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_execution_context_hashable_regression.py | test_safe_caching_pattern | 37 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_execution_context_hashable_regression.py | test_fixed_cache_fallback_data_method | 27 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_tool_registry_management.py | sample_registries | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_tool_registry_management.py | test_tool_search_by_category | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_tool_registry_registration_core.py | sample_tools | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_tool_registry_registration_core.py | test_register_single_tool | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_tool_registry_registration_core.py | test_register_multiple_tools_same_category | 18 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_tool_registry_registration_core.py | test_register_tools_multiple_categories | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_tool_registry_registration_core.py | test_register_tool_with_metadata | 20 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_tool_registry_registration_core.py | test_register_duplicate_tool_handling | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_tool_registry_registration_core.py | test_register_tool_validation_failure | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_tool_registry_registration_core.py | test_register_tool_invalid_category | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_tool_registry_registration_core.py | test_bulk_tool_registration | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_tool_registry_registration_core.py | test_tool_registration_rollback_on_error | 19 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_agent_routes.py | test_agent_message_processing | 28 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_agent_routes.py | test_agent_error_handling | 23 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_agent_routes.py | test_agent_message_validation | 36 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_agent_routes.py | test_agent_rate_limiting | 32 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\routes\test_agent_routes.py | test_agent_performance_metrics | 33 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\examples\test_database_fixtures_examples.py | test_bulk_model_creation | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\clickhouse\test_log_clustering_algorithms.py | test_log_clustering_with_similarity | 39 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\clickhouse\test_log_clustering_algorithms.py | test_error_cascade_detection | 37 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\clickhouse\test_log_clustering_algorithms.py | test_log_frequency_analysis | 42 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\clickhouse\test_log_clustering_algorithms.py | test_log_similarity_clustering | 52 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\clickhouse\test_log_clustering_algorithms.py | test_temporal_pattern_mining | 44 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\clickhouse\test_log_clustering_algorithms.py | test_log_anomaly_clustering | 63 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_permission_service_core.py | test_role_permissions_inheritance | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_permission_service_core.py | test_detect_developer_with_dev_mode_env | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_permission_service_core.py | test_detect_developer_with_netra_email | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_permission_service_core.py | test_detect_developer_with_dev_environment | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_permission_service_core.py | test_detect_developer_with_none_email | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_permission_service_core.py | test_update_user_role_auto_elevate_to_developer | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_permission_service_core.py | test_update_user_role_no_elevation_for_admin | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_permission_service_core.py | test_update_user_role_no_elevation_for_super_admin | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_permission_service_core.py | test_update_user_role_skip_developer_check | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_permission_service_core.py | test_update_user_role_already_developer | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_permission_service_core.py | test_update_user_role_power_user_elevation | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_permission_service_core.py | test_check_permission_standard_user | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_permission_service_core.py | test_check_permission_super_admin | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_permission_service_core.py | test_check_permission_developer | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_permission_service_core.py | test_get_user_permissions_super_admin | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\agents\test_triage_entity_intent.py | test_intent_confidence_scoring | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_websocket_message_regression.py | mock_thread_service | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_websocket_message_regression.py | test_extract_user_request_priority_order | 30 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_supply_research_service_reports.py | test_provider_comparison_section_formatting | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_permission_service_unit.py | free_tier_user | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_permission_service_unit.py | pro_tier_user | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_permission_service_unit.py | developer_user | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_permission_service_unit.py | admin_user | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_permission_service_unit.py | super_admin_user | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_permission_service_unit.py | test_custom_permissions_applied_correctly | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_permission_service_unit.py | test_empty_permissions_dict_handling | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_permission_service_unit.py | test_none_permissions_handling | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_permission_service_unit.py | test_unknown_role_gets_empty_permissions | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| tests\e2e\test_system_resilience.py | resilience_metrics | 21 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_async_task_service.py | test_initialization | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_pr_router_state.py | test_build_pr_state_data_success | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_pr_router_state.py | test_encode_decode_state_roundtrip | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_pr_router_state.py | test_encode_state_special_characters | 14 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\critical\test_websocket_batch_reliability.py | test_metrics_consistency_during_failures | 20 | 8 | Split into multiple focused test functions or extract helper methods |
| auth_service\tests\test_security.py | security_test_payloads | 27 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_key_manager.py | test_load_from_settings_success | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_key_manager.py | test_load_from_settings_jwt_key_too_short | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_reliability_mechanisms.py | test_initial_state_and_threshold_triggering | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_reliability_mechanisms.py | test_open_to_half_open_recovery | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_reliability_mechanisms.py | test_half_open_success_closes_circuit | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_reliability_mechanisms.py | test_half_open_failure_reopens_circuit | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_reliability_mechanisms.py | test_max_delay_cap_and_jitter | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_reliability_mechanisms.py | test_agent_isolation_and_error_tracking | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_reliability_mechanisms.py | test_health_scoring_and_metrics | 18 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_state_model_regression.py | test_connection_builder_creates_valid_state | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_state_model_regression.py | test_migration_state_init | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_state_model_regression.py | test_langchain_agent_state_init | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_state_model_regression.py | test_sub_agent_state_init | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_state_model_regression.py | test_agent_state_from_apex_optimizer | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_state_model_regression.py | test_current_system_state_init | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_state_model_regression.py | test_system_state_diagnostic_init | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_state_model_regression.py | test_missing_required_field_error_message | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_tool_permission_service_initialization.py | test_analytics_permission_configuration | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_tool_permission_service_initialization.py | test_advanced_optimization_permission_configuration | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_tool_permission_service_initialization.py | test_system_management_permission_configuration | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_tool_permission_service_initialization.py | test_developer_tools_permission_configuration | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\validation\test_websocket_message_validation.py | test_validate_user_message_structure | 26 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\validation\test_websocket_message_validation.py | test_field_extraction_priority | 26 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\validation\test_websocket_message_validation.py | test_empty_and_null_field_handling | 23 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\validation\test_websocket_message_validation.py | test_references_field_validation | 26 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\validation\test_websocket_message_validation.py | test_thread_id_extraction | 22 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\validation\test_websocket_message_validation.py | test_special_characters_preservation | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\validation\test_websocket_message_validation.py | test_unicode_content_handling | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\validation\test_websocket_message_validation.py | test_large_content_handling | 11 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\validation\test_websocket_message_validation.py | test_nested_payload_structure | 17 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\validation\test_websocket_message_validation.py | test_message_type_variations | 20 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\validation\test_websocket_message_validation.py | test_malformed_json_handling | 18 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\validation\test_websocket_message_validation.py | test_whitespace_in_content | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\validation\test_websocket_message_validation.py | test_html_and_script_content_preserved | 10 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\validation\test_websocket_message_validation.py | test_payload_type_coercion | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\validation\test_websocket_message_validation.py | test_missing_optional_fields | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| test_framework\pytest_bad_test_plugin.py | pytest_addoption | 22 | 8 | Split into multiple focused test functions or extract helper methods |
| test_framework\pytest_bad_test_plugin.py | pytest_collection_modifyitems | 20 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\security\test_integrated_security.py | app_with_security | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\security\test_integrated_security.py | test_end_to_end_security | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\security\test_integrated_security.py | test_security_chain_validation | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\security\test_integrated_security.py | test_security_headers_integration | 17 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\security\test_integrated_security.py | test_rate_limiting_integration | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\security\test_integrated_security.py | test_comprehensive_security_scan | 16 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\unit\test_websocket_connection_paradox_regression.py | test_connection_manager_public_attribute_exists | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_tool_lifecycle_health.py | test_tool_lifecycle_management_state_transitions | 12 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_tool_lifecycle_health.py | test_tool_lifecycle_history_tracking | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\services\test_tool_lifecycle_health.py | test_tool_health_monitoring_individual | 9 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_agent_reliability_mixin_health.py | mock_agent | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_agent_reliability_mixin_health.py | test_calculate_success_rate | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_agent_reliability_mixin_health.py | test_calculate_avg_response_time | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_agent_reliability_mixin_health.py | test_count_recent_errors | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_agent_reliability_mixin_health.py | test_calculate_overall_health | 21 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_agent_reliability_mixin_health.py | test_determine_health_status | 20 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_agent_reliability_mixin_health.py | mock_agent | 13 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_agent_reliability_mixin_health.py | test_get_comprehensive_health_status | 18 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_agent_reliability_mixin_health.py | test_get_error_summary_with_errors | 19 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_agent_reliability_mixin_health.py | test_reset_health_metrics | 15 | 8 | Split into multiple focused test functions or extract helper methods |
| app\tests\core\test_agent_reliability_mixin_health.py | test_should_perform_health_check | 12 | 8 | Split into multiple focused test functions or extract helper methods |

## Splitting Suggestions

### tests\unified\e2e\test_oauth_endpoint_validation_real.py

- File has 490 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_oauth_endpoint_validation_real_feature1.py
-    - tests\unified\e2e\test_oauth_endpoint_validation_real_feature2.py

### tests\unified\e2e\test_backend_frontend_state_synchronization.py

- File has 758 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_backend_frontend_state_synchronization_feature1.py
-    - tests\unified\e2e\test_backend_frontend_state_synchronization_feature2.py

### tests\conftest.py

- File has 305 lines (limit: 300)
- Recommended splitting strategies:
- 1. Split by test categories:
-    - tests\conftest_unit.py (unit tests)
-    - tests\conftest_integration.py (integration tests)
-    - tests\conftest_e2e.py (end-to-end tests)
- 4. Split by feature being tested:
-    - tests\conftest_feature1.py
-    - tests\conftest_feature2.py

### tests\e2e\test_spike_recovery.py

- File has 1242 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\e2e\test_spike_recovery_testthunderingherdloginspike.py
-    - tests\e2e\test_spike_recovery_testwebsocketconnectionavalanche.py
-    - tests\e2e\test_spike_recovery_testautoscalingresponsevalidation.py
- 3. Extract helper functions:
-    - tests\e2e\test_spike_recovery_helpers.py (12 helpers)
- 4. Split by feature being tested:
-    - tests\e2e\test_spike_recovery_feature1.py
-    - tests\e2e\test_spike_recovery_feature2.py

### app\tests\unit\test_agent_lifecycle.py

- File has 462 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\unit\test_agent_lifecycle_testagent.py
-    - app\tests\unit\test_agent_lifecycle_testlifecyclebasics.py
-    - app\tests\unit\test_agent_lifecycle_testentryconditions.py
- 3. Extract helper functions:
-    - app\tests\unit\test_agent_lifecycle_helpers.py (9 helpers)
- 4. Split by feature being tested:
-    - app\tests\unit\test_agent_lifecycle_feature1.py
-    - app\tests\unit\test_agent_lifecycle_feature2.py

### tests\unified\websocket\test_websocket_resilience_recovery.py

- File has 868 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\websocket\test_websocket_resilience_recovery_websocketresiliencetester.py
-    - tests\unified\websocket\test_websocket_resilience_recovery_testautomaticreconnection.py
-    - tests\unified\websocket\test_websocket_resilience_recovery_testmessagequeuingandrecovery.py
- 3. Extract helper functions:
-    - tests\unified\websocket\test_websocket_resilience_recovery_helpers.py (4 helpers)
- 4. Split by feature being tested:
-    - tests\unified\websocket\test_websocket_resilience_recovery_feature1.py
-    - tests\unified\websocket\test_websocket_resilience_recovery_feature2.py

### tests\unified\e2e\test_websocket_auth_multiservice.py

- File has 545 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_websocket_auth_multiservice_feature1.py
-    - tests\unified\e2e\test_websocket_auth_multiservice_feature2.py

### app\tests\websocket\test_websocket_integration_performance.py

- File has 316 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\websocket\test_websocket_integration_performance_websocketintegrationtesthelper.py
-    - app\tests\websocket\test_websocket_integration_performance_websocketintegrationtestverifier.py
-    - app\tests\websocket\test_websocket_integration_performance_testwebsocketintegratedperformance.py
- 3. Extract helper functions:
-    - app\tests\websocket\test_websocket_integration_performance_helpers.py (7 helpers)
- 4. Split by feature being tested:
-    - app\tests\websocket\test_websocket_integration_performance_feature1.py
-    - app\tests\websocket\test_websocket_integration_performance_feature2.py

### tests\integration\test_startup_system.py

- File has 431 lines (limit: 300)
- Recommended splitting strategies:
- 1. Split by test categories:
-    - tests\integration\test_startup_system_unit.py (unit tests)
-    - tests\integration\test_startup_system_integration.py (integration tests)
-    - tests\integration\test_startup_system_e2e.py (end-to-end tests)
- 2. Split by test classes:
-    - tests\integration\test_startup_system_testdatabaseconnector.py
-    - tests\integration\test_startup_system_testenvironmentvalidator.py
-    - tests\integration\test_startup_system_teststartupsystemintegration.py
- 4. Split by feature being tested:
-    - tests\integration\test_startup_system_feature1.py
-    - tests\integration\test_startup_system_feature2.py

### tests\unified\test_supervisor_pattern_compliance.py

- File has 394 lines (limit: 300)
- Recommended splitting strategies:
- 1. Split by test categories:
-    - tests\unified\test_supervisor_pattern_compliance_unit.py (unit tests)
-    - tests\unified\test_supervisor_pattern_compliance_integration.py (integration tests)
-    - tests\unified\test_supervisor_pattern_compliance_e2e.py (end-to-end tests)
- 2. Split by test classes:
-    - tests\unified\test_supervisor_pattern_compliance_testsupervisorlifecyclemanager.py
-    - tests\unified\test_supervisor_pattern_compliance_testworkfloworchestrator.py
-    - tests\unified\test_supervisor_pattern_compliance_testcircuitbreakerintegration.py
- 4. Split by feature being tested:
-    - tests\unified\test_supervisor_pattern_compliance_feature1.py
-    - tests\unified\test_supervisor_pattern_compliance_feature2.py

### app\tests\clickhouse\test_query_correctness.py

- File has 448 lines (limit: 300)
- Recommended splitting strategies:
- 1. Split by test categories:
-    - app\tests\clickhouse\test_query_correctness_unit.py (unit tests)
-    - app\tests\clickhouse\test_query_correctness_integration.py (integration tests)
-    - app\tests\clickhouse\test_query_correctness_e2e.py (end-to-end tests)
- 2. Split by test classes:
-    - app\tests\clickhouse\test_query_correctness_testcorpusqueries.py
-    - app\tests\clickhouse\test_query_correctness_testperformancemetricsqueries.py
-    - app\tests\clickhouse\test_query_correctness_testanomalydetectionqueries.py
- 4. Split by feature being tested:
-    - app\tests\clickhouse\test_query_correctness_feature1.py
-    - app\tests\clickhouse\test_query_correctness_feature2.py

### tests\unified\e2e\staging_test_helpers.py

- File has 327 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\e2e\staging_test_helpers_stagingtestresult.py
-    - tests\unified\e2e\staging_test_helpers_stagingtestsuite.py
- 3. Extract helper functions:
-    - tests\unified\e2e\staging_test_helpers_helpers.py (4 helpers)
- 4. Split by feature being tested:
-    - tests\unified\e2e\staging_test_helpers_feature1.py
-    - tests\unified\e2e\staging_test_helpers_feature2.py

### tests\unified\websocket\test_concurrent_connections.py

- File has 466 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - tests\unified\websocket\test_concurrent_connections_helpers.py (15 helpers)
- 4. Split by feature being tested:
-    - tests\unified\websocket\test_concurrent_connections_feature1.py
-    - tests\unified\websocket\test_concurrent_connections_feature2.py

### tests\e2e\websocket_resilience\test_5_backend_service_restart.py

- File has 1047 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - tests\e2e\websocket_resilience\test_5_backend_service_restart_helpers.py (12 helpers)
- 4. Split by feature being tested:
-    - tests\e2e\websocket_resilience\test_5_backend_service_restart_feature1.py
-    - tests\e2e\websocket_resilience\test_5_backend_service_restart_feature2.py

### test_framework\fake_test_detector.py

- File has 850 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - test_framework\fake_test_detector_faketestresult.py
-    - test_framework\fake_test_detector_faketeststats.py
-    - test_framework\fake_test_detector_faketestdetector.py
- 3. Extract helper functions:
-    - test_framework\fake_test_detector_helpers.py (33 helpers)
- 4. Split by feature being tested:
-    - test_framework\fake_test_detector_feature1.py
-    - test_framework\fake_test_detector_feature2.py

### app\tests\integration\test_message_flow_errors.py

- File has 595 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\integration\test_message_flow_errors_testwebsocketlayererrors.py
-    - app\tests\integration\test_message_flow_errors_testagentlayererrors.py
-    - app\tests\integration\test_message_flow_errors_testdatabaselayererrors.py
- 4. Split by feature being tested:
-    - app\tests\integration\test_message_flow_errors_feature1.py
-    - app\tests\integration\test_message_flow_errors_feature2.py

### app\tests\test_database_connectivity_improvements.py

- File has 598 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\test_database_connectivity_improvements_testfaststartupconnectionmanager.py
-    - app\tests\test_database_connectivity_improvements_testclickhousereliablemanager.py
-    - app\tests\test_database_connectivity_improvements_testgracefuldegradationmanager.py
- 4. Split by feature being tested:
-    - app\tests\test_database_connectivity_improvements_feature1.py
-    - app\tests\test_database_connectivity_improvements_feature2.py

### test_framework\test_user_journeys_extended.py

- File has 497 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - test_framework\test_user_journeys_extended_oauthloginjourneytest.py
-    - test_framework\test_user_journeys_extended_realwebsocketjourneytest.py
-    - test_framework\test_user_journeys_extended_extendeduserjourneytestsuite.py
- 3. Extract helper functions:
-    - test_framework\test_user_journeys_extended_helpers.py (4 helpers)
- 4. Split by feature being tested:
-    - test_framework\test_user_journeys_extended_feature1.py
-    - test_framework\test_user_journeys_extended_feature2.py

### tests\unified\e2e\session_sync_helpers.py

- File has 488 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\e2e\session_sync_helpers_sessiontestuser.py
-    - tests\unified\e2e\session_sync_helpers_sessionsynctesthelper.py
-    - tests\unified\e2e\session_sync_helpers_sessionexpirytesthelper.py
- 3. Extract helper functions:
-    - tests\unified\e2e\session_sync_helpers_helpers.py (7 helpers)
- 4. Split by feature being tested:
-    - tests\unified\e2e\session_sync_helpers_feature1.py
-    - tests\unified\e2e\session_sync_helpers_feature2.py

### app\tests\integration\test_message_flow_performance.py

- File has 527 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\integration\test_message_flow_performance_testmessageflowlatency.py
-    - app\tests\integration\test_message_flow_performance_testmessageflowthroughput.py
-    - app\tests\integration\test_message_flow_performance_testresourceusagemetrics.py
- 3. Extract helper functions:
-    - app\tests\integration\test_message_flow_performance_helpers.py (10 helpers)
- 4. Split by feature being tested:
-    - app\tests\integration\test_message_flow_performance_feature1.py
-    - app\tests\integration\test_message_flow_performance_feature2.py

### tests\unified\e2e\test_agent_orchestration_runner.py

- File has 369 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - tests\unified\e2e\test_agent_orchestration_runner_helpers.py (9 helpers)
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_agent_orchestration_runner_feature1.py
-    - tests\unified\e2e\test_agent_orchestration_runner_feature2.py

### test_framework\gcp_integration\log_reader.py

- File has 394 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - test_framework\gcp_integration\log_reader_helpers.py (7 helpers)
- 4. Split by feature being tested:
-    - test_framework\gcp_integration\log_reader_feature1.py
-    - test_framework\gcp_integration\log_reader_feature2.py

### app\tests\routes\test_synthetic_data_generation.py

- File has 356 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - app\tests\routes\test_synthetic_data_generation_feature1.py
-    - app\tests\routes\test_synthetic_data_generation_feature2.py

### app\tests\integration\staging\test_staging_multi_service_startup_sequence.py

- File has 369 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - app\tests\integration\staging\test_staging_multi_service_startup_sequence_helpers.py (4 helpers)
- 4. Split by feature being tested:
-    - app\tests\integration\staging\test_staging_multi_service_startup_sequence_feature1.py
-    - app\tests\integration\staging\test_staging_multi_service_startup_sequence_feature2.py

### tests\unified\e2e\test_session_state_synchronization.py

- File has 800 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\e2e\test_session_state_synchronization_sessionsynctestresult.py
-    - tests\unified\e2e\test_session_state_synchronization_sessionstatesynchronizationtester.py
- 3. Extract helper functions:
-    - tests\unified\e2e\test_session_state_synchronization_helpers.py (4 helpers)
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_session_state_synchronization_feature1.py
-    - tests\unified\e2e\test_session_state_synchronization_feature2.py

### tests\unified\e2e\test_error_propagation_real.py

- File has 1356 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\e2e\test_error_propagation_real_realerrorpropagationtester.py
-    - tests\unified\e2e\test_error_propagation_real_testrealerrorpropagation.py
- 3. Extract helper functions:
-    - tests\unified\e2e\test_error_propagation_real_helpers.py (19 helpers)
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_error_propagation_real_feature1.py
-    - tests\unified\e2e\test_error_propagation_real_feature2.py

### app\tests\e2e\thread_test_fixtures.py

- File has 415 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\e2e\thread_test_fixtures_threadtestdatafactory.py
-    - app\tests\e2e\thread_test_fixtures_threadtestscenarios.py
-    - app\tests\e2e\thread_test_fixtures_threadtestvalidators.py
- 3. Extract helper functions:
-    - app\tests\e2e\thread_test_fixtures_helpers.py (13 helpers)
- 4. Split by feature being tested:
-    - app\tests\e2e\thread_test_fixtures_feature1.py
-    - app\tests\e2e\thread_test_fixtures_feature2.py

### tests\unified\e2e\test_health_cascade.py

- File has 449 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - tests\unified\e2e\test_health_cascade_helpers.py (4 helpers)
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_health_cascade_feature1.py
-    - tests\unified\e2e\test_health_cascade_feature2.py

### app\tests\integration\test_service_health_integration.py

- File has 349 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - app\tests\integration\test_service_health_integration_helpers.py (8 helpers)
- 4. Split by feature being tested:
-    - app\tests\integration\test_service_health_integration_feature1.py
-    - app\tests\integration\test_service_health_integration_feature2.py

### test_framework\test_config.py

- File has 347 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - test_framework\test_config_helpers.py (4 helpers)
- 4. Split by feature being tested:
-    - test_framework\test_config_feature1.py
-    - test_framework\test_config_feature2.py

### tests\unified\test_fallback_mechanisms.py

- File has 304 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\test_fallback_mechanisms_fallbacktestresult.py
-    - tests\unified\test_fallback_mechanisms_testllmfallbackchain.py
-    - tests\unified\test_fallback_mechanisms_testdatabasefallback.py
- 3. Extract helper functions:
-    - tests\unified\test_fallback_mechanisms_helpers.py (7 helpers)
- 4. Split by feature being tested:
-    - tests\unified\test_fallback_mechanisms_feature1.py
-    - tests\unified\test_fallback_mechanisms_feature2.py

### tests\unified\e2e\test_multi_agent_collaboration_response.py

- File has 744 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_multi_agent_collaboration_response_feature1.py
-    - tests\unified\e2e\test_multi_agent_collaboration_response_feature2.py

### tests\unified\e2e\test_cors_configuration.py

- File has 415 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\e2e\test_cors_configuration_corstestconfig.py
-    - tests\unified\e2e\test_cors_configuration_testcorsconfiguration.py
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_cors_configuration_feature1.py
-    - tests\unified\e2e\test_cors_configuration_feature2.py

### app\tests\helpers\supervisor_test_helpers.py

- File has 451 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - app\tests\helpers\supervisor_test_helpers_helpers.py (52 helpers)
- 4. Split by feature being tested:
-    - app\tests\helpers\supervisor_test_helpers_feature1.py
-    - app\tests\helpers\supervisor_test_helpers_feature2.py

### tests\unified\e2e\test_jwt_cross_service.py

- File has 385 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_jwt_cross_service_feature1.py
-    - tests\unified\e2e\test_jwt_cross_service_feature2.py

### tests\unified\e2e\test_agent_write_review_refine_integration.py

- File has 381 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_agent_write_review_refine_integration_feature1.py
-    - tests\unified\e2e\test_agent_write_review_refine_integration_feature2.py

### tests\unified\e2e\test_jwt_cross_service_validation.py

- File has 671 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_jwt_cross_service_validation_feature1.py
-    - tests\unified\e2e\test_jwt_cross_service_validation_feature2.py

### tests\unified\websocket\test_ui_layer_timing.py

- File has 573 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\websocket\test_ui_layer_timing_testfastlayertiming.py
-    - tests\unified\websocket\test_ui_layer_timing_testmediumlayertiming.py
-    - tests\unified\websocket\test_ui_layer_timing_testslowlayertiming.py
- 3. Extract helper functions:
-    - tests\unified\websocket\test_ui_layer_timing_helpers.py (6 helpers)
- 4. Split by feature being tested:
-    - tests\unified\websocket\test_ui_layer_timing_feature1.py
-    - tests\unified\websocket\test_ui_layer_timing_feature2.py

### app\tests\services\test_security_service_oauth.py

- File has 336 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\services\test_security_service_oauth_testsecurityserviceoauth.py
-    - app\tests\services\test_security_service_oauth_testsecurityserviceconcurrency.py
- 3. Extract helper functions:
-    - app\tests\services\test_security_service_oauth_helpers.py (21 helpers)
- 4. Split by feature being tested:
-    - app\tests\services\test_security_service_oauth_feature1.py
-    - app\tests\services\test_security_service_oauth_feature2.py

### app\tests\fixtures\database_test_fixtures.py

- File has 315 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - app\tests\fixtures\database_test_fixtures_helpers.py (23 helpers)
- 4. Split by feature being tested:
-    - app\tests\fixtures\database_test_fixtures_feature1.py
-    - app\tests\fixtures\database_test_fixtures_feature2.py

### app\tests\database\test_repositories_comprehensive.py

- File has 521 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\database\test_repositories_comprehensive_testthreadrepositoryoperations.py
-    - app\tests\database\test_repositories_comprehensive_testmessagerepositoryqueries.py
-    - app\tests\database\test_repositories_comprehensive_testuserrepositoryauth.py
- 4. Split by feature being tested:
-    - app\tests\database\test_repositories_comprehensive_feature1.py
-    - app\tests\database\test_repositories_comprehensive_feature2.py

### tests\unified\e2e\test_websocket_message_guarantee_integration.py

- File has 481 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_websocket_message_guarantee_integration_feature1.py
-    - tests\unified\e2e\test_websocket_message_guarantee_integration_feature2.py

### app\tests\patterns\async_test_isolation_improved.py

- File has 322 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\patterns\async_test_isolation_improved_asynctestisolationmanager.py
-    - app\tests\patterns\async_test_isolation_improved_asynctestpatternvalidator.py
- 3. Extract helper functions:
-    - app\tests\patterns\async_test_isolation_improved_helpers.py (10 helpers)
- 4. Split by feature being tested:
-    - app\tests\patterns\async_test_isolation_improved_feature1.py
-    - app\tests\patterns\async_test_isolation_improved_feature2.py

### tests\e2e\websocket_resilience\test_7_heartbeat_validation.py

- File has 572 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - tests\e2e\websocket_resilience\test_7_heartbeat_validation_helpers.py (9 helpers)
- 4. Split by feature being tested:
-    - tests\e2e\websocket_resilience\test_7_heartbeat_validation_feature1.py
-    - tests\e2e\websocket_resilience\test_7_heartbeat_validation_feature2.py

### tests\unified\e2e\test_websocket_service_discovery.py

- File has 311 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_websocket_service_discovery_feature1.py
-    - tests\unified\e2e\test_websocket_service_discovery_feature2.py

### app\tests\integration\test_auth_service_integration.py

- File has 414 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - app\tests\integration\test_auth_service_integration_feature1.py
-    - app\tests\integration\test_auth_service_integration_feature2.py

### tests\unified\agent_test_harness.py

- File has 308 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\agent_test_harness_testservicestate.py
-    - tests\unified\agent_test_harness_agenttestharness.py
- 3. Extract helper functions:
-    - tests\unified\agent_test_harness_helpers.py (9 helpers)
- 4. Split by feature being tested:
-    - tests\unified\agent_test_harness_feature1.py
-    - tests\unified\agent_test_harness_feature2.py

### app\tests\critical\test_websocket_agent_startup.py

- File has 351 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\critical\test_websocket_agent_startup_testagentstartupwithoutcontext.py
-    - app\tests\critical\test_websocket_agent_startup_testagentstartupedgecases.py
- 4. Split by feature being tested:
-    - app\tests\critical\test_websocket_agent_startup_feature1.py
-    - app\tests\critical\test_websocket_agent_startup_feature2.py

### tests\unified\e2e\test_staging_websocket_messaging.py

- File has 503 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\e2e\test_staging_websocket_messaging_stagingwebsockettester.py
-    - tests\unified\e2e\test_staging_websocket_messaging_teststagingwebsocketconnection.py
-    - tests\unified\e2e\test_staging_websocket_messaging_teststagingwebsocketmessaging.py
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_staging_websocket_messaging_feature1.py
-    - tests\unified\e2e\test_staging_websocket_messaging_feature2.py

### tests\e2e\test_cors_comprehensive_e2e.py

- File has 310 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\e2e\test_cors_comprehensive_e2e_corsvalidationtester.py
-    - tests\e2e\test_cors_comprehensive_e2e_testcorscomprehensivee2e.py
- 4. Split by feature being tested:
-    - tests\e2e\test_cors_comprehensive_e2e_feature1.py
-    - tests\e2e\test_cors_comprehensive_e2e_feature2.py

### tests\unified\e2e\test_websocket_db_session_handling.py

- File has 700 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_websocket_db_session_handling_feature1.py
-    - tests\unified\e2e\test_websocket_db_session_handling_feature2.py

### tests\unified\e2e\test_real_agent_pipeline.py

- File has 329 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\e2e\test_real_agent_pipeline_testrealagentpipeline.py
-    - tests\unified\e2e\test_real_agent_pipeline_agentpipelinetestcore.py
-    - tests\unified\e2e\test_real_agent_pipeline_agentpipelinetestutils.py
- 3. Extract helper functions:
-    - tests\unified\e2e\test_real_agent_pipeline_helpers.py (13 helpers)
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_real_agent_pipeline_feature1.py
-    - tests\unified\e2e\test_real_agent_pipeline_feature2.py

### tests\unified\jwt_token_helpers.py

- File has 444 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\jwt_token_helpers_jwttesthelper.py
-    - tests\unified\jwt_token_helpers_jwttestfixtures.py
-    - tests\unified\jwt_token_helpers_jwtsecuritytester.py
- 3. Extract helper functions:
-    - tests\unified\jwt_token_helpers_helpers.py (23 helpers)
- 4. Split by feature being tested:
-    - tests\unified\jwt_token_helpers_feature1.py
-    - tests\unified\jwt_token_helpers_feature2.py

### app\tests\integration\test_transaction_coordination_integration.py

- File has 617 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\integration\test_transaction_coordination_integration_testdistributedtransactionpatterns.py
-    - app\tests\integration\test_transaction_coordination_integration_testdeadlockdetectionresolution.py
-    - app\tests\integration\test_transaction_coordination_integration_testcrossservicetransactionintegrity.py
- 3. Extract helper functions:
-    - app\tests\integration\test_transaction_coordination_integration_helpers.py (6 helpers)
- 4. Split by feature being tested:
-    - app\tests\integration\test_transaction_coordination_integration_feature1.py
-    - app\tests\integration\test_transaction_coordination_integration_feature2.py

### tests\unified\e2e\test_auth_service_health_check_integration.py

- File has 433 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\e2e\test_auth_service_health_check_integration_authservicerecoverytester.py
-    - tests\unified\e2e\test_auth_service_health_check_integration_testauthservicehealthcheckintegration.py
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_auth_service_health_check_integration_feature1.py
-    - tests\unified\e2e\test_auth_service_health_check_integration_feature2.py

### app\tests\integration\test_websocket_state_recovery.py

- File has 878 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\integration\test_websocket_state_recovery_staterecoverytesthelper.py
-    - app\tests\integration\test_websocket_state_recovery_testwebsocketstaterecovery.py
-    - app\tests\integration\test_websocket_state_recovery_testwebsocketstaterecoveryperformance.py
- 3. Extract helper functions:
-    - app\tests\integration\test_websocket_state_recovery_helpers.py (17 helpers)
- 4. Split by feature being tested:
-    - app\tests\integration\test_websocket_state_recovery_feature1.py
-    - app\tests\integration\test_websocket_state_recovery_feature2.py

### app\tests\clickhouse\test_performance_edge_cases.py

- File has 357 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\clickhouse\test_performance_edge_cases_testlargedatasetperformance.py
-    - app\tests\clickhouse\test_performance_edge_cases_testedgecasehandling.py
-    - app\tests\clickhouse\test_performance_edge_cases_testconcurrencyandasync.py
- 4. Split by feature being tested:
-    - app\tests\clickhouse\test_performance_edge_cases_feature1.py
-    - app\tests\clickhouse\test_performance_edge_cases_feature2.py

### app\tests\test_websocket_comprehensive.py

- File has 459 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\test_websocket_comprehensive_testwebsocketconnectionestablishment.py
-    - app\tests\test_websocket_comprehensive_testwebsocketauthvalidation.py
-    - app\tests\test_websocket_comprehensive_testwebsocketmessagerouting.py
- 4. Split by feature being tested:
-    - app\tests\test_websocket_comprehensive_feature1.py
-    - app\tests\test_websocket_comprehensive_feature2.py

### tests\unified\test_thread_management.py

- File has 339 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - tests\unified\test_thread_management_helpers.py (17 helpers)
- 4. Split by feature being tested:
-    - tests\unified\test_thread_management_feature1.py
-    - tests\unified\test_thread_management_feature2.py

### app\tests\integration\test_configuration_integration.py

- File has 318 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - app\tests\integration\test_configuration_integration_helpers.py (5 helpers)
- 4. Split by feature being tested:
-    - app\tests\integration\test_configuration_integration_feature1.py
-    - app\tests\integration\test_configuration_integration_feature2.py

### tests\unified\e2e\test_websocket_jwt_auth_real.py

- File has 510 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\e2e\test_websocket_jwt_auth_real_websocketjwtauthtester.py
-    - tests\unified\e2e\test_websocket_jwt_auth_real_tokensecuritytester.py
- 3. Extract helper functions:
-    - tests\unified\e2e\test_websocket_jwt_auth_real_helpers.py (4 helpers)
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_websocket_jwt_auth_real_feature1.py
-    - tests\unified\e2e\test_websocket_jwt_auth_real_feature2.py

### tests\unified\e2e\test_websocket_message_format_validation.py

- File has 454 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_websocket_message_format_validation_feature1.py
-    - tests\unified\e2e\test_websocket_message_format_validation_feature2.py

### tests\unified\e2e\test_enterprise_sso.py

- File has 301 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_enterprise_sso_feature1.py
-    - tests\unified\e2e\test_enterprise_sso_feature2.py

### tests\e2e\test_soak_testing.py

- File has 929 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\e2e\test_soak_testing_soaktestresults.py
-    - tests\e2e\test_soak_testing_websocketstresstest.py
-    - tests\e2e\test_soak_testing_databasestresstest.py
- 3. Extract helper functions:
-    - tests\e2e\test_soak_testing_helpers.py (12 helpers)
- 4. Split by feature being tested:
-    - tests\e2e\test_soak_testing_feature1.py
-    - tests\e2e\test_soak_testing_feature2.py

### tests\unified\e2e\test_llm_quality_gate_integration.py

- File has 346 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_llm_quality_gate_integration_feature1.py
-    - tests\unified\e2e\test_llm_quality_gate_integration_feature2.py

### tests\unified\e2e\test_oauth_real_service_flow.py

- File has 417 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - tests\unified\e2e\test_oauth_real_service_flow_helpers.py (5 helpers)
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_oauth_real_service_flow_feature1.py
-    - tests\unified\e2e\test_oauth_real_service_flow_feature2.py

### app\tests\performance\test_agent_load_stress.py

- File has 335 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\performance\test_agent_load_stress_agentloadtestfixtures.py
-    - app\tests\performance\test_agent_load_stress_testagentloadscenarios.py
-    - app\tests\performance\test_agent_load_stress_testagentstressscenarios.py
- 3. Extract helper functions:
-    - app\tests\performance\test_agent_load_stress_helpers.py (9 helpers)
- 4. Split by feature being tested:
-    - app\tests\performance\test_agent_load_stress_feature1.py
-    - app\tests\performance\test_agent_load_stress_feature2.py

### tests\integration\test_dev_launcher_errors.py

- File has 620 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - tests\integration\test_dev_launcher_errors_helpers.py (20 helpers)
- 4. Split by feature being tested:
-    - tests\integration\test_dev_launcher_errors_feature1.py
-    - tests\integration\test_dev_launcher_errors_feature2.py

### app\tests\agents\test_data_sub_agent_consolidated.py

- File has 563 lines (limit: 300)
- Recommended splitting strategies:
- 1. Split by test categories:
-    - app\tests\agents\test_data_sub_agent_consolidated_unit.py (unit tests)
-    - app\tests\agents\test_data_sub_agent_consolidated_integration.py (integration tests)
-    - app\tests\agents\test_data_sub_agent_consolidated_e2e.py (end-to-end tests)
- 2. Split by test classes:
-    - app\tests\agents\test_data_sub_agent_consolidated_testdatasubagentconsolidated.py
-    - app\tests\agents\test_data_sub_agent_consolidated_testclickhouseclient.py
-    - app\tests\agents\test_data_sub_agent_consolidated_testdatavalidator.py
- 4. Split by feature being tested:
-    - app\tests\agents\test_data_sub_agent_consolidated_feature1.py
-    - app\tests\agents\test_data_sub_agent_consolidated_feature2.py

### tests\unified\e2e\test_session_sync_validation.py

- File has 393 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_session_sync_validation_feature1.py
-    - tests\unified\e2e\test_session_sync_validation_feature2.py

### tests\unified\e2e\test_quality_gate_response_validation.py

- File has 489 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_quality_gate_response_validation_feature1.py
-    - tests\unified\e2e\test_quality_gate_response_validation_feature2.py

### app\tests\llm\test_llm_integration_real.py

- File has 343 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\llm\test_llm_integration_real_testrealresponsepatterns.py
-    - app\tests\llm\test_llm_integration_real_testretrymechanisms.py
-    - app\tests\llm\test_llm_integration_real_testcostoptimization.py
- 4. Split by feature being tested:
-    - app\tests\llm\test_llm_integration_real_feature1.py
-    - app\tests\llm\test_llm_integration_real_feature2.py

### app\tests\core\test_json_parsing_helpers_and_edge_cases.py

- File has 324 lines (limit: 300)
- Recommended splitting strategies:
- 1. Split by test categories:
-    - app\tests\core\test_json_parsing_helpers_and_edge_cases_unit.py (unit tests)
-    - app\tests\core\test_json_parsing_helpers_and_edge_cases_integration.py (integration tests)
-    - app\tests\core\test_json_parsing_helpers_and_edge_cases_e2e.py (end-to-end tests)
- 2. Split by test classes:
-    - app\tests\core\test_json_parsing_helpers_and_edge_cases_testhelperfunctions.py
-    - app\tests\core\test_json_parsing_helpers_and_edge_cases_testloggingbehavior.py
-    - app\tests\core\test_json_parsing_helpers_and_edge_cases_testedgecases.py
- 3. Extract helper functions:
-    - app\tests\core\test_json_parsing_helpers_and_edge_cases_helpers.py (8 helpers)
- 4. Split by feature being tested:
-    - app\tests\core\test_json_parsing_helpers_and_edge_cases_feature1.py
-    - app\tests\core\test_json_parsing_helpers_and_edge_cases_feature2.py

### app\tests\services\test_quality_gate_integration.py

- File has 376 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - app\tests\services\test_quality_gate_integration_helpers.py (28 helpers)
- 4. Split by feature being tested:
-    - app\tests\services\test_quality_gate_integration_feature1.py
-    - app\tests\services\test_quality_gate_integration_feature2.py

### test_framework\memory_optimized_executor.py

- File has 416 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - test_framework\memory_optimized_executor_helpers.py (8 helpers)
- 4. Split by feature being tested:
-    - test_framework\memory_optimized_executor_feature1.py
-    - test_framework\memory_optimized_executor_feature2.py

### tests\unified\e2e\test_health_check_cascade.py

- File has 384 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - tests\unified\e2e\test_health_check_cascade_helpers.py (11 helpers)
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_health_check_cascade_feature1.py
-    - tests\unified\e2e\test_health_check_cascade_feature2.py

### app\tests\e2e\conftest.py

- File has 668 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - app\tests\e2e\conftest_helpers.py (47 helpers)
- 4. Split by feature being tested:
-    - app\tests\e2e\conftest_feature1.py
-    - app\tests\e2e\conftest_feature2.py

### app\tests\integration\test_multi_agent_coordination_init.py

- File has 719 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - app\tests\integration\test_multi_agent_coordination_init_helpers.py (6 helpers)
- 4. Split by feature being tested:
-    - app\tests\integration\test_multi_agent_coordination_init_feature1.py
-    - app\tests\integration\test_multi_agent_coordination_init_feature2.py

### app\tests\integration\test_gcp_monitoring_routes.py

- File has 336 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - app\tests\integration\test_gcp_monitoring_routes_helpers.py (6 helpers)
- 4. Split by feature being tested:
-    - app\tests\integration\test_gcp_monitoring_routes_feature1.py
-    - app\tests\integration\test_gcp_monitoring_routes_feature2.py

### app\tests\integration\test_first_message_error_recovery.py

- File has 364 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - app\tests\integration\test_first_message_error_recovery_feature1.py
-    - app\tests\integration\test_first_message_error_recovery_feature2.py

### tests\e2e\websocket_resilience\test_3_message_queuing_disconnection.py

- File has 930 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\e2e\websocket_resilience\test_3_message_queuing_disconnection_queuetestmessage.py
-    - tests\e2e\websocket_resilience\test_3_message_queuing_disconnection_websocketqueuetestclient.py
- 3. Extract helper functions:
-    - tests\e2e\websocket_resilience\test_3_message_queuing_disconnection_helpers.py (8 helpers)
- 4. Split by feature being tested:
-    - tests\e2e\websocket_resilience\test_3_message_queuing_disconnection_feature1.py
-    - tests\e2e\websocket_resilience\test_3_message_queuing_disconnection_feature2.py

### app\tests\test_database_repository_critical.py

- File has 329 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - app\tests\test_database_repository_critical_feature1.py
-    - app\tests\test_database_repository_critical_feature2.py

### app\tests\integration\user_flows\test_free_tier_onboarding.py

- File has 306 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - app\tests\integration\user_flows\test_free_tier_onboarding_feature1.py
-    - app\tests\integration\user_flows\test_free_tier_onboarding_feature2.py

### app\tests\websocket\test_websocket_reliability_fixes.py

- File has 585 lines (limit: 300)
- Recommended splitting strategies:
- 1. Split by test categories:
-    - app\tests\websocket\test_websocket_reliability_fixes_unit.py (unit tests)
-    - app\tests\websocket\test_websocket_reliability_fixes_integration.py (integration tests)
-    - app\tests\websocket\test_websocket_reliability_fixes_e2e.py (end-to-end tests)
- 2. Split by test classes:
-    - app\tests\websocket\test_websocket_reliability_fixes_testdatabaseconnectionpooling.py
-    - app\tests\websocket\test_websocket_reliability_fixes_testjwttokenrefresh.py
-    - app\tests\websocket\test_websocket_reliability_fixes_testmemoryleakprevention.py
- 4. Split by feature being tested:
-    - app\tests\websocket\test_websocket_reliability_fixes_feature1.py
-    - app\tests\websocket\test_websocket_reliability_fixes_feature2.py

### tests\e2e\test_concurrent_tool_conflicts.py

- File has 1030 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\e2e\test_concurrent_tool_conflicts_concurrencytestmetrics.py
-    - tests\e2e\test_concurrent_tool_conflicts_concurrenttoolconflicttestframework.py
-    - tests\e2e\test_concurrent_tool_conflicts_testconcurrenttoolexecutionconflicts.py
- 3. Extract helper functions:
-    - tests\e2e\test_concurrent_tool_conflicts_helpers.py (6 helpers)
- 4. Split by feature being tested:
-    - tests\e2e\test_concurrent_tool_conflicts_feature1.py
-    - tests\e2e\test_concurrent_tool_conflicts_feature2.py

### app\tests\unit\test_staging_error_monitor.py

- File has 460 lines (limit: 300)
- Recommended splitting strategies:
- 1. Split by test categories:
-    - app\tests\unit\test_staging_error_monitor_unit.py (unit tests)
-    - app\tests\unit\test_staging_error_monitor_integration.py (integration tests)
-    - app\tests\unit\test_staging_error_monitor_e2e.py (end-to-end tests)
- 2. Split by test classes:
-    - app\tests\unit\test_staging_error_monitor_testerroranalyzer.py
-    - app\tests\unit\test_staging_error_monitor_testconsoleformatter.py
-    - app\tests\unit\test_staging_error_monitor_testdeploymentdecision.py
- 3. Extract helper functions:
-    - app\tests\unit\test_staging_error_monitor_helpers.py (6 helpers)
- 4. Split by feature being tested:
-    - app\tests\unit\test_staging_error_monitor_feature1.py
-    - app\tests\unit\test_staging_error_monitor_feature2.py

### tests\unified\websocket\test_event_structure_consistency.py

- File has 524 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\websocket\test_event_structure_consistency_testmessagestructureconsistency.py
-    - tests\unified\websocket\test_event_structure_consistency_testeventcatalogstructurecompliance.py
-    - tests\unified\websocket\test_event_structure_consistency_testlegacypatterndetection.py
- 3. Extract helper functions:
-    - tests\unified\websocket\test_event_structure_consistency_helpers.py (4 helpers)
- 4. Split by feature being tested:
-    - tests\unified\websocket\test_event_structure_consistency_feature1.py
-    - tests\unified\websocket\test_event_structure_consistency_feature2.py

### tests\unified\e2e\test_complete_oauth_chat_journey.py

- File has 621 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - tests\unified\e2e\test_complete_oauth_chat_journey_helpers.py (11 helpers)
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_complete_oauth_chat_journey_feature1.py
-    - tests\unified\e2e\test_complete_oauth_chat_journey_feature2.py

### tests\unified\e2e\test_auth_websocket_handshake_integration.py

- File has 316 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\e2e\test_auth_websocket_handshake_integration_authwebsockettester.py
-    - tests\unified\e2e\test_auth_websocket_handshake_integration_testauthwebsockethandshakeintegration.py
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_auth_websocket_handshake_integration_feature1.py
-    - tests\unified\e2e\test_auth_websocket_handshake_integration_feature2.py

### tests\unified\e2e\test_multi_agent_websocket_isolation.py

- File has 365 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - tests\unified\e2e\test_multi_agent_websocket_isolation_helpers.py (11 helpers)
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_multi_agent_websocket_isolation_feature1.py
-    - tests\unified\e2e\test_multi_agent_websocket_isolation_feature2.py

### app\tests\unit\test_security_middleware.py

- File has 400 lines (limit: 300)
- Recommended splitting strategies:
- 1. Split by test categories:
-    - app\tests\unit\test_security_middleware_unit.py (unit tests)
-    - app\tests\unit\test_security_middleware_integration.py (integration tests)
-    - app\tests\unit\test_security_middleware_e2e.py (end-to-end tests)
- 2. Split by test classes:
-    - app\tests\unit\test_security_middleware_testsecurityconfig.py
-    - app\tests\unit\test_security_middleware_testratelimittracker.py
-    - app\tests\unit\test_security_middleware_testinputvalidator.py
- 4. Split by feature being tested:
-    - app\tests\unit\test_security_middleware_feature1.py
-    - app\tests\unit\test_security_middleware_feature2.py

### tests\unified\e2e\test_real_rate_limiting.py

- File has 416 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_real_rate_limiting_feature1.py
-    - tests\unified\e2e\test_real_rate_limiting_feature2.py

### tests\websocket\test_websocket_integration.py

- File has 589 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\websocket\test_websocket_integration_testwebsocketservicediscovery.py
-    - tests\websocket\test_websocket_integration_testwebsocketcors.py
-    - tests\websocket\test_websocket_integration_testwebsocketauthentication.py
- 3. Extract helper functions:
-    - tests\websocket\test_websocket_integration_helpers.py (15 helpers)
- 4. Split by feature being tested:
-    - tests\websocket\test_websocket_integration_feature1.py
-    - tests\websocket\test_websocket_integration_feature2.py

### app\tests\e2e\test_agent_message_flow.py

- File has 632 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\e2e\test_agent_message_flow_testagentmessageflow.py
-    - app\tests\e2e\test_agent_message_flow_testagentmessageflowperformance.py
- 3. Extract helper functions:
-    - app\tests\e2e\test_agent_message_flow_helpers.py (7 helpers)
- 4. Split by feature being tested:
-    - app\tests\e2e\test_agent_message_flow_feature1.py
-    - app\tests\e2e\test_agent_message_flow_feature2.py

### tests\unified\e2e\test_jwt_lifecycle_real.py

- File has 620 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\e2e\test_jwt_lifecycle_real_jwtlifecycletestmanager.py
-    - tests\unified\e2e\test_jwt_lifecycle_real_testjwtlifecyclereal.py
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_jwt_lifecycle_real_feature1.py
-    - tests\unified\e2e\test_jwt_lifecycle_real_feature2.py

### tests\unified\e2e\test_session_persistence_complete.py

- File has 702 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_session_persistence_complete_feature1.py
-    - tests\unified\e2e\test_session_persistence_complete_feature2.py

### tests\unified\test_websocket_auth_handshake.py

- File has 362 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\test_websocket_auth_handshake_websocketauthhandshaketester.py
-    - tests\unified\test_websocket_auth_handshake_testwebsocketauthhandshake.py
- 3. Extract helper functions:
-    - tests\unified\test_websocket_auth_handshake_helpers.py (7 helpers)
- 4. Split by feature being tested:
-    - tests\unified\test_websocket_auth_handshake_feature1.py
-    - tests\unified\test_websocket_auth_handshake_feature2.py

### app\tests\services\test_generation_service_comprehensive.py

- File has 301 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\services\test_generation_service_comprehensive_testjobstatusmanagement.py
-    - app\tests\services\test_generation_service_comprehensive_testclickhouseoperations.py
-    - app\tests\services\test_generation_service_comprehensive_testexistingfunctions.py
- 4. Split by feature being tested:
-    - app\tests\services\test_generation_service_comprehensive_feature1.py
-    - app\tests\services\test_generation_service_comprehensive_feature2.py

### app\tests\integration\test_websocket_end_to_end.py

- File has 394 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\integration\test_websocket_end_to_end_testwebsocketconnectionlifecycle.py
-    - app\tests\integration\test_websocket_end_to_end_testwebsocketmessageprocessing.py
-    - app\tests\integration\test_websocket_end_to_end_testwebsocketbroadcasting.py
- 4. Split by feature being tested:
-    - app\tests\integration\test_websocket_end_to_end_feature1.py
-    - app\tests\integration\test_websocket_end_to_end_feature2.py

### tests\e2e\test_db_connection_pool.py

- File has 658 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\e2e\test_db_connection_pool_poolexhaustiontestharness.py
-    - tests\e2e\test_db_connection_pool_testdatabaseconnectionpoolexhaustion.py
-    - tests\e2e\test_db_connection_pool_testdatabaseconnectionpoolperformance.py
- 4. Split by feature being tested:
-    - tests\e2e\test_db_connection_pool_feature1.py
-    - tests\e2e\test_db_connection_pool_feature2.py

### app\tests\core\test_missing_tests_validation.py

- File has 311 lines (limit: 300)
- Recommended splitting strategies:
- 1. Split by test categories:
-    - app\tests\core\test_missing_tests_validation_unit.py (unit tests)
-    - app\tests\core\test_missing_tests_validation_integration.py (integration tests)
-    - app\tests\core\test_missing_tests_validation_e2e.py (end-to-end tests)
- 2. Split by test classes:
-    - app\tests\core\test_missing_tests_validation_testconfigvalidator.py
-    - app\tests\core\test_missing_tests_validation_testerrorcontext.py
-    - app\tests\core\test_missing_tests_validation_testcustomexceptions.py
- 4. Split by feature being tested:
-    - app\tests\core\test_missing_tests_validation_feature1.py
-    - app\tests\core\test_missing_tests_validation_feature2.py

### app\tests\integration\test_dev_auth_cold_start_integration.py

- File has 358 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\integration\test_dev_auth_cold_start_integration_devauthcoldstartintegrationtest.py
-    - app\tests\integration\test_dev_auth_cold_start_integration_testdevauthcoldstartintegration.py
- 4. Split by feature being tested:
-    - app\tests\integration\test_dev_auth_cold_start_integration_feature1.py
-    - app\tests\integration\test_dev_auth_cold_start_integration_feature2.py

### app\tests\websocket\test_websocket_performance_components.py

- File has 376 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\websocket\test_websocket_performance_components_testwebsocketmemorymanagerperformance.py
-    - app\tests\websocket\test_websocket_performance_components_testwebsocketmessagebatcherperformance.py
-    - app\tests\websocket\test_websocket_performance_components_testwebsocketcompressionperformance.py
- 4. Split by feature being tested:
-    - app\tests\websocket\test_websocket_performance_components_feature1.py
-    - app\tests\websocket\test_websocket_performance_components_feature2.py

### tests\integration\test_dev_launcher_real.py

- File has 571 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - tests\integration\test_dev_launcher_real_helpers.py (10 helpers)
- 4. Split by feature being tested:
-    - tests\integration\test_dev_launcher_real_feature1.py
-    - tests\integration\test_dev_launcher_real_feature2.py

### app\tests\auth_integration\test_auth_core.py

- File has 325 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\auth_integration\test_auth_core_testauthenticationcore.py
-    - app\tests\auth_integration\test_auth_core_testoptionalauthentication.py
-    - app\tests\auth_integration\test_auth_core_testauthenticationboundaries.py
- 4. Split by feature being tested:
-    - app\tests\auth_integration\test_auth_core_feature1.py
-    - app\tests\auth_integration\test_auth_core_feature2.py

### app\tests\unified_system\test_health_coordination.py

- File has 489 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - app\tests\unified_system\test_health_coordination_helpers.py (4 helpers)
- 4. Split by feature being tested:
-    - app\tests\unified_system\test_health_coordination_feature1.py
-    - app\tests\unified_system\test_health_coordination_feature2.py

### tests\integration\test_websocket_auth_handshake_complete_flow.py

- File has 366 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\integration\test_websocket_auth_handshake_complete_flow_websocketauthhandshaketester.py
-    - tests\integration\test_websocket_auth_handshake_complete_flow_testwebsocketauthhandshakecompleteflow.py
- 4. Split by feature being tested:
-    - tests\integration\test_websocket_auth_handshake_complete_flow_feature1.py
-    - tests\integration\test_websocket_auth_handshake_complete_flow_feature2.py

### auth_service\tests\utils\test_helpers.py

- File has 331 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - auth_service\tests\utils\test_helpers_authtestutils.py
-    - auth_service\tests\utils\test_helpers_tokentestutils.py
-    - auth_service\tests\utils\test_helpers_databasetestutils.py
- 3. Extract helper functions:
-    - auth_service\tests\utils\test_helpers_helpers.py (8 helpers)
- 4. Split by feature being tested:
-    - auth_service\tests\utils\test_helpers_feature1.py
-    - auth_service\tests\utils\test_helpers_feature2.py

### tests\unified\e2e\test_example_prompts_e2e_real_llm.py

- File has 458 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\e2e\test_example_prompts_e2e_real_llm_exampleprompttestcase.py
-    - tests\unified\e2e\test_example_prompts_e2e_real_llm_examplepromptstestdata.py
-    - tests\unified\e2e\test_example_prompts_e2e_real_llm_testexamplepromptse2erealllm.py
- 3. Extract helper functions:
-    - tests\unified\e2e\test_example_prompts_e2e_real_llm_helpers.py (10 helpers)
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_example_prompts_e2e_real_llm_feature1.py
-    - tests\unified\e2e\test_example_prompts_e2e_real_llm_feature2.py

### app\tests\core\test_async_function_utilities.py

- File has 326 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\core\test_async_function_utilities_testtimeoutfunctionscomplete.py
-    - app\tests\core\test_async_function_utilities_testretrydecoratorcomplete.py
-    - app\tests\core\test_async_function_utilities_testglobalfunctionscomplete.py
- 4. Split by feature being tested:
-    - app\tests\core\test_async_function_utilities_feature1.py
-    - app\tests\core\test_async_function_utilities_feature2.py

### app\tests\core\test_circuit_breaker.py

- File has 456 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\core\test_circuit_breaker_testcircuitconfig.py
-    - app\tests\core\test_circuit_breaker_testcircuitbreaker.py
-    - app\tests\core\test_circuit_breaker_testcircuitbreakerregistry.py
- 4. Split by feature being tested:
-    - app\tests\core\test_circuit_breaker_feature1.py
-    - app\tests\core\test_circuit_breaker_feature2.py

### tests\unified\e2e\test_websocket_reconnection_auth.py

- File has 518 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\e2e\test_websocket_reconnection_auth_websocketreconnectionauthtester.py
-    - tests\unified\e2e\test_websocket_reconnection_auth_testwebsocketreconnectionwithauth.py
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_websocket_reconnection_auth_feature1.py
-    - tests\unified\e2e\test_websocket_reconnection_auth_feature2.py

### test_framework\seed_data_manager.py

- File has 720 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - test_framework\seed_data_manager_helpers.py (7 helpers)
- 4. Split by feature being tested:
-    - test_framework\seed_data_manager_feature1.py
-    - test_framework\seed_data_manager_feature2.py

### tests\unified\e2e\cache_coherence_helpers.py

- File has 340 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - tests\unified\e2e\cache_coherence_helpers_helpers.py (4 helpers)
- 4. Split by feature being tested:
-    - tests\unified\e2e\cache_coherence_helpers_feature1.py
-    - tests\unified\e2e\cache_coherence_helpers_feature2.py

### tests\e2e\test_startup_comprehensive_e2e.py

- File has 518 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\e2e\test_startup_comprehensive_e2e_startupvalidationtester.py
-    - tests\e2e\test_startup_comprehensive_e2e_teststartupcomprehensivee2e.py
- 4. Split by feature being tested:
-    - tests\e2e\test_startup_comprehensive_e2e_feature1.py
-    - tests\e2e\test_startup_comprehensive_e2e_feature2.py

### tests\unified\test_auth_backend_database_consistency.py

- File has 384 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\test_auth_backend_database_consistency_databaseconsistencytester.py
-    - tests\unified\test_auth_backend_database_consistency_testauthbackenddatabaseconsistency.py
-    - tests\unified\test_auth_backend_database_consistency_testauthbackenddataintegrity.py
- 3. Extract helper functions:
-    - tests\unified\test_auth_backend_database_consistency_helpers.py (7 helpers)
- 4. Split by feature being tested:
-    - tests\unified\test_auth_backend_database_consistency_feature1.py
-    - tests\unified\test_auth_backend_database_consistency_feature2.py

### app\tests\websocket\test_websocket_bidirectional_types.py

- File has 421 lines (limit: 300)
- Recommended splitting strategies:
- 1. Split by test categories:
-    - app\tests\websocket\test_websocket_bidirectional_types_unit.py (unit tests)
-    - app\tests\websocket\test_websocket_bidirectional_types_integration.py (integration tests)
-    - app\tests\websocket\test_websocket_bidirectional_types_e2e.py (end-to-end tests)
- 2. Split by test classes:
-    - app\tests\websocket\test_websocket_bidirectional_types_testbidirectionaltypeconsistency.py
-    - app\tests\websocket\test_websocket_bidirectional_types_testwebsocketsendtothread.py
-    - app\tests\websocket\test_websocket_bidirectional_types_testwebsocketmessagevalidation.py
- 4. Split by feature being tested:
-    - app\tests\websocket\test_websocket_bidirectional_types_feature1.py
-    - app\tests\websocket\test_websocket_bidirectional_types_feature2.py

### tests\unified\websocket\test_auth_validation.py

- File has 435 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\websocket\test_auth_validation_websocketauthtester.py
-    - tests\unified\websocket\test_auth_validation_testwebsocketauthvalidation.py
-    - tests\unified\websocket\test_auth_validation_testwebsocketauthcompliance.py
- 3. Extract helper functions:
-    - tests\unified\websocket\test_auth_validation_helpers.py (6 helpers)
- 4. Split by feature being tested:
-    - tests\unified\websocket\test_auth_validation_feature1.py
-    - tests\unified\websocket\test_auth_validation_feature2.py

### tests\unified\e2e\test_authentication_token_flow.py

- File has 615 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - tests\unified\e2e\test_authentication_token_flow_helpers.py (7 helpers)
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_authentication_token_flow_feature1.py
-    - tests\unified\e2e\test_authentication_token_flow_feature2.py

### tests\unified\e2e\test_cross_service_session_sync.py

- File has 545 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_cross_service_session_sync_feature1.py
-    - tests\unified\e2e\test_cross_service_session_sync_feature2.py

### tests\unified\e2e\test_websocket_event_completeness.py

- File has 840 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\e2e\test_websocket_event_completeness_websocketeventcompletenesstestcore.py
-    - tests\unified\e2e\test_websocket_event_completeness_testwebsocketeventcompleteness.py
- 3. Extract helper functions:
-    - tests\unified\e2e\test_websocket_event_completeness_helpers.py (13 helpers)
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_websocket_event_completeness_feature1.py
-    - tests\unified\e2e\test_websocket_event_completeness_feature2.py

### tests\unified\e2e\test_database_connections.py

- File has 304 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\e2e\test_database_connections_databaseconnectiontester.py
-    - tests\unified\e2e\test_database_connections_devdatabasetestfixture.py
- 3. Extract helper functions:
-    - tests\unified\e2e\test_database_connections_helpers.py (5 helpers)
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_database_connections_feature1.py
-    - tests\unified\e2e\test_database_connections_feature2.py

### app\tests\core\test_alert_manager.py

- File has 318 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - app\tests\core\test_alert_manager_feature1.py
-    - app\tests\core\test_alert_manager_feature2.py

### app\tests\test_api_error_handling_critical.py

- File has 322 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - app\tests\test_api_error_handling_critical_feature1.py
-    - app\tests\test_api_error_handling_critical_feature2.py

### app\tests\critical\test_config_secrets_manager.py

- File has 381 lines (limit: 300)
- Recommended splitting strategies:
- 1. Split by test categories:
-    - app\tests\critical\test_config_secrets_manager_unit.py (unit tests)
-    - app\tests\critical\test_config_secrets_manager_integration.py (integration tests)
-    - app\tests\critical\test_config_secrets_manager_e2e.py (end-to-end tests)
- 2. Split by test classes:
-    - app\tests\critical\test_config_secrets_manager_testsecretmanagerinitialization.py
-    - app\tests\critical\test_config_secrets_manager_testsecretloadingcore.py
-    - app\tests\critical\test_config_secrets_manager_testconfigsecretsmanagercore.py
- 4. Split by feature being tested:
-    - app\tests\critical\test_config_secrets_manager_feature1.py
-    - app\tests\critical\test_config_secrets_manager_feature2.py

### app\tests\unit\test_new_user_critical_flows.py

- File has 334 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - app\tests\unit\test_new_user_critical_flows_helpers.py (4 helpers)
- 4. Split by feature being tested:
-    - app\tests\unit\test_new_user_critical_flows_feature1.py
-    - app\tests\unit\test_new_user_critical_flows_feature2.py

### app\tests\agents\test_supervisor_integration.py

- File has 439 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\agents\test_supervisor_integration_testqualitysupervisorvalidation.py
-    - app\tests\agents\test_supervisor_integration_testadmintooldispatcherrouting.py
-    - app\tests\agents\test_supervisor_integration_testcorpusadmindocumentmanagement.py
- 3. Extract helper functions:
-    - app\tests\agents\test_supervisor_integration_helpers.py (4 helpers)
- 4. Split by feature being tested:
-    - app\tests\agents\test_supervisor_integration_feature1.py
-    - app\tests\agents\test_supervisor_integration_feature2.py

### tests\unified\e2e\test_cold_start_zero_to_response.py

- File has 335 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - tests\unified\e2e\test_cold_start_zero_to_response_helpers.py (9 helpers)
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_cold_start_zero_to_response_feature1.py
-    - tests\unified\e2e\test_cold_start_zero_to_response_feature2.py

### app\tests\startup\test_config_validation.py

- File has 317 lines (limit: 300)
- Recommended splitting strategies:
- 1. Split by test categories:
-    - app\tests\startup\test_config_validation_unit.py (unit tests)
-    - app\tests\startup\test_config_validation_integration.py (integration tests)
-    - app\tests\startup\test_config_validation_e2e.py (end-to-end tests)
- 2. Split by test classes:
-    - app\tests\startup\test_config_validation_testserviceconfigvalidatorinit.py
-    - app\tests\startup\test_config_validation_testconfigfilechecking.py
-    - app\tests\startup\test_config_validation_testconfigloading.py
- 4. Split by feature being tested:
-    - app\tests\startup\test_config_validation_feature1.py
-    - app\tests\startup\test_config_validation_feature2.py

### app\tests\integration\test_first_time_user_comprehensive_critical.py

- File has 825 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - app\tests\integration\test_first_time_user_comprehensive_critical_helpers.py (4 helpers)
- 4. Split by feature being tested:
-    - app\tests\integration\test_first_time_user_comprehensive_critical_feature1.py
-    - app\tests\integration\test_first_time_user_comprehensive_critical_feature2.py

### test_framework\unified_orchestrator.py

- File has 455 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - test_framework\unified_orchestrator_helpers.py (18 helpers)
- 4. Split by feature being tested:
-    - test_framework\unified_orchestrator_feature1.py
-    - test_framework\unified_orchestrator_feature2.py

### tests\e2e\websocket_resilience\test_9_network_interface_switching.py

- File has 408 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - tests\e2e\websocket_resilience\test_9_network_interface_switching_helpers.py (5 helpers)
- 4. Split by feature being tested:
-    - tests\e2e\websocket_resilience\test_9_network_interface_switching_feature1.py
-    - tests\e2e\websocket_resilience\test_9_network_interface_switching_feature2.py

### tests\unified\e2e\test_real_websocket_auth_integration.py

- File has 465 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\e2e\test_real_websocket_auth_integration_realwebsocketauthtester.py
-    - tests\unified\e2e\test_real_websocket_auth_integration_concurrentconnectiontester.py
-    - tests\unified\e2e\test_real_websocket_auth_integration_testrealwebsocketauthintegration.py
- 3. Extract helper functions:
-    - tests\unified\e2e\test_real_websocket_auth_integration_helpers.py (7 helpers)
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_real_websocket_auth_integration_feature1.py
-    - tests\unified\e2e\test_real_websocket_auth_integration_feature2.py

### app\tests\critical\test_auth_user_persistence_regression.py

- File has 343 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\critical\test_auth_user_persistence_regression_testauthuserpersistenceregression.py
-    - app\tests\critical\test_auth_user_persistence_regression_testauthserviceintegration.py
- 4. Split by feature being tested:
-    - app\tests\critical\test_auth_user_persistence_regression_feature1.py
-    - app\tests\critical\test_auth_user_persistence_regression_feature2.py

### tests\unified\test_llm_integration.py

- File has 311 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\test_llm_integration_llmintegrationtester.py
-    - tests\unified\test_llm_integration_testllmfallbackchain.py
-    - tests\unified\test_llm_integration_testllmratelimithandling.py
- 3. Extract helper functions:
-    - tests\unified\test_llm_integration_helpers.py (13 helpers)
- 4. Split by feature being tested:
-    - tests\unified\test_llm_integration_feature1.py
-    - tests\unified\test_llm_integration_feature2.py

### tests\unified\test_resource_usage_integration.py

- File has 308 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\test_resource_usage_integration_testresourceefficiencyintegration.py
-    - tests\unified\test_resource_usage_integration_testresourcestresspatterns.py
- 3. Extract helper functions:
-    - tests\unified\test_resource_usage_integration_helpers.py (6 helpers)
- 4. Split by feature being tested:
-    - tests\unified\test_resource_usage_integration_feature1.py
-    - tests\unified\test_resource_usage_integration_feature2.py

### app\tests\services\test_synthetic_data_validation.py

- File has 465 lines (limit: 300)
- Recommended splitting strategies:
- 1. Split by test categories:
-    - app\tests\services\test_synthetic_data_validation_unit.py (unit tests)
-    - app\tests\services\test_synthetic_data_validation_integration.py (integration tests)
-    - app\tests\services\test_synthetic_data_validation_e2e.py (end-to-end tests)
- 2. Split by test classes:
-    - app\tests\services\test_synthetic_data_validation_testspecificationvalidation.py
-    - app\tests\services\test_synthetic_data_validation_testimplementationconsistency.py
-    - app\tests\services\test_synthetic_data_validation_testkeyfeatureimplementation.py
- 4. Split by feature being tested:
-    - app\tests\services\test_synthetic_data_validation_feature1.py
-    - app\tests\services\test_synthetic_data_validation_feature2.py

### app\tests\unified_system\test_oauth_flow.py

- File has 417 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\unified_system\test_oauth_flow_testoauthcompleteflow.py
-    - app\tests\unified_system\test_oauth_flow_testtokengenerationandvalidation.py
-    - app\tests\unified_system\test_oauth_flow_testwebsocketauthentication.py
- 4. Split by feature being tested:
-    - app\tests\unified_system\test_oauth_flow_feature1.py
-    - app\tests\unified_system\test_oauth_flow_feature2.py

### app\tests\e2e\test_middleware_hook_ordering.py

- File has 309 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\e2e\test_middleware_hook_ordering_testmiddlewareordering.py
-    - app\tests\e2e\test_middleware_hook_ordering_testhookexecutionsequence.py
-    - app\tests\e2e\test_middleware_hook_ordering_testmixincomposition.py
- 3. Extract helper functions:
-    - app\tests\e2e\test_middleware_hook_ordering_helpers.py (6 helpers)
- 4. Split by feature being tested:
-    - app\tests\e2e\test_middleware_hook_ordering_feature1.py
-    - app\tests\e2e\test_middleware_hook_ordering_feature2.py

### app\tests\core\test_config_manager.py

- File has 377 lines (limit: 300)
- Recommended splitting strategies:
- 1. Split by test categories:
-    - app\tests\core\test_config_manager_unit.py (unit tests)
-    - app\tests\core\test_config_manager_integration.py (integration tests)
-    - app\tests\core\test_config_manager_e2e.py (end-to-end tests)
- 2. Split by test classes:
-    - app\tests\core\test_config_manager_testsecretmanager.py
-    - app\tests\core\test_config_manager_testconfigvalidator.py
-    - app\tests\core\test_config_manager_testconfigmanager.py
- 4. Split by feature being tested:
-    - app\tests\core\test_config_manager_feature1.py
-    - app\tests\core\test_config_manager_feature2.py

### tests\e2e\test_throughput_delivery_guarantees.py

- File has 310 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - tests\e2e\test_throughput_delivery_guarantees_feature1.py
-    - tests\e2e\test_throughput_delivery_guarantees_feature2.py

### tests\unified\e2e\test_websocket_message_structure.py

- File has 505 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - tests\unified\e2e\test_websocket_message_structure_helpers.py (8 helpers)
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_websocket_message_structure_feature1.py
-    - tests\unified\e2e\test_websocket_message_structure_feature2.py

### tests\unified\e2e\test_websocket_jwt_complete.py

- File has 594 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_websocket_jwt_complete_feature1.py
-    - tests\unified\e2e\test_websocket_jwt_complete_feature2.py

### app\tests\e2e\test_thread_context.py

- File has 366 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\e2e\test_thread_context_contextpreservationtests.py
-    - app\tests\e2e\test_thread_context_messagehistorytests.py
-    - app\tests\e2e\test_thread_context_stateisolationtests.py
- 4. Split by feature being tested:
-    - app\tests\e2e\test_thread_context_feature1.py
-    - app\tests\e2e\test_thread_context_feature2.py

### tests\agents\test_supervisor_websocket_integration.py

- File has 346 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - tests\agents\test_supervisor_websocket_integration_feature1.py
-    - tests\agents\test_supervisor_websocket_integration_feature2.py

### app\tests\integration\test_circuit_breaker_cascade.py

- File has 698 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\integration\test_circuit_breaker_cascade_cascadetestresult.py
-    - app\tests\integration\test_circuit_breaker_cascade_testcircuitbreakercascade.py
- 4. Split by feature being tested:
-    - app\tests\integration\test_circuit_breaker_cascade_feature1.py
-    - app\tests\integration\test_circuit_breaker_cascade_feature2.py

### tests\unified\test_session_persistence.py

- File has 330 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - tests\unified\test_session_persistence_helpers.py (20 helpers)
- 4. Split by feature being tested:
-    - tests\unified\test_session_persistence_feature1.py
-    - tests\unified\test_session_persistence_feature2.py

### tests\unified\e2e\test_session_persistence_restart_real.py

- File has 753 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_session_persistence_restart_real_feature1.py
-    - tests\unified\e2e\test_session_persistence_restart_real_feature2.py

### app\tests\unified_system\fixtures.py

- File has 309 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - app\tests\unified_system\fixtures_feature1.py
-    - app\tests\unified_system\fixtures_feature2.py

### tests\unified\e2e\test_agent_compensation_integration.py

- File has 366 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_agent_compensation_integration_feature1.py
-    - tests\unified\e2e\test_agent_compensation_integration_feature2.py

### app\tests\core\test_error_handling.py

- File has 492 lines (limit: 300)
- Recommended splitting strategies:
- 1. Split by test categories:
-    - app\tests\core\test_error_handling_unit.py (unit tests)
-    - app\tests\core\test_error_handling_integration.py (integration tests)
-    - app\tests\core\test_error_handling_e2e.py (end-to-end tests)
- 2. Split by test classes:
-    - app\tests\core\test_error_handling_testerrorcodes.py
-    - app\tests\core\test_error_handling_testerrordetails.py
-    - app\tests\core\test_error_handling_testnetraexceptions.py
- 4. Split by feature being tested:
-    - app\tests\core\test_error_handling_feature1.py
-    - app\tests\core\test_error_handling_feature2.py

### app\tests\integration\staging\test_staging_clickhouse_http_native_ports.py

- File has 504 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - app\tests\integration\staging\test_staging_clickhouse_http_native_ports_helpers.py (5 helpers)
- 4. Split by feature being tested:
-    - app\tests\integration\staging\test_staging_clickhouse_http_native_ports_feature1.py
-    - app\tests\integration\staging\test_staging_clickhouse_http_native_ports_feature2.py

### tests\unified\harness_complete.py

- File has 405 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\harness_complete_testdataseeder.py
-    - tests\unified\harness_complete_teststate.py
-    - tests\unified\harness_complete_unifiedtestharnesscomplete.py
- 3. Extract helper functions:
-    - tests\unified\harness_complete_helpers.py (20 helpers)
- 4. Split by feature being tested:
-    - tests\unified\harness_complete_feature1.py
-    - tests\unified\harness_complete_feature2.py

### app\tests\integration\test_staging_health_check_integration.py

- File has 378 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - app\tests\integration\test_staging_health_check_integration_feature1.py
-    - app\tests\integration\test_staging_health_check_integration_feature2.py

### tests\unified\e2e\test_response_persistence_recovery.py

- File has 627 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_response_persistence_recovery_feature1.py
-    - tests\unified\e2e\test_response_persistence_recovery_feature2.py

### app\tests\integration\test_message_flow_auth.py

- File has 490 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\integration\test_message_flow_auth_testmessageflowauthentication.py
-    - app\tests\integration\test_message_flow_auth_testauthenticationintegrationflow.py
-    - app\tests\integration\test_message_flow_auth_testauthenticationperformance.py
- 3. Extract helper functions:
-    - app\tests\integration\test_message_flow_auth_helpers.py (7 helpers)
- 4. Split by feature being tested:
-    - app\tests\integration\test_message_flow_auth_feature1.py
-    - app\tests\integration\test_message_flow_auth_feature2.py

### app\tests\core\test_core_infrastructure_11_20.py

- File has 377 lines (limit: 300)
- Recommended splitting strategies:
- 1. Split by test categories:
-    - app\tests\core\test_core_infrastructure_11_20_unit.py (unit tests)
-    - app\tests\core\test_core_infrastructure_11_20_integration.py (integration tests)
-    - app\tests\core\test_core_infrastructure_11_20_e2e.py (end-to-end tests)
- 2. Split by test classes:
-    - app\tests\core\test_core_infrastructure_11_20_testconfigvalidator.py
-    - app\tests\core\test_core_infrastructure_11_20_testerrorcontext.py
-    - app\tests\core\test_core_infrastructure_11_20_testerrorhandlers.py
- 4. Split by feature being tested:
-    - app\tests\core\test_core_infrastructure_11_20_feature1.py
-    - app\tests\core\test_core_infrastructure_11_20_feature2.py

### tests\unified\e2e\test_multi_tab_session_real.py

- File has 485 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - tests\unified\e2e\test_multi_tab_session_real_helpers.py (13 helpers)
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_multi_tab_session_real_feature1.py
-    - tests\unified\e2e\test_multi_tab_session_real_feature2.py

### auth_service\tests\integration\test_oauth_flows.py

- File has 520 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - auth_service\tests\integration\test_oauth_flows_testgoogleoauthflow.py
-    - auth_service\tests\integration\test_oauth_flows_testgithuboauthflow.py
-    - auth_service\tests\integration\test_oauth_flows_testmicrosoftoauthflow.py
- 4. Split by feature being tested:
-    - auth_service\tests\integration\test_oauth_flows_feature1.py
-    - auth_service\tests\integration\test_oauth_flows_feature2.py

### tests\unified\e2e\test_websocket_event_structure.py

- File has 335 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - tests\unified\e2e\test_websocket_event_structure_helpers.py (5 helpers)
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_websocket_event_structure_feature1.py
-    - tests\unified\e2e\test_websocket_event_structure_feature2.py

### tests\unified\websocket\test_connection_cleanup.py

- File has 568 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\websocket\test_connection_cleanup_connectioncleanuptester.py
-    - tests\unified\websocket\test_connection_cleanup_testnormalconnectioncleanup.py
-    - tests\unified\websocket\test_connection_cleanup_testabnormalconnectioncleanup.py
- 3. Extract helper functions:
-    - tests\unified\websocket\test_connection_cleanup_helpers.py (5 helpers)
- 4. Split by feature being tested:
-    - tests\unified\websocket\test_connection_cleanup_feature1.py
-    - tests\unified\websocket\test_connection_cleanup_feature2.py

### app\tests\integration\test_database_pool_integration.py

- File has 354 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - app\tests\integration\test_database_pool_integration_helpers.py (7 helpers)
- 4. Split by feature being tested:
-    - app\tests\integration\test_database_pool_integration_feature1.py
-    - app\tests\integration\test_database_pool_integration_feature2.py

### test_framework\unified\orchestrator.py

- File has 557 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - test_framework\unified\orchestrator_testsuite.py
-    - test_framework\unified\orchestrator_unifiedtestorchestrator.py
- 4. Split by feature being tested:
-    - test_framework\unified\orchestrator_feature1.py
-    - test_framework\unified\orchestrator_feature2.py

### test_framework\unified\base_interfaces.py

- File has 432 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - test_framework\unified\base_interfaces_testenvironment.py
-    - test_framework\unified\base_interfaces_testlevel.py
-    - test_framework\unified\base_interfaces_testresult.py
- 3. Extract helper functions:
-    - test_framework\unified\base_interfaces_helpers.py (12 helpers)
- 4. Split by feature being tested:
-    - test_framework\unified\base_interfaces_feature1.py
-    - test_framework\unified\base_interfaces_feature2.py

### tests\unified\test_websocket_integration.py

- File has 313 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\test_websocket_integration_websocketauthtester.py
-    - tests\unified\test_websocket_integration_testwebsocketauthhandshake.py
-    - tests\unified\test_websocket_integration_testreconnectionwithauth.py
- 3. Extract helper functions:
-    - tests\unified\test_websocket_integration_helpers.py (11 helpers)
- 4. Split by feature being tested:
-    - tests\unified\test_websocket_integration_feature1.py
-    - tests\unified\test_websocket_integration_feature2.py

### tests\unified\e2e\payment_billing_helpers.py

- File has 370 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - tests\unified\e2e\payment_billing_helpers_helpers.py (15 helpers)
- 4. Split by feature being tested:
-    - tests\unified\e2e\payment_billing_helpers_feature1.py
-    - tests\unified\e2e\payment_billing_helpers_feature2.py

### app\tests\e2e\test_middleware_validation_security.py

- File has 301 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\e2e\test_middleware_validation_security_testrequestvalidationmiddleware.py
-    - app\tests\e2e\test_middleware_validation_security_testresponsetransformationmiddleware.py
-    - app\tests\e2e\test_middleware_validation_security_testratelimitingmiddleware.py
- 3. Extract helper functions:
-    - app\tests\e2e\test_middleware_validation_security_helpers.py (9 helpers)
- 4. Split by feature being tested:
-    - app\tests\e2e\test_middleware_validation_security_feature1.py
-    - app\tests\e2e\test_middleware_validation_security_feature2.py

### app\tests\auth_integration\test_real_auth_integration.py

- File has 417 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\auth_integration\test_real_auth_integration_testrealtokenvalidation.py
-    - app\tests\auth_integration\test_real_auth_integration_testrealuserretrieval.py
-    - app\tests\auth_integration\test_real_auth_integration_testrealpermissionvalidation.py
- 4. Split by feature being tested:
-    - app\tests\auth_integration\test_real_auth_integration_feature1.py
-    - app\tests\auth_integration\test_real_auth_integration_feature2.py

### tests\unified\e2e\test_websocket_advanced_integration.py

- File has 414 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - tests\unified\e2e\test_websocket_advanced_integration_helpers.py (12 helpers)
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_websocket_advanced_integration_feature1.py
-    - tests\unified\e2e\test_websocket_advanced_integration_feature2.py

### app\tests\integration\test_enterprise_features_integration.py

- File has 431 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - app\tests\integration\test_enterprise_features_integration_feature1.py
-    - app\tests\integration\test_enterprise_features_integration_feature2.py

### app\tests\integration\test_staging_auth_service_integration.py

- File has 486 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - app\tests\integration\test_staging_auth_service_integration_feature1.py
-    - app\tests\integration\test_staging_auth_service_integration_feature2.py

### tests\unified\test_jwt_permission_propagation.py

- File has 409 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - tests\unified\test_jwt_permission_propagation_feature1.py
-    - tests\unified\test_jwt_permission_propagation_feature2.py

### tests\unified\e2e\test_error_propagation_unified.py

- File has 784 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\e2e\test_error_propagation_unified_errorpropagationtester.py
-    - tests\unified\e2e\test_error_propagation_unified_testerrorpropagationunified.py
- 3. Extract helper functions:
-    - tests\unified\e2e\test_error_propagation_unified_helpers.py (13 helpers)
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_error_propagation_unified_feature1.py
-    - tests\unified\e2e\test_error_propagation_unified_feature2.py

### tests\unified\e2e\test_agent_orchestration_real_llm.py

- File has 470 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\e2e\test_agent_orchestration_real_llm_testagentorchestrationrealllm.py
-    - tests\unified\e2e\test_agent_orchestration_real_llm_testagentorchestrationperformance.py
- 3. Extract helper functions:
-    - tests\unified\e2e\test_agent_orchestration_real_llm_helpers.py (8 helpers)
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_agent_orchestration_real_llm_feature1.py
-    - tests\unified\e2e\test_agent_orchestration_real_llm_feature2.py

### tests\unified\test_harness.py

- File has 364 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\test_harness_teststate.py
-    - tests\unified\test_harness_unifiedtestharness.py
-    - tests\unified\test_harness_authflowtesthelper.py
- 3. Extract helper functions:
-    - tests\unified\test_harness_helpers.py (27 helpers)
- 4. Split by feature being tested:
-    - tests\unified\test_harness_feature1.py
-    - tests\unified\test_harness_feature2.py

### tests\unified\e2e\test_rate_limiting_complete.py

- File has 806 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_rate_limiting_complete_feature1.py
-    - tests\unified\e2e\test_rate_limiting_complete_feature2.py

### app\tests\integration\test_operational_systems_integration.py

- File has 797 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - app\tests\integration\test_operational_systems_integration_feature1.py
-    - app\tests\integration\test_operational_systems_integration_feature2.py

### app\tests\integration\test_critical_integration.py

- File has 415 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - app\tests\integration\test_critical_integration_helpers.py (9 helpers)
- 4. Split by feature being tested:
-    - app\tests\integration\test_critical_integration_feature1.py
-    - app\tests\integration\test_critical_integration_feature2.py

### app\tests\integration\user_flows\test_early_tier_flows.py

- File has 325 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - app\tests\integration\user_flows\test_early_tier_flows_feature1.py
-    - app\tests\integration\user_flows\test_early_tier_flows_feature2.py

### tests\unified\websocket\test_websocket_lifecycle_auth.py

- File has 518 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\websocket\test_websocket_lifecycle_auth_websocketlifecycleauthtester.py
-    - tests\unified\websocket\test_websocket_lifecycle_auth_testwebsocketconnectionlifecycle.py
-    - tests\unified\websocket\test_websocket_lifecycle_auth_testwebsocketpersistentconnection.py
- 3. Extract helper functions:
-    - tests\unified\websocket\test_websocket_lifecycle_auth_helpers.py (4 helpers)
- 4. Split by feature being tested:
-    - tests\unified\websocket\test_websocket_lifecycle_auth_feature1.py
-    - tests\unified\websocket\test_websocket_lifecycle_auth_feature2.py

### tests\integration\test_dev_environment_initialization.py

- File has 781 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\integration\test_dev_environment_initialization_testdevenvironmentinitialization.py
-    - tests\integration\test_dev_environment_initialization_testdevenvironmentedgecases.py
-    - tests\integration\test_dev_environment_initialization_testdevenvironmentrealservices.py
- 3. Extract helper functions:
-    - tests\integration\test_dev_environment_initialization_helpers.py (13 helpers)
- 4. Split by feature being tested:
-    - tests\integration\test_dev_environment_initialization_feature1.py
-    - tests\integration\test_dev_environment_initialization_feature2.py

### app\tests\integration\test_supply_research_optimization.py

- File has 622 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - app\tests\integration\test_supply_research_optimization_helpers.py (8 helpers)
- 4. Split by feature being tested:
-    - app\tests\integration\test_supply_research_optimization_feature1.py
-    - app\tests\integration\test_supply_research_optimization_feature2.py

### app\tests\e2e\multi_constraint_test_helpers.py

- File has 333 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - app\tests\e2e\multi_constraint_test_helpers_helpers.py (29 helpers)
- 4. Split by feature being tested:
-    - app\tests\e2e\multi_constraint_test_helpers_feature1.py
-    - app\tests\e2e\multi_constraint_test_helpers_feature2.py

### tests\unified\test_agent_startup_coverage_validation.py

- File has 447 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\test_agent_startup_coverage_validation_startuptestarea.py
-    - tests\unified\test_agent_startup_coverage_validation_testvalidationresult.py
-    - tests\unified\test_agent_startup_coverage_validation_startuptestdiscoverer.py
- 3. Extract helper functions:
-    - tests\unified\test_agent_startup_coverage_validation_helpers.py (23 helpers)
- 4. Split by feature being tested:
-    - tests\unified\test_agent_startup_coverage_validation_feature1.py
-    - tests\unified\test_agent_startup_coverage_validation_feature2.py

### app\tests\services\test_repository_basic_transactions.py

- File has 319 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - app\tests\services\test_repository_basic_transactions_feature1.py
-    - app\tests\services\test_repository_basic_transactions_feature2.py

### app\tests\unified_system\test_agent_activation.py

- File has 666 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\unified_system\test_agent_activation_agentactivationtesthelper.py
-    - app\tests\unified_system\test_agent_activation_testagentactivation.py
- 3. Extract helper functions:
-    - app\tests\unified_system\test_agent_activation_helpers.py (10 helpers)
- 4. Split by feature being tested:
-    - app\tests\unified_system\test_agent_activation_feature1.py
-    - app\tests\unified_system\test_agent_activation_feature2.py

### app\tests\integration\test_background_jobs_integration.py

- File has 535 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\integration\test_background_jobs_integration_testjobqueuemanagement.py
-    - app\tests\integration\test_background_jobs_integration_testjobfailurehandling.py
-    - app\tests\integration\test_background_jobs_integration_testjobstatustracking.py
- 3. Extract helper functions:
-    - app\tests\integration\test_background_jobs_integration_helpers.py (5 helpers)
- 4. Split by feature being tested:
-    - app\tests\integration\test_background_jobs_integration_feature1.py
-    - app\tests\integration\test_background_jobs_integration_feature2.py

### tests\unified\e2e\test_multi_service_integration.py

- File has 621 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\e2e\test_multi_service_integration_loadtestexecutor.py
-    - tests\unified\e2e\test_multi_service_integration_testmultiserviceintegration.py
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_multi_service_integration_feature1.py
-    - tests\unified\e2e\test_multi_service_integration_feature2.py

### app\tests\integration\test_revenue_pipeline_integration.py

- File has 377 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - app\tests\integration\test_revenue_pipeline_integration_feature1.py
-    - app\tests\integration\test_revenue_pipeline_integration_feature2.py

### app\tests\critical\test_websocket_message_routing_critical.py

- File has 507 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - app\tests\critical\test_websocket_message_routing_critical_feature1.py
-    - app\tests\critical\test_websocket_message_routing_critical_feature2.py

### app\tests\unified_system\test_message_pipeline.py

- File has 488 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\unified_system\test_message_pipeline_messagepipelinetesthelper.py
-    - app\tests\unified_system\test_message_pipeline_testmessagepipeline.py
- 3. Extract helper functions:
-    - app\tests\unified_system\test_message_pipeline_helpers.py (4 helpers)
- 4. Split by feature being tested:
-    - app\tests\unified_system\test_message_pipeline_feature1.py
-    - app\tests\unified_system\test_message_pipeline_feature2.py

### tests\unified\test_security_integration.py

- File has 358 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\test_security_integration_securitytesthelpers.py
-    - tests\unified\test_security_integration_testsecurityintegration.py
- 4. Split by feature being tested:
-    - tests\unified\test_security_integration_feature1.py
-    - tests\unified\test_security_integration_feature2.py

### app\tests\agents\test_supervisor_corpus_data.py

- File has 325 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\agents\test_supervisor_corpus_data_testcorpusadmindocumentmanagement.py
-    - app\tests\agents\test_supervisor_corpus_data_testsupplyresearcherdatacollection.py
-    - app\tests\agents\test_supervisor_corpus_data_testdemoserviceworkflow.py
- 3. Extract helper functions:
-    - app\tests\agents\test_supervisor_corpus_data_helpers.py (26 helpers)
- 4. Split by feature being tested:
-    - app\tests\agents\test_supervisor_corpus_data_feature1.py
-    - app\tests\agents\test_supervisor_corpus_data_feature2.py

### test_framework\staging_testing\endpoint_validator.py

- File has 593 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - test_framework\staging_testing\endpoint_validator_helpers.py (4 helpers)
- 4. Split by feature being tested:
-    - test_framework\staging_testing\endpoint_validator_feature1.py
-    - test_framework\staging_testing\endpoint_validator_feature2.py

### tests\unified\e2e\test_agent_tool_atomicity_integration.py

- File has 520 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\e2e\test_agent_tool_atomicity_integration_tooltestresult.py
-    - tests\unified\e2e\test_agent_tool_atomicity_integration_agenttoolatomicitytester.py
- 3. Extract helper functions:
-    - tests\unified\e2e\test_agent_tool_atomicity_integration_helpers.py (4 helpers)
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_agent_tool_atomicity_integration_feature1.py
-    - tests\unified\e2e\test_agent_tool_atomicity_integration_feature2.py

### app\tests\websocket\test_websocket_e2e_complete.py

- File has 419 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\websocket\test_websocket_e2e_complete_testwebsocketauthenticationflow.py
-    - app\tests\websocket\test_websocket_e2e_complete_testwebsocketmessageflow.py
-    - app\tests\websocket\test_websocket_e2e_complete_testagentresponsestreaming.py
- 4. Split by feature being tested:
-    - app\tests\websocket\test_websocket_e2e_complete_feature1.py
-    - app\tests\websocket\test_websocket_e2e_complete_feature2.py

### tests\unified\test_performance_targets.py

- File has 447 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\test_performance_targets_performancetestharness.py
-    - tests\unified\test_performance_targets_testagentstartuptime.py
-    - tests\unified\test_performance_targets_testfirstresponselatency.py
- 3. Extract helper functions:
-    - tests\unified\test_performance_targets_helpers.py (11 helpers)
- 4. Split by feature being tested:
-    - tests\unified\test_performance_targets_feature1.py
-    - tests\unified\test_performance_targets_feature2.py

### tests\e2e\websocket_resilience\test_6_rapid_reconnection_flapping.py

- File has 378 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - tests\e2e\websocket_resilience\test_6_rapid_reconnection_flapping_helpers.py (7 helpers)
- 4. Split by feature being tested:
-    - tests\e2e\websocket_resilience\test_6_rapid_reconnection_flapping_feature1.py
-    - tests\e2e\websocket_resilience\test_6_rapid_reconnection_flapping_feature2.py

### tests\e2e\test_concurrency_isolation_ORIGINAL_BACKUP.py

- File has 1501 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\e2e\test_concurrency_isolation_ORIGINAL_BACKUP_concurrencytestreport.py
-    - tests\e2e\test_concurrency_isolation_ORIGINAL_BACKUP_concurrencytestenvironment.py
-    - tests\e2e\test_concurrency_isolation_ORIGINAL_BACKUP_concurrenttestorchestrator.py
- 3. Extract helper functions:
-    - tests\e2e\test_concurrency_isolation_ORIGINAL_BACKUP_helpers.py (14 helpers)
- 4. Split by feature being tested:
-    - tests\e2e\test_concurrency_isolation_ORIGINAL_BACKUP_feature1.py
-    - tests\e2e\test_concurrency_isolation_ORIGINAL_BACKUP_feature2.py

### app\tests\critical\test_config_environment_detection.py

- File has 335 lines (limit: 300)
- Recommended splitting strategies:
- 1. Split by test categories:
-    - app\tests\critical\test_config_environment_detection_unit.py (unit tests)
-    - app\tests\critical\test_config_environment_detection_integration.py (integration tests)
-    - app\tests\critical\test_config_environment_detection_e2e.py (end-to-end tests)
- 2. Split by test classes:
-    - app\tests\critical\test_config_environment_detection_testenvironmentdetection.py
-    - app\tests\critical\test_config_environment_detection_testconfigurationcreation.py
-    - app\tests\critical\test_config_environment_detection_testwebsocketurlconfiguration.py
- 4. Split by feature being tested:
-    - app\tests\critical\test_config_environment_detection_feature1.py
-    - app\tests\critical\test_config_environment_detection_feature2.py

### app\tests\unit\test_circuit_breaker_core.py

- File has 333 lines (limit: 300)
- Recommended splitting strategies:
- 1. Split by test categories:
-    - app\tests\unit\test_circuit_breaker_core_unit.py (unit tests)
-    - app\tests\unit\test_circuit_breaker_core_integration.py (integration tests)
-    - app\tests\unit\test_circuit_breaker_core_e2e.py (end-to-end tests)
- 2. Split by test classes:
-    - app\tests\unit\test_circuit_breaker_core_testcircuitbreakerinitialization.py
-    - app\tests\unit\test_circuit_breaker_core_testcircuitstatetransitions.py
-    - app\tests\unit\test_circuit_breaker_core_testoperationexecution.py
- 3. Extract helper functions:
-    - app\tests\unit\test_circuit_breaker_core_helpers.py (5 helpers)
- 4. Split by feature being tested:
-    - app\tests\unit\test_circuit_breaker_core_feature1.py
-    - app\tests\unit\test_circuit_breaker_core_feature2.py

### tests\unified\e2e\test_agent_pipeline_real.py

- File has 526 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\e2e\test_agent_pipeline_real_agentpipelineexecutiontester.py
-    - tests\unified\e2e\test_agent_pipeline_real_agentpipelineperformancetester.py
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_agent_pipeline_real_feature1.py
-    - tests\unified\e2e\test_agent_pipeline_real_feature2.py

### app\tests\integration\test_system_startup_integration.py

- File has 316 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - app\tests\integration\test_system_startup_integration_helpers.py (8 helpers)
- 4. Split by feature being tested:
-    - app\tests\integration\test_system_startup_integration_feature1.py
-    - app\tests\integration\test_system_startup_integration_feature2.py

### app\tests\unit\test_rate_limiter_unit.py

- File has 594 lines (limit: 300)
- Recommended splitting strategies:
- 1. Split by test categories:
-    - app\tests\unit\test_rate_limiter_unit_unit.py (unit tests)
-    - app\tests\unit\test_rate_limiter_unit_integration.py (integration tests)
-    - app\tests\unit\test_rate_limiter_unit_e2e.py (end-to-end tests)
- 2. Split by test classes:
-    - app\tests\unit\test_rate_limiter_unit_testratelimitchecking.py
-    - app\tests\unit\test_rate_limiter_unit_testusagekeygeneration.py
-    - app\tests\unit\test_rate_limiter_unit_testusagetracking.py
- 3. Extract helper functions:
-    - app\tests\unit\test_rate_limiter_unit_helpers.py (6 helpers)
- 4. Split by feature being tested:
-    - app\tests\unit\test_rate_limiter_unit_feature1.py
-    - app\tests\unit\test_rate_limiter_unit_feature2.py

### tests\unified\test_import_integrity.py

- File has 438 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - tests\unified\test_import_integrity_helpers.py (10 helpers)
- 4. Split by feature being tested:
-    - tests\unified\test_import_integrity_feature1.py
-    - tests\unified\test_import_integrity_feature2.py

### tests\unified\e2e\test_agent_context_accumulation.py

- File has 440 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\e2e\test_agent_context_accumulation_agentcontextaccumulationtester.py
-    - tests\unified\e2e\test_agent_context_accumulation_testagentcontextaccumulation.py
-    - tests\unified\e2e\test_agent_context_accumulation_testcriticalcontextscenarios.py
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_agent_context_accumulation_feature1.py
-    - tests\unified\e2e\test_agent_context_accumulation_feature2.py

### app\tests\integration\test_first_time_user_permissions.py

- File has 362 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - app\tests\integration\test_first_time_user_permissions_feature1.py
-    - app\tests\integration\test_first_time_user_permissions_feature2.py

### app\tests\services\test_corpus_service_comprehensive.py

- File has 432 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\services\test_corpus_service_comprehensive_testcorpusdocumentindexing.py
-    - app\tests\services\test_corpus_service_comprehensive_testcorpussearchrelevance.py
-    - app\tests\services\test_corpus_service_comprehensive_testcorpusmanagement.py
- 4. Split by feature being tested:
-    - app\tests\services\test_corpus_service_comprehensive_feature1.py
-    - app\tests\services\test_corpus_service_comprehensive_feature2.py

### app\tests\startup\test_staged_health_monitor.py

- File has 514 lines (limit: 300)
- Recommended splitting strategies:
- 1. Split by test categories:
-    - app\tests\startup\test_staged_health_monitor_unit.py (unit tests)
-    - app\tests\startup\test_staged_health_monitor_integration.py (integration tests)
-    - app\tests\startup\test_staged_health_monitor_e2e.py (end-to-end tests)
- 2. Split by test classes:
-    - app\tests\startup\test_staged_health_monitor_testhealthstage.py
-    - app\tests\startup\test_staged_health_monitor_testserviceconfig.py
-    - app\tests\startup\test_staged_health_monitor_testhealthcheckresult.py
- 4. Split by feature being tested:
-    - app\tests\startup\test_staged_health_monitor_feature1.py
-    - app\tests\startup\test_staged_health_monitor_feature2.py

### auth_service\tests\utils\test_client.py

- File has 303 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - auth_service\tests\utils\test_client_authtestclient.py
-    - auth_service\tests\utils\test_client_mockauthtestclient.py
- 3. Extract helper functions:
-    - auth_service\tests\utils\test_client_helpers.py (17 helpers)
- 4. Split by feature being tested:
-    - auth_service\tests\utils\test_client_feature1.py
-    - auth_service\tests\utils\test_client_feature2.py

### app\tests\critical\test_config_loader_core.py

- File has 403 lines (limit: 300)
- Recommended splitting strategies:
- 1. Split by test categories:
-    - app\tests\critical\test_config_loader_core_unit.py (unit tests)
-    - app\tests\critical\test_config_loader_core_integration.py (integration tests)
-    - app\tests\critical\test_config_loader_core_e2e.py (end-to-end tests)
- 2. Split by test classes:
-    - app\tests\critical\test_config_loader_core_testenvironmentvariableloading.py
-    - app\tests\critical\test_config_loader_core_testclickhouseconfiguration.py
-    - app\tests\critical\test_config_loader_core_testllmconfigurationloading.py
- 4. Split by feature being tested:
-    - app\tests\critical\test_config_loader_core_feature1.py
-    - app\tests\critical\test_config_loader_core_feature2.py

### tests\unified\e2e\rate_limiting_advanced.py

- File has 333 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\e2e\rate_limiting_advanced_apiratelimittester.py
-    - tests\unified\e2e\rate_limiting_advanced_websocketratelimittester.py
-    - tests\unified\e2e\rate_limiting_advanced_agentthrottletester.py
- 3. Extract helper functions:
-    - tests\unified\e2e\rate_limiting_advanced_helpers.py (6 helpers)
- 4. Split by feature being tested:
-    - tests\unified\e2e\rate_limiting_advanced_feature1.py
-    - tests\unified\e2e\rate_limiting_advanced_feature2.py

### app\tests\integration\test_unified_auth_service.py

- File has 520 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\integration\test_unified_auth_service_unifiedauthtestmanager.py
-    - app\tests\integration\test_unified_auth_service_testunifiedauthflow.py
-    - app\tests\integration\test_unified_auth_service_testunifiedautherrorscenarios.py
- 4. Split by feature being tested:
-    - app\tests\integration\test_unified_auth_service_feature1.py
-    - app\tests\integration\test_unified_auth_service_feature2.py

### tests\e2e\websocket_resilience\test_1_reconnection_preserves_context.py

- File has 814 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - tests\e2e\websocket_resilience\test_1_reconnection_preserves_context_helpers.py (8 helpers)
- 4. Split by feature being tested:
-    - tests\e2e\websocket_resilience\test_1_reconnection_preserves_context_feature1.py
-    - tests\e2e\websocket_resilience\test_1_reconnection_preserves_context_feature2.py

### tests\e2e\test_rapid_message_succession.py

- File has 1408 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\e2e\test_rapid_message_succession_testsequentialmessageprocessingrapidsuccession.py
-    - tests\e2e\test_rapid_message_succession_testburstmessageidempotencyenforcement.py
-    - tests\e2e\test_rapid_message_succession_testqueueoverflowbackpressurehandling.py
- 3. Extract helper functions:
-    - tests\e2e\test_rapid_message_succession_helpers.py (11 helpers)
- 4. Split by feature being tested:
-    - tests\e2e\test_rapid_message_succession_feature1.py
-    - tests\e2e\test_rapid_message_succession_feature2.py

### app\tests\core\test_data_validation_comprehensive.py

- File has 343 lines (limit: 300)
- Recommended splitting strategies:
- 1. Split by test categories:
-    - app\tests\core\test_data_validation_comprehensive_unit.py (unit tests)
-    - app\tests\core\test_data_validation_comprehensive_integration.py (integration tests)
-    - app\tests\core\test_data_validation_comprehensive_e2e.py (end-to-end tests)
- 4. Split by feature being tested:
-    - app\tests\core\test_data_validation_comprehensive_feature1.py
-    - app\tests\core\test_data_validation_comprehensive_feature2.py

### app\tests\integration\test_concurrent_user_auth_load.py

- File has 432 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\integration\test_concurrent_user_auth_load_concurrentauthloadtest.py
-    - app\tests\integration\test_concurrent_user_auth_load_testconcurrentuserauthload.py
- 3. Extract helper functions:
-    - app\tests\integration\test_concurrent_user_auth_load_helpers.py (4 helpers)
- 4. Split by feature being tested:
-    - app\tests\integration\test_concurrent_user_auth_load_feature1.py
-    - app\tests\integration\test_concurrent_user_auth_load_feature2.py

### tests\unified\websocket\test_message_ordering.py

- File has 545 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\websocket\test_message_ordering_orderingtestmessage.py
-    - tests\unified\websocket\test_message_ordering_websocketorderingtester.py
-    - tests\unified\websocket\test_message_ordering_testwebsocketmessageordering.py
- 3. Extract helper functions:
-    - tests\unified\websocket\test_message_ordering_helpers.py (5 helpers)
- 4. Split by feature being tested:
-    - tests\unified\websocket\test_message_ordering_feature1.py
-    - tests\unified\websocket\test_message_ordering_feature2.py

### app\tests\e2e\test_validation_summary.py

- File has 339 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - app\tests\e2e\test_validation_summary_helpers.py (23 helpers)
- 4. Split by feature being tested:
-    - app\tests\e2e\test_validation_summary_feature1.py
-    - app\tests\e2e\test_validation_summary_feature2.py

### app\tests\e2e\test_thread_agent_integration.py

- File has 425 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\e2e\test_thread_agent_integration_threadagentworkflowtests.py
-    - app\tests\e2e\test_thread_agent_integration_threaddataintegritytests.py
-    - app\tests\e2e\test_thread_agent_integration_threaderrorhandlingtests.py
- 4. Split by feature being tested:
-    - app\tests\e2e\test_thread_agent_integration_feature1.py
-    - app\tests\e2e\test_thread_agent_integration_feature2.py

### tests\unified\test_error_recovery.py

- File has 468 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\test_error_recovery_recoverytestresult.py
-    - tests\unified\test_error_recovery_testservicecrashrecovery.py
-    - tests\unified\test_error_recovery_testwebsocketreconnection.py
- 3. Extract helper functions:
-    - tests\unified\test_error_recovery_helpers.py (12 helpers)
- 4. Split by feature being tested:
-    - tests\unified\test_error_recovery_feature1.py
-    - tests\unified\test_error_recovery_feature2.py

### app\tests\unit\test_async_rate_limiter.py

- File has 342 lines (limit: 300)
- Recommended splitting strategies:
- 1. Split by test categories:
-    - app\tests\unit\test_async_rate_limiter_unit.py (unit tests)
-    - app\tests\unit\test_async_rate_limiter_integration.py (integration tests)
-    - app\tests\unit\test_async_rate_limiter_e2e.py (end-to-end tests)
- 2. Split by test classes:
-    - app\tests\unit\test_async_rate_limiter_testratelimiterinitialization.py
-    - app\tests\unit\test_async_rate_limiter_testcallacquisition.py
-    - app\tests\unit\test_async_rate_limiter_testtimewindowbehavior.py
- 3. Extract helper functions:
-    - app\tests\unit\test_async_rate_limiter_helpers.py (5 helpers)
- 4. Split by feature being tested:
-    - app\tests\unit\test_async_rate_limiter_feature1.py
-    - app\tests\unit\test_async_rate_limiter_feature2.py

### app\tests\services\test_supply_research_service_price_calculations.py

- File has 305 lines (limit: 300)
- Recommended splitting strategies:
- 1. Split by test categories:
-    - app\tests\services\test_supply_research_service_price_calculations_unit.py (unit tests)
-    - app\tests\services\test_supply_research_service_price_calculations_integration.py (integration tests)
-    - app\tests\services\test_supply_research_service_price_calculations_e2e.py (end-to-end tests)
- 2. Split by test classes:
-    - app\tests\services\test_supply_research_service_price_calculations_testpricechangecalculations.py
-    - app\tests\services\test_supply_research_service_price_calculations_testprovidercomparison.py
-    - app\tests\services\test_supply_research_service_price_calculations_testanomalydetection.py
- 3. Extract helper functions:
-    - app\tests\services\test_supply_research_service_price_calculations_helpers.py (13 helpers)
- 4. Split by feature being tested:
-    - app\tests\services\test_supply_research_service_price_calculations_feature1.py
-    - app\tests\services\test_supply_research_service_price_calculations_feature2.py

### tests\unified\e2e\run_all_e2e_tests.py

- File has 341 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\e2e\run_all_e2e_tests_testfileresult.py
-    - tests\unified\e2e\run_all_e2e_tests_e2etestsummary.py
-    - tests\unified\e2e\run_all_e2e_tests_e2etestdiscovery.py
- 3. Extract helper functions:
-    - tests\unified\e2e\run_all_e2e_tests_helpers.py (13 helpers)
- 4. Split by feature being tested:
-    - tests\unified\e2e\run_all_e2e_tests_feature1.py
-    - tests\unified\e2e\run_all_e2e_tests_feature2.py

### app\tests\examples\test_pattern_examples.py

- File has 413 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\examples\test_pattern_examples_testagentserviceunit.py
-    - app\tests\examples\test_pattern_examples_testagentserviceintegration.py
-    - app\tests\examples\test_pattern_examples_testagentperformance.py
- 4. Split by feature being tested:
-    - app\tests\examples\test_pattern_examples_feature1.py
-    - app\tests\examples\test_pattern_examples_feature2.py

### tests\unified\e2e\test_microservice_isolation_validation.py

- File has 994 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - tests\unified\e2e\test_microservice_isolation_validation_helpers.py (7 helpers)
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_microservice_isolation_validation_feature1.py
-    - tests\unified\e2e\test_microservice_isolation_validation_feature2.py

### tests\unified\test_state_persistence.py

- File has 406 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - tests\unified\test_state_persistence_helpers.py (16 helpers)
- 4. Split by feature being tested:
-    - tests\unified\test_state_persistence_feature1.py
-    - tests\unified\test_state_persistence_feature2.py

### app\tests\integration\test_first_time_user_critical_journey.py

- File has 810 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - app\tests\integration\test_first_time_user_critical_journey_feature1.py
-    - app\tests\integration\test_first_time_user_critical_journey_feature2.py

### tests\unified\test_network_resilience.py

- File has 305 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\test_network_resilience_testnetworkpartitionhandling.py
-    - tests\unified\test_network_resilience_testpacketlossrecovery.py
-    - tests\unified\test_network_resilience_testdnsfailurehandling.py
- 4. Split by feature being tested:
-    - tests\unified\test_network_resilience_feature1.py
-    - tests\unified\test_network_resilience_feature2.py

### tests\unified\e2e\test_websocket_event_propagation_unified.py

- File has 392 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\e2e\test_websocket_event_propagation_unified_eventpropagationtester.py
-    - tests\unified\e2e\test_websocket_event_propagation_unified_testdatafactory.py
- 3. Extract helper functions:
-    - tests\unified\e2e\test_websocket_event_propagation_unified_helpers.py (5 helpers)
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_websocket_event_propagation_unified_feature1.py
-    - tests\unified\e2e\test_websocket_event_propagation_unified_feature2.py

### app\tests\agents\test_llm_agent_e2e_integration.py

- File has 316 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - app\tests\agents\test_llm_agent_e2e_integration_helpers.py (9 helpers)
- 4. Split by feature being tested:
-    - app\tests\agents\test_llm_agent_e2e_integration_feature1.py
-    - app\tests\agents\test_llm_agent_e2e_integration_feature2.py

### tests\test_example_message_integration_final.py

- File has 594 lines (limit: 300)
- Recommended splitting strategies:
- 1. Split by test categories:
-    - tests\test_example_message_integration_final_unit.py (unit tests)
-    - tests\test_example_message_integration_final_integration.py (integration tests)
-    - tests\test_example_message_integration_final_e2e.py (end-to-end tests)
- 2. Split by test classes:
-    - tests\test_example_message_integration_final_testcompleteintegrationflow.py
-    - tests\test_example_message_integration_final_testproductionreadinessvalidation.py
- 4. Split by feature being tested:
-    - tests\test_example_message_integration_final_feature1.py
-    - tests\test_example_message_integration_final_feature2.py

### tests\unified\e2e\test_disaster_recovery.py

- File has 468 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\e2e\test_disaster_recovery_disasterrecoverytestsuite.py
-    - tests\unified\e2e\test_disaster_recovery_testdisasterrecovery.py
-    - tests\unified\e2e\test_disaster_recovery_testdisasterrecoveryperformance.py
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_disaster_recovery_feature1.py
-    - tests\unified\e2e\test_disaster_recovery_feature2.py

### tests\unified\test_frontend_backend_api.py

- File has 839 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\test_frontend_backend_api_frontendbackendapitester.py
-    - tests\unified\test_frontend_backend_api_testfrontendbackendapicommunication.py
-    - tests\unified\test_frontend_backend_api_testcomprehensivefrontendbackendintegration.py
- 4. Split by feature being tested:
-    - tests\unified\test_frontend_backend_api_feature1.py
-    - tests\unified\test_frontend_backend_api_feature2.py

### tests\unified\e2e\test_rate_limiting_unified_real.py

- File has 659 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_rate_limiting_unified_real_feature1.py
-    - tests\unified\e2e\test_rate_limiting_unified_real_feature2.py

### app\tests\websocket\test_websocket_server_to_client_types.py

- File has 396 lines (limit: 300)
- Recommended splitting strategies:
- 1. Split by test categories:
-    - app\tests\websocket\test_websocket_server_to_client_types_unit.py (unit tests)
-    - app\tests\websocket\test_websocket_server_to_client_types_integration.py (integration tests)
-    - app\tests\websocket\test_websocket_server_to_client_types_e2e.py (end-to-end tests)
- 2. Split by test classes:
-    - app\tests\websocket\test_websocket_server_to_client_types_testservertoclientmessagetypes.py
-    - app\tests\websocket\test_websocket_server_to_client_types_testservermessagebatchvalidation.py
- 4. Split by feature being tested:
-    - app\tests\websocket\test_websocket_server_to_client_types_feature1.py
-    - app\tests\websocket\test_websocket_server_to_client_types_feature2.py

### tests\integration\test_cross_service_config.py

- File has 394 lines (limit: 300)
- Recommended splitting strategies:
- 1. Split by test categories:
-    - tests\integration\test_cross_service_config_unit.py (unit tests)
-    - tests\integration\test_cross_service_config_integration.py (integration tests)
-    - tests\integration\test_cross_service_config_e2e.py (end-to-end tests)
- 2. Split by test classes:
-    - tests\integration\test_cross_service_config_crossservicetestconfig.py
-    - tests\integration\test_cross_service_config_crossservicetesthelpers.py
- 3. Extract helper functions:
-    - tests\integration\test_cross_service_config_helpers.py (8 helpers)
- 4. Split by feature being tested:
-    - tests\integration\test_cross_service_config_feature1.py
-    - tests\integration\test_cross_service_config_feature2.py

### tests\unified\websocket\test_message_queue_basic.py

- File has 647 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\websocket\test_message_queue_basic_messagequeuetestharness.py
-    - tests\unified\websocket\test_message_queue_basic_testmessagequeuepersistence.py
-    - tests\unified\websocket\test_message_queue_basic_testqueueflushonreconnection.py
- 3. Extract helper functions:
-    - tests\unified\websocket\test_message_queue_basic_helpers.py (13 helpers)
- 4. Split by feature being tested:
-    - tests\unified\websocket\test_message_queue_basic_feature1.py
-    - tests\unified\websocket\test_message_queue_basic_feature2.py

### tests\unified\e2e\test_corpus_generation_pipeline_integration.py

- File has 479 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\e2e\test_corpus_generation_pipeline_integration_corpustestdata.py
-    - tests\unified\e2e\test_corpus_generation_pipeline_integration_corpusgenerationtester.py
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_corpus_generation_pipeline_integration_feature1.py
-    - tests\unified\e2e\test_corpus_generation_pipeline_integration_feature2.py

### app\tests\integration\test_cache_management_integration.py

- File has 512 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\integration\test_cache_management_integration_testcachewarmingstrategies.py
-    - app\tests\integration\test_cache_management_integration_testcachecoherencydistributed.py
-    - app\tests\integration\test_cache_management_integration_testcachettlmanagement.py
- 3. Extract helper functions:
-    - app\tests\integration\test_cache_management_integration_helpers.py (6 helpers)
- 4. Split by feature being tested:
-    - app\tests\integration\test_cache_management_integration_feature1.py
-    - app\tests\integration\test_cache_management_integration_feature2.py

### test_framework\docker_testing\compose_manager.py

- File has 401 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - test_framework\docker_testing\compose_manager_feature1.py
-    - test_framework\docker_testing\compose_manager_feature2.py

### tests\e2e\test_error_scenarios_comprehensive_e2e.py

- File has 581 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\e2e\test_error_scenarios_comprehensive_e2e_errorscenariotester.py
-    - tests\e2e\test_error_scenarios_comprehensive_e2e_testerrorscenarioscomprehensivee2e.py
- 4. Split by feature being tested:
-    - tests\e2e\test_error_scenarios_comprehensive_e2e_feature1.py
-    - tests\e2e\test_error_scenarios_comprehensive_e2e_feature2.py

### app\tests\core\test_async_edge_cases_error_handling.py

- File has 396 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\core\test_async_edge_cases_error_handling_testerrorcontextintegration.py
-    - app\tests\core\test_async_edge_cases_error_handling_testweakrefbehavior.py
-    - app\tests\core\test_async_edge_cases_error_handling_testconcurrencyedgecases.py
- 3. Extract helper functions:
-    - app\tests\core\test_async_edge_cases_error_handling_helpers.py (4 helpers)
- 4. Split by feature being tested:
-    - app\tests\core\test_async_edge_cases_error_handling_feature1.py
-    - app\tests\core\test_async_edge_cases_error_handling_feature2.py

### auth_service\tests\test_token_validation.py

- File has 486 lines (limit: 300)
- Recommended splitting strategies:
- 1. Split by test categories:
-    - auth_service\tests\test_token_validation_unit.py (unit tests)
-    - auth_service\tests\test_token_validation_integration.py (integration tests)
-    - auth_service\tests\test_token_validation_e2e.py (end-to-end tests)
- 2. Split by test classes:
-    - auth_service\tests\test_token_validation_testjwttokengeneration.py
-    - auth_service\tests\test_token_validation_testjwttokenvalidation.py
-    - auth_service\tests\test_token_validation_testjwttokenexpiry.py
- 3. Extract helper functions:
-    - auth_service\tests\test_token_validation_helpers.py (9 helpers)
- 4. Split by feature being tested:
-    - auth_service\tests\test_token_validation_feature1.py
-    - auth_service\tests\test_token_validation_feature2.py

### tests\unified\e2e\test_user_message_agent_pipeline.py

- File has 331 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\e2e\test_user_message_agent_pipeline_usermessagepipelinetester.py
-    - tests\unified\e2e\test_user_message_agent_pipeline_testusermessageagentpipeline.py
-    - tests\unified\e2e\test_user_message_agent_pipeline_testcriticalpipelinescenarios.py
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_user_message_agent_pipeline_feature1.py
-    - tests\unified\e2e\test_user_message_agent_pipeline_feature2.py

### tests\unified\e2e\test_agent_resource_cleanup_integration.py

- File has 399 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\e2e\test_agent_resource_cleanup_integration_concurrentresourcetester.py
-    - tests\unified\e2e\test_agent_resource_cleanup_integration_testagentresourcecleanupintegration.py
- 3. Extract helper functions:
-    - tests\unified\e2e\test_agent_resource_cleanup_integration_helpers.py (6 helpers)
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_agent_resource_cleanup_integration_feature1.py
-    - tests\unified\e2e\test_agent_resource_cleanup_integration_feature2.py

### tests\unified\e2e\test_websocket_comprehensive_e2e.py

- File has 345 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\e2e\test_websocket_comprehensive_e2e_websockete2etester.py
-    - tests\unified\e2e\test_websocket_comprehensive_e2e_testwebsocketcomprehensivee2e.py
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_websocket_comprehensive_e2e_feature1.py
-    - tests\unified\e2e\test_websocket_comprehensive_e2e_feature2.py

### app\tests\integration\test_helpers\user_flow_base.py

- File has 301 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - app\tests\integration\test_helpers\user_flow_base_feature1.py
-    - app\tests\integration\test_helpers\user_flow_base_feature2.py

### tests\unified\e2e\test_websocket_auth_integration.py

- File has 695 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\e2e\test_websocket_auth_integration_websocketauthtester.py
-    - tests\unified\e2e\test_websocket_auth_integration_tokenexpirytester.py
-    - tests\unified\e2e\test_websocket_auth_integration_messagepreservationtester.py
- 3. Extract helper functions:
-    - tests\unified\e2e\test_websocket_auth_integration_helpers.py (8 helpers)
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_websocket_auth_integration_feature1.py
-    - tests\unified\e2e\test_websocket_auth_integration_feature2.py

### app\tests\unified_system\test_thread_management.py

- File has 632 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - app\tests\unified_system\test_thread_management_feature1.py
-    - app\tests\unified_system\test_thread_management_feature2.py

### app\tests\services\test_corpus_audit.py

- File has 358 lines (limit: 300)
- Recommended splitting strategies:
- 1. Split by test categories:
-    - app\tests\services\test_corpus_audit_unit.py (unit tests)
-    - app\tests\services\test_corpus_audit_integration.py (integration tests)
-    - app\tests\services\test_corpus_audit_e2e.py (end-to-end tests)
- 2. Split by test classes:
-    - app\tests\services\test_corpus_audit_testcorpusauditrepository.py
-    - app\tests\services\test_corpus_audit_testcorpusauditlogger.py
-    - app\tests\services\test_corpus_audit_testaudittimer.py
- 4. Split by feature being tested:
-    - app\tests\services\test_corpus_audit_feature1.py
-    - app\tests\services\test_corpus_audit_feature2.py

### tests\unified\e2e\dev_launcher_test_fixtures.py

- File has 313 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - tests\unified\e2e\dev_launcher_test_fixtures_helpers.py (21 helpers)
- 4. Split by feature being tested:
-    - tests\unified\e2e\dev_launcher_test_fixtures_feature1.py
-    - tests\unified\e2e\dev_launcher_test_fixtures_feature2.py

### app\tests\integration\test_agent_state_persistence_recovery.py

- File has 519 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - app\tests\integration\test_agent_state_persistence_recovery_feature1.py
-    - app\tests\integration\test_agent_state_persistence_recovery_feature2.py

### app\tests\websocket\test_websocket_resilience.py

- File has 462 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\websocket\test_websocket_resilience_testwebsocketconnectionresilience.py
-    - app\tests\websocket\test_websocket_resilience_testwebsocketnetworkinstability.py
-    - app\tests\websocket\test_websocket_resilience_testwebsocketerrorrecovery.py
- 4. Split by feature being tested:
-    - app\tests\websocket\test_websocket_resilience_feature1.py
-    - app\tests\websocket\test_websocket_resilience_feature2.py

### tests\unified\e2e\test_cache_coherence.py

- File has 301 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_cache_coherence_feature1.py
-    - tests\unified\e2e\test_cache_coherence_feature2.py

### tests\unified\e2e\test_performance_sla_validation.py

- File has 312 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\e2e\test_performance_sla_validation_performancetestexecutor.py
-    - tests\unified\e2e\test_performance_sla_validation_testperformancesla.py
-    - tests\unified\e2e\test_performance_sla_validation_testbusinessvaluevalidation.py
- 3. Extract helper functions:
-    - tests\unified\e2e\test_performance_sla_validation_helpers.py (10 helpers)
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_performance_sla_validation_feature1.py
-    - tests\unified\e2e\test_performance_sla_validation_feature2.py

### app\tests\integration\user_flows\test_mid_tier_flows.py

- File has 311 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - app\tests\integration\user_flows\test_mid_tier_flows_feature1.py
-    - app\tests\integration\user_flows\test_mid_tier_flows_feature2.py

### app\tests\unified_system\test_circuit_breakers.py

- File has 491 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - app\tests\unified_system\test_circuit_breakers_helpers.py (4 helpers)
- 4. Split by feature being tested:
-    - app\tests\unified_system\test_circuit_breakers_feature1.py
-    - app\tests\unified_system\test_circuit_breakers_feature2.py

### test_framework\performance_optimizer.py

- File has 521 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - test_framework\performance_optimizer_helpers.py (23 helpers)
- 4. Split by feature being tested:
-    - test_framework\performance_optimizer_feature1.py
-    - test_framework\performance_optimizer_feature2.py

### app\tests\integration\test_user_session_persistence_restart.py

- File has 469 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\integration\test_user_session_persistence_restart_usersessionpersistencetest.py
-    - app\tests\integration\test_user_session_persistence_restart_testusersessionpersistencerestart.py
- 4. Split by feature being tested:
-    - app\tests\integration\test_user_session_persistence_restart_feature1.py
-    - app\tests\integration\test_user_session_persistence_restart_feature2.py

### test_framework\optimized_executor.py

- File has 660 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - test_framework\optimized_executor_testexecutionresult.py
-    - test_framework\optimized_executor_fasttestdatabase.py
-    - test_framework\optimized_executor_smarttestcache.py
- 3. Extract helper functions:
-    - test_framework\optimized_executor_helpers.py (18 helpers)
- 4. Split by feature being tested:
-    - test_framework\optimized_executor_feature1.py
-    - test_framework\optimized_executor_feature2.py

### tests\unified\e2e\test_websocket_ui_timing.py

- File has 416 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_websocket_ui_timing_feature1.py
-    - tests\unified\e2e\test_websocket_ui_timing_feature2.py

### tests\test_example_message_flow_comprehensive.py

- File has 1002 lines (limit: 300)
- Recommended splitting strategies:
- 1. Split by test categories:
-    - tests\test_example_message_flow_comprehensive_unit.py (unit tests)
-    - tests\test_example_message_flow_comprehensive_integration.py (integration tests)
-    - tests\test_example_message_flow_comprehensive_e2e.py (end-to-end tests)
- 2. Split by test classes:
-    - tests\test_example_message_flow_comprehensive_testmessagesequencer.py
-    - tests\test_example_message_flow_comprehensive_testconnectionstatemanager.py
-    - tests\test_example_message_flow_comprehensive_testsessionmanager.py
- 4. Split by feature being tested:
-    - tests\test_example_message_flow_comprehensive_feature1.py
-    - tests\test_example_message_flow_comprehensive_feature2.py

### tests\unified\test_jwt_secret_synchronization.py

- File has 321 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - tests\unified\test_jwt_secret_synchronization_helpers.py (11 helpers)
- 4. Split by feature being tested:
-    - tests\unified\test_jwt_secret_synchronization_feature1.py
-    - tests\unified\test_jwt_secret_synchronization_feature2.py

### tests\unified\websocket\test_basic_messaging.py

- File has 349 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\websocket\test_basic_messaging_basicmessagingtester.py
-    - tests\unified\websocket\test_basic_messaging_testbasicmessagesending.py
-    - tests\unified\websocket\test_basic_messaging_testbasicmessagereceiving.py
- 4. Split by feature being tested:
-    - tests\unified\websocket\test_basic_messaging_feature1.py
-    - tests\unified\websocket\test_basic_messaging_feature2.py

### test_framework\test_parser.py

- File has 408 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - test_framework\test_parser_helpers.py (9 helpers)
- 4. Split by feature being tested:
-    - test_framework\test_parser_feature1.py
-    - test_framework\test_parser_feature2.py

### app\tests\startup\test_startup_diagnostics.py

- File has 448 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\startup\test_startup_diagnostics_teststartupdiagnosticsinit.py
-    - app\tests\startup\test_startup_diagnostics_testsystemerrorcollection.py
-    - app\tests\startup\test_startup_diagnostics_testportconflictchecking.py
- 4. Split by feature being tested:
-    - app\tests\startup\test_startup_diagnostics_feature1.py
-    - app\tests\startup\test_startup_diagnostics_feature2.py

### tests\e2e\test_concurrent_agent_startup.py

- File has 1127 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\e2e\test_concurrent_agent_startup_testuser.py
-    - tests\e2e\test_concurrent_agent_startup_concurrenttestreport.py
-    - tests\e2e\test_concurrent_agent_startup_concurrenttestenvironment.py
- 3. Extract helper functions:
-    - tests\e2e\test_concurrent_agent_startup_helpers.py (9 helpers)
- 4. Split by feature being tested:
-    - tests\e2e\test_concurrent_agent_startup_feature1.py
-    - tests\e2e\test_concurrent_agent_startup_feature2.py

### tests\e2e\test_helpers\high_volume_server.py

- File has 513 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - tests\e2e\test_helpers\high_volume_server_feature1.py
-    - tests\e2e\test_helpers\high_volume_server_feature2.py

### tests\e2e\test_message_flow_comprehensive_e2e.py

- File has 521 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\e2e\test_message_flow_comprehensive_e2e_messageflowtester.py
-    - tests\e2e\test_message_flow_comprehensive_e2e_testmessageflowcomprehensivee2e.py
- 4. Split by feature being tested:
-    - tests\e2e\test_message_flow_comprehensive_e2e_feature1.py
-    - tests\e2e\test_message_flow_comprehensive_e2e_feature2.py

### app\tests\startup\test_error_aggregator.py

- File has 369 lines (limit: 300)
- Recommended splitting strategies:
- 1. Split by test categories:
-    - app\tests\startup\test_error_aggregator_unit.py (unit tests)
-    - app\tests\startup\test_error_aggregator_integration.py (integration tests)
-    - app\tests\startup\test_error_aggregator_e2e.py (end-to-end tests)
- 2. Split by test classes:
-    - app\tests\startup\test_error_aggregator_testerroraggregatorinit.py
-    - app\tests\startup\test_error_aggregator_testdatabasesetup.py
-    - app\tests\startup\test_error_aggregator_testerrorrecording.py
- 4. Split by feature being tested:
-    - app\tests\startup\test_error_aggregator_feature1.py
-    - app\tests\startup\test_error_aggregator_feature2.py

### test_framework\test_environment_setup.py

- File has 458 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - test_framework\test_environment_setup_testsession.py
-    - test_framework\test_environment_setup_testenvironmentvalidator.py
-    - test_framework\test_environment_setup_testenvironmentorchestrator.py
- 3. Extract helper functions:
-    - test_framework\test_environment_setup_helpers.py (8 helpers)
- 4. Split by feature being tested:
-    - test_framework\test_environment_setup_feature1.py
-    - test_framework\test_environment_setup_feature2.py

### app\tests\agents\test_triage_sub_agent.py

- File has 500 lines (limit: 300)
- Recommended splitting strategies:
- 1. Split by test categories:
-    - app\tests\agents\test_triage_sub_agent_unit.py (unit tests)
-    - app\tests\agents\test_triage_sub_agent_integration.py (integration tests)
-    - app\tests\agents\test_triage_sub_agent_e2e.py (end-to-end tests)
- 2. Split by test classes:
-    - app\tests\agents\test_triage_sub_agent_testtriagesubagentinitialization.py
-    - app\tests\agents\test_triage_sub_agent_testrequestvalidation.py
-    - app\tests\agents\test_triage_sub_agent_testentityextraction.py
- 4. Split by feature being tested:
-    - app\tests\agents\test_triage_sub_agent_feature1.py
-    - app\tests\agents\test_triage_sub_agent_feature2.py

### app\tests\example_isolated_test.py

- File has 370 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\example_isolated_test_testpostgresqlisolation.py
-    - app\tests\example_isolated_test_testclickhouseisolation.py
-    - app\tests\example_isolated_test_testfullstackisolation.py
- 4. Split by feature being tested:
-    - app\tests\example_isolated_test_feature1.py
-    - app\tests\example_isolated_test_feature2.py

### tests\unified\e2e\test_agent_workflow_tdd_integration.py

- File has 586 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\e2e\test_agent_workflow_tdd_integration_tddtestresult.py
-    - tests\unified\e2e\test_agent_workflow_tdd_integration_agentworkflowtddtester.py
- 3. Extract helper functions:
-    - tests\unified\e2e\test_agent_workflow_tdd_integration_helpers.py (5 helpers)
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_agent_workflow_tdd_integration_feature1.py
-    - tests\unified\e2e\test_agent_workflow_tdd_integration_feature2.py

### app\tests\core\test_type_validation_part4.py

- File has 356 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\core\test_type_validation_part4_testvalidationfunctions.py
-    - app\tests\core\test_type_validation_part4_testedgecases.py
- 3. Extract helper functions:
-    - app\tests\core\test_type_validation_part4_helpers.py (31 helpers)
- 4. Split by feature being tested:
-    - app\tests\core\test_type_validation_part4_feature1.py
-    - app\tests\core\test_type_validation_part4_feature2.py

### app\tests\integration\test_metrics_pipeline_integration.py

- File has 350 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - app\tests\integration\test_metrics_pipeline_integration_feature1.py
-    - app\tests\integration\test_metrics_pipeline_integration_feature2.py

### tests\unified\test_agent_startup_load_e2e.py

- File has 344 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\test_agent_startup_load_e2e_corruptedstatetestmanager.py
-    - tests\unified\test_agent_startup_load_e2e_loadtestmanager.py
- 3. Extract helper functions:
-    - tests\unified\test_agent_startup_load_e2e_helpers.py (5 helpers)
- 4. Split by feature being tested:
-    - tests\unified\test_agent_startup_load_e2e_feature1.py
-    - tests\unified\test_agent_startup_load_e2e_feature2.py

### app\tests\unified_system\test_dev_launcher_startup.py

- File has 489 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\unified_system\test_dev_launcher_startup_testdevlauncherstartup.py
-    - app\tests\unified_system\test_dev_launcher_startup_testfullsystemstartupsequence.py
-    - app\tests\unified_system\test_dev_launcher_startup_testservicedependencyresolution.py
- 4. Split by feature being tested:
-    - app\tests\unified_system\test_dev_launcher_startup_feature1.py
-    - app\tests\unified_system\test_dev_launcher_startup_feature2.py

### tests\unified\test_concurrent_agents.py

- File has 332 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\test_concurrent_agents_testconcurrentagentstartup.py
-    - tests\unified\test_concurrent_agents_testagentstateisolation.py
-    - tests\unified\test_concurrent_agents_testconcurrentmessagerouting.py
- 3. Extract helper functions:
-    - tests\unified\test_concurrent_agents_helpers.py (13 helpers)
- 4. Split by feature being tested:
-    - tests\unified\test_concurrent_agents_feature1.py
-    - tests\unified\test_concurrent_agents_feature2.py

### tests\websocket\test_secure_websocket.py

- File has 571 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\websocket\test_secure_websocket_testsecurewebsocketmanager.py
-    - tests\websocket\test_secure_websocket_testsecurewebsocketendpoint.py
-    - tests\websocket\test_secure_websocket_testmemoryleakprevention.py
- 4. Split by feature being tested:
-    - tests\websocket\test_secure_websocket_feature1.py
-    - tests\websocket\test_secure_websocket_feature2.py

### tests\unified\e2e\test_staging_services.py

- File has 308 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\e2e\test_staging_services_teststagingservicehealth.py
-    - tests\unified\e2e\test_staging_services_teststagingwebsocketconnectivity.py
-    - tests\unified\e2e\test_staging_services_teststagingdatabasehealth.py
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_staging_services_feature1.py
-    - tests\unified\e2e\test_staging_services_feature2.py

### tests\unified\websocket\test_state_sync.py

- File has 900 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\websocket\test_state_sync_mocktestusers.py
-    - tests\unified\websocket\test_state_sync_applicationteststate.py
-    - tests\unified\websocket\test_state_sync_websocketstatesynctester.py
- 3. Extract helper functions:
-    - tests\unified\websocket\test_state_sync_helpers.py (10 helpers)
- 4. Split by feature being tested:
-    - tests\unified\websocket\test_state_sync_feature1.py
-    - tests\unified\websocket\test_state_sync_feature2.py

### app\tests\unit\test_compensation_engine_core.py

- File has 372 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - app\tests\unit\test_compensation_engine_core_helpers.py (9 helpers)
- 4. Split by feature being tested:
-    - app\tests\unit\test_compensation_engine_core_feature1.py
-    - app\tests\unit\test_compensation_engine_core_feature2.py

### app\tests\integration\staging\test_staging_database_connection_resilience.py

- File has 353 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - app\tests\integration\staging\test_staging_database_connection_resilience_feature1.py
-    - app\tests\integration\staging\test_staging_database_connection_resilience_feature2.py

### tests\unified\test_agent_pipeline_real.py

- File has 371 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - tests\unified\test_agent_pipeline_real_helpers.py (13 helpers)
- 4. Split by feature being tested:
-    - tests\unified\test_agent_pipeline_real_feature1.py
-    - tests\unified\test_agent_pipeline_real_feature2.py

### tests\unified\test_real_user_signup_login_chat.py

- File has 353 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\test_real_user_signup_login_chat_realuserflowtester.py
-    - tests\unified\test_real_user_signup_login_chat_e2etestmanager.py
- 4. Split by feature being tested:
-    - tests\unified\test_real_user_signup_login_chat_feature1.py
-    - tests\unified\test_real_user_signup_login_chat_feature2.py

### tests\e2e\resource_isolation\test_performance_isolation.py

- File has 334 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - tests\e2e\resource_isolation\test_performance_isolation_feature1.py
-    - tests\e2e\resource_isolation\test_performance_isolation_feature2.py

### app\tests\e2e\test_thread_error_handling.py

- File has 420 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\e2e\test_thread_error_handling_threaddatabaseerrortests.py
-    - app\tests\e2e\test_thread_error_handling_threadstateerrortests.py
-    - app\tests\e2e\test_thread_error_handling_threadconcurrencyerrortests.py
- 4. Split by feature being tested:
-    - app\tests\e2e\test_thread_error_handling_feature1.py
-    - app\tests\e2e\test_thread_error_handling_feature2.py

### app\tests\e2e\test_websocket_integration.py

- File has 485 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\e2e\test_websocket_integration_testwebsocketconnection.py
-    - app\tests\e2e\test_websocket_integration_testwebsocketmessaging.py
-    - app\tests\e2e\test_websocket_integration_testwebsocketerrorhandling.py
- 4. Split by feature being tested:
-    - app\tests\e2e\test_websocket_integration_feature1.py
-    - app\tests\e2e\test_websocket_integration_feature2.py

### app\tests\integration\test_logging_audit_integration.py

- File has 433 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - app\tests\integration\test_logging_audit_integration_feature1.py
-    - app\tests\integration\test_logging_audit_integration_feature2.py

### app\tests\integration\test_message_flow_routing.py

- File has 574 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\integration\test_message_flow_routing_testwebsocketmessagerouting.py
-    - app\tests\integration\test_message_flow_routing_testroutingerrorscenarios.py
-    - app\tests\integration\test_message_flow_routing_testroutingperformance.py
- 4. Split by feature being tested:
-    - app\tests\integration\test_message_flow_routing_feature1.py
-    - app\tests\integration\test_message_flow_routing_feature2.py

### test_framework\smart_cache.py

- File has 388 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - test_framework\smart_cache_helpers.py (14 helpers)
- 4. Split by feature being tested:
-    - test_framework\smart_cache_feature1.py
-    - test_framework\smart_cache_feature2.py

### app\tests\core\test_fallback_coordinator_integration.py

- File has 326 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\core\test_fallback_coordinator_integration_testfallbackcoordinatorexecution.py
-    - app\tests\core\test_fallback_coordinator_integration_testfallbackcoordinatorintegration.py
- 4. Split by feature being tested:
-    - app\tests\core\test_fallback_coordinator_integration_feature1.py
-    - app\tests\core\test_fallback_coordinator_integration_feature2.py

### tests\unified\test_latency_targets.py

- File has 319 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\test_latency_targets_testfirstbytetime.py
-    - tests\unified\test_latency_targets_testwebsocketlatency.py
-    - tests\unified\test_latency_targets_testauthresponsetime.py
- 3. Extract helper functions:
-    - tests\unified\test_latency_targets_helpers.py (16 helpers)
- 4. Split by feature being tested:
-    - tests\unified\test_latency_targets_feature1.py
-    - tests\unified\test_latency_targets_feature2.py

### tests\unified\e2e\test_agent_context_isolation_integration.py

- File has 320 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_agent_context_isolation_integration_feature1.py
-    - tests\unified\e2e\test_agent_context_isolation_integration_feature2.py

### tests\unified\test_resource_usage.py

- File has 322 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\test_resource_usage_databaseconnectiontester.py
-    - tests\unified\test_resource_usage_testresourceusage.py
- 3. Extract helper functions:
-    - tests\unified\test_resource_usage_helpers.py (8 helpers)
- 4. Split by feature being tested:
-    - tests\unified\test_resource_usage_feature1.py
-    - tests\unified\test_resource_usage_feature2.py

### app\tests\websocket\test_websocket_client_to_server_types.py

- File has 313 lines (limit: 300)
- Recommended splitting strategies:
- 1. Split by test categories:
-    - app\tests\websocket\test_websocket_client_to_server_types_unit.py (unit tests)
-    - app\tests\websocket\test_websocket_client_to_server_types_integration.py (integration tests)
-    - app\tests\websocket\test_websocket_client_to_server_types_e2e.py (end-to-end tests)
- 2. Split by test classes:
-    - app\tests\websocket\test_websocket_client_to_server_types_testclienttoservermessagetypes.py
-    - app\tests\websocket\test_websocket_client_to_server_types_testclientmessagebatchvalidation.py
- 4. Split by feature being tested:
-    - app\tests\websocket\test_websocket_client_to_server_types_feature1.py
-    - app\tests\websocket\test_websocket_client_to_server_types_feature2.py

### app\tests\unified_system\test_service_recovery.py

- File has 609 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\unified_system\test_service_recovery_testservicerecoverybase.py
-    - app\tests\unified_system\test_service_recovery_teststartupfailurerecovery.py
-    - app\tests\unified_system\test_service_recovery_testindividualservicerestart.py
- 4. Split by feature being tested:
-    - app\tests\unified_system\test_service_recovery_feature1.py
-    - app\tests\unified_system\test_service_recovery_feature2.py

### tests\unified\e2e\dev_mode_integration_utils.py

- File has 669 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\e2e\dev_mode_integration_utils_testmode.py
-    - tests\unified\e2e\dev_mode_integration_utils_testmetrics.py
-    - tests\unified\e2e\dev_mode_integration_utils_corstesthelper.py
- 3. Extract helper functions:
-    - tests\unified\e2e\dev_mode_integration_utils_helpers.py (17 helpers)
- 4. Split by feature being tested:
-    - tests\unified\e2e\dev_mode_integration_utils_feature1.py
-    - tests\unified\e2e\dev_mode_integration_utils_feature2.py

### app\tests\unified_system\test_jwt_flow.py

- File has 411 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\unified_system\test_jwt_flow_jwttesthelper.py
-    - app\tests\unified_system\test_jwt_flow_testjwtcreationandsigning.py
-    - app\tests\unified_system\test_jwt_flow_testcrossservicejwtvalidation.py
- 3. Extract helper functions:
-    - app\tests\unified_system\test_jwt_flow_helpers.py (6 helpers)
- 4. Split by feature being tested:
-    - app\tests\unified_system\test_jwt_flow_feature1.py
-    - app\tests\unified_system\test_jwt_flow_feature2.py

### app\tests\unit\test_websocket_ghost_connections.py

- File has 334 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - app\tests\unit\test_websocket_ghost_connections_helpers.py (4 helpers)
- 4. Split by feature being tested:
-    - app\tests\unit\test_websocket_ghost_connections_feature1.py
-    - app\tests\unit\test_websocket_ghost_connections_feature2.py

### tests\unified\e2e\test_agent_state_sync_integration.py

- File has 431 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_agent_state_sync_integration_feature1.py
-    - tests\unified\e2e\test_agent_state_sync_integration_feature2.py

### tests\unified\websocket\test_websocket_service_discovery.py

- File has 707 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\websocket\test_websocket_service_discovery_websocketservicediscoverytester.py
-    - tests\unified\websocket\test_websocket_service_discovery_testbackendservicediscovery.py
-    - tests\unified\websocket\test_websocket_service_discovery_testfrontendconfigdiscovery.py
- 3. Extract helper functions:
-    - tests\unified\websocket\test_websocket_service_discovery_helpers.py (11 helpers)
- 4. Split by feature being tested:
-    - tests\unified\websocket\test_websocket_service_discovery_feature1.py
-    - tests\unified\websocket\test_websocket_service_discovery_feature2.py

### app\tests\seed_data_manager.py

- File has 490 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - app\tests\seed_data_manager_helpers.py (12 helpers)
- 4. Split by feature being tested:
-    - app\tests\seed_data_manager_feature1.py
-    - app\tests\seed_data_manager_feature2.py

### tests\unified\test_auth_service_health_check_integration.py

- File has 326 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\test_auth_service_health_check_integration_concurrentloadtester.py
-    - tests\unified\test_auth_service_health_check_integration_testauthservicehealthcheckintegration.py
- 4. Split by feature being tested:
-    - tests\unified\test_auth_service_health_check_integration_feature1.py
-    - tests\unified\test_auth_service_health_check_integration_feature2.py

### app\tests\unified_system\test_database_sync.py

- File has 465 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - app\tests\unified_system\test_database_sync_feature1.py
-    - app\tests\unified_system\test_database_sync_feature2.py

### tests\unified\e2e\test_production_data_e2e_real_llm.py

- File has 568 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\e2e\test_production_data_e2e_real_llm_testproductiondatae2erealllm.py
-    - tests\unified\e2e\test_production_data_e2e_real_llm_productiontestexecutor.py
- 3. Extract helper functions:
-    - tests\unified\e2e\test_production_data_e2e_real_llm_helpers.py (12 helpers)
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_production_data_e2e_real_llm_feature1.py
-    - tests\unified\e2e\test_production_data_e2e_real_llm_feature2.py

### app\tests\integration\test_first_message_streaming.py

- File has 339 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - app\tests\integration\test_first_message_streaming_feature1.py
-    - app\tests\integration\test_first_message_streaming_feature2.py

### tests\test_example_message_performance.py

- File has 575 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\test_example_message_performance_testperformancebenchmarks.py
-    - tests\test_example_message_performance_testscalabilitylimits.py
-    - tests\test_example_message_performance_teststresstests.py
- 4. Split by feature being tested:
-    - tests\test_example_message_performance_feature1.py
-    - tests\test_example_message_performance_feature2.py

### app\tests\integration\test_quality_gate_pipeline_integration.py

- File has 495 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - app\tests\integration\test_quality_gate_pipeline_integration_feature1.py
-    - app\tests\integration\test_quality_gate_pipeline_integration_feature2.py

### test_framework\test_user_journeys.py

- File has 437 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - test_framework\test_user_journeys_journeytestresult.py
-    - test_framework\test_user_journeys_journeytestbase.py
-    - test_framework\test_user_journeys_firsttimeuserjourneytest.py
- 3. Extract helper functions:
-    - test_framework\test_user_journeys_helpers.py (11 helpers)
- 4. Split by feature being tested:
-    - test_framework\test_user_journeys_feature1.py
-    - test_framework\test_user_journeys_feature2.py

### tests\e2e\test_cors_e2e.py

- File has 635 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\e2e\test_cors_e2e_testcorscompleteauthflow.py
-    - tests\e2e\test_cors_e2e_testcorsprenvironmentvalidation.py
-    - tests\e2e\test_cors_e2e_testcorsproductionstrictvalidation.py
- 4. Split by feature being tested:
-    - tests\e2e\test_cors_e2e_feature1.py
-    - tests\e2e\test_cors_e2e_feature2.py

### tests\unified\e2e\test_streaming_auth_validation.py

- File has 633 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - tests\unified\e2e\test_streaming_auth_validation_helpers.py (6 helpers)
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_streaming_auth_validation_feature1.py
-    - tests\unified\e2e\test_streaming_auth_validation_feature2.py

### tests\unified\test_database_operations.py

- File has 556 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\test_database_operations_databaseoperationstest.py
-    - tests\unified\test_database_operations_testpostgresqloperations.py
-    - tests\unified\test_database_operations_testclickhouseoperations.py
- 4. Split by feature being tested:
-    - tests\unified\test_database_operations_feature1.py
-    - tests\unified\test_database_operations_feature2.py

### tests\unified\e2e\test_websocket_concurrent_ordering.py

- File has 548 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\e2e\test_websocket_concurrent_ordering_burstmessagetester.py
-    - tests\unified\e2e\test_websocket_concurrent_ordering_testwebsocketconcurrentordering.py
- 3. Extract helper functions:
-    - tests\unified\e2e\test_websocket_concurrent_ordering_helpers.py (13 helpers)
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_websocket_concurrent_ordering_feature1.py
-    - tests\unified\e2e\test_websocket_concurrent_ordering_feature2.py

### tests\unified\e2e\test_websocket_event_completeness_integration.py

- File has 365 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_websocket_event_completeness_integration_feature1.py
-    - tests\unified\e2e\test_websocket_event_completeness_integration_feature2.py

### tests\unified\test_agent_cold_start.py

- File has 359 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\test_agent_cold_start_coldstarttestmanager.py
-    - tests\unified\test_agent_cold_start_coldstarttestvalidator.py
- 3. Extract helper functions:
-    - tests\unified\test_agent_cold_start_helpers.py (11 helpers)
- 4. Split by feature being tested:
-    - tests\unified\test_agent_cold_start_feature1.py
-    - tests\unified\test_agent_cold_start_feature2.py

### app\tests\core\test_error_recovery_scenarios.py

- File has 350 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\core\test_error_recovery_scenarios_errorrecoverytestfixtures.py
-    - app\tests\core\test_error_recovery_scenarios_testcascadingfailurescenarios.py
-    - app\tests\core\test_error_recovery_scenarios_testpartialsuccesshandling.py
- 4. Split by feature being tested:
-    - app\tests\core\test_error_recovery_scenarios_feature1.py
-    - app\tests\core\test_error_recovery_scenarios_feature2.py

### tests\unified\e2e\test_complete_user_journey.py

- File has 505 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\e2e\test_complete_user_journey_testuser.py
-    - tests\unified\e2e\test_complete_user_journey_testcompleteuserjourney.py
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_complete_user_journey_feature1.py
-    - tests\unified\e2e\test_complete_user_journey_feature2.py

### app\tests\performance\test_concurrent_user_performance.py

- File has 594 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\performance\test_concurrent_user_performance_loadtestresults.py
-    - app\tests\performance\test_concurrent_user_performance_scalabilitytester.py
-    - app\tests\performance\test_concurrent_user_performance_testconcurrentuserperformance.py
- 3. Extract helper functions:
-    - app\tests\performance\test_concurrent_user_performance_helpers.py (10 helpers)
- 4. Split by feature being tested:
-    - app\tests\performance\test_concurrent_user_performance_feature1.py
-    - app\tests\performance\test_concurrent_user_performance_feature2.py

### app\tests\integration\test_agent_cold_start.py

- File has 322 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - app\tests\integration\test_agent_cold_start_feature1.py
-    - app\tests\integration\test_agent_cold_start_feature2.py

### tests\e2e\test_real_services_e2e.py

- File has 1001 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\e2e\test_real_services_e2e_e2etestmetrics.py
-    - tests\e2e\test_real_services_e2e_realservicee2etestsuite.py
-    - tests\e2e\test_real_services_e2e_testrealservicese2e.py
- 3. Extract helper functions:
-    - tests\e2e\test_real_services_e2e_helpers.py (4 helpers)
- 4. Split by feature being tested:
-    - tests\e2e\test_real_services_e2e_feature1.py
-    - tests\e2e\test_real_services_e2e_feature2.py

### tests\e2e\conftest.py

- File has 366 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - tests\e2e\conftest_helpers.py (18 helpers)
- 4. Split by feature being tested:
-    - tests\e2e\conftest_feature1.py
-    - tests\e2e\conftest_feature2.py

### tests\unified\e2e\test_cross_service_auth_sync.py

- File has 499 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_cross_service_auth_sync_feature1.py
-    - tests\unified\e2e\test_cross_service_auth_sync_feature2.py

### tests\unified\e2e\test_real_database_consistency.py

- File has 572 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\e2e\test_real_database_consistency_testrealdatabaseconsistency.py
-    - tests\unified\e2e\test_real_database_consistency_testrealdatabaseperformance.py
- 3. Extract helper functions:
-    - tests\unified\e2e\test_real_database_consistency_helpers.py (15 helpers)
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_real_database_consistency_feature1.py
-    - tests\unified\e2e\test_real_database_consistency_feature2.py

### app\tests\auth_integration\test_real_user_session_management.py

- File has 374 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\auth_integration\test_real_user_session_management_usersessiontestmanager.py
-    - app\tests\auth_integration\test_real_user_session_management_testrealusercreation.py
-    - app\tests\auth_integration\test_real_user_session_management_testrealsessionmanagement.py
- 4. Split by feature being tested:
-    - app\tests\auth_integration\test_real_user_session_management_feature1.py
-    - app\tests\auth_integration\test_real_user_session_management_feature2.py

### app\tests\integration\test_websocket_reconnection.py

- File has 464 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - app\tests\integration\test_websocket_reconnection_feature1.py
-    - app\tests\integration\test_websocket_reconnection_feature2.py

### test_framework\bad_test_detector.py

- File has 383 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - test_framework\bad_test_detector_helpers.py (20 helpers)
- 4. Split by feature being tested:
-    - test_framework\bad_test_detector_feature1.py
-    - test_framework\bad_test_detector_feature2.py

### app\tests\unit\test_batch_message_transactional.py

- File has 348 lines (limit: 300)
- Recommended splitting strategies:
- 1. Split by test categories:
-    - app\tests\unit\test_batch_message_transactional_unit.py (unit tests)
-    - app\tests\unit\test_batch_message_transactional_integration.py (integration tests)
-    - app\tests\unit\test_batch_message_transactional_e2e.py (end-to-end tests)
- 2. Split by test classes:
-    - app\tests\unit\test_batch_message_transactional_testtransactionalbatchprocessor.py
-    - app\tests\unit\test_batch_message_transactional_testretrymanager.py
-    - app\tests\unit\test_batch_message_transactional_testmessagestatemanager.py
- 3. Extract helper functions:
-    - app\tests\unit\test_batch_message_transactional_helpers.py (4 helpers)
- 4. Split by feature being tested:
-    - app\tests\unit\test_batch_message_transactional_feature1.py
-    - app\tests\unit\test_batch_message_transactional_feature2.py

### tests\unified\e2e\test_auth_service_recovery.py

- File has 498 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_auth_service_recovery_feature1.py
-    - tests\unified\e2e\test_auth_service_recovery_feature2.py

### app\tests\integration\test_unified_message_flow.py

- File has 491 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\integration\test_unified_message_flow_testunifiedmessageflow.py
-    - app\tests\integration\test_unified_message_flow_testmessageflowerrorscenarios.py
-    - app\tests\integration\test_unified_message_flow_testmessageflowperformance.py
- 3. Extract helper functions:
-    - app\tests\integration\test_unified_message_flow_helpers.py (7 helpers)
- 4. Split by feature being tested:
-    - app\tests\integration\test_unified_message_flow_feature1.py
-    - app\tests\integration\test_unified_message_flow_feature2.py

### app\tests\performance\test_comprehensive_backend_performance.py

- File has 675 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\performance\test_comprehensive_backend_performance_performancetestmetrics.py
-    - app\tests\performance\test_comprehensive_backend_performance_databaseperformancetester.py
-    - app\tests\performance\test_comprehensive_backend_performance_websocketperformancetester.py
- 3. Extract helper functions:
-    - app\tests\performance\test_comprehensive_backend_performance_helpers.py (15 helpers)
- 4. Split by feature being tested:
-    - app\tests\performance\test_comprehensive_backend_performance_feature1.py
-    - app\tests\performance\test_comprehensive_backend_performance_feature2.py

### tests\unified\test_resource_limits.py

- File has 441 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\test_resource_limits_testagentresourceinitialization.py
-    - tests\unified\test_resource_limits_testresourcelimitvalidation.py
-    - tests\unified\test_resource_limits_testresourcelimitintegration.py
- 3. Extract helper functions:
-    - tests\unified\test_resource_limits_helpers.py (14 helpers)
- 4. Split by feature being tested:
-    - tests\unified\test_resource_limits_feature1.py
-    - tests\unified\test_resource_limits_feature2.py

### app\tests\integration\helpers\critical_integration_helpers.py

- File has 438 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\integration\helpers\critical_integration_helpers_revenuetesthelpers.py
-    - app\tests\integration\helpers\critical_integration_helpers_authenticationtesthelpers.py
-    - app\tests\integration\helpers\critical_integration_helpers_websockettesthelpers.py
- 4. Split by feature being tested:
-    - app\tests\integration\helpers\critical_integration_helpers_feature1.py
-    - app\tests\integration\helpers\critical_integration_helpers_feature2.py

### app\tests\services\test_fallback_response_service.py

- File has 454 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - app\tests\services\test_fallback_response_service_feature1.py
-    - app\tests\services\test_fallback_response_service_feature2.py

### app\tests\integration\test_sub_agent_registry_discovery.py

- File has 496 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - app\tests\integration\test_sub_agent_registry_discovery_feature1.py
-    - app\tests\integration\test_sub_agent_registry_discovery_feature2.py

### tests\unified\test_critical_imports_validation.py

- File has 408 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - tests\unified\test_critical_imports_validation_helpers.py (8 helpers)
- 4. Split by feature being tested:
-    - tests\unified\test_critical_imports_validation_feature1.py
-    - tests\unified\test_critical_imports_validation_feature2.py

### app\tests\e2e\test_complete_real_pipeline_e2e.py

- File has 355 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\e2e\test_complete_real_pipeline_e2e_testcompleterealpipeline.py
-    - app\tests\e2e\test_complete_real_pipeline_e2e_testrealpipelineerrorhandling.py
-    - app\tests\e2e\test_complete_real_pipeline_e2e_testrealpipelinewithvalidationreporting.py
- 3. Extract helper functions:
-    - app\tests\e2e\test_complete_real_pipeline_e2e_helpers.py (18 helpers)
- 4. Split by feature being tested:
-    - app\tests\e2e\test_complete_real_pipeline_e2e_feature1.py
-    - app\tests\e2e\test_complete_real_pipeline_e2e_feature2.py

### tests\unified\e2e\test_database_sync.py

- File has 318 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\e2e\test_database_sync_testdatabasesynce2e.py
-    - tests\unified\e2e\test_database_sync_testdatabasesyncperformance.py
-    - tests\unified\e2e\test_database_sync_testdatabasesyncresilience.py
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_database_sync_feature1.py
-    - tests\unified\e2e\test_database_sync_feature2.py

### app\tests\critical\test_agent_recovery_strategies.py

- File has 355 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\critical\test_agent_recovery_strategies_testtriageagentrecoverystrategy.py
-    - app\tests\critical\test_agent_recovery_strategies_testtriagerecoveryexecution.py
-    - app\tests\critical\test_agent_recovery_strategies_testdataanalysisrecoverystrategy.py
- 4. Split by feature being tested:
-    - app\tests\critical\test_agent_recovery_strategies_feature1.py
-    - app\tests\critical\test_agent_recovery_strategies_feature2.py

### tests\unified\e2e\run_critical_unified_tests.py

- File has 431 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\e2e\run_critical_unified_tests_testresult.py
-    - tests\unified\e2e\run_critical_unified_tests_testsuiteresult.py
-    - tests\unified\e2e\run_critical_unified_tests_criticaltestrunner.py
- 3. Extract helper functions:
-    - tests\unified\e2e\run_critical_unified_tests_helpers.py (7 helpers)
- 4. Split by feature being tested:
-    - tests\unified\e2e\run_critical_unified_tests_feature1.py
-    - tests\unified\e2e\run_critical_unified_tests_feature2.py

### tests\unified\e2e\test_real_billing_pipeline.py

- File has 385 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\e2e\test_real_billing_pipeline_billingpipelinetestcore.py
-    - tests\unified\e2e\test_real_billing_pipeline_testrealbillingpipeline.py
-    - tests\unified\e2e\test_real_billing_pipeline_testbillingedgecases.py
- 3. Extract helper functions:
-    - tests\unified\e2e\test_real_billing_pipeline_helpers.py (9 helpers)
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_real_billing_pipeline_feature1.py
-    - tests\unified\e2e\test_real_billing_pipeline_feature2.py

### tests\unified\e2e\test_websocket_message_streaming.py

- File has 383 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\e2e\test_websocket_message_streaming_websocketstreamingtester.py
-    - tests\unified\e2e\test_websocket_message_streaming_testwebsocketmessagestreaming.py
-    - tests\unified\e2e\test_websocket_message_streaming_testcriticalstreamingscenarios.py
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_websocket_message_streaming_feature1.py
-    - tests\unified\e2e\test_websocket_message_streaming_feature2.py

### tests\unified\test_isolation.py

- File has 368 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - tests\unified\test_isolation_helpers.py (9 helpers)
- 4. Split by feature being tested:
-    - tests\unified\test_isolation_feature1.py
-    - tests\unified\test_isolation_feature2.py

### tests\unified\test_dev_launcher_real_startup.py

- File has 436 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\test_dev_launcher_real_startup_realdevlaunchertester.py
-    - tests\unified\test_dev_launcher_real_startup_testdevlauncherrealstartup.py
- 3. Extract helper functions:
-    - tests\unified\test_dev_launcher_real_startup_helpers.py (6 helpers)
- 4. Split by feature being tested:
-    - tests\unified\test_dev_launcher_real_startup_feature1.py
-    - tests\unified\test_dev_launcher_real_startup_feature2.py

### app\tests\routes\test_synthetic_data_management.py

- File has 396 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - app\tests\routes\test_synthetic_data_management_feature1.py
-    - app\tests\routes\test_synthetic_data_management_feature2.py

### tests\unified\test_environment_config.py

- File has 510 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\test_environment_config_testenvironment.py
-    - tests\unified\test_environment_config_testsecrets.py
-    - tests\unified\test_environment_config_testenvironmentconfig.py
- 3. Extract helper functions:
-    - tests\unified\test_environment_config_helpers.py (30 helpers)
- 4. Split by feature being tested:
-    - tests\unified\test_environment_config_feature1.py
-    - tests\unified\test_environment_config_feature2.py

### tests\unified\e2e\test_real_session_persistence.py

- File has 541 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_real_session_persistence_feature1.py
-    - tests\unified\e2e\test_real_session_persistence_feature2.py

### app\tests\helpers\triage_test_helpers.py

- File has 414 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - app\tests\helpers\triage_test_helpers_helpers.py (36 helpers)
- 4. Split by feature being tested:
-    - app\tests\helpers\triage_test_helpers_feature1.py
-    - app\tests\helpers\triage_test_helpers_feature2.py

### app\tests\services\test_user_service.py

- File has 305 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - app\tests\services\test_user_service_feature1.py
-    - app\tests\services\test_user_service_feature2.py

### app\tests\e2e\test_websocket_thread_integration.py

- File has 375 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\e2e\test_websocket_thread_integration_threadwebsocketconnectiontests.py
-    - app\tests\e2e\test_websocket_thread_integration_threadmessageroutingtests.py
-    - app\tests\e2e\test_websocket_thread_integration_threadnotificationtests.py
- 4. Split by feature being tested:
-    - app\tests\e2e\test_websocket_thread_integration_feature1.py
-    - app\tests\e2e\test_websocket_thread_integration_feature2.py

### app\tests\core\test_system_health_monitor.py

- File has 350 lines (limit: 300)
- Recommended splitting strategies:
- 1. Split by test categories:
-    - app\tests\core\test_system_health_monitor_unit.py (unit tests)
-    - app\tests\core\test_system_health_monitor_integration.py (integration tests)
-    - app\tests\core\test_system_health_monitor_e2e.py (end-to-end tests)
- 4. Split by feature being tested:
-    - app\tests\core\test_system_health_monitor_feature1.py
-    - app\tests\core\test_system_health_monitor_feature2.py

### app\tests\services\test_advanced_orchestration.py

- File has 419 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - app\tests\services\test_advanced_orchestration_helpers.py (18 helpers)
- 4. Split by feature being tested:
-    - app\tests\services\test_advanced_orchestration_feature1.py
-    - app\tests\services\test_advanced_orchestration_feature2.py

### tests\unified\e2e\test_staging_complete_e2e.py

- File has 538 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\e2e\test_staging_complete_e2e_stagingtestresult.py
-    - tests\unified\e2e\test_staging_complete_e2e_staginge2etestsuite.py
-    - tests\unified\e2e\test_staging_complete_e2e_teststaginge2e.py
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_staging_complete_e2e_feature1.py
-    - tests\unified\e2e\test_staging_complete_e2e_feature2.py

### tests\unified\e2e\test_websocket_missing_events.py

- File has 405 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_websocket_missing_events_feature1.py
-    - tests\unified\e2e\test_websocket_missing_events_feature2.py

### app\tests\integration\test_staging_database_migration_validation.py

- File has 548 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - app\tests\integration\test_staging_database_migration_validation_feature1.py
-    - app\tests\integration\test_staging_database_migration_validation_feature2.py

### app\tests\e2e\test_multi_service.py

- File has 551 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\e2e\test_multi_service_testcrossserviceauthentication.py
-    - app\tests\e2e\test_multi_service_testdatabaseconsistency.py
-    - app\tests\e2e\test_multi_service_testservicediscovery.py
- 4. Split by feature being tested:
-    - app\tests\e2e\test_multi_service_feature1.py
-    - app\tests\e2e\test_multi_service_feature2.py

### tests\e2e\test_agent_message_flow_implementation.py

- File has 349 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - tests\e2e\test_agent_message_flow_implementation_feature1.py
-    - tests\e2e\test_agent_message_flow_implementation_feature2.py

### app\tests\websocket\test_websocket_frontend_integration.py

- File has 735 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\websocket\test_websocket_frontend_integration_testfrontendbackendintegration.py
-    - app\tests\websocket\test_websocket_frontend_integration_testwebsocketproviderbehavior.py
-    - app\tests\websocket\test_websocket_frontend_integration_testendtoendscenarios.py
- 3. Extract helper functions:
-    - app\tests\websocket\test_websocket_frontend_integration_helpers.py (15 helpers)
- 4. Split by feature being tested:
-    - app\tests\websocket\test_websocket_frontend_integration_feature1.py
-    - app\tests\websocket\test_websocket_frontend_integration_feature2.py

### app\tests\clickhouse\test_corpus_generation_coverage.py

- File has 524 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\clickhouse\test_corpus_generation_coverage_testcorpuslifecycle.py
-    - app\tests\clickhouse\test_corpus_generation_coverage_testworkloadtypescoverage.py
-    - app\tests\clickhouse\test_corpus_generation_coverage_testcontentgeneration.py
- 4. Split by feature being tested:
-    - app\tests\clickhouse\test_corpus_generation_coverage_feature1.py
-    - app\tests\clickhouse\test_corpus_generation_coverage_feature2.py

### tests\unified\websocket\test_missing_events_implementation.py

- File has 553 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\websocket\test_missing_events_implementation_testagentlifecycleevents.py
-    - tests\unified\websocket\test_missing_events_implementation_testprogressevents.py
-    - tests\unified\websocket\test_missing_events_implementation_testtoolevents.py
- 3. Extract helper functions:
-    - tests\unified\websocket\test_missing_events_implementation_helpers.py (7 helpers)
- 4. Split by feature being tested:
-    - tests\unified\websocket\test_missing_events_implementation_feature1.py
-    - tests\unified\websocket\test_missing_events_implementation_feature2.py

### app\tests\unit\test_first_time_user_real_critical.py

- File has 444 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - app\tests\unit\test_first_time_user_real_critical_feature1.py
-    - app\tests\unit\test_first_time_user_real_critical_feature2.py

### app\tests\integration\test_error_recovery.py

- File has 673 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\integration\test_error_recovery_testauthserviceerrorrecovery.py
-    - app\tests\integration\test_error_recovery_testbackenderrorpropagation.py
-    - app\tests\integration\test_error_recovery_testfrontenderrordisplay.py
- 3. Extract helper functions:
-    - app\tests\integration\test_error_recovery_helpers.py (5 helpers)
- 4. Split by feature being tested:
-    - app\tests\integration\test_error_recovery_feature1.py
-    - app\tests\integration\test_error_recovery_feature2.py

### tests\unified\e2e\test_new_user_complete_real.py

- File has 554 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - tests\unified\e2e\test_new_user_complete_real_helpers.py (8 helpers)
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_new_user_complete_real_feature1.py
-    - tests\unified\e2e\test_new_user_complete_real_feature2.py

### app\tests\websocket\test_websocket_comprehensive.py

- File has 725 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\websocket\test_websocket_comprehensive_websockettestclient.py
-    - app\tests\websocket\test_websocket_comprehensive_testwebsocketconnection.py
-    - app\tests\websocket\test_websocket_comprehensive_testwebsocketauthentication.py
- 4. Split by feature being tested:
-    - app\tests\websocket\test_websocket_comprehensive_feature1.py
-    - app\tests\websocket\test_websocket_comprehensive_feature2.py

### tests\unified\e2e\test_user_journey_complete_real.py

- File has 433 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - tests\unified\e2e\test_user_journey_complete_real_helpers.py (7 helpers)
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_user_journey_complete_real_feature1.py
-    - tests\unified\e2e\test_user_journey_complete_real_feature2.py

### tests\e2e\test_helpers\agent_isolation_base.py

- File has 340 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - tests\e2e\test_helpers\agent_isolation_base_helpers.py (8 helpers)
- 4. Split by feature being tested:
-    - tests\e2e\test_helpers\agent_isolation_base_feature1.py
-    - tests\e2e\test_helpers\agent_isolation_base_feature2.py

### tests\e2e\websocket_resilience\test_8_malformed_payload_handling.py

- File has 534 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - tests\e2e\websocket_resilience\test_8_malformed_payload_handling_helpers.py (8 helpers)
- 4. Split by feature being tested:
-    - tests\e2e\websocket_resilience\test_8_malformed_payload_handling_feature1.py
-    - tests\e2e\websocket_resilience\test_8_malformed_payload_handling_feature2.py

### tests\unified\e2e\test_cold_start_to_agent_response.py

- File has 400 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\e2e\test_cold_start_to_agent_response_coldstarttestresult.py
-    - tests\unified\e2e\test_cold_start_to_agent_response_websockettester.py
-    - tests\unified\e2e\test_cold_start_to_agent_response_testcoldstarttoagentresponse.py
- 3. Extract helper functions:
-    - tests\unified\e2e\test_cold_start_to_agent_response_helpers.py (5 helpers)
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_cold_start_to_agent_response_feature1.py
-    - tests\unified\e2e\test_cold_start_to_agent_response_feature2.py

### app\tests\integration\test_redis_session_state_sync.py

- File has 839 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - app\tests\integration\test_redis_session_state_sync_helpers.py (7 helpers)
- 4. Split by feature being tested:
-    - app\tests\integration\test_redis_session_state_sync_feature1.py
-    - app\tests\integration\test_redis_session_state_sync_feature2.py

### app\tests\core\test_fallback_coordinator_core.py

- File has 301 lines (limit: 300)
- Recommended splitting strategies:
- 1. Split by test categories:
-    - app\tests\core\test_fallback_coordinator_core_unit.py (unit tests)
-    - app\tests\core\test_fallback_coordinator_core_integration.py (integration tests)
-    - app\tests\core\test_fallback_coordinator_core_e2e.py (end-to-end tests)
- 4. Split by feature being tested:
-    - app\tests\core\test_fallback_coordinator_core_feature1.py
-    - app\tests\core\test_fallback_coordinator_core_feature2.py

### tests\e2e\websocket_resilience\test_10_token_refresh_websocket.py

- File has 535 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - tests\e2e\websocket_resilience\test_10_token_refresh_websocket_helpers.py (6 helpers)
- 4. Split by feature being tested:
-    - tests\e2e\websocket_resilience\test_10_token_refresh_websocket_feature1.py
-    - tests\e2e\websocket_resilience\test_10_token_refresh_websocket_feature2.py

### app\tests\test_database_manager.py

- File has 486 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - app\tests\test_database_manager_helpers.py (10 helpers)
- 4. Split by feature being tested:
-    - app\tests\test_database_manager_feature1.py
-    - app\tests\test_database_manager_feature2.py

### app\tests\mcp\test_mcp_service.py

- File has 405 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\mcp\test_mcp_service_testmcpclient.py
-    - app\tests\mcp\test_mcp_service_testmcptoolexecution.py
-    - app\tests\mcp\test_mcp_service_testmcpservice.py
- 4. Split by feature being tested:
-    - app\tests\mcp\test_mcp_service_feature1.py
-    - app\tests\mcp\test_mcp_service_feature2.py

### app\tests\integration\test_free_tier_value_demonstration_integration.py

- File has 498 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - app\tests\integration\test_free_tier_value_demonstration_integration_helpers.py (19 helpers)
- 4. Split by feature being tested:
-    - app\tests\integration\test_free_tier_value_demonstration_integration_feature1.py
-    - app\tests\integration\test_free_tier_value_demonstration_integration_feature2.py

### app\tests\unit\test_user_service_auth.py

- File has 465 lines (limit: 300)
- Recommended splitting strategies:
- 1. Split by test categories:
-    - app\tests\unit\test_user_service_auth_unit.py (unit tests)
-    - app\tests\unit\test_user_service_auth_integration.py (integration tests)
-    - app\tests\unit\test_user_service_auth_e2e.py (end-to-end tests)
- 3. Extract helper functions:
-    - app\tests\unit\test_user_service_auth_helpers.py (7 helpers)
- 4. Split by feature being tested:
-    - app\tests\unit\test_user_service_auth_feature1.py
-    - app\tests\unit\test_user_service_auth_feature2.py

### app\tests\llm\test_structured_generation.py

- File has 361 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\llm\test_structured_generation_testmockstructuredllm.py
-    - app\tests\llm\test_structured_generation_testllmmanagerstructuredgeneration.py
-    - app\tests\llm\test_structured_generation_testnestedjsonparsing.py
- 4. Split by feature being tested:
-    - app\tests\llm\test_structured_generation_feature1.py
-    - app\tests\llm\test_structured_generation_feature2.py

### tests\unified\e2e\test_session_persistence_unified.py

- File has 535 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - tests\unified\e2e\test_session_persistence_unified_helpers.py (9 helpers)
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_session_persistence_unified_feature1.py
-    - tests\unified\e2e\test_session_persistence_unified_feature2.py

### app\tests\routes\test_thread_messaging.py

- File has 356 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - app\tests\routes\test_thread_messaging_feature1.py
-    - app\tests\routes\test_thread_messaging_feature2.py

### app\tests\services\test_ws_connection_performance.py

- File has 331 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - app\tests\services\test_ws_connection_performance_helpers.py (14 helpers)
- 4. Split by feature being tested:
-    - app\tests\services\test_ws_connection_performance_feature1.py
-    - app\tests\services\test_ws_connection_performance_feature2.py

### app\tests\config\test_config_environment.py

- File has 385 lines (limit: 300)
- Recommended splitting strategies:
- 1. Split by test categories:
-    - app\tests\config\test_config_environment_unit.py (unit tests)
-    - app\tests\config\test_config_environment_integration.py (integration tests)
-    - app\tests\config\test_config_environment_e2e.py (end-to-end tests)
- 2. Split by test classes:
-    - app\tests\config\test_config_environment_testconfigenvironmentdetection.py
-    - app\tests\config\test_config_environment_testconfigobjectcreation.py
-    - app\tests\config\test_config_environment_testenvironmentvalidation.py
- 4. Split by feature being tested:
-    - app\tests\config\test_config_environment_feature1.py
-    - app\tests\config\test_config_environment_feature2.py

### app\tests\e2e\test_agent_orchestration_e2e.py

- File has 304 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\e2e\test_agent_orchestration_e2e_testcompleteuserflow.py
-    - app\tests\e2e\test_agent_orchestration_e2e_testagenthandoffs.py
-    - app\tests\e2e\test_agent_orchestration_e2e_testfailurerecovery.py
- 3. Extract helper functions:
-    - app\tests\e2e\test_agent_orchestration_e2e_helpers.py (13 helpers)
- 4. Split by feature being tested:
-    - app\tests\e2e\test_agent_orchestration_e2e_feature1.py
-    - app\tests\e2e\test_agent_orchestration_e2e_feature2.py

### app\tests\critical\test_websocket_coroutine_regression.py

- File has 337 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\critical\test_websocket_coroutine_regression_testcoroutinehandling.py
-    - app\tests\critical\test_websocket_coroutine_regression_testasyncawaitchain.py
-    - app\tests\critical\test_websocket_coroutine_regression_testcoroutineerrorscenarios.py
- 4. Split by feature being tested:
-    - app\tests\critical\test_websocket_coroutine_regression_feature1.py
-    - app\tests\critical\test_websocket_coroutine_regression_feature2.py

### app\tests\services\test_clickhouse_service.py

- File has 357 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\services\test_clickhouse_service_testclickhouseconnection.py
-    - app\tests\services\test_clickhouse_service_testbasicoperations.py
-    - app\tests\services\test_clickhouse_service_testworkloadeventsoperations.py
- 4. Split by feature being tested:
-    - app\tests\services\test_clickhouse_service_feature1.py
-    - app\tests\services\test_clickhouse_service_feature2.py

### tests\e2e\websocket_resilience\test_2_midstream_disconnection_recovery.py

- File has 1279 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - tests\e2e\websocket_resilience\test_2_midstream_disconnection_recovery_helpers.py (8 helpers)
- 4. Split by feature being tested:
-    - tests\e2e\websocket_resilience\test_2_midstream_disconnection_recovery_feature1.py
-    - tests\e2e\websocket_resilience\test_2_midstream_disconnection_recovery_feature2.py

### app\tests\e2e\test_thread_management.py

- File has 304 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\e2e\test_thread_management_testthreadcreation.py
-    - app\tests\e2e\test_thread_management_testthreadswitching.py
-    - app\tests\e2e\test_thread_management_testthreadpersistence.py
- 4. Split by feature being tested:
-    - app\tests\e2e\test_thread_management_feature1.py
-    - app\tests\e2e\test_thread_management_feature2.py

### app\tests\integration\test_websocket_lifecycle_integration.py

- File has 436 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - app\tests\integration\test_websocket_lifecycle_integration_feature1.py
-    - app\tests\integration\test_websocket_lifecycle_integration_feature2.py

### app\tests\e2e\test_system_startup.py

- File has 378 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\e2e\test_system_startup_testsystemstartup.py
-    - app\tests\e2e\test_system_startup_teststartupperformance.py
-    - app\tests\e2e\test_system_startup_teststartuprecovery.py
- 4. Split by feature being tested:
-    - app\tests\e2e\test_system_startup_feature1.py
-    - app\tests\e2e\test_system_startup_feature2.py

### tests\unified\test_agent_startup_performance_validation.py

- File has 360 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - tests\unified\test_agent_startup_performance_validation_helpers.py (17 helpers)
- 4. Split by feature being tested:
-    - tests\unified\test_agent_startup_performance_validation_feature1.py
-    - tests\unified\test_agent_startup_performance_validation_feature2.py

### tests\unified\e2e\test_websocket_multi_service.py

- File has 467 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_websocket_multi_service_feature1.py
-    - tests\unified\e2e\test_websocket_multi_service_feature2.py

### app\tests\test_api_agent_generation_critical.py

- File has 429 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - app\tests\test_api_agent_generation_critical_feature1.py
-    - app\tests\test_api_agent_generation_critical_feature2.py

### tests\unified\test_multi_service_health.py

- File has 448 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - tests\unified\test_multi_service_health_feature1.py
-    - tests\unified\test_multi_service_health_feature2.py

### app\tests\services\test_tool_orchestration.py

- File has 352 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - app\tests\services\test_tool_orchestration_helpers.py (18 helpers)
- 4. Split by feature being tested:
-    - app\tests\services\test_tool_orchestration_feature1.py
-    - app\tests\services\test_tool_orchestration_feature2.py

### app\tests\unified_system\test_websocket_state.py

- File has 683 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\unified_system\test_websocket_state_websockettestsession.py
-    - app\tests\unified_system\test_websocket_state_testwebsocketstatemanagement.py
- 4. Split by feature being tested:
-    - app\tests\unified_system\test_websocket_state_feature1.py
-    - app\tests\unified_system\test_websocket_state_feature2.py

### tests\e2e\resource_isolation\test_quota_enforcement.py

- File has 339 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - tests\e2e\resource_isolation\test_quota_enforcement_feature1.py
-    - tests\e2e\resource_isolation\test_quota_enforcement_feature2.py

### tests\unified\e2e\test_real_llm_environment_example.py

- File has 328 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\e2e\test_real_llm_environment_example_testrealllmenvironment.py
-    - tests\unified\e2e\test_real_llm_environment_example_testrealllmintegration.py
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_real_llm_environment_example_feature1.py
-    - tests\unified\e2e\test_real_llm_environment_example_feature2.py

### app\tests\startup\test_comprehensive_startup.py

- File has 365 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - app\tests\startup\test_comprehensive_startup_helpers.py (5 helpers)
- 4. Split by feature being tested:
-    - app\tests\startup\test_comprehensive_startup_feature1.py
-    - app\tests\startup\test_comprehensive_startup_feature2.py

### tests\e2e\test_agent_resource_isolation_ORIGINAL_BACKUP.py

- File has 1640 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - tests\e2e\test_agent_resource_isolation_ORIGINAL_BACKUP_helpers.py (26 helpers)
- 4. Split by feature being tested:
-    - tests\e2e\test_agent_resource_isolation_ORIGINAL_BACKUP_feature1.py
-    - tests\e2e\test_agent_resource_isolation_ORIGINAL_BACKUP_feature2.py

### tests\unified\agent_startup_test_data.py

- File has 346 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\agent_startup_test_data_testdatafactory.py
-    - tests\unified\agent_startup_test_data_loadtestdatagenerator.py
- 3. Extract helper functions:
-    - tests\unified\agent_startup_test_data_helpers.py (37 helpers)
- 4. Split by feature being tested:
-    - tests\unified\agent_startup_test_data_feature1.py
-    - tests\unified\agent_startup_test_data_feature2.py

### tests\unified\e2e\test_auth_service_independence.py

- File has 965 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - tests\unified\e2e\test_auth_service_independence_helpers.py (5 helpers)
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_auth_service_independence_feature1.py
-    - tests\unified\e2e\test_auth_service_independence_feature2.py

### tests\unified\e2e\test_database_user_sync.py

- File has 496 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\e2e\test_database_user_sync_usertestdata.py
-    - tests\unified\e2e\test_database_user_sync_databaseusersynctester.py
-    - tests\unified\e2e\test_database_user_sync_testdatabaseusersync.py
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_database_user_sync_feature1.py
-    - tests\unified\e2e\test_database_user_sync_feature2.py

### app\tests\integration\first_time_user_fixtures.py

- File has 376 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - app\tests\integration\first_time_user_fixtures_feature1.py
-    - app\tests\integration\first_time_user_fixtures_feature2.py

### tests\unified\e2e\test_agent_workflow_validation_real_llm.py

- File has 559 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\e2e\test_agent_workflow_validation_real_llm_agentworkflowtestcase.py
-    - tests\unified\e2e\test_agent_workflow_validation_real_llm_agentworkflowtestdata.py
-    - tests\unified\e2e\test_agent_workflow_validation_real_llm_testagentworkflowvalidationrealllm.py
- 3. Extract helper functions:
-    - tests\unified\e2e\test_agent_workflow_validation_real_llm_helpers.py (20 helpers)
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_agent_workflow_validation_real_llm_feature1.py
-    - tests\unified\e2e\test_agent_workflow_validation_real_llm_feature2.py

### test_framework\intelligent_parallelization.py

- File has 460 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - test_framework\intelligent_parallelization_testtype.py
-    - test_framework\intelligent_parallelization_testpriority.py
-    - test_framework\intelligent_parallelization_testmetrics.py
- 3. Extract helper functions:
-    - test_framework\intelligent_parallelization_helpers.py (27 helpers)
- 4. Split by feature being tested:
-    - test_framework\intelligent_parallelization_feature1.py
-    - test_framework\intelligent_parallelization_feature2.py

### app\tests\integration\test_websocket_auth_token_refresh.py

- File has 807 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - app\tests\integration\test_websocket_auth_token_refresh_helpers.py (10 helpers)
- 4. Split by feature being tested:
-    - app\tests\integration\test_websocket_auth_token_refresh_feature1.py
-    - app\tests\integration\test_websocket_auth_token_refresh_feature2.py

### tests\unified\test_websocket_lifecycle.py

- File has 346 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\test_websocket_lifecycle_testwebsocketagentmessagelifecycle.py
-    - tests\unified\test_websocket_lifecycle_testagentstatemanagement.py
-    - tests\unified\test_websocket_lifecycle_testwebsocketreliability.py
- 3. Extract helper functions:
-    - tests\unified\test_websocket_lifecycle_helpers.py (16 helpers)
- 4. Split by feature being tested:
-    - tests\unified\test_websocket_lifecycle_feature1.py
-    - tests\unified\test_websocket_lifecycle_feature2.py

### app\tests\websocket\test_performance_monitor_coverage.py

- File has 311 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\websocket\test_performance_monitor_coverage_testmonitoringcoverage.py
-    - app\tests\websocket\test_performance_monitor_coverage_testmonitoringreliabilitypatterns.py
- 4. Split by feature being tested:
-    - app\tests\websocket\test_performance_monitor_coverage_feature1.py
-    - app\tests\websocket\test_performance_monitor_coverage_feature2.py

### tests\integration\test_cross_service_integration.py

- File has 416 lines (limit: 300)
- Recommended splitting strategies:
- 1. Split by test categories:
-    - tests\integration\test_cross_service_integration_unit.py (unit tests)
-    - tests\integration\test_cross_service_integration_integration.py (integration tests)
-    - tests\integration\test_cross_service_integration_e2e.py (end-to-end tests)
- 2. Split by test classes:
-    - tests\integration\test_cross_service_integration_testcorsenhancements.py
-    - tests\integration\test_cross_service_integration_testhealthmonitorenhancements.py
-    - tests\integration\test_cross_service_integration_testdevlauncherintegration.py
- 4. Split by feature being tested:
-    - tests\integration\test_cross_service_integration_feature1.py
-    - tests\integration\test_cross_service_integration_feature2.py

### tests\unified\e2e\test_workspace_isolation.py

- File has 301 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\e2e\test_workspace_isolation_testworkspacedataisolation.py
-    - tests\unified\e2e\test_workspace_isolation_testworkspaceisolationcompliance.py
- 3. Extract helper functions:
-    - tests\unified\e2e\test_workspace_isolation_helpers.py (10 helpers)
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_workspace_isolation_feature1.py
-    - tests\unified\e2e\test_workspace_isolation_feature2.py

### tests\e2e\test_helpers\performance_base.py

- File has 687 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - tests\e2e\test_helpers\performance_base_helpers.py (11 helpers)
- 4. Split by feature being tested:
-    - tests\e2e\test_helpers\performance_base_feature1.py
-    - tests\e2e\test_helpers\performance_base_feature2.py

### tests\unified\e2e\test_auth_circuit_breaker.py

- File has 391 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - tests\unified\e2e\test_auth_circuit_breaker_helpers.py (5 helpers)
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_auth_circuit_breaker_feature1.py
-    - tests\unified\e2e\test_auth_circuit_breaker_feature2.py

### tests\unified\test_service_health_monitoring.py

- File has 570 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - tests\unified\test_service_health_monitoring_helpers.py (4 helpers)
- 4. Split by feature being tested:
-    - tests\unified\test_service_health_monitoring_feature1.py
-    - tests\unified\test_service_health_monitoring_feature2.py

### tests\integration\test_cors_integration.py

- File has 523 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\integration\test_cors_integration_testcorscrossoriginrequests.py
-    - tests\integration\test_cors_integration_testcorswebsocketintegration.py
-    - tests\integration\test_cors_integration_testcorspreflightrequests.py
- 4. Split by feature being tested:
-    - tests\integration\test_cors_integration_feature1.py
-    - tests\integration\test_cors_integration_feature2.py

### app\tests\e2e\test_agent_pipeline.py

- File has 586 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\e2e\test_agent_pipeline_testagentmessageprocessing.py
-    - app\tests\e2e\test_agent_pipeline_testsupervisoragentorchestration.py
-    - app\tests\e2e\test_agent_pipeline_testsubagentexecution.py
- 4. Split by feature being tested:
-    - app\tests\e2e\test_agent_pipeline_feature1.py
-    - app\tests\e2e\test_agent_pipeline_feature2.py

### tests\unified\e2e\test_data_export.py

- File has 535 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\e2e\test_data_export_dataexporte2etester.py
-    - tests\unified\e2e\test_data_export_fastdataexporttester.py
-    - tests\unified\e2e\test_data_export_dataexporttestmanager.py
- 3. Extract helper functions:
-    - tests\unified\e2e\test_data_export_helpers.py (8 helpers)
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_data_export_feature1.py
-    - tests\unified\e2e\test_data_export_feature2.py

### app\tests\integration\test_payment_webhook_processing.py

- File has 379 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - app\tests\integration\test_payment_webhook_processing_feature1.py
-    - app\tests\integration\test_payment_webhook_processing_feature2.py

### tests\e2e\test_cache_contention.py

- File has 1046 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\e2e\test_cache_contention_redistestclient.py
-    - tests\e2e\test_cache_contention_cachecontentiontestsuite.py
-    - tests\e2e\test_cache_contention_testcachecontentionsuite.py
- 3. Extract helper functions:
-    - tests\e2e\test_cache_contention_helpers.py (14 helpers)
- 4. Split by feature being tested:
-    - tests\e2e\test_cache_contention_feature1.py
-    - tests\e2e\test_cache_contention_feature2.py

### app\tests\integration\test_team_collaboration_permissions.py

- File has 990 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - app\tests\integration\test_team_collaboration_permissions_helpers.py (6 helpers)
- 4. Split by feature being tested:
-    - app\tests\integration\test_team_collaboration_permissions_feature1.py
-    - app\tests\integration\test_team_collaboration_permissions_feature2.py

### app\tests\integration\test_first_time_user_workspace.py

- File has 320 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - app\tests\integration\test_first_time_user_workspace_feature1.py
-    - app\tests\integration\test_first_time_user_workspace_feature2.py

### tests\unified\test_observability.py

- File has 351 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - tests\unified\test_observability_helpers.py (17 helpers)
- 4. Split by feature being tested:
-    - tests\unified\test_observability_feature1.py
-    - tests\unified\test_observability_feature2.py

### app\tests\routes\test_demo.py

- File has 406 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - app\tests\routes\test_demo_feature1.py
-    - app\tests\routes\test_demo_feature2.py

### tests\unified\e2e\test_critical_unified_flows.py

- File has 332 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\e2e\test_critical_unified_flows_testuser.py
-    - tests\unified\e2e\test_critical_unified_flows_unifiedtestharness.py
-    - tests\unified\e2e\test_critical_unified_flows_testcriticalunifiedflows.py
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_critical_unified_flows_feature1.py
-    - tests\unified\e2e\test_critical_unified_flows_feature2.py

### app\tests\integration\staging\test_staging_websocket_load_balancing.py

- File has 537 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\integration\staging\test_staging_websocket_load_balancing_websocketloadtester.py
-    - app\tests\integration\staging\test_staging_websocket_load_balancing_teststagingwebsocketloadbalancing.py
- 3. Extract helper functions:
-    - app\tests\integration\staging\test_staging_websocket_load_balancing_helpers.py (7 helpers)
- 4. Split by feature being tested:
-    - app\tests\integration\staging\test_staging_websocket_load_balancing_feature1.py
-    - app\tests\integration\staging\test_staging_websocket_load_balancing_feature2.py

### tests\integration\test_multi_agent_orchestration_state_management.py

- File has 546 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - tests\integration\test_multi_agent_orchestration_state_management_helpers.py (6 helpers)
- 4. Split by feature being tested:
-    - tests\integration\test_multi_agent_orchestration_state_management_feature1.py
-    - tests\integration\test_multi_agent_orchestration_state_management_feature2.py

### test_framework\resource_monitor.py

- File has 569 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - test_framework\resource_monitor_testresourceusage.py
-    - test_framework\resource_monitor_testshardoptimizer.py
- 3. Extract helper functions:
-    - test_framework\resource_monitor_helpers.py (32 helpers)
- 4. Split by feature being tested:
-    - test_framework\resource_monitor_feature1.py
-    - test_framework\resource_monitor_feature2.py

### tests\unified\e2e\test_multi_tab_isolation.py

- File has 429 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\e2e\test_multi_tab_isolation_multitabtestresult.py
-    - tests\unified\e2e\test_multi_tab_isolation_testmultitabisolation.py
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_multi_tab_isolation_feature1.py
-    - tests\unified\e2e\test_multi_tab_isolation_feature2.py

### app\tests\unit\services\test_gcp_error_service.py

- File has 347 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - app\tests\unit\services\test_gcp_error_service_helpers.py (9 helpers)
- 4. Split by feature being tested:
-    - app\tests\unit\services\test_gcp_error_service_feature1.py
-    - app\tests\unit\services\test_gcp_error_service_feature2.py

### test_framework\test_runners.py

- File has 528 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - test_framework\test_runners_helpers.py (8 helpers)
- 4. Split by feature being tested:
-    - test_framework\test_runners_feature1.py
-    - test_framework\test_runners_feature2.py

### tests\unified\test_auth_e2e_flow.py

- File has 318 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\test_auth_e2e_flow_unifiedtestharness.py
-    - tests\unified\test_auth_e2e_flow_testauthe2eflow.py
- 3. Extract helper functions:
-    - tests\unified\test_auth_e2e_flow_helpers.py (6 helpers)
- 4. Split by feature being tested:
-    - tests\unified\test_auth_e2e_flow_feature1.py
-    - tests\unified\test_auth_e2e_flow_feature2.py

### app\tests\critical\test_auth_integration_core.py

- File has 359 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\critical\test_auth_integration_core_testauthtokenvalidation.py
-    - app\tests\critical\test_auth_integration_core_testuserdatabaselookup.py
-    - app\tests\critical\test_auth_integration_core_testoptionalauthenticationflow.py
- 4. Split by feature being tested:
-    - app\tests\critical\test_auth_integration_core_feature1.py
-    - app\tests\critical\test_auth_integration_core_feature2.py

### app\tests\agents\test_llm_agent_integration.py

- File has 390 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - app\tests\agents\test_llm_agent_integration_feature1.py
-    - app\tests\agents\test_llm_agent_integration_feature2.py

### app\tests\critical\test_real_auth_integration_critical.py

- File has 380 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\critical\test_real_auth_integration_critical_criticalauthtestmanager.py
-    - app\tests\critical\test_real_auth_integration_critical_testcriticaltokenvalidation.py
-    - app\tests\critical\test_real_auth_integration_critical_testcriticaluserretrieval.py
- 4. Split by feature being tested:
-    - app\tests\critical\test_real_auth_integration_critical_feature1.py
-    - app\tests\critical\test_real_auth_integration_critical_feature2.py

### tests\e2e\websocket_resilience\test_4_reconnection_expired_token.py

- File has 1344 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - tests\e2e\websocket_resilience\test_4_reconnection_expired_token_helpers.py (16 helpers)
- 4. Split by feature being tested:
-    - tests\e2e\websocket_resilience\test_4_reconnection_expired_token_feature1.py
-    - tests\e2e\websocket_resilience\test_4_reconnection_expired_token_feature2.py

### app\tests\agents\test_triage_caching_async.py

- File has 322 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\agents\test_triage_caching_async_testcachingmechanisms.py
-    - app\tests\agents\test_triage_caching_async_testerrorhandlingandrecovery.py
-    - app\tests\agents\test_triage_caching_async_testasyncoperations.py
- 3. Extract helper functions:
-    - app\tests\agents\test_triage_caching_async_helpers.py (21 helpers)
- 4. Split by feature being tested:
-    - app\tests\agents\test_triage_caching_async_feature1.py
-    - app\tests\agents\test_triage_caching_async_feature2.py

### app\tests\integration\test_cache_invalidation_chain.py

- File has 1037 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - app\tests\integration\test_cache_invalidation_chain_helpers.py (10 helpers)
- 4. Split by feature being tested:
-    - app\tests\integration\test_cache_invalidation_chain_feature1.py
-    - app\tests\integration\test_cache_invalidation_chain_feature2.py

### tests\unified\e2e\test_database_sync_complete.py

- File has 938 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_database_sync_complete_feature1.py
-    - tests\unified\e2e\test_database_sync_complete_feature2.py

### tests\unified\websocket\test_heartbeat_basic.py

- File has 472 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\websocket\test_heartbeat_basic_heartbeattestconfig.py
-    - tests\unified\websocket\test_heartbeat_basic_heartbeattesttracker.py
-    - tests\unified\websocket\test_heartbeat_basic_heartbeattestmanager.py
- 3. Extract helper functions:
-    - tests\unified\websocket\test_heartbeat_basic_helpers.py (19 helpers)
- 4. Split by feature being tested:
-    - tests\unified\websocket\test_heartbeat_basic_feature1.py
-    - tests\unified\websocket\test_heartbeat_basic_feature2.py

### app\tests\e2e\test_artifact_validation.py

- File has 328 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - app\tests\e2e\test_artifact_validation_feature1.py
-    - app\tests\e2e\test_artifact_validation_feature2.py

### app\tests\integration\test_usage_metering_billing.py

- File has 639 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\integration\test_usage_metering_billing_testusagemeteringbilling.py
-    - app\tests\integration\test_usage_metering_billing_testbillingaccuracyedgecases.py
- 3. Extract helper functions:
-    - app\tests\integration\test_usage_metering_billing_helpers.py (11 helpers)
- 4. Split by feature being tested:
-    - app\tests\integration\test_usage_metering_billing_feature1.py
-    - app\tests\integration\test_usage_metering_billing_feature2.py

### tests\unified\e2e\test_agent_failure_websocket_recovery.py

- File has 716 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\e2e\test_agent_failure_websocket_recovery_testagentfailurewebsocketrecovery.py
-    - tests\unified\e2e\test_agent_failure_websocket_recovery_testcircuitbreakerwebsocketintegration.py
-    - tests\unified\e2e\test_agent_failure_websocket_recovery_testerroreventdetailvalidation.py
- 3. Extract helper functions:
-    - tests\unified\e2e\test_agent_failure_websocket_recovery_helpers.py (10 helpers)
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_agent_failure_websocket_recovery_feature1.py
-    - tests\unified\e2e\test_agent_failure_websocket_recovery_feature2.py

### tests\unified\e2e\test_jwt_secret_synchronization.py

- File has 383 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - tests\unified\e2e\test_jwt_secret_synchronization_helpers.py (4 helpers)
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_jwt_secret_synchronization_feature1.py
-    - tests\unified\e2e\test_jwt_secret_synchronization_feature2.py

### app\tests\routes\test_thread_analytics.py

- File has 465 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - app\tests\routes\test_thread_analytics_feature1.py
-    - app\tests\routes\test_thread_analytics_feature2.py

### app\tests\integration\user_flows\test_enterprise_flows.py

- File has 315 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - app\tests\integration\user_flows\test_enterprise_flows_feature1.py
-    - app\tests\integration\user_flows\test_enterprise_flows_feature2.py

### app\tests\e2e\test_cost_optimization_workflows.py

- File has 408 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\e2e\test_cost_optimization_workflows_testcostqualityconstraints.py
-    - app\tests\e2e\test_cost_optimization_workflows_testbudgetconstrainedoptimization.py
-    - app\tests\e2e\test_cost_optimization_workflows_testworkflowintegrity.py
- 3. Extract helper functions:
-    - app\tests\e2e\test_cost_optimization_workflows_helpers.py (27 helpers)
- 4. Split by feature being tested:
-    - app\tests\e2e\test_cost_optimization_workflows_feature1.py
-    - app\tests\e2e\test_cost_optimization_workflows_feature2.py

### app\tests\test_comprehensive_database_operations.py

- File has 480 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - app\tests\test_comprehensive_database_operations_feature1.py
-    - app\tests\test_comprehensive_database_operations_feature2.py

### tests\unified\e2e\test_thread_management_websocket.py

- File has 726 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - tests\unified\e2e\test_thread_management_websocket_helpers.py (12 helpers)
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_thread_management_websocket_feature1.py
-    - tests\unified\e2e\test_thread_management_websocket_feature2.py

### app\tests\test_mcp_integration.py

- File has 404 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\test_mcp_integration_testnetramcpserver.py
-    - app\tests\test_mcp_integration_testmcpservice.py
-    - app\tests\test_mcp_integration_testmcpintegration.py
- 4. Split by feature being tested:
-    - app\tests\test_mcp_integration_feature1.py
-    - app\tests\test_mcp_integration_feature2.py

### tests\unified\e2e\test_error_recovery_complete.py

- File has 627 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\e2e\test_error_recovery_complete_realcircuitbreakertester.py
-    - tests\unified\e2e\test_error_recovery_complete_testcompleteerrorrecovery.py
- 3. Extract helper functions:
-    - tests\unified\e2e\test_error_recovery_complete_helpers.py (6 helpers)
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_error_recovery_complete_feature1.py
-    - tests\unified\e2e\test_error_recovery_complete_feature2.py

### app\tests\integration\test_agent_tool_loading_validation.py

- File has 593 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - app\tests\integration\test_agent_tool_loading_validation_helpers.py (6 helpers)
- 4. Split by feature being tested:
-    - app\tests\integration\test_agent_tool_loading_validation_feature1.py
-    - app\tests\integration\test_agent_tool_loading_validation_feature2.py

### app\tests\integration\test_redis_session_integration.py

- File has 410 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - app\tests\integration\test_redis_session_integration_feature1.py
-    - app\tests\integration\test_redis_session_integration_feature2.py

### tests\unified\e2e\test_session_state_websocket_sync.py

- File has 409 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_session_state_websocket_sync_feature1.py
-    - tests\unified\e2e\test_session_state_websocket_sync_feature2.py

### app\tests\agents\test_llm_agent_e2e_flows.py

- File has 322 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - app\tests\agents\test_llm_agent_e2e_flows_helpers.py (13 helpers)
- 4. Split by feature being tested:
-    - app\tests\agents\test_llm_agent_e2e_flows_feature1.py
-    - app\tests\agents\test_llm_agent_e2e_flows_feature2.py

### auth_service\tests\unified\test_jwt_validation.py

- File has 354 lines (limit: 300)
- Recommended splitting strategies:
- 1. Split by test categories:
-    - auth_service\tests\unified\test_jwt_validation_unit.py (unit tests)
-    - auth_service\tests\unified\test_jwt_validation_integration.py (integration tests)
-    - auth_service\tests\unified\test_jwt_validation_e2e.py (end-to-end tests)
- 2. Split by test classes:
-    - auth_service\tests\unified\test_jwt_validation_testjwtsignaturevalidation.py
-    - auth_service\tests\unified\test_jwt_validation_testjwtclaimsvalidation.py
-    - auth_service\tests\unified\test_jwt_validation_testjwtrevocation.py
- 4. Split by feature being tested:
-    - auth_service\tests\unified\test_jwt_validation_feature1.py
-    - auth_service\tests\unified\test_jwt_validation_feature2.py

### tests\unified\e2e\test_service_to_service_auth.py

- File has 348 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_service_to_service_auth_feature1.py
-    - tests\unified\e2e\test_service_to_service_auth_feature2.py

### tests\unified\e2e\test_real_concurrent_users.py

- File has 556 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - tests\unified\e2e\test_real_concurrent_users_helpers.py (13 helpers)
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_real_concurrent_users_feature1.py
-    - tests\unified\e2e\test_real_concurrent_users_feature2.py

### tests\unified\e2e\test_database_comprehensive_e2e.py

- File has 359 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\e2e\test_database_comprehensive_e2e_databasee2etester.py
-    - tests\unified\e2e\test_database_comprehensive_e2e_testdatabasecomprehensivee2e.py
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_database_comprehensive_e2e_feature1.py
-    - tests\unified\e2e\test_database_comprehensive_e2e_feature2.py

### tests\unified\service_manager.py

- File has 363 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - tests\unified\service_manager_helpers.py (8 helpers)
- 4. Split by feature being tested:
-    - tests\unified\service_manager_feature1.py
-    - tests\unified\service_manager_feature2.py

### app\tests\e2e\test_error_propagation_workflows.py

- File has 333 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\e2e\test_error_propagation_workflows_testerrorpropagationthroughlayers.py
-    - app\tests\e2e\test_error_propagation_workflows_testrecoverycoordinationacrosslayers.py
-    - app\tests\e2e\test_error_propagation_workflows_testrealworkflowintegration.py
- 3. Extract helper functions:
-    - app\tests\e2e\test_error_propagation_workflows_helpers.py (12 helpers)
- 4. Split by feature being tested:
-    - app\tests\e2e\test_error_propagation_workflows_feature1.py
-    - app\tests\e2e\test_error_propagation_workflows_feature2.py

### app\tests\services\test_tool_permission_main.py

- File has 348 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\services\test_tool_permission_main_testchecktoolpermission.py
-    - app\tests\services\test_tool_permission_main_testgetusertoolavailability.py
-    - app\tests\services\test_tool_permission_main_testupgradepath.py
- 4. Split by feature being tested:
-    - app\tests\services\test_tool_permission_main_feature1.py
-    - app\tests\services\test_tool_permission_main_feature2.py

### app\tests\unit\test_usage_tracker_unit.py

- File has 729 lines (limit: 300)
- Recommended splitting strategies:
- 1. Split by test categories:
-    - app\tests\unit\test_usage_tracker_unit_unit.py (unit tests)
-    - app\tests\unit\test_usage_tracker_unit_integration.py (integration tests)
-    - app\tests\unit\test_usage_tracker_unit_e2e.py (end-to-end tests)
- 2. Split by test classes:
-    - app\tests\unit\test_usage_tracker_unit_testusagetracking.py
-    - app\tests\unit\test_usage_tracker_unit_testusagelimitchecking.py
-    - app\tests\unit\test_usage_tracker_unit_testupgradesavingscalculation.py
- 3. Extract helper functions:
-    - app\tests\unit\test_usage_tracker_unit_helpers.py (9 helpers)
- 4. Split by feature being tested:
-    - app\tests\unit\test_usage_tracker_unit_feature1.py
-    - app\tests\unit\test_usage_tracker_unit_feature2.py

### app\tests\config\test_config_loader.py

- File has 650 lines (limit: 300)
- Recommended splitting strategies:
- 1. Split by test categories:
-    - app\tests\config\test_config_loader_unit.py (unit tests)
-    - app\tests\config\test_config_loader_integration.py (integration tests)
-    - app\tests\config\test_config_loader_e2e.py (end-to-end tests)
- 2. Split by test classes:
-    - app\tests\config\test_config_loader_testcloudenvironmentdetection.py
-    - app\tests\config\test_config_loader_testconfigurationloading.py
-    - app\tests\config\test_config_loader_testconfigurationvalidation.py
- 3. Extract helper functions:
-    - app\tests\config\test_config_loader_helpers.py (5 helpers)
- 4. Split by feature being tested:
-    - app\tests\config\test_config_loader_feature1.py
-    - app\tests\config\test_config_loader_feature2.py

### app\tests\services\test_supply_research_scheduler_jobs.py

- File has 549 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\services\test_supply_research_scheduler_jobs_testsupplyresearchschedulerjobs.py
-    - app\tests\services\test_supply_research_scheduler_jobs_testsupplyresearchschedulerretrylogic.py
-    - app\tests\services\test_supply_research_scheduler_jobs_testsupplyresearchschedulerconcurrency.py
- 4. Split by feature being tested:
-    - app\tests\services\test_supply_research_scheduler_jobs_feature1.py
-    - app\tests\services\test_supply_research_scheduler_jobs_feature2.py

### app\tests\websocket\test_websocket_resilience_integration.py

- File has 570 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\websocket\test_websocket_resilience_integration_testcompleteconnectionlifecycle.py
-    - app\tests\websocket\test_websocket_resilience_integration_testfailurerecoveryscenarios.py
-    - app\tests\websocket\test_websocket_resilience_integration_testproductiondeploymentreadiness.py
- 4. Split by feature being tested:
-    - app\tests\websocket\test_websocket_resilience_integration_feature1.py
-    - app\tests\websocket\test_websocket_resilience_integration_feature2.py

### app\tests\integration\test_supervisor_agent_initialization_chain.py

- File has 393 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - app\tests\integration\test_supervisor_agent_initialization_chain_feature1.py
-    - app\tests\integration\test_supervisor_agent_initialization_chain_feature2.py

### tests\websocket\test_websocket_auth.py

- File has 305 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\websocket\test_websocket_auth_testwebsocketauthentication.py
-    - tests\websocket\test_websocket_auth_testwebsockettokenvalidation.py
-    - tests\websocket\test_websocket_auth_testwebsocketauthrecovery.py
- 4. Split by feature being tested:
-    - tests\websocket\test_websocket_auth_feature1.py
-    - tests\websocket\test_websocket_auth_feature2.py

### app\tests\integration\test_multi_service_health.py

- File has 562 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - app\tests\integration\test_multi_service_health_helpers.py (5 helpers)
- 4. Split by feature being tested:
-    - app\tests\integration\test_multi_service_health_feature1.py
-    - app\tests\integration\test_multi_service_health_feature2.py

### app\tests\services\test_circuit_breaker_integration.py

- File has 435 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\services\test_circuit_breaker_integration_testllmclientcircuitbreaker.py
-    - app\tests\services\test_circuit_breaker_integration_testdatabaseclientcircuitbreaker.py
-    - app\tests\services\test_circuit_breaker_integration_testhttpclientcircuitbreaker.py
- 3. Extract helper functions:
-    - app\tests\services\test_circuit_breaker_integration_helpers.py (7 helpers)
- 4. Split by feature being tested:
-    - app\tests\services\test_circuit_breaker_integration_feature1.py
-    - app\tests\services\test_circuit_breaker_integration_feature2.py

### test_framework\decorators.py

- File has 327 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - test_framework\decorators_helpers.py (26 helpers)
- 4. Split by feature being tested:
-    - test_framework\decorators_feature1.py
-    - test_framework\decorators_feature2.py

### test_framework\real_llm_config.py

- File has 672 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - test_framework\real_llm_config_testingmode.py
-    - test_framework\real_llm_config_realllmtestmanager.py
- 3. Extract helper functions:
-    - test_framework\real_llm_config_helpers.py (40 helpers)
- 4. Split by feature being tested:
-    - test_framework\real_llm_config_feature1.py
-    - test_framework\real_llm_config_feature2.py

### tests\unified\e2e\test_oauth_proxy_staging.py

- File has 448 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - tests\unified\e2e\test_oauth_proxy_staging_helpers.py (4 helpers)
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_oauth_proxy_staging_feature1.py
-    - tests\unified\e2e\test_oauth_proxy_staging_feature2.py

### app\tests\services\test_tool_permission_business_rate.py

- File has 335 lines (limit: 300)
- Recommended splitting strategies:
- 1. Split by test categories:
-    - app\tests\services\test_tool_permission_business_rate_unit.py (unit tests)
-    - app\tests\services\test_tool_permission_business_rate_integration.py (integration tests)
-    - app\tests\services\test_tool_permission_business_rate_e2e.py (end-to-end tests)
- 2. Split by test classes:
-    - app\tests\services\test_tool_permission_business_rate_testbusinessrequirements.py
-    - app\tests\services\test_tool_permission_business_rate_testratelimiting.py
-    - app\tests\services\test_tool_permission_business_rate_testrecordtoolusage.py
- 4. Split by feature being tested:
-    - app\tests\services\test_tool_permission_business_rate_feature1.py
-    - app\tests\services\test_tool_permission_business_rate_feature2.py

### app\tests\test_api_threads_messages_critical.py

- File has 355 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - app\tests\test_api_threads_messages_critical_feature1.py
-    - app\tests\test_api_threads_messages_critical_feature2.py

### tests\e2e\test_auth_race_conditions.py

- File has 1094 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\e2e\test_auth_race_conditions_testconcurrenttokenrefreshraceconditions.py
-    - tests\e2e\test_auth_race_conditions_testmultidevicelogincollision.py
-    - tests\e2e\test_auth_race_conditions_testconcurrentsessioninvalidation.py
- 3. Extract helper functions:
-    - tests\e2e\test_auth_race_conditions_helpers.py (16 helpers)
- 4. Split by feature being tested:
-    - tests\e2e\test_auth_race_conditions_feature1.py
-    - tests\e2e\test_auth_race_conditions_feature2.py

### tests\unified\test_metrics_collection.py

- File has 492 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\test_metrics_collection_metricscollectiontestharness.py
-    - tests\unified\test_metrics_collection_testagentmetricscollection.py
-    - tests\unified\test_metrics_collection_testmetricsstoragevalidation.py
- 3. Extract helper functions:
-    - tests\unified\test_metrics_collection_helpers.py (14 helpers)
- 4. Split by feature being tested:
-    - tests\unified\test_metrics_collection_feature1.py
-    - tests\unified\test_metrics_collection_feature2.py

### tests\unified\e2e\test_real_oauth_integration.py

- File has 596 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\e2e\test_real_oauth_integration_oauthintegrationtestrunner.py
-    - tests\unified\e2e\test_real_oauth_integration_oauthintegrationtestvalidator.py
-    - tests\unified\e2e\test_real_oauth_integration_testrealoauthintegration.py
- 3. Extract helper functions:
-    - tests\unified\e2e\test_real_oauth_integration_helpers.py (5 helpers)
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_real_oauth_integration_feature1.py
-    - tests\unified\e2e\test_real_oauth_integration_feature2.py

### app\tests\integration\test_multi_agent_collaboration.py

- File has 442 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - app\tests\integration\test_multi_agent_collaboration_helpers.py (6 helpers)
- 4. Split by feature being tested:
-    - app\tests\integration\test_multi_agent_collaboration_feature1.py
-    - app\tests\integration\test_multi_agent_collaboration_feature2.py

### app\tests\core\test_async_processing_locking.py

- File has 387 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\core\test_async_processing_locking_testasyncbatchprocessorcomplete.py
-    - app\tests\core\test_async_processing_locking_testasynclockcomplete.py
- 4. Split by feature being tested:
-    - app\tests\core\test_async_processing_locking_feature1.py
-    - app\tests\core\test_async_processing_locking_feature2.py

### app\tests\examples\test_real_functionality_examples.py

- File has 432 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\examples\test_real_functionality_examples_testunittestminimalmocking.py
-    - app\tests\examples\test_real_functionality_examples_testintegrationrealcomponents.py
-    - app\tests\examples\test_real_functionality_examples_teste2erealbackend.py
- 4. Split by feature being tested:
-    - app\tests\examples\test_real_functionality_examples_feature1.py
-    - app\tests\examples\test_real_functionality_examples_feature2.py

### app\tests\core\test_agent_recovery_strategies.py

- File has 530 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\core\test_agent_recovery_strategies_testrecoverycontext.py
-    - app\tests\core\test_agent_recovery_strategies_testtriagerecoverystrategy.py
-    - app\tests\core\test_agent_recovery_strategies_testdataanalysisrecoverystrategy.py
- 4. Split by feature being tested:
-    - app\tests\core\test_agent_recovery_strategies_feature1.py
-    - app\tests\core\test_agent_recovery_strategies_feature2.py

### app\tests\database\async_transaction_patterns_improved.py

- File has 301 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - app\tests\database\async_transaction_patterns_improved_helpers.py (5 helpers)
- 4. Split by feature being tested:
-    - app\tests\database\async_transaction_patterns_improved_feature1.py
-    - app\tests\database\async_transaction_patterns_improved_feature2.py

### auth_service\tests\test_session_management.py

- File has 356 lines (limit: 300)
- Recommended splitting strategies:
- 1. Split by test categories:
-    - auth_service\tests\test_session_management_unit.py (unit tests)
-    - auth_service\tests\test_session_management_integration.py (integration tests)
-    - auth_service\tests\test_session_management_e2e.py (end-to-end tests)
- 2. Split by test classes:
-    - auth_service\tests\test_session_management_testsessioncreation.py
-    - auth_service\tests\test_session_management_testsessionvalidation.py
-    - auth_service\tests\test_session_management_testsessionexpiry.py
- 4. Split by feature being tested:
-    - auth_service\tests\test_session_management_feature1.py
-    - auth_service\tests\test_session_management_feature2.py

### tests\unified\e2e\test_database_sync_real.py

- File has 633 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_database_sync_real_feature1.py
-    - tests\unified\e2e\test_database_sync_real_feature2.py

### app\tests\services\test_demo_service.py

- File has 431 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - app\tests\services\test_demo_service_feature1.py
-    - app\tests\services\test_demo_service_feature2.py

### app\tests\services\test_apex_optimizer_tool_selection_part2.py

- File has 331 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - app\tests\services\test_apex_optimizer_tool_selection_part2_feature1.py
-    - app\tests\services\test_apex_optimizer_tool_selection_part2_feature2.py

### app\tests\unit\test_async_resource_manager.py

- File has 429 lines (limit: 300)
- Recommended splitting strategies:
- 1. Split by test categories:
-    - app\tests\unit\test_async_resource_manager_unit.py (unit tests)
-    - app\tests\unit\test_async_resource_manager_integration.py (integration tests)
-    - app\tests\unit\test_async_resource_manager_e2e.py (end-to-end tests)
- 2. Split by test classes:
-    - app\tests\unit\test_async_resource_manager_testasyncresourcemanagerbasics.py
-    - app\tests\unit\test_async_resource_manager_testasynctaskpoolbasics.py
-    - app\tests\unit\test_async_resource_manager_testconcurrencycontrol.py
- 3. Extract helper functions:
-    - app\tests\unit\test_async_resource_manager_helpers.py (8 helpers)
- 4. Split by feature being tested:
-    - app\tests\unit\test_async_resource_manager_feature1.py
-    - app\tests\unit\test_async_resource_manager_feature2.py

### app\tests\integration\test_core_features_integration.py

- File has 567 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - app\tests\integration\test_core_features_integration_feature1.py
-    - app\tests\integration\test_core_features_integration_feature2.py

### test_framework\config\config_manager.py

- File has 433 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - test_framework\config\config_manager_helpers.py (22 helpers)
- 4. Split by feature being tested:
-    - test_framework\config\config_manager_feature1.py
-    - test_framework\config\config_manager_feature2.py

### tests\unified\e2e\test_websocket_connection_lifecycle_compliant.py

- File has 487 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_websocket_connection_lifecycle_compliant_feature1.py
-    - tests\unified\e2e\test_websocket_connection_lifecycle_compliant_feature2.py

### app\tests\test_json_extraction.py

- File has 321 lines (limit: 300)
- Recommended splitting strategies:
- 1. Split by test categories:
-    - app\tests\test_json_extraction_unit.py (unit tests)
-    - app\tests\test_json_extraction_integration.py (integration tests)
-    - app\tests\test_json_extraction_e2e.py (end-to-end tests)
- 2. Split by test classes:
-    - app\tests\test_json_extraction_testjsonextraction.py
-    - app\tests\test_json_extraction_testtruncatedjsonrecovery.py
-    - app\tests\test_json_extraction_testpartialjsonextraction.py
- 4. Split by feature being tested:
-    - app\tests\test_json_extraction_feature1.py
-    - app\tests\test_json_extraction_feature2.py

### app\tests\unit\test_app_factory.py

- File has 358 lines (limit: 300)
- Recommended splitting strategies:
- 1. Split by test categories:
-    - app\tests\unit\test_app_factory_unit.py (unit tests)
-    - app\tests\unit\test_app_factory_integration.py (integration tests)
-    - app\tests\unit\test_app_factory_e2e.py (end-to-end tests)
- 2. Split by test classes:
-    - app\tests\unit\test_app_factory_testfastapiappcreation.py
-    - app\tests\unit\test_app_factory_testerrorhandlerregistration.py
-    - app\tests\unit\test_app_factory_testsecuritymiddleware.py
- 3. Extract helper functions:
-    - app\tests\unit\test_app_factory_helpers.py (6 helpers)
- 4. Split by feature being tested:
-    - app\tests\unit\test_app_factory_feature1.py
-    - app\tests\unit\test_app_factory_feature2.py

### tests\e2e\test_agent_responses_comprehensive_e2e.py

- File has 434 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\e2e\test_agent_responses_comprehensive_e2e_agentresponsetester.py
-    - tests\e2e\test_agent_responses_comprehensive_e2e_testagentresponsescomprehensivee2e.py
- 4. Split by feature being tested:
-    - tests\e2e\test_agent_responses_comprehensive_e2e_feature1.py
-    - tests\e2e\test_agent_responses_comprehensive_e2e_feature2.py

### tests\unified\e2e\test_websocket_ui_timing_integration.py

- File has 545 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\e2e\test_websocket_ui_timing_integration_timingtestevent.py
-    - tests\unified\e2e\test_websocket_ui_timing_integration_websocketuitimingtester.py
- 3. Extract helper functions:
-    - tests\unified\e2e\test_websocket_ui_timing_integration_helpers.py (4 helpers)
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_websocket_ui_timing_integration_feature1.py
-    - tests\unified\e2e\test_websocket_ui_timing_integration_feature2.py

### tests\unified\websocket\test_multi_service_websocket_coherence.py

- File has 683 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\websocket\test_multi_service_websocket_coherence_multiservicewebsockettester.py
-    - tests\unified\websocket\test_multi_service_websocket_coherence_testservicehealthandavailability.py
-    - tests\unified\websocket\test_multi_service_websocket_coherence_testcrossservicecommunication.py
- 4. Split by feature being tested:
-    - tests\unified\websocket\test_multi_service_websocket_coherence_feature1.py
-    - tests\unified\websocket\test_multi_service_websocket_coherence_feature2.py

### app\tests\core\test_async_resource_pool_management.py

- File has 359 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\core\test_async_resource_pool_management_testasyncresourcemanagercomplete.py
-    - app\tests\core\test_async_resource_pool_management_testasynctaskpoolcomplete.py
-    - app\tests\core\test_async_resource_pool_management_testasyncconnectionpoolcomplete.py
- 4. Split by feature being tested:
-    - app\tests\core\test_async_resource_pool_management_feature1.py
-    - app\tests\core\test_async_resource_pool_management_feature2.py

### tests\unified\e2e\test_auth_token_cache.py

- File has 390 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_auth_token_cache_feature1.py
-    - tests\unified\e2e\test_auth_token_cache_feature2.py

### app\tests\unified_system\test_dev_mode.py

- File has 498 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\unified_system\test_dev_mode_testdevmodeauthentication.py
-    - app\tests\unified_system\test_dev_mode_testdevmodeintegration.py
- 4. Split by feature being tested:
-    - app\tests\unified_system\test_dev_mode_feature1.py
-    - app\tests\unified_system\test_dev_mode_feature2.py

### app\tests\websocket\test_websocket_production_security.py

- File has 472 lines (limit: 300)
- Recommended splitting strategies:
- 1. Split by test categories:
-    - app\tests\websocket\test_websocket_production_security_unit.py (unit tests)
-    - app\tests\websocket\test_websocket_production_security_integration.py (integration tests)
-    - app\tests\websocket\test_websocket_production_security_e2e.py (end-to-end tests)
- 2. Split by test classes:
-    - app\tests\websocket\test_websocket_production_security_testproductioncorssecurity.py
-    - app\tests\websocket\test_websocket_production_security_testthreatpatterndetection.py
-    - app\tests\websocket\test_websocket_production_security_testratelimitingandblocking.py
- 4. Split by feature being tested:
-    - app\tests\websocket\test_websocket_production_security_feature1.py
-    - app\tests\websocket\test_websocket_production_security_feature2.py

### test_framework\test_runner.py

- File has 926 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - test_framework\test_runner_helpers.py (58 helpers)
- 4. Split by feature being tested:
-    - test_framework\test_runner_feature1.py
-    - test_framework\test_runner_feature2.py

### app\tests\services\security_service_test_mocks.py

- File has 358 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - app\tests\services\security_service_test_mocks_helpers.py (31 helpers)
- 4. Split by feature being tested:
-    - app\tests\services\security_service_test_mocks_feature1.py
-    - app\tests\services\security_service_test_mocks_feature2.py

### app\tests\routes\test_route_fixtures.py

- File has 343 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - app\tests\routes\test_route_fixtures_helpers.py (15 helpers)
- 4. Split by feature being tested:
-    - app\tests\routes\test_route_fixtures_feature1.py
-    - app\tests\routes\test_route_fixtures_feature2.py

### test_framework\test_user_journeys_integration.py

- File has 349 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - test_framework\test_user_journeys_integration_userjourneytestorchestrator.py
-    - test_framework\test_user_journeys_integration_userjourneytestreporter.py
- 3. Extract helper functions:
-    - test_framework\test_user_journeys_integration_helpers.py (5 helpers)
- 4. Split by feature being tested:
-    - test_framework\test_user_journeys_integration_feature1.py
-    - test_framework\test_user_journeys_integration_feature2.py

### app\tests\unit\test_error_recovery_integration.py

- File has 405 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\unit\test_error_recovery_integration_testenhancederrorrecoverysystem.py
-    - app\tests\unit\test_error_recovery_integration_testconveniencefunctions.py
-    - app\tests\unit\test_error_recovery_integration_testintegrationscenarios.py
- 4. Split by feature being tested:
-    - app\tests\unit\test_error_recovery_integration_feature1.py
-    - app\tests\unit\test_error_recovery_integration_feature2.py

### tests\unified\e2e\test_thread_management_ui_update.py

- File has 524 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - tests\unified\e2e\test_thread_management_ui_update_helpers.py (4 helpers)
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_thread_management_ui_update_feature1.py
-    - tests\unified\e2e\test_thread_management_ui_update_feature2.py

### tests\integration\test_cross_service_session_state_synchronization.py

- File has 585 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - tests\integration\test_cross_service_session_state_synchronization_feature1.py
-    - tests\integration\test_cross_service_session_state_synchronization_feature2.py

### app\tests\agents\test_supervisor_advanced.py

- File has 302 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - app\tests\agents\test_supervisor_advanced_helpers.py (5 helpers)
- 4. Split by feature being tested:
-    - app\tests\agents\test_supervisor_advanced_feature1.py
-    - app\tests\agents\test_supervisor_advanced_feature2.py

### tests\unified\e2e\test_websocket_user_journey_integration.py

- File has 604 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\e2e\test_websocket_user_journey_integration_websocketuserjourneytester.py
-    - tests\unified\e2e\test_websocket_user_journey_integration_testwebsocketuserjourneyintegration.py
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_websocket_user_journey_integration_feature1.py
-    - tests\unified\e2e\test_websocket_user_journey_integration_feature2.py

### tests\unified\e2e\test_rate_limiting.py

- File has 386 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\e2e\test_rate_limiting_ratelimitflowtester.py
-    - tests\unified\e2e\test_rate_limiting_ratelimitflowtester.py
- 3. Extract helper functions:
-    - tests\unified\e2e\test_rate_limiting_helpers.py (4 helpers)
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_rate_limiting_feature1.py
-    - tests\unified\e2e\test_rate_limiting_feature2.py

### app\tests\unified_system\test_error_propagation.py

- File has 737 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - app\tests\unified_system\test_error_propagation_helpers.py (5 helpers)
- 4. Split by feature being tested:
-    - app\tests\unified_system\test_error_propagation_feature1.py
-    - app\tests\unified_system\test_error_propagation_feature2.py

### tests\unified\e2e\test_first_page_load_websocket_integration.py

- File has 470 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\e2e\test_first_page_load_websocket_integration_firstpageloadwebsockettester.py
-    - tests\unified\e2e\test_first_page_load_websocket_integration_testfirstpageloadwebsocketintegration.py
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_first_page_load_websocket_integration_feature1.py
-    - tests\unified\e2e\test_first_page_load_websocket_integration_feature2.py

### tests\unified\websocket\test_basic_error_handling.py

- File has 467 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\websocket\test_basic_error_handling_errorhandlingtester.py
-    - tests\unified\websocket\test_basic_error_handling_testmalformedjsonhandling.py
-    - tests\unified\websocket\test_basic_error_handling_testvalidationerrorhandling.py
- 4. Split by feature being tested:
-    - tests\unified\websocket\test_basic_error_handling_feature1.py
-    - tests\unified\websocket\test_basic_error_handling_feature2.py

### tests\unified\test_token_expiry_cross_service.py

- File has 315 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\test_token_expiry_cross_service_testtokenexpiryrejection.py
-    - tests\unified\test_token_expiry_cross_service_testtokenrefreshcrossservice.py
-    - tests\unified\test_token_expiry_cross_service_testgraceperiodhandling.py
- 4. Split by feature being tested:
-    - tests\unified\test_token_expiry_cross_service_feature1.py
-    - tests\unified\test_token_expiry_cross_service_feature2.py

### app\tests\startup\test_migration_tracker.py

- File has 359 lines (limit: 300)
- Recommended splitting strategies:
- 1. Split by test categories:
-    - app\tests\startup\test_migration_tracker_unit.py (unit tests)
-    - app\tests\startup\test_migration_tracker_integration.py (integration tests)
-    - app\tests\startup\test_migration_tracker_e2e.py (end-to-end tests)
- 2. Split by test classes:
-    - app\tests\startup\test_migration_tracker_testmigrationtrackerinit.py
-    - app\tests\startup\test_migration_tracker_teststatemanagement.py
-    - app\tests\startup\test_migration_tracker_testfileoperations.py
- 4. Split by feature being tested:
-    - app\tests\startup\test_migration_tracker_feature1.py
-    - app\tests\startup\test_migration_tracker_feature2.py

### tests\unified\e2e\test_multi_session_management.py

- File has 415 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\e2e\test_multi_session_management_conflictresolutiontester.py
-    - tests\unified\e2e\test_multi_session_management_testmultisessionmanagement.py
- 3. Extract helper functions:
-    - tests\unified\e2e\test_multi_session_management_helpers.py (7 helpers)
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_multi_session_management_feature1.py
-    - tests\unified\e2e\test_multi_session_management_feature2.py

### tests\unified\e2e\test_real_oauth_google_flow.py

- File has 457 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\e2e\test_real_oauth_google_flow_realoauthflowtester.py
-    - tests\unified\e2e\test_real_oauth_google_flow_oauthe2etestmanager.py
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_real_oauth_google_flow_feature1.py
-    - tests\unified\e2e\test_real_oauth_google_flow_feature2.py

### test_framework\report_generators.py

- File has 391 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - test_framework\report_generators_helpers.py (7 helpers)
- 4. Split by feature being tested:
-    - test_framework\report_generators_feature1.py
-    - test_framework\report_generators_feature2.py

### app\tests\unit\test_real_auth_service_integration.py

- File has 352 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\unit\test_real_auth_service_integration_realauthservicetestfixture.py
-    - app\tests\unit\test_real_auth_service_integration_testrealtokenvalidation.py
-    - app\tests\unit\test_real_auth_service_integration_testrealuserretrieval.py
- 4. Split by feature being tested:
-    - app\tests\unit\test_real_auth_service_integration_feature1.py
-    - app\tests\unit\test_real_auth_service_integration_feature2.py

### tests\unified\test_token_validation.py

- File has 367 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\test_token_validation_testtokenvalidationflow.py
-    - tests\unified\test_token_validation_testvalidtokenaccepted.py
-    - tests\unified\test_token_validation_testexpiredtokenrejected.py
- 4. Split by feature being tested:
-    - tests\unified\test_token_validation_feature1.py
-    - tests\unified\test_token_validation_feature2.py

### tests\unified\e2e\test_service_independence.py

- File has 1262 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_service_independence_feature1.py
-    - tests\unified\e2e\test_service_independence_feature2.py

### app\tests\integration\test_database_transaction_coordination.py

- File has 488 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - app\tests\integration\test_database_transaction_coordination_helpers.py (4 helpers)
- 4. Split by feature being tested:
-    - app\tests\integration\test_database_transaction_coordination_feature1.py
-    - app\tests\integration\test_database_transaction_coordination_feature2.py

### app\tests\routes\test_supply_management.py

- File has 358 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - app\tests\routes\test_supply_management_feature1.py
-    - app\tests\routes\test_supply_management_feature2.py

### tests\unified\e2e\test_agent_failure_cascade_integration.py

- File has 396 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_agent_failure_cascade_integration_feature1.py
-    - tests\unified\e2e\test_agent_failure_cascade_integration_feature2.py

### app\tests\services\test_supply_research_service_error_handling.py

- File has 327 lines (limit: 300)
- Recommended splitting strategies:
- 1. Split by test categories:
-    - app\tests\services\test_supply_research_service_error_handling_unit.py (unit tests)
-    - app\tests\services\test_supply_research_service_error_handling_integration.py (integration tests)
-    - app\tests\services\test_supply_research_service_error_handling_e2e.py (end-to-end tests)
- 2. Split by test classes:
-    - app\tests\services\test_supply_research_service_error_handling_testerrorhandling.py
-    - app\tests\services\test_supply_research_service_error_handling_testedgecasescenarios.py
-    - app\tests\services\test_supply_research_service_error_handling_testdataconsistency.py
- 3. Extract helper functions:
-    - app\tests\services\test_supply_research_service_error_handling_helpers.py (11 helpers)
- 4. Split by feature being tested:
-    - app\tests\services\test_supply_research_service_error_handling_feature1.py
-    - app\tests\services\test_supply_research_service_error_handling_feature2.py

### app\tests\integration\test_agent_initialization_integration.py

- File has 301 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - app\tests\integration\test_agent_initialization_integration_feature1.py
-    - app\tests\integration\test_agent_initialization_integration_feature2.py

### tests\unified\test_data_factory.py

- File has 333 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\test_data_factory_testuserdata.py
-    - tests\unified\test_data_factory_testmessagedata.py
-    - tests\unified\test_data_factory_testthreaddata.py
- 3. Extract helper functions:
-    - tests\unified\test_data_factory_helpers.py (30 helpers)
- 4. Split by feature being tested:
-    - tests\unified\test_data_factory_feature1.py
-    - tests\unified\test_data_factory_feature2.py

### tests\unified\e2e\test_multi_session_isolation.py

- File has 473 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_multi_session_isolation_feature1.py
-    - tests\unified\e2e\test_multi_session_isolation_feature2.py

### tests\unified\e2e\test_real_error_recovery.py

- File has 637 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\e2e\test_real_error_recovery_circuitbreakertester.py
-    - tests\unified\e2e\test_real_error_recovery_testrealerrorrecovery.py
- 3. Extract helper functions:
-    - tests\unified\e2e\test_real_error_recovery_helpers.py (7 helpers)
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_real_error_recovery_feature1.py
-    - tests\unified\e2e\test_real_error_recovery_feature2.py

### test_framework\ultra_test_orchestrator.py

- File has 431 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - test_framework\ultra_test_orchestrator_testprofilebuilder.py
-    - test_framework\ultra_test_orchestrator_ultratestorchestrator.py
- 3. Extract helper functions:
-    - test_framework\ultra_test_orchestrator_helpers.py (11 helpers)
- 4. Split by feature being tested:
-    - test_framework\ultra_test_orchestrator_feature1.py
-    - test_framework\ultra_test_orchestrator_feature2.py

### test_framework\test_execution_engine.py

- File has 429 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - test_framework\test_execution_engine_helpers.py (15 helpers)
- 4. Split by feature being tested:
-    - test_framework\test_execution_engine_feature1.py
-    - test_framework\test_execution_engine_feature2.py

### app\tests\isolated_test_config.py

- File has 429 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\isolated_test_config_isolatedtestconfig.py
-    - app\tests\isolated_test_config_performancetestconfig.py
- 3. Extract helper functions:
-    - app\tests\isolated_test_config_helpers.py (7 helpers)
- 4. Split by feature being tested:
-    - app\tests\isolated_test_config_feature1.py
-    - app\tests\isolated_test_config_feature2.py

### app\tests\agents\test_llm_agent_e2e_performance.py

- File has 328 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - app\tests\agents\test_llm_agent_e2e_performance_helpers.py (13 helpers)
- 4. Split by feature being tested:
-    - app\tests\agents\test_llm_agent_e2e_performance_feature1.py
-    - app\tests\agents\test_llm_agent_e2e_performance_feature2.py

### app\tests\integration\test_agent_response_pipeline_e2e.py

- File has 829 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - app\tests\integration\test_agent_response_pipeline_e2e_feature1.py
-    - app\tests\integration\test_agent_response_pipeline_e2e_feature2.py

### tests\unified\websocket\test_basic_connection.py

- File has 437 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\websocket\test_basic_connection_websocketconnectiontester.py
-    - tests\unified\websocket\test_basic_connection_testbasicwebsocketconnection.py
-    - tests\unified\websocket\test_basic_connection_testwebsocketconnectionerrors.py
- 4. Split by feature being tested:
-    - tests\unified\websocket\test_basic_connection_feature1.py
-    - tests\unified\websocket\test_basic_connection_feature2.py

### app\tests\critical\test_execution_context_hashable_regression.py

- File has 347 lines (limit: 300)
- Recommended splitting strategies:
- 1. Split by test categories:
-    - app\tests\critical\test_execution_context_hashable_regression_unit.py (unit tests)
-    - app\tests\critical\test_execution_context_hashable_regression_integration.py (integration tests)
-    - app\tests\critical\test_execution_context_hashable_regression_e2e.py (end-to-end tests)
- 2. Split by test classes:
-    - app\tests\critical\test_execution_context_hashable_regression_testexecutioncontexthashableregression.py
-    - app\tests\critical\test_execution_context_hashable_regression_testdataclassserializationpatterns.py
-    - app\tests\critical\test_execution_context_hashable_regression_testerrorhandlerregressionfixes.py
- 4. Split by feature being tested:
-    - app\tests\critical\test_execution_context_hashable_regression_feature1.py
-    - app\tests\critical\test_execution_context_hashable_regression_feature2.py

### app\tests\routes\test_agent_routes.py

- File has 309 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - app\tests\routes\test_agent_routes_helpers.py (4 helpers)
- 4. Split by feature being tested:
-    - app\tests\routes\test_agent_routes_feature1.py
-    - app\tests\routes\test_agent_routes_feature2.py

### app\tests\integration\test_security_audit_trail.py

- File has 795 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - app\tests\integration\test_security_audit_trail_feature1.py
-    - app\tests\integration\test_security_audit_trail_feature2.py

### app\tests\integration\test_auth_service_dependency_resolution.py

- File has 434 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\integration\test_auth_service_dependency_resolution_authservicedependencytest.py
-    - app\tests\integration\test_auth_service_dependency_resolution_testauthservicedependencyresolution.py
- 3. Extract helper functions:
-    - app\tests\integration\test_auth_service_dependency_resolution_helpers.py (5 helpers)
- 4. Split by feature being tested:
-    - app\tests\integration\test_auth_service_dependency_resolution_feature1.py
-    - app\tests\integration\test_auth_service_dependency_resolution_feature2.py

### app\tests\integration\test_first_time_user_billing.py

- File has 314 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - app\tests\integration\test_first_time_user_billing_feature1.py
-    - app\tests\integration\test_first_time_user_billing_feature2.py

### app\tests\integration\test_jwt_token_propagation.py

- File has 429 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\integration\test_jwt_token_propagation_jwttokenpropagationtest.py
-    - app\tests\integration\test_jwt_token_propagation_testjwttokenpropagation.py
- 4. Split by feature being tested:
-    - app\tests\integration\test_jwt_token_propagation_feature1.py
-    - app\tests\integration\test_jwt_token_propagation_feature2.py

### tests\unified\e2e\test_service_startup_health_real.py

- File has 560 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - tests\unified\e2e\test_service_startup_health_real_helpers.py (4 helpers)
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_service_startup_health_real_feature1.py
-    - tests\unified\e2e\test_service_startup_health_real_feature2.py

### app\tests\critical\test_business_critical_gaps.py

- File has 444 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\critical\test_business_critical_gaps_testwebsocketconnectionresilience.py
-    - app\tests\critical\test_business_critical_gaps_testagenttaskdelegation.py
-    - app\tests\critical\test_business_critical_gaps_testllmfallbackchain.py
- 4. Split by feature being tested:
-    - app\tests\critical\test_business_critical_gaps_feature1.py
-    - app\tests\critical\test_business_critical_gaps_feature2.py

### tests\unified\e2e\test_payment_billing_accuracy.py

- File has 488 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_payment_billing_accuracy_feature1.py
-    - tests\unified\e2e\test_payment_billing_accuracy_feature2.py

### tests\unified\e2e\test_websocket_token_expiry_reconnect.py

- File has 511 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\e2e\test_websocket_token_expiry_reconnect_tokenexpiryreconnectiontester.py
-    - tests\unified\e2e\test_websocket_token_expiry_reconnect_testwebsockettokenexpiryreconnect.py
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_websocket_token_expiry_reconnect_feature1.py
-    - tests\unified\e2e\test_websocket_token_expiry_reconnect_feature2.py

### tests\unified\e2e\test_agent_lifecycle_websocket_events.py

- File has 665 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\e2e\test_agent_lifecycle_websocket_events_agentlifecycleeventtestcore.py
-    - tests\unified\e2e\test_agent_lifecycle_websocket_events_testagentlifecyclewebsocketevents.py
- 3. Extract helper functions:
-    - tests\unified\e2e\test_agent_lifecycle_websocket_events_helpers.py (12 helpers)
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_agent_lifecycle_websocket_events_feature1.py
-    - tests\unified\e2e\test_agent_lifecycle_websocket_events_feature2.py

### app\tests\integration\test_metrics_aggregation_pipeline.py

- File has 702 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - app\tests\integration\test_metrics_aggregation_pipeline_helpers.py (8 helpers)
- 4. Split by feature being tested:
-    - app\tests\integration\test_metrics_aggregation_pipeline_feature1.py
-    - app\tests\integration\test_metrics_aggregation_pipeline_feature2.py

### tests\unified\test_service_startup_dependency_chain.py

- File has 445 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - tests\unified\test_service_startup_dependency_chain_helpers.py (6 helpers)
- 4. Split by feature being tested:
-    - tests\unified\test_service_startup_dependency_chain_feature1.py
-    - tests\unified\test_service_startup_dependency_chain_feature2.py

### app\tests\services\test_permission_service_core.py

- File has 302 lines (limit: 300)
- Recommended splitting strategies:
- 1. Split by test categories:
-    - app\tests\services\test_permission_service_core_unit.py (unit tests)
-    - app\tests\services\test_permission_service_core_integration.py (integration tests)
-    - app\tests\services\test_permission_service_core_e2e.py (end-to-end tests)
- 2. Split by test classes:
-    - app\tests\services\test_permission_service_core_testpermissionserviceconstants.py
-    - app\tests\services\test_permission_service_core_testdetectdeveloperstatus.py
-    - app\tests\services\test_permission_service_core_testupdateuserrole.py
- 4. Split by feature being tested:
-    - app\tests\services\test_permission_service_core_feature1.py
-    - app\tests\services\test_permission_service_core_feature2.py

### tests\unified\test_websocket_real_connection.py

- File has 618 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\test_websocket_real_connection_websocketrealconnectiontester.py
-    - tests\unified\test_websocket_real_connection_testwebsocketrealconnection.py
- 4. Split by feature being tested:
-    - tests\unified\test_websocket_real_connection_feature1.py
-    - tests\unified\test_websocket_real_connection_feature2.py

### tests\unified\test_basic_user_flow_e2e.py

- File has 389 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\test_basic_user_flow_e2e_basicuserflowe2etester.py
-    - tests\unified\test_basic_user_flow_e2e_testharnesscontext.py
-    - tests\unified\test_basic_user_flow_e2e_testclient.py
- 4. Split by feature being tested:
-    - tests\unified\test_basic_user_flow_e2e_feature1.py
-    - tests\unified\test_basic_user_flow_e2e_feature2.py

### app\tests\critical\test_websocket_message_regression.py

- File has 569 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\critical\test_websocket_message_regression_testwebsocketmessageregression.py
-    - app\tests\critical\test_websocket_message_regression_testwebsocketerrorpropagation.py
-    - app\tests\critical\test_websocket_message_regression_teststartagentusermessagepayloadconsistency.py
- 4. Split by feature being tested:
-    - app\tests\critical\test_websocket_message_regression_feature1.py
-    - app\tests\critical\test_websocket_message_regression_feature2.py

### tests\unified\e2e\test_service_health_checks.py

- File has 318 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - tests\unified\e2e\test_service_health_checks_helpers.py (9 helpers)
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_service_health_checks_feature1.py
-    - tests\unified\e2e\test_service_health_checks_feature2.py

### tests\unified\e2e\run_e2e_tests.py

- File has 531 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\e2e\run_e2e_tests_testresult.py
-    - tests\unified\e2e\run_e2e_tests_testdiscovery.py
-    - tests\unified\e2e\run_e2e_tests_e2etestexecutor.py
- 3. Extract helper functions:
-    - tests\unified\e2e\run_e2e_tests_helpers.py (15 helpers)
- 4. Split by feature being tested:
-    - tests\unified\e2e\run_e2e_tests_feature1.py
-    - tests\unified\e2e\run_e2e_tests_feature2.py

### tests\unified\e2e\agent_response_test_utilities.py

- File has 308 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\e2e\agent_response_test_utilities_responsetesttype.py
-    - tests\unified\e2e\agent_response_test_utilities_responsetestresult.py
-    - tests\unified\e2e\agent_response_test_utilities_errorscenariotester.py
- 3. Extract helper functions:
-    - tests\unified\e2e\agent_response_test_utilities_helpers.py (8 helpers)
- 4. Split by feature being tested:
-    - tests\unified\e2e\agent_response_test_utilities_feature1.py
-    - tests\unified\e2e\agent_response_test_utilities_feature2.py

### app\tests\unit\test_permission_service_unit.py

- File has 502 lines (limit: 300)
- Recommended splitting strategies:
- 1. Split by test categories:
-    - app\tests\unit\test_permission_service_unit_unit.py (unit tests)
-    - app\tests\unit\test_permission_service_unit_integration.py (integration tests)
-    - app\tests\unit\test_permission_service_unit_e2e.py (end-to-end tests)
- 2. Split by test classes:
-    - app\tests\unit\test_permission_service_unit_testpermissionchecking.py
-    - app\tests\unit\test_permission_service_unit_testrolehierarchyandlevels.py
-    - app\tests\unit\test_permission_service_unit_testdeveloperautodetection.py
- 3. Extract helper functions:
-    - app\tests\unit\test_permission_service_unit_helpers.py (7 helpers)
- 4. Split by feature being tested:
-    - app\tests\unit\test_permission_service_unit_feature1.py
-    - app\tests\unit\test_permission_service_unit_feature2.py

### tests\unified\e2e\test_session_persistence_restart.py

- File has 676 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_session_persistence_restart_feature1.py
-    - tests\unified\e2e\test_session_persistence_restart_feature2.py

### tests\e2e\test_system_resilience.py

- File has 678 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\e2e\test_system_resilience_resiliencetestmetrics.py
-    - tests\e2e\test_system_resilience_testsystemresilience.py
- 3. Extract helper functions:
-    - tests\e2e\test_system_resilience_helpers.py (5 helpers)
- 4. Split by feature being tested:
-    - tests\e2e\test_system_resilience_feature1.py
-    - tests\e2e\test_system_resilience_feature2.py

### app\tests\agents\agent_system_test_helpers.py

- File has 367 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - app\tests\agents\agent_system_test_helpers_helpers.py (6 helpers)
- 4. Split by feature being tested:
-    - app\tests\agents\agent_system_test_helpers_feature1.py
-    - app\tests\agents\agent_system_test_helpers_feature2.py

### app\tests\e2e\test_real_llm_workflow.py

- File has 319 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\e2e\test_real_llm_workflow_testrealllmworkflow.py
-    - app\tests\e2e\test_real_llm_workflow_testrealllmconcurrentworkflow.py
-    - app\tests\e2e\test_real_llm_workflow_testrealllmerrorhandling.py
- 4. Split by feature being tested:
-    - app\tests\e2e\test_real_llm_workflow_feature1.py
-    - app\tests\e2e\test_real_llm_workflow_feature2.py

### tests\e2e\test_websocket_resilience.py

- File has 508 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - tests\e2e\test_websocket_resilience_helpers.py (10 helpers)
- 4. Split by feature being tested:
-    - tests\e2e\test_websocket_resilience_feature1.py
-    - tests\e2e\test_websocket_resilience_feature2.py

### auth_service\tests\test_security.py

- File has 520 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - auth_service\tests\test_security_testsqlinjectionprevention.py
-    - auth_service\tests\test_security_testxssprevention.py
-    - auth_service\tests\test_security_testcsrfprotection.py
- 4. Split by feature being tested:
-    - auth_service\tests\test_security_feature1.py
-    - auth_service\tests\test_security_feature2.py

### app\tests\test_business_value_fixtures.py

- File has 442 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - app\tests\test_business_value_fixtures_helpers.py (44 helpers)
- 4. Split by feature being tested:
-    - app\tests\test_business_value_fixtures_feature1.py
-    - app\tests\test_business_value_fixtures_feature2.py

### tests\unified\test_auth_backend_integration.py

- File has 395 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\test_auth_backend_integration_authbackendtestcontext.py
-    - tests\unified\test_auth_backend_integration_authbackendintegrationtester.py
-    - tests\unified\test_auth_backend_integration_testauthbackendintegration.py
- 4. Split by feature being tested:
-    - tests\unified\test_auth_backend_integration_feature1.py
-    - tests\unified\test_auth_backend_integration_feature2.py

### app\tests\e2e\test_thread_performance.py

- File has 443 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\e2e\test_thread_performance_threadloadtests.py
-    - app\tests\e2e\test_thread_performance_threadstresstests.py
-    - app\tests\e2e\test_thread_performance_threadscalabilitytests.py
- 3. Extract helper functions:
-    - app\tests\e2e\test_thread_performance_helpers.py (5 helpers)
- 4. Split by feature being tested:
-    - app\tests\e2e\test_thread_performance_feature1.py
-    - app\tests\e2e\test_thread_performance_feature2.py

### app\tests\integration\test_reliability_scale_integration.py

- File has 431 lines (limit: 300)
- Recommended splitting strategies:
- 4. Split by feature being tested:
-    - app\tests\integration\test_reliability_scale_integration_feature1.py
-    - app\tests\integration\test_reliability_scale_integration_feature2.py

### tests\unified\e2e\test_dev_launcher_startup_complete.py

- File has 513 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\unified\e2e\test_dev_launcher_startup_complete_realdevlaunchertester.py
-    - tests\unified\e2e\test_dev_launcher_startup_complete_testdevlauncherstartupcomplete.py
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_dev_launcher_startup_complete_feature1.py
-    - tests\unified\e2e\test_dev_launcher_startup_complete_feature2.py

### app\tests\performance\test_sla_compliance.py

- File has 690 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - app\tests\performance\test_sla_compliance_apiloadtester.py
-    - app\tests\performance\test_sla_compliance_websocketlatencytester.py
-    - app\tests\performance\test_sla_compliance_concurrentusertester.py
- 3. Extract helper functions:
-    - app\tests\performance\test_sla_compliance_helpers.py (19 helpers)
- 4. Split by feature being tested:
-    - app\tests\performance\test_sla_compliance_feature1.py
-    - app\tests\performance\test_sla_compliance_feature2.py

### tests\unified\e2e\test_real_unified_signup_login_chat.py

- File has 310 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - tests\unified\e2e\test_real_unified_signup_login_chat_helpers.py (8 helpers)
- 4. Split by feature being tested:
-    - tests\unified\e2e\test_real_unified_signup_login_chat_feature1.py
-    - tests\unified\e2e\test_real_unified_signup_login_chat_feature2.py

### tests\e2e\test_security_permissions.py

- File has 757 lines (limit: 300)
- Recommended splitting strategies:
- 2. Split by test classes:
-    - tests\e2e\test_security_permissions_testtenantisolation.py
-    - tests\e2e\test_security_permissions_testadmintoolauthorization.py
-    - tests\e2e\test_security_permissions_testtierbasedfeaturegating.py
- 4. Split by feature being tested:
-    - tests\e2e\test_security_permissions_feature1.py
-    - tests\e2e\test_security_permissions_feature2.py

### app\tests\services\test_tool_lifecycle_health.py

- File has 375 lines (limit: 300)
- Recommended splitting strategies:
- 3. Extract helper functions:
-    - app\tests\services\test_tool_lifecycle_health_helpers.py (31 helpers)
- 4. Split by feature being tested:
-    - app\tests\services\test_tool_lifecycle_health_feature1.py
-    - app\tests\services\test_tool_lifecycle_health_feature2.py
