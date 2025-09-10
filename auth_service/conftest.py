"""
Auth service root conftest.py - Path configuration fix for Issue #178

CRITICAL FIX: Add project root to Python path to enable test_framework imports
when pytest runs from auth_service subdirectory.

Root Cause: pytest running from /auth_service can't import from parent /test_framework
Solution: Add parent directory to sys.path before any imports

Business Value Justification (BVJ):
- Segment: Platform/Internal Infrastructure
- Business Goal: System Stability and Test Infrastructure  
- Value Impact: Enables real service testing for auth service
- Strategic Impact: Prevents auth service test failures that could block critical features
"""

import os
import sys
from pathlib import Path

# CRITICAL FIX for Issue #178: Add project root to Python path
# This enables imports like 'from test_framework.conftest_real_services import ...'
# when pytest runs from the auth_service subdirectory
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Now all other imports should work normally
# Import the actual conftest configuration from tests/conftest.py
from auth_service.tests.conftest import *