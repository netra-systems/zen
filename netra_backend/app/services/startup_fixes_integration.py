# Use backend-specific isolated environment
try:
    from netra_backend.app.core.isolated_environment import get_env
except ImportError:
    # Production fallback if isolated_environment module unavailable
    import os
    def get_env():
        """Fallback environment accessor for production."""
        class FallbackEnv:
            def get(self, key, default=None):
                return os.environ.get(key, default)
            def set(self, key, value, source="production"):
                os.environ[key] = value
        return FallbackEnv()
except ImportError:
    # Production fallback if isolated_environment module unavailable
    import os
    def get_env():
        """Fallback environment accessor for production."""
        class FallbackEnv:
            def get(self, key, default=None):
                return os.environ.get(key, default)
            def set(self, key, value, source="production"):
                os.environ[key] = value
        return FallbackEnv()
"""Integration module for startup fixes

This module provides integration points for all the critical startup fixes
to ensure they are properly applied across the system.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: System Reliability and Development Velocity
- Value Impact: Eliminates critical startup failures that block development
- Strategic Impact: Ensures consistent, reliable system initialization

Fixes Integrated:
1. Environment Variable Mapping Mismatch (CLICKHOUSE_PASSWORD vs CLICKHOUSE_DEFAULT_PASSWORD)
2. Service Port Conflicts (Hard-coded ports causing failures)
3. Database User Transaction Rollback (Partial user records on failure)
4. Background Task Timeout Crash (4-minute crash from background tasks)
5. Redis Connection Failures (No local fallback when remote fails)
"""

import asyncio
import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class StartupFixesIntegration:
    """Integration manager for all startup fixes."""
    
    def __init__(self):
        """Initialize the startup fixes integration."""
        self.fixes_applied = set()
        self.environment_fixes = {}
        
    def apply_environment_variable_fixes(self) -> Dict[str, str]:
        """Apply environment variable mapping fixes.
        
        Returns:
            Dictionary of fixes applied
        """
        fixes = {}
        
        # FIX 1: ClickHouse password environment variable mapping
        clickhouse_password = get_env().get("CLICKHOUSE_PASSWORD")
        clickhouse_default_password = get_env().get("CLICKHOUSE_DEFAULT_PASSWORD")
        
        if clickhouse_default_password and not clickhouse_password:
            os.environ["CLICKHOUSE_PASSWORD"] = clickhouse_default_password
            fixes["clickhouse_password_mapping"] = f"Mapped CLICKHOUSE_DEFAULT_PASSWORD to CLICKHOUSE_PASSWORD"
            logger.info("Applied ClickHouse password environment variable mapping fix")
        elif clickhouse_password and not clickhouse_default_password:
            os.environ["CLICKHOUSE_DEFAULT_PASSWORD"] = clickhouse_password
            fixes["clickhouse_default_password_mapping"] = f"Mapped CLICKHOUSE_PASSWORD to CLICKHOUSE_DEFAULT_PASSWORD"
            logger.info("Applied reverse ClickHouse password environment variable mapping fix")
        
        # FIX 5: Redis mode local fallback
        redis_mode = get_env().get("REDIS_MODE")
        if not redis_mode:
            # Set default Redis mode that supports fallback
            os.environ["REDIS_MODE"] = "shared"  # Will fallback to local if remote fails
            fixes["redis_mode_default"] = "Set default REDIS_MODE with fallback capability"
            logger.info("Applied Redis mode default with fallback capability")
        
        self.environment_fixes = fixes
        self.fixes_applied.add("environment_variables")
        
        return fixes
    
    def verify_port_conflict_resolution(self) -> Dict[str, Any]:
        """Verify that port conflict resolution is properly configured.
        
        Returns:
            Dictionary with port conflict resolution status
        """
        status = {
            "dynamic_ports_enabled": False,
            "service_discovery_available": False,
            "port_conflict_resolution": False
        }
        
        # Service discovery removed for microservice independence
        # Port conflict resolution handled at deployment level
        status["service_discovery_available"] = False
        status["port_conflict_resolution"] = False
        logger.info("Service discovery disabled for microservice independence")
        
        # Check if dynamic port allocation is configured
        try:
            from netra_backend.app.core.network_constants import ServicePorts
            if hasattr(ServicePorts, 'DYNAMIC_PORT_MIN') and hasattr(ServicePorts, 'DYNAMIC_PORT_MAX'):
                status["dynamic_ports_enabled"] = True
                logger.info("Dynamic port allocation is configured")
        except ImportError:
            logger.warning("Network constants not available for dynamic port checking")
        
        if status["port_conflict_resolution"]:
            self.fixes_applied.add("port_conflicts")
        
        return status
    
    def verify_background_task_timeout_fix(self) -> Dict[str, Any]:
        """Verify that background task timeout fix is properly configured.
        
        Returns:
            Dictionary with background task manager status
        """
        status = {
            "background_task_manager_available": False,
            "default_timeout_configured": False,
            "timeout_seconds": None
        }
        
        try:
            from netra_backend.app.services.background_task_manager import background_task_manager
            status["background_task_manager_available"] = True
            
            # Check timeout configuration
            if hasattr(background_task_manager, 'default_timeout'):
                timeout = background_task_manager.default_timeout
                status["default_timeout_configured"] = True
                status["timeout_seconds"] = timeout
                
                if timeout <= 120:  # 2 minutes or less to prevent 4-minute crash
                    logger.info(f"Background task timeout properly configured: {timeout}s")
                    self.fixes_applied.add("background_task_timeout")
                else:
                    logger.warning(f"Background task timeout may be too high: {timeout}s")
            
        except ImportError:
            logger.warning("Background task manager not available")
        
        return status
    
    def verify_redis_fallback_fix(self) -> Dict[str, Any]:
        """Verify that Redis local fallback is properly configured.
        
        Returns:
            Dictionary with Redis fallback status
        """
        status = {
            "redis_manager_available": False,
            "fallback_configured": False,
            "redis_mode": get_env().get("REDIS_MODE")
        }
        
        try:
            from netra_backend.app.redis_manager import RedisManager
            status["redis_manager_available"] = True
            
            # Check if the Redis manager has local fallback capability
            redis_manager = RedisManager()
            if hasattr(redis_manager, '_create_redis_client'):
                status["fallback_configured"] = True
                logger.info("Redis local fallback is configured")
                self.fixes_applied.add("redis_fallback")
            
        except ImportError:
            logger.warning("Redis manager not available")
        
        return status
    
    def verify_database_transaction_fix(self) -> Dict[str, Any]:
        """Verify that database transaction rollback fix is available.
        
        Returns:
            Dictionary with database transaction fix status
        """
        status = {
            "auth_database_manager_available": False,
            "rollback_method_available": False
        }
        
        try:
            from netra_backend.app.db.database_manager import DatabaseManager
            status["auth_database_manager_available"] = True
            
            # Check if the rollback method is available
            if hasattr(DatabaseManager, 'create_user_with_rollback'):
                status["rollback_method_available"] = True
                logger.info("Database transaction rollback fix is available")
                self.fixes_applied.add("database_transaction_rollback")
            
        except ImportError:
            logger.warning("Database manager not available")
        
        return status
    
    async def run_comprehensive_verification(self) -> Dict[str, Any]:
        """Run comprehensive verification of all startup fixes.
        
        Returns:
            Dictionary with complete verification results
        """
        logger.info("Running comprehensive startup fixes verification...")
        
        results = {
            "timestamp": __import__("time").time(),
            "environment_fixes": self.apply_environment_variable_fixes(),
            "port_conflict_resolution": self.verify_port_conflict_resolution(),
            "background_task_timeout": self.verify_background_task_timeout_fix(),
            "redis_fallback": self.verify_redis_fallback_fix(),
            "database_transaction": self.verify_database_transaction_fix(),
            "fixes_applied": list(self.fixes_applied),
            "total_fixes": len(self.fixes_applied)
        }
        
        logger.info(f"Startup fixes verification complete: {results['total_fixes']}/5 fixes applied")
        
        return results
    
    def get_fix_status_summary(self) -> str:
        """Get a human-readable summary of fix status.
        
        Returns:
            Summary string describing which fixes are applied
        """
        total_fixes = 5
        applied_count = len(self.fixes_applied)
        
        status_lines = [
            f"Startup Fixes Status: {applied_count}/{total_fixes} applied",
            "",
            "✅ Applied fixes:"
        ]
        
        fix_descriptions = {
            "environment_variables": "Environment variable mapping (CLICKHOUSE_PASSWORD)",
            "port_conflicts": "Service port conflict resolution",
            "background_task_timeout": "Background task timeout (2-minute limit)",
            "redis_fallback": "Redis local fallback capability",
            "database_transaction_rollback": "Database transaction rollback handling"
        }
        
        for fix_key in self.fixes_applied:
            status_lines.append(f"  • {fix_descriptions.get(fix_key, fix_key)}")
        
        missing_fixes = set(fix_descriptions.keys()) - self.fixes_applied
        if missing_fixes:
            status_lines.extend([
                "",
                "❌ Missing fixes:"
            ])
            for fix_key in missing_fixes:
                status_lines.append(f"  • {fix_descriptions.get(fix_key, fix_key)}")
        
        return "\n".join(status_lines)


# Global instance for application use
startup_fixes = StartupFixesIntegration()


# Convenience functions
def apply_all_startup_fixes() -> Dict[str, Any]:
    """Apply all startup fixes and return results."""
    return asyncio.run(startup_fixes.run_comprehensive_verification())


def get_startup_fix_summary() -> str:
    """Get a summary of startup fix status."""
    return startup_fixes.get_fix_status_summary()


def ensure_environment_fixes():
    """Ensure environment variable fixes are applied."""
    startup_fixes.apply_environment_variable_fixes()