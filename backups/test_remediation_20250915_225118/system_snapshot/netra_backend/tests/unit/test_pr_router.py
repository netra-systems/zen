"""
Comprehensive unit tests for PR router implementation.

This file was refactored to meet the 450-line limit by splitting into:
- test_pr_router_auth.py - route_pr_auth and validation tests (8 tests)
- test_pr_router_state.py - state encoding/decoding tests (12 tests) 
- test_pr_router_security.py - security and validation tests (15 tests)
- test_pr_router_utils.py - utility and helper function tests (19 tests)

All functions are  <= 8 lines using proper test patterns.
Tests ALL 22 functions from pr_router.py with success and error cases.
Each function has AT LEAST 2 dedicated tests as required.

Total test coverage: 54 tests across all 22 functions

To run all PR router tests individually:
pytest app/tests/unit/test_pr_router_auth.py -v    # Auth tests
pytest app/tests/unit/test_pr_router_state.py -v   # State tests  
pytest app/tests/unit/test_pr_router_security.py -v # Security tests
pytest app/tests/unit/test_pr_router_utils.py -v   # Utils tests

To run all PR router tests at once:
pytest app/tests/unit/test_pr_router_*.py -v

Coverage verified: All 22 functions from pr_router.py are tested.
"""

# This file serves as documentation for the test suite structure
# Individual test files should be run separately to avoid fixture scope issues

import sys
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

pass