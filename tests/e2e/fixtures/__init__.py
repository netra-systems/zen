"""
E2E Test Fixtures Package

Shared fixtures and test data generators for end-to-end testing.
"""

from tests.e2e.high_volume_data import HighVolumeDataGenerator, MockAuthenticator
    HighVolumeDataGenerator,
    MockAuthenticator
)

__all__ = [
    'HighVolumeDataGenerator',
    'MockAuthenticator'
]
