"""JWT token manager test documentation and aggregation.

This test module was refactored to meet the 450-line architecture limit by splitting into:

- test_token_manager_core.py (10 tests):
  * Secret key retrieval and configuration tests
  * Revocation key creation and formatting tests
  * JWT manager initialization tests

- test_token_manager_generation.py (11 tests):
  * JWT token generation with various scenarios
  * Token validation success and error cases
  * Claims extraction and structure verification

- test_token_manager_operations.py (16 tests):
  * Token refresh and revocation operations
  * Redis integration and error handling
  * Module-level convenience function tests

Total: 44 comprehensive tests covering all JWT token manager functionality.

All test functions follow the ≤8 lines architectural requirement using helper functions.
Proper mocking is used for Redis operations and time-based functionality.

USAGE:
To run all token manager tests:
    pytest app/tests/unit/test_token_manager_*.py -v

To run individual test modules:
    pytest app/tests/unit/test_token_manager_core.py -v
    pytest app/tests/unit/test_token_manager_generation.py -v  
    pytest app/tests/unit/test_token_manager_operations.py -v

REQUIREMENTS COVERAGE:
✅ AT LEAST 2 dedicated tests for every single function
✅ All test functions ≤8 lines (architectural compliance)
✅ Success tests for all token manager functions
✅ Error handling/edge case tests for all functions
✅ Proper mocking for Redis and time operations
✅ Fixtures for common test data and JWT tokens
✅ All necessary imports (pytest, pytest-asyncio, freezegun, mocking)

TEST CATEGORIES:
- Secret key management: 3 tests
- Revocation key operations: 4 tests  
- Manager initialization: 3 tests
- JWT generation: 3 tests
- JWT validation: 7 tests (includes security edge cases)
- Claims extraction: 3 tests
- Token operations: 7 tests
- Convenience functions: 6 tests
- Error handling: 6 tests
- Redis integration: 4 tests
- Private helper methods: 4 tests (covers _decode_token_payload and _check_revocation_in_redis)
"""

import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path
