# 🏷️ Identifiers Literals

Component names, class names, field names, and identifiers

*Generated on 2025-08-21 22:10:00*

## 📊 Category Statistics

| Metric | Value |
|--------|-------|
| Total Literals | 612 |
| Subcategories | 6 |
| Average Confidence | 0.513 |

## 📋 Subcategories

- [class (41 literals)](#subcategory-class)
- [component (70 literals)](#subcategory-component)
- [field (34 literals)](#subcategory-field)
- [function (146 literals)](#subcategory-function)
- [hash (5 literals)](#subcategory-hash)
- [name (316 literals)](#subcategory-name)

## Subcategory: class {subcategory-class}

**Count**: 41 literals

### 🟡 Medium (0.5-0.8) (41 literals)

| Literal | Files | Context | Related |
|---------|-------|---------|---------|
| `ai` | manage_workflows.py:81 | WorkflowManager._get_workfl... | `go`, `go` |
| `ai` | manage_workflows.py:82 | WorkflowManager._get_workfl... | `go`, `go` |
| `ai` | workflow_presets.py:34 | WorkflowPresets.get_minimal... | `go`, `go` |
| `ai` | workflow_presets.py:49 | WorkflowPresets.get_standar... | `go`, `go` |
| `ai` | workflow_presets.py:64 | WorkflowPresets.get_full_pr... | `go`, `go` |
| `db` | comprehensive_import_scanner.py:157 | ComprehensiveImportScanner.... | `go`, `go` |
| `db` | categorizer_enhanced.py:284 | EnhancedStringLiteralCatego... | `go`, `go` |
| `GB` | cleanup_generated_files.py:147 | format_bytes | `go`, `go` |
| `gh` | cleanup_workflow_runs.py:18 | run_gh_command | `go`, `go` |
| `gh` | workflow_introspection.py:70 | WorkflowIntrospector._run_g... | `go`, `go` |
| `gh` | workflow_introspection.py:91 | WorkflowIntrospector.list_w... | `go`, `go` |
| `gh` | workflow_introspection.py:188 | WorkflowIntrospector.get_ru... | `go`, `go` |
| `gh` | workflow_introspection.py:209 | WorkflowIntrospector.watch_run | `go`, `go` |
| `go` | agent_tracking_helper.py:40 | AgentTrackingHelper | `in`, `up` |
| `go` | agent_tracking_helper.py:169 | AgentTrackingHelper._format... | `in`, `up` |
| `go` | agent_tracking_helper.py:181 | AgentTrackingHelper._extrac... | `in`, `up` |
| `go` | agent_tracking_helper.py:203 | AgentTrackingHelper._extrac... | `in`, `up` |
| `go` | agent_tracking_helper.py:233 | AgentTrackingHelper._format... | `in`, `up` |
| `in` | aggressive_syntax_fix.py:157 | aggressive_fix | `go`, `go` |
| `in` | generate_openapi_spec.py:103 | _get_security_schemes | `go`, `go` |
| `KB` | cleanup_generated_files.py:147 | format_bytes | `go`, `go` |
| `ls` | dependency_scanner.py:133 | get_installed_node_packages | `go`, `go` |
| `ls` | startup_diagnostics.py:97 | check_dependencies | `go`, `go` |
| `MB` | cleanup_generated_files.py:147 | format_bytes | `go`, `go` |
| `md` | startup_reporter.py:82 | MarkdownReportGenerator.gen... | `go`, `go` |
| `ms` | environment_validator.py:498 | main | `go`, `go` |
| `nt` | cleanup_workflow_runs.py:19 | run_gh_command | `go`, `go` |
| `nt` | diagnostic_helpers.py:110 | get_system_state | `go`, `go` |
| `OK` | check_e2e_imports.py:92 | E2EImportChecker.check_file... | `go`, `go` |
| `OK` | dev_launcher_core.py:123 | DevLauncher.cleanup | `go`, `go` |
| `OK` | dev_launcher_core.py:136 | DevLauncher.check_dependencies | `go`, `go` |
| `OK` | dev_launcher_service.py:133 | ServiceManager._finalize_ba... | `go`, `go` |
| `OK` | dev_launcher_service.py:239 | ServiceManager._finalize_fr... | `go`, `go` |
| `OK` | environment_validator.py:513 | main | `go`, `go` |
| `OK` | environment_validator.py:514 | main | `go`, `go` |
| `OK` | startup_diagnostics.py:78 | check_database_connection | `go`, `go` |
| `ps` | reset_clickhouse_final.py:18 | _check_docker_container | `go`, `go` |
| `rm` | dependency_installer.py:165 | clean_node_modules | `go`, `go` |
| `sh` | setup_act.py:46 | install_act | `go`, `go` |
| `up` | build_staging.py:142 | StagingBuilder.start_stagin... | `go`, `go` |
| `up` | start_auth_service.py:29 | AuthServiceManager.start_de... | `go`, `go` |

### Usage Examples

- **scripts\manage_workflows.py:81** - `WorkflowManager._get_workflow_category`
- **scripts\manage_workflows.py:82** - `WorkflowManager._get_workflow_category`
- **scripts\workflow_presets.py:34** - `WorkflowPresets.get_minimal_preset`

---

## Subcategory: component {subcategory-component}

**Count**: 70 literals

### 🟢 High (≥0.8) (68 literals)

| Literal | Files | Context | Related |
|---------|-------|---------|---------|
| `\_handler` | ssot_checker.py:96 | SSOTChecker._check_duplicat... | `JWTConstants.NE...`, `HeaderConstant... |
| `\_manager` | ssot_checker.py:99 | SSOTChecker._check_duplicat... | `JWTConstants.NE...`, `HeaderConstant... |
| `auth\_service` | auto_fix_test_violations.py:93 | TestFileAnalyzer.find_test_... | `JWTConstants.NE...`, `HeaderConstant... |
| `auth\_service` | business_value_test_index.py:412 | BusinessValueTestIndexer._d... | `JWTConstants.NE...`, `HeaderConstant... |
| `auth\_service` | check_imports.py:177 | ImportAnalyzer._find_local_... | `JWTConstants.NE...`, `HeaderConstant... |
| `auth\_service` | core.py:49 | ComplianceConfig.__init__ | `JWTConstants.NE...`, `HeaderConstant... |
| `auth\_service` | fake_test_scanner.py:58 | FakeTestScanner.scan_all_tests | `JWTConstants.NE...`, `HeaderConstant... |
| `auth\_service` | test_size_validator.py:131 | TestSizeValidator._discover... | `JWTConstants.NE...`, `HeaderConstant... |
| `auth\_service` | comprehensive_import_scanner.py:631 | ComprehensiveImportScanner.... | `JWTConstants.NE...`, `HeaderConstant... |
| `auth\_service` | deploy_to_gcp.py:82 | GCPDeployer.__init__ | `JWTConstants.NE...`, `HeaderConstant... |
| `auth\_service` | enhanced_string_literals_docs.py:28 | scan_and_generate_docs | `JWTConstants.NE...`, `HeaderConstant... |
| `auth\_service` | enhanced_string_literals_docs.py:93 | main | `JWTConstants.NE...`, `HeaderConstant... |
| `auth\_service` | remove_duplicate_test_setup.py:39 | main | `JWTConstants.NE...`, `HeaderConstant... |
| `auth\_service` | scan_string_literals.py:302 | main | `JWTConstants.NE...`, `HeaderConstant... |
| `auth\_service` | scan_string_literals_enhanced.py:302 | EnhancedStringLiteralIndexe... | `JWTConstants.NE...`, `HeaderConstant... |
| `auth\_service` | start_auth_service.py:52 | AuthServiceManager.start_au... | `JWTConstants.NE...`, `HeaderConstant... |
| `auth\_service` | test_staging_startup.py:83 | StagingStartupTester.test_d... | `JWTConstants.NE...`, `HeaderConstant... |
| `auth\_service` | validate_jwt_consistency.py:22 | module | `JWTConstants.NE...`, `HeaderConstant... |
| `auth\_service` | validate_network_constants.py:186 | validate_network_environmen... | `JWTConstants.NE...`, `HeaderConstant... |
| `= get\_connection\_manager` | fix_e2e_connection_manager_imports.py:92 | fix_connection_manager_imports | `JWTConstants.NE...`, `HeaderConstant... |
| `agent\_orchestration\_service` | fix_e2e_tests_comprehensive.py:59 | E2ETestFixer._get_common_fi... | `JWTConstants.NE...`, `HeaderConstant... |
| `agent\_service` | comprehensive_import_scanner.py:155 | ComprehensiveImportScanner.... | `JWTConstants.NE...`, `HeaderConstant... |
| `agent\_service` | fix_e2e_tests_comprehensive.py:66 | E2ETestFixer._get_common_fi... | `JWTConstants.NE...`, `HeaderConstant... |
| `agents/data\_sub\_agent` | extract_function_violations.py:49 | FunctionViolationExtractor.... | `JWTConstants.NE...`, `HeaderConstant... |
| `agents/triage\_sub\_agent` | extract_function_violations.py:51 | FunctionViolationExtractor.... | `JWTConstants.NE...`, `HeaderConstant... |
| `apex\_optimizer\_agent` | status_agent_analyzer.py:103 | AgentSystemAnalyzer._check_... | `JWTConstants.NE...`, `HeaderConstant... |
| `app\.agents\.demo\_agent` | validate_type_deduplication.py:62 | TypeDeduplicationValidator.... | `JWTConstants.NE...`, `HeaderConstant... |
| `app\.core\.secret\_manager` | test_staging_config.py:86 | _clear_config_cache | `JWTConstants.NE...`, `HeaderConstant... |
| `app\.core\.secret\_manager` | test_staging_config.py:87 | _clear_config_cache | `JWTConstants.NE...`, `HeaderConstant... |
| `base\_agent` | comprehensive_import_scanner.py:156 | ComprehensiveImportScanner.... | `JWTConstants.NE...`, `HeaderConstant... |
| `billing\_service` | fix_e2e_tests_comprehensive.py:60 | E2ETestFixer._get_common_fi... | `JWTConstants.NE...`, `HeaderConstant... |
| `data\_sub\_agent` | fix_comprehensive_imports.py:286 | ComprehensiveImportFixerV2.... | `JWTConstants.NE...`, `HeaderConstant... |
| `event\_handler` | scan_string_literals.py:76 | StringLiteralCategorizer | `JWTConstants.NE...`, `HeaderConstant... |
| `from tests\.e2e\.account\_deletion\_f...` | fix_e2e_test_imports.py:59 | ImportFixer.__init__ | `JWTConstants.NE...`, `HeaderConstant... |
| `from tests\.e2e\.integration\.auth\_f...` | fix_e2e_test_imports.py:61 | ImportFixer.__init__ | `JWTConstants.NE...`, `HeaderConstant... |
| `from tests\.e2e\.onboarding\_flow\_ex...` | fix_e2e_test_imports.py:62 | ImportFixer.__init__ | `JWTConstants.NE...`, `HeaderConstant... |
| `from tests\.e2e\.user\_journey\_executor` | fix_e2e_imports.py:78 | E2EImportFixer.__init__ | `JWTConstants.NE...`, `HeaderConstant... |
| `from tests\\\.e2e\\\.integration\\\.a...` | fix_e2e_test_imports.py:59 | ImportFixer.__init__ | `JWTConstants.NE...`, `HeaderConstant... |
| `from tests\\\.e2e\\\.integration\\\.a...` | fix_e2e_test_imports.py:61 | ImportFixer.__init__ | `JWTConstants.NE...`, `HeaderConstant... |
| `from tests\\\.e2e\\\.integration\\\.o...` | fix_e2e_test_imports.py:62 | ImportFixer.__init__ | `JWTConstants.NE...`, `HeaderConstant... |
| `from tests\\\.user\_journey\_executor` | fix_e2e_imports.py:78 | E2EImportFixer.__init__ | `JWTConstants.NE...`, `HeaderConstant... |
| `get\_connection\_manager` | fix_e2e_connection_manager_imports.py:72 | replace_mixed_import | `JWTConstants.NE...`, `HeaderConstant... |
| `HeaderConstants\.USER\_AGENT` | auth_constants_migration.py:56 | AuthConstantsMigrator.__init__ | `JWTConstants.NE...`, `auth_service` |
| `JWTConstants\.NETRA\_AUTH\_SERVICE` | auth_constants_migration.py:50 | AuthConstantsMigrator.__init__ | `HeaderConstants...`, `auth_service` |
| `K\_SERVICE` | test_config_loading.py:35 | _print_environment_variables | `JWTConstants.NE...`, `HeaderConstant... |
| `K\_SERVICE` | test_environment_detection.py:18 | test_auth_client_environmen... | `JWTConstants.NE...`, `HeaderConstant... |
| `K\_SERVICE` | test_environment_detection.py:43 | test_auth_client_environmen... | `JWTConstants.NE...`, `HeaderConstant... |
| `K\_SERVICE` | test_environment_detection.py:50 | test_auth_client_environmen... | `JWTConstants.NE...`, `HeaderConstant... |
| `K\_SERVICE` | test_environment_detection.py:57 | test_auth_client_environmen... | `JWTConstants.NE...`, `HeaderConstant... |
| `K\_SERVICE` | test_staging_config.py:43 | _set_staging_env_vars | `JWTConstants.NE...`, `HeaderConstant... |
| `K\_SERVICE` | test_staging_config.py:64 | _print_env_setup_status | `JWTConstants.NE...`, `HeaderConstant... |
| `optimization\_service` | fix_e2e_tests_comprehensive.py:54 | E2ETestFixer._get_common_fi... | `JWTConstants.NE...`, `HeaderConstant... |
| `real\_llm\_manager` | fix_e2e_tests_comprehensive.py:61 | E2ETestFixer._get_common_fi... | `JWTConstants.NE...`, `HeaderConstant... |
| `real\_websocket\_manager` | fix_e2e_tests_comprehensive.py:62 | E2ETestFixer._get_common_fi... | `JWTConstants.NE...`, `HeaderConstant... |
| `supervisor\_agent` | fix_e2e_tests_comprehensive.py:67 | E2ETestFixer._get_common_fi... | `JWTConstants.NE...`, `HeaderConstant... |
| `thread\_management\_service` | fix_e2e_tests_comprehensive.py:58 | E2ETestFixer._get_common_fi... | `JWTConstants.NE...`, `HeaderConstant... |
| `thread\_service` | comprehensive_import_scanner.py:155 | ComprehensiveImportScanner.... | `JWTConstants.NE...`, `HeaderConstant... |
| `thread\_service` | fast_import_checker.py:71 | fix_known_import_issues | `JWTConstants.NE...`, `HeaderConstant... |
| `thread\_service` | fast_import_checker.py:362 | scan_e2e_tests | `JWTConstants.NE...`, `HeaderConstant... |
| `thread\_service` | fast_import_checker.py:396 | verify_fixes | `JWTConstants.NE...`, `HeaderConstant... |
| `thread\_service` | fix_e2e_tests_comprehensive.py:72 | E2ETestFixer._get_common_fi... | `JWTConstants.NE...`, `HeaderConstant... |
| `unified\_manager` | import_management.py:48 | ImportManagementSystem.__in... | `JWTConstants.NE...`, `HeaderConstant... |
| `user\_service` | fix_e2e_tests_comprehensive.py:71 | E2ETestFixer._get_common_fi... | `JWTConstants.NE...`, `HeaderConstant... |
| `websocket\_manager` | fix_e2e_tests_comprehensive.py:65 | E2ETestFixer._get_common_fi... | `JWTConstants.NE...`, `HeaderConstant... |
| `websocket\_manager` | test_staging_startup.py:46 | StagingStartupTester.test_s... | `JWTConstants.NE...`, `HeaderConstant... |
| `websocket\_service` | comprehensive_import_scanner.py:155 | ComprehensiveImportScanner.... | `JWTConstants.NE...`, `HeaderConstant... |
| `ws\_manager` | fast_import_checker.py:366 | scan_e2e_tests | `JWTConstants.NE...`, `HeaderConstant... |
| `ws\_manager` | fast_import_checker.py:400 | verify_fixes | `JWTConstants.NE...`, `HeaderConstant... |

### 🟡 Medium (0.5-0.8) (2 literals)

| Literal | Files | Context | Related |
|---------|-------|---------|---------|
| `import netra\_backend\.app\.websocket...` | fix_e2e_imports.py:48 | E2EImportFixer.__init__ | `JWTConstants.NE...`, `HeaderConstant... |
| `Service URLs should include auth\_ser...` | validate_network_constants.py:186 | validate_network_environmen... | `JWTConstants.NE...`, `HeaderConstant... |

### Usage Examples

- **scripts\compliance\ssot_checker.py:96** - `SSOTChecker._check_duplicate_handlers`
- **scripts\compliance\ssot_checker.py:99** - `SSOTChecker._check_duplicate_handlers`
- **scripts\auto_fix_test_violations.py:93** - `TestFileAnalyzer.find_test_files`

---

## Subcategory: field {subcategory-field}

**Count**: 34 literals

### 🟢 High (≥0.8) (32 literals)

| Literal | Files | Context | Related |
|---------|-------|---------|---------|
| `agent\_orchestration` | business_value_test_index.py:97 | BusinessValueTestIndexer.__... | `user_flows`, `user_session_ti...` |
| `agent\_orchestration` | business_value_test_index.py:391 | BusinessValueTestIndexer._d... | `user_flows`, `user_session_ti...` |
| `agent\_orchestration` | business_value_test_index.py:437 | BusinessValueTestIndexer._c... | `user_flows`, `user_session_ti...` |
| `agent\_orchestration` | business_value_test_index.py:460 | BusinessValueTestIndexer._g... | `user_flows`, `user_session_ti...` |
| `agent\_orchestration` | business_value_test_index.py:631 | BusinessValueTestIndexer._i... | `user_flows`, `user_session_ti...` |
| `agent\_orchestration` | business_value_test_index.py:674 | BusinessValueTestIndexer._g... | `user_flows`, `user_session_ti...` |
| `agent\_validation\_report\.html` | validate_agent_tests.py:320 | AgentTestValidator.save_rep... | `user_flows`, `agent_orchestra...` |
| `boolean\_state` | scan_string_literals.py:91 | StringLiteralCategorizer | `user_flows`, `agent_orchestra...` |
| `git\_state` | metadata_header_generator.py:94 | MetadataHeaderGenerator.gen... | `user_flows`, `agent_orchestra...` |
| `git\_state` | metadata_header_generator.py:141 | MetadataHeaderGenerator.for... | `user_flows`, `agent_orchestra...` |
| `git\_state` | metadata_header_generator.py:141 | MetadataHeaderGenerator.for... | `user_flows`, `agent_orchestra...` |
| `git\_state` | metadata_header_generator.py:141 | MetadataHeaderGenerator.for... | `user_flows`, `agent_orchestra...` |
| `git\_state` | metadata_header_generator.py:159 | MetadataHeaderGenerator.for... | `user_flows`, `agent_orchestra...` |
| `git\_state` | metadata_header_generator.py:159 | MetadataHeaderGenerator.for... | `user_flows`, `agent_orchestra...` |
| `git\_state` | metadata_header_generator.py:159 | MetadataHeaderGenerator.for... | `user_flows`, `agent_orchestra...` |
| `git\_state` | metadata_header_generator.py:198 | MetadataHeaderGenerator._fo... | `user_flows`, `agent_orchestra...` |
| `git\_state` | metadata_header_generator.py:198 | MetadataHeaderGenerator._fo... | `user_flows`, `agent_orchestra...` |
| `git\_state` | metadata_header_generator.py:198 | MetadataHeaderGenerator._fo... | `user_flows`, `agent_orchestra...` |
| `git\_state` | metadata_header_generator.py:216 | MetadataHeaderGenerator._fo... | `user_flows`, `agent_orchestra...` |
| `git\_state` | metadata_header_generator.py:216 | MetadataHeaderGenerator._fo... | `user_flows`, `agent_orchestra...` |
| `git\_state` | metadata_header_generator.py:216 | MetadataHeaderGenerator._fo... | `user_flows`, `agent_orchestra...` |
| `git\_state` | metadata_header_generator.py:235 | MetadataHeaderGenerator._fo... | `user_flows`, `agent_orchestra...` |
| `git\_state` | metadata_header_generator.py:236 | MetadataHeaderGenerator._fo... | `user_flows`, `agent_orchestra...` |
| `git\_state` | metadata_header_generator.py:237 | MetadataHeaderGenerator._fo... | `user_flows`, `agent_orchestra...` |
| `message\_flow` | test_websocket_dev_mode.py:44 | WebSocketDevModeTest.__init__ | `user_flows`, `agent_orchestra...` |
| `message\_flow` | test_websocket_dev_mode.py:209 | WebSocketDevModeTest.test_w... | `user_flows`, `agent_orchestra...` |
| `thread\_ids` | seed_staging_data.py:358 | StagingDataSeeder.generate_... | `user_flows`, `agent_orchestra...` |
| `user\_flows` | auto_fix_test_sizes.py:357 | TestFileSplitter._determine... | `agent_orchestra...`, `agent_orchestr... |
| `user\_ids` | seed_staging_data.py:357 | StagingDataSeeder.generate_... | `user_flows`, `agent_orchestra...` |
| `user\_intent` | metadata_header_generator.py:92 | MetadataHeaderGenerator.gen... | `user_flows`, `agent_orchestra...` |
| `user\_session\_timeout` | demo_enhanced_categorizer.py:112 | categorize_specific_examples | `user_flows`, `agent_orchestra...` |
| `user\_tier` | seed_staging_data.py:322 | StagingDataSeeder._create_m... | `user_flows`, `agent_orchestra...` |

### 🔴 Low (<0.5) (2 literals)

| Literal | Files | Context | Related |
|---------|-------|---------|---------|
| `thread\_service = ThreadService\(\)` | fast_import_checker.py:80 | fix_known_import_issues | `user_flows`, `agent_orchestra...` |
| `thread\_service = ThreadService\(\)` | fast_import_checker.py:97 | fix_known_import_issues | `user_flows`, `agent_orchestra...` |

### Usage Examples

- **scripts\business_value_test_index.py:97** - `BusinessValueTestIndexer.__init__`
- **scripts\business_value_test_index.py:391** - `BusinessValueTestIndexer._determine_category`
- **scripts\business_value_test_index.py:437** - `BusinessValueTestIndexer._calculate_business_value_score`

---

## Subcategory: function {subcategory-function}

**Count**: 146 literals

### 🟡 Medium (0.5-0.8) (146 literals)

| Literal | Files | Context | Related |
|---------|-------|---------|---------|
| `\_api` | environment_validator.py:415 | EnvironmentValidator.genera... | `test_`, `test_` |
| `\_api` | environment_validator.py:457 | EnvironmentValidator._gener... | `test_`, `test_` |
| `\_backup` | file_checker.py:33 | FileChecker.check_file_naming | `test_`, `test_` |
| `\_backup` | find_large_app_files.py:25 | find_large_files | `test_`, `test_` |
| `\_branch\_` | auto_decompose_functions.py:241 | FunctionDecomposer._suggest... | `test_`, `test_` |
| `\_comprehensive` | generate_test_audit.py:102 | analyze_test_structure | `test_`, `test_` |
| `\_copy` | file_checker.py:33 | FileChecker.check_file_naming | `test_`, `test_` |
| `\_critical` | generate_test_audit.py:100 | analyze_test_structure | `test_`, `test_` |
| `\_current\_file\_path` | business_value_test_index.py:321 | BusinessValueTestIndexer._d... | `test_`, `test_` |
| `\_enhanced` | file_checker.py:33 | FileChecker.check_file_naming | `test_`, `test_` |
| `\_fixed` | file_checker.py:33 | FileChecker.check_file_naming | `test_`, `test_` |
| `\_helper` | test_refactor_helper.py:208 | TestRefactorHelper._determi... | `test_`, `test_` |
| `\_helper\_` | test_fixer.py:279 | TestFixer._split_function_c... | `test_`, `test_` |
| `\_initialization` | fix_e2e_tests_comprehensive.py:251 | E2ETestFixer._add_basic_tests | `test_`, `test_` |
| `\_input` | auto_decompose_functions.py:270 | FunctionDecomposer._suggest... | `test_`, `test_` |
| `\_integration\_` | real_test_requirements_enforcer.py:343 | RealTestRequirementsEnforce... | `test_`, `test_` |
| `\_latency\_avg` | real_service_test_metrics.py:106 | RealServiceTestMetrics.fina... | `test_`, `test_` |
| `\_latency\_avg` | real_service_test_metrics.py:161 | RealServiceTestMetrics._bui... | `test_`, `test_` |
| `\_legacy` | type_checker.py:127 | TypeChecker._categorize_files | `test_`, `test_` |
| `\_new` | file_checker.py:33 | FileChecker.check_file_naming | `test_`, `test_` |
| `\_old` | file_checker.py:33 | FileChecker.check_file_naming | `test_`, `test_` |
| `\_old` | type_checker.py:127 | TypeChecker._categorize_files | `test_`, `test_` |
| `\_old` | type_checker.py:203 | TypeChecker._are_separated_... | `test_`, `test_` |
| `\_old` | type_checker.py:203 | TypeChecker._are_separated_... | `test_`, `test_` |
| `\_part` | auto_split_files.py:201 | FileSplitter._suggest_logic... | `test_`, `test_` |
| `\_part` | auto_split_files.py:226 | FileSplitter._fallback_spli... | `test_`, `test_` |
| `\_part` | fix_all_test_issues.py:182 | split_large_test_file | `test_`, `test_` |
| `\_part` | fix_all_test_issues.py:198 | split_large_test_file | `test_`, `test_` |
| `\_part\_` | auto_decompose_functions.py:339 | FunctionDecomposer._suggest... | `test_`, `test_` |
| `\_part\_` | auto_fix_test_sizes.py:472 | TestFunctionOptimizer._spli... | `test_`, `test_` |
| `\_pr` | seed_staging_data.py:120 | StagingDataSeeder._build_ad... | `test_`, `test_` |
| `\_pr` | seed_staging_data.py:131 | StagingDataSeeder._build_ma... | `test_`, `test_` |
| `\_pr` | seed_staging_data.py:142 | StagingDataSeeder._build_re... | `test_`, `test_` |
| `\_process\_` | auto_decompose_functions.py:277 | FunctionDecomposer._suggest... | `test_`, `test_` |
| `\_real` | test_discovery_report.py:46 | EnhancedTestDiscoveryReport... | `test_`, `test_` |
| `\_safe\_operation\_` | auto_decompose_functions.py:307 | FunctionDecomposer._suggest... | `test_`, `test_` |
| `\_temp` | file_checker.py:33 | FileChecker.check_file_naming | `test_`, `test_` |
| `\_test` | real_test_linter.py:237 | RealTestLinter.check_git_diff | `test_`, `test_` |
| `\_test` | remove_test_stubs.py:99 | TestStubDetector.should_sca... | `test_`, `test_` |
| `\_test\_` | project_test_validator.py:121 | ProjectTestValidator._is_te... | `test_`, `test_` |
| `\_validate\_` | auto_decompose_functions.py:270 | FunctionDecomposer._suggest... | `test_`, `test_` |
| `architecture\_health\_` | architecture_reporter.py:26 | ArchitectureReporter.export... | `test_`, `test_` |
| `AWS\_` | local_secrets_manager.py:181 | LocalSecretsManager._get_gi... | `test_`, `test_` |
| `batch\_fix\_results\_` | fix_test_batch.py:374 | main | `test_`, `test_` |
| `benchmark\_report\_` | benchmark_optimization.py:390 | TestExecutionBenchmark._sav... | `test_`, `test_` |
| `clean\_slate\_` | clean_slate_executor.py:22 | CleanSlateExecutor.__init__ | `test_`, `test_` |
| `code\_review\_` | code_review_reporter.py:175 | CodeReviewReporter.save_report | `test_`, `test_` |
| `code\_review\_` | report_generator.py:185 | ReportGenerator.save_report | `test_`, `test_` |
| `complete\_` | test_refactor_helper.py:199 | TestRefactorHelper._determi... | `test_`, `test_` |
| `comprehensive\_fix\_` | comprehensive_test_fixer.py:406 | BatchProcessor.generate_report | `test_`, `test_` |
| `create\_` | auto_split_files.py:256 | FileSplitter._group_functio... | `test_`, `test_` |
| `delete\_` | auto_split_files.py:260 | FileSplitter._group_functio... | `test_`, `test_` |
| `demo\_` | function_complexity_linter.py:72 | FunctionComplexityLinter._i... | `test_`, `test_` |
| `DOCKER\_` | local_secrets_manager.py:181 | LocalSecretsManager._get_gi... | `test_`, `test_` |
| `example\_` | function_complexity_linter.py:72 | FunctionComplexityLinter._i... | `test_`, `test_` |
| `format\_` | code_review_ai_detector.py:49 | CodeReviewAIDetector._check... | `test_`, `test_` |
| `format\_` | ai_detector.py:44 | AIDetector._get_duplicate_p... | `test_`, `test_` |
| `full\_` | test_refactor_helper.py:199 | TestRefactorHelper._determi... | `test_`, `test_` |
| `GCP\_` | local_secrets_manager.py:181 | LocalSecretsManager._get_gi... | `test_`, `test_` |
| `get\_` | auto_split_files.py:252 | FileSplitter._group_functio... | `test_`, `test_` |
| `GITHUB\_` | local_secrets_manager.py:181 | LocalSecretsManager._get_gi... | `test_`, `test_` |
| `handler\_` | ssot_checker.py:97 | SSOTChecker._check_duplicat... | `test_`, `test_` |
| `manager\_` | ssot_checker.py:100 | SSOTChecker._check_duplicat... | `test_`, `test_` |
| `metadata\_` | setup_assistant.py:60 | _create_assistant_config | `test_`, `test_` |
| `mock\_` | real_test_requirements_enforcer.py:356 | RealTestRequirementsEnforce... | `test_`, `test_` |
| `NPM\_` | local_secrets_manager.py:181 | LocalSecretsManager._get_gi... | `test_`, `test_` |
| `params\_` | ssot_checker.py:155 | SSOTChecker._get_function_s... | `test_`, `test_` |
| `parse\_` | code_review_ai_detector.py:50 | CodeReviewAIDetector._check... | `test_`, `test_` |
| `parse\_` | ai_detector.py:45 | AIDetector._get_duplicate_p... | `test_`, `test_` |
| `patch\_` | analyze_mocks.py:152 | MockAnalyzer._get_decorator... | `test_`, `test_` |
| `patch\_` | analyze_mocks.py:155 | MockAnalyzer._get_decorator... | `test_`, `test_` |
| `port\_` | environment_validator.py:337 | EnvironmentValidator.check_... | `test_`, `test_` |
| `port\_` | environment_validator.py:340 | EnvironmentValidator.check_... | `test_`, `test_` |
| `port\_` | environment_validator.py:344 | EnvironmentValidator.check_... | `test_`, `test_` |
| `pre\_clean\_slate\_` | clean_slate_executor.py:24 | CleanSlateExecutor.__init__ | `test_`, `test_` |
| `process\_` | ssot_checker.py:171 | SSOTChecker._are_likely_dup... | `test_`, `test_` |
| `pytest\_` | test_limits_checker.py:133 | TestLimitsChecker._is_test_... | `test_`, `test_` |
| `pytest\_` | test_size_validator.py:263 | TestSizeValidator._is_test_... | `test_`, `test_` |
| `real\_` | test_discovery_report.py:46 | EnhancedTestDiscoveryReport... | `test_`, `test_` |
| `sample\_` | function_complexity_linter.py:72 | FunctionComplexityLinter._i... | `test_`, `test_` |
| `set\_` | auto_split_files.py:254 | FileSplitter._group_functio... | `test_`, `test_` |
| `split\_by\_` | test_refactor_helper.py:719 | main | `test_`, `test_` |
| `staging\_test\_pr\_` | validate_staging_config.py:243 | check_redis_connection | `test_`, `test_` |
| `test\_` | analyze_critical_paths.py:50 | module | `architecture_he...`, `_branch_` |
| `test\_` | analyze_test_overlap.py:98 | TestOverlapAnalyzer._collec... | `architecture_he...`, `_branch_` |
| `test\_` | analyze_test_overlap.py:123 | TestOverlapAnalyzer._extrac... | `architecture_he...`, `_branch_` |
| `test\_` | test_generator.py:34 | TestGenerator.generate_smar... | `architecture_he...`, `_branch_` |
| `test\_` | test_generator.py:86 | TestGenerator.find_test_file | `architecture_he...`, `_branch_` |
| `test\_` | test_generator.py:87 | TestGenerator.find_test_file | `architecture_he...`, `_branch_` |
| `test\_` | test_generator.py:88 | TestGenerator.find_test_file | `architecture_he...`, `_branch_` |
| `test\_` | test_reviewer.py:307 | AutonomousTestReviewer._fin... | `architecture_he...`, `_branch_` |
| `test\_` | test_reviewer.py:309 | AutonomousTestReviewer._fin... | `architecture_he...`, `_branch_` |
| `test\_` | test_reviewer.py:310 | AutonomousTestReviewer._fin... | `architecture_he...`, `_branch_` |
| `test\_` | test_reviewer.py:311 | AutonomousTestReviewer._fin... | `architecture_he...`, `_branch_` |
| `test\_` | auto_decompose_functions.py:409 | FunctionDecomposer._should_... | `architecture_he...`, `_branch_` |
| `test\_` | auto_fix_test_sizes.py:103 | TestSizeAnalyzer.analyze_file | `architecture_he...`, `_branch_` |
| `test\_` | auto_fix_test_sizes.py:448 | TestFunctionOptimizer.optim... | `architecture_he...`, `_branch_` |
| `test\_` | auto_fix_test_violations.py:106 | TestFileAnalyzer.find_test_... | `architecture_he...`, `_branch_` |
| `test\_` | auto_fix_test_violations.py:183 | TestFileAnalyzer._extract_f... | `architecture_he...`, `_branch_` |
| `test\_` | auto_split_files.py:250 | FileSplitter._group_functio... | `architecture_he...`, `_branch_` |
| `test\_` | auto_split_files.py:317 | FileSplitter._should_skip_file | `architecture_he...`, `_branch_` |
| `test\_` | business_value_test_index.py:169 | BusinessValueTestIndexer.sc... | `architecture_he...`, `_branch_` |
| `test\_` | business_value_test_index.py:184 | BusinessValueTestIndexer.sc... | `architecture_he...`, `_branch_` |
| `test\_` | business_value_test_index.py:209 | BusinessValueTestIndexer._s... | `architecture_he...`, `_branch_` |
| `test\_` | business_value_test_index.py:214 | BusinessValueTestIndexer._s... | `architecture_he...`, `_branch_` |
| `test\_` | check_e2e_imports.py:69 | E2EImportChecker.find_e2e_t... | `architecture_he...`, `_branch_` |
| `test\_` | generate_fix.py:361 | load_context | `architecture_he...`, `_branch_` |
| `test\_` | core.py:96 | ComplianceConfig.is_test_file | `architecture_he...`, `_branch_` |
| `test\_` | function_checker.py:75 | FunctionChecker._is_example... | `architecture_he...`, `_branch_` |
| `test\_` | project_test_validator.py:121 | ProjectTestValidator._is_te... | `architecture_he...`, `_branch_` |
| `test\_` | real_test_linter.py:237 | RealTestLinter.check_git_diff | `architecture_he...`, `_branch_` |
| `test\_` | real_test_requirements_enforcer.py:293 | FunctionSizeVisitor._check_... | `architecture_he...`, `_branch_` |
| `test\_` | relaxed_violation_counter.py:126 | RelaxedViolationCounter._is... | `architecture_he...`, `_branch_` |
| `test\_` | test_fixer.py:143 | TestGrouper.visit_FunctionDef | `architecture_he...`, `_branch_` |
| `test\_` | test_limits_checker.py:132 | TestLimitsChecker._is_test_... | `architecture_he...`, `_branch_` |
| `test\_` | test_refactor_helper.py:197 | TestRefactorHelper._determi... | `architecture_he...`, `_branch_` |
| `test\_` | test_refactor_helper.py:549 | TestRefactorHelper._extract... | `architecture_he...`, `_branch_` |
| `test\_` | test_size_validator.py:165 | TestSizeValidator._is_test_... | `architecture_he...`, `_branch_` |
| `test\_` | test_size_validator.py:262 | TestSizeValidator._is_test_... | `architecture_he...`, `_branch_` |
| `test\_` | final_syntax_fix.py:15 | create_minimal_test_file | `architecture_he...`, `_branch_` |
| `test\_` | final_syntax_fix.py:16 | create_minimal_test_file | `architecture_he...`, `_branch_` |
| `test\_` | find_large_app_files.py:24 | find_large_files | `architecture_he...`, `_branch_` |
| `test\_` | fix_all_test_issues.py:23 | find_test_files | `architecture_he...`, `_branch_` |
| `test\_` | fix_all_test_issues.py:156 | split_large_test_file | `architecture_he...`, `_branch_` |
| `test\_` | fix_e2e_tests_comprehensive.py:240 | E2ETestFixer._add_basic_tests | `architecture_he...`, `_branch_` |
| `test\_` | fix_e2e_tests_comprehensive.py:251 | E2ETestFixer._add_basic_tests | `architecture_he...`, `_branch_` |
| `test\_` | function_complexity_linter.py:65 | FunctionComplexityLinter._i... | `architecture_he...`, `_branch_` |
| `test\_` | function_complexity_linter.py:72 | FunctionComplexityLinter._i... | `architecture_he...`, `_branch_` |
| `test\_` | generate_test_audit.py:98 | analyze_test_structure | `architecture_he...`, `_branch_` |
| `test\_` | generate_test_audit.py:100 | analyze_test_structure | `architecture_he...`, `_branch_` |
| `test\_` | generate_test_audit.py:102 | analyze_test_structure | `architecture_he...`, `_branch_` |
| `test\_` | generate_test_audit.py:104 | analyze_test_structure | `architecture_he...`, `_branch_` |
| `test\_` | identify_violations.py:46 | scan_codebase | `architecture_he...`, `_branch_` |
| `test\_` | remove_test_stubs.py:78 | TestStubDetector.__init__ | `architecture_he...`, `_branch_` |
| `test\_` | remove_test_stubs.py:99 | TestStubDetector.should_sca... | `architecture_he...`, `_branch_` |
| `test\_` | split_large_files.py:115 | TestFileSplitter._extract_t... | `architecture_he...`, `_branch_` |
| `test\_` | categorizer_enhanced.py:255 | EnhancedStringLiteralCatego... | `architecture_he...`, `_branch_` |
| `test\_` | team_updates_compliance_analyzer.py:96 | ComplianceAnalyzer._should_... | `architecture_he...`, `_branch_` |
| `test\_` | validate_agent_tests.py:94 | AgentTestValidator._count_t... | `architecture_he...`, `_branch_` |
| `test\_` | validate_agent_tests.py:172 | AgentTestValidator.analyze_... | `architecture_he...`, `_branch_` |
| `test\_module\_` | check_e2e_imports.py:85 | E2EImportChecker.check_file... | `test_`, `test_` |
| `ui\_ux\_` | update_spec_timestamps.py:72 | module | `test_`, `test_` |
| `unified\_import\_report\_` | unified_import_manager.py:495 | UnifiedImportManager.save_r... | `test_`, `test_` |
| `update\_` | auto_split_files.py:258 | FileSplitter._group_functio... | `test_`, `test_` |
| `validate\_` | code_review_ai_detector.py:48 | CodeReviewAIDetector._check... | `test_`, `test_` |
| `validate\_` | ai_detector.py:43 | AIDetector._get_duplicate_p... | `test_`, `test_` |

### Usage Examples

- **scripts\environment_validator.py:415** - `EnvironmentValidator.generate_report`
- **scripts\environment_validator.py:457** - `EnvironmentValidator._generate_recommendations`
- **scripts\compliance\file_checker.py:33** - `FileChecker.check_file_naming`

---

## Subcategory: hash {subcategory-hash}

**Count**: 5 literals

### 🟡 Medium (0.5-0.8) (5 literals)

| Literal | Files | Context | Related |
|---------|-------|---------|---------|
| `304612253870` | dev_launcher_secrets.py:22 | EnhancedSecretLoader.__init__ | `ab12cd34ef56`, `701982941522` |
| `304612253870` | fetch_secrets_to_env.py:23 | _get_project_id | `ab12cd34ef56`, `701982941522` |
| `701982941522` | dev_launcher_secrets.py:22 | EnhancedSecretLoader.__init__ | `ab12cd34ef56`, `304612253870` |
| `701982941522` | fetch_secrets_to_env.py:23 | _get_project_id | `ab12cd34ef56`, `304612253870` |
| `ab12cd34ef56` | demo_enhanced_categorizer.py:110 | categorize_specific_examples | `701982941522`, `304612253870` |

### Usage Examples

- **scripts\dev_launcher_secrets.py:22** - `EnhancedSecretLoader.__init__`
- **scripts\fetch_secrets_to_env.py:23** - `_get_project_id`
- **scripts\dev_launcher_secrets.py:22** - `EnhancedSecretLoader.__init__`

---

## Subcategory: name {subcategory-name}

**Count**: 316 literals

### 🔴 Low (<0.5) (316 literals)

| Literal | Files | Context | Related |
|---------|-------|---------|---------|
| `
   Fetching ` | dev_launcher_secrets.py:87 | EnhancedSecretLoader._fetch... | `def `, `class ` |
| `
  Running ` | deploy_to_gcp.py:175 | GCPDeployer.run_pre_deploym... | `def `, `class ` |
| `
Checking ` | build_staging.py:184 | StagingBuilder.health_check | `def `, `class ` |
| `
Checking ` | fast_import_checker.py:66 | fix_known_import_issues | `def `, `class ` |
| `
Checking ` | fast_import_checker.py:112 | fix_known_import_issues | `def `, `class ` |
| `
Checking ` | fast_import_checker.py:153 | fix_known_import_issues | `def `, `class ` |
| `
Checking ` | fast_import_checker.py:203 | fix_known_import_issues | `def `, `class ` |
| `
Created ` | split_learnings.py:139 | main | `def `, `class ` |
| `
Creating ` | fast_import_checker.py:264 | fix_known_import_issues | `def `, `class ` |
| `
Exported ` | analyze_mocks.py:283 | MockAnalyzer.export_unjusti... | `def `, `class ` |
| `
Fixed ` | aggressive_syntax_fix.py:211 | main | `def `, `class ` |
| `
Fixed ` | final_syntax_fix.py:115 | main | `def `, `class ` |
| `
Fixed ` | fix_all_connection_manager_imports.py:76 | main | `def `, `class ` |
| `
Fixed ` | fix_all_e2e_imports.py:119 | main | `def `, `class ` |
| `
Fixed ` | fix_double_modern.py:46 | main | `def `, `class ` |
| `
Fixed ` | fix_frontend_tests.py:148 | main | `def `, `class ` |
| `
Fixed ` | fix_import_indents.py:90 | main | `def `, `class ` |
| `
Fixed ` | fix_remaining_e2e_imports.py:89 | main | `def `, `class ` |
| `
Fixed ` | fix_remaining_imports.py:93 | main | `def `, `class ` |
| `
Fixed ` | fix_simple_import_errors.py:110 | main | `def `, `class ` |
| `
Found ` | merge_results.py:112 | handle_coverage_files | `def `, `class ` |
| `
Found ` | find_top_mocks.py:109 | main | `def `, `class ` |
| `
Found ` | decompose_functions.py:175 | main | `def `, `class ` |
| `
Found ` | fix_supervisor_imports.py:94 | main | `def `, `class ` |
| `
Found ` | force_cancel_workflow.py:92 | _display_stuck_runs_summary | `def `, `class ` |
| `
Modified ` | fix_all_import_issues.py:284 | main | `def `, `class ` |
| `
Processed ` | fix_remaining_syntax_errors.py:221 | main | `def `, `class ` |
| `
Running ` | import_management.py:123 | ImportManagementSystem.fix_... | `def `, `class ` |
| `
Scanning ` | comprehensive_import_scanner.py:573 | ComprehensiveImportScanner.... | `def `, `class ` |
| `
Split ` | split_large_files.py:241 | _get_user_confirmations | `def `, `class ` |
| `
Testing ` | verify_startup_fix.py:90 | main | `def `, `class ` |
| `
Validation ` | validate_agent_tests.py:367 | main | `def `, `class ` |
| `     Line ` | enforce_limits.py:178 | EnforcementReporter.generat... | `def `, `class ` |
| `    def ` | aggressive_syntax_fix.py:62 | aggressive_fix | `def `, `class ` |
| `    Line ` | auth_constants_migration.py:316 | AuthConstantsMigrator.gener... | `def `, `class ` |
| `    Line ` | check_netra_backend_imports.py:256 | ImportAnalyzer.generate_report | `def `, `class ` |
| `  Analyzed ` | check_netra_backend_imports.py:328 | main | `def `, `class ` |
| `  Analyzed ` | check_netra_backend_imports.py:333 | main | `def `, `class ` |
| `  Attempt ` | build_staging.py:197 | StagingBuilder.health_check | `def `, `class ` |
| `  Checking ` | deploy_to_gcp.py:619 | GCPDeployer.health_check | `def `, `class ` |
| `  Deleting ` | deploy_to_gcp.py:718 | GCPDeployer.cleanup | `def `, `class ` |
| `  Fixed ` | fix_embedded_setup_imports.py:163 | EmbeddedSetupImportFixer.pr... | `def `, `class ` |
| `  Fixed ` | fix_malformed_imports.py:205 | MalformedImportFixer.proces... | `def `, `class ` |
| `  Found ` | code_review_analysis.py:52 | CodeReviewAnalysis._analyze... | `def `, `class ` |
| `  Found ` | fix_netra_backend_imports.py:269 | main | `def `, `class ` |
| `  Found ` | fix_netra_backend_imports.py:275 | main | `def `, `class ` |
| `  Found ` | git_analyzer.py:34 | GitAnalyzer._analyze_recent... | `def `, `class ` |
| `  Line ` | check_schema_imports.py:362 | SchemaImportAnalyzer.genera... | `def `, `class ` |
| `  Line ` | deduplicate_types.py:239 | TypeDeduplicator.preview_ch... | `def `, `class ` |
| `  Line ` | fix_imports.py:186 | ImportFixer.fix_file | `def `, `class ` |
| `  Line ` | fix_netra_domain.py:35 | fix_domain_in_file | `def `, `class ` |
| `  Merged ` | fix_schema_imports.py:104 | SchemaImportFixer._move_sch... | `def `, `class ` |
| `  Skipping ` | fix_embedded_setup_imports.py:143 | EmbeddedSetupImportFixer.pr... | `def `, `class ` |
| `  Skipping ` | fix_malformed_imports.py:185 | MalformedImportFixer.proces... | `def `, `class ` |
| `  Updated ` | fix_missing_functions.py:120 | main | `def `, `class ` |
| ` and ` | check_imports.py:289 | ImportAnalyzer.generate_report | `def `, `class ` |
| ` AREA

` | function_complexity_analyzer.py:252 | FunctionComplexityAnalyzer.... | `def `, `class ` |
| ` attempts` | dev_launcher_monitoring.py:23 | wait_for_service | `def `, `class ` |
| ` characters` | schema_sync.py:124 | validate_typescript_output | `def `, `class ` |
| ` configuration` | environment_validator_database.py:222 | DatabaseValidator._add_data... | `def `, `class ` |
| ` credentials` | environment_validator_database.py:220 | DatabaseValidator._add_data... | `def `, `class ` |
| ` detected` | emergency_boundary_actions.py:465 | main | `def `, `class ` |
| ` environment` | validate_network_constants.py:235 | main | `def `, `class ` |
| ` failed` | deploy_to_gcp.py:188 | GCPDeployer.run_pre_deploym... | `def `, `class ` |
| ` files` | aggressive_syntax_fix.py:211 | main | `def `, `class ` |
| ` files` | auth_constants_migration.py:303 | AuthConstantsMigrator.gener... | `def `, `class ` |
| ` files` | check_netra_backend_imports.py:328 | main | `def `, `class ` |
| ` files` | check_netra_backend_imports.py:333 | main | `def `, `class ` |
| ` files` | code_review_ai_detector.py:73 | CodeReviewAIDetector._check... | `def `, `class ` |
| ` files` | core.py:134 | ViolationBuilder.duplicate_... | `def `, `class ` |
| ` files` | reporter.py:248 | ComplianceReporter._print_c... | `def `, `class ` |
| ` files` | reporter_stats.py:55 | StatisticsCalculator.displa... | `def `, `class ` |
| ` files` | ssot_checker.py:71 | SSOTChecker._check_duplicat... | `def `, `class ` |
| ` files` | create_agent_fix_tasks.py:56 | create_agent_tasks | `def `, `class ` |
| ` files` | create_enforcement_tools.py:244 | EnforcementEngine.find_dupl... | `def `, `class ` |
| ` files` | deduplicate_types.py:421 | main | `def `, `class ` |
| ` files` | extract_function_violations.py:101 | main | `def `, `class ` |
| ` files` | final_syntax_fix.py:115 | main | `def `, `class ` |
| ` files` | fix_all_connection_manager_imports.py:76 | main | `def `, `class ` |
| ` files` | fix_all_e2e_imports.py:119 | main | `def `, `class ` |
| ` files` | fix_all_import_issues.py:284 | main | `def `, `class ` |
| ` files` | fix_double_modern.py:46 | main | `def `, `class ` |
| ` files` | fix_import_indents.py:90 | main | `def `, `class ` |
| ` files` | fix_remaining_e2e_imports.py:89 | main | `def `, `class ` |
| ` files` | fix_remaining_imports.py:93 | main | `def `, `class ` |
| ` files` | fix_remaining_syntax_errors.py:221 | main | `def `, `class ` |
| ` files` | fix_schema_imports.py:171 | SchemaImportFixer.fix_all_i... | `def `, `class ` |
| ` FILES` | fix_schema_imports.py:244 | SchemaImportFixer.generate_... | `def `, `class ` |
| ` files` | fix_simple_import_errors.py:110 | main | `def `, `class ` |
| ` files` | fix_supervisor_imports.py:103 | main | `def `, `class ` |
| ` files` | ai_detector.py:74 | AIDetector._report_duplicates | `def `, `class ` |
| ` fixes` | fix_netra_backend_imports.py:189 | ImportFixer.generate_report | `def `, `class ` |
| ` found` | dependency_services.py:79 | check_redis_installation | `def `, `class ` |
| ` found` | env_checker.py:133 | check_node_version | `def `, `class ` |
| ` found` | env_checker.py:154 | get_git_version | `def `, `class ` |
| ` from ` | cleanup_workflow_runs.py:258 | _clean_workflow_runs | `def `, `class ` |
| ` functions` | auto_decompose_functions.py:471 | main | `def `, `class ` |
| ` functions` | code_review_ai_detector.py:99 | CodeReviewAIDetector._check... | `def `, `class ` |
| ` functions
` | function_complexity_analyzer.py:236 | FunctionComplexityAnalyzer.... | `def `, `class ` |
| ` import` | check_netra_backend_imports.py:146 | ImportAnalyzer._check_import | `def `, `class ` |
| ` import` | fix_all_import_issues.py:75 | ComprehensiveImportFixer._b... | `def `, `class ` |
| ` import ` | auth_constants_migration.py:258 | AuthConstantsMigrator._extr... | `def `, `class ` |
| ` import ` | auth_constants_migration.py:259 | AuthConstantsMigrator._extr... | `def `, `class ` |
| ` import ` | check_schema_imports.py:232 | SchemaImportAnalyzer._check... | `def `, `class ` |
| ` import ` | e2e_import_fixer_comprehensive.py:184 | E2EImportFixer.analyze_file | `def `, `class ` |
| ` import ` | e2e_import_fixer_comprehensive.py:253 | E2EImportFixer._check_impor... | `def `, `class ` |
| ` import ` | e2e_import_fixer_comprehensive.py:264 | E2EImportFixer._check_impor... | `def `, `class ` |
| ` import ` | e2e_import_fixer_comprehensive.py:294 | E2EImportFixer._check_impor... | `def `, `class ` |
| ` import ` | e2e_import_fixer_comprehensive.py:347 | E2EImportFixer._suggest_fix... | `def `, `class ` |
| ` import ` | e2e_import_fixer_comprehensive.py:351 | E2EImportFixer._suggest_fix... | `def `, `class ` |
| ` import ` | fix_all_import_syntax.py:22 | fix_import_syntax_patterns | `def `, `class ` |
| ` import ` | fix_all_import_syntax.py:54 | fix_import_syntax_patterns | `def `, `class ` |
| ` import ` | fix_all_import_syntax.py:63 | fix_import_syntax_patterns | `def `, `class ` |
| ` import ` | fix_imports.py:145 | ImportFixer.fix_file | `def `, `class ` |
| ` import ` | fix_import_syntax_errors.py:36 | fix_import_syntax_in_file | `def `, `class ` |
| ` import ` | fix_schema_imports.py:198 | SchemaImportFixer.update_in... | `def `, `class ` |
| ` instances` | code_review_ai_detector.py:85 | CodeReviewAIDetector._check... | `def `, `class ` |
| ` instances` | reporter_stats.py:62 | StatisticsCalculator.displa... | `def `, `class ` |
| ` instances` | ai_detector.py:89 | AIDetector._check_typescrip... | `def `, `class ` |
| ` interfaces` | schema_sync.py:125 | validate_typescript_output | `def `, `class ` |
| ` invalid` | workflow_validator.py:120 | WorkflowValidator._validate... | `def `, `class ` |
| ` learnings` | split_learnings_robust.py:141 | main | `def `, `class ` |
| ` LIMIT` | boundary_enforcer_system_checks.py:182 | ViolationFactory.create_com... | `def `, `class ` |
| ` lines` | analyze_critical_paths.py:76 | module | `def `, `class ` |
| ` lines` | check_function_lengths.py:62 | module | `def `, `class ` |
| ` lines` | decompose_functions.py:160 | generate_report | `def `, `class ` |
| ` lines` | extract_function_violations.py:108 | main | `def `, `class ` |
| ` lines` | find_long_functions.py:53 | scan_directory | `def `, `class ` |
| ` lines` | function_complexity_linter.py:215 | FunctionComplexityLinter._p... | `def `, `class ` |
| ` literals` | query_string_literals.py:206 | main | `def `, `class ` |
| ` literals` | markdown_reporter.py:343 | MarkdownReporter._generate_... | `def `, `class ` |
| ` literals` | markdown_reporter.py:355 | MarkdownReporter._generate_... | `def `, `class ` |
| ` Literals` | markdown_reporter.py:407 | MarkdownReporter._generate_... | `def `, `class ` |
| ` literals` | markdown_reporter.py:452 | MarkdownReporter._generate_... | `def `, `class ` |
| ` locations` | query_string_literals.py:176 | main | `def `, `class ` |
| ` methods` | auto_split_files.py:162 | FileSplitter._suggest_class... | `def `, `class ` |
| ` mocks` | find_top_mocks.py:147 | main | `def `, `class ` |
| ` mode` | unified_import_manager.py:633 | main | `def `, `class ` |
| ` modules` | core.py:111 | ViolationBuilder.file_size_... | `def `, `class ` |
| ` modules` | split_large_files.py:251 | _handle_file_splitting | `def `, `class ` |
| ` more` | audit_permissions.py:81 | main | `def `, `class ` |
| ` more` | check_imports.py:292 | ImportAnalyzer.generate_report | `def `, `class ` |
| ` more` | check_imports.py:304 | ImportAnalyzer.generate_report | `def `, `class ` |
| ` more` | e2e_import_fixer_comprehensive.py:534 | E2EImportFixer.print_report | `def `, `class ` |
| ` more` | e2e_import_fixer_comprehensive.py:595 | main | `def `, `class ` |
| ` more` | fix_netra_backend_imports.py:199 | ImportFixer.generate_report | `def `, `class ` |
| ` more` | fix_remaining_syntax_errors.py:236 | main | `def `, `class ` |
| ` more` | query_string_literals.py:159 | main | `def `, `class ` |
| ` more` | query_string_literals.py:195 | main | `def `, `class ` |
| ` more` | unified_import_manager.py:537 | UnifiedImportManager.print_... | `def `, `class ` |
| ` more` | unified_import_manager.py:544 | UnifiedImportManager.print_... | `def `, `class ` |
| ` more` | validate_type_deduplication.py:296 | TypeDeduplicationValidator.... | `def `, `class ` |
| ` more` | validate_type_deduplication.py:308 | TypeDeduplicationValidator.... | `def `, `class ` |
| ` more ` | generate_security_report.py:135 | _get_overflow_text | `def `, `class ` |
| ` occurrences` | check_netra_backend_imports.py:244 | ImportAnalyzer.generate_report | `def `, `class ` |
| ` occurrences` | e2e_import_fixer_comprehensive.py:514 | E2EImportFixer.print_report | `def `, `class ` |
| ` passed` | deploy_to_gcp.py:186 | GCPDeployer.run_pre_deploym... | `def `, `class ` |
| ` schemas` | schema_sync.py:84 | print_sync_results | `def `, `class ` |
| ` seconds` | code_review_ai_detector.py:30 | CodeReviewAIDetector.run_co... | `def `, `class ` |
| ` seconds` | code_review_analysis.py:33 | CodeReviewAnalysis.run_command | `def `, `class ` |
| ` seconds` | command_runner.py:29 | CommandRunner.run | `def `, `class ` |
| ` secrets` | create_staging_secrets.py:168 | _print_summary | `def `, `class ` |
| ` service` | environment_validator_database.py:218 | DatabaseValidator._add_data... | `def `, `class ` |
| ` specs` | team_updates_sync.py:103 | generate_simple_report | `def `, `class ` |
| ` successful` | config_setup_scripts.py:164 | verify_module_imports | `def `, `class ` |
| ` times` | analyze_mocks.py:256 | MockAnalyzer.print_summary | `def `, `class ` |
| ` times` | find_top_mocks.py:129 | main | `def `, `class ` |
| ` types` | reporter_stats.py:60 | StatisticsCalculator.displa... | `def `, `class ` |
| ` violations` | boundary_enforcer_report_generator.py:134 | ConsoleReportPrinter._print... | `def `, `class ` |
| ` violations` | validate_type_deduplication.py:374 | main | `def `, `class ` |
| ` with ` | auto_split_files.py:162 | FileSplitter._suggest_class... | `def `, `class ` |
| `Action ` | emergency_boundary_actions.py:309 | EmergencyActionSystem._exec... | `def `, `class ` |
| `Address ` | architecture_scanner_quality.py:105 | QualityScanner._find_debt_p... | `def `, `class ` |
| `Analyzing ` | check_imports.py:379 | main | `def `, `class ` |
| `Analyzing ` | e2e_import_fixer_comprehensive.py:414 | E2EImportFixer.run_comprehe... | `def `, `class ` |
| `Basic ` | generate_openapi_spec.py:150 | create_readme_headers | `def `, `class ` |
| `Basic ` | generate_openapi_spec.py:184 | upload_spec_to_readme | `def `, `class ` |
| `Built ` | fix_all_import_issues.py:133 | ComprehensiveImportFixer._b... | `def `, `class ` |
| `Check ` | environment_validator_database.py:220 | DatabaseValidator._add_data... | `def `, `class ` |
| `Checking ` | fix_remaining_syntax_errors.py:193 | main | `def `, `class ` |
| `class ` | aggressive_syntax_fix.py:52 | aggressive_fix | `def `, `    def ` |
| `class ` | aggressive_syntax_fix.py:66 | aggressive_fix | `def `, `    def ` |
| `class ` | aggressive_syntax_fix.py:80 | aggressive_fix | `def `, `    def ` |
| `class ` | aggressive_syntax_fix.py:119 | aggressive_fix | `def `, `    def ` |
| `Class ` | auto_split_files.py:162 | FileSplitter._suggest_class... | `def `, `class ` |
| `class ` | boundary_enforcer_file_checks.py:103 | ASTAnalyzer.extract_ast_nodes | `def `, `    def ` |
| `class ` | fix_all_import_syntax.py:40 | fix_import_syntax_patterns | `def `, `    def ` |
| `class ` | fix_import_syntax_errors.py:47 | fix_import_syntax_in_file | `def `, `    def ` |
| `class ` | fix_schema_imports.py:90 | SchemaImportFixer._move_sch... | `def `, `    def ` |
| `Cleaned ` | cleanup_workflow_runs.py:293 | _clean_local_items | `def `, `class ` |
| `Consolidate ` | architecture_scanner.py:172 | ArchitectureScanner._filter... | `def `, `class ` |
| `Creating ` | fix_schema_imports.py:180 | SchemaImportFixer.update_in... | `def `, `class ` |
| `Creating ` | seed_staging_data.py:87 | StagingDataSeeder.seed_users | `def `, `class ` |
| `Creating ` | seed_staging_data.py:155 | StagingDataSeeder.seed_thre... | `def `, `class ` |
| `def ` | aggressive_syntax_fix.py:50 | aggressive_fix | `class `, `    def ` |
| `def ` | aggressive_syntax_fix.py:118 | aggressive_fix | `class `, `    def ` |
| `def ` | fix_all_import_syntax.py:41 | fix_import_syntax_patterns | `class `, `    def ` |
| `def ` | fix_import_syntax_errors.py:48 | fix_import_syntax_in_file | `class `, `    def ` |
| `def ` | fix_missing_functions.py:92 | add_missing_functions | `class `, `    def ` |
| `Executed ` | emergency_boundary_actions.py:454 | main | `def `, `class ` |
| `Fetching ` | fetch_secrets_to_env.py:70 | _fetch_all_secrets | `def `, `class ` |
| `File ` | auto_split_files.py:383 | main | `def `, `class ` |
| `Fix ` | e2e_import_fixer_comprehensive.py:458 | E2EImportFixer.generate_report | `def `, `class ` |
| `Fixed ` | e2e_import_fixer_comprehensive.py:397 | E2EImportFixer.fix_file | `def `, `class ` |
| `Fixed ` | fix_all_import_issues.py:156 | ComprehensiveImportFixer.fi... | `def `, `class ` |
| `Fixed ` | fix_e2e_connection_manager_imports.py:129 | main | `def `, `class ` |
| `Fixed ` | fix_imports.py:190 | ImportFixer.fix_file | `def `, `class ` |
| `Fixed ` | fix_monitoring_violations.py:71 | fix_alert_manager_core | `def `, `class ` |
| `Fixed ` | fix_monitoring_violations.py:111 | fix_alert_notifications | `def `, `class ` |
| `Fixed ` | fix_netra_backend_imports.py:139 | ImportFixer.fix_directory | `def `, `class ` |
| `Fixed ` | fix_workflow_env_issues.py:110 | main | `def `, `class ` |
| `for ` | decompose_functions.py:127 | suggest_decomposition | `def `, `class ` |
| `Found ` | aggressive_syntax_fix.py:179 | main | `def `, `class ` |
| `Found ` | check_e2e_imports.py:197 | E2EImportChecker.check_all | `def `, `class ` |
| `Found ` | check_schema_imports.py:116 | SchemaImportAnalyzer._build... | `def `, `class ` |
| `Found ` | merge_results.py:28 | find_result_files | `def `, `class ` |
| `Found ` | cleanup_workflow_runs.py:251 | _clean_workflow_runs | `def `, `class ` |
| `Found ` | cleanup_workflow_runs.py:268 | _clean_artifacts | `def `, `class ` |
| `Found ` | clean_slate_executor.py:90 | CleanSlateExecutor.phase1_a... | `def `, `class ` |
| `Found ` | code_review_ai_detector.py:84 | CodeReviewAIDetector._check... | `def `, `class ` |
| `Found ` | code_review_ai_detector.py:98 | CodeReviewAIDetector._check... | `def `, `class ` |
| `Found ` | code_review_ai_detector.py:129 | CodeReviewAIDetector._check... | `def `, `class ` |
| `Found ` | code_review_ai_detector.py:138 | CodeReviewAIDetector._check... | `def `, `class ` |
| `Found ` | analyze_mocks.py:207 | MockAnalyzer.analyze_all | `def `, `class ` |
| `Found ` | create_enforcement_tools.py:327 | EnforcementEngine.run_all_c... | `def `, `class ` |
| `Found ` | decompose_functions.py:139 | generate_report | `def `, `class ` |
| `Found ` | env_checker.py:202 | check_required_files | `def `, `class ` |
| `Found ` | extract_function_violations.py:100 | main | `def `, `class ` |
| `Found ` | final_syntax_fix.py:88 | main | `def `, `class ` |
| `Found ` | fix_all_connection_manager_imports.py:68 | main | `def `, `class ` |
| `Found ` | fix_all_import_issues.py:172 | ComprehensiveImportFixer.fi... | `def `, `class ` |
| `Found ` | fix_e2e_connection_manager_imports.py:116 | main | `def `, `class ` |
| `Found ` | fix_embedded_setup_imports.py:187 | EmbeddedSetupImportFixer.pr... | `def `, `class ` |
| `Found ` | fix_frontend_tests.py:141 | main | `def `, `class ` |
| `Found ` | fix_malformed_imports.py:229 | MalformedImportFixer.proces... | `def `, `class ` |
| `Found ` | fix_remaining_syntax_errors.py:202 | main | `def `, `class ` |
| `Found ` | fix_testcontainers_imports.py:120 | main | `def `, `class ` |
| `Found ` | query_string_literals.py:153 | main | `def `, `class ` |
| `Found ` | ai_detector.py:88 | AIDetector._check_typescrip... | `def `, `class ` |
| `Found ` | ai_detector.py:112 | AIDetector._check_bare_exce... | `def `, `class ` |
| `Found ` | split_learnings_robust.py:141 | main | `def `, `class ` |
| `Found ` | update_spec_timestamps.py:212 | main | `def `, `class ` |
| `Found ` | validate_agent_tests.py:339 | main | `def `, `class ` |
| `from ` | aggressive_syntax_fix.py:121 | aggressive_fix | `def `, `class ` |
| `from ` | auth_constants_migration.py:225 | AuthConstantsMigrator.migra... | `def `, `class ` |
| `from ` | check_netra_backend_imports.py:94 | ImportAnalyzer.analyze_file | `def `, `class ` |
| `from ` | check_netra_backend_imports.py:106 | ImportAnalyzer.analyze_file | `def `, `class ` |
| `from ` | check_netra_backend_imports.py:146 | ImportAnalyzer._check_import | `def `, `class ` |
| `from ` | check_schema_imports.py:232 | SchemaImportAnalyzer._check... | `def `, `class ` |
| `from ` | e2e_import_fixer_comprehensive.py:184 | E2EImportFixer.analyze_file | `def `, `class ` |
| `from ` | e2e_import_fixer_comprehensive.py:253 | E2EImportFixer._check_impor... | `def `, `class ` |
| `from ` | e2e_import_fixer_comprehensive.py:264 | E2EImportFixer._check_impor... | `def `, `class ` |
| `from ` | e2e_import_fixer_comprehensive.py:294 | E2EImportFixer._check_impor... | `def `, `class ` |
| `from ` | e2e_import_fixer_comprehensive.py:347 | E2EImportFixer._suggest_fix... | `def `, `class ` |
| `from ` | e2e_import_fixer_comprehensive.py:351 | E2EImportFixer._suggest_fix... | `def `, `class ` |
| `from ` | fix_all_import_syntax.py:22 | fix_import_syntax_patterns | `def `, `class ` |
| `from ` | fix_all_import_syntax.py:38 | fix_import_syntax_patterns | `def `, `class ` |
| `from ` | fix_e2e_imports.py:120 | E2EImportFixer.fix_file | `def `, `class ` |
| `from ` | fix_e2e_imports.py:135 | E2EImportFixer.fix_file | `def `, `class ` |
| `from ` | fix_e2e_imports.py:215 | E2EImportFixer.cleanup_content | `def `, `class ` |
| `from ` | fix_imports.py:138 | ImportFixer.fix_file | `def `, `class ` |
| `from ` | fix_imports.py:145 | ImportFixer.fix_file | `def `, `class ` |
| `from ` | fix_imports.py:216 | ImportFixer.fix_duplicate_i... | `def `, `class ` |
| `from ` | fix_import_syntax_errors.py:36 | fix_import_syntax_in_file | `def `, `class ` |
| `from ` | fix_import_syntax_errors.py:44 | fix_import_syntax_in_file | `def `, `class ` |
| `from ` | fix_missing_functions.py:51 | add_missing_imports | `def `, `class ` |
| `from ` | fix_missing_functions.py:81 | add_missing_functions | `def `, `class ` |
| `function ` | boundary_enforcer_file_checks.py:105 | ASTAnalyzer.extract_ast_nodes | `def `, `class ` |
| `Git ` | env_checker.py:154 | get_git_version | `def `, `class ` |
| `import ` | aggressive_syntax_fix.py:120 | aggressive_fix | `def `, `class ` |
| `import ` | auth_constants_migration.py:224 | AuthConstantsMigrator.migra... | `def `, `class ` |
| `import ` | check_netra_backend_imports.py:81 | ImportAnalyzer.analyze_file | `def `, `class ` |
| `import ` | config_setup_scripts.py:157 | verify_module_imports | `def `, `class ` |
| `import ` | e2e_import_fixer_comprehensive.py:213 | E2EImportFixer._check_import | `def `, `class ` |
| `import ` | e2e_import_fixer_comprehensive.py:214 | E2EImportFixer._check_import | `def `, `class ` |
| `import ` | e2e_import_fixer_comprehensive.py:219 | E2EImportFixer._check_import | `def `, `class ` |
| `import ` | e2e_import_fixer_comprehensive.py:233 | E2EImportFixer._check_import | `def `, `class ` |
| `import ` | e2e_import_fixer_comprehensive.py:243 | E2EImportFixer._check_import | `def `, `class ` |
| `import ` | fix_all_import_syntax.py:39 | fix_import_syntax_patterns | `def `, `class ` |
| `import ` | fix_comprehensive_imports.py:103 | ComprehensiveImportFixerV2.... | `def `, `class ` |
| `import ` | fix_e2e_imports.py:120 | E2EImportFixer.fix_file | `def `, `class ` |
| `import ` | fix_e2e_imports.py:135 | E2EImportFixer.fix_file | `def `, `class ` |
| `import ` | fix_e2e_imports.py:215 | E2EImportFixer.cleanup_content | `def `, `class ` |
| `import ` | fix_imports.py:216 | ImportFixer.fix_duplicate_i... | `def `, `class ` |
| `import ` | fix_import_syntax_errors.py:45 | fix_import_syntax_in_file | `def `, `class ` |
| `import ` | fix_missing_functions.py:51 | add_missing_imports | `def `, `class ` |
| `import ` | fix_missing_functions.py:81 | add_missing_functions | `def `, `class ` |
| `Installed ` | dependency_installer.py:121 | install_package_list | `def `, `class ` |
| `interface ` | auto_split_files.py:100 | FileSplitter._analyze_types... | `def `, `class ` |
| `Line ` | e2e_import_fixer_comprehensive.py:389 | E2EImportFixer.fix_file | `def `, `class ` |
| `Loaded ` | generate_string_literals_docs.py:102 | main | `def `, `class ` |
| `Migrated ` | auth_constants_migration.py:246 | AuthConstantsMigrator.migra... | `def `, `class ` |
| `Missing ` | env_checker.py:204 | check_required_files | `def `, `class ` |
| `Moved ` | fix_schema_imports.py:109 | SchemaImportFixer._move_sch... | `def `, `class ` |
| `Parsing ` | split_learnings.py:125 | main | `def `, `class ` |
| `Part ` | auto_decompose_functions.py:340 | FunctionDecomposer._suggest... | `def `, `class ` |
| `Port ` | environment_validator_ports.py:203 | PortValidator._add_port_rec... | `def `, `class ` |
| `Processing ` | fix_imports.py:253 | ImportFixer.fix_directory | `def `, `class ` |
| `python ` | fix_e2e_tests_comprehensive.py:387 | main | `def `, `class ` |
| `Reading ` | split_learnings_robust.py:134 | main | `def `, `class ` |
| `Redis ` | dependency_services.py:79 | check_redis_installation | `def `, `class ` |
| `Removed ` | fix_imports.py:230 | ImportFixer.fix_duplicate_i... | `def `, `class ` |
| `Scanning ` | auth_constants_migration.py:269 | AuthConstantsMigrator.check... | `def `, `class ` |
| `Scanning ` | fix_all_import_issues.py:197 | ComprehensiveImportFixer.fi... | `def `, `class ` |
| `Scanning ` | scan_string_literals.py:309 | main | `def `, `class ` |
| `Skipping ` | reset_clickhouse_auto.py:72 | _check_password_requirements | `def `, `class ` |
| `Skipping ` | reset_clickhouse_auto.py:135 | reset_clickhouse_instance | `def `, `class ` |
| `Spec ` | code_review_analysis.py:127 | CodeReviewAnalysis._check_k... | `def `, `class ` |
| `Spec ` | spec_checker.py:60 | SpecChecker._validate_imple... | `def `, `class ` |
| `Start ` | environment_validator_database.py:218 | DatabaseValidator._add_data... | `def `, `class ` |
| `Task ` | create_agent_fix_tasks.py:56 | create_agent_tasks | `def `, `class ` |
| `Tests ` | aggressive_syntax_fix.py:102 | aggressive_fix | `def `, `class ` |
| `token ` | force_cancel_workflow.py:15 | get_workflow_runs | `def `, `class ` |
| `token ` | force_cancel_workflow.py:32 | force_cancel_workflow | `def `, `class ` |
| `Verify ` | environment_validator_database.py:222 | DatabaseValidator._add_data... | `def `, `class ` |
| `while ` | decompose_functions.py:127 | suggest_decomposition | `def `, `class ` |

### Usage Examples

- **scripts\dev_launcher_secrets.py:87** - `EnhancedSecretLoader._fetch_all_secrets`
- **scripts\deploy_to_gcp.py:175** - `GCPDeployer.run_pre_deployment_checks`
- **scripts\build_staging.py:184** - `StagingBuilder.health_check`

---

## 🔗 Navigation

- 🏠 [Back to Main Index](../string_literals_index.md)
- 📂 [Browse Other Categories](./)

---

*This is the detailed documentation for the `identifiers` category.*
*For the complete system overview, see the [Main String Literals Index](../string_literals_index.md).*