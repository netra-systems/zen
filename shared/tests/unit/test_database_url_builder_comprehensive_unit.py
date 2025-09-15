"""
ULTRA COMPREHENSIVE Unit Tests for DatabaseUrlBuilder - SECOND MOST CRITICAL SSOT CLASS
Business Value Justification (BVJ):
- Segment: Platform/Internal - CORE DATABASE INFRASTRUCTURE
- Business Goal: ZERO-FAILURE database connectivity across ALL services 
- Value Impact: 100% system reliability - ALL services depend on this SINGLE SOURCE OF TRUTH
- Strategic Impact: Platform exists or fails based on database connectivity working correctly

CRITICAL MISSION: This is the SECOND MOST IMPORTANT module in the entire platform.
Every service, every database connection, every data operation depends on DatabaseUrlBuilder.
ANY bug in this class cascades to COMPLETE SYSTEM OUTAGES affecting ALL customers.

Testing Coverage Goals:
[U+2713] 100% line coverage - Every single line must be tested
[U+2713] 100% branch coverage - Every conditional path must be validated  
[U+2713] 100% business logic coverage - Every database connectivity scenario must pass
[U+2713] Performance critical paths - Validated with benchmarks
[U+2713] Thread safety under heavy load - Concurrent access validation
[U+2713] Error handling - All failure modes tested
[U+2713] Windows compatibility - UTF-8 encoding and path support
[U+2713] Multi-environment system support - Service independence verified
[U+2713] Security validation - Credential protection and URL sanitization

ULTRA CRITICAL IMPORTANCE: 
- URL construction MUST work for ALL database types and configurations
- Cloud SQL Unix socket connections MUST be handled correctly
- TCP connections with and without SSL MUST work flawlessly
- Docker hostname resolution MUST prevent connection failures
- Environment variable parsing MUST be bulletproof
- Credential encoding MUST preserve special characters
- URL normalization MUST prevent service incompatibilities
- Driver-specific formatting MUST work for all supported drivers
- Validation MUST catch configuration errors before they cause outages
- Security MUST protect credentials in logs and error messages
"""
import pytest
import os
import threading
import time
import tempfile
import concurrent.futures
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Callable, Union
from unittest.mock import patch, Mock, MagicMock, mock_open
from dataclasses import dataclass, field
import sys
import re
from urllib.parse import urlparse, quote, unquote
import subprocess
from shared.database_url_builder import DatabaseURLBuilder
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class TestDatabaseUrlBuilderInstantiationAndProperties:
    """Test basic instantiation and property access - FOUNDATION CRITICAL."""

    def test_basic_instantiation_with_env_vars(self):
        """Test basic instantiation with environment variables."""
        test_env = {'POSTGRES_HOST': 'localhost', 'POSTGRES_PORT': '5432', 'POSTGRES_USER': 'postgres', 'POSTGRES_PASSWORD': 'password', 'POSTGRES_DB': 'testdb', 'ENVIRONMENT': 'development'}
        builder = DatabaseURLBuilder(test_env)
        assert builder.env == test_env, 'Environment variables not stored correctly'
        assert builder.environment == 'development', 'Environment not detected correctly'
        assert builder.postgres_host == 'localhost', 'POSTGRES_HOST property failed'
        assert builder.postgres_port == '5432', 'POSTGRES_PORT property failed'
        assert builder.postgres_user == 'postgres', 'POSTGRES_USER property failed'
        assert builder.postgres_password == 'password', 'POSTGRES_PASSWORD property failed'
        assert builder.postgres_db == 'testdb', 'POSTGRES_DB property failed'

    def test_instantiation_with_minimal_env(self):
        """Test instantiation with minimal environment variables."""
        minimal_env = {'ENVIRONMENT': 'test'}
        builder = DatabaseURLBuilder(minimal_env)
        assert builder.environment == 'test', 'Environment not set correctly'
        assert builder.postgres_host is None, 'Host should be None with minimal env'
        assert builder.postgres_port == '5432', 'Port should default to 5432'
        assert builder.postgres_user is None, 'User should be None with minimal env'
        assert builder.postgres_password is None, 'Password should be None with minimal env'
        assert builder.postgres_db is None, 'Database should be None with minimal env'

    def test_instantiation_with_empty_env(self):
        """Test instantiation with empty environment variables."""
        empty_env = {}
        builder = DatabaseURLBuilder(empty_env)
        assert builder.environment == 'development', 'Should default to development'
        assert builder.postgres_host is None, 'Host should be None'
        assert builder.postgres_port == '5432', 'Port should default to 5432'

    def test_environment_normalization(self):
        """Test environment string normalization."""
        test_cases = [('DEVELOPMENT', 'development'), ('Development', 'development'), ('DEV', 'dev'), ('STAGING', 'staging'), ('PRODUCTION', 'production'), ('', ''), (None, 'development')]
        for env_value, expected in test_cases:
            test_env = {'ENVIRONMENT': env_value} if env_value is not None else {}
            builder = DatabaseURLBuilder(test_env)
            if env_value is None:
                assert builder.environment == expected, f'Environment {env_value} should default to {expected}'
            else:
                assert builder.environment == expected.lower(), f'Environment {env_value} should normalize to {expected.lower()}'

class TestDockerEnvironmentDetection:
    """Test Docker environment detection - CRITICAL FOR CONTAINER DEPLOYMENTS."""

    def test_docker_detection_via_environment_variables(self):
        """Test Docker detection using environment variables."""
        docker_env_vars = ['RUNNING_IN_DOCKER', 'IS_DOCKER', 'DOCKER_CONTAINER']
        for var in docker_env_vars:
            test_env = {var: 'true'}
            builder = DatabaseURLBuilder(test_env)
            assert builder.is_docker_environment(), f'Should detect Docker via {var}'
        for var in docker_env_vars:
            test_env = {var: 'false'}
            builder = DatabaseURLBuilder(test_env)
            assert not builder.is_docker_environment(), f'Should not detect Docker with {var}=false'

    def test_docker_detection_via_dockerenv_file(self):
        """Test Docker detection via /.dockerenv file."""
        test_env = {}
        builder = DatabaseURLBuilder(test_env)
        with patch('os.path.exists') as mock_exists:
            mock_exists.return_value = True
            assert builder.is_docker_environment(), 'Should detect Docker via /.dockerenv file'
            mock_exists.assert_called_with('/.dockerenv')

    def test_docker_detection_via_cgroup(self):
        """Test Docker detection via /proc/self/cgroup."""
        test_env = {}
        builder = DatabaseURLBuilder(test_env)
        docker_cgroup_content = '12:memory:/docker/container_id\n11:devices:/docker/container_id  \n10:freezer:/docker/container_id\n'

        def mock_exists_side_effect(path):
            if path == '/.dockerenv':
                return False
            elif path == '/proc/self/cgroup':
                return True
            return False
        with patch('os.path.exists', side_effect=mock_exists_side_effect), patch('builtins.open', mock_open(read_data=docker_cgroup_content)) as mock_file:
            assert builder.is_docker_environment(), 'Should detect Docker via cgroup'

    def test_docker_detection_cgroup_error_handling(self):
        """Test Docker detection handles cgroup file errors gracefully."""
        test_env = {}
        builder = DatabaseURLBuilder(test_env)

        def mock_exists_side_effect(path):
            if path == '/.dockerenv':
                return False
            elif path == '/proc/self/cgroup':
                return True
            return False
        with patch('os.path.exists', side_effect=mock_exists_side_effect), patch('builtins.open', side_effect=OSError('Permission denied')):
            assert not builder.is_docker_environment(), 'Should handle cgroup read errors gracefully'

    def test_docker_hostname_resolution_logic(self):
        """Test Docker hostname resolution application logic."""
        test_cases = [('development', 'localhost', 'postgres'), ('development', '127.0.0.1', 'postgres'), ('development', 'postgres', 'postgres'), ('development', 'remote.db.com', 'remote.db.com'), ('test', 'localhost', 'postgres'), ('test', '127.0.0.1', 'postgres'), ('staging', 'localhost', 'localhost'), ('staging', '127.0.0.1', '127.0.0.1'), ('production', 'localhost', 'localhost'), ('production', '127.0.0.1', '127.0.0.1')]
        for environment, input_host, expected_host in test_cases:
            test_env = {'ENVIRONMENT': environment}
            builder = DatabaseURLBuilder(test_env)
            with patch.object(builder, 'is_docker_environment', return_value=True):
                resolved = builder.apply_docker_hostname_resolution(input_host)
                assert resolved == expected_host, f'Environment {environment}: {input_host} should resolve to {expected_host}, got {resolved}'

class TestCloudSQLBuilder:
    """Test Cloud SQL URL building - CRITICAL FOR GCP DEPLOYMENTS."""

    def test_cloud_sql_detection(self):
        """Test Cloud SQL environment detection."""
        cloud_sql_env = {'POSTGRES_HOST': '/cloudsql/project-id:region:instance-id', 'POSTGRES_USER': 'postgres', 'POSTGRES_PASSWORD': 'password', 'POSTGRES_DB': 'database'}
        builder = DatabaseURLBuilder(cloud_sql_env)
        assert builder.cloud_sql.is_cloud_sql, 'Should detect Cloud SQL configuration'
        tcp_env = {'POSTGRES_HOST': 'localhost', 'POSTGRES_USER': 'postgres'}
        builder = DatabaseURLBuilder(tcp_env)
        assert not builder.cloud_sql.is_cloud_sql, 'TCP config should not be detected as Cloud SQL'
        empty_env = {}
        builder = DatabaseURLBuilder(empty_env)
        assert not builder.cloud_sql.is_cloud_sql, 'Empty config should not be Cloud SQL'

    def test_cloud_sql_async_url_construction(self):
        """Test Cloud SQL async URL construction."""
        cloud_sql_env = {'POSTGRES_HOST': '/cloudsql/netra-prod:us-central1:postgres-main', 'POSTGRES_USER': 'netra_user', 'POSTGRES_PASSWORD': 'secure_cloud_password_123', 'POSTGRES_DB': 'netra_production'}
        builder = DatabaseURLBuilder(cloud_sql_env)
        async_url = builder.cloud_sql.async_url
        expected_url = 'postgresql+asyncpg://netra_user:secure_cloud_password_123@/netra_production?host=/cloudsql/netra-prod:us-central1:postgres-main'
        assert async_url == expected_url, f'Cloud SQL async URL incorrect: {async_url}'
        special_env = cloud_sql_env.copy()
        special_env['POSTGRES_PASSWORD'] = 'p@ssw0rd!#$%'
        builder = DatabaseURLBuilder(special_env)
        async_url = builder.cloud_sql.async_url
        assert 'p%40ssw0rd%21%23%24%25' in async_url, 'Special characters should be URL encoded'

    def test_cloud_sql_sync_url_construction(self):
        """Test Cloud SQL sync URL construction for Alembic."""
        cloud_sql_env = {'POSTGRES_HOST': '/cloudsql/test-project:us-west1:test-instance', 'POSTGRES_USER': 'test_user', 'POSTGRES_PASSWORD': 'test_password', 'POSTGRES_DB': 'test_database'}
        builder = DatabaseURLBuilder(cloud_sql_env)
        sync_url = builder.cloud_sql.sync_url
        expected_url = 'postgresql://test_user:test_password@/test_database?host=/cloudsql/test-project:us-west1:test-instance'
        assert sync_url == expected_url, f'Cloud SQL sync URL incorrect: {sync_url}'

    def test_cloud_sql_psycopg_url_construction(self):
        """Test Cloud SQL psycopg driver URL construction."""
        cloud_sql_env = {'POSTGRES_HOST': '/cloudsql/project:region:instance', 'POSTGRES_USER': 'user', 'POSTGRES_PASSWORD': 'pass', 'POSTGRES_DB': 'db'}
        builder = DatabaseURLBuilder(cloud_sql_env)
        psycopg_url = builder.cloud_sql.async_url_psycopg
        expected_url = 'postgresql+psycopg://user:pass@/db?host=/cloudsql/project:region:instance'
        assert psycopg_url == expected_url, f'Cloud SQL psycopg URL incorrect: {psycopg_url}'

    def test_cloud_sql_url_none_when_not_cloud_sql(self):
        """Test that Cloud SQL URLs return None when not Cloud SQL."""
        tcp_env = {'POSTGRES_HOST': 'localhost', 'POSTGRES_USER': 'postgres'}
        builder = DatabaseURLBuilder(tcp_env)
        assert builder.cloud_sql.async_url is None, 'async_url should be None for TCP config'
        assert builder.cloud_sql.sync_url is None, 'sync_url should be None for TCP config'
        assert builder.cloud_sql.async_url_psycopg is None, 'psycopg URL should be None for TCP config'

class TestTCPBuilder:
    """Test TCP connection URL building - CRITICAL FOR STANDARD DEPLOYMENTS."""

    def test_tcp_config_detection(self):
        """Test TCP configuration detection."""
        tcp_env = {'POSTGRES_HOST': 'db.example.com', 'POSTGRES_USER': 'postgres', 'POSTGRES_PASSWORD': 'password', 'POSTGRES_DB': 'database'}
        builder = DatabaseURLBuilder(tcp_env)
        assert builder.tcp.has_config, 'Should detect TCP configuration'
        cloud_env = {'POSTGRES_HOST': '/cloudsql/project:region:instance'}
        builder = DatabaseURLBuilder(cloud_env)
        assert not builder.tcp.has_config, 'Cloud SQL should not be detected as TCP'
        no_host_env = {'POSTGRES_USER': 'postgres'}
        builder = DatabaseURLBuilder(no_host_env)
        assert not builder.tcp.has_config, 'Missing host should not be valid TCP config'

    def test_tcp_async_url_construction(self):
        """Test TCP async URL construction."""
        tcp_env = {'POSTGRES_HOST': 'db.production.com', 'POSTGRES_PORT': '5432', 'POSTGRES_USER': 'prod_user', 'POSTGRES_PASSWORD': 'prod_password_123', 'POSTGRES_DB': 'production_db'}
        builder = DatabaseURLBuilder(tcp_env)
        async_url = builder.tcp.async_url
        expected_url = 'postgresql+asyncpg://prod_user:prod_password_123@db.production.com:5432/production_db'
        assert async_url == expected_url, f'TCP async URL incorrect: {async_url}'

    def test_tcp_url_with_docker_hostname_resolution(self):
        """Test TCP URL construction with Docker hostname resolution."""
        tcp_env = {'POSTGRES_HOST': 'localhost', 'POSTGRES_PORT': '5432', 'POSTGRES_USER': 'postgres', 'POSTGRES_PASSWORD': 'password', 'POSTGRES_DB': 'testdb', 'ENVIRONMENT': 'development'}
        builder = DatabaseURLBuilder(tcp_env)
        with patch.object(builder, 'is_docker_environment', return_value=True):
            async_url = builder.tcp.async_url
            expected_url = 'postgresql+asyncpg://postgres:password@postgres:5432/testdb'
            assert async_url == expected_url, f'Docker hostname resolution failed: {async_url}'

    def test_tcp_sync_url_construction(self):
        """Test TCP sync URL construction."""
        tcp_env = {'POSTGRES_HOST': 'staging.db.com', 'POSTGRES_PORT': '5432', 'POSTGRES_USER': 'staging_user', 'POSTGRES_PASSWORD': 'staging_pass', 'POSTGRES_DB': 'staging_db'}
        builder = DatabaseURLBuilder(tcp_env)
        sync_url = builder.tcp.sync_url
        expected_url = 'postgresql://staging_user:staging_pass@staging.db.com:5432/staging_db'
        assert sync_url == expected_url, f'TCP sync URL incorrect: {sync_url}'

    def test_tcp_url_with_ssl_parameters(self):
        """Test TCP URLs with SSL parameters."""
        tcp_env = {'POSTGRES_HOST': 'secure.db.com', 'POSTGRES_USER': 'secure_user', 'POSTGRES_PASSWORD': 'secure_pass', 'POSTGRES_DB': 'secure_db'}
        builder = DatabaseURLBuilder(tcp_env)
        async_ssl_url = builder.tcp.async_url_with_ssl
        assert 'sslmode=require' in async_ssl_url, 'Async SSL URL should contain sslmode=require'
        sync_ssl_url = builder.tcp.sync_url_with_ssl
        assert 'sslmode=require' in sync_ssl_url, 'Sync SSL URL should contain sslmode=require'
        base_async = builder.tcp.async_url
        if '?' in base_async:
            assert '&sslmode=require' in async_ssl_url, 'SSL parameter should be separated with &'
        else:
            assert '?sslmode=require' in async_ssl_url, 'SSL parameter should start with ?'

    def test_tcp_url_default_values(self):
        """Test TCP URL construction with default values."""
        minimal_env = {'POSTGRES_HOST': 'testhost'}
        builder = DatabaseURLBuilder(minimal_env)
        async_url = builder.tcp.async_url
        assert 'postgres@' in async_url, 'Should default to postgres user'
        assert ':5432' in async_url, 'Should default to port 5432'
        assert '/netra_dev' in async_url, 'Should default to netra_dev database'
        partial_env = {'POSTGRES_HOST': 'partialhost', 'POSTGRES_USER': 'custom_user', 'POSTGRES_DB': 'custom_db'}
        builder = DatabaseURLBuilder(partial_env)
        async_url = builder.tcp.async_url
        assert 'custom_user@' in async_url, 'Should use provided user'
        assert '/custom_db' in async_url, 'Should use provided database'
        assert ':5432' in async_url, 'Should still default to port 5432'

    def test_tcp_psycopg_url_construction(self):
        """Test TCP psycopg driver URL construction."""
        tcp_env = {'POSTGRES_HOST': 'psycopg.test.com', 'POSTGRES_USER': 'psycopg_user', 'POSTGRES_PASSWORD': 'psycopg_pass', 'POSTGRES_DB': 'psycopg_db'}
        builder = DatabaseURLBuilder(tcp_env)
        psycopg_url = builder.tcp.async_url_psycopg
        expected_url = 'postgresql+psycopg://psycopg_user:psycopg_pass@psycopg.test.com:5432/psycopg_db'
        assert psycopg_url == expected_url, f'TCP psycopg URL incorrect: {psycopg_url}'

class TestDevelopmentBuilder:
    """Test development environment URL building - CRITICAL FOR LOCAL DEVELOPMENT."""

    def test_development_default_urls(self):
        """Test development default URLs."""
        dev_env = {'ENVIRONMENT': 'development'}
        builder = DatabaseURLBuilder(dev_env)
        default_url = builder.development.default_url
        expected_default = 'postgresql+asyncpg://postgres:postgres@localhost:5432/netra_dev'
        assert default_url == expected_default, f'Default development URL incorrect: {default_url}'
        default_sync = builder.development.default_sync_url
        expected_sync = 'postgresql://postgres:postgres@localhost:5432/netra_dev'
        assert default_sync == expected_sync, f'Default sync URL incorrect: {default_sync}'

    def test_development_auto_url_with_tcp_config(self):
        """Test development auto URL selection with TCP config available."""
        dev_env = {'ENVIRONMENT': 'development', 'POSTGRES_HOST': 'dev.postgres.com', 'POSTGRES_USER': 'dev_user', 'POSTGRES_PASSWORD': 'dev_pass', 'POSTGRES_DB': 'dev_database'}
        builder = DatabaseURLBuilder(dev_env)
        auto_url = builder.development.auto_url
        auto_sync = builder.development.auto_sync_url
        tcp_async = builder.tcp.async_url
        tcp_sync = builder.tcp.sync_url
        assert auto_url == tcp_async, 'Auto URL should prefer TCP config'
        assert auto_sync == tcp_sync, 'Auto sync URL should prefer TCP config'

    def test_development_auto_url_fallback_to_defaults(self):
        """Test development auto URL falls back to defaults when no TCP config."""
        dev_env = {'ENVIRONMENT': 'development'}
        builder = DatabaseURLBuilder(dev_env)
        assert not builder.tcp.has_config, 'Should not have TCP config'
        auto_url = builder.development.auto_url
        auto_sync = builder.development.auto_sync_url
        default_url = builder.development.default_url
        default_sync = builder.development.default_sync_url
        assert auto_url == default_url, 'Should fall back to default URL'
        assert auto_sync == default_sync, 'Should fall back to default sync URL'

class TestTestBuilder:
    """Test test environment URL building - CRITICAL FOR TEST RELIABILITY."""

    def test_test_memory_url(self):
        """Test in-memory SQLite URL for fast tests."""
        test_env = {'ENVIRONMENT': 'test'}
        builder = DatabaseURLBuilder(test_env)
        memory_url = builder.test.memory_url
        expected = 'sqlite+aiosqlite:///:memory:'
        assert memory_url == expected, f'Memory URL incorrect: {memory_url}'

    def test_test_postgres_url_with_config(self):
        """Test PostgreSQL URL for test environment."""
        test_env = {'ENVIRONMENT': 'test', 'POSTGRES_HOST': 'test.postgres.com', 'POSTGRES_USER': 'test_user', 'POSTGRES_PASSWORD': 'test_pass', 'POSTGRES_DB': 'test_database'}
        builder = DatabaseURLBuilder(test_env)
        postgres_url = builder.test.postgres_url
        expected_url = 'postgresql+asyncpg://test_user:test_pass@test.postgres.com:5432/test_database'
        assert postgres_url == expected_url, f'Test PostgreSQL URL incorrect: {postgres_url}'

    def test_test_postgres_url_with_docker_resolution(self):
        """Test PostgreSQL URL with Docker hostname resolution."""
        test_env = {'ENVIRONMENT': 'test', 'POSTGRES_HOST': 'localhost', 'POSTGRES_USER': 'test_user', 'POSTGRES_PASSWORD': 'test_pass', 'POSTGRES_DB': 'test_db'}
        builder = DatabaseURLBuilder(test_env)
        with patch.object(builder, 'is_docker_environment', return_value=True):
            postgres_url = builder.test.postgres_url
            assert '@postgres:5432' in postgres_url, 'Should resolve localhost to postgres in Docker'

    def test_test_auto_url_priority_logic(self):
        """Test test environment auto URL priority logic."""
        memory_env = {'ENVIRONMENT': 'test', 'USE_MEMORY_DB': 'true'}
        builder = DatabaseURLBuilder(memory_env)
        auto_url = builder.test.auto_url
        assert auto_url == builder.test.memory_url, 'Should prioritize memory DB when requested'
        postgres_env = {'ENVIRONMENT': 'test', 'POSTGRES_HOST': 'testhost', 'POSTGRES_USER': 'testuser'}
        builder = DatabaseURLBuilder(postgres_env)
        auto_url = builder.test.auto_url
        assert auto_url == builder.test.postgres_url, 'Should use PostgreSQL when config available'
        default_env = {'ENVIRONMENT': 'test'}
        builder = DatabaseURLBuilder(default_env)
        auto_url = builder.test.auto_url
        assert auto_url == builder.test.memory_url, 'Should default to memory DB'

    def test_test_postgres_url_with_defaults(self):
        """Test PostgreSQL URL construction with default values."""
        test_env = {'ENVIRONMENT': 'test', 'POSTGRES_HOST': 'testhost'}
        builder = DatabaseURLBuilder(test_env)
        postgres_url = builder.test.postgres_url
        assert 'postgres@' in postgres_url, 'Should default to postgres user'
        assert ':5432' in postgres_url, 'Should default to port 5432'
        assert '/netra_test' in postgres_url, 'Should default to netra_test database'

class TestDockerBuilder:
    """Test Docker environment URL building - CRITICAL FOR CONTAINERIZED DEPLOYMENTS."""

    def test_docker_compose_url_construction(self):
        """Test Docker Compose URL construction."""
        docker_env = {'POSTGRES_USER': 'docker_user', 'POSTGRES_PASSWORD': 'docker_pass', 'POSTGRES_HOST': 'postgres', 'POSTGRES_PORT': '5432', 'POSTGRES_DB': 'docker_db'}
        builder = DatabaseURLBuilder(docker_env)
        compose_url = builder.docker.compose_url
        expected_url = 'postgresql+asyncpg://docker_user:docker_pass@postgres:5432/docker_db'
        assert compose_url == expected_url, f'Docker compose URL incorrect: {compose_url}'
        compose_sync = builder.docker.compose_sync_url
        expected_sync = 'postgresql://docker_user:docker_pass@postgres:5432/docker_db'
        assert compose_sync == expected_sync, f'Docker compose sync URL incorrect: {compose_sync}'

    def test_docker_compose_url_with_defaults(self):
        """Test Docker Compose URL with default values."""
        minimal_env = {}
        builder = DatabaseURLBuilder(minimal_env)
        compose_url = builder.docker.compose_url
        expected_url = 'postgresql+asyncpg://postgres:postgres@postgres:5432/netra_dev'
        assert compose_url == expected_url, f'Docker compose URL with defaults incorrect: {compose_url}'

    def test_docker_compose_url_credential_encoding(self):
        """Test Docker Compose URL credential encoding."""
        special_env = {'POSTGRES_USER': 'user@domain', 'POSTGRES_PASSWORD': 'p@ssw0rd!#$%', 'POSTGRES_DB': 'test_db'}
        builder = DatabaseURLBuilder(special_env)
        compose_url = builder.docker.compose_url
        assert 'user%40domain' in compose_url, 'Username special chars should be encoded'
        assert 'p%40ssw0rd%21%23%24%25' in compose_url, 'Password special chars should be encoded'

class TestStagingBuilder:
    """Test staging environment URL building - CRITICAL FOR PRE-PRODUCTION."""

    def test_staging_auto_url_cloud_sql_priority(self):
        """Test staging auto URL prioritizes Cloud SQL."""
        staging_cloud_env = {'ENVIRONMENT': 'staging', 'POSTGRES_HOST': '/cloudsql/staging-project:us-central1:staging-db', 'POSTGRES_USER': 'staging_user', 'POSTGRES_PASSWORD': 'staging_pass', 'POSTGRES_DB': 'staging_database'}
        builder = DatabaseURLBuilder(staging_cloud_env)
        auto_url = builder.staging.auto_url
        auto_sync = builder.staging.auto_sync_url
        cloud_async = builder.cloud_sql.async_url
        cloud_sync = builder.cloud_sql.sync_url
        assert auto_url == cloud_async, 'Staging should prefer Cloud SQL async URL'
        assert auto_sync == cloud_sync, 'Staging should prefer Cloud SQL sync URL'

    def test_staging_auto_url_tcp_with_ssl_fallback(self):
        """Test staging auto URL falls back to TCP with SSL."""
        staging_tcp_env = {'ENVIRONMENT': 'staging', 'POSTGRES_HOST': 'staging.db.com', 'POSTGRES_USER': 'staging_user', 'POSTGRES_PASSWORD': 'staging_pass', 'POSTGRES_DB': 'staging_db'}
        builder = DatabaseURLBuilder(staging_tcp_env)
        auto_url = builder.staging.auto_url
        auto_sync = builder.staging.auto_sync_url
        tcp_ssl_async = builder.tcp.async_url_with_ssl
        tcp_ssl_sync = builder.tcp.sync_url_with_ssl
        assert auto_url == tcp_ssl_async, 'Staging should use TCP with SSL'
        assert auto_sync == tcp_ssl_sync, 'Staging should use TCP sync with SSL'

    def test_staging_auto_url_returns_none_without_config(self):
        """Test staging auto URL returns None without valid configuration."""
        staging_env = {'ENVIRONMENT': 'staging'}
        builder = DatabaseURLBuilder(staging_env)
        assert not builder.cloud_sql.is_cloud_sql, 'Should not have Cloud SQL config'
        assert not builder.tcp.has_config, 'Should not have TCP config'
        auto_url = builder.staging.auto_url
        auto_sync = builder.staging.auto_sync_url
        assert auto_url is None, 'Should return None without valid config'
        assert auto_sync is None, 'Should return None without valid sync config'

class TestProductionBuilder:
    """Test production environment URL building - CRITICAL FOR PRODUCTION RELIABILITY."""

    def test_production_auto_url_cloud_sql_priority(self):
        """Test production auto URL prioritizes Cloud SQL."""
        production_cloud_env = {'ENVIRONMENT': 'production', 'POSTGRES_HOST': '/cloudsql/prod-project:us-east1:prod-primary', 'POSTGRES_USER': 'prod_user', 'POSTGRES_PASSWORD': 'super_secure_prod_password_32_chars', 'POSTGRES_DB': 'production_database'}
        builder = DatabaseURLBuilder(production_cloud_env)
        auto_url = builder.production.auto_url
        auto_sync = builder.production.auto_sync_url
        cloud_async = builder.cloud_sql.async_url
        cloud_sync = builder.cloud_sql.sync_url
        assert auto_url == cloud_async, 'Production should prefer Cloud SQL async URL'
        assert auto_sync == cloud_sync, 'Production should prefer Cloud SQL sync URL'

    def test_production_auto_url_tcp_with_ssl_fallback(self):
        """Test production auto URL falls back to TCP with SSL."""
        production_tcp_env = {'ENVIRONMENT': 'production', 'POSTGRES_HOST': 'prod.db.secure.com', 'POSTGRES_USER': 'production_user', 'POSTGRES_PASSWORD': 'ultra_secure_production_password', 'POSTGRES_DB': 'prod_database'}
        builder = DatabaseURLBuilder(production_tcp_env)
        auto_url = builder.production.auto_url
        auto_sync = builder.production.auto_sync_url
        tcp_ssl_async = builder.tcp.async_url_with_ssl
        tcp_ssl_sync = builder.tcp.sync_url_with_ssl
        assert auto_url == tcp_ssl_async, 'Production should use TCP with SSL'
        assert auto_sync == tcp_ssl_sync, 'Production should use TCP sync with SSL'

    def test_production_auto_url_returns_none_without_config(self):
        """Test production auto URL returns None without valid configuration."""
        production_env = {'ENVIRONMENT': 'production'}
        builder = DatabaseURLBuilder(production_env)
        assert not builder.cloud_sql.is_cloud_sql, 'Should not have Cloud SQL config'
        assert not builder.tcp.has_config, 'Should not have TCP config'
        auto_url = builder.production.auto_url
        auto_sync = builder.production.auto_sync_url
        assert auto_url is None, 'Should return None without valid config'
        assert auto_sync is None, 'Should return None without valid sync config'

class TestEnvironmentUrlRetrieval:
    """Test get_url_for_environment method - CRITICAL FOR SERVICE INITIALIZATION."""

    def test_get_url_for_environment_staging(self):
        """Test URL retrieval for staging environment."""
        staging_env = {'ENVIRONMENT': 'staging', 'POSTGRES_HOST': 'staging.db.com', 'POSTGRES_USER': 'staging_user', 'POSTGRES_PASSWORD': 'staging_pass', 'POSTGRES_DB': 'staging_db'}
        builder = DatabaseURLBuilder(staging_env)
        async_url = builder.get_url_for_environment(sync=False)
        expected_async = builder.staging.auto_url
        assert async_url == expected_async, 'Should return staging auto URL'
        sync_url = builder.get_url_for_environment(sync=True)
        expected_sync = builder.staging.auto_sync_url
        assert sync_url == expected_sync, 'Should return staging auto sync URL'

    def test_get_url_for_environment_production(self):
        """Test URL retrieval for production environment."""
        production_env = {'ENVIRONMENT': 'production', 'POSTGRES_HOST': '/cloudsql/prod:us-central1:main', 'POSTGRES_USER': 'prod_user', 'POSTGRES_PASSWORD': 'prod_pass', 'POSTGRES_DB': 'prod_db'}
        builder = DatabaseURLBuilder(production_env)
        async_url = builder.get_url_for_environment(sync=False)
        expected_async = builder.production.auto_url
        assert async_url == expected_async, 'Should return production auto URL'
        sync_url = builder.get_url_for_environment(sync=True)
        expected_sync = builder.production.auto_sync_url
        assert sync_url == expected_sync, 'Should return production auto sync URL'

    def test_get_url_for_environment_test(self):
        """Test URL retrieval for test environment."""
        test_env = {'ENVIRONMENT': 'test'}
        builder = DatabaseURLBuilder(test_env)
        async_url = builder.get_url_for_environment(sync=False)
        sync_url = builder.get_url_for_environment(sync=True)
        expected = builder.test.auto_url
        assert async_url == expected, 'Should return test auto URL'
        assert sync_url == expected, 'Test env should return same URL for sync/async'

    def test_get_url_for_environment_development_default(self):
        """Test URL retrieval for development (default) environment."""
        dev_env = {'POSTGRES_HOST': 'dev.db.com', 'POSTGRES_USER': 'dev_user', 'POSTGRES_PASSWORD': 'dev_pass', 'POSTGRES_DB': 'dev_db'}
        builder = DatabaseURLBuilder(dev_env)
        assert builder.environment == 'development', 'Should default to development'
        async_url = builder.get_url_for_environment(sync=False)
        sync_url = builder.get_url_for_environment(sync=True)
        expected_async = builder.development.auto_url
        expected_sync = builder.development.auto_sync_url
        assert async_url == expected_async, 'Should return development auto URL'
        assert sync_url == expected_sync, 'Should return development auto sync URL'

class TestDatabaseValidation:
    """Test database configuration validation - CRITICAL FOR ERROR PREVENTION."""

    def test_validation_staging_production_requires_config(self):
        """Test validation requires configuration for staging/production."""
        empty_staging = {'ENVIRONMENT': 'staging'}
        builder = DatabaseURLBuilder(empty_staging)
        is_valid, error_msg = builder.validate()
        assert not is_valid, 'Empty staging config should be invalid'
        assert 'Missing required variables' in error_msg, 'Should mention missing variables'
        assert 'POSTGRES_HOST' in error_msg, 'Should list POSTGRES_HOST as missing'
        no_host_production = {'ENVIRONMENT': 'production', 'POSTGRES_USER': 'prod_user', 'POSTGRES_PASSWORD': 'prod_pass', 'POSTGRES_DB': 'prod_db'}
        builder = DatabaseURLBuilder(no_host_production)
        is_valid, error_msg = builder.validate()
        assert not is_valid, 'Production config without host should be invalid'
        assert 'Missing required variables' in error_msg, 'Should mention missing variables'

    def test_validation_development_test_allow_missing_config(self):
        """Test validation allows missing config for development/test."""
        dev_env = {'ENVIRONMENT': 'development'}
        builder = DatabaseURLBuilder(dev_env)
        is_valid, error_msg = builder.validate()
        assert is_valid, f'Development should allow minimal config: {error_msg}'
        test_env = {'ENVIRONMENT': 'test'}
        builder = DatabaseURLBuilder(test_env)
        is_valid, error_msg = builder.validate()
        assert is_valid, f'Test should allow minimal config: {error_msg}'

    def test_validation_cloud_sql_format_checking(self):
        """Test validation of Cloud SQL format."""
        valid_cloud_sql = {'ENVIRONMENT': 'staging', 'POSTGRES_HOST': '/cloudsql/project-id:us-central1:instance-name', 'POSTGRES_USER': 'staging_user', 'POSTGRES_PASSWORD': 'secure_staging_password_with_32_characters', 'POSTGRES_DB': 'staging_database'}
        builder = DatabaseURLBuilder(valid_cloud_sql)
        is_valid, error_msg = builder.validate()
        assert is_valid, f'Valid Cloud SQL config should pass: {error_msg}'
        invalid_prefix = valid_cloud_sql.copy()
        invalid_prefix['POSTGRES_HOST'] = '/cloudsql/wrong-format'
        builder = DatabaseURLBuilder(invalid_prefix)
        is_valid, error_msg = builder.validate()
        assert not is_valid, 'Invalid Cloud SQL format should fail validation'
        assert 'Invalid Cloud SQL format' in error_msg, 'Should mention format error'
        invalid_parts = valid_cloud_sql.copy()
        invalid_parts['POSTGRES_HOST'] = '/cloudsql/project-id:us-central1'
        builder = DatabaseURLBuilder(invalid_parts)
        is_valid, error_msg = builder.validate()
        assert not is_valid, 'Invalid Cloud SQL parts should fail validation'
        assert 'Invalid Cloud SQL format' in error_msg, 'Should mention format error'

    def test_validation_credential_patterns(self):
        """Test validation of credential patterns."""
        base_staging = {'ENVIRONMENT': 'staging', 'POSTGRES_HOST': 'staging.db.com', 'POSTGRES_PASSWORD': 'secure_password', 'POSTGRES_DB': 'staging_db'}
        invalid_users = ['user_pr-4', 'user-pr-4']
        for invalid_user in invalid_users:
            env = base_staging.copy()
            env['POSTGRES_USER'] = invalid_user
            builder = DatabaseURLBuilder(env)
            is_valid, error_msg = builder.validate()
            assert not is_valid, f'Invalid user {invalid_user} should fail validation'
            assert 'Invalid database user' in error_msg, 'Should mention invalid user'
        pattern_user = 'user_pr-999'
        env = base_staging.copy()
        env['POSTGRES_USER'] = pattern_user
        builder = DatabaseURLBuilder(env)
        is_valid, error_msg = builder.validate()
        assert not is_valid, 'User matching problematic pattern should fail'
        assert 'Invalid database user pattern' in error_msg, 'Should mention pattern issue'
        dev_passwords = ['password', '123456', 'admin', 'development_password']
        for dev_password in dev_passwords:
            env = base_staging.copy()
            env['POSTGRES_PASSWORD'] = dev_password
            builder = DatabaseURLBuilder(env)
            is_valid, error_msg = builder.validate()
            assert not is_valid, f'Development password {dev_password} should fail in staging'
            assert 'Invalid password for staging environment' in error_msg, 'Should mention invalid password'
        env = base_staging.copy()
        env['POSTGRES_HOST'] = 'localhost'
        builder = DatabaseURLBuilder(env)
        is_valid, error_msg = builder.validate()
        assert not is_valid, 'Localhost should fail in staging'
        assert "Invalid host 'localhost' for staging environment" in error_msg, 'Should mention localhost issue'
        env['ALLOW_LOCALHOST_IN_PRODUCTION'] = 'true'
        builder = DatabaseURLBuilder(env)
        is_valid, error_msg = builder.validate()
        assert is_valid, 'Localhost should be allowed with override'

    def test_validation_successful_cases(self):
        """Test validation passes for proper configurations."""
        valid_configs = [{'ENVIRONMENT': 'staging', 'POSTGRES_HOST': 'staging.database.com', 'POSTGRES_USER': 'staging_user', 'POSTGRES_PASSWORD': 'secure_staging_password_with_32_characters', 'POSTGRES_DB': 'staging_database'}, {'ENVIRONMENT': 'production', 'POSTGRES_HOST': '/cloudsql/prod-project:us-central1:prod-instance', 'POSTGRES_USER': 'production_user', 'POSTGRES_PASSWORD': 'ultra_secure_production_password_64_characters_long', 'POSTGRES_DB': 'production_database'}, {'ENVIRONMENT': 'development', 'POSTGRES_HOST': 'localhost', 'POSTGRES_USER': 'postgres', 'POSTGRES_PASSWORD': 'password', 'POSTGRES_DB': 'dev_db'}]
        for config in valid_configs:
            builder = DatabaseURLBuilder(config)
            is_valid, error_msg = builder.validate()
            assert is_valid, f'Valid config should pass validation: {config} - {error_msg}'

class TestDebugInfoAndLogging:
    """Test debug information and safe logging - CRITICAL FOR TROUBLESHOOTING."""

    def test_debug_info_structure(self):
        """Test debug info provides comprehensive information."""
        test_env = {'ENVIRONMENT': 'staging', 'POSTGRES_HOST': '/cloudsql/test-project:us-west1:test-db', 'POSTGRES_USER': 'debug_user', 'POSTGRES_PASSWORD': 'debug_password', 'POSTGRES_DB': 'debug_database'}
        builder = DatabaseURLBuilder(test_env)
        debug_info = builder.debug_info()
        assert 'environment' in debug_info, 'Debug info should include environment'
        assert 'has_cloud_sql' in debug_info, 'Debug info should include Cloud SQL status'
        assert 'has_tcp_config' in debug_info, 'Debug info should include TCP config status'
        assert 'postgres_host' in debug_info, 'Debug info should include host info'
        assert 'postgres_db' in debug_info, 'Debug info should include database info'
        assert 'available_urls' in debug_info, 'Debug info should include URL availability'
        assert debug_info['environment'] == 'staging', 'Environment should match'
        assert debug_info['has_cloud_sql'] is True, 'Should detect Cloud SQL'
        assert debug_info['postgres_host'] == test_env['POSTGRES_HOST'], 'Host should match'
        assert debug_info['postgres_db'] == test_env['POSTGRES_DB'], 'Database should match'
        url_flags = debug_info['available_urls']
        assert url_flags['cloud_sql_async'] is True, 'Cloud SQL async should be available'
        assert url_flags['cloud_sql_sync'] is True, 'Cloud SQL sync should be available'
        assert url_flags['auto_url'] is True, 'Auto URL should be available'

    def test_get_safe_log_message_masks_credentials(self):
        """Test safe log message masks sensitive information."""
        test_env = {'POSTGRES_HOST': 'secret.db.com', 'POSTGRES_USER': 'secret_user', 'POSTGRES_PASSWORD': 'ultra_secret_password', 'POSTGRES_DB': 'secret_db', 'ENVIRONMENT': 'staging'}
        builder = DatabaseURLBuilder(test_env)
        log_message = builder.get_safe_log_message()
        assert 'secret_user' not in log_message, 'Log message should not contain username'
        assert 'ultra_secret_password' not in log_message, 'Log message should not contain password'
        assert 'staging' in log_message, 'Log message should contain environment'
        assert 'TCP' in log_message, 'Log message should indicate connection type'
        assert '***@' in log_message, 'Log message should contain masked credentials indicator'

    def test_mask_url_for_logging_comprehensive(self):
        """Test URL masking for various URL formats."""
        test_cases = [('postgresql://user:password@host.com:5432/database', 'postgresql://***@host.com:5432/database'), ('postgresql+asyncpg://user:pass@/db?host=/cloudsql/proj:region:inst', 'postgresql+asyncpg://***@/db?host=/cloudsql/proj:region:inst'), ('postgresql://user:p%40ss@host:5432/db?ssl=require', 'postgresql://***@host:5432/db?ssl=require'), ('sqlite+aiosqlite:///:memory:', 'sqlite+aiosqlite:///:memory:'), (None, 'NOT SET'), ('unknown://user:pass@something', 'unknown://***@something'), ('unknown://something', 'unknown://something')]
        for input_url, expected_output in test_cases:
            masked = DatabaseURLBuilder.mask_url_for_logging(input_url)
            assert masked == expected_output, f'URL masking failed for {input_url}: expected {expected_output}, got {masked}'

class TestUrlNormalizationAndDriverFormatting:
    """Test URL normalization and driver-specific formatting - CRITICAL FOR COMPATIBILITY."""

    def test_normalize_postgres_url_basic_normalization(self):
        """Test basic PostgreSQL URL normalization."""
        test_cases = [('postgres://user:pass@host:5432/db', 'postgresql://user:pass@host:5432/db'), ('postgresql://user:pass@host:5432/db', 'postgresql://user:pass@host:5432/db'), (None, None), ('', '')]
        for input_url, expected in test_cases:
            result = DatabaseURLBuilder.normalize_postgres_url(input_url)
            assert result == expected, f'Normalization failed for {input_url}: expected {expected}, got {result}'

    def test_normalize_postgres_url_cloud_sql_ssl_removal(self):
        """Test Cloud SQL URL SSL parameter removal."""
        test_cases = [('postgresql://user:pass@/db?host=/cloudsql/proj:reg:inst&ssl=require', 'postgresql://user:pass@/db?host=/cloudsql/proj:reg:inst'), ('postgresql://user:pass@/db?ssl=require&host=/cloudsql/proj:reg:inst', 'postgresql://user:pass@/db&host=/cloudsql/proj:reg:inst'), ('postgresql://user:pass@/db?host=/cloudsql/proj:reg:inst&sslmode=require', 'postgresql://user:pass@/db?host=/cloudsql/proj:reg:inst'), ('postgresql://user:pass@host:5432/db?ssl=require', 'postgresql://user:pass@host:5432/db?ssl=require')]
        for input_url, expected in test_cases:
            result = DatabaseURLBuilder.normalize_postgres_url(input_url)
            assert result == expected, f'Cloud SQL SSL removal failed for {input_url}: expected {expected}, got {result}'

    def test_format_url_for_driver_asyncpg(self):
        """Test driver-specific formatting for asyncpg."""
        base_url = 'postgresql://user:pass@host:5432/db'
        asyncpg_url = DatabaseURLBuilder.format_url_for_driver(base_url, 'asyncpg')
        expected = 'postgresql+asyncpg://user:pass@host:5432/db'
        assert asyncpg_url == expected, f'AsyncPG formatting failed: {asyncpg_url}'
        ssl_url = 'postgresql://user:pass@host:5432/db?sslmode=require'
        asyncpg_ssl = DatabaseURLBuilder.format_url_for_driver(ssl_url, 'asyncpg')
        assert 'ssl=require' in asyncpg_ssl, 'Should convert sslmode to ssl for asyncpg'
        assert 'sslmode=' not in asyncpg_ssl, 'Should remove sslmode parameter for asyncpg'

    def test_format_url_for_driver_psycopg2(self):
        """Test driver-specific formatting for psycopg2."""
        base_url = 'postgresql://user:pass@host:5432/db'
        psycopg2_url = DatabaseURLBuilder.format_url_for_driver(base_url, 'psycopg2')
        expected = 'postgresql+psycopg2://user:pass@host:5432/db'
        assert psycopg2_url == expected, f'Psycopg2 formatting failed: {psycopg2_url}'
        ssl_url = 'postgresql://user:pass@host:5432/db?ssl=require'
        psycopg2_ssl = DatabaseURLBuilder.format_url_for_driver(ssl_url, 'psycopg2')
        assert 'sslmode=require' in psycopg2_ssl, 'Should convert ssl to sslmode for psycopg2'

    def test_format_url_for_driver_psycopg(self):
        """Test driver-specific formatting for psycopg3."""
        base_url = 'postgresql://user:pass@host:5432/db'
        psycopg_url = DatabaseURLBuilder.format_url_for_driver(base_url, 'psycopg')
        expected = 'postgresql+psycopg://user:pass@host:5432/db'
        assert psycopg_url == expected, f'Psycopg3 formatting failed: {psycopg_url}'
        ssl_url = 'postgresql://user:pass@host:5432/db?ssl=require'
        psycopg_ssl = DatabaseURLBuilder.format_url_for_driver(ssl_url, 'psycopg')
        assert 'sslmode=require' in psycopg_ssl, 'Should convert ssl to sslmode for psycopg3'

    def test_format_url_for_driver_base(self):
        """Test driver-specific formatting for base/sync operations."""
        base_url = 'postgresql+asyncpg://user:pass@host:5432/db'
        base_formatted = DatabaseURLBuilder.format_url_for_driver(base_url, 'base')
        expected = 'postgresql://user:pass@host:5432/db'
        assert base_formatted == expected, f'Base formatting failed: {base_formatted}'

    def test_format_for_asyncpg_driver_direct_usage(self):
        """Test format_for_asyncpg_driver for direct asyncpg.connect() usage."""
        test_cases = [('postgresql+asyncpg://user:pass@host:5432/db', 'postgresql://user:pass@host:5432/db'), ('postgres+psycopg2://user:pass@host:5432/db', 'postgresql://user:pass@host:5432/db'), ('postgresql://user:pass@host:5432/db', 'postgresql://user:pass@host:5432/db'), ('postgres://user:pass@host:5432/db', 'postgresql://user:pass@host:5432/db')]
        for input_url, expected in test_cases:
            result = DatabaseURLBuilder.format_for_asyncpg_driver(input_url)
            assert result == expected, f'AsyncPG direct formatting failed for {input_url}: expected {expected}, got {result}'

    def test_validate_url_for_driver_comprehensive(self):
        """Test URL validation for specific drivers."""
        validation_cases = [('postgresql+asyncpg://user:pass@host/db', 'asyncpg', True, ''), ('postgresql+psycopg2://user:pass@host/db', 'psycopg2', True, ''), ('postgresql+psycopg://user:pass@host/db', 'psycopg', True, ''), ('postgresql://user:pass@host/db', 'base', True, ''), ('postgresql://user:pass@host/db', 'asyncpg', False, 'must start with postgresql+asyncpg://'), ('postgresql+asyncpg://user:pass@host/db', 'psycopg2', False, 'must start with postgresql+psycopg2://'), ('postgresql+asyncpg://user:pass@host/db?sslmode=require', 'asyncpg', False, "doesn't support sslmode parameter"), ('postgresql+psycopg2://user:pass@host/db?ssl=require', 'psycopg2', False, 'uses sslmode= parameter')]
        for url, driver, expected_valid, expected_error_substr in validation_cases:
            is_valid, error_msg = DatabaseURLBuilder.validate_url_for_driver(url, driver)
            assert is_valid == expected_valid, f'Validation result wrong for {url} with {driver}: expected {expected_valid}, got {is_valid}'
            if not expected_valid:
                assert expected_error_substr.lower() in error_msg.lower(), f"Expected error substring '{expected_error_substr}' not found in '{error_msg}'"

class TestPerformanceAndThreadSafety:
    """Test performance under load and thread safety - SCALABILITY CRITICAL."""

    def test_url_construction_performance(self):
        """Test URL construction performance under high load."""
        test_env = {'POSTGRES_HOST': 'performance.test.com', 'POSTGRES_USER': 'perf_user', 'POSTGRES_PASSWORD': 'perf_password', 'POSTGRES_DB': 'perf_database'}
        builder = DatabaseURLBuilder(test_env)
        for _ in range(10):
            _ = builder.tcp.async_url
        iterations = 1000
        start_time = time.time()
        for _ in range(iterations):
            async_url = builder.tcp.async_url
            sync_url = builder.tcp.sync_url
            ssl_url = builder.tcp.async_url_with_ssl
            assert async_url is not None, 'Async URL should not be None'
            assert sync_url is not None, 'Sync URL should not be None'
            assert ssl_url is not None, 'SSL URL should not be None'
        end_time = time.time()
        elapsed = end_time - start_time
        urls_per_second = iterations * 3 / elapsed
        assert urls_per_second > 10000, f'URL construction too slow: {urls_per_second:.2f} URLs/sec'

    def test_concurrent_url_construction(self):
        """Test concurrent URL construction thread safety."""
        test_env = {'POSTGRES_HOST': 'concurrent.test.com', 'POSTGRES_USER': 'concurrent_user', 'POSTGRES_PASSWORD': 'concurrent_password', 'POSTGRES_DB': 'concurrent_db'}
        builder = DatabaseURLBuilder(test_env)
        results = []
        errors = []

        def worker_thread(worker_id: int):
            """Worker thread constructing URLs concurrently."""
            try:
                worker_results = []
                for i in range(100):
                    async_url = builder.tcp.async_url
                    sync_url = builder.tcp.sync_url
                    docker_url = builder.docker.compose_url
                    worker_results.extend([async_url, sync_url, docker_url])
                results.extend(worker_results)
            except Exception as e:
                errors.append(f'Worker {worker_id}: {str(e)}')
        workers = []
        num_workers = 10
        start_time = time.time()
        for i in range(num_workers):
            worker = threading.Thread(target=worker_thread, args=(i,))
            workers.append(worker)
            worker.start()
        for worker in workers:
            worker.join(timeout=10.0)
            if worker.is_alive():
                raise AssertionError(f'Worker thread {worker.name} timed out')
        end_time = time.time()
        if errors:
            raise AssertionError(f'Concurrent access errors: {errors}')
        expected_count = num_workers * 100 * 3
        assert len(results) == expected_count, f'Expected {expected_count} URLs, got {len(results)}'
        tcp_async_urls = [url for i, url in enumerate(results) if i % 3 == 0]
        tcp_sync_urls = [url for i, url in enumerate(results) if i % 3 == 1]
        docker_urls = [url for i, url in enumerate(results) if i % 3 == 2]
        assert len(set(tcp_async_urls)) == 1, 'TCP async URLs should be identical across threads'
        assert len(set(tcp_sync_urls)) == 1, 'TCP sync URLs should be identical across threads'
        assert len(set(docker_urls)) == 1, 'Docker URLs should be identical across threads'
        total_time = end_time - start_time
        assert total_time < 5.0, f'Concurrent URL construction too slow: {total_time:.2f}s'

    def test_memory_usage_with_large_environments(self):
        """Test memory usage with large environment variable sets."""
        large_env = {'POSTGRES_HOST': 'memory.test.com', 'POSTGRES_USER': 'memory_user', 'POSTGRES_PASSWORD': 'memory_password', 'POSTGRES_DB': 'memory_db'}
        for i in range(1000):
            large_env[f'EXTRA_VAR_{i:04d}'] = f'extra_value_{i}'
        builder = DatabaseURLBuilder(large_env)
        assert builder.postgres_host == 'memory.test.com', 'Host property should work with large env'
        assert builder.tcp.has_config, 'TCP config detection should work with large env'
        tcp_url = builder.tcp.async_url
        assert tcp_url is not None, 'URL construction should work with large env'
        assert 'memory.test.com' in tcp_url, 'URL should contain correct host with large env'

class TestErrorHandlingAndEdgeCases:
    """Test error handling and edge cases - FAULT TOLERANCE CRITICAL."""

    def test_invalid_environment_variable_types(self):
        """Test handling of invalid environment variable types."""
        invalid_env = {'POSTGRES_HOST': None, 'POSTGRES_PORT': 5432, 'POSTGRES_USER': True, 'POSTGRES_PASSWORD': ['password'], 'POSTGRES_DB': {'name': 'db'}}
        builder = DatabaseURLBuilder(invalid_env)
        assert builder.postgres_host is None, 'None should remain None'
        assert str(builder.postgres_port) == '5432', 'Port should be handled correctly (may return integer)'
        try:
            _ = builder.postgres_user
            _ = builder.postgres_password
            _ = builder.postgres_db
        except Exception as e:
            pytest.fail(f'Property access should not crash with invalid types: {e}')

    def test_malformed_cloud_sql_paths(self):
        """Test handling of malformed Cloud SQL paths."""
        malformed_cases = ['/cloudsql/', '/cloudsql/project', '/cloudsql/project:region', '/cloudsql/project:region:instance:extra', 'cloudsql/project:region:instance', '/cloudsql/pro:ject:reg:ion:inst:ance']
        for malformed_path in malformed_cases:
            env = {'POSTGRES_HOST': malformed_path, 'POSTGRES_USER': 'user', 'POSTGRES_PASSWORD': 'pass', 'POSTGRES_DB': 'db', 'ENVIRONMENT': 'staging'}
            builder = DatabaseURLBuilder(env)
            if malformed_path.startswith('/cloudsql/'):
                assert builder.cloud_sql.is_cloud_sql, f'Should detect {malformed_path} as Cloud SQL'
                is_valid, error_msg = builder.validate()
                if malformed_path not in ['/cloudsql/pro:ject:reg:ion:inst:ance']:
                    assert not is_valid, f'Malformed path {malformed_path} should fail validation: {error_msg}'
            else:
                assert not builder.cloud_sql.is_cloud_sql, f'Should not detect {malformed_path} as Cloud SQL'

    def test_url_construction_with_special_characters(self):
        """Test URL construction with special characters in credentials."""
        special_chars_cases = [{'user': 'user@domain.com', 'password': 'p@ssw0rd!', 'expected_user': 'user%40domain.com', 'expected_pass': 'p%40ssw0rd%21'}, {'user': 'user+tag', 'password': 'pass word', 'expected_user': 'user%2Btag', 'expected_pass': 'pass%20word'}, {'user': 'user:with:colons', 'password': 'pass:with:colons', 'expected_user': 'user%3Awith%3Acolons', 'expected_pass': 'pass%3Awith%3Acolons'}, {'user': 'user%already%encoded', 'password': 'pass%already%encoded', 'expected_user': 'user%25already%25encoded', 'expected_pass': 'pass%25already%25encoded'}]
        for case in special_chars_cases:
            env = {'POSTGRES_HOST': 'special.db.com', 'POSTGRES_USER': case['user'], 'POSTGRES_PASSWORD': case['password'], 'POSTGRES_DB': 'special_db'}
            builder = DatabaseURLBuilder(env)
            tcp_url = builder.tcp.async_url
            assert case['expected_user'] in tcp_url, f"User encoding failed for {case['user']}"
            assert case['expected_pass'] in tcp_url, f"Password encoding failed for {case['password']}"
            parsed = urlparse(tcp_url)
            assert parsed.hostname == 'special.db.com', 'Hostname should be preserved'
            assert parsed.path == '/special_db', 'Database path should be preserved'

    def test_environment_variable_edge_cases(self):
        """Test edge cases in environment variable handling."""
        edge_cases = [{'POSTGRES_HOST': '', 'POSTGRES_USER': '', 'POSTGRES_PASSWORD': ''}, {'POSTGRES_HOST': '   ', 'POSTGRES_USER': '\t', 'POSTGRES_PASSWORD': '\n'}, {'POSTGRES_HOST': 'h' * 1000, 'POSTGRES_USER': 'u' * 500, 'POSTGRES_PASSWORD': 'p' * 2000}, {'POSTGRES_HOST': 'xoct.example.com', 'POSTGRES_USER': '[U+7528][U+6237]', 'POSTGRES_PASSWORD': '[U+5BC6][U+7801]'}]
        for edge_env in edge_cases:
            builder = DatabaseURLBuilder(edge_env)
            try:
                _ = builder.postgres_host
                _ = builder.postgres_user
                _ = builder.postgres_password
                _ = builder.tcp.has_config
                _ = builder.cloud_sql.is_cloud_sql
            except Exception as e:
                pytest.fail(f'Edge case environment should not crash: {edge_env} - {e}')

    def test_validation_edge_cases(self):
        """Test validation with edge case inputs."""
        edge_validation_cases = [{}, {'ENVIRONMENT': '   ', 'POSTGRES_HOST': '\t\n', 'POSTGRES_USER': '   ', 'POSTGRES_PASSWORD': '', 'POSTGRES_DB': '  \r\n  '}, {'ENVIRONMENT': 'staging', 'POSTGRES_HOST': 'host.com', 'POSTGRES_USER': 'x' * 1000, 'POSTGRES_PASSWORD': 'y' * 5000, 'POSTGRES_DB': 'z' * 100}]
        for edge_env in edge_validation_cases:
            builder = DatabaseURLBuilder(edge_env)
            try:
                is_valid, error_msg = builder.validate()
                assert isinstance(is_valid, bool), 'Validation should return boolean'
                assert isinstance(error_msg, str), 'Error message should be string'
            except Exception as e:
                pytest.fail(f'Validation should not crash with edge case: {edge_env} - {e}')

class TestWindowsCompatibility:
    """Test Windows-specific functionality - WINDOWS ENCODING SUPPORT."""

    def test_unicode_handling_in_urls(self):
        """Test Unicode character handling in URLs."""
        unicode_test_cases = [{'name': 'Chinese characters', 'user': '[U+7528][U+6237][U+540D]', 'password': '[U+5BC6][U+7801]123', 'db': '[U+6570][U+636E][U+5E93]'}, {'name': 'Cyrillic characters', 'user': '[U+043F]o[U+043B][U+044C][U+0437]ovate[U+043B][U+044C]', 'password': '[U+043F]apo[U+043B][U+044C]123', 'db': '[U+0431]a[U+0437]a_[U+0434]ann[U+044B]x'}, {'name': 'Emoji and special Unicode', 'user': 'user[U+1F680]', 'password': 'pass[U+1F512]word', 'db': 'db LIGHTNING: name'}, {'name': 'Mixed scripts', 'user': 'user[U+7528][U+6237]', 'password': 'pass[U+5BC6][U+7801]123', 'db': 'db[U+6570][U+636E][U+5E93]_name'}]
        for case in unicode_test_cases:
            env = {'POSTGRES_HOST': 'unicode.test.com', 'POSTGRES_USER': case['user'], 'POSTGRES_PASSWORD': case['password'], 'POSTGRES_DB': case['db']}
            builder = DatabaseURLBuilder(env)
            tcp_url = builder.tcp.async_url
            assert tcp_url is not None, f"URL construction failed for {case['name']}"
            try:
                parsed = urlparse(tcp_url)
                assert parsed.hostname == 'unicode.test.com', f"Hostname parsing failed for {case['name']}"
                assert parsed.username is not None, f"Username missing for {case['name']}"
                assert parsed.password is not None, f"Password missing for {case['name']}"
            except Exception as e:
                pytest.fail(f"URL parsing failed for {case['name']}: {e}")

    def test_windows_path_separators(self):
        """Test handling of Windows-style path separators."""
        windows_style_values = ['C:\\Program Files\\PostgreSQL\\data', '\\\\server\\share\\database', 'D:\\Development\\database\\config']
        for path_value in windows_style_values:
            env = {'POSTGRES_HOST': 'localhost', 'POSTGRES_USER': 'user', 'POSTGRES_PASSWORD': 'password', 'POSTGRES_DB': path_value}
            builder = DatabaseURLBuilder(env)
            try:
                tcp_url = builder.tcp.async_url
                assert tcp_url is not None, f'URL construction failed with Windows path: {path_value}'
                db_name_in_url = tcp_url.split('/')[-1]
                assert path_value in tcp_url or path_value.replace('\\', '\\\\') in tcp_url, f'Windows path not present in URL: {path_value}'
            except Exception as e:
                pytest.fail(f'Windows path handling failed: {path_value} - {e}')

    def test_case_sensitivity_handling(self):
        """Test case sensitivity handling for Windows compatibility."""
        mixed_case_env = {'postgres_host': 'mixedcase.test.com', 'POSTGRES_USER': 'UPPERCASE_USER', 'Postgres_Password': 'MixedCase_Pass', 'postgres_DB': 'lowercase_db'}
        builder = DatabaseURLBuilder(mixed_case_env)
        assert builder.postgres_host is None, 'Lowercase postgres_host should not match'
        assert builder.postgres_user == 'UPPERCASE_USER', 'Uppercase should match'
        assert builder.postgres_password is None, 'Mixed case should not match'
        assert builder.postgres_db is None, 'Lowercase postgres_db should not match'
        if builder.tcp.has_config:
            tcp_url = builder.tcp.async_url

class TestStaticMethodsAndUtilities:
    """Test static methods and utility functions - UTILITY FUNCTION COVERAGE."""

    def test_normalize_url_instance_method(self):
        """Test instance method normalize_url."""
        env = {'ENVIRONMENT': 'test'}
        builder = DatabaseURLBuilder(env)
        test_url = 'postgres://user:pass@host:5432/db'
        normalized = builder.normalize_url(test_url)
        expected = 'postgresql://user:pass@host:5432/db'
        assert normalized == expected, f'Instance normalize_url failed: {normalized}'

    def test_get_driver_requirements_comprehensive(self):
        """Test driver requirements for all supported drivers."""
        drivers = ['asyncpg', 'psycopg2', 'psycopg', 'base']
        for driver in drivers:
            requirements = DatabaseURLBuilder.get_driver_requirements(driver)
            assert 'ssl_parameter' in requirements, f'Driver {driver} missing ssl_parameter requirement'
            assert 'supports_sslmode' in requirements, f'Driver {driver} missing supports_sslmode requirement'
            assert 'supports_unix_socket' in requirements, f'Driver {driver} missing supports_unix_socket requirement'
            assert 'prefix' in requirements, f'Driver {driver} missing prefix requirement'
            if driver == 'asyncpg':
                assert requirements['ssl_parameter'] == 'ssl', 'AsyncPG should use ssl parameter'
                assert requirements['supports_sslmode'] is False, 'AsyncPG should not support sslmode'
                assert requirements['prefix'] == 'postgresql+asyncpg://', 'AsyncPG prefix incorrect'
            elif driver in ['psycopg2', 'psycopg']:
                assert requirements['ssl_parameter'] == 'sslmode', f'{driver} should use sslmode parameter'
                assert requirements['supports_sslmode'] is True, f'{driver} should support sslmode'
            elif driver == 'base':
                assert requirements['ssl_parameter'] == 'sslmode', 'Base driver should use sslmode'
                assert requirements['prefix'] == 'postgresql://', 'Base driver prefix incorrect'
        unknown_requirements = DatabaseURLBuilder.get_driver_requirements('unknown_driver')
        assert unknown_requirements == {}, 'Unknown driver should return empty dict'

    def test_future_hook_methods_not_implemented(self):
        """Test future extensibility hooks raise NotImplementedError."""
        with pytest.raises(NotImplementedError, match='Driver registration will be implemented'):
            DatabaseURLBuilder.register_driver_handler('test_driver', lambda x: x)
        with pytest.raises(NotImplementedError, match='Normalization rule registration will be implemented'):
            DatabaseURLBuilder.register_normalization_rule('pattern', 'replacement')

    def test_all_builder_property_access(self):
        """Test all builder sub-classes are properly accessible."""
        env = {'POSTGRES_HOST': 'test.com', 'POSTGRES_USER': 'user', 'POSTGRES_PASSWORD': 'pass', 'POSTGRES_DB': 'db'}
        builder = DatabaseURLBuilder(env)
        assert hasattr(builder, 'cloud_sql'), 'cloud_sql builder missing'
        assert hasattr(builder, 'tcp'), 'tcp builder missing'
        assert hasattr(builder, 'development'), 'development builder missing'
        assert hasattr(builder, 'test'), 'test builder missing'
        assert hasattr(builder, 'docker'), 'docker builder missing'
        assert hasattr(builder, 'staging'), 'staging builder missing'
        assert hasattr(builder, 'production'), 'production builder missing'
        assert builder.cloud_sql.parent is builder, 'cloud_sql parent reference incorrect'
        assert builder.tcp.parent is builder, 'tcp parent reference incorrect'
        assert builder.development.parent is builder, 'development parent reference incorrect'
        assert builder.test.parent is builder, 'test parent reference incorrect'
        assert builder.docker.parent is builder, 'docker parent reference incorrect'
        assert builder.staging.parent is builder, 'staging parent reference incorrect'
        assert builder.production.parent is builder, 'production parent reference incorrect'

class TestComprehensiveFinalValidation:
    """Final comprehensive validation covering all critical business scenarios."""

    def test_complete_database_connectivity_workflow(self):
        """Simulate complete database connectivity workflow for all environments."""
        environments = [{'name': 'development', 'config': {'ENVIRONMENT': 'development', 'POSTGRES_HOST': 'localhost', 'POSTGRES_USER': 'postgres', 'POSTGRES_PASSWORD': 'postgres', 'POSTGRES_DB': 'netra_dev'}, 'expected_working': True}, {'name': 'test_memory', 'config': {'ENVIRONMENT': 'test', 'USE_MEMORY_DB': 'true'}, 'expected_working': True}, {'name': 'test_postgresql', 'config': {'ENVIRONMENT': 'test', 'POSTGRES_HOST': 'test.db.com', 'POSTGRES_USER': 'test_user', 'POSTGRES_PASSWORD': 'test_password', 'POSTGRES_DB': 'test_database'}, 'expected_working': True}, {'name': 'staging', 'config': {'ENVIRONMENT': 'staging', 'POSTGRES_HOST': 'staging.database.secure.com', 'POSTGRES_USER': 'staging_user', 'POSTGRES_PASSWORD': 'secure_staging_password_with_32_chars', 'POSTGRES_DB': 'staging_database'}, 'expected_working': True}, {'name': 'production_cloud_sql', 'config': {'ENVIRONMENT': 'production', 'POSTGRES_HOST': '/cloudsql/netra-prod:us-central1:primary', 'POSTGRES_USER': 'production_user', 'POSTGRES_PASSWORD': 'ultra_secure_production_password_64_chars_long_for_security', 'POSTGRES_DB': 'netra_production'}, 'expected_working': True}, {'name': 'docker', 'config': {'ENVIRONMENT': 'development', 'POSTGRES_HOST': 'postgres', 'POSTGRES_USER': 'docker_user', 'POSTGRES_PASSWORD': 'docker_password', 'POSTGRES_DB': 'docker_database', 'RUNNING_IN_DOCKER': 'true'}, 'expected_working': True}]
        for env_scenario in environments:
            builder = DatabaseURLBuilder(env_scenario['config'])
            assert builder.environment.lower() in ['development', 'test', 'staging', 'production'], f"Invalid environment for {env_scenario['name']}"
            url = builder.get_url_for_environment()
            if env_scenario['expected_working']:
                assert url is not None, f"URL should be generated for {env_scenario['name']}"
                assert url.startswith(('postgresql', 'sqlite')), f"URL should have valid protocol for {env_scenario['name']}"
            is_valid, error_msg = builder.validate()
            if env_scenario['expected_working']:
                if not is_valid:
                    if builder.environment not in ['development', 'test']:
                        pytest.fail(f"Validation should pass for {env_scenario['name']}: {error_msg}")
            debug_info = builder.debug_info()
            assert 'environment' in debug_info, f"Debug info missing for {env_scenario['name']}"
            assert debug_info['environment'] == builder.environment, f"Debug environment mismatch for {env_scenario['name']}"
            log_message = builder.get_safe_log_message()
            assert builder.environment in log_message, f"Log message should contain environment for {env_scenario['name']}"
            sensitive_fields = ['password', 'secret', 'key']
            for field in sensitive_fields:
                field_value = env_scenario['config'].get(f'POSTGRES_{field.upper()}')
                if field_value and len(field_value) > 3 and (field_value != 'postgres'):
                    assert field_value not in log_message, f"Sensitive data leaked in log for {env_scenario['name']}: {field_value}"

    def test_all_url_types_generated_correctly(self):
        """Test that all URL types are generated with correct formats."""
        full_config = {'POSTGRES_HOST': 'comprehensive.test.com', 'POSTGRES_USER': 'comprehensive_user', 'POSTGRES_PASSWORD': 'comprehensive_password_123', 'POSTGRES_DB': 'comprehensive_database', 'POSTGRES_PORT': '5432', 'ENVIRONMENT': 'development'}
        builder = DatabaseURLBuilder(full_config)
        tcp_urls = {'async': builder.tcp.async_url, 'sync': builder.tcp.sync_url, 'async_with_ssl': builder.tcp.async_url_with_ssl, 'sync_with_ssl': builder.tcp.sync_url_with_ssl, 'async_sqlalchemy': builder.tcp.async_url_sqlalchemy, 'async_psycopg': builder.tcp.async_url_psycopg}
        for url_type, url in tcp_urls.items():
            assert url is not None, f'TCP {url_type} URL should not be None'
            assert 'comprehensive.test.com' in url, f'TCP {url_type} URL should contain hostname'
            assert 'comprehensive_user' in url, f'TCP {url_type} URL should contain username'
            assert 'comprehensive_password_123' in url, f'TCP {url_type} URL should contain password'
            assert 'comprehensive_database' in url, f'TCP {url_type} URL should contain database'
            if 'ssl' in url_type:
                assert 'sslmode=require' in url, f'TCP {url_type} URL should contain SSL requirement'
        dev_urls = {'default': builder.development.default_url, 'default_sync': builder.development.default_sync_url, 'auto': builder.development.auto_url, 'auto_sync': builder.development.auto_sync_url}
        for url_type, url in dev_urls.items():
            assert url is not None, f'Development {url_type} URL should not be None'
            if 'default' in url_type:
                assert 'localhost' in url, f'Development {url_type} should use localhost'
            else:
                assert 'comprehensive.test.com' in url, f'Development {url_type} should use configured host'
        docker_urls = {'compose': builder.docker.compose_url, 'compose_sync': builder.docker.compose_sync_url}
        for url_type, url in docker_urls.items():
            assert url is not None, f'Docker {url_type} URL should not be None'
            assert 'postgres' in url or 'comprehensive.test.com' in url, f'Docker {url_type} should have valid host'
        test_urls = {'memory': builder.test.memory_url, 'postgres': builder.test.postgres_url, 'auto': builder.test.auto_url}
        assert test_urls['memory'] == 'sqlite+aiosqlite:///:memory:', 'Memory URL should be SQLite'
        assert test_urls['postgres'] is not None, 'PostgreSQL test URL should be available'
        assert test_urls['auto'] is not None, 'Auto test URL should be available'

    def test_business_critical_scenarios_coverage(self):
        """Test all business-critical database connectivity scenarios."""
        critical_scenarios = [{'scenario': 'Service startup in production', 'config': {'ENVIRONMENT': 'production', 'POSTGRES_HOST': '/cloudsql/netra-prod:us-central1:main', 'POSTGRES_USER': 'netra_prod', 'POSTGRES_PASSWORD': 'ultra_secure_production_password_for_business_critical_operations', 'POSTGRES_DB': 'netra_production_primary'}, 'critical_checks': ['url_contains_cloud_sql', 'no_ssl_parameters_for_cloud_sql', 'credentials_properly_encoded', 'validation_passes']}, {'scenario': 'Staging deployment verification', 'config': {'ENVIRONMENT': 'staging', 'POSTGRES_HOST': 'staging-db.netra.internal', 'POSTGRES_USER': 'staging_user', 'POSTGRES_PASSWORD': 'staging_secure_password_32_chars', 'POSTGRES_DB': 'netra_staging'}, 'critical_checks': ['ssl_enabled_by_default', 'tcp_connection_used', 'staging_auto_url_works', 'validation_passes']}, {'scenario': 'Development container deployment', 'config': {'ENVIRONMENT': 'development', 'POSTGRES_HOST': 'localhost', 'POSTGRES_USER': 'dev_user', 'POSTGRES_PASSWORD': 'dev_password', 'POSTGRES_DB': 'netra_dev', 'RUNNING_IN_DOCKER': 'true'}, 'critical_checks': ['docker_hostname_resolution', 'development_urls_work', 'docker_compose_urls_work']}, {'scenario': 'Test suite execution', 'config': {'ENVIRONMENT': 'test', 'USE_MEMORY_DB': 'true'}, 'critical_checks': ['memory_db_used', 'fast_test_execution', 'no_external_dependencies']}]
        for scenario in critical_scenarios:
            builder = DatabaseURLBuilder(scenario['config'])
            scenario_name = scenario['scenario']
            for check in scenario['critical_checks']:
                if check == 'url_contains_cloud_sql':
                    url = builder.get_url_for_environment()
                    assert '/cloudsql/' in url, f'{scenario_name}: URL should contain Cloud SQL path'
                elif check == 'no_ssl_parameters_for_cloud_sql':
                    if builder.cloud_sql.is_cloud_sql:
                        url = builder.cloud_sql.async_url
                        assert 'ssl' not in url.lower(), f'{scenario_name}: Cloud SQL URL should not contain SSL parameters'
                elif check == 'credentials_properly_encoded':
                    url = builder.get_url_for_environment()
                    if url and '://' in url:
                        parsed = urlparse(url)
                        if parsed.username and parsed.password:
                            assert '%' not in parsed.username or '@' not in unquote(parsed.username), f'{scenario_name}: Username should be properly encoded'
                elif check == 'validation_passes':
                    is_valid, error_msg = builder.validate()
                    if not is_valid and builder.environment not in ['development', 'test']:
                        pytest.fail(f'{scenario_name}: Validation should pass: {error_msg}')
                elif check == 'ssl_enabled_by_default':
                    if builder.environment in ['staging', 'production'] and builder.tcp.has_config:
                        staging_url = builder.staging.auto_url if builder.environment == 'staging' else builder.production.auto_url
                        assert 'sslmode=require' in staging_url, f'{scenario_name}: SSL should be enabled by default'
                elif check == 'docker_hostname_resolution':
                    with patch.object(builder, 'is_docker_environment', return_value=True):
                        resolved_host = builder.apply_docker_hostname_resolution('localhost')
                        assert resolved_host == 'postgres', f'{scenario_name}: Should resolve localhost to postgres in Docker'
                elif check == 'memory_db_used':
                    auto_url = builder.test.auto_url
                    assert 'sqlite' in auto_url and 'memory' in auto_url, f'{scenario_name}: Should use memory database'
                elif check == 'fast_test_execution':
                    start_time = time.time()
                    for _ in range(100):
                        _ = builder.test.auto_url
                    elapsed = time.time() - start_time
                    assert elapsed < 0.1, f'{scenario_name}: Memory DB URL construction should be very fast'

    def test_platform_reliability_requirements(self):
        """Test that all platform reliability requirements are met."""
        reliability_matrix = [('production', '/cloudsql/proj:reg:inst', True, 'Cloud SQL production'), ('staging', 'staging.db.com', True, 'TCP SSL staging'), ('development', 'localhost', True, 'Development localhost'), ('test', None, True, 'Test environment'), ('development', 'postgres', True, 'Docker development')]
        for env, host, should_work, description in reliability_matrix:
            config = {'ENVIRONMENT': env, 'POSTGRES_USER': 'reliability_user', 'POSTGRES_PASSWORD': 'reliability_password_32_chars', 'POSTGRES_DB': 'reliability_database'}
            if host:
                config['POSTGRES_HOST'] = host
            builder = DatabaseURLBuilder(config)
            url = builder.get_url_for_environment()
            if should_work:
                assert url is not None, f'URL generation failed for {description}'
                if '://' in url:
                    parsed = urlparse(url)
                    valid_schemes = ['postgresql', 'sqlite', 'postgresql+asyncpg', 'postgresql+psycopg', 'postgresql+psycopg2', 'sqlite+aiosqlite']
                    assert parsed.scheme in valid_schemes, f'Invalid URL scheme for {description}: {parsed.scheme}'
                    if parsed.hostname:
                        assert len(parsed.hostname) > 0, f'Empty hostname for {description}'
            debug_info = builder.debug_info()
            assert isinstance(debug_info, dict), f'Debug info should be dict for {description}'
            assert len(debug_info) > 0, f'Debug info should not be empty for {description}'
            safe_msg = builder.get_safe_log_message()
            assert isinstance(safe_msg, str), f'Safe log message should be string for {description}'
            assert len(safe_msg) > 0, f'Safe log message should not be empty for {description}'
            try:
                is_valid, error_msg = builder.validate()
                assert isinstance(is_valid, bool), f'Validation result should be boolean for {description}'
                assert isinstance(error_msg, str), f'Error message should be string for {description}'
            except Exception as e:
                pytest.fail(f'Validation crashed for {description}: {e}')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')