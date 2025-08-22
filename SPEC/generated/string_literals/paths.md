# 🛤️ Paths Literals

API endpoints, file paths, directories, and URLs

*Generated on 2025-08-21 21:56:03*

## 📊 Category Statistics

| Metric | Value |
|--------|-------|
| Total Literals | 663 |
| Subcategories | 6 |
| Average Confidence | 0.900 |

## 📋 Subcategories

- [api_endpoint (4 literals)](#subcategory-api-endpoint)
- [dir_path (69 literals)](#subcategory-dir-path)
- [endpoint (61 literals)](#subcategory-endpoint)
- [file_path (451 literals)](#subcategory-file-path)
- [url (74 literals)](#subcategory-url)
- [websocket_endpoint (4 literals)](#subcategory-websocket-endpoint)

## Subcategory: api_endpoint {subcategory-api-endpoint}

**Count**: 4 literals

### 🟢 High (≥0.8) (4 literals)

| Literal | Files | Context | Related |
|---------|-------|---------|---------|
| `/api/auth/config` | launcher.py:664 | DevLauncher._verify_auth_sy... | `/api/health`, `/api/threads` |
| `/api/health` | test_staging_env.py:121 | StagingTester.test_frontend... | `/api/auth/confi...`, `/api/threads` |
| `/api/threads` | test_staging_env.py:69 | StagingTester.test_database... | `/api/auth/confi...`, `/api/health` |
| `/api/user/me` | test_auth_integration.py:70 | AuthServiceTester.test_back... | `/api/auth/confi...`, `/api/health` |

### Usage Examples

- **dev_launcher\launcher.py:664** - `DevLauncher._verify_auth_system`
- **scripts\test_staging_env.py:121** - `StagingTester.test_frontend_api_proxy`
- **scripts\test_staging_env.py:69** - `StagingTester.test_database_connection`

---

## Subcategory: dir_path {subcategory-dir-path}

**Count**: 69 literals

### 🟢 High (≥0.8) (69 literals)

| Literal | Files | Context | Related |
|---------|-------|---------|---------|
| `app/` | code_review_ai_detector.py:47 | CodeReviewAIDetector._check... | `SPEC/`, `SPEC/learnings/` |
| `app/agents` | websocket_coherence_review.py:16 | find_backend_events | `SPEC/`, `SPEC/learnings/` |
| `app/agents/` | code_review_analysis.py:115 | CodeReviewAnalysis._check_k... | `SPEC/`, `SPEC/learnings/` |
| `app/agents/admin\_tool\_dispatcher` | analyze_critical_paths.py:7 | module | `SPEC/`, `SPEC/learnings/` |
| `app/agents/corpus\_admin` | analyze_critical_paths.py:8 | module | `SPEC/`, `SPEC/learnings/` |
| `app/agents/data\_sub\_agent` | analyze_critical_paths.py:9 | module | `SPEC/`, `SPEC/learnings/` |
| `app/agents/supervisor` | analyze_critical_paths.py:6 | module | `SPEC/`, `SPEC/learnings/` |
| `app/agents/supply\_researcher` | analyze_critical_paths.py:10 | module | `SPEC/`, `SPEC/learnings/` |
| `app/agents/triage\_sub\_agent` | analyze_critical_paths.py:11 | module | `SPEC/`, `SPEC/learnings/` |
| `app/auth/` | code_review_analysis.py:117 | CodeReviewAnalysis._check_k... | `SPEC/`, `SPEC/learnings/` |
| `app/config\.\*` | system_diagnostics.py:238 | SystemDiagnostics._find_con... | `SPEC/`, `SPEC/learnings/` |
| `app/data/generated/content\_corpuses` | cleanup_generated_files.py:29 | module | `SPEC/`, `SPEC/learnings/` |
| `app/data/generated/jobs` | cleanup_generated_files.py:36 | module | `SPEC/`, `SPEC/learnings/` |
| `app/db` | analyze_critical_paths.py:13 | module | `SPEC/`, `SPEC/learnings/` |
| `app/db/` | code_review_analysis.py:116 | CodeReviewAnalysis._check_k... | `SPEC/`, `SPEC/learnings/` |
| `app/llm` | analyze_critical_paths.py:15 | module | `SPEC/`, `SPEC/learnings/` |
| `app/pytest\.ini` | fix_common_test_issues.py:13 | fix_async_tests | `SPEC/`, `SPEC/learnings/` |
| `app/routes` | audit_permissions.py:49 | main | `SPEC/`, `SPEC/learnings/` |
| `app/services` | websocket_coherence_review.py:16 | find_backend_events | `SPEC/`, `SPEC/learnings/` |
| `app/services/apex\_optimizer\_agent/` | code_review_analysis.py:136 | CodeReviewAnalysis._check_m... | `SPEC/`, `SPEC/learnings/` |
| `app/services/cache/` | code_review_analysis.py:138 | CodeReviewAnalysis._check_m... | `SPEC/`, `SPEC/learnings/` |
| `app/services/corpus` | analyze_critical_paths.py:12 | module | `SPEC/`, `SPEC/learnings/` |
| `app/services/database/` | code_review_analysis.py:116 | CodeReviewAnalysis._check_k... | `SPEC/`, `SPEC/learnings/` |
| `app/services/state/` | code_review_analysis.py:137 | CodeReviewAnalysis._check_m... | `SPEC/`, `SPEC/learnings/` |
| `app/tests` | aggressive_syntax_fix.py:14 | get_files_with_errors | `SPEC/`, `SPEC/learnings/` |
| `app/tests/agents` | test_backend_optimized.py:68 | module | `SPEC/`, `SPEC/learnings/` |
| `app/tests/core` | benchmark_optimization.py:74 | TestExecutionBenchmark._dis... | `SPEC/`, `SPEC/learnings/` |
| `app/tests/core/test\_config\_manager\...` | test_backend_optimized.py:89 | module | `SPEC/`, `SPEC/learnings/` |
| `app/tests/core/test\_error\_handling\...` | test_backend_optimized.py:88 | module | `SPEC/`, `SPEC/learnings/` |
| `app/tests/critical` | fix_e2e_connection_manager_imports.py:33 | find_files_with_connection_... | `SPEC/`, `SPEC/learnings/` |
| `app/tests/e2e` | fix_e2e_connection_manager_imports.py:29 | find_files_with_connection_... | `SPEC/`, `SPEC/learnings/` |
| `app/tests/integration` | test_backend_optimized.py:62 | module | `SPEC/`, `SPEC/learnings/` |
| `app/tests/models` | test_failure_scanner.py:48 | _get_test_paths_to_scan | `SPEC/`, `SPEC/learnings/` |
| `app/tests/performance` | test_backend_optimized.py:74 | module | `SPEC/`, `SPEC/learnings/` |
| `app/tests/performance/test\_reports` | cleanup_generated_files.py:43 | module | `SPEC/`, `SPEC/learnings/` |
| `app/tests/routes` | benchmark_optimization.py:79 | TestExecutionBenchmark._dis... | `SPEC/`, `SPEC/learnings/` |
| `app/tests/services` | benchmark_optimization.py:74 | TestExecutionBenchmark._dis... | `SPEC/`, `SPEC/learnings/` |
| `app/tests/services/agents/test\_sub\_...` | fix_common_test_issues.py:28 | run_simple_unit_tests | `SPEC/`, `SPEC/learnings/` |
| `app/tests/services/agents/test\_super...` | fix_common_test_issues.py:29 | run_simple_unit_tests | `SPEC/`, `SPEC/learnings/` |
| `app/tests/services/database` | test_failure_scanner.py:43 | _get_test_paths_to_scan | `SPEC/`, `SPEC/learnings/` |
| `app/tests/unit` | fix_e2e_connection_manager_imports.py:32 | find_files_with_connection_... | `SPEC/`, `SPEC/learnings/` |
| `app/tests/utils` | test_failure_scanner.py:49 | _get_test_paths_to_scan | `SPEC/`, `SPEC/learnings/` |
| `app/tests/websocket` | fix_e2e_connection_manager_imports.py:34 | find_files_with_connection_... | `SPEC/`, `SPEC/learnings/` |
| `app/websocket` | analyze_critical_paths.py:14 | module | `SPEC/`, `SPEC/learnings/` |
| `frontend/` | ai_detector.py:140 | AIDetector._check_console_logs | `SPEC/`, `SPEC/learnings/` |
| `frontend/\*\*/\*\.ts` | architecture_metrics.py:225 | ArchitectureMetrics._count_... | `SPEC/`, `SPEC/learnings/` |
| `frontend/\*\*/\*\.tsx` | architecture_metrics.py:225 | ArchitectureMetrics._count_... | `SPEC/`, `SPEC/learnings/` |
| `frontend/\.next` | performance_checker.py:40 | PerformanceChecker._check_f... | `SPEC/`, `SPEC/learnings/` |
| `frontend/\_\_tests\_\_` | fix_frontend_tests.py:129 | main | `SPEC/`, `SPEC/learnings/` |
| `frontend/\_\_tests\_\_/system/startup...` | startup_test_executor.py:113 | FrontendTestExecutor.run_tests | `SPEC/`, `SPEC/learnings/` |
| `frontend/hooks` | websocket_coherence_review.py:54 | find_frontend_handlers | `SPEC/`, `SPEC/learnings/` |
| `frontend/schemas` | check_schema_imports.py:75 | SchemaImportAnalyzer | `SPEC/`, `SPEC/learnings/` |
| `frontend/store` | websocket_coherence_review.py:54 | find_frontend_handlers | `SPEC/`, `SPEC/learnings/` |
| `frontend/tests` | project_test_validator.py:63 | ProjectTestValidator._find_... | `SPEC/`, `SPEC/learnings/` |
| `frontend/types/` | ai_detector.py:84 | AIDetector._check_typescrip... | `SPEC/`, `SPEC/learnings/` |
| `frontend/types/agent\.ts` | deduplicate_types.py:69 | TypeDeduplicator._setup_dup... | `SPEC/`, `SPEC/learnings/` |
| `frontend/types/backend\_schema\_auto\...` | generate_frontend_types.py:30 | main | `SPEC/`, `SPEC/learnings/` |
| `frontend/types/chat\.ts` | deduplicate_types.py:70 | TypeDeduplicator._setup_dup... | `SPEC/`, `SPEC/learnings/` |
| `scripts/start\_with\_discovery\.js` | dev_launcher_service.py:189 | ServiceManager._build_front... | `SPEC/`, `SPEC/learnings/` |
| `SPEC/` | spec_checker.py:53 | SpecChecker._spec_exists | `SPEC/learnings/`, `SPEC/legacy_spe...` |
| `SPEC/learnings/` | split_learnings.py:105 | create_index | `SPEC/`, `SPEC/legacy_spe...` |
| `SPEC/legacy\_specs\_report\.md` | update_spec_timestamps.py:273 | main | `SPEC/`, `SPEC/learnings/` |
| `tests/` | decompose_functions.py:89 | _should_skip_file | `SPEC/`, `SPEC/learnings/` |
| `tests/agents` | find_top_mocks.py:33 | find_mock_patterns | `SPEC/`, `SPEC/learnings/` |
| `tests/e2e` | find_top_mocks.py:32 | find_mock_patterns | `SPEC/`, `SPEC/learnings/` |
| `tests/integration` | find_top_mocks.py:31 | find_mock_patterns | `SPEC/`, `SPEC/learnings/` |
| `tests/unified` | find_top_mocks.py:30 | find_mock_patterns | `SPEC/`, `SPEC/learnings/` |
| `tests/unified/e2e` | fix_e2e_connection_manager_imports.py:30 | find_files_with_connection_... | `SPEC/`, `SPEC/learnings/` |
| `tests/websocket` | find_top_mocks.py:34 | find_mock_patterns | `SPEC/`, `SPEC/learnings/` |

### Usage Examples

- **scripts\code_review_ai_detector.py:47** - `CodeReviewAIDetector._check_duplicates`
- **scripts\websocket_coherence_review.py:16** - `find_backend_events`
- **scripts\code_review_analysis.py:115** - `CodeReviewAnalysis._check_key_specifications`

---

## Subcategory: endpoint {subcategory-endpoint}

**Count**: 61 literals

### 🟢 High (≥0.8) (61 literals)

| Literal | Files | Context | Related |
|---------|-------|---------|---------|
| `    \[OK\] ` | test_staging_startup.py:188 | StagingStartupTester.test_h... | ` != `, ` (` |
| ` \!= ` | validate_network_constants.py:154 | validate_service_endpoints | `    [OK] `, ` (` |
| ` \(` | audit_permissions.py:32 | analyze_route_file | `    [OK] `, ` != ` |
| ` \-> ` | websocket_validator.py:95 | WebSocketValidator._print_e... | `    [OK] `, ` != ` |
| ` failed: ` | test_auth_integration.py:55 | AuthServiceTester.test_auth... | `    [OK] `, ` != ` |
| ` passed` | validate_staging_health.py:69 | StagingHealthValidator._che... | `    [OK] `, ` != ` |
| ` WebSocket endpoints` | websocket_validator.py:78 | WebSocketValidator._discove... | `    [OK] `, ` != ` |
| `\.\*?\(?=\\ndef\|\\Z\)` | audit_permissions.py:27 | analyze_route_file | `    [OK] `, ` != ` |
| `/auth/callback` | verify_auth_config.py:29 | check_auth_service_endpoints | `    [OK] `, ` != ` |
| `/auth/callback?code=test\_code` | test_oauth_flows_sync.py:55 | TestOAuthBasicEndpoints.tes... | `    [OK] `, ` != ` |
| `/auth/callback?state=test\_state` | test_oauth_flows_sync.py:51 | TestOAuthBasicEndpoints.tes... | `    [OK] `, ` != ` |
| `/auth/config` | verify_auth_config.py:27 | check_auth_service_endpoints | `    [OK] `, ` != ` |
| `/auth/health` | test_oauth_flows_sync.py:62 | TestOAuthBasicEndpoints.tes... | `    [OK] `, ` != ` |
| `/auth/login` | verify_auth_config.py:28 | check_auth_service_endpoints | `    [OK] `, ` != ` |
| `/auth/login?provider=google` | test_oauth_flows_sync.py:38 | TestOAuthBasicEndpoints.tes... | `    [OK] `, ` != ` |
| `/auth/logout` | verify_auth_config.py:30 | check_auth_service_endpoints | `    [OK] `, ` != ` |
| `/auth/me` | verify_auth_config.py:32 | check_auth_service_endpoints | `    [OK] `, ` != ` |
| `/auth/token` | verify_auth_config.py:31 | check_auth_service_endpoints | `    [OK] `, ` != ` |
| `/docs` | test_auth_integration.py:43 | AuthServiceTester.test_auth... | `    [OK] `, ` != ` |
| `/health` | test_staging_startup.py:180 | StagingStartupTester.test_h... | `    [OK] `, ` != ` |
| `/health/live` | test_staging_startup.py:182 | StagingStartupTester.test_h... | `    [OK] `, ` != ` |
| `/health/ready` | test_staging_startup.py:181 | StagingStartupTester.test_h... | `    [OK] `, ` != ` |
| `/live` | validate_staging_health.py:60 | StagingHealthValidator._che... | `    [OK] `, ` != ` |
| `/ready` | validate_staging_health.py:56 | StagingHealthValidator._che... | `    [OK] `, ` != ` |
| `2\.0` | test_websocket_validator_fix.py:39 | TestWebSocketValidatorFix.t... | `    [OK] `, ` != ` |
| `8000` | test_websocket_validator_fix.py:203 | TestWebSocketValidatorFix.t... | `    [OK] `, ` != ` |
| `@\\w\+\\\.\(get\|post\|put\|delete\|p...` | status_integration_analyzer.py:109 | IntegrationAnalyzer._extrac... | `    [OK] `, ` != ` |
| `@router\\\.\(get\|post\|put\|delete\|...` | audit_permissions.py:20 | analyze_route_file | `    [OK] `, ` != ` |
| `accounts\.google\.com/o/oauth2/v2/auth` | test_oauth_flows_sync.py:42 | TestOAuthBasicEndpoints.tes... | `    [OK] `, ` != ` |
| `API Documentation` | test_auth_integration.py:43 | AuthServiceTester.test_auth... | `    [OK] `, ` != ` |
| `Auth Endpoint: ` | test_auth_integration.py:52 | AuthServiceTester.test_auth... | `    [OK] `, ` != ` |
| `Auth Health` | test_auth_integration.py:44 | AuthServiceTester.test_auth... | `    [OK] `, ` != ` |
| `auth\-service` | test_oauth_flows_sync.py:67 | TestOAuthBasicEndpoints.tes... | `    [OK] `, ` != ` |
| `Check liveness endpoint\.` | validate_staging_health.py:59 | StagingHealthValidator._che... | `    [OK] `, ` != ` |
| `Check readiness endpoint\.` | validate_staging_health.py:55 | StagingHealthValidator._che... | `    [OK] `, ` != ` |
| `client\_id=` | test_oauth_flows_sync.py:43 | TestOAuthBasicEndpoints.tes... | `    [OK] `, ` != ` |
| `def\\s\+` | audit_permissions.py:27 | analyze_route_file | `    [OK] `, ` != ` |
| `Discovered ` | websocket_validator.py:78 | WebSocketValidator._discove... | `    [OK] `, ` != ` |
| `Endpoint ` | test_auth_integration.py:55 | AuthServiceTester.test_auth... | `    [OK] `, ` != ` |
| `Health Check` | validate_staging_health.py:52 | StagingHealthValidator._che... | `    [OK] `, ` != ` |
| `Health endpoint returned ` | test_websocket_dev_mode.py:137 | WebSocketDevModeTest.test_h... | `    [OK] `, ` != ` |
| `Invalid health response: ` | test_websocket_dev_mode.py:134 | WebSocketDevModeTest.test_h... | `    [OK] `, ` != ` |
| `Invalid Request` | test_websocket_connection_issue.py:93 | TestWebSocketConnectionIssu... | `    [OK] `, ` != ` |
| `Liveness Check` | validate_staging_health.py:60 | StagingHealthValidator._che... | `    [OK] `, ` != ` |
| `Max retries exceeded` | validate_staging_health.py:76 | StagingHealthValidator._che... | `    [OK] `, ` != ` |
| `os\.environ` | test_websocket_validator_fix.py:203 | TestWebSocketValidatorFix.t... | `    [OK] `, ` != ` |
| `Readiness Check` | validate_staging_health.py:56 | StagingHealthValidator._che... | `    [OK] `, ` != ` |
| `redirect\_uri=` | test_oauth_flows_sync.py:44 | TestOAuthBasicEndpoints.tes... | `    [OK] `, ` != ` |
| `scope=openid%20email%20profile` | test_oauth_flows_sync.py:46 | TestOAuthBasicEndpoints.tes... | `    [OK] `, ` != ` |
| `state=` | test_oauth_flows_sync.py:45 | TestOAuthBasicEndpoints.tes... | `    [OK] `, ` != ` |
| `Test AuthEndpoints model` | test_oauth_models.py:131 | TestAuthEndpoints | `    [OK] `, ` != ` |
| `test\-user\-123` | test_single_database.py:66 | test_auth_routes_no_duplica... | `    [OK] `, ` != ` |
| `Testing health endpoints\.\.\.` | test_staging_startup.py:177 | StagingStartupTester.test_h... | `    [OK] `, ` != ` |
| `Validation error: ` | launcher.py:450 | DevLauncher._validate_webso... | `    [OK] `, ` != ` |
| `WebSocket endpoint configuration\.` | websocket_validator.py:38 | WebSocketEndpoint | `    [OK] `, ` != ` |
| `WebSocket validation failed: ` | launcher.py:449 | DevLauncher._validate_webso... | `    [OK] `, ` != ` |
| `websockets\.connect` | test_websocket_connection_issue.py:66 | TestWebSocketConnectionIssu... | `    [OK] `, ` != ` |
| `ws://` | websocket_validator.py:82 | WebSocketValidator._add_end... | `    [OK] `, ` != ` |
| `ws://localhost:8000/ws` | test_websocket_connection_issue.py:73 | TestWebSocketConnectionIssu... | `    [OK] `, ` != ` |
| `ws://localhost:8000/ws/secure` | test_websocket_validator_fix.py:72 | TestWebSocketValidatorFix.t... | `    [OK] `, ` != ` |
| `ℹ️` | websocket_validator.py:133 | WebSocketValidator._print_n... | `    [OK] `, ` != ` |

### Usage Examples

- **scripts\test_staging_startup.py:188** - `StagingStartupTester.test_health_endpoints`
- **scripts\validate_network_constants.py:154** - `validate_service_endpoints`
- **scripts\audit_permissions.py:32** - `analyze_route_file`

---

## Subcategory: file_path {subcategory-file-path}

**Count**: 451 literals

### 🟢 High (≥0.8) (451 literals)

| Literal | Files | Context | Related |
|---------|-------|---------|---------|
| `   2\. View: app/tests/examples/test\...` | demo_feature_flag_system.py:275 | main | `   cat SPEC/lea...`, `   cat app/tes... |
| `   cat app/tests/examples/test\_size\...` | demo_test_size_enforcement.py:200 | demo_cli_usage | `   2. View: app...`, `   cat SPEC/le... |
| `   cat SPEC/learnings/import\_managem...` | setup_import_hooks.py:166 | main | `   2. View: app...`, `   cat app/tes... |
| `   python scripts/compliance/test\_si...` | demo_test_size_enforcement.py:182 | demo_cli_usage | `   2. View: app...`, `   cat SPEC/le... |
| `  \[BAD\] test\_core\_2\.py` | prevent_numbered_files.py:154 | main | `   2. View: app...`, `   cat SPEC/le... |
| `  \[BAD\] test\_integration\_batch\_1...` | prevent_numbered_files.py:153 | main | `   2. View: app...`, `   cat SPEC/le... |
| `  \[BAD\] test\_utilities\_3\.py` | prevent_numbered_files.py:155 | main | `   2. View: app...`, `   cat SPEC/le... |
| `  \[OK\] test\_data\_validation\_fiel...` | prevent_numbered_files.py:150 | main | `   2. View: app...`, `   cat SPEC/le... |
| `  \[OK\] test\_message\_persistence\.py` | prevent_numbered_files.py:151 | main | `   2. View: app...`, `   cat SPEC/le... |
| `  \[OK\] test\_user\_authentication\.py` | prevent_numbered_files.py:149 | main | `   2. View: app...`, `   cat SPEC/le... |
| `  python enhanced\_schema\_sync\.py` | schema_sync.py:186 | print_usage | `   2. View: app...`, `   cat SPEC/le... |
| `  python scripts/fix\_netra\_backend\...` | fix_netra_backend_imports.py:222 | ImportFixer.generate_report | `   2. View: app...`, `   cat SPEC/le... |
| `  python scripts/scan\_string\_litera...` | fix_netra_domain.py:84 | main | `   2. View: app...`, `   cat SPEC/le... |
| ` from \.env` | local_secrets.py:62 | LocalSecretManager._build_f... | `   2. View: app...`, `   cat SPEC/le... |
| ` variables from \.env` | env_file_loader.py:36 | EnvFileLoader.load_env_file | `   2. View: app...`, `   cat SPEC/le... |
| `\*\*/\*\.json` | analyze_failures.py:64 | TestFailureAnalyzer.analyze... | `   2. View: app...`, `   cat SPEC/le... |
| `\*\*/\*\.py` | aggressive_syntax_fix.py:23 | get_files_with_errors | `   2. View: app...`, `   cat SPEC/le... |
| `\*\*/\*\_l3\.py` | standardize_l3_test_names.py:22 | find_l3_files | `   2. View: app...`, `   cat SPEC/le... |
| `\*\*/\*\_test\.py` | analyze_mocks.py:68 | MockAnalyzer.find_test_files | `   2. View: app...`, `   cat SPEC/le... |
| `\*\*/conftest\.py` | real_test_requirements_enforcer.py:100 | RealTestRequirementsEnforce... | `   2. View: app...`, `   cat SPEC/le... |
| `\*\*/test\*\.py` | generate_test_audit.py:84 | analyze_test_structure | `   2. View: app...`, `   cat SPEC/le... |
| `\*\*/test\_\*\.py` | analyze_mocks.py:67 | MockAnalyzer.find_test_files | `   2. View: app...`, `   cat SPEC/le... |
| `\*\*/tests/\*\*/\*\.py` | real_test_requirements_enforcer.py:99 | RealTestRequirementsEnforce... | `   2. View: app...`, `   cat SPEC/le... |
| `\*\.json` | agent_tracking_helper.py:62 | AgentTrackingHelper | `   2. View: app...`, `   cat SPEC/le... |
| `\*\.py` | audit_permissions.py:50 | main | `   2. View: app...`, `   cat SPEC/le... |
| `\*\.xml` | agent_tracking_helper.py:62 | AgentTrackingHelper | `   2. View: app...`, `   cat SPEC/le... |
| `\*\.yaml` | act_wrapper.py:54 | ACTWrapper.list_workflows | `   2. View: app...`, `   cat SPEC/le... |
| `\*\.yml` | act_wrapper.py:52 | ACTWrapper.list_workflows | `   2. View: app...`, `   cat SPEC/le... |
| `\*/content\_corpus\.json` | cleanup_generated_files.py:30 | module | `   2. View: app...`, `   cat SPEC/le... |
| `\*\_core\.py` | e2e_import_fixer_comprehensive.py:129 | E2EImportFixer.discover_all... | `   2. View: app...`, `   cat SPEC/le... |
| `\*\_critical\.py` | validate_agent_tests.py:70 | AgentTestValidator.find_cri... | `   2. View: app...`, `   cat SPEC/le... |
| `\*\_fixtures\.py` | e2e_import_fixer_comprehensive.py:127 | E2EImportFixer.discover_all... | `   2. View: app...`, `   cat SPEC/le... |
| `\*\_helpers\.py` | e2e_import_fixer_comprehensive.py:126 | E2EImportFixer.discover_all... | `   2. View: app...`, `   cat SPEC/le... |
| `\*\_managers\.py` | e2e_import_fixer_comprehensive.py:131 | E2EImportFixer.discover_all... | `   2. View: app...`, `   cat SPEC/le... |
| `\*\_services\.py` | e2e_import_fixer_comprehensive.py:130 | E2EImportFixer.discover_all... | `   2. View: app...`, `   cat SPEC/le... |
| `\*\_sub\_agent\.py` | status_agent_analyzer.py:82 | AgentSystemAnalyzer._check_... | `   2. View: app...`, `   cat SPEC/le... |
| `\*\_test\.py` | align_test_imports.py:73 | TestImportAligner.scan_test... | `   2. View: app...`, `   cat SPEC/le... |
| `\*\_utils\.py` | e2e_import_fixer_comprehensive.py:128 | E2EImportFixer.discover_all... | `   2. View: app...`, `   cat SPEC/le... |
| `\*E2E\*\.py` | check_e2e_imports.py:59 | E2EImportChecker.find_e2e_t... | `   2. View: app...`, `   cat SPEC/le... |
| `\*e2e\*\.py` | check_e2e_imports.py:59 | E2EImportChecker.find_e2e_t... | `   2. View: app...`, `   cat SPEC/le... |
| `\*test\.py` | generate_test_audit.py:46 | count_test_files | `   2. View: app...`, `   cat SPEC/le... |
| `\-\-cov\-report=json:reports/coverage...` | test_backend.py:264 | _get_coverage_options | `   2. View: app...`, `   cat SPEC/le... |
| `\-\-ignore\-glob=\*conftest\.py` | simple_perf_runner.py:46 | _build_pytest_command | `   2. View: app...`, `   cat SPEC/le... |
| `\-\-json\-report\-file=reports/tests/...` | test_backend.py:280 | _add_output_args | `   2. View: app...`, `   cat SPEC/le... |
| `\-\-json\-report\-file=test\_results\...` | test_example_message_flow.py:98 | ExampleMessageFlowTestRunne... | `   2. View: app...`, `   cat SPEC/le... |
| `\./\.env` | environment_validator.py:100 | EnvironmentValidator.valida... | `   2. View: app...`, `   cat SPEC/le... |
| `\.act\.env` | act_wrapper.py:25 | ACTWrapper.__init__ | `   2. View: app...`, `   cat SPEC/le... |
| `\.dev\_services\.json` | config_validator.py:247 | validate_service_config | `   2. View: app...`, `   cat SPEC/le... |
| `\.env` | main.py:25 | module | `   2. View: app...`, `   cat SPEC/le... |
| `\.github/workflows/boundary\-enforcem...` | boundary_enforcer_cli_handler.py:55 | HookInstaller.install_hooks | `   2. View: app...`, `   cat SPEC/le... |
| `\.json` | architecture_reporter.py:26 | ArchitectureReporter.export... | `   2. View: app...`, `   cat SPEC/le... |
| `\.pre\-commit\-config\.yaml` | boundary_enforcer_cli_handler.py:53 | HookInstaller.install_hooks | `   2. View: app...`, `   cat SPEC/le... |
| `\.py` | agent_tracking_helper.py:26 | AgentTrackingHelper | `   2. View: app...`, `   cat SPEC/le... |
| `\.xml` | metadata_header_generator.py:179 | MetadataHeaderGenerator.get... | `   2. View: app...`, `   cat SPEC/le... |
| `\.yaml` | test_env.py:107 | TestEnvironment.create_temp... | `   2. View: app...`, `   cat SPEC/le... |
| `\.yml` | act_wrapper.py:79 | ACTWrapper._resolve_workflo... | `   2. View: app...`, `   cat SPEC/le... |
| `/\*\*/\*\.py` | core.py:56 | ComplianceConfig.get_patterns | `   2. View: app...`, `   cat SPEC/le... |
| `/\*\*/\*\_test\.py` | mock_justification_checker.py:61 | MockJustificationChecker._g... | `   2. View: app...`, `   cat SPEC/le... |
| `/\*\*/test\_\*\.py` | mock_justification_checker.py:60 | MockJustificationChecker._g... | `   2. View: app...`, `   cat SPEC/le... |
| `/\_\_init\_\_\.py` | comprehensive_test_fixer.py:237 | TestFixer._module_to_file_path | `   2. View: app...`, `   cat SPEC/le... |
| `/openapi\.json` | main.py:138 | module | `   2. View: app...`, `   cat SPEC/le... |
| `/test/config\.json` | test_config_validator.py:52 | TestValidationContext.test_... | `   2. View: app...`, `   cat SPEC/le... |
| `/tests/\*\*/\*\.py` | mock_justification_checker.py:62 | MockJustificationChecker._g... | `   2. View: app...`, `   cat SPEC/le... |
| `\_\*\.json` | crash_reporter.py:199 | CrashReporter.list_reports | `   2. View: app...`, `   cat SPEC/le... |
| `\_\_init\_\_\.py` | audit_permissions.py:50 | main | `   2. View: app...`, `   cat SPEC/le... |
| `\_\_main\_\_\.py` | enhance_dev_launcher_boundaries.py:64 | enhance_launcher_args | `   2. View: app...`, `   cat SPEC/le... |
| `\_core\.py` | auto_fix_test_violations.py:419 | TestFileSplitter._split_int... | `   2. View: app...`, `   cat SPEC/le... |
| `\_e2e\.py` | test_size_validator.py:374 | TestSizeValidator._generate... | `   2. View: app...`, `   cat SPEC/le... |
| `\_extended\.py` | auto_fix_test_violations.py:426 | TestFileSplitter._split_int... | `   2. View: app...`, `   cat SPEC/le... |
| `\_feature1\.py` | test_size_validator.py:389 | TestSizeValidator._generate... | `   2. View: app...`, `   cat SPEC/le... |
| `\_feature2\.py` | test_size_validator.py:390 | TestSizeValidator._generate... | `   2. View: app...`, `   cat SPEC/le... |
| `\_fixtures\.py` | auto_fix_test_sizes.py:273 | TestFileSplitter.split_over... | `   2. View: app...`, `   cat SPEC/le... |
| `\_functions\.py` | test_refactor_helper.py:474 | TestRefactorHelper._strateg... | `   2. View: app...`, `   cat SPEC/le... |
| `\_helpers\.py` | auto_fix_test_sizes.py:275 | TestFileSplitter.split_over... | `   2. View: app...`, `   cat SPEC/le... |
| `\_integration\.py` | test_limits_checker.py:201 | TestLimitsChecker._suggest_... | `   2. View: app...`, `   cat SPEC/le... |
| `\_l3\.py` | standardize_l3_test_names.py:30 | get_new_filename | `   2. View: app...`, `   cat SPEC/le... |
| `\_schemas\.py` | fix_schema_imports.py:54 | SchemaImportFixer._move_sch... | `   2. View: app...`, `   cat SPEC/le... |
| `\_test\.py` | test_generator.py:89 | TestGenerator.find_test_file | `   2. View: app...`, `   cat SPEC/le... |
| `\_unit\.py` | test_limits_checker.py:200 | TestLimitsChecker._suggest_... | `   2. View: app...`, `   cat SPEC/le... |
| `\_utilities\.py` | test_refactor_helper.py:572 | TestRefactorHelper._strateg... | `   2. View: app...`, `   cat SPEC/le... |
| `\_utils\.py` | auto_fix_test_violations.py:383 | TestFileSplitter._split_int... | `   2. View: app...`, `   cat SPEC/le... |
| `agent\_fix\_tasks\.json` | create_agent_fix_tasks.py:47 | create_agent_tasks | `   2. View: app...`, `   cat SPEC/le... |
| `agent\_fixtures\.py` | fix_e2e_imports.py:322 | E2EImportFixer.create_missi... | `   2. View: app...`, `   cat SPEC/le... |
| `agent\_service\.py` | status_agent_analyzer.py:62 | AgentSystemAnalyzer._determ... | `   2. View: app...`, `   cat SPEC/le... |
| `agent\_validation\_metrics\.json` | validate_agent_tests.py:324 | AgentTestValidator.save_rep... | `   2. View: app...`, `   cat SPEC/le... |
| `agents/test\_example\_prompts\_e2e\_r...` | add_test_markers.py:207 | TestMarkerAdder.run | `   2. View: app...`, `   cat SPEC/le... |
| `ai\_factory\_patterns\.xml` | update_spec_timestamps.py:60 | module | `   2. View: app...`, `   cat SPEC/le... |
| `ai\_factory\_status\_report\.xml` | update_spec_timestamps.py:65 | module | `   2. View: app...`, `   cat SPEC/le... |
| `align\_test\_imports\.py` | import_management.py:50 | ImportManagementSystem.__in... | `   2. View: app...`, `   cat SPEC/le... |
| `alignment\_report\.json` | align_test_imports.py:420 | TestImportAligner.generate_... | `   2. View: app...`, `   cat SPEC/le... |
| `anti\_regression\.xml` | update_spec_timestamps.py:48 | module | `   2. View: app...`, `   cat SPEC/le... |
| `app/\*\*/\*\.py` | architecture_metrics.py:225 | ArchitectureMetrics._count_... | `   2. View: app...`, `   cat SPEC/le... |
| `app/agents/\*\.py` | function_complexity_analyzer.py:154 | FunctionComplexityAnalyzer.... | `   2. View: app...`, `   cat SPEC/le... |
| `app/agents/state\.py` | deduplicate_types.py:66 | TypeDeduplicator._setup_dup... | `   2. View: app...`, `   cat SPEC/le... |
| `app/core/\*\.py` | function_complexity_analyzer.py:155 | FunctionComplexityAnalyzer.... | `   2. View: app...`, `   cat SPEC/le... |
| `app/db/\*\.py` | function_complexity_analyzer.py:153 | FunctionComplexityAnalyzer.... | `   2. View: app...`, `   cat SPEC/le... |
| `app/middleware/tool\_permission\_midd...` | test_environment_detection.py:79 | test_middleware_environment... | `   2. View: app...`, `   cat SPEC/le... |
| `app/monitoring/alert\_manager\_core\.py` | fix_monitoring_violations.py:13 | fix_alert_manager_core | `   2. View: app...`, `   cat SPEC/le... |
| `app/monitoring/alert\_notifications\.py` | fix_monitoring_violations.py:75 | fix_alert_notifications | `   2. View: app...`, `   cat SPEC/le... |
| `app/routes/factory\_compliance\.py` | test_environment_detection.py:88 | test_middleware_environment... | `   2. View: app...`, `   cat SPEC/le... |
| `app/routes/websockets\.py` | code_review_analysis.py:114 | CodeReviewAnalysis._check_k... | `   2. View: app...`, `   cat SPEC/le... |
| `app/schemas\.py` | generate-types.py:7 | main | `   2. View: app...`, `   cat SPEC/le... |
| `app/schemas/ToolPermission\.py` | test_environment_detection.py:114 | test_schema_defaults | `   2. View: app...`, `   cat SPEC/le... |
| `app/schemas/WebSocket\.py` | deduplicate_types.py:68 | TypeDeduplicator._setup_dup... | `   2. View: app...`, `   cat SPEC/le... |
| `app/schemas/websocket\_types\.py` | deduplicate_types.py:67 | TypeDeduplicator._setup_dup... | `   2. View: app...`, `   cat SPEC/le... |
| `app/services/agent\_service\.py` | code_review_analysis.py:115 | CodeReviewAnalysis._check_k... | `   2. View: app...`, `   cat SPEC/le... |
| `app/services/factory\_status/factory\...` | test_environment_detection.py:97 | test_middleware_environment... | `   2. View: app...`, `   cat SPEC/le... |
| `app/services/security\_service\.py` | code_review_analysis.py:117 | CodeReviewAnalysis._check_k... | `   2. View: app...`, `   cat SPEC/le... |
| `app/tests/\*\*/\*\.py` | test_limits_checker.py:54 | TestLimitsChecker._find_tes... | `   2. View: app...`, `   cat SPEC/le... |
| `app/tests/\*\*/\*test\*\.py` | fix_import_issues.py:129 | main | `   2. View: app...`, `   cat SPEC/le... |
| `app/tests/agents/test\_supervisor\_co...` | split_large_files.py:203 | _initialize_splitter_and_files | `   2. View: app...`, `   cat SPEC/le... |
| `app/tests/core/test\_async\_utils\.py` | split_large_files.py:206 | _initialize_splitter_and_files | `   2. View: app...`, `   cat SPEC/le... |
| `app/tests/core/test\_config\_manager\.py` | fix_common_test_issues.py:32 | run_simple_unit_tests | `   2. View: app...`, `   cat SPEC/le... |
| `app/tests/core/test\_error\_handling\.py` | benchmark_optimization.py:77 | TestExecutionBenchmark._dis... | `   2. View: app...`, `   cat SPEC/le... |
| `app/tests/core/test\_missing\_tests\_...` | split_large_files.py:206 | _initialize_splitter_and_files | `   2. View: app...`, `   cat SPEC/le... |
| `app/tests/performance/test\_agent\_lo...` | simple_perf_runner.py:37 | _get_additional_test_files | `   2. View: app...`, `   cat SPEC/le... |
| `app/tests/performance/test\_benchmark...` | simple_perf_runner.py:26 | _get_performance_test_files | `   2. View: app...`, `   cat SPEC/le... |
| `app/tests/performance/test\_concurren...` | simple_perf_runner.py:28 | _get_performance_test_files | `   2. View: app...`, `   cat SPEC/le... |
| `app/tests/performance/test\_corpus\_g...` | simple_perf_runner.py:35 | _get_additional_test_files | `   2. View: app...`, `   cat SPEC/le... |
| `app/tests/performance/test\_database\...` | simple_perf_runner.py:27 | _get_performance_test_files | `   2. View: app...`, `   cat SPEC/le... |
| `app/tests/performance/test\_large\_sc...` | simple_perf_runner.py:36 | _get_additional_test_files | `   2. View: app...`, `   cat SPEC/le... |
| `app/tests/routes/test\_health\_route\.py` | benchmark_optimization.py:76 | TestExecutionBenchmark._dis... | `   2. View: app...`, `   cat SPEC/le... |
| `app/tests/services/agents/test\_tools...` | fix_common_test_issues.py:30 | run_simple_unit_tests | `   2. View: app...`, `   cat SPEC/le... |
| `app/tests/services/apex\_optimizer\_a...` | fix_common_test_issues.py:31 | run_simple_unit_tests | `   2. View: app...`, `   cat SPEC/le... |
| `app/tests/services/test\_quality\_gat...` | split_large_files.py:205 | _initialize_splitter_and_files | `   2. View: app...`, `   cat SPEC/le... |
| `app/tests/services/test\_security\_se...` | test_failure_scanner.py:42 | _get_test_paths_to_scan | `   2. View: app...`, `   cat SPEC/le... |
| `app/tests/services/test\_tool\_permis...` | split_large_files.py:204 | _initialize_splitter_and_files | `   2. View: app...`, `   cat SPEC/le... |
| `app/tests/test\_agent\_service\_criti...` | test_backend_optimized.py:98 | module | `   2. View: app...`, `   cat SPEC/le... |
| `app/tests/test\_api\_endpoints\_criti...` | test_backend_optimized.py:97 | module | `   2. View: app...`, `   cat SPEC/le... |
| `app/websocket/\*\.py` | function_complexity_analyzer.py:152 | FunctionComplexityAnalyzer.... | `   2. View: app...`, `   cat SPEC/le... |
| `app/ws\_manager\.py` | code_review_analysis.py:114 | CodeReviewAnalysis._check_k... | `   2. View: app...`, `   cat SPEC/le... |
| `architecture\.xml` | update_spec_timestamps.py:133 | is_legacy_spec | `   2. View: app...`, `   cat SPEC/le... |
| `auth\.json` | service_discovery.py:83 | ServiceDiscovery.write_auth... | `   2. View: app...`, `   cat SPEC/le... |
| `auth\_core/\*\.py` | coverage_config.py:189 | AuthServiceCoverageConfig._... | `   2. View: app...`, `   cat SPEC/le... |
| `auth\_core/core/\*\.py` | coverage_config.py:190 | AuthServiceCoverageConfig._... | `   2. View: app...`, `   cat SPEC/le... |
| `auth\_core/database/\*\.py` | coverage_config.py:193 | AuthServiceCoverageConfig._... | `   2. View: app...`, `   cat SPEC/le... |
| `auth\_core/models/\*\.py` | coverage_config.py:194 | AuthServiceCoverageConfig._... | `   2. View: app...`, `   cat SPEC/le... |
| `auth\_core/routes/\*\.py` | coverage_config.py:192 | AuthServiceCoverageConfig._... | `   2. View: app...`, `   cat SPEC/le... |
| `auth\_core/services/\*\.py` | coverage_config.py:191 | AuthServiceCoverageConfig._... | `   2. View: app...`, `   cat SPEC/le... |
| `auth\_service/tests/\*\*/\*test\*\.py` | fix_import_issues.py:131 | main | `   2. View: app...`, `   cat SPEC/le... |
| `auth\_service/tests/conftest\.py` | check_conftest_violations.py:14 | module | `   2. View: app...`, `   cat SPEC/le... |
| `autonomous\_test\_review\.json` | report_generator.py:32 | ReportGenerator.generate_re... | `   2. View: app...`, `   cat SPEC/le... |
| `backend\.json` | service_discovery.py:28 | ServiceDiscovery.read_backe... | `   2. View: app...`, `   cat SPEC/le... |
| `bad\_tests\.json` | generate_test_audit.py:127 | check_test_health | `   2. View: app...`, `   cat SPEC/le... |
| `base\.py` | type_checker.py:155 | TypeChecker._filter_backend... | `   2. View: app...`, `   cat SPEC/le... |
| `business\_value\_coverage\.json` | business_value_test_index.py:688 | BusinessValueTestIndexer.sa... | `   2. View: app...`, `   cat SPEC/le... |
| `business\_value\_test\_coverage\.xml` | business_value_test_index.py:115 | BusinessValueTestIndexer._l... | `   2. View: app...`, `   cat SPEC/le... |
| `check\_architecture\_compliance\.py` | clean_slate_executor.py:149 | CleanSlateExecutor.phase3_c... | `   2. View: app...`, `   cat SPEC/le... |
| `check\_netra\_backend\_imports\.py` | import_management.py:49 | ImportManagementSystem.__in... | `   2. View: app...`, `   cat SPEC/le... |
| `cleanup\_test\_processes\.py` | test_frontend.py:525 | handle_cleanup | `   2. View: app...`, `   cat SPEC/le... |
| `clickhouse\.xml` | update_spec_timestamps.py:53 | module | `   2. View: app...`, `   cat SPEC/le... |
| `clickhouse/test\_realistic\_clickhous...` | add_test_markers.py:210 | TestMarkerAdder.run | `   2. View: app...`, `   cat SPEC/le... |
| `code\_changes\.xml` | update_spec_timestamps.py:46 | module | `   2. View: app...`, `   cat SPEC/le... |
| `compliance\_reporting\.xml` | update_spec_timestamps.py:66 | module | `   2. View: app...`, `   cat SPEC/le... |
| `comprehensive\_fix\_report\.json` | comprehensive_e2e_import_fixer.py:359 | main | `   2. View: app...`, `   cat SPEC/le... |
| `config\.json` | manage_precommit.py:13 | module | `   2. View: app...`, `   cat SPEC/le... |
| `config\.py` | enhance_dev_launcher_boundaries.py:14 | enhance_launcher_config | `   2. View: app...`, `   cat SPEC/le... |
| `config/settings\.yaml` | clean_slate_executor.py:73 | CleanSlateExecutor.phase1_a... | `   2. View: app...`, `   cat SPEC/le... |
| `CONFIG\_FILE: \.github/workflow\-conf...` | validate_workflow_config.py:63 | check_workflow_references | `   2. View: app...`, `   cat SPEC/le... |
| `conftest\.py` | check_conftest_violations.py:35 | find_all_conftest_files | `   2. View: app...`, `   cat SPEC/le... |
| `context\.py` | project_test_validator.py:114 | ProjectTestValidator._is_te... | `   2. View: app...`, `   cat SPEC/le... |
| `conventions\.xml` | update_spec_timestamps.py:45 | module | `   2. View: app...`, `   cat SPEC/le... |
| `core\.xml` | update_spec_timestamps.py:130 | is_legacy_spec | `   2. View: app...`, `   cat SPEC/le... |
| `coverage\-\*\.xml` | merge_results.py:109 | handle_coverage_files | `   2. View: app...`, `   cat SPEC/le... |
| `coverage\-final\.json` | business_value_test_index.py:530 | BusinessValueTestIndexer.lo... | `   2. View: app...`, `   cat SPEC/le... |
| `coverage\.json` | coverage_config.py:43 | CoverageConfig | `   2. View: app...`, `   cat SPEC/le... |
| `coverage\.xml` | coverage_config.py:42 | CoverageConfig | `   2. View: app...`, `   cat SPEC/le... |
| `coverage\_analysis\.json` | coverage_reporter.py:152 | CoverageReporter.generate_c... | `   2. View: app...`, `   cat SPEC/le... |
| `coverage\_requirements\.xml` | update_spec_timestamps.py:52 | module | `   2. View: app...`, `   cat SPEC/le... |
| `create\_db\.py` | config_setup_core.py:72 | run_database_creation | `   2. View: app...`, `   cat SPEC/le... |
| `critical\_helpers\.py` | fix_e2e_imports.py:266 | E2EImportFixer.create_missi... | `   2. View: app...`, `   cat SPEC/le... |
| `cypress\-results\.json` | cleanup_generated_files.py:51 | module | `   2. View: app...`, `   cat SPEC/le... |
| `data\.xml` | update_spec_timestamps.py:129 | is_legacy_spec | `   2. View: app...`, `   cat SPEC/le... |
| `database\.py` | cache_manager.py:190 | CacheManager.has_migration_... | `   2. View: app...`, `   cat SPEC/le... |
| `database\.xml` | code_review_analysis.py:116 | CodeReviewAnalysis._check_k... | `   2. View: app...`, `   cat SPEC/le... |
| `dependency\_hashes\.json` | dependency_checker.py:63 | AsyncDependencyChecker._set... | `   2. View: app...`, `   cat SPEC/le... |
| `dev\_launcher\.py` | test_launcher_validation.py:27 | test_launcher_help | `   2. View: app...`, `   cat SPEC/le... |
| `doc\_overall\.xml` | update_spec_timestamps.py:123 | is_legacy_spec | `   2. View: app...`, `   cat SPEC/le... |
| `docker\-compose\.auth\.yml` | start_auth_service.py:20 | AuthServiceManager.__init__ | `   2. View: app...`, `   cat SPEC/le... |
| `docker\-compose\.staging\.yml` | build_staging.py:28 | StagingBuilder.__init__ | `   2. View: app...`, `   cat SPEC/le... |
| `e2e\-demo\.xml` | update_spec_timestamps.py:124 | is_legacy_spec | `   2. View: app...`, `   cat SPEC/le... |
| `e2e\_import\_report\.json` | check_e2e_imports.py:238 | E2EImportChecker.generate_r... | `   2. View: app...`, `   cat SPEC/le... |
| `emergency\_actions\.json` | emergency_boundary_actions.py:38 | EmergencyActionSystem.__init__ | `   2. View: app...`, `   cat SPEC/le... |
| `emergency\_report\.json` | emergency_boundary_actions.py:325 | EmergencyActionSystem._gene... | `   2. View: app...`, `   cat SPEC/le... |
| `environment\_validation\_report\.json` | environment_validator.py:522 | main | `   2. View: app...`, `   cat SPEC/le... |
| `failure\_scan\.json` | comprehensive_test_fixer.py:351 | BatchProcessor._get_failing... | `   2. View: app...`, `   cat SPEC/le... |
| `fix\_all\_import\_issues\.py` | import_management.py:46 | ImportManagementSystem.__in... | `   2. View: app...`, `   cat SPEC/le... |
| `fix\_comprehensive\_imports\.py` | import_management.py:47 | ImportManagementSystem.__in... | `   2. View: app...`, `   cat SPEC/le... |
| `fixtures\.py` | project_test_validator.py:112 | ProjectTestValidator._is_te... | `   2. View: app...`, `   cat SPEC/le... |
| `frontend\.json` | service_discovery.py:52 | ServiceDiscovery.read_front... | `   2. View: app...`, `   cat SPEC/le... |
| `frontend/package\.json` | dependency_scanner.py:113 | scan_node_dependencies | `   2. View: app...`, `   cat SPEC/le... |
| `frontend/tests/conftest\.py` | check_conftest_violations.py:17 | module | `   2. View: app...`, `   cat SPEC/le... |
| `frontend\_validation\.json` | validate_frontend_tests.py:249 | main | `   2. View: app...`, `   cat SPEC/le... |
| `function\_violations\_top1000\.json` | create_agent_fix_tasks.py:9 | create_agent_tasks | `   2. View: app...`, `   cat SPEC/le... |
| `gemini\-pr\-review\.yml` | validate_workflow_config.py:76 | check_workflow_references | `   2. View: app...`, `   cat SPEC/le... |
| `Generated by auto\_fix\_test\_violati...` | auto_fix_test_violations.py:519 | TestFileSplitter._create_sp... | `   2. View: app...`, `   cat SPEC/le... |
| `github\_actions\.xml` | update_spec_timestamps.py:59 | module | `   2. View: app...`, `   cat SPEC/le... |
| `growth\_control\.xml` | update_spec_timestamps.py:62 | module | `   2. View: app...`, `   cat SPEC/le... |
| `harness\.py` | project_test_validator.py:113 | ProjectTestValidator._is_te... | `   2. View: app...`, `   cat SPEC/le... |
| `hashes\.json` | cache_manager.py:61 | CacheManager._setup_cache_f... | `   2. View: app...`, `   cat SPEC/le... |
| `helpers\.py` | project_test_validator.py:112 | ProjectTestValidator._is_te... | `   2. View: app...`, `   cat SPEC/le... |
| `history\.xml` | update_spec_timestamps.py:121 | is_legacy_spec | `   2. View: app...`, `   cat SPEC/le... |
| `import\_issues\.json` | check_netra_backend_imports.py:342 | main | `   2. View: app...`, `   cat SPEC/le... |
| `import\_management\.py` | setup_import_hooks.py:64 | verify_tools | `   2. View: app...`, `   cat SPEC/le... |
| `import\_management\_report\.json` | import_management.py:220 | ImportManagementSystem.gene... | `   2. View: app...`, `   cat SPEC/le... |
| `import\_test\_results\.json` | fix_all_import_issues.py:42 | ComprehensiveImportFixer._l... | `   2. View: app...`, `   cat SPEC/le... |
| `independent\_services\.xml` | update_spec_timestamps.py:49 | module | `   2. View: app...`, `   cat SPEC/le... |
| `index\.xml` | split_learnings.py:116 | create_index | `   2. View: app...`, `   cat SPEC/le... |
| `install\_dev\_env\.py` | setup.py:37 | _validate_installer_exists | `   2. View: app...`, `   cat SPEC/le... |
| `instructions\.xml` | update_spec_timestamps.py:127 | is_legacy_spec | `   2. View: app...`, `   cat SPEC/le... |
| `jest\.config\.json` | validate_frontend_tests.py:92 | FrontendTestValidator._chec... | `   2. View: app...`, `   cat SPEC/le... |
| `jwt\_consistency\_validation\.json` | validate_jwt_consistency.py:213 | validate_jwt_secret_consist... | `   2. View: app...`, `   cat SPEC/le... |
| `launcher\.py` | enhance_dev_launcher_boundaries.py:115 | enhance_launcher_main | `   2. View: app...`, `   cat SPEC/le... |
| `learnings\.xml` | split_learnings.py:121 | main | `   2. View: app...`, `   cat SPEC/le... |
| `logs/emergency\_report\.json` | emergency_boundary_actions.py:196 | EmergencyActionSystem._crea... | `   2. View: app...`, `   cat SPEC/le... |
| `logs/urgent\_violations\.json` | emergency_boundary_actions.py:229 | EmergencyActionSystem._crea... | `   2. View: app...`, `   cat SPEC/le... |
| `logs/warning\_report\.json` | emergency_boundary_actions.py:262 | EmergencyActionSystem._crea... | `   2. View: app...`, `   cat SPEC/le... |
| `main\.py` | coverage_config.py:203 | AuthServiceCoverageConfig._... | `   2. View: app...`, `   cat SPEC/le... |
| `main\_db\_sync\.py` | test_single_database.py:20 | test_no_main_db_sync_module | `   2. View: app...`, `   cat SPEC/le... |
| `master\_wip\_index\.xml` | update_spec_timestamps.py:64 | module | `   2. View: app...`, `   cat SPEC/le... |
| `metadata\_archiver\.py` | archiver_generator.py:17 | ArchiverGenerator.__init__ | `   2. View: app...`, `   cat SPEC/le... |
| `metadata\_config\.json` | config_manager.py:22 | ConfigurationManager._get_c... | `   2. View: app...`, `   cat SPEC/le... |
| `metadata\_log\.json` | metadata_header_generator.py:328 | MetadataHeaderGenerator.sav... | `   2. View: app...`, `   cat SPEC/le... |
| `metadata\_validator\.py` | status_manager.py:67 | StatusManager._check_valida... | `   2. View: app...`, `   cat SPEC/le... |
| `model\_setup\_helpers\.py` | fix_e2e_imports.py:235 | E2EImportFixer.create_missi... | `   2. View: app...`, `   cat SPEC/le... |
| `models\.py` | type_checker.py:154 | TypeChecker._filter_backend... | `   2. View: app...`, `   cat SPEC/le... |
| `netra\_backend/\*\*/\*\.py` | unified_import_manager.py:349 | UnifiedImportManager._check... | `   2. View: app...`, `   cat SPEC/le... |
| `netra\_backend/app/agents/supervisor\...` | fix_comprehensive_imports.py:277 | ComprehensiveImportFixerV2.... | `   2. View: app...`, `   cat SPEC/le... |
| `netra\_backend/app/core/configuration...` | fast_import_checker.py:64 | fix_known_import_issues | `   2. View: app...`, `   cat SPEC/le... |
| `netra\_backend/app/dependencies\.py` | fast_import_checker.py:201 | fix_known_import_issues | `   2. View: app...`, `   cat SPEC/le... |
| `netra\_backend/app/services/apex\_opt...` | fast_import_checker.py:110 | fix_known_import_issues | `   2. View: app...`, `   cat SPEC/le... |
| `netra\_backend/app/services/llm/cost\...` | fast_import_checker.py:151 | fix_known_import_issues | `   2. View: app...`, `   cat SPEC/le... |
| `netra\_backend/tests/agents/test\_dat...` | fix_comprehensive_imports.py:278 | ComprehensiveImportFixerV2.... | `   2. View: app...`, `   cat SPEC/le... |
| `netra\_backend/tests/conftest\.py` | check_conftest_violations.py:15 | module | `   2. View: app...`, `   cat SPEC/le... |
| `netra\_backend/tests/integration/crit...` | fix_netra_domain.py:51 | main | `   2. View: app...`, `   cat SPEC/le... |
| `netra\_backend/tests/integration/crit...` | fix_netra_domain.py:48 | main | `   2. View: app...`, `   cat SPEC/le... |
| `netra\_backend/tests/integration/crit...` | fix_netra_domain.py:49 | main | `   2. View: app...`, `   cat SPEC/le... |
| `netra\_backend/tests/integration/crit...` | fix_netra_domain.py:50 | main | `   2. View: app...`, `   cat SPEC/le... |
| `netra\_backend/tests/integration/test...` | fix_netra_domain.py:53 | main | `   2. View: app...`, `   cat SPEC/le... |
| `netra\_backend/tests/integration/test...` | fix_netra_domain.py:55 | main | `   2. View: app...`, `   cat SPEC/le... |
| `netra\_backend/tests/integration/test...` | fix_netra_domain.py:52 | main | `   2. View: app...`, `   cat SPEC/le... |
| `netra\_backend/tests/integration/test...` | fix_netra_domain.py:54 | main | `   2. View: app...`, `   cat SPEC/le... |
| `netra\_backend/tests/routes/test\_\*a...` | test_backend.py:34 | module | `   2. View: app...`, `   cat SPEC/le... |
| `netra\_backend/tests/routes/test\_hea...` | test_backend.py:38 | module | `   2. View: app...`, `   cat SPEC/le... |
| `netra\_backend/tests/routes/test\_web...` | test_backend.py:33 | module | `   2. View: app...`, `   cat SPEC/le... |
| `netra\_backend/tests/test\_agent\_ser...` | test_backend.py:36 | module | `   2. View: app...`, `   cat SPEC/le... |
| `netra\_backend/tests/test\_api\_endpo...` | test_backend.py:36 | module | `   2. View: app...`, `   cat SPEC/le... |
| `netra\_backend/tests/test\_auth\*\.py` | test_backend.py:34 | module | `   2. View: app...`, `   cat SPEC/le... |
| `netra\_backend/tests/test\_database\*...` | test_backend.py:35 | module | `   2. View: app...`, `   cat SPEC/le... |
| `netra\_backend/tests/test\_websocket\.py` | test_backend.py:33 | module | `   2. View: app...`, `   cat SPEC/le... |
| `no\_test\_stubs\.xml` | update_spec_timestamps.py:47 | module | `   2. View: app...`, `   cat SPEC/le... |
| `oauth\.py` | status_integration_analyzer.py:147 | IntegrationAnalyzer._check_... | `   2. View: app...`, `   cat SPEC/le... |
| `openapi\.json` | generate_openAPI_schema.py:36 | generate_openapi_schema | `   2. View: app...`, `   cat SPEC/le... |
| `orchestrator\.yml` | validate_workflow_config.py:80 | check_workflow_references | `   2. View: app...`, `   cat SPEC/le... |
| `organized\_violations\.json` | extract_violations.py:77 | module | `   2. View: app...`, `   cat SPEC/le... |
| `package\-lock\.json` | agent_tracking_helper.py:53 | AgentTrackingHelper | `   2. View: app...`, `   cat SPEC/le... |
| `package\.json` | agent_tracking_helper.py:53 | AgentTrackingHelper | `   2. View: app...`, `   cat SPEC/le... |
| `performance\.json` | cache_manager.py:64 | CacheManager._setup_cache_f... | `   2. View: app...`, `   cat SPEC/le... |
| `postgres\.xml` | update_spec_timestamps.py:54 | module | `   2. View: app...`, `   cat SPEC/le... |
| `PRODUCTION\_SECRETS\_ISOLATION\.xml` | update_spec_timestamps.py:58 | module | `   2. View: app...`, `   cat SPEC/le... |
| `python\_files=test\_\*\.py` | simple_perf_runner.py:45 | _build_pytest_command | `   2. View: app...`, `   cat SPEC/le... |
| `registry\.py` | deduplicate_types.py:140 | TypeDeduplicator.find_pytho... | `   2. View: app...`, `   cat SPEC/le... |
| `reports/cleanup\_log\.json` | cleanup_generated_files.py:291 | main | `   2. View: app...`, `   cat SPEC/le... |
| `reports/coverage/coverage\.json` | analyze_coverage.py:4 | module | `   2. View: app...`, `   cat SPEC/le... |
| `review\.xml` | update_spec_timestamps.py:122 | is_legacy_spec | `   2. View: app...`, `   cat SPEC/le... |
| `Run: python scripts/fix\_frontend\_te...` | validate_frontend_tests.py:213 | FrontendTestValidator._get_... | `   2. View: app...`, `   cat SPEC/le... |
| `run\_migrations\.py` | config_setup_core.py:82 | run_database_migrations | `   2. View: app...`, `   cat SPEC/le... |
| `run\_server\.py` | dev_launcher_service.py:71 | ServiceManager._get_server_... | `   2. View: app...`, `   cat SPEC/le... |
| `run\_server\_enhanced\.py` | dev_launcher_service.py:70 | ServiceManager._get_server_... | `   2. View: app...`, `   cat SPEC/le... |
| `runners\.py` | project_test_validator.py:114 | ProjectTestValidator._is_te... | `   2. View: app...`, `   cat SPEC/le... |
| `schema\_import\_violations\.json` | check_schema_imports.py:430 | main | `   2. View: app...`, `   cat SPEC/le... |
| `schemas\.py` | fix_schema_imports.py:33 | SchemaImportFixer.move_sche... | `   2. View: app...`, `   cat SPEC/le... |
| `scripts/\*\*/\*\.py` | architecture_metrics.py:225 | ArchitectureMetrics._count_... | `   2. View: app...`, `   cat SPEC/le... |
| `scripts/auto\_split\_files\.py` | emergency_boundary_actions.py:355 | EmergencyActionSystem._exec... | `   2. View: app...`, `   cat SPEC/le... |
| `scripts/boundary\_enforcer\.py` | emergency_boundary_actions.py:77 | EmergencyActionSystem._get_... | `   2. View: app...`, `   cat SPEC/le... |
| `scripts/business\_value\_test\_index\.py` | generate_wip_report.py:160 | WIPReportGenerator.generate... | `   2. View: app...`, `   cat SPEC/le... |
| `scripts/check\_architecture\_complian...` | deploy_to_gcp.py:161 | GCPDeployer.run_pre_deploym... | `   2. View: app...`, `   cat SPEC/le... |
| `scripts/fix\_e2e\_imports\.py` | fix_netra_domain.py:56 | main | `   2. View: app...`, `   cat SPEC/le... |
| `scripts/scan\_string\_literals\.py` | deploy_to_gcp.py:166 | GCPDeployer.run_pre_deploym... | `   2. View: app...`, `   cat SPEC/le... |
| `scripts/verify\_workflow\_status\.py` | test_verify_workflow.py:32 | test_help_command | `   2. View: app...`, `   cat SPEC/le... |
| `scripts/workflow\_validator\.py` | setup_act.py:137 | run_validation | `   2. View: app...`, `   cat SPEC/le... |
| `secrets\.json` | cache_manager.py:63 | CacheManager._setup_cache_f... | `   2. View: app...`, `   cat SPEC/le... |
| `security\.xml` | code_review_analysis.py:117 | CodeReviewAnalysis._check_k... | `   2. View: app...`, `   cat SPEC/le... |
| `selfchecks\.xml` | update_spec_timestamps.py:126 | is_legacy_spec | `   2. View: app...`, `   cat SPEC/le... |
| `services\.json` | cache_manager.py:62 | CacheManager._setup_cache_f... | `   2. View: app...`, `   cat SPEC/le... |
| `services\.xml` | update_spec_timestamps.py:131 | is_legacy_spec | `   2. View: app...`, `   cat SPEC/le... |
| `services/test\_synthetic\_data\_servi...` | add_test_markers.py:209 | TestMarkerAdder.run | `   2. View: app...`, `   cat SPEC/le... |
| `settings\.json` | enhance_dev_launcher_boundaries.py:263 | _create_vscode_settings | `   2. View: app...`, `   cat SPEC/le... |
| `setup\.py` | analyze_failures.py:145 | TestFailureAnalyzer._determ... | `   2. View: app...`, `   cat SPEC/le... |
| `shared/schemas\.json` | generate-json-schema.py:24 | main | `   2. View: app...`, `   cat SPEC/le... |
| `SPEC/\*\.xml` | fix_import_issues.py:132 | main | `   2. View: app...`, `   cat SPEC/le... |
| `SPEC/generated/string\_literals\.json` | query_string_literals.py:17 | StringLiteralQuery.__init__ | `   2. View: app...`, `   cat SPEC/le... |
| `staging\-environment\.yml` | act_wrapper.py:150 | StagingDeployer.__init__ | `   2. View: app...`, `   cat SPEC/le... |
| `staging\_base\.py` | fix_e2e_imports.py:290 | E2EImportFixer.create_missi... | `   2. View: app...`, `   cat SPEC/le... |
| `startup\_history\.json` | startup_profiler.py:236 | StartupProfiler._get_histor... | `   2. View: app...`, `   cat SPEC/le... |
| `state\.json` | cache_manager.py:60 | CacheManager._setup_cache_f... | `   2. View: app...`, `   cat SPEC/le... |
| `Status\.xml` | update_spec_timestamps.py:120 | is_legacy_spec | `   2. View: app...`, `   cat SPEC/le... |
| `string\_literals\_index\.xml` | update_spec_timestamps.py:50 | module | `   2. View: app...`, `   cat SPEC/le... |
| `subagents\.xml` | code_review_analysis.py:115 | CodeReviewAnalysis._check_k... | `   2. View: app...`, `   cat SPEC/le... |
| `supervisor\.py` | status_agent_analyzer.py:50 | AgentSystemAnalyzer._check_... | `   2. View: app...`, `   cat SPEC/le... |
| `supervisor\_consolidated\.py` | status_agent_analyzer.py:51 | AgentSystemAnalyzer._check_... | `   2. View: app...`, `   cat SPEC/le... |
| `swimlane\.xml` | update_spec_timestamps.py:125 | is_legacy_spec | `   2. View: app...`, `   cat SPEC/le... |
| `system\_boundaries\.xml` | update_spec_timestamps.py:61 | module | `   2. View: app...`, `   cat SPEC/le... |
| `tasks\.json` | enhance_dev_launcher_boundaries.py:269 | _create_vscode_tasks | `   2. View: app...`, `   cat SPEC/le... |
| `terraform\-lock\-cleanup\.yml` | validate_workflow_config.py:76 | check_workflow_references | `   2. View: app...`, `   cat SPEC/le... |
| `test\*\.py` | generate_test_audit.py:41 | count_test_files | `   2. View: app...`, `   cat SPEC/le... |
| `test\-act\-simple\.yml` | test_workflows_with_act.py:284 | WorkflowTester.run_tests | `   2. View: app...`, `   cat SPEC/le... |
| `test\-results\-\*\.json` | merge_results.py:24 | find_result_files | `   2. View: app...`, `   cat SPEC/le... |
| `test\_\*\.py` | align_test_imports.py:72 | TestImportAligner.scan_test... | `   2. View: app...`, `   cat SPEC/le... |
| `test\_agent\_registry\_initialization...` | generate_startup_integration_tests.py:114 | module | `   2. View: app...`, `   cat SPEC/le... |
| `test\_categories\.py` | add_test_markers.py:206 | TestMarkerAdder.run | `   2. View: app...`, `   cat SPEC/le... |
| `test\_categorization\.json` | add_test_markers.py:22 | TestMarkerAdder.__init__ | `   2. View: app...`, `   cat SPEC/le... |
| `test\_clickhouse\_schema\_validation\...` | generate_startup_integration_tests.py:66 | module | `   2. View: app...`, `   cat SPEC/le... |
| `test\_cloud\_sql\_proxy\.py` | verify_staging_tests.py:27 | verify_test_files | `   2. View: app...`, `   cat SPEC/le... |
| `test\_compliance\.json` | extract_violations.py:10 | extract_violations | `   2. View: app...`, `   cat SPEC/le... |
| `test\_config\.py` | align_test_imports.py:220 | TestImportAligner.fix_test_... | `   2. View: app...`, `   cat SPEC/le... |
| `test\_configuration\_validation\_envi...` | generate_startup_integration_tests.py:146 | module | `   2. View: app...`, `   cat SPEC/le... |
| `test\_cors\_configuration\.py` | verify_staging_tests.py:35 | verify_test_files | `   2. View: app...`, `   cat SPEC/le... |
| `test\_database\_connection\_pool\_ini...` | generate_startup_integration_tests.py:18 | module | `   2. View: app...`, `   cat SPEC/le... |
| `test\_database\_migrations\.py` | verify_staging_tests.py:32 | verify_test_files | `   2. View: app...`, `   cat SPEC/le... |
| `test\_deployment\_rollback\.py` | verify_staging_tests.py:37 | verify_test_files | `   2. View: app...`, `   cat SPEC/le... |
| `test\_discovery\.py` | align_test_imports.py:319 | TestImportAligner.fix_test_... | `   2. View: app...`, `   cat SPEC/le... |
| `test\_environment\_precedence\.py` | verify_staging_tests.py:29 | verify_test_files | `   2. View: app...`, `   cat SPEC/le... |
| `test\_environment\_secrets\_loading\_...` | generate_startup_integration_tests.py:34 | module | `   2. View: app...`, `   cat SPEC/le... |
| `test\_error\_recovery\_startup\_resil...` | generate_startup_integration_tests.py:194 | module | `   2. View: app...`, `   cat SPEC/le... |
| `test\_feature\_flags\.json` | demo_feature_flag_system.py:239 | demonstrate_business_value | `   2. View: app...`, `   cat SPEC/le... |
| `test\_fixtures\.py` | fix_e2e_imports.py:345 | E2EImportFixer.create_missi... | `   2. View: app...`, `   cat SPEC/le... |
| `test\_framework/\*\*/\*\.py` | boundary_enforcer_core_types.py:63 | get_file_patterns | `   2. View: app...`, `   cat SPEC/le... |
| `test\_framework/comprehensive\_report...` | function_complexity_analyzer.py:150 | FunctionComplexityAnalyzer.... | `   2. View: app...`, `   cat SPEC/le... |
| `test\_framework/runner\.py` | function_complexity_analyzer.py:149 | FunctionComplexityAnalyzer.... | `   2. View: app...`, `   cat SPEC/le... |
| `test\_framework/test\_discovery\.py` | function_complexity_analyzer.py:148 | FunctionComplexityAnalyzer.... | `   2. View: app...`, `   cat SPEC/le... |
| `test\_health\_checks\.py` | verify_staging_tests.py:33 | verify_test_files | `   2. View: app...`, `   cat SPEC/le... |
| `test\_history\.json` | team_updates_test_analyzer.py:18 | TestReportAnalyzer.__init__ | `   2. View: app...`, `   cat SPEC/le... |
| `test\_llm\_api\_connectivity\_validat...` | generate_startup_integration_tests.py:50 | module | `   2. View: app...`, `   cat SPEC/le... |
| `test\_llm\_integration\.py` | verify_staging_tests.py:36 | verify_test_files | `   2. View: app...`, `   cat SPEC/le... |
| `test\_metric\_collection\_initializat...` | generate_startup_integration_tests.py:162 | module | `   2. View: app...`, `   cat SPEC/le... |
| `test\_multi\_service\_secrets\.py` | verify_staging_tests.py:30 | verify_test_files | `   2. View: app...`, `   cat SPEC/le... |
| `test\_observability\_pipeline\.py` | verify_staging_tests.py:38 | verify_test_files | `   2. View: app...`, `   cat SPEC/le... |
| `test\_overlap\_report\.json` | analyze_test_overlap.py:498 | TestOverlapAnalyzer._save_r... | `   2. View: app...`, `   cat SPEC/le... |
| `test\_realistic\_data\_integration\.py` | add_test_markers.py:208 | TestMarkerAdder.run | `   2. View: app...`, `   cat SPEC/le... |
| `test\_redis\_lifecycle\.py` | verify_staging_tests.py:31 | verify_test_files | `   2. View: app...`, `   cat SPEC/le... |
| `test\_redis\_session\_store\_initiali...` | generate_startup_integration_tests.py:82 | module | `   2. View: app...`, `   cat SPEC/le... |
| `test\_reporting\.xml` | update_spec_timestamps.py:67 | module | `   2. View: app...`, `   cat SPEC/le... |
| `test\_reports/real\_test\_violations\...` | real_test_requirements_enforcer.py:594 | main | `   2. View: app...`, `   cat SPEC/le... |
| `test\_resource\_limits\.py` | verify_staging_tests.py:39 | verify_test_files | `   2. View: app...`, `   cat SPEC/le... |
| `test\_results\.json` | business_value_test_index.py:542 | BusinessValueTestIndexer.lo... | `   2. View: app...`, `   cat SPEC/le... |
| `test\_runner\.py` | build_staging.py:209 | StagingBuilder.run_tests | `   2. View: app...`, `   cat SPEC/le... |
| `test\_runner\_guide\.xml` | update_spec_timestamps.py:63 | module | `   2. View: app...`, `   cat SPEC/le... |
| `test\_secret\_manager\_integration\.py` | verify_staging_tests.py:25 | verify_test_files | `   2. View: app...`, `   cat SPEC/le... |
| `test\_size\_compliance\_examples\.py` | demo_test_size_enforcement.py:31 | demo_test_size_validator | `   2. View: app...`, `   cat SPEC/le... |
| `test\_size\_violations\.json` | auto_fix_test_sizes.py:601 | TestSizeFixer.__init__ | `   2. View: app...`, `   cat SPEC/le... |
| `test\_staging\_production\_parity\_va...` | generate_startup_integration_tests.py:210 | module | `   2. View: app...`, `   cat SPEC/le... |
| `test\_staging\_startup\.py` | verify_staging_tests.py:28 | verify_test_files | `   2. View: app...`, `   cat SPEC/le... |
| `test\_startup\_health\_check\_compreh...` | generate_startup_integration_tests.py:98 | module | `   2. View: app...`, `   cat SPEC/le... |
| `test\_startup\_performance\_timing\_v...` | generate_startup_integration_tests.py:178 | module | `   2. View: app...`, `   cat SPEC/le... |
| `test\_terraform\_deployment\_consiste...` | verify_staging_tests.py:26 | verify_test_files | `   2. View: app...`, `   cat SPEC/le... |
| `test\_update\_spec\.xml` | test_reviewer.py:24 | AutonomousTestReviewer.__in... | `   2. View: app...`, `   cat SPEC/le... |
| `test\_utils\.py` | remove_duplicate_test_setup.py:55 | main | `   2. View: app...`, `   cat SPEC/le... |
| `test\_websocket\_infrastructure\_star...` | generate_startup_integration_tests.py:130 | module | `   2. View: app...`, `   cat SPEC/le... |
| `test\_websocket\_load\_balancer\.py` | verify_staging_tests.py:34 | verify_test_files | `   2. View: app...`, `   cat SPEC/le... |
| `testing\.xml` | update_spec_timestamps.py:51 | module | `   2. View: app...`, `   cat SPEC/le... |
| `tests/\*\*/\*\.py` | analyze_mocks.py:65 | MockAnalyzer.find_test_files | `   2. View: app...`, `   cat SPEC/le... |
| `tests/\*\*/\*\_test\.py` | test_limits_checker.py:59 | TestLimitsChecker._find_tes... | `   2. View: app...`, `   cat SPEC/le... |
| `tests/\*\*/\*test\*\.py` | fix_import_issues.py:130 | main | `   2. View: app...`, `   cat SPEC/le... |
| `tests/conftest\.py` | check_conftest_violations.py:16 | module | `   2. View: app...`, `   cat SPEC/le... |
| `tests/e2e/agent\_isolation/test\_file...` | fix_simple_import_errors.py:84 | main | `   2. View: app...`, `   cat SPEC/le... |
| `tests/e2e/agent\_isolation/test\_memo...` | fix_simple_import_errors.py:85 | main | `   2. View: app...`, `   cat SPEC/le... |
| `tests/e2e/fixtures/\_\_init\_\_\.py` | fix_simple_import_errors.py:86 | main | `   2. View: app...`, `   cat SPEC/le... |
| `tests/e2e/integration/test\_agent\_or...` | fix_all_e2e_imports.py:123 | main | `   2. View: app...`, `   cat SPEC/le... |
| `tests/e2e/integration/test\_auth\_jwt...` | fix_all_e2e_imports.py:124 | main | `   2. View: app...`, `   cat SPEC/le... |
| `tests/e2e/integration/test\_auth\_jwt...` | fix_all_e2e_imports.py:125 | main | `   2. View: app...`, `   cat SPEC/le... |
| `tests/e2e/resource\_isolation/infrast...` | fix_simple_import_errors.py:89 | main | `   2. View: app...`, `   cat SPEC/le... |
| `tests/e2e/resource\_isolation/suite/t...` | fix_simple_import_errors.py:90 | main | `   2. View: app...`, `   cat SPEC/le... |
| `tests/e2e/resource\_isolation/test\_i...` | fix_import_indents.py:76 | main | `   2. View: app...`, `   cat SPEC/le... |
| `tests/e2e/resource\_isolation/test\_s...` | fix_simple_import_errors.py:88 | main | `   2. View: app...`, `   cat SPEC/le... |
| `tests/e2e/test\_data\_factory\.py` | fix_remaining_e2e_imports.py:118 | create_missing_helpers | `   2. View: app...`, `   cat SPEC/le... |
| `tests/e2e/test\_helpers\.py` | fix_remaining_e2e_imports.py:97 | create_missing_helpers | `   2. View: app...`, `   cat SPEC/le... |
| `tests/e2e/test\_helpers/\_\_init\_\_\.py` | fix_simple_import_errors.py:92 | main | `   2. View: app...`, `   cat SPEC/le... |
| `tests/e2e/test\_helpers/throughput\_h...` | fix_import_indents.py:67 | main | `   2. View: app...`, `   cat SPEC/le... |
| `tests/e2e/websocket\_resilience/test\...` | fix_simple_import_errors.py:93 | main | `   2. View: app...`, `   cat SPEC/le... |
| `tests/e2e/websocket\_resilience/test\...` | fix_import_indents.py:71 | main | `   2. View: app...`, `   cat SPEC/le... |
| `tests/e2e/websocket\_resilience/test\...` | fix_import_indents.py:62 | main | `   2. View: app...`, `   cat SPEC/le... |
| `tests/e2e/websocket\_resilience/test\...` | fix_import_indents.py:57 | main | `   2. View: app...`, `   cat SPEC/le... |
| `tests/e2e/websocket\_resilience/test\...` | fix_import_indents.py:58 | main | `   2. View: app...`, `   cat SPEC/le... |
| `tests/e2e/websocket\_resilience/test\...` | fix_import_indents.py:65 | main | `   2. View: app...`, `   cat SPEC/le... |
| `tests/factories\.py` | fix_remaining_e2e_imports.py:157 | create_missing_helpers | `   2. View: app...`, `   cat SPEC/le... |
| `tests/test\_example\_message\_flow\.py` | test_example_message_flow.py:49 | ExampleMessageFlowTestRunne... | `   2. View: app...`, `   cat SPEC/le... |
| `tests/test\_example\_message\_integra...` | test_example_message_flow.py:54 | ExampleMessageFlowTestRunne... | `   2. View: app...`, `   cat SPEC/le... |
| `tests/test\_super\_e2e\.py` | startup_test_executor.py:199 | E2ETestExecutor._setup_and_... | `   2. View: app...`, `   cat SPEC/le... |
| `tests/test\_system\_startup\.py` | startup_test_executor.py:43 | BackendTestExecutor.run_tests | `   2. View: app...`, `   cat SPEC/le... |
| `tests/unified/e2e/concurrent\_user\_s...` | fix_remaining_imports.py:67 | main | `   2. View: app...`, `   cat SPEC/le... |
| `tests/unified/e2e/file\_upload\_pipel...` | fix_remaining_imports.py:50 | main | `   2. View: app...`, `   cat SPEC/le... |
| `tests/unified/e2e/helpers/error\_prop...` | fix_remaining_imports.py:72 | main | `   2. View: app...`, `   cat SPEC/le... |
| `tests/unified/e2e/helpers/service\_in...` | fix_remaining_imports.py:73 | main | `   2. View: app...`, `   cat SPEC/le... |
| `tests/unified/e2e/helpers/service\_in...` | fix_remaining_imports.py:71 | main | `   2. View: app...`, `   cat SPEC/le... |
| `tests/unified/e2e/onboarding\_flow\_e...` | fix_remaining_imports.py:68 | main | `   2. View: app...`, `   cat SPEC/le... |
| `tests/unified/e2e/session\_persistenc...` | fix_remaining_imports.py:69 | main | `   2. View: app...`, `   cat SPEC/le... |
| `tests/unified/e2e/test\_agent\_billin...` | fix_remaining_imports.py:61 | main | `   2. View: app...`, `   cat SPEC/le... |
| `tests/unified/e2e/test\_agent\_collab...` | fix_import_indents.py:60 | main | `   2. View: app...`, `   cat SPEC/le... |
| `tests/unified/e2e/test\_agent\_failur...` | fix_import_indents.py:73 | main | `   2. View: app...`, `   cat SPEC/le... |
| `tests/unified/e2e/test\_agent\_orches...` | fix_remaining_imports.py:58 | main | `   2. View: app...`, `   cat SPEC/le... |
| `tests/unified/e2e/test\_ai\_supply\_c...` | fix_remaining_imports.py:64 | main | `   2. View: app...`, `   cat SPEC/le... |
| `tests/unified/e2e/test\_auth\_token\_...` | fix_import_indents.py:77 | main | `   2. View: app...`, `   cat SPEC/le... |
| `tests/unified/e2e/test\_auth\_websock...` | fix_remaining_imports.py:48 | main | `   2. View: app...`, `   cat SPEC/le... |
| `tests/unified/e2e/test\_auth\_websock...` | fix_remaining_imports.py:56 | main | `   2. View: app...`, `   cat SPEC/le... |
| `tests/unified/e2e/test\_auth\_websock...` | fix_import_indents.py:74 | main | `   2. View: app...`, `   cat SPEC/le... |
| `tests/unified/e2e/test\_cost\_trackin...` | fix_remaining_imports.py:54 | main | `   2. View: app...`, `   cat SPEC/le... |
| `tests/unified/e2e/test\_cross\_servic...` | fix_import_indents.py:72 | main | `   2. View: app...`, `   cat SPEC/le... |
| `tests/unified/e2e/test\_data\_crud\_u...` | fix_import_indents.py:55 | main | `   2. View: app...`, `   cat SPEC/le... |
| `tests/unified/e2e/test\_database\_con...` | fix_remaining_imports.py:47 | main | `   2. View: app...`, `   cat SPEC/le... |
| `tests/unified/e2e/test\_disaster\_rec...` | fix_import_indents.py:75 | main | `   2. View: app...`, `   cat SPEC/le... |
| `tests/unified/e2e/test\_error\_cascad...` | fix_remaining_imports.py:53 | main | `   2. View: app...`, `   cat SPEC/le... |
| `tests/unified/e2e/test\_export\_pipel...` | fix_remaining_imports.py:49 | main | `   2. View: app...`, `   cat SPEC/le... |
| `tests/unified/e2e/test\_health\_monit...` | fix_import_indents.py:69 | main | `   2. View: app...`, `   cat SPEC/le... |
| `tests/unified/e2e/test\_memory\_leak\...` | fix_import_indents.py:56 | main | `   2. View: app...`, `   cat SPEC/le... |
| `tests/unified/e2e/test\_quota\_manage...` | fix_remaining_imports.py:45 | main | `   2. View: app...`, `   cat SPEC/le... |
| `tests/unified/e2e/test\_real\_rate\_l...` | fix_remaining_imports.py:57 | main | `   2. View: app...`, `   cat SPEC/le... |
| `tests/unified/e2e/test\_service\_fail...` | fix_remaining_imports.py:46 | main | `   2. View: app...`, `   cat SPEC/le... |
| `tests/unified/e2e/test\_session\_pers...` | fix_remaining_imports.py:63 | main | `   2. View: app...`, `   cat SPEC/le... |
| `tests/unified/e2e/test\_session\_stat...` | fix_remaining_imports.py:59 | main | `   2. View: app...`, `   cat SPEC/le... |
| `tests/unified/e2e/test\_thread\_manag...` | fix_import_indents.py:59 | main | `   2. View: app...`, `   cat SPEC/le... |
| `tests/unified/e2e/test\_token\_expiry...` | fix_remaining_imports.py:55 | main | `   2. View: app...`, `   cat SPEC/le... |
| `tests/unified/e2e/test\_token\_lifecy...` | fix_import_indents.py:61 | main | `   2. View: app...`, `   cat SPEC/le... |
| `tests/unified/e2e/test\_websocket\_ev...` | fix_import_indents.py:68 | main | `   2. View: app...`, `   cat SPEC/le... |
| `tests/unified/e2e/test\_websocket\_gu...` | fix_remaining_imports.py:62 | main | `   2. View: app...`, `   cat SPEC/le... |
| `tests/unified/e2e/test\_websocket\_me...` | fix_import_indents.py:66 | main | `   2. View: app...`, `   cat SPEC/le... |
| `tests/unified/e2e/test\_websocket\_me...` | fix_remaining_imports.py:52 | main | `   2. View: app...`, `   cat SPEC/le... |
| `tests/unified/e2e/test\_websocket\_re...` | fix_import_indents.py:63 | main | `   2. View: app...`, `   cat SPEC/le... |
| `tests/unified/e2e/test\_workspace\_is...` | fix_remaining_imports.py:60 | main | `   2. View: app...`, `   cat SPEC/le... |
| `tests/unified/e2e/websocket\_message\...` | fix_remaining_imports.py:70 | main | `   2. View: app...`, `   cat SPEC/le... |
| `tests/unified/health\_service\_checke...` | fix_remaining_imports.py:65 | main | `   2. View: app...`, `   cat SPEC/le... |
| `tests/unified/oauth\_flow\_manager\.py` | fix_remaining_imports.py:66 | main | `   2. View: app...`, `   cat SPEC/le... |
| `tests/unified/test\_load\_performance...` | fix_remaining_imports.py:51 | main | `   2. View: app...`, `   cat SPEC/le... |
| `tests/unified/test\_oauth\_flow\.py` | fix_import_indents.py:64 | main | `   2. View: app...`, `   cat SPEC/le... |
| `tests/unified/test\_transaction\_cons...` | fix_import_indents.py:70 | main | `   2. View: app...`, `   cat SPEC/le... |
| `type\_deduplication\_report\.json` | deduplicate_types.py:416 | main | `   2. View: app...`, `   cat SPEC/le... |
| `type\_safety\.xml` | update_spec_timestamps.py:44 | module | `   2. View: app...`, `   cat SPEC/le... |
| `types\.py` | type_checker.py:154 | TypeChecker._filter_backend... | `   2. View: app...`, `   cat SPEC/le... |
| `types\.xml` | update_spec_timestamps.py:128 | is_legacy_spec | `   2. View: app...`, `   cat SPEC/le... |
| `unified\_import\_manager\.py` | import_management.py:48 | ImportManagementSystem.__in... | `   2. View: app...`, `   cat SPEC/le... |
| `unified\_test\_runner\.py` | deploy_to_gcp.py:171 | GCPDeployer.run_pre_deploym... | `   2. View: app...`, `   cat SPEC/le... |
| `unified\_tools\.py` | fix_schema_imports.py:48 | SchemaImportFixer._move_sch... | `   2. View: app...`, `   cat SPEC/le... |
| `unjustified\_mocks\.json` | analyze_mocks.py:266 | MockAnalyzer.export_unjusti... | `   2. View: app...`, `   cat SPEC/le... |
| `utils\.py` | project_test_validator.py:113 | ProjectTestValidator._is_te... | `   2. View: app...`, `   cat SPEC/le... |
| `violation\_analysis\.json` | identify_violations.py:95 | module | `   2. View: app...`, `   cat SPEC/le... |
| `websocket\_communication\.xml` | update_spec_timestamps.py:56 | module | `   2. View: app...`, `   cat SPEC/le... |
| `websockets\.xml` | code_review_analysis.py:114 | CodeReviewAnalysis._check_k... | `   2. View: app...`, `   cat SPEC/le... |
| `workflow\-config\.yml` | manage_workflows.py:25 | WorkflowManager.__init__ | `   2. View: app...`, `   cat SPEC/le... |
| `workflow\-test\-report\.json` | test_workflows_with_act.py:350 | WorkflowTester.generate_report | `   2. View: app...`, `   cat SPEC/le... |
| `workload\_models\.py` | fix_schema_imports.py:50 | SchemaImportFixer._move_sch... | `   2. View: app...`, `   cat SPEC/le... |
| `ws\_manager\.py` | fast_import_checker.py:262 | fix_known_import_issues | `   2. View: app...`, `   cat SPEC/le... |

### Usage Examples

- **scripts\demo_feature_flag_system.py:275** - `main`
- **scripts\compliance\demo_test_size_enforcement.py:200** - `demo_cli_usage`
- **scripts\setup_import_hooks.py:166** - `main`

---

## Subcategory: url {subcategory-url}

**Count**: 74 literals

### 🟢 High (≥0.8) (74 literals)

| Literal | Files | Context | Related |
|---------|-------|---------|---------|
| `http://` | service_discovery.py:39 | ServiceDiscovery.write_back... | `http://127.0.0....`, `http://127.0.0... |
| `http://127\.0\.0\.1:3000` | main.py:183 | module | `http://`, `http://127.0.0....` |
| `http://127\.0\.0\.1:3001` | main.py:184 | module | `http://`, `http://127.0.0....` |
| `http://127\.0\.0\.1:3002` | main.py:185 | module | `http://`, `http://127.0.0....` |
| `http://127\.0\.0\.1:8000` | main.py:186 | module | `http://`, `http://127.0.0....` |
| `http://127\.0\.0\.1:8001` | main.py:187 | module | `http://`, `http://127.0.0....` |
| `http://127\.0\.0\.1:8002` | main.py:188 | module | `http://`, `http://127.0.0....` |
| `http://127\.0\.0\.1:8080` | main.py:189 | module | `http://`, `http://127.0.0....` |
| `http://127\.0\.0\.1:8081` | main.py:190 | module | `http://`, `http://127.0.0....` |
| `http://127\.0\.0\.1:8082` | main.py:191 | module | `http://`, `http://127.0.0....` |
| `http://localhost` | test_staging_env.py:21 | StagingTester.__init__ | `http://`, `http://127.0.0....` |
| `http://localhost:` | dev_launcher_core.py:239 | DevLauncher._monitor_services | `http://`, `http://127.0.0....` |
| `http://localhost:11434` | service_config.py:136 | ServicesConfiguration | `http://`, `http://127.0.0....` |
| `http://localhost:3000` | config.py:72 | AuthConfig.get_frontend_url | `http://`, `http://127.0.0....` |
| `http://localhost:3000,http://localhos...` | test_env.py:54 | TestEnvironment | `http://`, `http://127.0.0....` |
| `http://localhost:3000/auth/callback` | test_oauth_models.py:195 | TestAuthConfigResponse.test... | `http://`, `http://127.0.0....` |
| `http://localhost:3001` | main.py:175 | module | `http://`, `http://127.0.0....` |
| `http://localhost:3002` | main.py:176 | module | `http://`, `http://127.0.0....` |
| `http://localhost:62832` | test_dynamic_port_health.py:85 | TestDynamicPortHealthChecks... | `http://`, `http://127.0.0....` |
| `http://localhost:62832/health/ready` | test_dynamic_port_health.py:59 | TestDynamicPortHealthChecks... | `http://`, `http://127.0.0....` |
| `http://localhost:62837` | test_dynamic_port_health.py:73 | TestDynamicPortHealthChecks... | `http://`, `http://127.0.0....` |
| `http://localhost:8000` | main.py:161 | module | `http://`, `http://127.0.0....` |
| `http://localhost:8000/api/auth/config` | test_startup_validator.py:99 | TestStartupValidator.test_u... | `http://`, `http://127.0.0....` |
| `http://localhost:8000/api/health` | validate_network_constants.py:123 | validate_url_constants | `http://`, `http://127.0.0....` |
| `http://localhost:8000/docs` | progress_indicator.py:190 | ProgressIndicator._show_ser... | `http://`, `http://127.0.0....` |
| `http://localhost:8000/health/live` | test_health_registration.py:66 | TestHealthRegistrationHelpe... | `http://`, `http://127.0.0....` |
| `http://localhost:8000/health/ready` | test_dynamic_port_health.py:165 | TestDynamicPortHealthChecks... | `http://`, `http://127.0.0....` |
| `http://localhost:8001` | main.py:178 | module | `http://`, `http://127.0.0....` |
| `http://localhost:8002` | main.py:179 | module | `http://`, `http://127.0.0....` |
| `http://localhost:8080` | main.py:162 | module | `http://`, `http://127.0.0....` |
| `http://localhost:8080/docs` | build_staging.py:178 | StagingBuilder.health_check | `http://`, `http://127.0.0....` |
| `http://localhost:8080/health` | build_staging.py:176 | StagingBuilder.health_check | `http://`, `http://127.0.0....` |
| `http://localhost:8081` | config.py:84 | AuthConfig.get_auth_service... | `http://`, `http://127.0.0....` |
| `http://localhost:8081/auth/callback` | test_env.py:206 | EnvironmentPresets.oauth_te... | `http://`, `http://127.0.0....` |
| `http://localhost:8081/auth/dev/login` | test_oauth_models.py:198 | TestAuthConfigResponse.test... | `http://`, `http://127.0.0....` |
| `http://localhost:8081/auth/login` | test_oauth_models.py:193 | TestAuthConfigResponse.test... | `http://`, `http://127.0.0....` |
| `http://localhost:8081/auth/logout` | test_oauth_models.py:194 | TestAuthConfigResponse.test... | `http://`, `http://127.0.0....` |
| `http://localhost:8081/auth/token` | test_oauth_models.py:196 | TestAuthConfigResponse.test... | `http://`, `http://127.0.0....` |
| `http://localhost:8081/auth/verify` | test_oauth_models.py:197 | TestAuthConfigResponse.test... | `http://`, `http://127.0.0....` |
| `http://localhost:8081/health` | start_auth_service.py:70 | AuthServiceManager.start_au... | `http://`, `http://127.0.0....` |
| `http://localhost:8082` | main.py:182 | module | `http://`, `http://127.0.0....` |
| `http://localhost:8082/health/ready` | test_dynamic_port_health.py:45 | TestDynamicPortHealthChecks... | `http://`, `http://127.0.0....` |
| `http://malicious\-site\.com` | test_websocket_dev_mode.py:158 | WebSocketDevModeTest.test_c... | `http://`, `http://127.0.0....` |
| `https://` | test_oauth_models.py:143 | TestAuthEndpoints.test_requ... | `http://`, `http://127.0.0....` |
| `https://accounts\.google\.com` | token_factory.py:201 | OAuthTokenFactory.create_go... | `http://`, `http://127.0.0....` |
| `https://accounts\.google\.com/o/oauth...` | auth_routes.py:115 | initiate_oauth_login | `http://`, `http://127.0.0....` |
| `https://api\.github\.com` | verify_workflow_status.py:78 | WorkflowStatusVerifier._cre... | `http://`, `http://127.0.0....` |
| `https://api\.github\.com/repos/` | cleanup_staging_environments.py:88 | StagingEnvironmentCleaner.c... | `http://`, `http://127.0.0....` |
| `https://api\.netrasystems\.ai` | main.py:168 | module | `http://`, `http://127.0.0....` |
| `https://api\.staging\.netrasystems\.ai` | main.py:159 | module | `http://`, `http://127.0.0....` |
| `https://app\.example\.com` | test_oauth_models.py:181 | TestAuthConfigResponse.test... | `http://`, `http://127.0.0....` |
| `https://app\.example\.com/auth/callback` | test_oauth_models.py:138 | TestAuthEndpoints.test_requ... | `http://`, `http://127.0.0....` |
| `https://app\.netrasystems\.ai` | main.py:167 | module | `http://`, `http://127.0.0....` |
| `https://app\.staging\.netrasystems\.ai` | config.py:68 | AuthConfig.get_frontend_url | `http://`, `http://127.0.0....` |
| `https://auth\.example\.com/auth/login` | test_oauth_models.py:136 | TestAuthEndpoints.test_requ... | `http://`, `http://127.0.0....` |
| `https://auth\.example\.com/auth/logout` | test_oauth_models.py:137 | TestAuthEndpoints.test_requ... | `http://`, `http://127.0.0....` |
| `https://auth\.example\.com/auth/token` | test_oauth_models.py:139 | TestAuthEndpoints.test_requ... | `http://`, `http://127.0.0....` |
| `https://auth\.example\.com/auth/verify` | test_oauth_models.py:140 | TestAuthEndpoints.test_requ... | `http://`, `http://127.0.0....` |
| `https://auth\.netrasystems\.ai` | config.py:82 | AuthConfig.get_auth_service... | `http://`, `http://127.0.0....` |
| `https://auth\.staging\.netrasystems\.ai` | config.py:80 | AuthConfig.get_auth_service... | `http://`, `http://127.0.0....` |
| `https://avatars\.githubusercontent\.com/` | token_factory.py:226 | OAuthTokenFactory.create_gi... | `http://`, `http://127.0.0....` |
| `https://dash\.readme\.com/api/v1` | generate_openapi_spec.py:138 | get_readme_url | `http://`, `http://127.0.0....` |
| `https://evil\.com` | test_security.py:257 | TestCSRFProtection.test_csr... | `http://`, `http://127.0.0....` |
| `https://example\.com/avatar\.jpg` | test_auth_oauth_google.py:49 | module | `http://`, `http://127.0.0....` |
| `https://example\.com/avatar/` | user_factory.py:87 | UserFactory.create_oauth_us... | `http://`, `http://127.0.0....` |
| `https://example\.com/john\.jpg` | test_auth_oauth_google.py:235 | TestGoogleOAuthFlow.test_go... | `http://`, `http://127.0.0....` |
| `https://malicious\-site\.com` | test_security.py:258 | TestCSRFProtection.test_csr... | `http://`, `http://127.0.0....` |
| `https://netrasystems\.ai` | config.py:70 | AuthConfig.get_frontend_url | `http://`, `http://127.0.0....` |
| `https://netrasystems\.ai/license` | generate_openapi_spec.py:71 | _add_contact_info | `http://`, `http://127.0.0....` |
| `https://netrasystems\.ai/support` | generate_openapi_spec.py:67 | _add_contact_info | `http://`, `http://127.0.0....` |
| `https://oauth2\.googleapis\.com` | validate_network_constants.py:157 | validate_service_endpoints | `http://`, `http://127.0.0....` |
| `https://oauth2\.googleapis\.com/token` | auth_routes.py:418 | oauth_callback | `http://`, `http://127.0.0....` |
| `https://staging\-api\.netrasystems\.ai` | generate_openapi_spec.py:81 | _add_servers | `http://`, `http://127.0.0....` |
| `https://www\.googleapis\.com/oauth2/v...` | auth_routes.py:437 | oauth_callback | `http://`, `http://127.0.0....` |

### Usage Examples

- **scripts\service_discovery.py:39** - `ServiceDiscovery.write_backend_info`
- **auth_service\main.py:183** - `module`
- **auth_service\main.py:184** - `module`

---

## Subcategory: websocket_endpoint {subcategory-websocket-endpoint}

**Count**: 4 literals

### 🟢 High (≥0.8) (4 literals)

| Literal | Files | Context | Related |
|---------|-------|---------|---------|
| `/ws` | dev_launcher_service.py:135 | ServiceManager._finalize_ba... | `/ws/secure`, `/ws/secure/conf...` |
| `/ws/secure` | test_websocket_validator_fix.py:74 | TestWebSocketValidatorFix.t... | `/ws`, `/ws/secure/conf...` |
| `/ws/secure/config` | test_websocket_dev_mode.py:90 | WebSocketDevModeTest.test_c... | `/ws`, `/ws/secure` |
| `/ws/secure/health` | test_websocket_dev_mode.py:120 | WebSocketDevModeTest.test_h... | `/ws`, `/ws/secure` |

### Usage Examples

- **scripts\dev_launcher_service.py:135** - `ServiceManager._finalize_backend_startup`
- **dev_launcher\tests\test_websocket_validator_fix.py:74** - `TestWebSocketValidatorFix.test_validator_sends_plain_json_to_secure_endpoints`
- **scripts\test_websocket_dev_mode.py:90** - `WebSocketDevModeTest.test_config_endpoint`

---

## 🔗 Navigation

- 🏠 [Back to Main Index](../string_literals_index.md)
- 📂 [Browse Other Categories](./)

### Related Categories

- ⚙️ [Configuration](configuration.md) - Paths are often stored in configuration

---

*This is the detailed documentation for the `paths` category.*
*For the complete system overview, see the [Main String Literals Index](../string_literals_index.md).*