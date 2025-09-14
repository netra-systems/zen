#!/usr/bin/env python3
"""
Test script to verify unit test import fixes are working
"""
import os
import subprocess
import sys

# Test the two specific files we fixed
test_files = [
    'netra_backend/tests/unit/websocket/test_connection_id_generation.py',
    'netra_backend/tests/unit/deprecated/test_websocket_manager_factory.py'
]

success_count = 0
for file in test_files:
    try:
        result = subprocess.run([
            sys.executable, '-m', 'pytest', file, '--collect-only', '--quiet'
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print(f'✅ {file}: COLLECTION SUCCESS')
            success_count += 1
        else:
            print(f'❌ {file}: COLLECTION FAILED')
            print(f'   Error: {result.stderr.strip()}')
    except Exception as e:
        print(f'❌ {file}: EXCEPTION - {e}')

print(f'\nSUMMARY: {success_count}/{len(test_files)} files can be collected successfully')