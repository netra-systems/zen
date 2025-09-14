"""
Staging Test Suite - Critical Staging Environment Validation

This module contains the 10 most critical tests for validating the staging environment.
All tests use IsolatedEnvironment for configuration and support both local and staging environments.

CRITICAL REQUIREMENTS:
- Use real services (no mocks)
- Handle staging URLs properly  
- Use IsolatedEnvironment for configuration
- Clear error messages for debugging
- Support individual and suite execution

STAGING URLS:
- Backend: https://netra-backend-staging-701982941522.us-central1.run.app
- Auth: https://netra-auth-service-701982941522.us-central1.run.app
- Frontend: https://netra-frontend-staging-701982941522.us-central1.run.app
"""

__version__ = "1.0.0"
