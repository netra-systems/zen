"""
Auth Service Test Managers Module
"""
import sys
from pathlib import Path

# Add the project root to Python path for imports
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    # Import the JWT test manager from the main test framework
    from test_framework.auth_jwt_test_manager import JWTGenerationTestManager
    __all__ = ['JWTGenerationTestManager']
except ImportError as e:
    # Fallback - try to import from current auth_service location
    raise ImportError(f"Could not import JWTGenerationTestManager: {e}")
