"""
CRITICAL GOLDEN PATH COMPATIBILITY MODULE

IMPORT COMPATIBILITY: models_auth.py
Status: COMPATIBILITY LAYER - Re-exports User model from models_user.py
Purpose: Enables Golden Path tests to import User model successfully
Business Impact: Fixes critical Golden Path test collection blocking $500K+ ARR validation

SSOT COMPLIANCE:
- The actual User model is defined in models_user.py (SSOT location)
- This module provides backward compatibility for existing imports
- Service boundaries maintained: netra_backend owns User database model
- Auth service handles authentication logic, not data models

CREATED: 2025-09-10 to resolve Golden Path import blocker #2
GOLDEN PATH DEPENDENCY: Required for test collection and execution
"""

# Re-export User model from the SSOT location
from netra_backend.app.db.models_user import User, Secret, ToolUsageLog

# Maintain compatibility for any existing imports
__all__ = ["User", "Secret", "ToolUsageLog"]