"""
Test file to validate specific fixes for auth and websocket test failures
"""
import pytest
from tests.e2e.config import get_test_environment_config, TestEnvironmentType
from tests.e2e.harness_utils import UnifiedTestHarnessComplete
from tests.e2e.jwt_token_helpers import JWTTestHelper
from tests.e2e.database_sync_fixtures import create_test_user_data
from shared.isolated_environment import IsolatedEnvironment

@pytest.mark.e2e
def test_config_function_signature():
    """Test that get_test_environment_config works with both signatures"""
    config1 = get_test_environment_config(TestEnvironmentType.LOCAL)
    assert config1 is not None
    assert config1.environment_type == TestEnvironmentType.LOCAL
    config2 = get_test_environment_config(environment=TestEnvironmentType.LOCAL)
    assert config2 is not None
    assert config2.environment_type == TestEnvironmentType.LOCAL
    assert config1.base_url == config2.base_url
    assert config1.services.auth == config2.services.auth

@pytest.mark.e2e
def test_test_services_has_frontend():
    """Test that TestServices now includes frontend attribute"""
    config = get_test_environment_config()
    assert hasattr(config.services, 'frontend')
    assert config.services.frontend is not None
    assert config.services.frontend == 'http://localhost:3000'

@pytest.mark.e2e
def test_harness_initialization():
    """Test that UnifiedTestHarnessComplete can be initialized without errors"""
    harness = UnifiedTestHarnessComplete('test_fixes')
    assert harness is not None
    assert hasattr(harness, 'project_root')
    assert hasattr(harness, 'database_manager')
    assert hasattr(harness, 'service_manager')
    project_root = harness.project_root
    assert project_root is not None

@pytest.mark.e2e
def test_jwt_helper_initialization():
    """Test that JWTTestHelper can be initialized"""
    jwt_helper = JWTTestHelper()
    assert jwt_helper is not None
    assert hasattr(jwt_helper, 'environment')

@pytest.mark.e2e
def test_database_fixtures():
    """Test that database fixtures work"""
    user_data = create_test_user_data('test_user')
    assert user_data is not None
    assert 'email' in user_data
    assert 'id' in user_data
    assert user_data['email'].startswith('sync-test-')
    assert user_data['id'].startswith('sync-test-')

@pytest.mark.e2e
def test_environment_type_attribute():
    """Test that environment_type attribute exists on config"""
    config = get_test_environment_config()
    assert hasattr(config, 'environment_type')
    assert config.environment_type == TestEnvironmentType.LOCAL
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')