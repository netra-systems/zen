"""Auth Controller - Compatibility Layer

This module provides backward compatibility for auth controller imports.
Auth logic is implemented in the routes/auth_routes module following FastAPI patterns.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Maintain test compatibility while following SSOT principles
- Value Impact: Ensures existing tests continue to work without breaking changes
- Strategic Impact: Maintains system stability during module consolidation
"""

from netra_backend.app.routes.auth_routes import (
    health,
    login_flow,
    token_management,
    callback_processor,
    debug_helpers,
    oauth_validation,
    utils
)

# Import auth route functionality
from netra_backend.app.routes.auth.auth import router as auth_router

# Create compatibility aliases
AuthController = type('AuthController', (), {
    'health': health,
    'login_flow': login_flow,
    'token_management': token_management,
    'callback_processor': callback_processor,
    'debug_helpers': debug_helpers,
    'oauth_validation': oauth_validation,
    'utils': utils,
    'router': auth_router
})

# Re-export all functionality for backward compatibility
__all__ = [
    'AuthController',
    'health',
    'login_flow', 
    'token_management',
    'callback_processor',
    'debug_helpers',
    'oauth_validation',
    'utils',
    'auth_router'
]