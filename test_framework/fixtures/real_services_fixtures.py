"""Real Services Fixtures Module - SSOT Integration Testing Infrastructure

This module provides the RealServicesFixtureMixin class that was missing and
causing import errors for 625+ e2e tests. Follows SSOT test framework patterns.

Business Value:
- Segment: Platform/Internal - Test Infrastructure
- Business Goal: Enable e2e and integration test execution
- Value Impact: Unblock 625+ tests for Golden Path validation
- Strategic Impact: Critical for $500K+ ARR protection testing

CRITICAL: This module implements REAL service connections following SSOT patterns.
It integrates with existing real_services.py fixtures while providing the mixin
interface that failing tests expect.
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

try:
    # Import existing SSOT real services infrastructure
    from test_framework.fixtures.real_services import (
        real_postgres_connection,
        real_redis_fixture,
        real_services_fixture,
        with_test_database
    )
    REAL_SERVICES_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Real services fixtures not available: {e}")
    REAL_SERVICES_AVAILABLE = False

from shared.isolated_environment import get_env


class RealServicesFixtureMixin:
    """Mixin providing real services integration for e2e and integration tests.

    This mixin provides the interface that failing e2e tests expect while
    delegating to the existing SSOT real services infrastructure.

    Expected Usage:
        class TestMyFeature(SSotAsyncTestCase, RealServicesFixtureMixin):
            async def asyncSetUp(self):
                await super().asyncSetUp()
                await self.setup_real_services()

            async def test_something(self):
                db = await self.get_real_database_session()
                redis = await self.get_real_redis_client()
                # ... test logic with real services

    CRITICAL: This follows SSOT patterns and integrates with existing
    test framework infrastructure rather than duplicating functionality.
    """

    def _ensure_real_services_attrs(self):
        """Ensure real services attributes are initialized (lazy initialization)."""
        if not hasattr(self, '_real_services_setup'):
            self._real_services_setup = False
        if not hasattr(self, '_real_postgres_info'):
            self._real_postgres_info = None
        if not hasattr(self, '_real_db_session'):
            self._real_db_session = None
        if not hasattr(self, '_real_redis_client'):
            self._real_redis_client = None
        if not hasattr(self, '_real_services_config'):
            self._real_services_config = None

    async def setup_real_services(self):
        """Set up real services for integration testing.

        This method initializes connections to real PostgreSQL, Redis, and
        other services required for integration testing. It delegates to
        the existing SSOT real services infrastructure.

        Raises:
            RuntimeError: If real services cannot be initialized
        """
        self._ensure_real_services_attrs()

        if self._real_services_setup:
            logger.debug("Real services already set up")
            return

        if not REAL_SERVICES_AVAILABLE:
            logger.error("Real services fixtures not available - cannot set up real services")
            raise RuntimeError(
                "Real services infrastructure not available. "
                "Ensure test_framework.fixtures.real_services is properly installed."
            )

        env = get_env()
        use_real_services = env.get("USE_REAL_SERVICES", "false").lower() == "true"

        if not use_real_services:
            logger.warning(
                "USE_REAL_SERVICES not set - real services may not be available. "
                "Set USE_REAL_SERVICES=true for full integration testing."
            )

        try:
            # Set up real PostgreSQL connection using existing SSOT infrastructure
            self._real_postgres_info = await self._setup_real_postgres()

            # Set up real database session using existing SSOT infrastructure
            self._real_db_session = await self._setup_real_database_session()

            # Set up real Redis client using existing SSOT infrastructure
            self._real_redis_client = await self._setup_real_redis()

            # Set up comprehensive real services configuration
            self._real_services_config = await self._setup_real_services_config()

            self._real_services_setup = True
            logger.info("Real services setup completed successfully")

        except Exception as e:
            logger.error(f"Failed to set up real services: {e}")
            await self.cleanup_real_services()
            raise RuntimeError(f"Real services setup failed: {e}")

    async def cleanup_real_services(self):
        """Clean up real services connections and resources.

        This method properly closes all real service connections and
        cleans up resources to prevent leaks during testing.
        """
        self._ensure_real_services_attrs()
        cleanup_errors = []

        # Clean up Redis connection
        if self._real_redis_client:
            try:
                if hasattr(self._real_redis_client, 'aclose'):
                    await self._real_redis_client.aclose()
                elif hasattr(self._real_redis_client, 'close'):
                    await self._real_redis_client.close()
                self._real_redis_client = None
            except Exception as e:
                cleanup_errors.append(f"Redis cleanup failed: {e}")

        # Clean up database session
        if self._real_db_session:
            try:
                if hasattr(self._real_db_session, 'close'):
                    await self._real_db_session.close()
                elif hasattr(self._real_db_session, 'rollback'):
                    await self._real_db_session.rollback()
                self._real_db_session = None
            except Exception as e:
                cleanup_errors.append(f"Database session cleanup failed: {e}")

        # Clean up PostgreSQL connection info
        if self._real_postgres_info and isinstance(self._real_postgres_info, dict):
            engine = self._real_postgres_info.get('engine')
            if engine and hasattr(engine, 'dispose'):
                try:
                    await engine.dispose()
                except Exception as e:
                    cleanup_errors.append(f"Database engine cleanup failed: {e}")

        self._real_postgres_info = None
        self._real_services_config = None
        self._real_services_setup = False

        if cleanup_errors:
            logger.warning(f"Real services cleanup had errors: {cleanup_errors}")
        else:
            logger.debug("Real services cleanup completed successfully")

    async def get_real_database_session(self):
        """Get real database session for integration testing.

        Returns:
            AsyncSession: Real database session or None if not available

        Raises:
            RuntimeError: If real services not set up or database not available
        """
        if not self._real_services_setup:
            await self.setup_real_services()

        if not self._real_db_session:
            raise RuntimeError(
                "Real database session not available. "
                "Ensure PostgreSQL is running and USE_REAL_SERVICES=true is set."
            )

        return self._real_db_session

    async def get_real_redis_client(self):
        """Get real Redis client for integration testing.

        Returns:
            redis.Redis: Real Redis client or None if not available

        Raises:
            RuntimeError: If real services not set up or Redis not available
        """
        if not self._real_services_setup:
            await self.setup_real_services()

        if not self._real_redis_client:
            raise RuntimeError(
                "Real Redis client not available. "
                "Ensure Redis is running and USE_REAL_SERVICES=true is set."
            )

        return self._real_redis_client

    def get_real_services_config(self) -> Optional[Dict[str, Any]]:
        """Get real services configuration.

        Returns:
            Dict containing real services URLs, ports, and connection info
        """
        self._ensure_real_services_attrs()
        return self._real_services_config

    def is_real_services_available(self) -> bool:
        """Check if real services are available and set up.

        Returns:
            bool: True if real services are available and set up
        """
        self._ensure_real_services_attrs()
        return self._real_services_setup and REAL_SERVICES_AVAILABLE

    # Private helper methods that delegate to existing SSOT infrastructure

    async def _setup_real_postgres(self):
        """Set up real PostgreSQL connection using existing SSOT infrastructure."""
        try:
            # Use pytest fixture pattern to create PostgreSQL connection
            # This delegates to the existing real_postgres_connection fixture
            from test_framework.fixtures.real_services import real_postgres_connection

            # Simulate fixture behavior
            async def postgres_fixture():
                async for connection in real_postgres_connection():
                    return connection

            postgres_info = await postgres_fixture()

            if not postgres_info or not postgres_info.get("available", False):
                raise RuntimeError("PostgreSQL connection not available")

            return postgres_info

        except Exception as e:
            logger.error(f"Failed to set up real PostgreSQL: {e}")
            raise

    async def _setup_real_database_session(self):
        """Set up real database session using existing SSOT infrastructure."""
        try:
            if not self._real_postgres_info or not self._real_postgres_info.get("available", False):
                raise RuntimeError("PostgreSQL connection required for database session")

            # Use pytest fixture pattern to create database session
            from test_framework.fixtures.real_services import with_test_database

            # Simulate fixture behavior
            async def session_fixture():
                async for session in with_test_database(self._real_postgres_info):
                    return session

            db_session = await session_fixture()

            if not db_session:
                raise RuntimeError("Database session not available")

            return db_session

        except Exception as e:
            logger.error(f"Failed to set up real database session: {e}")
            raise

    async def _setup_real_redis(self):
        """Set up real Redis client using existing SSOT infrastructure."""
        try:
            # Use pytest fixture pattern to create Redis client
            from test_framework.fixtures.real_services import real_redis_fixture

            # Simulate fixture behavior
            async def redis_fixture():
                async for client in real_redis_fixture():
                    return client

            redis_client = await redis_fixture()

            if not redis_client:
                raise RuntimeError("Redis client not available")

            return redis_client

        except Exception as e:
            logger.error(f"Failed to set up real Redis: {e}")
            raise

    async def _setup_real_services_config(self):
        """Set up comprehensive real services configuration."""
        try:
            # Use pytest fixture pattern to create services config
            from test_framework.fixtures.real_services import real_services_fixture

            # Simulate fixture behavior with the database session we already have
            async def services_fixture():
                async for config in real_services_fixture(self._real_postgres_info, self._real_db_session):
                    return config

            services_config = await services_fixture()

            if not services_config:
                raise RuntimeError("Real services configuration not available")

            return services_config

        except Exception as e:
            logger.error(f"Failed to set up real services configuration: {e}")
            raise


# Backward compatibility aliases for existing tests
RealServicesTestMixin = RealServicesFixtureMixin
RealServicesMixin = RealServicesFixtureMixin

# Export for wildcard imports
__all__ = [
    "RealServicesFixtureMixin",
    "RealServicesTestMixin",
    "RealServicesMixin"
]