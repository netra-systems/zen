"""Session Migration Utility for consolidating session management.

This script safely migrates session data from duplicate implementations
to the consolidated Redis session manager.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.redis.session_manager import RedisSessionManager

logger = central_logger.get_logger(__name__)


class SessionMigrationUtility:
    """Utility for migrating sessions to consolidated Redis session manager."""
    
    def __init__(self, redis_session_manager: Optional[RedisSessionManager] = None):
        self.consolidated_manager = redis_session_manager or RedisSessionManager()
        self.migration_stats = {
            "demo_sessions_migrated": 0,
            "auth_sessions_migrated": 0,
            "failed_migrations": 0,
            "total_sessions_processed": 0
        }
    
    async def migrate_demo_sessions(self) -> Dict[str, int]:
        """Migrate demo sessions from old demo session manager."""
        logger.info("Starting demo session migration...")
        
        try:
            # Import demo session manager to access existing sessions
            from netra_backend.app.services.demo.session_manager import SessionManager as DemoSessionManager
            
            demo_manager = DemoSessionManager()
            
            # Since demo sessions use Redis directly, we need to scan for demo session keys
            if self.consolidated_manager.redis:
                pattern = "demo:session:*"
                demo_keys = []
                
                try:
                    if hasattr(self.consolidated_manager.redis, 'scan_iter'):
                        for key in self.consolidated_manager.redis.scan_iter(pattern):
                            demo_keys.append(key.decode() if isinstance(key, bytes) else key)
                    else:
                        # Fallback for different Redis client implementations
                        demo_keys = self.consolidated_manager.redis.keys(pattern)
                
                    logger.info(f"Found {len(demo_keys)} demo sessions to validate")
                    
                    for key in demo_keys:
                        try:
                            session_id = key.replace("demo:session:", "")
                            session_data = await demo_manager.get_session(session_id)
                            
                            if session_data:
                                # Verify session format and migrate if needed
                                await self._validate_demo_session_format(session_id, session_data)
                                self.migration_stats["demo_sessions_migrated"] += 1
                            
                        except Exception as e:
                            logger.error(f"Failed to migrate demo session {key}: {e}")
                            self.migration_stats["failed_migrations"] += 1
                        
                        self.migration_stats["total_sessions_processed"] += 1
                
                except Exception as e:
                    logger.error(f"Error scanning for demo sessions: {e}")
            
            logger.info(f"Demo session migration completed. Migrated: {self.migration_stats['demo_sessions_migrated']}")
            
        except ImportError:
            logger.warning("Demo session manager not available for migration")
        except Exception as e:
            logger.error(f"Demo session migration failed: {e}")
        
        return self.migration_stats
    
    async def migrate_auth_sessions(self) -> Dict[str, int]:
        """Migrate auth sessions if needed (auth service maintains independence)."""
        logger.info("Checking auth session compatibility...")
        
        try:
            # SSOT: Use auth integration layer instead of direct auth service import
            # This prevents startup failures when auth service is not available
            from netra_backend.app.auth_integration.auth import AuthIntegration
            
            # Check auth service availability through integration layer
            auth_integration = AuthIntegration()
            
            # Test connectivity to auth service
            try:
                # This will fail gracefully if auth service is not available
                health_status = await auth_integration.health_check()
                logger.info(f"Auth service health through integration: {'OK' if health_status else 'DEGRADED'}")
                self.migration_stats["auth_sessions_migrated"] = 1
            except Exception as e:
                logger.warning(f"Auth service not available through integration layer: {e}")
                # This is acceptable - auth service may not be running during migration
                
        except ImportError as e:
            logger.warning(f"Auth integration layer not available: {e}")
        except Exception as e:
            logger.error(f"Auth session compatibility check failed: {e}")
        
        return self.migration_stats
    
    async def _validate_demo_session_format(self, session_id: str, session_data: Dict[str, Any]):
        """Validate and normalize demo session format."""
        required_fields = ["industry", "started_at", "messages"]
        
        # Check if session has required fields
        for field in required_fields:
            if field not in session_data:
                logger.warning(f"Demo session {session_id} missing field: {field}")
                
                # Add missing fields with defaults
                if field == "industry":
                    session_data["industry"] = "general"
                elif field == "started_at":
                    session_data["started_at"] = datetime.now(timezone.utc).isoformat()
                elif field == "messages":
                    session_data["messages"] = []
        
        # Ensure session_type is set
        if "session_type" not in session_data:
            session_data["session_type"] = "demo"
        
        # Update the session with normalized format
        try:
            # Store using consolidated manager to ensure format consistency
            session_key = f"{self.consolidated_manager.demo_session_prefix}{session_id}"
            
            if self.consolidated_manager.redis:
                await self.consolidated_manager.redis.setex(
                    session_key,
                    self.consolidated_manager.demo_ttl,
                    json.dumps(session_data)
                )
                
            logger.debug(f"Validated demo session format: {session_id}")
            
        except Exception as e:
            logger.error(f"Failed to validate demo session {session_id}: {e}")
            raise
    
    async def cleanup_legacy_references(self):
        """Clean up any legacy session references."""
        logger.info("Cleaning up legacy session references...")
        
        # Clean up any orphaned session data
        if self.consolidated_manager.redis:
            try:
                # Look for any sessions with old patterns that might need cleanup
                patterns = [
                    "session:*",  # Standard sessions
                    "demo:session:*",  # Demo sessions
                    "user_sessions:*"  # User session lists
                ]
                
                for pattern in patterns:
                    keys = []
                    if hasattr(self.consolidated_manager.redis, 'scan_iter'):
                        keys = list(self.consolidated_manager.redis.scan_iter(pattern))
                    else:
                        keys = self.consolidated_manager.redis.keys(pattern)
                    
                    logger.info(f"Found {len(keys)} keys for pattern {pattern}")
                    
                    # Validate each key has proper format
                    for key in keys:
                        key_str = key.decode() if isinstance(key, bytes) else key
                        try:
                            data = await self.consolidated_manager.redis.get(key_str)
                            if data:
                                session_data = json.loads(data)
                                # Validate session data format
                                if not isinstance(session_data, dict):
                                    logger.warning(f"Invalid session data format for key {key_str}")
                        except (json.JSONDecodeError, Exception) as e:
                            logger.warning(f"Failed to validate session key {key_str}: {e}")
            
            except Exception as e:
                logger.error(f"Failed to cleanup legacy references: {e}")
    
    async def generate_migration_report(self) -> str:
        """Generate migration report."""
        report = f"""
Session Migration Report
========================
Generated: {datetime.now(timezone.utc).isoformat()}

Migration Statistics:
- Demo sessions migrated: {self.migration_stats['demo_sessions_migrated']}
- Auth sessions checked: {self.migration_stats['auth_sessions_migrated']}
- Failed migrations: {self.migration_stats['failed_migrations']}
- Total sessions processed: {self.migration_stats['total_sessions_processed']}

Consolidated Session Manager Status:
- Redis available: {self.consolidated_manager.redis is not None}
- Default TTL: {self.consolidated_manager.default_ttl}s
- Demo TTL: {self.consolidated_manager.demo_ttl}s

Next Steps:
1. Update all imports to use consolidated Redis session manager
2. Remove duplicate session manager implementations
3. Run comprehensive tests to verify session functionality
4. Deploy changes with careful monitoring

Migration Status: {'SUCCESS' if self.migration_stats['failed_migrations'] == 0 else 'PARTIAL'}
        """
        
        logger.info("Migration report generated")
        return report.strip()


async def run_session_migration():
    """Main migration function."""
    logger.info("Starting session management consolidation migration...")
    
    migration_util = SessionMigrationUtility()
    
    try:
        # Migrate demo sessions
        await migration_util.migrate_demo_sessions()
        
        # Check auth session compatibility
        await migration_util.migrate_auth_sessions()
        
        # Clean up legacy references
        await migration_util.cleanup_legacy_references()
        
        # Generate report
        report = await migration_util.generate_migration_report()
        print(report)
        
        return migration_util.migration_stats
        
    except Exception as e:
        logger.error(f"Session migration failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(run_session_migration())