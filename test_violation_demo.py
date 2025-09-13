#!/usr/bin/env python3
"""
Demo script to understand the SSOT violation detection.
This will deliberately create a violation to understand the pattern.
"""

import os
import sys
from unittest.mock import patch

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

def test_direct_violation():
    """Test a direct os.environ assignment to understand violation detection."""

    detected_violations = []

    def mock_setitem(key, value):
        """Mock os.environ.__setitem__ to detect direct assignments."""
        import traceback
        stack = traceback.extract_stack()
        # Find the first non-mock frame
        for frame in reversed(stack[:-1]):
            if 'mock' not in frame.filename and 'test_violation_demo.py' not in frame.filename:
                caller_info = f"{frame.filename}:{frame.lineno} in {frame.name}"
                break
        else:
            caller_info = "test_violation_demo.py"

        violation = {
            'key': key,
            'value': value,
            'stack_trace': caller_info
        }
        detected_violations.append(violation)
        print(f"VIOLATION DETECTED: {caller_info} - os.environ['{key}'] = '{value}'")

        # Actually set the value
        dict.__setitem__(os.environ, key, value)

    # Test the secret manager with violation detection
    with patch.object(os.environ, '__setitem__', side_effect=mock_setitem):
        try:
            # Import and test the secret manager
            from netra_backend.app.core.secret_manager_core import EnhancedSecretManager
            from netra_backend.app.schemas.config_types import EnvironmentType

            print("Creating EnhancedSecretManager...")
            secret_manager = EnhancedSecretManager(EnvironmentType.TESTING)

            print("Calling set_secret...")
            secret_manager.set_secret("TEST_VIOLATION_KEY", "test_value")

            print(f"Violations detected: {len(detected_violations)}")
            for violation in detected_violations:
                print(f"  - {violation}")

        except Exception as e:
            print(f"Error during test: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    test_direct_violation()