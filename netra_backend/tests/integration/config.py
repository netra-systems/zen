"""Integration test configuration."""

from enum import Enum

class ServiceTier(str, Enum):
    """Test tiers for rate limiting and billing tests."""
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"

# Test configuration settings
TEST_CONFIG = {
    "mock": True,
    "test_environment": "integration",
    "rate_limits": {
        ServiceTier.FREE: {"requests_per_minute": 10, "burst": 5},
        ServiceTier.PRO: {"requests_per_minute": 100, "burst": 20},
        ServiceTier.ENTERPRISE: {"requests_per_minute": 1000, "burst": 100},
    },
}