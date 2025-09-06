from shared.isolated_environment import get_env
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import TestDatabaseManager
from test_framework.redis_test_utils_test_utils.test_redis_manager import TestRedisManager
from auth_service.core.auth_manager import AuthManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment
from unittest.mock import Mock, patch, MagicMock

# REMOVED_SYNTAX_ERROR: '''
env = get_env()
# REMOVED_SYNTAX_ERROR: Critical Staging Root Cause Validation Tests

# REMOVED_SYNTAX_ERROR: This file contains failing tests that reproduce each identified staging error
# REMOVED_SYNTAX_ERROR: for root cause validation. These tests are designed to FAIL and demonstrate
# REMOVED_SYNTAX_ERROR: the exact conditions that cause each staging deployment error.

# REMOVED_SYNTAX_ERROR: QA Agent: Root Cause Analysis
# REMOVED_SYNTAX_ERROR: Created: 2025-08-24
# REMOVED_SYNTAX_ERROR: Purpose: Validate root causes through failing test reproduction
""

import asyncio
import pytest
import os
import re
import sys
from pathlib import Path
import asyncpg

# Setup test path using absolute imports
from test_framework import setup_test_path
setup_test_path()


# REMOVED_SYNTAX_ERROR: class TestPostgreSQLAuthenticationFailure:
    # REMOVED_SYNTAX_ERROR: """Test suite reproducing PostgreSQL authentication failures in staging."""

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_wrong_credentials_in_database_url_secret(self):
        # REMOVED_SYNTAX_ERROR: '''
        # REMOVED_SYNTAX_ERROR: FAILING TEST: Reproduces exact PostgreSQL auth failure from staging.

        # REMOVED_SYNTAX_ERROR: Root Cause: DATABASE_URL secret contains wrong password for Cloud SQL user.
        # REMOVED_SYNTAX_ERROR: This test MUST fail with "password authentication failed" error.
        # REMOVED_SYNTAX_ERROR: """"
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.configuration.database import DatabaseConfigManager

        # Simulate exact staging secret with wrong password
        # REMOVED_SYNTAX_ERROR: wrong_credentials_url = ( )
        # REMOVED_SYNTAX_ERROR: "postgresql://postgres:wrong_staging_password@"
        # REMOVED_SYNTAX_ERROR: "/postgres?host=/cloudsql/netra-staging:us-central1:netra-postgres&sslmode=require"
        

        # REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, { ))
        # REMOVED_SYNTAX_ERROR: "DATABASE_URL": wrong_credentials_url,
        # REMOVED_SYNTAX_ERROR: "ENVIRONMENT": "staging"
        # REMOVED_SYNTAX_ERROR: }):
            # REMOVED_SYNTAX_ERROR: manager = DatabaseConfigManager()
            # REMOVED_SYNTAX_ERROR: postgres_url = manager._get_postgres_url()

            # Convert to asyncpg format
            # REMOVED_SYNTAX_ERROR: async_url = manager._normalize_postgres_url(postgres_url)

            # This MUST fail with authentication error when connecting
            # REMOVED_SYNTAX_ERROR: with pytest.raises(Exception) as exc_info:
                # Simulate actual connection attempt
                # REMOVED_SYNTAX_ERROR: conn = await asyncpg.connect(async_url)
                # REMOVED_SYNTAX_ERROR: await conn.close()

                # Verify it's an authentication failure
                # REMOVED_SYNTAX_ERROR: error_str = str(exc_info.value).lower()
                # REMOVED_SYNTAX_ERROR: assert any(keyword in error_str for keyword in [ ))
                # REMOVED_SYNTAX_ERROR: "password authentication failed",
                # REMOVED_SYNTAX_ERROR: "authentication failed",
                # REMOVED_SYNTAX_ERROR: "fe_sendauth"
                # REMOVED_SYNTAX_ERROR: ]), "formatted_string"

                # Removed problematic line: @pytest.mark.asyncio
                # Removed problematic line: async def test_user_does_not_exist_on_cloud_sql(self):
                    # REMOVED_SYNTAX_ERROR: '''
                    # REMOVED_SYNTAX_ERROR: FAILING TEST: Reproduces error when DATABASE_URL user doesn"t exist.

                    # REMOVED_SYNTAX_ERROR: Root Cause: Secret Manager has user 'postgres' but Cloud SQL instance
                    # REMOVED_SYNTAX_ERROR: was created with different user (e.g., 'netra_user').
                    # REMOVED_SYNTAX_ERROR: """"
                    # REMOVED_SYNTAX_ERROR: nonexistent_user_url = ( )
                    # REMOVED_SYNTAX_ERROR: "postgresql://nonexistent_user:any_password@"
                    # REMOVED_SYNTAX_ERROR: "/postgres?host=/cloudsql/netra-staging:us-central1:netra-postgres&sslmode=require"
                    

                    # REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, { ))
                    # REMOVED_SYNTAX_ERROR: "DATABASE_URL": nonexistent_user_url,
                    # REMOVED_SYNTAX_ERROR: "ENVIRONMENT": "staging"
                    # REMOVED_SYNTAX_ERROR: }):
                        # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.configuration.database import DatabaseConfigManager
                        # REMOVED_SYNTAX_ERROR: manager = DatabaseConfigManager()

                        # REMOVED_SYNTAX_ERROR: async_url = manager._normalize_postgres_url(nonexistent_user_url)

                        # This MUST fail with "role does not exist" or similar
                        # REMOVED_SYNTAX_ERROR: with pytest.raises(Exception) as exc_info:
                            # REMOVED_SYNTAX_ERROR: conn = await asyncpg.connect(async_url)
                            # REMOVED_SYNTAX_ERROR: await conn.close()

                            # REMOVED_SYNTAX_ERROR: error_str = str(exc_info.value).lower()
                            # REMOVED_SYNTAX_ERROR: assert any(keyword in error_str for keyword in [ ))
                            # REMOVED_SYNTAX_ERROR: "role", "user", "does not exist", "authentication"
                            # REMOVED_SYNTAX_ERROR: ]), "formatted_string"


# REMOVED_SYNTAX_ERROR: class TestSSLParameterMismatch:
    # REMOVED_SYNTAX_ERROR: """Test suite reproducing SSL parameter mismatches in staging."""

# REMOVED_SYNTAX_ERROR: def test_sslmode_to_ssl_conversion_breaks_asyncpg(self):
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: FAILING TEST: Reproduces "unrecognized configuration parameter 'ssl'" error.

    # REMOVED_SYNTAX_ERROR: Root Cause: Converting sslmode=require to ssl=require breaks asyncpg
    # REMOVED_SYNTAX_ERROR: for Cloud SQL Unix socket connections.
    # REMOVED_SYNTAX_ERROR: """"
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.configuration.database import DatabaseConfigManager

    # Cloud SQL URL with sslmode (common in Secret Manager)
    # REMOVED_SYNTAX_ERROR: cloud_sql_url = ( )
    # REMOVED_SYNTAX_ERROR: "postgresql://netra_user:password@"
    # REMOVED_SYNTAX_ERROR: "/postgres?host=/cloudsql/netra-staging:us-central1:netra-postgres&sslmode=require"
    

    # REMOVED_SYNTAX_ERROR: manager = DatabaseConfigManager()

    # This conversion is INCORRECT for Cloud SQL
    # REMOVED_SYNTAX_ERROR: normalized_url = manager._normalize_postgres_url(cloud_sql_url)

    # The problem: URL still contains sslmode which is invalid for asyncpg with Unix sockets
    # REMOVED_SYNTAX_ERROR: assert "sslmode=" in normalized_url, "URL should still contain sslmode (demonstrating the bug)"

    # When asyncpg tries to connect with sslmode parameter on Unix socket, it fails
    # REMOVED_SYNTAX_ERROR: with pytest.raises(Exception) as exc_info:
        # Simulate asyncpg parsing the connection string
        # REMOVED_SYNTAX_ERROR: import urllib.parse as urlparse
        # REMOVED_SYNTAX_ERROR: parsed = urlparse.urlparse(normalized_url)
        # REMOVED_SYNTAX_ERROR: query_params = urlparse.parse_qs(parsed.query)

        # REMOVED_SYNTAX_ERROR: if 'sslmode' in query_params and '/cloudsql/' in normalized_url:
            # REMOVED_SYNTAX_ERROR: raise ValueError("unrecognized configuration parameter 'sslmode'")

            # REMOVED_SYNTAX_ERROR: error_str = str(exc_info.value)
            # REMOVED_SYNTAX_ERROR: assert "unrecognized configuration parameter" in error_str

# REMOVED_SYNTAX_ERROR: def test_inconsistent_ssl_handling_across_services(self):
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: FAILING TEST: Shows how auth service and backend handle SSL differently.

    # REMOVED_SYNTAX_ERROR: Root Cause: Each service has different URL normalization logic,
    # REMOVED_SYNTAX_ERROR: causing inconsistent SSL parameter handling.
    # REMOVED_SYNTAX_ERROR: """"
    # REMOVED_SYNTAX_ERROR: test_url = ( )
    # REMOVED_SYNTAX_ERROR: "postgresql://user:pass@/db?host=/cloudsql/instance&sslmode=require"
    

    # Backend normalization (from DatabaseConfigManager)
    # REMOVED_SYNTAX_ERROR: backend_url = test_url.replace("postgresql://", "postgresql+asyncpg://")
    # Backend might keep sslmode

    # Auth service normalization (different logic)
    # REMOVED_SYNTAX_ERROR: auth_url = test_url.replace("postgresql://", "postgresql+asyncpg://")
    # REMOVED_SYNTAX_ERROR: auth_url = re.sub(r'[&?]sslmode=[^&]*', '', auth_url)  # Removes sslmode

    # This MUST fail because services handle URLs differently
    # REMOVED_SYNTAX_ERROR: assert backend_url != auth_url, "Services should handle URLs consistently"
    # REMOVED_SYNTAX_ERROR: assert "sslmode=" in backend_url and "sslmode=" not in auth_url, \
    # REMOVED_SYNTAX_ERROR: "Inconsistent SSL parameter handling between services"


# REMOVED_SYNTAX_ERROR: class TestClickHouseLocalhostConnection:
    # REMOVED_SYNTAX_ERROR: """Test suite reproducing ClickHouse localhost connection errors."""

# REMOVED_SYNTAX_ERROR: def test_missing_clickhouse_url_defaults_to_localhost(self):
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: FAILING TEST: Reproduces ClickHouse trying to connect to localhost in staging.

    # REMOVED_SYNTAX_ERROR: Root Cause: Missing CLICKHOUSE_URL in staging deployment causes
    # REMOVED_SYNTAX_ERROR: fallback to localhost default.
    # REMOVED_SYNTAX_ERROR: """"
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.configuration.database import DatabaseConfigManager

    # REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, { ))
    # REMOVED_SYNTAX_ERROR: "ENVIRONMENT": "staging",
    # REMOVED_SYNTAX_ERROR: "CLICKHOUSE_URL": "",  # Not set in staging
    # REMOVED_SYNTAX_ERROR: "CLICKHOUSE_HOST": "",  # Also not set
    # REMOVED_SYNTAX_ERROR: }):
        # REMOVED_SYNTAX_ERROR: manager = DatabaseConfigManager()
        # REMOVED_SYNTAX_ERROR: ch_config = manager._get_clickhouse_configuration()

        # This MUST fail - staging should not default to localhost
        # REMOVED_SYNTAX_ERROR: assert ch_config["host"] == "", "ClickHouse host should be empty in staging when not configured"

        # Configuration system still tries to build localhost URL
        # REMOVED_SYNTAX_ERROR: if not ch_config["host"] and manager._environment in ["staging", "production"]:
            # REMOVED_SYNTAX_ERROR: pytest.fail("ClickHouse defaulting to localhost in staging environment")

# REMOVED_SYNTAX_ERROR: def test_deployment_script_missing_clickhouse_secrets(self):
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: FAILING TEST: Shows deployment script not configuring ClickHouse secrets.

    # REMOVED_SYNTAX_ERROR: Root Cause: GCP deployment script missing CLICKHOUSE_URL in secret mapping.
    # REMOVED_SYNTAX_ERROR: """"
    # Read deployment script
    # REMOVED_SYNTAX_ERROR: deploy_script_path = Path(__file__).parent.parent.parent.parent / "scripts" / "deploy_to_gcp.py"

    # REMOVED_SYNTAX_ERROR: if deploy_script_path.exists():
        # REMOVED_SYNTAX_ERROR: with open(deploy_script_path) as f:
            # REMOVED_SYNTAX_ERROR: deploy_content = f.read()

            # Check if ClickHouse secrets are configured
            # REMOVED_SYNTAX_ERROR: required_clickhouse_secrets = [ )
            # REMOVED_SYNTAX_ERROR: "CLICKHOUSE_URL",
            # REMOVED_SYNTAX_ERROR: "CLICKHOUSE_HOST",
            # REMOVED_SYNTAX_ERROR: "CLICKHOUSE_PASSWORD"
            

            # REMOVED_SYNTAX_ERROR: missing_secrets = []
            # REMOVED_SYNTAX_ERROR: for secret in required_clickhouse_secrets:
                # REMOVED_SYNTAX_ERROR: if secret not in deploy_content:
                    # REMOVED_SYNTAX_ERROR: missing_secrets.append(secret)

                    # This MUST fail if secrets are missing
                    # REMOVED_SYNTAX_ERROR: assert not missing_secrets, "formatted_string"


# REMOVED_SYNTAX_ERROR: class TestRedisConfigurationDefault:
    # REMOVED_SYNTAX_ERROR: """Test suite reproducing Redis configuration errors."""

# REMOVED_SYNTAX_ERROR: def test_hardcoded_localhost_overrides_staging_environment(self):
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: FAILING TEST: Reproduces Redis connecting to localhost in staging.

    # REMOVED_SYNTAX_ERROR: Root Cause: Configuration classes have hardcoded localhost defaults
    # REMOVED_SYNTAX_ERROR: that override staging environment detection.
    # REMOVED_SYNTAX_ERROR: """"
    # REMOVED_SYNTAX_ERROR: from auth_service.auth_core.config import AuthConfig

    # REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, { ))
    # REMOVED_SYNTAX_ERROR: "ENVIRONMENT": "staging",
    # REMOVED_SYNTAX_ERROR: "REDIS_URL": "",  # Not set in deployment
    # REMOVED_SYNTAX_ERROR: }):
        # REMOVED_SYNTAX_ERROR: redis_url = AuthConfig.get_redis_url()

        # This MUST fail - staging should not use localhost
        # REMOVED_SYNTAX_ERROR: assert "localhost" not in redis_url, \
        # REMOVED_SYNTAX_ERROR: "formatted_string"

# REMOVED_SYNTAX_ERROR: def test_redis_secret_not_mapped_in_deployment(self):
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: FAILING TEST: Shows REDIS_URL not configured in Cloud Run deployment.

    # REMOVED_SYNTAX_ERROR: Root Cause: Deployment script not setting REDIS_URL secret properly.
    # REMOVED_SYNTAX_ERROR: """"
    # REMOVED_SYNTAX_ERROR: deploy_script_path = Path(__file__).parent.parent.parent.parent / "scripts" / "deploy_to_gcp.py"

    # REMOVED_SYNTAX_ERROR: if deploy_script_path.exists():
        # REMOVED_SYNTAX_ERROR: with open(deploy_script_path) as f:
            # REMOVED_SYNTAX_ERROR: deploy_content = f.read()

            # Check for Redis secret configuration
            # REMOVED_SYNTAX_ERROR: redis_secret_patterns = [ )
            # REMOVED_SYNTAX_ERROR: "REDIS_URL=",
            # REMOVED_SYNTAX_ERROR: "redis-url",
            # REMOVED_SYNTAX_ERROR: "--set-secrets.*redis"
            

            # REMOVED_SYNTAX_ERROR: has_redis_config = any( )
            # REMOVED_SYNTAX_ERROR: re.search(pattern, deploy_content, re.IGNORECASE)
            # REMOVED_SYNTAX_ERROR: for pattern in redis_secret_patterns
            

            # This MUST fail if Redis not configured
            # REMOVED_SYNTAX_ERROR: assert has_redis_config, "Deployment script missing Redis URL secret configuration"


# REMOVED_SYNTAX_ERROR: class TestMissingEnvironmentVariables:
    # REMOVED_SYNTAX_ERROR: """Test suite reproducing missing environment variable errors."""

# REMOVED_SYNTAX_ERROR: def test_no_startup_validation_for_required_config(self):
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: FAILING TEST: Shows services starting without required configuration.

    # REMOVED_SYNTAX_ERROR: Root Cause: No fail-fast validation to check required environment
    # REMOVED_SYNTAX_ERROR: variables before service initialization.
    # REMOVED_SYNTAX_ERROR: """"
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.configuration.database import DatabaseConfigManager

    # Simulate completely missing configuration
    # REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, { ))
    # REMOVED_SYNTAX_ERROR: "DATABASE_URL": "",
    # REMOVED_SYNTAX_ERROR: "REDIS_URL": "",
    # REMOVED_SYNTAX_ERROR: "CLICKHOUSE_URL": "",
    # REMOVED_SYNTAX_ERROR: "ENVIRONMENT": "staging"
    # REMOVED_SYNTAX_ERROR: }, clear=True):

        # REMOVED_SYNTAX_ERROR: manager = DatabaseConfigManager()

        # Service MUST fail to start with missing critical config
        # REMOVED_SYNTAX_ERROR: with pytest.raises(Exception) as exc_info:
            # This should raise ConfigurationError but doesn't
            # REMOVED_SYNTAX_ERROR: config_summary = manager.get_database_summary()

            # Check if all critical configs are missing
            # REMOVED_SYNTAX_ERROR: if not any([ ))
            # REMOVED_SYNTAX_ERROR: config_summary.get("postgres_configured"),
            # REMOVED_SYNTAX_ERROR: config_summary.get("clickhouse_configured"),
            # REMOVED_SYNTAX_ERROR: config_summary.get("redis_configured")
            # REMOVED_SYNTAX_ERROR: ]):
                # REMOVED_SYNTAX_ERROR: raise ValueError("All critical database configurations missing")

                # REMOVED_SYNTAX_ERROR: assert "configuration" in str(exc_info.value).lower()

# REMOVED_SYNTAX_ERROR: def test_deployment_secrets_mapping_incomplete(self):
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: FAILING TEST: Shows incomplete secret mapping in Cloud Run deployment.

    # REMOVED_SYNTAX_ERROR: Root Cause: Some required secrets not properly mapped from Secret Manager
    # REMOVED_SYNTAX_ERROR: to Cloud Run environment variables.
    # REMOVED_SYNTAX_ERROR: """"
    # REMOVED_SYNTAX_ERROR: deploy_script_path = Path(__file__).parent.parent.parent.parent / "scripts" / "deploy_to_gcp.py"

    # REMOVED_SYNTAX_ERROR: if deploy_script_path.exists():
        # REMOVED_SYNTAX_ERROR: with open(deploy_script_path) as f:
            # REMOVED_SYNTAX_ERROR: deploy_content = f.read()

            # Critical secrets that MUST be present
            # REMOVED_SYNTAX_ERROR: critical_secrets = [ )
            # REMOVED_SYNTAX_ERROR: "DATABASE_URL",
            # REMOVED_SYNTAX_ERROR: "JWT_SECRET_KEY",
            # REMOVED_SYNTAX_ERROR: "GOOGLE_CLIENT_ID",
            # REMOVED_SYNTAX_ERROR: "GOOGLE_CLIENT_SECRET",
            # REMOVED_SYNTAX_ERROR: "REDIS_URL",
            # REMOVED_SYNTAX_ERROR: "CLICKHOUSE_URL"
            

            # Find secret mapping sections
            # REMOVED_SYNTAX_ERROR: secret_sections = re.findall(r'--set-secrets[^"]+', deploy_content)"
            # REMOVED_SYNTAX_ERROR: all_secrets = " ".join(secret_sections)

            # REMOVED_SYNTAX_ERROR: missing_critical = []
            # REMOVED_SYNTAX_ERROR: for secret in critical_secrets:
                # REMOVED_SYNTAX_ERROR: if secret not in all_secrets:
                    # REMOVED_SYNTAX_ERROR: missing_critical.append(secret)

                    # This MUST fail if critical secrets missing
                    # REMOVED_SYNTAX_ERROR: assert not missing_critical, "formatted_string"


# REMOVED_SYNTAX_ERROR: class TestConfigurationHierarchyIssues:
    # REMOVED_SYNTAX_ERROR: """Test suite reproducing configuration hierarchy and precedence issues."""

# REMOVED_SYNTAX_ERROR: def test_development_defaults_override_staging_detection(self):
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: FAILING TEST: Shows development defaults taking precedence over staging.

    # REMOVED_SYNTAX_ERROR: Root Cause: Configuration loading prioritizes hardcoded defaults
    # REMOVED_SYNTAX_ERROR: over environment-specific detection.
    # REMOVED_SYNTAX_ERROR: """"
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.configuration.database import DatabaseConfigManager

    # REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, { ))
    # REMOVED_SYNTAX_ERROR: "ENVIRONMENT": "staging",
    # Simulate missing configuration
    # REMOVED_SYNTAX_ERROR: "DATABASE_URL": "",
    # REMOVED_SYNTAX_ERROR: "CLICKHOUSE_HOST": "",
    # REMOVED_SYNTAX_ERROR: "REDIS_URL": ""
    # REMOVED_SYNTAX_ERROR: }):
        # REMOVED_SYNTAX_ERROR: manager = DatabaseConfigManager()

        # Get default configurations
        # REMOVED_SYNTAX_ERROR: postgres_url = manager._get_default_postgres_url()
        # REMOVED_SYNTAX_ERROR: ch_config = manager._get_clickhouse_configuration()

        # This MUST fail - staging should not get development defaults
        # REMOVED_SYNTAX_ERROR: staging_issues = []

        # REMOVED_SYNTAX_ERROR: if "localhost" in postgres_url:
            # REMOVED_SYNTAX_ERROR: staging_issues.append("PostgreSQL defaulting to localhost")

            # REMOVED_SYNTAX_ERROR: if ch_config.get("host") == "localhost":
                # REMOVED_SYNTAX_ERROR: staging_issues.append("ClickHouse defaulting to localhost")

                # REMOVED_SYNTAX_ERROR: assert not staging_issues, "formatted_string"

# REMOVED_SYNTAX_ERROR: def test_secret_manager_precedence_over_environment(self):
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: FAILING TEST: Shows Secret Manager values not taking precedence.

    # REMOVED_SYNTAX_ERROR: Root Cause: Configuration system not properly prioritizing Secret Manager
    # REMOVED_SYNTAX_ERROR: secrets over local environment variables.
    # REMOVED_SYNTAX_ERROR: """"
    # Simulate conflicting configuration sources
    # REMOVED_SYNTAX_ERROR: local_db_url = "postgresql://local:local@localhost:5432/local"
    # REMOVED_SYNTAX_ERROR: secret_db_url = "postgresql://staging:staging@/staging?host=/cloudsql/instance"

    # REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, { ))
    # REMOVED_SYNTAX_ERROR: "DATABASE_URL": local_db_url,
    # REMOVED_SYNTAX_ERROR: "ENVIRONMENT": "staging"
    # REMOVED_SYNTAX_ERROR: }):
        # Mock Secret Manager returning different value
        # Mock: Component isolation for testing without external dependencies
        # REMOVED_SYNTAX_ERROR: with patch('os.environ.get') as mock_get:
# REMOVED_SYNTAX_ERROR: def mock_env_get(key, default=None):
    # REMOVED_SYNTAX_ERROR: if key == "DATABASE_URL":
        # REMOVED_SYNTAX_ERROR: return secret_db_url  # Secret Manager value
        # REMOVED_SYNTAX_ERROR: return env.get(key, default)

        # REMOVED_SYNTAX_ERROR: mock_get.side_effect = mock_env_get

        # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.configuration.database import DatabaseConfigManager
        # REMOVED_SYNTAX_ERROR: manager = DatabaseConfigManager()

        # REMOVED_SYNTAX_ERROR: actual_url = manager._get_postgres_url()

        # This MUST fail - should use Secret Manager value, not local
        # REMOVED_SYNTAX_ERROR: assert actual_url == secret_db_url, \
        # REMOVED_SYNTAX_ERROR: "formatted_string"


        # REMOVED_SYNTAX_ERROR: if __name__ == "__main__":
            # These tests are designed to FAIL and demonstrate root causes
            # Run with: pytest -v --tb=short test_staging_root_cause_validation.py
            # REMOVED_SYNTAX_ERROR: pass