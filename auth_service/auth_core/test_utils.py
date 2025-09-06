"""
Test utilities for auth_core
"""
import sys
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from test_framework.auth_jwt_test_manager import JWTGenerationTestManager

__all__ = ["JWTGenerationTestManager"]
