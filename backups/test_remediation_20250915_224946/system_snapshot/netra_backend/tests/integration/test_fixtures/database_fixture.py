"""
Database test fixture for integration tests
"""

import logging
from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)


class DatabaseTestFixture:
    """Database test fixture that wraps real database connections."""
    
    def __init__(self):
        """Initialize database test fixture."""
        self.env = get_env()
        
    def is_available(self) -> bool:
        """Check if database is available for testing."""
        # Use same pattern as real_services fixture
        use_real_services = self.env.get("USE_REAL_SERVICES", "false").lower() == "true"
        if not use_real_services:
            logger.info("Database fixture not available - USE_REAL_SERVICES not set")
            return False
            
        try:
            # Try to import sqlalchemy to check if database dependencies are available
            from sqlalchemy.ext.asyncio import AsyncSession
            return True
        except ImportError:
            logger.warning("Database dependencies not available")
            return False