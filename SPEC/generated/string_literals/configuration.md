# ⚙️ Configuration Literals

System configuration keys, environment variables, and settings

*Generated on 2025-08-21 21:55:53*

## 📊 Category Statistics

| Metric | Value |
|--------|-------|
| Total Literals | 3,546 |
| Subcategories | 5 |
| Average Confidence | 0.900 |

## 📋 Subcategories

- [config_key (17 literals)](#subcategory-config-key)
- [config_name (2 literals)](#subcategory-config-name)
- [config_param (1 literals)](#subcategory-config-param)
- [config_value (461 literals)](#subcategory-config-value)
- [env_var (3065 literals)](#subcategory-env-var)

## Subcategory: config_key {subcategory-config-key}

**Count**: 17 literals

### 🟢 High (≥0.8) (17 literals)

| Literal | Files | Context | Related |
|---------|-------|---------|---------|
| `   export TEST\_ANTHROPIC\_API\_KEY=y...` | demo_real_llm_testing.py:226 | demo_cli_usage | `   export TEST_...`, `AuthConstants.... |
| `   export TEST\_OPENAI\_API\_KEY=your...` | demo_real_llm_testing.py:225 | demo_cli_usage | `   export TEST_...`, `AuthConstants.... |
| `AuthConstants\.AUTH\_SERVICE\_URL` | auth_constants_migration.py:79 | AuthConstantsMigrator.__init__ | `   export TEST_...`, `   export TEST... |
| `AuthConstants\.SERVICE\_SECRET` | auth_constants_migration.py:82 | AuthConstantsMigrator.__init__ | `   export TEST_...`, `   export TEST... |
| `CredentialConstants\.API\_KEY` | auth_constants_migration.py:65 | AuthConstantsMigrator.__init__ | `   export TEST_...`, `   export TEST... |
| `CredentialConstants\.DATABASE\_URL` | auth_constants_migration.py:66 | AuthConstantsMigrator.__init__ | `   export TEST_...`, `   export TEST... |
| `CredentialConstants\.GEMINI\_API\_KEY` | auth_constants_migration.py:64 | AuthConstantsMigrator.__init__ | `   export TEST_...`, `   export TEST... |
| `CredentialConstants\.GOOGLE\_CLIENT\_...` | auth_constants_migration.py:63 | AuthConstantsMigrator.__init__ | `   export TEST_...`, `   export TEST... |
| `dev\_launcher\.launcher\.get\_free\_port` | test_launcher_health.py:227 | TestErrorRecovery._test_por... | `   export TEST_...`, `   export TEST... |
| `dev\_launcher\.utils\.get\_free\_port` | test_default_launcher.py:209 | TestPortAllocationImproveme... | `   export TEST_...`, `   export TEST... |
| `JWTConstants\.ACCESS\_TOKEN` | auth_constants_migration.py:37 | AuthConstantsMigrator.__init__ | `   export TEST_...`, `   export TEST... |
| `JWTConstants\.FERNET\_KEY` | auth_constants_migration.py:36 | AuthConstantsMigrator.__init__ | `   export TEST_...`, `   export TEST... |
| `JWTConstants\.JWT\_SECRET\_KEY` | auth_constants_migration.py:35 | AuthConstantsMigrator.__init__ | `   export TEST_...`, `   export TEST... |
| `JWTConstants\.REFRESH\_TOKEN` | auth_constants_migration.py:38 | AuthConstantsMigrator.__init__ | `   export TEST_...`, `   export TEST... |
| `Loading DATABASE\_URL` | filter_patterns.py:97 | module | `   export TEST_...`, `   export TEST... |
| `OAuthConstants\.CLIENT\_SECRET` | auth_constants_migration.py:72 | AuthConstantsMigrator.__init__ | `   export TEST_...`, `   export TEST... |
| `OAuthConstants\.REDIRECT\_URI` | auth_constants_migration.py:73 | AuthConstantsMigrator.__init__ | `   export TEST_...`, `   export TEST... |

### Usage Examples

- **scripts\demo_real_llm_testing.py:226** - `demo_cli_usage`
- **scripts\demo_real_llm_testing.py:225** - `demo_cli_usage`
- **scripts\auth_constants_migration.py:79** - `AuthConstantsMigrator.__init__`

---

## Subcategory: config_name {subcategory-config-name}

**Count**: 2 literals

### 🟢 High (≥0.8) (2 literals)

| Literal | Files | Context | Related |
|---------|-------|---------|---------|
| `dev\_launcher\.launcher\.load\_or\_cr...` | test_launcher_health.py:213 | TestErrorRecovery.test_port... | `dev_launcher.se...`, `
   Configurin... |
| `dev\_launcher\.service\_config\.load\...` | test_launcher.py:268 | TestDevLauncher.test_check_... | `dev_launcher.la...`, `
   Configurin... |

### Usage Examples

- **dev_launcher\tests\test_launcher_health.py:213** - `TestErrorRecovery.test_port_conflict_recovery`
- **dev_launcher\tests\test_launcher.py:268** - `TestDevLauncher.test_check_environment_success`

---

## Subcategory: config_param {subcategory-config-param}

**Count**: 1 literals

### 🟢 High (≥0.8) (1 literals)

| Literal | Files | Context | Related |
|---------|-------|---------|---------|
| `DEFAULT\_TEST\_PATHS\\s\*=\\s\*\\\[\[...` | align_test_imports.py:330 | TestImportAligner.fix_test_... | `
   Configuring...`, `
  Authenticat... |

### Usage Examples

- **scripts\align_test_imports.py:330** - `TestImportAligner.fix_test_discovery_paths`

---

## Subcategory: config_value {subcategory-config-value}

**Count**: 461 literals

### 🟢 High (≥0.8) (461 literals)

| Literal | Files | Context | Related |
|---------|-------|---------|---------|
| `
   Configuring local ` | service_config.py:469 | ServiceConfigWizard._custom... | `
  Authenticati...`, `
  Database:` |
| `
  Authentication:` | test_config_loading.py:93 | _check_auth_configurations | `
   Configuring...`, `
  Database:` |
| `
  Database:` | test_config_loading.py:115 | _check_database_configuration | `
   Configuring...`, `
  Authenticat... |
| `
  Environment: ` | test_staging_config.py:99 | _check_environment_config | `
   Configuring...`, `
  Authenticat... |
| `
  LLM Configurations:` | test_config_loading.py:79 | _check_llm_configurations | `
   Configuring...`, `
  Authenticat... |
| `
  OAuth Configuration:` | test_config_loading.py:105 | _check_oauth_configuration | `
   Configuring...`, `
  Authenticat... |
| `
\[CONFIG\] Configuration:` | dev_launcher_monitoring.py:145 | print_configuration_summary | `
   Configuring...`, `
  Authenticat... |
| `
\[COST CONTROL\]:` | workflow_config_utils.py:44 | WorkflowConfigUtils._show_c... | `
   Configuring...`, `
  Authenticat... |
| `
\[CRITICAL\] Configuration Status:` | test_config_loading.py:70 | _check_all_configurations | `
   Configuring...`, `
  Authenticat... |
| `
\[FEATURES\]:` | workflow_config_utils.py:26 | WorkflowConfigUtils._show_f... | `
   Configuring...`, `
  Authenticat... |
| `
\[TEST HIERARCHY\]:` | workflow_config_utils.py:52 | WorkflowConfigUtils._show_t... | `
   Configuring...`, `
  Authenticat... |
| `
\[WORKFLOWS\]:` | workflow_config_utils.py:35 | WorkflowConfigUtils._show_w... | `
   Configuring...`, `
  Authenticat... |
| `
Configuration file: ` | __main__.py:369 | handle_service_configuration | `
   Configuring...`, `
  Authenticat... |
| `
Expected Endpoints:` | verify_auth_config.py:59 | verify_environment_config | `
   Configuring...`, `
  Authenticat... |
| `
Expected Redirect URIs:` | verify_auth_config.py:64 | verify_environment_config | `
   Configuring...`, `
  Authenticat... |
| `
JWT\_ALGORITHM=HS256
JWT\_EXPIRATION...` | config_setup_core.py:178 | get_env_security_config | `
   Configuring...`, `
  Authenticat... |
| `
OAuth Configuration:` | verify_auth_config.py:69 | verify_environment_config | `
   Configuring...`, `
  Authenticat... |
| `
⚠️  Configuration warnings:` | service_config.py:421 | ServiceConfigWizard.run | `
   Configuring...`, `
  Authenticat... |
| `
📦 ` | service_config.py:436 | ServiceConfigWizard._config... | `
   Configuring...`, `
  Authenticat... |
| `
🔧 OAuth Configuration:` | monitor_oauth_flow.py:43 | OAuthMonitor.check_oauth_co... | `
   Configuring...`, `
  Authenticat... |
| `  ` | workflow_config_utils.py:30 | WorkflowConfigUtils._show_f... | `
   Configuring...`, `
  Authenticat... |
| `    ` | test_config_loading.py:89 | _check_single_llm_config | `
   Configuring...`, `
  Authenticat... |
| `     ` | service_config.py:476 | ServiceConfigWizard._custom... | `
   Configuring...`, `
  Authenticat... |
| `                       ` | __main__.py:401 | handle_service_configuration | `
   Configuring...`, `
  Authenticat... |
| `            project\_root=find\_proje...` | enhance_dev_launcher_boundaries.py:35 | enhance_launcher_config | `
   Configuring...`, `
  Authenticat... |
| `       Invalid value, keeping ` | service_config.py:486 | ServiceConfigWizard._custom... | `
   Configuring...`, `
  Authenticat... |
| `     \- ` | demo_real_llm_testing.py:118 | demo_real_llm_configuration | `
   Configuring...`, `
  Authenticat... |
| `     ❌ Configuration error: ` | test_example_message_flow.py:244 | ExampleMessageFlowTestRunne... | `
   Configuring...`, `
  Authenticat... |
| `    \[OK\] ` | test_staging_startup.py:121 | StagingStartupTester.test_c... | `
   Configuring...`, `
  Authenticat... |
| `    Blocks: ` | workflow_config_utils.py:61 | WorkflowConfigUtils._show_t... | `
   Configuring...`, `
  Authenticat... |
| `    Client ID: ` | test_config_loading.py:106 | _check_oauth_configuration | `
   Configuring...`, `
  Authenticat... |
| `    Client Secret: ` | test_config_loading.py:107 | _check_oauth_configuration | `
   Configuring...`, `
  Authenticat... |
| `    Depends on: ` | workflow_config_utils.py:59 | WorkflowConfigUtils._show_t... | `
   Configuring...`, `
  Authenticat... |
| `    Fernet Key: ` | test_config_loading.py:97 | _check_auth_configurations | `
   Configuring...`, `
  Authenticat... |
| `    Fernet Key: MISSING` | test_staging_config.py:140 | _check_fernet_config | `
   Configuring...`, `
  Authenticat... |
| `    JWT Secret: ` | test_config_loading.py:96 | _check_auth_configurations | `
   Configuring...`, `
  Authenticat... |
| `    JWT Secret: MISSING` | test_staging_config.py:131 | _check_jwt_config | `
   Configuring...`, `
  Authenticat... |
| `    URL: ` | test_config_loading.py:116 | _check_database_configuration | `
   Configuring...`, `
  Authenticat... |
| `   \* Dynamic ports: ` | dev_launcher_monitoring.py:146 | print_configuration_summary | `
   Configuring...`, `
  Authenticat... |
| `   \* Secret loading: ` | dev_launcher_monitoring.py:152 | print_configuration_summary | `
   Configuring...`, `
  Authenticat... |
| `   \* Turbopack: ` | dev_launcher_monitoring.py:151 | print_configuration_summary | `
   Configuring...`, `
  Authenticat... |
| `   API key status:` | demo_real_llm_testing.py:121 | demo_real_llm_configuration | `
   Configuring...`, `
  Authenticat... |
| `   Available models:` | demo_real_llm_testing.py:116 | demo_real_llm_configuration | `
   Configuring...`, `
  Authenticat... |
| `   Choice \[1\-4, default=1\]: ` | service_config.py:447 | ServiceConfigWizard._config... | `
   Configuring...`, `
  Authenticat... |
| `   Cost budget: $` | demo_real_llm_testing.py:112 | demo_real_llm_configuration | `
   Configuring...`, `
  Authenticat... |
| `   Customize local ` | service_config.py:463 | ServiceConfigWizard._config... | `
   Configuring...`, `
  Authenticat... |
| `   Enabled: ` | demo_real_llm_testing.py:110 | demo_real_llm_configuration | `
   Configuring...`, `
  Authenticat... |
| `   Options:` | service_config.py:440 | ServiceConfigWizard._config... | `
   Configuring...`, `
  Authenticat... |
| `   Rate limit: ` | demo_real_llm_testing.py:113 | demo_real_llm_configuration | `
   Configuring...`, `
  Authenticat... |
| `   Recommended: ` | service_config.py:437 | ServiceConfigWizard._config... | `
   Configuring...`, `
  Authenticat... |
| `   Testing mode: ` | demo_real_llm_testing.py:111 | demo_real_llm_configuration | `
   Configuring...`, `
  Authenticat... |
| `  \- ` | verify_auth_config.py:61 | verify_environment_config | `
   Configuring...`, `
  Authenticat... |
| `  \[OK\] Test level: ` | verify_staging_tests.py:96 | verify_test_runner_config | `
   Configuring...`, `
  Authenticat... |
| `  \[SIMULATE\] Checking configuration...` | test_staging_startup.py:119 | StagingStartupTester.test_c... | `
   Configuring...`, `
  Authenticat... |
| `  Auth Service URL: ` | config.py:125 | AuthConfig.log_configuration | `
   Configuring...`, `
  Authenticat... |
| `  Callback: ` | monitor_oauth_flow.py:50 | OAuthMonitor.check_oauth_co... | `
   Configuring...`, `
  Authenticat... |
| `  Category: ` | test_backend.py:366 | _print_test_config_details | `
   Configuring...`, `
  Authenticat... |
| `  ClickHouse: ` | config.py:282 | LauncherConfig._log_clickho... | `
   Configuring...`, `
  Authenticat... |
| `  Client ID: ` | monitor_oauth_flow.py:49 | OAuthMonitor.check_oauth_co... | `
   Configuring...`, `
  Authenticat... |
| `  Coverage: ` | test_backend.py:368 | _print_test_config_details | `
   Configuring...`, `
  Authenticat... |
| `  Daily limit: $` | workflow_config_utils.py:46 | WorkflowConfigUtils._show_c... | `
   Configuring...`, `
  Authenticat... |
| `  Database URL: ` | config.py:138 | AuthConfig.log_configuration | `
   Configuring...`, `
  Authenticat... |
| `  Environment: ` | config.py:123 | AuthConfig.log_configuration | `
   Configuring...`, `
  Authenticat... |
| `  Fail Fast: ` | test_backend.py:369 | _print_test_config_details | `
   Configuring...`, `
  Authenticat... |
| `  Frontend URL: ` | config.py:124 | AuthConfig.log_configuration | `
   Configuring...`, `
  Authenticat... |
| `  Google Client ID: ` | config.py:126 | AuthConfig.log_configuration | `
   Configuring...`, `
  Authenticat... |
| `  Google Client Secret: ` | config.py:127 | AuthConfig.log_configuration | `
   Configuring...`, `
  Authenticat... |
| `  JWT Secret: ` | config.py:128 | AuthConfig.log_configuration | `
   Configuring...`, `
  Authenticat... |
| `  LLM: ` | config.py:292 | LauncherConfig._log_llm_config | `
   Configuring...`, `
  Authenticat... |
| `  Monthly budget: $` | workflow_config_utils.py:47 | WorkflowConfigUtils._show_c... | `
   Configuring...`, `
  Authenticat... |
| `  Parallel: ` | test_backend.py:367 | _print_test_config_details | `
   Configuring...`, `
  Authenticat... |
| `  PostgreSQL: ` | config.py:287 | LauncherConfig._log_postgre... | `
   Configuring...`, `
  Authenticat... |
| `  Redirect URIs: ` | monitor_oauth_flow.py:51 | OAuthMonitor.check_oauth_co... | `
   Configuring...`, `
  Authenticat... |
| `  Redis: ` | config.py:277 | LauncherConfig._log_redis_c... | `
   Configuring...`, `
  Authenticat... |
| `  • ` | config.py:348 | LauncherConfig._print_servi... | `
   Configuring...`, `
  Authenticat... |
| `  • Dynamic ports: ` | config.py:369 | LauncherConfig._print_dynam... | `
   Configuring...`, `
  Authenticat... |
| `  • Secret loading: ` | config.py:396 | LauncherConfig._print_secre... | `
   Configuring...`, `
  Authenticat... |
| `  • Turbopack: ` | config.py:392 | LauncherConfig._print_turbo... | `
   Configuring...`, `
  Authenticat... |
| `  • Verbose output: ` | config.py:400 | LauncherConfig._print_verbo... | `
   Configuring...`, `
  Authenticat... |
| `  ✅ ` | config.py:431 | LauncherConfig._show_env_fi... | `
   Configuring...`, `
  Authenticat... |
| `  ❌ ` | config.py:433 | LauncherConfig._show_env_fi... | `
   Configuring...`, `
  Authenticat... |
| ` \(` | workflow_config_utils.py:39 | WorkflowConfigUtils._show_w... | `
   Configuring...`, `
  Authenticat... |
| ` \($` | demo_real_llm_testing.py:118 | demo_real_llm_configuration | `
   Configuring...`, `
  Authenticat... |
| ` \(not found\)` | config.py:433 | LauncherConfig._show_env_fi... | `
   Configuring...`, `
  Authenticat... |
| ` \- ` | config.py:431 | LauncherConfig._show_env_fi... | `
   Configuring...`, `
  Authenticat... |
| ` : ` | __main__.py:394 | handle_service_configuration | `
   Configuring...`, `
  Authenticat... |
| ` <\-> ` | workflow_config_utils.py:82 | WorkflowConfigUtils._check_... | `
   Configuring...`, `
  Authenticat... |
| ` = ` | coverage_config.py:91 | CoverageConfig.create_cover... | `
   Configuring...`, `
  Authenticat... |
| ` = <not set>` | config.py:456 | LauncherConfig._show_env_va... | `
   Configuring...`, `
  Authenticat... |
| ` \[` | service_config.py:476 | ServiceConfigWizard._custom... | `
   Configuring...`, `
  Authenticat... |
| ` and ` | config.py:102 | LauncherConfig._validate | `
   Configuring...`, `
  Authenticat... |
| ` bytes\)` | config.py:431 | LauncherConfig._show_env_fi... | `
   Configuring...`, `
  Authenticat... |
| ` calls/minute` | demo_real_llm_testing.py:113 | demo_real_llm_configuration | `
   Configuring...`, `
  Authenticat... |
| ` Current Service Configuration` | __main__.py:367 | handle_service_configuration | `
   Configuring...`, `
  Authenticat... |
| ` days old` | config_validator.py:106 | ServiceConfigValidator._che... | `
   Configuring...`, `
  Authenticat... |
| ` Environment` | verify_auth_config.py:47 | verify_environment_config | `
   Configuring...`, `
  Authenticat... |
| ` environment` | environment_validator.py:380 | EnvironmentValidator.valida... | `
   Configuring...`, `
  Authenticat... |
| ` for '` | service_config.py:498 | ServiceConfigWizard._ask_ye... | `
   Configuring...`, `
  Authenticat... |
| ` modules` | schema_sync.py:65 | print_configuration | `
   Configuring...`, `
  Authenticat... |
| ` optimization requests\.\.\.` | seed_staging_data.py:205 | StagingDataSeeder._get_opti... | `
   Configuring...`, `
  Authenticat... |
| ` Service configuration updated` | __main__.py:362 | handle_service_configuration | `
   Configuring...`, `
  Authenticat... |
| ` settings?` | service_config.py:463 | ServiceConfigWizard._config... | `
   Configuring...`, `
  Authenticat... |
| ` Using recommended configuration:` | service_config.py:380 | ServiceConfigWizard.run | `
   Configuring...`, `
  Authenticat... |
| `"staging"` | verify_staging_tests.py:88 | verify_test_runner_config | `
   Configuring...`, `
  Authenticat... |
| `"staging\-quick"` | verify_staging_tests.py:89 | verify_test_runner_config | `
   Configuring...`, `
  Authenticat... |
| `"use\_turbopack": self\.use\_turbopack,` | enhance_dev_launcher_boundaries.py:44 | enhance_launcher_config | `
   Configuring...`, `
  Authenticat... |
| `\# Security
SECRET\_KEY=dev\-secret\-...` | config_setup_core.py:177 | get_env_security_config | `
   Configuring...`, `
  Authenticat... |
| `\*\*\*` | config.py:461 | LauncherConfig._mask_env_va... | `
   Configuring...`, `
  Authenticat... |
| `\*\*/agents/\*\*` | config_manager.py:37 | ConfigurationManager._get_f... | `
   Configuring...`, `
  Authenticat... |
| `\*\*/auth/\*\*` | config_manager.py:36 | ConfigurationManager._get_f... | `
   Configuring...`, `
  Authenticat... |
| `\*\*/docs/\*\*` | config_manager.py:38 | ConfigurationManager._get_f... | `
   Configuring...`, `
  Authenticat... |
| `\*\*/payment/\*\*` | config_manager.py:36 | ConfigurationManager._get_f... | `
   Configuring...`, `
  Authenticat... |
| `\*\*/routes/\*\*` | config_manager.py:37 | ConfigurationManager._get_f... | `
   Configuring...`, `
  Authenticat... |
| `\*\*/scripts/\*\*` | config_manager.py:38 | ConfigurationManager._get_f... | `
   Configuring...`, `
  Authenticat... |
| `\*\*/security/\*\*` | config_manager.py:36 | ConfigurationManager._get_f... | `
   Configuring...`, `
  Authenticat... |
| `\*\*/services/\*\*` | config_manager.py:37 | ConfigurationManager._get_f... | `
   Configuring...`, `
  Authenticat... |
| `\*\*/supervisor\*` | config_manager.py:36 | ConfigurationManager._get_f... | `
   Configuring...`, `
  Authenticat... |
| `\*\*/tests/\*\*` | config_manager.py:38 | ConfigurationManager._get_f... | `
   Configuring...`, `
  Authenticat... |
| `\*\.egg\-info` | core.py:88 | ComplianceConfig._get_skip_... | `
   Configuring...`, `
  Authenticat... |
| `\*/\.pytest\_cache/\*` | coverage_config.py:202 | AuthServiceCoverageConfig._... | `
   Configuring...`, `
  Authenticat... |
| `\*/\.venv/\*` | coverage_config.py:25 | CoverageConfig | `
   Configuring...`, `
  Authenticat... |
| `\*/\_\_pycache\_\_/\*` | coverage_config.py:23 | CoverageConfig | `
   Configuring...`, `
  Authenticat... |
| `\*/alembic/\*` | coverage_config.py:201 | AuthServiceCoverageConfig._... | `
   Configuring...`, `
  Authenticat... |
| `\*/migrations/\*` | coverage_config.py:24 | CoverageConfig | `
   Configuring...`, `
  Authenticat... |
| `\*/test\_\*` | coverage_config.py:22 | CoverageConfig | `
   Configuring...`, `
  Authenticat... |
| `\*/tests/\*` | coverage_config.py:21 | CoverageConfig | `
   Configuring...`, `
  Authenticat... |
| `\*/venv/\*` | coverage_config.py:26 | CoverageConfig | `
   Configuring...`, `
  Authenticat... |
| `, ` | coverage_config.py:93 | CoverageConfig.create_cover... | `
   Configuring...`, `
  Authenticat... |
| `\-\-api\-url` | build_staging.py:264 | _add_configuration_arguments | `
   Configuring...`, `
  Authenticat... |
| `\-\-check\-file\-boundaries` | boundary_enforcer_cli_handler.py:32 | CLIArgumentParser._configur... | `
   Configuring...`, `
  Authenticat... |
| `\-\-check\-function\-boundaries` | boundary_enforcer_cli_handler.py:33 | CLIArgumentParser._configur... | `
   Configuring...`, `
  Authenticat... |
| `\-\-config\-file` | cleanup_staging_environments.py:418 | _add_config_arguments | `
   Configuring...`, `
  Authenticat... |
| `\-\-cov\-branch` | coverage_config.py:111 | CoverageConfig.get_pytest_c... | `
   Configuring...`, `
  Authenticat... |
| `\-\-cov\-fail\-under=` | coverage_config.py:107 | CoverageConfig.get_pytest_c... | `
   Configuring...`, `
  Authenticat... |
| `\-\-cov\-report=html:` | coverage_config.py:117 | CoverageConfig.get_pytest_c... | `
   Configuring...`, `
  Authenticat... |
| `\-\-cov\-report=json:` | coverage_config.py:123 | CoverageConfig.get_pytest_c... | `
   Configuring...`, `
  Authenticat... |
| `\-\-cov\-report=term\-missing` | coverage_config.py:114 | CoverageConfig.get_pytest_c... | `
   Configuring...`, `
  Authenticat... |
| `\-\-cov\-report=xml:` | coverage_config.py:120 | CoverageConfig.get_pytest_c... | `
   Configuring...`, `
  Authenticat... |
| `\-\-cov=` | coverage_config.py:106 | CoverageConfig.get_pytest_c... | `
   Configuring...`, `
  Authenticat... |
| `\-\-enforce` | boundary_enforcer_cli_handler.py:31 | CLIArgumentParser._configur... | `
   Configuring...`, `
  Authenticat... |
| `\-\-fail\-on\-critical` | boundary_enforcer_cli_handler.py:34 | CLIArgumentParser._configur... | `
   Configuring...`, `
  Authenticat... |
| `\-\-fail\-on\-emergency` | boundary_enforcer_cli_handler.py:35 | CLIArgumentParser._configur... | `
   Configuring...`, `
  Authenticat... |
| `\-\-output` | cleanup_staging_environments.py:419 | _add_config_arguments | `
   Configuring...`, `
  Authenticat... |
| `\-\-project\-id` | staging_error_monitor.py:246 | load_config_from_args | `
   Configuring...`, `
  Authenticat... |
| `\-\-service` | staging_error_monitor.py:248 | load_config_from_args | `
   Configuring...`, `
  Authenticat... |
| `\-\-tag` | build_staging.py:263 | _add_configuration_arguments | `
   Configuring...`, `
  Authenticat... |
| `\-\-target\-coverage` | main.py:59 | _add_configuration_arguments | `
   Configuring...`, `
  Authenticat... |
| `\-\-version` | service_config.py:283 | ServicesConfiguration._chec... | `
   Configuring...`, `
  Authenticat... |
| `\-c` | test_backend.py:194 | _add_config_file_args | `
   Configuring...`, `
  Authenticat... |
| `\. Review configuration\.` | recovery_actions.py:216 | RecoveryActions.handle_conf... | `
   Configuring...`, `
  Authenticat... |
| `\.\*` | system_diagnostics.py:236 | SystemDiagnostics._find_con... | `
   Configuring...`, `
  Authenticat... |
| `\.\.\.` | monitor_oauth_flow.py:49 | OAuthMonitor.check_oauth_co... | `
   Configuring...`, `
  Authenticat... |
| `\.\.\.\)` | config.py:341 | LauncherConfig._print_servi... | `
   Configuring...`, `
  Authenticat... |
| `\.4f` | demo_real_llm_testing.py:118 | demo_real_llm_configuration | `
   Configuring...`, `
  Authenticat... |
| `\.act\.secrets` | setup_act.py:66 | create_config_files | `
   Configuring...`, `
  Authenticat... |
| `\.config` | system_diagnostics.py:237 | SystemDiagnostics._find_con... | `
   Configuring...`, `
  Authenticat... |
| `\.coverage` | core.py:89 | ComplianceConfig._get_skip_... | `
   Configuring...`, `
  Authenticat... |
| `\.coveragerc` | coverage_config.py:82 | CoverageConfig.create_cover... | `
   Configuring...`, `
  Authenticat... |
| `\.eggs` | core.py:88 | ComplianceConfig._get_skip_... | `
   Configuring...`, `
  Authenticat... |
| `\.env\*` | system_diagnostics.py:240 | SystemDiagnostics._find_con... | `
   Configuring...`, `
  Authenticat... |
| `\.env\.development` | config.py:422 | LauncherConfig._get_env_fil... | `
   Configuring...`, `
  Authenticat... |
| `\.env\.development\.local` | config.py:423 | LauncherConfig._get_env_fil... | `
   Configuring...`, `
  Authenticat... |
| `\.env\.test` | test_backend.py:63 | _setup_dotenv_test_config | `
   Configuring...`, `
  Authenticat... |
| `\.git` | core.py:84 | ComplianceConfig._get_skip_... | `
   Configuring...`, `
  Authenticat... |
| `\.gitignore` | setup_act.py:95 | create_config_files | `
   Configuring...`, `
  Authenticat... |
| `\.idea` | core.py:88 | ComplianceConfig._get_skip_... | `
   Configuring...`, `
  Authenticat... |
| `\.local\_secrets` | setup_act.py:99 | create_config_files | `
   Configuring...`, `
  Authenticat... |
| `\.netra/crash\_reports` | crash_recovery_models.py:107 | MonitoringConfig | `
   Configuring...`, `
  Authenticat... |
| `\.nox` | core.py:89 | ComplianceConfig._get_skip_... | `
   Configuring...`, `
  Authenticat... |
| `\.pytest\_cache` | core.py:85 | ComplianceConfig._get_skip_... | `
   Configuring...`, `
  Authenticat... |
| `\.secrets\.key` | setup_act.py:100 | create_config_files | `
   Configuring...`, `
  Authenticat... |
| `\.spec\.` | core.py:96 | ComplianceConfig.is_test_file | `
   Configuring...`, `
  Authenticat... |
| `\.terraform` | core.py:91 | ComplianceConfig._get_skip_... | `
   Configuring...`, `
  Authenticat... |
| `\.test\.` | core.py:96 | ComplianceConfig.is_test_file | `
   Configuring...`, `
  Authenticat... |
| `\.tox` | core.py:89 | ComplianceConfig._get_skip_... | `
   Configuring...`, `
  Authenticat... |
| `\.venv` | core.py:85 | ComplianceConfig._get_skip_... | `
   Configuring...`, `
  Authenticat... |
| `\.vs` | core.py:88 | ComplianceConfig._get_skip_... | `
   Configuring...`, `
  Authenticat... |
| `\.vscode` | core.py:88 | ComplianceConfig._get_skip_... | `
   Configuring...`, `
  Authenticat... |
| `/\*\*/\*\.ts` | core.py:56 | ComplianceConfig.get_patterns | `
   Configuring...`, `
  Authenticat... |
| `/\*\*/\*\.tsx` | core.py:56 | ComplianceConfig.get_patterns | `
   Configuring...`, `
  Authenticat... |
| `/1k tokens\)` | demo_real_llm_testing.py:118 | demo_real_llm_configuration | `
   Configuring...`, `
  Authenticat... |
| `/auth/callback` | auth_routes.py:72 | get_auth_config | `
   Configuring...`, `
  Authenticat... |
| `/auth/config` | test_oauth_flows_auth.py:28 | TestSyntaxFix.test_google_o... | `
   Configuring...`, `
  Authenticat... |
| `/auth/dev/login` | auth_routes.py:75 | get_auth_config | `
   Configuring...`, `
  Authenticat... |
| `/auth/health` | auth_routes.py:78 | get_auth_config | `
   Configuring...`, `
  Authenticat... |
| `/auth/login` | auth_routes.py:70 | get_auth_config | `
   Configuring...`, `
  Authenticat... |
| `/auth/logout` | auth_routes.py:71 | get_auth_config | `
   Configuring...`, `
  Authenticat... |
| `/auth/refresh` | auth_routes.py:77 | get_auth_config | `
   Configuring...`, `
  Authenticat... |
| `/auth/token` | auth_routes.py:73 | get_auth_config | `
   Configuring...`, `
  Authenticat... |
| `/auth/validate` | auth_routes.py:76 | get_auth_config | `
   Configuring...`, `
  Authenticat... |
| `/auth/verify` | auth_routes.py:74 | get_auth_config | `
   Configuring...`, `
  Authenticat... |
| `/config` | auth_routes.py:60 | get_auth_config | `
   Configuring...`, `
  Authenticat... |
| `/day, $` | validate_workflow_config.py:201 | _print_config_details | `
   Configuring...`, `
  Authenticat... |
| `/health` | validate_staging_health.py:243 | StagingSecurityValidator._c... | `
   Configuring...`, `
  Authenticat... |
| `/month` | validate_workflow_config.py:202 | _print_config_details | `
   Configuring...`, `
  Authenticat... |
| `/postgres` | test_config.py:121 | PostgresTestConfig.create_t... | `
   Configuring...`, `
  Authenticat... |
| `/test/` | core.py:96 | ComplianceConfig.is_test_file | `
   Configuring...`, `
  Authenticat... |
| `/tests/` | core.py:96 | ComplianceConfig.is_test_file | `
   Configuring...`, `
  Authenticat... |
| `/tmp/act\-artifacts/` | setup_act.py:102 | create_config_files | `
   Configuring...`, `
  Authenticat... |
| `1\.0` | config_manager.py:76 | ConfigurationManager._creat... | `
   Configuring...`, `
  Authenticat... |
| `12` | config.py:346 | LauncherConfig._print_servi... | `
   Configuring...`, `
  Authenticat... |
| `127\.0\.0\.1` | service_config.py:241 | ServicesConfiguration._add_... | `
   Configuring...`, `
  Authenticat... |
| `15` | config.py:48 | AuthConfig.get_jwt_access_e... | `
   Configuring...`, `
  Authenticat... |
| `2\.0` | test_websocket_dev_mode.py:98 | WebSocketDevModeTest.test_c... | `
   Configuring...`, `
  Authenticat... |
| `24` | config.py:110 | AuthConfig.get_session_ttl_... | `
   Configuring...`, `
  Authenticat... |
| `25` | config.py:431 | LauncherConfig._show_env_fi... | `
   Configuring...`, `
  Authenticat... |
| `30` | config.py:454 | LauncherConfig._show_env_va... | `
   Configuring...`, `
  Authenticat... |
| `46YQC0J~6SfZ\.` | service_config.py:102 | ServicesConfiguration | `
   Configuring...`, `
  Authenticat... |
| `512Mi` | deploy_to_gcp.py:42 | ServiceConfig | `
   Configuring...`, `
  Authenticat... |
| `5432` | test_config.py:105 | PostgresTestConfig.__init__ | `
   Configuring...`, `
  Authenticat... |
| `6379` | secret_config.py:52 | SecretConfig.get_static_def... | `
   Configuring...`, `
  Authenticat... |
| `8123` | service_config.py:93 | ServicesConfiguration | `
   Configuring...`, `
  Authenticat... |
| `8443` | dev_launcher_secrets.py:164 | EnhancedSecretLoader._get_s... | `
   Configuring...`, `
  Authenticat... |
| `9000` | secret_config.py:54 | SecretConfig.get_static_def... | `
   Configuring...`, `
  Authenticat... |
| `: ` | demo_real_llm_testing.py:118 | demo_real_llm_configuration | `
   Configuring...`, `
  Authenticat... |
| `://` | config.py:134 | AuthConfig.log_configuration | `
   Configuring...`, `
  Authenticat... |
| `://\*\*\*@` | config.py:138 | AuthConfig.log_configuration | `
   Configuring...`, `
  Authenticat... |
| `\[DISABLED\]` | workflow_config_utils.py:38 | WorkflowConfigUtils._show_w... | `
   Configuring...`, `
  Authenticat... |
| `\[ENABLED\]` | workflow_config_utils.py:38 | WorkflowConfigUtils._show_w... | `
   Configuring...`, `
  Authenticat... |
| `\[green\]Created \.act\.env template\...` | setup_act.py:92 | create_config_files | `
   Configuring...`, `
  Authenticat... |
| `\[green\]Created \.act\.secrets templ...` | setup_act.py:78 | create_config_files | `
   Configuring...`, `
  Authenticat... |
| `\[green\]Updated \.gitignore\[/green\]` | setup_act.py:115 | create_config_files | `
   Configuring...`, `
  Authenticat... |
| `\[OFF\]` | workflow_config_utils.py:29 | WorkflowConfigUtils._show_f... | `
   Configuring...`, `
  Authenticat... |
| `\[OK\] Configuration created: ` | verify_startup_fix.py:51 | test_config_creation | `
   Configuring...`, `
  Authenticat... |
| `\[OK\] GCP Project: ` | validate_staging_config.py:357 | check_gcp_configuration | `
   Configuring...`, `
  Authenticat... |
| `\[ON\]` | workflow_config_utils.py:29 | WorkflowConfigUtils._show_f... | `
   Configuring...`, `
  Authenticat... |
| `\[SUCCESS\] Applied preset: ` | manage_workflows.py:158 | WorkflowManager._apply_pres... | `
   Configuring...`, `
  Authenticat... |
| `\]: ` | service_config.py:476 | ServiceConfigWizard._custom... | `
   Configuring...`, `
  Authenticat... |
| `\_test\.` | core.py:96 | ComplianceConfig.is_test_file | `
   Configuring...`, `
  Authenticat... |
| `Access token duration: ` | test_auth_token_generation.py:265 | TestJWTTokenGeneration.test... | `
   Configuring...`, `
  Authenticat... |
| `Access\-Control\-Allow\-Origin` | validate_staging_health.py:244 | StagingSecurityValidator._c... | `
   Configuring...`, `
  Authenticat... |
| `access\-control\-allow\-origin` | test_auth_integration.py:117 | AuthServiceTester.test_cors... | `
   Configuring...`, `
  Authenticat... |
| `Access\-Control\-Request\-Method` | test_auth_integration.py:109 | AuthServiceTester.test_cors... | `
   Configuring...`, `
  Authenticat... |
| `act\-results/` | setup_act.py:101 | create_config_files | `
   Configuring...`, `
  Authenticat... |
| `Add configuration arguments` | main.py:57 | _add_configuration_arguments | `
   Configuring...`, `
  Authenticat... |
| `ai\-focus` | core.py:77 | ReviewConfig.should_run_smo... | `
   Configuring...`, `
  Authenticat... |
| `ai\-issues` | core.py:97 | ReviewConfig.is_ai_focused | `
   Configuring...`, `
  Authenticat... |
| `API key configured` | test_config_loading.py:88 | _check_single_llm_config | `
   Configuring...`, `
  Authenticat... |
| `API Keys` | secret_config.py:64 | SecretConfig.get_secret_cat... | `
   Configuring...`, `
  Authenticat... |
| `app\.config` | test_staging_config.py:84 | _clear_config_cache | `
   Configuring...`, `
  Authenticat... |
| `Auth Service` | __main__.py:376 | handle_service_configuration | `
   Configuring...`, `
  Authenticat... |
| `Auth service configuration` | auth_models.py:94 | AuthConfig | `
   Configuring...`, `
  Authenticat... |
| `Auth Service Configuration:` | config.py:122 | AuthConfig.log_configuration | `
   Configuring...`, `
  Authenticat... |
| `Auth Service URL: ` | verify_auth_config.py:49 | verify_environment_config | `
   Configuring...`, `
  Authenticat... |
| `auth\.netrasystems\.ai` | service_config.py:157 | ServicesConfiguration | `
   Configuring...`, `
  Authenticat... |
| `auth\.staging` | monitor_oauth_flow.py:54 | OAuthMonitor.check_oauth_co... | `
   Configuring...`, `
  Authenticat... |
| `auth\_core/\*` | coverage_config.py:19 | CoverageConfig | `
   Configuring...`, `
  Authenticat... |
| `auth\_core/\*/test\_\*` | coverage_config.py:200 | AuthServiceCoverageConfig._... | `
   Configuring...`, `
  Authenticat... |
| `auth\_core/core` | coverage_config.py:181 | AuthServiceCoverageConfig._... | `
   Configuring...`, `
  Authenticat... |
| `auth\_core/database` | coverage_config.py:184 | AuthServiceCoverageConfig._... | `
   Configuring...`, `
  Authenticat... |
| `auth\_core/routes` | coverage_config.py:183 | AuthServiceCoverageConfig._... | `
   Configuring...`, `
  Authenticat... |
| `auth\_core/services` | coverage_config.py:182 | AuthServiceCoverageConfig._... | `
   Configuring...`, `
  Authenticat... |
| `auth\_core/tests/\*` | coverage_config.py:199 | AuthServiceCoverageConfig._... | `
   Configuring...`, `
  Authenticat... |
| `Backend modules: ` | schema_sync.py:65 | print_configuration | `
   Configuring...`, `
  Authenticat... |
| `Base configuration` | config.py:421 | LauncherConfig._get_env_fil... | `
   Configuring...`, `
  Authenticat... |
| `Capture configuration snapshot` | diagnostic_helpers.py:124 | get_configuration | `
   Configuring...`, `
  Authenticat... |
| `Check authentication configurations` | test_config_loading.py:92 | _check_auth_configurations | `
   Configuring...`, `
  Authenticat... |
| `Check CORS configuration\.` | validate_staging_health.py:240 | StagingSecurityValidator._c... | `
   Configuring...`, `
  Authenticat... |
| `Check database configuration` | test_config_loading.py:110 | _check_database_configuration | `
   Configuring...`, `
  Authenticat... |
| `Check environment configuration` | test_staging_config.py:97 | _check_environment_config | `
   Configuring...`, `
  Authenticat... |
| `Check JWT configuration` | test_staging_config.py:125 | _check_jwt_config | `
   Configuring...`, `
  Authenticat... |
| `Check LLM configurations` | test_config_loading.py:77 | _check_llm_configurations | `
   Configuring...`, `
  Authenticat... |
| `Check OAuth configuration` | test_config_loading.py:100 | _check_oauth_configuration | `
   Configuring...`, `
  Authenticat... |
| `Check skipped` | validate_staging_health.py:249 | StagingSecurityValidator._c... | `
   Configuring...`, `
  Authenticat... |
| `Checking ` | verify_auth_config.py:47 | verify_environment_config | `
   Configuring...`, `
  Authenticat... |
| `Circular dependency: ` | workflow_config_utils.py:82 | WorkflowConfigUtils._check_... | `
   Configuring...`, `
  Authenticat... |
| `Cleanup database connections` | test_config.py:60 | TestDatabaseConfig.cleanup | `
   Configuring...`, `
  Authenticat... |
| `clickhouse\+https` | service_config.py:198 | ServicesConfiguration._add_... | `
   Configuring...`, `
  Authenticat... |
| `clickhouse\-client` | service_config.py:292 | ServicesConfiguration._chec... | `
   Configuring...`, `
  Authenticat... |
| `clickhouse://` | service_config.py:202 | ServicesConfiguration._add_... | `
   Configuring...`, `
  Authenticat... |
| `Cloud/shared resource` | __main__.py:389 | handle_service_configuration | `
   Configuring...`, `
  Authenticat... |
| `Complete services configuration\.` | service_config.py:67 | ServicesConfiguration | `
   Configuring...`, `
  Authenticat... |
| `Config endpoint returned ` | test_websocket_dev_mode.py:107 | WebSocketDevModeTest.test_c... | `
   Configuring...`, `
  Authenticat... |
| `Config file missing: ` | recovery_actions.py:214 | RecoveryActions.handle_conf... | `
   Configuring...`, `
  Authenticat... |
| `Config is old` | test_config_validator.py:40 | TestConfigValidationResult.... | `
   Configuring...`, `
  Authenticat... |
| `Config issue: ` | recovery_actions.py:216 | RecoveryActions.handle_conf... | `
   Configuring...`, `
  Authenticat... |
| `config\.\*` | system_diagnostics.py:239 | SystemDiagnostics._find_con... | `
   Configuring...`, `
  Authenticat... |
| `config/` | system_diagnostics.py:236 | SystemDiagnostics._find_con... | `
   Configuring...`, `
  Authenticat... |
| `Configuration file \(JSON\)` | cleanup_staging_environments.py:418 | _add_config_arguments | `
   Configuring...`, `
  Authenticat... |
| `Configuration is ` | config_validator.py:106 | ServiceConfigValidator._che... | `
   Configuring...`, `
  Authenticat... |
| `Configuration loaded from ` | service_config.py:350 | ServicesConfiguration.load_... | `
   Configuring...`, `
  Authenticat... |
| `Configuration notice: ` | service_config.py:522 | load_or_create_config | `
   Configuring...`, `
  Authenticat... |
| `Configuration saved to ` | manage_precommit.py:31 | save_config | `
   Configuring...`, `
  Authenticat... |
| `Configuration setup` | install_dev_env.py:117 | DevEnvironmentInstaller.run... | `
   Configuring...`, `
  Authenticat... |
| `Configuration validation failed: ` | test_example_message_flow.py:245 | ExampleMessageFlowTestRunne... | `
   Configuring...`, `
  Authenticat... |
| `Configuration validation status\.` | config_validator.py:30 | ConfigStatus | `
   Configuring...`, `
  Authenticat... |
| `Configuration:` | config.py:296 | LauncherConfig.show_configu... | `
   Configuring...`, `
  Authenticat... |
| `CORS Configuration` | test_auth_integration.py:118 | AuthServiceTester.test_cors... | `
   Configuring...`, `
  Authenticat... |
| `CORS test failed: ` | test_auth_integration.py:123 | AuthServiceTester.test_cors... | `
   Configuring...`, `
  Authenticat... |
| `Cost Budget: $` | validate_workflow_config.py:201 | _print_config_details | `
   Configuring...`, `
  Authenticat... |
| `cpmdn7pVpsJSK2mb7lUTj2VaQhSC1L3S` | service_config.py:81 | ServicesConfiguration | `
   Configuring...`, `
  Authenticat... |
| `CREATE DATABASE "` | test_config.py:133 | PostgresTestConfig.create_t... | `
   Configuring...`, `
  Authenticat... |
| `Create decision engine\.` | test_config_validator.py:116 | TestConfigDecisionEngine.en... | `
   Configuring...`, `
  Authenticat... |
| `Create development configuration\.` | test_launcher_integration.py:259 | TestMultiEnvironment._creat... | `
   Configuring...`, `
  Authenticat... |
| `Create installer configuration` | installer_types.py:48 | create_installer_config | `
   Configuring...`, `
  Authenticat... |
| `Create optimization configuration` | test_backend_optimized.py:163 | OptimizedTestManager._creat... | `
   Configuring...`, `
  Authenticat... |
| `Create production configuration\.` | test_launcher_integration.py:266 | TestMultiEnvironment._creat... | `
   Configuring...`, `
  Authenticat... |
| `Create test configuration\.` | test_launcher_health.py:266 | TestErrorRecovery._create_t... | `
   Configuring...`, `
  Authenticat... |
| `Create test database` | test_config.py:113 | PostgresTestConfig.create_t... | `
   Configuring...`, `
  Authenticat... |
| `Create validation context\.` | test_config_validator.py:69 | TestServiceConfigValidator.... | `
   Configuring...`, `
  Authenticat... |
| `Create validator instance\.` | test_config_validator.py:74 | TestServiceConfigValidator.... | `
   Configuring...`, `
  Authenticat... |
| `Created test database: ` | test_config.py:134 | PostgresTestConfig.create_t... | `
   Configuring...`, `
  Authenticat... |
| `Creating ` | seed_staging_data.py:205 | StagingDataSeeder._get_opti... | `
   Configuring...`, `
  Authenticat... |
| `Daily limit \($` | workflow_config_utils.py:91 | WorkflowConfigUtils._check_... | `
   Configuring...`, `
  Authenticat... |
| `Database engine disposed` | test_config.py:63 | TestDatabaseConfig.cleanup | `
   Configuring...`, `
  Authenticat... |
| `Database tables reset` | test_config.py:94 | TestDatabaseConfig.reset_ta... | `
   Configuring...`, `
  Authenticat... |
| `dev\-postgres\.example\.com` | service_config.py:121 | ServicesConfiguration | `
   Configuring...`, `
  Authenticat... |
| `dev\_google\_client\_123` | test_oauth_models.py:202 | TestAuthConfigResponse.test... | `
   Configuring...`, `
  Authenticat... |
| `dev\_launcher\.config\.find\_project\...` | test_default_launcher.py:24 | TestDefaultLauncherConfig.t... | `
   Configuring...`, `
  Authenticat... |
| `dev\_launcher\.config\_validator\.Con...` | test_config_validator.py:172 | TestValidateServiceConfig.t... | `
   Configuring...`, `
  Authenticat... |
| `dev\_launcher\.config\_validator\.Ser...` | test_config_validator.py:171 | TestValidateServiceConfig.t... | `
   Configuring...`, `
  Authenticat... |
| `dev\_launcher\.launcher\.DevLauncher\...` | test_default_launcher.py:133 | TestDefaultLauncherConfig.t... | `
   Configuring...`, `
  Authenticat... |
| `dev\_launcher\.launcher\.setup\_logging` | test_default_launcher.py:134 | TestDefaultLauncherConfig.t... | `
   Configuring...`, `
  Authenticat... |
| `Development overrides` | config.py:422 | LauncherConfig._get_env_fil... | `
   Configuring...`, `
  Authenticat... |
| `Display current configuration` | manage_workflows.py:144 | WorkflowManager.show_config | `
   Configuring...`, `
  Authenticat... |
| `Display features configuration` | workflow_config_utils.py:25 | WorkflowConfigUtils._show_f... | `
   Configuring...`, `
  Authenticat... |
| `Display workflows configuration` | workflow_config_utils.py:34 | WorkflowConfigUtils._show_w... | `
   Configuring...`, `
  Authenticat... |
| `dist\-packages` | core.py:86 | ComplianceConfig._get_skip_... | `
   Configuring...`, `
  Authenticat... |
| `Docker image tag` | build_staging.py:263 | _add_configuration_arguments | `
   Configuring...`, `
  Authenticat... |
| `Drop test database` | test_config.py:139 | PostgresTestConfig.drop_tes... | `
   Configuring...`, `
  Authenticat... |
| `Dropped test database: ` | test_config.py:152 | PostgresTestConfig.drop_tes... | `
   Configuring...`, `
  Authenticat... |
| `e2e` | coverage_config.py:162 | CoverageThresholds.get_conf... | `
   Configuring...`, `
  Authenticat... |
| `Enhanced Schema Synchronization` | schema_sync.py:63 | print_configuration | `
   Configuring...`, `
  Authenticat... |
| `env vars` | test_staging_config.py:113 | _check_single_staging_llm_c... | `
   Configuring...`, `
  Authenticat... |
| `Failed to validate ` | system_diagnostics.py:262 | SystemDiagnostics._validate... | `
   Configuring...`, `
  Authenticat... |
| `Force sync: ` | schema_sync.py:68 | print_configuration | `
   Configuring...`, `
  Authenticat... |
| `Frontend output: ` | schema_sync.py:66 | print_configuration | `
   Configuring...`, `
  Authenticat... |
| `GCP Configuration Check` | validate_staging_config.py:344 | check_gcp_configuration | `
   Configuring...`, `
  Authenticat... |
| `Get authentication configuration` | test_client.py:183 | AuthTestClient.get_auth_config | `
   Configuring...`, `
  Authenticat... |
| `Get current environment` | config.py:17 | AuthConfig.get_environment | `
   Configuring...`, `
  Authenticat... |
| `Get integrations configuration` | config_manager.py:52 | ConfigurationManager._get_i... | `
   Configuring...`, `
  Authenticat... |
| `Get JWT algorithm` | config.py:40 | AuthConfig.get_jwt_algorithm | `
   Configuring...`, `
  Authenticat... |
| `Get monitoring configuration` | config_manager.py:42 | ConfigurationManager._get_m... | `
   Configuring...`, `
  Authenticat... |
| `Get services configuration\.` | config.py:228 | LauncherConfig.services_config | `
   Configuring...`, `
  Authenticat... |
| `get\-value` | validate_staging_config.py:349 | check_gcp_configuration | `
   Configuring...`, `
  Authenticat... |
| `Google OAuth` | secret_config.py:63 | SecretConfig.get_secret_cat... | `
   Configuring...`, `
  Authenticat... |
| `google\_client\_123` | test_oauth_models.py:178 | TestAuthConfigResponse.test... | `
   Configuring...`, `
  Authenticat... |
| `gpt\-4` | setup_assistant.py:56 | _create_assistant_config | `
   Configuring...`, `
  Authenticat... |
| `Handle configuration\-related issues\.` | recovery_actions.py:207 | RecoveryActions.handle_conf... | `
   Configuring...`, `
  Authenticat... |
| `HS256` | config.py:42 | AuthConfig.get_jwt_algorithm | `
   Configuring...`, `
  Authenticat... |
| `Initialize computed fields\.` | config.py:83 | LauncherConfig.__post_init__ | `
   Configuring...`, `
  Authenticat... |
| `Invalid backend port` | test_launcher.py:44 | TestLauncherConfig.test_con... | `
   Configuring...`, `
  Authenticat... |
| `Invalid backend port: ` | config.py:102 | LauncherConfig._validate | `
   Configuring...`, `
  Authenticat... |
| `Invalid config response: ` | test_websocket_dev_mode.py:104 | WebSocketDevModeTest.test_c... | `
   Configuring...`, `
  Authenticat... |
| `Invalid frontend port` | test_launcher.py:48 | TestLauncherConfig.test_con... | `
   Configuring...`, `
  Authenticat... |
| `Invalid frontend port: ` | config.py:105 | LauncherConfig._validate | `
   Configuring...`, `
  Authenticat... |
| `jest\.config\.cjs` | validate_frontend_tests.py:90 | FrontendTestValidator._chec... | `
   Configuring...`, `
  Authenticat... |
| `jest\.config\.js` | validate_frontend_tests.py:89 | FrontendTestValidator._chec... | `
   Configuring...`, `
  Authenticat... |
| `jest\.config\.unified\.cjs` | validate_frontend_tests.py:91 | FrontendTestValidator._chec... | `
   Configuring...`, `
  Authenticat... |
| `Load current configuration` | manage_precommit.py:16 | load_config | `
   Configuring...`, `
  Authenticat... |
| `Load service configuration\.` | config.py:232 | LauncherConfig._load_servic... | `
   Configuring...`, `
  Authenticat... |
| `Load workflow configuration` | manage_workflows.py:30 | WorkflowManager.load_config | `
   Configuring...`, `
  Authenticat... |
| `Local instance` | __main__.py:388 | handle_service_configuration | `
   Configuring...`, `
  Authenticat... |
| `Log ClickHouse configuration\.` | config.py:280 | LauncherConfig._log_clickho... | `
   Configuring...`, `
  Authenticat... |
| `Log directory: ` | config.py:261 | LauncherConfig.log_verbose_... | `
   Configuring...`, `
  Authenticat... |
| `Log LLM configuration\.` | config.py:290 | LauncherConfig._log_llm_config | `
   Configuring...`, `
  Authenticat... |
| `Log PostgreSQL configuration\.` | config.py:285 | LauncherConfig._log_postgre... | `
   Configuring...`, `
  Authenticat... |
| `Log Redis configuration\.` | config.py:275 | LauncherConfig._log_redis_c... | `
   Configuring...`, `
  Authenticat... |
| `m, Integration=` | validate_workflow_config.py:196 | _print_config_details | `
   Configuring...`, `
  Authenticat... |
| `m, Unit=` | validate_workflow_config.py:195 | _print_config_details | `
   Configuring...`, `
  Authenticat... |
| `Missing ` | verify_auth_config.py:88 | verify_environment_config | `
   Configuring...`, `
  Authenticat... |
| `Missing configs: ` | test_staging_startup.py:131 | StagingStartupTester.test_c... | `
   Configuring...`, `
  Authenticat... |
| `Missing required section: ` | validate_workflow_config.py:31 | validate_config_structure | `
   Configuring...`, `
  Authenticat... |
| `Missing timeout for: ` | validate_workflow_config.py:47 | validate_config_structure | `
   Configuring...`, `
  Authenticat... |
| `Mock implementation` | __main__.py:390 | handle_service_configuration | `
   Configuring...`, `
  Authenticat... |
| `Mock LLM response` | service_config.py:143 | ServicesConfiguration | `
   Configuring...`, `
  Authenticat... |
| `netra\-assistant` | setup_assistant.py:51 | _create_assistant_config | `
   Configuring...`, `
  Authenticat... |
| `netra\-backend` | staging_error_monitor.py:53 | MonitorConfig | `
   Configuring...`, `
  Authenticat... |
| `netra\-core\-generation\-1` | __main__.py:328 | handle_service_configuration | `
   Configuring...`, `
  Authenticat... |
| `netra\-staging` | staging_error_monitor.py:52 | MonitorConfig | `
   Configuring...`, `
  Authenticat... |
| `NO \(webpack\)` | dev_launcher_monitoring.py:151 | print_configuration_summary | `
   Configuring...`, `
  Authenticat... |
| `No API key` | test_config_loading.py:88 | _check_single_llm_config | `
   Configuring...`, `
  Authenticat... |
| `Node Version: ` | validate_workflow_config.py:193 | _print_config_details | `
   Configuring...`, `
  Authenticat... |
| `not found` | recovery_actions.py:213 | RecoveryActions.handle_conf... | `
   Configuring...`, `
  Authenticat... |
| `NOT SET` | config.py:126 | AuthConfig.log_configuration | `
   Configuring...`, `
  Authenticat... |
| `Not set` | workflow_config_utils.py:46 | WorkflowConfigUtils._show_c... | `
   Configuring...`, `
  Authenticat... |
| `OAuth config for ` | test_environment_detection.py:143 | test_oauth_config_fallback | `
   Configuring...`, `
  Authenticat... |
| `OK \- Configured` | test_config_loading.py:96 | _check_auth_configurations | `
   Configuring...`, `
  Authenticat... |
| `pathlib\.Path\.exists` | test_default_launcher.py:25 | TestDefaultLauncherConfig.t... | `
   Configuring...`, `
  Authenticat... |
| `pip\-wheel\-metadata` | core.py:89 | ComplianceConfig._get_skip_... | `
   Configuring...`, `
  Authenticat... |
| `PostgreSQL \(main database\)` | service_config.py:407 | ServiceConfigWizard.run | `
   Configuring...`, `
  Authenticat... |
| `postgresql\+asyncpg://` | test_config.py:109 | PostgresTestConfig.__init__ | `
   Configuring...`, `
  Authenticat... |
| `PostgreSQL\-specific test configuration` | test_config.py:98 | PostgresTestConfig | `
   Configuring...`, `
  Authenticat... |
| `postgresql://` | service_config.py:224 | ServicesConfiguration._add_... | `
   Configuring...`, `
  Authenticat... |
| `postgresql://mock:mock@localhost:5432...` | service_config.py:215 | ServicesConfiguration._add_... | `
   Configuring...`, `
  Authenticat... |
| `postgresql://test:test@localhost:5432...` | test_single_database.py:84 | test_database_url_configura... | `
   Configuring...`, `
  Authenticat... |
| `Print configuration options\.` | config.py:355 | LauncherConfig._print_confi... | `
   Configuring...`, `
  Authenticat... |
| `Print configuration summary\.` | dev_launcher_monitoring.py:144 | print_configuration_summary | `
   Configuring...`, `
  Authenticat... |
| `Print logging configuration\.` | config.py:381 | LauncherConfig._print_loggi... | `
   Configuring...`, `
  Authenticat... |
| `Print secrets configuration\.` | config.py:395 | LauncherConfig._print_secre... | `
   Configuring...`, `
  Authenticat... |
| `Print synchronization configuration\.` | schema_sync.py:62 | print_configuration | `
   Configuring...`, `
  Authenticat... |
| `Print Turbopack configuration\.` | config.py:391 | LauncherConfig._print_turbo... | `
   Configuring...`, `
  Authenticat... |
| `Print verbose configuration\.` | config.py:399 | LauncherConfig._print_verbo... | `
   Configuring...`, `
  Authenticat... |
| `Project root: ` | config.py:260 | LauncherConfig.log_verbose_... | `
   Configuring...`, `
  Authenticat... |
| `pytest\.ini` | test_backend.py:189 | _add_config_file_args | `
   Configuring...`, `
  Authenticat... |
| `Python Version: ` | validate_workflow_config.py:192 | _print_config_details | `
   Configuring...`, `
  Authenticat... |
| `redis\-17593\.c305\.ap\-south\-1\-1\....` | service_config.py:79 | ServicesConfiguration | `
   Configuring...`, `
  Authenticat... |
| `redis\-cli` | service_config.py:283 | ServicesConfiguration._chec... | `
   Configuring...`, `
  Authenticat... |
| `redis://` | config_validator.py:141 | ServiceConfigValidator._get... | `
   Configuring...`, `
  Authenticat... |
| `redis://:` | service_config.py:188 | ServicesConfiguration._add_... | `
   Configuring...`, `
  Authenticat... |
| `redis://localhost:6379` | config.py:103 | AuthConfig.get_redis_url | `
   Configuring...`, `
  Authenticat... |
| `redis://redis:6379` | config.py:103 | AuthConfig.get_redis_url | `
   Configuring...`, `
  Authenticat... |
| `Refresh token duration: ` | test_auth_token_generation.py:268 | TestJWTTokenGeneration.test... | `
   Configuring...`, `
  Authenticat... |
| `requirements\.txt` | diagnostic_helpers.py:128 | get_configuration | `
   Configuring...`, `
  Authenticat... |
| `return cls\(` | enhance_dev_launcher_boundaries.py:22 | enhance_launcher_config | `
   Configuring...`, `
  Authenticat... |
| `Runner Type: ` | validate_workflow_config.py:191 | _print_config_details | `
   Configuring...`, `
  Authenticat... |
| `Running in ` | environment_validator.py:380 | EnvironmentValidator.valida... | `
   Configuring...`, `
  Authenticat... |
| `Save configuration` | manage_precommit.py:27 | save_config | `
   Configuring...`, `
  Authenticat... |
| `Save tracking configuration` | enabler.py:45 | MetadataTrackingEnabler._co... | `
   Configuring...`, `
  Authenticat... |
| `Save workflow configuration` | manage_workflows.py:37 | WorkflowManager.save_config | `
   Configuring...`, `
  Authenticat... |
| `Secret Manager` | test_staging_config.py:113 | _check_single_staging_llm_c... | `
   Configuring...`, `
  Authenticat... |
| `Service configuration loaded:` | config.py:268 | LauncherConfig._log_service... | `
   Configuring...`, `
  Authenticat... |
| `Service Modes:` | config.py:309 | LauncherConfig._print_servi... | `
   Configuring...`, `
  Authenticat... |
| `Service token duration: ` | test_auth_token_generation.py:271 | TestJWTTokenGeneration.test... | `
   Configuring...`, `
  Authenticat... |
| `Service unreachable` | test_config_validator.py:41 | TestConfigValidationResult.... | `
   Configuring...`, `
  Authenticat... |
| `Setting up configuration\.\.\.` | install_dev_env.py:115 | DevEnvironmentInstaller.run... | `
   Configuring...`, `
  Authenticat... |
| `Show configuration summary\.` | config.py:295 | LauncherConfig.show_configu... | `
   Configuring...`, `
  Authenticat... |
| `site\-packages` | core.py:86 | ComplianceConfig._get_skip_... | `
   Configuring...`, `
  Authenticat... |
| `spec\.` | core.py:96 | ComplianceConfig.is_test_file | `
   Configuring...`, `
  Authenticat... |
| `sqlite\+aiosqlite:///:memory:` | test_config.py:23 | TestDatabaseConfig.__init__ | `
   Configuring...`, `
  Authenticat... |
| `static/admin` | core.py:90 | ComplianceConfig._get_skip_... | `
   Configuring...`, `
  Authenticat... |
| `static/rest\_framework` | core.py:90 | ComplianceConfig._get_skip_... | `
   Configuring...`, `
  Authenticat... |
| `Terraform\-generated` | config.py:423 | LauncherConfig._get_env_fil... | `
   Configuring...`, `
  Authenticat... |
| `terraform/\.terraform` | core.py:91 | ComplianceConfig._get_skip_... | `
   Configuring...`, `
  Authenticat... |
| `Test AuthConfigResponse model` | test_oauth_models.py:165 | TestAuthConfigResponse | `
   Configuring...`, `
  Authenticat... |
| `Test ConfigDecisionEngine class\.` | test_config_validator.py:104 | TestConfigDecisionEngine | `
   Configuring...`, `
  Authenticat... |
| `Test configuration creation\.` | verify_startup_fix.py:43 | test_config_creation | `
   Configuring...`, `
  Authenticat... |
| `Test configuration management\.` | test_launcher.py:28 | TestLauncherConfig | `
   Configuring...`, `
  Authenticat... |
| `Test Configuration:` | test_backend.py:365 | _print_test_config_details | `
   Configuring...`, `
  Authenticat... |
| `Test ConfigValidationResult model\.` | test_config_validator.py:27 | TestConfigValidationResult | `
   Configuring...`, `
  Authenticat... |
| `Test CORS configuration` | test_auth_integration.py:105 | AuthServiceTester.test_cors... | `
   Configuring...`, `
  Authenticat... |
| `Test environment\-based configuration\.` | test_launcher_config.py:175 | TestEnvironmentConfiguration | `
   Configuring...`, `
  Authenticat... |
| `Test ServiceConfigValidator class\.` | test_config_validator.py:60 | TestServiceConfigValidator | `
   Configuring...`, `
  Authenticat... |
| `Test Timeouts: Smoke=` | validate_workflow_config.py:195 | _print_config_details | `
   Configuring...`, `
  Authenticat... |
| `test\-gemini\-key\-from\-env` | test_staging_config.py:113 | _check_single_staging_llm_c... | `
   Configuring...`, `
  Authenticat... |
| `test\-jwt\-key\-from\-env` | test_staging_config.py:128 | _check_jwt_config | `
   Configuring...`, `
  Authenticat... |
| `test\-project` | test_launcher.py:79 | TestLauncherConfig.test_con... | `
   Configuring...`, `
  Authenticat... |
| `test\-project\-123` | test_launcher_validation.py:170 | test_config_env_vars | `
   Configuring...`, `
  Authenticat... |
| `test\-service` | test_auth_token_generation.py:238 | TestJWTTokenGeneration.test... | `
   Configuring...`, `
  Authenticat... |
| `Testing configuration loading\.\.\.` | test_staging_startup.py:108 | StagingStartupTester.test_c... | `
   Configuring...`, `
  Authenticat... |
| `third\-party` | core.py:86 | ComplianceConfig._get_skip_... | `
   Configuring...`, `
  Authenticat... |
| `Unit Test Shards: ` | validate_workflow_config.py:199 | _print_config_details | `
   Configuring...`, `
  Authenticat... |
| `Unreachable: ` | config_validator.py:129 | ServiceConfigValidator._val... | `
   Configuring...`, `
  Authenticat... |
| `utf\-8` | align_test_imports.py:227 | TestImportAligner.fix_test_... | `
   Configuring...`, `
  Authenticat... |
| `Validate configuration values\.` | config.py:99 | LauncherConfig._validate | `
   Configuring...`, `
  Authenticat... |
| `Validate system configuration` | test_example_message_flow.py:230 | ExampleMessageFlowTestRunne... | `
   Configuring...`, `
  Authenticat... |
| `Validate workflow configuration` | manage_workflows.py:161 | WorkflowManager.validate_co... | `
   Configuring...`, `
  Authenticat... |
| `Validating security configuration\.\.\.` | environment_validator.py:349 | EnvironmentValidator.valida... | `
   Configuring...`, `
  Authenticat... |
| `Validation level: ` | schema_sync.py:67 | print_configuration | `
   Configuring...`, `
  Authenticat... |
| `Verify OAuth configuration` | monitor_oauth_flow.py:42 | OAuthMonitor.check_oauth_co... | `
   Configuring...`, `
  Authenticat... |
| `win32` | test_backend.py:58 | _configure_windows_asyncio | `
   Configuring...`, `
  Authenticat... |
| `wwwroot/lib` | core.py:90 | ComplianceConfig._get_skip_... | `
   Configuring...`, `
  Authenticat... |
| `Y/n` | service_config.py:494 | ServiceConfigWizard._ask_ye... | `
   Configuring...`, `
  Authenticat... |
| `y/N` | service_config.py:494 | ServiceConfigWizard._ask_ye... | `
   Configuring...`, `
  Authenticat... |
| `yarn\.lock` | core.py:90 | ComplianceConfig._get_skip_... | `
   Configuring...`, `
  Authenticat... |
| `YES \(experimental\)` | dev_launcher_monitoring.py:151 | print_configuration_summary | `
   Configuring...`, `
  Authenticat... |
| `YES \(uvicorn native\)` | config.py:373 | LauncherConfig._print_backe... | `
   Configuring...`, `
  Authenticat... |
| `ZmVybmV0LXRlc3Qta2V5LXBsYWNlaG9sZGVyL...` | test_staging_config.py:137 | _check_fernet_config | `
   Configuring...`, `
  Authenticat... |
| `• ` | config.py:254 | LauncherConfig._print | `
   Configuring...`, `
  Authenticat... |
| `☁️` | config.py:314 | LauncherConfig._print_servi... | `
   Configuring...`, `
  Authenticat... |
| `⚠️  ` | service_config.py:262 | ServicesConfiguration.validate | `
   Configuring...`, `
  Authenticat... |

### Usage Examples

- **dev_launcher\service_config.py:469** - `ServiceConfigWizard._customize_local_config`
- **scripts\test_config_loading.py:93** - `_check_auth_configurations`
- **scripts\test_config_loading.py:115** - `_check_database_configuration`

---

## Subcategory: env_var {subcategory-env-var}

**Count**: 3065 literals

### 🟢 High (≥0.8) (3065 literals)

| Literal | Files | Context | Related |
|---------|-------|---------|---------|
| `\_\_` | analyze_test_overlap.py:95 | TestOverlapAnalyzer._collec... | `ABC`, `ABORT` |
| `\_\_eq\_\_` | function_complexity_linter.py:64 | FunctionComplexityLinter._i... | `ABC`, `ABORT` |
| `\_\_init\_\_` | architecture_scanner.py:207 | ArchitectureScanner._check_... | `ABC`, `ABORT` |
| `\_\_main\_\_` | main.py:344 | module | `ABC`, `ABORT` |
| `\_\_pycache\_\_` | align_test_imports.py:80 | TestImportAligner.scan_test... | `ABC`, `ABORT` |
| `\_\_repr\_\_` | function_complexity_linter.py:64 | FunctionComplexityLinter._i... | `ABC`, `ABORT` |
| `\_\_str\_\_` | function_complexity_linter.py:64 | FunctionComplexityLinter._i... | `ABC`, `ABORT` |
| `\_\_tests\_\_` | align_test_imports.py:35 | TestImportAligner.__init__ | `ABC`, `ABORT` |
| `\_allocate\_dynamic\_ports` | test_launcher_health.py:229 | TestErrorRecovery._test_por... | `ABC`, `ABORT` |
| `\_api` | environment_validator.py:415 | EnvironmentValidator.genera... | `ABC`, `ABORT` |
| `\_backup` | file_checker.py:33 | FileChecker.check_file_naming | `ABC`, `ABORT` |
| `\_branch\_` | auto_decompose_functions.py:241 | FunctionDecomposer._suggest... | `ABC`, `ABORT` |
| `\_check\_http\_server` | test_websocket_connection_issue.py:107 | TestWebSocketConnectionIssu... | `ABC`, `ABORT` |
| `\_comprehensive` | generate_test_audit.py:102 | analyze_test_structure | `ABC`, `ABORT` |
| `\_copy` | file_checker.py:33 | FileChecker.check_file_naming | `ABC`, `ABORT` |
| `\_cors\_middleware\_getter` | health_monitor.py:585 | HealthMonitor.get_cross_ser... | `ABC`, `ABORT` |
| `\_critical` | generate_test_audit.py:100 | analyze_test_structure | `ABC`, `ABORT` |
| `\_current\_file\_path` | business_value_test_index.py:321 | BusinessValueTestIndexer._d... | `ABC`, `ABORT` |
| `\_dependencies` | cache_manager.py:210 | CacheManager.has_dependenci... | `ABC`, `ABORT` |
| `\_deps` | startup_optimizer.py:120 | StartupOptimizer.can_skip_step | `ABC`, `ABORT` |
| `\_enhanced` | file_checker.py:33 | FileChecker.check_file_naming | `ABC`, `ABORT` |
| `\_fixed` | file_checker.py:33 | FileChecker.check_file_naming | `ABC`, `ABORT` |
| `\_get\_token\_expiry` | test_auth_token_validation.py:87 | TestJWTTokenValidation.test... | `ABC`, `ABORT` |
| `\_graceful\_shutdown` | test_default_launcher.py:276 | TestGracefulShutdownImprove... | `ABC`, `ABORT` |
| `\_handler` | ssot_checker.py:96 | SSOTChecker._check_duplicat... | `ABC`, `ABORT` |
| `\_health` | service_startup.py:252 | ServiceStartupCoordinator.c... | `ABC`, `ABORT` |
| `\_helper` | test_refactor_helper.py:208 | TestRefactorHelper._determi... | `ABC`, `ABORT` |
| `\_helper\_` | test_fixer.py:279 | TestFixer._split_function_c... | `ABC`, `ABORT` |
| `\_HOST` | secret_validator.py:89 | SecretValidator._has_potent... | `ABC`, `ABORT` |
| `\_initialization` | fix_e2e_tests_comprehensive.py:251 | E2ETestFixer._add_basic_tests | `ABC`, `ABORT` |
| `\_input` | auto_decompose_functions.py:270 | FunctionDecomposer._suggest... | `ABC`, `ABORT` |
| `\_install` | dependency_checker.py:335 | AsyncDependencyChecker.inst... | `ABC`, `ABORT` |
| `\_integration\_` | real_test_requirements_enforcer.py:343 | RealTestRequirementsEnforce... | `ABC`, `ABORT` |
| `\_is\_port\_available` | test_startup_comprehensive.py:187 | TestPortManagerWindows.test... | `ABC`, `ABORT` |
| `\_latency\_avg` | real_service_test_metrics.py:106 | RealServiceTestMetrics.fina... | `ABC`, `ABORT` |
| `\_legacy` | type_checker.py:127 | TypeChecker._categorize_files | `ABC`, `ABORT` |
| `\_manager` | ssot_checker.py:99 | SSOTChecker._check_duplicat... | `ABC`, `ABORT` |
| `\_MODE` | service_config.py:54 | ServiceResource.get_env_vars | `ABC`, `ABORT` |
| `\_new` | file_checker.py:33 | FileChecker.check_file_naming | `ABC`, `ABORT` |
| `\_npm` | dependency_checker.py:190 | AsyncDependencyChecker._che... | `ABC`, `ABORT` |
| `\_npm\_check` | dependency_checker.py:130 | AsyncDependencyChecker._cre... | `ABC`, `ABORT` |
| `\_old` | file_checker.py:33 | FileChecker.check_file_naming | `ABC`, `ABORT` |
| `\_part` | auto_split_files.py:201 | FileSplitter._suggest_logic... | `ABC`, `ABORT` |
| `\_part\_` | auto_decompose_functions.py:339 | FunctionDecomposer._suggest... | `ABC`, `ABORT` |
| `\_pip` | dependency_checker.py:146 | AsyncDependencyChecker._che... | `ABC`, `ABORT` |
| `\_pip\_check` | dependency_checker.py:118 | AsyncDependencyChecker._cre... | `ABC`, `ABORT` |
| `\_pr` | seed_staging_data.py:120 | StagingDataSeeder._build_ad... | `ABC`, `ABORT` |
| `\_process\_` | auto_decompose_functions.py:277 | FunctionDecomposer._suggest... | `ABC`, `ABORT` |
| `\_real` | test_discovery_report.py:46 | EnhancedTestDiscoveryReport... | `ABC`, `ABORT` |
| `\_safe\_operation\_` | auto_decompose_functions.py:307 | FunctionDecomposer._suggest... | `ABC`, `ABORT` |
| `\_service\_discovery` | health_monitor.py:597 | HealthMonitor.get_cross_ser... | `ABC`, `ABORT` |
| `\_start` | startup_profiler.py:89 | StartupProfiler.start_phase... | `ABC`, `ABORT` |
| `\_startup` | service_startup.py:224 | ServiceStartupCoordinator.s... | `ABC`, `ABORT` |
| `\_temp` | file_checker.py:33 | FileChecker.check_file_naming | `ABC`, `ABORT` |
| `\_terminate\_all\_services` | test_dev_user_flow.py:259 | TestDevLauncherIntegration.... | `ABC`, `ABORT` |
| `\_test` | real_test_linter.py:237 | RealTestLinter.check_git_diff | `ABC`, `ABORT` |
| `\_test\_` | project_test_validator.py:121 | ProjectTestValidator._is_te... | `ABC`, `ABORT` |
| `\_user\_` | user_factory.py:82 | UserFactory.create_oauth_us... | `ABC`, `ABORT` |
| `\_validate` | test_dev_user_flow.py:28 | TestDevUserCreation.mock_de... | `ABC`, `ABORT` |
| `\_validate\_` | auto_decompose_functions.py:270 | FunctionDecomposer._suggest... | `ABC`, `ABORT` |
| `\_verify\_windows\_process` | test_startup_comprehensive.py:294 | TestHealthMonitorGracePerio... | `ABC`, `ABORT` |
| `ABC` | remove_test_stubs.py:211 | TestStubDetector._scan_empt... | `ABORT`, `ACCESS_TOKEN_EX...` |
| `ABORT` | crash_detector.py:42 | CrashDetector._build_fatal_... | `ABC`, `ACCESS_TOKEN_EX...` |
| `absolute` | check_netra_backend_imports.py:48 | ImportAnalyzer.__init__ | `ABC`, `ABORT` |
| `abstract` | type_checker.py:155 | TypeChecker._filter_backend... | `ABC`, `ABORT` |
| `abstractmethod` | remove_test_stubs.py:211 | TestStubDetector._scan_empt... | `ABC`, `ABORT` |
| `Accept` | test_client.py:24 | AuthTestClient.__init__ | `ABC`, `ABORT` |
| `access` | jwt_handler.py:49 | JWTHandler.create_access_token | `ABC`, `ABORT` |
| `access\_denied` | test_auth_oauth_errors.py:119 | TestOAuthErrorHandling.test... | `ABC`, `ABORT` |
| `access\_token` | auth_routes.py:179 | refresh_tokens | `ABC`, `ABORT` |
| `ACCESS\_TOKEN\_EXPIRE\_MINUTES` | test_env.py:24 | TestEnvironment | `ABC`, `ABORT` |
| `ACCOUNT\_LOCKED` | audit_factory.py:24 | AuditLogFactory | `ABC`, `ABORT` |
| `account\_locked` | auth_service.py:63 | AuthService.login | `ABC`, `ABORT` |
| `ACCOUNT\_LOCKOUT\_DURATION` | test_env.py:60 | TestEnvironment | `ABC`, `ABORT` |
| `ACCOUNT\_UNLOCKED` | audit_factory.py:25 | AuditLogFactory | `ABC`, `ABORT` |
| `account\_unlocked` | audit_factory.py:25 | AuditLogFactory | `ABC`, `ABORT` |
| `ACT` | test_workflows_with_act.py:241 | WorkflowTester.check_common... | `ABC`, `ABORT` |
| `act` | act_wrapper.py:30 | ACTWrapper._validate_prereq... | `ABC`, `ABORT` |
| `action` | permission_factory.py:59 | PermissionFactory.create_pe... | `ABC`, `ABORT` |
| `active` | connection.py:238 | AuthDatabase.get_status | `ABC`, `ABORT` |
| `active\_tasks` | crash_recovery.py:226 | CrashRecoveryManager.get_mo... | `ABC`, `ABORT` |
| `actual\_implementation` | analyze_failures.py:151 | TestFailureAnalyzer._determ... | `ABC`, `ABORT` |
| `actual\_lines` | enforce_limits.py:198 | EnforcementReporter.generat... | `ABC`, `ABORT` |
| `actual\_value` | auto_fix_test_sizes.py:634 | TestSizeFixer.fix_all_viola... | `ABC`, `ABORT` |
| `ACTUALLY` | auto_fix_test_violations.py:338 | TestFileSplitter.split_larg... | `ABC`, `ABORT` |
| `AdaptiveService` | test_launcher_health.py:196 | TestAdvancedHealthMonitor._... | `ABC`, `ABORT` |
| `add` | comprehensive_test_fixer.py:86 | CodeGenerator.generate_func... | `ABC`, `ABORT` |
| `add\_function` | comprehensive_test_fixer.py:47 | TestFailureAnalyzer.analyze... | `ABC`, `ABORT` |
| `add\_streamer` | test_launcher.py:315 | TestDevLauncher.disabled_te... | `ABC`, `ABORT` |
| `added` | schema_sync.py:95 | print_changes_detected | `ABC`, `ABORT` |
| `admin` | auth_routes.py:355 | dev_login | `ABC`, `ABORT` |
| `AdminDep` | audit_permissions.py:34 | analyze_route_file | `ABC`, `ABORT` |
| `advanced` | seed_staging_data.py:231 | StagingDataSeeder._generate... | `ABC`, `ABORT` |
| `after` | auth_models.py:32 | LoginRequest.validate_passw... | `ABC`, `ABORT` |
| `agent` | agent_tracking_helper.py:127 | AgentTrackingHelper._create... | `ABC`, `ABORT` |
| `agent\_name` | websocket_coherence_review.py:124 | check_payload_completeness | `ABC`, `ABORT` |
| `agent\_orchestration` | business_value_test_index.py:97 | BusinessValueTestIndexer.__... | `ABC`, `ABORT` |
| `agent\_orchestration\_service` | fix_e2e_tests_comprehensive.py:59 | E2ETestFixer._get_common_fi... | `ABC`, `ABORT` |
| `agent\_service` | comprehensive_import_scanner.py:155 | ComprehensiveImportScanner.... | `ABC`, `ABORT` |
| `AgentConfig` | validate_type_deduplication.py:60 | TypeDeduplicationValidator.... | `ABC`, `ABORT` |
| `AgentMetadata` | deduplicate_types.py:79 | TypeDeduplicator._setup_pyt... | `ABC`, `ABORT` |
| `AgentResult` | deduplicate_types.py:77 | TypeDeduplicator._setup_pyt... | `ABC`, `ABORT` |
| `agents` | check_e2e_imports.py:43 | E2EImportChecker.__init__ | `ABC`, `ABORT` |
| `AgentService` | categorize_tests.py:74 | TestCategorizer._get_integr... | `ABC`, `ABORT` |
| `AgentState` | deduplicate_types.py:76 | TypeDeduplicator._setup_pyt... | `ABC`, `ABORT` |
| `AgentStatus` | deduplicate_types.py:78 | TypeDeduplicator._setup_pyt... | `ABC`, `ABORT` |
| `AgentSystemAnalyzer` | status_analyzer.py:27 | module | `ABC`, `ABORT` |
| `AgentUpdatePayload` | deduplicate_types.py:92 | TypeDeduplicator._setup_web... | `ABC`, `ABORT` |
| `aggressive` | benchmark_optimization.py:171 | TestExecutionBenchmark._run... | `ABC`, `ABORT` |
| `ai` | auto_fix_test_sizes.py:354 | TestFileSplitter._determine... | `ABC`, `ABORT` |
| `ai\_assistance` | workflow_presets.py:29 | WorkflowPresets.get_minimal... | `ABC`, `ABORT` |
| `ai\_provider\_simulator` | fix_e2e_tests_comprehensive.py:52 | E2ETestFixer._get_common_fi... | `ABC`, `ABORT` |
| `aiosqlite` | dependency_installer.py:101 | install_essential_packages_... | `ABC`, `ABORT` |
| `alembic` | clean_slate_executor.py:116 | CleanSlateExecutor.phase2_d... | `ABC`, `ABORT` |
| `alert\_count` | boundary_monitor.py:213 | BoundaryMonitorIntegration.... | `ABC`, `ABORT` |
| `alert\_on\_coverage\_drop` | config_manager.py:45 | ConfigurationManager._get_m... | `ABC`, `ABORT` |
| `alert\_on\_critical\_changes` | config_manager.py:44 | ConfigurationManager._get_m... | `ABC`, `ABORT` |
| `AlertSeverity` | validate_type_deduplication.py:66 | TypeDeduplicationValidator.... | `ABC`, `ABORT` |
| `alg` | test_auth_token_security.py:194 | TestJWTSignatureVerificatio... | `ABC`, `ABORT` |
| `align\_tests` | import_management.py:50 | ImportManagementSystem.__in... | `ABC`, `ABORT` |
| `all` | business_value_test_index.py:386 | BusinessValueTestIndexer._d... | `ABC`, `ABORT` |
| `ALLOWED\_HOSTS` | test_env.py:55 | TestEnvironment | `ABC`, `ABORT` |
| `allowed\_values` | environment_validator_core.py:96 | EnvironmentValidatorCore._d... | `ABC`, `ABORT` |
| `alternatives` | environment_validator_ports.py:41 | PortValidator._define_requi... | `ABC`, `ABORT` |
| `analysis` | coverage_reporter.py:162 | CoverageReporter.generate_c... | `ABC`, `ABORT` |
| `AnalysisRequest` | generate-json-schema.py:14 | main | `ABC`, `ABORT` |
| `analytics` | business_value_test_index.py:100 | BusinessValueTestIndexer.__... | `ABC`, `ABORT` |
| `analyze` | test_refactor_helper.py:674 | main | `ABC`, `ABORT` |
| `annual\_cost\_savings` | benchmark_optimization.py:308 | TestExecutionBenchmark._gen... | `ABC`, `ABORT` |
| `annual\_savings\_usd` | benchmark_optimization.py:288 | TestExecutionBenchmark._est... | `ABC`, `ABORT` |
| `anonymous` | check_test_compliance.py:47 | check_function_lengths | `ABC`, `ABORT` |
| `anthropic` | demo_real_llm_testing.py:122 | demo_real_llm_configuration | `ABC`, `ABORT` |
| `ANTHROPIC\_` | local_secrets.py:93 | LocalSecretManager._is_rele... | `ABC`, `ABORT` |
| `ANTHROPIC\_API\_KEY` | categorize_tests.py:48 | TestCategorizer._get_llm_pa... | `ABC`, `ABORT` |
| `Any` | fix_missing_functions.py:75 | add_missing_functions | `ABC`, `ABORT` |
| `apex\_optimizer\_agent` | status_agent_analyzer.py:103 | AgentSystemAnalyzer._check_... | `ABC`, `ABORT` |
| `API` | monitor_oauth_flow.py:28 | OAuthMonitor.check_services | `ABC`, `ABORT` |
| `api` | test_reviewer.py:225 | AutonomousTestReviewer._ide... | `ABC`, `ABORT` |
| `API\_BASE\_URL` | test_staging.py:30 | setup_staging_env | `ABC`, `ABORT` |
| `api\_endpoint` | scan_string_literals.py:72 | StringLiteralCategorizer | `ABC`, `ABORT` |
| `api\_endpoints` | status_renderer.py:74 | StatusReportRenderer._build... | `ABC`, `ABORT` |
| `API\_KEY` | code_review_analysis.py:190 | CodeReviewAnalysis._check_h... | `ABC`, `ABORT` |
| `api\_key` | auth_models.py:23 | AuthProvider | `ABC`, `ABORT` |
| `api\_keys` | demo_real_llm_testing.py:60 | demo_environment_validation | `ABC`, `ABORT` |
| `api\_keys\_configured` | environment_validator.py:415 | EnvironmentValidator.genera... | `ABC`, `ABORT` |
| `api\_latency` | seed_staging_data.py:283 | StagingDataSeeder._get_metr... | `ABC`, `ABORT` |
| `api\_response\_time` | startup_performance.py:31 | PerformanceMetrics.to_dict | `ABC`, `ABORT` |
| `api\_routes` | test_staging_startup.py:45 | StagingStartupTester.test_s... | `ABC`, `ABORT` |
| `api\_url` | dev_launcher_config.py:157 | setup_frontend_environment | `ABC`, `ABORT` |
| `API\_VERSION` | generate_openapi_spec.py:58 | _add_metadata | `ABC`, `ABORT` |
| `apiKey` | generate_openapi_spec.py:102 | _get_security_schemes | `ABC`, `ABORT` |
| `app` | test_reviewer.py:187 | AutonomousTestReviewer._ide... | `ABC`, `ABORT` |
| `append` | create_enforcement_tools.py:389 | add_advanced_arguments | `ABC`, `ABORT` |
| `appendix` | status_types.py:172 | ReportSections | `ABC`, `ABORT` |
| `application\_name` | connection.py:166 | AuthDatabase._get_cloud_sql... | `ABC`, `ABORT` |
| `apply` | generate_fix.py:309 | FixValidator._apply_patch | `ABC`, `ABORT` |
| `architectural\_debt` | architecture_metrics.py:50 | ArchitectureMetrics._calcul... | `ABC`, `ABORT` |
| `architecture\_health\_` | architecture_reporter.py:26 | ArchitectureReporter.export... | `ABC`, `ABORT` |
| `ArchitectureEnforcer` | __init__.py:16 | module | `ABC`, `ABORT` |
| `archive` | check_conftest_violations.py:23 | module | `ABC`, `ABORT` |
| `archived` | update_spec_timestamps.py:36 | module | `ABC`, `ABORT` |
| `archived\_implementations` | update_spec_timestamps.py:35 | module | `ABC`, `ABORT` |
| `archiver` | metadata_enabler.py:86 | MetadataTrackingEnabler.get... | `ABC`, `ABORT` |
| `archiver\_exists` | status_manager.py:83 | StatusManager.get_status | `ABC`, `ABORT` |
| `archiver\_script\_exists` | metadata_enabler.py:126 | MetadataTrackingEnabler._ca... | `ABC`, `ABORT` |
| `ArchiverGenerator` | __init__.py:21 | module | `ABC`, `ABORT` |
| `args` | test_generator.py:156 | _generate_basic_function_test | `ABC`, `ABORT` |
| `args\_kwargs\_stub` | remove_test_stubs.py:196 | TestStubDetector._scan_args... | `ABC`, `ABORT` |
| `args\_kwargs\_stubs` | remove_test_stubs.py:61 | TestStubDetector.__init__ | `ABC`, `ABORT` |
| `artifacts` | cleanup_staging_environments.py:224 | StagingEnvironmentCleaner.c... | `ABC`, `ABORT` |
| `artifacts\_url` | workflow_introspection.py:202 | WorkflowIntrospector.get_wo... | `ABC`, `ABORT` |
| `ascii` | team_updates_sync.py:177 | main | `ABC`, `ABORT` |
| `assert` | analyze_test_overlap.py:211 | TestOverlapAnalyzer._extrac... | `ABC`, `ABORT` |
| `assertion` | test_reviewer.py:162 | AutonomousTestReviewer._ass... | `ABC`, `ABORT` |
| `assertion\_count` | validate_agent_tests.py:302 | AgentTestValidator.export_j... | `ABC`, `ABORT` |
| `assertion\_error` | analyze_failures.py:40 | TestFailureAnalyzer | `ABC`, `ABORT` |
| `assertion\_similarity` | analyze_test_overlap.py:634 | TestOverlapAnalyzer._save_c... | `ABC`, `ABORT` |
| `AssertionError` | analyze_failures.py:40 | TestFailureAnalyzer | `ABC`, `ABORT` |
| `AssertionHelpers` | __init__.py:19 | module | `ABC`, `ABORT` |
| `assignment\_block` | auto_decompose_functions.py:115 | FunctionDecomposer._identif... | `ABC`, `ABORT` |
| `assistant` | seed_staging_data.py:192 | StagingDataSeeder.seed_thre... | `ABC`, `ABORT` |
| `async` | auto_fix_test_sizes.py:569 | TestFunctionOptimizer._manu... | `ABC`, `ABORT` |
| `async\_mock` | analyze_mocks.py:43 | MockAnalyzer.__init__ | `ABC`, `ABORT` |
| `async\_test\_count` | validate_agent_tests.py:300 | AgentTestValidator.export_j... | `ABC`, `ABORT` |
| `AsyncAdaptedQueuePool` | connection.py:242 | AuthDatabase.get_status | `ABC`, `ABORT` |
| `asyncio` | auto_fix_test_sizes.py:533 | TestFunctionOptimizer._crea... | `ABC`, `ABORT` |
| `asyncpg` | dependency_installer.py:101 | install_essential_packages_... | `ABC`, `ABORT` |
| `AsyncTestBase` | __init__.py:15 | module | `ABC`, `ABORT` |
| `attempt\_number` | audit_factory.py:94 | AuditLogFactory.create_logi... | `ABC`, `ABORT` |
| `attr` | analyze_test_overlap.py:193 | TestOverlapAnalyzer._extrac... | `ABC`, `ABORT` |
| `attribute\_error` | analyze_failures.py:37 | TestFailureAnalyzer | `ABC`, `ABORT` |
| `AttributeError` | comprehensive_test_fixer.py:56 | TestFailureAnalyzer.analyze... | `ABC`, `ABORT` |
| `AuditLogFactory` | __init__.py:20 | module | `ABC`, `ABORT` |
| `AUTH` | auth_starter.py:55 | AuthStarter.start_auth_service | `ABC`, `ABORT` |
| `Auth` | health_registration.py:73 | HealthRegistrationHelper._r... | `ABC`, `ABORT` |
| `auth` | coverage_reporter.py:280 | CoverageReporter._generate_... | `ABC`, `ABORT` |
| `auth\_audit\_logs` | models.py:69 | AuthAuditLog | `ABC`, `ABORT` |
| `AUTH\_BASE\_URL` | test_staging.py:31 | setup_staging_env | `ABC`, `ABORT` |
| `auth\_client` | comprehensive_import_scanner.py:153 | ComprehensiveImportScanner.... | `ABC`, `ABORT` |
| `auth\_client\_core` | comprehensive_import_scanner.py:153 | ComprehensiveImportScanner.... | `ABC`, `ABORT` |
| `auth\_code\_` | token_factory.py:238 | OAuthTokenFactory.create_au... | `ABC`, `ABORT` |
| `auth\_core` | coverage_config.py:18 | CoverageConfig | `ABC`, `ABORT` |
| `auth\_db` | __init__.py:14 | module | `ABC`, `ABORT` |
| `auth\_deps` | launcher.py:329 | DevLauncher._register_optim... | `ABC`, `ABORT` |
| `AUTH\_FAST\_TEST\_MODE` | connection.py:31 | AuthDatabase.__init__ | `ABC`, `ABORT` |
| `auth\_integration` | comprehensive_import_scanner.py:152 | ComprehensiveImportScanner.... | `ABC`, `ABORT` |
| `AUTH\_PORT` | launcher.py:385 | DevLauncher._set_env_var_de... | `ABC`, `ABORT` |
| `auth\_provider` | test_base.py:147 | AuthTestBase.assert_user_da... | `ABC`, `ABORT` |
| `auth\_reload` | config.py:207 | LauncherConfig.to_dict | `ABC`, `ABORT` |
| `auth\_service` | auto_fix_test_violations.py:93 | TestFileAnalyzer.find_test_... | `ABC`, `ABORT` |
| `auth\_service\_cloud` | connection.py:166 | AuthDatabase._get_cloud_sql... | `ABC`, `ABORT` |
| `AUTH\_SERVICE\_ENABLED` | service_config.py:234 | ServicesConfiguration._add_... | `ABC`, `ABORT` |
| `AUTH\_SERVICE\_HOST` | auth_starter.py:133 | AuthStarter._create_auth_env | `ABC`, `ABORT` |
| `auth\_service\_local` | connection.py:178 | AuthDatabase._get_local_con... | `ABC`, `ABORT` |
| `AUTH\_SERVICE\_NAME` | auth_starter.py:160 | AuthStarter._create_auth_env | `ABC`, `ABORT` |
| `AUTH\_SERVICE\_PORT` | auth_starter.py:132 | AuthStarter._create_auth_env | `ABC`, `ABORT` |
| `AUTH\_SERVICE\_URL` | config.py:84 | AuthConfig.get_auth_service... | `ABC`, `ABORT` |
| `auth\_sessions` | models.py:45 | AuthSession | `ABC`, `ABORT` |
| `auth\_startup` | service_startup.py:187 | ServiceStartupCoordinator.s... | `ABC`, `ABORT` |
| `auth\_tokens\_valid` | health_monitor.py:561 | HealthMonitor.get_cross_ser... | `ABC`, `ABORT` |
| `auth\_users` | models.py:15 | AuthUser | `ABC`, `ABORT` |
| `AuthAuditLog` | __init__.py:18 | module | `ABC`, `ABORT` |
| `AuthAuditRepository` | __init__.py:21 | module | `ABC`, `ABORT` |
| `AuthConstants` | auth_constants_migration.py:103 | AuthConstantsMigrator.__init__ | `ABC`, `ABORT` |
| `authenticate` | status_integration_analyzer.py:71 | IntegrationAnalyzer._check_... | `ABC`, `ABORT` |
| `authenticated` | audit_permissions.py:43 | analyze_route_file | `ABC`, `ABORT` |
| `authentication` | auth_routes.py:34 | module | `ABC`, `ABORT` |
| `AuthErrorConstants` | auth_constants_migration.py:105 | AuthConstantsMigrator.__init__ | `ABC`, `ABORT` |
| `author` | team_updates_formatter.py:96 | HumanFormatter.format_features | `ABC`, `ABORT` |
| `Authorization` | auth_routes.py:438 | oauth_callback | `ABC`, `ABORT` |
| `authorization\_code` | auth_routes.py:424 | oauth_callback | `ABC`, `ABORT` |
| `authorized\_redirect\_uris` | monitor_oauth_flow.py:51 | OAuthMonitor.check_oauth_co... | `ABC`, `ABORT` |
| `AuthSession` | __init__.py:17 | module | `ABC`, `ABORT` |
| `AuthSessionFactory` | __init__.py:16 | module | `ABC`, `ABORT` |
| `AuthSessionRepository` | __init__.py:20 | module | `ABC`, `ABORT` |
| `AuthTestBase` | __init__.py:14 | module | `ABC`, `ABORT` |
| `AuthTestClient` | __init__.py:18 | module | `ABC`, `ABORT` |
| `AuthTestMixin` | __init__.py:18 | module | `ABC`, `ABORT` |
| `AuthTestUtils` | __init__.py:15 | module | `ABC`, `ABORT` |
| `AuthUser` | __init__.py:16 | module | `ABC`, `ABORT` |
| `AuthUserFactory` | __init__.py:14 | module | `ABC`, `ABORT` |
| `AuthUserRepository` | __init__.py:19 | module | `ABC`, `ABORT` |
| `auto` | main.py:43 | _add_mode_arguments | `ABC`, `ABORT` |
| `auto\_approve\_score` | config_manager.py:27 | ConfigurationManager._get_r... | `ABC`, `ABORT` |
| `auto\_cleanup` | workflow_presets.py:29 | WorkflowPresets.get_minimal... | `ABC`, `ABORT` |
| `auto\_detection` | metadata_header_generator.py:103 | MetadataHeaderGenerator.gen... | `ABC`, `ABORT` |
| `AUTO\_FIX` | emergency_boundary_actions.py:237 | EmergencyActionSystem._crea... | `ABC`, `ABORT` |
| `auto\_review\_enabled` | config_manager.py:65 | ConfigurationManager._get_s... | `ABC`, `ABORT` |
| `auto\_review\_threshold` | config_manager.py:66 | ConfigurationManager._get_s... | `ABC`, `ABORT` |
| `auto\_score` | metadata_header_generator.py:109 | MetadataHeaderGenerator.gen... | `ABC`, `ABORT` |
| `AUTO\_SPLIT` | emergency_boundary_actions.py:215 | EmergencyActionSystem._crea... | `ABC`, `ABORT` |
| `AUTOCOMMIT` | test_config.py:122 | PostgresTestConfig.create_t... | `ABC`, `ABORT` |
| `autofix` | manage_workflows.py:81 | WorkflowManager._get_workfl... | `ABC`, `ABORT` |
| `automated` | audit_factory.py:194 | AuditLogFactory.create_acco... | `ABC`, `ABORT` |
| `AutonomousTestReviewer` | __init__.py:22 | module | `ABC`, `ABORT` |
| `aux` | system_diagnostics.py:88 | SystemDiagnostics.find_zomb... | `ABC`, `ABORT` |
| `Available` | startup_environment.py:141 | DependencyChecker._check_po... | `ABC`, `ABORT` |
| `available` | environment_validator_ports.py:101 | PortValidator._check_port_a... | `ABC`, `ABORT` |
| `available\_providers` | demo_real_llm_testing.py:62 | demo_environment_validation | `ABC`, `ABORT` |
| `avatar\_url` | token_factory.py:226 | OAuthTokenFactory.create_gi... | `ABC`, `ABORT` |
| `average` | real_service_test_metrics.py:93 | RealServiceTestMetrics.fina... | `ABC`, `ABORT` |
| `average\_coverage` | coverage_reporter.py:220 | CoverageReporter._analyze_c... | `ABC`, `ABORT` |
| `average\_duration` | generate_performance_report.py:42 | add_summary_timing | `ABC`, `ABORT` |
| `average\_value\_score` | business_value_test_index.py:566 | BusinessValueTestIndexer.ge... | `ABC`, `ABORT` |
| `avg\_complexity` | analyze_test_overlap.py:64 | TestOverlapAnalyzer.__init__ | `ABC`, `ABORT` |
| `avg\_file\_size` | boundary_enforcer_report_generator.py:125 | ConsoleReportPrinter._print... | `ABC`, `ABORT` |
| `avg\_ms` | validate_staging_health.py:165 | StagingPerformanceValidator... | `ABC`, `ABORT` |
| `AWS\_` | local_secrets_manager.py:181 | LocalSecretsManager._get_gi... | `ABC`, `ABORT` |
| `BACKEND` | dev_launcher_service.py:110 | ServiceManager._start_backe... | `ABC`, `ABORT` |
| `Backend` | build_staging.py:176 | StagingBuilder.health_check | `ABC`, `ABORT` |
| `backend` | auth_service.py:370 | AuthService._get_service_name | `ABC`, `ABORT` |
| `backend\_deps` | launcher.py:328 | DevLauncher._register_optim... | `ABC`, `ABORT` |
| `BACKEND\_PORT` | debug_uvicorn_recursion.py:19 | module | `ABC`, `ABORT` |
| `backend\_port` | config.py:202 | LauncherConfig.to_dict | `ABC`, `ABORT` |
| `backend\_reload` | config.py:137 | LauncherConfig.from_args | `ABC`, `ABORT` |
| `backend\_services` | status_renderer.py:72 | StatusReportRenderer._build... | `ABC`, `ABORT` |
| `backend\_startup` | service_startup.py:195 | ServiceStartupCoordinator.s... | `ABC`, `ABORT` |
| `BACKEND\_URL` | test_env.py:46 | TestEnvironment | `ABC`, `ABORT` |
| `backend\_ws` | test_websocket_connection_issue.py:104 | TestWebSocketConnectionIssu... | `ABC`, `ABORT` |
| `background\_tasks` | test_staging_startup.py:47 | StagingStartupTester.test_s... | `ABC`, `ABORT` |
| `backup` | type_checker.py:120 | TypeChecker._categorize_files | `ABC`, `ABORT` |
| `backup\_location` | metadata_header_generator.py:128 | MetadataHeaderGenerator.gen... | `ABC`, `ABORT` |
| `backups` | clean_slate_executor.py:24 | CleanSlateExecutor.__init__ | `ABC`, `ABORT` |
| `bad\_tests` | fake_test_scanner.py:242 | FakeTestScanner.generate_co... | `ABC`, `ABORT` |
| `balanced` | analyze_failures.py:192 | TestFailureAnalyzer._determ... | `ABC`, `ABORT` |
| `base` | check_schema_imports.py:166 | SchemaImportAnalyzer._is_sc... | `ABC`, `ABORT` |
| `base\_agent` | comprehensive_import_scanner.py:156 | ComprehensiveImportScanner.... | `ABC`, `ABORT` |
| `BASE\_URL` | test_staging.py:29 | setup_staging_env | `ABC`, `ABORT` |
| `base\_url` | verify_auth_config.py:53 | verify_environment_config | `ABC`, `ABORT` |
| `BaseExecutionEngine` | fix_comprehensive_imports.py:136 | ComprehensiveImportFixerV2.... | `ABC`, `ABORT` |
| `baseline\_tracking\_implementation` | metadata_header_generator.py:113 | MetadataHeaderGenerator.gen... | `ABC`, `ABORT` |
| `BaseWebSocketPayload` | deduplicate_types.py:93 | TypeDeduplicator._setup_web... | `ABC`, `ABORT` |
| `bash` | agent_tracking_helper.py:46 | AgentTrackingHelper | `ABC`, `ABORT` |
| `basic` | seed_staging_data.py:231 | StagingDataSeeder._generate... | `ABC`, `ABORT` |
| `basic\_optimization` | demo_real_llm_testing.py:74 | demo_environment_validation | `ABC`, `ABORT` |
| `batch\_fix\_results\_` | fix_test_batch.py:374 | main | `ABC`, `ABORT` |
| `bcrypt` | dependency_installer.py:102 | install_essential_packages_... | `ABC`, `ABORT` |
| `Bearer` | auth_models.py:42 | LoginResponse | `ABC`, `ABORT` |
| `bearer` | generate_openapi_spec.py:99 | _get_security_schemes | `ABC`, `ABORT` |
| `bearerAuth` | generate_openapi_spec.py:98 | _get_security_schemes | `ABC`, `ABORT` |
| `bearerFormat` | generate_openapi_spec.py:99 | _get_security_schemes | `ABC`, `ABORT` |
| `benchmark` | test_reviewer.py:229 | AutonomousTestReviewer._ide... | `ABC`, `ABORT` |
| `benchmark\_metadata` | benchmark_optimization.py:295 | TestExecutionBenchmark._gen... | `ABC`, `ABORT` |
| `benchmark\_report\_` | benchmark_optimization.py:390 | TestExecutionBenchmark._sav... | `ABC`, `ABORT` |
| `benchmark\_results` | benchmark_optimization.py:386 | TestExecutionBenchmark._sav... | `ABC`, `ABORT` |
| `benchmark\_version` | benchmark_optimization.py:298 | TestExecutionBenchmark._gen... | `ABC`, `ABORT` |
| `billing\_service` | fix_e2e_tests_comprehensive.py:60 | E2ETestFixer._get_common_fi... | `ABC`, `ABORT` |
| `bin` | config_setup_core.py:36 | get_venv_python_path | `ABC`, `ABORT` |
| `block\_commits\_without\_metadata` | config_manager.py:64 | ConfigurationManager._get_s... | `ABC`, `ABORT` |
| `BLOCK\_PIPELINE` | emergency_boundary_actions.py:204 | EmergencyActionSystem._crea... | `ABC`, `ABORT` |
| `blocks` | workflow_config_utils.py:56 | WorkflowConfigUtils._show_t... | `ABC`, `ABORT` |
| `blue` | verify_workflow_status.py:247 | OutputFormatter.display_table | `ABC`, `ABORT` |
| `body` | boundary_enforcer_function_checks.py:122 | FunctionAnalyzer.generate_r... | `ABC`, `ABORT` |
| `boolean\_state` | scan_string_literals.py:104 | StringLiteralCategorizer | `ABC`, `ABORT` |
| `both` | reset_clickhouse_final.py:122 | determine_reset_target | `ABC`, `ABORT` |
| `BOUNDARY` | boundary_monitor.py:198 | BoundaryMonitorIntegration.... | `ABC`, `ABORT` |
| `boundary\_check\_interval` | __main__.py:285 | create_parser | `ABC`, `ABORT` |
| `boundary\_monitor` | enhance_dev_launcher_boundaries.py:121 | enhance_launcher_main | `ABC`, `ABORT` |
| `bower\_components` | core.py:87 | ComplianceConfig._get_skip_... | `ABC`, `ABORT` |
| `Branch` | verify_workflow_status.py:250 | OutputFormatter.display_table | `ABC`, `ABORT` |
| `branch` | coverage_config.py:58 | CoverageConfig.get_coverage... | `ABC`, `ABORT` |
| `branch\_name` | test_workflows_with_act.py:191 | WorkflowTester.create_event... | `ABC`, `ABORT` |
| `breaking` | metadata_header_generator.py:98 | MetadataHeaderGenerator.gen... | `ABC`, `ABORT` |
| `brew` | dependency_services.py:61 | get_mac_pg_instructions | `ABC`, `ABORT` |
| `BROWSER` | startup_validator.py:69 | StartupValidator._handle_br... | `ABC`, `ABORT` |
| `budget` | manage_workflows.py:188 | _setup_budget_parser | `ABC`, `ABORT` |
| `bufsize` | utils.py:371 | create_subprocess | `ABC`, `ABORT` |
| `bugs` | team_updates_formatter.py:68 | HumanFormatter.format_execu... | `ABC`, `ABORT` |
| `build` | architecture_metrics.py:267 | ArchitectureMetrics._should... | `ABC`, `ABORT` |
| `builds` | deploy_to_gcp.py:427 | GCPDeployer.build_image_cloud | `ABC`, `ABORT` |
| `bulk` | test_session_cleanup.py:199 | TestSessionCleanupJob.test_... | `ABC`, `ABORT` |
| `business` | ultra_thinking_analyzer.py:188 | UltraThinkingAnalyzer._extr... | `ABC`, `ABORT` |
| `business\_logic` | ultra_thinking_analyzer.py:42 | UltraThinkingAnalyzer.analy... | `ABC`, `ABORT` |
| `business\_value` | demo_feature_flag_system.py:247 | demonstrate_business_value | `ABC`, `ABORT` |
| `business\_value\_test\_coverage` | business_value_test_index.py:118 | BusinessValueTestIndexer._l... | `ABC`, `ABORT` |
| `businessValue` | test_example_message_flow.py:289 | ExampleMessageFlowTestRunne... | `ABC`, `ABORT` |
| `by\_class` | test_size_validator.py:394 | TestSizeValidator.auto_spli... | `ABC`, `ABORT` |
| `by\_file` | analyze_mocks.py:222 | MockAnalyzer.generate_report | `ABC`, `ABORT` |
| `by\_type` | analyze_mocks.py:221 | MockAnalyzer.generate_report | `ABC`, `ABORT` |
| `bytes\_freed` | cleanup_generated_files.py:297 | main | `ABC`, `ABORT` |
| `CACHE` | launcher.py:341 | DevLauncher.check_environment | `ABC`, `ABORT` |
| `cache` | auto_fix_test_sizes.py:352 | TestFileSplitter._determine... | `ABC`, `ABORT` |
| `cache\_dir` | cache_manager.py:473 | CacheManager._get_cache_sta... | `ABC`, `ABORT` |
| `cache\_enabled` | test_backend_optimized.py:171 | OptimizedTestManager._creat... | `ABC`, `ABORT` |
| `cache\_entry\_counts` | cache_manager.py:478 | CacheManager._get_cache_sta... | `ABC`, `ABORT` |
| `cache\_file` | dependency_checker.py:424 | AsyncDependencyChecker.get_... | `ABC`, `ABORT` |
| `cache\_files\_exist` | cache_manager.py:474 | CacheManager._get_cache_sta... | `ABC`, `ABORT` |
| `cache\_hit\_rate` | seed_staging_data.py:285 | StagingDataSeeder._get_metr... | `ABC`, `ABORT` |
| `cache\_hits` | benchmark_optimization.py:183 | TestExecutionBenchmark._run... | `ABC`, `ABORT` |
| `cache\_size` | dependency_checker.py:425 | AsyncDependencyChecker.get_... | `ABC`, `ABORT` |
| `cache\_state` | startup_optimizer.py:597 | create_init_phase_steps | `ABC`, `ABORT` |
| `cache\_stats` | real_service_test_metrics.py:24 | RealServiceTestMetrics.__in... | `ABC`, `ABORT` |
| `cache\_ttl\_hours` | test_backend_optimized.py:181 | OptimizedTestManager._creat... | `ABC`, `ABORT` |
| `cache\_valid` | cache_manager.py:370 | CacheManager.get_cache_stats | `ABC`, `ABORT` |
| `cache\_validity` | startup_optimizer.py:598 | create_init_phase_steps | `ABC`, `ABORT` |
| `cache\_warming` | startup_optimizer.py:617 | create_prepare_phase_steps | `ABC`, `ABORT` |
| `CacheConfig` | validate_type_deduplication.py:59 | TypeDeduplicationValidator.... | `ABC`, `ABORT` |
| `CacheConstants` | auth_constants_migration.py:106 | AuthConstantsMigrator.__init__ | `ABC`, `ABORT` |
| `cached` | test_backend_optimized.py:260 | OptimizedTestManager._fallb... | `ABC`, `ABORT` |
| `cached\_at` | secret_cache.py:143 | SecretCache._cache_individu... | `ABC`, `ABORT` |
| `cached\_dependencies` | dependency_checker.py:423 | AsyncDependencyChecker.get_... | `ABC`, `ABORT` |
| `cached\_steps` | launcher.py:881 | DevLauncher._handle_cleanup | `ABC`, `ABORT` |
| `CacheEncryption` | cache_entry.py:77 | CacheEncryption.from_key_st... | `ABC`, `ABORT` |
| `CacheEntry` | cache_entry.py:44 | CacheEntry.from_dict | `ABC`, `ABORT` |
| `CacheManager` | cache_warmer.py:26 | CacheWarmer.__init__ | `ABC`, `ABORT` |
| `caching` | validate_workflow_config.py:25 | validate_config_structure | `ABC`, `ABORT` |
| `call\_site` | analyze_failures.py:149 | TestFailureAnalyzer._determ... | `ABC`, `ABORT` |
| `callback` | test_oauth_flows_auth.py:45 | TestSyntaxFix.test_oauth_en... | `ABC`, `ABORT` |
| `callback\_result` | audit_factory.py:176 | AuditLogFactory.create_oaut... | `ABC`, `ABORT` |
| `cancelled` | seed_staging_data.py:209 | StagingDataSeeder._get_opti... | `ABC`, `ABORT` |
| `canonical\_schema\_mapping` | check_schema_imports.py:396 | SchemaImportAnalyzer.export... | `ABC`, `ABORT` |
| `canonical\_schemas\_found` | check_schema_imports.py:294 | SchemaImportAnalyzer.analyz... | `ABC`, `ABORT` |
| `capabilities` | setup_assistant.py:38 | _get_assistant_metadata | `ABC`, `ABORT` |
| `capacity` | seed_staging_data.py:230 | StagingDataSeeder._generate... | `ABC`, `ABORT` |
| `categories` | add_test_markers.py:37 | TestMarkerAdder.get_markers... | `ABC`, `ABORT` |
| `categories\_scanned` | test_failure_scanner.py:199 | _finalize_scan_results | `ABC`, `ABORT` |
| `category` | test_refactor_helper.py:425 | TestRefactorHelper._strateg... | `ABC`, `ABORT` |
| `category\_breakdown` | validate_frontend_tests.py:201 | FrontendTestValidator._gene... | `ABC`, `ABORT` |
| `change\_classification` | metadata_header_generator.py:95 | MetadataHeaderGenerator.gen... | `ABC`, `ABORT` |
| `CHANGE\_ME` | secret_validator.py:75 | SecretValidator._is_invalid... | `ABC`, `ABORT` |
| `change\_me` | secret_validator.py:75 | SecretValidator._is_invalid... | `ABC`, `ABORT` |
| `change\_method` | audit_factory.py:122 | AuditLogFactory.create_pass... | `ABC`, `ABORT` |
| `changed` | team_updates_documentation_analyzer.py:178 | DocumentationAnalyzer._stat... | `ABC`, `ABORT` |
| `changes` | agent_tracking_helper.py:132 | AgentTrackingHelper._create... | `ABC`, `ABORT` |
| `CHECK` | environment_checker.py:37 | EnvironmentChecker.check_en... | `ABC`, `ABORT` |
| `check` | comprehensive_test_fixer.py:253 | TestFixer._should_be_async | `ABC`, `ABORT` |
| `check\_and\_fix\_attribute` | fix_test_batch.py:62 | TestAnalyzer.analyze_failure | `ABC`, `ABORT` |
| `check\_and\_fix\_import` | fix_test_batch.py:51 | TestAnalyzer.analyze_failure | `ABC`, `ABORT` |
| `check\_environment` | test_dev_user_flow.py:67 | TestDevUserCreation.test_de... | `ABC`, `ABORT` |
| `check\_netra` | import_management.py:49 | ImportManagementSystem.__in... | `ABC`, `ABORT` |
| `check\_same\_thread` | connection.py:49 | AuthDatabase.initialize | `ABC`, `ABORT` |
| `check\_suite\_url` | workflow_introspection.py:204 | WorkflowIntrospector.get_wo... | `ABC`, `ABORT` |
| `check\_validity` | startup_optimizer.py:598 | create_init_phase_steps | `ABC`, `ABORT` |
| `checked` | cache_warmer.py:60 | CacheWarmer._warm_migration... | `ABC`, `ABORT` |
| `Checking` | auth_constants_migration.py:283 | AuthConstantsMigrator.migra... | `ABC`, `ABORT` |
| `choco` | setup_act.py:49 | install_act | `ABC`, `ABORT` |
| `CI` | config_validator.py:274 | _detect_ci_environment | `ABC`, `ABORT` |
| `ci` | test_verify_workflow_status.py:106 | WorkflowStatusTester.test_t... | `ABC`, `ABORT` |
| `ci\_cd\_pipeline` | config_manager.py:55 | ConfigurationManager._get_i... | `ABC`, `ABORT` |
| `CircuitBreaker` | validate_type_deduplication.py:65 | TypeDeduplicationValidator.... | `ABC`, `ABORT` |
| `circular\_dependencies` | check_imports.py:33 | ImportAnalyzer.analyze_file | `ABC`, `ABORT` |
| `class` | architecture_scanner.py:133 | ArchitectureScanner._extrac... | `ABC`, `ABORT` |
| `class\_based` | auto_split_files.py:168 | FileSplitter._suggest_class... | `ABC`, `ABORT` |
| `class\_name` | check_schema_imports.py:390 | SchemaImportAnalyzer.export... | `ABC`, `ABORT` |
| `class\_to\_function` | test_refactor_helper.py:333 | TestRefactorHelper._analyze... | `ABC`, `ABORT` |
| `classes` | test_generator.py:58 | TestGenerator._generate_tes... | `ABC`, `ABORT` |
| `claude` | generate_fix.py:36 | AIFixGenerator._get_api_key | `ABC`, `ABORT` |
| `clean` | metadata_header_generator.py:56 | MetadataHeaderGenerator._ge... | `ABC`, `ABORT` |
| `clean\_slate\_` | clean_slate_executor.py:22 | CleanSlateExecutor.__init__ | `ABC`, `ABORT` |
| `CLEANUP` | launcher.py:188 | DevLauncher._graceful_shutdown | `ABC`, `ABORT` |
| `cleanup` | test_websocket_dev_mode.py:46 | WebSocketDevModeTest.__init__ | `ABC`, `ABORT` |
| `cleanup\_duration\_seconds` | test_session_cleanup.py:281 | TestSessionMaintenanceSched... | `ABC`, `ABORT` |
| `cleanup\_expired\_sessions` | test_session_cleanup.py:259 | TestSessionMaintenanceSched... | `ABC`, `ABORT` |
| `cleanup\_inactive\_sessions` | test_session_cleanup.py:260 | TestSessionMaintenanceSched... | `ABC`, `ABORT` |
| `cleanup\_monitoring` | enhance_dev_launcher_boundaries.py:148 | enhance_launcher_main | `ABC`, `ABORT` |
| `cleanup\_timestamp` | test_session_cleanup.py:282 | TestSessionMaintenanceSched... | `ABC`, `ABORT` |
| `clear` | service_discovery.py:125 | module | `ABC`, `ABORT` |
| `ClickHouse` | categorize_tests.py:250 | TestCategorizer._extract_se... | `ABC`, `ABORT` |
| `clickhouse` | business_value_test_index.py:349 | BusinessValueTestIndexer._d... | `ABC`, `ABORT` |
| `CLICKHOUSE\_` | config_validator.py:282 | _extract_env_overrides | `ABC`, `ABORT` |
| `clickhouse\_connect` | environment_validator_dependencies.py:202 | DependencyValidator._check_... | `ABC`, `ABORT` |
| `clickhouse\_connection` | environment_validator.py:203 | EnvironmentValidator.test_c... | `ABC`, `ABORT` |
| `clickhouse\_connectivity` | environment_validator.py:409 | EnvironmentValidator.genera... | `ABC`, `ABORT` |
| `CLICKHOUSE\_DATABASE` | reset_clickhouse.py:15 | module | `ABC`, `ABORT` |
| `CLICKHOUSE\_DB` | dev_launcher_secrets.py:166 | EnhancedSecretLoader._get_s... | `ABC`, `ABORT` |
| `CLICKHOUSE\_DEFAULT\_PASSWORD` | dev_launcher_secrets.py:109 | EnhancedSecretLoader._get_s... | `ABC`, `ABORT` |
| `CLICKHOUSE\_DEVELOPMENT\_PASSWORD` | dev_launcher_secrets.py:110 | EnhancedSecretLoader._get_s... | `ABC`, `ABORT` |
| `CLICKHOUSE\_HOST` | dev_launcher_secrets.py:163 | EnhancedSecretLoader._get_s... | `ABC`, `ABORT` |
| `clickhouse\_host\_url\_placeholder` | dev_launcher_secrets.py:163 | EnhancedSecretLoader._get_s... | `ABC`, `ABORT` |
| `clickhouse\_http` | port_manager.py:413 | PortManager.get_recommended... | `ABC`, `ABORT` |
| `CLICKHOUSE\_HTTP\_PORT` | database_connector.py:158 | DatabaseConnector._construc... | `ABC`, `ABORT` |
| `clickhouse\_init` | comprehensive_import_scanner.py:157 | ComprehensiveImportScanner.... | `ABC`, `ABORT` |
| `clickhouse\_native` | port_manager.py:414 | PortManager.get_recommended... | `ABC`, `ABORT` |
| `CLICKHOUSE\_NATIVE\_PORT` | service_config.py:92 | ServicesConfiguration | `ABC`, `ABORT` |
| `CLICKHOUSE\_PASSWORD` | reset_clickhouse.py:14 | module | `ABC`, `ABORT` |
| `CLICKHOUSE\_PORT` | dev_launcher_secrets.py:164 | EnhancedSecretLoader._get_s... | `ABC`, `ABORT` |
| `CLICKHOUSE\_SECURE` | validate_staging_config.py:263 | check_clickhouse_connection | `ABC`, `ABORT` |
| `CLICKHOUSE\_SHARED\_HOST` | service_config.py:99 | ServicesConfiguration | `ABC`, `ABORT` |
| `CLICKHOUSE\_URL` | test_backend.py:82 | _create_test_environment_dict | `ABC`, `ABORT` |
| `CLICKHOUSE\_USER` | dev_launcher_secrets.py:165 | EnhancedSecretLoader._get_s... | `ABC`, `ABORT` |
| `ClickHouseClient` | categorize_tests.py:63 | TestCategorizer._get_clickh... | `ABC`, `ABORT` |
| `ClickHouseQueryError` | fix_comprehensive_imports.py:98 | ComprehensiveImportFixerV2.... | `ABC`, `ABORT` |
| `client` | real_test_requirements_enforcer.py:239 | MockComponentVisitor.visit_... | `ABC`, `ABORT` |
| `client\_id` | auth_routes.py:421 | oauth_callback | `ABC`, `ABORT` |
| `client\_id\_prefix` | environment_validator.py:291 | EnvironmentValidator.valida... | `ABC`, `ABORT` |
| `client\_info` | test_security.py:206 | TestXSSPrevention.test_user... | `ABC`, `ABORT` |
| `client\_secret` | auth_routes.py:422 | oauth_callback | `ABC`, `ABORT` |
| `ClientMessage` | validate_type_deduplication.py:77 | TypeDeduplicationValidator.... | `ABC`, `ABORT` |
| `CLIHandler` | __init__.py:17 | module | `ABC`, `ABORT` |
| `clock` | unicode_utils.py:92 | module | `ABC`, `ABORT` |
| `close` | database_connector.py:642 | DatabaseConnector._cleanup_... | `ABC`, `ABORT` |
| `closed` | cleanup_staging_environments.py:99 | StagingEnvironmentCleaner.c... | `ABC`, `ABORT` |
| `Cloud` | config.py:314 | LauncherConfig._print_servi... | `ABC`, `ABORT` |
| `cloud` | reset_clickhouse_auto.py:153 | determine_target_configs | `ABC`, `ABORT` |
| `cloud\_sql\_proxy` | validate_staging_config.py:364 | check_gcp_configuration | `ABC`, `ABORT` |
| `cloudsql` | validate_staging_config.py:96 | parse_database_url | `ABC`, `ABORT` |
| `cls` | analyze_test_overlap.py:200 | TestOverlapAnalyzer._extrac... | `ABC`, `ABORT` |
| `cmd` | test_launcher_process.py:189 | TestAdvancedProcessManager.... | `ABC`, `ABORT` |
| `cmdline` | cleanup_test_processes.py:61 | find_test_processes | `ABC`, `ABORT` |
| `code` | auth_routes.py:420 | oauth_callback | `ABC`, `ABORT` |
| `code\_lines` | test_size_validator.py:314 | TestSizeValidator._analyze_... | `ABC`, `ABORT` |
| `code\_quality` | architecture_scanner_quality.py:146 | QualityScanner._find_qualit... | `ABC`, `ABORT` |
| `code\_quality\_issues` | architecture_metrics.py:51 | ArchitectureMetrics._calcul... | `ABC`, `ABORT` |
| `code\_review\_` | code_review_reporter.py:175 | CodeReviewReporter.save_report | `ABC`, `ABORT` |
| `code\_review\_tools` | config_manager.py:56 | ConfigurationManager._get_i... | `ABC`, `ABORT` |
| `code\_snippet` | architecture_scanner_quality.py:61 | QualityScanner._find_stub_p... | `ABC`, `ABORT` |
| `CodeReviewer` | __init__.py:16 | module | `ABC`, `ABORT` |
| `collection\_warnings` | generate_test_audit.py:115 | check_test_health | `ABC`, `ABORT` |
| `column\_name` | scan_string_literals.py:85 | StringLiteralCategorizer | `ABC`, `ABORT` |
| `com` | __main__.py:405 | handle_service_configuration | `ABC`, `ABORT` |
| `combined\_recommendations` | fake_test_scanner.py:243 | FakeTestScanner.generate_co... | `ABC`, `ABORT` |
| `command` | act_wrapper.py:204 | create_parser | `ABC`, `ABORT` |
| `command\_timeout` | connection.py:171 | AuthDatabase._get_cloud_sql... | `ABC`, `ABORT` |
| `Commands` | test_refactor_helper.py:671 | main | `ABC`, `ABORT` |
| `comments` | metadata_header_generator.py:108 | MetadataHeaderGenerator.gen... | `ABC`, `ABORT` |
| `commit` | agent_tracking_helper.py:84 | AgentTrackingHelper._get_gi... | `ABC`, `ABORT` |
| `commit\_sha` | test_workflows_with_act.py:192 | WorkflowTester.create_event... | `ABC`, `ABORT` |
| `commit\_summary` | team_updates_formatter.py:33 | HumanFormatter.format_full_... | `ABC`, `ABORT` |
| `commits` | team_updates_git_analyzer.py:29 | GitAnalyzer.analyze | `ABC`, `ABORT` |
| `comparison` | benchmark_optimization.py:37 | TestExecutionBenchmark.__in... | `ABC`, `ABORT` |
| `compatible` | environment_validator_dependencies.py:77 | DependencyValidator._valida... | `ABC`, `ABORT` |
| `Compiling` | filter_patterns.py:138 | module | `ABC`, `ABORT` |
| `COMPLETE` | fix_missing_functions.py:123 | main | `ABC`, `ABORT` |
| `complete\_` | test_refactor_helper.py:199 | TestRefactorHelper._determi... | `ABC`, `ABORT` |
| `completed` | force_cancel_workflow.py:83 | _print_run_info | `ABC`, `ABORT` |
| `completed\_` | test_phase3_multiprocessing.py:68 | TestParallelExecutor.slow_task | `ABC`, `ABORT` |
| `completed\_at` | seed_staging_data.py:263 | StagingDataSeeder._build_op... | `ABC`, `ABORT` |
| `completedAt` | workflow_introspection.py:153 | WorkflowIntrospector.get_ru... | `ABC`, `ABORT` |
| `complex\_workflows` | demo_real_llm_testing.py:74 | demo_environment_validation | `ABC`, `ABORT` |
| `complexity` | test_generator.py:146 | _generate_single_function_t... | `ABC`, `ABORT` |
| `complexity\_boundary` | boundary_enforcer_system_checks.py:179 | ViolationFactory.create_com... | `ABC`, `ABORT` |
| `complexity\_debt` | boundary_enforcer_report_generator.py:127 | ConsoleReportPrinter._print... | `ABC`, `ABORT` |
| `complexity\_delta` | metadata_header_generator.py:121 | MetadataHeaderGenerator.gen... | `ABC`, `ABORT` |
| `COMPLEXITY\_LIMIT` | boundary_enforcer_system_checks.py:180 | ViolationFactory.create_com... | `ABC`, `ABORT` |
| `complexity\_score` | function_complexity_analyzer.py:390 | _convert_results_to_json | `ABC`, `ABORT` |
| `compliance` | business_value_test_index.py:392 | BusinessValueTestIndexer._d... | `ABC`, `ABORT` |
| `compliance\_rate` | check_test_compliance.py:136 | scan_test_files | `ABC`, `ABORT` |
| `compliance\_score` | core.py:171 | _build_summary | `ABC`, `ABORT` |
| `compliance\_scores` | architecture_dashboard_html.py:51 | DashboardHTMLComponents.gen... | `ABC`, `ABORT` |
| `compliance\_status` | enforce_limits.py:207 | EnforcementReporter.generat... | `ABC`, `ABORT` |
| `compliance\_trends` | team_updates_compliance_analyzer.py:31 | ComplianceAnalyzer.analyze | `ABC`, `ABORT` |
| `compliance\_violations` | team_updates_compliance_analyzer.py:32 | ComplianceAnalyzer.analyze | `ABC`, `ABORT` |
| `ComplianceConfig` | __init__.py:15 | module | `ABC`, `ABORT` |
| `ComplianceReporter` | __init__.py:19 | module | `ABC`, `ABORT` |
| `ComplianceResults` | __init__.py:14 | module | `ABC`, `ABORT` |
| `compliant` | team_updates_sync.py:89 | generate_simple_report | `ABC`, `ABORT` |
| `Component` | metadata_header_generator.py:76 | MetadataHeaderGenerator.gen... | `ABC`, `ABORT` |
| `component` | auto_split_files.py:110 | FileSplitter._analyze_types... | `ABC`, `ABORT` |
| `component\_coverage` | business_value_test_index.py:593 | BusinessValueTestIndexer.ge... | `ABC`, `ABORT` |
| `component\_details` | status_types.py:167 | ReportSections | `ABC`, `ABORT` |
| `component\_name` | scan_string_literals.py:79 | StringLiteralCategorizer | `ABC`, `ABORT` |
| `components` | business_value_test_index.py:76 | BusinessValueTestIndexer.__... | `ABC`, `ABORT` |
| `components\_covered` | business_value_test_index.py:567 | BusinessValueTestIndexer.ge... | `ABC`, `ABORT` |
| `compose` | business_value_test_index.py:344 | BusinessValueTestIndexer._d... | `ABC`, `ABORT` |
| `comprehensive` | demo_real_llm_testing.py:188 | demo_test_environment_orche... | `ABC`, `ABORT` |
| `comprehensive\_fix\_` | comprehensive_test_fixer.py:406 | BatchProcessor.generate_report | `ABC`, `ABORT` |
| `compute\_hours` | cleanup_staging_environments.py:133 | StagingEnvironmentCleaner.g... | `ABC`, `ABORT` |
| `computer` | __main__.py:381 | handle_service_configuration | `ABC`, `ABORT` |
| `Conclusion` | verify_workflow_status.py:249 | OutputFormatter.display_table | `ABC`, `ABORT` |
| `conclusion` | cleanup_workflow_runs.py:254 | _clean_workflow_runs | `ABC`, `ABORT` |
| `concurrency` | workflow_validator.py:152 | WorkflowValidator._check_un... | `ABC`, `ABORT` |
| `concurrent` | auto_fix_test_sizes.py:348 | TestFileSplitter._determine... | `ABC`, `ABORT` |
| `ConcurrentService` | test_launcher_health.py:334 | TestHealthStatusManagement.... | `ABC`, `ABORT` |
| `conda` | dependency_checker.py:28 | DependencyType | `ABC`, `ABORT` |
| `condensed\_groups` | log_filter.py:230 | LogFilter.get_filter_stats | `ABC`, `ABORT` |
| `conditional\_branches` | auto_decompose_functions.py:262 | FunctionDecomposer._suggest... | `ABC`, `ABORT` |
| `conditionals` | function_complexity_analyzer.py:62 | FunctionVisitor._analyze_fu... | `ABC`, `ABORT` |
| `conditions` | cleanup_staging_environments.py:63 | StagingEnvironmentCleaner.g... | `ABC`, `ABORT` |
| `confidence` | generate_security_report.py:126 | _format_vulnerability_list | `ABC`, `ABORT` |
| `CONFIDENCE\_END` | generate_fix.py:226 | AIFixGenerator._add_respons... | `ABC`, `ABORT` |
| `CONFIDENCE\_START` | generate_fix.py:226 | AIFixGenerator._add_respons... | `ABC`, `ABORT` |
| `CONFIG` | config.py:296 | LauncherConfig.show_configu... | `ABC`, `ABORT` |
| `Config` | validate_type_deduplication.py:166 | TypeDeduplicationValidator.... | `ABC`, `ABORT` |
| `config` | audit_permissions.py:93 | main | `ABC`, `ABORT` |
| `config\_endpoint` | test_websocket_dev_mode.py:40 | WebSocketDevModeTest.__init__ | `ABC`, `ABORT` |
| `config\_exists` | metadata_enabler.py:127 | MetadataTrackingEnabler._ca... | `ABC`, `ABORT` |
| `config\_fixes` | align_test_imports.py:411 | TestImportAligner.generate_... | `ABC`, `ABORT` |
| `config\_key` | scan_string_literals.py:67 | StringLiteralCategorizer | `ABC`, `ABORT` |
| `config\_name` | scan_string_literals.py:69 | StringLiteralCategorizer | `ABC`, `ABORT` |
| `config\_param` | scan_string_literals.py:68 | StringLiteralCategorizer | `ABC`, `ABORT` |
| `config\_value` | scan_string_literals.py:127 | StringLiteralCategorizer.ca... | `ABC`, `ABORT` |
| `Configuration` | status_manager.py:123 | StatusManager.print_status | `ABC`, `ABORT` |
| `configuration` | fix_schema_imports.py:35 | SchemaImportFixer.move_sche... | `ABC`, `ABORT` |
| `configuration\_exists` | status_manager.py:81 | StatusManager.get_status | `ABC`, `ABORT` |
| `configuration\_loading` | test_staging_startup.py:39 | StagingStartupTester.test_s... | `ABC`, `ABORT` |
| `ConfigurationManager` | __init__.py:18 | module | `ABC`, `ABORT` |
| `configure\_gcp\_staging\_environment` | verify_staging_tests.py:103 | verify_test_runner_config | `ABC`, `ABORT` |
| `CONFIGURED` | demo_real_llm_testing.py:124 | demo_real_llm_configuration | `ABC`, `ABORT` |
| `Configured` | status_section_renderers.py:116 | ComponentDetailsRenderer._f... | `ABC`, `ABORT` |
| `configured` | status_integration_analyzer.py:55 | IntegrationAnalyzer._check_... | `ABC`, `ABORT` |
| `CONFIRMATION` | reset_clickhouse.py:224 | print_confirmation_header | `ABC`, `ABORT` |
| `conflicts` | environment_validator_ports.py:24 | PortValidator.validate_requ... | `ABC`, `ABORT` |
| `conftest\_files` | generate_test_audit.py:64 | analyze_test_structure | `ABC`, `ABORT` |
| `connect\_args` | connection.py:68 | AuthDatabase.initialize | `ABC`, `ABORT` |
| `CONNECTED` | environment_validator.py:408 | EnvironmentValidator.genera... | `ABC`, `ABORT` |
| `Connected` | startup_environment.py:130 | DependencyChecker._check_redis | `ABC`, `ABORT` |
| `connected` | database_connector.py:46 | ConnectionStatus | `ABC`, `ABORT` |
| `connected\_clients` | environment_validator.py:269 | EnvironmentValidator.test_r... | `ABC`, `ABORT` |
| `connecting` | database_connector.py:45 | ConnectionStatus | `ABC`, `ABORT` |
| `connection` | auto_fix_test_sizes.py:342 | TestFileSplitter._determine... | `ABC`, `ABORT` |
| `connection\_error` | analyze_failures.py:48 | TestFailureAnalyzer | `ABC`, `ABORT` |
| `connection\_time` | environment_validator_database.py:95 | DatabaseValidator._test_pos... | `ABC`, `ABORT` |
| `ConnectionManager` | e2e_import_fixer_comprehensive.py:105 | E2EImportFixer.__init__ | `ABC`, `ABORT` |
| `consecutive\_failures` | health_monitor.py:427 | HealthMonitor.get_grace_per... | `ABC`, `ABORT` |
| `conservative` | analyze_failures.py:194 | TestFailureAnalyzer._determ... | `ABC`, `ABORT` |
| `consistently\_failing` | fake_test_scanner.py:298 | FakeTestScanner.generate_co... | `ABC`, `ABORT` |
| `console` | validate_type_deduplication.py:323 | TypeDeduplicationValidator.... | `ABC`, `ABORT` |
| `consolidated` | status_agent_analyzer.py:71 | AgentSystemAnalyzer._determ... | `ABC`, `ABORT` |
| `constraint` | seed_staging_data.py:230 | StagingDataSeeder._generate... | `ABC`, `ABORT` |
| `contact` | generate_openapi_spec.py:64 | _add_contact_info | `ABC`, `ABORT` |
| `content` | auto_fix_test_violations.py:531 | TestFileSplitter._create_sp... | `ABC`, `ABORT` |
| `content\_end` | auto_split_files.py:160 | FileSplitter._suggest_class... | `ABC`, `ABORT` |
| `content\_pattern` | auto_split_files.py:100 | FileSplitter._analyze_types... | `ABC`, `ABORT` |
| `content\_preview` | test_refactor_helper.py:605 | TestRefactorHelper.generate... | `ABC`, `ABORT` |
| `content\_similarity` | analyze_test_overlap.py:373 | TestOverlapAnalyzer._genera... | `ABC`, `ABORT` |
| `content\_start` | auto_split_files.py:159 | FileSplitter._suggest_class... | `ABC`, `ABORT` |
| `context` | analyze_mocks.py:276 | MockAnalyzer.export_unjusti... | `ABC`, `ABORT` |
| `continuous` | types.py:34 | ReviewMode | `ABC`, `ABORT` |
| `contributors` | team_updates_formatter.py:72 | HumanFormatter.format_execu... | `ABC`, `ABORT` |
| `conversation\_id` | metadata_header_generator.py:113 | MetadataHeaderGenerator.gen... | `ABC`, `ABORT` |
| `conversion` | test_example_message_flow.py:289 | ExampleMessageFlowTestRunne... | `ABC`, `ABORT` |
| `conversion\_environment` | fix_e2e_tests_comprehensive.py:50 | E2ETestFixer._get_common_fi... | `ABC`, `ABORT` |
| `core` | auto_fix_test_sizes.py:359 | TestFileSplitter._determine... | `ABC`, `ABORT` |
| `corpus\_admin` | comprehensive_import_scanner.py:156 | ComprehensiveImportScanner.... | `ABC`, `ABORT` |
| `corpus\_metrics` | function_checker.py:76 | FunctionChecker._is_example... | `ABC`, `ABORT` |
| `CorpusOperation` | fix_all_import_issues.py:68 | ComprehensiveImportFixer._b... | `ABC`, `ABORT` |
| `CORS` | launcher.py:737 | DevLauncher._start_health_m... | `ABC`, `ABORT` |
| `cors` | validate_staging_health.py:214 | StagingSecurityValidator.va... | `ABC`, `ABORT` |
| `cors\_enabled` | health_monitor.py:76 | HealthStatus.update_cross_s... | `ABC`, `ABORT` |
| `cors\_headers\_required` | service_discovery.py:134 | ServiceDiscovery.register_s... | `ABC`, `ABORT` |
| `cors\_metadata` | service_discovery.py:130 | ServiceDiscovery.register_s... | `ABC`, `ABORT` |
| `cors\_metrics` | health_monitor.py:592 | HealthMonitor.get_cross_ser... | `ABC`, `ABORT` |
| `CORS\_ORIGINS` | main.py:143 | module | `ABC`, `ABORT` |
| `cors\_validation` | test_websocket_dev_mode.py:42 | WebSocketDevModeTest.__init__ | `ABC`, `ABORT` |
| `cost` | seed_staging_data.py:229 | StagingDataSeeder._generate... | `ABC`, `ABORT` |
| `cost\_budget\_daily` | validate_workflow_config.py:201 | _print_config_details | `ABC`, `ABORT` |
| `cost\_budget\_monthly` | validate_workflow_config.py:202 | _print_config_details | `ABC`, `ABORT` |
| `cost\_control` | manage_workflows.py:130 | WorkflowManager.set_cost_bu... | `ABC`, `ABORT` |
| `cost\_monitoring` | workflow_presets.py:29 | WorkflowPresets.get_minimal... | `ABC`, `ABORT` |
| `cost\_optimization` | business_value_test_index.py:99 | BusinessValueTestIndexer.__... | `ABC`, `ABORT` |
| `cost\_optimized` | manage_workflows.py:196 | _setup_utility_parsers | `ABC`, `ABORT` |
| `cost\_per\_request` | seed_staging_data.py:284 | StagingDataSeeder._get_metr... | `ABC`, `ABORT` |
| `cost\_savings\_calculator` | fix_e2e_tests_comprehensive.py:51 | E2ETestFixer._get_common_fi... | `ABC`, `ABORT` |
| `cost\_savings\_estimate` | benchmark_optimization.py:252 | TestExecutionBenchmark._com... | `ABC`, `ABORT` |
| `CostOptimizer` | fast_import_checker.py:157 | fix_known_import_issues | `ABC`, `ABORT` |
| `Count` | workflow_validator.py:187 | WorkflowValidator._display_... | `ABC`, `ABORT` |
| `count` | architecture_dashboard_tables.py:87 | DashboardTableRenderers._ge... | `ABC`, `ABORT` |
| `Cover` | coverage_config.py:49 | CoverageConfig | `ABC`, `ABORT` |
| `coverage` | coverage_reporter.py:207 | CoverageReporter._analyze_c... | `ABC`, `ABORT` |
| `coverage\_delta` | metadata_header_generator.py:122 | MetadataHeaderGenerator.gen... | `ABC`, `ABORT` |
| `coverage\_distribution` | coverage_reporter.py:214 | CoverageReporter._analyze_c... | `ABC`, `ABORT` |
| `coverage\_drop\_threshold` | config_manager.py:46 | ConfigurationManager._get_m... | `ABC`, `ABORT` |
| `coverage\_gap` | report_generator.py:101 | ReportGenerator._generate_j... | `ABC`, `ABORT` |
| `coverage\_gaps` | business_value_test_index.py:615 | BusinessValueTestIndexer.ge... | `ABC`, `ABORT` |
| `coverage\_goal` | report_generator.py:100 | ReportGenerator._generate_j... | `ABC`, `ABORT` |
| `coverage\_info` | team_updates_formatter.py:126 | HumanFormatter.format_test_... | `ABC`, `ABORT` |
| `coverage\_percent` | generate_report.py:37 | _get_summary_rows | `ABC`, `ABORT` |
| `coverage\_percentage` | business_value_test_index.py:568 | BusinessValueTestIndexer.ge... | `ABC`, `ABORT` |
| `coverage\_reports` | coverage_config.py:34 | CoverageConfig | `ABC`, `ABORT` |
| `coverage\_score` | generate_wip_report.py:148 | WIPReportGenerator.calculat... | `ABC`, `ABORT` |
| `CoverageConfig` | __init__.py:9 | module | `ABC`, `ABORT` |
| `CoverageReporter` | __init__.py:9 | module | `ABC`, `ABORT` |
| `covered` | analyze_coverage.py:17 | module | `ABC`, `ABORT` |
| `covered\_lines` | analyze_coverage.py:17 | module | `ABC`, `ABORT` |
| `cpp` | agent_tracking_helper.py:34 | AgentTrackingHelper | `ABC`, `ABORT` |
| `cpu\_bound` | parallel_executor.py:26 | TaskType | `ABC`, `ABORT` |
| `cpu\_count` | startup_environment.py:46 | StartupEnvironment._record_... | `ABC`, `ABORT` |
| `cpu\_intensive` | test_backend_optimized.py:75 | module | `ABC`, `ABORT` |
| `cpu\_result` | test_phase3_multiprocessing.py:334 | test_phase3_integration | `ABC`, `ABORT` |
| `cpu\_task\_` | test_phase3_multiprocessing.py:378 | disabled_test_speedup_targe... | `ABC`, `ABORT` |
| `cpu\_workers` | parallel_executor.py:290 | ParallelExecutor.get_perfor... | `ABC`, `ABORT` |
| `crash\_` | crash_recovery_models.py:78 | CrashReport | `ABC`, `ABORT` |
| `CrashReport` | crash_recovery_models.py:129 | module | `ABC`, `ABORT` |
| `CrashSeverity` | crash_recovery_models.py:125 | module | `ABC`, `ABORT` |
| `CrashStatistics` | crash_recovery_models.py:132 | module | `ABC`, `ABORT` |
| `create` | ultra_thinking_analyzer.py:175 | UltraThinkingAnalyzer._iden... | `ABC`, `ABORT` |
| `create\_` | auto_split_files.py:256 | FileSplitter._group_functio... | `ABC`, `ABORT` |
| `create\_autospec` | analyze_mocks.py:45 | MockAnalyzer.__init__ | `ABC`, `ABORT` |
| `CREATE\_ISSUES` | emergency_boundary_actions.py:248 | EmergencyActionSystem._crea... | `ABC`, `ABORT` |
| `create\_module` | comprehensive_test_fixer.py:70 | TestFailureAnalyzer.analyze... | `ABC`, `ABORT` |
| `create\_new` | config_validator.py:224 | ConfigDecisionEngine.get_fa... | `ABC`, `ABORT` |
| `create\_review\_config` | __init__.py:14 | module | `ABC`, `ABORT` |
| `create\_review\_data` | __init__.py:15 | module | `ABC`, `ABORT` |
| `created\_at` | session_manager.py:66 | SessionManager.create_session | `ABC`, `ABORT` |
| `created\_for` | seed_staging_data.py:180 | StagingDataSeeder.seed_thre... | `ABC`, `ABORT` |
| `createMockComponent` | real_test_requirements_enforcer.py:71 | RealTestRequirementsEnforce... | `ABC`, `ABORT` |
| `creation\_method` | audit_factory.py:139 | AuditLogFactory.create_toke... | `ABC`, `ABORT` |
| `creationflags` | utils.py:383 | create_subprocess | `ABC`, `ABORT` |
| `creationTimestamp` | cleanup_staging_environments.py:60 | StagingEnvironmentCleaner.g... | `ABC`, `ABORT` |
| `creators` | auto_split_files.py:257 | FileSplitter._group_functio... | `ABC`, `ABORT` |
| `CredentialConstants` | auth_constants_migration.py:102 | AuthConstantsMigrator.__init__ | `ABC`, `ABORT` |
| `CRITICAL` | emergency_boundary_actions.py:49 | EmergencyActionSystem.asses... | `ABC`, `ABORT` |
| `Critical` | config_manager.py:30 | ConfigurationManager._get_r... | `ABC`, `ABORT` |
| `critical` | architecture_dashboard_html.py:135 | DashboardHTMLComponents._ge... | `ABC`, `ABORT` |
| `critical\_alerts` | team_updates_formatter.py:29 | HumanFormatter.format_full_... | `ABC`, `ABORT` |
| `critical\_failures` | environment_validator.py:428 | EnvironmentValidator.genera... | `ABC`, `ABORT` |
| `critical\_files` | fake_test_scanner.py:89 | FakeTestScanner.scan_all_tests | `ABC`, `ABORT` |
| `critical\_issues` | comprehensive_import_scanner.py:87 | ComprehensiveScanReport.to_... | `ABC`, `ABORT` |
| `critical\_paths` | test_generator.py:59 | TestGenerator._generate_tes... | `ABC`, `ABORT` |
| `critical\_test\_count` | business_value_test_index.py:603 | BusinessValueTestIndexer.ge... | `ABC`, `ABORT` |
| `critical\_test\_percentage` | business_value_test_index.py:604 | BusinessValueTestIndexer.ge... | `ABC`, `ABORT` |
| `criticality` | test_reviewer.py:97 | AutonomousTestReviewer._per... | `ABC`, `ABORT` |
| `cross\_category\_overlaps` | analyze_test_overlap.py:410 | TestOverlapAnalyzer._genera... | `ABC`, `ABORT` |
| `cross\_service` | health_monitor.py:580 | HealthMonitor.get_cross_ser... | `ABC`, `ABORT` |
| `CROSS\_SERVICE\_AUTH\_TOKEN` | launcher.py:407 | DevLauncher._ensure_cross_s... | `ABC`, `ABORT` |
| `cross\_service\_integration` | health_monitor.py:558 | HealthMonitor.get_cross_ser... | `ABC`, `ABORT` |
| `cross\_service\_status` | health_monitor.py:72 | HealthStatus.update_cross_s... | `ABC`, `ABORT` |
| `cross\_service\_token` | service_discovery.py:177 | ServiceDiscovery.get_cross_... | `ABC`, `ABORT` |
| `cryptography` | setup_act.py:120 | install_dependencies | `ABC`, `ABORT` |
| `csharp` | agent_tracking_helper.py:38 | AgentTrackingHelper | `ABC`, `ABORT` |
| `CSV` | health_monitor.py:266 | HealthMonitor._verify_windo... | `ABC`, `ABORT` |
| `csv` | remove_test_stubs.py:269 | TestStubDetector.generate_r... | `ABC`, `ABORT` |
| `current` | check_netra_backend_imports.py:298 | ImportAnalyzer.export_issue... | `ABC`, `ABORT` |
| `current\_directory` | system_diagnostics.py:295 | SystemDiagnostics.get_syste... | `ABC`, `ABORT` |
| `current\_lines` | decompose_functions.py:108 | suggest_decomposition | `ABC`, `ABORT` |
| `current\_password` | test_client.py:139 | AuthTestClient.change_password | `ABC`, `ABORT` |
| `custom` | permission_factory.py:169 | PermissionFactory.create_cu... | `ABC`, `ABORT` |
| `customer\_value\_features` | business_value_test_index.py:397 | BusinessValueTestIndexer._d... | `ABC`, `ABORT` |
| `cwd` | utils.py:376 | create_subprocess | `ABC`, `ABORT` |
| `cyan` | act_wrapper.py:134 | ACTWrapper._create_workflow... | `ABC`, `ABORT` |
| `cypress` | cleanup_test_processes.py:70 | find_test_processes | `ABC`, `ABORT` |
| `daily` | seed_staging_data.py:232 | StagingDataSeeder._generate... | `ABC`, `ABORT` |
| `daily\_audit\_report` | config_manager.py:47 | ConfigurationManager._get_m... | `ABC`, `ABORT` |
| `daily\_limit` | manage_workflows.py:134 | WorkflowManager.set_cost_bu... | `ABC`, `ABORT` |
| `daily\_savings\_usd` | benchmark_optimization.py:286 | TestExecutionBenchmark._est... | `ABC`, `ABORT` |
| `darwin` | dependency_services.py:49 | get_os_specific_pg_instruct... | `ABC`, `ABORT` |
| `data` | test_session_management.py:161 | TestSessionRefresh.test_ref... | `ABC`, `ABORT` |
| `data\_analysis` | setup_assistant.py:18 | _get_assistant_tools | `ABC`, `ABORT` |
| `data\_sub\_agent` | fix_comprehensive_imports.py:286 | ComprehensiveImportFixerV2.... | `ABC`, `ABORT` |
| `data\_validators` | test_reviewer.py:90 | AutonomousTestReviewer._per... | `ABC`, `ABORT` |
| `DATABASE` | launcher.py:441 | DevLauncher._validate_datab... | `ABC`, `ABORT` |
| `Database` | categorize_tests.py:249 | TestCategorizer._extract_se... | `ABC`, `ABORT` |
| `database` | test_auth_oauth_errors.py:386 | TestOAuthErrorHandling.test... | `ABC`, `ABORT` |
| `database\_` | health_monitor.py:475 | HealthMonitor.get_all_status | `ABC`, `ABORT` |
| `database\_check` | launcher.py:326 | DevLauncher._register_optim... | `ABC`, `ABORT` |
| `database\_connection` | environment_validator.py:88 | EnvironmentValidator._add_r... | `ABC`, `ABORT` |
| `database\_connectivity` | environment_validator.py:408 | EnvironmentValidator.genera... | `ABC`, `ABORT` |
| `database\_connectivity\_master` | comprehensive_import_scanner.py:157 | ComprehensiveImportScanner.... | `ABC`, `ABORT` |
| `database\_connector` | launcher.py:212 | DevLauncher._graceful_shutdown | `ABC`, `ABORT` |
| `DATABASE\_ECHO\_SQL` | test_settings.py:167 | TestSettings.to_env_dict | `ABC`, `ABORT` |
| `database\_exists` | metadata_enabler.py:124 | MetadataTrackingEnabler._ca... | `ABC`, `ABORT` |
| `DATABASE\_URL` | config.py:91 | AuthConfig.get_database_url | `ABC`, `ABORT` |
| `database\_url` | test_config_loading.py:111 | _check_database_configuration | `ABC`, `ABORT` |
| `databaseId` | workflow_introspection.py:121 | WorkflowIntrospector.get_re... | `ABC`, `ABORT` |
| `DatabaseManager` | __init__.py:17 | module | `ABC`, `ABORT` |
| `databases` | cleanup_staging_environments.py:247 | StagingEnvironmentCleaner.c... | `ABC`, `ABORT` |
| `DatabaseTestMixin` | __init__.py:16 | module | `ABC`, `ABORT` |
| `DatabaseTestUtils` | __init__.py:17 | module | `ABC`, `ABORT` |
| `DataFetchingError` | fix_comprehensive_imports.py:99 | ComprehensiveImportFixerV2.... | `ABC`, `ABORT` |
| `DataSource` | generate-json-schema.py:20 | main | `ABC`, `ABORT` |
| `DataSubAgentClickHouseOperations` | fix_comprehensive_imports.py:59 | ComprehensiveImportFixerV2.... | `ABC`, `ABORT` |
| `date` | deduplicate_types.py:364 | TypeDeduplicator.generate_r... | `ABC`, `ABORT` |
| `datetime` | test_refactor_helper.py:133 | TestRefactorHelper._categor... | `ABC`, `ABORT` |
| `db` | auto_fix_test_sizes.py:340 | TestFileSplitter._determine... | `ABC`, `ABORT` |
| `db\_latencies` | real_service_test_metrics.py:51 | RealServiceTestMetrics.trac... | `ABC`, `ABORT` |
| `db\_name` | test_config.py:128 | PostgresTestConfig.create_t... | `ABC`, `ABORT` |
| `db\_queries` | real_service_test_metrics.py:23 | RealServiceTestMetrics.__in... | `ABC`, `ABORT` |
| `DB\_URL` | migration_runner.py:98 | MigrationRunner._get_databa... | `ABC`, `ABORT` |
| `DEBUG` | test_env.py:50 | TestEnvironment | `ABC`, `ABORT` |
| `debug` | debug_uvicorn_recursion.py:29 | module | `ABC`, `ABORT` |
| `decorator` | analyze_mocks.py:115 | MockAnalyzer.analyze_file | `ABC`, `ABORT` |
| `decorator\_list` | check_function_lengths.py:12 | count_function_lines | `ABC`, `ABORT` |
| `dedicated\_ws` | websocket_validator.py:76 | WebSocketValidator._discove... | `ABC`, `ABORT` |
| `def` | fix_e2e_tests_comprehensive.py:152 | E2ETestFixer._find_missing_... | `ABC`, `ABORT` |
| `DEFAULT` | launcher.py:395 | DevLauncher._set_env_var_de... | `ABC`, `ABORT` |
| `default` | test_base.py:108 | AuthTestBase.create_test_ac... | `ABC`, `ABORT` |
| `default\_port` | env_checker.py:235 | get_service_ports_status | `ABC`, `ABORT` |
| `default\_provider` | service_config.py:141 | ServicesConfiguration | `ABC`, `ABORT` |
| `definitions` | architecture_dashboard_tables.py:83 | DashboardTableRenderers._ge... | `ABC`, `ABORT` |
| `degraded` | auth_routes.py:511 | health_check | `ABC`, `ABORT` |
| `DELETE` | test_security.py:273 | TestCSRFProtection.test_met... | `ABC`, `ABORT` |
| `delete` | test_auth_token_security.py:42 | TestJWTClaimsExtraction.setUp | `ABC`, `ABORT` |
| `delete\_` | auto_split_files.py:260 | FileSplitter._group_functio... | `ABC`, `ABORT` |
| `deleted\_files` | cleanup_generated_files.py:299 | main | `ABC`, `ABORT` |
| `deleters` | auto_split_files.py:261 | FileSplitter._group_functio... | `ABC`, `ABORT` |
| `delta` | team_updates_formatter.py:132 | HumanFormatter.format_test_... | `ABC`, `ABORT` |
| `demo` | function_checker.py:75 | FunctionChecker._is_example... | `ABC`, `ABORT` |
| `demo\_` | function_complexity_linter.py:72 | FunctionComplexityLinter._i... | `ABC`, `ABORT` |
| `DemoAgent` | validate_type_deduplication.py:62 | TypeDeduplicationValidator.... | `ABC`, `ABORT` |
| `denied` | test_auth_oauth_errors.py:144 | TestOAuthErrorHandling.test... | `ABC`, `ABORT` |
| `DENY` | main.py:280 | add_service_headers | `ABC`, `ABORT` |
| `dep\_result` | test_phase3_multiprocessing.py:342 | test_phase3_integration | `ABC`, `ABORT` |
| `dependencies` | ultra_thinking_analyzer.py:41 | UltraThinkingAnalyzer.analy... | `ABC`, `ABORT` |
| `dependencies\_` | cache_warmer.py:116 | CacheWarmer._warm_service_d... | `ABC`, `ABORT` |
| `dependencies\_modified` | metadata_header_generator.py:99 | MetadataHeaderGenerator.gen... | `ABC`, `ABORT` |
| `depends\_on` | validate_agent_tests.py:196 | AgentTestValidator.check_te... | `ABC`, `ABORT` |
| `deploy` | deploy_to_gcp.py:468 | GCPDeployer.deploy_service | `ABC`, `ABORT` |
| `DEPLOY\_TARGET` | act_wrapper.py:167 | StagingDeployer._prepare_en... | `ABC`, `ABORT` |
| `deployment` | manage_workflows.py:80 | WorkflowManager._get_workfl... | `ABC`, `ABORT` |
| `deployment\_related` | staging_error_monitor.py:74 | ErrorAnalyzer.categorize_er... | `ABC`, `ABORT` |
| `DEPRECATED` | update_spec_timestamps.py:22 | module | `ABC`, `ABORT` |
| `deprecated` | test_reviewer.py:160 | AutonomousTestReviewer._ass... | `ABC`, `ABORT` |
| `deprecated\_mock` | types.py:40 | TestPattern | `ABC`, `ABORT` |
| `DeprecationWarning` | filter_patterns.py:21 | module | `ABC`, `ABORT` |
| `DEPS` | progress_indicator.py:126 | ProgressIndicator._default_... | `ABC`, `ABORT` |
| `describe` | create_staging_secrets.py:42 | check_secret_exists | `ABC`, `ABORT` |
| `description` | test_auth_oauth_errors.py:232 | TestOAuthErrorHandling.test... | `ABC`, `ABORT` |
| `desktop` | test_session_management.py:181 | TestMultiDeviceSessionManag... | `ABC`, `ABORT` |
| `destroy` | cleanup_staging_environments.py:174 | StagingEnvironmentCleaner.c... | `ABC`, `ABORT` |
| `detail` | test_oauth_flows_sync.py:88 | TestOAuthErrorScenarios.tes... | `ABC`, `ABORT` |
| `detailed\_metrics` | test_backend_optimized.py:221 | OptimizedTestManager._compi... | `ABC`, `ABORT` |
| `detailed\_results` | benchmark_optimization.py:186 | TestExecutionBenchmark._run... | `ABC`, `ABORT` |
| `detailed\_summary` | generate_wip_report.py:61 | WIPReportGenerator.run_comp... | `ABC`, `ABORT` |
| `Details` | architecture_dashboard_tables.py:110 | DashboardTableRenderers.ren... | `ABC`, `ABORT` |
| `details` | check_e2e_imports.py:234 | E2EImportChecker.generate_r... | `ABC`, `ABORT` |
| `DetectionMethod` | crash_recovery_models.py:123 | module | `ABC`, `ABORT` |
| `DetectionResult` | crash_recovery_models.py:126 | module | `ABC`, `ABORT` |
| `dev` | auth_routes.py:292 | dev_login | `ABC`, `ABORT` |
| `dev\_launcher` | enhance_dev_launcher_boundaries.py:14 | enhance_launcher_config | `ABC`, `ABORT` |
| `DEV\_MODE\_DISABLE\_LLM` | generate_openapi_spec.py:28 | module | `ABC`, `ABORT` |
| `dev\_user` | service_config.py:123 | ServicesConfiguration | `ABC`, `ABORT` |
| `devDependencies` | dependency_scanner.py:121 | scan_node_dependencies | `ABC`, `ABORT` |
| `DeveloperDep` | audit_permissions.py:36 | analyze_route_file | `ABC`, `ABORT` |
| `development` | config.py:18 | AuthConfig.get_environment | `ABC`, `ABORT` |
| `development\_security` | environment_validator.py:379 | EnvironmentValidator.valida... | `ABC`, `ABORT` |
| `development\_user` | reset_clickhouse.py:13 | module | `ABC`, `ABORT` |
| `device` | test_session_management.py:180 | TestMultiDeviceSessionManag... | `ABC`, `ABORT` |
| `device\_` | session_factory.py:37 | SessionFactory.create_sessi... | `ABC`, `ABORT` |
| `device\_id` | repository.py:168 | AuthSessionRepository.creat... | `ABC`, `ABORT` |
| `DevLauncher` | __init__.py:12 | module | `ABC`, `ABORT` |
| `diagnose` | crash_recovery_models.py:32 | RecoveryStage | `ABC`, `ABORT` |
| `DiagnosisResult` | crash_recovery_models.py:127 | module | `ABC`, `ABORT` |
| `Dict` | comprehensive_test_fixer.py:204 | TestFixer.fix_missing_function | `ABC`, `ABORT` |
| `dict` | analyze_mocks.py:141 | MockAnalyzer._is_mock_decor... | `ABC`, `ABORT` |
| `diff` | boundary_enforcer_system_checks.py:129 | SystemMetricsCalculator._ge... | `ABC`, `ABORT` |
| `dim` | verify_workflow_status.py:251 | OutputFormatter.display_table | `ABC`, `ABORT` |
| `dir\_path` | scan_string_literals.py:75 | StringLiteralCategorizer | `ABC`, `ABORT` |
| `directory` | coverage_config.py:67 | CoverageConfig.get_coverage... | `ABC`, `ABORT` |
| `disable` | manage_precommit.py:116 | main | `ABC`, `ABORT` |
| `DISABLED` | manage_precommit.py:82 | status | `ABC`, `ABORT` |
| `Disabled` | deploy_to_gcp.py:654 | GCPDeployer.deploy_all | `ABC`, `ABORT` |
| `disabled` | demo_feature_flag_system.py:48 | demonstrate_feature_flag_ba... | `ABC`, `ABORT` |
| `disabled\_by` | manage_precommit.py:41 | enable_hooks | `ABC`, `ABORT` |
| `disabled\_date` | manage_precommit.py:39 | enable_hooks | `ABC`, `ABORT` |
| `disabled\_reason` | manage_precommit.py:37 | enable_hooks | `ABC`, `ABORT` |
| `DISCOVERY` | launcher.py:739 | DevLauncher._start_health_m... | `ABC`, `ABORT` |
| `disk\_usage` | system_diagnostics.py:300 | SystemDiagnostics.get_syste... | `ABC`, `ABORT` |
| `DisplayFormatter` | __init__.py:18 | module | `ABC`, `ABORT` |
| `dist` | architecture_metrics.py:267 | ArchitectureMetrics._should... | `ABC`, `ABORT` |
| `doc\_changes` | team_updates_documentation_analyzer.py:29 | DocumentationAnalyzer.analyze | `ABC`, `ABORT` |
| `docker` | act_wrapper.py:47 | ACTWrapper._check_docker | `ABC`, `ABORT` |
| `DOCKER\_` | local_secrets_manager.py:181 | LocalSecretsManager._get_gi... | `ABC`, `ABORT` |
| `DOCKER\_PASSWORD` | workflow_validator.py:212 | SecretValidator._load_requi... | `ABC`, `ABORT` |
| `Dockerfile` | validate_service_independence.py:86 | ServiceIndependenceValidato... | `ABC`, `ABORT` |
| `docs` | architecture_metrics.py:266 | ArchitectureMetrics._should... | `ABC`, `ABORT` |
| `documentation` | team_updates_orchestrator.py:86 | TeamUpdatesOrchestrator._ca... | `ABC`, `ABORT` |
| `documentation\_health` | team_updates_documentation_analyzer.py:32 | DocumentationAnalyzer.analyze | `ABC`, `ABORT` |
| `dotenv` | environment_validator_dependencies.py:203 | DependencyValidator._check_... | `ABC`, `ABORT` |
| `down` | build_staging.py:160 | StagingBuilder.stop_staging... | `ABC`, `ABORT` |
| `dry\_run` | test_refactor_helper.py:594 | TestRefactorHelper.generate... | `ABC`, `ABORT` |
| `dto` | check_schema_imports.py:160 | SchemaImportAnalyzer._is_sc... | `ABC`, `ABORT` |
| `dummy` | real_test_requirements_enforcer.py:238 | MockComponentVisitor.visit_... | `ABC`, `ABORT` |
| `duplicate` | analyze_test_overlap.py:323 | TestOverlapAnalyzer._calcul... | `ABC`, `ABORT` |
| `duplicate\_files\_removed` | deduplicate_types.py:370 | TypeDeduplicator.generate_r... | `ABC`, `ABORT` |
| `duplicate\_imports` | check_imports.py:35 | ImportAnalyzer.analyze_file | `ABC`, `ABORT` |
| `duplicate\_line` | check_imports.py:96 | ImportAnalyzer.analyze_file | `ABC`, `ABORT` |
| `duplicate\_test` | types.py:43 | TestPattern | `ABC`, `ABORT` |
| `duplicate\_type\_boundary` | boundary_enforcer_type_checks.py:36 | TypeBoundaryChecker.check_d... | `ABC`, `ABORT` |
| `duplicate\_types` | architecture_dashboard_tables.py:70 | DashboardTableRenderers.ren... | `ABC`, `ABORT` |
| `Duplicates` | architecture_dashboard_tables.py:75 | DashboardTableRenderers.ren... | `ABC`, `ABORT` |
| `duplicates` | analyze_test_overlap.py:65 | TestOverlapAnalyzer.__init__ | `ABC`, `ABORT` |
| `duplicates\_removed` | fix_imports.py:246 | ImportFixer.fix_directory | `ABC`, `ABORT` |
| `duration` | benchmark_optimization.py:129 | TestExecutionBenchmark._run... | `ABC`, `ABORT` |
| `dynamic` | config.py:128 | LauncherConfig.from_args | `ABC`, `ABORT` |
| `dynamic\_ports` | config.py:204 | LauncherConfig.to_dict | `ABC`, `ABORT` |
| `early` | business_value_test_index.py:108 | BusinessValueTestIndexer.__... | `ABC`, `ABORT` |
| `echo` | connection.py:66 | AuthDatabase.initialize | `ABC`, `ABORT` |
| `efficiency\_score` | benchmark_optimization.py:250 | TestExecutionBenchmark._com... | `ABC`, `ABORT` |
| `element` | project_test_validator.py:172 | MockComponentVisitor.visit_... | `ABC`, `ABORT` |
| `email` | repository.py:39 | AuthUserRepository.create_o... | `ABC`, `ABORT` |
| `EMERGENCY` | boundary_enforcer_report_generator.py:197 | PRCommentGenerator._determi... | `ABC`, `ABORT` |
| `EMERGENCY\_BACKUP` | emergency_boundary_actions.py:182 | EmergencyActionSystem._crea... | `ABC`, `ABORT` |
| `emergency\_backups` | emergency_boundary_actions.py:318 | EmergencyActionSystem._crea... | `ABC`, `ABORT` |
| `emergency\_level` | emergency_boundary_actions.py:333 | EmergencyActionSystem._gene... | `ABC`, `ABORT` |
| `EMERGENCY\_REPORT` | emergency_boundary_actions.py:193 | EmergencyActionSystem._crea... | `ABC`, `ABORT` |
| `emergency\_violations` | emergency_boundary_actions.py:103 | EmergencyActionSystem._crea... | `ABC`, `ABORT` |
| `empty\_implementation` | remove_test_stubs.py:230 | TestStubDetector._scan_empt... | `ABC`, `ABORT` |
| `empty\_implementations` | remove_test_stubs.py:65 | TestStubDetector.__init__ | `ABC`, `ABORT` |
| `enable` | deploy_to_gcp.py:226 | GCPDeployer.enable_apis | `ABC`, `ABORT` |
| `ENABLE\_ALL\_SERVICES` | service_config.py:253 | ServicesConfiguration._add_... | `ABC`, `ABORT` |
| `ENABLE\_REAL\_LLM` | categorize_tests.py:49 | TestCategorizer._get_llm_pa... | `ABC`, `ABORT` |
| `ENABLE\_REAL\_LLM\_TESTING` | add_test_markers.py:186 | TestMarkerAdder.add_conditi... | `ABC`, `ABORT` |
| `ENABLED` | manage_precommit.py:82 | status | `ABC`, `ABORT` |
| `Enabled` | deploy_to_gcp.py:654 | GCPDeployer.deploy_all | `ABC`, `ABORT` |
| `enabled` | main.py:84 | lifespan | `ABC`, `ABORT` |
| `enabled\_date` | manage_precommit.py:46 | enable_hooks | `ABC`, `ABORT` |
| `enabled\_reason` | manage_precommit.py:45 | enable_hooks | `ABC`, `ABORT` |
| `end` | auto_split_files.py:203 | FileSplitter._suggest_logic... | `ABC`, `ABORT` |
| `end\_line` | auto_decompose_functions.py:118 | FunctionDecomposer._identif... | `ABC`, `ABORT` |
| `end\_lineno` | analyze_critical_paths.py:19 | count_function_lines | `ABC`, `ABORT` |
| `end\_time` | real_service_test_metrics.py:19 | RealServiceTestMetrics.__in... | `ABC`, `ABORT` |
| `end\_to\_end` | test_reviewer.py:227 | AutonomousTestReviewer._ide... | `ABC`, `ABORT` |
| `endpoint` | auto_fix_test_sizes.py:344 | TestFileSplitter._determine... | `ABC`, `ABORT` |
| `endpoints` | test_oauth_flows_auth.py:33 | TestSyntaxFix.test_google_o... | `ABC`, `ABORT` |
| `enforce\_metadata` | config_manager.py:63 | ConfigurationManager._get_s... | `ABC`, `ABORT` |
| `enforce\_session\_limits` | test_session_cleanup.py:261 | TestSessionMaintenanceSched... | `ABC`, `ABORT` |
| `english` | analyze_test_overlap.py:250 | TestOverlapAnalyzer._analyz... | `ABC`, `ABORT` |
| `enterprise` | permission_factory.py:226 | RoleFactory | `ABC`, `ABORT` |
| `enterprise\_sso` | demo_feature_flag_system.py:100 | demonstrate_environment_ove... | `ABC`, `ABORT` |
| `ENV` | launcher.py:345 | DevLauncher.check_environment | `ABC`, `ABORT` |
| `env` | boundary_enforcer_core_types.py:71 | get_skip_patterns | `ABC`, `ABORT` |
| `env\_check` | launcher.py:325 | DevLauncher._register_optim... | `ABC`, `ABORT` |
| `env\_file` | dev_launcher_secrets.py:47 | EnhancedSecretLoader._parse... | `ABC`, `ABORT` |
| `env\_file\_existence` | environment_validator.py:88 | EnvironmentValidator._add_r... | `ABC`, `ABORT` |
| `env\_file\_load` | environment_validator.py:75 | EnvironmentValidator._load_... | `ABC`, `ABORT` |
| `env\_file\_security` | environment_validator.py:356 | EnvironmentValidator.valida... | `ABC`, `ABORT` |
| `env\_files` | environment_validator_core.py:27 | EnvironmentValidatorCore.va... | `ABC`, `ABORT` |
| `env\_files\_found` | environment_validator.py:407 | EnvironmentValidator.genera... | `ABC`, `ABORT` |
| `env\_files\_hash` | secret_cache.py:216 | SecretCache.get_cache_stats | `ABC`, `ABORT` |
| `env\_local` | local_secrets.py:67 | LocalSecretManager._build_f... | `ABC`, `ABORT` |
| `ENV\_MODE` | auth_starter.py:159 | AuthStarter._create_auth_env | `ABC`, `ABORT` |
| `env\_type` | scan_string_literals.py:99 | StringLiteralCategorizer | `ABC`, `ABORT` |
| `env\_validate` | startup_optimizer.py:607 | create_validate_phase_steps | `ABC`, `ABORT` |
| `env\_validation` | startup_optimizer.py:607 | create_validate_phase_steps | `ABC`, `ABORT` |
| `env\_var` | scan_string_literals.py:66 | StringLiteralCategorizer | `ABC`, `ABORT` |
| `env\_var\_name` | scan_string_literals.py:98 | StringLiteralCategorizer | `ABC`, `ABORT` |
| `ENVIRONMENT` | config.py:18 | AuthConfig.get_environment | `ABC`, `ABORT` |
| `Environment` | dev_launcher_secrets.py:243 | EnhancedSecretLoader._get_e... | `ABC`, `ABORT` |
| `environment` | connection.py:239 | AuthDatabase.get_status | `ABC`, `ABORT` |
| `environment\_check` | launcher.py:325 | DevLauncher._register_optim... | `ABC`, `ABORT` |
| `environment\_files` | cache_warmer.py:136 | CacheWarmer._warm_environme... | `ABC`, `ABORT` |
| `environment\_name` | test_workflows_with_act.py:189 | WorkflowTester.create_event... | `ABC`, `ABORT` |
| `environment\_status` | environment_validator.py:406 | EnvironmentValidator.genera... | `ABC`, `ABORT` |
| `environment\_vars` | validate_staging_config.py:390 | initialize_results_tracking | `ABC`, `ABORT` |
| `environments\_checked` | cleanup_staging_environments.py:30 | StagingEnvironmentCleaner._... | `ABC`, `ABORT` |
| `environments\_cleaned` | cleanup_staging_environments.py:31 | StagingEnvironmentCleaner._... | `ABC`, `ABORT` |
| `ERROR` | test_settings.py:149 | TestSettings.for_performanc... | `ABC`, `ABORT` |
| `Error` | unified_import_manager.py:161 | UnifiedImportManager._check... | `ABC`, `ABORT` |
| `error` | audit_factory.py:176 | AuditLogFactory.create_oaut... | `ABC`, `ABORT` |
| `error\_capture` | crash_recovery_models.py:31 | RecoveryStage | `ABC`, `ABORT` |
| `error\_code` | assertion_helpers.py:159 | AssertionHelpers.assert_err... | `ABC`, `ABORT` |
| `error\_description` | test_auth_oauth_errors.py:120 | TestOAuthErrorHandling.test... | `ABC`, `ABORT` |
| `error\_handlers` | test_reviewer.py:89 | AutonomousTestReviewer._per... | `ABC`, `ABORT` |
| `error\_handling` | auto_decompose_functions.py:328 | FunctionDecomposer._suggest... | `ABC`, `ABORT` |
| `error\_message` | audit_factory.py:56 | AuditLogFactory.create_audi... | `ABC`, `ABORT` |
| `error\_rate` | seed_staging_data.py:283 | StagingDataSeeder._get_metr... | `ABC`, `ABORT` |
| `error\_rate\_percent` | validate_staging_health.py:138 | StagingPerformanceValidator... | `ABC`, `ABORT` |
| `error\_score` | staging_error_monitor.py:123 | DeploymentDecision.should_f... | `ABC`, `ABORT` |
| `error\_simulation` | fix_e2e_tests_comprehensive.py:74 | E2ETestFixer._get_common_fi... | `ABC`, `ABORT` |
| `error\_trace` | analyze_failures.py:142 | TestFailureAnalyzer._determ... | `ABC`, `ABORT` |
| `error\_type` | comprehensive_test_fixer.py:32 | TestFailureAnalyzer.analyze... | `ABC`, `ABORT` |
| `error\_types` | fix_comprehensive_imports.py:103 | ComprehensiveImportFixerV2.... | `ABC`, `ABORT` |
| `ERRORS` | fix_netra_backend_imports.py:204 | ImportFixer.generate_report | `ABC`, `ABORT` |
| `errors` | auto_fix_test_sizes.py:621 | TestSizeFixer.fix_all_viola... | `ABC`, `ABORT` |
| `errors\_fixed` | import_management.py:56 | ImportManagementSystem.__in... | `ABC`, `ABORT` |
| `errors\_list` | generate_report.py:115 | _format_errors | `ABC`, `ABORT` |
| `ErrorService` | test_launcher_process.py:248 | TestLogStreaming.test_log_s... | `ABC`, `ABORT` |
| `estimated\_cost` | cleanup_staging_environments.py:136 | StagingEnvironmentCleaner.g... | `ABC`, `ABORT` |
| `estimated\_coverage` | generate_wip_report.py:149 | WIPReportGenerator.calculat... | `ABC`, `ABORT` |
| `estimated\_improvement` | test_backend_optimized.py:347 | print_results_summary | `ABC`, `ABORT` |
| `estimated\_lines` | demo_test_size_enforcement.py:103 | demo_test_refactor_helper | `ABC`, `ABORT` |
| `estimated\_success\_rate` | analyze_failures.py:84 | TestFailureAnalyzer.analyze... | `ABC`, `ABORT` |
| `estimatedTime` | test_example_message_flow.py:290 | ExampleMessageFlowTestRunne... | `ABC`, `ABORT` |
| `Event` | workflow_introspection.py:245 | OutputFormatter.display_run... | `ABC`, `ABORT` |
| `event` | scan_string_literals.py:130 | StringLiteralCategorizer.ca... | `ABC`, `ABORT` |
| `event\_handler` | scan_string_literals.py:89 | StringLiteralCategorizer | `ABC`, `ABORT` |
| `event\_metadata` | audit_factory.py:57 | AuditLogFactory.create_audi... | `ABC`, `ABORT` |
| `event\_name` | scan_string_literals.py:131 | StringLiteralCategorizer.ca... | `ABC`, `ABORT` |
| `event\_type` | audit_factory.py:51 | AuditLogFactory.create_audi... | `ABC`, `ABORT` |
| `events` | scan_string_literals.py:88 | StringLiteralCategorizer | `ABC`, `ABORT` |
| `example` | function_checker.py:75 | FunctionChecker._is_example... | `ABC`, `ABORT` |
| `example\_` | function_complexity_linter.py:72 | FunctionComplexityLinter._i... | `ABC`, `ABORT` |
| `example\_message\_id` | test_example_message_flow.py:284 | ExampleMessageFlowTestRunne... | `ABC`, `ABORT` |
| `example\_message\_metadata` | test_example_message_flow.py:285 | ExampleMessageFlowTestRunne... | `ABC`, `ABORT` |
| `example\_usage` | function_checker.py:76 | FunctionChecker._is_example... | `ABC`, `ABORT` |
| `examples` | demo_test_size_enforcement.py:31 | demo_test_size_validator | `ABC`, `ABORT` |
| `EXCELLENT` | architecture_reporter.py:83 | ArchitectureReporter._get_h... | `ABC`, `ABORT` |
| `excellent` | coverage_reporter.py:198 | CoverageReporter._analyze_c... | `ABC`, `ABORT` |
| `except` | decompose_functions.py:125 | suggest_decomposition | `ABC`, `ABORT` |
| `exception` | test_auth_oauth_errors.py:293 | TestOAuthErrorHandling.test... | `ABC`, `ABORT` |
| `excess` | team_updates_compliance_analyzer.py:49 | ComplianceAnalyzer.check_30... | `ABC`, `ABORT` |
| `excess\_lines` | architecture_dashboard_tables.py:34 | DashboardTableRenderers._ge... | `ABC`, `ABORT` |
| `excessive\_mocking` | project_test_validator.py:286 | ProjectTestValidator._check... | `ABC`, `ABORT` |
| `exclude\_files` | cleanup_generated_files.py:24 | module | `ABC`, `ABORT` |
| `excluded\_lines` | coverage_reporter.py:63 | CoverageReporter.parse_cove... | `ABC`, `ABORT` |
| `executable` | environment_validator_dependencies.py:75 | DependencyValidator._valida... | `ABC`, `ABORT` |
| `execute` | ultra_thinking_analyzer.py:167 | UltraThinkingAnalyzer._iden... | `ABC`, `ABORT` |
| `execution\_plan` | metadata_header_generator.py:90 | MetadataHeaderGenerator.gen... | `ABC`, `ABORT` |
| `execution\_results` | test_backend_optimized.py:218 | OptimizedTestManager._compi... | `ABC`, `ABORT` |
| `execution\_time` | validate_agent_tests.py:299 | AgentTestValidator.export_j... | `ABC`, `ABORT` |
| `executive\_summary` | status_types.py:166 | ReportSections | `ABC`, `ABORT` |
| `executor` | dependency_checker.py:406 | AsyncDependencyChecker.cleanup | `ABC`, `ABORT` |
| `exists` | environment_validator_core.py:107 | EnvironmentValidatorCore._l... | `ABC`, `ABORT` |
| `exit\_code` | dev_launcher_processes.py:160 | ProcessMonitor._log_crash | `ABC`, `ABORT` |
| `exp` | jwt_handler.py:123 | JWTHandler._build_payload | `ABC`, `ABORT` |
| `expected` | check_netra_backend_imports.py:299 | ImportAnalyzer.export_issue... | `ABC`, `ABORT` |
| `expected\_exit\_code` | test_verify_workflow_status_corrected.py:64 | WorkflowStatusTester.run_test | `ABC`, `ABORT` |
| `expected\_path` | environment_validator.py:100 | EnvironmentValidator.valida... | `ABC`, `ABORT` |
| `expected\_status` | test_auth_oauth_errors.py:167 | TestOAuthErrorHandling.test... | `ABC`, `ABORT` |
| `expected\_valid` | test_auth_oauth_google.py:173 | TestGoogleOAuthFlow.test_go... | `ABC`, `ABORT` |
| `expected\_value` | test_size_validator.py:481 | TestSizeValidator._generate... | `ABC`, `ABORT` |
| `expected\_values` | analyze_failures.py:151 | TestFailureAnalyzer._determ... | `ABC`, `ABORT` |
| `experimental` | demo_feature_flag_system.py:49 | demonstrate_feature_flag_ba... | `ABC`, `ABORT` |
| `expired` | assertion_helpers.py:56 | AssertionHelpers.assert_tok... | `ABC`, `ABORT` |
| `expired\_entry\_counts` | cache_manager.py:490 | CacheManager._get_cache_sta... | `ABC`, `ABORT` |
| `expired\_session` | test_session_management.py:115 | TestSessionExpiry.test_sess... | `ABC`, `ABORT` |
| `expired\_sessions\_cleaned` | test_session_cleanup.py:278 | TestSessionMaintenanceSched... | `ABC`, `ABORT` |
| `expires\_at` | test_base.py:155 | AuthTestBase.assert_session... | `ABC`, `ABORT` |
| `expires\_in` | auth_routes.py:182 | refresh_tokens | `ABC`, `ABORT` |
| `EXPLANATION\_END` | generate_fix.py:225 | AIFixGenerator._add_respons... | `ABC`, `ABORT` |
| `EXPLANATION\_START` | generate_fix.py:225 | AIFixGenerator._add_respons... | `ABC`, `ABORT` |
| `export` | local_secrets_manager.py:213 | main | `ABC`, `ABORT` |
| `external` | check_netra_backend_imports.py:53 | ImportAnalyzer.__init__ | `ABC`, `ABORT` |
| `extract\_utilities` | test_refactor_helper.py:581 | TestRefactorHelper._strateg... | `ABC`, `ABORT` |
| `extreme` | seed_staging_data.py:231 | StagingDataSeeder._generate... | `ABC`, `ABORT` |
| `factory` | audit_permissions.py:93 | main | `ABC`, `ABORT` |
| `FAIL` | boundary_enforcer_report_generator.py:173 | ConsoleReportPrinter._deter... | `ABC`, `ABORT` |
| `fail\_fast` | test_backend_optimized.py:100 | module | `ABC`, `ABORT` |
| `fail\_fast\_enabled` | test_backend_optimized.py:172 | OptimizedTestManager._creat... | `ABC`, `ABORT` |
| `fail\_fast\_threshold` | test_backend_optimized.py:182 | OptimizedTestManager._creat... | `ABC`, `ABORT` |
| `fail\_under` | coverage_config.py:64 | CoverageConfig.get_coverage... | `ABC`, `ABORT` |
| `FAILED` | demo_real_llm_testing.py:49 | demo_environment_validation | `ABC`, `ABORT` |
| `Failed` | test_workflows_with_act.py:207 | WorkflowTester.extract_error | `ABC`, `ABORT` |
| `failed` | check_e2e_imports.py:50 | E2EImportChecker.__init__ | `ABC`, `ABORT` |
| `failed\_phases` | startup_optimizer.py:586 | StartupOptimizer.get_phase_... | `ABC`, `ABORT` |
| `failed\_steps` | startup_optimizer.py:310 | StartupOptimizer.get_timing... | `ABC`, `ABORT` |
| `failed\_tasks` | parallel_executor.py:286 | ParallelExecutor.get_perfor... | `ABC`, `ABORT` |
| `failed\_tests` | process_results.py:173 | TestResultProcessor.generat... | `ABC`, `ABORT` |
| `FAILING` | boundary_enforcer_report_generator.py:199 | PRCommentGenerator._determi... | `ABC`, `ABORT` |
| `failing\_tests` | generate_test_audit.py:116 | check_test_health | `ABC`, `ABORT` |
| `failure` | auto_fix_test_sizes.py:350 | TestFileSplitter._determine... | `ABC`, `ABORT` |
| `failure\_count` | benchmark_optimization.py:132 | TestExecutionBenchmark._run... | `ABC`, `ABORT` |
| `failure\_rate` | test_failure_scanner.py:198 | _finalize_scan_results | `ABC`, `ABORT` |
| `failure\_reason` | audit_factory.py:95 | AuditLogFactory.create_logi... | `ABC`, `ABORT` |
| `failures` | generate_report.py:92 | _format_failures | `ABC`, `ABORT` |
| `fair` | coverage_reporter.py:200 | CoverageReporter._analyze_c... | `ABC`, `ABORT` |
| `fake` | real_test_requirements_enforcer.py:238 | MockComponentVisitor.visit_... | `ABC`, `ABORT` |
| `fake\_test\_count` | fake_test_scanner.py:176 | FakeTestScanner._get_critic... | `ABC`, `ABORT` |
| `fake\_tests` | fake_test_scanner.py:166 | FakeTestScanner._get_critic... | `ABC`, `ABORT` |
| `fake\_tests\_by\_directory` | fake_test_scanner.py:86 | FakeTestScanner.scan_all_tests | `ABC`, `ABORT` |
| `fake\_tests\_by\_severity` | fake_test_scanner.py:88 | FakeTestScanner.scan_all_tests | `ABC`, `ABORT` |
| `fake\_tests\_by\_type` | fake_test_scanner.py:87 | FakeTestScanner.scan_all_tests | `ABC`, `ABORT` |
| `fake\_token` | test_verify_workflow_status.py:122 | WorkflowStatusTester.test_r... | `ABC`, `ABORT` |
| `fallback` | crash_recovery_models.py:34 | RecoveryStage | `ABC`, `ABORT` |
| `fallback\_mode` | test_backend_optimized.py:277 | OptimizedTestManager._fallb... | `ABC`, `ABORT` |
| `False` | coverage_config.py:91 | CoverageConfig.create_cover... | `ABC`, `ABORT` |
| `false` | config.py:116 | AuthConfig.is_redis_disabled | `ABC`, `ABORT` |
| `FAST\_STARTUP\_MODE` | migration_runner.py:87 | MigrationRunner._should_ski... | `ABC`, `ABORT` |
| `fastapi` | config_setup_scripts.py:143 | test_python_imports | `ABC`, `ABORT` |
| `FATAL` | crash_detector.py:40 | CrashDetector._build_fatal_... | `ABC`, `ABORT` |
| `fatal` | log_streamer.py:45 | LogStreamer.__init__ | `ABC`, `ABORT` |
| `Feature` | metadata_header_generator.py:75 | MetadataHeaderGenerator.gen... | `ABC`, `ABORT` |
| `feature` | test_refactor_helper.py:508 | TestRefactorHelper._strateg... | `ABC`, `ABORT` |
| `feature\_based` | test_refactor_helper.py:507 | TestRefactorHelper._strateg... | `ABC`, `ABORT` |
| `features` | demo_feature_flag_system.py:246 | demonstrate_business_value | `ABC`, `ABORT` |
| `FERNET\_` | local_secrets.py:93 | LocalSecretManager._is_rele... | `ABC`, `ABORT` |
| `FERNET\_KEY` | dev_launcher_secrets.py:112 | EnhancedSecretLoader._get_s... | `ABC`, `ABORT` |
| `fernet\_key` | environment_validator.py:367 | EnvironmentValidator.valida... | `ABC`, `ABORT` |
| `fetch` | ssot_checker.py:148 | SSOTChecker._get_function_s... | `ABC`, `ABORT` |
| `File` | act_wrapper.py:134 | ACTWrapper._create_workflow... | `ABC`, `ABORT` |
| `file` | coverage_reporter.py:207 | CoverageReporter._analyze_c... | `ABC`, `ABORT` |
| `file\_analyses` | test_size_validator.py:80 | TestSizeValidator.validate_... | `ABC`, `ABORT` |
| `file\_compliance` | architecture_metrics.py:77 | ArchitectureMetrics._calcul... | `ABC`, `ABORT` |
| `file\_count` | cache_warmer.py:60 | CacheWarmer._warm_migration... | `ABC`, `ABORT` |
| `file\_details` | demo_real_llm_testing.py:81 | demo_environment_validation | `ABC`, `ABORT` |
| `file\_error` | project_test_validator.py:147 | ProjectTestValidator._valid... | `ABC`, `ABORT` |
| `file\_fixes` | align_test_imports.py:412 | TestImportAligner.generate_... | `ABC`, `ABORT` |
| `file\_hashes` | startup_optimizer.py:606 | create_validate_phase_steps | `ABC`, `ABORT` |
| `file\_ids` | setup_assistant.py:59 | _create_assistant_config | `ABC`, `ABORT` |
| `file\_line\_boundary` | boundary_enforcer_file_checks.py:68 | FileBoundaryChecker._build_... | `ABC`, `ABORT` |
| `file\_naming` | file_checker.py:48 | FileChecker.check_file_naming | `ABC`, `ABORT` |
| `file\_path` | agent_tracking_helper.py:349 | AgentTrackingHelper.create_... | `ABC`, `ABORT` |
| `file\_patterns` | config_manager.py:68 | ConfigurationManager._get_s... | `ABC`, `ABORT` |
| `file\_results` | coverage_reporter.py:163 | CoverageReporter.generate_c... | `ABC`, `ABORT` |
| `file\_size` | architecture_scanner_helpers.py:166 | ScannerHelpers.create_file_... | `ABC`, `ABORT` |
| `FILE\_SIZE\_LIMIT` | boundary_enforcer_file_checks.py:69 | FileBoundaryChecker._build_... | `ABC`, `ABORT` |
| `file\_size\_violations` | architecture_dashboard_tables.py:17 | DashboardTableRenderers.ren... | `ABC`, `ABORT` |
| `file\_splits` | real_test_linter.py:199 | RealTestLinter.generate_fix... | `ABC`, `ABORT` |
| `file\_violations` | create_agent_fix_tasks.py:13 | create_agent_tasks | `ABC`, `ABORT` |
| `filename` | coverage_reporter.py:119 | CoverageReporter.parse_cove... | `ABC`, `ABORT` |
| `Files` | architecture_dashboard_tables.py:75 | DashboardTableRenderers.ren... | `ABC`, `ABORT` |
| `files` | coverage_reporter.py:66 | CoverageReporter.parse_cove... | `ABC`, `ABORT` |
| `files\_affected` | deduplicate_types.py:366 | TypeDeduplicator.generate_r... | `ABC`, `ABORT` |
| `files\_checked` | fix_all_import_issues.py:175 | ComprehensiveImportFixer.fi... | `ABC`, `ABORT` |
| `files\_created` | auto_fix_test_sizes.py:694 | TestSizeFixer.fix_specific_... | `ABC`, `ABORT` |
| `files\_deleted` | cleanup_generated_files.py:296 | main | `ABC`, `ABORT` |
| `files\_exceeding\_limit` | test_size_validator.py:82 | TestSizeValidator.validate_... | `ABC`, `ABORT` |
| `files\_fixed` | comprehensive_e2e_import_fixer.py:352 | main | `ABC`, `ABORT` |
| `files\_modified` | cleanup_duplicate_tests.py:257 | TestModuleImportCleaner.run... | `ABC`, `ABORT` |
| `files\_needing\_attention` | coverage_reporter.py:219 | CoverageReporter._analyze_c... | `ABC`, `ABORT` |
| `files\_processed` | auto_fix_test_sizes.py:617 | TestSizeFixer.fix_all_viola... | `ABC`, `ABORT` |
| `files\_split` | auto_fix_test_sizes.py:618 | TestSizeFixer.fix_all_viola... | `ABC`, `ABORT` |
| `files\_to\_fix` | create_agent_fix_tasks.py:12 | create_agent_tasks | `ABC`, `ABORT` |
| `files\_with\_issues` | comprehensive_import_scanner.py:80 | ComprehensiveScanReport.to_... | `ABC`, `ABORT` |
| `files\_with\_long\_functions` | check_test_compliance.py:134 | scan_test_files | `ABC`, `ABORT` |
| `files\_with\_mock\_components` | check_test_compliance.py:135 | scan_test_files | `ABC`, `ABORT` |
| `files\_with\_violations` | check_schema_imports.py:290 | SchemaImportAnalyzer.analyz... | `ABC`, `ABORT` |
| `FilterPresets` | log_filter.py:341 | module | `ABC`, `ABORT` |
| `final\_block` | auto_decompose_functions.py:125 | FunctionDecomposer._identif... | `ABC`, `ABORT` |
| `find\_process\_using\_port` | test_startup_comprehensive.py:204 | TestPortManagerWindows.test... | `ABC`, `ABORT` |
| `findstr` | process_manager.py:399 | ProcessManager._cleanup_por... | `ABC`, `ABORT` |
| `fire` | unicode_utils.py:86 | module | `ABC`, `ABORT` |
| `first\_line` | check_imports.py:95 | ImportAnalyzer.analyze_file | `ABC`, `ABORT` |
| `fix` | import_management.py:267 | ImportManagementSystem.run_... | `ABC`, `ABORT` |
| `fix\_all` | import_management.py:46 | ImportManagementSystem.__in... | `ABC`, `ABORT` |
| `fix\_applied` | fix_test_batch.py:266 | BatchTestProcessor._initial... | `ABC`, `ABORT` |
| `fix\_comprehensive` | import_management.py:47 | ImportManagementSystem.__in... | `ABC`, `ABORT` |
| `FIX\_END` | generate_fix.py:224 | AIFixGenerator._add_respons... | `ABC`, `ABORT` |
| `fix\_module\_import` | fix_test_batch.py:78 | TestAnalyzer.analyze_failure | `ABC`, `ABORT` |
| `fix\_needed` | comprehensive_test_fixer.py:35 | TestFailureAnalyzer.analyze... | `ABC`, `ABORT` |
| `FIX\_START` | generate_fix.py:224 | AIFixGenerator._add_respons... | `ABC`, `ABORT` |
| `fix\_strategy` | fix_test_batch.py:40 | TestAnalyzer.analyze_failure | `ABC`, `ABORT` |
| `fix\_suggestion` | test_size_validator.py:445 | TestSizeValidator._generate... | `ABC`, `ABORT` |
| `fixable\_count` | analyze_failures.py:76 | TestFailureAnalyzer.analyze... | `ABC`, `ABORT` |
| `fixable\_tests` | analyze_failures.py:81 | TestFailureAnalyzer.analyze... | `ABC`, `ABORT` |
| `Fixed` | comprehensive_import_scanner.py:793 | main | `ABC`, `ABORT` |
| `fixed` | check_e2e_imports.py:53 | E2EImportChecker.__init__ | `ABC`, `ABORT` |
| `fixed\_files` | comprehensive_e2e_import_fixer.py:283 | ComprehensiveE2EImportFixer... | `ABC`, `ABORT` |
| `fixed\_recently` | team_updates_compliance_analyzer.py:162 | ComplianceAnalyzer._parse_c... | `ABC`, `ABORT` |
| `fixes` | dependency_scanner.py:268 | main | `ABC`, `ABORT` |
| `fixes\_applied` | comprehensive_test_fixer.py:413 | BatchProcessor.generate_report | `ABC`, `ABORT` |
| `fixes\_by\_file` | comprehensive_e2e_import_fixer.py:284 | ComprehensiveE2EImportFixer... | `ABC`, `ABORT` |
| `fixme` | ultra_thinking_analyzer.py:194 | UltraThinkingAnalyzer._extr... | `ABC`, `ABORT` |
| `fixture` | analyze_test_overlap.py:190 | TestOverlapAnalyzer._extrac... | `ABC`, `ABORT` |
| `fixture\_similarity` | analyze_test_overlap.py:633 | TestOverlapAnalyzer._save_c... | `ABC`, `ABORT` |
| `fixtures` | auto_fix_test_sizes.py:272 | TestFileSplitter.split_over... | `ABC`, `ABORT` |
| `flaky\_pattern` | types.py:45 | TestPattern | `ABC`, `ABORT` |
| `flaky\_tests` | team_updates_test_analyzer.py:147 | TestReportAnalyzer._extract... | `ABC`, `ABORT` |
| `folder` | unicode_utils.py:88 | module | `ABC`, `ABORT` |
| `for` | aggressive_syntax_fix.py:157 | aggressive_fix | `ABC`, `ABORT` |
| `format\_` | code_review_ai_detector.py:49 | CodeReviewAIDetector._check... | `ABC`, `ABORT` |
| `framework` | align_test_imports.py:34 | TestImportAligner.__init__ | `ABC`, `ABORT` |
| `free` | business_value_test_index.py:107 | BusinessValueTestIndexer.__... | `ABC`, `ABORT` |
| `free\_mb` | system_diagnostics.py:319 | SystemDiagnostics._get_disk... | `ABC`, `ABORT` |
| `freemium` | update_spec_timestamps.py:114 | is_legacy_spec | `ABC`, `ABORT` |
| `from` | comprehensive_import_scanner.py:171 | ComprehensiveImportScanner.... | `ABC`, `ABORT` |
| `FRONTEND` | dev_launcher_service.py:228 | ServiceManager._finalize_fr... | `ABC`, `ABORT` |
| `Frontend` | build_staging.py:177 | StagingBuilder.health_check | `ABC`, `ABORT` |
| `frontend` | align_test_imports.py:35 | TestImportAligner.__init__ | `ABC`, `ABORT` |
| `frontend\_components` | status_renderer.py:73 | StatusReportRenderer._build... | `ABC`, `ABORT` |
| `frontend\_coverage` | test_frontend.py:136 | _get_coverage_directory | `ABC`, `ABORT` |
| `frontend\_deps` | environment_checker.py:119 | EnvironmentChecker._check_f... | `ABC`, `ABORT` |
| `frontend\_deps\_installed` | environment_validator_dependencies.py:119 | DependencyValidator._valida... | `ABC`, `ABORT` |
| `frontend\_layout` | update_spec_timestamps.py:73 | module | `ABC`, `ABORT` |
| `FRONTEND\_PORT` | test_frontend.py:270 | check_frontend_running | `ABC`, `ABORT` |
| `frontend\_port` | config.py:203 | LauncherConfig.to_dict | `ABC`, `ABORT` |
| `frontend\_reload` | config.py:206 | LauncherConfig.to_dict | `ABC`, `ABORT` |
| `frontend\_startup` | service_startup.py:204 | ServiceStartupCoordinator.s... | `ABC`, `ABORT` |
| `FRONTEND\_URL` | config.py:72 | AuthConfig.get_frontend_url | `ABC`, `ABORT` |
| `full` | build_staging.py:256 | _add_action_arguments | `ABC`, `ABORT` |
| `full\_` | test_refactor_helper.py:199 | TestRefactorHelper._determi... | `ABC`, `ABORT` |
| `full\_name` | user_factory.py:39 | UserFactory.create_user_data | `ABC`, `ABORT` |
| `full\_path` | add_test_markers.py:136 | TestMarkerAdder.process_file | `ABC`, `ABORT` |
| `FULL\_SYSTEM` | emergency_boundary_actions.py:185 | EmergencyActionSystem._crea... | `ABC`, `ABORT` |
| `fully\_compliant` | team_updates_compliance_analyzer.py:146 | ComplianceAnalyzer._determi... | `ABC`, `ABORT` |
| `FULLY\_ENABLED` | metadata_enabler.py:134 | MetadataTrackingEnabler._ca... | `ABC`, `ABORT` |
| `Function` | architecture_dashboard_tables.py:48 | DashboardTableRenderers.ren... | `ABC`, `ABORT` |
| `function` | conftest.py:37 | initialized_test_db | `ABC`, `ABORT` |
| `function\_based` | auto_split_files.py:189 | FileSplitter._suggest_funct... | `ABC`, `ABORT` |
| `function\_complexity` | architecture_scanner_helpers.py:180 | ScannerHelpers.create_funct... | `ABC`, `ABORT` |
| `function\_complexity\_violations` | architecture_dashboard_tables.py:43 | DashboardTableRenderers.ren... | `ABC`, `ABORT` |
| `function\_compliance` | architecture_metrics.py:78 | ArchitectureMetrics._calcul... | `ABC`, `ABORT` |
| `function\_errors` | reporter.py:302 | ComplianceReporter._print_a... | `ABC`, `ABORT` |
| `function\_group` | auto_split_files.py:182 | FileSplitter._suggest_funct... | `ABC`, `ABORT` |
| `function\_line\_boundary` | boundary_enforcer_function_checks.py:81 | FunctionBoundaryChecker._bu... | `ABC`, `ABORT` |
| `function\_name` | test_size_validator.py:490 | TestSizeValidator._generate... | `ABC`, `ABORT` |
| `function\_refactors` | real_test_linter.py:206 | RealTestLinter.generate_fix... | `ABC`, `ABORT` |
| `function\_signature` | analyze_failures.py:149 | TestFailureAnalyzer._determ... | `ABC`, `ABORT` |
| `function\_size` | auto_fix_test_violations.py:234 | TestFileAnalyzer._check_fun... | `ABC`, `ABORT` |
| `FUNCTION\_SIZE\_LIMIT` | boundary_enforcer_function_checks.py:82 | FunctionBoundaryChecker._bu... | `ABC`, `ABORT` |
| `function\_to\_fixture` | test_refactor_helper.py:332 | TestRefactorHelper._analyze... | `ABC`, `ABORT` |
| `function\_to\_function` | test_refactor_helper.py:331 | TestRefactorHelper._analyze... | `ABC`, `ABORT` |
| `function\_violations` | team_updates_compliance_analyzer.py:30 | ComplianceAnalyzer.analyze | `ABC`, `ABORT` |
| `functions` | test_generator.py:57 | TestGenerator._generate_tes... | `ABC`, `ABORT` |
| `functions\_exceeding\_limit` | test_size_validator.py:83 | TestSizeValidator.validate_... | `ABC`, `ABORT` |
| `functions\_modified` | agent_tracking_helper.py:356 | AgentTrackingHelper.create_... | `ABC`, `ABORT` |
| `functions\_optimized` | auto_fix_test_sizes.py:619 | TestSizeFixer.fix_all_viola... | `ABC`, `ABORT` |
| `functions\_removed` | cleanup_duplicate_tests.py:258 | TestModuleImportCleaner.run... | `ABC`, `ABORT` |
| `GB` | cleanup_generated_files.py:147 | format_bytes | `ABC`, `ABORT` |
| `gcloud` | cleanup_staging_environments.py:44 | StagingEnvironmentCleaner.g... | `ABC`, `ABORT` |
| `gcp` | validate_staging_config.py:392 | initialize_results_tracking | `ABC`, `ABORT` |
| `GCP\_` | local_secrets_manager.py:181 | LocalSecretsManager._get_gi... | `ABC`, `ABORT` |
| `GCP\_PROJECT\_ID` | secret_loader.py:87 | AuthSecretLoader._load_from... | `ABC`, `ABORT` |
| `GCP\_PROJECT\_ID\_NUMERICAL\_STAGING` | test_config_loading.py:35 | _print_environment_variables | `ABC`, `ABORT` |
| `GCP\_REGION` | cleanup_staging_environments.py:405 | _add_basic_arguments | `ABC`, `ABORT` |
| `GCP\_STAGING\_SA\_KEY` | validate_staging_config.py:55 | get_required_github_secrets | `ABC`, `ABORT` |
| `gear` | unicode_utils.py:85 | module | `ABC`, `ABORT` |
| `gemini` | generate_fix.py:37 | AIFixGenerator._get_api_key | `ABC`, `ABORT` |
| `GEMINI\_` | local_secrets.py:92 | LocalSecretManager._is_rele... | `ABC`, `ABORT` |
| `gemini\_api` | environment_validator.py:299 | EnvironmentValidator.valida... | `ABC`, `ABORT` |
| `GEMINI\_API\_KEY` | categorize_tests.py:48 | TestCategorizer._get_llm_pa... | `ABC`, `ABORT` |
| `general` | comprehensive_import_scanner.py:564 | ComprehensiveImportScanner.... | `ABC`, `ABORT` |
| `GENERATE\_SCHEMA\_MODE` | generate_openAPI_schema.py:7 | module | `ABC`, `ABORT` |
| `generate\_stream` | fix_missing_functions.py:29 | module | `ABC`, `ABORT` |
| `generated\_at` | coverage_reporter.py:164 | CoverageReporter.generate_c... | `ABC`, `ABORT` |
| `generated\_files` | test_refactor_helper.py:592 | TestRefactorHelper.generate... | `ABC`, `ABORT` |
| `generic` | ssot_checker.py:141 | SSOTChecker._get_function_s... | `ABC`, `ABORT` |
| `GET` | cleanup_workflow_runs.py:60 | get_workflow_runs | `ABC`, `ABORT` |
| `get` | ssot_checker.py:148 | SSOTChecker._get_function_s... | `ABC`, `ABORT` |
| `get\_` | auto_split_files.py:252 | FileSplitter._group_functio... | `ABC`, `ABORT` |
| `get\_all` | comprehensive_test_fixer.py:82 | CodeGenerator.generate_func... | `ABC`, `ABORT` |
| `get\_async\_db` | fast_import_checker.py:207 | fix_known_import_issues | `ABC`, `ABORT` |
| `get\_config` | code_review_ai_detector.py:47 | CodeReviewAIDetector._check... | `ABC`, `ABORT` |
| `get\_connection\_manager` | fix_e2e_connection_manager_imports.py:72 | replace_mixed_import | `ABC`, `ABORT` |
| `get\_cors\_metrics` | health_monitor.py:588 | HealthMonitor.get_cross_ser... | `ABC`, `ABORT` |
| `get\_current\_user` | audit_permissions.py:36 | analyze_route_file | `ABC`, `ABORT` |
| `get\_db` | fast_import_checker.py:214 | fix_known_import_issues | `ABC`, `ABORT` |
| `get\_db\_session` | __init__.py:15 | module | `ABC`, `ABORT` |
| `get\_fix\_suggestions` | test_launcher.py:295 | TestDevLauncher.test_check_... | `ABC`, `ABORT` |
| `getters` | auto_split_files.py:253 | FileSplitter._group_functio... | `ABC`, `ABORT` |
| `gh` | cleanup_workflow_runs.py:18 | run_gh_command | `ABC`, `ABORT` |
| `git` | agent_tracking_helper.py:75 | AgentTrackingHelper._get_gi... | `ABC`, `ABORT` |
| `git\_branch` | agent_tracking_helper.py:350 | AgentTrackingHelper.create_... | `ABC`, `ABORT` |
| `git\_commit` | agent_tracking_helper.py:351 | AgentTrackingHelper.create_... | `ABC`, `ABORT` |
| `git\_diff` | generate_fix.py:203 | AIFixGenerator._add_git_dif... | `ABC`, `ABORT` |
| `git\_hooks` | metadata_enabler.py:83 | MetadataTrackingEnabler.get... | `ABC`, `ABORT` |
| `git\_hooks\_installed` | git_hooks_manager.py:96 | GitHooksManager.get_status | `ABC`, `ABORT` |
| `git\_state` | metadata_header_generator.py:94 | MetadataHeaderGenerator.gen... | `ABC`, `ABORT` |
| `GitHooksManager` | __init__.py:16 | module | `ABC`, `ABORT` |
| `github` | auth_models.py:22 | AuthProvider | `ABC`, `ABORT` |
| `GITHUB\_` | local_secrets_manager.py:181 | LocalSecretsManager._get_gi... | `ABC`, `ABORT` |
| `github\_access\_` | token_factory.py:218 | OAuthTokenFactory.create_gi... | `ABC`, `ABORT` |
| `GITHUB\_ACTIONS` | validate_staging_config.py:446 | main | `ABC`, `ABORT` |
| `GITHUB\_CLIENT\_ID` | test_env.py:40 | TestEnvironment | `ABC`, `ABORT` |
| `GITHUB\_CLIENT\_SECRET` | test_env.py:41 | TestEnvironment | `ABC`, `ABORT` |
| `GITHUB\_REPOSITORY` | cleanup_staging_environments.py:27 | StagingEnvironmentCleaner._... | `ABC`, `ABORT` |
| `github\_secrets` | validate_staging_config.py:390 | initialize_results_tracking | `ABC`, `ABORT` |
| `GITHUB\_TOKEN` | cleanup_staging_environments.py:26 | StagingEnvironmentCleaner._... | `ABC`, `ABORT` |
| `GITLAB\_CI` | config_validator.py:274 | _detect_ci_environment | `ABC`, `ABORT` |
| `global` | validate_workflow_config.py:24 | validate_config_structure | `ABC`, `ABORT` |
| `globe` | unicode_utils.py:87 | module | `ABC`, `ABORT` |
| `go` | agent_tracking_helper.py:40 | AgentTrackingHelper | `ABC`, `ABORT` |
| `goal` | generate_startup_integration_tests.py:21 | module | `ABC`, `ABORT` |
| `GOOD` | architecture_reporter.py:85 | ArchitectureReporter._get_h... | `ABC`, `ABORT` |
| `good` | coverage_reporter.py:199 | CoverageReporter._analyze_c... | `ABC`, `ABORT` |
| `google` | repository.py:40 | AuthUserRepository.create_o... | `ABC`, `ABORT` |
| `GOOGLE\_` | local_secrets.py:92 | LocalSecretManager._is_rele... | `ABC`, `ABORT` |
| `google\_access\_` | token_factory.py:193 | OAuthTokenFactory.create_go... | `ABC`, `ABORT` |
| `GOOGLE\_API\_KEY` | generate_fix.py:37 | AIFixGenerator._get_api_key | `ABC`, `ABORT` |
| `GOOGLE\_CLIENT\_ID` | secret_loader.py:131 | AuthSecretLoader.get_google... | `ABC`, `ABORT` |
| `google\_client\_id` | test_oauth_flows_auth.py:32 | TestSyntaxFix.test_google_o... | `ABC`, `ABORT` |
| `GOOGLE\_CLIENT\_SECRET` | secret_loader.py:157 | AuthSecretLoader.get_google... | `ABC`, `ABORT` |
| `GOOGLE\_CLOUD\_PROJECT` | dev_launcher_secrets.py:23 | EnhancedSecretLoader.__init__ | `ABC`, `ABORT` |
| `google\_oauth` | environment_validator.py:289 | EnvironmentValidator.valida... | `ABC`, `ABORT` |
| `GOOGLE\_OAUTH\_CLIENT\_ID\_DEV` | verify_auth_config.py:77 | verify_environment_config | `ABC`, `ABORT` |
| `GOOGLE\_OAUTH\_CLIENT\_ID\_PROD` | verify_auth_config.py:74 | verify_environment_config | `ABC`, `ABORT` |
| `GOOGLE\_OAUTH\_CLIENT\_ID\_PRODUCTION` | secret_loader.py:125 | AuthSecretLoader.get_google... | `ABC`, `ABORT` |
| `GOOGLE\_OAUTH\_CLIENT\_ID\_STAGING` | secret_loader.py:120 | AuthSecretLoader.get_google... | `ABC`, `ABORT` |
| `GOOGLE\_OAUTH\_CLIENT\_SECRET\_DEV` | verify_auth_config.py:78 | verify_environment_config | `ABC`, `ABORT` |
| `GOOGLE\_OAUTH\_CLIENT\_SECRET\_PROD` | verify_auth_config.py:75 | verify_environment_config | `ABC`, `ABORT` |
| `GOOGLE\_OAUTH\_CLIENT\_SECRET\_PRODUC...` | secret_loader.py:151 | AuthSecretLoader.get_google... | `ABC`, `ABORT` |
| `GOOGLE\_OAUTH\_CLIENT\_SECRET\_STAGING` | secret_loader.py:146 | AuthSecretLoader.get_google... | `ABC`, `ABORT` |
| `google\_refresh\_` | token_factory.py:194 | OAuthTokenFactory.create_go... | `ABC`, `ABORT` |
| `google\_secret` | dev_launcher_secrets.py:92 | EnhancedSecretLoader._fetch... | `ABC`, `ABORT` |
| `gpu\_utilization` | seed_staging_data.py:284 | StagingDataSeeder._get_metr... | `ABC`, `ABORT` |
| `grace\_period` | health_monitor.py:36 | ServiceState | `ABC`, `ABORT` |
| `grace\_period\_over` | health_monitor.py:422 | HealthMonitor.get_grace_per... | `ABC`, `ABORT` |
| `grace\_period\_remaining` | health_monitor.py:421 | HealthMonitor.get_grace_per... | `ABC`, `ABORT` |
| `grace\_period\_seconds` | health_monitor.py:420 | HealthMonitor.get_grace_per... | `ABC`, `ABORT` |
| `grant\_method` | audit_factory.py:214 | AuditLogFactory.create_perm... | `ABC`, `ABORT` |
| `grant\_type` | auth_routes.py:424 | oauth_callback | `ABC`, `ABORT` |
| `granted\_at` | permission_factory.py:60 | PermissionFactory.create_pe... | `ABC`, `ABORT` |
| `granted\_by` | audit_factory.py:213 | AuditLogFactory.create_perm... | `ABC`, `ABORT` |
| `green` | act_wrapper.py:135 | ACTWrapper._create_workflow... | `ABC`, `ABORT` |
| `growth\_velocity` | boundary_enforcer_report_generator.py:126 | ConsoleReportPrinter._print... | `ABC`, `ABORT` |
| `gunicorn` | validate_service_independence.py:126 | ServiceIndependenceValidato... | `ABC`, `ABORT` |
| `handle` | ultra_thinking_analyzer.py:167 | UltraThinkingAnalyzer._iden... | `ABC`, `ABORT` |
| `handle\_` | ssot_checker.py:171 | SSOTChecker._are_likely_dup... | `ABC`, `ABORT` |
| `handler` | auto_fix_test_sizes.py:369 | TestFileSplitter._determine... | `ABC`, `ABORT` |
| `handler\_` | ssot_checker.py:97 | SSOTChecker._check_duplicat... | `ABC`, `ABORT` |
| `handlers` | auto_fix_test_sizes.py:370 | TestFileSplitter._determine... | `ABC`, `ABORT` |
| `hardcoded\_test\_data` | remove_test_stubs.py:55 | TestStubDetector.__init__ | `ABC`, `ABORT` |
| `hardcoded\_wait` | test_reviewer.py:165 | AutonomousTestReviewer._ass... | `ABC`, `ABORT` |
| `has\_conditionals` | function_complexity_analyzer.py:393 | _convert_results_to_json | `ABC`, `ABORT` |
| `has\_conditions` | boundary_enforcer_function_checks.py:132 | FunctionAnalyzer._analyze_s... | `ABC`, `ABORT` |
| `has\_docstring` | test_size_validator.py:316 | TestSizeValidator._analyze_... | `ABC`, `ABORT` |
| `has\_environment\_changed` | test_dev_user_flow.py:108 | TestDevUserCreation.test_de... | `ABC`, `ABORT` |
| `has\_loops` | function_complexity_analyzer.py:392 | _convert_results_to_json | `ABC`, `ABORT` |
| `has\_nested\_functions` | function_complexity_analyzer.py:391 | _convert_results_to_json | `ABC`, `ABORT` |
| `has\_return` | test_generator.py:157 | _generate_basic_function_test | `ABC`, `ABORT` |
| `has\_side\_effects` | ultra_thinking_analyzer.py:82 | UltraThinkingAnalyzer._anal... | `ABC`, `ABORT` |
| `has\_skip\_marker` | categorize_tests.py:86 | TestCategorizer._initialize... | `ABC`, `ABORT` |
| `has\_try\_except` | boundary_enforcer_function_checks.py:133 | FunctionAnalyzer._analyze_s... | `ABC`, `ABORT` |
| `hash` | team_updates_documentation_analyzer.py:111 | DocumentationAnalyzer._pars... | `ABC`, `ABORT` |
| `hash\_check` | startup_optimizer.py:606 | create_validate_phase_steps | `ABC`, `ABORT` |
| `hashed\_password` | test_mixins.py:159 | AuthTestMixin.setup_auth_mocks | `ABC`, `ABORT` |
| `hashes` | cache_manager.py:61 | CacheManager._setup_cache_f... | `ABC`, `ABORT` |
| `HEAD` | agent_tracking_helper.py:75 | AgentTrackingHelper._get_gi... | `ABC`, `ABORT` |
| `head` | clean_slate_executor.py:116 | CleanSlateExecutor.phase2_d... | `ABC`, `ABORT` |
| `head\_branch` | verify_workflow_status.py:124 | WorkflowStatusVerifier._par... | `ABC`, `ABORT` |
| `head\_sha` | verify_workflow_status.py:125 | WorkflowStatusVerifier._par... | `ABC`, `ABORT` |
| `headBranch` | workflow_introspection.py:126 | WorkflowIntrospector.get_re... | `ABC`, `ABORT` |
| `header` | generate_openapi_spec.py:103 | _get_security_schemes | `ABC`, `ABORT` |
| `HeaderConstants` | auth_constants_migration.py:101 | AuthConstantsMigrator.__init__ | `ABC`, `ABORT` |
| `headers` | assertion_helpers.py:237 | AssertionHelpers.assert_rat... | `ABC`, `ABORT` |
| `heads` | migration_runner.py:144 | MigrationRunner._get_head_r... | `ABC`, `ABORT` |
| `headSha` | workflow_introspection.py:127 | WorkflowIntrospector.get_re... | `ABC`, `ABORT` |
| `HEALTH` | health_registration.py:83 | HealthRegistrationHelper.re... | `ABC`, `ABORT` |
| `health` | build_staging.py:256 | _add_action_arguments | `ABC`, `ABORT` |
| `health\_check` | health_monitor.py:169 | HealthMonitor.register_service | `ABC`, `ABORT` |
| `health\_checks` | service_startup.py:409 | ServiceStartupCoordinator.g... | `ABC`, `ABORT` |
| `health\_endpoint` | test_websocket_dev_mode.py:41 | WebSocketDevModeTest.__init__ | `ABC`, `ABORT` |
| `health\_monitor` | launcher.py:193 | DevLauncher._graceful_shutdown | `ABC`, `ABORT` |
| `health\_status` | scan_string_literals.py:103 | StringLiteralCategorizer | `ABC`, `ABORT` |
| `health\_url` | crash_detector.py:140 | CrashDetector.run_all_detec... | `ABC`, `ABORT` |
| `HealthScoreCalculator` | status_analyzer.py:29 | module | `ABC`, `ABORT` |
| `healthy` | auth_routes.py:511 | health_check | `ABC`, `ABORT` |
| `healthy\_services` | service_startup.py:410 | ServiceStartupCoordinator.g... | `ABC`, `ABORT` |
| `heartbeat` | status_integration_analyzer.py:57 | IntegrationAnalyzer._check_... | `ABC`, `ABORT` |
| `Hello` | test_launcher_process.py:303 | TestLogStreaming._assert_un... | `ABC`, `ABORT` |
| `HELP` | launcher.py:355 | DevLauncher.check_environment | `ABC`, `ABORT` |
| `help\_display` | test_verify_workflow_status.py:79 | WorkflowStatusTester.test_h... | `ABC`, `ABORT` |
| `helper` | auto_fix_test_violations.py:447 | TestFileSplitter._extract_u... | `ABC`, `ABORT` |
| `helpers` | fix_e2e_imports.py:226 | E2EImportFixer.create_missi... | `ABC`, `ABORT` |
| `hierarchical\_testing` | workflow_config_utils.py:98 | WorkflowConfigUtils._check_... | `ABC`, `ABORT` |
| `HIGH` | check_test_stubs.py:67 | CITestStubChecker._print_de... | `ABC`, `ABORT` |
| `High` | metadata_header_generator.py:317 | MetadataHeaderGenerator.add... | `ABC`, `ABORT` |
| `high` | architecture_metrics.py:18 | ArchitectureMetrics | `ABC`, `ABORT` |
| `high\_confidence\_count` | analyze_failures.py:78 | TestFailureAnalyzer.analyze... | `ABC`, `ABORT` |
| `high\_failure\_rate` | fake_test_scanner.py:299 | FakeTestScanner.generate_co... | `ABC`, `ABORT` |
| `high\_risk` | config_manager.py:36 | ConfigurationManager._get_f... | `ABC`, `ABORT` |
| `high\_value\_test\_count` | business_value_test_index.py:602 | BusinessValueTestIndexer.ge... | `ABC`, `ABORT` |
| `highest\_impact\_files` | coverage_reporter.py:210 | CoverageReporter._analyze_c... | `ABC`, `ABORT` |
| `highlight` | test_discovery_report.py:94 | EnhancedTestDiscoveryReport... | `ABC`, `ABORT` |
| `highly\_similar` | analyze_test_overlap.py:66 | TestOverlapAnalyzer.__init__ | `ABC`, `ABORT` |
| `history` | cleanup_generated_files.py:25 | module | `ABC`, `ABORT` |
| `hit\_rate` | real_service_test_metrics.py:24 | RealServiceTestMetrics.__in... | `ABC`, `ABORT` |
| `hits` | coverage_reporter.py:123 | CoverageReporter.parse_cove... | `ABC`, `ABORT` |
| `hooks` | git_hooks_manager.py:17 | GitHooksManager.__init__ | `ABC`, `ABORT` |
| `hooks\_directory` | git_hooks_manager.py:99 | GitHooksManager.get_status | `ABC`, `ABORT` |
| `host` | environment_validator.py:229 | EnvironmentValidator.test_c... | `ABC`, `ABORT` |
| `hourly` | seed_staging_data.py:232 | StagingDataSeeder._generate... | `ABC`, `ABORT` |
| `html` | coverage_config.py:66 | CoverageConfig.get_coverage... | `ABC`, `ABORT` |
| `html\_url` | verify_workflow_status.py:128 | WorkflowStatusVerifier._par... | `ABC`, `ABORT` |
| `htmlcov` | coverage_config.py:41 | CoverageConfig | `ABC`, `ABORT` |
| `http` | main.py:269 | add_service_headers | `ABC`, `ABORT` |
| `http\_port` | installer_types.py:77 | create_version_requirements | `ABC`, `ABORT` |
| `https` | validate_staging_health.py:212 | StagingSecurityValidator.va... | `ABC`, `ABORT` |
| `httpx` | config_setup_scripts.py:144 | test_python_imports | `ABC`, `ABORT` |
| `iat` | jwt_handler.py:122 | JWTHandler._build_payload | `ABC`, `ABORT` |
| `ID` | verify_workflow_status.py:246 | OutputFormatter.display_table | `ABC`, `ABORT` |
| `id` | repository.py:41 | AuthUserRepository.create_o... | `ABC`, `ABORT` |
| `id\_field` | scan_string_literals.py:81 | StringLiteralCategorizer | `ABC`, `ABORT` |
| `id\_token` | token_factory.py:198 | OAuthTokenFactory.create_go... | `ABC`, `ABORT` |
| `identified\_date` | update_spec_timestamps.py:178 | add_timestamp_to_xml | `ABC`, `ABORT` |
| `identifiers` | scan_string_literals.py:78 | StringLiteralCategorizer | `ABC`, `ABORT` |
| `if\_branch` | auto_decompose_functions.py:143 | FunctionDecomposer._identif... | `ABC`, `ABORT` |
| `ignore` | boundary_enforcer.py:204 | main | `ABC`, `ABORT` |
| `ignore\_folders` | check_architecture_compliance.py:30 | _create_enforcer | `ABC`, `ABORT` |
| `images` | cleanup_staging_environments.py:224 | StagingEnvironmentCleaner.c... | `ABC`, `ABORT` |
| `immediate\_fixes` | real_test_linter.py:193 | RealTestLinter.generate_fix... | `ABC`, `ABORT` |
| `impact` | generate_startup_integration_tests.py:22 | module | `ABC`, `ABORT` |
| `impact\_level` | test_backend_optimized.py:347 | print_results_summary | `ABC`, `ABORT` |
| `impact\_score` | emergency_boundary_actions.py:94 | EmergencyActionSystem._coun... | `ABC`, `ABORT` |
| `implementation\_steps` | seed_staging_data.py:249 | StagingDataSeeder._generate... | `ABC`, `ABORT` |
| `import` | align_test_imports.py:129 | TestImportAligner.fix_relat... | `ABC`, `ABORT` |
| `import\_correction` | fix_test_batch.py:312 | BatchTestProcessor._apply_t... | `ABC`, `ABORT` |
| `import\_error` | analyze_failures.py:32 | TestFailureAnalyzer | `ABC`, `ABORT` |
| `import\_errors` | check_e2e_imports.py:51 | E2EImportChecker.__init__ | `ABC`, `ABORT` |
| `import\_fixes` | align_test_imports.py:410 | TestImportAligner.generate_... | `ABC`, `ABORT` |
| `import\_similarity` | analyze_test_overlap.py:632 | TestOverlapAnalyzer._save_c... | `ABC`, `ABORT` |
| `import\_statement` | check_schema_imports.py:43 | SchemaViolation.to_dict | `ABC`, `ABORT` |
| `important` | ultra_thinking_analyzer.py:194 | UltraThinkingAnalyzer._extr... | `ABC`, `ABORT` |
| `imported\_from` | check_schema_imports.py:44 | SchemaViolation.to_dict | `ABC`, `ABORT` |
| `imported\_items` | check_schema_imports.py:45 | SchemaViolation.to_dict | `ABC`, `ABORT` |
| `ImportError` | comprehensive_test_fixer.py:44 | TestFailureAnalyzer.analyze... | `ABC`, `ABORT` |
| `imports` | test_refactor_helper.py:106 | TestRefactorHelper.analyze_... | `ABC`, `ABORT` |
| `imports\_fixed` | fix_imports.py:245 | ImportFixer.fix_directory | `ABC`, `ABORT` |
| `improvement\_suggestions` | architecture_dashboard.py:110 | ArchitectureDashboard._rend... | `ABC`, `ABORT` |
| `improving` | team_updates_compliance_analyzer.py:83 | ComplianceAnalyzer.get_comp... | `ABC`, `ABORT` |
| `in` | aggressive_syntax_fix.py:157 | aggressive_fix | `ABC`, `ABORT` |
| `in\_development` | demo_feature_flag_system.py:47 | demonstrate_feature_flag_ba... | `ABC`, `ABORT` |
| `in\_progress` | force_cancel_workflow.py:67 | _display_and_find_stuck_runs | `ABC`, `ABORT` |
| `inactive\_hours` | cleanup_staging_environments.py:326 | StagingEnvironmentCleaner._... | `ABC`, `ABORT` |
| `inactive\_sessions\_cleaned` | test_session_cleanup.py:279 | TestSessionMaintenanceSched... | `ABC`, `ABORT` |
| `Include` | business_value_test_index.py:134 | BusinessValueTestIndexer.sc... | `ABC`, `ABORT` |
| `include` | coverage_config.py:56 | CoverageConfig.get_coverage... | `ABC`, `ABORT` |
| `incompatible` | dependency_scanner.py:217 | calculate_summary_stats | `ABC`, `ABORT` |
| `incomplete\_cache` | secret_cache.py:199 | SecretCache._generate_secre... | `ABC`, `ABORT` |
| `incorrect\_path` | e2e_import_fixer_comprehensive.py:218 | E2EImportFixer._check_import | `ABC`, `ABORT` |
| `indentation\_error` | analyze_failures.py:35 | TestFailureAnalyzer | `ABC`, `ABORT` |
| `IndentationError` | analyze_failures.py:35 | TestFailureAnalyzer | `ABC`, `ABORT` |
| `index` | split_learnings.py:93 | create_index | `ABC`, `ABORT` |
| `index\_error` | analyze_failures.py:43 | TestFailureAnalyzer | `ABC`, `ABORT` |
| `IndexError` | analyze_failures.py:43 | TestFailureAnalyzer | `ABC`, `ABORT` |
| `inf` | benchmark_optimization.py:232 | TestExecutionBenchmark._com... | `ABC`, `ABORT` |
| `INFO` | test_env.py:51 | TestEnvironment | `ABC`, `ABORT` |
| `info` | act_wrapper.py:47 | ACTWrapper._check_docker | `ABC`, `ABORT` |
| `infrastructure\_plumbing` | business_value_test_index.py:395 | BusinessValueTestIndexer._d... | `ABC`, `ABORT` |
| `inherits` | ultra_thinking_analyzer.py:92 | UltraThinkingAnalyzer._anal... | `ABC`, `ABORT` |
| `INIT` | progress_indicator.py:124 | ProgressIndicator._default_... | `ABC`, `ABORT` |
| `init` | auto_fix_test_violations.py:640 | FunctionRefactor._extract_s... | `ABC`, `ABORT` |
| `initial` | migration_runner.py:67 | MigrationRunner.check_and_r... | `ABC`, `ABORT` |
| `initialize` | test_single_database.py:33 | test_single_database_initia... | `ABC`, `ABORT` |
| `input` | real_service_test_metrics.py:33 | RealServiceTestMetrics.__in... | `ABC`, `ABORT` |
| `inputs` | test_workflows_with_act.py:188 | WorkflowTester.create_event... | `ABC`, `ABORT` |
| `install` | dependency_installer.py:66 | upgrade_pip | `ABC`, `ABORT` |
| `install\_deps` | startup_optimizer.py:615 | create_prepare_phase_steps | `ABC`, `ABORT` |
| `installed\_packages` | environment_validator_dependencies.py:78 | DependencyValidator._valida... | `ABC`, `ABORT` |
| `instruction` | split_learnings.py:109 | create_index | `ABC`, `ABORT` |
| `instructions` | setup_assistant.py:57 | _create_assistant_config | `ABC`, `ABORT` |
| `insufficient\_scope` | test_auth_oauth_errors.py:236 | TestOAuthErrorHandling.test... | `ABC`, `ABORT` |
| `integration` | test_env.py:214 | get_test_environment | `ABC`, `ABORT` |
| `integration\_patterns` | categorize_tests.py:42 | TestCategorizer._initialize... | `ABC`, `ABORT` |
| `integration\_tests` | aggressive_syntax_fix.py:17 | get_files_with_errors | `ABC`, `ABORT` |
| `IntegrationAnalyzer` | status_analyzer.py:26 | module | `ABC`, `ABORT` |
| `integrations` | config_manager.py:79 | ConfigurationManager._creat... | `ABC`, `ABORT` |
| `IntegrationStatus` | status_agent_analyzer.py:205 | HealthScoreCalculator.calcu... | `ABC`, `ABORT` |
| `interface` | auto_split_files.py:101 | FileSplitter._analyze_types... | `ABC`, `ABORT` |
| `interfaces` | comprehensive_import_scanner.py:152 | ComprehensiveImportScanner.... | `ABC`, `ABORT` |
| `internal\_overlaps` | analyze_test_overlap.py:409 | TestOverlapAnalyzer._genera... | `ABC`, `ABORT` |
| `INTERRUPT` | dev_launcher_core.py:263 | DevLauncher._wait_for_proce... | `ABC`, `ABORT` |
| `Invalid` | test_workflows_with_act.py:209 | WorkflowTester.extract_error | `ABC`, `ABORT` |
| `invalid` | test_workflows_with_act.py:210 | WorkflowTester.extract_error | `ABC`, `ABORT` |
| `invalid\_combination` | test_verify_workflow_status_corrected.py:104 | WorkflowStatusTester.test_b... | `ABC`, `ABORT` |
| `invalid\_credentials` | auth_service.py:55 | AuthService.login | `ABC`, `ABORT` |
| `invalid\_grant` | test_auth_oauth_errors.py:164 | TestOAuthErrorHandling.test... | `ABC`, `ABORT` |
| `invalid\_request` | test_auth_oauth_google.py:177 | TestGoogleOAuthFlow.test_go... | `ABC`, `ABORT` |
| `invalid\_run\_id` | test_verify_workflow_status_corrected.py:148 | WorkflowStatusTester.test_r... | `ABC`, `ABORT` |
| `invalid\_service` | auth_service.py:239 | AuthService.create_service_... | `ABC`, `ABORT` |
| `invalid\_state` | test_auth_oauth_errors.py:87 | TestOAuthErrorHandling.test... | `ABC`, `ABORT` |
| `invalid\_token` | auth_service.py:479 | AuthService.confirm_passwor... | `ABC`, `ABORT` |
| `invalid\_wait` | test_verify_workflow_status.py:95 | WorkflowStatusTester.test_a... | `ABC`, `ABORT` |
| `io\_bound` | test_backend_optimized.py:81 | module | `ABC`, `ABORT` |
| `io\_result` | test_phase3_multiprocessing.py:338 | test_phase3_integration | `ABC`, `ABORT` |
| `io\_workers` | parallel_executor.py:291 | ParallelExecutor.get_perfor... | `ABC`, `ABORT` |
| `ios\_` | session_factory.py:83 | SessionFactory.create_mobil... | `ABC`, `ABORT` |
| `ip` | repository.py:166 | AuthSessionRepository.creat... | `ABC`, `ABORT` |
| `ip\_address` | auth_routes.py:367 | dev_login | `ABC`, `ABORT` |
| `ipconfig` | recovery_actions.py:263 | RecoveryActions.reset_netwo... | `ABC`, `ABORT` |
| `is\_active` | session_factory.py:41 | SessionFactory.create_sessi... | `ABC`, `ABORT` |
| `is\_async` | extract_function_violations.py:32 | FunctionViolationExtractor.... | `ABC`, `ABORT` |
| `is\_beta` | generate_openapi_spec.py:171 | create_readme_version | `ABC`, `ABORT` |
| `is\_canonical` | check_schema_imports.py:392 | SchemaImportAnalyzer.export... | `ABC`, `ABORT` |
| `is\_cloud\_run` | connection.py:240 | AuthDatabase.get_status | `ABC`, `ABORT` |
| `is\_critical` | extract_function_violations.py:33 | FunctionViolationExtractor.... | `ABC`, `ABORT` |
| `is\_integration` | categorize_tests.py:85 | TestCategorizer._initialize... | `ABC`, `ABORT` |
| `is\_legacy` | update_spec_timestamps.py:177 | add_timestamp_to_xml | `ABC`, `ABORT` |
| `is\_ready` | main.py:313 | health_ready | `ABC`, `ABORT` |
| `is\_running` | process_manager.py:526 | ProcessManager._create_proc... | `ABC`, `ABORT` |
| `is\_stable` | generate_openapi_spec.py:170 | create_readme_version | `ABC`, `ABORT` |
| `is\_superuser` | seed_staging_data.py:122 | StagingDataSeeder._build_ad... | `ABC`, `ABORT` |
| `is\_test\_mode` | connection.py:241 | AuthDatabase.get_status | `ABC`, `ABORT` |
| `is\_unit` | categorize_tests.py:86 | TestCategorizer._initialize... | `ABC`, `ABORT` |
| `is\_valid` | secret_loader.py:153 | SecretLoader._cache_secrets... | `ABC`, `ABORT` |
| `is\_verified` | auth_service.py:227 | AuthService.create_oauth_user | `ABC`, `ABORT` |
| `isolated` | test_refactor_helper.py:202 | TestRefactorHelper._determi... | `ABC`, `ABORT` |
| `isolation\_level` | demo_real_llm_testing.py:64 | demo_environment_validation | `ABC`, `ABORT` |
| `iss` | jwt_handler.py:125 | JWTHandler._build_payload | `ABC`, `ABORT` |
| `issue` | architecture_scanner_helpers.py:191 | ScannerHelpers.create_missi... | `ABC`, `ABORT` |
| `issue\_summary` | comprehensive_import_scanner.py:86 | ComprehensiveScanReport.to_... | `ABC`, `ABORT` |
| `issues` | status_renderer.py:77 | StatusReportRenderer._build... | `ABC`, `ABORT` |
| `issues\_fixed` | comprehensive_e2e_import_fixer.py:353 | main | `ABC`, `ABORT` |
| `issues\_found` | unified_import_manager.py:97 | UnifiedImportManager.check_... | `ABC`, `ABORT` |
| `java` | agent_tracking_helper.py:33 | AgentTrackingHelper | `ABC`, `ABORT` |
| `javascript` | agent_tracking_helper.py:27 | AgentTrackingHelper | `ABC`, `ABORT` |
| `JENKINS\_URL` | config_validator.py:274 | _detect_ci_environment | `ABC`, `ABORT` |
| `jest` | cleanup_test_processes.py:70 | find_test_processes | `ABC`, `ABORT` |
| `Jobs` | act_wrapper.py:136 | ACTWrapper._create_workflow... | `ABC`, `ABORT` |
| `jobs` | act_wrapper.py:66 | ACTWrapper._parse_workflow | `ABC`, `ABORT` |
| `journeys` | fix_e2e_test_imports.py:112 | ImportFixer.scan_test_direc... | `ABC`, `ABORT` |
| `js\_excessive\_mocking` | real_test_requirements_enforcer.py:398 | RealTestRequirementsEnforce... | `ABC`, `ABORT` |
| `js\_function\_size` | real_test_requirements_enforcer.py:445 | RealTestRequirementsEnforce... | `ABC`, `ABORT` |
| `js\_mock\_component` | real_test_requirements_enforcer.py:380 | RealTestRequirementsEnforce... | `ABC`, `ABORT` |
| `json` | coverage_config.py:73 | CoverageConfig.get_coverage... | `ABC`, `ABORT` |
| `json\_output` | test_verify_workflow_status.py:145 | WorkflowStatusTester.test_o... | `ABC`, `ABORT` |
| `json\_output\_format` | test_verify_workflow_status_corrected.py:169 | WorkflowStatusTester.test_o... | `ABC`, `ABORT` |
| `jsonrpc` | test_websocket_connection_issue.py:46 | TestWebSocketConnectionIssu... | `ABC`, `ABORT` |
| `jspm\_packages` | core.py:87 | ComplianceConfig._get_skip_... | `ABC`, `ABORT` |
| `jsx` | agent_tracking_helper.py:29 | AgentTrackingHelper | `ABC`, `ABORT` |
| `jti` | token_factory.py:42 | TokenFactory.create_token_c... | `ABC`, `ABORT` |
| `justification` | business_value_test_index.py:611 | BusinessValueTestIndexer.ge... | `ABC`, `ABORT` |
| `JWT` | test_auth_token_security.py:211 | TestJWTSignatureVerificatio... | `ABC`, `ABORT` |
| `jwt` | coverage_reporter.py:280 | CoverageReporter._generate_... | `ABC`, `ABORT` |
| `JWT\_` | local_secrets.py:93 | LocalSecretManager._is_rele... | `ABC`, `ABORT` |
| `JWT\_ACCESS\_EXPIRY\_MINUTES` | config.py:48 | AuthConfig.get_jwt_access_e... | `ABC`, `ABORT` |
| `JWT\_ALGORITHM` | config.py:42 | AuthConfig.get_jwt_algorithm | `ABC`, `ABORT` |
| `jwt\_handler` | test_mixins.py:153 | AuthTestMixin.setup_auth_mocks | `ABC`, `ABORT` |
| `JWT\_REFRESH\_EXPIRY\_DAYS` | config.py:54 | AuthConfig.get_jwt_refresh_... | `ABC`, `ABORT` |
| `JWT\_SECRET` | secret_loader.py:66 | AuthSecretLoader.get_jwt_se... | `ABC`, `ABORT` |
| `JWT\_SECRET\_KEY` | secret_loader.py:60 | AuthSecretLoader.get_jwt_se... | `ABC`, `ABORT` |
| `jwt\_secret\_key` | test_config_loading.py:94 | _check_auth_configurations | `ABC`, `ABORT` |
| `JWT\_SECRET\_PRODUCTION` | secret_loader.py:47 | AuthSecretLoader.get_jwt_se... | `ABC`, `ABORT` |
| `JWT\_SECRET\_STAGING` | secret_loader.py:34 | AuthSecretLoader.get_jwt_se... | `ABC`, `ABORT` |
| `JWT\_SERVICE\_EXPIRY\_MINUTES` | config.py:60 | AuthConfig.get_jwt_service_... | `ABC`, `ABORT` |
| `JWTConstants` | auth_constants_migration.py:100 | AuthConstantsMigrator.__init__ | `ABC`, `ABORT` |
| `K\_REVISION` | test_config_loading.py:35 | _print_environment_variables | `ABC`, `ABORT` |
| `K\_SERVICE` | connection.py:30 | AuthDatabase.__init__ | `ABC`, `ABORT` |
| `KB` | cleanup_generated_files.py:147 | format_bytes | `ABC`, `ABORT` |
| `KEY` | test_config_loading.py:50 | _mask_sensitive_value | `ABC`, `ABORT` |
| `key` | unicode_utils.py:89 | module | `ABC`, `ABORT` |
| `key\_error` | analyze_failures.py:42 | TestFailureAnalyzer | `ABC`, `ABORT` |
| `key\_prefix` | environment_validator.py:301 | EnvironmentValidator.valida... | `ABC`, `ABORT` |
| `keyboard\_interrupt` | analyze_failures.py:53 | TestFailureAnalyzer | `ABC`, `ABORT` |
| `KeyboardInterrupt` | analyze_failures.py:53 | TestFailureAnalyzer | `ABC`, `ABORT` |
| `KeyError` | analyze_failures.py:42 | TestFailureAnalyzer | `ABC`, `ABORT` |
| `kotlin` | agent_tracking_helper.py:43 | AgentTrackingHelper | `ABC`, `ABORT` |
| `Langfuse` | dev_launcher_secrets.py:240 | EnhancedSecretLoader._get_e... | `ABC`, `ABORT` |
| `LANGFUSE\_` | local_secrets.py:92 | LocalSecretManager._is_rele... | `ABC`, `ABORT` |
| `langfuse\_keys` | environment_validator.py:311 | EnvironmentValidator.valida... | `ABC`, `ABORT` |
| `LANGFUSE\_PUBLIC\_KEY` | dev_launcher_secrets.py:108 | EnhancedSecretLoader._get_s... | `ABC`, `ABORT` |
| `LANGFUSE\_SECRET\_KEY` | dev_launcher_secrets.py:107 | EnhancedSecretLoader._get_s... | `ABC`, `ABORT` |
| `large` | ssot_checker.py:138 | SSOTChecker._get_function_s... | `ABC`, `ABORT` |
| `largest\_file` | test_size_validator.py:85 | TestSizeValidator.validate_... | `ABC`, `ABORT` |
| `largest\_function` | test_size_validator.py:86 | TestSizeValidator.validate_... | `ABC`, `ABORT` |
| `last\_activity` | session_manager.py:67 | SessionManager.create_session | `ABC`, `ABORT` |
| `last\_check` | boundary_monitor.py:215 | BoundaryMonitorIntegration.... | `ABC`, `ABORT` |
| `last\_day` | team_updates.py:38 | main | `ABC`, `ABORT` |
| `last\_edited` | update_spec_timestamps.py:162 | add_timestamp_to_xml | `ABC`, `ABORT` |
| `last\_error` | database_connector.py:659 | DatabaseConnector.get_conne... | `ABC`, `ABORT` |
| `last\_hour` | team_updates.py:39 | main | `ABC`, `ABORT` |
| `last\_month` | team_updates.py:39 | main | `ABC`, `ABORT` |
| `last\_startup` | cache_manager.py:272 | CacheManager._get_successfu... | `ABC`, `ABORT` |
| `last\_startup\_time` | cache_manager.py:371 | CacheManager.get_cache_stats | `ABC`, `ABORT` |
| `last\_updated` | split_learnings.py:71 | create_category_file | `ABC`, `ABORT` |
| `last\_week` | team_updates.py:39 | main | `ABC`, `ABORT` |
| `lastTransitionTime` | cleanup_staging_environments.py:63 | StagingEnvironmentCleaner.g... | `ABC`, `ABORT` |
| `latency` | seed_staging_data.py:229 | StagingDataSeeder._generate... | `ABC`, `ABORT` |
| `latency\_optimization` | seed_staging_data.py:208 | StagingDataSeeder._get_opti... | `ABC`, `ABORT` |
| `latest` | build_staging.py:48 | StagingBuilder.build_backend | `ABC`, `ABORT` |
| `LAUNCH` | dev_launcher_core.py:150 | DevLauncher.run | `ABC`, `ABORT` |
| `LauncherConfig` | config.py:122 | LauncherConfig.from_args | `ABC`, `ABORT` |
| `learning` | split_learnings.py:36 | parse_learnings | `ABC`, `ABORT` |
| `learnings` | split_learnings.py:68 | create_category_file | `ABC`, `ABORT` |
| `LEGACY` | update_spec_timestamps.py:25 | module | `ABC`, `ABORT` |
| `legacy` | generate_test_audit.py:226 | generate_audit_report | `ABC`, `ABORT` |
| `legacy\_framework` | test_reviewer.py:161 | AutonomousTestReviewer._ass... | `ABC`, `ABORT` |
| `legacy\_integration\_tests` | check_e2e_imports.py:45 | E2EImportChecker.__init__ | `ABC`, `ABORT` |
| `legacy\_status` | update_spec_timestamps.py:173 | add_timestamp_to_xml | `ABC`, `ABORT` |
| `length` | check_test_compliance.py:61 | check_function_lengths | `ABC`, `ABORT` |
| `level` | emergency_boundary_actions.py:62 | EmergencyActionSystem.execu... | `ABC`, `ABORT` |
| `levels` | workflow_config_utils.py:53 | WorkflowConfigUtils._show_t... | `ABC`, `ABORT` |
| `Lib` | business_value_test_index.py:134 | BusinessValueTestIndexer.sc... | `ABC`, `ABORT` |
| `lib` | core.py:87 | ComplianceConfig._get_skip_... | `ABC`, `ABORT` |
| `libs` | core.py:87 | ComplianceConfig._get_skip_... | `ABC`, `ABORT` |
| `LICENSE` | agent_tracking_helper.py:64 | AgentTrackingHelper | `ABC`, `ABORT` |
| `license` | generate_openapi_spec.py:69 | _add_contact_info | `ABC`, `ABORT` |
| `line` | architecture_scanner.py:132 | ArchitectureScanner._extrac... | `ABC`, `ABORT` |
| `line\_count` | function_complexity_analyzer.py:386 | _convert_results_to_json | `ABC`, `ABORT` |
| `line\_num` | extract_violations.py:26 | extract_violations | `ABC`, `ABORT` |
| `line\_number` | architecture_scanner_helpers.py:178 | ScannerHelpers.create_funct... | `ABC`, `ABORT` |
| `line\_violations` | team_updates_compliance_analyzer.py:29 | ComplianceAnalyzer.analyze | `ABC`, `ABORT` |
| `lineno` | analyze_critical_paths.py:19 | count_function_lines | `ABC`, `ABORT` |
| `Lines` | architecture_dashboard_tables.py:22 | DashboardTableRenderers.ren... | `ABC`, `ABORT` |
| `lines` | architecture_dashboard_tables.py:33 | DashboardTableRenderers._ge... | `ABC`, `ABORT` |
| `lines\_added` | agent_tracking_helper.py:354 | AgentTrackingHelper.create_... | `ABC`, `ABORT` |
| `lines\_covered` | generate_report.py:165 | parse_coverage_xml | `ABC`, `ABORT` |
| `lines\_deleted` | metadata_header_generator.py:120 | MetadataHeaderGenerator.gen... | `ABC`, `ABORT` |
| `lines\_modified` | metadata_header_generator.py:119 | MetadataHeaderGenerator.gen... | `ABC`, `ABORT` |
| `lines\_removed` | agent_tracking_helper.py:355 | AgentTrackingHelper.create_... | `ABC`, `ABORT` |
| `lines\_scanned` | crash_detector.py:94 | CrashDetector.detect_log_crash | `ABC`, `ABORT` |
| `lines\_valid` | generate_report.py:166 | parse_coverage_xml | `ABC`, `ABORT` |
| `lint` | test_frontend.py:315 | run_lint | `ABC`, `ABORT` |
| `lint\_issues` | metadata_header_generator.py:123 | MetadataHeaderGenerator.gen... | `ABC`, `ABORT` |
| `linux` | installer_types.py:55 | create_installer_config | `ABC`, `ABORT` |
| `list` | act_wrapper.py:211 | add_subcommands | `ABC`, `ABORT` |
| `LISTEN` | system_diagnostics.py:76 | SystemDiagnostics._extract_... | `ABC`, `ABORT` |
| `LISTENING` | port_manager.py:140 | PortManager._windows_port_c... | `ABC`, `ABORT` |
| `listening` | environment_validator_ports.py:102 | PortValidator._check_port_a... | `ABC`, `ABORT` |
| `literals` | query_string_literals.py:42 | StringLiteralQuery.search | `ABC`, `ABORT` |
| `live` | validate_staging_health.py:42 | StagingHealthValidator.vali... | `ABC`, `ABORT` |
| `LLM` | categorize_tests.py:249 | TestCategorizer._extract_se... | `ABC`, `ABORT` |
| `llm` | auto_fix_test_sizes.py:354 | TestFileSplitter._determine... | `ABC`, `ABORT` |
| `LLM\_` | config_validator.py:282 | _extract_env_overrides | `ABC`, `ABORT` |
| `llm\_calls` | real_service_test_metrics.py:21 | RealServiceTestMetrics.__in... | `ABC`, `ABORT` |
| `llm\_configs` | test_config_loading.py:78 | _check_llm_configurations | `ABC`, `ABORT` |
| `llm\_costs` | real_service_test_metrics.py:22 | RealServiceTestMetrics.__in... | `ABC`, `ABORT` |
| `LLMCostOptimizer` | fast_import_checker.py:164 | fix_known_import_issues | `ABC`, `ABORT` |
| `load` | auto_fix_test_sizes.py:348 | TestFileSplitter._determine... | `ABC`, `ABORT` |
| `load\_all\_secrets` | test_dev_user_flow.py:239 | TestDevLauncherIntegration.... | `ABC`, `ABORT` |
| `load\_cache` | startup_optimizer.py:597 | create_init_phase_steps | `ABC`, `ABORT` |
| `load\_env` | startup_optimizer.py:599 | create_init_phase_steps | `ABC`, `ABORT` |
| `LOAD\_SECRETS` | test_config_loading.py:35 | _print_environment_variables | `ABC`, `ABORT` |
| `load\_secrets` | config.py:208 | LauncherConfig.to_dict | `ABC`, `ABORT` |
| `load\_test\_config` | __init__.py:9 | module | `ABC`, `ABORT` |
| `loaded` | cache_warmer.py:139 | CacheWarmer._warm_environme... | `ABC`, `ABORT` |
| `Local` | config.py:313 | LauncherConfig._print_servi... | `ABC`, `ABORT` |
| `local` | models.py:23 | AuthUser | `ABC`, `ABORT` |
| `localhost` | main.py:264 | module | `ABC`, `ABORT` |
| `Location` | test_auth_oauth_errors.py:142 | TestOAuthErrorHandling.test... | `ABC`, `ABORT` |
| `location` | test_oauth_flows_sync.py:41 | TestOAuthBasicEndpoints.tes... | `ABC`, `ABORT` |
| `locations` | query_string_literals.py:90 | StringLiteralQuery.validate | `ABC`, `ABORT` |
| `lock` | unicode_utils.py:90 | module | `ABC`, `ABORT` |
| `lock\_reason` | audit_factory.py:193 | AuditLogFactory.create_acco... | `ABC`, `ABORT` |
| `LOCKOUT\_DURATION\_MINUTES` | auth_service.py:44 | AuthService.__init__ | `ABC`, `ABORT` |
| `log` | boundary_enforcer_system_checks.py:121 | SystemMetricsCalculator._ge... | `ABC`, `ABORT` |
| `log\_analysis` | crash_recovery_models.py:26 | DetectionMethod | `ABC`, `ABORT` |
| `log\_dir` | config.py:215 | LauncherConfig.to_dict | `ABC`, `ABORT` |
| `log\_exists` | crash_detector.py:108 | CrashDetector._create_log_n... | `ABC`, `ABORT` |
| `log\_file` | crash_detector.py:94 | CrashDetector.detect_log_crash | `ABC`, `ABORT` |
| `LOG\_LEVEL` | test_env.py:51 | TestEnvironment | `ABC`, `ABORT` |
| `log\_manager` | launcher.py:201 | DevLauncher._graceful_shutdown | `ABC`, `ABORT` |
| `LogFilter` | log_filter.py:235 | LogFilter.from_env | `ABC`, `ABORT` |
| `logging` | monitor_oauth_flow.py:105 | OAuthMonitor.monitor_logs | `ABC`, `ABORT` |
| `logical` | auto_split_files.py:204 | FileSplitter._suggest_logic... | `ABC`, `ABORT` |
| `logical\_blocks` | auto_decompose_functions.py:231 | FunctionDecomposer._suggest... | `ABC`, `ABORT` |
| `login` | auth_service.py:91 | AuthService.login | `ABC`, `ABORT` |
| `login\_attempt` | audit_factory.py:39 | AuditLogFactory.create_audi... | `ABC`, `ABORT` |
| `LOGIN\_FAILED` | audit_factory.py:20 | AuditLogFactory | `ABC`, `ABORT` |
| `login\_failed` | audit_factory.py:20 | AuditLogFactory | `ABC`, `ABORT` |
| `login\_method` | audit_factory.py:75 | AuditLogFactory.create_logi... | `ABC`, `ABORT` |
| `LOGIN\_SUCCESS` | audit_factory.py:19 | AuditLogFactory | `ABC`, `ABORT` |
| `login\_success` | audit_factory.py:19 | AuditLogFactory | `ABC`, `ABORT` |
| `LogLevel` | log_filter.py:339 | module | `ABC`, `ABORT` |
| `LOGOUT` | audit_factory.py:21 | AuditLogFactory | `ABC`, `ABORT` |
| `logout` | auth_service.py:130 | AuthService.logout | `ABC`, `ABORT` |
| `logout\_type` | audit_factory.py:107 | AuditLogFactory.create_logo... | `ABC`, `ABORT` |
| `logs` | build_staging.py:230 | StagingBuilder.view_logs | `ABC`, `ABORT` |
| `logs\_url` | workflow_introspection.py:203 | WorkflowIntrospector.get_wo... | `ABC`, `ABORT` |
| `loops` | function_complexity_analyzer.py:61 | FunctionVisitor._analyze_fu... | `ABC`, `ABORT` |
| `LOW` | generate_security_report.py:99 | _format_vulnerability_groups | `ABC`, `ABORT` |
| `Low` | metadata_header_generator.py:321 | MetadataHeaderGenerator.add... | `ABC`, `ABORT` |
| `low` | code_review_ai_detector.py:19 | CodeReviewAIDetector.__init__ | `ABC`, `ABORT` |
| `low\_confidence\_count` | analyze_failures.py:80 | TestFailureAnalyzer.analyze... | `ABC`, `ABORT` |
| `low\_risk` | config_manager.py:38 | ConfigurationManager._get_f... | `ABC`, `ABORT` |
| `low\_test\_count` | business_value_test_index.py:629 | BusinessValueTestIndexer._i... | `ABC`, `ABORT` |
| `low\_tier\_coverage` | business_value_test_index.py:647 | BusinessValueTestIndexer._i... | `ABC`, `ABORT` |
| `lowest\_coverage\_files` | coverage_reporter.py:206 | CoverageReporter._analyze_c... | `ABC`, `ABORT` |
| `ls` | dependency_scanner.py:133 | get_installed_node_packages | `ABC`, `ABORT` |
| `lsof` | port_manager.py:160 | PortManager._unix_port_check | `ABC`, `ABORT` |
| `MAD` | team_updates_documentation_analyzer.py:114 | DocumentationAnalyzer._pars... | `ABC`, `ABORT` |
| `magenta` | verify_workflow_status.py:250 | OutputFormatter.display_table | `ABC`, `ABORT` |
| `magic\_mock` | analyze_mocks.py:42 | MockAnalyzer.__init__ | `ABC`, `ABORT` |
| `magnifier` | unicode_utils.py:91 | module | `ABC`, `ABORT` |
| `Main` | test_fixer.py:158 | TestFixer._group_tests_by_c... | `ABC`, `ABORT` |
| `main` | ultra_thinking_analyzer.py:167 | UltraThinkingAnalyzer._iden... | `ABC`, `ABORT` |
| `main\_clickhouse` | database_connector.py:142 | DatabaseConnector._discover... | `ABC`, `ABORT` |
| `main\_postgres` | database_connector.py:136 | DatabaseConnector._discover... | `ABC`, `ABORT` |
| `main\_redis` | database_connector.py:148 | DatabaseConnector._discover... | `ABC`, `ABORT` |
| `major` | project_test_validator.py:157 | ProjectTestValidator._check... | `ABC`, `ABORT` |
| `malicious\_data` | test_security.py:333 | TestInputValidation.test_js... | `ABC`, `ABORT` |
| `malicious\_headers` | test_security.py:65 | security_test_payloads | `ABC`, `ABORT` |
| `managed` | deploy_to_gcp.py:470 | GCPDeployer.deploy_service | `ABC`, `ABORT` |
| `manager` | auto_fix_test_sizes.py:365 | TestFileSplitter._determine... | `ABC`, `ABORT` |
| `manager\_` | ssot_checker.py:100 | SSOTChecker._check_duplicat... | `ABC`, `ABORT` |
| `managers` | auto_fix_test_sizes.py:366 | TestFileSplitter._determine... | `ABC`, `ABORT` |
| `manual\_review` | fix_test_batch.py:82 | TestAnalyzer.analyze_failure | `ABC`, `ABORT` |
| `mark` | analyze_test_overlap.py:194 | TestOverlapAnalyzer._extrac... | `ABC`, `ABORT` |
| `markdown` | generate_performance_report.py:14 | generate_performance_report | `ABC`, `ABORT` |
| `max` | real_service_test_metrics.py:95 | RealServiceTestMetrics.fina... | `ABC`, `ABORT` |
| `max\_age\_days` | cleanup_generated_files.py:298 | main | `ABC`, `ABORT` |
| `max\_cost\_per\_pr` | cleanup_staging_environments.py:332 | StagingEnvironmentCleaner._... | `ABC`, `ABORT` |
| `max\_failures` | health_monitor.py:171 | HealthMonitor.register_service | `ABC`, `ABORT` |
| `max\_file\_lines` | core.py:169 | _build_summary | `ABC`, `ABORT` |
| `max\_function\_lines` | core.py:170 | _build_summary | `ABC`, `ABORT` |
| `max\_lines` | enforce_limits.py:199 | EnforcementReporter.generat... | `ABC`, `ABORT` |
| `max\_lines\_allowed` | function_complexity_linter.py:167 | FunctionComplexityLinter.ge... | `ABC`, `ABORT` |
| `MAX\_LOGIN\_ATTEMPTS` | auth_service.py:43 | AuthService.__init__ | `ABC`, `ABORT` |
| `max\_overflow` | connection.py:75 | AuthDatabase.initialize | `ABC`, `ABORT` |
| `MAX\_SESSIONS\_PER\_USER` | test_settings.py:181 | TestSettings.to_env_dict | `ABC`, `ABORT` |
| `max\_workers` | test_backend_optimized.py:179 | OptimizedTestManager._creat... | `ABC`, `ABORT` |
| `MB` | cleanup_generated_files.py:147 | format_bytes | `ABC`, `ABORT` |
| `MCPClientCreateRequest` | fix_all_import_issues.py:68 | ComprehensiveImportFixer._b... | `ABC`, `ABORT` |
| `md` | startup_reporter.py:82 | MarkdownReportGenerator.gen... | `ABC`, `ABORT` |
| `median\_coverage` | coverage_reporter.py:221 | CoverageReporter._analyze_c... | `ABC`, `ABORT` |
| `MEDIUM` | check_test_stubs.py:68 | CITestStubChecker._print_de... | `ABC`, `ABORT` |
| `Medium` | metadata_header_generator.py:77 | MetadataHeaderGenerator.gen... | `ABC`, `ABORT` |
| `medium` | architecture_metrics.py:19 | ArchitectureMetrics | `ABC`, `ABORT` |
| `medium\_confidence\_count` | analyze_failures.py:79 | TestFailureAnalyzer.analyze... | `ABC`, `ABORT` |
| `medium\_risk` | config_manager.py:37 | ConfigurationManager._get_f... | `ABC`, `ABORT` |
| `memory` | auto_fix_test_sizes.py:352 | TestFileSplitter._determine... | `ABC`, `ABORT` |
| `memory\_after\_startup` | startup_performance.py:30 | PerformanceMetrics.to_dict | `ABC`, `ABORT` |
| `memory\_aware` | test_backend_optimized.py:69 | module | `ABC`, `ABORT` |
| `memory\_baseline` | startup_performance.py:29 | PerformanceMetrics.to_dict | `ABC`, `ABORT` |
| `memory\_per\_worker\_mb` | test_backend_optimized.py:180 | OptimizedTestManager._creat... | `ABC`, `ABORT` |
| `memory\_total` | startup_environment.py:47 | StartupEnvironment._record_... | `ABC`, `ABORT` |
| `memory\_usage` | seed_staging_data.py:284 | StagingDataSeeder._get_metr... | `ABC`, `ABORT` |
| `memory\_used` | environment_validator.py:268 | EnvironmentValidator.test_r... | `ABC`, `ABORT` |
| `merged` | cleanup_staging_environments.py:97 | StagingEnvironmentCleaner.c... | `ABC`, `ABORT` |
| `Message` | deduplicate_types.py:81 | TypeDeduplicator._setup_pyt... | `ABC`, `ABORT` |
| `message` | assertion_helpers.py:159 | AssertionHelpers.assert_err... | `ABC`, `ABORT` |
| `message\_flow` | test_websocket_dev_mode.py:44 | WebSocketDevModeTest.__init__ | `ABC`, `ABORT` |
| `messages` | seed_staging_data.py:55 | StagingDataSeeder.__init__ | `ABC`, `ABORT` |
| `messages\_per\_thread` | seed_staging_data.py:153 | StagingDataSeeder.seed_thre... | `ABC`, `ABORT` |
| `messages\_seen` | log_filter.py:229 | LogFilter.get_filter_stats | `ABC`, `ABORT` |
| `MessageType` | deduplicate_types.py:82 | TypeDeduplicator._setup_pyt... | `ABC`, `ABORT` |
| `metadata` | architecture_reporter.py:39 | ArchitectureReporter._build... | `ABC`, `ABORT` |
| `metadata\_` | setup_assistant.py:60 | _create_assistant_config | `ABC`, `ABORT` |
| `metadata\_validator` | hooks_manager.py:118 | GitHooksManager._validate_h... | `ABC`, `ABORT` |
| `MetadataTrackingEnabler` | __init__.py:23 | module | `ABC`, `ABORT` |
| `method` | benchmark_optimization.py:135 | TestExecutionBenchmark._run... | `ABC`, `ABORT` |
| `method\_names` | test_size_validator.py:333 | TestSizeValidator._analyze_... | `ABC`, `ABORT` |
| `methods` | test_generator.py:213 | _generate_method_tests | `ABC`, `ABORT` |
| `metric\_name` | scan_string_literals.py:94 | StringLiteralCategorizer | `ABC`, `ABORT` |
| `metric\_status` | scan_string_literals.py:95 | StringLiteralCategorizer | `ABC`, `ABORT` |
| `metric\_type` | seed_staging_data.py:315 | StagingDataSeeder._create_m... | `ABC`, `ABORT` |
| `metrics` | architecture_dashboard.py:64 | ArchitectureDashboard._prep... | `ABC`, `ABORT` |
| `metrics\_collected` | startup_profiler.py:290 | StartupProfiler.get_perform... | `ABC`, `ABORT` |
| `MetricsCalculationError` | fix_comprehensive_imports.py:100 | ComprehensiveImportFixerV2.... | `ABC`, `ABORT` |
| `MetricType` | validate_type_deduplication.py:71 | TypeDeduplicationValidator.... | `ABC`, `ABORT` |
| `mid` | business_value_test_index.py:109 | BusinessValueTestIndexer.__... | `ABC`, `ABORT` |
| `Migrating` | auth_constants_migration.py:283 | AuthConstantsMigrator.migra... | `ABC`, `ABORT` |
| `migration` | auto_fix_test_sizes.py:340 | TestFileSplitter._determine... | `ABC`, `ABORT` |
| `migration\_check` | launcher.py:327 | DevLauncher._register_optim... | `ABC`, `ABORT` |
| `migration\_files` | cache_warmer.py:58 | CacheWarmer._warm_migration... | `ABC`, `ABORT` |
| `MIGRATIONS` | migration_runner.py:44 | MigrationRunner.check_and_r... | `ABC`, `ABORT` |
| `migrations` | architecture_metrics.py:265 | ArchitectureMetrics._should... | `ABC`, `ABORT` |
| `min` | real_service_test_metrics.py:94 | RealServiceTestMetrics.fina... | `ABC`, `ABORT` |
| `min\_length` | environment_validator_core.py:77 | EnvironmentValidatorCore._d... | `ABC`, `ABORT` |
| `min\_version` | installer_types.py:68 | create_version_requirements | `ABC`, `ABORT` |
| `minimal` | manage_workflows.py:196 | _setup_utility_parsers | `ABC`, `ABORT` |
| `minor` | project_test_validator.py:313 | ProjectTestValidator.genera... | `ABC`, `ABORT` |
| `minor\_issues` | team_updates_formatter.py:13 | HumanFormatter.__init__ | `ABC`, `ABORT` |
| `misc` | test_refactor_helper.py:557 | TestRefactorHelper._extract... | `ABC`, `ABORT` |
| `misses` | real_service_test_metrics.py:24 | RealServiceTestMetrics.__in... | `ABC`, `ABORT` |
| `MISSING` | test_config_loading.py:87 | _check_single_llm_config | `ABC`, `ABORT` |
| `missing` | analyze_coverage.py:15 | module | `ABC`, `ABORT` |
| `missing\_args` | test_verify_workflow_status.py:88 | WorkflowStatusTester.test_a... | `ABC`, `ABORT` |
| `missing\_argument` | analyze_failures.py:44 | TestFailureAnalyzer | `ABC`, `ABORT` |
| `missing\_assertion` | test_reviewer.py:163 | AutonomousTestReviewer._ass... | `ABC`, `ABORT` |
| `missing\_attr` | fix_test_batch.py:60 | TestAnalyzer.analyze_failure | `ABC`, `ABORT` |
| `missing\_imports` | validate_frontend_tests.py:202 | FrontendTestValidator._gene... | `ABC`, `ABORT` |
| `missing\_item` | comprehensive_test_fixer.py:34 | TestFailureAnalyzer.analyze... | `ABC`, `ABORT` |
| `missing\_keys` | secret_loader.py:154 | SecretLoader._cache_secrets... | `ABC`, `ABORT` |
| `missing\_lines` | coverage_reporter.py:62 | CoverageReporter.parse_cove... | `ABC`, `ABORT` |
| `missing\_module` | comprehensive_import_scanner.py:294 | ComprehensiveImportScanner.... | `ABC`, `ABORT` |
| `missing\_modules` | check_imports.py:34 | ImportAnalyzer.analyze_file | `ABC`, `ABORT` |
| `missing\_name` | comprehensive_import_scanner.py:360 | ComprehensiveImportScanner.... | `ABC`, `ABORT` |
| `missing\_nodejs` | environment_validator_dependencies.py:185 | DependencyValidator._valida... | `ABC`, `ABORT` |
| `missing\_providers` | demo_real_llm_testing.py:63 | demo_environment_validation | `ABC`, `ABORT` |
| `missing\_python` | environment_validator_dependencies.py:183 | DependencyValidator._valida... | `ABC`, `ABORT` |
| `missing\_required\_args` | test_verify_workflow_status_corrected.py:95 | WorkflowStatusTester.test_b... | `ABC`, `ABORT` |
| `missing\_token` | test_verify_workflow_status.py:104 | WorkflowStatusTester.test_t... | `ABC`, `ABORT` |
| `missing\_type` | architecture_scanner_helpers.py:193 | ScannerHelpers.create_missi... | `ABC`, `ABORT` |
| `missing\_type\_annotations` | architecture_metrics.py:49 | ArchitectureMetrics._calcul... | `ABC`, `ABORT` |
| `mixed` | parallel_executor.py:29 | TaskType | `ABC`, `ABORT` |
| `mobile` | test_session_management.py:180 | TestMultiDeviceSessionManag... | `ABC`, `ABORT` |
| `Mock` | validate_agent_tests.py:185 | AgentTestValidator.analyze_... | `ABC`, `ABORT` |
| `mock` | business_value_test_index.py:354 | BusinessValueTestIndexer._d... | `ABC`, `ABORT` |
| `mock\_` | real_test_requirements_enforcer.py:356 | RealTestRequirementsEnforce... | `ABC`, `ABORT` |
| `mock\_access\_token` | test_oauth_flows_sync.py:156 | test_oauth_token_exchange_m... | `ABC`, `ABORT` |
| `mock\_call` | analyze_mocks.py:41 | MockAnalyzer.__init__ | `ABC`, `ABORT` |
| `mock\_clickhouse\_client` | fix_e2e_tests_comprehensive.py:57 | E2ETestFixer._get_common_fi... | `ABC`, `ABORT` |
| `mock\_client\_id` | test_client.py:190 | AuthTestClient.get_auth_config | `ABC`, `ABORT` |
| `mock\_component\_class` | project_test_validator.py:174 | MockComponentVisitor.visit_... | `ABC`, `ABORT` |
| `mock\_component\_function` | project_test_validator.py:186 | MockComponentVisitor.visit_... | `ABC`, `ABORT` |
| `mock\_component\_pattern` | real_test_validator.py:158 | RealTestValidator._check_mo... | `ABC`, `ABORT` |
| `mock\_components` | check_test_compliance.py:92 | scan_test_files | `ABC`, `ABORT` |
| `mock\_count` | check_test_compliance.py:127 | scan_test_files | `ABC`, `ABORT` |
| `mock\_database\_clients` | fix_e2e_tests_comprehensive.py:70 | E2ETestFixer._get_common_fi... | `ABC`, `ABORT` |
| `mock\_implementation\_comment` | remove_test_stubs.py:150 | TestStubDetector._scan_comm... | `ABC`, `ABORT` |
| `mock\_implementation\_comments` | remove_test_stubs.py:47 | TestStubDetector.__init__ | `ABC`, `ABORT` |
| `mock\_justification` | mock_justification_checker.py:168 | MockJustificationChecker._c... | `ABC`, `ABORT` |
| `mock\_justified` | analyze_mocks.py:144 | MockAnalyzer._is_mock_decor... | `ABC`, `ABORT` |
| `mock\_only` | add_test_markers.py:52 | TestMarkerAdder.get_markers... | `ABC`, `ABORT` |
| `mock\_patch` | analyze_mocks.py:37 | MockAnalyzer.__init__ | `ABC`, `ABORT` |
| `mock\_patterns` | categorize_tests.py:41 | TestCategorizer._initialize... | `ABC`, `ABORT` |
| `mock\_redis\_client` | fix_e2e_tests_comprehensive.py:56 | E2ETestFixer._get_common_fi... | `ABC`, `ABORT` |
| `mock\_reductions` | real_test_linter.py:215 | RealTestLinter.generate_fix... | `ABC`, `ABORT` |
| `mock\_refresh\_token` | test_oauth_flows_sync.py:157 | test_oauth_token_exchange_m... | `ABC`, `ABORT` |
| `mock\_usage\_ratio` | validate_agent_tests.py:301 | AgentTestValidator.export_j... | `ABC`, `ABORT` |
| `mock\_user` | test_client.py:117 | AuthTestClient.validate_tok... | `ABC`, `ABORT` |
| `mock\_websocket` | fix_e2e_tests_comprehensive.py:64 | E2ETestFixer._get_common_fi... | `ABC`, `ABORT` |
| `mocks\_with\_justification` | analyze_mocks.py:220 | MockAnalyzer.generate_report | `ABC`, `ABORT` |
| `mocks\_without\_justification` | analyze_mocks.py:219 | MockAnalyzer.generate_report | `ABC`, `ABORT` |
| `MockUser` | test_helpers.py:114 | AuthTestUtils.authenticate_... | `ABC`, `ABORT` |
| `mode` | import_management.py:313 | main | `ABC`, `ABORT` |
| `model` | agent_tracking_helper.py:127 | AgentTrackingHelper._create... | `ABC`, `ABORT` |
| `model\_inference\_time` | seed_staging_data.py:283 | StagingDataSeeder._get_metr... | `ABC`, `ABORT` |
| `model\_selection` | setup_assistant.py:30 | _get_assistant_capabilities | `ABC`, `ABORT` |
| `models` | fix_schema_imports.py:34 | SchemaImportFixer.move_sche... | `ABC`, `ABORT` |
| `MODERATE` | generate_wip_report.py:247 | WIPReportGenerator._generat... | `ABC`, `ABORT` |
| `moderate` | identify_violations.py:98 | module | `ABC`, `ABORT` |
| `modified\_files` | fix_all_import_issues.py:206 | ComprehensiveImportFixer.fi... | `ABC`, `ABORT` |
| `module` | check_imports.py:154 | ImportAnalyzer._check_import | `ABC`, `ABORT` |
| `module\_count` | boundary_enforcer_report_generator.py:124 | ConsoleReportPrinter._print... | `ABC`, `ABORT` |
| `module\_count\_boundary` | boundary_enforcer_system_checks.py:159 | ViolationFactory.create_mod... | `ABC`, `ABORT` |
| `MODULE\_COUNT\_LIMIT` | boundary_enforcer_system_checks.py:160 | ViolationFactory.create_mod... | `ABC`, `ABORT` |
| `module\_not\_found` | analyze_failures.py:144 | TestFailureAnalyzer._determ... | `ABC`, `ABORT` |
| `module\_path` | check_schema_imports.py:391 | SchemaImportAnalyzer.export... | `ABC`, `ABORT` |
| `ModuleNotFoundError` | comprehensive_test_fixer.py:68 | TestFailureAnalyzer.analyze... | `ABC`, `ABORT` |
| `MONITOR` | boundary_enforcer_report_generator.py:175 | ConsoleReportPrinter._deter... | `ABC`, `ABORT` |
| `monitor` | audit_permissions.py:93 | main | `ABC`, `ABORT` |
| `MONITORING` | launcher.py:735 | DevLauncher._start_health_m... | `ABC`, `ABORT` |
| `monitoring` | cleanup_staging_environments.py:142 | StagingEnvironmentCleaner.g... | `ABC`, `ABORT` |
| `monitoring\_active` | crash_recovery.py:223 | CrashRecoveryManager.get_mo... | `ABC`, `ABORT` |
| `monitoring\_systems` | config_manager.py:57 | ConfigurationManager._get_i... | `ABC`, `ABORT` |
| `MonitoringConfig` | crash_recovery_models.py:131 | module | `ABC`, `ABORT` |
| `monkeypatch` | categorize_tests.py:69 | TestCategorizer._get_mock_p... | `ABC`, `ABORT` |
| `monokai` | workflow_introspection.py:389 | main | `ABC`, `ABORT` |
| `monolithic` | update_spec_timestamps.py:31 | module | `ABC`, `ABORT` |
| `monthly` | seed_staging_data.py:232 | StagingDataSeeder._generate... | `ABC`, `ABORT` |
| `monthly\_budget` | manage_workflows.py:138 | WorkflowManager.set_cost_bu... | `ABC`, `ABORT` |
| `monthly\_savings\_usd` | benchmark_optimization.py:287 | TestExecutionBenchmark._est... | `ABC`, `ABORT` |
| `most\_common\_violations` | check_schema_imports.py:293 | SchemaImportAnalyzer.analyz... | `ABC`, `ABORT` |
| `mostly\_compliant` | team_updates_compliance_analyzer.py:148 | ComplianceAnalyzer._determi... | `ABC`, `ABORT` |
| `MOSTLY\_ENABLED` | metadata_enabler.py:136 | MetadataTrackingEnabler._ca... | `ABC`, `ABORT` |
| `ms` | environment_validator.py:498 | main | `ABC`, `ABORT` |
| `multi\_service\_coverage` | business_value_test_index.py:601 | BusinessValueTestIndexer.ge... | `ABC`, `ABORT` |
| `multiple` | analyze_mocks.py:141 | MockAnalyzer._is_mock_decor... | `ABC`, `ABORT` |
| `MULTIPLE\_FILES` | emergency_boundary_actions.py:218 | EmergencyActionSystem._crea... | `ABC`, `ABORT` |
| `must` | ultra_thinking_analyzer.py:188 | UltraThinkingAnalyzer._extr... | `ABC`, `ABORT` |
| `mv` | standardize_l3_test_names.py:133 | rename_with_git | `ABC`, `ABORT` |
| `Name` | act_wrapper.py:135 | ACTWrapper._create_workflow... | `ABC`, `ABORT` |
| `name` | repository.py:48 | AuthUserRepository.create_o... | `ABC`, `ABORT` |
| `name\_error` | analyze_failures.py:33 | TestFailureAnalyzer | `ABC`, `ABORT` |
| `naming\_patterns` | generate_test_audit.py:67 | analyze_test_structure | `ABC`, `ABORT` |
| `needs\_attention` | team_updates_documentation_analyzer.py:203 | DocumentationAnalyzer._asse... | `ABC`, `ABORT` |
| `needs\_implementation` | fix_test_batch.py:311 | BatchTestProcessor._apply_t... | `ABC`, `ABORT` |
| `nested\_functions` | function_complexity_analyzer.py:60 | FunctionVisitor._analyze_fu... | `ABC`, `ABORT` |
| `net` | recovery_actions.py:241 | RecoveryActions._restart_de... | `ABC`, `ABORT` |
| `netra` | test_async_postgres.py:149 | main | `ABC`, `ABORT` |
| `netra\_backend` | align_test_imports.py:31 | TestImportAligner.__init__ | `ABC`, `ABORT` |
| `netra\_dev` | environment_validator_database.py:53 | DatabaseValidator._parse_po... | `ABC`, `ABORT` |
| `netra\_dev\_password` | service_config.py:95 | ServicesConfiguration | `ABC`, `ABORT` |
| `NETRA\_ENV` | test_launcher_config.py:185 | TestEnvironmentConfiguratio... | `ABC`, `ABORT` |
| `NETRA\_STARTUP\_MODE` | launcher.py:73 | DevLauncher._setup_startup_... | `ABC`, `ABORT` |
| `netstat` | port_manager.py:131 | PortManager._windows_port_c... | `ABC`, `ABORT` |
| `network\_bound` | parallel_executor.py:28 | TaskType | `ABC`, `ABORT` |
| `network\_gb` | cleanup_staging_environments.py:135 | StagingEnvironmentCleaner.g... | `ABC`, `ABORT` |
| `networking` | recovery_actions.py:269 | RecoveryActions.reset_netwo... | `ABC`, `ABORT` |
| `new` | test_session_management.py:161 | TestSessionRefresh.test_ref... | `ABC`, `ABORT` |
| `new\_files\_created` | auto_fix_test_sizes.py:620 | TestSizeFixer.fix_all_viola... | `ABC`, `ABORT` |
| `new\_learnings` | team_updates_documentation_analyzer.py:31 | DocumentationAnalyzer.analyze | `ABC`, `ABORT` |
| `new\_mock\_token` | test_client.py:105 | AuthTestClient.refresh_token | `ABC`, `ABORT` |
| `new\_password` | test_client.py:140 | AuthTestClient.change_password | `ABC`, `ABORT` |
| `next` | cleanup_test_processes.py:70 | find_test_processes | `ABC`, `ABORT` |
| `NEXT\_DISABLE\_FAST\_REFRESH` | dev_launcher_config.py:172 | setup_frontend_environment | `ABC`, `ABORT` |
| `next\_execution\_config` | test_backend_optimized.py:222 | OptimizedTestManager._compi... | `ABC`, `ABORT` |
| `NEXT\_PUBLIC\_API\_URL` | dev_launcher_config.py:157 | setup_frontend_environment | `ABC`, `ABORT` |
| `NEXT\_PUBLIC\_WS\_URL` | dev_launcher_config.py:158 | setup_frontend_environment | `ABC`, `ABORT` |
| `nginx` | recovery_actions.py:235 | RecoveryActions._get_common... | `ABC`, `ABORT` |
| `NO` | dev_launcher_monitoring.py:146 | print_configuration_summary | `ABC`, `ABORT` |
| `no\_automatic\_fix` | analyze_failures.py:186 | TestFailureAnalyzer._determ... | `ABC`, `ABORT` |
| `no\_browser` | config.py:210 | LauncherConfig.to_dict | `ABC`, `ABORT` |
| `no\_cache` | config.py:173 | LauncherConfig.from_args | `ABC`, `ABORT` |
| `no\_coverage` | types.py:44 | TestPattern | `ABC`, `ABORT` |
| `NO\_DUPLICATE\_TYPES` | boundary_enforcer_type_checks.py:156 | DuplicateTypeViolationFacto... | `ABC`, `ABORT` |
| `no\_emoji` | check_architecture_compliance.py:28 | _create_enforcer | `ABC`, `ABORT` |
| `no\_env\_files` | secret_cache_validation.py:138 | SecretValidationCache._get_... | `ABC`, `ABORT` |
| `no\_parallel` | config.py:189 | LauncherConfig.from_args | `ABC`, `ABORT` |
| `no\_reload` | config.py:142 | LauncherConfig.from_args | `ABC`, `ABORT` |
| `no\_secrets` | config.py:154 | LauncherConfig.from_args | `ABC`, `ABORT` |
| `no\_smart\_limits` | check_architecture_compliance.py:27 | _create_enforcer | `ABC`, `ABORT` |
| `no\_test\_limits` | check_architecture_compliance.py:31 | _create_enforcer | `ABC`, `ABORT` |
| `NO\_TEST\_STUBS` | boundary_enforcer_type_checks.py:124 | TestStubChecker._create_tes... | `ABC`, `ABORT` |
| `no\_turbopack` | config.py:188 | LauncherConfig.from_args | `ABC`, `ABORT` |
| `Node` | startup_diagnostics.py:99 | check_dependencies | `ABC`, `ABORT` |
| `node` | auto_decompose_functions.py:144 | FunctionDecomposer._identif... | `ABC`, `ABORT` |
| `NODE\_ENV` | deploy_to_gcp.py:109 | GCPDeployer.__init__ | `ABC`, `ABORT` |
| `node\_modules` | architecture_metrics.py:265 | ArchitectureMetrics._should... | `ABC`, `ABORT` |
| `nodejs` | environment_validator_dependencies.py:33 | DependencyValidator.validat... | `ABC`, `ABORT` |
| `nodejs\_dependencies` | environment_validator_dependencies.py:184 | DependencyValidator._valida... | `ABC`, `ABORT` |
| `non\_canonical\_import` | check_schema_imports.py:224 | SchemaImportAnalyzer._check... | `ABC`, `ABORT` |
| `non\_canonical\_schemas\_found` | check_schema_imports.py:295 | SchemaImportAnalyzer.analyz... | `ABC`, `ABORT` |
| `non\_compliant` | team_updates_compliance_analyzer.py:152 | ComplianceAnalyzer._determi... | `ABC`, `ABORT` |
| `non\_interactive` | config.py:187 | LauncherConfig.from_args | `ABC`, `ABORT` |
| `none` | test_auth_token_security.py:194 | TestJWTSignatureVerificatio... | `ABC`, `ABORT` |
| `NonExistent` | test_launcher.py:132 | TestProcessManager.test_ter... | `ABC`, `ABORT` |
| `nonexistent\_repo` | test_verify_workflow_status.py:120 | WorkflowStatusTester.test_r... | `ABC`, `ABORT` |
| `nonexistent\_workflow` | test_verify_workflow_status.py:129 | WorkflowStatusTester.test_w... | `ABC`, `ABORT` |
| `normal` | create_agent_fix_tasks.py:38 | create_agent_tasks | `ABC`, `ABORT` |
| `nosniff` | main.py:279 | add_service_headers | `ABC`, `ABORT` |
| `NOT\_CONFIGURED` | demo_real_llm_testing.py:124 | demo_real_llm_configuration | `ABC`, `ABORT` |
| `not\_fixable\_count` | analyze_failures.py:77 | TestFailureAnalyzer.analyze... | `ABC`, `ABORT` |
| `not\_fixable\_tests` | analyze_failures.py:82 | TestFailureAnalyzer.analyze... | `ABC`, `ABORT` |
| `not\_found` | cleanup_staging_environments.py:93 | StagingEnvironmentCleaner.c... | `ABC`, `ABORT` |
| `not\_initialized` | connection.py:238 | AuthDatabase.get_status | `ABC`, `ABORT` |
| `not\_ready` | main.py:325 | health_ready | `ABC`, `ABORT` |
| `notifications` | validate_workflow_config.py:26 | validate_config_structure | `ABC`, `ABORT` |
| `NotImplemented` | status_renderer.py:156 | StatusReportRenderer._build... | `ABC`, `ABORT` |
| `npm` | deduplicate_types.py:317 | TypeDeduplicator.run_tests | `ABC`, `ABORT` |
| `NPM\_` | local_secrets_manager.py:181 | LocalSecretsManager._get_gi... | `ABC`, `ABORT` |
| `NPM\_TOKEN` | workflow_validator.py:211 | SecretValidator._load_requi... | `ABC`, `ABORT` |
| `npm\_version` | environment_validator_dependencies.py:117 | DependencyValidator._valida... | `ABC`, `ABORT` |
| `npx` | test_frontend.py:336 | run_type_check | `ABC`, `ABORT` |
| `nt` | cleanup_workflow_runs.py:19 | run_gh_command | `ABC`, `ABORT` |
| `NullPool` | connection.py:242 | AuthDatabase.get_status | `ABC`, `ABORT` |
| `num\_statements` | coverage_reporter.py:61 | CoverageReporter.parse_cove... | `ABC`, `ABORT` |
| `number` | coverage_reporter.py:125 | CoverageReporter.parse_cove... | `ABC`, `ABORT` |
| `OAuth` | monitor_oauth_flow.py:119 | OAuthMonitor.monitor_logs | `ABC`, `ABORT` |
| `oauth` | test_env.py:217 | get_test_environment | `ABC`, `ABORT` |
| `OAUTH\_CALLBACK` | audit_factory.py:33 | AuditLogFactory | `ABC`, `ABORT` |
| `oauth\_callback` | audit_factory.py:33 | AuditLogFactory | `ABC`, `ABORT` |
| `oauth\_client` | test_mixins.py:154 | AuthTestMixin.setup_auth_mocks | `ABC`, `ABORT` |
| `oauth\_client\_id` | verify_auth_config.py:85 | verify_environment_config | `ABC`, `ABORT` |
| `oauth\_client\_secret` | verify_auth_config.py:92 | verify_environment_config | `ABC`, `ABORT` |
| `oauth\_config` | test_config_loading.py:101 | _check_oauth_configuration | `ABC`, `ABORT` |
| `OAUTH\_ERROR` | audit_factory.py:34 | AuditLogFactory | `ABC`, `ABORT` |
| `oauth\_error` | audit_factory.py:34 | AuditLogFactory | `ABC`, `ABORT` |
| `oauth\_mock\_token` | test_client.py:180 | AuthTestClient.oauth_callback | `ABC`, `ABORT` |
| `oauth\_provider` | audit_factory.py:175 | AuditLogFactory.create_oaut... | `ABC`, `ABORT` |
| `OAUTH\_REDIRECT\_URL` | test_env.py:206 | EnvironmentPresets.oauth_te... | `ABC`, `ABORT` |
| `oauth\_response` | test_mixins.py:230 | AuthTestMixin.simulate_oaut... | `ABC`, `ABORT` |
| `oauth\_state\_` | token_factory.py:233 | OAuthTokenFactory.create_oa... | `ABC`, `ABORT` |
| `OAuthConstants` | auth_constants_migration.py:104 | AuthConstantsMigrator.__init__ | `ABC`, `ABORT` |
| `OAuthTokenFactory` | __init__.py:18 | module | `ABC`, `ABORT` |
| `object` | analyze_mocks.py:141 | MockAnalyzer._is_mock_decor... | `ABC`, `ABORT` |
| `object\_type` | fix_test_batch.py:59 | TestAnalyzer.analyze_failure | `ABC`, `ABORT` |
| `observability` | business_value_test_index.py:102 | BusinessValueTestIndexer.__... | `ABC`, `ABORT` |
| `OBSOLETE` | update_spec_timestamps.py:23 | module | `ABC`, `ABORT` |
| `occurrences` | websocket_coherence_review.py:261 | _build_event_inventory | `ABC`, `ABORT` |
| `OFF` | manage_workflows.py:126 | WorkflowManager.set_feature | `ABC`, `ABORT` |
| `Off` | config.py:316 | LauncherConfig._print_servi... | `ABC`, `ABORT` |
| `OK` | check_e2e_imports.py:92 | E2EImportChecker.check_file... | `ABC`, `ABORT` |
| `ok` | test_websocket_validator_fix.py:40 | TestWebSocketValidatorFix.t... | `ABC`, `ABORT` |
| `old` | deduplicate_types.py:376 | TypeDeduplicator.generate_r... | `ABC`, `ABORT` |
| `old\_id` | auth_routes.py:317 | dev_login | `ABC`, `ABORT` |
| `ollama` | service_config.py:135 | ServicesConfiguration | `ABC`, `ABORT` |
| `omit` | coverage_config.py:57 | CoverageConfig.get_coverage... | `ABC`, `ABORT` |
| `ON` | manage_workflows.py:126 | WorkflowManager.set_feature | `ABC`, `ABORT` |
| `on` | debug_uvicorn_recursion.py:28 | module | `ABC`, `ABORT` |
| `onboard` | auto_fix_test_sizes.py:356 | TestFileSplitter._determine... | `ABC`, `ABORT` |
| `open` | cleanup_staging_environments.py:102 | StagingEnvironmentCleaner.c... | `ABC`, `ABORT` |
| `openai` | demo_real_llm_testing.py:122 | demo_real_llm_configuration | `ABC`, `ABORT` |
| `OPENAI\_` | local_secrets.py:93 | LocalSecretManager._is_rele... | `ABC`, `ABORT` |
| `OPENAI\_API\_KEY` | categorize_tests.py:48 | TestCategorizer._get_llm_pa... | `ABC`, `ABORT` |
| `openapi` | generate_openapi_spec.py:243 | validate_spec | `ABC`, `ABORT` |
| `OperationalError` | environment_validator.py:184 | EnvironmentValidator.test_p... | `ABC`, `ABORT` |
| `ops` | ultra_thinking_analyzer.py:141 | UltraThinkingAnalyzer._is_v... | `ABC`, `ABORT` |
| `optimization` | setup_assistant.py:19 | _get_assistant_tools | `ABC`, `ABORT` |
| `optimization\_ids` | seed_staging_data.py:359 | StagingDataSeeder.generate_... | `ABC`, `ABORT` |
| `optimization\_level` | seed_staging_data.py:231 | StagingDataSeeder._generate... | `ABC`, `ABORT` |
| `optimization\_recommendations` | test_backend_optimized.py:220 | OptimizedTestManager._compi... | `ABC`, `ABORT` |
| `optimization\_service` | fix_e2e_tests_comprehensive.py:54 | E2ETestFixer._get_common_fi... | `ABC`, `ABORT` |
| `optimization\_types` | seed_staging_data.py:208 | StagingDataSeeder._get_opti... | `ABC`, `ABORT` |
| `optimizations` | seed_staging_data.py:56 | StagingDataSeeder.__init__ | `ABC`, `ABORT` |
| `optimized\_cost` | seed_staging_data.py:246 | StagingDataSeeder._generate... | `ABC`, `ABORT` |
| `optimized\_execution` | benchmark_optimization.py:36 | TestExecutionBenchmark.__in... | `ABC`, `ABORT` |
| `optimized\_execution\_simulated` | benchmark_optimization.py:225 | TestExecutionBenchmark._sim... | `ABC`, `ABORT` |
| `optimized\_test\_cache` | test_backend_optimized.py:111 | OptimizedTestManager.__init__ | `ABC`, `ABORT` |
| `OPTIONS` | main.py:234 | DynamicCORSMiddleware.dispatch | `ABC`, `ABORT` |
| `Origin` | test_security.py:257 | TestCSRFProtection.test_csr... | `ABC`, `ABORT` |
| `origin` | main.py:231 | DynamicCORSMiddleware.dispatch | `ABC`, `ABORT` |
| `original\_cost` | seed_staging_data.py:245 | StagingDataSeeder._generate... | `ABC`, `ABORT` |
| `original\_file` | test_refactor_helper.py:590 | TestRefactorHelper.generate... | `ABC`, `ABORT` |
| `original\_functions` | auto_fix_test_sizes.py:693 | TestSizeFixer.fix_specific_... | `ABC`, `ABORT` |
| `original\_lines` | auto_fix_test_sizes.py:692 | TestSizeFixer.fix_specific_... | `ABC`, `ABORT` |
| `OS` | system_diagnostics.py:131 | SystemDiagnostics._check_wi... | `ABC`, `ABORT` |
| `os` | test_refactor_helper.py:133 | TestRefactorHelper._categor... | `ABC`, `ABORT` |
| `os\_environment` | env_file_loader.py:94 | EnvFileLoader.capture_exist... | `ABC`, `ABORT` |
| `other` | business_value_test_index.py:376 | BusinessValueTestIndexer._d... | `ABC`, `ABORT` |
| `outdated` | dependency_scanner.py:217 | calculate_summary_stats | `ABC`, `ABORT` |
| `output` | coverage_config.py:71 | CoverageConfig.get_coverage... | `ABC`, `ABORT` |
| `OutputHandler` | __init__.py:18 | module | `ABC`, `ABORT` |
| `outputs` | workflow_introspection.py:201 | WorkflowIntrospector.get_wo... | `ABC`, `ABORT` |
| `overall\_compliance` | architecture_dashboard_html.py:51 | DashboardHTMLComponents.gen... | `ABC`, `ABORT` |
| `overall\_grade` | coverage_reporter.py:205 | CoverageReporter._analyze_c... | `ABC`, `ABORT` |
| `overall\_similarity` | analyze_test_overlap.py:372 | TestOverlapAnalyzer._genera... | `ABC`, `ABORT` |
| `overall\_status` | demo_real_llm_testing.py:93 | demo_environment_validation | `ABC`, `ABORT` |
| `OVERRIDE\_TEST\_ENV` | test_backend.py:108 | _apply_environment_variables | `ABC`, `ABORT` |
| `package\_json` | utils.py:319 | check_project_structure | `ABC`, `ABORT` |
| `packages` | environment_validator_dependencies.py:34 | DependencyValidator.validat... | `ABC`, `ABORT` |
| `PANIC` | crash_detector.py:42 | CrashDetector._build_fatal_... | `ABC`, `ABORT` |
| `PARALLEL` | launcher.py:759 | DevLauncher._run_parallel_p... | `ABC`, `ABORT` |
| `parallel\_enabled` | service_startup.py:411 | ServiceStartupCoordinator.g... | `ABC`, `ABORT` |
| `parallel\_executor` | launcher.py:208 | DevLauncher._graceful_shutdown | `ABC`, `ABORT` |
| `parallel\_factor` | test_backend_optimized.py:59 | module | `ABC`, `ABORT` |
| `parallel\_startup` | launcher.py:312 | DevLauncher._setup_new_cach... | `ABC`, `ABORT` |
| `parameter` | architecture_scanner_helpers.py:203 | ScannerHelpers.create_missi... | `ABC`, `ABORT` |
| `parameters` | auto_decompose_functions.py:222 | FunctionDecomposer._suggest... | `ABC`, `ABORT` |
| `parametrize` | analyze_test_overlap.py:194 | TestOverlapAnalyzer._extrac... | `ABC`, `ABORT` |
| `params` | test_websocket_connection_issue.py:164 | TestWebSocketConnectionIssu... | `ABC`, `ABORT` |
| `params\_` | ssot_checker.py:155 | SSOTChecker._get_function_s... | `ABC`, `ABORT` |
| `parent\_task\_id` | metadata_header_generator.py:91 | MetadataHeaderGenerator.gen... | `ABC`, `ABORT` |
| `parse\_` | code_review_ai_detector.py:50 | CodeReviewAIDetector._check... | `ABC`, `ABORT` |
| `parse\_error` | enforce_limits.py:90 | FunctionLineChecker.check_file | `ABC`, `ABORT` |
| `partially\_compliant` | team_updates_compliance_analyzer.py:150 | ComplianceAnalyzer._determi... | `ABC`, `ABORT` |
| `PARTIALLY\_ENABLED` | metadata_enabler.py:138 | MetadataTrackingEnabler._ca... | `ABC`, `ABORT` |
| `PASS` | boundary_enforcer_report_generator.py:176 | ConsoleReportPrinter._deter... | `ABC`, `ABORT` |
| `pass\_rate` | team_updates_formatter.py:69 | HumanFormatter.format_execu... | `ABC`, `ABORT` |
| `PASSED` | comprehensive_test_fixer.py:311 | BatchProcessor.process_all_... | `ABC`, `ABORT` |
| `passed` | generate_performance_report.py:34 | add_summary_section | `ABC`, `ABORT` |
| `passed\_tests` | team_updates_formatter.py:130 | HumanFormatter.format_test_... | `ABC`, `ABORT` |
| `PASSING` | boundary_enforcer_report_generator.py:202 | PRCommentGenerator._determi... | `ABC`, `ABORT` |
| `passing` | validate_staging_health.py:148 | StagingPerformanceValidator... | `ABC`, `ABORT` |
| `passlib` | dependency_installer.py:102 | install_essential_packages_... | `ABC`, `ABORT` |
| `PASSWORD` | code_review_analysis.py:192 | CodeReviewAnalysis._check_h... | `ABC`, `ABORT` |
| `password` | audit_factory.py:75 | AuditLogFactory.create_logi... | `ABC`, `ABORT` |
| `PASSWORD\_CHANGE` | audit_factory.py:22 | AuditLogFactory | `ABC`, `ABORT` |
| `password\_change` | audit_factory.py:22 | AuditLogFactory | `ABC`, `ABORT` |
| `password\_hasher` | test_mixins.py:152 | AuthTestMixin.setup_auth_mocks | `ABC`, `ABORT` |
| `PASSWORD\_RESET` | audit_factory.py:23 | AuditLogFactory | `ABC`, `ABORT` |
| `password\_reset` | audit_factory.py:23 | AuditLogFactory | `ABC`, `ABORT` |
| `password\_reset\_completed` | auth_service.py:505 | AuthService.confirm_passwor... | `ABC`, `ABORT` |
| `password\_reset\_requested` | auth_service.py:442 | AuthService.request_passwor... | `ABC`, `ABORT` |
| `password\_reset\_tokens` | models.py:91 | PasswordResetToken | `ABC`, `ABORT` |
| `patch` | generate_fix.py:321 | FixValidator._apply_patch | `ABC`, `ABORT` |
| `patch\_` | analyze_mocks.py:152 | MockAnalyzer._get_decorator... | `ABC`, `ABORT` |
| `patch\_decorator` | analyze_mocks.py:36 | MockAnalyzer.__init__ | `ABC`, `ABORT` |
| `patch\_dict` | analyze_mocks.py:39 | MockAnalyzer.__init__ | `ABC`, `ABORT` |
| `patch\_file` | generate_fix.py:332 | FixValidator._apply_patch | `ABC`, `ABORT` |
| `patch\_multiple` | analyze_mocks.py:40 | MockAnalyzer.__init__ | `ABC`, `ABORT` |
| `patch\_object` | analyze_mocks.py:38 | MockAnalyzer.__init__ | `ABC`, `ABORT` |
| `path` | check_imports.py:343 | main | `ABC`, `ABORT` |
| `paths` | generate_openapi_spec.py:243 | validate_spec | `ABC`, `ABORT` |
| `pattern` | architecture_scanner_quality.py:58 | QualityScanner._find_stub_p... | `ABC`, `ABORT` |
| `patterns` | cleanup_generated_files.py:23 | module | `ABC`, `ABORT` |
| `Pending` | metadata_header_generator.py:106 | MetadataHeaderGenerator.gen... | `ABC`, `ABORT` |
| `pending` | fix_test_batch.py:265 | BatchTestProcessor._initial... | `ABC`, `ABORT` |
| `percent` | analyze_coverage.py:14 | module | `ABC`, `ABORT` |
| `percent\_covered` | coverage_reporter.py:64 | CoverageReporter.parse_cove... | `ABC`, `ABORT` |
| `percentile` | startup_profiler.py:238 | StartupProfiler._get_histor... | `ABC`, `ABORT` |
| `PERF` | launcher.py:880 | DevLauncher._handle_cleanup | `ABC`, `ABORT` |
| `perf` | auto_fix_test_violations.py:491 | TestFileSplitter._determine... | `ABC`, `ABORT` |
| `performance` | test_reviewer.py:216 | AutonomousTestReviewer._ide... | `ABC`, `ABORT` |
| `performance\_analysis` | test_backend_optimized.py:219 | OptimizedTestManager._compi... | `ABC`, `ABORT` |
| `performance\_comparison` | benchmark_optimization.py:302 | TestExecutionBenchmark._gen... | `ABC`, `ABORT` |
| `performance\_grade` | benchmark_optimization.py:184 | TestExecutionBenchmark._run... | `ABC`, `ABORT` |
| `performance\_issues` | generate_performance_report.py:48 | add_performance_issues | `ABC`, `ABORT` |
| `performance\_monitor` | fix_e2e_tests_comprehensive.py:73 | E2ETestFixer._get_common_fi... | `ABC`, `ABORT` |
| `performance\_optimization` | seed_staging_data.py:208 | StagingDataSeeder._get_opti... | `ABC`, `ABORT` |
| `PerformanceMetric` | fix_e2e_imports.py:98 | E2EImportFixer.__init__ | `ABC`, `ABORT` |
| `PerfService` | test_launcher_health.py:163 | TestAdvancedHealthMonitor._... | `ABC`, `ABORT` |
| `period\_days` | crash_reporter.py:230 | CrashReporter._build_crash_... | `ABC`, `ABORT` |
| `permanent` | cache_entry.py:153 | module | `ABC`, `ABORT` |
| `permission` | audit_factory.py:212 | AuditLogFactory.create_perm... | `ABC`, `ABORT` |
| `permission\_error` | analyze_failures.py:49 | TestFailureAnalyzer | `ABC`, `ABORT` |
| `PERMISSION\_GRANTED` | audit_factory.py:31 | AuditLogFactory | `ABC`, `ABORT` |
| `permission\_granted` | audit_factory.py:31 | AuditLogFactory | `ABC`, `ABORT` |
| `permission\_id` | permission_factory.py:57 | PermissionFactory.create_pe... | `ABC`, `ABORT` |
| `PERMISSION\_REVOKED` | audit_factory.py:32 | AuditLogFactory | `ABC`, `ABORT` |
| `permission\_revoked` | audit_factory.py:32 | AuditLogFactory | `ABC`, `ABORT` |
| `permission\_system` | fix_e2e_tests_comprehensive.py:53 | E2ETestFixer._get_common_fi... | `ABC`, `ABORT` |
| `PermissionError` | analyze_failures.py:49 | TestFailureAnalyzer | `ABC`, `ABORT` |
| `PermissionFactory` | __init__.py:19 | module | `ABC`, `ABORT` |
| `permissions` | auth_routes.py:233 | get_current_user | `ABC`, `ABORT` |
| `pg\_isready` | config_setup_core.py:52 | check_postgresql_status | `ABC`, `ABORT` |
| `phase\_` | startup_profiler.py:106 | StartupProfiler.end_phase_t... | `ABC`, `ABORT` |
| `phase\_results` | startup_optimizer.py:466 | StartupOptimizer.execute_ph... | `ABC`, `ABORT` |
| `phase\_times` | cache_manager.py:447 | CacheManager._create_startu... | `ABC`, `ABORT` |
| `phase\_timings` | startup_optimizer.py:589 | StartupOptimizer.get_phase_... | `ABC`, `ABORT` |
| `phases` | startup_optimizer.py:425 | StartupOptimizer.register_p... | `ABC`, `ABORT` |
| `php` | agent_tracking_helper.py:44 | AgentTrackingHelper | `ABC`, `ABORT` |
| `picture` | user_factory.py:87 | UserFactory.create_oauth_us... | `ABC`, `ABORT` |
| `pid` | cleanup_test_processes.py:61 | find_test_processes | `ABC`, `ABORT` |
| `ping` | test_staging_env.py:85 | StagingTester.test_websocke... | `ABC`, `ABORT` |
| `pip` | dependency_installer.py:55 | get_venv_paths | `ABC`, `ABORT` |
| `PLACEHOLDER` | secret_validator.py:74 | SecretValidator._is_invalid... | `ABC`, `ABORT` |
| `placeholder` | environment_validator.py:294 | EnvironmentValidator._valid... | `ABC`, `ABORT` |
| `plain` | build_staging.py:62 | StagingBuilder.build_backend | `ABC`, `ABORT` |
| `plan\_tier` | seed_staging_data.py:122 | StagingDataSeeder._build_ad... | `ABC`, `ABORT` |
| `platform` | startup_environment.py:45 | StartupEnvironment._record_... | `ABC`, `ABORT` |
| `pong` | test_websocket_dev_mode.py:207 | WebSocketDevModeTest.test_w... | `ABC`, `ABORT` |
| `pool` | generate_startup_integration_tests.py:312 | generate_test_file | `ABC`, `ABORT` |
| `pool\_pre\_ping` | connection.py:78 | AuthDatabase.initialize | `ABC`, `ABORT` |
| `pool\_recycle` | connection.py:77 | AuthDatabase.initialize | `ABC`, `ABORT` |
| `pool\_reset\_on\_return` | connection.py:79 | AuthDatabase.initialize | `ABC`, `ABORT` |
| `pool\_size` | connection.py:74 | AuthDatabase.initialize | `ABC`, `ABORT` |
| `pool\_timeout` | connection.py:76 | AuthDatabase.initialize | `ABC`, `ABORT` |
| `pool\_type` | connection.py:242 | AuthDatabase.get_status | `ABC`, `ABORT` |
| `poolclass` | connection.py:67 | AuthDatabase.initialize | `ABC`, `ABORT` |
| `poor` | coverage_reporter.py:201 | CoverageReporter._analyze_c... | `ABC`, `ABORT` |
| `PORT` | main.py:79 | lifespan | `ABC`, `ABORT` |
| `port` | environment_validator.py:230 | EnvironmentValidator.test_c... | `ABC`, `ABORT` |
| `port\_` | environment_validator.py:337 | EnvironmentValidator.check_... | `ABC`, `ABORT` |
| `port\_availability` | startup_optimizer.py:608 | create_validate_phase_steps | `ABC`, `ABORT` |
| `port\_check` | startup_optimizer.py:608 | create_validate_phase_steps | `ABC`, `ABORT` |
| `ports` | environment_validator_ports.py:23 | PortValidator.validate_requ... | `ABC`, `ABORT` |
| `ports\_verified` | health_monitor.py:426 | HealthMonitor.get_grace_per... | `ABC`, `ABORT` |
| `POST` | test_security.py:272 | TestCSRFProtection.test_met... | `ABC`, `ABORT` |
| `post\_commit\_hook` | git_hooks_manager.py:98 | GitHooksManager.get_status | `ABC`, `ABORT` |
| `postgres` | test_env.py:216 | get_test_environment | `ABC`, `ABORT` |
| `POSTGRES\_` | config_validator.py:282 | _extract_env_overrides | `ABC`, `ABORT` |
| `postgres\_connection` | environment_validator.py:153 | EnvironmentValidator.test_p... | `ABC`, `ABORT` |
| `postgres\_core` | comprehensive_import_scanner.py:157 | ComprehensiveImportScanner.... | `ABC`, `ABORT` |
| `POSTGRES\_HOST` | test_config.py:104 | PostgresTestConfig.__init__ | `ABC`, `ABORT` |
| `POSTGRES\_PASSWORD` | test_config.py:107 | PostgresTestConfig.__init__ | `ABC`, `ABORT` |
| `POSTGRES\_PORT` | test_config.py:105 | PostgresTestConfig.__init__ | `ABC`, `ABORT` |
| `POSTGRES\_URL` | migration_runner.py:98 | MigrationRunner._get_databa... | `ABC`, `ABORT` |
| `POSTGRES\_USER` | test_config.py:106 | PostgresTestConfig.__init__ | `ABC`, `ABORT` |
| `PostgresContainer` | fix_testcontainers_imports.py:55 | fix_testcontainers_imports | `ABC`, `ABORT` |
| `PostgreSQL` | environment_validator.py:322 | EnvironmentValidator.check_... | `ABC`, `ABORT` |
| `postgresql` | dependency_scanner.py:157 | scan_system_dependencies | `ABC`, `ABORT` |
| `PR\_NUMBER` | auth_routes.py:88 | get_auth_config | `ABC`, `ABORT` |
| `pr\_number` | cleanup_staging_environments.py:66 | StagingEnvironmentCleaner.g... | `ABC`, `ABORT` |
| `pr\_review` | workflow_presets.py:34 | WorkflowPresets.get_minimal... | `ABC`, `ABORT` |
| `pre\_clean\_slate\_` | clean_slate_executor.py:24 | CleanSlateExecutor.__init__ | `ABC`, `ABORT` |
| `pre\_commit\_hook` | git_hooks_manager.py:97 | GitHooksManager.get_status | `ABC`, `ABORT` |
| `pre\_existing` | staging_error_monitor.py:74 | ErrorAnalyzer.categorize_er... | `ABC`, `ABORT` |
| `precommit` | unified_import_manager.py:575 | run_precommit_check | `ABC`, `ABORT` |
| `precommit\_checks\_enabled` | manage_precommit.py:21 | load_config | `ABC`, `ABORT` |
| `preexec\_fn` | utils.py:389 | create_subprocess | `ABC`, `ABORT` |
| `PREPARE` | startup_optimizer.py:49 | StartupPhase | `ABC`, `ABORT` |
| `prepare` | auto_fix_test_violations.py:640 | FunctionRefactor._extract_s... | `ABC`, `ABORT` |
| `preset` | manage_workflows.py:195 | _setup_utility_parsers | `ABC`, `ABORT` |
| `prevention` | team_updates_documentation_analyzer.py:165 | DocumentationAnalyzer._extr... | `ABC`, `ABORT` |
| `previous` | team_updates_test_analyzer.py:69 | TestReportAnalyzer.calculat... | `ABC`, `ABORT` |
| `previous\_version` | metadata_header_generator.py:126 | MetadataHeaderGenerator.gen... | `ABC`, `ABORT` |
| `print` | ultra_thinking_analyzer.py:113 | UltraThinkingAnalyzer._has_... | `ABC`, `ABORT` |
| `print\_validation\_summary` | test_launcher.py:277 | TestDevLauncher.test_check_... | `ABC`, `ABORT` |
| `priority` | create_agent_fix_tasks.py:38 | create_agent_tasks | `ABC`, `ABORT` |
| `priority\_failure\_count` | test_failure_scanner.py:200 | _finalize_scan_results | `ABC`, `ABORT` |
| `priority\_failures` | comprehensive_test_fixer.py:358 | BatchProcessor._get_failing... | `ABC`, `ABORT` |
| `priority\_order` | team_updates_orchestrator.py:56 | TeamUpdatesOrchestrator.pri... | `ABC`, `ABORT` |
| `private` | auto_split_files.py:249 | FileSplitter._group_functio... | `ABC`, `ABORT` |
| `pro` | seed_staging_data.py:322 | StagingDataSeeder._create_m... | `ABC`, `ABORT` |
| `problem` | team_updates_documentation_analyzer.py:163 | DocumentationAnalyzer._extr... | `ABC`, `ABORT` |
| `process` | ultra_thinking_analyzer.py:167 | UltraThinkingAnalyzer._iden... | `ABC`, `ABORT` |
| `process\_` | ssot_checker.py:171 | SSOTChecker._are_likely_dup... | `ABC`, `ABORT` |
| `process\_count` | system_diagnostics.py:301 | SystemDiagnostics.get_syste... | `ABC`, `ABORT` |
| `process\_info` | environment_validator_ports.py:103 | PortValidator._check_port_a... | `ABC`, `ABORT` |
| `process\_manager` | launcher.py:187 | DevLauncher._graceful_shutdown | `ABC`, `ABORT` |
| `process\_message` | fix_missing_functions.py:16 | module | `ABC`, `ABORT` |
| `process\_monitoring` | crash_recovery_models.py:24 | DetectionMethod | `ABC`, `ABORT` |
| `process\_verified` | health_monitor.py:425 | HealthMonitor.get_grace_per... | `ABC`, `ABORT` |
| `processed` | fix_test_batch.py:231 | BatchTestProcessor.process_... | `ABC`, `ABORT` |
| `processes` | process_manager.py:511 | ProcessManager.get_all_stats | `ABC`, `ABORT` |
| `Processing` | create_enforcement_tools.py:55 | ProgressTracker.__init__ | `ABC`, `ABORT` |
| `processing` | auto_decompose_functions.py:171 | FunctionDecomposer._identif... | `ABC`, `ABORT` |
| `ProcessingResult` | validate_type_deduplication.py:82 | TypeDeduplicationValidator.... | `ABC`, `ABORT` |
| `ProcessPoolExecutor` | log_filter.py:124 | LogFilter._is_background_task | `ABC`, `ABORT` |
| `PRODUCTION` | migration_runner.py:218 | MigrationRunner._is_develop... | `ABC`, `ABORT` |
| `production` | config.py:19 | AuthConfig.get_environment | `ABC`, `ABORT` |
| `production\_files\_with\_violations` | relaxed_violation_counter.py:39 | RelaxedViolationCounter.get... | `ABC`, `ABORT` |
| `production\_security` | environment_validator.py:376 | EnvironmentValidator.valida... | `ABC`, `ABORT` |
| `production\_violations` | relaxed_violation_counter.py:36 | RelaxedViolationCounter.get... | `ABC`, `ABORT` |
| `productivity\_classification` | benchmark_optimization.py:251 | TestExecutionBenchmark._com... | `ABC`, `ABORT` |
| `productivity\_gain` | benchmark_optimization.py:182 | TestExecutionBenchmark._run... | `ABC`, `ABORT` |
| `professional` | seed_staging_data.py:133 | StagingDataSeeder._build_ma... | `ABC`, `ABORT` |
| `profile` | test_auth_oauth_google.py:313 | TestGoogleOAuthFlow.test_go... | `ABC`, `ABORT` |
| `profile\_` | startup_profiler.py:261 | StartupProfiler.save_profile | `ABC`, `ABORT` |
| `project` | deploy_to_gcp.py:130 | GCPDeployer.check_gcloud | `ABC`, `ABORT` |
| `project\_id` | config.py:185 | LauncherConfig.from_args | `ABC`, `ABORT` |
| `project\_root` | metadata_enabler.py:80 | MetadataTrackingEnabler.get... | `ABC`, `ABORT` |
| `prompt\_hash` | agent_tracking_helper.py:352 | AgentTrackingHelper.create_... | `ABC`, `ABORT` |
| `prompt\_summary` | agent_tracking_helper.py:131 | AgentTrackingHelper._create... | `ABC`, `ABORT` |
| `prompt\_user` | config_validator.py:229 | ConfigDecisionEngine.get_fa... | `ABC`, `ABORT` |
| `property\_mock` | analyze_mocks.py:44 | MockAnalyzer.__init__ | `ABC`, `ABORT` |
| `proposed\_files` | test_size_validator.py:401 | TestSizeValidator.auto_spli... | `ABC`, `ABORT` |
| `Proprietary` | generate_openapi_spec.py:70 | _add_contact_info | `ABC`, `ABORT` |
| `Props` | validate_type_deduplication.py:166 | TypeDeduplicationValidator.... | `ABC`, `ABORT` |
| `Protocol` | remove_test_stubs.py:211 | TestStubDetector._scan_empt... | `ABC`, `ABORT` |
| `protocol` | type_checker.py:155 | TypeChecker._filter_backend... | `ABC`, `ABORT` |
| `provider` | repository.py:40 | AuthUserRepository.create_o... | `ABC`, `ABORT` |
| `provider\_data` | user_factory.py:84 | UserFactory.create_oauth_us... | `ABC`, `ABORT` |
| `provider\_user\_id` | user_factory.py:82 | UserFactory.create_oauth_us... | `ABC`, `ABORT` |
| `providers` | status_integration_analyzer.py:76 | IntegrationAnalyzer._check_... | `ABC`, `ABORT` |
| `ps` | reset_clickhouse_final.py:18 | _check_docker_container | `ABC`, `ABORT` |
| `psql` | dependency_scanner.py:157 | scan_system_dependencies | `ABC`, `ABORT` |
| `public` | audit_permissions.py:44 | analyze_route_file | `ABC`, `ABORT` |
| `purpose` | auto_decompose_functions.py:220 | FunctionDecomposer._suggest... | `ABC`, `ABORT` |
| `push` | deploy_to_gcp.py:386 | GCPDeployer.build_image_local | `ABC`, `ABORT` |
| `pydantic` | check_schema_imports.py:166 | SchemaImportAnalyzer._is_sc... | `ABC`, `ABORT` |
| `pyramid\_score` | generate_wip_report.py:147 | WIPReportGenerator.calculat... | `ABC`, `ABORT` |
| `pytest` | connection.py:42 | AuthDatabase.initialize | `ABC`, `ABORT` |
| `pytest\_` | test_limits_checker.py:133 | TestLimitsChecker._is_test_... | `ABC`, `ABORT` |
| `pytest\_asyncio` | test_backend.py:153 | _check_all_python_packages | `ABC`, `ABORT` |
| `pytest\_cov` | test_backend.py:154 | _check_all_python_packages | `ABC`, `ABORT` |
| `pytest\_mock` | test_backend.py:154 | _check_all_python_packages | `ABC`, `ABORT` |
| `Python` | diagnostic_helpers.py:59 | create_dependency_error | `ABC`, `ABORT` |
| `python` | agent_tracking_helper.py:26 | AgentTrackingHelper | `ABC`, `ABORT` |
| `python\_files` | deduplicate_types.py:368 | TypeDeduplicator.generate_r... | `ABC`, `ABORT` |
| `python\_requirements` | environment_validator_dependencies.py:182 | DependencyValidator._valida... | `ABC`, `ABORT` |
| `python\_version` | startup_environment.py:44 | StartupEnvironment._record_... | `ABC`, `ABORT` |
| `PYTHONIOENCODING` | test_launcher_validation.py:18 | module | `ABC`, `ABORT` |
| `PYTHONPATH` | dev_launcher_config.py:144 | setup_environment_variables | `ABC`, `ABORT` |
| `PYTHONUNBUFFERED` | deploy_to_gcp.py:78 | GCPDeployer.__init__ | `ABC`, `ABORT` |
| `pyyaml` | setup_act.py:120 | install_dependencies | `ABC`, `ABORT` |
| `quality\_gates` | business_value_test_index.py:399 | BusinessValueTestIndexer._d... | `ABC`, `ABORT` |
| `quality\_metrics` | business_value_test_index.py:598 | BusinessValueTestIndexer.ge... | `ABC`, `ABORT` |
| `quality\_optimization` | setup_assistant.py:29 | _get_assistant_capabilities | `ABC`, `ABORT` |
| `quality\_scores` | real_service_test_metrics.py:25 | RealServiceTestMetrics.__in... | `ABC`, `ABORT` |
| `quality\_summary` | real_service_test_metrics.py:92 | RealServiceTestMetrics.fina... | `ABC`, `ABORT` |
| `QualityTrend` | fix_all_import_issues.py:68 | ComprehensiveImportFixer._b... | `ABC`, `ABORT` |
| `query` | code_review_analysis.py:164 | CodeReviewAnalysis._check_n... | `ABC`, `ABORT` |
| `queue\_depth` | seed_staging_data.py:285 | StagingDataSeeder._get_metr... | `ABC`, `ABORT` |
| `queued` | force_cancel_workflow.py:67 | _display_and_find_stuck_runs | `ABC`, `ABORT` |
| `quick` | types.py:31 | ReviewMode | `ABC`, `ABORT` |
| `quick\_test` | test_example_message_flow.py:406 | run_quick_validation | `ABC`, `ABORT` |
| `quick\_user` | test_example_message_flow.py:414 | run_quick_validation | `ABC`, `ABORT` |
| `rate\_limit\_exceeded` | test_auth_oauth_errors.py:188 | TestOAuthErrorHandling.test... | `ABC`, `ABORT` |
| `RATE\_LIMITING\_ENABLED` | test_env.py:58 | TestEnvironment | `ABC`, `ABORT` |
| `rb` | cache_entry.py:105 | ContentHasher.hash_file_con... | `ABC`, `ABORT` |
| `react` | environment_validator_dependencies.py:235 | DependencyValidator._check_... | `ABC`, `ABORT` |
| `read` | auth_routes.py:355 | dev_login | `ABC`, `ABORT` |
| `read\_backend\_info` | test_launcher.py:393 | TestIntegration.test_full_l... | `ABC`, `ABORT` |
| `read\_error` | enforce_limits.py:56 | FileLineChecker.check_file | `ABC`, `ABORT` |
| `readable` | environment_validator_core.py:114 | EnvironmentValidatorCore._v... | `ABC`, `ABORT` |
| `README\_API\_KEY` | generate_openapi_spec.py:332 | _handle_readme_sync | `ABC`, `ABORT` |
| `READY` | launcher.py:648 | DevLauncher._wait_for_backe... | `ABC`, `ABORT` |
| `ready` | main.py:317 | health_ready | `ABC`, `ABORT` |
| `ready\_confirmed` | health_monitor.py:419 | HealthMonitor.get_grace_per... | `ABC`, `ABORT` |
| `ready\_for\_launch` | environment_validator.py:396 | EnvironmentValidator.genera... | `ABC`, `ABORT` |
| `real\_` | test_discovery_report.py:46 | EnhancedTestDiscoveryReport... | `ABC`, `ABORT` |
| `real\_clickhouse` | categorize_tests.py:30 | TestCategorizer._initialize... | `ABC`, `ABORT` |
| `real\_database` | categorize_tests.py:30 | TestCategorizer._initialize... | `ABC`, `ABORT` |
| `real\_llm` | business_value_test_index.py:87 | BusinessValueTestIndexer.__... | `ABC`, `ABORT` |
| `real\_llm\_coverage` | business_value_test_index.py:599 | BusinessValueTestIndexer.ge... | `ABC`, `ABORT` |
| `real\_llm\_manager` | fix_e2e_tests_comprehensive.py:61 | E2ETestFixer._get_common_fi... | `ABC`, `ABORT` |
| `real\_redis` | categorize_tests.py:30 | TestCategorizer._initialize... | `ABC`, `ABORT` |
| `real\_services` | add_test_markers.py:50 | TestMarkerAdder.get_markers... | `ABC`, `ABORT` |
| `real\_system` | orchestrator.py:90 | ArchitectureEnforcer._calcu... | `ABC`, `ABORT` |
| `real\_tool\_dispatcher` | fix_e2e_tests_comprehensive.py:63 | E2ETestFixer._get_common_fi... | `ABC`, `ABORT` |
| `real\_websocket` | business_value_test_index.py:345 | BusinessValueTestIndexer._d... | `ABC`, `ABORT` |
| `real\_websocket\_manager` | fix_e2e_tests_comprehensive.py:62 | E2ETestFixer._get_common_fi... | `ABC`, `ABORT` |
| `reason` | main.py:325 | health_ready | `ABC`, `ABORT` |
| `reasons` | update_spec_timestamps.py:181 | add_timestamp_to_xml | `ABC`, `ABORT` |
| `recent` | test_session_cleanup.py:174 | TestSessionCleanupJob.test_... | `ABC`, `ABORT` |
| `recent\_runs` | team_updates_test_analyzer.py:73 | TestReportAnalyzer.calculat... | `ABC`, `ABORT` |
| `RECOMMENDATION` | fix_common_test_issues.py:73 | main | `ABC`, `ABORT` |
| `Recommendation` | architecture_dashboard_tables.py:22 | DashboardTableRenderers.ren... | `ABC`, `ABORT` |
| `recommendation` | architecture_dashboard_tables.py:36 | DashboardTableRenderers._ge... | `ABC`, `ABORT` |
| `RECOMMENDATIONS` | unified_import_manager.py:549 | UnifiedImportManager.print_... | `ABC`, `ABORT` |
| `recommendations` | coverage_reporter.py:215 | CoverageReporter._analyze_c... | `ABC`, `ABORT` |
| `recommended\_actions` | emergency_boundary_actions.py:338 | EmergencyActionSystem._gene... | `ABC`, `ABORT` |
| `reconfigure` | real_test_validator.py:343 | main | `ABC`, `ABORT` |
| `record\_count` | demo_real_llm_testing.py:85 | demo_environment_validation | `ABC`, `ABORT` |
| `recovery\_action` | health_monitor.py:170 | HealthMonitor.register_service | `ABC`, `ABORT` |
| `recovery\_attempt` | crash_recovery_models.py:33 | RecoveryStage | `ABC`, `ABORT` |
| `recovery\_instructions` | metadata_header_generator.py:129 | MetadataHeaderGenerator.gen... | `ABC`, `ABORT` |
| `RecoveryAttempt` | crash_recovery_models.py:128 | module | `ABC`, `ABORT` |
| `RecoveryStage` | crash_recovery_models.py:124 | module | `ABC`, `ABORT` |
| `recycle` | unicode_utils.py:93 | module | `ABC`, `ABORT` |
| `red` | boundary_enforcer_report_generator.py:197 | PRCommentGenerator._determi... | `ABC`, `ABORT` |
| `redirect\_uri` | auth_routes.py:423 | oauth_callback | `ABC`, `ABORT` |
| `redirect\_uris` | verify_auth_config.py:55 | verify_environment_config | `ABC`, `ABORT` |
| `Redis` | categorize_tests.py:250 | TestCategorizer._extract_se... | `ABC`, `ABORT` |
| `redis` | auto_fix_test_sizes.py:352 | TestFileSplitter._determine... | `ABC`, `ABORT` |
| `REDIS\_` | config_validator.py:282 | _extract_env_overrides | `ABC`, `ABORT` |
| `redis\_client` | test_session_cleanup.py:231 | TestSessionCleanupJob.test_... | `ABC`, `ABORT` |
| `redis\_connection` | environment_validator.py:250 | EnvironmentValidator.test_r... | `ABC`, `ABORT` |
| `redis\_connectivity` | environment_validator.py:410 | EnvironmentValidator.genera... | `ABC`, `ABORT` |
| `REDIS\_DB` | test_env.py:35 | TestEnvironment | `ABC`, `ABORT` |
| `REDIS\_DISABLED` | config.py:116 | AuthConfig.is_redis_disabled | `ABC`, `ABORT` |
| `REDIS\_HOST` | test_env.py:33 | TestEnvironment | `ABC`, `ABORT` |
| `REDIS\_MODE` | service_config.py:72 | ServicesConfiguration | `ABC`, `ABORT` |
| `REDIS\_PASSWORD` | dev_launcher_secrets.py:113 | EnhancedSecretLoader._get_s... | `ABC`, `ABORT` |
| `REDIS\_PORT` | test_env.py:34 | TestEnvironment | `ABC`, `ABORT` |
| `REDIS\_URL` | config.py:104 | AuthConfig.get_redis_url | `ABC`, `ABORT` |
| `redis\_version` | environment_validator.py:267 | EnvironmentValidator.test_r... | `ABC`, `ABORT` |
| `RedisContainer` | fix_testcontainers_imports.py:48 | fix_testcontainers_imports | `ABC`, `ABORT` |
| `RedisTestMixin` | __init__.py:17 | module | `ABC`, `ABORT` |
| `refactors` | team_updates_git_analyzer.py:56 | GitAnalyzer.summarize_commits | `ABC`, `ABORT` |
| `Referer` | test_security.py:258 | TestCSRFProtection.test_csr... | `ABC`, `ABORT` |
| `refresh` | jwt_handler.py:58 | JWTHandler.create_refresh_t... | `ABC`, `ABORT` |
| `refresh\_token` | auth_routes.py:180 | refresh_tokens | `ABC`, `ABORT` |
| `refresh\_token\_` | session_factory.py:110 | SessionFactory.create_sessi... | `ABC`, `ABORT` |
| `REFRESH\_TOKEN\_EXPIRE\_DAYS` | test_env.py:25 | TestEnvironment | `ABC`, `ABORT` |
| `refresh\_token\_hash` | session_factory.py:113 | SessionFactory.create_sessi... | `ABC`, `ABORT` |
| `refreshed` | test_session_management.py:152 | TestSessionRefresh.test_ref... | `ABC`, `ABORT` |
| `region` | cleanup_staging_environments.py:71 | StagingEnvironmentCleaner.g... | `ABC`, `ABORT` |
| `registered\_at` | service_discovery.py:131 | ServiceDiscovery.register_s... | `ABC`, `ABORT` |
| `registered\_service\_origins` | health_monitor.py:601 | HealthMonitor.get_cross_ser... | `ABC`, `ABORT` |
| `related` | analyze_test_overlap.py:329 | TestOverlapAnalyzer._calcul... | `ABC`, `ABORT` |
| `related\_imports` | analyze_failures.py:147 | TestFailureAnalyzer._determ... | `ABC`, `ABORT` |
| `relative` | check_netra_backend_imports.py:52 | ImportAnalyzer.__init__ | `ABC`, `ABORT` |
| `relative\_import` | comprehensive_import_scanner.py:323 | ComprehensiveImportScanner.... | `ABC`, `ABORT` |
| `relative\_import\_issues` | check_imports.py:32 | ImportAnalyzer.analyze_file | `ABC`, `ABORT` |
| `relaxed\_counts` | generate_wip_report.py:60 | WIPReportGenerator.run_comp... | `ABC`, `ABORT` |
| `relocated\_module` | e2e_import_fixer_comprehensive.py:262 | E2EImportFixer._check_impor... | `ABC`, `ABORT` |
| `remaining\_issues` | fix_e2e_tests_comprehensive.py:330 | E2ETestFixer.fix_all_issues | `ABC`, `ABORT` |
| `remote` | cleanup_workflow_runs.py:217 | get_repo_from_git | `ABC`, `ABORT` |
| `remove` | comprehensive_test_fixer.py:88 | CodeGenerator.generate_func... | `ABC`, `ABORT` |
| `removed` | schema_sync.py:95 | print_changes_detected | `ABC`, `ABORT` |
| `replace` | test_generator.py:46 | TestGenerator.modernize_tes... | `ABC`, `ABORT` |
| `replacements` | deduplicate_types.py:371 | TypeDeduplicator.generate_r... | `ABC`, `ABORT` |
| `report` | coverage_config.py:60 | CoverageConfig.get_coverage... | `ABC`, `ABORT` |
| `report\_path` | import_management.py:98 | ImportManagementSystem.chec... | `ABC`, `ABORT` |
| `ReportGenerator` | __init__.py:21 | module | `ABC`, `ABORT` |
| `reporting` | setup_assistant.py:20 | _get_assistant_tools | `ABC`, `ABORT` |
| `reports` | architecture_dashboard.py:27 | ArchitectureDashboard.gener... | `ABC`, `ABORT` |
| `request` | check_schema_imports.py:160 | SchemaImportAnalyzer._is_sc... | `ABC`, `ABORT` |
| `request\_count` | seed_staging_data.py:207 | StagingDataSeeder._get_opti... | `ABC`, `ABORT` |
| `request\_type` | seed_staging_data.py:224 | StagingDataSeeder._generate... | `ABC`, `ABORT` |
| `RequestModel` | generate-json-schema.py:16 | main | `ABC`, `ABORT` |
| `require\_admin` | audit_permissions.py:34 | analyze_route_file | `ABC`, `ABORT` |
| `require\_permission` | audit_permissions.py:36 | analyze_route_file | `ABC`, `ABORT` |
| `required` | deploy_to_gcp.py:162 | GCPDeployer.run_pre_deploym... | `ABC`, `ABORT` |
| `required\_env\_vars` | environment_validator.py:88 | EnvironmentValidator._add_r... | `ABC`, `ABORT` |
| `requirement` | ultra_thinking_analyzer.py:188 | UltraThinkingAnalyzer._extr... | `ABC`, `ABORT` |
| `requirements` | utils.py:316 | check_project_structure | `ABC`, `ABORT` |
| `requires\_action` | emergency_boundary_actions.py:105 | EmergencyActionSystem._crea... | `ABC`, `ABORT` |
| `reset\_failed` | auth_service.py:456 | AuthService.request_passwor... | `ABC`, `ABORT` |
| `resilience` | fix_e2e_test_imports.py:115 | ImportFixer.scan_test_direc... | `ABC`, `ABORT` |
| `resolution\_rate` | crash_reporter.py:236 | CrashReporter._build_crash_... | `ABC`, `ABORT` |
| `resolved\_crashes` | crash_reporter.py:232 | CrashReporter._build_crash_... | `ABC`, `ABORT` |
| `resource` | permission_factory.py:58 | PermissionFactory.create_pe... | `ABC`, `ABORT` |
| `resource\_monitoring` | test_backend_optimized.py:173 | OptimizedTestManager._creat... | `ABC`, `ABORT` |
| `resource\_optimization` | seed_staging_data.py:208 | StagingDataSeeder._get_opti... | `ABC`, `ABORT` |
| `resources\_freed` | cleanup_staging_environments.py:32 | StagingEnvironmentCleaner._... | `ABC`, `ABORT` |
| `response` | test_auth_oauth_errors.py:163 | TestOAuthErrorHandling.test... | `ABC`, `ABORT` |
| `response\_data` | test_auth_oauth_google.py:171 | TestGoogleOAuthFlow.test_go... | `ABC`, `ABORT` |
| `response\_time` | validate_staging_health.py:144 | StagingPerformanceValidator... | `ABC`, `ABORT` |
| `response\_time\_ms` | environment_validator.py:423 | EnvironmentValidator.genera... | `ABC`, `ABORT` |
| `restart` | recovery_actions.py:241 | RecoveryActions._restart_de... | `ABC`, `ABORT` |
| `restart\_count` | dev_launcher_processes.py:161 | ProcessMonitor._log_crash | `ABC`, `ABORT` |
| `RestartService` | test_launcher_process.py:153 | TestAdvancedProcessManager.... | `ABC`, `ABORT` |
| `result` | test_websocket_connection_issue.py:60 | TestWebSocketConnectionIssu... | `ABC`, `ABORT` |
| `RESULTS` | test_staging_startup.py:262 | StagingStartupTester.run_al... | `ABC`, `ABORT` |
| `results` | fake_test_scanner.py:120 | FakeTestScanner.scan_directory | `ABC`, `ABORT` |
| `retry\_count` | database_connector.py:660 | DatabaseConnector.get_conne... | `ABC`, `ABORT` |
| `retrying` | database_connector.py:48 | ConnectionStatus | `ABC`, `ABORT` |
| `return\_type` | auto_decompose_functions.py:223 | FunctionDecomposer._suggest... | `ABC`, `ABORT` |
| `returncode` | simple_perf_runner.py:60 | _create_result_dict | `ABC`, `ABORT` |
| `revenue` | generate_startup_integration_tests.py:23 | module | `ABC`, `ABORT` |
| `review\_assertion` | fix_test_batch.py:68 | TestAnalyzer.analyze_failure | `ABC`, `ABORT` |
| `review\_required` | config_manager.py:27 | ConfigurationManager._get_r... | `ABC`, `ABORT` |
| `review\_tracking` | metadata_header_generator.py:105 | MetadataHeaderGenerator.gen... | `ABC`, `ABORT` |
| `ReviewConfig` | __init__.py:12 | module | `ABC`, `ABORT` |
| `ReviewData` | __init__.py:13 | module | `ABC`, `ABORT` |
| `reviewer` | metadata_header_generator.py:107 | MetadataHeaderGenerator.gen... | `ABC`, `ABORT` |
| `ReviewMode` | __init__.py:16 | module | `ABC`, `ABORT` |
| `rich` | setup_act.py:120 | install_dependencies | `ABC`, `ABORT` |
| `risk\_assessment` | metadata_header_generator.py:101 | MetadataHeaderGenerator.gen... | `ABC`, `ABORT` |
| `risk\_level` | environment_validator.py:360 | EnvironmentValidator.valida... | `ABC`, `ABORT` |
| `risk\_levels` | config_manager.py:67 | ConfigurationManager._get_s... | `ABC`, `ABORT` |
| `rm` | dependency_installer.py:165 | clean_node_modules | `ABC`, `ABORT` |
| `rmdir` | dependency_installer.py:163 | clean_node_modules | `ABC`, `ABORT` |
| `rocket` | service_config.py:364 | ServiceConfigWizard.run | `ABC`, `ABORT` |
| `role` | generate_fix.py:81 | AIFixGenerator._generate_cl... | `ABC`, `ABORT` |
| `role\_assignment` | audit_factory.py:214 | AuditLogFactory.create_perm... | `ABC`, `ABORT` |
| `roles` | seed_staging_data.py:86 | StagingDataSeeder.seed_users | `ABC`, `ABORT` |
| `rollback` | connection.py:79 | AuthDatabase.initialize | `ABC`, `ABORT` |
| `rollback\_actions` | startup_optimizer.py:436 | StartupOptimizer.register_r... | `ABC`, `ABORT` |
| `rollback\_command` | metadata_header_generator.py:127 | MetadataHeaderGenerator.gen... | `ABC`, `ABORT` |
| `rollback\_info` | metadata_header_generator.py:125 | MetadataHeaderGenerator.gen... | `ABC`, `ABORT` |
| `Root` | test_auth_integration.py:42 | AuthServiceTester.test_auth... | `ABC`, `ABORT` |
| `root` | analyze_test_overlap.py:114 | TestOverlapAnalyzer._extrac... | `ABC`, `ABORT` |
| `root\_directory` | scan_string_literals.py:210 | StringLiteralIndexer.genera... | `ABC`, `ABORT` |
| `root\_path` | architecture_reporter.py:49 | ArchitectureReporter._get_r... | `ABC`, `ABORT` |
| `route` | auto_fix_test_sizes.py:344 | TestFileSplitter._determine... | `ABC`, `ABORT` |
| `routes` | fix_schema_imports.py:33 | SchemaImportFixer.move_sche... | `ABC`, `ABORT` |
| `rps` | validate_staging_health.py:183 | StagingPerformanceValidator... | `ABC`, `ABORT` |
| `ruby` | agent_tracking_helper.py:39 | AgentTrackingHelper | `ABC`, `ABORT` |
| `rule` | ultra_thinking_analyzer.py:188 | UltraThinkingAnalyzer._extr... | `ABC`, `ABORT` |
| `run` | coverage_config.py:54 | CoverageConfig.get_coverage... | `ABC`, `ABORT` |
| `run\_id` | process_results.py:185 | TestResultProcessor.generat... | `ABC`, `ABORT` |
| `run\_migrations` | startup_optimizer.py:616 | create_prepare_phase_steps | `ABC`, `ABORT` |
| `run\_number` | force_cancel_workflow.py:76 | _extract_run_info | `ABC`, `ABORT` |
| `runner` | process_results.py:187 | TestResultProcessor.generat... | `ABC`, `ABORT` |
| `runners` | validate_workflow_config.py:35 | validate_config_structure | `ABC`, `ABORT` |
| `running` | main.py:295 | root | `ABC`, `ABORT` |
| `runs` | workflow_introspection.py:348 | main | `ABC`, `ABORT` |
| `rust` | agent_tracking_helper.py:41 | AgentTrackingHelper | `ABC`, `ABORT` |
| `safe\_refresh` | test_security.py:160 | TestXSSPrevention.test_logi... | `ABC`, `ABORT` |
| `safe\_token` | test_security.py:159 | TestXSSPrevention.test_logi... | `ABC`, `ABORT` |
| `sample` | function_checker.py:75 | FunctionChecker._is_example... | `ABC`, `ABORT` |
| `sample\_` | function_complexity_linter.py:72 | FunctionComplexityLinter._i... | `ABC`, `ABORT` |
| `sample\_tables` | environment_validator.py:177 | EnvironmentValidator.test_p... | `ABC`, `ABORT` |
| `save` | ultra_thinking_analyzer.py:113 | UltraThinkingAnalyzer._has_... | `ABC`, `ABORT` |
| `savings\_percentage` | seed_staging_data.py:247 | StagingDataSeeder._generate... | `ABC`, `ABORT` |
| `scan\_duration` | comprehensive_import_scanner.py:84 | ComprehensiveScanReport.to_... | `ABC`, `ABORT` |
| `scan\_timestamp` | architecture_metrics.py:33 | ArchitectureMetrics.calcula... | `ABC`, `ABORT` |
| `scenarios` | generate_startup_integration_tests.py:24 | module | `ABC`, `ABORT` |
| `SCHEDULE` | emergency_boundary_actions.py:273 | EmergencyActionSystem._crea... | `ABC`, `ABORT` |
| `schedule` | workflow_validator.py:156 | WorkflowValidator._check_un... | `ABC`, `ABORT` |
| `SCHEDULE\_CLEANUP` | emergency_boundary_actions.py:270 | EmergencyActionSystem._crea... | `ABC`, `ABORT` |
| `scheduler` | auth_service.py:372 | AuthService._get_service_name | `ABC`, `ABORT` |
| `schema` | auto_fix_test_sizes.py:340 | TestFileSplitter._determine... | `ABC`, `ABORT` |
| `schema\_definitions` | check_schema_imports.py:387 | SchemaImportAnalyzer.export... | `ABC`, `ABORT` |
| `schemas` | check_schema_imports.py:113 | SchemaImportAnalyzer._build... | `ABC`, `ABORT` |
| `scheme` | generate_openapi_spec.py:99 | _get_security_schemes | `ABC`, `ABORT` |
| `scope` | token_factory.py:197 | OAuthTokenFactory.create_go... | `ABC`, `ABORT` |
| `score` | business_value_test_index.py:610 | BusinessValueTestIndexer.ge... | `ABC`, `ABORT` |
| `ScriptGeneratorBase` | __init__.py:19 | module | `ABC`, `ABORT` |
| `Scripts` | business_value_test_index.py:134 | BusinessValueTestIndexer.sc... | `ABC`, `ABORT` |
| `scripts` | test_reviewer.py:26 | AutonomousTestReviewer.__in... | `ABC`, `ABORT` |
| `search` | query_string_literals.py:135 | main | `ABC`, `ABORT` |
| `SECRET` | code_review_analysis.py:191 | CodeReviewAnalysis._check_h... | `ABC`, `ABORT` |
| `secret` | test_security.py:243 | TestCSRFProtection.test_sec... | `ABC`, `ABORT` |
| `secret\_` | secret_cache.py:138 | SecretCache._cache_individu... | `ABC`, `ABORT` |
| `secret\_entries` | secret_cache.py:214 | SecretCache.get_cache_stats | `ABC`, `ABORT` |
| `SECRET\_KEY` | environment_validator.py:113 | EnvironmentValidator._valid... | `ABC`, `ABORT` |
| `secret\_loading` | launcher.py:771 | DevLauncher._run_parallel_p... | `ABC`, `ABORT` |
| `SECRET\_MANAGER\_PROJECT` | validate_staging_config.py:322 | check_environment_variables | `ABC`, `ABORT` |
| `SECRET\_MANAGER\_PROJECT\_ID` | test_config_loading.py:35 | _print_environment_variables | `ABC`, `ABORT` |
| `secret\_strength` | environment_validator.py:138 | EnvironmentValidator._valid... | `ABC`, `ABORT` |
| `SECRETS` | launcher.py:473 | DevLauncher.load_secrets | `ABC`, `ABORT` |
| `secrets` | create_staging_secrets.py:42 | check_secret_exists | `ABC`, `ABORT` |
| `secrets\_hash` | secret_cache_validation.py:70 | SecretValidationCache.cache... | `ABC`, `ABORT` |
| `secrets\_in\_env\_file` | environment_validator.py:413 | EnvironmentValidator.genera... | `ABC`, `ABORT` |
| `secrets\_loading` | test_staging_startup.py:40 | StagingStartupTester.test_s... | `ABC`, `ABORT` |
| `secrets\_metadata` | secret_cache_validation.py:67 | SecretValidationCache.cache... | `ABC`, `ABORT` |
| `secrets\_validation` | cache_warmer.py:171 | CacheWarmer._warm_secrets_c... | `ABC`, `ABORT` |
| `secure` | environment_validator_database.py:87 | DatabaseValidator._parse_cl... | `ABC`, `ABORT` |
| `SECURE\_HEADERS\_ENABLED` | main.py:278 | add_service_headers | `ABC`, `ABORT` |
| `secure\_password` | test_limits_examples.py:11 | test_user_authentication_fl... | `ABC`, `ABORT` |
| `secure\_websocket` | test_websocket_dev_mode.py:127 | WebSocketDevModeTest.test_h... | `ABC`, `ABORT` |
| `secure\_ws` | test_websocket_validator_fix.py:71 | TestWebSocketValidatorFix.t... | `ABC`, `ABORT` |
| `Security` | dev_launcher_secrets.py:241 | EnhancedSecretLoader._get_e... | `ABC`, `ABORT` |
| `security` | test_reviewer.py:217 | AutonomousTestReviewer._ide... | `ABC`, `ABORT` |
| `security\_assessment` | environment_validator.py:412 | EnvironmentValidator.genera... | `ABC`, `ABORT` |
| `security\_checks` | generate_security_report.py:179 | _format_test_result_row | `ABC`, `ABORT` |
| `security\_issue\_count` | generate_security_report.py:72 | _build_security_metrics_table | `ABC`, `ABORT` |
| `security\_issues` | generate_security_report.py:141 | _build_test_issues_section | `ABC`, `ABORT` |
| `security\_level` | test_websocket_dev_mode.py:128 | WebSocketDevModeTest.test_h... | `ABC`, `ABORT` |
| `securitySchemes` | generate_openapi_spec.py:90 | _add_security_schemes | `ABC`, `ABORT` |
| `seed` | demo_real_llm_testing.py:146 | demo_seed_data_management | `ABC`, `ABORT` |
| `seed\_data` | demo_real_llm_testing.py:80 | demo_environment_validation | `ABC`, `ABORT` |
| `segment` | generate_startup_integration_tests.py:20 | module | `ABC`, `ABORT` |
| `select` | code_review_analysis.py:164 | CodeReviewAnalysis._check_n... | `ABC`, `ABORT` |
| `self` | analyze_test_overlap.py:200 | TestOverlapAnalyzer._extrac... | `ABC`, `ABORT` |
| `send` | ultra_thinking_analyzer.py:113 | UltraThinkingAnalyzer._has_... | `ABC`, `ABORT` |
| `sensitive` | test_session_management.py:341 | TestSessionSecurityAndHijac... | `ABC`, `ABORT` |
| `sequence` | seed_staging_data.py:196 | StagingDataSeeder.seed_thre... | `ABC`, `ABORT` |
| `sequence\_number` | metadata_header_generator.py:114 | MetadataHeaderGenerator.gen... | `ABC`, `ABORT` |
| `SERIALIZABLE` | test_settings.py:19 | DatabaseTestSettings | `ABC`, `ABORT` |
| `server\_error` | test_auth_oauth_errors.py:180 | TestOAuthErrorHandling.test... | `ABC`, `ABORT` |
| `server\_settings` | connection.py:165 | AuthDatabase._get_cloud_sql... | `ABC`, `ABORT` |
| `server\_startup` | test_websocket_dev_mode.py:39 | WebSocketDevModeTest.__init__ | `ABC`, `ABORT` |
| `ServerMessage` | validate_type_deduplication.py:76 | TypeDeduplicationValidator.... | `ABC`, `ABORT` |
| `servers` | generate_openapi_spec.py:78 | _add_servers | `ABC`, `ABORT` |
| `Service` | test_launcher_process.py:124 | TestAdvancedProcessManager.... | `ABC`, `ABORT` |
| `service` | jwt_handler.py:69 | JWTHandler.create_service_t... | `ABC`, `ABORT` |
| `service\_` | test_startup_comprehensive.py:458 | TestAsyncOperations.test_co... | `ABC`, `ABORT` |
| `service\_discovery\_active` | health_monitor.py:77 | HealthStatus.update_cross_s... | `ABC`, `ABORT` |
| `SERVICE\_DISCOVERY\_PATH` | auth_starter.py:156 | AuthStarter._create_auth_env | `ABC`, `ABORT` |
| `service\_id` | test_security.py:140 | TestSQLInjectionPrevention.... | `ABC`, `ABORT` |
| `service\_name` | cleanup_staging_environments.py:67 | StagingEnvironmentCleaner.g... | `ABC`, `ABORT` |
| `service\_path` | validate_service_independence.py:256 | main | `ABC`, `ABORT` |
| `service\_registry` | test_staging_startup.py:44 | StagingStartupTester.test_s... | `ABC`, `ABORT` |
| `service\_secret` | test_security.py:141 | TestSQLInjectionPrevention.... | `ABC`, `ABORT` |
| `SERVICE\_SECRET\_` | auth_service.py:363 | AuthService._validate_service | `ABC`, `ABORT` |
| `ServiceConfig` | crash_recovery_models.py:130 | module | `ABC`, `ABORT` |
| `SERVICES` | config.py:309 | LauncherConfig._print_servi... | `ABC`, `ABORT` |
| `services` | auto_fix_test_sizes.py:368 | TestFileSplitter._determine... | `ABC`, `ABORT` |
| `services\_affected` | crash_reporter.py:234 | CrashReporter._build_crash_... | `ABC`, `ABORT` |
| `services\_monitored` | crash_recovery.py:224 | CrashRecoveryManager.get_mo... | `ABC`, `ABORT` |
| `ServicesConfiguration` | service_config.py:321 | ServicesConfiguration.load_... | `ABC`, `ABORT` |
| `session` | auth_routes.py:234 | get_current_user | `ABC`, `ABORT` |
| `SESSION\_CREATED` | audit_factory.py:29 | AuditLogFactory | `ABC`, `ABORT` |
| `session\_created` | audit_factory.py:29 | AuditLogFactory | `ABC`, `ABORT` |
| `SESSION\_EXPIRE\_HOURS` | test_settings.py:180 | TestSettings.to_env_dict | `ABC`, `ABORT` |
| `SESSION\_EXPIRED` | audit_factory.py:30 | AuditLogFactory | `ABC`, `ABORT` |
| `session\_expired` | audit_factory.py:30 | AuditLogFactory | `ABC`, `ABORT` |
| `session\_id` | session_manager.py:181 | SessionManager.get_user_ses... | `ABC`, `ABORT` |
| `session\_limits\_enforced` | test_session_cleanup.py:280 | TestSessionMaintenanceSched... | `ABC`, `ABORT` |
| `session\_manager` | auth_routes.py:228 | get_current_user | `ABC`, `ABORT` |
| `session\_tracking` | metadata_header_generator.py:111 | MetadataHeaderGenerator.gen... | `ABC`, `ABORT` |
| `SESSION\_TTL\_HOURS` | config.py:110 | AuthConfig.get_session_ttl_... | `ABC`, `ABORT` |
| `session\_type` | audit_factory.py:157 | AuditLogFactory.create_sess... | `ABC`, `ABORT` |
| `SessionFactory` | __init__.py:15 | module | `ABC`, `ABORT` |
| `sessions` | test_client.py:219 | AuthTestClient.get_user_ses... | `ABC`, `ABORT` |
| `SET` | validate_jwt_consistency.py:155 | validate_jwt_secret_consist... | `ABC`, `ABORT` |
| `set` | deploy_to_gcp.py:141 | GCPDeployer.check_gcloud | `ABC`, `ABORT` |
| `set\_` | auto_split_files.py:254 | FileSplitter._group_functio... | `ABC`, `ABORT` |
| `setters` | auto_split_files.py:255 | FileSplitter._group_functio... | `ABC`, `ABORT` |
| `Settings` | generate-json-schema.py:22 | main | `ABC`, `ABORT` |
| `settings` | audit_permissions.py:93 | main | `ABC`, `ABORT` |
| `settings\_count` | environment_validator.py:231 | EnvironmentValidator.test_c... | `ABC`, `ABORT` |
| `setUp` | test_refactor_helper.py:212 | TestRefactorHelper._determi... | `ABC`, `ABORT` |
| `setup` | auto_fix_test_violations.py:640 | FunctionRefactor._extract_s... | `ABC`, `ABORT` |
| `setup\_coverage` | __init__.py:9 | module | `ABC`, `ABORT` |
| `setup\_method` | test_refactor_helper.py:212 | TestRefactorHelper._determi... | `ABC`, `ABORT` |
| `setup\_monitoring` | enhance_dev_launcher_boundaries.py:139 | enhance_launcher_main | `ABC`, `ABORT` |
| `setup\_signal\_handlers` | test_launcher_process.py:340 | TestResourceManagement._tes... | `ABC`, `ABORT` |
| `setup\_test\_path` | check_test_import_order.py:27 | check_import_order | `ABC`, `ABORT` |
| `severe` | identify_violations.py:97 | module | `ABC`, `ABORT` |
| `severities` | fake_test_scanner.py:167 | FakeTestScanner._get_critic... | `ABC`, `ABORT` |
| `Severity` | architecture_dashboard_tables.py:22 | DashboardTableRenderers.ren... | `ABC`, `ABORT` |
| `severity` | architecture_dashboard_tables.py:29 | DashboardTableRenderers._ge... | `ABC`, `ABORT` |
| `severity\_breakdown` | architecture_metrics.py:38 | ArchitectureMetrics.calcula... | `ABC`, `ABORT` |
| `sh` | setup_act.py:46 | install_act | `ABC`, `ABORT` |
| `SHA` | verify_workflow_status.py:251 | OutputFormatter.display_table | `ABC`, `ABORT` |
| `shard` | generate_report.py:80 | _format_shard_row | `ABC`, `ABORT` |
| `shards` | generate_report.py:69 | _format_shard_results | `ABC`, `ABORT` |
| `share` | generate_test_audit.py:28 | module | `ABC`, `ABORT` |
| `shared` | auth_starter.py:140 | AuthStarter._create_auth_env | `ABC`, `ABORT` |
| `shared\_utilities` | test_refactor_helper.py:334 | TestRefactorHelper._analyze... | `ABC`, `ABORT` |
| `short` | cache_entry.py:158 | module | `ABC`, `ABORT` |
| `should` | ultra_thinking_analyzer.py:188 | UltraThinkingAnalyzer._extr... | `ABC`, `ABORT` |
| `should\_monitor` | health_monitor.py:423 | HealthMonitor.get_grace_per... | `ABC`, `ABORT` |
| `show` | manage_workflows.py:197 | _setup_utility_parsers | `ABC`, `ABORT` |
| `show\_all` | check_architecture_compliance.py:25 | _create_enforcer | `ABC`, `ABORT` |
| `show\_contexts` | coverage_config.py:68 | CoverageConfig.get_coverage... | `ABC`, `ABORT` |
| `show\_missing` | coverage_config.py:61 | CoverageConfig.get_coverage... | `ABC`, `ABORT` |
| `show\_summary` | startup_optimizer.py:635 | create_verify_phase_steps | `ABC`, `ABORT` |
| `SHUTDOWN` | launcher.py:174 | DevLauncher._signal_handler | `ABC`, `ABORT` |
| `shutdown` | test_default_launcher.py:252 | TestGracefulShutdownImprove... | `ABC`, `ABORT` |
| `SIGHUP` | __main__.py:81 | setup_signal_handlers | `ABC`, `ABORT` |
| `Signals` | launcher.py:173 | DevLauncher._signal_handler | `ABC`, `ABORT` |
| `SignalService` | test_launcher_process.py:328 | TestResourceManagement.test... | `ABC`, `ABORT` |
| `signup` | auto_fix_test_sizes.py:356 | TestFileSplitter._determine... | `ABC`, `ABORT` |
| `silent` | config.py:172 | LauncherConfig.from_args | `ABC`, `ABORT` |
| `similar` | analyze_test_overlap.py:327 | TestOverlapAnalyzer._calcul... | `ABC`, `ABORT` |
| `similarity` | analyze_test_overlap.py:426 | TestOverlapAnalyzer._genera... | `ABC`, `ABORT` |
| `similarity\_type` | analyze_test_overlap.py:635 | TestOverlapAnalyzer._save_c... | `ABC`, `ABORT` |
| `simple` | auto_split_files.py:229 | FileSplitter._fallback_spli... | `ABC`, `ABORT` |
| `simple\_split` | auto_decompose_functions.py:351 | FunctionDecomposer._suggest... | `ABC`, `ABORT` |
| `simulated` | benchmark_optimization.py:226 | TestExecutionBenchmark._sim... | `ABC`, `ABORT` |
| `SIMULATING` | auto_fix_test_violations.py:338 | TestFileSplitter.split_larg... | `ABC`, `ABORT` |
| `single` | extract_violations.py:61 | extract_violations | `ABC`, `ABORT` |
| `size` | environment_validator_core.py:115 | EnvironmentValidatorCore._v... | `ABC`, `ABORT` |
| `size\_bytes` | demo_real_llm_testing.py:84 | demo_environment_validation | `ABC`, `ABORT` |
| `SKIP` | environment_validator.py:250 | EnvironmentValidator.test_r... | `ABC`, `ABORT` |
| `skip` | test_reviewer.py:166 | AutonomousTestReviewer._ass... | `ABC`, `ABORT` |
| `SKIP\_APP\_INIT` | simple_perf_runner.py:21 | _setup_environment | `ABC`, `ABORT` |
| `skip\_covered` | coverage_config.py:62 | CoverageConfig.get_coverage... | `ABC`, `ABORT` |
| `SKIP\_MIGRATIONS` | migration_runner.py:86 | MigrationRunner._should_ski... | `ABC`, `ABORT` |
| `skip\_on\_draft\_pr` | workflow_presets.py:78 | WorkflowPresets.get_cost_op... | `ABC`, `ABORT` |
| `SKIP\_STARTUP\_CHECKS` | generate_openapi_spec.py:29 | module | `ABC`, `ABORT` |
| `SKIP\_TESTS` | act_wrapper.py:168 | StagingDeployer._prepare_en... | `ABC`, `ABORT` |
| `Skipped` | split_large_files.py:256 | _handle_file_splitting | `ABC`, `ABORT` |
| `skipped` | generate_report.py:54 | _get_test_count_rows | `ABC`, `ABORT` |
| `skipped\_tests` | test_reviewer.py:167 | AutonomousTestReviewer._ass... | `ABC`, `ABORT` |
| `sla` | seed_staging_data.py:230 | StagingDataSeeder._generate... | `ABC`, `ABORT` |
| `sleep` | test_reviewer.py:164 | AutonomousTestReviewer._ass... | `ABC`, `ABORT` |
| `slow\_setup` | types.py:46 | TestPattern | `ABC`, `ABORT` |
| `slowest\_steps` | startup_optimizer.py:311 | StartupOptimizer.get_timing... | `ABC`, `ABORT` |
| `small` | ssot_checker.py:134 | SSOTChecker._get_function_s... | `ABC`, `ABORT` |
| `smart\_retry` | workflow_presets.py:28 | WorkflowPresets.get_minimal... | `ABC`, `ABORT` |
| `smoke` | benchmark_optimization.py:75 | TestExecutionBenchmark._dis... | `ABC`, `ABORT` |
| `socket` | validate_staging_config.py:123 | _parse_cloudsql_url | `ABC`, `ABORT` |
| `solution` | team_updates_documentation_analyzer.py:164 | DocumentationAnalyzer._extr... | `ABC`, `ABORT` |
| `sort` | coverage_config.py:63 | CoverageConfig.get_coverage... | `ABC`, `ABORT` |
| `source` | coverage_config.py:55 | CoverageConfig.get_coverage... | `ABC`, `ABORT` |
| `source\_code` | generate_fix.py:195 | AIFixGenerator._add_source_... | `ABC`, `ABORT` |
| `source\_file` | analyze_failures.py:147 | TestFailureAnalyzer._determ... | `ABC`, `ABORT` |
| `sparkles` | unicode_utils.py:94 | module | `ABC`, `ABORT` |
| `SPEC` | test_reviewer.py:24 | AutonomousTestReviewer.__in... | `ABC`, `ABORT` |
| `spec` | generate_openapi_spec.py:183 | upload_spec_to_readme | `ABC`, `ABORT` |
| `spec\_updates` | team_updates_documentation_analyzer.py:30 | DocumentationAnalyzer.analyze | `ABC`, `ABORT` |
| `specific\_issues` | unified_import_manager.py:372 | UnifiedImportManager._check... | `ABC`, `ABORT` |
| `specific\_run\_id` | test_verify_workflow_status.py:153 | WorkflowStatusTester.test_r... | `ABC`, `ABORT` |
| `specification` | split_learnings.py:63 | create_category_file | `ABC`, `ABORT` |
| `speedup\_achieved` | benchmark_optimization.py:304 | TestExecutionBenchmark._gen... | `ABC`, `ABORT` |
| `speedup\_factor` | benchmark_optimization.py:246 | TestExecutionBenchmark._com... | `ABC`, `ABORT` |
| `Split` | core.py:118 | ViolationBuilder.function_v... | `ABC`, `ABORT` |
| `split\_by\_` | test_refactor_helper.py:719 | main | `ABC`, `ABORT` |
| `split\_by\_category` | test_refactor_helper.py:443 | TestRefactorHelper._strateg... | `ABC`, `ABORT` |
| `split\_by\_class` | test_refactor_helper.py:483 | TestRefactorHelper._strateg... | `ABC`, `ABORT` |
| `split\_by\_feature` | test_refactor_helper.py:516 | TestRefactorHelper._strateg... | `ABC`, `ABORT` |
| `splitting\_suggestions` | test_size_validator.py:497 | TestSizeValidator._generate... | `ABC`, `ABORT` |
| `sql` | agent_tracking_helper.py:45 | AgentTrackingHelper | `ABC`, `ABORT` |
| `SQL\_ECHO` | connection.py:66 | AuthDatabase.initialize | `ABC`, `ABORT` |
| `sql\_injection` | test_security.py:48 | security_test_payloads | `ABC`, `ABORT` |
| `sql\_keyword` | scan_string_literals.py:86 | StringLiteralCategorizer | `ABC`, `ABORT` |
| `sqlalchemy` | config_setup_scripts.py:143 | test_python_imports | `ABC`, `ABORT` |
| `sqlite` | environment_validator.py:212 | EnvironmentValidator._is_su... | `ABC`, `ABORT` |
| `src` | comprehensive_import_scanner.py:632 | ComprehensiveImportScanner.... | `ABC`, `ABORT` |
| `ssot\_violation` | ssot_checker.py:69 | SSOTChecker._check_duplicat... | `ABC`, `ABORT` |
| `stage` | test_auth_oauth_errors.py:292 | TestOAuthErrorHandling.test... | `ABC`, `ABORT` |
| `staging` | config.py:19 | AuthConfig.get_environment | `ABC`, `ABORT` |
| `STAGING\_API\_URL` | test_staging.py:26 | setup_staging_env | `ABC`, `ABORT` |
| `STAGING\_AUTH\_URL` | test_staging.py:27 | setup_staging_env | `ABC`, `ABORT` |
| `STAGING\_BASE\_URL` | validate_staging_health.py:30 | StagingHealthValidator.__in... | `ABC`, `ABORT` |
| `staging\_config` | verify_staging_tests.py:20 | verify_test_files | `ABC`, `ABORT` |
| `STAGING\_DB\_PASSWORD` | validate_staging_config.py:56 | get_required_github_secrets | `ABC`, `ABORT` |
| `STAGING\_FRONTEND\_URL` | test_staging.py:28 | setup_staging_env | `ABC`, `ABORT` |
| `staging\_test\_pr\_` | validate_staging_config.py:243 | check_redis_connection | `ABC`, `ABORT` |
| `STAGING\_URL` | test_staging.py:25 | setup_staging_env | `ABC`, `ABORT` |
| `stale` | config_validator.py:33 | ConfigStatus | `ABC`, `ABORT` |
| `standalone` | test_refactor_helper.py:475 | TestRefactorHelper._strateg... | `ABC`, `ABORT` |
| `standard` | test_refactor_helper.py:114 | TestRefactorHelper._extract... | `ABC`, `ABORT` |
| `standard\_execution` | benchmark_optimization.py:35 | TestExecutionBenchmark.__in... | `ABC`, `ABORT` |
| `standard\_pytest` | benchmark_optimization.py:135 | TestExecutionBenchmark._run... | `ABC`, `ABORT` |
| `start` | auto_split_files.py:202 | FileSplitter._suggest_logic... | `ABC`, `ABORT` |
| `start\_auth` | startup_optimizer.py:624 | create_launch_phase_steps | `ABC`, `ABORT` |
| `start\_backend` | startup_optimizer.py:625 | create_launch_phase_steps | `ABC`, `ABORT` |
| `start\_frontend` | startup_optimizer.py:626 | create_launch_phase_steps | `ABC`, `ABORT` |
| `start\_line` | auto_decompose_functions.py:117 | FunctionDecomposer._identif... | `ABC`, `ABORT` |
| `start\_time` | real_service_test_metrics.py:18 | RealServiceTestMetrics.__in... | `ABC`, `ABORT` |
| `StartAgentMessage` | generate-json-schema.py:17 | main | `ABC`, `ABORT` |
| `StartAgentPayload` | generate-json-schema.py:18 | main | `ABC`, `ABORT` |
| `Started` | workflow_introspection.py:246 | OutputFormatter.display_run... | `ABC`, `ABORT` |
| `started` | log_buffer.py:239 | LogBuffer._is_important_mes... | `ABC`, `ABORT` |
| `started\_at` | auth_starter.py:247 | AuthStarter._write_auth_dis... | `ABC`, `ABORT` |
| `startedAt` | workflow_introspection.py:129 | WorkflowIntrospector.get_re... | `ABC`, `ABORT` |
| `starter` | seed_staging_data.py:146 | StagingDataSeeder._build_re... | `ABC`, `ABORT` |
| `starting` | health_monitor.py:35 | ServiceState | `ABC`, `ABORT` |
| `startup\_metrics` | cache_manager.py:262 | CacheManager.get_startup_me... | `ABC`, `ABORT` |
| `startup\_mode` | launcher.py:71 | DevLauncher._setup_startup_... | `ABC`, `ABORT` |
| `startup\_optimizer` | launcher.py:205 | DevLauncher._graceful_shutdown | `ABC`, `ABORT` |
| `startup\_time` | startup_performance.py:28 | PerformanceMetrics.to_dict | `ABC`, `ABORT` |
| `StartupCheckResult` | fast_import_checker.py:116 | fix_known_import_issues | `ABC`, `ABORT` |
| `StartupMode` | log_filter.py:338 | module | `ABC`, `ABORT` |
| `StartupProgressTracker` | log_filter.py:340 | module | `ABC`, `ABORT` |
| `State` | validate_type_deduplication.py:166 | TypeDeduplicationValidator.... | `ABC`, `ABORT` |
| `state` | test_auth_oauth_errors.py:121 | TestOAuthErrorHandling.test... | `ABC`, `ABORT` |
| `statements` | coverage_reporter.py:211 | CoverageReporter._analyze_c... | `ABC`, `ABORT` |
| `states` | scan_string_literals.py:101 | StringLiteralCategorizer | `ABC`, `ABORT` |
| `static` | dev_launcher_secrets.py:163 | EnhancedSecretLoader._get_s... | `ABC`, `ABORT` |
| `statistics` | coverage_reporter.py:218 | CoverageReporter._analyze_c... | `ABC`, `ABORT` |
| `stats` | query_string_literals.py:135 | main | `ABC`, `ABORT` |
| `Status` | local_secrets_manager.py:135 | LocalSecretsManager.list_se... | `ABC`, `ABORT` |
| `status` | connection.py:238 | AuthDatabase.get_status | `ABC`, `ABORT` |
| `status\_code` | test_auth_oauth_errors.py:162 | TestOAuthErrorHandling.test... | `ABC`, `ABORT` |
| `status\_value` | scan_string_literals.py:102 | StringLiteralCategorizer | `ABC`, `ABORT` |
| `status\_weights` | seed_staging_data.py:210 | StagingDataSeeder._get_opti... | `ABC`, `ABORT` |
| `statuses` | seed_staging_data.py:209 | StagingDataSeeder._get_opti... | `ABC`, `ABORT` |
| `StatusManager` | __init__.py:22 | module | `ABC`, `ABORT` |
| `stderr` | simple_perf_runner.py:62 | _create_result_dict | `ABC`, `ABORT` |
| `stdout` | simple_perf_runner.py:61 | _create_result_dict | `ABC`, `ABORT` |
| `step\_` | startup_profiler.py:140 | StartupProfiler.end_step_timer | `ABC`, `ABORT` |
| `step\_results` | startup_optimizer.py:303 | StartupOptimizer.get_timing... | `ABC`, `ABORT` |
| `step\_timings` | startup_optimizer.py:302 | StartupOptimizer.get_timing... | `ABC`, `ABORT` |
| `steps` | deploy_to_gcp.py:415 | GCPDeployer.build_image_cloud | `ABC`, `ABORT` |
| `still\_broken` | comprehensive_e2e_import_fixer.py:285 | ComprehensiveE2EImportFixer... | `ABC`, `ABORT` |
| `STOP` | dev_launcher_core.py:105 | DevLauncher._cleanup_handler | `ABC`, `ABORT` |
| `stop` | build_staging.py:256 | _add_action_arguments | `ABC`, `ABORT` |
| `STOP\_DEVELOPMENT` | emergency_boundary_actions.py:171 | EmergencyActionSystem._crea... | `ABC`, `ABORT` |
| `STOPPED` | launcher.py:242 | DevLauncher._terminate_all_... | `ABC`, `ABORT` |
| `storage\_gb` | cleanup_staging_environments.py:134 | StagingEnvironmentCleaner.g... | `ABC`, `ABORT` |
| `store` | test_frontend.py:34 | module | `ABC`, `ABORT` |
| `store\_true` | add_test_markers.py:236 | main | `ABC`, `ABORT` |
| `strategies` | demo_test_size_enforcement.py:95 | demo_test_refactor_helper | `ABC`, `ABORT` |
| `strategy` | test_refactor_helper.py:591 | TestRefactorHelper.generate... | `ABC`, `ABORT` |
| `stream` | comprehensive_test_fixer.py:94 | CodeGenerator.generate_func... | `ABC`, `ABORT` |
| `strict` | enforce_limits.py:228 | create_argument_parser | `ABC`, `ABORT` |
| `structural\_similarity` | analyze_test_overlap.py:374 | TestOverlapAnalyzer._genera... | `ABC`, `ABORT` |
| `stub` | real_test_requirements_enforcer.py:238 | MockComponentVisitor.visit_... | `ABC`, `ABORT` |
| `sub` | jwt_handler.py:104 | JWTHandler.refresh_access_t... | `ABC`, `ABORT` |
| `SubAgentLifecycle` | fix_all_import_issues.py:69 | ComprehensiveImportFixer._b... | `ABC`, `ABORT` |
| `SubAgentState` | comprehensive_e2e_import_fixer.py:61 | ComprehensiveE2EImportFixer... | `ABC`, `ABORT` |
| `SubAgentUpdate` | fix_all_import_issues.py:69 | ComprehensiveImportFixer._b... | `ABC`, `ABORT` |
| `subdirs` | cleanup_generated_files.py:25 | module | `ABC`, `ABORT` |
| `submit` | deploy_to_gcp.py:427 | GCPDeployer.build_image_cloud | `ABC`, `ABORT` |
| `SUCCESS` | clean_slate_executor.py:208 | CleanSlateExecutor.execute | `ABC`, `ABORT` |
| `Success` | test_dynamic_port_health.py:39 | TestDynamicPortHealthChecks... | `ABC`, `ABORT` |
| `success` | auth_routes.py:156 | logout | `ABC`, `ABORT` |
| `success\_count` | benchmark_optimization.py:131 | TestExecutionBenchmark._run... | `ABC`, `ABORT` |
| `success\_rate` | benchmark_optimization.py:133 | TestExecutionBenchmark._run... | `ABC`, `ABORT` |
| `success\_rate\_improvement` | benchmark_optimization.py:249 | TestExecutionBenchmark._com... | `ABC`, `ABORT` |
| `successful` | check_e2e_imports.py:49 | E2EImportChecker.__init__ | `ABC`, `ABORT` |
| `successful\_phases` | startup_optimizer.py:585 | StartupOptimizer.get_phase_... | `ABC`, `ABORT` |
| `successful\_runs` | cache_manager.py:273 | CacheManager._get_successfu... | `ABC`, `ABORT` |
| `successful\_tasks` | parallel_executor.py:285 | ParallelExecutor.get_perfor... | `ABC`, `ABORT` |
| `sudo` | recovery_actions.py:243 | RecoveryActions._restart_de... | `ABC`, `ABORT` |
| `suggest` | test_refactor_helper.py:679 | main | `ABC`, `ABORT` |
| `suggested\_fix` | check_schema_imports.py:47 | SchemaViolation.to_dict | `ABC`, `ABORT` |
| `suggested\_strategy` | analyze_failures.py:83 | TestFailureAnalyzer.analyze... | `ABC`, `ABORT` |
| `suggestion` | critical_error_handler.py:62 | CriticalErrorHandler.check_... | `ABC`, `ABORT` |
| `suggestions` | test_refactor_helper.py:84 | TestRefactorHelper.analyze_... | `ABC`, `ABORT` |
| `SUMMARY` | check_e2e_imports.py:280 | main | `ABC`, `ABORT` |
| `summary` | coverage_reporter.py:72 | CoverageReporter.parse_cove... | `ABC`, `ABORT` |
| `SUPERSEDED` | update_spec_timestamps.py:28 | module | `ABC`, `ABORT` |
| `superuser` | test_auth_token_security.py:110 | TestJWTClaimsExtraction.tes... | `ABC`, `ABORT` |
| `supervisor` | fix_comprehensive_imports.py:289 | ComprehensiveImportFixerV2.... | `ABC`, `ABORT` |
| `supervisor\_agent` | fix_e2e_tests_comprehensive.py:67 | E2ETestFixer._get_common_fi... | `ABC`, `ABORT` |
| `supervisor\_consolidated` | comprehensive_import_scanner.py:156 | ComprehensiveImportScanner.... | `ABC`, `ABORT` |
| `supply\_catalog\_management` | setup_assistant.py:31 | _get_assistant_capabilities | `ABC`, `ABORT` |
| `SupplyResearcherAgent` | fix_comprehensive_imports.py:207 | ComprehensiveImportFixerV2.... | `ABC`, `ABORT` |
| `supports\_cross\_service` | service_discovery.py:133 | ServiceDiscovery.register_s... | `ABC`, `ABORT` |
| `sut` | comprehensive_import_scanner.py:599 | ComprehensiveImportScanner.... | `ABC`, `ABORT` |
| `sut\_files\_scanned` | comprehensive_import_scanner.py:83 | ComprehensiveScanReport.to_... | `ABC`, `ABORT` |
| `sut\_issues` | comprehensive_import_scanner.py:89 | ComprehensiveScanReport.to_... | `ABC`, `ABORT` |
| `swift` | agent_tracking_helper.py:42 | AgentTrackingHelper | `ABC`, `ABORT` |
| `syntax` | comprehensive_import_scanner.py:179 | ComprehensiveImportScanner.... | `ABC`, `ABORT` |
| `syntax\_error` | analyze_failures.py:34 | TestFailureAnalyzer | `ABC`, `ABORT` |
| `syntax\_errors` | check_e2e_imports.py:52 | E2EImportChecker.__init__ | `ABC`, `ABORT` |
| `syntax\_valid` | test_workflows_with_act.py:307 | WorkflowTester.run_tests | `ABC`, `ABORT` |
| `SyntaxError` | analyze_failures.py:34 | TestFailureAnalyzer | `ABC`, `ABORT` |
| `sys` | test_refactor_helper.py:133 | TestRefactorHelper._categor... | `ABC`, `ABORT` |
| `system` | audit_factory.py:213 | AuditLogFactory.create_perm... | `ABC`, `ABORT` |
| `system\_exit` | analyze_failures.py:52 | TestFailureAnalyzer | `ABC`, `ABORT` |
| `system\_info\_error` | system_diagnostics.py:303 | SystemDiagnostics.get_syste... | `ABC`, `ABORT` |
| `system\_metrics` | emergency_boundary_actions.py:337 | EmergencyActionSystem._gene... | `ABC`, `ABORT` |
| `SYSTEM\_WIDE` | boundary_enforcer_system_checks.py:159 | ViolationFactory.create_mod... | `ABC`, `ABORT` |
| `systemctl` | recovery_actions.py:243 | RecoveryActions._restart_de... | `ABC`, `ABORT` |
| `SystemExit` | analyze_failures.py:52 | TestFailureAnalyzer | `ABC`, `ABORT` |
| `table` | verify_workflow_status.py:197 | CLIHandler.parse_args | `ABC`, `ABORT` |
| `table\_name` | scan_string_literals.py:84 | StringLiteralCategorizer | `ABC`, `ABORT` |
| `table\_output` | test_verify_workflow_status.py:138 | WorkflowStatusTester.test_o... | `ABC`, `ABORT` |
| `table\_output\_format` | test_verify_workflow_status_corrected.py:161 | WorkflowStatusTester.test_o... | `ABC`, `ABORT` |
| `tables\_count` | environment_validator.py:176 | EnvironmentValidator.test_p... | `ABC`, `ABORT` |
| `tags` | seed_staging_data.py:318 | StagingDataSeeder._create_m... | `ABC`, `ABORT` |
| `target` | analyze_mocks.py:277 | MockAnalyzer.export_unjusti... | `ABC`, `ABORT` |
| `target\_duration` | test_backend_optimized.py:58 | module | `ABC`, `ABORT` |
| `target\_folders` | check_architecture_compliance.py:29 | _create_enforcer | `ABC`, `ABORT` |
| `target\_functions` | decompose_functions.py:109 | suggest_decomposition | `ABC`, `ABORT` |
| `target\_met` | launcher.py:880 | DevLauncher._handle_cleanup | `ABC`, `ABORT` |
| `target\_metric` | seed_staging_data.py:229 | StagingDataSeeder._generate... | `ABC`, `ABORT` |
| `task\_` | test_phase3_multiprocessing.py:81 | TestParallelExecutor.test_p... | `ABC`, `ABORT` |
| `task\_a` | test_phase3_multiprocessing.py:126 | TestParallelExecutor.test_d... | `ABC`, `ABORT` |
| `task\_b` | test_phase3_multiprocessing.py:127 | TestParallelExecutor.test_d... | `ABC`, `ABORT` |
| `task\_c` | test_phase3_multiprocessing.py:128 | TestParallelExecutor.test_d... | `ABC`, `ABORT` |
| `task\_description` | metadata_header_generator.py:89 | MetadataHeaderGenerator.gen... | `ABC`, `ABORT` |
| `task\_id` | agent_tracking_helper.py:128 | AgentTrackingHelper._create... | `ABC`, `ABORT` |
| `taskkill` | dev_launcher_processes.py:113 | ProcessMonitor._terminate_p... | `ABC`, `ABORT` |
| `tasklist` | service_discovery.py:106 | ServiceDiscovery.is_service... | `ABC`, `ABORT` |
| `tcp\_keepalives\_count` | connection.py:169 | AuthDatabase._get_cloud_sql... | `ABC`, `ABORT` |
| `tcp\_keepalives\_idle` | connection.py:167 | AuthDatabase._get_cloud_sql... | `ABC`, `ABORT` |
| `tcp\_keepalives\_interval` | connection.py:168 | AuthDatabase._get_cloud_sql... | `ABC`, `ABORT` |
| `team\_collaboration` | business_value_test_index.py:101 | BusinessValueTestIndexer.__... | `ABC`, `ABORT` |
| `team\_updates` | team_updates.py:64 | main | `ABC`, `ABORT` |
| `tearDown` | test_refactor_helper.py:212 | TestRefactorHelper._determi... | `ABC`, `ABORT` |
| `teardown` | test_refactor_helper.py:212 | TestRefactorHelper._determi... | `ABC`, `ABORT` |
| `teardown\_method` | test_refactor_helper.py:212 | TestRefactorHelper._determi... | `ABC`, `ABORT` |
| `temp` | recovery_actions.py:42 | RecoveryActions._get_temp_d... | `ABC`, `ABORT` |
| `temp\_` | test_launcher_integration.py:325 | TestFileManagement._create_... | `ABC`, `ABORT` |
| `TempService` | test_launcher_process.py:321 | TestResourceManagement._add... | `ABC`, `ABORT` |
| `TERM\_PROGRAM` | dev_launcher_config.py:104 | _check_platform_emoji_support | `ABC`, `ABORT` |
| `terminate\_all` | test_launcher_health.py:274 | TestErrorRecovery._test_cle... | `ABC`, `ABORT` |
| `terraform` | cleanup_staging_environments.py:174 | StagingEnvironmentCleaner.c... | `ABC`, `ABORT` |
| `Test` | analyze_test_overlap.py:124 | TestOverlapAnalyzer._extrac... | `ABC`, `ABORT` |
| `test` | config.py:103 | AuthConfig.get_redis_url | `ABC`, `ABORT` |
| `test\_` | analyze_critical_paths.py:50 | module | `ABC`, `ABORT` |
| `test\_access\_token` | test_mixins.py:163 | AuthTestMixin.setup_auth_mocks | `ABC`, `ABORT` |
| `test\_auth\_service` | test_config.py:100 | PostgresTestConfig.__init__ | `ABC`, `ABORT` |
| `test\_auth\_token` | fix_e2e_tests_comprehensive.py:68 | E2ETestFixer._get_common_fi... | `ABC`, `ABORT` |
| `test\_automation` | config_manager.py:54 | ConfigurationManager._get_i... | `ABC`, `ABORT` |
| `test\_backend` | cleanup_test_processes.py:80 | find_test_processes | `ABC`, `ABORT` |
| `test\_ch` | demo_real_llm_testing.py:197 | demo_test_environment_orche... | `ABC`, `ABORT` |
| `test\_code` | generate_fix.py:188 | AIFixGenerator._add_test_an... | `ABC`, `ABORT` |
| `test\_complexity` | ultra_thinking_analyzer.py:93 | UltraThinkingAnalyzer._anal... | `ABC`, `ABORT` |
| `test\_configs` | generate_test_audit.py:66 | analyze_test_structure | `ABC`, `ABORT` |
| `test\_count` | benchmark_optimization.py:130 | TestExecutionBenchmark._run... | `ABC`, `ABORT` |
| `test\_cpu` | test_phase3_multiprocessing.py:334 | test_phase3_integration | `ABC`, `ABORT` |
| `test\_data` | analyze_failures.py:151 | TestFailureAnalyzer._determ... | `ABC`, `ABORT` |
| `test\_database\_session` | fix_e2e_tests_comprehensive.py:55 | E2ETestFixer._get_common_fi... | `ABC`, `ABORT` |
| `TEST\_DATABASE\_URL` | test_env.py:29 | TestEnvironment | `ABC`, `ABORT` |
| `test\_db` | demo_real_llm_testing.py:197 | demo_test_environment_orche... | `ABC`, `ABORT` |
| `test\_dep` | test_phase3_multiprocessing.py:342 | test_phase3_integration | `ABC`, `ABORT` |
| `test\_details` | add_test_markers.py:213 | TestMarkerAdder.run | `ABC`, `ABORT` |
| `test\_directories` | generate_test_audit.py:63 | analyze_test_structure | `ABC`, `ABORT` |
| `test\_env` | test_base.py:41 | AsyncTestBase.teardown_method | `ABC`, `ABORT` |
| `test\_failures` | team_updates_formatter.py:141 | HumanFormatter.format_test_... | `ABC`, `ABORT` |
| `TEST\_FEATURE\_ENTERPRISE\_SSO` | demo_feature_flag_system.py:108 | demonstrate_environment_ove... | `ABC`, `ABORT` |
| `test\_file` | analyze_failures.py:142 | TestFailureAnalyzer._determ... | `ABC`, `ABORT` |
| `test\_file\_size` | orchestrator.py:175 | ArchitectureEnforcer.genera... | `ABC`, `ABORT` |
| `test\_files` | orchestrator.py:91 | ArchitectureEnforcer._calcu... | `ABC`, `ABORT` |
| `test\_files\_scanned` | comprehensive_import_scanner.py:82 | ComprehensiveScanReport.to_... | `ABC`, `ABORT` |
| `test\_files\_with\_violations` | relaxed_violation_counter.py:40 | RelaxedViolationCounter.get... | `ABC`, `ABORT` |
| `test\_framework` | align_test_imports.py:34 | TestImportAligner.__init__ | `ABC`, `ABORT` |
| `test\_framework\_size` | generate_test_audit.py:117 | check_test_health | `ABC`, `ABORT` |
| `test\_frameworks` | generate_test_audit.py:68 | analyze_test_structure | `ABC`, `ABORT` |
| `test\_frontend` | cleanup_test_processes.py:80 | find_test_processes | `ABC`, `ABORT` |
| `test\_function\_complexity` | orchestrator.py:175 | ArchitectureEnforcer.genera... | `ABC`, `ABORT` |
| `test\_google\_client\_id` | conftest.py:16 | module | `ABC`, `ABORT` |
| `test\_google\_client\_secret` | conftest.py:17 | module | `ABC`, `ABORT` |
| `test\_health` | team_updates_orchestrator.py:86 | TeamUpdatesOrchestrator._ca... | `ABC`, `ABORT` |
| `test\_hierarchy` | workflow_config_utils.py:53 | WorkflowConfigUtils._show_t... | `ABC`, `ABORT` |
| `test\_integration` | project_test_validator.py:264 | ProjectTestValidator._check... | `ABC`, `ABORT` |
| `test\_io` | test_phase3_multiprocessing.py:338 | test_phase3_integration | `ABC`, `ABORT` |
| `test\_issues` | comprehensive_import_scanner.py:88 | ComprehensiveScanReport.to_... | `ABC`, `ABORT` |
| `test\_jwt\_secret\_key\_that\_is\_lon...` | conftest.py:15 | module | `ABC`, `ABORT` |
| `test\_level` | process_results.py:186 | TestResultProcessor.generat... | `ABC`, `ABORT` |
| `test\_mcp` | test_websocket_connection_issue.py:72 | TestWebSocketConnectionIssu... | `ABC`, `ABORT` |
| `test\_methods` | test_size_validator.py:332 | TestSizeValidator._analyze_... | `ABC`, `ABORT` |
| `test\_metrics` | team_updates_formatter.py:65 | HumanFormatter.format_execu... | `ABC`, `ABORT` |
| `test\_mode` | startup_environment.py:48 | StartupEnvironment._record_... | `ABC`, `ABORT` |
| `test\_module\_` | check_e2e_imports.py:85 | E2EImportChecker.check_file... | `ABC`, `ABORT` |
| `test\_module\_import` | cleanup_duplicate_tests.py:82 | TestModuleImportCleaner.has... | `ABC`, `ABORT` |
| `test\_name` | generate_report.py:104 | _format_single_failure | `ABC`, `ABORT` |
| `test\_pass` | validate_network_constants.py:82 | validate_database_constants | `ABC`, `ABORT` |
| `test\_password` | test_oauth_models.py:42 | TestLoginRequest.test_valid... | `ABC`, `ABORT` |
| `test\_port` | installer_types.py:67 | create_version_requirements | `ABC`, `ABORT` |
| `test\_priority` | test_generator.py:186 | _needs_error_test | `ABC`, `ABORT` |
| `test\_project` | test_phase3_multiprocessing.py:151 | TestAsyncDependencyChecker.... | `ABC`, `ABORT` |
| `test\_redis` | demo_real_llm_testing.py:197 | demo_test_environment_orche... | `ABC`, `ABORT` |
| `test\_refresh\_token` | test_mixins.py:164 | AuthTestMixin.setup_auth_mocks | `ABC`, `ABORT` |
| `test\_reports` | align_test_imports.py:420 | TestImportAligner.generate_... | `ABC`, `ABORT` |
| `test\_results` | real_service_test_metrics.py:26 | RealServiceTestMetrics.__in... | `ABC`, `ABORT` |
| `test\_runner` | cleanup_test_processes.py:80 | find_test_processes | `ABC`, `ABORT` |
| `test\_runners` | generate_test_audit.py:65 | analyze_test_structure | `ABC`, `ABORT` |
| `test\_schema\_import` | check_schema_imports.py:254 | SchemaImportAnalyzer._check... | `ABC`, `ABORT` |
| `test\_service` | test_startup_comprehensive.py:60 | TestProcessManagerWindows.t... | `ABC`, `ABORT` |
| `test\_state` | test_auth_oauth_errors.py:121 | TestOAuthErrorHandling.test... | `ABC`, `ABORT` |
| `test\_status` | team_updates_formatter.py:123 | HumanFormatter.format_test_... | `ABC`, `ABORT` |
| `test\_stub` | architecture_scanner_quality.py:60 | QualityScanner._find_stub_p... | `ABC`, `ABORT` |
| `test\_stub\_boundary` | boundary_enforcer_type_checks.py:123 | TestStubChecker._create_tes... | `ABC`, `ABORT` |
| `test\_stubs` | architecture_metrics.py:48 | ArchitectureMetrics._calcul... | `ABC`, `ABORT` |
| `test\_suggestions` | cli.py:104 | OutputHandler.process_output | `ABC`, `ABORT` |
| `test\_task` | test_phase3_multiprocessing.py:47 | TestParallelExecutor.test_s... | `ABC`, `ABORT` |
| `test\_tube` | __main__.py:383 | handle_service_configuration | `ABC`, `ABORT` |
| `test\_type\_distribution` | business_value_test_index.py:597 | BusinessValueTestIndexer.ge... | `ABC`, `ABORT` |
| `test\_user` | test_example_message_flow.py:292 | ExampleMessageFlowTestRunne... | `ABC`, `ABORT` |
| `test\_user\_data` | fix_e2e_tests_comprehensive.py:69 | E2ETestFixer._get_common_fi... | `ABC`, `ABORT` |
| `test\_utils` | check_test_import_order.py:39 | check_import_order | `ABC`, `ABORT` |
| `test\_value` | validate_staging_config.py:244 | check_redis_connection | `ABC`, `ABORT` |
| `test\_violations` | relaxed_violation_counter.py:37 | RelaxedViolationCounter.get... | `ABC`, `ABORT` |
| `TestAnalysis` | __init__.py:15 | module | `ABC`, `ABORT` |
| `testcontainers` | business_value_test_index.py:344 | BusinessValueTestIndexer._d... | `ABC`, `ABORT` |
| `TestCoverageAnalyzer` | status_analyzer.py:28 | module | `ABC`, `ABORT` |
| `TestCoverageInfo` | status_agent_analyzer.py:148 | TestCoverageAnalyzer._check... | `ABC`, `ABORT` |
| `TestCoverageStatus` | status_agent_analyzer.py:137 | TestCoverageAnalyzer.check_... | `ABC`, `ABORT` |
| `TestEnvironment` | __init__.py:9 | module | `ABC`, `ABORT` |
| `TestGenerator` | __init__.py:20 | module | `ABC`, `ABORT` |
| `TESTING` | auth_service.py:450 | AuthService.request_passwor... | `ABC`, `ABORT` |
| `testing` | manage_workflows.py:78 | WorkflowManager._get_workfl... | `ABC`, `ABORT` |
| `TestMetadata` | __init__.py:18 | module | `ABC`, `ABORT` |
| `TestModule` | final_syntax_fix.py:21 | create_minimal_test_file | `ABC`, `ABORT` |
| `testpass` | test_security.py:87 | TestSQLInjectionPrevention.... | `ABC`, `ABORT` |
| `TestPattern` | __init__.py:17 | module | `ABC`, `ABORT` |
| `TestProviders` | fix_frontend_tests.py:16 | _should_skip_file | `ABC`, `ABORT` |
| `TestResults` | status_agent_analyzer.py:205 | HealthScoreCalculator.calcu... | `ABC`, `ABORT` |
| `tests` | aggressive_syntax_fix.py:15 | get_files_with_errors | `ABC`, `ABORT` |
| `TestService` | test_dev_user_flow.py:88 | TestDevUserCreation.test_de... | `ABC`, `ABORT` |
| `TestSettings` | test_settings.py:112 | TestSettings.for_unit_tests | `ABC`, `ABORT` |
| `text` | test_auth_oauth_errors.py:381 | TestOAuthErrorHandling.test... | `ABC`, `ABORT` |
| `third\_party` | core.py:86 | ComplianceConfig._get_skip_... | `ABC`, `ABORT` |
| `Thread` | deduplicate_types.py:82 | TypeDeduplicator._setup_pyt... | `ABC`, `ABORT` |
| `thread\_id` | seed_staging_data.py:217 | StagingDataSeeder._generate... | `ABC`, `ABORT` |
| `thread\_ids` | seed_staging_data.py:358 | StagingDataSeeder.generate_... | `ABC`, `ABORT` |
| `thread\_management\_service` | fix_e2e_tests_comprehensive.py:58 | E2ETestFixer._get_common_fi... | `ABC`, `ABORT` |
| `thread\_service` | comprehensive_import_scanner.py:155 | ComprehensiveImportScanner.... | `ABC`, `ABORT` |
| `ThreadMetadata` | deduplicate_types.py:104 | TypeDeduplicator._setup_typ... | `ABC`, `ABORT` |
| `ThreadPoolExecutor` | log_filter.py:123 | LogFilter._is_background_task | `ABC`, `ABORT` |
| `threads` | seed_staging_data.py:54 | StagingDataSeeder.__init__ | `ABC`, `ABORT` |
| `threads\_per\_user` | seed_staging_data.py:152 | StagingDataSeeder.seed_thre... | `ABC`, `ABORT` |
| `ThreadService` | fast_import_checker.py:78 | fix_known_import_issues | `ABC`, `ABORT` |
| `throughput` | seed_staging_data.py:229 | StagingDataSeeder._generate... | `ABC`, `ABORT` |
| `throughput\_optimization` | seed_staging_data.py:208 | StagingDataSeeder._get_opti... | `ABC`, `ABORT` |
| `throughput\_rps` | validate_staging_health.py:137 | StagingPerformanceValidator... | `ABC`, `ABORT` |
| `tier` | business_value_test_index.py:648 | BusinessValueTestIndexer._i... | `ABC`, `ABORT` |
| `tier\_coverage` | business_value_test_index.py:592 | BusinessValueTestIndexer.ge... | `ABC`, `ABORT` |
| `TIME` | launcher.py:875 | DevLauncher._handle_cleanup | `ABC`, `ABORT` |
| `time` | test_refactor_helper.py:133 | TestRefactorHelper._categor... | `ABC`, `ABORT` |
| `time\_range\_days` | seed_staging_data.py:329 | StagingDataSeeder.seed_metrics | `ABC`, `ABORT` |
| `time\_saved\_hours\_per\_day` | benchmark_optimization.py:289 | TestExecutionBenchmark._est... | `ABC`, `ABORT` |
| `time\_saved\_percentage` | benchmark_optimization.py:248 | TestExecutionBenchmark._com... | `ABC`, `ABORT` |
| `time\_saved\_seconds` | benchmark_optimization.py:247 | TestExecutionBenchmark._com... | `ABC`, `ABORT` |
| `time\_window` | seed_staging_data.py:232 | StagingDataSeeder._generate... | `ABC`, `ABORT` |
| `TIMEOUT` | comprehensive_test_fixer.py:383 | BatchProcessor._run_test | `ABC`, `ABORT` |
| `Timeout` | process_manager.py:172 | ProcessManager._run_taskkil... | `ABC`, `ABORT` |
| `timeout` | benchmark_optimization.py:147 | TestExecutionBenchmark._run... | `ABC`, `ABORT` |
| `timeout\_error` | analyze_failures.py:47 | TestFailureAnalyzer | `ABC`, `ABORT` |
| `timeouts` | validate_workflow_config.py:24 | validate_config_structure | `ABC`, `ABORT` |
| `TimeoutService` | test_launcher_process.py:181 | TestAdvancedProcessManager.... | `ABC`, `ABORT` |
| `TimeRange` | generate-json-schema.py:21 | main | `ABC`, `ABORT` |
| `timestamp` | main.py:59 | AuthServiceHealthInterface.... | `ABC`, `ABORT` |
| `title` | generate_openapi_spec.py:52 | _add_metadata | `ABC`, `ABORT` |
| `tmp` | recovery_actions.py:43 | RecoveryActions._get_temp_d... | `ABC`, `ABORT` |
| `to\_dict` | startup_reporter.py:44 | ReportData.__init__ | `ABC`, `ABORT` |
| `TODO` | secret_validator.py:75 | SecretValidator._is_invalid... | `ABC`, `ABORT` |
| `todo` | ultra_thinking_analyzer.py:194 | UltraThinkingAnalyzer._extr... | `ABC`, `ABORT` |
| `TOKEN` | launcher.py:408 | DevLauncher._ensure_cross_s... | `ABC`, `ABORT` |
| `token` | test_oauth_flows_auth.py:45 | TestSyntaxFix.test_oauth_en... | `ABC`, `ABORT` |
| `TOKEN\_CREATED` | audit_factory.py:26 | AuditLogFactory | `ABC`, `ABORT` |
| `token\_created` | audit_factory.py:26 | AuditLogFactory | `ABC`, `ABORT` |
| `token\_exchange` | test_auth_oauth_errors.py:292 | TestOAuthErrorHandling.test... | `ABC`, `ABORT` |
| `TOKEN\_REFRESHED` | audit_factory.py:27 | AuditLogFactory | `ABC`, `ABORT` |
| `token\_refreshed` | audit_factory.py:27 | AuditLogFactory | `ABC`, `ABORT` |
| `TOKEN\_REVOKED` | audit_factory.py:28 | AuditLogFactory | `ABC`, `ABORT` |
| `token\_revoked` | audit_factory.py:28 | AuditLogFactory | `ABC`, `ABORT` |
| `token\_type` | jwt_handler.py:84 | JWTHandler.validate_token | `ABC`, `ABORT` |
| `token\_usage` | seed_staging_data.py:283 | StagingDataSeeder._get_metr... | `ABC`, `ABORT` |
| `TokenFactory` | __init__.py:17 | module | `ABC`, `ABORT` |
| `TokenTestUtils` | __init__.py:16 | module | `ABC`, `ABORT` |
| `too\_many\_failed\_attempts` | audit_factory.py:184 | AuditLogFactory.create_acco... | `ABC`, `ABORT` |
| `tool` | metadata_header_generator.py:32 | MetadataHeaderGenerator._ge... | `ABC`, `ABORT` |
| `tool\_version` | architecture_reporter.py:50 | ArchitectureReporter._get_r... | `ABC`, `ABORT` |
| `ToolInput` | validate_type_deduplication.py:70 | TypeDeduplicationValidator.... | `ABC`, `ABORT` |
| `ToolResult` | validate_type_deduplication.py:69 | TypeDeduplicationValidator.... | `ABC`, `ABORT` |
| `ToolResultData` | deduplicate_types.py:80 | TypeDeduplicator._setup_pyt... | `ABC`, `ABORT` |
| `tools` | setup_assistant.py:58 | _create_assistant_config | `ABC`, `ABORT` |
| `tools\_available` | import_management.py:197 | ImportManagementSystem.gene... | `ABC`, `ABORT` |
| `tools\_run` | import_management.py:59 | ImportManagementSystem.__in... | `ABC`, `ABORT` |
| `ToolStatus` | validate_type_deduplication.py:68 | TypeDeduplicationValidator.... | `ABC`, `ABORT` |
| `top` | recovery_manager.py:46 | RecoveryManager._get_system... | `ABC`, `ABORT` |
| `top\_mocked\_targets` | analyze_mocks.py:223 | MockAnalyzer.generate_report | `ABC`, `ABORT` |
| `top\_overlaps\_by\_category` | analyze_test_overlap.py:360 | TestOverlapAnalyzer._genera... | `ABC`, `ABORT` |
| `top\_unjustified` | analyze_mocks.py:224 | MockAnalyzer.generate_report | `ABC`, `ABORT` |
| `top\_value\_tests` | business_value_test_index.py:606 | BusinessValueTestIndexer.ge... | `ABC`, `ABORT` |
| `total` | analyze_coverage.py:16 | module | `ABC`, `ABORT` |
| `total\_business\_value` | business_value_test_index.py:589 | BusinessValueTestIndexer.ge... | `ABC`, `ABORT` |
| `total\_checks` | environment_validator.py:397 | EnvironmentValidator.genera... | `ABC`, `ABORT` |
| `total\_commits` | team_updates_git_analyzer.py:32 | GitAnalyzer.analyze | `ABC`, `ABORT` |
| `total\_condensed` | log_filter.py:231 | LogFilter.get_filter_stats | `ABC`, `ABORT` |
| `total\_config\_fixes` | align_test_imports.py:415 | TestImportAligner.generate_... | `ABC`, `ABORT` |
| `total\_crashes` | crash_reporter.py:231 | CrashReporter._build_crash_... | `ABC`, `ABORT` |
| `total\_duration` | generate_performance_report.py:41 | add_summary_timing | `ABC`, `ABORT` |
| `total\_entries` | secret_cache.py:215 | SecretCache.get_cache_stats | `ABC`, `ABORT` |
| `total\_errors` | import_management.py:55 | ImportManagementSystem.__in... | `ABC`, `ABORT` |
| `total\_failures` | analyze_failures.py:75 | TestFailureAnalyzer.analyze... | `ABC`, `ABORT` |
| `total\_fake\_tests` | fake_test_scanner.py:85 | FakeTestScanner.scan_all_tests | `ABC`, `ABORT` |
| `total\_file\_fixes` | align_test_imports.py:416 | TestImportAligner.generate_... | `ABC`, `ABORT` |
| `total\_files` | boundary_enforcer_report_generator.py:122 | ConsoleReportPrinter._print... | `ABC`, `ABORT` |
| `total\_files\_analyzed` | check_schema_imports.py:289 | SchemaImportAnalyzer.analyz... | `ABC`, `ABORT` |
| `total\_files\_checked` | core.py:167 | _build_summary | `ABC`, `ABORT` |
| `total\_files\_modified` | metadata_header_generator.py:115 | MetadataHeaderGenerator.gen... | `ABC`, `ABORT` |
| `total\_files\_scanned` | architecture_dashboard_html.py:84 | DashboardHTMLComponents._ge... | `ABC`, `ABORT` |
| `total\_files\_with\_violations` | relaxed_violation_counter.py:41 | RelaxedViolationCounter.get... | `ABC`, `ABORT` |
| `total\_functions\_scanned` | architecture_dashboard_html.py:94 | DashboardHTMLComponents._ge... | `ABC`, `ABORT` |
| `total\_import\_fixes` | align_test_imports.py:414 | TestImportAligner.generate_... | `ABC`, `ABORT` |
| `total\_issues` | comprehensive_import_scanner.py:81 | ComprehensiveScanReport.to_... | `ABC`, `ABORT` |
| `total\_lines` | analyze_test_overlap.py:63 | TestOverlapAnalyzer.__init__ | `ABC`, `ABORT` |
| `total\_literals` | query_string_literals.py:111 | StringLiteralQuery.get_stats | `ABC`, `ABORT` |
| `total\_llm\_cost` | real_service_test_metrics.py:100 | RealServiceTestMetrics.fina... | `ABC`, `ABORT` |
| `total\_loc\_boundary` | boundary_enforcer_system_checks.py:169 | ViolationFactory.create_tot... | `ABC`, `ABORT` |
| `TOTAL\_LOC\_LIMIT` | boundary_enforcer_system_checks.py:170 | ViolationFactory.create_tot... | `ABC`, `ABORT` |
| `total\_mb` | system_diagnostics.py:317 | SystemDiagnostics._get_disk... | `ABC`, `ABORT` |
| `total\_methods` | test_size_validator.py:331 | TestSizeValidator._analyze_... | `ABC`, `ABORT` |
| `total\_mocks` | analyze_mocks.py:218 | MockAnalyzer.generate_report | `ABC`, `ABORT` |
| `total\_replacements` | deduplicate_types.py:365 | TypeDeduplicator.generate_r... | `ABC`, `ABORT` |
| `total\_similarity\_pairs` | analyze_test_overlap.py:350 | TestOverlapAnalyzer._genera... | `ABC`, `ABORT` |
| `total\_startup\_time` | startup_optimizer.py:301 | StartupOptimizer.get_timing... | `ABC`, `ABORT` |
| `total\_steps\_executed` | startup_optimizer.py:588 | StartupOptimizer.get_phase_... | `ABC`, `ABORT` |
| `total\_steps\_skipped` | startup_optimizer.py:587 | StartupOptimizer.get_phase_... | `ABC`, `ABORT` |
| `total\_tasks` | parallel_executor.py:284 | ParallelExecutor.get_perfor... | `ABC`, `ABORT` |
| `total\_test\_files` | analyze_test_overlap.py:348 | TestOverlapAnalyzer._genera... | `ABC`, `ABORT` |
| `total\_test\_functions` | analyze_test_overlap.py:349 | TestOverlapAnalyzer._genera... | `ABC`, `ABORT` |
| `total\_tests` | analyze_test_overlap.py:62 | TestOverlapAnalyzer.__init__ | `ABC`, `ABORT` |
| `total\_time` | startup_optimizer.py:583 | StartupOptimizer.get_phase_... | `ABC`, `ABORT` |
| `total\_tracked\_tests` | fake_test_scanner.py:300 | FakeTestScanner.generate_co... | `ABC`, `ABORT` |
| `total\_validation\_time\_ms` | environment_validator.py:403 | EnvironmentValidator.genera... | `ABC`, `ABORT` |
| `total\_violations` | architecture_dashboard_html.py:74 | DashboardHTMLComponents._ge... | `ABC`, `ABORT` |
| `totals` | coverage_reporter.py:59 | CoverageReporter.parse_cove... | `ABC`, `ABORT` |
| `traceback` | test_auth_oauth_errors.py:384 | TestOAuthErrorHandling.test... | `ABC`, `ABORT` |
| `trend` | team_updates_compliance_analyzer.py:160 | ComplianceAnalyzer._parse_c... | `ABC`, `ABORT` |
| `trends` | architecture_reporter.py:42 | ArchitectureReporter._build... | `ABC`, `ABORT` |
| `True` | coverage_config.py:91 | CoverageConfig.create_cover... | `ABC`, `ABORT` |
| `true` | config.py:116 | AuthConfig.is_redis_disabled | `ABC`, `ABORT` |
| `try\_blocks` | auto_decompose_functions.py:191 | FunctionDecomposer._identif... | `ABC`, `ABORT` |
| `tsc` | test_frontend.py:336 | run_type_check | `ABC`, `ABORT` |
| `tsx` | agent_tracking_helper.py:30 | AgentTrackingHelper | `ABC`, `ABORT` |
| `typ` | test_auth_token_security.py:211 | TestJWTSignatureVerificatio... | `ABC`, `ABORT` |
| `type` | token_factory.py:38 | TokenFactory.create_token_c... | `ABC`, `ABORT` |
| `type\_error` | analyze_failures.py:36 | TestFailureAnalyzer | `ABC`, `ABORT` |
| `types` | query_string_literals.py:118 | StringLiteralQuery.get_stats | `ABC`, `ABORT` |
| `types\_unified` | deduplicate_types.py:367 | TypeDeduplicator.generate_r... | `ABC`, `ABORT` |
| `typescript` | agent_tracking_helper.py:28 | AgentTrackingHelper | `ABC`, `ABORT` |
| `typescript\_files` | deduplicate_types.py:369 | TypeDeduplicator.generate_r... | `ABC`, `ABORT` |
| `typescript\_modular` | auto_split_files.py:116 | FileSplitter._analyze_types... | `ABC`, `ABORT` |
| `typing` | type_checker.py:155 | TypeChecker._filter_backend... | `ABC`, `ABORT` |
| `ui\_ux\_` | update_spec_timestamps.py:72 | module | `ABC`, `ABORT` |
| `ultra\_fast` | test_backend_optimized.py:91 | module | `ABC`, `ABORT` |
| `UltraThinkingAnalyzer` | __init__.py:19 | module | `ABC`, `ABORT` |
| `unauthorized\_client` | test_auth_oauth_errors.py:172 | TestOAuthErrorHandling.test... | `ABC`, `ABORT` |
| `unavailable` | validate_staging_health.py:92 | StagingHealthValidator._che... | `ABC`, `ABORT` |
| `Uncategorized` | split_learnings.py:42 | parse_learnings | `ABC`, `ABORT` |
| `uncategorized` | categorize_tests.py:31 | TestCategorizer._initialize... | `ABC`, `ABORT` |
| `uncommitted\_count` | metadata_header_generator.py:62 | MetadataHeaderGenerator._ge... | `ABC`, `ABORT` |
| `UnicodeService` | test_launcher_process.py:294 | TestLogStreaming._capture_u... | `ABC`, `ABORT` |
| `unified` | business_value_test_index.py:162 | BusinessValueTestIndexer.sc... | `ABC`, `ABORT` |
| `unified\_chat\_ui\_ux` | update_spec_timestamps.py:75 | module | `ABC`, `ABORT` |
| `unified\_import\_report\_` | unified_import_manager.py:495 | UnifiedImportManager.save_r... | `ABC`, `ABORT` |
| `unified\_manager` | import_management.py:48 | ImportManagementSystem.__in... | `ABC`, `ABORT` |
| `unified\_tools` | fix_schema_imports.py:33 | SchemaImportFixer.move_sche... | `ABC`, `ABORT` |
| `unit` | test_env.py:210 | get_test_environment | `ABC`, `ABORT` |
| `unit\_patterns` | categorize_tests.py:43 | TestCategorizer._initialize... | `ABC`, `ABORT` |
| `unit\_tests` | generate_wip_report.py:103 | WIPReportGenerator.calculat... | `ABC`, `ABORT` |
| `unittest` | test_reviewer.py:223 | AutonomousTestReviewer._ide... | `ABC`, `ABORT` |
| `universal\_newlines` | utils.py:372 | create_subprocess | `ABC`, `ABORT` |
| `Unknown` | check_netra_backend_imports.py:167 | ImportAnalyzer._create_issue | `ABC`, `ABORT` |
| `unknown` | agent_tracking_helper.py:86 | AgentTrackingHelper._get_gi... | `ABC`, `ABORT` |
| `unknown\_error` | analyze_failures.py:138 | TestFailureAnalyzer._classi... | `ABC`, `ABORT` |
| `unmatched` | fix_all_test_issues.py:240 | main | `ABC`, `ABORT` |
| `unparse` | ultra_thinking_analyzer.py:156 | UltraThinkingAnalyzer._extr... | `ABC`, `ABORT` |
| `unreachable` | config_validator.py:35 | ConfigStatus | `ABC`, `ABORT` |
| `unresolved\_crashes` | crash_reporter.py:233 | CrashReporter._build_crash_... | `ABC`, `ABORT` |
| `up` | build_staging.py:142 | StagingBuilder.start_stagin... | `ABC`, `ABORT` |
| `update` | ultra_thinking_analyzer.py:175 | UltraThinkingAnalyzer._iden... | `ABC`, `ABORT` |
| `update\_` | auto_split_files.py:258 | FileSplitter._group_functio... | `ABC`, `ABORT` |
| `update\_cache` | startup_optimizer.py:634 | create_verify_phase_steps | `ABC`, `ABORT` |
| `Updated` | team_updates_documentation_analyzer.py:185 | DocumentationAnalyzer._simp... | `ABC`, `ABORT` |
| `updated` | team_updates_documentation_analyzer.py:176 | DocumentationAnalyzer._stat... | `ABC`, `ABORT` |
| `updated\_at` | user_factory.py:44 | UserFactory.create_user_data | `ABC`, `ABORT` |
| `updatedAt` | workflow_introspection.py:130 | WorkflowIntrospector.get_re... | `ABC`, `ABORT` |
| `updaters` | auto_split_files.py:259 | FileSplitter._group_functio... | `ABC`, `ABORT` |
| `upgrade` | clean_slate_executor.py:116 | CleanSlateExecutor.phase2_d... | `ABC`, `ABORT` |
| `uptime\_seconds` | main.py:60 | AuthServiceHealthInterface.... | `ABC`, `ABORT` |
| `URGENT\_REPORT` | emergency_boundary_actions.py:226 | EmergencyActionSystem._crea... | `ABC`, `ABORT` |
| `URL` | validate_staging_config.py:327 | check_environment_variables | `ABC`, `ABORT` |
| `url` | cleanup_staging_environments.py:70 | StagingEnvironmentCleaner.g... | `ABC`, `ABORT` |
| `usage` | split_learnings.py:108 | create_index | `ABC`, `ABORT` |
| `usage\_current` | seed_staging_data.py:124 | StagingDataSeeder._build_ad... | `ABC`, `ABORT` |
| `usage\_quota` | seed_staging_data.py:124 | StagingDataSeeder._build_ad... | `ABC`, `ABORT` |
| `use\_defaults` | config_validator.py:226 | ConfigDecisionEngine.get_fa... | `ABC`, `ABORT` |
| `use\_existing` | config_validator.py:231 | ConfigDecisionEngine.get_fa... | `ABC`, `ABORT` |
| `USE\_REAL\_SERVICES` | test_staging.py:36 | setup_staging_env | `ABC`, `ABORT` |
| `use\_turbopack` | config.py:213 | LauncherConfig.to_dict | `ABC`, `ABORT` |
| `used\_mb` | system_diagnostics.py:318 | SystemDiagnostics._get_disk... | `ABC`, `ABORT` |
| `used\_memory\_human` | environment_validator.py:268 | EnvironmentValidator.test_r... | `ABC`, `ABORT` |
| `used\_refresh\_tokens` | auth_service.py:182 | AuthService._refresh_with_r... | `ABC`, `ABORT` |
| `USER` | manage_precommit.py:67 | disable_hooks | `ABC`, `ABORT` |
| `User` | deduplicate_types.py:81 | TypeDeduplicator._setup_pyt... | `ABC`, `ABORT` |
| `user` | auth_routes.py:379 | dev_login | `ABC`, `ABORT` |
| `user\_agent` | repository.py:167 | AuthSessionRepository.creat... | `ABC`, `ABORT` |
| `user\_cancelled\_login` | test_auth_oauth_errors.py:128 | TestOAuthErrorHandling.test... | `ABC`, `ABORT` |
| `user\_flows` | auto_fix_test_sizes.py:357 | TestFileSplitter._determine... | `ABC`, `ABORT` |
| `user\_id` | session_manager.py:65 | SessionManager.create_session | `ABC`, `ABORT` |
| `user\_ids` | seed_staging_data.py:357 | StagingDataSeeder.generate_... | `ABC`, `ABORT` |
| `user\_info` | test_auth_oauth_errors.py:298 | TestOAuthErrorHandling.test... | `ABC`, `ABORT` |
| `user\_initiated` | audit_factory.py:107 | AuditLogFactory.create_logo... | `ABC`, `ABORT` |
| `user\_intent` | metadata_header_generator.py:92 | MetadataHeaderGenerator.gen... | `ABC`, `ABORT` |
| `user\_not\_found` | auth_service.py:488 | AuthService.confirm_passwor... | `ABC`, `ABORT` |
| `user\_service` | fix_e2e_tests_comprehensive.py:71 | E2ETestFixer._get_common_fi... | `ABC`, `ABORT` |
| `user\_tier` | seed_staging_data.py:322 | StagingDataSeeder._create_m... | `ABC`, `ABORT` |
| `UserFactory` | __init__.py:13 | module | `ABC`, `ABORT` |
| `UserMessagePayload` | deduplicate_types.py:91 | TypeDeduplicator._setup_web... | `ABC`, `ABORT` |
| `username` | environment_validator_database.py:71 | DatabaseValidator._parse_po... | `ABC`, `ABORT` |
| `users` | seed_staging_data.py:53 | StagingDataSeeder.__init__ | `ABC`, `ABORT` |
| `uses` | workflow_validator.py:122 | WorkflowValidator._validate... | `ABC`, `ABORT` |
| `uses\_mocks` | categorize_tests.py:85 | TestCategorizer._initialize... | `ABC`, `ABORT` |
| `uses\_real\_clickhouse` | add_test_markers.py:46 | TestMarkerAdder.get_markers... | `ABC`, `ABORT` |
| `uses\_real\_database` | add_test_markers.py:42 | TestMarkerAdder.get_markers... | `ABC`, `ABORT` |
| `uses\_real\_llm` | add_test_markers.py:40 | TestMarkerAdder.get_markers... | `ABC`, `ABORT` |
| `uses\_real\_redis` | add_test_markers.py:44 | TestMarkerAdder.get_markers... | `ABC`, `ABORT` |
| `UTC` | enhanced_fix_datetime_deprecation.py:53 | _update_from_import | `ABC`, `ABORT` |
| `util` | auto_fix_test_violations.py:448 | TestFileSplitter._extract_u... | `ABC`, `ABORT` |
| `utilities` | auto_fix_test_sizes.py:274 | TestFileSplitter.split_over... | `ABC`, `ABORT` |
| `uvicorn` | config_setup_scripts.py:143 | test_python_imports | `ABC`, `ABORT` |
| `valid` | auth_routes.py:208 | verify_auth | `ABC`, `ABORT` |
| `valid\_format` | environment_validator_core.py:147 | EnvironmentValidatorCore._v... | `ABC`, `ABORT` |
| `valid\_secret` | test_security.py:141 | TestSQLInjectionPrevention.... | `ABC`, `ABORT` |
| `VALIDATE` | startup_optimizer.py:48 | StartupPhase | `ABC`, `ABORT` |
| `validate` | act_wrapper.py:212 | add_subcommands | `ABC`, `ABORT` |
| `validate\_` | code_review_ai_detector.py:48 | CodeReviewAIDetector._check... | `ABC`, `ABORT` |
| `validate\_all` | test_launcher.py:276 | TestDevLauncher.test_check_... | `ABC`, `ABORT` |
| `validate\_token` | e2e_import_fixer_comprehensive.py:103 | E2EImportFixer.__init__ | `ABC`, `ABORT` |
| `validate\_token\_jwt` | e2e_import_fixer_comprehensive.py:103 | E2EImportFixer.__init__ | `ABC`, `ABORT` |
| `validated` | cache_warmer.py:173 | CacheWarmer._warm_secrets_c... | `ABC`, `ABORT` |
| `validated\_data` | auto_decompose_functions.py:280 | FunctionDecomposer._suggest... | `ABC`, `ABORT` |
| `validation` | auto_decompose_functions.py:170 | FunctionDecomposer._identif... | `ABC`, `ABORT` |
| `validation\_` | secret_cache.py:209 | SecretCache.get_cache_stats | `ABC`, `ABORT` |
| `validation\_entries` | secret_cache.py:213 | SecretCache.get_cache_stats | `ABC`, `ABORT` |
| `validation\_passed` | validate_agent_tests.py:293 | AgentTestValidator.export_j... | `ABC`, `ABORT` |
| `validation\_processing` | auto_decompose_functions.py:297 | FunctionDecomposer._suggest... | `ABC`, `ABORT` |
| `validation\_result` | secret_cache.py:111 | SecretCache.validate_cached... | `ABC`, `ABORT` |
| `validation\_summary` | environment_validator.py:395 | EnvironmentValidator.genera... | `ABC`, `ABORT` |
| `validation\_test` | test_example_message_flow.py:284 | ExampleMessageFlowTestRunne... | `ABC`, `ABORT` |
| `ValidationConstants` | auth_constants_migration.py:107 | AuthConstantsMigrator.__init__ | `ABC`, `ABORT` |
| `ValidationResult` | validate_type_deduplication.py:83 | TypeDeduplicationValidator.... | `ABC`, `ABORT` |
| `validator` | metadata_enabler.py:85 | MetadataTrackingEnabler.get... | `ABC`, `ABORT` |
| `validator\_exists` | status_manager.py:82 | StatusManager.get_status | `ABC`, `ABORT` |
| `validator\_script\_exists` | metadata_enabler.py:125 | MetadataTrackingEnabler._ca... | `ABC`, `ABORT` |
| `ValidatorGenerator` | __init__.py:20 | module | `ABC`, `ABORT` |
| `value` | architecture_metrics.py:151 | ArchitectureMetrics._get_fi... | `ABC`, `ABORT` |
| `value\_error` | analyze_failures.py:41 | TestFailureAnalyzer | `ABC`, `ABORT` |
| `value\_length` | environment_validator_core.py:146 | EnvironmentValidatorCore._v... | `ABC`, `ABORT` |
| `value\_score` | business_value_test_index.py:75 | BusinessValueTestIndexer.__... | `ABC`, `ABORT` |
| `ValueError` | analyze_failures.py:41 | TestFailureAnalyzer | `ABC`, `ABORT` |
| `variables` | environment_validator_core.py:28 | EnvironmentValidatorCore.va... | `ABC`, `ABORT` |
| `variables\_count` | environment_validator_core.py:116 | EnvironmentValidatorCore._v... | `ABC`, `ABORT` |
| `vendor` | core.py:86 | ComplianceConfig._get_skip_... | `ABC`, `ABORT` |
| `venv` | architecture_metrics.py:267 | ArchitectureMetrics._should... | `ABC`, `ABORT` |
| `venv\_test` | auto_fix_test_violations.py:103 | TestFileAnalyzer.find_test_... | `ABC`, `ABORT` |
| `verbose` | config.py:158 | LauncherConfig.from_args | `ABC`, `ABORT` |
| `verbose\_background` | config.py:168 | LauncherConfig.from_args | `ABC`, `ABORT` |
| `verbose\_tables` | config.py:169 | LauncherConfig.from_args | `ABC`, `ABORT` |
| `verified\_email` | user_factory.py:86 | UserFactory.create_oauth_us... | `ABC`, `ABORT` |
| `VERIFY` | startup_optimizer.py:51 | StartupPhase | `ABC`, `ABORT` |
| `verify` | ultra_thinking_analyzer.py:171 | UltraThinkingAnalyzer._iden... | `ABC`, `ABORT` |
| `verify\_exp` | token_factory.py:175 | TokenFactory.decode_token | `ABC`, `ABORT` |
| `verify\_signature` | jwt_handler.py:140 | JWTHandler.extract_user_id | `ABC`, `ABORT` |
| `version` | main.py:58 | AuthServiceHealthInterface.... | `ABC`, `ABORT` |
| `versions` | create_staging_secrets.py:70 | create_secret | `ABC`, `ABORT` |
| `view` | project_test_validator.py:172 | MockComponentVisitor.visit_... | `ABC`, `ABORT` |
| `Violation` | __init__.py:13 | module | `ABC`, `ABORT` |
| `violation\_counts` | architecture_dashboard_html.py:74 | DashboardHTMLComponents._ge... | `ABC`, `ABORT` |
| `violation\_limit` | check_architecture_compliance.py:26 | _create_enforcer | `ABC`, `ABORT` |
| `violation\_type` | auto_fix_test_sizes.py:627 | TestSizeFixer.fix_all_viola... | `ABC`, `ABORT` |
| `violation\_type\_breakdown` | remove_test_stubs.py:262 | TestStubDetector.generate_r... | `ABC`, `ABORT` |
| `violation\_types` | check_schema_imports.py:292 | SchemaImportAnalyzer.analyz... | `ABC`, `ABORT` |
| `violations` | analyze_critical_paths.py:56 | module | `ABC`, `ABORT` |
| `virtual\_env` | environment_validator_dependencies.py:76 | DependencyValidator._valida... | `ABC`, `ABORT` |
| `virtualenv` | core.py:85 | ComplianceConfig._get_skip_... | `ABC`, `ABORT` |
| `vm\_stat` | system_diagnostics.py:163 | SystemDiagnostics._check_un... | `ABC`, `ABORT` |
| `vscode` | dev_launcher_config.py:105 | _check_platform_emoji_support | `ABC`, `ABORT` |
| `vue` | agent_tracking_helper.py:32 | AgentTrackingHelper | `ABC`, `ABORT` |
| `vulnerabilities` | generate_security_report.py:76 | _build_vulnerabilities_section | `ABC`, `ABORT` |
| `vulnerability\_count` | generate_security_report.py:56 | _get_security_status_badge | `ABC`, `ABORT` |
| `WAIT` | startup_validator.py:26 | StartupValidator.verify_bac... | `ABC`, `ABORT` |
| `wait\_for\_all` | test_launcher.py:390 | TestIntegration.test_full_l... | `ABC`, `ABORT` |
| `waiting` | force_cancel_workflow.py:67 | _display_and_find_stuck_runs | `ABC`, `ABORT` |
| `warm\_cache` | startup_optimizer.py:617 | create_prepare_phase_steps | `ABC`, `ABORT` |
| `WARN` | launcher.py:244 | DevLauncher._terminate_all_... | `ABC`, `ABORT` |
| `warn` | enforce_limits.py:228 | create_argument_parser | `ABC`, `ABORT` |
| `WARNING` | test_env.py:165 | EnvironmentPresets.unit_tes... | `ABC`, `ABORT` |
| `Warning` | unified_import_manager.py:162 | UnifiedImportManager._check... | `ABC`, `ABORT` |
| `warning` | main.py:337 | health_ready | `ABC`, `ABORT` |
| `WARNING\_REPORT` | emergency_boundary_actions.py:259 | EmergencyActionSystem._crea... | `ABC`, `ABORT` |
| `WARNINGS` | check_netra_backend_imports.py:267 | ImportAnalyzer.generate_report | `ABC`, `ABORT` |
| `warnings` | reporter_stats.py:48 | StatisticsCalculator._get_f... | `ABC`, `ABORT` |
| `watch` | workflow_introspection.py:209 | WorkflowIntrospector.watch_run | `ABC`, `ABORT` |
| `watch\_boundaries` | enhance_dev_launcher_boundaries.py:20 | enhance_launcher_config | `ABC`, `ABORT` |
| `WATCHPACK\_POLLING` | dev_launcher_config.py:171 | setup_frontend_environment | `ABC`, `ABORT` |
| `wave` | unicode_utils.py:84 | module | `ABC`, `ABORT` |
| `weak\_secrets` | environment_validator.py:140 | EnvironmentValidator._valid... | `ABC`, `ABORT` |
| `weak\_secrets\_detected` | environment_validator.py:414 | EnvironmentValidator.genera... | `ABC`, `ABORT` |
| `web` | audit_factory.py:157 | AuditLogFactory.create_sess... | `ABC`, `ABORT` |
| `web\_` | session_factory.py:93 | SessionFactory.create_web_s... | `ABC`, `ABORT` |
| `webpack` | cleanup_test_processes.py:70 | find_test_processes | `ABC`, `ABORT` |
| `WEBSOCKET` | launcher.py:450 | DevLauncher._validate_webso... | `ABC`, `ABORT` |
| `WebSocket` | fix_frontend_tests.py:84 | _add_fetch_mock_if_needed | `ABC`, `ABORT` |
| `websocket` | auto_fix_test_sizes.py:342 | TestFileSplitter._determine... | `ABC`, `ABORT` |
| `websocket\_config` | test_websocket_dev_mode.py:96 | WebSocketDevModeTest.test_c... | `ABC`, `ABORT` |
| `websocket\_connection` | test_websocket_dev_mode.py:43 | WebSocketDevModeTest.__init__ | `ABC`, `ABORT` |
| `websocket\_endpoint` | e2e_import_fixer_comprehensive.py:104 | E2EImportFixer.__init__ | `ABC`, `ABORT` |
| `websocket\_event` | scan_string_literals.py:91 | StringLiteralCategorizer | `ABC`, `ABORT` |
| `websocket\_manager` | fix_e2e_tests_comprehensive.py:65 | E2ETestFixer._get_common_fi... | `ABC`, `ABORT` |
| `WEBSOCKET\_PORT` | launcher.py:386 | DevLauncher._set_env_var_de... | `ABC`, `ABORT` |
| `websocket\_service` | comprehensive_import_scanner.py:155 | ComprehensiveImportScanner.... | `ABC`, `ABORT` |
| `WebSocketConnectionManager` | validate_type_deduplication.py:58 | TypeDeduplicationValidator.... | `ABC`, `ABORT` |
| `WebSocketError` | deduplicate_types.py:90 | TypeDeduplicator._setup_web... | `ABC`, `ABORT` |
| `WebSocketManager` | categorize_tests.py:74 | TestCategorizer._get_integr... | `ABC`, `ABORT` |
| `WebSocketMessage` | deduplicate_types.py:88 | TypeDeduplicator._setup_web... | `ABC`, `ABORT` |
| `WebSocketMessageType` | deduplicate_types.py:89 | TypeDeduplicator._setup_web... | `ABC`, `ABORT` |
| `WebSocketProvider` | fix_frontend_tests.py:14 | _should_skip_file | `ABC`, `ABORT` |
| `weekly` | seed_staging_data.py:232 | StagingDataSeeder._generate... | `ABC`, `ABORT` |
| `weekly\_summary\_report` | config_manager.py:48 | ConfigurationManager._get_m... | `ABC`, `ABORT` |
| `which` | validate_staging_config.py:364 | check_gcp_configuration | `ABC`, `ABORT` |
| `white` | workflow_validator.py:187 | WorkflowValidator._display_... | `ABC`, `ABORT` |
| `widget` | project_test_validator.py:172 | MockComponentVisitor.visit_... | `ABC`, `ABORT` |
| `Windows` | service_discovery.py:103 | ServiceDiscovery.is_service... | `ABC`, `ABORT` |
| `windows` | dependency_services.py:43 | get_os_specific_pg_instruct... | `ABC`, `ABORT` |
| `wip\_items` | status_types.py:170 | ReportSections | `ABC`, `ABORT` |
| `wmic` | recovery_manager.py:45 | RecoveryManager._get_system... | `ABC`, `ABORT` |
| `worker` | auth_service.py:371 | AuthService._get_service_name | `ABC`, `ABORT` |
| `Workflow` | workflow_introspection.py:241 | OutputFormatter.display_run... | `ABC`, `ABORT` |
| `workflow` | act_wrapper.py:220 | add_run_command | `ABC`, `ABORT` |
| `workflow\_call` | test_workflows_with_act.py:148 | WorkflowTester.test_workflo... | `ABC`, `ABORT` |
| `workflow\_control` | validate_workflow_config.py:26 | validate_config_structure | `ABC`, `ABORT` |
| `workflow\_runs` | cleanup_workflow_runs.py:63 | get_workflow_runs | `ABC`, `ABORT` |
| `workflowName` | workflow_introspection.py:123 | WorkflowIntrospector.get_re... | `ABC`, `ABORT` |
| `workflows` | act_wrapper.py:23 | ACTWrapper.__init__ | `ABC`, `ABORT` |
| `Workload` | generate-json-schema.py:19 | main | `ABC`, `ABORT` |
| `workload\_analysis` | setup_assistant.py:26 | _get_assistant_capabilities | `ABC`, `ABORT` |
| `worst\_offenders` | architecture_metrics.py:39 | ArchitectureMetrics.calcula... | `ABC`, `ABORT` |
| `worst\_violations` | function_complexity_linter.py:170 | FunctionComplexityLinter.ge... | `ABC`, `ABORT` |
| `write` | auth_routes.py:355 | dev_login | `ABC`, `ABORT` |
| `write\_backend\_info` | test_launcher.py:316 | TestDevLauncher.disabled_te... | `ABC`, `ABORT` |
| `write\_frontend\_info` | test_launcher.py:392 | TestIntegration.test_full_l... | `ABC`, `ABORT` |
| `wrong` | test_auth_token_security.py:394 | TestJWTSecurityBoundaries.t... | `ABC`, `ABORT` |
| `wrongpass` | test_security.py:351 | TestSecurityLogging.test_fa... | `ABC`, `ABORT` |
| `ws` | auto_fix_test_sizes.py:342 | TestFileSplitter._determine... | `ABC`, `ABORT` |
| `WS\_BASE\_URL` | test_staging.py:33 | setup_staging_env | `ABC`, `ABORT` |
| `ws\_manager` | fast_import_checker.py:366 | scan_e2e_tests | `ABC`, `ABORT` |
| `ws\_url` | dev_launcher_config.py:158 | setup_frontend_environment | `ABC`, `ABORT` |
| `WT\_SESSION` | dev_launcher_config.py:103 | _check_platform_emoji_support | `ABC`, `ABORT` |
| `xdist` | test_backend.py:155 | _check_all_python_packages | `ABC`, `ABORT` |
| `xml` | coverage_config.py:70 | CoverageConfig.get_coverage... | `ABC`, `ABORT` |
| `xss\_payloads` | test_security.py:56 | security_test_payloads | `ABC`, `ABORT` |
| `XXX` | secret_validator.py:76 | SecretValidator._is_invalid... | `ABC`, `ABORT` |
| `xxx` | secret_validator.py:76 | SecretValidator._is_invalid... | `ABC`, `ABORT` |
| `XXXms` | log_buffer.py:163 | LogBuffer._normalize_message | `ABC`, `ABORT` |
| `yaml` | agent_tracking_helper.py:47 | AgentTrackingHelper | `ABC`, `ABORT` |
| `yarn` | dependency_checker.py:27 | DependencyType | `ABC`, `ABORT` |
| `yellow` | act_wrapper.py:136 | ACTWrapper._create_workflow... | `ABC`, `ABORT` |
| `YES` | dev_launcher_monitoring.py:146 | print_configuration_summary | `ABC`, `ABORT` |
| `yes` | cleanup_generated_files.py:218 | get_user_confirmation | `ABC`, `ABORT` |
| `YOUR\_` | secret_validator.py:74 | SecretValidator._is_invalid... | `ABC`, `ABORT` |
| `your\_` | secret_validator.py:74 | SecretValidator._is_invalid... | `ABC`, `ABORT` |

### Usage Examples

- **scripts\analyze_test_overlap.py:95** - `TestOverlapAnalyzer._collect_tests`
- **scripts\function_complexity_linter.py:64** - `FunctionComplexityLinter._is_special_function`
- **scripts\architecture_scanner.py:207** - `ArchitectureScanner._check_function_types`

---

## 🔗 Navigation

- 🏠 [Back to Main Index](../string_literals_index.md)
- 📂 [Browse Other Categories](./)

### Related Categories

- 🛤️ [Paths](paths.md) - Configuration often contains paths and URLs

---

*This is the detailed documentation for the `configuration` category.*
*For the complete system overview, see the [Main String Literals Index](../string_literals_index.md).*