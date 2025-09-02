"""
Test Repository Framework

SSOT repository factory for all test database access.
"""

from .test_repository_factory import TestRepositoryFactory, RepositoryComplianceError

__all__ = ["TestRepositoryFactory", "RepositoryComplianceError"]