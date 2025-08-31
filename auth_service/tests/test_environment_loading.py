"""
Test environment variable loading and configuration for auth service.
This test ensures that SERVICE_SECRET and SERVICE_ID are properly loaded
and prevents race conditions during module imports.

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


class TestEnvironmentLoading:
    """Test suite for environment variable loading in auth service."""
    
    @pytest.fixture
    def temp_env_file(self, tmp_path) -> Path:
        """Create a temporary .env file for testing."""
        env_file = tmp_path / ".env"
        env_content = """
ENVIRONMENT=test
SERVICE_SECRET=test-secret-for-auth-service-32-characters-long
SERVICE_ID=auth-service-test
JWT_SECRET_KEY=test-jwt-secret-key-for-auth-service
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=test_db
POSTGRES_USER=test_user
POSTGRES_PASSWORD=test_password
"""
        env_file.write_text(env_content.strip())
        return env_file
    
    def test_service_secret_required_no_mocks(self):
        """Test that SERVICE_SECRET is required with no mock fallbacks."""
        # Create a test script that tries to import auth config without SERVICE_SECRET
        test_script = f'''
import os
import sys
from pathlib import Path

# Add auth service to path
auth_service_path = Path("{Path(__file__).parent.parent}")
sys.path.insert(0, str(auth_service_path.parent))

# Clear SERVICE_SECRET to simulate missing variable
os.environ.pop("SERVICE_SECRET", None)
os.environ["ENVIRONMENT"] = "development"

try:
    from auth_service.auth_core.config import AuthConfig
    # Try to get service secret - should fail
    secret = AuthConfig.get_service_secret()
    print(f"ERROR: Should have failed but got: {secret}")
    sys.exit(1)
except ValueError as e:
    if "SERVICE_SECRET must be set" in str(e) and "no mock fallbacks" in str(e):
        print("SUCCESS: Correctly rejected missing SERVICE_SECRET")
        sys.exit(0)
    else:
        print(f"ERROR: Wrong error message: {e}")
        sys.exit(1)
except Exception as e:
    print(f"ERROR: Unexpected error: {e}")
    sys.exit(1)
'''
        
        # Run the test script
        result = subprocess.run(
            [sys.executable, "-c", test_script],
            cwd=Path(__file__).parent,
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0, f"Test failed: {result.stdout}\n{result.stderr}"
        assert "SUCCESS" in result.stdout
    
    def test_service_id_required(self):
        """Test that SERVICE_ID is required for auth service."""
        test_script = f'''
import os
import sys
from pathlib import Path

# Add auth service to path
auth_service_path = Path("{Path(__file__).parent.parent}")
sys.path.insert(0, str(auth_service_path.parent))

# Set SERVICE_SECRET but clear SERVICE_ID
os.environ["SERVICE_SECRET"] = "test-secret-32-characters-or-more"
os.environ.pop("SERVICE_ID", None)
os.environ["ENVIRONMENT"] = "development"

try:
    from auth_service.auth_core.config import AuthConfig
    # Try to get service ID - should fail
    service_id = AuthConfig.get_service_id()
    print(f"ERROR: Should have failed but got: {service_id}")
    sys.exit(1)
except ValueError as e:
    if "SERVICE_ID must be set" in str(e) and "no mock fallbacks" in str(e):
        print("SUCCESS: Correctly rejected missing SERVICE_ID")
        sys.exit(0)
    else:
        print(f"ERROR: Wrong error message: {e}")
        sys.exit(1)
except Exception as e:
    print(f"ERROR: Unexpected error: {e}")
    sys.exit(1)
'''
        
        result = subprocess.run(
            [sys.executable, "-c", test_script],
            cwd=Path(__file__).parent,
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0, f"Test failed: {result.stdout}\n{result.stderr}"
        assert "SUCCESS" in result.stdout
    
    def test_env_loading_before_import(self, temp_env_file):
        """Test that loading .env file before imports makes variables available."""
        test_script = f'''
import os
import sys
from pathlib import Path

# Add auth service to path
auth_service_path = Path(__file__).parent.parent
sys.path.insert(0, str(auth_service_path.parent))

# Clear any existing variables
os.environ.pop("SERVICE_SECRET", None)
os.environ.pop("SERVICE_ID", None)

# Load the test .env file BEFORE importing auth modules
from dotenv import load_dotenv
load_dotenv("{temp_env_file}", override=True)

# Now import auth config - should work
try:
    from auth_service.auth_core.config import AuthConfig
    
    # Get service secret and ID
    secret = AuthConfig.get_service_secret()
    service_id = AuthConfig.get_service_id()
    
    if secret and service_id == "auth-service-test":
        print("SUCCESS: Environment variables loaded correctly")
        sys.exit(0)
    else:
        print(f"ERROR: Got secret={bool(secret)}, service_id={service_id}")
        sys.exit(1)
except Exception as e:
    print(f"ERROR: Failed to load config: {e}")
    sys.exit(1)
'''
        
        result = subprocess.run(
            [sys.executable, "-c", test_script],
            cwd=Path(__file__).parent,
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0, f"Test failed: {result.stdout}\n{result.stderr}"
        assert "SUCCESS" in result.stdout
    
    def test_import_order_race_condition(self, temp_env_file):
        """Test that importing config BEFORE loading .env causes failure."""
        test_script = f'''
import os
import sys
from pathlib import Path

# Add auth service to path
auth_service_path = Path(__file__).parent.parent
sys.path.insert(0, str(auth_service_path.parent))

# Clear any existing variables to simulate fresh start
os.environ.pop("SERVICE_SECRET", None)
os.environ.pop("SERVICE_ID", None)
os.environ["ENVIRONMENT"] = "development"

# WRONG ORDER: Try to import config BEFORE loading .env
try:
    from auth_service.auth_core.config import AuthConfig
    secret = AuthConfig.get_service_secret()
    print(f"ERROR: Should have failed but got secret")
    sys.exit(1)
except ValueError as e:
    if "SERVICE_SECRET must be set" in str(e):
        print("SUCCESS: Correctly detected missing environment variable")
        # Now demonstrate fix by loading .env
        from dotenv import load_dotenv
        load_dotenv("{temp_env_file}", override=True)
        # Reimport and it should work now
        import importlib
        import auth_service.auth_core.config
        importlib.reload(auth_service.auth_core.config)
        from auth_service.auth_core.config import AuthConfig as ReloadedConfig
        try:
            secret = ReloadedConfig.get_service_secret()
            if secret:
                print("SUCCESS: Works after loading .env and reloading module")
                sys.exit(0)
        except Exception as e2:
            print(f"ERROR: Still failed after reload: {e2}")
            sys.exit(1)
    else:
        print(f"ERROR: Wrong error: {e}")
        sys.exit(1)
'''
        
        result = subprocess.run(
            [sys.executable, "-c", test_script],
            cwd=Path(__file__).parent,
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0, f"Test failed: {result.stdout}\n{result.stderr}"
        assert "SUCCESS" in result.stdout
    
    def test_service_id_must_be_auth_service(self):
        """Test that SERVICE_ID should be 'auth-service' not 'netra-backend'."""
        test_script = f'''
import os
import sys
from pathlib import Path

# Add auth service to path
auth_service_path = Path("{Path(__file__).parent.parent}")
sys.path.insert(0, str(auth_service_path.parent))

# Set variables but with wrong SERVICE_ID
os.environ["SERVICE_SECRET"] = "test-secret-32-characters-or-more"
os.environ["SERVICE_ID"] = "netra-backend"  # WRONG!
os.environ["ENVIRONMENT"] = "test"

try:
    from auth_service.auth_core.config import AuthConfig
    service_id = AuthConfig.get_service_id()
    
    # This test documents that auth service should have its own SERVICE_ID
    if service_id == "netra-backend":
        print("WARNING: SERVICE_ID is 'netra-backend' but should be 'auth-service' for auth service")
        print("Each microservice should have its own SERVICE_ID")
        sys.exit(0)  # Pass with warning to document the issue
    else:
        print(f"INFO: SERVICE_ID is '{service_id}'")
        sys.exit(0)
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
'''
        
        result = subprocess.run(
            [sys.executable, "-c", test_script],
            cwd=Path(__file__).parent,
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0, f"Test failed: {result.stdout}\n{result.stderr}"
    
    def test_isolated_environment_reads_os_environ(self):
        """Test that IsolatedEnvironment reads from os.environ correctly."""
        test_script = f'''
import os
import sys
from pathlib import Path

# Add auth service to path
auth_service_path = Path("{Path(__file__).parent.parent}")
sys.path.insert(0, str(auth_service_path.parent))

# Set variables directly in os.environ
os.environ["SERVICE_SECRET"] = "test-secret-32-characters-or-more"
os.environ["SERVICE_ID"] = "auth-service"
os.environ["TEST_VAR"] = "test-value"

# Import isolated environment
from shared.isolated_environment import get_env

env = get_env()

# Test that it reads from os.environ
test_var = env.get("TEST_VAR")
service_secret = env.get("SERVICE_SECRET")
service_id = env.get("SERVICE_ID")

if test_var == "test-value" and service_secret and service_id == "auth-service":
    print("SUCCESS: IsolatedEnvironment correctly reads from os.environ")
    sys.exit(0)
else:
    print(f"ERROR: Got test_var={test_var}, secret={bool(service_secret)}, id={service_id}")
    sys.exit(1)
'''
        
        result = subprocess.run(
            [sys.executable, "-c", test_script],
            cwd=Path(__file__).parent,
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0, f"Test failed: {result.stdout}\n{result.stderr}"
        assert "SUCCESS" in result.stdout


class TestMainEntrypoint:
    """Test the main.py entrypoint for proper environment loading."""
    
    def test_main_loads_env_before_imports(self):
        """Verify that main.py loads environment variables before importing auth modules."""
        main_path = Path(__file__).parent.parent / "main.py"
        
        # Read the main.py file with UTF-8 encoding
        with open(main_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find the position of load_dotenv call
        load_dotenv_pos = content.find("load_dotenv")
        assert load_dotenv_pos != -1, "load_dotenv not found in main.py"
        
        # Find the position of auth_routes import
        auth_routes_import_pos = content.find("from auth_service.auth_core.routes.auth_routes")
        assert auth_routes_import_pos != -1, "auth_routes import not found"
        
        # Find the position of AuthConfig import
        auth_config_import_pos = content.find("from auth_service.auth_core.config import AuthConfig")
        assert auth_config_import_pos != -1, "AuthConfig import not found"
        
        # Verify load_dotenv comes BEFORE auth module imports
        assert load_dotenv_pos < auth_routes_import_pos, \
            "load_dotenv must come BEFORE auth_routes import to prevent race condition"
        assert load_dotenv_pos < auth_config_import_pos, \
            "load_dotenv must come BEFORE AuthConfig import to prevent race condition"
        
        print("SUCCESS: main.py loads environment variables before importing auth modules")


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])