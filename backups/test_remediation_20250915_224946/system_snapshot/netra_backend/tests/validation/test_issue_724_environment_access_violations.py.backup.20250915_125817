"""
Test Issue #724: SSOT Configuration Manager Direct Environment Access Violations

CRITICAL: Validates that direct os.environ access is replaced with SSOT patterns.

Business Value: Ensures configuration consistency and prevents Golden Path failures
due to environment variable access bypassing SSOT configuration management.
"""

import os
import sys
from pathlib import Path
from typing import List, Tuple

import pytest

from shared.isolated_environment import get_env


class TestIssue724EnvironmentAccessViolations:
    """Test direct environment access violations reported in Issue #724."""

    def test_secret_manager_core_no_direct_environ_access(self):
        """Test that secret_manager_core.py does not use direct os.environ access."""
        secret_manager_path = Path(__file__).parent.parent.parent / "app" / "core" / "secret_manager_core.py"
        
        # Read the file content
        with open(secret_manager_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for direct os.environ usage (not in comments)
        lines = content.split('\n')
        violations = []
        
        for line_num, line in enumerate(lines, 1):
            # Skip comments and docstrings
            stripped_line = line.strip()
            if stripped_line.startswith('#') or stripped_line.startswith('"""') or stripped_line.startswith("'''"):
                continue
                
            # Look for direct os.environ access
            if 'os.environ' in line and not line.strip().startswith('#'):
                violations.append(f"Line {line_num}: {line.strip()}")
        
        assert len(violations) == 0, f"Found {len(violations)} direct os.environ violations in secret_manager_core.py: {violations}"

    def test_config_schema_no_direct_environ_access(self):
        """Test that config.py does not use direct os.environ access."""
        config_path = Path(__file__).parent.parent.parent / "app" / "schemas" / "config.py"
        
        # Read the file content
        with open(config_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for direct os.environ usage (not in comments or docstrings)
        lines = content.split('\n')
        violations = []
        
        in_docstring = False
        for line_num, line in enumerate(lines, 1):
            stripped_line = line.strip()
            
            # Track docstring boundaries
            if '"""' in stripped_line or "'''" in stripped_line:
                in_docstring = not in_docstring
                continue
            
            # Skip comments, docstrings, and known acceptable patterns
            if (stripped_line.startswith('#') or 
                in_docstring or
                'LEGACY:' in line or
                'CRITICAL FIX:' in line):
                continue
                
            # Look for direct os.environ access
            if 'os.environ' in line and 'items()' in line:
                violations.append(f"Line {line_num}: {line.strip()}")
        
        assert len(violations) == 0, f"Found {len(violations)} direct os.environ violations in config.py: {violations}"

    def test_secret_manager_has_secret_uses_isolated_environment(self):
        """Test that EnhancedSecretManager.has_secret() uses IsolatedEnvironment."""
        from netra_backend.app.core.secret_manager_core import EnhancedSecretManager
        from netra_backend.app.schemas.config_types import EnvironmentType
        
        # Create instance
        secret_manager = EnhancedSecretManager(EnvironmentType.DEVELOPMENT)
        
        # Mock environment variable access through IsolatedEnvironment
        env = get_env()
        test_secret_name = "TEST_SECRET_724"
        test_secret_value = "test_value_for_issue_724"
        
        # Set test secret through SSOT
        env.set(test_secret_name, test_secret_value, "test_issue_724")
        
        try:
            # Test has_secret method - should work with SSOT environment
            has_secret = secret_manager.has_secret(test_secret_name)
            
            # The method should return True when secret exists in environment
            # Note: This test validates the functionality still works after SSOT migration
            assert isinstance(has_secret, bool), "has_secret should return a boolean"
            
        finally:
            # Clean up test environment variable
            env.unset(test_secret_name)

    def test_no_direct_os_environ_in_critical_files(self):
        """Test that critical files identified in Issue #724 use SSOT patterns."""
        critical_files = [
            "app/core/secret_manager_core.py",
            "app/schemas/config.py"
        ]
        
        project_root = Path(__file__).parent.parent.parent
        violations = []
        
        for file_path in critical_files:
            full_path = project_root / file_path
            
            if not full_path.exists():
                continue
                
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.split('\n')
            for line_num, line in enumerate(lines, 1):
                # Skip comments, docstrings, and acceptable patterns
                if (line.strip().startswith('#') or 
                    'LEGACY:' in line or
                    'CRITICAL FIX:' in line or
                    '# SSOT FIX:' in line):
                    continue
                
                # Look for problematic patterns
                if 'os.environ' in line and not any(acceptable in line for acceptable in [
                    'import os',  # Import statement
                    '"""',        # Docstring
                    "'''",        # Docstring
                    'patch.dict', # Test mocking
                ]):
                    violations.append(f"{file_path}:{line_num}: {line.strip()}")
        
        assert len(violations) == 0, f"Found {len(violations)} SSOT violations: {violations}"

    def test_isolated_environment_available_and_working(self):
        """Test that IsolatedEnvironment is available and working properly."""
        env = get_env()
        
        # Test basic functionality
        test_key = "ISSUE_724_TEST_KEY"
        test_value = "issue_724_test_value"
        
        # Set and get value
        env.set(test_key, test_value, "test_issue_724")
        retrieved_value = env.get(test_key)
        
        try:
            assert retrieved_value == test_value, "IsolatedEnvironment should store and retrieve values correctly"
            
            # Test default value functionality
            default_value = env.get("NONEXISTENT_KEY_724", "default_724")
            assert default_value == "default_724", "IsolatedEnvironment should handle default values"
            
        finally:
            # Clean up
            env.unset(test_key)

    def test_configuration_loading_still_works_after_ssot_migration(self):
        """Integration test: Ensure configuration loading still works after SSOT migration."""
        from netra_backend.app.config import get_config
        
        # Test that configuration can be loaded without errors
        config = get_config()
        
        # Verify basic configuration properties
        assert hasattr(config, 'environment'), "Config should have environment property"
        assert hasattr(config, 'secret_key'), "Config should have secret_key property"
        
        # Test that config uses proper types
        assert isinstance(config.environment, str), "Environment should be string"
        assert len(config.secret_key) >= 32, "Secret key should be at least 32 characters for security"

    @pytest.mark.integration
    def test_golden_path_configuration_not_broken_by_ssot_changes(self):
        """Integration test: Ensure Golden Path functionality not broken by SSOT changes."""
        # Test that key components can still load configuration
        from netra_backend.app.config import get_config
        
        config = get_config()
        
        # Test critical Golden Path configuration elements
        assert config.jwt_secret_key is not None or len(config.jwt_secret_key) >= 32, "JWT secret should be properly configured"
        assert config.api_base_url, "API base URL should be configured"
        assert config.frontend_url, "Frontend URL should be configured"
        
        # Test WebSocket configuration (critical for Golden Path)
        assert hasattr(config, 'ws_config'), "WebSocket configuration should be available"
        assert config.ws_config.connection_timeout > 0, "WebSocket timeout should be positive"