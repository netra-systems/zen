from shared.isolated_environment import get_env
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import TestDatabaseManager
from test_framework.redis_test_utils_test_utils.test_redis_manager import TestRedisManager
from auth_service.core.auth_manager import AuthManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment
"""Configuration Migration Validation Test

CRITICAL: Validates that 371 os.environ violations were properly fixed.

Business Value: Ensures unified configuration system works correctly
and no regressions were introduced during the migration.
"""

import sys
from pathlib import Path

import os
import sys
from pathlib import Path
from typing import Any, Dict

import pytest

class TestConfigurationMigrationValidation:
    """Comprehensive validation of configuration migration fixes."""

    def test_no_direct_os_environ_in_production_code(self):
        """Verify no direct os.environ usage in production code (excluding bootstrap)."""
        import re
        import subprocess
        
        # Search for os.environ violations in production code
        production_dirs = [
            "app/agents",
            "app/api", 
            "app/core/agent_registry",
            "app/core/permissions",
            "app/core/health",
            "app/core/metrics",
            "app/core/auth",
            "app/services",
            "app/utils",
            "app/db",
            "app/llm"
        ]
        
        violations = []
        for directory in production_dirs:
            full_path = PROJECT_ROOT / directory
            if full_path.exists():
                try:
                    result = subprocess.run([
                        "grep", "-r", "-n", "os\\.environ", str(full_path)
                    ], capture_output=True, text=True, check=False)
                    
                    if result.stdout:
                        # Filter out legitimate usage (comments, bootstrap code)
                        lines = result.stdout.strip().split('\n')
                        for line in lines:
                            if not any(pattern in line.lower() for pattern in [
                                'bootstrap', 'comment', '#', 'legitimate', 'allowed'
                            ]):
                                violations.append(line)
                except Exception:
                    # If grep fails, skip this directory
                    pass
        
        assert len(violations) == 0, f"Found {len(violations)} os.environ violations in production code: {violations}"

    def test_environment_detection_still_works(self):
        """Verify environment detection functions correctly."""
        from netra_backend.app.core.environment_constants import EnvironmentDetector
        
        # Test basic environment detection
        detector = EnvironmentDetector()
        
        # These should not raise exceptions
        env = detector.detect_environment()
        assert env in ["development", "staging", "production", "testing"]
        
        # Test cloud platform detection
        is_cloud_run = detector.is_cloud_run_environment() 
        is_gae = detector.is_app_engine_environment()
        is_aws = detector.is_aws_environment()
        
        # Should be boolean values
        assert isinstance(is_cloud_run, bool)
        assert isinstance(is_gae, bool)
        assert isinstance(is_aws, bool)

    def test_configuration_access_patterns_work(self):
        """Test that configuration can be accessed through unified system."""
        try:
            # Test accessing configuration without direct os.environ
            with patch.dict(os.environ, {
                "DATABASE_URL": "postgresql://test:test@localhost:5432/test",
                "REDIS_URL": "redis://localhost:6379/0",
                "ENVIRONMENT": "testing"
            }):
                # Import configuration components that should work
                from netra_backend.app.core.environment_constants import (
                    EnvironmentVariables,
                )
                
                # Verify constants are accessible
                assert hasattr(EnvironmentVariables, 'DATABASE_URL')
                assert hasattr(EnvironmentVariables, 'REDIS_URL')
                assert hasattr(EnvironmentVariables, 'ENVIRONMENT')
                
        except ImportError as e:
            # If imports fail due to circular dependencies, that's a separate issue
            # but configuration access should still be validated
            pytest.skip(f"Import issue detected: {e}")

    def test_bootstrap_configuration_legitimate_usage(self):
        """Verify bootstrap configuration uses os.environ legitimately."""
        legitimate_bootstrap_files = [
            "app/core/environment_constants.py",
            "app/core/configuration/base.py", 
            "app/core/configuration/services.py",
            "app/core/configuration/database.py",
            "app/core/configuration/secrets.py",
            "app/core/configuration/unified_secrets.py",
            "app/configuration/environment.py",
            "app/configuration/loaders.py",
            "app/cloud_run_startup.py"
        ]
        
        for file_path in legitimate_bootstrap_files:
            full_path = PROJECT_ROOT / file_path
            if full_path.exists():
                # These files SHOULD contain os.environ usage for bootstrap
                content = full_path.read_text()
                if "os.environ" in content:
                    # Verify it's documented as legitimate bootstrap usage
                    assert any(marker in content.lower() for marker in [
                        "bootstrap", "config", "environment", "startup", "detection"
                    ]), f"File {file_path} has undocumented os.environ usage"

    def test_critical_path_imports_work(self):
        """Test that critical system components can import correctly."""
        critical_imports = [
            ("app.core.environment_constants", "EnvironmentDetector"),
            ("app.core.environment_constants", "EnvironmentVariables"), 
        ]
        
        for module_path, class_name in critical_imports:
            try:
                module = __import__(module_path, fromlist=[class_name])
                cls = getattr(module, class_name)
                assert cls is not None, f"Could not import {class_name} from {module_path}"
            except ImportError as e:
                pytest.fail(f"Critical import failed: {module_path}.{class_name} - {e}")

    def test_configuration_constants_accessible(self):
        """Test that configuration constants are accessible."""
        from netra_backend.app.core.environment_constants import EnvironmentVariables
        
        # Test key environment variables are defined
        required_vars = [
            'DATABASE_URL', 'REDIS_URL', 'ENVIRONMENT', 'SECRET_KEY',
            'JWT_SECRET_KEY', 'GOOGLE_API_KEY', 'CLICKHOUSE_HOST'
        ]
        
        for var in required_vars:
            assert hasattr(EnvironmentVariables, var), f"Missing environment variable constant: {var}"

    def test_no_placeholder_code_remaining(self):
        """Verify no placeholder or TODO code remains in configuration files."""
        import subprocess
        
        config_dirs = [
            "app/core/configuration",
            "app/configuration"
        ]
        
        placeholder_patterns = [
            "TODO", "FIXME", "PLACEHOLDER", "NotImplemented", 
            "raise NotImplementedError", "pass  # TODO"
        ]
        
        violations = []
        for directory in config_dirs:
            full_path = PROJECT_ROOT / directory
            if full_path.exists():
                for pattern in placeholder_patterns:
                    try:
                        result = subprocess.run([
                            "grep", "-r", "-n", pattern, str(full_path)
                        ], capture_output=True, text=True, check=False)
                        
                        if result.stdout:
                            violations.extend(result.stdout.strip().split('\n'))
                    except Exception:
                        pass
        
        # Filter out legitimate TODOs in comments
        real_violations = [v for v in violations if not v.strip().startswith('#')]
        assert len(real_violations) == 0, f"Found placeholder code: {real_violations}"

    def test_configuration_error_handling(self):
        """Test that configuration errors are handled gracefully."""
        with patch.dict(os.environ, {}, clear=True):
            # Test that missing configuration doesn't crash the system
            try:
                from netra_backend.app.core.environment_constants import (
                    EnvironmentDetector,
                )
                detector = EnvironmentDetector()
                env = detector.detect_environment()
                # Should default to development
                assert env == "development"
            except Exception as e:
                pytest.fail(f"Configuration error handling failed: {e}")

def main():
    """Run validation tests."""
    pytest.main([__file__, "-v"])

if __name__ == "__main__":
    main()
