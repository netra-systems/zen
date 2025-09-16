"""
Redis test fixture for integration tests
"""

import logging
from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)


class RedisTestFixture:
    """Redis test fixture that wraps real Redis connections."""
    
    def __init__(self):
        """Initialize Redis test fixture."""
        self.env = get_env()
        
    def is_available(self) -> bool:
        """Check if Redis is available for testing."""
        # Use same pattern as real_services fixture
        use_real_services = self.env.get("USE_REAL_SERVICES", "false").lower() == "true"
        if not use_real_services:
            logger.info("Redis fixture not available - USE_REAL_SERVICES not set")
            return False
            
        try:
            # Try to import redis to check if Redis dependencies are available
            import redis.asyncio as redis
            return True
        except ImportError:
            logger.warning("Redis dependencies not available")
            return False