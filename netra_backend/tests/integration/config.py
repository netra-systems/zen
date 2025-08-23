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
        TestTier.FREE: {"requests_per_minute": 10, "burst": 5},
        TestTier.PRO: {"requests_per_minute": 100, "burst": 20},
        TestTier.ENTERPRISE: {"requests_per_minute": 1000, "burst": 100},
    }
}