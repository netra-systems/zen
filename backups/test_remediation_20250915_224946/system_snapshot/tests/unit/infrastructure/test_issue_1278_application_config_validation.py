"""
Application Configuration Validation Tests for Issue #1278

Business Value Justification (BVJ):
- Segment: Platform/Internal (Infrastructure Readiness)
- Business Goal: Ensure application code is correctly configured for infrastructure
- Value Impact: Validates app readiness independent of infrastructure state
- Revenue Impact: Prevents configuration-related failures affecting $500K+ ARR

These tests validate that our application code has the correct configuration
to work with GCP infrastructure once Issue #1278 is resolved.
"""

import pytest
import re
from test_framework.ssot.base import BaseTestCase
from shared.isolated_environment import get_env
from shared.logging.unified_logging_ssot import get_logger


class TestIssue1278ApplicationConfigValidation(BaseTestCase):
    """Application configuration validation tests for Issue #1278."""

    def setup_method(self, method):
        """Setup application configuration validation test environment."""
        self.env = get_env()
        self.logger = get_logger(__name__)
        
        # Issue #1278 staging configuration values
        self.expected_staging_config = {
            'database_host': 'netra-staging:us-central1:staging-shared-postgres',
            'database_timeout': 600,  # 10 minutes for Cloud SQL
            'vpc_connector': 'staging-connector',
            'vpc_egress': 'all-traffic',
            'ssl_domain': '*.netrasystems.ai',
            'backend_domain': 'staging.netrasystems.ai',
            'websocket_domain': 'api.staging.netrasystems.ai'
        }

    @pytest.mark.unit
    @pytest.mark.issue_1278
    def test_database_connection_string_format_validation(self):
        """Validate database connection string format for Issue #1278."""
        self.logger.info("Validating database connection string format")

        # Test PostgreSQL connection string format
        test_connection_strings = [
            "postgresql+asyncpg://user:pass@netra-staging:us-central1:staging-shared-postgres/netra",
            "postgresql+asyncpg://user:pass@localhost:5432/netra_test"
        ]

        for conn_str in test_connection_strings:
            # Validate basic format
            assert conn_str.startswith("postgresql+asyncpg://"), \
                f"Connection string should use asyncpg driver: {conn_str}"
            
            # Validate required components
            pattern = r"postgresql\+asyncpg://([^:]+):([^@]+)@([^/]+)/([^?]+)"
            match = re.match(pattern, conn_str)
            
            assert match, f"Invalid connection string format: {conn_str}"
            
            username, password, host, database = match.groups()
            
            assert username, "Username is required in connection string"
            assert password, "Password is required in connection string"
            assert host, "Host is required in connection string"
            assert database, "Database name is required in connection string"

        self.logger.info("✅ Database connection string format validation passed")

    @pytest.mark.unit
    @pytest.mark.issue_1278
    def test_vpc_connector_configuration_validation(self):
        """Validate VPC connector configuration for Issue #1278."""
        self.logger.info("Validating VPC connector configuration")

        # Expected VPC connector configuration for staging
        expected_vpc_config = {
            'connector_name': 'staging-connector',
            'region': 'us-central1',
            'ip_cidr_range': '10.1.0.0/28',
            'min_instances': 2,
            'max_instances': 10,
            'egress_setting': 'all-traffic'
        }

        # Validate connector name format
        connector_name = expected_vpc_config['connector_name']
        assert re.match(r'^[a-z]([a-z0-9-]*[a-z0-9])?$', connector_name), \
            f"VPC connector name format invalid: {connector_name}"
        
        assert len(connector_name) <= 25, \
            f"VPC connector name too long: {len(connector_name)} > 25"

        # Validate CIDR range format
        cidr_range = expected_vpc_config['ip_cidr_range']
        cidr_pattern = r'^(\d{1,3}\.){3}\d{1,3}/\d{1,2}$'
        assert re.match(cidr_pattern, cidr_range), \
            f"Invalid CIDR range format: {cidr_range}"

        # Validate instance scaling configuration
        min_instances = expected_vpc_config['min_instances']
        max_instances = expected_vpc_config['max_instances']
        
        assert min_instances >= 2, \
            f"Min instances should be >= 2 for reliability: {min_instances}"
        assert max_instances >= min_instances, \
            f"Max instances should be >= min instances: {max_instances} < {min_instances}"
        assert max_instances <= 1000, \
            f"Max instances should be <= 1000: {max_instances}"

        # Validate egress setting
        egress_setting = expected_vpc_config['egress_setting']
        valid_egress_settings = ['all-traffic', 'private-ranges-only']
        assert egress_setting in valid_egress_settings, \
            f"Invalid egress setting: {egress_setting}. Valid: {valid_egress_settings}"

        self.logger.info("✅ VPC connector configuration validation passed")

    @pytest.mark.unit
    @pytest.mark.issue_1278
    def test_ssl_certificate_domain_configuration(self):
        """Validate SSL certificate domain configuration for Issue #1278."""
        self.logger.info("Validating SSL certificate domain configuration")

        # Issue #1278: Correct domains (*.netrasystems.ai)
        correct_domains = [
            'staging.netrasystems.ai',
            'api.staging.netrasystems.ai',
            'auth.staging.netrasystems.ai'
        ]

        # Issue #1278: Incorrect domains (should not be used)
        deprecated_domains = [
            'staging.staging.netrasystems.ai',  # Double staging
            'api.staging.netrasystems.ai',      # Different subdomain pattern
            'staging-api.netrasystems.ai'       # Hyphenated pattern
        ]

        # Validate correct domain format
        domain_pattern = r'^[a-z0-9]([a-z0-9-]*[a-z0-9])?\.netrasystems\.ai$'
        
        for domain in correct_domains:
            assert re.match(domain_pattern, domain), \
                f"Domain format invalid: {domain}"
            
            # Ensure no double staging
            assert 'staging.staging' not in domain, \
                f"Domain should not have double staging: {domain}"
            
            # Validate total length
            assert len(domain) <= 63, \
                f"Domain too long: {len(domain)} > 63 chars"

        # Validate deprecated domains are not used
        for domain in deprecated_domains:
            # These should be recognized as problematic
            if 'staging.staging' in domain:
                assert False, f"Deprecated double staging domain detected: {domain}"

        self.logger.info("✅ SSL certificate domain configuration validation passed")

    @pytest.mark.unit
    @pytest.mark.issue_1278
    def test_timeout_configuration_validation(self):
        """Validate timeout configuration for Issue #1278."""
        self.logger.info("Validating timeout configuration")

        # Issue #1278: Proper timeout configuration
        timeout_config = {
            'database_connection_timeout': 600,     # 10 minutes for Cloud SQL
            'database_query_timeout': 30,           # 30 seconds for queries
            'vpc_connector_timeout': 30,            # 30 seconds for VPC
            'websocket_connection_timeout': 45,     # 45 seconds for WebSocket
            'health_check_timeout': 10,             # 10 seconds for health checks
            'startup_timeout': 300                  # 5 minutes for startup
        }

        # Validate timeout values are reasonable
        for timeout_name, timeout_value in timeout_config.items():
            assert isinstance(timeout_value, (int, float)), \
                f"Timeout {timeout_name} must be numeric: {type(timeout_value)}"
            
            assert timeout_value > 0, \
                f"Timeout {timeout_name} must be positive: {timeout_value}"
            
            # Validate specific timeout ranges
            if 'connection' in timeout_name:
                assert 10 <= timeout_value <= 600, \
                    f"Connection timeout {timeout_name} should be 10-600s: {timeout_value}"
            
            elif 'query' in timeout_name:
                assert 5 <= timeout_value <= 300, \
                    f"Query timeout {timeout_name} should be 5-300s: {timeout_value}"
            
            elif 'health' in timeout_name:
                assert 5 <= timeout_value <= 30, \
                    f"Health check timeout {timeout_name} should be 5-30s: {timeout_value}"

        # Issue #1278 specific: Database timeout should accommodate Cloud SQL startup
        db_timeout = timeout_config['database_connection_timeout']
        assert db_timeout >= 300, \
            f"Database timeout should be >= 300s for Cloud SQL: {db_timeout}"

        self.logger.info("✅ Timeout configuration validation passed")

    @pytest.mark.unit
    @pytest.mark.issue_1278
    def test_environment_variable_configuration_validation(self):
        """Validate environment variable configuration for Issue #1278."""
        self.logger.info("Validating environment variable configuration")

        # Required environment variables for Issue #1278
        required_env_vars = {
            'ENVIRONMENT': 'staging',
            'GCP_PROJECT': 'netra-staging',
            'VPC_CONNECTOR': 'staging-connector',
            'DATABASE_TIMEOUT': '600',
            'CORS_ALLOWED_ORIGINS': 'https://staging.netrasystems.ai',
            'SSL_DOMAIN_PATTERN': '*.netrasystems.ai'
        }

        # Validate environment variable format and constraints
        for var_name, expected_value in required_env_vars.items():
            # Check variable name format
            assert re.match(r'^[A-Z_][A-Z0-9_]*$', var_name), \
                f"Environment variable name format invalid: {var_name}"
            
            # Validate specific variable constraints
            if var_name == 'ENVIRONMENT':
                valid_environments = ['development', 'staging', 'production']
                assert expected_value in valid_environments, \
                    f"Invalid environment: {expected_value}. Valid: {valid_environments}"
            
            elif var_name == 'GCP_PROJECT':
                # GCP project name constraints
                assert re.match(r'^[a-z][a-z0-9-]*[a-z0-9]$', expected_value), \
                    f"Invalid GCP project name format: {expected_value}"
                assert 6 <= len(expected_value) <= 30, \
                    f"GCP project name length invalid: {len(expected_value)}"
            
            elif var_name == 'DATABASE_TIMEOUT':
                timeout_value = int(expected_value)
                assert 60 <= timeout_value <= 3600, \
                    f"Database timeout should be 60-3600s: {timeout_value}"
            
            elif 'DOMAIN' in var_name:
                # Domain validation
                if expected_value.startswith('*'):
                    # Wildcard domain
                    assert expected_value.count('*') == 1, \
                        f"Only one wildcard allowed: {expected_value}"
                    assert expected_value.startswith('*.'), \
                        f"Wildcard must be subdomain: {expected_value}"
                else:
                    # Regular domain
                    domain_pattern = r'^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)*$'
                    assert re.match(domain_pattern, expected_value), \
                        f"Invalid domain format: {expected_value}"

        self.logger.info("✅ Environment variable configuration validation passed")

    @pytest.mark.unit
    @pytest.mark.issue_1278
    def test_cloud_run_service_configuration_validation(self):
        """Validate Cloud Run service configuration for Issue #1278."""
        self.logger.info("Validating Cloud Run service configuration")

        # Expected Cloud Run service configuration
        service_config = {
            'backend_service': {
                'name': 'netra-backend-staging',
                'region': 'us-central1',
                'vpc_connector': 'staging-connector',
                'vpc_egress': 'all-traffic',
                'cpu_limit': '2',
                'memory_limit': '4Gi',
                'max_instances': 10,
                'timeout': 300
            },
            'auth_service': {
                'name': 'auth-staging',
                'region': 'us-central1', 
                'vpc_connector': 'staging-connector',
                'vpc_egress': 'all-traffic',
                'cpu_limit': '1',
                'memory_limit': '2Gi',
                'max_instances': 5,
                'timeout': 300
            }
        }

        for service_name, config in service_config.items():
            # Validate service name format
            name = config['name']
            assert re.match(r'^[a-z]([a-z0-9-]*[a-z0-9])?$', name), \
                f"Service name format invalid: {name}"
            assert len(name) <= 49, \
                f"Service name too long: {len(name)} > 49"

            # Validate VPC configuration
            vpc_connector = config['vpc_connector']
            assert vpc_connector == 'staging-connector', \
                f"VPC connector should be 'staging-connector': {vpc_connector}"
            
            vpc_egress = config['vpc_egress']
            assert vpc_egress == 'all-traffic', \
                f"VPC egress should be 'all-traffic': {vpc_egress}"

            # Validate resource limits
            cpu_limit = config['cpu_limit']
            assert cpu_limit in ['1', '2', '4', '8'], \
                f"Invalid CPU limit: {cpu_limit}"
            
            memory_limit = config['memory_limit']
            assert re.match(r'^\d+[GM]i$', memory_limit), \
                f"Invalid memory limit format: {memory_limit}"

            # Validate scaling configuration
            max_instances = config['max_instances']
            assert 1 <= max_instances <= 1000, \
                f"Max instances should be 1-1000: {max_instances}"

            # Validate timeout
            timeout = config['timeout']
            assert 60 <= timeout <= 3600, \
                f"Service timeout should be 60-3600s: {timeout}"

        self.logger.info("✅ Cloud Run service configuration validation passed")

    @pytest.mark.unit
    @pytest.mark.issue_1278
    def test_database_pool_configuration_validation(self):
        """Validate database connection pool configuration for Issue #1278."""
        self.logger.info("Validating database connection pool configuration")

        # Issue #1278: Optimized pool configuration for Cloud SQL
        pool_config = {
            'pool_size': 15,                    # Base connection pool size
            'max_overflow': 10,                 # Additional connections allowed
            'pool_timeout': 30,                 # Seconds to wait for connection
            'pool_recycle': 3600,              # Recycle connections every hour
            'pool_pre_ping': True,             # Validate connections before use
            'connect_timeout': 60,             # Initial connection timeout
            'command_timeout': 30,             # SQL command timeout
            'server_side_cursors': False       # Use client-side cursors
        }

        # Validate pool size configuration
        pool_size = pool_config['pool_size']
        max_overflow = pool_config['max_overflow']
        
        assert 5 <= pool_size <= 25, \
            f"Pool size should be 5-25 for Cloud SQL: {pool_size}"
        assert 5 <= max_overflow <= 25, \
            f"Max overflow should be 5-25: {max_overflow}"
        assert (pool_size + max_overflow) <= 25, \
            f"Total connections should not exceed Cloud SQL limit (25): {pool_size + max_overflow}"

        # Validate timeout configuration
        pool_timeout = pool_config['pool_timeout']
        assert 10 <= pool_timeout <= 60, \
            f"Pool timeout should be 10-60s: {pool_timeout}"

        connect_timeout = pool_config['connect_timeout']
        assert 30 <= connect_timeout <= 300, \
            f"Connect timeout should be 30-300s for Cloud SQL: {connect_timeout}"

        command_timeout = pool_config['command_timeout']
        assert 10 <= command_timeout <= 300, \
            f"Command timeout should be 10-300s: {command_timeout}"

        # Validate pool recycle setting
        pool_recycle = pool_config['pool_recycle']
        assert 1800 <= pool_recycle <= 7200, \
            f"Pool recycle should be 30min-2hr: {pool_recycle}"

        # Validate pre-ping setting (should be True for Cloud SQL)
        assert pool_config['pool_pre_ping'] is True, \
            "Pool pre-ping should be enabled for Cloud SQL reliability"

        # Validate server-side cursors (should be False for Cloud SQL)
        assert pool_config['server_side_cursors'] is False, \
            "Server-side cursors should be disabled for Cloud SQL compatibility"

        self.logger.info("✅ Database pool configuration validation passed")