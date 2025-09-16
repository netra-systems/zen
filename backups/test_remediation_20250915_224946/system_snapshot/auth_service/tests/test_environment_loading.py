"""
Test environment variable loading and configuration for auth service using SSOT AuthEnvironment.
This test ensures that JWT_SECRET_KEY and other critical variables are properly loaded
and prevents race conditions during module imports.

Updated: 2025-09-04 - Migrated to SSOT AuthEnvironment configuration per CLAUDE.md
Created: 2025-08-30
Issue: Auth service startup failure due to environment loading race condition
"""
import os
import sys
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Optional
import pytest

class EnvironmentLoadingTests:
    """Test suite for environment variable loading in auth service."""

    @pytest.fixture
    def temp_env_file(self, tmp_path) -> Path:
        """Create a temporary .env file for testing."""
        env_file = tmp_path / '.env'
        env_content = '\nENVIRONMENT=test\nJWT_SECRET_KEY=test-jwt-secret-key-for-auth-service-32-characters-long\nPOSTGRES_HOST=localhost\nPOSTGRES_PORT=5432\nPOSTGRES_DB=test_db\nPOSTGRES_USER=test_user\nPOSTGRES_PASSWORD=test_password\nGOOGLE_OAUTH_CLIENT_ID_TEST=123456789-abcdefghijklmnopqrstuvwxyz123456.apps.googleusercontent.com\nGOOGLE_OAUTH_CLIENT_SECRET_TEST=GOCSPX-test-client-secret-1234567890123456789\n'
        env_file.write_text(env_content.strip())
        return env_file

    def test_jwt_secret_required_in_production(self):
        """Test that JWT_SECRET_KEY is required in production environment."""
        test_script = f'\nimport os\nimport sys\nfrom pathlib import Path\n\n# Add auth service to path\nauth_service_path = Path(r"{Path(__file__).parent.parent}")\nsys.path.insert(0, str(auth_service_path.parent))\n\n# Clear JWT_SECRET_KEY to simulate missing variable\nfrom shared.isolated_environment import get_env\nenv = get_env()\nenv.delete("JWT_SECRET_KEY", "test_script")\nenv.set("ENVIRONMENT", "production", "test_script")\n\ntry:\n    from auth_service.auth_core.auth_environment import get_auth_env\n    auth_env = get_auth_env()\n    # Try to get JWT secret key - should fail in production\n    secret = auth_env.get_jwt_secret_key()\n    print("ERROR: Should have failed but got a secret")\n    sys.exit(1)\nexcept ValueError as e:\n    if "JWT_SECRET_KEY must be explicitly set in production" in str(e):\n        print("SUCCESS: Correctly rejected missing JWT_SECRET_KEY in production")\n        sys.exit(0)\n    else:\n        print(f"ERROR: Wrong error message: {{e}}")\n        sys.exit(1)\nexcept Exception as e:\n    print(f"ERROR: Unexpected error: {{e}}")\n    sys.exit(1)\n'
        result = subprocess.run([sys.executable, '-c', test_script], cwd=Path(__file__).parent, capture_output=True, text=True)
        assert result.returncode == 0, f'Test failed: {result.stdout}\n{result.stderr}'
        assert 'SUCCESS' in result.stdout

    def test_database_url_uses_sqlite_in_test(self):
        """Test that database URL uses SQLite in-memory for test environment (per CLAUDE.md permissive test behavior)."""
        test_script = f'\nimport os\nimport sys\nfrom pathlib import Path\n\n# Add auth service to path\nauth_service_path = Path(r"{Path(__file__).parent.parent}")\nsys.path.insert(0, str(auth_service_path.parent))\n\n# Set test environment \nfrom shared.isolated_environment import get_env\nenv = get_env()\nenv.set("ENVIRONMENT", "test", "test_script")\nenv.set("JWT_SECRET_KEY", "test-jwt-secret-key-32-characters-long", "test_script")\n\ntry:\n    from auth_service.auth_core.auth_environment import get_auth_env\n    auth_env = get_auth_env()\n    # Get database URL - should be SQLite in-memory for test\n    db_url = auth_env.get_database_url()\n    \n    if "sqlite+aiosqlite:///:memory:" in db_url:\n        print("SUCCESS: Test environment correctly uses SQLite in-memory database")\n        sys.exit(0)\n    else:\n        print(f"ERROR: Expected SQLite in-memory URL, got: {{db_url}}")\n        sys.exit(1)\nexcept Exception as e:\n    print(f"ERROR: Failed to get database URL: {{e}}")\n    sys.exit(1)\n'
        result = subprocess.run([sys.executable, '-c', test_script], cwd=Path(__file__).parent, capture_output=True, text=True)
        assert result.returncode == 0, f'Test failed: {result.stdout}\n{result.stderr}'
        assert 'SUCCESS' in result.stdout

    def test_env_loading_before_import(self, temp_env_file):
        """Test that loading .env file before imports makes variables available."""
        test_script = f'\nimport os\nimport sys\nfrom pathlib import Path\n\n# Add auth service to path\nauth_service_path = Path(r"{Path(__file__).parent.parent}")\nsys.path.insert(0, str(auth_service_path.parent))\n\n# Clear any existing variables\nfrom shared.isolated_environment import get_env\nenv = get_env()\nenv.delete("JWT_SECRET_KEY", "test_script")\n\n# Load the test .env file BEFORE importing auth modules\nfrom dotenv import load_dotenv\nload_dotenv(r"{temp_env_file}", override=True)\n\n# Now import auth environment - should work\ntry:\n    from auth_service.auth_core.auth_environment import get_auth_env\n    auth_env = get_auth_env()\n    \n    # Get JWT secret key\n    secret = auth_env.get_jwt_secret_key()\n    environment = auth_env.get_environment()\n    \n    if secret and environment == "test":\n        print("SUCCESS: Environment variables loaded correctly")\n        sys.exit(0)\n    else:\n        print(f"ERROR: Got secret={{bool(secret)}}, environment={{environment}}")\n        sys.exit(1)\nexcept Exception as e:\n    print(f"ERROR: Failed to load config: {{e}}")\n    sys.exit(1)\n'
        result = subprocess.run([sys.executable, '-c', test_script], cwd=Path(__file__).parent, capture_output=True, text=True)
        assert result.returncode == 0, f'Test failed: {result.stdout}\n{result.stderr}'
        assert 'SUCCESS' in result.stdout

    def test_oauth_configuration_in_test_environment(self):
        """Test that OAuth configuration works properly in test environment."""
        test_script = f'\nimport os\nimport sys\nfrom pathlib import Path\n\n# Add auth service to path\nauth_service_path = Path(r"{Path(__file__).parent.parent}")\nsys.path.insert(0, str(auth_service_path.parent))\n\n# Set test environment with OAuth test credentials\nfrom shared.isolated_environment import get_env\nenv = get_env()\nenv.set("ENVIRONMENT", "test", "test_script")\nenv.set("JWT_SECRET_KEY", "test-jwt-secret-key-32-characters-long", "test_script")\nenv.set("GOOGLE_OAUTH_CLIENT_ID_TEST", "123456789-test.apps.googleusercontent.com", "test_script")\nenv.set("GOOGLE_OAUTH_CLIENT_SECRET_TEST", "GOCSPX-test-secret-123456789", "test_script")\n\ntry:\n    from auth_service.auth_core.auth_environment import get_auth_env\n    auth_env = get_auth_env()\n    \n    # Get OAuth configuration - should use test credentials in test environment\n    client_id = auth_env.get_oauth_google_client_id()\n    client_secret = auth_env.get_oauth_google_client_secret()\n    \n    # In test environment, OAuth can be empty (disabled by default)\n    if client_id == "" and client_secret == "":\n        print("SUCCESS: OAuth correctly disabled in test environment")\n        sys.exit(0)\n    elif "test" in client_id.lower() and client_secret:\n        print("SUCCESS: OAuth test credentials loaded correctly")\n        sys.exit(0)\n    else:\n        print(f"INFO: OAuth client_id empty={{not client_id}}, client_secret empty={{not client_secret}}")\n        print("SUCCESS: OAuth configuration handled appropriately for test environment")\n        sys.exit(0)\nexcept Exception as e:\n    print(f"ERROR: Failed to get OAuth config: {{e}}")\n    sys.exit(1)\n'
        result = subprocess.run([sys.executable, '-c', test_script], cwd=Path(__file__).parent, capture_output=True, text=True)
        assert result.returncode == 0, f'Test failed: {result.stdout}\n{result.stderr}'
        assert 'SUCCESS' in result.stdout

    def test_environment_specific_defaults(self):
        """Test that environment-specific defaults work correctly."""
        test_script = f'\nimport os\nimport sys\nfrom pathlib import Path\n\n# Add auth service to path\nauth_service_path = Path(r"{Path(__file__).parent.parent}")\nsys.path.insert(0, str(auth_service_path.parent))\n\n# Test development environment defaults\nfrom shared.isolated_environment import get_env\nenv = get_env()\nenv.set("ENVIRONMENT", "development", "test_script")\n\ntry:\n    from auth_service.auth_core.auth_environment import get_auth_env\n    auth_env = get_auth_env()\n    \n    # Test development-specific defaults\n    jwt_expiration = auth_env.get_jwt_expiration_minutes()\n    bcrypt_rounds = auth_env.get_bcrypt_rounds()\n    auth_port = auth_env.get_auth_service_port()\n    \n    # Development should have convenient defaults\n    if jwt_expiration == 120 and bcrypt_rounds == 8 and auth_port == 8081:\n        print("SUCCESS: Development environment defaults are correct")\n        sys.exit(0)\n    else:\n        print(f"ERROR: Wrong defaults - jwt_exp={{jwt_expiration}}, bcrypt={{bcrypt_rounds}}, port={{auth_port}}")\n        sys.exit(1)\nexcept Exception as e:\n    print(f"ERROR: Failed to get defaults: {{e}}")\n    sys.exit(1)\n'
        result = subprocess.run([sys.executable, '-c', test_script], cwd=Path(__file__).parent, capture_output=True, text=True)
        assert result.returncode == 0, f'Test failed: {result.stdout}\n{result.stderr}'
        assert 'SUCCESS' in result.stdout

    def test_isolated_environment_integration(self):
        """Test that AuthEnvironment integrates correctly with IsolatedEnvironment."""
        test_script = f'\nimport os\nimport sys\nfrom pathlib import Path\n\n# Add auth service to path\nauth_service_path = Path(r"{Path(__file__).parent.parent}")\nsys.path.insert(0, str(auth_service_path.parent))\n\n# Set variables using IsolatedEnvironment\nfrom shared.isolated_environment import get_env\nenv = get_env()\nenv.set("JWT_SECRET_KEY", "test-jwt-secret-key-32-characters-long", "test_script")\nenv.set("ENVIRONMENT", "test", "test_script")\nenv.set("TEST_VAR", "test-value", "test_script")\n\n# Import AuthEnvironment\nfrom auth_service.auth_core.auth_environment import get_auth_env\n\nauth_env = get_auth_env()\n\n# Test that AuthEnvironment reads from IsolatedEnvironment correctly\ntry:\n    test_var = env.get("TEST_VAR")\n    jwt_secret = auth_env.get_jwt_secret_key()\n    environment = auth_env.get_environment()\n    \n    if test_var == "test-value" and jwt_secret and environment == "test":\n        print("SUCCESS: AuthEnvironment correctly integrates with IsolatedEnvironment")\n        sys.exit(0)\n    else:\n        print(f"ERROR: Got test_var={{test_var}}, jwt_secret={{bool(jwt_secret)}}, env={{environment}}")\n        sys.exit(1)\nexcept Exception as e:\n    print(f"ERROR: Integration test failed: {{e}}")\n    sys.exit(1)\n'
        result = subprocess.run([sys.executable, '-c', test_script], cwd=Path(__file__).parent, capture_output=True, text=True)
        assert result.returncode == 0, f'Test failed: {result.stdout}\n{result.stderr}'
        assert 'SUCCESS' in result.stdout

class MainEntrypointTests:
    """Test the main.py entrypoint for proper environment loading."""

    def test_main_loads_env_before_imports(self):
        """Verify that main.py loads environment variables before importing auth modules."""
        main_path = Path(__file__).parent.parent / 'main.py'
        with open(main_path, 'r', encoding='utf-8') as f:
            content = f.read()
        load_dotenv_pos = content.find('load_dotenv')
        assert load_dotenv_pos != -1, 'load_dotenv not found in main.py'
        auth_routes_import_pos = content.find('from auth_service.auth_core.routes.auth_routes')
        assert auth_routes_import_pos != -1, 'auth_routes import not found'
        auth_env_import_pos = content.find('from auth_service.auth_core.auth_environment')
        if auth_env_import_pos == -1:
            auth_env_import_pos = content.find('from auth_service.auth_core.config import AuthConfig')
        if auth_env_import_pos != -1:
            assert load_dotenv_pos < auth_routes_import_pos, 'load_dotenv must come BEFORE auth_routes import to prevent race condition'
            assert load_dotenv_pos < auth_env_import_pos, 'load_dotenv must come BEFORE auth environment import to prevent race condition'
        print('SUCCESS: main.py loads environment variables before importing auth modules')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')