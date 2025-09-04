"""
AdminToolDispatcher Migration Helper

This module provides utilities to help migrate from singleton AdminToolDispatcher
patterns to the modern request-scoped pattern with UserExecutionContext.

Business Value: Smooth migration path without breaking existing functionality.
"""

import uuid
from datetime import datetime, timezone
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from netra_backend.app.websocket_core.manager import WebSocketManager

from langchain_core.tools import BaseTool
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.agents.admin_tool_dispatcher.factory import AdminToolDispatcherFactory
from netra_backend.app.agents.admin_tool_dispatcher.dispatcher_core import AdminToolDispatcher
from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext
from netra_backend.app.db.models_postgres import User
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class AdminToolDispatcherMigrationHelper:
    """Helper utilities for migrating AdminToolDispatcher to request-scoped pattern."""
    
    @staticmethod
    def create_temporary_context_for_migration(
        admin_user: User,
        operation_name: str = "legacy_admin_migration"
    ) -> UserExecutionContext:
        """Create a temporary UserExecutionContext for legacy code migration.
        
        This is a MIGRATION HELPER ONLY - use proper request contexts in production.
        Creates a temporary context to bridge legacy code that doesn't have proper
        request context to the modern request-scoped pattern.
        
        Args:
            admin_user: Admin user performing the operation
            operation_name: Name of the operation (for tracking)
            
        Returns:
            UserExecutionContext: Temporary context for migration
        """
        logger.warning(f"⚠️ Creating TEMPORARY context for admin migration - admin_user: {admin_user.id}")
        logger.warning("⚠️ This should only be used during migration - provide proper UserExecutionContext in production")
        
        # Create temporary IDs for migration using UnifiedIDManager for consistency
        from netra_backend.app.core.unified_id_manager import UnifiedIDManager
        temp_user_id = f"admin_{admin_user.id}"
        base_thread_id = UnifiedIDManager.generate_thread_id()
        temp_thread_id = f"migration_{base_thread_id}"
        temp_run_id = UnifiedIDManager.generate_run_id(temp_thread_id)
        
        return UserExecutionContext(
            user_id=temp_user_id,
            thread_id=temp_thread_id,
            run_id=temp_run_id,
            request_id=str(uuid.uuid4()),
            websocket_connection_id=None,
            created_at=datetime.now(timezone.utc),
            metadata={
                'migration_helper': True,
                'original_admin_user_id': admin_user.id,
                'operation_name': operation_name,
                'warning': 'TEMPORARY CONTEXT - Replace with proper request context'
            }
        )
    
    @staticmethod
    async def upgrade_legacy_admin_dispatcher_creation(
        admin_user: User,
        db_session: AsyncSession,
        tools: List[BaseTool] = None,
        llm_manager = None,
        websocket_manager: Optional['WebSocketManager'] = None,
        user_context: Optional[UserExecutionContext] = None
    ) -> AdminToolDispatcher:
        """Upgrade legacy AdminToolDispatcher creation to modern pattern.
        
        This method provides a smooth migration path by:
        1. Using provided user_context if available (RECOMMENDED)
        2. Creating temporary context if not provided (MIGRATION ONLY)
        3. Using modern factory pattern in both cases
        
        Args:
            admin_user: User performing admin operations
            db_session: Database session for admin operations
            tools: Optional list of tools to register
            llm_manager: Optional LLM manager
            websocket_manager: Optional WebSocket manager
            user_context: Optional UserExecutionContext (RECOMMENDED - provide this!)
            
        Returns:
            AdminToolDispatcher: Modern request-scoped admin dispatcher
        """
        # Check if we have a proper user context
        if user_context is not None:
            logger.info(f"✅ Upgrading legacy AdminToolDispatcher with provided UserExecutionContext")
            return await AdminToolDispatcherFactory.create_admin_dispatcher(
                user_context, admin_user, db_session, tools, websocket_manager
            )
        
        # Fallback: Create temporary context (migration path)
        logger.warning(f"⚠️ No UserExecutionContext provided - creating temporary context for migration")
        logger.warning(f"⚠️ Please update calling code to provide proper UserExecutionContext")
        
        temp_context = AdminToolDispatcherMigrationHelper.create_temporary_context_for_migration(
            admin_user, "legacy_admin_dispatcher_upgrade"
        )
        
        return await AdminToolDispatcherFactory.create_admin_dispatcher(
            temp_context, admin_user, db_session, tools, websocket_manager
        )
    
    @staticmethod
    def detect_legacy_usage(dispatcher: AdminToolDispatcher) -> bool:
        """Detect if an AdminToolDispatcher instance is using legacy patterns.
        
        Args:
            dispatcher: AdminToolDispatcher instance to check
            
        Returns:
            bool: True if using legacy patterns, False if modern
        """
        # Check for modern request-scoped markers
        if hasattr(dispatcher, '_is_request_scoped') and dispatcher._is_request_scoped:
            return False
        
        # Check for legacy global markers
        if hasattr(dispatcher, '_is_legacy_global') and dispatcher._is_legacy_global:
            return True
        
        # Check for modern admin context
        if hasattr(dispatcher, '_admin_context') and dispatcher._admin_context:
            return False
        
        # Check if parent has user_context (modern pattern)
        if hasattr(dispatcher, 'user_context') and dispatcher.user_context:
            return False
        
        # Default assumption: if no clear markers, assume legacy
        logger.warning(f"⚠️ AdminToolDispatcher usage pattern unclear - assuming legacy")
        return True
    
    @staticmethod
    def log_migration_status(dispatcher: AdminToolDispatcher) -> None:
        """Log migration status of an AdminToolDispatcher instance.
        
        Args:
            dispatcher: AdminToolDispatcher instance to analyze
        """
        is_legacy = AdminToolDispatcherMigrationHelper.detect_legacy_usage(dispatcher)
        
        if is_legacy:
            logger.warning(f"🔄 LEGACY AdminToolDispatcher detected:")
            logger.warning(f"   - User: {getattr(dispatcher, 'user', {}).id if hasattr(dispatcher, 'user') else 'Unknown'}")
            logger.warning(f"   - Pattern: Global/Singleton (may cause user isolation issues)")
            logger.warning(f"   - Migration: Use AdminToolDispatcherFactory.create_admin_dispatcher()")
        else:
            context_id = "Unknown"
            if hasattr(dispatcher, '_admin_context') and dispatcher._admin_context:
                context_id = dispatcher._admin_context.get_correlation_id()
            elif hasattr(dispatcher, 'user_context') and dispatcher.user_context:
                context_id = dispatcher.user_context.get_correlation_id()
            
            logger.info(f"✅ MODERN AdminToolDispatcher detected:")
            logger.info(f"   - Context: {context_id}")
            logger.info(f"   - Pattern: Request-Scoped (proper user isolation)")
            logger.info(f"   - Status: Fully migrated")
    
    @staticmethod
    def create_migration_report(dispatchers: List[AdminToolDispatcher]) -> dict:
        """Create migration status report for multiple AdminToolDispatcher instances.
        
        Args:
            dispatchers: List of AdminToolDispatcher instances to analyze
            
        Returns:
            dict: Migration status report
        """
        legacy_count = 0
        modern_count = 0
        unclear_count = 0
        
        legacy_details = []
        modern_details = []
        
        for i, dispatcher in enumerate(dispatchers):
            try:
                is_legacy = AdminToolDispatcherMigrationHelper.detect_legacy_usage(dispatcher)
                
                if is_legacy:
                    legacy_count += 1
                    legacy_details.append({
                        'index': i,
                        'user_id': getattr(dispatcher, 'user', {}).id if hasattr(dispatcher, 'user') else None,
                        'type': 'legacy'
                    })
                else:
                    modern_count += 1
                    context_id = "Unknown"
                    if hasattr(dispatcher, '_admin_context') and dispatcher._admin_context:
                        context_id = dispatcher._admin_context.get_correlation_id()
                    elif hasattr(dispatcher, 'user_context') and dispatcher.user_context:
                        context_id = dispatcher.user_context.get_correlation_id()
                    
                    modern_details.append({
                        'index': i,
                        'context_id': context_id,
                        'type': 'modern'
                    })
                    
            except Exception as e:
                unclear_count += 1
                logger.error(f"Error analyzing dispatcher {i}: {e}")
        
        total_count = len(dispatchers)
        migration_percentage = (modern_count / total_count * 100) if total_count > 0 else 0
        
        report = {
            'total_dispatchers': total_count,
            'modern_count': modern_count,
            'legacy_count': legacy_count,
            'unclear_count': unclear_count,
            'migration_percentage': migration_percentage,
            'migration_complete': legacy_count == 0 and unclear_count == 0,
            'modern_details': modern_details,
            'legacy_details': legacy_details,
            'recommendations': []
        }
        
        # Add recommendations
        if legacy_count > 0:
            report['recommendations'].append(
                f"Migrate {legacy_count} legacy AdminToolDispatcher instances to use "
                f"AdminToolDispatcherFactory.create_admin_dispatcher() with UserExecutionContext"
            )
        
        if unclear_count > 0:
            report['recommendations'].append(
                f"Investigate {unclear_count} AdminToolDispatcher instances with unclear patterns"
            )
        
        if migration_percentage == 100:
            report['recommendations'].append(
                "✅ All AdminToolDispatcher instances are using modern request-scoped pattern!"
            )
        
        return report


# Convenience functions for common migration scenarios
async def upgrade_admin_dispatcher_creation(
    admin_user: User,
    db_session: AsyncSession,
    **kwargs
) -> AdminToolDispatcher:
    """Convenience function for upgrading legacy AdminToolDispatcher creation."""
    return await AdminToolDispatcherMigrationHelper.upgrade_legacy_admin_dispatcher_creation(
        admin_user, db_session, **kwargs
    )


def create_migration_context(admin_user: User) -> UserExecutionContext:
    """Convenience function for creating temporary migration context."""
    return AdminToolDispatcherMigrationHelper.create_temporary_context_for_migration(admin_user)


def analyze_dispatcher_migration_status(dispatcher: AdminToolDispatcher) -> dict:
    """Convenience function for analyzing single dispatcher migration status."""
    is_legacy = AdminToolDispatcherMigrationHelper.detect_legacy_usage(dispatcher)
    AdminToolDispatcherMigrationHelper.log_migration_status(dispatcher)
    
    return {
        'is_legacy': is_legacy,
        'is_modern': not is_legacy,
        'migration_needed': is_legacy
    }


# Export all public interfaces
__all__ = [
    'AdminToolDispatcherMigrationHelper',
    'upgrade_admin_dispatcher_creation', 
    'create_migration_context',
    'analyze_dispatcher_migration_status'
]