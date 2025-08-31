#!/usr/bin/env python
"""Wrapper to run staging tests with environment variables set."""

import os
import sys
import subprocess

# Set environment variables
os.environ['E2E_BYPASS_KEY'] = '25006a4abd79f48e8e7a62c2b1b87245a449348ac0a01ac69a18521c7e140444'
os.environ['ENVIRONMENT'] = 'staging'

# Run the staging tests
result = subprocess.run([sys.executable, 'tests/run_staging_tests.py', '--quick'], capture_output=False)
sys.exit(result.returncode)