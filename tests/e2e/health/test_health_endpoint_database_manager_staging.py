"""
E2E Test: Health Endpoint Database Manager on Staging

Purpose: Test health endpoint behavior with database manager import issue on staging GCP
Issue #572: Database manager unavailable for health checks

This test MUST show degraded health endpoint behavior due to the import issue.
Note: This runs against staging GCP environment, not docker.
"""
import pytest
import asyncio
import aiohttp
import os
import json
from datetime import datetime
from typing import Dict, Any
from test_framework.ssot.base_test_case import SSotAsyncTestCase

@pytest.mark.e2e
class HealthEndpointDatabaseManagerStagingTests(SSotAsyncTestCase):
    """E2E test for health endpoint database manager issues on staging."""

    @classmethod
    def setUpClass(cls):
        """Set up class-level test configuration."""
        super().setUpClass()
        cls.staging_base_url = os.getenv('STAGING_BASE_URL', 'https://netra-staging-backend-12345-ue.a.run.app')
        cls.timeout = aiohttp.ClientTimeout(total=30)
        if not cls.staging_base_url or cls.staging_base_url.startswith('https://netra-staging-backend-12345'):
            pytest.skip('Staging URL not properly configured - skipping E2E tests')

    async def asyncSetUp(self):
        """Set up async test resources."""
        await super().asyncSetUp()
        self.session = aiohttp.ClientSession(timeout=self.timeout)

    async def asyncTearDown(self):
        """Clean up async test resources."""
        if hasattr(self, 'session'):
            await self.session.close()
        await super().asyncTearDown()

    async def test_health_endpoint_basic_availability_staging(self):
        """
        Test that staging health endpoint is accessible.
        
        This should PASS - basic connectivity test.
        """
        try:
            async with self.session.get(f'{self.staging_base_url}/health') as response:
                assert response.status in [200, 503], f'Health endpoint should be accessible, got status: {response.status}'
                content_type = response.headers.get('content-type', '')
                assert 'application/json' in content_type, f'Health endpoint should return JSON, got: {content_type}'
                data = await response.json()
                assert isinstance(data, dict), 'Health endpoint should return JSON object'
                assert 'status' in data, 'Health response should have status field'
        except aiohttp.ClientError as e:
            pytest.fail(f'Failed to connect to staging health endpoint: {e}')

    async def test_health_endpoint_database_manager_issue_staging(self):
        """
        CRITICAL: This test MUST show database manager issues on staging.
        
        Test that the health endpoint on staging shows database manager unavailability
        due to the import issue in deep_checks.py.
        """
        try:
            async with self.session.get(f'{self.staging_base_url}/health') as response:
                data = await response.json()
                overall_status = data.get('status')
                components = data.get('components', {})
                checks = data.get('checks', [])
                database_deep_found = False
                database_deep_unhealthy = False
                database_unavailable_message = False
                if 'database_deep' in components:
                    database_deep_found = True
                    db_deep_status = components['database_deep'].get('status')
                    db_deep_message = components['database_deep'].get('message', '').lower()
                    if db_deep_status == 'unhealthy':
                        database_deep_unhealthy = True
                    if 'unavailable' in db_deep_message or 'not initialized' in db_deep_message:
                        database_unavailable_message = True
                for check in checks:
                    if check.get('component_name') == 'database_deep':
                        database_deep_found = True
                        if check.get('status') == 'unhealthy':
                            database_deep_unhealthy = True
                        message = check.get('message', '').lower()
                        if 'unavailable' in message or 'not initialized' in message:
                            database_unavailable_message = True
                assert database_deep_found, f"Database deep check should be present in health response. Available components: {list(components.keys())}, Available checks: {[c.get('component_name') for c in checks]}"
                assert database_deep_unhealthy, f'Database deep check should be unhealthy due to import issue. If this passes, the issue may be resolved.'
                assert database_unavailable_message, f'Database deep check should indicate unavailability due to import failure. If this passes, the import issue may be resolved.'
        except aiohttp.ClientError as e:
            pytest.fail(f'Failed to test staging health endpoint: {e}')
        except json.JSONDecodeError as e:
            pytest.fail(f'Failed to parse health endpoint JSON response: {e}')

    async def test_health_endpoint_deep_checks_integration_staging(self):
        """
        Test that deep health checks are integrated into the staging health endpoint.
        
        This verifies that the deep_checks.py module is being used by the health endpoint,
        which means the import issue affects the staging environment.
        """
        try:
            async with self.session.get(f'{self.staging_base_url}/health') as response:
                data = await response.json()
                components = data.get('components', {})
                checks = data.get('checks', [])
                deep_check_components = ['database_deep', 'redis_deep', 'websocket_deep']
                found_deep_checks = []
                for component_name in deep_check_components:
                    if component_name in components:
                        found_deep_checks.append(component_name)
                for check in checks:
                    component_name = check.get('component_name')
                    if component_name in deep_check_components:
                        if component_name not in found_deep_checks:
                            found_deep_checks.append(component_name)
                assert len(found_deep_checks) > 0, f"Should have deep health checks integrated in staging. Available components: {list(components.keys())}, Available check names: {[c.get('component_name') for c in checks]}"
                if 'database_deep' in found_deep_checks:
                    db_deep_info = None
                    if 'database_deep' in components:
                        db_deep_info = components['database_deep']
                    else:
                        for check in checks:
                            if check.get('component_name') == 'database_deep':
                                db_deep_info = check
                                break
                    if db_deep_info:
                        message = db_deep_info.get('message', '').lower()
                        status = db_deep_info.get('status')
                        assert status == 'unhealthy', f'Database deep check should be unhealthy on staging due to import issue. Status: {status}, Message: {message}'
                        assert 'unavailable' in message or 'not initialized' in message, f'Database deep check should indicate unavailability. Message: {message}'
        except aiohttp.ClientError as e:
            pytest.fail(f'Failed to test deep checks integration on staging: {e}')

    async def test_staging_environment_validation(self):
        """
        Validate that we're testing against the correct staging environment.
        
        This should PASS and confirms we're testing the right environment.
        """
        try:
            async with self.session.get(f'{self.staging_base_url}/') as response:
                assert response.status in [200, 404, 405], f'Should connect to staging environment, got: {response.status}'
            async with self.session.get(f'{self.staging_base_url}/health') as response:
                data = await response.json()
                assert 'status' in data, 'Health endpoint should have status'
                environment_indicators = ['environment', 'env', 'deployment', 'stage']
                found_environment = False
                for key in environment_indicators:
                    if key in data:
                        found_environment = True
                        break
                if found_environment:
                    env_info = str(data.get('environment', data.get('env', data.get('deployment', data.get('stage', ''))))).lower()
                    if env_info:
                        assert 'staging' in env_info or 'stage' in env_info, f'Should be testing staging environment, got: {env_info}'
        except aiohttp.ClientError as e:
            pytest.fail(f'Failed to validate staging environment: {e}')

    async def test_health_response_structure_staging(self):
        """
        Test the structure of health response to understand the format.
        
        This helps understand how the import issue manifests in the actual response.
        """
        try:
            async with self.session.get(f'{self.staging_base_url}/health') as response:
                data = await response.json()
                print(f'\nStaging Health Response Structure:')
                print(f'Status Code: {response.status}')
                print(f'Response Keys: {list(data.keys())}')
                if 'components' in data:
                    print(f"Components: {list(data['components'].keys())}")
                    for comp_name, comp_data in data['components'].items():
                        if 'database' in comp_name.lower():
                            print(f"Database Component '{comp_name}': {comp_data}")
                if 'checks' in data:
                    print(f"Checks count: {len(data['checks'])}")
                    for check in data['checks']:
                        comp_name = check.get('component_name', 'unknown')
                        if 'database' in comp_name.lower():
                            print(f"Database Check '{comp_name}': status={check.get('status')}, message={check.get('message')}")
                assert isinstance(data, dict), 'Health response should be a dictionary'
                assert 'status' in data, 'Health response should have overall status'
                assert 'components' in data or 'checks' in data, 'Health response should have components or checks'
        except aiohttp.ClientError as e:
            pytest.fail(f'Failed to test health response structure: {e}')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')