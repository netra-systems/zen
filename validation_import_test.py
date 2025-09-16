#!/usr/bin/env python3
"""
Issue #1176 Remediation - Import Validation Test
Validates that all critical system imports still work after remediation changes.
"""

import sys
import traceback

def test_critical_imports():
    """Test imports of modules modified during Issue #1176 remediation."""
    print('=== IMPORT VALIDATION TEST ===')
    print('Testing critical system imports after Issue #1176 remediation...')

    # Test modified modules
    test_modules = [
        'tests.unified_test_runner',
        'netra_backend.app.config',
        'test_framework.ssot.base_test_case',
        'dev_launcher.isolated_environment'
    ]

    success_count = 0
    failed_modules = []

    for module in test_modules:
        try:
            __import__(module)
            print(f'✅ {module} - Import successful')
            success_count += 1
        except Exception as e:
            print(f'❌ {module} - Import failed: {e}')
            failed_modules.append((module, str(e)))
            traceback.print_exc()

    print(f'\n=== IMPORT SUMMARY ===')
    print(f'Successful imports: {success_count}/{len(test_modules)}')

    if success_count == len(test_modules):
        print('✅ Import validation: PASSED')
        return True
    else:
        print('❌ Import validation: FAILED')
        print(f'Failed modules: {[m[0] for m in failed_modules]}')
        return False

if __name__ == '__main__':
    success = test_critical_imports()
    sys.exit(0 if success else 1)