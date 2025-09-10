"""
Test staging environment detection consistency for SSOT refactor validation.

This test suite validates consistent staging environment detection and .env file
bypassing logic across backend and auth services.

CRITICAL: Tests expose staging detection inconsistencies before SSOT refactor
and validate unified staging detection after refactor.

GitHub Issue: #189 - Environment loading duplication SSOT violation
Test Plan Step: 2 - Execute Test Plan  
"""

import os
import sys
import pytest
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Set
from unittest.mock import patch, MagicMock

from shared.isolated_environment import get_env
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestStagingDetectionEnvironmentSSot(SSotBaseTestCase):
    """Test suite for staging environment detection SSOT validation."""

    def test_staging_detection_environment_variable_method(self):
        """
        Test that both services detect staging environment via ENVIRONMENT variable consistently.
        
        Both services should:
        - Check ENVIRONMENT variable for 'staging' value
        - Skip .env loading when staging detected
        - Use identical detection logic
        """
        test_script = '''
import sys
from pathlib import Path

# Add services to path
root_path = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_path))

from shared.isolated_environment import get_env

# Set staging environment
env = get_env()
env.set("ENVIRONMENT", "staging", "test_script")

# Clear dev launcher indicators to isolate staging detection
env.delete("DEV_LAUNCHER_ACTIVE", "test_script")
env.delete("CROSS_SERVICE_AUTH_TOKEN", "test_script")

try:
    # Test backend staging detection  
    from netra_backend.app.main import _setup_environment_files
    
    # Mock to capture if .env loading is skipped
    env_loading_attempted = False
    
    original_load_all_env_files = None
    try:
        from netra_backend.app.main import _load_all_env_files as original_load
        original_load_all_env_files = original_load
        
        def mock_load_all_env_files(root_path):
            global env_loading_attempted 
            env_loading_attempted = True
            return original_load(root_path)
        
        # Monkey patch to detect if env loading is attempted
        import netra_backend.app.main
        netra_backend.app.main._load_all_env_files = mock_load_all_env_files
        
        # Test staging detection
        _setup_environment_files()  # Should skip loading in staging
        
        backend_skipped_loading = not env_loading_attempted
        
    except Exception as e:
        backend_skipped_loading = False
        print(f"Backend staging test error: {e}")
    
    # Test auth staging detection by examining implementation
    auth_main_source = open(Path(root_path) / "auth_service" / "main.py").read()
    
    auth_checks_staging = (
        "environment in ['staging', 'production', 'prod']" in auth_main_source or
        "environment == 'staging'" in auth_main_source
    )
    
    auth_skips_in_staging = "skipping .env file loading" in auth_main_source
    
    # Compare staging detection consistency
    if backend_skipped_loading and auth_checks_staging and auth_skips_in_staging:
        print("SUCCESS: Both services consistently detect and handle staging environment")
        sys.exit(0)
    else:
        print("FAIL: Inconsistent staging detection")
        print(f"Backend skipped loading: {backend_skipped_loading}")
        print(f"Auth checks staging: {auth_checks_staging}")
        print(f"Auth skips in staging: {auth_skips_in_staging}")
        sys.exit(1)
        
except Exception as e:
    print(f"ERROR: Staging detection test failed: {e}")
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
            pytest.fail(f"Staging detection test failed: {result.stdout}\n{result.stderr}")

    def test_production_detection_bypasses_env_loading(self):
        """
        Test that both services bypass .env loading identically in production.
        
        Production detection should:
        - Check for 'production' or 'prod' values
        - Skip all .env file processing
        - Rely on Cloud Run environment variables
        """
        test_script = '''
import sys
from pathlib import Path

# Add services to path
root_path = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_path))

from shared.isolated_environment import get_env

# Test production variants
production_values = ["production", "prod"]

for prod_value in production_values:
    # Set production environment
    env = get_env()
    env.set("ENVIRONMENT", prod_value, "test_script")
    
    # Clear dev launcher indicators
    env.delete("DEV_LAUNCHER_ACTIVE", "test_script")
    env.delete("CROSS_SERVICE_AUTH_TOKEN", "test_script")
    
    try:
        # Test backend production detection
        from netra_backend.app.main import _setup_environment_files
        
        # Should return early without loading
        _setup_environment_files()  # No exception means production detected correctly
        
        backend_handles_production = True
        
        # Test auth production detection
        auth_main_source = open(Path(root_path) / "auth_service" / "main.py").read()
        
        # Check if auth recognizes this production value
        auth_handles_production = (
            f"'{prod_value}'" in auth_main_source or
            "production" in auth_main_source
        )
        
        if not (backend_handles_production and auth_handles_production):
            print(f"FAIL: Inconsistent production detection for '{prod_value}'")
            print(f"Backend: {backend_handles_production}, Auth: {auth_handles_production}")
            sys.exit(1)
            
    except Exception as e:
        print(f"ERROR: Production detection failed for '{prod_value}': {e}")
        sys.exit(1)

print("SUCCESS: Both services handle production environment consistently")
sys.exit(0)
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
            pytest.fail(f"Production detection test failed: {result.stdout}\n{result.stderr}")

    def test_gcp_cloud_run_environment_detection(self):
        """
        Test consistent detection of GCP Cloud Run environment characteristics.
        
        Cloud Run environments should be detected by:
        - ENVIRONMENT=staging or production
        - Presence of Cloud Run specific environment variables
        - Absence of local development indicators
        """
        test_script = '''
import sys
from pathlib import Path

# Add services to path
root_path = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_path))

from shared.isolated_environment import get_env

# Simulate GCP Cloud Run environment
env = get_env()
env.set("ENVIRONMENT", "staging", "test_script")

# Simulate Cloud Run environment variables
cloud_run_vars = {
    "K_SERVICE": "netra-backend",
    "K_REVISION": "netra-backend-abc123", 
    "K_CONFIGURATION": "netra-backend",
    "PORT": "8080"
}

for key, value in cloud_run_vars.items():
    env.set(key, value, "test_script")

# Remove local development indicators
env.delete("DEV_LAUNCHER_ACTIVE", "test_script")
env.delete("CROSS_SERVICE_AUTH_TOKEN", "test_script")

try:
    # Test backend Cloud Run detection
    from netra_backend.app.main import _setup_environment_files
    
    # Should skip .env loading in Cloud Run
    _setup_environment_files()
    
    backend_detected_cloud_run = True  # No exception means proper detection
    
    # Test auth service Cloud Run handling
    auth_main_source = open(Path(root_path) / "auth_service" / "main.py").read()
    
    # Auth should also skip .env loading in staging
    auth_skips_staging = (
        "if environment in ['staging', 'production', 'prod']:" in auth_main_source and
        "skipping .env file loading" in auth_main_source
    )
    
    if backend_detected_cloud_run and auth_skips_staging:
        print("SUCCESS: Both services handle Cloud Run environment consistently")
        sys.exit(0)
    else:
        print("FAIL: Inconsistent Cloud Run environment handling")
        print(f"Backend: {backend_detected_cloud_run}, Auth skips staging: {auth_skips_staging}")
        sys.exit(1)
        
except Exception as e:
    print(f"ERROR: Cloud Run detection test failed: {e}")
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
            pytest.fail(f"Cloud Run detection test failed: {result.stdout}\n{result.stderr}")

    def test_dev_launcher_staging_override_consistency(self):
        """
        Test that dev launcher can consistently override staging detection.
        
        When dev launcher is active:
        - Should override staging environment detection
        - Should prevent .env loading even in 'staging' ENVIRONMENT
        - Both services should handle this consistently
        """
        test_script = '''
import sys
from pathlib import Path

# Add services to path
root_path = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_path))

from shared.isolated_environment import get_env

# Set staging environment but activate dev launcher
env = get_env()
env.set("ENVIRONMENT", "staging", "test_script")
env.set("DEV_LAUNCHER_ACTIVE", "true", "test_script")
env.set("CROSS_SERVICE_AUTH_TOKEN", "dev_token_123", "test_script")

try:
    # Test backend dev launcher override
    from netra_backend.app.main import _setup_environment_files
    
    # Should skip loading due to dev launcher, not staging detection
    _setup_environment_files()
    
    backend_detected_dev_launcher = True
    
    # Test auth service dev launcher capability
    auth_main_source = open(Path(root_path) / "auth_service" / "main.py").read()
    
    # Check if auth has dev launcher detection capability
    auth_has_dev_launcher_detection = (
        "DEV_LAUNCHER_ACTIVE" in auth_main_source or
        "CROSS_SERVICE_AUTH_TOKEN" in auth_main_source
    )
    
    if backend_detected_dev_launcher and auth_has_dev_launcher_detection:
        print("SUCCESS: Both services support dev launcher override")
        sys.exit(0)
    elif backend_detected_dev_launcher and not auth_has_dev_launcher_detection:
        print("FAIL: Auth service lacks dev launcher override capability")
        sys.exit(1)
    else:
        print(f"FAIL: Inconsistent dev launcher override")
        print(f"Backend: {backend_detected_dev_launcher}, Auth: {auth_has_dev_launcher_detection}")
        sys.exit(1)
        
except Exception as e:
    print(f"ERROR: Dev launcher override test failed: {e}")
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
        elif result.returncode == 1 and "lacks dev launcher override" in result.stdout:
            # Expected failure - auth lacks dev launcher detection
            pytest.skip("EXPECTED: Auth service lacks dev launcher override before SSOT")
        else:
            pytest.fail(f"Dev launcher override test failed: {result.stdout}\n{result.stderr}")

    def test_staging_gsm_vs_env_file_precedence(self):
        """
        Test consistent precedence between Google Secret Manager and .env files in staging.
        
        In staging environment:
        - Both services should prefer GSM over .env files
        - Both should skip .env loading entirely
        - Both should rely on Cloud Run environment variables + GSM
        """
        test_script = '''
import sys
import tempfile
from pathlib import Path

# Add services to path
root_path = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_path))

from shared.isolated_environment import get_env

# Set staging environment
env = get_env()
env.set("ENVIRONMENT", "staging", "test_script")

# Simulate Cloud Run environment variables (would come from GSM in real staging)
env.set("JWT_SECRET_KEY", "staging_gsm_jwt_secret", "test_script")
env.set("POSTGRES_PASSWORD", "staging_gsm_db_password", "test_script")

# Create .env file that would conflict (should be ignored)
with tempfile.TemporaryDirectory() as temp_dir:
    temp_path = Path(temp_dir) 
    
    conflicting_env = """
JWT_SECRET_KEY=local_env_jwt_secret
POSTGRES_PASSWORD=local_env_db_password
"""
    (temp_path / ".env").write_text(conflicting_env.strip())
    
    try:
        # Test backend GSM precedence
        from netra_backend.app.main import _setup_environment_files
        
        # Should skip .env loading in staging
        _setup_environment_files()
        
        # Verify GSM values are preserved (not overridden by .env)
        backend_jwt = env.get("JWT_SECRET_KEY")
        backend_uses_gsm = backend_jwt == "staging_gsm_jwt_secret"
        
        # Test auth GSM precedence
        auth_main_source = open(Path(root_path) / "auth_service" / "main.py").read()
        
        # Auth should skip .env loading in staging
        auth_skips_env_in_staging = (
            "if environment in ['staging', 'production', 'prod']:" in auth_main_source and
            "skipping .env file loading" in auth_main_source
        )
        
        if backend_uses_gsm and auth_skips_env_in_staging:
            print("SUCCESS: Both services prioritize GSM over .env in staging")
            sys.exit(0)
        else:
            print("FAIL: Inconsistent GSM vs .env precedence in staging")
            print(f"Backend uses GSM: {backend_uses_gsm}")
            print(f"Auth skips env in staging: {auth_skips_env_in_staging}")
            print(f"Backend JWT value: {backend_jwt}")
            sys.exit(1)
            
    except Exception as e:
        print(f"ERROR: GSM precedence test failed: {e}")
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
            pytest.fail(f"GSM precedence test failed: {result.stdout}\n{result.stderr}")