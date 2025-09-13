#!/usr/bin/env python3
"""
Test script to force a violation and ensure detection is working.
"""

import os
import sys
from unittest.mock import patch

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

def test_forced_violation():
    """Test by directly creating a violation to verify detection works."""

    detected_violations = []

    def mock_setitem(key, value):
        """Mock os.environ.__setitem__ to detect direct assignments."""
        import traceback
        stack = traceback.extract_stack()
        caller_info = "forced_violation_test"
        for frame in reversed(stack[:-1]):
            if 'mock' not in frame.filename:
                caller_info = f"{frame.filename}:{frame.lineno} in {frame.name}"
                break

        violation = {
            'key': key,
            'value': value,
            'stack_trace': caller_info
        }
        detected_violations.append(violation)
        print(f"VIOLATION DETECTED: {caller_info} - os.environ['{key}'] = '{value}'")

        # Actually set the value
        dict.__setitem__(os.environ, key, value)

    # Test with forced violation
    with patch.object(os.environ, '__setitem__', side_effect=mock_setitem):
        print("Testing direct violation...")

        # This should trigger the violation detector
        os.environ['FORCED_VIOLATION'] = 'test_value'

        print(f"Direct violations detected: {len(detected_violations)}")

        # Now test the secret manager
        try:
            from netra_backend.app.core.secret_manager_core import EnhancedSecretManager
            from netra_backend.app.schemas.config_types import EnvironmentType

            print("Testing EnhancedSecretManager...")
            secret_manager = EnhancedSecretManager(EnvironmentType.TESTING)
            secret_manager.set_secret("SECRET_MANAGER_TEST", "test_value")

            print(f"Total violations detected: {len(detected_violations)}")
            for i, violation in enumerate(detected_violations):
                print(f"  {i+1}. {violation['stack_trace']} - os.environ['{violation['key']}'] = '{violation['value']}'")

        except Exception as e:
            print(f"Error during secret manager test: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    test_forced_violation()