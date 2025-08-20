"""
E2E Test Fixtures Package

Shared fixtures and test data generators for end-to-end testing.
"""

from .high_volume_data import (
    HighVolumeDataGenerator,
    MockAuthenticator
)

__all__ = [
    'HighVolumeDataGenerator',
    'MockAuthenticator'
]