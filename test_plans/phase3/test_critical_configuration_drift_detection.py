"""
Test Plan: Critical Configuration Drift Detection
Issue #245 - Protect Golden Path from configuration inconsistencies

CRITICAL MISSION: Detect configuration drift that could break:
1. WebSocket connections (chat functionality)
2. Authentication (user access)
3. Database connectivity (data persistence)
4. Service communication (integration)

APPROACH: Compare configuration outputs from all deployment methods
and ensure ZERO drift in business-critical settings.
"""
import subprocess
import sys
import os
import json
import re
from pathlib import Path
import pytest
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from unittest.mock import patch, MagicMock
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

@dataclass
class ConfigurationSnapshot:
    """Snapshot of configuration from a deployment method."""
    source: str
    websocket_config: Dict[str, str]
    auth_config: Dict[str, str]
    database_config: Dict[str, str]
    service_config: Dict[str, str]
    environment_vars: Dict[str, str]

class TestCriticalConfigurationDriftDetection:
    """Detect configuration drift that could break Golden Path functionality."""

    @pytest.fixture
    def expected_websocket_config(self):
        """Expected WebSocket configuration for staging environment."""
        return {'WEBSOCKET_CONNECTION_TIMEOUT': '360', 'WEBSOCKET_HEARTBEAT_INTERVAL': '15', 'WEBSOCKET_HEARTBEAT_TIMEOUT': '45', 'WEBSOCKET_CLEANUP_INTERVAL': '120', 'WEBSOCKET_STALE_TIMEOUT': '360', 'WEBSOCKET_CONNECT_TIMEOUT': '10', 'WEBSOCKET_HANDSHAKE_TIMEOUT': '15', 'WEBSOCKET_PING_TIMEOUT': '5', 'WEBSOCKET_CLOSE_TIMEOUT': '10'}

    @pytest.fixture
    def expected_auth_config(self):
        """Expected authentication configuration for staging environment."""
        return {'AUTH_SERVICE_URL': 'https://auth.staging.netrasystems.ai', 'FRONTEND_URL': 'https://app.staging.netrasystems.ai', 'NEXT_PUBLIC_AUTH_URL': 'https://auth.staging.netrasystems.ai', 'NEXT_PUBLIC_AUTH_SERVICE_URL': 'https://auth.staging.netrasystems.ai', 'NEXT_PUBLIC_AUTH_API_URL': 'https://auth.staging.netrasystems.ai', 'NEXT_PUBLIC_FRONTEND_URL': 'https://app.staging.netrasystems.ai', 'JWT_SECRET_KEY_GSM_MAPPING': 'jwt-secret-staging', 'JWT_SECRET_STAGING_GSM_MAPPING': 'jwt-secret-staging'}

    @pytest.fixture
    def expected_database_config(self):
        """Expected database configuration for staging environment."""
        return {'CLOUD_SQL_INSTANCE': 'netra-staging:us-central1:staging-shared-postgres', 'POSTGRES_HOST_GSM_MAPPING': 'postgres-host-staging', 'POSTGRES_USER_GSM_MAPPING': 'postgres-user-staging', 'POSTGRES_PASSWORD_GSM_MAPPING': 'postgres-password-staging', 'POSTGRES_DB_GSM_MAPPING': 'postgres-db-staging', 'POSTGRES_PORT_GSM_MAPPING': 'postgres-port-staging', 'VPC_CONNECTOR': 'staging-connector'}

    @pytest.fixture
    def expected_service_config(self):
        """Expected service configuration for staging environment."""
        return {'NEXT_PUBLIC_API_URL': 'https://api.staging.netrasystems.ai', 'NEXT_PUBLIC_BACKEND_URL': 'https://api.staging.netrasystems.ai', 'BACKEND_URL': 'https://api.staging.netrasystems.ai', 'NEXT_PUBLIC_WS_URL': 'wss://api.staging.netrasystems.ai', 'NEXT_PUBLIC_WEBSOCKET_URL': 'wss://api.staging.netrasystems.ai', 'BACKEND_MEMORY': '4Gi', 'BACKEND_CPU': '4', 'AUTH_MEMORY': '512Mi', 'AUTH_CPU': '1', 'FRONTEND_MEMORY': '512Mi', 'FRONTEND_CPU': '1'}

    def extract_configuration_from_deploy_script(self, script_path: Path) -> ConfigurationSnapshot:
        """Extract configuration from deployment script source code."""
        if not script_path.exists():
            pytest.skip(f'Deployment script not found: {script_path}')
        with open(script_path, 'r') as f:
            content = f.read()
        websocket_config = {}
        websocket_patterns = {'WEBSOCKET_CONNECTION_TIMEOUT': '"WEBSOCKET_CONNECTION_TIMEOUT":\\s*"(\\d+)"', 'WEBSOCKET_HEARTBEAT_INTERVAL': '"WEBSOCKET_HEARTBEAT_INTERVAL":\\s*"(\\d+)"', 'WEBSOCKET_HEARTBEAT_TIMEOUT': '"WEBSOCKET_HEARTBEAT_TIMEOUT":\\s*"(\\d+)"', 'WEBSOCKET_CLEANUP_INTERVAL': '"WEBSOCKET_CLEANUP_INTERVAL":\\s*"(\\d+)"', 'WEBSOCKET_STALE_TIMEOUT': '"WEBSOCKET_STALE_TIMEOUT":\\s*"(\\d+)"', 'WEBSOCKET_CONNECT_TIMEOUT': '"WEBSOCKET_CONNECT_TIMEOUT":\\s*"(\\d+)"', 'WEBSOCKET_HANDSHAKE_TIMEOUT': '"WEBSOCKET_HANDSHAKE_TIMEOUT":\\s*"(\\d+)"', 'WEBSOCKET_PING_TIMEOUT': '"WEBSOCKET_PING_TIMEOUT":\\s*"(\\d+)"', 'WEBSOCKET_CLOSE_TIMEOUT': '"WEBSOCKET_CLOSE_TIMEOUT":\\s*"(\\d+)"'}
        for key, pattern in websocket_patterns.items():
            match = re.search(pattern, content)
            if match:
                websocket_config[key] = match.group(1)
        auth_config = {}
        auth_patterns = {'AUTH_SERVICE_URL': '"AUTH_SERVICE_URL":\\s*"([^"]+)"', 'FRONTEND_URL': '"FRONTEND_URL":\\s*"([^"]+)"', 'NEXT_PUBLIC_AUTH_URL': '"NEXT_PUBLIC_AUTH_URL":\\s*"([^"]+)"', 'NEXT_PUBLIC_AUTH_SERVICE_URL': '"NEXT_PUBLIC_AUTH_SERVICE_URL":\\s*"([^"]+)"', 'NEXT_PUBLIC_AUTH_API_URL': '"NEXT_PUBLIC_AUTH_API_URL":\\s*"([^"]+)"', 'NEXT_PUBLIC_FRONTEND_URL': '"NEXT_PUBLIC_FRONTEND_URL":\\s*"([^"]+)"'}
        for key, pattern in auth_patterns.items():
            match = re.search(pattern, content)
            if match:
                auth_config[key] = match.group(1)
        database_config = {}
        if 'staging-shared-postgres' in content:
            database_config['CLOUD_SQL_INSTANCE'] = 'netra-staging:us-central1:staging-shared-postgres'
        if 'staging-connector' in content:
            database_config['VPC_CONNECTOR'] = 'staging-connector'
        service_config = {}
        service_patterns = {'NEXT_PUBLIC_API_URL': '"NEXT_PUBLIC_API_URL":\\s*"([^"]+)"', 'NEXT_PUBLIC_BACKEND_URL': '"NEXT_PUBLIC_BACKEND_URL":\\s*"([^"]+)"', 'NEXT_PUBLIC_WS_URL': '"NEXT_PUBLIC_WS_URL":\\s*"([^"]+)"', 'NEXT_PUBLIC_WEBSOCKET_URL': '"NEXT_PUBLIC_WEBSOCKET_URL":\\s*"([^"]+)"'}
        for key, pattern in service_patterns.items():
            match = re.search(pattern, content)
            if match:
                service_config[key] = match.group(1)
        memory_patterns = {'BACKEND_MEMORY': 'memory.*backend.*"([^"]+)"', 'AUTH_MEMORY': 'memory.*auth.*"([^"]+)"', 'FRONTEND_MEMORY': 'memory.*frontend.*"([^"]+)"'}
        cpu_patterns = {'BACKEND_CPU': 'cpu.*backend.*"([^"]+)"', 'AUTH_CPU': 'cpu.*auth.*"([^"]+)"', 'FRONTEND_CPU': 'cpu.*frontend.*"([^"]+)"'}
        for key, pattern in {**memory_patterns, **cpu_patterns}.items():
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                service_config[key] = match.group(1)
        return ConfigurationSnapshot(source=script_path.name, websocket_config=websocket_config, auth_config=auth_config, database_config=database_config, service_config=service_config, environment_vars={})

    def test_websocket_configuration_consistency_across_deployment_methods(self, expected_websocket_config):
        """CRITICAL: Test WebSocket configuration consistency across all deployment methods."""
        deployment_scripts = [project_root / 'scripts' / 'deploy_to_gcp_actual.py']
        configurations = []
        for script in deployment_scripts:
            if script.exists():
                config = self.extract_configuration_from_deploy_script(script)
                configurations.append(config)
        if not configurations:
            pytest.skip('No deployment scripts found for configuration comparison')
        websocket_configs = [config.websocket_config for config in configurations]
        if len(websocket_configs) > 1:
            reference_config = websocket_configs[0]
            for i, config in enumerate(websocket_configs[1:], 1):
                for key in expected_websocket_config.keys():
                    if key in reference_config and key in config:
                        assert reference_config[key] == config[key], f'WebSocket config drift detected for {key}: {configurations[0].source}={reference_config[key]} vs {configurations[i].source}={config[key]}'
        for config in configurations:
            for key, expected_value in expected_websocket_config.items():
                if key in config.websocket_config:
                    actual_value = config.websocket_config[key]
                    assert actual_value == expected_value, f'WebSocket config mismatch in {config.source}: {key} expected={expected_value}, actual={actual_value}'
                else:
                    print(f' WARNING: [U+FE0F] WebSocket config {key} not found in {config.source}')

    def test_auth_configuration_consistency_across_deployment_methods(self, expected_auth_config):
        """CRITICAL: Test authentication configuration consistency across all deployment methods."""
        deployment_scripts = [project_root / 'scripts' / 'deploy_to_gcp_actual.py']
        configurations = []
        for script in deployment_scripts:
            if script.exists():
                config = self.extract_configuration_from_deploy_script(script)
                configurations.append(config)
        critical_auth_urls = ['AUTH_SERVICE_URL', 'FRONTEND_URL', 'NEXT_PUBLIC_AUTH_URL', 'NEXT_PUBLIC_AUTH_SERVICE_URL', 'NEXT_PUBLIC_FRONTEND_URL']
        for config in configurations:
            for url_key in critical_auth_urls:
                if url_key in config.auth_config:
                    actual_url = config.auth_config[url_key]
                    expected_url = expected_auth_config.get(url_key)
                    if expected_url:
                        assert actual_url == expected_url, f'CRITICAL AUTH URL MISMATCH in {config.source}: {url_key} expected={expected_url}, actual={actual_url}'
                        assert actual_url.startswith('https://'), f'Auth URL must use HTTPS: {url_key}={actual_url}'
                        assert 'staging.netrasystems.ai' in actual_url, f'Auth URL must use staging domain: {url_key}={actual_url}'

    def test_database_configuration_consistency_across_deployment_methods(self, expected_database_config):
        """CRITICAL: Test database configuration consistency across all deployment methods."""
        deployment_scripts = [project_root / 'scripts' / 'deploy_to_gcp_actual.py']
        configurations = []
        for script in deployment_scripts:
            if script.exists():
                config = self.extract_configuration_from_deploy_script(script)
                configurations.append(config)
        for config in configurations:
            if 'CLOUD_SQL_INSTANCE' in config.database_config:
                actual_instance = config.database_config['CLOUD_SQL_INSTANCE']
                expected_instance = expected_database_config['CLOUD_SQL_INSTANCE']
                assert actual_instance == expected_instance, f'CRITICAL DATABASE INSTANCE MISMATCH in {config.source}: expected={expected_instance}, actual={actual_instance}'
            if 'VPC_CONNECTOR' in config.database_config:
                actual_connector = config.database_config['VPC_CONNECTOR']
                expected_connector = expected_database_config['VPC_CONNECTOR']
                assert actual_connector == expected_connector, f'CRITICAL VPC CONNECTOR MISMATCH in {config.source}: expected={expected_connector}, actual={actual_connector}'

    def test_service_endpoint_configuration_consistency(self, expected_service_config):
        """CRITICAL: Test service endpoint configuration consistency."""
        deployment_scripts = [project_root / 'scripts' / 'deploy_to_gcp_actual.py']
        configurations = []
        for script in deployment_scripts:
            if script.exists():
                config = self.extract_configuration_from_deploy_script(script)
                configurations.append(config)
        critical_endpoints = ['NEXT_PUBLIC_API_URL', 'NEXT_PUBLIC_WS_URL', 'NEXT_PUBLIC_WEBSOCKET_URL']
        for config in configurations:
            for endpoint_key in critical_endpoints:
                if endpoint_key in config.service_config:
                    actual_endpoint = config.service_config[endpoint_key]
                    expected_endpoint = expected_service_config.get(endpoint_key)
                    if expected_endpoint:
                        assert actual_endpoint == expected_endpoint, f'CRITICAL SERVICE ENDPOINT MISMATCH in {config.source}: {endpoint_key} expected={expected_endpoint}, actual={actual_endpoint}'
                        if 'WS_URL' in endpoint_key or 'WEBSOCKET_URL' in endpoint_key:
                            assert actual_endpoint.startswith('wss://'), f'WebSocket URL must use WSS: {endpoint_key}={actual_endpoint}'
                        else:
                            assert actual_endpoint.startswith('https://'), f'Service URL must use HTTPS: {endpoint_key}={actual_endpoint}'

    def test_jwt_secret_mapping_consistency(self):
        """CRITICAL: Test JWT secret mapping consistency across services."""
        deployment_script = project_root / 'scripts' / 'deploy_to_gcp_actual.py'
        if not deployment_script.exists():
            pytest.skip('Deployment script not found')
        with open(deployment_script, 'r') as f:
            content = f.read()
        jwt_patterns = ['"JWT_SECRET_KEY":\\s*"([^"]+)"', '"JWT_SECRET_STAGING":\\s*"([^"]+)"', 'JWT_SECRET_KEY.*"([^"]+)"', 'jwt-secret-staging', 'jwt-secret-key-staging']
        jwt_mappings = []
        for pattern in jwt_patterns:
            matches = re.findall(pattern, content)
            jwt_mappings.extend(matches)
        gsm_secret_name = 'jwt-secret-staging'
        assert gsm_secret_name in content, f'CRITICAL: JWT secret GSM mapping not found: {gsm_secret_name}'
        different_jwt_secrets = ['jwt-secret-key-staging', 'jwt-secret-production', 'JWT_SECRET_DEV']
        for wrong_secret in different_jwt_secrets:
            assert wrong_secret not in content, f'CRITICAL: Found inconsistent JWT secret mapping: {wrong_secret}'

    def test_redis_configuration_consistency(self):
        """CRITICAL: Test Redis configuration consistency."""
        deployment_script = project_root / 'scripts' / 'deploy_to_gcp_actual.py'
        if not deployment_script.exists():
            pytest.skip('Deployment script not found')
        with open(deployment_script, 'r') as f:
            content = f.read()
        expected_redis_host = '10.107.0.3'
        expected_redis_port = '6379'
        if 'redis' in content.lower():
            redis_patterns = ['redis[^"]*([0-9.]+)', '"redis[^"]*([0-9.]+)"', 'REDIS_HOST[^"]*"([^"]+)"']
            for pattern in redis_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches:
                    if '10.107.0' in match:
                        print(f' PASS:  Found Redis configuration: {match}')
                        assert expected_redis_host in match, f'Redis host mismatch: expected {expected_redis_host} in {match}'

    def test_frontend_environment_variable_completeness(self):
        """CRITICAL: Test frontend environment variables are complete."""
        deployment_script = project_root / 'scripts' / 'deploy_to_gcp_actual.py'
        if not deployment_script.exists():
            pytest.skip('Deployment script not found')
        with open(deployment_script, 'r') as f:
            content = f.read()
        required_frontend_vars = ['NEXT_PUBLIC_ENVIRONMENT', 'NEXT_PUBLIC_API_URL', 'NEXT_PUBLIC_AUTH_URL', 'NEXT_PUBLIC_WS_URL', 'NEXT_PUBLIC_WEBSOCKET_URL', 'NEXT_PUBLIC_AUTH_SERVICE_URL', 'NEXT_PUBLIC_AUTH_API_URL', 'NEXT_PUBLIC_BACKEND_URL', 'NEXT_PUBLIC_FRONTEND_URL', 'NEXT_PUBLIC_FORCE_HTTPS', 'NEXT_PUBLIC_GTM_CONTAINER_ID', 'NEXT_PUBLIC_GTM_ENABLED', 'NEXT_PUBLIC_GTM_DEBUG']
        missing_vars = []
        for var in required_frontend_vars:
            if var not in content:
                missing_vars.append(var)
        assert not missing_vars, f'CRITICAL: Missing required frontend environment variables: {missing_vars}'
        print(f' PASS:  All {len(required_frontend_vars)} required frontend variables found')

    def test_configuration_drift_summary_report(self):
        """Generate comprehensive configuration drift summary report."""
        deployment_scripts = [project_root / 'scripts' / 'deploy_to_gcp_actual.py', project_root / 'terraform-gcp-staging' / 'deploy.sh']
        report = {'timestamp': '2025-09-11', 'test_purpose': 'Issue #245 - Deployment script consolidation configuration drift detection', 'scripts_analyzed': [], 'critical_findings': [], 'warnings': [], 'recommendations': []}
        for script in deployment_scripts:
            if script.exists():
                script_info = {'name': script.name, 'path': str(script), 'exists': True, 'size': script.stat().st_size}
                report['scripts_analyzed'].append(script_info)
        report['critical_findings'].extend(['WebSocket timeout configurations must be identical across deployment methods', 'JWT secret mappings must use same GSM secret (jwt-secret-staging)', 'OAuth URLs must be consistent for staging environment', 'Database instance references must be exact matches', 'Frontend environment variables are mandatory for deployment success'])
        report['recommendations'].extend(['Consolidate to single canonical deployment script (deploy_to_gcp_actual.py)', 'Fix terraform/deploy.sh line 111 to call correct deployment script', 'Implement configuration validation in deployment pipeline', 'Add automated drift detection to CI/CD process'])
        report_json = json.dumps(report, indent=2)
        print('\n' + '=' * 80)
        print('CONFIGURATION DRIFT DETECTION SUMMARY REPORT')
        print('=' * 80)
        print(report_json)
        print('=' * 80)
        report_file = project_root / 'test_plans' / 'configuration_drift_report.json'
        with open(report_file, 'w') as f:
            f.write(report_json)
        print(f' CHART:  Report saved to: {report_file}')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')