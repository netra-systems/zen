"""Migration Lock Management System

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Prevent database corruption from concurrent migrations
- Value Impact: Ensures data integrity during multi-service cold starts
- Strategic Impact: Enables reliable horizontal scaling and zero-downtime deployments

This module provides advisory lock management for database migrations
to prevent race conditions during concurrent service startup.
"""

import asyncio
import time
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.exc import OperationalError, DisconnectionError

from netra_backend.app.logging_config import central_logger
from netra_backend.app.db.database_manager import DatabaseManager

logger = central_logger.get_logger(__name__)


class MigrationLockManager:
    """Manages advisory locks for database migrations to prevent race conditions."""
    
    # PostgreSQL advisory lock constants
    MIGRATION_LOCK_KEY = 982451653  # Unique lock key for migrations
    SCHEMA_VERSION_LOCK_KEY = 982451654  # Lock key for schema version updates
    
    def __init__(self, engine: AsyncEngine = None):
        """Initialize migration lock manager.
        
        Args:
            engine: Optional AsyncEngine. If None, creates one from DatabaseManager.
        """
        self._engine = engine
        self._lock_timeout = 300  # 5 minutes maximum lock hold time
        self._acquisition_timeout = 60  # 1 minute to acquire lock
        
    async def _get_engine(self) -> AsyncEngine:
        """Get or create database engine lazily."""
        if not self._engine:
            # MIGRATION NOTE: Consider using netra_backend.app.database for SSOT compliance
            from netra_backend.app.db.postgres_core import AsyncDatabase
            async_db = AsyncDatabase()
            await async_db._ensure_initialized()
            self._engine = async_db._engine
        return self._engine
    
    async def _execute_lock_query(self, session: AsyncSession, query: str, lock_key: int) -> Any:
        """Execute advisory lock query with error handling.
        
        Args:
            session: Database session
            query: SQL query to execute
            lock_key: Advisory lock key
            
        Returns:
            Query result
        """
        try:
            result = await session.execute(text(query), {"lock_key": lock_key})
            return result.scalar()
        except (OperationalError, DisconnectionError) as e:
            logger.error(f"Lock operation failed: {e}")
            raise
    
    async def acquire_migration_lock(self, timeout: Optional[float] = None) -> bool:
        """Acquire advisory lock for migrations.
        
        Args:
            timeout: Optional timeout in seconds. If None, uses default.
            
        Returns:
            True if lock acquired successfully, False otherwise
        """
        timeout = timeout or self._acquisition_timeout
        engine = await self._get_engine()
        
        start_time = time.time()
        
        while (time.time() - start_time) < timeout:
            try:
                async with engine.begin() as conn:
                    # Try to acquire non-blocking advisory lock
                    result = await conn.execute(
                        text("SELECT pg_try_advisory_lock(:lock_key)"),
                        {"lock_key": self.MIGRATION_LOCK_KEY}
                    )
                    
                    if result.scalar():
                        logger.info(f"Migration advisory lock acquired (key: {self.MIGRATION_LOCK_KEY})")
                        return True
                        
                    # Lock not available, wait before retry
                    await asyncio.sleep(1.0)
                    
            except Exception as e:
                logger.warning(f"Failed to acquire migration lock: {e}")
                await asyncio.sleep(2.0)  # Wait longer on error
                
        logger.error(f"Failed to acquire migration lock within {timeout}s timeout")
        return False
    
    async def release_migration_lock(self) -> bool:
        """Release advisory lock for migrations.
        
        Returns:
            True if lock released successfully, False otherwise
        """
        try:
            engine = await self._get_engine()
            
            async with engine.begin() as conn:
                result = await conn.execute(
                    text("SELECT pg_advisory_unlock(:lock_key)"),
                    {"lock_key": self.MIGRATION_LOCK_KEY}
                )
                
                if result.scalar():
                    logger.info(f"Migration advisory lock released (key: {self.MIGRATION_LOCK_KEY})")
                    return True
                else:
                    logger.warning("Migration lock was not held by this session")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to release migration lock: {e}")
            return False
    
    @asynccontextmanager
    async def migration_lock_context(self, timeout: Optional[float] = None):
        """Context manager for migration lock acquisition and release.
        
        Args:
            timeout: Optional timeout for lock acquisition
            
        Yields:
            True if lock acquired, False otherwise
            
        Example:
            async with migration_manager.migration_lock_context() as locked:
                if locked:
                    # Perform migration operations
                    pass
        """
        lock_acquired = False
        try:
            lock_acquired = await self.acquire_migration_lock(timeout)
            yield lock_acquired
        finally:
            if lock_acquired:
                await self.release_migration_lock()
    
    async def get_lock_status(self) -> Dict[str, Any]:
        """Get current lock status information.
        
        Returns:
            Dictionary with lock status details
        """
        try:
            engine = await self._get_engine()
            
            async with engine.begin() as conn:
                # Query current advisory locks
                result = await conn.execute(text("""
                    SELECT 
                        classid,
                        objid,
                        objsubid,
                        locktype,
                        mode,
                        granted,
                        pid,
                        application_name
                    FROM pg_locks 
                    WHERE locktype = 'advisory' 
                    AND objid = :lock_key
                """), {"lock_key": self.MIGRATION_LOCK_KEY})
                
                locks = []
                for row in result:
                    locks.append({
                        "classid": row[0],
                        "objid": row[1],
                        "objsubid": row[2],
                        "locktype": row[3],
                        "mode": row[4],
                        "granted": row[5],
                        "pid": row[6],
                        "application_name": row[7]
                    })
                
                return {
                    "lock_key": self.MIGRATION_LOCK_KEY,
                    "active_locks": locks,
                    "lock_count": len(locks),
                    "timestamp": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Failed to get lock status: {e}")
            return {
                "lock_key": self.MIGRATION_LOCK_KEY,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def force_release_all_locks(self) -> int:
        """Force release all advisory locks (emergency use only).
        
        Returns:
            Number of locks released
        """
        try:
            engine = await self._get_engine()
            
            async with engine.begin() as conn:
                # Release all advisory locks held by this session
                result = await conn.execute(text("SELECT pg_advisory_unlock_all()"))
                
                logger.warning("Force released all advisory locks for current session")
                return 1  # pg_advisory_unlock_all() doesn't return count
                
        except Exception as e:
            logger.error(f"Failed to force release locks: {e}")
            return 0


class SchemaVersionTracker:
    """Tracks database schema versions and compatibility."""
    
    def __init__(self, lock_manager: MigrationLockManager = None):
        """Initialize schema version tracker.
        
        Args:
            lock_manager: Optional MigrationLockManager instance
        """
        self.lock_manager = lock_manager or MigrationLockManager()
    
    async def _ensure_version_table(self, session: AsyncSession):
        """Ensure schema version tracking table exists."""
        await session.execute(text("""
            CREATE TABLE IF NOT EXISTS netra_schema_versions (
                component VARCHAR(50) PRIMARY KEY,
                version VARCHAR(20) NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                applied_by VARCHAR(100),
                checksum VARCHAR(64),
                metadata JSONB DEFAULT '{}'::jsonb
            )
        """))
        await session.commit()
    
    async def get_schema_version(self, component: str = "netra_backend") -> Optional[str]:
        """Get current schema version for component.
        
        Args:
            component: Component name (default: netra_backend)
            
        Returns:
            Current schema version or None if not found
        """
        try:
            engine = await self.lock_manager._get_engine()
            
            async with engine.begin() as conn:
                session = AsyncSession(conn, expire_on_commit=False)
                await self._ensure_version_table(session)
                
                result = await session.execute(
                    text("SELECT version FROM netra_schema_versions WHERE component = :component"),
                    {"component": component}
                )
                
                row = result.first()
                return row[0] if row else None
                
        except Exception as e:
            logger.error(f"Failed to get schema version for {component}: {e}")
            return None
    
    async def set_schema_version(self, component: str, version: str, 
                               applied_by: str = None, checksum: str = None,
                               metadata: Dict = None) -> bool:
        """Set schema version for component.
        
        Args:
            component: Component name
            version: Schema version
            applied_by: Who applied the schema (optional)
            checksum: Schema checksum (optional)
            metadata: Additional metadata (optional)
            
        Returns:
            True if version set successfully, False otherwise
        """
        try:
            async with self.lock_manager.migration_lock_context() as locked:
                if not locked:
                    logger.error("Could not acquire migration lock to set schema version")
                    return False
                
                engine = await self.lock_manager._get_engine()
                
                async with engine.begin() as conn:
                    session = AsyncSession(conn, expire_on_commit=False)
                    await self._ensure_version_table(session)
                    
                    # Upsert schema version
                    await session.execute(text("""
                        INSERT INTO netra_schema_versions 
                        (component, version, applied_by, checksum, metadata)
                        VALUES (:component, :version, :applied_by, :checksum, :metadata)
                        ON CONFLICT (component) DO UPDATE SET
                            version = EXCLUDED.version,
                            applied_at = CURRENT_TIMESTAMP,
                            applied_by = EXCLUDED.applied_by,
                            checksum = EXCLUDED.checksum,
                            metadata = EXCLUDED.metadata
                    """), {
                        "component": component,
                        "version": version,
                        "applied_by": applied_by or "system",
                        "checksum": checksum,
                        "metadata": metadata or {}
                    })
                    
                    await session.commit()
                    logger.info(f"Set schema version for {component}: {version}")
                    return True
                    
        except Exception as e:
            logger.error(f"Failed to set schema version for {component}: {e}")
            return False
    
    async def check_version_compatibility(self, component: str, required_version: str) -> bool:
        """Check if current schema version is compatible with required version.
        
        Args:
            component: Component name
            required_version: Required minimum version
            
        Returns:
            True if compatible, False otherwise
        """
        current_version = await self.get_schema_version(component)
        
        if not current_version:
            logger.warning(f"No schema version found for {component}")
            return False
        
        try:
            # Simple version comparison (semantic versioning)
            current_parts = [int(x) for x in current_version.split('.')]
            required_parts = [int(x) for x in required_version.split('.')]
            
            # Pad shorter version with zeros
            max_len = max(len(current_parts), len(required_parts))
            current_parts.extend([0] * (max_len - len(current_parts)))
            required_parts.extend([0] * (max_len - len(required_parts)))
            
            compatible = current_parts >= required_parts
            
            if not compatible:
                logger.error(f"Schema version incompatible for {component}: "
                           f"current={current_version}, required={required_version}")
            
            return compatible
            
        except ValueError as e:
            logger.error(f"Invalid version format: {e}")
            return False


# Global instance for easy access
migration_lock_manager = MigrationLockManager()
schema_version_tracker = SchemaVersionTracker(migration_lock_manager)


# Export main classes and instances
__all__ = [
    "MigrationLockManager", "SchemaVersionTracker",
    "migration_lock_manager", "schema_version_tracker"
]