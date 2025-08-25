"""
Auth Service Client for backend service.

This module provides access to the AuthServiceClient from the clients package
to maintain compatibility with existing tests and service expectations.

Business Value Justification (BVJ):
- Segment: ALL (Infrastructure for all tiers)
- Business Goal: Reliable auth service integration
- Value Impact: Enables secure authentication across all services
- Strategic Impact: Foundation for multi-service authentication
"""

from netra_backend.app.clients.auth_client_core import AuthServiceClient

# Export AuthServiceClient for backwards compatibility and expected import paths
__all__ = ["AuthServiceClient"]