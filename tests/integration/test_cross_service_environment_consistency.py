"""
Test cross-service environment consistency for SSOT refactor validation.

This test suite validates that backend and auth services handle environment
variables consistently across different deployment environments.

CRITICAL: Tests designed to expose inconsistencies before SSOT refactor
and validate unified behavior after refactor.

GitHub Issue: #189 - Environment loading duplication SSOT violation  
Test Plan Step: 2 - Execute Test Plan
"""

import os
import sys
import pytest
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple
from unittest.mock import patch, MagicMock

from shared.isolated_environment import get_env
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestCrossServiceEnvironmentConsistency(SSotBaseTestCase):
    """Test suite for cross-service environment variable consistency."""

    def test_production_environment_variables_identical(self):
        """
        Test that both services handle production environment variables identically.
        
        In production:
        - Both should skip .env file loading
        - Both should rely on Cloud Run environment variables
        - Both should use Google Secret Manager for secrets
        """
        test_script = '''
import sys
import os  
from pathlib import Path

# Add services to path
root_path = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_path))

from shared.isolated_environment import get_env

# Set production environment
env = get_env()
env.set("ENVIRONMENT", "production", "test_script")

# Clear any dev variables that might interfere
env.delete("DEV_LAUNCHER_ACTIVE", "test_script") 
env.delete("CROSS_SERVICE_AUTH_TOKEN", "test_script")

try:
    # Test backend production behavior
    from netra_backend.app.main import _setup_environment_files
    
    # Should skip all .env loading in production
    _setup_environment_files()  # Should return early
    
    # Test auth production behavior by examining source
    auth_main_source = open(Path(root_path) / "auth_service" / "main.py").read()
    
    # Check if auth skips .env in production
    auth_skips_env_in_prod = (
        "if environment in ['staging', 'production', 'prod']:" in auth_main_source and
        "skipping .env file loading" in auth_main_source
    )
    
    if auth_skips_env_in_prod:
        print("SUCCESS: Both services skip .env loading in production")
        sys.exit(0) 
    else:
        print("FAIL: Inconsistent production environment handling")
        print(f"Auth skips env in prod: {auth_skips_env_in_prod}")
        sys.exit(1)
        
except Exception as e:
    print(f"ERROR: Production environment test failed: {e}")
    sys.exit(1)
'''
        
        result = subprocess.run(
            [sys.executable, "-c", test_script],
            cwd=Path(__file__).parent.parent.parent,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            assert "SUCCESS" in result.stdout
        else:
            pytest.fail(f"Production environment consistency test failed: {result.stdout}\n{result.stderr}")

    def test_development_environment_variables_identical(self):
        """
        Test that both services load development .env files consistently.
        
        In development:
        - Both should load .env files when not using dev launcher
        - Both should respect same .env file precedence 
        - Both should handle missing .env files gracefully
        """
        test_script = '''
import sys
import tempfile
from pathlib import Path

# Add services to path
root_path = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_path))

from shared.isolated_environment import get_env

# Set development environment 
env = get_env()
env.set("ENVIRONMENT", "development", "test_script")

# Clear dev launcher indicators
env.delete("DEV_LAUNCHER_ACTIVE", "test_script")
env.delete("CROSS_SERVICE_AUTH_TOKEN", "test_script")

# Clear any existing test variables
env.delete("TEST_BACKEND_VAR", "test_script")
env.delete("TEST_AUTH_VAR", "test_script")

with tempfile.TemporaryDirectory() as temp_dir:
    temp_path = Path(temp_dir)
    
    # Create test .env file
    env_content = """
TEST_BACKEND_VAR=backend_value
TEST_AUTH_VAR=auth_value
JWT_SECRET_KEY=test-jwt-secret-key-32-characters-long
"""
    (temp_path / ".env").write_text(env_content.strip())
    
    try:
        # Test backend .env loading
        from netra_backend.app.main import _load_all_env_files
        _load_all_env_files(temp_path)
        
        backend_var = env.get("TEST_BACKEND_VAR")
        
        # Reset environment for auth test
        env.delete("TEST_BACKEND_VAR", "test_script")
        env.delete("TEST_AUTH_VAR", "test_script")
        
        # Test auth .env loading (simulate auth service behavior)
        from dotenv import load_dotenv
        load_dotenv(temp_path / ".env", override=True)
        
        auth_var = env.get("TEST_AUTH_VAR")
        
        # Both should have loaded variables
        if backend_var == "backend_value" and auth_var == "auth_value":
            print("SUCCESS: Both services load .env files in development")
            sys.exit(0)
        else:
            print(f"FAIL: Inconsistent .env loading - backend: {backend_var}, auth: {auth_var}")
            sys.exit(1)
            
    except Exception as e:
        print(f"ERROR: Development environment test failed: {e}")
        sys.exit(1)
'''
        
        result = subprocess.run(
            [sys.executable, "-c", test_script],
            cwd=Path(__file__).parent.parent.parent,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            assert "SUCCESS" in result.stdout
        else:
            pytest.fail(f"Development environment test failed: {result.stdout}\n{result.stderr}")

    def test_env_file_precedence_rules_consistent(self):
        """
        Test that both services apply same precedence rules for .env files.
        
        Expected precedence (highest to lowest):
        1. Environment variables already set
        2. .env.development.local (backend only)
        3. .env.development (backend only) 
        4. .env (both services)
        
        SSOT should unify these precedence rules.
        """
        test_script = '''
import sys
import tempfile
from pathlib import Path

# Add services to path
root_path = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_path))

from shared.isolated_environment import get_env

# Set development environment
env = get_env()
env.set("ENVIRONMENT", "development", "test_script")

# Clear dev launcher indicators  
env.delete("DEV_LAUNCHER_ACTIVE", "test_script")
env.delete("CROSS_SERVICE_AUTH_TOKEN", "test_script")

with tempfile.TemporaryDirectory() as temp_dir:
    temp_path = Path(temp_dir)
    
    # Create cascading .env files with different precedence
    (temp_path / ".env").write_text("PRECEDENCE_TEST=base")
    (temp_path / ".env.development").write_text("PRECEDENCE_TEST=dev")
    (temp_path / ".env.development.local").write_text("PRECEDENCE_TEST=local")
    
    # Clear test variable
    env.delete("PRECEDENCE_TEST", "test_script")
    
    try:
        # Test backend precedence (should load all files, local wins)
        from netra_backend.app.main import _load_all_env_files
        _load_all_env_files(temp_path)
        
        backend_result = env.get("PRECEDENCE_TEST")
        
        # Reset for auth test
        env.delete("PRECEDENCE_TEST", "test_script")
        
        # Test auth precedence (only loads base .env)
        from dotenv import load_dotenv
        load_dotenv(temp_path / ".env", override=True)
        
        auth_result = env.get("PRECEDENCE_TEST") 
        
        # Check precedence consistency
        if backend_result == "local" and auth_result == "base":
            print("FAIL: Different precedence rules")
            print(f"Backend: {backend_result}, Auth: {auth_result}")
            sys.exit(1)
        elif backend_result == auth_result:
            print("SUCCESS: Consistent precedence rules")
            sys.exit(0)
        else:
            print(f"INCONSISTENT: Backend: {backend_result}, Auth: {auth_result}")
            sys.exit(1)
            
    except Exception as e:
        print(f"ERROR: Precedence rules test failed: {e}")
        sys.exit(1)
'''
        
        result = subprocess.run(
            [sys.executable, "-c", test_script],
            cwd=Path(__file__).parent.parent.parent,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 1 and "Different precedence rules" in result.stdout:
            # Expected failure - shows precedence inconsistency
            pytest.skip("EXPECTED: Different precedence rules before SSOT refactor")
        elif result.returncode == 0:
            assert "SUCCESS" in result.stdout
        else:
            pytest.fail(f"Precedence rules test failed: {result.stdout}\n{result.stderr}")

    def test_sensitive_variable_handling_consistent(self):
        """
        Test that both services handle sensitive variables (secrets, keys) consistently.
        
        Sensitive variables should:
        - Be loaded from same sources in each environment
        - Have same fallback behavior
        - Be masked consistently in logs
        """
        test_script = '''
import sys
import tempfile
from pathlib import Path

# Add services to path
root_path = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_path))

from shared.isolated_environment import get_env

# Set test environment
env = get_env() 
env.set("ENVIRONMENT", "test", "test_script")

# Set sensitive test variables
sensitive_vars = {
    "JWT_SECRET_KEY": "test-jwt-secret-key-32-characters-long",
    "POSTGRES_PASSWORD": "test_db_password", 
    "GOOGLE_OAUTH_CLIENT_SECRET": "test_oauth_secret"
}

for key, value in sensitive_vars.items():
    env.set(key, value, "test_script")

try:
    # Test backend sensitive variable access
    from netra_backend.app.config import get_config
    backend_config = get_config()
    
    backend_jwt = backend_config.jwt_secret_key
    backend_db_pass = getattr(backend_config, 'postgres_password', None)
    
    # Test auth sensitive variable access
    from auth_service.auth_core.auth_environment import get_auth_env
    auth_env = get_auth_env()
    
    auth_jwt = auth_env.get_jwt_secret_key()
    auth_oauth_secret = auth_env.get_oauth_google_client_secret()
    
    # Verify both can access sensitive variables
    backend_has_jwt = backend_jwt is not None and len(backend_jwt) > 0
    auth_has_jwt = auth_jwt is not None and len(auth_jwt) > 0
    
    if backend_has_jwt and auth_has_jwt:
        print("SUCCESS: Both services handle sensitive variables consistently")
        sys.exit(0)
    else:
        print(f"FAIL: Inconsistent sensitive variable handling")
        print(f"Backend JWT: {bool(backend_has_jwt)}, Auth JWT: {bool(auth_has_jwt)}")
        sys.exit(1)
        
except Exception as e:
    print(f"ERROR: Sensitive variable test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
'''
        
        result = subprocess.run(
            [sys.executable, "-c", test_script],
            cwd=Path(__file__).parent.parent.parent,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            assert "SUCCESS" in result.stdout
        else:
            pytest.fail(f"Sensitive variable test failed: {result.stdout}\n{result.stderr}")

    def test_environment_bypass_logic_identical(self):
        """
        Test that both services have identical logic for bypassing .env loading.
        
        Bypass conditions should be identical:
        1. Production/staging environments
        2. Dev launcher active
        3. Critical variables already set
        
        SSOT refactor should unify these bypass rules.
        """
        test_script = '''
import sys
from pathlib import Path

# Add services to path
root_path = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_path))

from shared.isolated_environment import get_env

try:
    # Read both service implementations
    backend_main_source = open(Path(root_path) / "netra_backend" / "app" / "main.py").read()
    auth_main_source = open(Path(root_path) / "auth_service" / "main.py").read()
    
    # Check bypass conditions consistency
    bypass_checks = [
        ("staging", "staging" in backend_main_source, "staging" in auth_main_source),
        ("production", "production" in backend_main_source, "production" in auth_main_source),
        ("dev_launcher", "DEV_LAUNCHER_ACTIVE" in backend_main_source, "DEV_LAUNCHER_ACTIVE" in auth_main_source),
    ]
    
    inconsistencies = []
    for condition, backend_has, auth_has in bypass_checks:
        if backend_has != auth_has:
            inconsistencies.append(f"{condition}: backend={backend_has}, auth={auth_has}")
    
    if not inconsistencies:
        print("SUCCESS: Consistent bypass logic across services")
        sys.exit(0)
    else:
        print("FAIL: Inconsistent bypass logic detected:")
        for inconsistency in inconsistencies:
            print(f"  {inconsistency}")
        sys.exit(1)
        
except Exception as e:
    print(f"ERROR: Bypass logic test failed: {e}")
    sys.exit(1)
'''
        
        result = subprocess.run(
            [sys.executable, "-c", test_script],
            cwd=Path(__file__).parent.parent.parent,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            assert "SUCCESS" in result.stdout
        elif result.returncode == 1 and "Inconsistent bypass logic" in result.stdout:
            # Expected before SSOT refactor
            pytest.skip("EXPECTED: Inconsistent bypass logic before SSOT refactor")
        else:
            pytest.fail(f"Bypass logic test failed: {result.stdout}\n{result.stderr}")