# Test Environment Hardening Migration Report
**Total Files to Migrate:** 142

## Files with Direct os.environ Patches

**Total Occurrences:** 722

### E2E Tests (32 files)

#### tests\e2e\test_cloud_sql_proxy_regression.py
- **Occurrences:** 4
- **Lines:**
  - Line 127: `@patch.dict(os.environ, {...`
  - Line 149: `@patch.dict(os.environ, {...`
  - Line 175: `@patch.dict(os.environ, {...`
  - ... and 1 more

#### tests\e2e\test_configuration_e2e.py
- **Occurrences:** 15
- **Lines:**
  - Line 50: `with patch.dict(os.environ, staging_env, clear=True):...`
  - Line 71: `with patch.dict(os.environ, env_without_db_url, clear=True):...`
  - Line 85: `with patch.dict(os.environ, staging_env, clear=True):...`
  - ... and 12 more

#### tests\e2e\test_cors_dynamic_ports.py
- **Occurrences:** 5
- **Lines:**
  - Line 172: `#         with patch.dict(os.environ, {"ENVIRONMENT": "testing", "CORS_ORIGINS":...`
  - Line 677: `#         with patch.dict(os.environ, {"ENVIRONMENT": "staging", "CORS_ORIGINS":...`
  - Line 707: `#         with patch.dict(os.environ, {"ENVIRONMENT": "development"}):...`
  - ... and 2 more

#### tests\e2e\test_cors_e2e.py
- **Occurrences:** 7
- **Lines:**
  - Line 224: `with patch.dict(os.environ, {"ENVIRONMENT": "staging"}):...`
  - Line 255: `with patch.dict(os.environ, {"ENVIRONMENT": "staging"}):...`
  - Line 279: `with patch.dict(os.environ, {"ENVIRONMENT": "production", "CORS_ORIGINS": ""}):...`
  - ... and 4 more

#### tests\e2e\test_critical_auth_service_cascade_failures.py
- **Occurrences:** 6
- **Lines:**
  - Line 59: `with patch.dict(os.environ, auth_service_down_env):...`
  - Line 121: `with patch.dict(os.environ, startup_failure_env, clear=False):...`
  - Line 181: `with patch.dict(os.environ, deployment_env):...`
  - ... and 3 more

#### tests\e2e\test_database_postgres_connectivity_e2e.py
- **Occurrences:** 10
- **Lines:**
  - Line 60: `with patch.dict(os.environ, postgres_error_env):...`
  - Line 96: `with patch.dict(os.environ, postgres_error_env):...`
  - Line 134: `with patch.dict(os.environ, postgres_error_env):...`
  - ... and 7 more

#### tests\e2e\test_deployment_configuration_validation.py
- **Occurrences:** 7
- **Lines:**
  - Line 221: `with patch.dict(os.environ, local_overrides):...`
  - Line 265: `with patch.dict(os.environ, staging_env_without_clickhouse, clear=True):...`
  - Line 301: `with patch.dict(os.environ, staging_env_without_redis, clear=True):...`
  - ... and 4 more

#### tests\e2e\test_deployment_scaling_validation.py
- **Occurrences:** 1
- **Lines:**
  - Line 185: `with patch.dict(os.environ, version_env, clear=False):...`

#### tests\e2e\test_oauth_configuration.py
- **Occurrences:** 15
- **Lines:**
  - Line 62: `with mock.patch.dict(os.environ, mock_env_vars, clear=True):...`
  - Line 78: `with mock.patch.dict(os.environ, empty_env_vars, clear=True):...`
  - Line 91: `with mock.patch.dict(os.environ, placeholder_env_vars, clear=True):...`
  - ... and 12 more

#### tests\e2e\test_service_availability_integration.py
- **Occurrences:** 3
- **Lines:**
  - Line 131: `with patch.dict(os.environ, {'USE_REAL_SERVICES': 'true'}):...`
  - Line 135: `with patch.dict(os.environ, {'TEST_USE_REAL_LLM': 'true'}):...`
  - Line 139: `with patch.dict(os.environ, {'USE_REAL_SERVICES': 'TRUE'}):...`

#### tests\e2e\test_staging_auth_config.py
- **Occurrences:** 3
- **Lines:**
  - Line 25: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, staging_env):...`
  - Line 88: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, staging_env):...`
  - Line 126: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, production_env):...`

#### tests\e2e\test_staging_database_config_migration.py
- **Occurrences:** 1
- **Lines:**
  - Line 182: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {'ENVIRONMENT': 'staging'}):...`

#### tests\e2e\test_staging_database_name_misconfiguration.py
- **Occurrences:** 1
- **Lines:**
  - Line 72: `# Removed problematic line: with mock.patch.dict(os.environ, staging_env, clear=...`

#### tests\e2e\test_staging_deployment_errors.py
- **Occurrences:** 4
- **Lines:**
  - Line 69: `with patch.dict(os.environ, {"DATABASE_URL": staging_url, "ENVIRONMENT": "stagin...`
  - Line 99: `with patch.dict(os.environ, {"ENVIRONMENT": "staging", "CLICKHOUSE_URL": ""}):...`
  - Line 265: `with patch.dict(os.environ, {"DATABASE_URL": "postgresql://fake:fake@fake/fake"}...`
  - ... and 1 more

#### tests\e2e\test_staging_import_and_config_issues.py
- **Occurrences:** 5
- **Lines:**
  - Line 116: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {'ENVIRONMENT': environment}...`
  - Line 136: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {'ENVIRONMENT': 'staging'}):...`
  - Line 276: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {'ENVIRONMENT': 'staging'}):...`
  - ... and 2 more

#### tests\integration\test_deployment_config_e2e.py
- **Occurrences:** 3
- **Lines:**
  - Line 111: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, { ))...`
  - Line 125: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, { ))...`
  - Line 190: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, self.test_env_vars):...`

#### tests\e2e\test_cloud_sql_proxy_regression.py
- **Occurrences:** 4
- **Lines:**
  - Line 127: `@patch.dict(os.environ, {...`
  - Line 149: `@patch.dict(os.environ, {...`
  - Line 175: `@patch.dict(os.environ, {...`
  - ... and 1 more

#### tests\e2e\test_configuration_e2e.py
- **Occurrences:** 15
- **Lines:**
  - Line 50: `with patch.dict(os.environ, staging_env, clear=True):...`
  - Line 71: `with patch.dict(os.environ, env_without_db_url, clear=True):...`
  - Line 85: `with patch.dict(os.environ, staging_env, clear=True):...`
  - ... and 12 more

#### tests\e2e\test_cors_dynamic_ports.py
- **Occurrences:** 5
- **Lines:**
  - Line 172: `#         with patch.dict(os.environ, {"ENVIRONMENT": "testing", "CORS_ORIGINS":...`
  - Line 677: `#         with patch.dict(os.environ, {"ENVIRONMENT": "staging", "CORS_ORIGINS":...`
  - Line 707: `#         with patch.dict(os.environ, {"ENVIRONMENT": "development"}):...`
  - ... and 2 more

#### tests\e2e\test_cors_e2e.py
- **Occurrences:** 7
- **Lines:**
  - Line 224: `with patch.dict(os.environ, {"ENVIRONMENT": "staging"}):...`
  - Line 255: `with patch.dict(os.environ, {"ENVIRONMENT": "staging"}):...`
  - Line 279: `with patch.dict(os.environ, {"ENVIRONMENT": "production", "CORS_ORIGINS": ""}):...`
  - ... and 4 more

#### tests\e2e\test_critical_auth_service_cascade_failures.py
- **Occurrences:** 6
- **Lines:**
  - Line 59: `with patch.dict(os.environ, auth_service_down_env):...`
  - Line 121: `with patch.dict(os.environ, startup_failure_env, clear=False):...`
  - Line 181: `with patch.dict(os.environ, deployment_env):...`
  - ... and 3 more

#### tests\e2e\test_database_postgres_connectivity_e2e.py
- **Occurrences:** 10
- **Lines:**
  - Line 60: `with patch.dict(os.environ, postgres_error_env):...`
  - Line 96: `with patch.dict(os.environ, postgres_error_env):...`
  - Line 134: `with patch.dict(os.environ, postgres_error_env):...`
  - ... and 7 more

#### tests\e2e\test_deployment_configuration_validation.py
- **Occurrences:** 7
- **Lines:**
  - Line 221: `with patch.dict(os.environ, local_overrides):...`
  - Line 265: `with patch.dict(os.environ, staging_env_without_clickhouse, clear=True):...`
  - Line 301: `with patch.dict(os.environ, staging_env_without_redis, clear=True):...`
  - ... and 4 more

#### tests\e2e\test_deployment_scaling_validation.py
- **Occurrences:** 1
- **Lines:**
  - Line 185: `with patch.dict(os.environ, version_env, clear=False):...`

#### tests\e2e\test_oauth_configuration.py
- **Occurrences:** 15
- **Lines:**
  - Line 62: `with mock.patch.dict(os.environ, mock_env_vars, clear=True):...`
  - Line 78: `with mock.patch.dict(os.environ, empty_env_vars, clear=True):...`
  - Line 91: `with mock.patch.dict(os.environ, placeholder_env_vars, clear=True):...`
  - ... and 12 more

#### tests\e2e\test_service_availability_integration.py
- **Occurrences:** 3
- **Lines:**
  - Line 131: `with patch.dict(os.environ, {'USE_REAL_SERVICES': 'true'}):...`
  - Line 135: `with patch.dict(os.environ, {'TEST_USE_REAL_LLM': 'true'}):...`
  - Line 139: `with patch.dict(os.environ, {'USE_REAL_SERVICES': 'TRUE'}):...`

#### tests\e2e\test_staging_auth_config.py
- **Occurrences:** 3
- **Lines:**
  - Line 25: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, staging_env):...`
  - Line 88: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, staging_env):...`
  - Line 126: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, production_env):...`

#### tests\e2e\test_staging_database_config_migration.py
- **Occurrences:** 1
- **Lines:**
  - Line 182: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {'ENVIRONMENT': 'staging'}):...`

#### tests\e2e\test_staging_database_name_misconfiguration.py
- **Occurrences:** 1
- **Lines:**
  - Line 72: `# Removed problematic line: with mock.patch.dict(os.environ, staging_env, clear=...`

#### tests\e2e\test_staging_deployment_errors.py
- **Occurrences:** 4
- **Lines:**
  - Line 69: `with patch.dict(os.environ, {"DATABASE_URL": staging_url, "ENVIRONMENT": "stagin...`
  - Line 99: `with patch.dict(os.environ, {"ENVIRONMENT": "staging", "CLICKHOUSE_URL": ""}):...`
  - Line 265: `with patch.dict(os.environ, {"DATABASE_URL": "postgresql://fake:fake@fake/fake"}...`
  - ... and 1 more

#### tests\e2e\test_staging_import_and_config_issues.py
- **Occurrences:** 5
- **Lines:**
  - Line 116: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {'ENVIRONMENT': environment}...`
  - Line 136: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {'ENVIRONMENT': 'staging'}):...`
  - Line 276: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {'ENVIRONMENT': 'staging'}):...`
  - ... and 2 more

#### tests\integration\test_deployment_config_e2e.py
- **Occurrences:** 3
- **Lines:**
  - Line 111: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, { ))...`
  - Line 125: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, { ))...`
  - Line 190: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, self.test_env_vars):...`

### INTEGRATION Tests (32 files)

#### dev_launcher\tests\test_launcher_integration.py
- **Occurrences:** 1
- **Lines:**
  - Line 301: `with patch.dict(os.environ, {'NETRA_ENV': env}):...`

#### netra_backend\tests\auth_integration\test_jwt_secret_consistency.py
- **Occurrences:** 12
- **Lines:**
  - Line 26: `with patch.dict(os.environ, {...`
  - Line 43: `with patch.dict(os.environ, {...`
  - Line 61: `with patch.dict(os.environ, {...`
  - ... and 9 more

#### netra_backend\tests\critical\test_staging_integration_flow.py
- **Occurrences:** 1
- **Lines:**
  - Line 58: `with patch.dict(os.environ, env_vars):...`

#### netra_backend\tests\integration\critical_paths\test_staging_environment_imports.py
- **Occurrences:** 3
- **Lines:**
  - Line 238: `with mock.patch.dict(os.environ, {...`
  - Line 246: `with mock.patch.dict(os.environ, {...`
  - Line 253: `with mock.patch.dict(os.environ, {...`

#### tests\integration\test_alpine_regular_switching.py
- **Occurrences:** 4
- **Lines:**
  - Line 827: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {"PROJECT_ROOT": str(temp_pa...`
  - Line 1035: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {"FORCE_ALPINE": "true", "CI...`
  - Line 1046: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {"FORCE_ALPINE": "false", "C...`
  - ... and 1 more

#### tests\integration\test_auth_url_configuration.py
- **Occurrences:** 13
- **Lines:**
  - Line 50: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {'ENVIRONMENT': env}, clear=...`
  - Line 69: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {'ENVIRONMENT': env}, clear=...`
  - Line 100: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {'ENVIRONMENT': env}, clear=...`
  - ... and 10 more

#### tests\integration\test_configuration_access_database_issues.py
- **Occurrences:** 2
- **Lines:**
  - Line 160: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, config_vars, clear=False):...`
  - Line 406: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, test_vars, clear=False):...`

#### tests\integration\test_cors_comprehensive.py
- **Occurrences:** 23
- **Lines:**
  - Line 171: `with patch.dict(os.environ, {"ENVIRONMENT": "development"}):...`
  - Line 182: `with patch.dict(os.environ, {"ENVIRONMENT": "staging"}):...`
  - Line 191: `with patch.dict(os.environ, {"ENVIRONMENT": "production"}):...`
  - ... and 20 more

#### tests\integration\test_cors_staging_specific.py
- **Occurrences:** 12
- **Lines:**
  - Line 42: `with patch.dict(os.environ, {"ENVIRONMENT": "staging"}):...`
  - Line 63: `with patch.dict(os.environ, {**clear_env, **env_var}, clear=False):...`
  - Line 70: `with patch.dict(os.environ, {"ENVIRONMENT": "staging"}):...`
  - ... and 9 more

#### tests\integration\test_cross_service_config_fixtures.py
- **Occurrences:** 1
- **Lines:**
  - Line 175: `with patch.dict(os.environ, test_env, clear=False):...`

#### tests\integration\test_cross_service_url_alignment.py
- **Occurrences:** 11
- **Lines:**
  - Line 59: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {'ENVIRONMENT': env}, clear=...`
  - Line 92: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {'ENVIRONMENT': env}, clear=...`
  - Line 114: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {'ENVIRONMENT': env}, clear=...`
  - ... and 8 more

#### tests\integration\test_dev_environment_initialization.py
- **Occurrences:** 6
- **Lines:**
  - Line 105: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, self.test_env, clear=False):...`
  - Line 413: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, self.test_env, clear=False):...`
  - Line 468: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, self.test_env, clear=False):...`
  - ... and 3 more

#### tests\integration\test_gcp_staging_config_validation.py
- **Occurrences:** 2
- **Lines:**
  - Line 294: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {}, clear=True):...`
  - Line 548: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {}, clear=True):  # Simulate...`

#### tests\integration\test_jwt_secret_sync.py
- **Occurrences:** 8
- **Lines:**
  - Line 87: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, { ))...`
  - Line 97: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, { ))...`
  - Line 107: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, { ))...`
  - ... and 5 more

#### tests\integration\test_startup_system_performance.py
- **Occurrences:** 1
- **Lines:**
  - Line 94: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, essential_env, clear=False):...`

#### tests\integration\test_workflow_verification_l2.py
- **Occurrences:** 2
- **Lines:**
  - Line 478: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {"GITHUB_TOKEN": "env_token_...`
  - Line 485: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {}, clear=True):...`

#### dev_launcher\tests\test_launcher_integration.py
- **Occurrences:** 1
- **Lines:**
  - Line 301: `with patch.dict(os.environ, {'NETRA_ENV': env}):...`

#### netra_backend\tests\auth_integration\test_jwt_secret_consistency.py
- **Occurrences:** 12
- **Lines:**
  - Line 26: `with patch.dict(os.environ, {...`
  - Line 43: `with patch.dict(os.environ, {...`
  - Line 61: `with patch.dict(os.environ, {...`
  - ... and 9 more

#### netra_backend\tests\critical\test_staging_integration_flow.py
- **Occurrences:** 1
- **Lines:**
  - Line 58: `with patch.dict(os.environ, env_vars):...`

#### netra_backend\tests\integration\critical_paths\test_staging_environment_imports.py
- **Occurrences:** 3
- **Lines:**
  - Line 238: `with mock.patch.dict(os.environ, {...`
  - Line 246: `with mock.patch.dict(os.environ, {...`
  - Line 253: `with mock.patch.dict(os.environ, {...`

#### tests\integration\test_alpine_regular_switching.py
- **Occurrences:** 4
- **Lines:**
  - Line 827: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {"PROJECT_ROOT": str(temp_pa...`
  - Line 1035: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {"FORCE_ALPINE": "true", "CI...`
  - Line 1046: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {"FORCE_ALPINE": "false", "C...`
  - ... and 1 more

#### tests\integration\test_auth_url_configuration.py
- **Occurrences:** 13
- **Lines:**
  - Line 50: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {'ENVIRONMENT': env}, clear=...`
  - Line 69: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {'ENVIRONMENT': env}, clear=...`
  - Line 100: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {'ENVIRONMENT': env}, clear=...`
  - ... and 10 more

#### tests\integration\test_configuration_access_database_issues.py
- **Occurrences:** 2
- **Lines:**
  - Line 160: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, config_vars, clear=False):...`
  - Line 406: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, test_vars, clear=False):...`

#### tests\integration\test_cors_comprehensive.py
- **Occurrences:** 23
- **Lines:**
  - Line 171: `with patch.dict(os.environ, {"ENVIRONMENT": "development"}):...`
  - Line 182: `with patch.dict(os.environ, {"ENVIRONMENT": "staging"}):...`
  - Line 191: `with patch.dict(os.environ, {"ENVIRONMENT": "production"}):...`
  - ... and 20 more

#### tests\integration\test_cors_staging_specific.py
- **Occurrences:** 12
- **Lines:**
  - Line 42: `with patch.dict(os.environ, {"ENVIRONMENT": "staging"}):...`
  - Line 63: `with patch.dict(os.environ, {**clear_env, **env_var}, clear=False):...`
  - Line 70: `with patch.dict(os.environ, {"ENVIRONMENT": "staging"}):...`
  - ... and 9 more

#### tests\integration\test_cross_service_config_fixtures.py
- **Occurrences:** 1
- **Lines:**
  - Line 175: `with patch.dict(os.environ, test_env, clear=False):...`

#### tests\integration\test_cross_service_url_alignment.py
- **Occurrences:** 11
- **Lines:**
  - Line 59: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {'ENVIRONMENT': env}, clear=...`
  - Line 92: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {'ENVIRONMENT': env}, clear=...`
  - Line 114: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {'ENVIRONMENT': env}, clear=...`
  - ... and 8 more

#### tests\integration\test_dev_environment_initialization.py
- **Occurrences:** 6
- **Lines:**
  - Line 105: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, self.test_env, clear=False):...`
  - Line 413: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, self.test_env, clear=False):...`
  - Line 468: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, self.test_env, clear=False):...`
  - ... and 3 more

#### tests\integration\test_gcp_staging_config_validation.py
- **Occurrences:** 2
- **Lines:**
  - Line 294: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {}, clear=True):...`
  - Line 548: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {}, clear=True):  # Simulate...`

#### tests\integration\test_jwt_secret_sync.py
- **Occurrences:** 8
- **Lines:**
  - Line 87: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, { ))...`
  - Line 97: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, { ))...`
  - Line 107: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, { ))...`
  - ... and 5 more

#### tests\integration\test_startup_system_performance.py
- **Occurrences:** 1
- **Lines:**
  - Line 94: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, essential_env, clear=False):...`

#### tests\integration\test_workflow_verification_l2.py
- **Occurrences:** 2
- **Lines:**
  - Line 478: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {"GITHUB_TOKEN": "env_token_...`
  - Line 485: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {}, clear=True):...`

### UNIT Tests (16 files)

#### auth_service\tests\unit\test_auth_environment_urls.py
- **Occurrences:** 16
- **Lines:**
  - Line 52: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {'ENVIRONMENT': 'development...`
  - Line 64: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {'ENVIRONMENT': 'test'}):...`
  - Line 75: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {'ENVIRONMENT': 'staging'}):...`
  - ... and 13 more

#### netra_backend\tests\unit\test_auth_startup_validation.py
- **Occurrences:** 7
- **Lines:**
  - Line 24: `with patch.dict(os.environ, {}, clear=True):...`
  - Line 59: `with patch.dict(os.environ, test_env):...`
  - Line 92: `with patch.dict(os.environ, test_env):...`
  - ... and 4 more

#### netra_backend\tests\unit\test_oauth_config_validation.py
- **Occurrences:** 1
- **Lines:**
  - Line 261: `with patch.dict(os.environ, env_vars, clear=False):...`

#### netra_backend\tests\unit\core\test_configuration_validation.py
- **Occurrences:** 1
- **Lines:**
  - Line 208: `with patch.dict(os.environ, {'ENVIRONMENT': 'production'}):...`

#### netra_backend\tests\unit\core\test_jwt_secret_ssot_compliance.py
- **Occurrences:** 1
- **Lines:**
  - Line 247: `with patch.dict(os.environ, {...`

#### tests\unit\test_config_regression_prevention.py
- **Occurrences:** 2
- **Lines:**
  - Line 265: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, { ))...`
  - Line 350: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, { ))...`

#### tests\unit\test_deployment_config_validation.py
- **Occurrences:** 1
- **Lines:**
  - Line 205: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {}, clear=True):  # Clear al...`

#### tests\unit\test_env_file_staging_protection.py
- **Occurrences:** 4
- **Lines:**
  - Line 30: `with patch.dict(os.environ, {"ENVIRONMENT": "staging"}, clear=False):...`
  - Line 60: `with patch.dict(os.environ, {"ENVIRONMENT": "production"}, clear=False):...`
  - Line 97: `with patch.dict(os.environ, env_vars, clear=True):...`
  - ... and 1 more

#### auth_service\tests\unit\test_auth_environment_urls.py
- **Occurrences:** 16
- **Lines:**
  - Line 52: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {'ENVIRONMENT': 'development...`
  - Line 64: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {'ENVIRONMENT': 'test'}):...`
  - Line 75: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {'ENVIRONMENT': 'staging'}):...`
  - ... and 13 more

#### netra_backend\tests\unit\test_auth_startup_validation.py
- **Occurrences:** 7
- **Lines:**
  - Line 24: `with patch.dict(os.environ, {}, clear=True):...`
  - Line 59: `with patch.dict(os.environ, test_env):...`
  - Line 92: `with patch.dict(os.environ, test_env):...`
  - ... and 4 more

#### netra_backend\tests\unit\test_oauth_config_validation.py
- **Occurrences:** 1
- **Lines:**
  - Line 261: `with patch.dict(os.environ, env_vars, clear=False):...`

#### netra_backend\tests\unit\core\test_configuration_validation.py
- **Occurrences:** 1
- **Lines:**
  - Line 208: `with patch.dict(os.environ, {'ENVIRONMENT': 'production'}):...`

#### netra_backend\tests\unit\core\test_jwt_secret_ssot_compliance.py
- **Occurrences:** 1
- **Lines:**
  - Line 247: `with patch.dict(os.environ, {...`

#### tests\unit\test_config_regression_prevention.py
- **Occurrences:** 2
- **Lines:**
  - Line 265: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, { ))...`
  - Line 350: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, { ))...`

#### tests\unit\test_deployment_config_validation.py
- **Occurrences:** 1
- **Lines:**
  - Line 205: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {}, clear=True):  # Clear al...`

#### tests\unit\test_env_file_staging_protection.py
- **Occurrences:** 4
- **Lines:**
  - Line 30: `with patch.dict(os.environ, {"ENVIRONMENT": "staging"}, clear=False):...`
  - Line 60: `with patch.dict(os.environ, {"ENVIRONMENT": "production"}, clear=False):...`
  - Line 97: `with patch.dict(os.environ, env_vars, clear=True):...`
  - ... and 1 more

### MISSION_CRITICAL Tests (14 files)

#### tests\mission_critical\test_data_sub_agent_ssot_compliance.py
- **Occurrences:** 1
- **Lines:**
  - Line 145: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {"TEST_VAR": "should_not_acc...`

#### tests\mission_critical\test_isolated_environment_compliance.py
- **Occurrences:** 1
- **Lines:**
  - Line 110: `"""Test EnvironmentPatcher as drop-in replacement for patch.dict(os.environ)."""...`

#### tests\mission_critical\test_service_secret_dependency.py
- **Occurrences:** 23
- **Lines:**
  - Line 54: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {}, clear=True):...`
  - Line 63: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {"SERVICE_SECRET": "test_sec...`
  - Line 69: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {"SERVICE_SECRET": ""}):...`
  - ... and 20 more

#### tests\mission_critical\test_service_secret_regression_simple.py
- **Occurrences:** 2
- **Lines:**
  - Line 27: `with patch.dict(os.environ, {}, clear=True):...`
  - Line 31: `with patch.dict(os.environ, {"SERVICE_SECRET": "test_secret"}):...`

#### tests\mission_critical\test_ssot_backward_compatibility.py
- **Occurrences:** 1
- **Lines:**
  - Line 775: `with patch.dict(os.environ, {test_var_name: test_var_value}):...`

#### tests\mission_critical\test_staging_auth_cross_service_validation.py
- **Occurrences:** 1
- **Lines:**
  - Line 372: `# Test 2: Secret source analysis - Migrated from patch.dict(os.environ)...`

#### tests\mission_critical\test_staging_auth_url_regression.py
- **Occurrences:** 13
- **Lines:**
  - Line 66: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {'ENVIRONMENT': 'staging'}, ...`
  - Line 101: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {'ENVIRONMENT': 'staging'}, ...`
  - Line 135: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {'ENVIRONMENT': 'staging'}, ...`
  - ... and 10 more

#### tests\mission_critical\test_data_sub_agent_ssot_compliance.py
- **Occurrences:** 1
- **Lines:**
  - Line 145: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {"TEST_VAR": "should_not_acc...`

#### tests\mission_critical\test_isolated_environment_compliance.py
- **Occurrences:** 1
- **Lines:**
  - Line 110: `"""Test EnvironmentPatcher as drop-in replacement for patch.dict(os.environ)."""...`

#### tests\mission_critical\test_service_secret_dependency.py
- **Occurrences:** 23
- **Lines:**
  - Line 54: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {}, clear=True):...`
  - Line 63: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {"SERVICE_SECRET": "test_sec...`
  - Line 69: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {"SERVICE_SECRET": ""}):...`
  - ... and 20 more

#### tests\mission_critical\test_service_secret_regression_simple.py
- **Occurrences:** 2
- **Lines:**
  - Line 27: `with patch.dict(os.environ, {}, clear=True):...`
  - Line 31: `with patch.dict(os.environ, {"SERVICE_SECRET": "test_secret"}):...`

#### tests\mission_critical\test_ssot_backward_compatibility.py
- **Occurrences:** 1
- **Lines:**
  - Line 775: `with patch.dict(os.environ, {test_var_name: test_var_value}):...`

#### tests\mission_critical\test_staging_auth_cross_service_validation.py
- **Occurrences:** 1
- **Lines:**
  - Line 372: `# Test 2: Secret source analysis - Migrated from patch.dict(os.environ)...`

#### tests\mission_critical\test_staging_auth_url_regression.py
- **Occurrences:** 13
- **Lines:**
  - Line 66: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {'ENVIRONMENT': 'staging'}, ...`
  - Line 101: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {'ENVIRONMENT': 'staging'}, ...`
  - Line 135: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {'ENVIRONMENT': 'staging'}, ...`
  - ... and 10 more

### SECURITY Tests (4 files)

#### tests\security\test_frontend_build_security_issues.py
- **Occurrences:** 2
- **Lines:**
  - Line 179: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, mock_env, clear=True):...`
  - Line 355: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {env_var: malicious_value}):...`

#### tests\security\test_service_secret_fallback_vulnerability.py
- **Occurrences:** 1
- **Lines:**
  - Line 466: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {"SERVICE_SECRET": "", "FORC...`

#### tests\security\test_frontend_build_security_issues.py
- **Occurrences:** 2
- **Lines:**
  - Line 179: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, mock_env, clear=True):...`
  - Line 355: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {env_var: malicious_value}):...`

#### tests\security\test_service_secret_fallback_vulnerability.py
- **Occurrences:** 1
- **Lines:**
  - Line 466: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {"SERVICE_SECRET": "", "FORC...`

### OTHER Tests (44 files)

#### database_scripts\test_create_auth.py
- **Occurrences:** 1
- **Lines:**
  - Line 131: `with patch.dict(os.environ, staging_env, clear=True):...`

#### scripts\migrate_test_environment_access.py
- **Occurrences:** 8
- **Lines:**
  - Line 10: `- Replace ALL patch.dict(os.environ) with IsolatedEnvironment context managers...`
  - Line 46: `# Pattern 1: patch.dict(os.environ, {...})...`
  - Line 50: `'description': 'patch.dict(os.environ) calls'...`
  - ... and 5 more

#### scripts\migrate_test_environment_hardening.py
- **Occurrences:** 6
- **Lines:**
  - Line 25: `Analyze a file for patch.dict(os.environ) patterns....`
  - Line 37: `if 'patch.dict(os.environ' in line:...`
  - Line 110: `report.append("with patch.dict(os.environ, {'ENVIRONMENT': 'staging'}):\n")...`
  - ... and 3 more

#### scripts\test_auth_database_sessions.py
- **Occurrences:** 3
- **Lines:**
  - Line 179: `with patch.dict(os.environ, {"DATABASE_URL": url}):...`
  - Line 198: `with patch.dict(os.environ, {"DATABASE_URL": url}):...`
  - Line 333: `with patch.dict(os.environ, {"DATABASE_URL": "postgresql://user:pass@localhost:5...`

#### scripts\test_redis_config_critical_failure.py
- **Occurrences:** 1
- **Lines:**
  - Line 101: `with patch.dict(os.environ, staging_env, clear=True):...`

#### tests\test_alpine_container_selection.py
- **Occurrences:** 7
- **Lines:**
  - Line 152: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {"PROJECT_ROOT": str(temp_pr...`
  - Line 166: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {"PROJECT_ROOT": str(temp_pr...`
  - Line 181: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {"PROJECT_ROOT": str(temp_pr...`
  - ... and 4 more

#### tests\test_jwt_secret_synchronization.py
- **Occurrences:** 11
- **Lines:**
  - Line 46: `with patch.dict(os.environ, {"JWT_SECRET_KEY": test_secret, "ENVIRONMENT": "deve...`
  - Line 68: `with patch.dict(os.environ, {"JWT_SECRET_KEY": test_secret, "ENVIRONMENT": "deve...`
  - Line 94: `with patch.dict(os.environ, {"JWT_SECRET_KEY": test_secret, "ENVIRONMENT": "deve...`
  - ... and 8 more

#### auth_service\tests\test_auth_port_configuration.py
- **Occurrences:** 10
- **Lines:**
  - Line 88: `with patch.dict(os.environ, {...`
  - Line 130: `with patch.dict(os.environ, {...`
  - Line 158: `with patch.dict(os.environ, {...`
  - ... and 7 more

#### dev_launcher\tests\test_launcher_config.py
- **Occurrences:** 2
- **Lines:**
  - Line 191: `with patch.dict(os.environ, {'NETRA_ENV': env}):...`
  - Line 198: `with patch.dict(os.environ, {'NETRA_ENV': 'production'}):...`

#### dev_launcher\tests\test_nextjs_config_validation.py
- **Occurrences:** 1
- **Lines:**
  - Line 523: `with patch.dict(os.environ, {"NODE_ENV": env}):...`

#### netra_backend\tests\test_configuration_resilience.py
- **Occurrences:** 9
- **Lines:**
  - Line 59: `with patch.dict(os.environ, {}, clear=True):...`
  - Line 61: `with patch.dict(os.environ, {...`
  - Line 91: `with patch.dict(os.environ, {...`
  - ... and 6 more

#### netra_backend\tests\test_migration_staging_configuration_issues.py
- **Occurrences:** 5
- **Lines:**
  - Line 170: `with patch.dict(os.environ, staging_env, clear=True):...`
  - Line 215: `with patch.dict(os.environ, staging_env, clear=True):...`
  - Line 267: `with patch.dict(os.environ, cloud_run_env, clear=True):...`
  - ... and 2 more

#### netra_backend\tests\test_redis_connection_staging_issues.py
- **Occurrences:** 8
- **Lines:**
  - Line 55: `with patch.dict(os.environ, staging_env, clear=True):...`
  - Line 100: `with patch.dict(os.environ, staging_env, clear=True):...`
  - Line 147: `with patch.dict(os.environ, staging_env, clear=True):...`
  - ... and 5 more

#### netra_backend\tests\test_redis_graceful_degradation.py
- **Occurrences:** 5
- **Lines:**
  - Line 61: `with patch.dict(os.environ, {...`
  - Line 95: `with patch.dict(os.environ, {...`
  - Line 131: `with patch.dict(os.environ, {...`
  - ... and 2 more

#### netra_backend\tests\test_startup_dependencies.py
- **Occurrences:** 1
- **Lines:**
  - Line 65: `with patch.dict(os.environ, {...`

#### netra_backend\tests\validation\test_config_migration_validation.py
- **Occurrences:** 2
- **Lines:**
  - Line 98: `with patch.dict(os.environ, {...`
  - Line 206: `with patch.dict(os.environ, {}, clear=True):...`

#### tests\critical\test_health_route_configuration_chaos.py
- **Occurrences:** 2
- **Lines:**
  - Line 790: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, env_vars, clear=False):...`
  - Line 876: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, test_env, clear=False):...`

#### tests\database\test_port_configuration_mismatch.py
- **Occurrences:** 4
- **Lines:**
  - Line 138: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, env_5433, clear=False):...`
  - Line 184: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, env_5432, clear=False):...`
  - Line 215: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, env_config, clear=False):...`
  - ... and 1 more

#### tests\staging\test_staging_service_auth.py
- **Occurrences:** 1
- **Lines:**
  - Line 86: `with patch.dict(os.environ, {...`

#### tests\websocket\test_mock_request_antipattern.py
- **Occurrences:** 4
- **Lines:**
  - Line 91: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {'USE_WEBSOCKET_SUPERVISOR_V...`
  - Line 435: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {'USE_WEBSOCKET_SUPERVISOR_V...`
  - Line 441: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {'USE_WEBSOCKET_SUPERVISOR_V...`
  - ... and 1 more

#### tests\websocket\test_mock_request_antipattern_fixed.py
- **Occurrences:** 2
- **Lines:**
  - Line 334: `with patch.dict(os.environ, {'USE_WEBSOCKET_SUPERVISOR_V3': 'false'}):...`
  - Line 340: `with patch.dict(os.environ, {'USE_WEBSOCKET_SUPERVISOR_V3': 'true'}):...`

#### tests\websocket\test_websocket_supervisor_isolation.py
- **Occurrences:** 2
- **Lines:**
  - Line 251: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {'USE_WEBSOCKET_SUPERVISOR_V...`
  - Line 366: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {'USE_WEBSOCKET_SUPERVISOR_V...`

#### test_framework\tests\test_url_assertions_example.py
- **Occurrences:** 3
- **Lines:**
  - Line 64: `with patch.dict(os.environ, {'ENVIRONMENT': 'development'}):...`
  - Line 81: `with patch.dict(os.environ, {'ENVIRONMENT': 'staging'}):...`
  - Line 106: `with patch.dict(os.environ, {'ENVIRONMENT': 'production'}):...`

#### database_scripts\test_create_auth.py
- **Occurrences:** 1
- **Lines:**
  - Line 131: `with patch.dict(os.environ, staging_env, clear=True):...`

#### scripts\test_auth_database_sessions.py
- **Occurrences:** 3
- **Lines:**
  - Line 179: `with patch.dict(os.environ, {"DATABASE_URL": url}):...`
  - Line 198: `with patch.dict(os.environ, {"DATABASE_URL": url}):...`
  - Line 333: `with patch.dict(os.environ, {"DATABASE_URL": "postgresql://user:pass@localhost:5...`

#### scripts\test_redis_config_critical_failure.py
- **Occurrences:** 1
- **Lines:**
  - Line 101: `with patch.dict(os.environ, staging_env, clear=True):...`

#### tests\test_alpine_container_selection.py
- **Occurrences:** 7
- **Lines:**
  - Line 152: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {"PROJECT_ROOT": str(temp_pr...`
  - Line 166: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {"PROJECT_ROOT": str(temp_pr...`
  - Line 181: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {"PROJECT_ROOT": str(temp_pr...`
  - ... and 4 more

#### tests\test_jwt_secret_synchronization.py
- **Occurrences:** 11
- **Lines:**
  - Line 46: `with patch.dict(os.environ, {"JWT_SECRET_KEY": test_secret, "ENVIRONMENT": "deve...`
  - Line 68: `with patch.dict(os.environ, {"JWT_SECRET_KEY": test_secret, "ENVIRONMENT": "deve...`
  - Line 94: `with patch.dict(os.environ, {"JWT_SECRET_KEY": test_secret, "ENVIRONMENT": "deve...`
  - ... and 8 more

#### auth_service\tests\test_auth_port_configuration.py
- **Occurrences:** 10
- **Lines:**
  - Line 88: `with patch.dict(os.environ, {...`
  - Line 130: `with patch.dict(os.environ, {...`
  - Line 158: `with patch.dict(os.environ, {...`
  - ... and 7 more

#### dev_launcher\tests\test_launcher_config.py
- **Occurrences:** 2
- **Lines:**
  - Line 191: `with patch.dict(os.environ, {'NETRA_ENV': env}):...`
  - Line 198: `with patch.dict(os.environ, {'NETRA_ENV': 'production'}):...`

#### dev_launcher\tests\test_nextjs_config_validation.py
- **Occurrences:** 1
- **Lines:**
  - Line 523: `with patch.dict(os.environ, {"NODE_ENV": env}):...`

#### netra_backend\tests\test_configuration_resilience.py
- **Occurrences:** 9
- **Lines:**
  - Line 59: `with patch.dict(os.environ, {}, clear=True):...`
  - Line 61: `with patch.dict(os.environ, {...`
  - Line 91: `with patch.dict(os.environ, {...`
  - ... and 6 more

#### netra_backend\tests\test_migration_staging_configuration_issues.py
- **Occurrences:** 5
- **Lines:**
  - Line 170: `with patch.dict(os.environ, staging_env, clear=True):...`
  - Line 215: `with patch.dict(os.environ, staging_env, clear=True):...`
  - Line 267: `with patch.dict(os.environ, cloud_run_env, clear=True):...`
  - ... and 2 more

#### netra_backend\tests\test_redis_connection_staging_issues.py
- **Occurrences:** 8
- **Lines:**
  - Line 55: `with patch.dict(os.environ, staging_env, clear=True):...`
  - Line 100: `with patch.dict(os.environ, staging_env, clear=True):...`
  - Line 147: `with patch.dict(os.environ, staging_env, clear=True):...`
  - ... and 5 more

#### netra_backend\tests\test_redis_graceful_degradation.py
- **Occurrences:** 5
- **Lines:**
  - Line 61: `with patch.dict(os.environ, {...`
  - Line 95: `with patch.dict(os.environ, {...`
  - Line 131: `with patch.dict(os.environ, {...`
  - ... and 2 more

#### netra_backend\tests\test_startup_dependencies.py
- **Occurrences:** 1
- **Lines:**
  - Line 65: `with patch.dict(os.environ, {...`

#### netra_backend\tests\validation\test_config_migration_validation.py
- **Occurrences:** 2
- **Lines:**
  - Line 98: `with patch.dict(os.environ, {...`
  - Line 206: `with patch.dict(os.environ, {}, clear=True):...`

#### tests\critical\test_health_route_configuration_chaos.py
- **Occurrences:** 2
- **Lines:**
  - Line 790: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, env_vars, clear=False):...`
  - Line 876: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, test_env, clear=False):...`

#### tests\database\test_port_configuration_mismatch.py
- **Occurrences:** 4
- **Lines:**
  - Line 138: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, env_5433, clear=False):...`
  - Line 184: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, env_5432, clear=False):...`
  - Line 215: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, env_config, clear=False):...`
  - ... and 1 more

#### tests\staging\test_staging_service_auth.py
- **Occurrences:** 1
- **Lines:**
  - Line 86: `with patch.dict(os.environ, {...`

#### tests\websocket\test_mock_request_antipattern.py
- **Occurrences:** 4
- **Lines:**
  - Line 91: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {'USE_WEBSOCKET_SUPERVISOR_V...`
  - Line 435: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {'USE_WEBSOCKET_SUPERVISOR_V...`
  - Line 441: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {'USE_WEBSOCKET_SUPERVISOR_V...`
  - ... and 1 more

#### tests\websocket\test_mock_request_antipattern_fixed.py
- **Occurrences:** 2
- **Lines:**
  - Line 334: `with patch.dict(os.environ, {'USE_WEBSOCKET_SUPERVISOR_V3': 'false'}):...`
  - Line 340: `with patch.dict(os.environ, {'USE_WEBSOCKET_SUPERVISOR_V3': 'true'}):...`

#### tests\websocket\test_websocket_supervisor_isolation.py
- **Occurrences:** 2
- **Lines:**
  - Line 251: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {'USE_WEBSOCKET_SUPERVISOR_V...`
  - Line 366: `# REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {'USE_WEBSOCKET_SUPERVISOR_V...`

#### test_framework\tests\test_url_assertions_example.py
- **Occurrences:** 3
- **Lines:**
  - Line 64: `with patch.dict(os.environ, {'ENVIRONMENT': 'development'}):...`
  - Line 81: `with patch.dict(os.environ, {'ENVIRONMENT': 'staging'}):...`
  - Line 106: `with patch.dict(os.environ, {'ENVIRONMENT': 'production'}):...`

## Migration Pattern
### Bad Pattern (Direct os.environ patch):
```python
with patch.dict(os.environ, {'ENVIRONMENT': 'staging'}):
    # test code
```

### Good Pattern (IsolatedEnvironment):
```python
from shared.isolated_environment import IsolatedEnvironment

env = IsolatedEnvironment()
env.set('ENVIRONMENT', 'staging')
# test code
env.reset()  # Clean up
```

### Alternative Pattern (Context Manager):
```python
from shared.isolated_environment import IsolatedEnvironment

with IsolatedEnvironment.temporary_override({'ENVIRONMENT': 'staging'}):
    # test code
```

## Risk Assessment
- **Current Risk:** MEDIUM - Test environment configs can leak between tests
- **Post-Migration Risk:** LOW - Each test has isolated environment
- **Business Impact:** Prevents false test passes due to environment pollution
- **Technical Impact:** Ensures test reliability and reproducibility
