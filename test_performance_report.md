# Test Suite Performance Analysis Report
Generated: 2025-08-26 01:38:57

## Summary
- **Files Analyzed**: 1377
- **Performance Issues Found**: 3708
- **Potentially Flaky Tests**: 1758

## Critical Optimization Recommendations
1. **CRITICAL**: CRITICAL: tests\test_deployment_edge_cases.py has 184.1s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
2. **HIGH**: HIGH: tests\test_deployment_performance_monitoring.py has 1.6s of sleep calls. Consider optimizing with performance helpers.
3. **CRITICAL**: CRITICAL: tests\test_deployment_performance_validation.py has 15.0s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
4. **CRITICAL**: CRITICAL: tests\test_error_handling_edge_cases.py has 15.0s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
5. **CRITICAL**: CRITICAL: tests\test_gcp_staging_startup_sequence_robustness.py has 65.0s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
6. **CRITICAL**: CRITICAL: tests\agents\test_agent_e2e_critical_performance.py has 10.2s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
7. **CRITICAL**: CRITICAL: tests\agents\test_supervisor_prompts_utils.py has 5.1s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
8. **HIGH**: HIGH: tests\clickhouse\test_corpus_generation_coverage.py has 2.1s of sleep calls. Consider optimizing with performance helpers.
9. **HIGH**: HIGH: tests\clickhouse\test_corpus_validation.py has 2.1s of sleep calls. Consider optimizing with performance helpers.
10. **CRITICAL**: CRITICAL: tests\clickhouse\test_performance_edge_cases.py has 10.0s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
11. **HIGH**: HIGH: tests\clickhouse\test_query_correctness.py has 2.1s of sleep calls. Consider optimizing with performance helpers.
12. **HIGH**: HIGH: tests\core\test_async_edge_cases_error_handling.py has 1.6s of sleep calls. Consider optimizing with performance helpers.
13. **HIGH**: HIGH: tests\core\test_async_function_utilities.py has 4.3s of sleep calls. Consider optimizing with performance helpers.
14. **HIGH**: HIGH: tests\core\test_async_processing_locking.py has 1.3s of sleep calls. Consider optimizing with performance helpers.
15. **HIGH**: HIGH: tests\core\test_async_rate_limiting_circuit_breaker.py has 4.0s of sleep calls. Consider optimizing with performance helpers.
16. **HIGH**: HIGH: tests\core\test_async_resource_pool_management.py has 1.6s of sleep calls. Consider optimizing with performance helpers.
17. **HIGH**: HIGH: tests\core\test_async_task_pool.py has 1.1s of sleep calls. Consider optimizing with performance helpers.
18. **CRITICAL**: CRITICAL: tests\core\test_base_service_mixin.py has 10.1s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
19. **HIGH**: HIGH: tests\core\test_circuit_breaker.py has 3.1s of sleep calls. Consider optimizing with performance helpers.
20. **HIGH**: HIGH: tests\core\test_reliability_mechanisms.py has 1.2s of sleep calls. Consider optimizing with performance helpers.
21. **CRITICAL**: CRITICAL: tests\critical\test_gcp_staging_database_index_creation_skipped.py has 300.3s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
22. **CRITICAL**: CRITICAL: tests\critical\test_gcp_staging_postgres_health_check_failures.py has 10.0s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
23. **CRITICAL**: CRITICAL: tests\database\test_database_connections.py has 15.0s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
24. **CRITICAL**: CRITICAL: tests\e2e\test_agent_pipeline.py has 10.0s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
25. **HIGH**: HIGH: tests\e2e\test_middleware_validation_security.py has 1.1s of sleep calls. Consider optimizing with performance helpers.
26. **HIGH**: HIGH: tests\e2e\test_multi_service.py has 2.2s of sleep calls. Consider optimizing with performance helpers.
27. **CRITICAL**: CRITICAL: tests\e2e\test_system_startup.py has 7.0s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
28. **HIGH**: HIGH: tests\integration\test_agent_database_resilience.py has 2.0s of sleep calls. Consider optimizing with performance helpers.
29. **CRITICAL**: CRITICAL: tests\integration\test_background_jobs_redis_queue.py has 15.7s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
30. **HIGH**: HIGH: tests\integration\test_cache_invalidation_basic.py has 1.1s of sleep calls. Consider optimizing with performance helpers.
31. **HIGH**: HIGH: tests\integration\test_cache_invalidation_redis.py has 2.0s of sleep calls. Consider optimizing with performance helpers.
32. **HIGH**: HIGH: tests\integration\test_circuit_breaker_service_failures.py has 4.0s of sleep calls. Consider optimizing with performance helpers.
33. **CRITICAL**: CRITICAL: tests\integration\test_core_basics_comprehensive.py has 5.7s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
34. **HIGH**: HIGH: tests\integration\test_database_pool_integration.py has 2.0s of sleep calls. Consider optimizing with performance helpers.
35. **HIGH**: HIGH: tests\integration\test_database_transaction_coordination.py has 2.0s of sleep calls. Consider optimizing with performance helpers.
36. **CRITICAL**: CRITICAL: tests\integration\test_distributed_tracing_otel.py has 16.6s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
37. **CRITICAL**: CRITICAL: tests\integration\test_first_message_error_recovery.py has 10.1s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
38. **HIGH**: HIGH: tests\integration\test_first_time_user_permissions.py has 2.0s of sleep calls. Consider optimizing with performance helpers.
39. **HIGH**: HIGH: tests\integration\test_llm_response_caching_redis.py has 2.0s of sleep calls. Consider optimizing with performance helpers.
40. **CRITICAL**: CRITICAL: tests\integration\test_metrics_pipeline_prometheus.py has 13.0s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
41. **CRITICAL**: CRITICAL: tests\integration\test_microservice_dependency_startup_sequence.py has 10.7s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
42. **HIGH**: HIGH: tests\integration\test_migration_rollback_recovery.py has 2.1s of sleep calls. Consider optimizing with performance helpers.
43. **CRITICAL**: CRITICAL: tests\integration\test_multi_service_startup_orchestration.py has 16.5s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
44. **CRITICAL**: CRITICAL: tests\integration\test_staging_external_services.py has 30.0s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
45. **HIGH**: HIGH: tests\integration\test_user_login_flows.py has 1.6s of sleep calls. Consider optimizing with performance helpers.
46. **CRITICAL**: CRITICAL: tests\integration\test_websocket_auth_cold_start.py has 13.0s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
47. **CRITICAL**: CRITICAL: tests\integration\test_websocket_auth_cold_start_extended.py has 78.0s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
48. **HIGH**: HIGH: tests\integration\test_websocket_connection_leak_detection.py has 1.1s of sleep calls. Consider optimizing with performance helpers.
49. **HIGH**: HIGH: tests\performance\test_agent_load_stress.py has 3.0s of sleep calls. Consider optimizing with performance helpers.
50. **HIGH**: HIGH: tests\performance\test_concurrent_user_performance.py has 2.8s of sleep calls. Consider optimizing with performance helpers.
51. **HIGH**: HIGH: tests\performance\test_performance_cache.py has 1.2s of sleep calls. Consider optimizing with performance helpers.
52. **HIGH**: HIGH: tests\performance\test_performance_monitoring.py has 1.1s of sleep calls. Consider optimizing with performance helpers.
53. **HIGH**: HIGH: tests\performance\test_sla_compliance.py has 2.8s of sleep calls. Consider optimizing with performance helpers.
54. **CRITICAL**: CRITICAL: tests\routes\test_websocket_advanced.py has 35.0s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
55. **CRITICAL**: CRITICAL: tests\security\test_security_middleware.py has 10.0s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
56. **HIGH**: HIGH: tests\services\test_advanced_orchestration.py has 2.0s of sleep calls. Consider optimizing with performance helpers.
57. **CRITICAL**: CRITICAL: tests\services\test_circuit_breaker_manager_comprehensive.py has 10.1s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
58. **HIGH**: HIGH: tests\services\test_database_basic_transactions.py has 2.1s of sleep calls. Consider optimizing with performance helpers.
59. **HIGH**: HIGH: tests\services\test_llm_cache_service.py has 2.0s of sleep calls. Consider optimizing with performance helpers.
60. **HIGH**: HIGH: tests\services\test_llm_provider_switching.py has 1.1s of sleep calls. Consider optimizing with performance helpers.
61. **HIGH**: HIGH: tests\services\test_repository_basic_transactions.py has 2.1s of sleep calls. Consider optimizing with performance helpers.
62. **CRITICAL**: CRITICAL: tests\services\test_scheduler_jobs_core.py has 10.0s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
63. **CRITICAL**: CRITICAL: tests\services\test_supply_research_scheduler_jobs.py has 10.3s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
64. **HIGH**: HIGH: tests\services\test_synthetic_data_service_websocket.py has 2.6s of sleep calls. Consider optimizing with performance helpers.
65. **HIGH**: HIGH: tests\startup\test_backend_server_listening_fix.py has 3.5s of sleep calls. Consider optimizing with performance helpers.
66. **HIGH**: HIGH: tests\startup\test_minimal_server_startup.py has 2.1s of sleep calls. Consider optimizing with performance helpers.
67. **HIGH**: HIGH: tests\startup\test_server_startup_listening.py has 2.5s of sleep calls. Consider optimizing with performance helpers.
68. **CRITICAL**: CRITICAL: tests\startup\test_server_startup_timeout_fix.py has 65.0s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
69. **CRITICAL**: CRITICAL: tests\unified_system\test_dev_launcher_startup.py has 14.5s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
70. **CRITICAL**: CRITICAL: tests\unified_system\test_error_propagation.py has 10.0s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
71. **HIGH**: HIGH: tests\unified_system\test_jwt_flow.py has 5.0s of sleep calls. Consider optimizing with performance helpers.
72. **HIGH**: HIGH: tests\unified_system\test_service_recovery.py has 1.8s of sleep calls. Consider optimizing with performance helpers.
73. **HIGH**: HIGH: tests\unit\test_async_rate_limiter.py has 1.1s of sleep calls. Consider optimizing with performance helpers.
74. **HIGH**: HIGH: tests\unit\test_llm_heartbeat_logging.py has 1.2s of sleep calls. Consider optimizing with performance helpers.
75. **HIGH**: HIGH: tests\websocket\test_compression_auth.py has 3.8s of sleep calls. Consider optimizing with performance helpers.
76. **HIGH**: HIGH: tests\websocket\test_memory_monitoring.py has 1.0s of sleep calls. Consider optimizing with performance helpers.
77. **HIGH**: HIGH: tests\websocket\test_message_ordering.py has 2.0s of sleep calls. Consider optimizing with performance helpers.
78. **CRITICAL**: CRITICAL: tests\websocket\test_state_synchronizer_exceptions.py has 10.0s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
79. **HIGH**: HIGH: tests\websocket\test_websocket_comprehensive.py has 2.6s of sleep calls. Consider optimizing with performance helpers.
80. **HIGH**: HIGH: tests\websocket\test_websocket_e2e_complete.py has 3.5s of sleep calls. Consider optimizing with performance helpers.
81. **HIGH**: HIGH: tests\websocket\test_websocket_integration_performance.py has 2.0s of sleep calls. Consider optimizing with performance helpers.
82. **HIGH**: HIGH: tests\integration\critical_paths\test_agent_caching_strategy.py has 2.0s of sleep calls. Consider optimizing with performance helpers.
83. **HIGH**: HIGH: tests\integration\critical_paths\test_agent_collaboration_workflow.py has 2.0s of sleep calls. Consider optimizing with performance helpers.
84. **CRITICAL**: CRITICAL: tests\integration\critical_paths\test_agent_communication_basic.py has 22.0s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
85. **HIGH**: HIGH: tests\integration\critical_paths\test_agent_config_hot_reload.py has 2.6s of sleep calls. Consider optimizing with performance helpers.
86. **HIGH**: HIGH: tests\integration\critical_paths\test_agent_error_propagation.py has 1.9s of sleep calls. Consider optimizing with performance helpers.
87. **HIGH**: HIGH: tests\integration\critical_paths\test_agent_failover_recovery_l4.py has 3.5s of sleep calls. Consider optimizing with performance helpers.
88. **CRITICAL**: CRITICAL: tests\integration\critical_paths\test_agent_metrics_collection.py has 86.0s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
89. **CRITICAL**: CRITICAL: tests\integration\critical_paths\test_agent_priority_queue.py has 274.2s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
90. **HIGH**: HIGH: tests\integration\critical_paths\test_agent_resource_allocation.py has 2.0s of sleep calls. Consider optimizing with performance helpers.
91. **CRITICAL**: CRITICAL: tests\integration\critical_paths\test_agent_timeout_cancellation.py has 10.7s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
92. **CRITICAL**: CRITICAL: tests\integration\critical_paths\test_api_gateway_orchestration_l4.py has 7.1s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
93. **CRITICAL**: CRITICAL: tests\integration\critical_paths\test_api_gateway_rate_limiting.py has 65.0s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
94. **CRITICAL**: CRITICAL: tests\integration\critical_paths\test_api_rate_limiting_enforcement.py has 148.0s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
95. **CRITICAL**: CRITICAL: tests\integration\critical_paths\test_api_rate_limiting_first_requests.py has 15.1s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
96. **HIGH**: HIGH: tests\integration\critical_paths\test_api_request_lifecycle_complete_l4.py has 4.8s of sleep calls. Consider optimizing with performance helpers.
97. **HIGH**: HIGH: tests\integration\critical_paths\test_api_response_caching.py has 1.1s of sleep calls. Consider optimizing with performance helpers.
98. **CRITICAL**: CRITICAL: tests\integration\critical_paths\test_api_timeout_cascade.py has 30.2s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
99. **HIGH**: HIGH: tests\integration\critical_paths\test_auth_config_availability.py has 2.1s of sleep calls. Consider optimizing with performance helpers.
100. **HIGH**: HIGH: tests\integration\critical_paths\test_auth_config_hot_reload.py has 1.3s of sleep calls. Consider optimizing with performance helpers.
101. **HIGH**: HIGH: tests\integration\critical_paths\test_auth_failover_scenarios_l4.py has 4.5s of sleep calls. Consider optimizing with performance helpers.
102. **HIGH**: HIGH: tests\integration\critical_paths\test_auth_flow_l4.py has 3.0s of sleep calls. Consider optimizing with performance helpers.
103. **HIGH**: HIGH: tests\integration\critical_paths\test_auth_service_circuit_breaker_cascade.py has 4.2s of sleep calls. Consider optimizing with performance helpers.
104. **CRITICAL**: CRITICAL: tests\integration\critical_paths\test_auth_service_failover_complete_l4.py has 11.9s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
105. **HIGH**: HIGH: tests\integration\critical_paths\test_auth_service_health_dependencies.py has 2.2s of sleep calls. Consider optimizing with performance helpers.
106. **HIGH**: HIGH: tests\integration\critical_paths\test_auth_service_recovery_crash.py has 3.1s of sleep calls. Consider optimizing with performance helpers.
107. **HIGH**: HIGH: tests\integration\critical_paths\test_auth_session_lifecycle_complete_l4.py has 4.2s of sleep calls. Consider optimizing with performance helpers.
108. **CRITICAL**: CRITICAL: tests\integration\critical_paths\test_auth_token_refresh_flow.py has 5.5s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
109. **CRITICAL**: CRITICAL: tests\integration\critical_paths\test_background_job_orchestration.py has 10.0s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
110. **CRITICAL**: CRITICAL: tests\integration\critical_paths\test_cache_coherence_l4.py has 6.0s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
111. **HIGH**: HIGH: tests\integration\critical_paths\test_cache_invalidation_cascade.py has 3.0s of sleep calls. Consider optimizing with performance helpers.
112. **HIGH**: HIGH: tests\integration\critical_paths\test_cache_stampede_prevention.py has 1.6s of sleep calls. Consider optimizing with performance helpers.
113. **HIGH**: HIGH: tests\integration\critical_paths\test_cache_ttl_expiration_accuracy.py has 4.1s of sleep calls. Consider optimizing with performance helpers.
114. **HIGH**: HIGH: tests\integration\critical_paths\test_circuit_breaker_cascade.py has 1.6s of sleep calls. Consider optimizing with performance helpers.
115. **CRITICAL**: CRITICAL: tests\integration\critical_paths\test_circuit_breaker_l4.py has 17.0s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
116. **HIGH**: HIGH: tests\integration\critical_paths\test_concurrent_session_management_l4.py has 2.8s of sleep calls. Consider optimizing with performance helpers.
117. **CRITICAL**: CRITICAL: tests\integration\critical_paths\test_connection_pool_management.py has 5.0s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
118. **HIGH**: HIGH: tests\integration\critical_paths\test_cors_auth_service_l4.py has 2.0s of sleep calls. Consider optimizing with performance helpers.
119. **HIGH**: HIGH: tests\integration\critical_paths\test_cross_database_transaction_consistency.py has 2.1s of sleep calls. Consider optimizing with performance helpers.
120. **CRITICAL**: CRITICAL: tests\integration\critical_paths\test_database_coordination_l2.py has 10.6s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
121. **CRITICAL**: CRITICAL: tests\integration\critical_paths\test_database_failover_recovery_flow.py has 10.0s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
122. **CRITICAL**: CRITICAL: tests\integration\critical_paths\test_database_pool_initialization.py has 6.0s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
123. **HIGH**: HIGH: tests\integration\critical_paths\test_database_read_replica_routing.py has 3.0s of sleep calls. Consider optimizing with performance helpers.
124. **CRITICAL**: CRITICAL: tests\integration\critical_paths\test_database_transaction_deadlock_resolution.py has 6.8s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
125. **HIGH**: HIGH: tests\integration\critical_paths\test_database_transaction_integrity_l4.py has 2.2s of sleep calls. Consider optimizing with performance helpers.
126. **HIGH**: HIGH: tests\integration\critical_paths\test_data_migration_integrity_l4.py has 1.0s of sleep calls. Consider optimizing with performance helpers.
127. **HIGH**: HIGH: tests\integration\critical_paths\test_data_persistence_redis.py has 1.5s of sleep calls. Consider optimizing with performance helpers.
128. **HIGH**: HIGH: tests\integration\critical_paths\test_dev_environment_chat_initialization_l4.py has 2.0s of sleep calls. Consider optimizing with performance helpers.
129. **HIGH**: HIGH: tests\integration\critical_paths\test_dev_environment_concurrent_users_l4.py has 2.0s of sleep calls. Consider optimizing with performance helpers.
130. **CRITICAL**: CRITICAL: tests\integration\critical_paths\test_dev_environment_full_flow.py has 7.0s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
131. **HIGH**: HIGH: tests\integration\critical_paths\test_dev_environment_websocket_connection_l4.py has 2.0s of sleep calls. Consider optimizing with performance helpers.
132. **HIGH**: HIGH: tests\integration\critical_paths\test_disaster_recovery_failover_l4.py has 3.0s of sleep calls. Consider optimizing with performance helpers.
133. **CRITICAL**: CRITICAL: tests\integration\critical_paths\test_distributed_auth_state_sync_l4.py has 5.1s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
134. **HIGH**: HIGH: tests\integration\critical_paths\test_enterprise_auth_integration_l4.py has 2.0s of sleep calls. Consider optimizing with performance helpers.
135. **CRITICAL**: CRITICAL: tests\integration\critical_paths\test_enterprise_resource_isolation_l4.py has 24.0s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
136. **CRITICAL**: CRITICAL: tests\integration\critical_paths\test_error_database_failures.py has 10.0s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
137. **HIGH**: HIGH: tests\integration\critical_paths\test_error_handling_recovery.py has 2.1s of sleep calls. Consider optimizing with performance helpers.
138. **CRITICAL**: CRITICAL: tests\integration\critical_paths\test_frontend_initial_auth_flow_l4.py has 17.0s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
139. **HIGH**: HIGH: tests\integration\critical_paths\test_graceful_websocket_shutdown.py has 4.3s of sleep calls. Consider optimizing with performance helpers.
140. **HIGH**: HIGH: tests\integration\critical_paths\test_health_check_cascade.py has 2.5s of sleep calls. Consider optimizing with performance helpers.
141. **HIGH**: HIGH: tests\integration\critical_paths\test_health_check_cascade_failure.py has 2.5s of sleep calls. Consider optimizing with performance helpers.
142. **CRITICAL**: CRITICAL: tests\integration\critical_paths\test_heartbeat_mechanism.py has 92.6s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
143. **CRITICAL**: CRITICAL: tests\integration\critical_paths\test_integration_failures_audit.py has 7.6s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
144. **HIGH**: HIGH: tests\integration\critical_paths\test_job_concurrency_limits.py has 4.0s of sleep calls. Consider optimizing with performance helpers.
145. **CRITICAL**: CRITICAL: tests\integration\critical_paths\test_job_progress_tracking.py has 34.6s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
146. **CRITICAL**: CRITICAL: tests\integration\critical_paths\test_job_queue_priority_processing.py has 44.0s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
147. **CRITICAL**: CRITICAL: tests\integration\critical_paths\test_job_retry_with_dead_letter.py has 88.7s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
148. **CRITICAL**: CRITICAL: tests\integration\critical_paths\test_job_scheduling_accuracy.py has 10.0s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
149. **CRITICAL**: CRITICAL: tests\integration\critical_paths\test_jwt_refresh_websocket.py has 19.0s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
150. **HIGH**: HIGH: tests\integration\critical_paths\test_jwt_token_propagation_l4.py has 3.0s of sleep calls. Consider optimizing with performance helpers.
151. **CRITICAL**: CRITICAL: tests\integration\critical_paths\test_llm_provider_failover.py has 31.1s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
152. **HIGH**: HIGH: tests\integration\critical_paths\test_message_processing_dlq.py has 4.5s of sleep calls. Consider optimizing with performance helpers.
153. **HIGH**: HIGH: tests\integration\critical_paths\test_message_queue_overflow_recovery.py has 3.1s of sleep calls. Consider optimizing with performance helpers.
154. **HIGH**: HIGH: tests\integration\critical_paths\test_message_queue_processing_pipeline.py has 3.0s of sleep calls. Consider optimizing with performance helpers.
155. **CRITICAL**: CRITICAL: tests\integration\critical_paths\test_metrics_pipeline_l4.py has 37.0s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
156. **CRITICAL**: CRITICAL: tests\integration\critical_paths\test_multi_service_startup_sequence.py has 11.0s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
157. **HIGH**: HIGH: tests\integration\critical_paths\test_payment_processing_e2e_l4.py has 1.1s of sleep calls. Consider optimizing with performance helpers.
158. **CRITICAL**: CRITICAL: tests\integration\critical_paths\test_peak_load_autoscaling_l4.py has 5.7s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
159. **HIGH**: HIGH: tests\integration\critical_paths\test_performance_scalability_l2.py has 1.6s of sleep calls. Consider optimizing with performance helpers.
160. **HIGH**: HIGH: tests\integration\critical_paths\test_postgres_connection_pool_exhaustion.py has 1.1s of sleep calls. Consider optimizing with performance helpers.
161. **CRITICAL**: CRITICAL: tests\integration\critical_paths\test_rate_limiting_load_protection.py has 6.5s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
162. **CRITICAL**: CRITICAL: tests\integration\critical_paths\test_redis_cluster_coordination_l4.py has 6.0s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
163. **CRITICAL**: CRITICAL: tests\integration\critical_paths\test_redis_memory_pressure_eviction.py has 65.1s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
164. **HIGH**: HIGH: tests\integration\critical_paths\test_redis_session_management_flow.py has 5.0s of sleep calls. Consider optimizing with performance helpers.
165. **HIGH**: HIGH: tests\integration\critical_paths\test_redis_websocket_state_sync.py has 3.1s of sleep calls. Consider optimizing with performance helpers.
166. **HIGH**: HIGH: tests\integration\critical_paths\test_security_breach_response_l4.py has 2.5s of sleep calls. Consider optimizing with performance helpers.
167. **HIGH**: HIGH: tests\integration\critical_paths\test_service_mesh_l4.py has 1.9s of sleep calls. Consider optimizing with performance helpers.
168. **HIGH**: HIGH: tests\integration\critical_paths\test_session_cleanup.py has 1.7s of sleep calls. Consider optimizing with performance helpers.
169. **HIGH**: HIGH: tests\integration\critical_paths\test_session_invalidation_cascade.py has 2.0s of sleep calls. Consider optimizing with performance helpers.
170. **CRITICAL**: CRITICAL: tests\integration\critical_paths\test_session_management_basic.py has 10.0s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
171. **HIGH**: HIGH: tests\integration\critical_paths\test_session_persistence_restart.py has 5.0s of sleep calls. Consider optimizing with performance helpers.
172. **HIGH**: HIGH: tests\integration\critical_paths\test_session_validation.py has 1.6s of sleep calls. Consider optimizing with performance helpers.
173. **HIGH**: HIGH: tests\integration\critical_paths\test_staging_worker_startup_validation.py has 2.7s of sleep calls. Consider optimizing with performance helpers.
174. **HIGH**: HIGH: tests\integration\critical_paths\test_startup_manager_integration.py has 3.7s of sleep calls. Consider optimizing with performance helpers.
175. **CRITICAL**: CRITICAL: tests\integration\critical_paths\test_system_startup_sequences_l4.py has 6.5s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
176. **HIGH**: HIGH: tests\integration\critical_paths\test_token_validation_chain_complete_l4.py has 2.5s of sleep calls. Consider optimizing with performance helpers.
177. **CRITICAL**: CRITICAL: tests\integration\critical_paths\test_user_state_persistence_complete_l4.py has 6.0s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
178. **CRITICAL**: CRITICAL: tests\integration\critical_paths\test_webhook_delivery_reliability.py has 27.5s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
179. **HIGH**: HIGH: tests\integration\critical_paths\test_websocket_connection_draining.py has 1.6s of sleep calls. Consider optimizing with performance helpers.
180. **HIGH**: HIGH: tests\integration\critical_paths\test_websocket_heartbeat_monitoring.py has 2.0s of sleep calls. Consider optimizing with performance helpers.
181. **CRITICAL**: CRITICAL: tests\integration\critical_paths\test_websocket_heartbeat_zombie.py has 140.2s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
182. **CRITICAL**: CRITICAL: tests\integration\critical_paths\test_websocket_load_balancing.py has 7.0s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
183. **CRITICAL**: CRITICAL: tests\integration\critical_paths\test_websocket_load_balancing_l4.py has 6.5s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
184. **HIGH**: HIGH: tests\integration\critical_paths\test_websocket_message_delivery_guarantees_l4.py has 2.0s of sleep calls. Consider optimizing with performance helpers.
185. **HIGH**: HIGH: tests\integration\critical_paths\test_websocket_reconnection_resilience_l4.py has 3.1s of sleep calls. Consider optimizing with performance helpers.
186. **CRITICAL**: CRITICAL: tests\integration\critical_paths\test_websocket_resilience_l4.py has 9.0s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
187. **HIGH**: HIGH: tests\integration\critical_paths\test_websocket_state_recovery_restart.py has 3.0s of sleep calls. Consider optimizing with performance helpers.
188. **CRITICAL**: CRITICAL: tests\integration\critical_paths\test_websocket_unified_critical.py has 6.3s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
189. **HIGH**: HIGH: tests\integration\staging_config\test_redis_lifecycle.py has 1.5s of sleep calls. Consider optimizing with performance helpers.
190. **CRITICAL**: CRITICAL: tests\integration\red_team\tier1_catastrophic\test_agent_lifecycle_management.py has 11.2s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
191. **CRITICAL**: CRITICAL: tests\integration\red_team\tier1_catastrophic\test_api_gateway_rate_limiting_accuracy.py has 6.0s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
192. **HIGH**: HIGH: tests\integration\red_team\tier1_catastrophic\test_database_migration_failure_recovery.py has 2.0s of sleep calls. Consider optimizing with performance helpers.
193. **CRITICAL**: CRITICAL: tests\integration\red_team\tier1_catastrophic\test_postgresql_connection_pool_exhaustion.py has 6.0s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
194. **CRITICAL**: CRITICAL: tests\integration\red_team\tier1_catastrophic\test_service_discovery_failure_cascades.py has 6.1s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
195. **CRITICAL**: CRITICAL: tests\integration\red_team\tier1_catastrophic\test_user_session_persistence_restart.py has 7.1s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
196. **HIGH**: HIGH: tests\integration\red_team\tier1_catastrophic\test_websocket_authentication_integration.py has 4.0s of sleep calls. Consider optimizing with performance helpers.
197. **CRITICAL**: CRITICAL: tests\integration\red_team\tier1_catastrophic\test_websocket_message_broadcasting.py has 5.9s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
198. **HIGH**: HIGH: tests\integration\red_team\tier2_3_security_performance\test_performance_bottlenecks.py has 2.9s of sleep calls. Consider optimizing with performance helpers.
199. **CRITICAL**: CRITICAL: tests\integration\red_team\tier2_major_failures\test_background_job_processing.py has 9.0s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
200. **CRITICAL**: CRITICAL: tests\integration\red_team\tier2_major_failures\test_circuit_breaker_state_management.py has 11.6s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
201. **CRITICAL**: CRITICAL: tests\integration\red_team\tier2_major_failures\test_clickhouse_data_ingestion_pipeline.py has 19.0s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
202. **HIGH**: HIGH: tests\integration\red_team\tier2_major_failures\test_graceful_degradation.py has 2.1s of sleep calls. Consider optimizing with performance helpers.
203. **CRITICAL**: CRITICAL: tests\integration\red_team\tier2_major_failures\test_redis_session_store_consistency.py has 18.0s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
204. **CRITICAL**: CRITICAL: tests\integration\red_team\tier2_major_failures\test_transaction_rollback_coordination.py has 10.0s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
205. **CRITICAL**: CRITICAL: tests\unit\core\test_error_handling_enhanced.py has 10.0s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
206. **CRITICAL**: CRITICAL: tests\unit\core\resilience\test_unified_circuit_breaker.py has 7.6s of sleep calls. Consider using fast_test decorator or mocking time.sleep.
207. **MEDIUM**: MEDIUM: Found LLM calls in 72 test files. Consider using mock LLM responses for faster testing.
208. **LOW**: LOW: Found 14 large test files (>50KB). Consider splitting into smaller, focused test files.

## Performance Pattern Analysis
### Sleep Calls
- **Occurrences**: 1576
- **Files Affected**: 453

### Network Calls
- **Occurrences**: 28
- **Files Affected**: 13

### Database Operations
- **Occurrences**: 1563
- **Files Affected**: 206

### Llm Calls
- **Occurrences**: 354
- **Files Affected**: 72

### File Operations
- **Occurrences**: 187
- **Files Affected**: 62

## Potentially Flaky Tests
Tests that may be unreliable due to timing, randomness, or external dependencies:

### tests\test_basic_health_endpoint.py
- `test_basic_health_endpoint_startup_timeout` (line 200) - Indicators: time\.time\(\)

### tests\test_clickhouse_client_comprehensive.py
- `test_is_healthy_stale_check` (line 134) - Indicators: datetime\.now\(\)
- `test_query_with_different_parameter_types` (line 144) - Indicators: datetime\.now\(\)
- `test_concurrent_operations` (line 166) - Indicators: datetime\.now\(\)

### tests\test_comprehensive_database_operations.py
- `test_connection_pool_efficiency` (line 64) - Indicators: time\.time\(\)
- `test_connection_pool_statistics` (line 79) - Indicators: time\.time\(\)
- `test_transaction_commit_rollback` (line 93) - Indicators: time\.time\(\)
- `test_query_optimization_timing` (line 138) - Indicators: time\.time\(\)
- `test_bulk_insert_performance` (line 157) - Indicators: time\.time\(\)
- `test_schema_migration_simulation` (line 177) - Indicators: time\.time\(\)
- `test_replication_lag_monitoring` (line 269) - Indicators: time\.time\(\)
- `test_concurrent_operations` (line 288) - Indicators: time\.time\(\)
- `test_index_performance_comparison` (line 330) - Indicators: time\.time\(\)
- `test_index_usage_verification` (line 349) - Indicators: time\.time\(\)
- `test_query_performance_monitoring` (line 408) - Indicators: time\.time\(\)
- `test_resource_usage_tracking` (line 435) - Indicators: time\.time\(\)

### tests\test_deployment_edge_cases.py
- `test_performance_without_cpu_boost` (line 306) - Indicators: time\.time\(\)
- `test_concurrent_cpu_operations_no_boost` (line 338) - Indicators: threading\., time\.time\(\)
- `test_cpu_throttling_detection` (line 377) - Indicators: time\.time\(\)

### tests\test_deployment_performance_monitoring.py
- `test_continuous_memory_monitoring` (line 47) - Indicators: time\.time\(\)
- `test_real_time_performance_dashboard` (line 137) - Indicators: time\.time\(\)
- `test_resource_utilization_trending` (line 231) - Indicators: time\.time\(\)

### tests\test_deployment_performance_validation.py
- `test_startup_within_timeout_limits` (line 33) - Indicators: time\.time\(\)
- `test_startup_timeout_detection_and_recovery` (line 66) - Indicators: time\.time\(\)
- `test_startup_progress_monitoring` (line 92) - Indicators: time\.time\(\)
- `test_cpu_optimization_effectiveness` (line 174) - Indicators: time\.time\(\)
- `test_resource_limits_compliance` (line 192) - Indicators: time\.time\(\)
- `test_memory_leak_prevention` (line 224) - Indicators: time\.time\(\)
- `test_health_endpoint_response_time` (line 269) - Indicators: time\.time\(\)
- `test_ready_endpoint_performance` (line 305) - Indicators: time\.time\(\)
- `test_health_endpoint_under_load` (line 327) - Indicators: time\.time\(\)
- `test_probe_failure_recovery` (line 479) - Indicators: time\.time\(\)
- `test_probe_timeout_handling` (line 493) - Indicators: time\.time\(\)

### tests\test_error_handling_edge_cases.py
- `test_file_system_edge_cases` (line 209) - Indicators: tempfile\.
- `test_config_parsing_edge_cases` (line 226) - Indicators: tempfile\.

### tests\test_gcp_staging_api_endpoint_availability.py
- `test_staging_environment_route_validation` (line 342) - Indicators: os\.environ
- `test_gcp_cloud_run_route_accessibility` (line 371) - Indicators: os\.environ

### tests\test_gcp_staging_clickhouse_secrets_formatting.py
- `test_staging_environment_clickhouse_strict_validation` (line 380) - Indicators: os\.environ

### tests\test_gcp_staging_clickhouse_url_validation.py
- `test_clickhouse_host_environment_variable_parsing` (line 152) - Indicators: os\.environ
- `test_clickhouse_database_construction_with_malformed_config` (line 176) - Indicators: os\.environ
- `test_staging_environment_clickhouse_url_strict_validation` (line 232) - Indicators: os\.environ

### tests\test_gcp_staging_database_auth_failures.py
- `test_auth_service_postgres_connection_failure` (line 170) - Indicators: os\.environ
- `test_staging_environment_credential_requirements` (line 195) - Indicators: os\.environ

### tests\test_gcp_staging_migration_lock_issues.py
- `test_staging_migration_lock_configuration` (line 433) - Indicators: os\.environ

### tests\test_gcp_staging_redis_connection_issues.py
- `test_staging_environment_redis_requirements` (line 322) - Indicators: os\.environ

### tests\test_gcp_staging_secret_key_validation.py
- `test_secret_key_too_short_under_32_characters` (line 28) - Indicators: os\.environ
- `test_secret_key_missing_entirely` (line 59) - Indicators: os\.environ
- `test_secret_key_insecure_default_values` (line 84) - Indicators: os\.environ
- `test_secret_key_minimum_entropy_requirements` (line 121) - Indicators: os\.environ
- `test_jwt_secret_missing_when_secret_key_present` (line 215) - Indicators: os\.environ
- `test_jwt_secret_different_from_secret_key` (line 244) - Indicators: os\.environ
- `test_jwt_secret_insufficient_length` (line 273) - Indicators: os\.environ
- `test_config_system_rejects_invalid_secret_key` (line 320) - Indicators: os\.environ
- `test_staging_environment_secret_validation_strictness` (line 337) - Indicators: os\.environ
- `test_secret_key_generation_helper_validation` (line 362) - Indicators: os\.environ

### tests\test_gcp_staging_startup_sequence_robustness.py
- `test_staging_startup_validation_comprehensive` (line 416) - Indicators: os\.environ
- `test_staging_startup_performance_requirements` (line 442) - Indicators: os\.environ, time\.time\(\)

### tests\test_health_monitor_checks.py
- `test_thread_management_health` (line 618) - Indicators: threading\.
- `test_environment_configuration_health` (line 636) - Indicators: threading\.

### tests\test_imports.py
- `test_import_performance` (line 237) - Indicators: time\.time\(\)

### tests\test_iteration3_clickhouse_control_character_failures.py
- `test_clickhouse_connection_string_building_with_unsanitized_components` (line 262) - Indicators: os\.environ
- `test_staging_environment_clickhouse_strict_control_character_validation` (line 286) - Indicators: os\.environ

### tests\test_iteration3_integration_failure_scenarios.py
- `test_health_check_fails_due_to_password_corruption_and_missing_methods` (line 26) - Indicators: os\.environ
- `test_staging_deployment_cascade_failure_all_three_issues` (line 72) - Indicators: os\.environ
- `test_system_startup_blocked_by_all_three_persistent_issues` (line 113) - Indicators: os\.environ
- `test_error_propagation_through_system_layers` (line 168) - Indicators: os\.environ
- `test_recovery_mechanisms_fail_due_to_compound_issues` (line 281) - Indicators: os\.environ
- `test_failsafe_mechanisms_bypass_all_three_issues` (line 334) - Indicators: os\.environ

### tests\test_iteration3_password_sanitization_failures.py
- `test_staging_password_entropy_validation` (line 313) - Indicators: os\.environ

### tests\test_migration_staging_configuration_issues.py
- `test_database_schema_initialization_migration_dependency_fails` (line 152) - Indicators: os\.environ
- `test_migration_file_loading_with_missing_alembic_ini_fails` (line 199) - Indicators: os\.environ
- `test_staging_deployment_alembic_environment_setup_fails` (line 247) - Indicators: os\.environ
- `test_relative_vs_absolute_path_resolution_fails` (line 307) - Indicators: os\.environ
- `test_alembic_ini_file_permissions_in_deployment_fails` (line 339) - Indicators: os\.environ

### tests\test_os_environ_violations.py
- `test_no_direct_os_environ_access` (line 171) - Indicators: os\.environ
- `test_no_os_getenv_usage` (line 213) - Indicators: os\.environ
- `test_no_environ_get_usage` (line 254) - Indicators: os\.environ
- `test_justified_env_access_has_markers` (line 294) - Indicators: os\.environ
- `test_env_access_patterns_consistency` (line 346) - Indicators: os\.environ

### tests\test_redis_connection_staging_issues.py
- `test_redis_initialization_with_proper_async_handling` (line 40) - Indicators: os\.environ
- `test_redis_async_connection_with_environment_variables_works` (line 84) - Indicators: os\.environ
- `test_redis_fallback_behavior_works_correctly` (line 131) - Indicators: os\.environ
- `test_redis_connection_pool_configuration_scoping_fails` (line 178) - Indicators: os\.environ
- `test_redis_health_check_with_environment_detection_fails` (line 222) - Indicators: os\.environ
- `test_redis_configuration_loading_order_fails` (line 272) - Indicators: os\.environ
- `test_redis_manager_singleton_initialization_scoping_fails` (line 321) - Indicators: os\.environ
- `test_redis_retry_mechanism_with_scoping_fails` (line 363) - Indicators: os\.environ

### tests\test_startup_issues_validation.py
- `test_environment_checker_uses_correct_model` (line 66) - Indicators: os\.environ
- `test_execution_monitor_has_start_monitoring` (line 89) - Indicators: os\.environ
- `test_startup_module_imports` (line 191) - Indicators: os\.environ
- `test_startup_checks_can_run` (line 200) - Indicators: os\.environ

### tests\test_websocket_comprehensive.py
- `test_message_ordering` (line 301) - Indicators: time\.time\(\)
- `test_binary_message_handling` (line 335) - Indicators: time\.time\(\)
- `test_performance_under_load` (line 451) - Indicators: time\.time\(\)

### tests\agents\test_agent_async_mock_improvements.py
- `test_performance_with_proper_mocks` (line 154) - Indicators: time\.time\(\)
- `test_memory_efficient_async_mocks` (line 180) - Indicators: time\.time\(\)

### tests\agents\test_agent_e2e_critical_performance.py
- `test_10_performance_and_timeout_handling` (line 188) - Indicators: datetime\.now\(\)
- `test_load_balancing_and_degradation` (line 209) - Indicators: datetime\.now\(\)

### tests\agents\test_agent_orchestration_comprehensive.py
- `test_parallel_agent_coordination` (line 249) - Indicators: time\.time\(\)
- `test_agent_failure_propagation_patterns` (line 274) - Indicators: time\.time\(\)

### tests\agents\test_agent_state_recovery_comprehensive.py
- `test_concurrent_state_operations` (line 177) - Indicators: time\.time\(\)
- `test_state_cleanup_and_garbage_collection` (line 274) - Indicators: time\.time\(\)
- `test_high_frequency_state_updates` (line 444) - Indicators: time\.time\(\)

### tests\agents\test_data_sub_agent_core.py
- `test_validate_required_fields` (line 178) - Indicators: datetime\.now\(\)
- `test_validate_missing_fields` (line 194) - Indicators: datetime\.now\(\)

### tests\agents\test_error_handler_global.py
- `test_decorator_retry_delay` (line 273) - Indicators: time\.time\(\)

### tests\agents\test_llm_agent_advanced_integration.py
- `test_concurrent_request_handling` (line 56) - Indicators: time\.time\(\)
- `test_performance_metrics` (line 88) - Indicators: time\.time\(\)

### tests\agents\test_llm_agent_basic_operations.py
- `test_multi_agent_coordination` (line 152) - Indicators: time\.time\(\)
- `test_performance_metrics` (line 164) - Indicators: time\.time\(\)

### tests\agents\test_llm_agent_e2e_performance.py
- `test_performance_metrics` (line 61) - Indicators: time\.time\(\)
- `test_error_recovery` (line 79) - Indicators: time\.time\(\)
- `test_flow_performance_benchmarks` (line 161) - Indicators: time\.time\(\)
- `test_high_load_scenarios` (line 173) - Indicators: time\.time\(\)

### tests\agents\test_llm_agent_state_persistence.py
- `test_concurrent_state_operations` (line 160) - Indicators: random\.

### tests\agents\test_multi_agent_coordination_performance.py
- `test_sequential_agent_coordination` (line 58) - Indicators: time\.time\(\)
- `test_parallel_agent_coordination` (line 137) - Indicators: time\.time\(\)
- `test_agent_failure_recovery_coordination` (line 207) - Indicators: time\.time\(\)
- `test_performance_under_high_concurrency` (line 376) - Indicators: time\.time\(\)

### tests\agents\test_supply_researcher_infrastructure.py
- `test_performance_metrics_collection` (line 74) - Indicators: datetime\.now\(\)
- `test_health_check_endpoints` (line 153) - Indicators: datetime\.now\(\)

### tests\agents\test_supply_researcher_management.py
- `test_schedule_frequency_calculations` (line 26) - Indicators: datetime\.now\(\)

### tests\agents\test_triage_caching_async.py
- `test_cache_hit_performance` (line 67) - Indicators: datetime\.now\(\)
- `test_cache_invalidation_scenarios` (line 93) - Indicators: datetime\.now\(\)

### tests\agents\test_triage_edge_performance.py
- `test_request_processing_performance` (line 119) - Indicators: datetime\.now\(\)
- `test_memory_efficiency` (line 144) - Indicators: datetime\.now\(\)
- `test_triage_result_comprehensive_validation` (line 199) - Indicators: datetime\.now\(\)

### tests\agents\test_websocket_agent_communication_enhanced.py
- `test_websocket_rate_limiting_for_agent_updates` (line 203) - Indicators: time\.time\(\)
- `test_websocket_performance_monitoring` (line 372) - Indicators: time\.time\(\)

### tests\auth_integration\test_jwt_secret_consistency.py
- `test_both_services_use_same_jwt_secret_key_env_var` (line 25) - Indicators: os\.environ
- `test_jwt_secret_key_takes_priority_over_jwt_secret` (line 46) - Indicators: os\.environ
- `test_auth_service_jwt_handler_uses_correct_secret` (line 63) - Indicators: os\.environ
- `test_token_validation_consistency` (line 83) - Indicators: os\.environ
- `test_environment_specific_secret_priority` (line 105) - Indicators: os\.environ
- `test_development_fallback_when_no_secrets` (line 129) - Indicators: os\.environ
- `test_staging_production_require_secret` (line 143) - Indicators: os\.environ
- `test_auth_client_and_auth_service_consistency` (line 174) - Indicators: os\.environ
- `test_backend_auth_integration_uses_same_secret` (line 197) - Indicators: os\.environ

### tests\clickhouse\test_clickhouse_performance.py
- `test_batch_insert_performance` (line 30) - Indicators: time\.time\(\)
- `test_query_performance_with_indexes` (line 119) - Indicators: time\.time\(\)
- `test_query_interceptor_statistics` (line 171) - Indicators: time\.time\(\)

### tests\clickhouse\test_corpus_generation_coverage.py
- `test_workload_distribution_tracking` (line 153) - Indicators: datetime\.now\(\)

### tests\clickhouse\test_performance_edge_cases.py
- `test_query_with_large_result_set` (line 62) - Indicators: datetime\.now\(\)
- `test_statistics_query_on_million_records` (line 75) - Indicators: datetime\.now\(\)
- `test_time_window_query_optimization` (line 105) - Indicators: datetime\.now\(\)
- `test_null_values_in_nested_arrays` (line 145) - Indicators: datetime\.now\(\)
- `test_zero_standard_deviation_handling` (line 158) - Indicators: datetime\.now\(\)
- `test_malformed_record_validation` (line 170) - Indicators: datetime\.now\(\)
- `test_statistics_with_empty_data` (line 287) - Indicators: datetime\.now\(\)
- `test_statistics_with_single_value` (line 296) - Indicators: datetime\.now\(\)
- `test_trend_detection_insufficient_data` (line 307) - Indicators: datetime\.now\(\)
- `test_correlation_with_constant_values` (line 316) - Indicators: datetime\.now\(\)
- `test_seasonality_insufficient_data` (line 332) - Indicators: datetime\.now\(\)
- `test_outlier_detection_small_dataset` (line 344) - Indicators: datetime\.now\(\)

### tests\clickhouse\test_query_correctness.py
- `test_anomaly_detection_query_structure` (line 360) - Indicators: datetime\.now\(\)
- `test_nested_array_access_pattern` (line 671) - Indicators: datetime\.now\(\)
- `test_nested_array_existence_check` (line 697) - Indicators: datetime\.now\(\)
- `test_null_safety_in_calculations` (line 726) - Indicators: datetime\.now\(\)

### tests\config\test_config_environment.py
- `test_get_environment_testing` (line 87) - Indicators: os\.environ
- `test_get_environment_cloud_run_detected` (line 98) - Indicators: os\.environ
- `test_get_environment_explicit_environment_var` (line 125) - Indicators: os\.environ
- `test_testing_environment_takes_precedence` (line 149) - Indicators: os\.environ
- `test_create_config_production` (line 187) - Indicators: os\.environ
- `test_create_config_staging` (line 200) - Indicators: os\.environ
- `test_create_config_testing` (line 212) - Indicators: os\.environ
- `test_cloud_run_detection_with_k_service` (line 282) - Indicators: os\.environ
- `test_app_engine_detection` (line 297) - Indicators: os\.environ
- `test_google_cloud_project_detection` (line 312) - Indicators: os\.environ
- `test_logger_initialization` (line 334) - Indicators: os\.environ
- `test_multiple_environment_detections_consistent` (line 370) - Indicators: time\.time\(\)
- `test_config_creation_performance` (line 382) - Indicators: time\.time\(\)
- `test_environment_variable_unicode_handling` (line 397) - Indicators: os\.environ, time\.time\(\)

### tests\config\test_config_loader.py
- `test_detect_cloud_run_environment_with_k_service` (line 85) - Indicators: os\.environ
- `test_detect_cloud_run_environment_staging_pattern` (line 98) - Indicators: os\.environ
- `test_detect_cloud_run_environment_not_present` (line 110) - Indicators: os\.environ
- `test_detect_app_engine_environment_standard` (line 118) - Indicators: os\.environ
- `test_detect_app_engine_environment_flex` (line 130) - Indicators: os\.environ
- `test_detect_kubernetes_environment` (line 142) - Indicators: os\.environ
- `test_detect_multiple_cloud_environments_precedence` (line 155) - Indicators: os\.environ
- `test_load_config_from_environment_success` (line 187) - Indicators: os\.environ
- `test_load_config_from_environment_missing_variables` (line 216) - Indicators: os\.environ
- `test_load_config_from_environment_type_conversion` (line 237) - Indicators: os\.environ
- `test_load_config_environment_override_defaults` (line 295) - Indicators: os\.environ
- `test_validate_required_config_success` (line 328) - Indicators: os\.environ
- `test_fallback_to_default_configuration` (line 438) - Indicators: os\.environ
- `test_fallback_configuration_hierarchy` (line 464) - Indicators: os\.environ
- `test_graceful_degradation_partial_config_failure` (line 499) - Indicators: os\.environ
- `test_config_load_error_creation` (line 524) - Indicators: os\.environ
- `test_config_loader_type_conversion_errors` (line 542) - Indicators: os\.environ
- `test_config_loading_performance_large_environment` (line 591) - Indicators: os\.environ, time\.time\(\)
- `test_config_validation_performance` (line 615) - Indicators: os\.environ, time\.time\(\)
- `test_cloud_environment_detection_caching` (line 631) - Indicators: os\.environ, time\.time\(\)

### tests\config\test_unified_config_e2e.py
- `test_fresh_startup_loads_config` (line 25) - Indicators: os\.environ
- `test_staging_environment_bootstrap` (line 45) - Indicators: os\.environ
- `test_production_environment_security` (line 63) - Indicators: os\.environ
- `test_database_connection_lifecycle` (line 82) - Indicators: os\.environ
- `test_database_pool_behavior` (line 99) - Indicators: os\.environ
- `test_development_to_staging_transition` (line 298) - Indicators: os\.environ
- `test_pr_environment_detection` (line 319) - Indicators: os\.environ
- `test_complete_config_validation` (line 339) - Indicators: os\.environ
- `test_config_caching_performance` (line 385) - Indicators: time\.time\(\)
- `test_hot_reload_performance` (line 402) - Indicators: time\.time\(\)
- `test_recovery_from_corrupt_config` (line 417) - Indicators: time\.time\(\)
- `test_fallback_chain_for_critical_services` (line 447) - Indicators: os\.environ
- `test_environment_overrides_visibility` (line 498) - Indicators: os\.environ

### tests\config\test_unified_config_integration.py
- `test_database_url_retrieval_from_config` (line 28) - Indicators: os\.environ
- `test_sync_engine_creation_uses_config` (line 37) - Indicators: os\.environ
- `test_startup_fallback_on_config_error` (line 343) - Indicators: os\.environ
- `test_database_and_cache_config_alignment` (line 361) - Indicators: os\.environ
- `test_database_fallback_on_config_error` (line 444) - Indicators: os\.environ
- `test_redis_graceful_degradation` (line 454) - Indicators: os\.environ
- `test_cache_defaults_on_config_error` (line 468) - Indicators: os\.environ

### tests\config\test_unified_config_unit.py
- `test_singleton_pattern` (line 23) - Indicators: os\.environ
- `test_config_loading_caches_result` (line 29) - Indicators: os\.environ
- `test_environment_detection` (line 36) - Indicators: os\.environ
- `test_hot_reload_capability` (line 47) - Indicators: os\.environ
- `test_config_summary_generation` (line 58) - Indicators: os\.environ
- `test_config_class_selection_by_environment` (line 102) - Indicators: os\.environ
- `test_environment_override_detection` (line 118) - Indicators: os\.environ
- `test_configuration_population_order` (line 129) - Indicators: os\.environ

### tests\core\test_agent_recovery_strategies.py
- `test_recovery_execution_timing` (line 402) - Indicators: time\.time\(\)
- `test_concurrent_recovery_operations` (line 426) - Indicators: time\.time\(\)

### tests\core\test_agent_reliability_mixin_health.py
- `test_should_perform_health_check` (line 275) - Indicators: time\.time\(\)

### tests\core\test_async_edge_cases_error_handling.py
- `test_concurrent_rate_limiter_stress` (line 264) - Indicators: time\.time\(\)
- `test_circuit_breaker_race_conditions` (line 287) - Indicators: time\.time\(\)

### tests\core\test_async_function_utilities.py
- `test_nested_timeout_operations` (line 98) - Indicators: time\.time\(\)
- `test_timeout_precision` (line 114) - Indicators: time\.time\(\)
- `test_retry_basic_functionality` (line 133) - Indicators: time\.time\(\)
- `test_retry_exponential_backoff` (line 200) - Indicators: time\.time\(\)
- `test_retry_immediate_success` (line 221) - Indicators: time\.time\(\)
- `test_retry_timing_accuracy` (line 235) - Indicators: time\.time\(\)
- `test_shutdown_async_utils` (line 257) - Indicators: time\.time\(\)
- `test_global_utilities_integration` (line 265) - Indicators: time\.time\(\)

### tests\core\test_async_globals_threadpool.py
- `test_run_sync_function_in_threadpool` (line 46) - Indicators: threading\.
- `test_run_sync_function_with_kwargs` (line 54) - Indicators: threading\.
- `test_threadpool_reuses_executor` (line 61) - Indicators: threading\.
- `test_shutdown_async_utils` (line 75) - Indicators: threading\.

### tests\core\test_async_integration_scenarios.py
- `test_batch_processor_with_rate_limiter` (line 74) - Indicators: time\.time\(\)

### tests\core\test_async_processing_locking.py
- `test_batch_processor_time_triggering` (line 81) - Indicators: time\.time\(\)
- `test_batch_processor_concurrent_additions` (line 102) - Indicators: time\.time\(\)
- `test_lock_fairness` (line 357) - Indicators: time\.time\(\)
- `test_lock_context_manager_cleanup` (line 379) - Indicators: time\.time\(\)
- `test_cleanup` (line 385) - Indicators: time\.time\(\)

### tests\core\test_async_rate_limiter.py
- `test_initialization` (line 29) - Indicators: time\.time\(\)
- `test_acquire_under_limit` (line 33) - Indicators: time\.time\(\)
- `test_acquire_over_limit` (line 43) - Indicators: time\.time\(\)
- `test_time_window_cleanup` (line 57) - Indicators: time\.time\(\)

### tests\core\test_async_rate_limiting_circuit_breaker.py
- `test_rate_limiter_basic_functionality` (line 27) - Indicators: time\.time\(\)
- `test_rate_limiter_window_reset` (line 46) - Indicators: time\.time\(\)
- `test_rate_limiter_concurrent_requests` (line 64) - Indicators: time\.time\(\)
- `test_rate_limiter_different_rates` (line 86) - Indicators: time\.time\(\)
- `test_rate_limiter_burst_handling` (line 109) - Indicators: time\.time\(\)
- `test_circuit_breaker_closed_state` (line 127) - Indicators: time\.time\(\)
- `test_circuit_breaker_with_timeout_operation` (line 224) - Indicators: time\.time\(\)
- `test_circuit_breaker_concurrent_operations` (line 240) - Indicators: time\.time\(\)

### tests\core\test_async_resource_pool_management.py
- `test_connection_pool_timeout_handling` (line 240) - Indicators: time\.time\(\)
- `test_connection_pool_error_recovery` (line 270) - Indicators: time\.time\(\)

### tests\core\test_async_task_pool.py
- `test_submit_background_task_during_shutdown` (line 68) - Indicators: time\.time\(\)
- `test_active_task_count` (line 74) - Indicators: time\.time\(\)
- `test_concurrent_task_limit` (line 83) - Indicators: time\.time\(\)
- `test_shutdown` (line 104) - Indicators: time\.time\(\)

### tests\core\test_async_timeout_retry.py
- `test_with_retry_exhausts_attempts` (line 83) - Indicators: time\.time\(\)
- `test_with_retry_exponential_backoff` (line 94) - Indicators: time\.time\(\)

### tests\core\test_config_manager.py
- `test_initialization` (line 30) - Indicators: os\.environ
- `test_load_from_environment` (line 41) - Indicators: os\.environ
- `test_secret_manager_client_creation_success` (line 55) - Indicators: os\.environ
- `test_get_validation_report_failure` (line 187) - Indicators: os\.environ
- `test_initialization` (line 202) - Indicators: os\.environ
- `test_get_environment_development` (line 213) - Indicators: os\.environ
- `test_get_environment_testing` (line 226) - Indicators: os\.environ
- `test_get_environment_production` (line 235) - Indicators: os\.environ
- `test_create_base_config_development` (line 247) - Indicators: os\.environ
- `test_create_base_config_unknown_defaults_to_dev` (line 255) - Indicators: os\.environ
- `test_reload_config` (line 331) - Indicators: os\.environ
- `test_full_configuration_flow` (line 339) - Indicators: os\.environ
- `test_testing_configuration` (line 368) - Indicators: os\.environ
- `test_configuration_error_handling` (line 376) - Indicators: os\.environ

### tests\core\test_core_infrastructure_11_20.py
- `test_error_response_structure` (line 102) - Indicators: datetime\.now\(\)
- `test_http_exception_handler` (line 117) - Indicators: datetime\.now\(\)
- `test_graceful_degradation` (line 400) - Indicators: os\.environ

### tests\core\test_reliability_mechanisms.py
- `test_exponential_backoff_timing` (line 89) - Indicators: time\.time\(\)
- `test_max_delay_cap_and_jitter` (line 106) - Indicators: time\.time\(\)

### tests\core\test_type_validation_part1.py
- `test_parse_typescript_file_with_interface` (line 83) - Indicators: tempfile\.
- `test_parse_typescript_file_with_type_alias` (line 120) - Indicators: tempfile\.
- `test_parse_typescript_file_with_nested_objects` (line 144) - Indicators: tempfile\.
- `test_parse_interface_fields_with_comments` (line 173) - Indicators: tempfile\.

### tests\core\test_type_validation_part3.py
- `test_validator_initialization` (line 33) - Indicators: tempfile\.
- `test_validate_schemas_missing_frontend_schema` (line 39) - Indicators: tempfile\.
- `test_validate_schemas_missing_backend_field` (line 78) - Indicators: tempfile\.
- `test_validate_schemas_with_type_mismatch` (line 113) - Indicators: tempfile\.
- `test_validate_schemas_type_alias_skip` (line 157) - Indicators: tempfile\.
- `test_validate_schemas_extra_frontend_schema` (line 191) - Indicators: tempfile\.

### tests\core\test_type_validation_part4.py
- `test_validate_type_consistency` (line 39) - Indicators: tempfile\.
- `test_null_and_undefined_handling` (line 325) - Indicators: tempfile\.
- `test_error_recovery_mechanisms` (line 333) - Indicators: tempfile\.

### tests\critical\test_business_critical_gaps.py
- `test_permission_boundaries_enforcement` (line 440) - Indicators: datetime\.now\(\)
- `test_audit_trail_completeness` (line 451) - Indicators: datetime\.now\(\)
- `test_resource_cleanup_on_shutdown` (line 467) - Indicators: datetime\.now\(\)

### tests\critical\test_config_environment_detection.py
- `test_testing_environment_detection_takes_priority` (line 39) - Indicators: os\.environ
- `test_cloud_run_environment_detection_staging` (line 51) - Indicators: os\.environ
- `test_cloud_run_environment_detection_production` (line 64) - Indicators: os\.environ
- `test_fallback_to_environment_variable` (line 77) - Indicators: os\.environ
- `test_default_development_environment` (line 90) - Indicators: os\.environ
- `test_production_config_creation` (line 107) - Indicators: os\.environ
- `test_websocket_url_updated_with_server_port` (line 201) - Indicators: os\.environ
- `test_websocket_url_not_modified_without_server_port` (line 213) - Indicators: os\.environ
- `test_websocket_url_logging_when_port_updated` (line 225) - Indicators: os\.environ
- `test_cloud_run_staging_detection_with_k_service` (line 241) - Indicators: os\.environ
- `test_cloud_run_detection_without_indicators` (line 263) - Indicators: os\.environ
- `test_cloud_run_detection_with_pr_number` (line 279) - Indicators: os\.environ
- `test_config_classes_mapping_completeness` (line 299) - Indicators: os\.environ
- `test_environment_detection_with_mixed_case` (line 351) - Indicators: os\.environ
- `test_environment_detection_with_whitespace` (line 365) - Indicators: os\.environ
- `test_environment_detection_logging` (line 378) - Indicators: os\.environ

### tests\critical\test_config_loader_core.py
- `test_load_env_var_success_with_valid_config` (line 149) - Indicators: os\.environ
- `test_load_env_var_failure_missing_field` (line 173) - Indicators: os\.environ
- `test_load_env_var_failure_missing_env_var` (line 190) - Indicators: os\.environ
- `test_load_env_var_success_with_existing_field` (line 205) - Indicators: os\.environ
- `test_set_clickhouse_host_updates_both_configs` (line 224) - Indicators: os\.environ
- `test_get_attribute_or_none_missing_attribute` (line 478) - Indicators: os\.environ
- `test_k_service_staging_detection` (line 498) - Indicators: os\.environ
- `test_k_service_no_staging_detection` (line 508) - Indicators: os\.environ
- `test_pr_number_staging_detection` (line 518) - Indicators: os\.environ
- `test_pr_number_no_staging_detection` (line 528) - Indicators: os\.environ
- `test_detect_cloud_run_environment_k_service_priority` (line 538) - Indicators: os\.environ
- `test_detect_cloud_run_environment_fallback_to_pr_number` (line 559) - Indicators: os\.environ

### tests\critical\test_config_secrets_manager.py
- `test_staging_environment_project_id_selection` (line 33) - Indicators: os\.environ
- `test_production_environment_project_id_selection` (line 43) - Indicators: os\.environ
- `test_fallback_project_id_when_no_environment` (line 53) - Indicators: os\.environ
- `test_secret_manager_logger_initialization` (line 63) - Indicators: os\.environ
- `test_fallback_to_environment_variables_when_gcp_fails` (line 103) - Indicators: os\.environ
- `test_empty_secrets_handled_gracefully` (line 121) - Indicators: os\.environ
- `test_environment_isolation_between_staging_and_production` (line 275) - Indicators: os\.environ
- `test_secret_loading_error_handling_preserves_security` (line 292) - Indicators: os\.environ

### tests\critical\test_gcp_staging_edge_cases_comprehensive.py
- `test_multiple_config_corruption_cascade_failure_fails` (line 32) - Indicators: os\.environ

### tests\critical\test_staging_configuration_logging_circular_dependency.py
- `test_fallback_config_loading_with_broken_logger_fails` (line 205) - Indicators: os\.environ
- `test_singleton_initialization_race_condition_fails` (line 230) - Indicators: os\.environ

### tests\critical\test_staging_integration_flow.py
- `test_websocket_auth_staging` (line 187) - Indicators: os\.environ
- `test_websocket_reconnection_staging` (line 193) - Indicators: os\.environ
- `test_error_logging_staging` (line 203) - Indicators: os\.environ
- `test_error_recovery_staging` (line 209) - Indicators: os\.environ
- `test_graceful_shutdown_staging` (line 215) - Indicators: os\.environ
- `test_deployment_validation_staging` (line 258) - Indicators: os\.environ

### tests\critical\test_staging_root_cause_validation.py
- `test_wrong_credentials_in_database_url_secret` (line 31) - Indicators: os\.environ
- `test_user_does_not_exist_on_cloud_sql` (line 71) - Indicators: os\.environ
- `test_missing_clickhouse_url_defaults_to_localhost` (line 170) - Indicators: os\.environ
- `test_deployment_script_missing_clickhouse_secrets` (line 194) - Indicators: os\.environ
- `test_hardcoded_localhost_overrides_staging_environment` (line 227) - Indicators: os\.environ
- `test_redis_secret_not_mapped_in_deployment` (line 246) - Indicators: os\.environ
- `test_no_startup_validation_for_required_config` (line 277) - Indicators: os\.environ
- `test_development_defaults_override_staging_detection` (line 350) - Indicators: os\.environ
- `test_secret_manager_precedence_over_environment` (line 383) - Indicators: os\.environ

### tests\critical\test_staging_startup_initialization_order.py
- `test_staging_environment_detection_during_early_startup_fails` (line 269) - Indicators: os\.environ
- `test_staging_secret_loading_before_config_ready_fails` (line 296) - Indicators: os\.environ

### tests\critical\test_startup_check_import_issue.py
- `test_check_environment_variables_fails_with_wrong_import` (line 74) - Indicators: os\.environ
- `test_startup_check_result_signature_mismatch` (line 101) - Indicators: os\.environ

### tests\critical\test_websocket_auth_regression.py
- `test_websocket_connection_timeout_behavior` (line 304) - Indicators: time\.time\(\)
- `test_unknown_message_type_handling` (line 331) - Indicators: time\.time\(\)

### tests\critical\test_websocket_coroutine_regression.py
- `test_coroutine_early_detection` (line 370) - Indicators: time\.time\(\)

### tests\critical\test_websocket_message_regression.py
- `test_complete_message_flow_real_websocket` (line 146) - Indicators: time\.time\(\)
- `test_concurrent_messages_real_websocket` (line 183) - Indicators: time\.time\(\)
- `test_large_message_handling_real_websocket` (line 231) - Indicators: time\.time\(\)
- `test_empty_message_content_real_websocket` (line 264) - Indicators: time\.time\(\)

### tests\database\test_redis_connection_fix_verified.py
- `test_redis_connection_works_with_python312` (line 19) - Indicators: os\.environ
- `test_dev_launcher_database_validation_succeeds` (line 46) - Indicators: os\.environ

### tests\database\test_redis_connection_python312.py
- `test_redis_connection_works_with_python312` (line 21) - Indicators: os\.environ
- `test_dev_launcher_database_validation_succeeds` (line 48) - Indicators: os\.environ

### tests\e2e\test_admin_corpus_generation.py
- `test_configuration_suggestions` (line 108) - Indicators: os\.environ

### tests\e2e\test_agent_message_flow.py
- `test_concurrent_message_throughput` (line 1009) - Indicators: datetime\.now\(\)

### tests\e2e\test_agent_pipeline.py
- `test_response_time_performance` (line 550) - Indicators: time\.time\(\)
- `test_concurrent_request_handling` (line 580) - Indicators: time\.time\(\)

### tests\e2e\test_agent_scaling_load_testing.py
- `test_agent_connection_pool_under_load` (line 285) - Indicators: time\.time\(\)
- `test_agent_circuit_breaker_under_load` (line 374) - Indicators: time\.time\(\)

### tests\e2e\test_complete_real_pipeline_e2e.py
- `test_complete_triage_to_data_pipeline` (line 36) - Indicators: os\.environ

### tests\e2e\test_latency_optimization_workflows_core.py
- `test_parallel_processing_optimization` (line 73) - Indicators: time\.time\(\)
- `test_workflow_execution_time_bounds` (line 84) - Indicators: time\.time\(\)
- `test_agent_step_timing_consistency` (line 96) - Indicators: time\.time\(\)
- `test_ep_002_latency_budget_constraint_real_llm` (line 108) - Indicators: time\.time\(\)

### tests\e2e\test_mixins_comprehensive.py
- `test_cache_size_limits` (line 208) - Indicators: time\.time\(\)
- `test_health_metrics_caching` (line 219) - Indicators: time\.time\(\)
- `test_cache_invalidation_timing` (line 230) - Indicators: time\.time\(\)

### tests\e2e\test_multi_service.py
- `test_data_synchronization_lag` (line 270) - Indicators: time\.time\(\)
- `test_service_health_coordination` (line 304) - Indicators: time\.time\(\)

### tests\e2e\test_real_llm_workflow.py
- `test_complete_optimization_workflow_real_llm` (line 60) - Indicators: time\.time\(\)
- `test_concurrent_real_llm_workflows` (line 169) - Indicators: time\.time\(\)

### tests\e2e\test_staging_environment_auth_urls.py
- `test_full_oauth_flow_staging_urls` (line 41) - Indicators: os\.environ
- `test_environment_variable_propagation` (line 150) - Indicators: os\.environ
- `test_cross_service_communication_urls` (line 169) - Indicators: os\.environ

### tests\e2e\test_system_startup.py
- `test_dev_launcher_starts_all_services` (line 83) - Indicators: time\.time\(\)
- `test_service_health_endpoints_respond` (line 105) - Indicators: time\.time\(\)
- `test_database_connections_established` (line 135) - Indicators: time\.time\(\)
- `test_service_startup_order` (line 233) - Indicators: time\.time\(\)
- `test_graceful_shutdown` (line 253) - Indicators: time\.time\(\)
- `test_startup_time_within_limits` (line 274) - Indicators: time\.time\(\)
- `test_parallel_startup_faster_than_sequential` (line 291) - Indicators: time\.time\(\)
- `test_retry_on_startup_failure` (line 311) - Indicators: time\.time\(\)

### tests\e2e\test_thread_management.py
- `test_thread_expiration_after_timeout` (line 185) - Indicators: time\.time\(\)
- `test_concurrent_thread_creation` (line 215) - Indicators: time\.time\(\)

### tests\examples\test_feature_flag_environment_demo.py
- `test_environment_override_demo` (line 23) - Indicators: os\.environ
- `test_enterprise_sso_when_enabled` (line 48) - Indicators: os\.environ

### tests\integration\test_advanced_analytics_export.py
- `test_01_clickhouse_large_dataset_export` (line 58) - Indicators: time\.time\(\)
- `test_03_scheduled_export_automation` (line 143) - Indicators: time\.time\(\)

### tests\integration\test_agent_database_resilience.py
- `test_agent_database_retry_with_exponential_backoff` (line 25) - Indicators: time\.time\(\)
- `test_agent_database_timeout_handling` (line 86) - Indicators: time\.time\(\)
- `test_agent_database_deadlock_detection_recovery` (line 122) - Indicators: time\.time\(\)

### tests\integration\test_agent_pipeline_performance.py
- `test_pipeline_performance_under_concurrent_load` (line 59) - Indicators: time\.time\(\)
- `test_end_to_end_response_time_sla_compliance` (line 193) - Indicators: time\.time\(\)

### tests\integration\test_agent_registry_initialization_validation.py
- `test_supervisor_initialization` (line 79) - Indicators: time\.time\(\)
- `test_sub_agent_discovery` (line 101) - Indicators: time\.time\(\)
- `test_communication_setup` (line 111) - Indicators: time\.time\(\)
- `test_smoke_agent_registry_initialization_validation` (line 127) - Indicators: time\.time\(\)
- `test_multi_environment_validation` (line 150) - Indicators: time\.time\(\)
- `test_performance_under_load` (line 155) - Indicators: time\.time\(\)
- `test_failure_cascade_impact` (line 160) - Indicators: time\.time\(\)

### tests\integration\test_api_security_authentication_bypass.py
- `test_session_fixation_prevention` (line 159) - Indicators: time\.time\(\)

### tests\integration\test_auth_edge_cases.py
- `test_jwt_none_algorithm_attack` (line 175) - Indicators: random\.
- `test_race_condition_in_token_refresh` (line 302) - Indicators: random\.
- `test_session_fixation_prevention` (line 329) - Indicators: random\.
- `test_brute_force_protection` (line 493) - Indicators: time\.time\(\)
- `test_password_complexity_bypass_attempts` (line 521) - Indicators: time\.time\(\)

### tests\integration\test_auth_jwt_redis_session.py
- `test_auth_redis_integration_comprehensive` (line 575) - Indicators: time\.time\(\)

### tests\integration\test_auth_service_session_validation.py
- `test_expired_session_token_rejection` (line 116) - Indicators: time\.time\(\)

### tests\integration\test_auth_system_verification.py
- `test_auth_service_startup_timeout_configuration` (line 122) - Indicators: time\.time\(\)

### tests\integration\test_background_jobs_redis_queue.py
- `test_job_scheduling_and_delayed_execution` (line 298) - Indicators: time\.time\(\)

### tests\integration\test_cache_invalidation_basic.py
- `test_cache_invalidation_pattern_exists` (line 16) - Indicators: datetime\.now\(\)
- `test_concurrent_cache_operations` (line 41) - Indicators: datetime\.now\(\)
- `test_cache_ttl_simulation` (line 84) - Indicators: datetime\.now\(\)
- `test_cache_size_limit_simulation` (line 119) - Indicators: datetime\.now\(\)
- `test_cache_invalidation_performance` (line 148) - Indicators: datetime\.now\(\)
- `test_partial_cache_invalidation` (line 176) - Indicators: datetime\.now\(\)

### tests\integration\test_cache_invalidation_redis.py
- `test_pattern_based_clearing` (line 182) - Indicators: time\.time\(\)
- `test_cache_invalidation_performance` (line 434) - Indicators: time\.time\(\)
- `test_cache_consistency_validation` (line 457) - Indicators: time\.time\(\)

### tests\integration\test_cache_redis_invalidation.py
- `test_cascade_invalidation_propagation` (line 58) - Indicators: random\.
- `test_tag_based_invalidation_redis` (line 88) - Indicators: time\.time\(\)

### tests\integration\test_cache_service_cascade.py
- `test_race_condition_prevention` (line 112) - Indicators: time\.time\(\)
- `test_service_level_invalidation` (line 197) - Indicators: time\.time\(\)
- `test_cascade_propagation_timing` (line 248) - Indicators: time\.time\(\)
- `test_batch_invalidation_efficiency` (line 290) - Indicators: time\.time\(\)

### tests\integration\test_clickhouse_schema_validation_comprehensive.py
- `test_table_schema_validation` (line 84) - Indicators: time\.time\(\)
- `test_column_types_and_constraints` (line 106) - Indicators: time\.time\(\)
- `test_event_schema_compatibility` (line 116) - Indicators: time\.time\(\)
- `test_smoke_clickhouse_schema_validation_comprehensive` (line 132) - Indicators: time\.time\(\)
- `test_multi_environment_validation` (line 155) - Indicators: time\.time\(\)
- `test_performance_under_load` (line 160) - Indicators: time\.time\(\)
- `test_failure_cascade_impact` (line 165) - Indicators: time\.time\(\)

### tests\integration\test_compensation_engine_e2e.py
- `test_database_setup` (line 53) - Indicators: tempfile\.

### tests\integration\test_configuration_integration.py
- `test_configuration_loading_from_environment` (line 71) - Indicators: os\.environ
- `test_environment_specific_configurations` (line 117) - Indicators: os\.environ
- `test_configuration_validation_and_errors` (line 140) - Indicators: os\.environ
- `test_configuration_fallback_mechanisms` (line 159) - Indicators: os\.environ
- `test_configuration_hot_reload` (line 226) - Indicators: os\.environ
- `test_secret_management_integration` (line 254) - Indicators: os\.environ
- `test_configuration_caching_and_performance` (line 283) - Indicators: os\.environ
- `test_configuration_environment_isolation` (line 312) - Indicators: os\.environ
- `test_microservice_configuration_independence` (line 321) - Indicators: os\.environ

### tests\integration\test_configuration_validation_environment_parity.py
- `test_cross_environment_validation` (line 84) - Indicators: time\.time\(\)
- `test_setting_overrides` (line 106) - Indicators: time\.time\(\)
- `test_feature_flag_consistency` (line 116) - Indicators: time\.time\(\)
- `test_smoke_configuration_validation_environment_parity` (line 132) - Indicators: time\.time\(\)
- `test_multi_environment_validation` (line 155) - Indicators: time\.time\(\)
- `test_performance_under_load` (line 160) - Indicators: time\.time\(\)
- `test_failure_cascade_impact` (line 165) - Indicators: time\.time\(\)

### tests\integration\test_critical_auth_integration.py
- `test_session_security_validation` (line 67) - Indicators: time\.time\(\)

### tests\integration\test_critical_functionality_demo.py
- `test_intentional_failure_for_demo` (line 110) - Indicators: datetime\.now\(\)
- `test_performance_basic_sanity` (line 119) - Indicators: datetime\.now\(\)

### tests\integration\test_cross_service_transactions.py
- `test_atomic_cross_service_transaction_commit` (line 134) - Indicators: tempfile\.

### tests\integration\test_database_connection_fix.py
- `test_database_connection_environment_override` (line 41) - Indicators: os\.environ
- `test_identify_database_server_availability` (line 55) - Indicators: os\.environ
- `test_apply_temporary_database_fix` (line 104) - Indicators: os\.environ

### tests\integration\test_database_connection_pooling.py
- `test_connection_reuse_efficiency` (line 100) - Indicators: time\.time\(\)
- `test_concurrent_connection_handling` (line 139) - Indicators: time\.time\(\)
- `test_connection_cleanup_on_exception` (line 182) - Indicators: time\.time\(\)
- `test_sequential_vs_pooled_performance` (line 298) - Indicators: time\.time\(\)

### tests\integration\test_database_connection_pool_initialization_validation.py
- `test_pool_creation_and_sizing_validation` (line 84) - Indicators: time\.time\(\)
- `test_clickhouse_http_native_pools` (line 108) - Indicators: time\.time\(\)
- `test_redis_connection_pool_config` (line 118) - Indicators: time\.time\(\)
- `test_smoke_database_connection_pool_initialization_validation` (line 134) - Indicators: time\.time\(\)
- `test_multi_environment_validation` (line 157) - Indicators: time\.time\(\)
- `test_performance_under_load` (line 162) - Indicators: time\.time\(\)
- `test_failure_cascade_impact` (line 167) - Indicators: time\.time\(\)

### tests\integration\test_database_connection_pool_monitoring.py
- `test_connection_leak_detection` (line 108) - Indicators: time\.time\(\)
- `test_connection_timeout_monitoring` (line 228) - Indicators: time\.time\(\)
- `test_concurrent_connection_stress` (line 276) - Indicators: time\.time\(\)

### tests\integration\test_database_connection_reliability.py
- `test_real_database_connections` (line 144) - Indicators: os\.environ
- `test_connection_retry_logic` (line 158) - Indicators: os\.environ

### tests\integration\test_database_connectivity_l3_real.py
- `test_database_manager_real_url_processing` (line 88) - Indicators: os\.environ
- `test_db_connection_manager_integration` (line 282) - Indicators: os\.environ
- `test_session` (line 300) - Indicators: os\.environ
- `test_clickhouse_connectivity_real` (line 311) - Indicators: os\.environ
- `test_database_migration_patterns` (line 318) - Indicators: os\.environ
- `test_ssl_connection_handling` (line 350) - Indicators: os\.environ

### tests\integration\test_database_health_checker_sslmode_fix.py
- `test_database_manager_converts_sslmode_to_ssl` (line 77) - Indicators: os\.environ
- `test_get_converted_async_db_url_prevents_sslmode` (line 92) - Indicators: os\.environ
- `test_health_checker_works_with_converted_url` (line 109) - Indicators: os\.environ
- `test_cloud_sql_url_has_no_ssl_params` (line 142) - Indicators: os\.environ
- `test_init_async_db_validates_url_conversion` (line 157) - Indicators: os\.environ

### tests\integration\test_database_migration_performance.py
- `test_concurrent_migration_prevention` (line 63) - Indicators: tempfile\.
- `test_migration_performance_validation` (line 92) - Indicators: time\.time\(\)

### tests\integration\test_database_url_builder_integration.py
- `test_environment_variable_integration` (line 96) - Indicators: os\.environ
- `test_url_normalization_consistency` (line 117) - Indicators: os\.environ

### tests\integration\test_dev_launcher_startup.py
- `test_environment_variable_loading_consistency` (line 168) - Indicators: os\.environ
- `test_database_connectivity_validation` (line 192) - Indicators: os\.environ
- `test_service_initialization_order` (line 223) - Indicators: tempfile\.
- `test_error_recovery_scenarios` (line 267) - Indicators: tempfile\.
- `test_launcher_run_basic_flow` (line 293) - Indicators: tempfile\.
- `test_windows_specific_features` (line 351) - Indicators: subprocess\.
- `test_launcher_configuration_validation` (line 373) - Indicators: subprocess\.

### tests\integration\test_environment_secrets_loading_validation.py
- `test_google_secrets_manager_integration` (line 84) - Indicators: time\.time\(\)
- `test_local_env_fallback` (line 106) - Indicators: time\.time\(\)
- `test_api_key_loading_for_llms` (line 116) - Indicators: time\.time\(\)
- `test_smoke_environment_secrets_loading_validation` (line 132) - Indicators: time\.time\(\)
- `test_multi_environment_validation` (line 155) - Indicators: time\.time\(\)
- `test_performance_under_load` (line 160) - Indicators: time\.time\(\)
- `test_failure_cascade_impact` (line 165) - Indicators: time\.time\(\)

### tests\integration\test_error_handling_integration.py
- `test_service_error_propagation` (line 82) - Indicators: time\.time\(\)
- `test_circuit_breaker_integration` (line 99) - Indicators: time\.time\(\)
- `test_graceful_degradation_scenario` (line 117) - Indicators: time\.time\(\)
- `test_exponential_backoff_retry` (line 135) - Indicators: time\.time\(\)
- `test_dead_letter_queue_processing` (line 156) - Indicators: time\.time\(\)
- `test_service_health_check_recovery` (line 172) - Indicators: time\.time\(\)
- `test_error_metrics_aggregation` (line 193) - Indicators: time\.time\(\)
- `test_comprehensive_error_recovery_workflow` (line 212) - Indicators: time\.time\(\)

### tests\integration\test_error_recovery_startup_resilience_validation.py
- `test_database_failure_recovery` (line 84) - Indicators: time\.time\(\)
- `test_service_degradation` (line 106) - Indicators: time\.time\(\)
- `test_retry_mechanisms` (line 116) - Indicators: time\.time\(\)
- `test_smoke_error_recovery_startup_resilience_validation` (line 132) - Indicators: time\.time\(\)
- `test_multi_environment_validation` (line 155) - Indicators: time\.time\(\)
- `test_performance_under_load` (line 160) - Indicators: time\.time\(\)
- `test_failure_cascade_impact` (line 165) - Indicators: time\.time\(\)

### tests\integration\test_first_time_user_onboarding.py
- `test_session_persistence_across_refresh` (line 189) - Indicators: time\.time\(\)

### tests\integration\test_first_time_user_workspace.py
- `test_privacy_settings_enforcement` (line 114) - Indicators: time\.time\(\)

### tests\integration\test_fixtures_common.py
- `test_database` (line 32) - Indicators: tempfile\.

### tests\integration\test_free_to_paid_conversion.py
- `test_infra` (line 47) - Indicators: tempfile\.

### tests\integration\test_frontend_startup_issues.py
- `test_frontend_dependencies_check` (line 135) - Indicators: subprocess\.
- `test_frontend_build_requirements` (line 169) - Indicators: subprocess\.

### tests\integration\test_llm_api_connectivity_validation_all_providers.py
- `test_gemini_api_connectivity` (line 84) - Indicators: time\.time\(\)
- `test_gpt_4_and_claude_connections` (line 106) - Indicators: time\.time\(\)
- `test_rate_limiting_handling` (line 116) - Indicators: time\.time\(\)
- `test_smoke_llm_api_connectivity_validation_all_providers` (line 132) - Indicators: time\.time\(\)
- `test_multi_environment_validation` (line 155) - Indicators: time\.time\(\)
- `test_performance_under_load` (line 160) - Indicators: time\.time\(\)
- `test_failure_cascade_impact` (line 165) - Indicators: time\.time\(\)

### tests\integration\test_llm_websocket_database_recovery.py
- `test_connection_pool_warmup` (line 87) - Indicators: time\.time\(\)
- `test_state_preservation_on_disconnect` (line 124) - Indicators: time\.time\(\)
- `test_automatic_reconnection_logic` (line 156) - Indicators: time\.time\(\)
- `test_message_queue_recovery` (line 185) - Indicators: time\.time\(\)

### tests\integration\test_logging_audit_integration_core.py
- `test_logger` (line 55) - Indicators: tempfile\.

### tests\integration\test_message_persistence_and_coordination.py
- `test_parallel_agent_execution` (line 201) - Indicators: time\.time\(\)
- `test_agent_response_aggregation` (line 237) - Indicators: time\.time\(\)

### tests\integration\test_message_queue_redis_streams.py
- `test_dead_letter_queue_handling` (line 283) - Indicators: time\.time\(\)
- `test_stream_processing_performance_comprehensive` (line 838) - Indicators: time\.time\(\)

### tests\integration\test_metrics_pipeline_prometheus.py
- `test_metrics_collection_and_exposure` (line 129) - Indicators: time\.time\(\)
- `test_metrics_pipeline_performance` (line 201) - Indicators: time\.time\(\)
- `test_custom_metrics_with_labels` (line 235) - Indicators: time\.time\(\)

### tests\integration\test_metric_collection_initialization_validation.py
- `test_prometheus_setup` (line 84) - Indicators: time\.time\(\)
- `test_metrics_registration` (line 106) - Indicators: time\.time\(\)
- `test_aggregation_pipeline` (line 116) - Indicators: time\.time\(\)
- `test_smoke_metric_collection_initialization_validation` (line 132) - Indicators: time\.time\(\)
- `test_multi_environment_validation` (line 155) - Indicators: time\.time\(\)
- `test_performance_under_load` (line 160) - Indicators: time\.time\(\)
- `test_failure_cascade_impact` (line 165) - Indicators: time\.time\(\)

### tests\integration\test_microservice_dependency_startup_sequence.py
- `test_correct_startup_dependency_order` (line 465) - Indicators: time\.time\(\)
- `test_startup_retry_mechanism_on_transient_failures` (line 699) - Indicators: time\.time\(\)
- `test_basic_startup_smoke_test` (line 788) - Indicators: time\.time\(\)
- `test_startup_with_external_dependencies` (line 865) - Indicators: time\.time\(\)
- `test_rolling_update_startup_sequence` (line 871) - Indicators: time\.time\(\)

### tests\integration\test_migration_rollback_recovery.py
- `test_migration_failure_triggers_rollback` (line 94) - Indicators: subprocess\.

### tests\integration\test_migration_state_recovery_integration.py
- `test_migration_tracker_integration` (line 94) - Indicators: tempfile\.

### tests\integration\test_missing_database_tables.py
- `test_run_alembic_check` (line 200) - Indicators: subprocess\.
- `test_manual_table_creation_if_needed` (line 235) - Indicators: subprocess\.

### tests\integration\test_oauth_staging_redirect_flow.py
- `test_oauth_google_login_staging_redirect` (line 33) - Indicators: os\.environ
- `test_all_oauth_endpoints_use_staging_urls` (line 197) - Indicators: os\.environ

### tests\integration\test_payment_gateway_integration.py
- `test_02_failed_payment_handling_recovery` (line 59) - Indicators: time\.time\(\)
- `test_03_subscription_lifecycle_management` (line 71) - Indicators: time\.time\(\)
- `test_04_webhook_processing_idempotency` (line 83) - Indicators: time\.time\(\)

### tests\integration\test_rate_limiting_backpressure.py
- `test_token_bucket_basic_consumption` (line 130) - Indicators: time\.time\(\)
- `test_token_bucket_refill_mechanics` (line 141) - Indicators: time\.time\(\)
- `test_token_bucket_burst_handling` (line 154) - Indicators: time\.time\(\)
- `test_token_bucket_reset` (line 162) - Indicators: time\.time\(\)
- `test_burst_traffic_detection` (line 211) - Indicators: time\.time\(\)
- `test_sliding_window_counter` (line 222) - Indicators: time\.time\(\)
- `test_adaptive_rate_limiter_behavior` (line 235) - Indicators: time\.time\(\)

### tests\integration\test_rate_limiting_redis.py
- `test_sliding_window_implementation` (line 128) - Indicators: time\.time\(\)
- `test_burst_handling_capacity` (line 188) - Indicators: time\.time\(\)
- `test_rate_limiting_performance_load` (line 596) - Indicators: time\.time\(\)
- `test_rate_limiting_redis_consistency` (line 619) - Indicators: time\.time\(\)

### tests\integration\test_redis_configuration_fix.py
- `test_environment_variable_setting_fix` (line 68) - Indicators: os\.environ
- `test_isolated_environment_redis_configuration` (line 87) - Indicators: os\.environ

### tests\integration\test_redis_session_core.py
- `test_websocket_connection_redis_state_creation` (line 79) - Indicators: time\.time\(\)

### tests\integration\test_redis_session_performance.py
- `test_state_synchronization_real_time` (line 79) - Indicators: time\.time\(\)
- `test_state_conflict_resolution` (line 239) - Indicators: time\.time\(\)

### tests\integration\test_redis_session_store_initialization_validation.py
- `test_session_store_configuration` (line 84) - Indicators: time\.time\(\)
- `test_serialization_deserialization` (line 106) - Indicators: time\.time\(\)
- `test_ttl_and_cleanup` (line 116) - Indicators: time\.time\(\)
- `test_smoke_redis_session_store_initialization_validation` (line 132) - Indicators: time\.time\(\)
- `test_multi_environment_validation` (line 155) - Indicators: time\.time\(\)
- `test_performance_under_load` (line 160) - Indicators: time\.time\(\)
- `test_failure_cascade_impact` (line 165) - Indicators: time\.time\(\)

### tests\integration\test_service_health_integration.py
- `test_health_check_endpoint_validation` (line 66) - Indicators: time\.time\(\)
- `test_health_check_performance_and_timeouts` (line 346) - Indicators: time\.time\(\)

### tests\integration\test_sso_saml_error_scenarios.py
- `test_concurrent_tenant_isolation` (line 137) - Indicators: time\.time\(\)

### tests\integration\test_sso_saml_integration.py
- `test_saml_assertion_validation_success` (line 110) - Indicators: time\.time\(\)
- `test_sso_token_exchange_flow` (line 130) - Indicators: time\.time\(\)
- `test_multi_tenant_isolation_during_sso` (line 152) - Indicators: time\.time\(\)
- `test_invalid_saml_assertion_rejection` (line 196) - Indicators: time\.time\(\)
- `test_expired_saml_assertion_rejection` (line 204) - Indicators: time\.time\(\)
- `test_sso_performance_under_load` (line 212) - Indicators: time\.time\(\)
- `test_session_cleanup_on_logout` (line 233) - Indicators: time\.time\(\)

### tests\integration\test_staging_external_services.py
- `test_clickhouse_service_initialization_fails` (line 121) - Indicators: time\.time\(\)
- `test_redis_service_not_provisioned_fails` (line 278) - Indicators: time\.time\(\)
- `test_redis_operations_require_connection_fails` (line 493) - Indicators: time\.time\(\)

### tests\integration\test_staging_production_parity_validation.py
- `test_configuration_parity` (line 84) - Indicators: time\.time\(\)
- `test_service_discovery` (line 106) - Indicators: time\.time\(\)
- `test_scaling_behavior` (line 116) - Indicators: time\.time\(\)
- `test_smoke_staging_production_parity_validation` (line 132) - Indicators: time\.time\(\)
- `test_multi_environment_validation` (line 155) - Indicators: time\.time\(\)
- `test_performance_under_load` (line 160) - Indicators: time\.time\(\)
- `test_failure_cascade_impact` (line 165) - Indicators: time\.time\(\)

### tests\integration\test_startup_health_check_comprehensive_validation.py
- `test_sequential_health_checks` (line 84) - Indicators: time\.time\(\)
- `test_environment_validation` (line 106) - Indicators: time\.time\(\)
- `test_database_connectivity` (line 116) - Indicators: time\.time\(\)
- `test_smoke_startup_health_check_comprehensive_validation` (line 132) - Indicators: time\.time\(\)
- `test_multi_environment_validation` (line 155) - Indicators: time\.time\(\)
- `test_performance_under_load` (line 160) - Indicators: time\.time\(\)
- `test_failure_cascade_impact` (line 165) - Indicators: time\.time\(\)

### tests\integration\test_startup_performance_timing_validation.py
- `test_10_second_target_validation` (line 84) - Indicators: time\.time\(\)
- `test_load_condition_testing` (line 106) - Indicators: time\.time\(\)
- `test_cold_vs_warm_start` (line 116) - Indicators: time\.time\(\)
- `test_smoke_startup_performance_timing_validation` (line 132) - Indicators: time\.time\(\)
- `test_multi_environment_validation` (line 155) - Indicators: time\.time\(\)
- `test_performance_under_load` (line 160) - Indicators: time\.time\(\)
- `test_failure_cascade_impact` (line 165) - Indicators: time\.time\(\)

### tests\integration\test_system_startup_integration.py
- `test_complete_startup_sequence_success` (line 53) - Indicators: os\.environ
- `test_environment_variable_validation_failure` (line 125) - Indicators: os\.environ
- `test_database_connection_failure_recovery` (line 145) - Indicators: os\.environ
- `test_service_initialization_order` (line 192) - Indicators: os\.environ
- `test_health_check_endpoint_validation` (line 240) - Indicators: os\.environ
- `test_startup_failure_scenarios` (line 287) - Indicators: os\.environ
- `test_staging_environment_strict_validation` (line 306) - Indicators: os\.environ

### tests\integration\test_thread_management_critical.py
- `test_bulk_thread_operations_performance` (line 342) - Indicators: datetime\.now\(\)

### tests\integration\test_thread_performance_regression.py
- `test_single_thread_creation_performance` (line 48) - Indicators: time\.time\(\)
- `test_bulk_thread_creation_performance` (line 89) - Indicators: time\.time\(\)
- `test_concurrent_thread_operations_performance` (line 262) - Indicators: time\.time\(\)

### tests\integration\test_transaction_coordination_integration.py
- `test_two_phase_commit_protocol` (line 126) - Indicators: time\.time\(\)
- `test_saga_pattern_implementation` (line 183) - Indicators: time\.time\(\)
- `test_transaction_isolation_levels` (line 245) - Indicators: time\.time\(\)
- `test_deadlock_detection_algorithm` (line 295) - Indicators: time\.time\(\)
- `test_deadlock_prevention_strategies` (line 359) - Indicators: time\.time\(\)
- `test_timeout_based_deadlock_resolution` (line 411) - Indicators: time\.time\(\)
- `test_cross_service_data_consistency` (line 454) - Indicators: time\.time\(\)
- `test_distributed_transaction_rollback` (line 536) - Indicators: time\.time\(\)

### tests\integration\test_user_flows_main.py
- `test_user_journey_performance_metrics` (line 205) - Indicators: time\.time\(\)
- `test_user_data` (line 252) - Indicators: time\.time\(\)

### tests\integration\test_user_registration_flow.py
- `test_registration_performance_under_load` (line 127) - Indicators: time\.time\(\)
- `test_registration_failure_recovery` (line 152) - Indicators: time\.time\(\)

### tests\integration\test_user_tier_management.py
- `test_usage_tracking_and_metering` (line 62) - Indicators: time\.time\(\)

### tests\integration\test_user_websocket_lifecycle.py
- `test_websocket_reconnection_handling` (line 97) - Indicators: time\.time\(\)

### tests\integration\test_websocket_auth_cold_start_extended.py
- `test_cold_start_valid_auth_memory_pressure` (line 63) - Indicators: os\.environ
- `test_concurrent_auth_thundering_herd` (line 788) - Indicators: random\.
- `test_concurrent_auth_connection_hijacking` (line 959) - Indicators: random\.

### tests\integration\test_websocket_connection_leak_detection.py
- `test_websocket_connection_timeout_handling` (line 174) - Indicators: time\.time\(\)
- `test_websocket_connection_limit_enforcement` (line 210) - Indicators: time\.time\(\)

### tests\integration\test_websocket_error_recovery.py
- `test_websocket_performance_under_connection_load` (line 48) - Indicators: time\.time\(\)
- `test_message_queue_performance_under_load` (line 117) - Indicators: time\.time\(\)

### tests\integration\test_websocket_infrastructure_startup_validation.py
- `test_server_initialization` (line 67) - Indicators: time\.time\(\)
- `test_authentication_integration` (line 89) - Indicators: time\.time\(\)
- `test_connection_pooling` (line 99) - Indicators: time\.time\(\)
- `test_smoke_websocket_infrastructure_startup_validation` (line 115) - Indicators: time\.time\(\)
- `test_multi_environment_validation` (line 138) - Indicators: time\.time\(\)
- `test_performance_under_load` (line 143) - Indicators: time\.time\(\)
- `test_failure_cascade_impact` (line 148) - Indicators: time\.time\(\)

### tests\integration\test_websocket_reconnection_core.py
- `test_exponential_backoff_reconnection` (line 414) - Indicators: time\.time\(\)

### tests\integration\test_websocket_redis_pubsub.py
- `test_concurrent_connections_performance` (line 300) - Indicators: time\.time\(\)

### tests\llm\test_llm_integration_real.py
- `test_exponential_backoff_rate_limit` (line 171) - Indicators: time\.time\(\)
- `test_model_fallback_on_failure` (line 185) - Indicators: time\.time\(\)
- `test_timeout_handling` (line 198) - Indicators: time\.time\(\)

### tests\llm\test_structured_generation.py
- `test_config` (line 38) - Indicators: os\.environ

### tests\monitoring\test_agent_monitoring_comprehensive.py
- `test_agent_performance_metrics` (line 25) - Indicators: time\.time\(\)
- `test_agent_error_metrics_and_alerting` (line 101) - Indicators: time\.time\(\)
- `test_agent_resource_utilization_monitoring` (line 195) - Indicators: time\.time\(\)
- `test_agent_distributed_tracing` (line 270) - Indicators: time\.time\(\)
- `test_agent_error_tracing` (line 371) - Indicators: time\.time\(\)
- `test_agent_custom_metrics_and_dashboards` (line 443) - Indicators: time\.time\(\)
- `test_agent_config_change_tracking` (line 529) - Indicators: time\.time\(\)
- `test_agent_health_monitoring_integration` (line 594) - Indicators: time\.time\(\)

### tests\performance\test_agent_performance_comprehensive.py
- `test_agent_initialization_latency` (line 26) - Indicators: time\.time\(\)
- `test_agent_concurrent_execution_latency` (line 141) - Indicators: time\.time\(\)

### tests\performance\test_concurrent_processing.py
- `test_resource_contention_handling` (line 67) - Indicators: multiprocessing\.

### tests\performance\test_corpus_generation_perf.py
- `test_large_corpus_generation` (line 55) - Indicators: time\.time\(\)
- `test_concurrent_generations` (line 77) - Indicators: time\.time\(\)
- `test_batch_processing_performance` (line 126) - Indicators: time\.time\(\)
- `test_streaming_generation` (line 159) - Indicators: time\.time\(\)
- `test_throughput_measurement` (line 223) - Indicators: time\.time\(\)
- `test_latency_percentiles` (line 246) - Indicators: time\.time\(\)

### tests\performance\test_performance_cache.py
- `test_cache_performance` (line 86) - Indicators: time\.time\(\)
- `test_query_caching` (line 124) - Indicators: time\.time\(\)

### tests\recovery\test_agent_error_recovery_comprehensive.py
- `test_agent_automatic_error_recovery` (line 24) - Indicators: time\.time\(\)
- `test_agent_cascading_failure_prevention` (line 114) - Indicators: time\.time\(\)
- `test_agent_state_recovery_and_rollback` (line 214) - Indicators: time\.time\(\)

### tests\routes\test_health_route.py
- `test_basic_import` (line 7) - Indicators: os\.environ
- `test_health_endpoint_direct` (line 32) - Indicators: os\.environ
- `test_live_endpoint` (line 50) - Indicators: os\.environ

### tests\routes\test_health_route_llm_issue.py
- `test_llm_health_check_missing_method` (line 27) - Indicators: os\.environ

### tests\routes\test_reference_management.py
- `test_get_reference_by_id` (line 65) - Indicators: datetime\.now\(\)

### tests\routes\test_threads_routes.py
- `test_thread_creation` (line 19) - Indicators: datetime\.now\(\)
- `test_thread_pagination` (line 39) - Indicators: datetime\.now\(\)

### tests\routes\test_thread_crud.py
- `test_thread_creation` (line 28) - Indicators: datetime\.now\(\)
- `test_thread_retrieval` (line 102) - Indicators: datetime\.now\(\)
- `test_thread_update` (line 138) - Indicators: datetime\.now\(\)
- `test_thread_deletion` (line 171) - Indicators: datetime\.now\(\)
- `test_thread_status_management` (line 192) - Indicators: datetime\.now\(\)
- `test_thread_metadata_management` (line 224) - Indicators: datetime\.now\(\)
- `test_thread_duplication` (line 261) - Indicators: datetime\.now\(\)

### tests\routes\test_thread_messaging.py
- `test_thread_pagination` (line 28) - Indicators: datetime\.now\(\)
- `test_thread_message_addition` (line 60) - Indicators: datetime\.now\(\)
- `test_message_editing` (line 204) - Indicators: datetime\.now\(\)
- `test_message_reactions_and_feedback` (line 301) - Indicators: datetime\.now\(\)
- `test_message_threading_and_replies` (line 332) - Indicators: datetime\.now\(\)

### tests\security\test_agent_security_comprehensive.py
- `test_agent_session_security` (line 95) - Indicators: time\.time\(\)

### tests\security\test_integrated_security.py
- `test_performance_under_load` (line 56) - Indicators: time\.time\(\)
- `test_security_chain_validation` (line 79) - Indicators: time\.time\(\)

### tests\security\test_oauth_jwt_security_vulnerabilities.py
- `test_jwt_none_algorithm_bypass_attack` (line 111) - Indicators: time\.time\(\)
- `test_jwt_payload_tampering_attack` (line 152) - Indicators: time\.time\(\)
- `test_jwt_malicious_claims_injection` (line 319) - Indicators: time\.time\(\)
- `test_oauth_real_vulnerability_detection` (line 391) - Indicators: time\.time\(\)

### tests\services\test_apex_optimizer_tool_selection_part4.py
- `test_tool_selection_performance` (line 64) - Indicators: time\.time\(\)
- `test_concurrent_tool_execution_scaling` (line 90) - Indicators: time\.time\(\)

### tests\services\test_base_repository.py
- `test_repository_create` (line 29) - Indicators: time\.time\(\)
- `test_repository_bulk_create` (line 36) - Indicators: time\.time\(\)
- `test_repository_get_by_id` (line 66) - Indicators: time\.time\(\)

### tests\services\test_circuit_breaker_manager_comprehensive.py
- `test_circuit_breaker_metrics_collection` (line 335) - Indicators: datetime\.now\(\)
- `test_bulk_circuit_breaker_operations` (line 357) - Indicators: datetime\.now\(\)

### tests\services\test_corpus_service.py
- `test_corpus_status_enum` (line 19) - Indicators: datetime\.now\(\)
- `test_corpus_schema` (line 28) - Indicators: datetime\.now\(\)
- `test_corpus_create_schema` (line 48) - Indicators: datetime\.now\(\)

### tests\services\test_corpus_service_comprehensive.py
- `test_incremental_indexing` (line 224) - Indicators: datetime\.now\(\)
- `test_document_deduplication` (line 249) - Indicators: datetime\.now\(\)

### tests\services\test_job_store_service.py
- `test_job_store_initialization` (line 20) - Indicators: datetime\.now\(\)
- `test_set_and_get_job` (line 26) - Indicators: datetime\.now\(\)
- `test_update_job_status` (line 45) - Indicators: datetime\.now\(\)
- `test_nonexistent_job` (line 62) - Indicators: datetime\.now\(\)
- `test_global_job_store` (line 69) - Indicators: datetime\.now\(\)

### tests\services\test_llm_cache_service.py
- `test_llm_cache_service_initialization` (line 13) - Indicators: time\.time\(\)
- `test_cache_set_and_get` (line 19) - Indicators: time\.time\(\)
- `test_cache_size_limit` (line 66) - Indicators: time\.time\(\)

### tests\services\test_llm_load_balancing.py
- `test_response_time_based_load_balancing` (line 105) - Indicators: time\.time\(\)
- `test_adaptive_load_balancing` (line 131) - Indicators: time\.time\(\)

### tests\services\test_permission_service_admin.py
- `test_permission_escalation_attempt` (line 118) - Indicators: os\.environ
- `test_grant_permission` (line 141) - Indicators: os\.environ

### tests\services\test_permission_service_core.py
- `test_critical_permissions_restricted` (line 45) - Indicators: os\.environ
- `test_detect_developer_with_dev_mode_env` (line 56) - Indicators: os\.environ
- `test_detect_developer_with_netra_email` (line 74) - Indicators: os\.environ
- `test_detect_developer_with_dev_environment` (line 92) - Indicators: os\.environ
- `test_detect_developer_priority_order` (line 108) - Indicators: os\.environ
- `test_detect_developer_with_none_email` (line 118) - Indicators: os\.environ
- `test_update_user_role_auto_elevate_to_developer` (line 135) - Indicators: os\.environ

### tests\services\test_permission_service_integration.py
- `test_production_environment_security` (line 89) - Indicators: os\.environ
- `test_customer_support_workflow` (line 109) - Indicators: os\.environ
- `test_environment_based_access_control` (line 188) - Indicators: os\.environ
- `test_privilege_escalation_prevention` (line 219) - Indicators: os\.environ
- `test_role_transition_security` (line 243) - Indicators: os\.environ

### tests\services\test_quality_gate_storage_stats.py
- `test_validate_batch_parallel_execution` (line 162) - Indicators: time\.time\(\)

### tests\services\test_quality_gate_validation.py
- `test_cache_hit_performance` (line 136) - Indicators: time\.time\(\)

### tests\services\test_rate_limiting_service_comprehensive.py
- `test_rate_limit_config_creation` (line 45) - Indicators: datetime\.now\(\)
- `test_rate_limit_config_defaults` (line 50) - Indicators: datetime\.now\(\)
- `test_rate_limit_result_structure` (line 56) - Indicators: datetime\.now\(\)
- `test_add_named_limiter` (line 72) - Indicators: datetime\.now\(\)
- `test_get_nonexistent_limiter_returns_default` (line 95) - Indicators: datetime\.now\(\)
- `test_rate_limit_check_allowed` (line 101) - Indicators: datetime\.now\(\)
- `test_rate_limit_check_denied` (line 119) - Indicators: datetime\.now\(\)

### tests\services\test_redis_manager_performance.py
- `test_high_throughput_operations` (line 35) - Indicators: time\.time\(\)
- `test_memory_usage_under_load` (line 54) - Indicators: time\.time\(\)

### tests\services\test_state_persistence.py
- `test_state_versioning` (line 134) - Indicators: datetime\.now\(\)
- `test_concurrent_state_updates` (line 165) - Indicators: datetime\.now\(\)

### tests\services\test_state_persistence_integration_critical.py
- `test_correct_session_pattern` (line 68) - Indicators: datetime\.now\(\)
- `test_save_state_with_datetime` (line 76) - Indicators: datetime\.now\(\)
- `test_datetime_serialization` (line 128) - Indicators: datetime\.now\(\)
- `test_save_sub_agent_result` (line 147) - Indicators: datetime\.now\(\)
- `test_list_thread_runs` (line 218) - Indicators: datetime\.now\(\)

### tests\services\test_supply_research_scheduler_jobs.py
- `test_concurrent_job_limit_enforcement` (line 431) - Indicators: random\.

### tests\services\test_thread_repository.py
- `test_get_active_threads` (line 38) - Indicators: datetime\.now\(\)
- `test_archive_thread` (line 63) - Indicators: datetime\.now\(\)

### tests\services\test_thread_service.py
- `test_get_or_create_thread_existing` (line 65) - Indicators: time\.time\(\)

### tests\services\test_tool_dispatcher.py
- `test_tool_registration` (line 49) - Indicators: time\.time\(\)

### tests\services\test_tool_registry_performance.py
- `test_large_scale_tool_registration` (line 34) - Indicators: time\.time\(\)
- `test_tool_discovery_performance` (line 60) - Indicators: time\.time\(\)
- `test_concurrent_tool_access` (line 85) - Indicators: time\.time\(\)
- `test_memory_usage_with_large_registry` (line 120) - Indicators: threading\.
- `test_tool_search_performance` (line 145) - Indicators: time\.time\(\)
- `test_bulk_operations_performance` (line 172) - Indicators: time\.time\(\)
- `test_cache_performance` (line 194) - Indicators: time\.time\(\)
- `test_stress_test_tool_operations` (line 218) - Indicators: time\.time\(\)

### tests\services\test_websocket_message_router_comprehensive.py
- `test_middleware_pipeline_processing` (line 147) - Indicators: time\.time\(\)
- `test_multiple_handlers_different_types` (line 174) - Indicators: time\.time\(\)

### tests\services\test_ws_connection_performance.py
- `test_high_volume_connection_handling` (line 57) - Indicators: time\.time\(\)

### tests\startup\test_backend_server_listening_fix.py
- `test_health_endpoint` (line 114) - Indicators: time\.time\(\)

### tests\startup\test_config_engine.py
- `test_get_fallback_action_stale_ci` (line 142) - Indicators: os\.environ
- `test_detect_ci_environment_true` (line 157) - Indicators: os\.environ
- `test_detect_ci_environment_false` (line 163) - Indicators: os\.environ
- `test_extract_env_overrides` (line 169) - Indicators: os\.environ
- `test_handle_fallback_action_use_defaults` (line 177) - Indicators: os\.environ
- `test_handle_fallback_action_prompt_user` (line 186) - Indicators: os\.environ

### tests\startup\test_config_validation.py
- `test_check_file_age_recent` (line 127) - Indicators: datetime\.now\(\)
- `test_check_file_age_stale` (line 138) - Indicators: datetime\.now\(\)
- `test_load_config_success` (line 160) - Indicators: datetime\.now\(\)

### tests\startup\test_health_monitor_adaptive.py
- `test_apply_adaptive_rules_slow_startup` (line 52) - Indicators: datetime\.now\(\)
- `test_apply_adaptive_rules_frequent_failures` (line 65) - Indicators: datetime\.now\(\)
- `test_count_recent_failures` (line 75) - Indicators: datetime\.now\(\)
- `test_get_check_interval_adaptive` (line 94) - Indicators: datetime\.now\(\)

### tests\startup\test_health_monitor_checks.py
- `test_update_service_stage_progression` (line 157) - Indicators: datetime\.now\(\)
- `test_calculate_stage_initialization` (line 173) - Indicators: datetime\.now\(\)
- `test_calculate_stage_startup` (line 178) - Indicators: datetime\.now\(\)
- `test_calculate_stage_warming` (line 183) - Indicators: datetime\.now\(\)

### tests\startup\test_health_monitor_core.py
- `test_stage_config_creation` (line 95) - Indicators: datetime\.now\(\)
- `test_service_state_creation` (line 111) - Indicators: datetime\.now\(\)
- `test_monitor_init` (line 125) - Indicators: datetime\.now\(\)
- `test_init_stage_configs` (line 132) - Indicators: datetime\.now\(\)

### tests\startup\test_migration_race_condition.py
- `test_concurrent_initialization_race_condition` (line 202) - Indicators: threading\.

### tests\startup\test_server_startup_listening.py
- `test_server_health_once_started` (line 70) - Indicators: time\.time\(\)

### tests\startup\test_server_startup_timeout_fix.py
- `test_database_initialization_timeout_protection` (line 32) - Indicators: time\.time\(\)
- `test_startup_health_checks_timeout_protection` (line 64) - Indicators: time\.time\(\)
- `test_async_postgres_initialization_wrapper` (line 95) - Indicators: time\.time\(\)
- `test_mock_database_mode_fast_path` (line 195) - Indicators: time\.time\(\)
- `test_complete_startup_with_timeouts` (line 225) - Indicators: time\.time\(\)

### tests\startup\test_staged_health_monitor.py
- `test_stage_config_creation` (line 108) - Indicators: datetime\.now\(\)
- `test_service_state_creation` (line 124) - Indicators: datetime\.now\(\)
- `test_monitor_init` (line 138) - Indicators: datetime\.now\(\)
- `test_init_stage_configs` (line 145) - Indicators: datetime\.now\(\)
- `test_update_service_stage_progression` (line 349) - Indicators: datetime\.now\(\)
- `test_calculate_stage_initialization` (line 365) - Indicators: datetime\.now\(\)
- `test_calculate_stage_startup` (line 370) - Indicators: datetime\.now\(\)
- `test_calculate_stage_warming` (line 375) - Indicators: datetime\.now\(\)
- `test_calculate_stage_operational` (line 380) - Indicators: datetime\.now\(\)
- `test_apply_adaptive_rules_slow_startup` (line 388) - Indicators: datetime\.now\(\)
- `test_apply_adaptive_rules_frequent_failures` (line 400) - Indicators: datetime\.now\(\)
- `test_count_recent_failures` (line 410) - Indicators: datetime\.now\(\)
- `test_get_check_interval_adaptive` (line 429) - Indicators: datetime\.now\(\)

### tests\startup\test_startup_diagnostics.py
- `test_init_creates_empty_lists` (line 88) - Indicators: os\.environ
- `test_collect_real_system_errors` (line 99) - Indicators: os\.environ
- `test_collect_errors_with_missing_env` (line 117) - Indicators: os\.environ
- `test_check_port_conflicts_real_ports` (line 131) - Indicators: os\.environ
- `test_check_database_connection_real` (line 183) - Indicators: os\.environ
- `test_database_connection_with_test_db` (line 199) - Indicators: os\.environ
- `test_database_connection_with_invalid_url` (line 209) - Indicators: os\.environ
- `test_check_dependencies_real_environment` (line 225) - Indicators: os\.environ, subprocess\.
- `test_python_environment_check` (line 238) - Indicators: subprocess\.
- `test_pip_availability` (line 250) - Indicators: subprocess\.
- `test_check_environment_variables_current_env` (line 265) - Indicators: os\.environ, subprocess\.
- `test_environment_variables_with_required_set` (line 278) - Indicators: os\.environ
- `test_environment_variables_missing_critical` (line 293) - Indicators: os\.environ
- `test_check_migrations_up_to_date` (line 317) - Indicators: os\.environ
- `test_check_migrations_pending` (line 328) - Indicators: os\.environ

### tests\test_framework\test_coverage_generation.py
- `test_unit_level_generates_coverage` (line 27) - Indicators: subprocess\.
- `test_integration_level_generates_coverage` (line 56) - Indicators: subprocess\.
- `test_critical_level_generates_coverage` (line 84) - Indicators: subprocess\.
- `test_smoke_level_does_not_generate_coverage` (line 112) - Indicators: subprocess\.
- `test_no_coverage_flag_overrides_unit_level` (line 138) - Indicators: subprocess\.
- `test_coverage_in_backend_args_unit_level` (line 180) - Indicators: subprocess\.

### tests\unified_system\test_agent_activation.py
- `test_sub_agent_spawning` (line 350) - Indicators: time\.time\(\)

### tests\unified_system\test_dev_launcher_startup.py
- `test_startup_time_within_limits` (line 642) - Indicators: time\.time\(\)
- `test_parallel_startup_performance_gain` (line 681) - Indicators: time\.time\(\)

### tests\unified_system\test_health_coordination.py
- `test_health_check_performance_requirements` (line 290) - Indicators: time\.time\(\)
- `test_health_check_error_scenarios` (line 334) - Indicators: time\.time\(\)

### tests\unified_system\test_message_pipeline.py
- `test_first_message_agent_activation` (line 129) - Indicators: time\.time\(\)
- `test_concurrent_message_processing` (line 362) - Indicators: time\.time\(\)
- `test_error_handling_and_recovery` (line 427) - Indicators: time\.time\(\)

### tests\unified_system\test_service_recovery.py
- `test_crash_detection_and_recovery` (line 607) - Indicators: time\.time\(\)

### tests\unit\test_agent_lifecycle.py
- `test_post_run_completion` (line 151) - Indicators: time\.time\(\)
- `test_post_run_failure` (line 158) - Indicators: time\.time\(\)
- `test_execution_timing_calculation` (line 163) - Indicators: time\.time\(\)
- `test_lifecycle_status_update_success` (line 169) - Indicators: time\.time\(\)
- `test_lifecycle_status_update_failure` (line 175) - Indicators: time\.time\(\)

### tests\unit\test_async_rate_limiter.py
- `test_rate_limiter_stores_max_calls` (line 72) - Indicators: time\.time\(\)
- `test_rate_limiter_stores_time_window` (line 76) - Indicators: time\.time\(\)
- `test_rate_limiter_starts_empty` (line 80) - Indicators: time\.time\(\)
- `test_acquire_single_call` (line 99) - Indicators: time\.time\(\)
- `test_acquire_multiple_calls` (line 106) - Indicators: time\.time\(\)
- `test_acquire_beyond_limit_waits` (line 113) - Indicators: time\.time\(\)
- `test_can_make_call_check` (line 124) - Indicators: time\.time\(\)
- `test_acquire_updates_call_list` (line 131) - Indicators: time\.time\(\)
- `test_partial_window_expiration` (line 156) - Indicators: time\.time\(\)
- `test_cleanup_old_calls_method` (line 167) - Indicators: time\.time\(\)
- `test_wait_time_calculation` (line 174) - Indicators: time\.time\(\)
- `test_concurrent_acquisitions` (line 184) - Indicators: time\.time\(\)
- `test_lock_prevents_race_conditions` (line 191) - Indicators: time\.time\(\)
- `test_many_expired_calls_cleanup` (line 274) - Indicators: time\.time\(\)
- `test_recursive_acquire_handling` (line 284) - Indicators: time\.time\(\)
- `test_current_calls_property` (line 300) - Indicators: time\.time\(\)
- `test_remaining_calls_property` (line 307) - Indicators: time\.time\(\)
- `test_remaining_calls_never_negative` (line 314) - Indicators: time\.time\(\)
- `test_property_consistency` (line 322) - Indicators: time\.time\(\)

### tests\unit\test_async_resource_manager.py
- `test_concurrent_limit_respected` (line 193) - Indicators: time\.time\(\)
- `test_semaphore_controls_execution` (line 206) - Indicators: time\.time\(\)
- `test_task_cleanup_after_completion` (line 220) - Indicators: time\.time\(\)
- `test_task_pool_shutdown_empty` (line 232) - Indicators: time\.time\(\)
- `test_task_pool_shutdown_with_tasks` (line 238) - Indicators: time\.time\(\)
- `test_shutdown_timeout_handling` (line 249) - Indicators: time\.time\(\)
- `test_shutdown_idempotent` (line 263) - Indicators: time\.time\(\)
- `test_get_global_resource_manager` (line 272) - Indicators: time\.time\(\)

### tests\unit\test_auth_staging_url_configuration.py
- `test_auth_config_returns_correct_staging_urls` (line 51) - Indicators: os\.environ
- `test_database_password_authentication_fails_with_wrong_credentials` (line 174) - Indicators: os\.environ
- `test_pre_deployment_credential_validation_missing` (line 192) - Indicators: os\.environ
- `test_cloud_sql_proxy_connection_format_mismatch` (line 206) - Indicators: os\.environ
- `test_socket_close_error_on_sigterm` (line 226) - Indicators: os\.environ
- `test_jwt_secret_environment_variable_mismatch` (line 289) - Indicators: os\.environ
- `test_jwt_malformed_not_enough_segments` (line 306) - Indicators: os\.environ
- `test_oauth_callback_incomplete_user_data` (line 314) - Indicators: os\.environ
- `test_oauth_invalid_client_staging_dev_mismatch` (line 336) - Indicators: os\.environ
- `test_oauth_redirect_uri_domain_mismatch` (line 352) - Indicators: os\.environ
- `test_missing_oauth_environment_validation` (line 366) - Indicators: os\.environ
- `test_sslmode_parameter_not_converted_for_asyncpg` (line 379) - Indicators: os\.environ
- `test_cloud_sql_unix_socket_with_ssl_parameters` (line 397) - Indicators: os\.environ
- `test_missing_comprehensive_ssl_resolution` (line 412) - Indicators: os\.environ
- `test_full_staging_deployment_simulation` (line 423) - Indicators: os\.environ
- `test_pre_deployment_validation_framework_needed` (line 466) - Indicators: os\.environ

### tests\unit\test_batch_message_transactional.py
- `test_filter_retryable_messages` (line 138) - Indicators: time\.time\(\)

### tests\unit\test_circuit_breaker_core.py
- `test_metrics_track_state_changes` (line 327) - Indicators: datetime\.now\(\)
- `test_should_attempt_reset_after_timeout` (line 336) - Indicators: datetime\.now\(\)
- `test_should_not_reset_before_timeout` (line 344) - Indicators: datetime\.now\(\)
- `test_open_to_half_open_transition` (line 350) - Indicators: datetime\.now\(\)
- `test_cleanup_cancels_health_check_task` (line 363) - Indicators: datetime\.now\(\)
- `test_public_record_methods_work` (line 372) - Indicators: datetime\.now\(\)

### tests\unit\test_cost_calculator_critical.py
- `test_batch_calculation_performance` (line 202) - Indicators: time\.time\(\)
- `test_concurrent_calculation_consistency` (line 210) - Indicators: time\.time\(\)

### tests\unit\test_feature_flags_example.py
- `test_api_response_time` (line 93) - Indicators: time\.time\(\)
- `test_websocket_integration` (line 112) - Indicators: time\.time\(\)

### tests\unit\test_llm_heartbeat_logging.py
- `test_global_heartbeat_logger_singleton` (line 80) - Indicators: time\.time\(\)
- `test_elapsed_time_calculation` (line 86) - Indicators: time\.time\(\)
- `test_heartbeat_message_format` (line 99) - Indicators: time\.time\(\)

### tests\unit\test_llm_resource_manager.py
- `test_concurrent_limit` (line 22) - Indicators: datetime\.now\(\)
- `test_rate_limiting` (line 41) - Indicators: datetime\.now\(\)
- `test_batch_collection` (line 59) - Indicators: datetime\.now\(\)

### tests\unit\test_metrics_collector_core.py
- `test_record_metric_basic` (line 272) - Indicators: datetime\.now\(\)
- `test_cleanup_old_metrics` (line 286) - Indicators: datetime\.now\(\)

### tests\unit\test_metrics_collector_summary.py
- `test_get_recent_metrics_filtered` (line 33) - Indicators: datetime\.now\(\)
- `test_get_recent_metrics_nonexistent` (line 53) - Indicators: datetime\.now\(\)
- `test_get_metric_summary_with_data` (line 61) - Indicators: datetime\.now\(\)
- `test_calculate_cache_hit_ratio_missing_stats` (line 113) - Indicators: datetime\.now\(\)
- `test_metric_buffer_size_limits` (line 123) - Indicators: datetime\.now\(\)
- `test_summary_statistics_accuracy` (line 138) - Indicators: datetime\.now\(\)
- `test_time_based_filtering_edge_cases` (line 162) - Indicators: datetime\.now\(\)
- `test_metric_aggregation_performance` (line 190) - Indicators: datetime\.now\(\)
- `test_concurrent_metric_access_safety` (line 219) - Indicators: datetime\.now\(\)
- `test_metric_cleanup_efficiency` (line 250) - Indicators: datetime\.now\(\)

### tests\unit\test_permission_service_unit.py
- `test_developer_or_higher_detection` (line 235) - Indicators: os\.environ
- `test_power_user_not_developer` (line 239) - Indicators: os\.environ
- `test_superuser_flag_grants_admin_access` (line 243) - Indicators: os\.environ
- `test_dev_mode_enables_developer_status` (line 252) - Indicators: os\.environ
- `test_dev_mode_false_no_developer_status` (line 258) - Indicators: os\.environ
- `test_netra_domain_enables_developer_status` (line 263) - Indicators: os\.environ
- `test_external_domain_no_developer_status` (line 272) - Indicators: os\.environ
- `test_dev_environment_enables_developer_status` (line 279) - Indicators: os\.environ
- `test_prod_environment_no_developer_status` (line 285) - Indicators: os\.environ
- `test_should_elevate_to_developer_checks` (line 293) - Indicators: os\.environ
- `test_should_not_elevate_existing_developer` (line 298) - Indicators: os\.environ
- `test_should_not_elevate_admin` (line 303) - Indicators: os\.environ
- `test_elevate_user_to_developer_updates_fields` (line 308) - Indicators: os\.environ
- `test_update_user_role_with_dev_detection` (line 316) - Indicators: os\.environ
- `test_update_user_role_without_dev_detection` (line 324) - Indicators: os\.environ

### tests\unit\test_postgres_events_config_migration.py
- `test_database_url_environment_variable_handling` (line 123) - Indicators: os\.environ
- `test_pool_configuration_without_database_config_class` (line 134) - Indicators: os\.environ
- `test_resilience_handling_during_config_errors` (line 147) - Indicators: os\.environ

### tests\unit\test_pr_router_state.py
- `test_validate_state_timestamp_valid` (line 70) - Indicators: time\.time\(\)
- `test_validate_state_timestamp_expired` (line 77) - Indicators: time\.time\(\)
- `test_store_csrf_token_redis_enabled` (line 89) - Indicators: time\.time\(\)
- `test_validate_csrf_token_success` (line 98) - Indicators: time\.time\(\)

### tests\unit\test_security_middleware.py
- `test_rate_limit_multiple_identifiers_independent` (line 106) - Indicators: time\.time\(\)
- `test_rate_limit_cleanup_old_requests` (line 119) - Indicators: time\.time\(\)
- `test_rate_limit_blocked_ip_remains_blocked` (line 132) - Indicators: time\.time\(\)

### tests\unit\test_user_service_auth.py
- `test_password_verification_timing_attack_resistance` (line 269) - Indicators: time\.time\(\)
- `test_password_hash_verification_edge_cases` (line 286) - Indicators: time\.time\(\)

### tests\utils\test_file_crypto_validation_utils.py
- `test_file_operations` (line 32) - Indicators: tempfile\.
- `test_cleanup_on_error` (line 43) - Indicators: tempfile\.

### tests\utils\test_monitoring_debug_migration_utils.py
- `test_metric_aggregation` (line 41) - Indicators: time\.time\(\)
- `test_profiling_utilities` (line 81) - Indicators: time\.time\(\)

### tests\validation\test_config_migration_validation.py
- `test_no_direct_os_environ_in_production_code` (line 23) - Indicators: os\.environ
- `test_environment_detection_still_works` (line 66) - Indicators: os\.environ, subprocess\.
- `test_configuration_access_patterns_work` (line 87) - Indicators: os\.environ
- `test_bootstrap_configuration_legitimate_usage` (line 111) - Indicators: os\.environ
- `test_critical_path_imports_work` (line 136) - Indicators: os\.environ
- `test_configuration_constants_accessible` (line 151) - Indicators: os\.environ
- `test_configuration_error_handling` (line 197) - Indicators: os\.environ, subprocess\.

### tests\websocket\test_compression_auth.py
- `test_websocket_compression` (line 91) - Indicators: random\., time\.time\(\)
- `test_authentication_expiry_during_connection` (line 196) - Indicators: time\.time\(\)

### tests\websocket\test_concurrent_connections.py
- `test_concurrent_connection_limit_1000_users` (line 91) - Indicators: time\.time\(\)
- `test_rapid_connect_disconnect_cycles` (line 124) - Indicators: time\.time\(\)
- `test_connection_pool_exhaustion_recovery` (line 166) - Indicators: time\.time\(\)

### tests\websocket\test_memory_monitoring.py
- `test_memory_leak_detection_long_connections` (line 87) - Indicators: time\.time\(\)

### tests\websocket\test_message_ordering.py
- `test_binary_data_transmission` (line 127) - Indicators: random\.
- `test_protocol_version_mismatch` (line 187) - Indicators: random\.

### tests\websocket\test_websocket_auth_edge_cases.py
- `test_rate_limiter_cleanup` (line 495) - Indicators: time\.time\(\)

### tests\websocket\test_websocket_basic_security.py
- `test_websocket_connection_info_validation` (line 72) - Indicators: datetime\.now\(\)
- `test_websocket_security_headers_validation` (line 92) - Indicators: datetime\.now\(\)

### tests\websocket\test_websocket_comprehensive.py
- `test_message_send_receive_json_first` (line 274) - Indicators: time\.time\(\)
- `test_message_json_validation_errors` (line 307) - Indicators: time\.time\(\)
- `test_ping_pong_system_messages` (line 327) - Indicators: time\.time\(\)
- `test_cors_origin_validation_allowed` (line 563) - Indicators: os\.environ
- `test_cors_wildcard_patterns` (line 571) - Indicators: os\.environ
- `test_environment_origins_configuration` (line 580) - Indicators: os\.environ
- `test_websocket_cors_validation` (line 592) - Indicators: os\.environ
- `test_heartbeat_messages` (line 612) - Indicators: time\.time\(\)
- `test_connection_timeout_detection` (line 631) - Indicators: time\.time\(\)
- `test_message_throughput` (line 763) - Indicators: time\.time\(\)
- `test_large_message_handling` (line 793) - Indicators: time\.time\(\)

### tests\websocket\test_websocket_e2e_complete.py
- `test_connection_survives_component_rerender` (line 237) - Indicators: time\.time\(\)
- `test_graceful_error_recovery` (line 255) - Indicators: time\.time\(\)
- `test_heartbeat_keepalive` (line 370) - Indicators: time\.time\(\)
- `test_message_ordering_preservation` (line 384) - Indicators: time\.time\(\)
- `test_websocket_manual_db_sessions` (line 408) - Indicators: time\.time\(\)

### tests\websocket\test_websocket_integration_performance.py
- `test_integrated_performance_improvements` (line 124) - Indicators: time\.time\(\)
- `test_integrated_stress_scenario` (line 163) - Indicators: time\.time\(\)
- `test_integrated_component_interaction` (line 212) - Indicators: time\.time\(\)

### tests\websocket\test_websocket_production_security.py
- `test_tunnel_service_blocking` (line 106) - Indicators: random\.
- `test_browser_extension_blocking` (line 120) - Indicators: random\.
- `test_violation_tracking` (line 199) - Indicators: time\.time\(\)
- `test_temporary_blocking_threshold` (line 210) - Indicators: time\.time\(\)
- `test_many_violations_performance` (line 416) - Indicators: time\.time\(\)
- `test_blocked_origins_lookup_performance` (line 436) - Indicators: time\.time\(\)
- `test_memory_usage_under_attack` (line 457) - Indicators: time\.time\(\)

### tests\websocket\test_websocket_reliability_fixes.py
- `test_message_queue_size_limit` (line 351) - Indicators: time\.time\(\)
- `test_timestamp_array_cleanup` (line 387) - Indicators: time\.time\(\)
- `test_pending_message_retry_mechanism` (line 485) - Indicators: time\.time\(\)
- `test_message_dropped_after_max_retries` (line 523) - Indicators: time\.time\(\)
- `test_jitter_prevents_thundering_herd` (line 632) - Indicators: random\.
- `test_production_https_requirement` (line 665) - Indicators: random\.

### tests\websocket\test_websocket_resilience.py
- `test_connection_timeout_handling` (line 135) - Indicators: time\.time\(\)
- `test_graceful_disconnection_handling` (line 162) - Indicators: time\.time\(\)

### tests\websocket\test_websocket_serialization_critical.py
- `test_datetime_serialization_error_exact_reproduction` (line 66) - Indicators: datetime\.now\(\)
- `test_datetime_encoder_fix_comprehensive` (line 78) - Indicators: datetime\.now\(\)
- `test_invalid_thread_created_message_type` (line 93) - Indicators: datetime\.now\(\)
- `test_all_websocket_message_types_serialization` (line 104) - Indicators: datetime\.now\(\)
- `test_complex_nested_object_serialization` (line 124) - Indicators: datetime\.now\(\)
- `test_broadcast_with_datetime_recovery` (line 138) - Indicators: datetime\.now\(\)
- `test_binary_data_handling` (line 161) - Indicators: datetime\.now\(\)
- `test_large_message_validation` (line 176) - Indicators: datetime\.now\(\)
- `test_connection_state_transitions_serialization` (line 188) - Indicators: datetime\.now\(\)
- `test_concurrent_datetime_serialization` (line 203) - Indicators: datetime\.now\(\)
- `test_message_type_enum_validation_comprehensive` (line 214) - Indicators: datetime\.now\(\)
- `test_broadcast_result_serialization` (line 224) - Indicators: datetime\.now\(\)
- `test_message_validation_security_patterns` (line 237) - Indicators: datetime\.now\(\)
- `test_datetime_in_all_payload_positions` (line 249) - Indicators: datetime\.now\(\)
- `test_serialization_edge_cases` (line 264) - Indicators: datetime\.now\(\)

### tests\e2e\infrastructure\test_llm_test_manager.py
- `test_initialization_with_config` (line 54) - Indicators: os\.environ
- `test_environment_config_loading` (line 60) - Indicators: os\.environ
- `test_mock_response_generation` (line 71) - Indicators: os\.environ
- `test_cache_key_generation` (line 79) - Indicators: os\.environ

### tests\integration\coordination\test_agent_initialization.py
- `test_multi_agent_coordination_initialization` (line 38) - Indicators: time\.time\(\)
- `test_agent_registration_process` (line 51) - Indicators: time\.time\(\)
- `test_simultaneous_agent_startup` (line 61) - Indicators: time\.time\(\)
- `test_agent_initialization_order_tracking` (line 74) - Indicators: time\.time\(\)
- `test_coordination_group_creation` (line 86) - Indicators: time\.time\(\)
- `test_coordination_metrics_tracking` (line 116) - Indicators: time\.time\(\)
- `test_large_scale_agent_initialization` (line 127) - Indicators: time\.time\(\)
- `test_agent_initialization_failure_handling` (line 140) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_2fa_verification.py
- `test_complete_totp_setup_and_verification` (line 810) - Indicators: time\.time\(\)
- `test_sms_fallback_flow` (line 872) - Indicators: time\.time\(\)
- `test_2fa_rate_limiting` (line 937) - Indicators: time\.time\(\)
- `test_session_enhancement_flow` (line 980) - Indicators: time\.time\(\)
- `test_cross_method_verification` (line 1022) - Indicators: time\.time\(\)
- `test_complete_totp_setup_and_verification_flow` (line 1106) - Indicators: time\.time\(\)
- `test_sms_fallback_verification_flow` (line 1145) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_agent_audit_trail.py
- `test_audit_event_querying` (line 680) - Indicators: datetime\.now\(\)
- `test_compliance_reporting` (line 763) - Indicators: datetime\.now\(\)
- `test_encrypted_storage` (line 806) - Indicators: datetime\.now\(\)
- `test_audit_performance` (line 898) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_agent_caching_strategy.py
- `test_cache_performance_benchmarks` (line 1045) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_agent_config_hot_reload.py
- `test_config_file_watching` (line 535) - Indicators: datetime\.now\(\)
- `test_config_validation_rules` (line 565) - Indicators: datetime\.now\(\)
- `test_config_reload_performance` (line 666) - Indicators: time\.time\(\)
- `test_yaml_config_support` (line 703) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_agent_context_isolation_boundaries.py
- `test_cross_tenant_isolation` (line 183) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_agent_context_window.py
- `test_context_compression_summarization` (line 705) - Indicators: datetime\.now\(\)
- `test_context_compression_keywords` (line 740) - Indicators: datetime\.now\(\)
- `test_sliding_window_compression` (line 785) - Indicators: datetime\.now\(\)
- `test_automatic_compression_on_capacity` (line 820) - Indicators: datetime\.now\(\)
- `test_context_window_performance` (line 985) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_agent_cost_optimization.py
- `test_concurrent_optimization_performance` (line 353) - Indicators: time\.time\(\)
- `test_cost_optimization_metrics` (line 374) - Indicators: time\.time\(\)
- `test_optimization_performance_requirements` (line 419) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_agent_cost_tracking.py
- `test_realtime_cache_updates` (line 937) - Indicators: datetime\.now\(\)
- `test_budget_forecasting` (line 1039) - Indicators: datetime\.now\(\)
- `test_cost_tracking_performance` (line 1156) - Indicators: time\.time\(\), datetime\.now\(\)

### tests\integration\critical_paths\test_agent_cost_tracking_l3.py
- `test_real_time_tracking_performance` (line 524) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_agent_dependency_resolution.py
- `test_dependency_resolution_performance` (line 755) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_agent_error_propagation.py
- `test_error_propagation_performance` (line 666) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_agent_failover_recovery_l4.py
- `test_failure_detection` (line 282) - Indicators: random\., time\.time\(\)
- `test_automatic_failover` (line 325) - Indicators: time\.time\(\)
- `test_state_recovery` (line 379) - Indicators: time\.time\(\)
- `test_circuit_breaker` (line 438) - Indicators: time\.time\(\)
- `test_graceful_degradation` (line 481) - Indicators: random\.

### tests\integration\critical_paths\test_agent_fallback_strategies.py
- `test_concurrent_fallback_execution` (line 798) - Indicators: time\.time\(\)
- `test_strategy_success_rate_tracking` (line 833) - Indicators: time\.time\(\)
- `test_fallback_performance_benchmark` (line 857) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_agent_metrics_collection.py
- `test_concurrent_metric_collection` (line 997) - Indicators: time\.time\(\)
- `test_metrics_collection_performance` (line 1033) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_agent_orchestration_revenue_path_l4.py
- `test_concurrent_revenue_workflows` (line 674) - Indicators: time\.time\(\)
- `test_failure_recovery_revenue_protection` (line 726) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_agent_pipeline_circuit_breaking.py
- `test_recovery_mechanism` (line 192) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_agent_pipeline_real_llm.py
- `test_end_to_end_agent_pipeline` (line 405) - Indicators: time\.time\(\)
- `test_error_recovery_scenarios` (line 1114) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_agent_priority_queue.py
- `test_priority_ordering_with_age_factor` (line 564) - Indicators: datetime\.now\(\)
- `test_deadline_based_priority_boost` (line 590) - Indicators: datetime\.now\(\)
- `test_starvation_prevention` (line 612) - Indicators: datetime\.now\(\)
- `test_task_retry_mechanism` (line 639) - Indicators: datetime\.now\(\)
- `test_concurrent_task_processing` (line 685) - Indicators: time\.time\(\)
- `test_queue_capacity_limits` (line 720) - Indicators: time\.time\(\)
- `test_priority_queue_performance` (line 803) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_agent_quality_gate.py
- `test_recent_assessments_retrieval` (line 988) - Indicators: datetime\.now\(\)
- `test_quality_gate_performance` (line 1040) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_agent_quality_gate_pipeline.py
- `test_performance_quality_tradeoff` (line 322) - Indicators: time\.time\(\)
- `test_real_time_quality_monitoring` (line 366) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_agent_resource_allocation.py
- `test_resource_allocation_performance` (line 757) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_agent_resource_pool_management.py
- `test_agent_allocation_within_limits` (line 118) - Indicators: time\.time\(\)
- `test_resource_pool_scaling` (line 205) - Indicators: time\.time\(\)
- `test_memory_pressure_handling` (line 313) - Indicators: time\.time\(\)
- `test_cpu_throttling` (line 357) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_agent_result_aggregation.py
- `test_concurrent_result_aggregation` (line 821) - Indicators: time\.time\(\)
- `test_aggregation_performance_benchmark` (line 856) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_agent_state_persistence.py
- `test_state_validation_rules` (line 445) - Indicators: datetime\.now\(\)
- `test_concurrent_state_operations` (line 470) - Indicators: datetime\.now\(\)
- `test_state_persistence_performance` (line 536) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_agent_state_recovery.py
- `test_agent_crash_and_recovery_under_30_seconds` (line 484) - Indicators: time\.time\(\), tempfile\.
- `test_state_reconstruction_from_checkpoints` (line 514) - Indicators: time\.time\(\)
- `test_failure_detection_and_alerting` (line 630) - Indicators: time\.time\(\)
- `test_recovery_performance_under_load` (line 658) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_agent_timeout_cancellation.py
- `test_cleanup_timeout_handling` (line 669) - Indicators: time\.time\(\)
- `test_cancellation_hook_execution` (line 699) - Indicators: time\.time\(\)
- `test_hook` (line 706) - Indicators: time\.time\(\)
- `test_timeout_cancellation_performance` (line 729) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_agent_tool_authorization.py
- `test_authorization_caching_performance` (line 450) - Indicators: time\.time\(\)
- `test_cross_service_authorization_validation` (line 479) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_agent_tool_execution.py
- `test_concurrent_tool_execution` (line 123) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_agent_tool_loading.py
- `test_concurrent_tool_loading` (line 323) - Indicators: time\.time\(\)
- `test_tool_registry_persistence` (line 353) - Indicators: time\.time\(\)
- `test_tool_loading_performance_benchmark` (line 390) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_agent_version_compatibility.py
- `test_concurrent_version_operations` (line 482) - Indicators: datetime\.now\(\)
- `test_version_compatibility_performance` (line 522) - Indicators: time\.time\(\)
- `test_version_registry_persistence` (line 552) - Indicators: time\.time\(\), datetime\.now\(\)

### tests\integration\critical_paths\test_alert_routing_escalation.py
- `test_alert_routing_accuracy` (line 258) - Indicators: time\.time\(\)
- `test_notification_delivery_reliability` (line 424) - Indicators: time\.time\(\)
- `test_alert_routing_performance_l3` (line 681) - Indicators: time\.time\(\)
- `test_alert_deduplication_and_grouping_l3` (line 706) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_api_authentication.py
- `test_bearer_token_authentication` (line 52) - Indicators: time\.time\(\)
- `test_api_key_authentication` (line 82) - Indicators: time\.time\(\)
- `test_expired_token_rejection` (line 108) - Indicators: time\.time\(\)
- `test_invalid_token_format` (line 140) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_api_cors_policy_enforcement.py
- `test_cors_metrics_accuracy` (line 906) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_api_gateway_load_distribution.py
- `test_response_caching` (line 231) - Indicators: time\.time\(\)
- `test_failover_handling` (line 269) - Indicators: time\.time\(\)
- `test_performance_metrics` (line 304) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_api_gateway_orchestration_l4.py
- `test_authentication_flow_l4` (line 332) - Indicators: time\.time\(\)
- `test_rate_limiting_l4` (line 386) - Indicators: time\.time\(\)
- `test_api_gateway_performance_under_load_l4` (line 739) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_api_gateway_rate_limiting.py
- `test_concurrent_endpoint_requests` (line 344) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_api_key_user_mapping.py
- `test_api_key_validation_flow` (line 324) - Indicators: time\.time\(\)
- `test_rate_limiting_behavior` (line 382) - Indicators: time\.time\(\)
- `test_user_context_caching` (line 426) - Indicators: time\.time\(\)
- `test_audit_trail_integrity` (line 464) - Indicators: time\.time\(\)
- `test_error_scenarios` (line 507) - Indicators: time\.time\(\)
- `test_complete_api_key_user_mapping_flow` (line 604) - Indicators: time\.time\(\)
- `test_api_key_rate_limiting_per_key` (line 637) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_api_rate_limiting_first_requests.py
- `test_burst_traffic` (line 323) - Indicators: time\.time\(\)
- `test_concurrent_users` (line 356) - Indicators: time\.time\(\)
- `test_rate_limit_recovery_after_wait` (line 613) - Indicators: time\.time\(\)
- `test_redis_rate_limit_data_consistency` (line 675) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_api_request_lifecycle_complete_l4.py
- `test_middleware_chain_execution` (line 119) - Indicators: time\.time\(\)
- `test_request_retry_with_backoff` (line 271) - Indicators: time\.time\(\)
- `test_request_tracing_and_correlation` (line 479) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_api_request_routing_rules.py
- `test_load_balancing_distribution` (line 368) - Indicators: time\.time\(\)
- `test_concurrent_routing_requests` (line 687) - Indicators: time\.time\(\)
- `test_route_not_found_handling` (line 716) - Indicators: time\.time\(\)
- `test_routing_metrics_accuracy` (line 798) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_api_request_transformation.py
- `test_transformation_accuracy` (line 837) - Indicators: time\.time\(\)
- `test_transformation_metrics_accuracy` (line 1224) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_api_response_caching.py
- `test_cache_hit_ratio` (line 516) - Indicators: time\.time\(\)
- `test_cache_ttl_expiration` (line 810) - Indicators: time\.time\(\)
- `test_concurrent_cache_requests` (line 836) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_api_response_compression.py
- `test_compression_effectiveness` (line 426) - Indicators: time\.time\(\)
- `test_concurrent_compression_requests` (line 728) - Indicators: time\.time\(\)
- `test_compression_headers_correctness` (line 758) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_api_timeout_cascade.py
- `test_timeout_performance_requirements` (line 843) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_api_versioning_compatibility.py
- `test_version_compatibility` (line 286) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_auth_brute_force_protection.py
- `test_failed_login_tracking` (line 105) - Indicators: time\.time\(\)
- `test_ip_based_rate_limiting` (line 179) - Indicators: time\.time\(\)
- `test_captcha_requirement_after_failures` (line 201) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_auth_cache_invalidation.py
- `test_user_cache_invalidation_flow` (line 494) - Indicators: time\.time\(\)
- `test_cache_coherency_validation` (line 554) - Indicators: time\.time\(\)
- `test_permission_invalidation_cascade` (line 610) - Indicators: time\.time\(\)
- `test_real_time_notification_latency` (line 657) - Indicators: time\.time\(\)
- `test_complete_auth_cache_invalidation_flow` (line 744) - Indicators: time\.time\(\)
- `test_cache_coherency_after_invalidation` (line 787) - Indicators: time\.time\(\)
- `test_concurrent_cache_invalidation_handling` (line 844) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_auth_config_availability.py
- `test_config_endpoint_basic` (line 224) - Indicators: time\.time\(\)
- `test_concurrent_requests` (line 272) - Indicators: time\.time\(\)
- `test_resilience_with_failures` (line 374) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_auth_config_hot_reload.py
- `test_concurrent_coordination_and_no_restart` (line 408) - Indicators: time\.time\(\)
- `test_performance_under_rapid_changes` (line 435) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_auth_flow_l4.py
- `test_logout_flow` (line 712) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_auth_middleware_chain_validation.py
- `test_handler` (line 182) - Indicators: time\.time\(\)
- `test_auth_middleware_token_validation` (line 230) - Indicators: time\.time\(\)
- `test_middleware_performance_under_load` (line 505) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_auth_service_failover_complete_l4.py
- `test_primary_auth_failure_detection` (line 59) - Indicators: time\.time\(\)
- `test_session_state_replication` (line 179) - Indicators: time\.time\(\)
- `test_cascading_failure_recovery` (line 262) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_auth_service_health_dependencies.py
- `test_redis_connectivity` (line 200) - Indicators: time\.time\(\)
- `test_dependency_health_checks` (line 279) - Indicators: os\.environ
- `test_auth_service_performance_metrics` (line 547) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_auth_service_recovery_crash.py
- `test_requests_during_crash_fallback` (line 247) - Indicators: time\.time\(\)
- `test_graceful_vs_crash_recovery_comparison` (line 462) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_auth_session_lifecycle_complete_l4.py
- `test_token_validation_with_clock_skew` (line 277) - Indicators: time\.time\(\)
- `test_session_migration_between_devices` (line 304) - Indicators: time\.time\(\)
- `test_jwt_signature_rotation` (line 424) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_auth_token_refresh_high_load.py
- `test_concurrent_token_refresh_1000_users` (line 150) - Indicators: time\.time\(\)
- `test_sustained_refresh_load_pattern` (line 212) - Indicators: random\.
- `test_token_refresh_race_conditions` (line 265) - Indicators: random\., time\.time\(\)

### tests\integration\critical_paths\test_billing_accuracy_l4.py
- `test_billing_performance_under_sustained_load` (line 782) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_binary_message_handling.py
- `test_large_file_performance` (line 731) - Indicators: time\.time\(\)
- `test_concurrent_uploads` (line 785) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_business_critical_flows_l2.py
- `test_usage_metering_pipeline` (line 390) - Indicators: time\.time\(\)
- `test_payment_webhook_processing` (line 494) - Indicators: time\.time\(\)
- `test_subscription_lifecycle` (line 680) - Indicators: time\.time\(\)
- `test_revenue_recognition` (line 836) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_cache_coherence_l4.py
- `test_cache_write_performance` (line 167) - Indicators: time\.time\(\)
- `test_cache_read_performance` (line 212) - Indicators: time\.time\(\)
- `test_cache_invalidation_coherence` (line 256) - Indicators: time\.time\(\)
- `test_ttl_accuracy_and_eviction` (line 330) - Indicators: time\.time\(\)
- `test_concurrent_cache_operations` (line 384) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_cache_consistency_across_regions.py
- `test_eventual_consistency` (line 296) - Indicators: random\., time\.time\(\)
- `test_conflict_resolution` (line 384) - Indicators: random\.
- `test_cross_region_read_performance` (line 497) - Indicators: random\.

### tests\integration\critical_paths\test_cache_invalidation.py
- `test_multi_service_cache_invalidation` (line 188) - Indicators: time\.time\(\)
- `test_redis_circuit_breaker_integration` (line 390) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_cache_invalidation_cascade.py
- `test_cache_coherence` (line 257) - Indicators: random\.
- `test_cache_metrics` (line 540) - Indicators: random\.

### tests\integration\critical_paths\test_cache_key_collision_handling.py
- `test_birthday_paradox_collisions` (line 266) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_cache_serialization_performance.py
- `test_serialization_format_performance` (line 337) - Indicators: time\.time\(\)
- `test_concurrent_serialization_performance` (line 405) - Indicators: time\.time\(\)
- `test_large_data_serialization` (line 471) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_cache_stampede_prevention.py
- `test_basic_stampede_prevention` (line 277) - Indicators: time\.time\(\)
- `test_multiple_key_stampede_prevention` (line 314) - Indicators: random\., time\.time\(\)
- `test_cache_warming_prevention` (line 433) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_cache_state_management_l2.py
- `test_66_redis_cache_invalidation_cascade` (line 75) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_cache_ttl_expiration_accuracy.py
- `test_ttl_precision_under_load` (line 235) - Indicators: random\., time\.time\(\)
- `test_bulk_ttl_accuracy` (line 360) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_cache_warming_strategy.py
- `test_cold_vs_warm_latency` (line 582) - Indicators: random\.
- `test_warming_efficiency` (line 638) - Indicators: random\., time\.time\(\)

### tests\integration\critical_paths\test_circuit_breaker_cascade.py
- `test_cascade_protection` (line 135) - Indicators: time\.time\(\)
- `test_circuit_breaker_redis_integration` (line 311) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_circuit_breaker_l4.py
- `test_circuit_breaker_state_transitions` (line 402) - Indicators: time\.time\(\)
- `test_cascade_failure_prevention` (line 468) - Indicators: time\.time\(\)
- `test_recovery_monitoring` (line 676) - Indicators: time\.time\(\)
- `test_circuit_breaker_performance_under_load_l4` (line 998) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_clickhouse_batch_insertion_performance.py
- `test_batch_insertion_performance` (line 159) - Indicators: random\., time\.time\(\)
- `test_large_batch_memory_usage` (line 228) - Indicators: time\.time\(\)
- `test_concurrent_batch_insertions` (line 292) - Indicators: time\.time\(\)
- `test_data_consistency_after_batch_insert` (line 358) - Indicators: time\.time\(\), datetime\.now\(\)
- `test_data_consistency_validation` (line 503) - Indicators: time\.time\(\)
- `test_performance_under_memory_pressure` (line 515) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_cold_startup_readiness_detection.py
- `test_startup_timeout_detection` (line 202) - Indicators: time\.time\(\)
- `test_health_endpoint_provides_startup_progress_info` (line 222) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_concurrent_editing_performance.py
- `test_permission_check_performance_benchmarks` (line 203) - Indicators: time\.time\(\)
- `test_high_volume_permission_validation` (line 228) - Indicators: time\.time\(\)
- `test_concurrent_workspace_operations` (line 256) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_concurrent_session_management_l4.py
- `test_concurrent_session_creation_same_user` (line 52) - Indicators: random\.
- `test_session_state_consistency_under_concurrent_updates` (line 160) - Indicators: random\.

### tests\integration\critical_paths\test_concurrent_user_login_sessions.py
- `test_login_race_condition_handling` (line 357) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_configuration_hot_reload.py
- `test_concurrent_config_updates` (line 919) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_configuration_hot_reload_l3.py
- `test_concurrent_reloads` (line 442) - Indicators: time\.time\(\)
- `test_rollback_capabilities` (line 469) - Indicators: time\.time\(\)
- `test_zero_downtime_updates` (line 561) - Indicators: time\.time\(\)
- `test_performance_under_load` (line 815) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_configuration_validation_pipeline.py
- `test_basic_config_validation_performance` (line 514) - Indicators: time\.time\(\)
- `test_schema_validation_comprehensive` (line 540) - Indicators: time\.time\(\)
- `test_validation_result_caching` (line 737) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_config_hot_reload_l4.py
- `test_secret_rotation_hot_reload` (line 1164) - Indicators: time\.time\(\)
- `test_l4_concurrent_config_updates_coordination` (line 1916) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_connection_pool_management.py
- `test_pool_performance_benchmarks` (line 1153) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_core_system_initialization.py
- `test_startup_performance_benchmarks` (line 381) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_cost_optimization_workflow_l4.py
- `test_cost_calculation_accuracy_l4` (line 405) - Indicators: time\.time\(\)
- `test_budget_monitoring_and_alerts_l4` (line 474) - Indicators: time\.time\(\)
- `test_cost_optimization_algorithms_l4` (line 559) - Indicators: time\.time\(\)
- `test_cost_optimization_workflow_e2e_l4` (line 841) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_cross_database_transaction_consistency.py
- `test_atomic_cross_database_operations` (line 520) - Indicators: time\.time\(\)
- `test_eventual_consistency_synchronization` (line 537) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_cross_region_consistency_l4.py
- `test_eventual_consistency` (line 614) - Indicators: random\.
- `test_conflict_resolution` (line 710) - Indicators: random\.
- `test_region_failover` (line 916) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_cross_service_auth_propagation_complete_l4.py
- `test_auth_context_enrichment_across_services` (line 133) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_cross_service_config_consistency.py
- `test_service_discovery_integration` (line 696) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_custom_metrics_registration.py
- `test_metric_registration_process` (line 219) - Indicators: time\.time\(\)
- `test_dynamic_metric_collection` (line 282) - Indicators: time\.time\(\)
- `test_metric_lifecycle_management` (line 503) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_database_coordination_l2.py
- `test_58_database_lock_contention` (line 420) - Indicators: time\.time\(\)
- `test_61_materialized_view_refresh` (line 559) - Indicators: time\.time\(\)
- `test_62_database_backup_integration` (line 600) - Indicators: time\.time\(\), datetime\.now\(\)

### tests\integration\critical_paths\test_database_failover_recovery_flow.py
- `test_replica_synchronization` (line 140) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_database_migration_rollback.py
- `test_migration_validation_prevents_dangerous_operations` (line 810) - Indicators: time\.time\(\)
- `test_concurrent_migration_safety` (line 832) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_database_partition_management.py
- `test_partition_maintenance_operations` (line 378) - Indicators: datetime\.now\(\)
- `test_partition_query_optimization` (line 463) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_database_pool_initialization.py
- `test_connection_acquisition_performance` (line 294) - Indicators: time\.time\(\)
- `test_pool_size_limits_enforcement` (line 346) - Indicators: time\.time\(\)
- `test_connection_recycling_and_health` (line 434) - Indicators: time\.time\(\)
- `test_connection_leak_detection` (line 547) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_database_query_timeout_handling.py
- `test_postgres_query_timeout_enforcement` (line 183) - Indicators: time\.time\(\), datetime\.now\(\)
- `test_clickhouse_query_timeout_enforcement` (line 254) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_database_read_replica_routing.py
- `test_read_load_balancing` (line 255) - Indicators: random\., time\.time\(\)

### tests\integration\critical_paths\test_database_sharding_strategy_l4.py
- `test_sharding_performance_under_load_l4` (line 772) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_database_transaction_consistency.py
- `test_postgres_transaction_atomicity` (line 88) - Indicators: time\.time\(\)
- `test_clickhouse_consistency` (line 176) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_database_transaction_deadlock_resolution.py
- `test_transaction_isolation_levels` (line 485) - Indicators: time\.time\(\)
- `test_deadlock_monitoring_and_logging` (line 525) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_database_transaction_integrity_l4.py
- `test_bulk_insert_atomicity` (line 280) - Indicators: random\., time\.time\(\)

### tests\integration\critical_paths\test_dev_environment_agent_response_flow_l4.py
- `test_message_processing` (line 309) - Indicators: datetime\.now\(\)
- `test_conversation_flow` (line 446) - Indicators: time\.time\(\)
- `test_agent_handoff` (line 514) - Indicators: time\.time\(\)
- `test_concurrent_responses` (line 579) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_dev_environment_auth_login_complete_l4.py
- `test_user_registration` (line 100) - Indicators: time\.time\(\), datetime\.now\(\)
- `test_email_verification` (line 162) - Indicators: time\.time\(\)
- `test_user_login` (line 204) - Indicators: time\.time\(\)
- `test_token_validation` (line 257) - Indicators: time\.time\(\), datetime\.now\(\)
- `test_token_refresh` (line 298) - Indicators: time\.time\(\)
- `test_cross_service_auth` (line 350) - Indicators: time\.time\(\), datetime\.now\(\)
- `test_logout_flow` (line 465) - Indicators: datetime\.now\(\)

### tests\integration\critical_paths\test_dev_environment_chat_initialization_l4.py
- `test_basic_thread_creation` (line 230) - Indicators: time\.time\(\)
- `test_context_loading` (line 320) - Indicators: time\.time\(\), datetime\.now\(\)
- `test_agent_assignment` (line 399) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_dev_environment_concurrent_users_l4.py
- `test_user_isolation` (line 467) - Indicators: time\.time\(\)
- `test_concurrent_scenario` (line 600) - Indicators: datetime\.now\(\)

### tests\integration\critical_paths\test_dev_environment_websocket_connection_l4.py
- `test_basic_connection` (line 108) - Indicators: time\.time\(\), datetime\.now\(\)
- `test_concurrent_connections` (line 150) - Indicators: time\.time\(\)
- `test_heartbeat_mechanism` (line 209) - Indicators: time\.time\(\), datetime\.now\(\)
- `test_reconnection_logic` (line 262) - Indicators: time\.time\(\)
- `test_message_delivery` (line 302) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_dev_login_cold_start.py
- `test_dev_login_user_creation` (line 257) - Indicators: time\.time\(\)
- `test_auth_config_endpoint_cold_start_performance` (line 278) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_distributed_auth_state_sync_l4.py
- `test_concurrent_writes_conflict_resolution` (line 311) - Indicators: time\.time\(\)
- `test_cross_region_token_validation` (line 463) - Indicators: time\.time\(\)
- `test_distributed_rate_limiting` (line 519) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_distributed_lock_contention.py
- `test_high_contention_scenarios` (line 253) - Indicators: time\.time\(\)
- `test_deadlock_detection_and_resolution` (line 346) - Indicators: time\.time\(\)
- `test_lock_performance_under_load` (line 547) - Indicators: random\., time\.time\(\)

### tests\integration\critical_paths\test_distributed_tracing.py
- `test_context_propagation` (line 143) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_error_circuit_breakers.py
- `test_load_based_circuit_behavior` (line 335) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_frontend_initial_auth_flow_l4.py
- `test_frontend_auth_flow_performance_l4` (line 990) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_graceful_websocket_shutdown.py
- `test_message_preservation_during_shutdown` (line 1206) - Indicators: time\.time\(\)
- `test_shutdown_performance_benchmarks` (line 1645) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_health_check_cascade.py
- `test_dependency_health_propagation` (line 128) - Indicators: time\.time\(\)
- `test_health_check_alerting` (line 165) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_health_check_cascade_initialization.py
- `test_dependency_chain_validation` (line 456) - Indicators: time\.time\(\)
- `test_performance_overhead` (line 528) - Indicators: time\.time\(\)
- `test_recovery_detection` (line 567) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_heartbeat_mechanism.py
- `test_heartbeat_performance_under_load` (line 1461) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_integration_failures_audit.py
- `test_agent_retry_with_exponential_backoff` (line 164) - Indicators: datetime\.now\(\)
- `test_agent_memory_leak_under_sustained_load` (line 197) - Indicators: datetime\.now\(\)
- `test_memory_pressure_graceful_degradation` (line 603) - Indicators: datetime\.now\(\)

### tests\integration\critical_paths\test_job_concurrency_limits.py
- `test_resource_exhaustion_handling_l3` (line 777) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_job_progress_tracking.py
- `test_progress_broadcast_functionality_l3` (line 711) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_job_queue_priority_processing.py
- `test_concurrent_priority_processing_l3` (line 271) - Indicators: time\.time\(\)
- `test_queue_statistics_accuracy_l3` (line 308) - Indicators: time\.time\(\)
- `test_priority_queue_performance_l3` (line 343) - Indicators: time\.time\(\)
- `test_mixed_workload_priority_handling_l3` (line 382) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_job_retry_with_dead_letter.py
- `test_exponential_backoff_implementation_l3` (line 332) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_jwt_refresh_websocket.py
- `test_jwt_refresh_with_expired_refresh_token` (line 715) - Indicators: time\.time\(\)
- `test_jwt_refresh_performance_under_load` (line 768) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_llm_provider_failover.py
- `test_circuit_breaker_recovery` (line 633) - Indicators: time\.time\(\)
- `test_failover_performance_benchmarks` (line 734) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_message_compression.py
- `test_messages` (line 941) - Indicators: time\.time\(\)
- `test_basic_compression_functionality` (line 1000) - Indicators: time\.time\(\)
- `test_compression_performance_benchmarks` (line 1393) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_message_ordering_guarantees.py
- `test_basic_sequence_assignment` (line 502) - Indicators: time\.time\(\)
- `test_order_enforcer_delivery` (line 712) - Indicators: time\.time\(\)
- `test_ordering_performance_benchmarks` (line 932) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_message_pipeline_l4.py
- `test_throughput_performance` (line 616) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_message_queue_websocket_broadcast.py
- `test_user_targeted_messaging` (line 732) - Indicators: time\.time\(\)
- `test_client_connection_lifecycle` (line 936) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_metrics_aggregation_pipeline_l4.py
- `test_time_series_aggregation_l4` (line 330) - Indicators: time\.time\(\)
- `test_metrics_aggregation_pipeline_e2e_l4` (line 821) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_metrics_observability.py
- `test_sla_monitoring` (line 185) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_metrics_pipeline_l4.py
- `test_dashboard_queries` (line 521) - Indicators: time\.time\(\)
- `test_datasource_connection` (line 548) - Indicators: time\.time\(\)
- `test_metrics_pipeline_performance_l4_staging` (line 698) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_metrics_prometheus.py
- `test_metrics_time_series` (line 170) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_metrics_retention_policy.py
- `test_automated_cleanup_process` (line 472) - Indicators: time\.time\(\)
- `test_compliance_tracking` (line 534) - Indicators: random\., time\.time\(\)

### tests\integration\critical_paths\test_multitab_websocket_sync.py
- `test_concurrent_tab_operations` (line 1251) - Indicators: time\.time\(\)
- `test_tab_lifecycle_performance` (line 1372) - Indicators: time\.time\(\)
- `test_comprehensive_metrics_tracking` (line 1426) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_multi_agent_orchestration.py
- `test_parallel_agent_execution_with_result_aggregation` (line 417) - Indicators: time\.time\(\)
- `test_agent_failure_recovery_with_state_preservation` (line 442) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_multi_agent_workflow.py
- `test_parallel_workflow_execution` (line 358) - Indicators: time\.time\(\)
- `test_conditional_workflow_routing` (line 383) - Indicators: time\.time\(\)
- `test_concurrent_workflow_execution` (line 499) - Indicators: time\.time\(\)
- `test_workflow_performance_benchmark` (line 532) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_multi_device_session_sync.py
- `test_concurrent_device_state_conflicts` (line 763) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_multi_device_session_sync_l4.py
- `test_real_time_updates` (line 163) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_multi_service_auth_token_propagation.py
- `test_token_invalidation_propagation` (line 140) - Indicators: time\.time\(\)
- `test_concurrent_token_access` (line 183) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_multi_service_token_propagation.py
- `test_backend_token_validation` (line 123) - Indicators: time\.time\(\)
- `test_database_user_context` (line 153) - Indicators: time\.time\(\)
- `test_redis_cache_user_context` (line 186) - Indicators: time\.time\(\)
- `test_agent_service_propagation` (line 224) - Indicators: time\.time\(\)
- `test_concurrent_token_propagation` (line 256) - Indicators: time\.time\(\)
- `test_multi_service_token_propagation_flow` (line 333) - Indicators: time\.time\(\)
- `test_concurrent_multi_token_propagation` (line 379) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_multi_tenant_config_isolation.py
- `test_configuration_namespace_isolation` (line 300) - Indicators: time\.time\(\)
- `test_data_residency_enforcement` (line 404) - Indicators: time\.time\(\)
- `test_cache_namespace_separation` (line 550) - Indicators: time\.time\(\)
- `test_configuration_hot_reload_per_tenant` (line 622) - Indicators: time\.time\(\)
- `test_analytics_isolation_validation` (line 707) - Indicators: time\.time\(\)
- `test_database_row_level_security` (line 806) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_multi_tenant_isolation.py
- `test_cross_tenant_access` (line 211) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_multi_tenant_isolation_l4.py
- `test_cross_organization_access_prevention` (line 278) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_multi_tenant_session_isolation.py
- `test_concurrent_operations` (line 215) - Indicators: random\.

### tests\integration\critical_paths\test_multi_tenant_workspace_isolation.py
- `test_cross_tenant_workspace_access_prevention` (line 383) - Indicators: time\.time\(\)
- `test_concurrent_multi_tenant_operations` (line 668) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_oauth_jwt_websocket_flow.py
- `test_token_propagation` (line 378) - Indicators: time\.time\(\)
- `test_error_scenarios` (line 424) - Indicators: time\.time\(\)
- `test_complete_oauth_jwt_websocket_flow` (line 525) - Indicators: time\.time\(\)
- `test_oauth_jwt_websocket_error_handling` (line 589) - Indicators: time\.time\(\)
- `test_oauth_jwt_websocket_performance_benchmarks` (line 641) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_password_reset_token_flow.py
- `test_token_expiration_handling` (line 360) - Indicators: time\.time\(\)
- `test_multi_device_token_invalidation` (line 384) - Indicators: time\.time\(\)
- `test_cleanup_expired_tokens_performance` (line 441) - Indicators: time\.time\(\)
- `test_password_reset_flow_metrics` (line 460) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_performance_scalability_l2.py
- `test_82_batch_processing_performance` (line 1012) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_postgres_connection_pool_exhaustion.py
- `test_pool_exhaustion_behavior` (line 146) - Indicators: time\.time\(\)
- `test_concurrent_connection_requests` (line 243) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_prometheus_metrics_accuracy.py
- `test_prometheus_timestamp_accuracy_l3` (line 455) - Indicators: time\.time\(\)
- `test_prometheus_label_consistency_l3` (line 481) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_rate_limiting.py
- `test_burst_capacity` (line 172) - Indicators: time\.time\(\)
- `test_sustained_rate_limiting` (line 196) - Indicators: time\.time\(\)
- `test_multi_identifier_isolation` (line 227) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_rate_limiting_per_tier.py
- `test_tier_differentiation` (line 411) - Indicators: time\.time\(\)
- `test_burst_handling` (line 475) - Indicators: time\.time\(\)
- `test_dynamic_limit_updates` (line 528) - Indicators: time\.time\(\)
- `test_fair_queuing` (line 583) - Indicators: time\.time\(\)
- `test_tier_based_rate_limiting_differentiation` (line 671) - Indicators: time\.time\(\)
- `test_burst_allowance_handling` (line 702) - Indicators: time\.time\(\)
- `test_rate_limiting_performance_under_load` (line 759) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_redis_cache_invalidation_cascade.py
- `test_invalidation_under_load` (line 379) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_redis_cache_warming_startup.py
- `test_incremental_cache_warming` (line 486) - Indicators: time\.time\(\)
- `test_cache_invalidation_handling` (line 525) - Indicators: random\., time\.time\(\)
- `test_parallel_cache_warming_efficiency` (line 559) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_redis_cluster_coordination_l4.py
- `test_master_slave_replication` (line 190) - Indicators: time\.time\(\)
- `test_automatic_failover` (line 248) - Indicators: time\.time\(\)
- `test_resharding` (line 306) - Indicators: time\.time\(\)
- `test_performance_under_load` (line 424) - Indicators: random\., time\.time\(\)

### tests\integration\critical_paths\test_redis_cluster_resharding.py
- `test_performance_impact_during_resharding` (line 388) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_redis_memory_pressure_eviction.py
- `test_concurrent_eviction_performance` (line 419) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_saml_sso_integration.py
- `test_complete_saml_sso_flow` (line 486) - Indicators: time\.time\(\)
- `test_jit_user_provisioning` (line 568) - Indicators: time\.time\(\)
- `test_assertion_replay_protection` (line 614) - Indicators: time\.time\(\)
- `test_attribute_mapping_roles` (line 648) - Indicators: time\.time\(\)
- `test_session_management_sso` (line 707) - Indicators: time\.time\(\)
- `test_complete_saml_sso_authentication_flow` (line 794) - Indicators: time\.time\(\)
- `test_jit_user_provisioning_and_updates` (line 833) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_service_discovery.py
- `test_load_balanced_service_calls` (line 258) - Indicators: time\.time\(\)
- `test_service_failover` (line 331) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_service_discovery_bootstrap.py
- `test_service_registration_within_time_limits_l3` (line 611) - Indicators: time\.time\(\)
- `test_service_discovery_returns_correct_endpoints_l3` (line 633) - Indicators: time\.time\(\)
- `test_health_status_propagation_l3` (line 667) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_service_mesh_discovery.py
- `test_service_discovery_l4` (line 42) - Indicators: time\.time\(\)
- `test_instance_health` (line 99) - Indicators: random\., time\.time\(\)
- `test_service_discovery_l4_staging` (line 137) - Indicators: time\.time\(\)
- `test_service_discovery_concurrent_access` (line 223) - Indicators: time\.time\(\)
- `test_service_discovery_instance_registration` (line 262) - Indicators: time\.time\(\)
- `test_service_discovery_failure_recovery` (line 318) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_service_mesh_l4.py
- `test_service_discovery_l4` (line 246) - Indicators: time\.time\(\)
- `test_instance_health` (line 303) - Indicators: time\.time\(\)
- `test_load_balancing_algorithms_l4` (line 337) - Indicators: time\.time\(\)
- `test_round_robin_lb` (line 383) - Indicators: time\.time\(\)
- `test_random_lb` (line 527) - Indicators: random\.
- `test_circuit_breaker_half_open_to_closed` (line 848) - Indicators: time\.time\(\)
- `test_circuit_breaker_failure_threshold` (line 893) - Indicators: time\.time\(\)
- `test_circuit_breaker_timeout` (line 950) - Indicators: time\.time\(\)
- `test_retry_policies_l4` (line 997) - Indicators: time\.time\(\)
- `test_exponential_backoff_retry` (line 1025) - Indicators: time\.time\(\)
- `test_fixed_delay_retry` (line 1113) - Indicators: time\.time\(\)
- `test_linear_backoff_retry` (line 1181) - Indicators: time\.time\(\)
- `test_retry_jitter` (line 1276) - Indicators: time\.time\(\)
- `test_service_mesh_performance_l4_staging` (line 1478) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_service_mesh_routing.py
- `test_round_robin_lb` (line 92) - Indicators: time\.time\(\)
- `test_random_lb` (line 238) - Indicators: random\.

### tests\integration\critical_paths\test_session_persistence_restart.py
- `test_session_recovery_after_restart` (line 470) - Indicators: time\.time\(\)
- `test_websocket_reconnection_after_restart` (line 921) - Indicators: time\.time\(\)
- `test_restart_performance_impact` (line 1195) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_slo_calculation_accuracy.py
- `test_slo_calculation_performance_l3` (line 906) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_staging_environment_imports.py
- `test_middleware_setup_without_dev_launcher` (line 74) - Indicators: os\.environ
- `test_staging_cors_configuration` (line 91) - Indicators: os\.environ
- `test_route` (line 106) - Indicators: os\.environ
- `test_staging_environment_detection` (line 230) - Indicators: os\.environ

### tests\integration\critical_paths\test_staging_secrets_loading.py
- `test_staging_config_secret_loading_failure` (line 100) - Indicators: os\.environ
- `test_production_config_secret_loading_failure` (line 135) - Indicators: os\.environ
- `test_development_config_still_affected_by_placeholder_bug` (line 161) - Indicators: os\.environ
- `test_environment_detection_edge_cases` (line 222) - Indicators: os\.environ
- `test_cloud_sql_logging_repetition` (line 248) - Indicators: os\.environ
- `test_secret_validation_consistency_cross_environments` (line 281) - Indicators: os\.environ
- `test_unified_config_manager_secret_integration` (line 306) - Indicators: os\.environ
- `test_configuration_error_propagation` (line 364) - Indicators: os\.environ
- `test_secret_manager_types_consistency` (line 384) - Indicators: os\.environ
- `test_complete_staging_secret_loading_pipeline` (line 434) - Indicators: os\.environ
- `test_gcp_secret_manager_availability_detection` (line 484) - Indicators: os\.environ
- `test_secret_mapping_configuration_consistency` (line 513) - Indicators: os\.environ

### tests\integration\critical_paths\test_staging_worker_startup_validation.py
- `test_worker_exit_code_3_detection` (line 297) - Indicators: os\.environ
- `test_cloudsql_connection_validation` (line 310) - Indicators: os\.environ
- `test_dependency_cascade_failure` (line 329) - Indicators: os\.environ
- `test_worker_configuration_requirements` (line 346) - Indicators: os\.environ
- `test_multiple_worker_startup` (line 364) - Indicators: os\.environ
- `test_startup_timeout_handling` (line 400) - Indicators: os\.environ, time\.time\(\)
- `test_error_pattern_detection` (line 423) - Indicators: os\.environ, time\.time\(\)
- `test_staging_worker_health_check_integration` (line 443) - Indicators: os\.environ

### tests\integration\critical_paths\test_startup_manager_integration.py
- `test_app` (line 40) - Indicators: os\.environ
- `test_startup_manager_timeout_handling_with_app_state` (line 177) - Indicators: time\.time\(\)
- `test_startup_manager_metrics_integration` (line 552) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_subscription_tier_enforcement.py
- `test_free_tier_monthly_limit_enforcement` (line 158) - Indicators: time\.time\(\)
- `test_mid_tier_concurrent_limit_enforcement` (line 242) - Indicators: time\.time\(\)
- `test_enterprise_unlimited_access` (line 318) - Indicators: time\.time\(\)
- `test_tier_downgrade_enforcement` (line 363) - Indicators: time\.time\(\)
- `test_cross_service_tier_validation` (line 432) - Indicators: time\.time\(\)
- `test_billing_event_generation` (line 496) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_supervisor_subagent_communication.py
- `test_basic_delegation_flow` (line 381) - Indicators: time\.time\(\)
- `test_sub_agent_tool_execution` (line 468) - Indicators: time\.time\(\)
- `test_parallel_sub_agent_execution` (line 539) - Indicators: time\.time\(\)
- `test_state_persistence_across_agents` (line 627) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_system_startup_sequences_l4.py
- `test_startup_auth_token_generation` (line 391) - Indicators: time\.time\(\)
- `test_startup_websocket_auth_initialization` (line 411) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_trace_sampling_accuracy.py
- `test_sampling_performance_impact` (line 546) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_user_state_persistence_complete_l4.py
- `test_user_state_during_database_failure` (line 154) - Indicators: time\.time\(\)
- `test_user_activity_tracking_persistence` (line 199) - Indicators: time\.time\(\)
- `test_user_state_versioning` (line 238) - Indicators: time\.time\(\)
- `test_user_state_bulk_operations` (line 279) - Indicators: time\.time\(\)
- `test_user_state_migration` (line 363) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_websocket_auth_handshake.py
- `test_expired_token_rejection` (line 1300) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_websocket_binary_message_handling.py
- `test_large_binary_file_handling` (line 453) - Indicators: time\.time\(\)
- `test_binary_message_websocket_transmission` (line 500) - Indicators: time\.time\(\)
- `test_binary_message_size_limits` (line 682) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_websocket_broadcast_performance.py
- `test_small_scale_broadcast_baseline` (line 204) - Indicators: time\.time\(\)
- `test_medium_scale_broadcast_performance` (line 303) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_websocket_circuit_breaker.py
- `test_circuit_breaker_basic_functionality` (line 825) - Indicators: time\.time\(\)
- `test_circuit_breaker_performance_benchmarks` (line 1266) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_websocket_connection_draining.py
- `test_connection_migration_during_draining` (line 159) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_websocket_database_integration.py
- `test_concurrent_sessions` (line 259) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_websocket_first_load.py
- `test_websocket_upgrade_from_http` (line 383) - Indicators: time\.time\(\)
- `test_authentication_token_validation` (line 428) - Indicators: time\.time\(\)
- `test_connection_establishment_performance` (line 513) - Indicators: time\.time\(\)
- `test_concurrent_connections_50_plus` (line 753) - Indicators: time\.time\(\)
- `test_websocket_performance_under_load` (line 868) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_websocket_health_check.py
- `test_unhealthy_connection_detection` (line 842) - Indicators: time\.time\(\)
- `test_concurrent_health_checks` (line 880) - Indicators: time\.time\(\)
- `test_health_check_performance_benchmarks` (line 1025) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_websocket_heartbeat_monitoring.py
- `test_heartbeat_expiration_detection` (line 289) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_websocket_jwt_validation_failure.py
- `test_websocket_successful_auth_dev_environment` (line 190) - Indicators: os\.environ

### tests\integration\critical_paths\test_websocket_load_balancing.py
- `test_concurrent_routing_performance` (line 1529) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_websocket_load_balancing_l4.py
- `test_connection_distribution_l4` (line 276) - Indicators: random\., time\.time\(\)
- `test_server_failover_l4` (line 375) - Indicators: time\.time\(\)
- `test_health_check_monitoring_l4` (line 457) - Indicators: time\.time\(\)
- `test_websocket_load_balancing_performance_l4` (line 624) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_websocket_message_compression.py
- `test_basic_message_compression` (line 311) - Indicators: time\.time\(\)
- `test_compression_performance_under_load` (line 561) - Indicators: time\.time\(\)
- `test_compression_bandwidth_savings` (line 653) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_websocket_message_delivery_guarantees_l4.py
- `test_message_ordering_under_load` (line 48) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_websocket_rate_limiting_per_client.py
- `test_rate_limiting_accuracy_and_performance` (line 638) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_websocket_reconnection_resilience_l4.py
- `test_websocket_exponential_backoff_reconnection` (line 112) - Indicators: time\.time\(\)
- `test_websocket_connection_state_machine` (line 217) - Indicators: time\.time\(\)
- `test_websocket_reconnect_with_auth_refresh` (line 309) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_websocket_reconnection_state.py
- `test_connection_state_preservation` (line 779) - Indicators: time\.time\(\)
- `test_message_buffering_during_disconnect` (line 827) - Indicators: time\.time\(\)
- `test_successful_reconnection_with_state_restoration` (line 875) - Indicators: time\.time\(\)
- `test_state_expiration_handling` (line 1074) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_websocket_reconnection_state_recovery.py
- `test_state_recovery_performance` (line 637) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_websocket_resilience_l4.py
- `test_websocket_performance_under_stress_l4` (line 1023) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_websocket_resilience_recovery.py
- `test_message_delivery_during_reconnection` (line 365) - Indicators: time\.time\(\)
- `test_message_queuing_during_disconnection` (line 610) - Indicators: time\.time\(\)

### tests\integration\critical_paths\test_websocket_unified_critical.py
- `test_regular_json_format` (line 372) - Indicators: time\.time\(\)
- `test_json_rpc_format_mcp_endpoint` (line 393) - Indicators: time\.time\(\)
- `test_graceful_disconnect_cleanup` (line 572) - Indicators: time\.time\(\)
- `test_connection_timeout_handling` (line 606) - Indicators: time\.time\(\)
- `test_cors_validation` (line 626) - Indicators: time\.time\(\)
- `test_connection_cleanup_race_conditions` (line 948) - Indicators: time\.time\(\)

### tests\integration\llm\test_llm_providers.py
- `test_llm_provider_token_tracking` (line 54) - Indicators: time\.time\(\)
- `test_llm_provider_performance_timing` (line 66) - Indicators: time\.time\(\)
- `test_llm_manager_provider_fallback` (line 78) - Indicators: time\.time\(\)
- `test_llm_manager_request_metrics_tracking` (line 91) - Indicators: time\.time\(\)

### tests\integration\metrics\test_metrics_pipeline.py
- `test_end_to_end_pipeline_performance` (line 47) - Indicators: time\.time\(\)
- `test_pipeline_data_integrity` (line 96) - Indicators: time\.time\(\)
- `test_pipeline_metric_accuracy` (line 114) - Indicators: time\.time\(\)
- `test_pipeline_efficiency_metrics` (line 144) - Indicators: time\.time\(\)
- `test_high_volume_pipeline_reliability` (line 167) - Indicators: time\.time\(\)
- `test_buffer_overflow_handling` (line 191) - Indicators: time\.time\(\)

### tests\integration\metrics\test_metric_aggregation.py
- `test_metrics_aggregation_processing` (line 45) - Indicators: time\.time\(\)
- `test_request_count_aggregation` (line 64) - Indicators: time\.time\(\)

### tests\integration\metrics\test_metric_collection.py
- `test_user_action_metric_capture` (line 43) - Indicators: time\.time\(\)
- `test_metric_metadata_capture` (line 60) - Indicators: time\.time\(\)

### tests\integration\metrics\test_metric_storage.py
- `test_metrics_storage_verification` (line 44) - Indicators: time\.time\(\)
- `test_data_persistence` (line 66) - Indicators: time\.time\(\)
- `test_storage_metadata_tracking` (line 82) - Indicators: time\.time\(\)
- `test_multiple_storage_operations` (line 95) - Indicators: time\.time\(\)
- `test_storage_performance_at_scale` (line 112) - Indicators: time\.time\(\)
- `test_storage_error_handling` (line 131) - Indicators: time\.time\(\)

### tests\integration\staging\test_staging_database_connection_resilience.py
- `test_postgresql_connection_pooling_and_failover` (line 88) - Indicators: time\.time\(\)

### tests\integration\staging\test_staging_secrets_manager_integration.py
- `test_fallback_mechanism_local_to_gsm` (line 113) - Indicators: os\.environ
- `test_secret_caching_mechanism` (line 175) - Indicators: os\.environ
- `test_error_handling_for_unavailable_secrets` (line 200) - Indicators: os\.environ
- `test_secret_validation_against_staging_requirements` (line 221) - Indicators: os\.environ
- `test_local_environment_file_precedence` (line 246) - Indicators: os\.environ
- `test_secret_interpolation_in_staging` (line 279) - Indicators: os\.environ

### tests\integration\staging\test_staging_startup_configuration_validation.py
- `test_all_required_staging_environment_variables_present` (line 61) - Indicators: os\.environ
- `test_staging_ssl_requirements_enforced` (line 82) - Indicators: os\.environ
- `test_configuration_loading_from_multiple_sources` (line 99) - Indicators: os\.environ
- `test_staging_specific_settings_override_development_defaults` (line 111) - Indicators: os\.environ
- `test_clickhouse_staging_configuration_validation` (line 130) - Indicators: os\.environ
- `test_fallback_to_default_when_env_missing` (line 154) - Indicators: os\.environ
- `test_configuration_validation_reports_comprehensive_issues` (line 171) - Indicators: os\.environ
- `test_database_summary_reflects_staging_state` (line 188) - Indicators: os\.environ
- `test_localhost_restriction_enforced_in_staging` (line 203) - Indicators: os\.environ

### tests\integration\staging_config\test_database_migrations.py
- `test_pending_migrations` (line 73) - Indicators: os\.environ, subprocess\.
- `test_migration_rollback` (line 111) - Indicators: os\.environ, subprocess\.
- `test_schema_consistency` (line 155) - Indicators: os\.environ, subprocess\.

### tests\integration\staging_config\test_health_checks.py
- `test_health_check_timeout` (line 185) - Indicators: time\.time\(\)

### tests\integration\staging_config\test_redis_lifecycle.py
- `test_redis_persistence` (line 77) - Indicators: time\.time\(\)

### tests\integration\staging_config\test_resource_limits.py
- `test_request_rate_limits` (line 115) - Indicators: time\.time\(\)
- `test_payload_size_limits` (line 151) - Indicators: time\.time\(\)

### tests\integration\staging_config\test_staging_startup.py
- `test_startup_with_staging_config` (line 115) - Indicators: os\.environ
- `test_startup_performance` (line 346) - Indicators: time\.time\(\)
- `test_startup_graceful_shutdown` (line 372) - Indicators: time\.time\(\)

### tests\integration\staging_config\test_websocket_load_balancer.py
- `test_websocket_connection` (line 27) - Indicators: time\.time\(\)
- `test_websocket_sticky_sessions` (line 55) - Indicators: time\.time\(\)

### tests\integration\critical_missing\tier1_critical\test_agent_tool_execution_pipeline.py
- `test_basic_tool_execution_pipeline` (line 207) - Indicators: time\.time\(\)
- `test_permission_failure_handling` (line 219) - Indicators: time\.time\(\)
- `test_timeout_handling` (line 228) - Indicators: time\.time\(\)
- `test_concurrent_tool_executions` (line 239) - Indicators: time\.time\(\)
- `test_supervisor_to_subagent_delegation` (line 267) - Indicators: time\.time\(\)

### tests\integration\critical_missing\tier1_critical\test_database_transaction_rollback.py
- `test_data` (line 59) - Indicators: time\.time\(\)
- `test_basic_transaction_rollback` (line 83) - Indicators: time\.time\(\)
- `test_multi_table_rollback_cascade` (line 108) - Indicators: time\.time\(\)
- `test_large_transaction_rollback_performance` (line 297) - Indicators: time\.time\(\)

### tests\integration\critical_missing\tier1_critical\test_subscription_tier_enforcement.py
- `test_free_tier_tool_limits` (line 91) - Indicators: time\.time\(\)
- `test_pro_tier_feature_access` (line 112) - Indicators: time\.time\(\)

### tests\integration\red_team\tier1_catastrophic\test_cross_database_transaction_consistency.py
- `test_03_concurrent_cross_database_transactions_fails` (line 330) - Indicators: time\.time\(\)

### tests\integration\red_team\tier1_catastrophic\test_cross_service_auth_token_validation.py
- `test_02_backend_token_validation_fails` (line 159) - Indicators: time\.time\(\)
- `test_03_token_expiration_handling_fails` (line 206) - Indicators: time\.time\(\)
- `test_05_cross_service_jwt_secret_consistency_fails` (line 266) - Indicators: time\.time\(\)
- `test_06_token_user_context_propagation_fails` (line 310) - Indicators: time\.time\(\)
- `test_07_concurrent_token_validation_fails` (line 353) - Indicators: time\.time\(\)
- `test_08_token_refresh_integration_fails` (line 403) - Indicators: time\.time\(\)

### tests\integration\red_team\tier1_catastrophic\test_llm_service_integration.py
- `test_04_concurrent_llm_requests_fails` (line 281) - Indicators: time\.time\(\)
- `test_07_llm_streaming_response_fails` (line 503) - Indicators: time\.time\(\)

### tests\integration\red_team\tier1_catastrophic\test_message_persistence_and_retrieval.py
- `test_02_message_api_creation_fails` (line 186) - Indicators: time\.time\(\)

### tests\integration\red_team\tier1_catastrophic\test_postgresql_connection_pool_exhaustion.py
- `test_01_connection_pool_basic_exhaustion_fails` (line 99) - Indicators: time\.time\(\)

### tests\integration\red_team\tier1_catastrophic\test_user_session_persistence_restart.py
- `test_01_session_creation_in_redis_fails` (line 83) - Indicators: time\.time\(\)
- `test_02_active_session_validation_fails` (line 124) - Indicators: time\.time\(\)
- `test_03_session_activity_tracking_fails` (line 173) - Indicators: time\.time\(\)
- `test_04_service_restart_session_persistence_fails` (line 224) - Indicators: time\.time\(\)
- `test_05_concurrent_session_management_fails` (line 283) - Indicators: time\.time\(\)
- `test_06_session_expiry_cleanup_fails` (line 356) - Indicators: time\.time\(\)
- `test_07_session_security_validation_fails` (line 414) - Indicators: time\.time\(\)
- `test_08_session_data_integrity_fails` (line 491) - Indicators: time\.time\(\)

### tests\integration\red_team\tier1_catastrophic\test_user_state_synchronization.py
- `test_06_user_data_export_consistency_fails` (line 466) - Indicators: time\.time\(\)

### tests\integration\red_team\tier1_catastrophic\test_websocket_authentication_integration.py
- `test_websocket_connection_with_real_jwt_fails` (line 97) - Indicators: time\.time\(\)
- `test_token_expiration_during_active_websocket_fails` (line 153) - Indicators: time\.time\(\)
- `test_websocket_rejection_with_invalid_tokens_fails` (line 207) - Indicators: time\.time\(\)
- `test_websocket_auth_service_integration_failure` (line 264) - Indicators: time\.time\(\)
- `test_websocket_concurrent_auth_race_condition` (line 310) - Indicators: time\.time\(\)

### tests\integration\red_team\tier1_catastrophic\test_websocket_message_broadcasting.py
- `test_01_basic_websocket_connection_fails` (line 112) - Indicators: time\.time\(\)
- `test_02_message_broadcast_to_single_client_fails` (line 170) - Indicators: time\.time\(\)
- `test_04_agent_to_frontend_message_flow_fails` (line 368) - Indicators: time\.time\(\)
- `test_05_websocket_connection_recovery_fails` (line 493) - Indicators: time\.time\(\)
- `test_06_websocket_message_ordering_fails` (line 588) - Indicators: time\.time\(\)
- `test_08_websocket_error_handling_fails` (line 826) - Indicators: time\.time\(\)

### tests\integration\red_team\tier2_3_security_performance\test_monitoring_observability.py
- `test_36_health_check_endpoint_accuracy_fails` (line 98) - Indicators: tempfile\.
- `test_39_environment_variable_propagation_fails` (line 457) - Indicators: time\.time\(\)
- `test_40_secret_management_integration_fails` (line 601) - Indicators: os\.environ

### tests\integration\red_team\tier2_3_security_performance\test_performance_bottlenecks.py
- `test_31_database_query_performance_under_load_fails` (line 125) - Indicators: time\.time\(\)
- `test_32_connection_pool_scaling_fails` (line 247) - Indicators: time\.time\(\)
- `test_35_cache_invalidation_timing_fails` (line 567) - Indicators: time\.time\(\)

### tests\integration\red_team\tier2_major_failures\test_background_job_processing.py
- `test_05_job_persistence_recovery_fails` (line 580) - Indicators: time\.time\(\)

### tests\integration\red_team\tier2_major_failures\test_file_upload_and_storage.py
- `test_01_basic_file_upload_fails` (line 129) - Indicators: tempfile\.

### tests\integration\red_team\tier2_major_failures\test_graceful_degradation.py
- `test_02_resource_cleanup_fails` (line 169) - Indicators: tempfile\.

### tests\integration\red_team\tier2_major_failures\test_retry_logic_coordination.py
- `test_03_cross_service_retry_amplification_prevention_fails` (line 223) - Indicators: time\.time\(\)
- `test_04_adaptive_retry_strategy_fails` (line 293) - Indicators: time\.time\(\)

### tests\unit\core\test_configuration_validation.py
- `test_configuration_environment_variables` (line 52) - Indicators: os\.environ
- `test_timeout_values_are_reasonable` (line 72) - Indicators: os\.environ
- `test_timeout_environment_specificity` (line 80) - Indicators: os\.environ

### tests\unit\core\test_error_recovery_comprehensive.py
- `test_recovery_context_elapsed_time` (line 44) - Indicators: datetime\.now\(\)
- `test_recovery_context_with_custom_values` (line 60) - Indicators: datetime\.now\(\)

### tests\unit\core\test_secret_manager_comprehensive.py
- `test_production_secret_value_fallback` (line 367) - Indicators: os\.environ
- `test_load_secrets_from_environment_integration` (line 392) - Indicators: os\.environ

### tests\unit\db\test_database_manager.py
- `test_get_base_database_url_conversion` (line 58) - Indicators: os\.environ
- `test_get_base_database_url_default_fallback` (line 71) - Indicators: os\.environ
- `test_validate_base_url` (line 156) - Indicators: os\.environ
- `test_validate_migration_url_sync_format` (line 172) - Indicators: os\.environ
- `test_validate_application_url` (line 187) - Indicators: os\.environ
- `test_is_cloud_sql_environment_true` (line 206) - Indicators: os\.environ
- `test_is_cloud_sql_environment_false` (line 213) - Indicators: os\.environ
- `test_is_cloud_sql_environment_no_url` (line 220) - Indicators: os\.environ
- `test_is_local_development_true` (line 229) - Indicators: os\.environ
- `test_is_local_development_false` (line 240) - Indicators: os\.environ
- `test_is_remote_environment` (line 254) - Indicators: os\.environ
- `test_create_migration_engine_basic` (line 271) - Indicators: os\.environ
- `test_create_migration_engine_with_sql_echo` (line 302) - Indicators: os\.environ
- `test_create_application_engine_basic` (line 309) - Indicators: os\.environ
- `test_create_application_engine_cloud_sql` (line 331) - Indicators: os\.environ
- `test_get_migration_session` (line 369) - Indicators: os\.environ
- `test_get_application_session` (line 379) - Indicators: os\.environ
- `test_invalid_url_format_handling` (line 402) - Indicators: os\.environ
- `test_empty_database_url_handling` (line 411) - Indicators: os\.environ
- `test_missing_database_url_handling` (line 423) - Indicators: os\.environ
- `test_driver_mismatch_validation` (line 435) - Indicators: os\.environ
- `test_ssl_parameter_mismatch_validation` (line 445) - Indicators: os\.environ
- `test_default_environment_handling` (line 455) - Indicators: os\.environ
- `test_migration_engine_can_connect` (line 478) - Indicators: os\.environ
- `test_application_session_can_create` (line 497) - Indicators: os\.environ
- `test_url_conversion_end_to_end` (line 515) - Indicators: os\.environ
- `test_url_with_query_parameters_preserved` (line 582) - Indicators: os\.environ
- `test_url_with_special_characters_in_credentials` (line 592) - Indicators: os\.environ
- `test_multiple_ssl_parameters_handling` (line 602) - Indicators: os\.environ
- `test_default_database_url_by_environment` (line 618) - Indicators: os\.environ
- `test_malformed_url_parsing_error` (line 636) - Indicators: os\.environ
- `test_connection_pool_configuration_errors` (line 666) - Indicators: os\.environ
- `test_engine_creation_with_timeout_errors` (line 678) - Indicators: os\.environ
- `test_session_factory_error_handling` (line 694) - Indicators: os\.environ
- `test_concurrent_access_error_handling` (line 706) - Indicators: os\.environ
- `test_environment_variable_handling_with_special_chars` (line 731) - Indicators: os\.environ
- `test_database_manager_state_consistency` (line 755) - Indicators: os\.environ

### tests\unit\services\test_gcp_error_service.py
- `test_build_time_range_invalid_format_defaults` (line 169) - Indicators: datetime\.now\(\)
- `test_build_list_request_with_filters` (line 177) - Indicators: datetime\.now\(\)
- `test_build_list_request_minimal_query` (line 194) - Indicators: datetime\.now\(\)
- `test_create_summary_comprehensive_counts` (line 206) - Indicators: datetime\.now\(\)
- `test_count_by_severity_all_levels` (line 216) - Indicators: datetime\.now\(\)

### tests\unit\agents\data_sub_agent\test_data_validator.py
- `test_validate_valid_raw_data` (line 182) - Indicators: datetime\.now\(\)
- `test_validate_empty_data` (line 194) - Indicators: datetime\.now\(\)
- `test_validate_insufficient_data_points` (line 203) - Indicators: datetime\.now\(\)
- `test_validate_data_with_missing_required_fields` (line 220) - Indicators: datetime\.now\(\)
- `test_validate_data_with_high_null_percentage` (line 233) - Indicators: datetime\.now\(\)
- `test_validate_metric_values_out_of_range` (line 250) - Indicators: datetime\.now\(\)
- `test_validate_invalid_metric_value_types` (line 269) - Indicators: datetime\.now\(\)
- `test_validate_time_span_too_short` (line 288) - Indicators: datetime\.now\(\)
- `test_validate_time_span_sufficient_duration` (line 548) - Indicators: datetime\.now\(\)
- `test_validate_time_span_insufficient_duration` (line 562) - Indicators: datetime\.now\(\)
- `test_validate_time_span_insufficient_timestamps` (line 576) - Indicators: datetime\.now\(\)
- `test_validate_time_span_mixed_timestamp_formats` (line 586) - Indicators: datetime\.now\(\)
- `test_validate_extremely_large_dataset` (line 610) - Indicators: datetime\.now\(\)
- `test_validate_unicode_and_special_characters` (line 631) - Indicators: datetime\.now\(\)
- `test_validate_boundary_metric_values` (line 652) - Indicators: datetime\.now\(\)

### tests\unit\core\resilience\test_domain_circuit_breakers.py
- `test_rate_limit_exceeded` (line 243) - Indicators: time\.time\(\)
- `test_rate_limit_reset` (line 248) - Indicators: time\.time\(\)
- `test_get_stats` (line 260) - Indicators: time\.time\(\)
- `test_initial_state` (line 572) - Indicators: time\.time\(\)
- `test_task_lifecycle` (line 579) - Indicators: time\.time\(\)
- `test_task_failure_with_context_preservation` (line 600) - Indicators: time\.time\(\)
- `test_security_monitor_edge_cases` (line 879) - Indicators: time\.time\(\)
- `test_agent_task_manager_edge_cases` (line 893) - Indicators: time\.time\(\)

### tests\unit\core\resilience\test_unified_circuit_breaker.py
- `test_health_based_recovery` (line 552) - Indicators: time\.time\(\)
- `test_cleanup_health_monitoring` (line 569) - Indicators: time\.time\(\)
- `test_memory_usage_sliding_window` (line 1045) - Indicators: time\.time\(\)
- `test_response_time_tracking_bounds` (line 1059) - Indicators: time\.time\(\)

## Recommended Actions
1. **Immediate**: Apply `@fast_test` decorator to tests with sleep calls
2. **Short-term**: Mock external dependencies (network, LLM, database)
3. **Medium-term**: Refactor large test files into smaller, focused modules
4. **Long-term**: Implement comprehensive performance monitoring in CI

## Tools Available
- `test_framework.performance_helpers.fast_test` - Mock sleep functions
- `test_framework.performance_helpers.timeout_override` - Reduce timeouts
- `test_framework.performance_helpers.mock_external_dependencies` - Mock external calls
- `test_framework.performance_helpers.FlakynessReducer` - Stable wait conditions