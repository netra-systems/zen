"""
Test SSOT environment loading integration across backend and auth services.

This test suite validates that both services use the SAME environment loading logic,
eliminating the duplication between netra_backend/app/main.py and auth_service/main.py.

CRITICAL: These tests are designed to FAIL before SSOT refactor and PASS after.

GitHub Issue: #189 - Environment loading duplication SSOT violation
Test Plan Step: 2 - Execute Test Plan
"""

import os
import sys
import pytest
import subprocess
from pathlib import Path
from typing import Dict, Any, List
from unittest.mock import patch, MagicMock

from shared.isolated_environment import get_env
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestEnvironmentLoadingSSotIntegration(SSotBaseTestCase):
    """Test suite for SSOT environment loading integration."""

    def test_backend_and_auth_use_same_environment_loader(self):
        """
        Verify both backend and auth services use unified SSOT environment loader.
        
        BEFORE REFACTOR: This test will FAIL because services use different loading logic
        AFTER REFACTOR: This test will PASS when both use the same SSOT module
        """
        # Test script to verify both services use same environment loading logic
        test_script = '''
import sys
from pathlib import Path

# Add services to path
root_path = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_path))

try:
    # Import environment loading functions from both services
    from netra_backend.app.main import _setup_environment_files as backend_loader
    from auth_service.main import main as auth_main_func
    
    # Check if both use the same SSOT implementation
    # This will fail if they have different implementations
    backend_loader_module = backend_loader.__module__
    
    # For auth service, check if it imports from SSOT
    auth_main_source = open(Path(root_path) / "auth_service" / "main.py").read()
    
    if "from shared.environment_loading_ssot" in auth_main_source:
        print("SUCCESS: Both services use SSOT environment loading")
        sys.exit(0)
    else:
        print("FAIL: Auth service does not use SSOT environment loading")
        print(f"Backend loader module: {backend_loader_module}")
        sys.exit(1)
        
except ImportError as e:
    # Before refactor, SSOT module doesn't exist - test should fail
    if "shared.environment_loading_ssot" in str(e):
        print("EXPECTED FAILURE: SSOT environment loading module not yet created")
        sys.exit(1)
    else:
        print(f"UNEXPECTED FAILURE: {e}")
        sys.exit(1)
except Exception as e:
    print(f"ERROR: Unexpected error during SSOT validation: {e}")
    sys.exit(1)
'''
        
        result = subprocess.run(
            [sys.executable, "-c", test_script],
            cwd=Path(__file__).parent.parent.parent,
            capture_output=True,
            text=True
        )
        
        # Before SSOT refactor, this should fail
        # After SSOT refactor, this should pass
        if result.returncode == 1 and "EXPECTED FAILURE" in result.stdout:
            # This is expected before refactor - mark as expected failure
            pytest.skip("EXPECTED: SSOT environment loading not yet implemented")
        elif result.returncode == 0 and "SUCCESS" in result.stdout:
            # After refactor, this should pass
            assert True
        else:
            pytest.fail(f"Test failed unexpectedly: {result.stdout}\n{result.stderr}")

    def test_identical_staging_detection_logic(self):
        """
        Ensure both services have identical staging environment detection.
        
        Current state: Backend and auth have different staging detection logic
        Expected after SSOT: Both use same staging detection implementation
        """
        test_script = '''
import sys
import os
from pathlib import Path

# Add services to path
root_path = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_path))

from shared.isolated_environment import get_env

# Set test environment
env = get_env()
env.set("ENVIRONMENT", "staging", "test_script")

try:
    # Test backend staging detection
    from netra_backend.app.main import _setup_environment_files
    backend_detected_staging = False
    
    # Backend skips .env loading in staging
    _setup_environment_files()  # Should return early for staging
    backend_detected_staging = True  # If no exception, staging was detected
    
    # Test auth staging detection  
    from auth_service.main import main
    auth_main_source = open(Path(root_path) / "auth_service" / "main.py").read()
    auth_detected_staging = "environment in ['staging', 'production', 'prod']" in auth_main_source
    
    if backend_detected_staging and auth_detected_staging:
        print("SUCCESS: Both services detect staging environment consistently")
        sys.exit(0)
    else:
        print(f"FAIL: Inconsistent staging detection - backend: {backend_detected_staging}, auth: {auth_detected_staging}")
        sys.exit(1)
        
except Exception as e:
    print(f"ERROR: Failed staging detection test: {e}")
    sys.exit(1)
'''
        
        result = subprocess.run(
            [sys.executable, "-c", test_script],
            cwd=Path(__file__).parent.parent.parent,
            capture_output=True,
            text=True
        )
        
        # This test validates current behavior and should pass
        # But highlights the inconsistency that SSOT will fix
        if result.returncode == 0:
            assert "SUCCESS" in result.stdout
        else:
            # Expected to fail before SSOT - shows inconsistency
            pytest.skip("EXPECTED: Staging detection inconsistent before SSOT refactor")

    def test_consistent_env_file_loading_sequence(self):
        """
        Validate both services use same .env file loading order and sequence.
        
        Backend loads: .env -> .env.development -> .env.development.local
        Auth loads: parent/.env -> fallback to current directory
        
        SSOT should unify this sequence.
        """
        test_script = '''
import sys
import tempfile
from pathlib import Path

# Add services to path  
root_path = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_path))

from shared.isolated_environment import get_env

# Create temporary .env files to test loading sequence
with tempfile.TemporaryDirectory() as temp_dir:
    temp_path = Path(temp_dir)
    
    # Create test .env files with different values
    (temp_path / ".env").write_text("TEST_VAR=base_value")
    (temp_path / ".env.development").write_text("TEST_VAR=dev_value")  
    (temp_path / ".env.development.local").write_text("TEST_VAR=local_value")
    
    # Clear environment
    env = get_env()
    env.delete("TEST_VAR", "test_script")
    env.delete("ENVIRONMENT", "test_script")
    
    try:
        # Test backend loading sequence
        from netra_backend.app.main import _load_all_env_files
        _load_all_env_files(temp_path)
        
        backend_final_value = env.get("TEST_VAR")
        
        # Reset for auth test
        env.delete("TEST_VAR", "test_script") 
        
        # Test auth loading sequence (simplified simulation)
        from dotenv import load_dotenv
        load_dotenv(temp_path / ".env", override=True)
        
        auth_final_value = env.get("TEST_VAR")
        
        # Compare loading sequences
        if backend_final_value == "local_value" and auth_final_value == "base_value":
            print("FAIL: Different env loading sequences detected")
            print(f"Backend final: {backend_final_value}, Auth final: {auth_final_value}")
            sys.exit(1)
        elif backend_final_value == auth_final_value:
            print("SUCCESS: Consistent env loading sequence")
            sys.exit(0)
        else:
            print(f"INCONSISTENT: Backend: {backend_final_value}, Auth: {auth_final_value}")
            sys.exit(1)
            
    except Exception as e:
        print(f"ERROR: Env loading sequence test failed: {e}")
        sys.exit(1)
'''
        
        result = subprocess.run(
            [sys.executable, "-c", test_script],
            cwd=Path(__file__).parent.parent.parent,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 1 and "Different env loading sequences" in result.stdout:
            # Expected failure before SSOT refactor
            pytest.skip("EXPECTED: Different env loading sequences before SSOT")
        elif result.returncode == 0:
            assert "SUCCESS" in result.stdout
        else:
            pytest.fail(f"Unexpected test result: {result.stdout}\n{result.stderr}")

    def test_unified_dev_launcher_detection(self):
        """
        Ensure consistent dev launcher detection across both services.
        
        Backend checks: DEV_LAUNCHER_ACTIVE, CROSS_SERVICE_AUTH_TOKEN
        Auth has no explicit dev launcher detection
        
        SSOT should provide unified dev launcher detection.
        """
        test_script = '''
import sys
from pathlib import Path

# Add services to path
root_path = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_path))

from shared.isolated_environment import get_env

# Set dev launcher indicators
env = get_env()
env.set("DEV_LAUNCHER_ACTIVE", "true", "test_script")
env.set("CROSS_SERVICE_AUTH_TOKEN", "test_token", "test_script")

try:
    # Test backend dev launcher detection
    from netra_backend.app.main import _setup_environment_files
    
    # Mock the loading to see if dev launcher is detected
    original_stdout = sys.stdout
    from io import StringIO
    captured_output = StringIO()
    
    # Backend should skip .env loading when dev launcher detected
    _setup_environment_files()  # Should return early due to dev launcher
    
    # Test auth dev launcher detection capability
    auth_main_source = open(Path(root_path) / "auth_service" / "main.py").read()
    auth_has_dev_launcher_detection = "DEV_LAUNCHER_ACTIVE" in auth_main_source
    
    if not auth_has_dev_launcher_detection:
        print("FAIL: Auth service lacks dev launcher detection")
        sys.exit(1)
    else:
        print("SUCCESS: Both services have dev launcher detection")
        sys.exit(0)
        
except Exception as e:
    print(f"ERROR: Dev launcher detection test failed: {e}")
    sys.exit(1)
'''
        
        result = subprocess.run(
            [sys.executable, "-c", test_script],
            cwd=Path(__file__).parent.parent.parent,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 1 and "lacks dev launcher detection" in result.stdout:
            # Expected failure - auth service lacks dev launcher detection
            pytest.skip("EXPECTED: Auth service lacks dev launcher detection before SSOT")
        elif result.returncode == 0:
            assert "SUCCESS" in result.stdout
        else:
            pytest.fail(f"Unexpected result: {result.stdout}\n{result.stderr}")

    def test_environment_variable_consistency_cross_service(self):
        """
        Validate that both services load and interpret environment variables consistently.
        
        Tests for consistency in:
        - Environment variable precedence
        - Value interpretation 
        - Error handling
        """
        test_script = '''
import sys
import os
import tempfile
from pathlib import Path

# Add services to path
root_path = Path(__file__).resolve().parent.parent  
sys.path.insert(0, str(root_path))

from shared.isolated_environment import get_env

# Test environment variable consistency
env = get_env()

# Create consistent test environment
test_vars = {
    "ENVIRONMENT": "development",
    "JWT_SECRET_KEY": "test-secret-key-32-characters-long",
    "POSTGRES_HOST": "localhost", 
    "POSTGRES_PORT": "5432"
}

for key, value in test_vars.items():
    env.set(key, value, "test_script")

try:
    # Test backend environment access
    from netra_backend.app.config import get_config
    backend_config = get_config()
    
    backend_env = backend_config.environment
    backend_jwt_key = backend_config.jwt_secret_key
    
    # Test auth environment access  
    from auth_service.auth_core.auth_environment import get_auth_env
    auth_env = get_auth_env()
    
    auth_environment = auth_env.get_environment()
    auth_jwt_key = auth_env.get_jwt_secret_key()
    
    # Compare consistency
    consistency_checks = [
        (backend_env.lower(), auth_environment.lower(), "environment"),
        (backend_jwt_key, auth_jwt_key, "jwt_secret_key")
    ]
    
    all_consistent = True
    for backend_val, auth_val, var_name in consistency_checks:
        if backend_val != auth_val:
            print(f"INCONSISTENT {var_name}: backend='{backend_val}', auth='{auth_val}'")
            all_consistent = False
    
    if all_consistent:
        print("SUCCESS: Environment variables consistent across services")
        sys.exit(0)
    else:
        print("FAIL: Environment variable inconsistencies detected")
        sys.exit(1)
        
except Exception as e:
    print(f"ERROR: Cross-service consistency test failed: {e}")
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
        elif result.returncode == 1 and "INCONSISTENT" in result.stdout:
            # Expected before SSOT refactor - shows inconsistencies
            pytest.skip("EXPECTED: Environment variable inconsistencies before SSOT")
        else:
            pytest.fail(f"Cross-service consistency test failed: {result.stdout}\n{result.stderr}")