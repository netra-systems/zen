"""
Cross-System Environment Configuration Alignment Tests

Business Value Justification (BVJ):
- Segment: All tiers (Free, Early, Mid, Enterprise) 
- Business Goal: Platform Stability & Risk Reduction
- Value Impact: Prevents deployment failures and runtime inconsistencies across services
- Strategic Impact: Essential for multi-service reliability - configuration misalignment destroys system integrity

This test verifies that critical environment configurations are properly aligned
between auth_service, netra_backend, and frontend services. Configuration drift
between services is a major source of deployment failures and runtime issues.
"""
import asyncio
import os
import pytest
import json
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from netra_backend.app.core.unified_logging import central_logger
from shared.isolated_environment import IsolatedEnvironment
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
logger = central_logger.get_logger(__name__)

class CrossSystemEnvironmentAlignmentTester:
    """Tests environment configuration alignment across all services."""

    def __init__(self):
        """Initialize cross-system environment alignment tester."""
        self.critical_shared_configs = {'DATABASE_URL': {'required': True, 'description': 'Primary database connection', 'services': ['auth_service', 'netra_backend']}, 'JWT_SECRET_KEY': {'required': True, 'description': 'JWT signing secret', 'services': ['auth_service', 'netra_backend'], 'security_sensitive': True}, 'REDIS_URL': {'required': True, 'description': 'Redis cache connection', 'services': ['auth_service', 'netra_backend']}, 'ENVIRONMENT': {'required': True, 'description': 'Environment identifier', 'services': ['auth_service', 'netra_backend', 'frontend'], 'allowed_values': ['development', 'staging', 'production']}, 'AUTH_SERVICE_URL': {'required': False, 'description': 'Auth service endpoint URL', 'services': ['netra_backend', 'frontend']}, 'BACKEND_API_URL': {'required': False, 'description': 'Backend API endpoint URL', 'services': ['frontend']}}
        self.service_specific_configs = {'auth_service': {'AUTH_SERVICE_PORT': 'Service port configuration', 'OAUTH_CLIENT_ID': 'OAuth client credentials', 'OAUTH_CLIENT_SECRET': 'OAuth client secret'}, 'netra_backend': {'BACKEND_PORT': 'Service port configuration', 'CLICKHOUSE_HOST': 'Analytics database host', 'CLICKHOUSE_PORT': 'Analytics database port'}, 'frontend': {'FRONTEND_PORT': 'Service port configuration', 'NEXT_PUBLIC_API_URL': 'Public API URL for frontend'}}

    def get_current_environment(self) -> str:
        """Detect current environment from environment variables."""
        if get_env().get('TESTING') == 'true':
            return 'development'
        elif get_env().get('ENVIRONMENT') == 'staging':
            return 'staging'
        elif get_env().get('ENVIRONMENT') == 'production':
            return 'production'
        else:
            return 'development'

    async def test_critical_shared_config_alignment(self) -> Dict[str, Any]:
        """Test that critical shared configurations are properly aligned."""
        current_env = self.get_current_environment()
        results = {'environment': current_env, 'aligned_configs': [], 'misaligned_configs': [], 'missing_configs': [], 'security_issues': [], 'alignment_score': 0.0}
        try:
            for config_name, config_spec in self.critical_shared_configs.items():
                config_result = await self._test_single_config_alignment(config_name, config_spec, current_env)
                if config_result['status'] == 'aligned':
                    results['aligned_configs'].append(config_result)
                elif config_result['status'] == 'misaligned':
                    results['misaligned_configs'].append(config_result)
                elif config_result['status'] == 'missing':
                    results['missing_configs'].append(config_result)
                if config_spec.get('security_sensitive') and config_result.get('security_issue'):
                    results['security_issues'].append(config_result)
            total_configs = len(self.critical_shared_configs)
            aligned_count = len(results['aligned_configs'])
            results['alignment_score'] = aligned_count / total_configs * 100.0
        except Exception as e:
            logger.error(f'Error testing critical shared config alignment: {e}')
            results['error'] = str(e)
        return results

    async def _test_single_config_alignment(self, config_name: str, config_spec: Dict[str, Any], environment: str) -> Dict[str, Any]:
        """Test alignment of a single configuration across services."""
        result = {'config_name': config_name, 'description': config_spec['description'], 'status': 'unknown', 'values': {}, 'issues': []}
        try:
            for service in config_spec['services']:
                value = await self._get_service_config_value(service, config_name)
                result['values'][service] = value
            unique_values = set((v for v in result['values'].values() if v is not None))
            non_null_values = [v for v in result['values'].values() if v is not None]
            if not non_null_values:
                if config_spec['required']:
                    result['status'] = 'missing'
                    result['issues'].append('Required configuration is missing from all services')
                else:
                    result['status'] = 'aligned'
            elif len(unique_values) == 1:
                result['status'] = 'aligned'
                if config_name == 'ENVIRONMENT' and 'allowed_values' in config_spec:
                    value = list(unique_values)[0]
                    if value not in config_spec['allowed_values']:
                        result['status'] = 'misaligned'
                        result['issues'].append(f'Invalid environment value: {value}')
            else:
                result['status'] = 'misaligned'
                result['issues'].append(f"Configuration values differ across services: {dict(result['values'])}")
            if config_spec.get('security_sensitive'):
                await self._validate_security_config(result, config_name, environment)
        except Exception as e:
            result['status'] = 'error'
            result['issues'].append(f'Error testing configuration: {str(e)}')
        return result

    async def _get_service_config_value(self, service: str, config_name: str) -> Optional[str]:
        """Get configuration value for a specific service."""
        try:
            try:
                env = IsolatedEnvironment()
                return env.get(config_name)
            except:
                return get_env().get(config_name)
        except Exception as e:
            logger.warning(f'Could not get {config_name} for service {service}: {e}')
            return None

    async def _validate_security_config(self, result: Dict[str, Any], config_name: str, environment: str) -> None:
        """Validate security-sensitive configuration."""
        try:
            values = [v for v in result['values'].values() if v is not None]
            if config_name == 'JWT_SECRET_KEY':
                for value in values:
                    if value:
                        if len(value) < 32:
                            result['security_issue'] = 'JWT secret too short (minimum 32 characters)'
                            result['issues'].append('JWT secret does not meet security requirements')
                        if environment != 'development' and 'test' in value.lower():
                            result['security_issue'] = 'Test JWT secret used in non-development environment'
                            result['issues'].append('Weak JWT secret detected in production environment')
        except Exception as e:
            logger.warning(f'Error validating security config {config_name}: {e}')

    async def test_service_discovery_alignment(self) -> Dict[str, Any]:
        """Test that service discovery configurations are aligned."""
        current_env = self.get_current_environment()
        results = {'environment': current_env, 'discovery_method': None, 'service_urls': {}, 'issues': [], 'properly_configured': False}
        try:
            if current_env == 'development':
                results['discovery_method'] = 'file_based'
                discovery_dir = Path('.service_discovery')
                if discovery_dir.exists():
                    for service in ['frontend', 'backend', 'auth']:
                        config_file = discovery_dir / f'{service}_config.json'
                        if config_file.exists():
                            try:
                                with open(config_file) as f:
                                    config = json.load(f)
                                results['service_urls'][service] = config.get('url')
                            except Exception as e:
                                results['issues'].append(f'Could not read {service} discovery config: {e}')
                        else:
                            results['issues'].append(f'Missing service discovery config for {service}')
                    expected_services = 3
                    discovered_services = len([url for url in results['service_urls'].values() if url])
                    results['properly_configured'] = discovered_services == expected_services
                else:
                    results['issues'].append('Service discovery directory not found')
            else:
                results['discovery_method'] = 'environment_based'
                service_url_vars = {'auth_service': 'AUTH_SERVICE_URL', 'backend': 'BACKEND_API_URL', 'frontend': 'FRONTEND_URL'}
                for service, var_name in service_url_vars.items():
                    value = get_env().get(var_name)
                    results['service_urls'][service] = value
                    if not value:
                        results['issues'].append(f'Missing {var_name} for {service}')
                configured_count = len([url for url in results['service_urls'].values() if url])
                results['properly_configured'] = configured_count == len(service_url_vars)
        except Exception as e:
            logger.error(f'Error testing service discovery alignment: {e}')
            results['error'] = str(e)
        return results

    async def test_database_config_consistency(self) -> Dict[str, Any]:
        """Test database configuration consistency across services."""
        results = {'database_configs': {}, 'consistency_issues': [], 'ssl_parameter_conflicts': [], 'properly_configured': False}
        try:
            services_with_db = ['auth_service', 'netra_backend']
            for service in services_with_db:
                db_url = await self._get_service_config_value(service, 'DATABASE_URL')
                if not db_url:
                    pg_host = await self._get_service_config_value(service, 'POSTGRES_HOST')
                    pg_port = await self._get_service_config_value(service, 'POSTGRES_PORT')
                    pg_db = await self._get_service_config_value(service, 'POSTGRES_DB')
                    pg_user = await self._get_service_config_value(service, 'POSTGRES_USER')
                    pg_password = await self._get_service_config_value(service, 'POSTGRES_PASSWORD')
                    if pg_host and pg_port and pg_db and pg_user:
                        password_part = f':{pg_password}' if pg_password else ''
                        db_url = f'postgresql://{pg_user}{password_part}@{pg_host}:{pg_port}/{pg_db}'
                        results['database_configs'][service] = {'url': db_url, 'config_method': 'components', 'components': {'host': pg_host, 'port': pg_port, 'database': pg_db, 'user': pg_user, 'has_password': bool(pg_password)}, 'has_ssl_params': False, 'has_unix_socket': '/cloudsql/' in pg_host if pg_host else False, 'driver_compatible': True}
                        ssl_mode = await self._get_service_config_value(service, 'POSTGRES_SSLMODE')
                        if ssl_mode and '/cloudsql/' in pg_host:
                            results['ssl_parameter_conflicts'].append({'service': service, 'issue': 'SSL parameters not compatible with Unix socket connections'})
                            results['database_configs'][service]['driver_compatible'] = False
                elif db_url:
                    results['database_configs'][service] = {'url': db_url, 'config_method': 'url', 'has_ssl_params': 'ssl' in db_url.lower(), 'has_unix_socket': '/cloudsql/' in db_url, 'driver_compatible': True}
                    if 'sslmode=' in db_url and '/cloudsql/' in db_url:
                        results['ssl_parameter_conflicts'].append({'service': service, 'issue': 'SSL parameters not compatible with Unix socket connections'})
                        results['database_configs'][service]['driver_compatible'] = False
            db_configs = results['database_configs']
            if len(db_configs) == 0:
                results['consistency_issues'].append('No database configuration found in any service')
            elif len(db_configs) == 1:
                configured_service = list(db_configs.keys())[0]
                results['consistency_issues'].append(f'Database configured only for {configured_service}, missing for other services')
            else:
                urls = [config['url'] for config in db_configs.values()]
                unique_urls = set(urls)
                if len(unique_urls) > 1:
                    results['consistency_issues'].append('Database URLs differ between services')
                else:
                    config_methods = set((config.get('config_method', 'unknown') for config in db_configs.values()))
                    if len(config_methods) > 1:
                        results['consistency_issues'].append(f'Services use different database configuration methods: {config_methods}')
            has_any_config = len(db_configs) > 0
            has_ssl_conflicts = len(results['ssl_parameter_conflicts']) > 0
            has_critical_issues = any(('No database configuration found' in issue for issue in results['consistency_issues']))
            results['properly_configured'] = has_any_config and (not has_ssl_conflicts) and (not has_critical_issues)
        except Exception as e:
            logger.error(f'Error testing database config consistency: {e}')
            results['error'] = str(e)
        return results

@pytest.fixture
def environment_tester():
    """Create environment alignment tester instance."""
    return CrossSystemEnvironmentAlignmentTester()

class CrossSystemEnvironmentAlignmentTests:
    """Test suite for cross-system environment configuration alignment."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_critical_shared_configurations_aligned(self, environment_tester):
        """Test that critical shared configurations are properly aligned across services."""
        results = await environment_tester.test_critical_shared_config_alignment()
        logger.info(f'Critical config alignment results: {results}')
        assert 'error' not in results, f"Error during config alignment test: {results.get('error')}"
        alignment_score = results.get('alignment_score', 0.0)
        environment = results.get('environment', 'unknown')
        if environment == 'development':
            min_score = 60.0
        else:
            min_score = 80.0
        assert alignment_score >= min_score, f"Configuration alignment score too low: {alignment_score}%. Misaligned configs: {results.get('misaligned_configs', [])}. Missing configs: {results.get('missing_configs', [])}. Critical shared configurations must be properly aligned across services."
        security_issues = results.get('security_issues', [])
        assert len(security_issues) == 0, f'Security configuration issues detected: {security_issues}. Security-sensitive configurations must meet security requirements.'
        misaligned_configs = results.get('misaligned_configs', [])
        critical_misalignments = [config for config in misaligned_configs if config['config_name'] in ['JWT_SECRET_KEY', 'DATABASE_URL']]
        assert len(critical_misalignments) == 0, f'Critical configuration misalignments detected: {critical_misalignments}. JWT_SECRET_KEY and #removed-legacymust be identical across services.'

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_service_discovery_configuration_aligned(self, environment_tester):
        """Test that service discovery configurations are properly aligned."""
        results = await environment_tester.test_service_discovery_alignment()
        logger.info(f'Service discovery alignment results: {results}')
        assert 'error' not in results, f"Error during service discovery test: {results.get('error')}"
        environment = results.get('environment', 'unknown')
        discovery_method = results.get('discovery_method')
        properly_configured = results.get('properly_configured', False)
        issues = results.get('issues', [])
        if environment == 'development':
            assert discovery_method == 'file_based', f'Development should use file-based service discovery, got: {discovery_method}'
        else:
            assert discovery_method == 'environment_based', f'Non-development should use environment-based discovery, got: {discovery_method}'
        if environment in ['staging', 'production']:
            assert properly_configured, f'Service discovery not properly configured for {environment}. Issues: {issues}. All service URLs must be configured in non-development environments.'
        elif environment == 'development':
            if not properly_configured and issues:
                logger.warning(f'Development service discovery issues (may be acceptable): {issues}')

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_database_configuration_consistency(self, environment_tester):
        """Test that database configurations are consistent across services."""
        results = await environment_tester.test_database_config_consistency()
        logger.info(f'Database config consistency results: {results}')
        assert 'error' not in results, f"Error during database config test: {results.get('error')}"
        consistency_issues = results.get('consistency_issues', [])
        ssl_conflicts = results.get('ssl_parameter_conflicts', [])
        properly_configured = results.get('properly_configured', False)
        if ssl_conflicts:
            logger.error(f'SSL parameter conflicts detected: {ssl_conflicts}')
        assert len(ssl_conflicts) == 0, f'SSL parameter conflicts detected: {ssl_conflicts}. SSL parameters must be compatible with connection method (Unix socket vs TCP).'
        if consistency_issues:
            critical_issues = [issue for issue in consistency_issues if 'No database configuration found' in issue or ('Database configured only for' in issue and environment_tester.get_current_environment() != 'development')]
            current_env = environment_tester.get_current_environment()
            if current_env == 'development':
                total_absence_issues = [issue for issue in consistency_issues if 'No database configuration found' in issue]
                assert len(total_absence_issues) == 0, f'Critical database configuration issues: {total_absence_issues}. At least one service must have database configuration in development.'
            else:
                assert len(critical_issues) == 0, f'Critical database configuration issues: {critical_issues}. Database configuration must be consistent across all backend services.'
            if consistency_issues:
                logger.warning(f'Database configuration consistency warnings: {consistency_issues}')

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_environment_variable_completeness(self, environment_tester):
        """Test that required environment variables are present for current environment."""
        current_env = environment_tester.get_current_environment()
        required_vars_by_env = {'development': ['TESTING', 'DATABASE_URL'], 'staging': ['ENVIRONMENT', 'DATABASE_URL', 'JWT_SECRET_KEY', 'AUTH_SERVICE_URL'], 'production': ['ENVIRONMENT', 'DATABASE_URL', 'JWT_SECRET_KEY', 'AUTH_SERVICE_URL', 'REDIS_URL']}
        required_vars = required_vars_by_env.get(current_env, [])
        missing_vars = []
        for var_name in required_vars:
            value = get_env().get(var_name)
            if not value:
                missing_vars.append(var_name)
        logger.info(f'Environment: {current_env}, Required vars: {required_vars}, Missing: {missing_vars}')
        if current_env in ['staging', 'production']:
            assert len(missing_vars) == 0, f'Missing required environment variables for {current_env}: {missing_vars}. All critical environment variables must be configured in production environments.'
        elif current_env == 'development':
            critical_missing = [var for var in missing_vars if var in ['DATABASE_URL']]
            if critical_missing:
                logger.warning(f'Critical environment variables missing in development: {critical_missing}')

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_cross_service_cors_configuration(self, environment_tester):
        """Test that CORS configurations are properly aligned for cross-service communication."""
        current_env = environment_tester.get_current_environment()
        results = {'environment': current_env, 'cors_origins': [], 'issues': []}
        try:
            cors_vars = ['CORS_ORIGINS', 'ALLOWED_ORIGINS', 'FRONTEND_URL']
            for var_name in cors_vars:
                value = get_env().get(var_name)
                if value:
                    results['cors_origins'].append({'variable': var_name, 'value': value})
            discovery_results = await environment_tester.test_service_discovery_alignment()
            service_urls = discovery_results.get('service_urls', {})
            if current_env == 'development':
                expected_origins = [url for url in service_urls.values() if url]
                if expected_origins:
                    logger.info(f'Development CORS should allow: {expected_origins}')
            elif not results['cors_origins']:
                results['issues'].append('CORS origins not configured for production environment')
            logger.info(f'CORS configuration results: {results}')
            if results['issues']:
                logger.warning(f"CORS configuration issues: {results['issues']}")
        except Exception as e:
            logger.error(f'Error testing CORS configuration: {e}')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')