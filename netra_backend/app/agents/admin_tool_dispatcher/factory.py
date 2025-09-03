"""
AdminToolDispatcher Factory - Request-Scoped Pattern Implementation

This factory provides the modern request-scoped AdminToolDispatcher creation
with complete UserExecutionContext integration for perfect user isolation.

Business Value: Eliminates cross-user data contamination in admin operations.
"""

import asyncio
from contextlib import asynccontextmanager
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from netra_backend.app.websocket_core.manager import WebSocketManager

from langchain_core.tools import BaseTool
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.agents.admin_tool_dispatcher.dispatcher_core import AdminToolDispatcher
from netra_backend.app.agents.admin_tool_dispatcher.modernized_wrapper import ModernizedAdminToolDispatcher
from netra_backend.app.agents.supervisor.user_execution_context import (
    UserExecutionContext,
    validate_user_context,
    InvalidContextError
)
from netra_backend.app.db.models_postgres import User
from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.permission_service import PermissionService
from netra_backend.app.services.websocket_event_emitter import (
    WebSocketEventEmitterFactory
)

logger = central_logger.get_logger(__name__)


class AdminToolDispatcherFactory:
    """Factory for creating request-scoped AdminToolDispatcher instances with perfect user isolation."""
    
    @staticmethod
    async def create_admin_dispatcher(
        user_context: UserExecutionContext,
        admin_user: User,
        db_session: AsyncSession,
        tools: List[BaseTool] = None,
        websocket_manager: Optional['WebSocketManager'] = None,
        permission_service = None,
        llm_manager = None
    ) -> AdminToolDispatcher:
        """Create request-scoped admin tool dispatcher with user isolation.
        
        This is the RECOMMENDED way to create AdminToolDispatcher instances for
        all new code. Provides complete request isolation and WebSocket integration.
        
        Args:
            user_context: UserExecutionContext for complete request isolation (REQUIRED)
            admin_user: User performing admin operations (must have admin permissions)
            db_session: Database session for admin operations (REQUIRED)
            tools: Optional list of tools to register initially
            websocket_manager: Optional WebSocket manager for event routing
            permission_service: Optional permission service for security
            llm_manager: Optional LLM manager (legacy compatibility)
            
        Returns:
            AdminToolDispatcher: Isolated admin dispatcher for this request
            
        Raises:
            PermissionError: If admin_user lacks admin permissions
            InvalidContextError: If user_context is invalid
            ValueError: If required parameters are missing
        """
        logger.info(f"🏭 Creating request-scoped AdminToolDispatcher for admin user {admin_user.id}")
        
        # Early validation of admin permissions
        if not PermissionService.is_developer_or_higher(admin_user):
            raise PermissionError(f"User {admin_user.id} lacks admin permissions for AdminToolDispatcher")
        
        # Validate and enhance user context for admin operations
        validated_context = validate_user_context(user_context)
        admin_context = validated_context.create_child_context(
            operation_name="admin_tool_dispatch",
            additional_metadata={
                'admin_user_id': admin_user.id,
                'admin_permissions': PermissionService.get_user_permissions(admin_user),
                'operation_type': 'admin_dispatch',
                'db_session_available': db_session is not None
            }
        )
        
        # Create WebSocket emitter if manager provided
        websocket_emitter = None
        if websocket_manager:
            try:
                websocket_emitter = await WebSocketEventEmitterFactory.create_emitter(
                    admin_context, websocket_manager
                )
                logger.debug(f"✅ WebSocket emitter created for admin context {admin_context.get_correlation_id()}")
            except Exception as e:
                logger.error(f"Failed to create WebSocket emitter for admin dispatcher: {e}")
                # Continue without WebSocket support rather than failing completely
        
        # Create modernized admin dispatcher with full request-scoped support
        try:
            dispatcher = ModernizedAdminToolDispatcher(
                user_context=admin_context,
                admin_user=admin_user,
                db_session=db_session,
                tools=tools or [],
                websocket_manager=websocket_manager,
                llm_manager=llm_manager
            )
            
            logger.info(f"✅ Created request-scoped AdminToolDispatcher for admin {admin_user.id} "
                       f"in context {admin_context.get_correlation_id()}")
            
            return dispatcher
            
        except Exception as e:
            logger.error(f"Failed to create AdminToolDispatcher for admin user {admin_user.id}: {e}")
            raise
    
    @staticmethod
    @asynccontextmanager
    async def create_admin_context(
        user_context: UserExecutionContext,
        admin_user: User,
        db_session: AsyncSession,
        tools: List[BaseTool] = None,
        websocket_manager: Optional['WebSocketManager'] = None
    ):
        """Create admin dispatcher context manager with automatic cleanup.
        
        This is the RECOMMENDED pattern for short-lived admin operations.
        Automatically handles cleanup and resource management.
        
        Args:
            user_context: UserExecutionContext for complete request isolation
            admin_user: User performing admin operations (must have admin permissions)
            db_session: Database session for admin operations
            tools: Optional list of tools to register initially
            websocket_manager: Optional WebSocket manager for event routing
            
        Yields:
            AdminToolDispatcher: Scoped admin dispatcher with automatic cleanup
            
        Example:
            async with AdminToolDispatcherFactory.create_admin_context(
                user_context, admin_user, db_session, websocket_manager=ws_manager
            ) as admin_dispatcher:
                result = await admin_dispatcher.dispatch("admin_tool", param="value")
                # Automatic cleanup happens here
        """
        dispatcher = None
        try:
            dispatcher = await AdminToolDispatcherFactory.create_admin_dispatcher(
                user_context, admin_user, db_session, tools, websocket_manager
            )
            
            correlation_id = getattr(dispatcher, '_admin_context', user_context).get_correlation_id()
            logger.debug(f"📦 ADMIN CONTEXT: {correlation_id} created with auto-cleanup")
            
            yield dispatcher
            
        except Exception as e:
            logger.error(f"Admin dispatcher context creation failed: {e}")
            raise
            
        finally:
            if dispatcher and hasattr(dispatcher, 'cleanup'):
                try:
                    await dispatcher.cleanup()
                    correlation_id = getattr(dispatcher, '_admin_context', user_context).get_correlation_id()
                    logger.debug(f"📦 ADMIN CONTEXT: {correlation_id} disposed")
                except Exception as e:
                    logger.error(f"Admin dispatcher cleanup failed: {e}")
    
    @staticmethod
    def create_legacy_admin_dispatcher(
        admin_user: User,
        db_session: AsyncSession,
        tools: List[BaseTool] = None,
        llm_manager = None,
        websocket_manager = None
    ) -> AdminToolDispatcher:
        """Create legacy admin dispatcher (DEPRECATED).
        
        WARNING: This creates a global admin dispatcher that may cause user isolation issues.
        Use create_admin_dispatcher() with UserExecutionContext for new code.
        
        Args:
            admin_user: User performing admin operations
            db_session: Database session for admin operations
            tools: Optional list of tools to register initially
            llm_manager: Optional LLM manager
            websocket_manager: Optional WebSocket manager
            
        Returns:
            AdminToolDispatcher: Global admin dispatcher (DEPRECATED)
        """
        import warnings
        warnings.warn(
            "create_legacy_admin_dispatcher() creates global state that may cause user isolation issues. "
            "Use create_admin_dispatcher() with UserExecutionContext for proper isolation.",
            DeprecationWarning,
            stacklevel=2
        )
        
        logger.warning(f"⚠️ Creating LEGACY AdminToolDispatcher for admin {admin_user.id}")
        logger.warning("⚠️ This may cause user isolation issues in concurrent scenarios")
        
        # Create with current constructor
        dispatcher = AdminToolDispatcher(
            llm_manager=llm_manager,
            tool_dispatcher=None,
            tools=tools or [],
            db=db_session,
            user=admin_user,
            websocket_manager=websocket_manager
        )
        
        # Mark as legacy for monitoring
        dispatcher._is_legacy_global = True
        dispatcher._is_request_scoped = False
        
        return dispatcher


# Convenience functions for common usage patterns
async def create_request_scoped_admin_dispatcher(
    user_context: UserExecutionContext,
    admin_user: User,
    db_session: AsyncSession,
    tools: List[BaseTool] = None,
    websocket_manager: Optional['WebSocketManager'] = None
) -> AdminToolDispatcher:
    """Convenience function to create request-scoped admin dispatcher."""
    return await AdminToolDispatcherFactory.create_admin_dispatcher(
        user_context, admin_user, db_session, tools, websocket_manager
    )


@asynccontextmanager
async def admin_dispatcher_context(
    user_context: UserExecutionContext,
    admin_user: User,
    db_session: AsyncSession,
    websocket_manager: Optional['WebSocketManager'] = None
):
    """Convenience context manager for scoped admin dispatcher."""
    async with AdminToolDispatcherFactory.create_admin_context(
        user_context, admin_user, db_session, None, websocket_manager
    ) as dispatcher:
        yield dispatcher


def create_legacy_admin_dispatcher(
    admin_user: User,
    db_session: AsyncSession,
    tools: List[BaseTool] = None,
    llm_manager = None,
    websocket_manager = None
) -> AdminToolDispatcher:
    """Convenience function to create legacy admin dispatcher (DEPRECATED)."""
    return AdminToolDispatcherFactory.create_legacy_admin_dispatcher(
        admin_user, db_session, tools, llm_manager, websocket_manager
    )


# Export all public interfaces
__all__ = [
    'AdminToolDispatcherFactory',
    'create_request_scoped_admin_dispatcher',
    'admin_dispatcher_context',
    'create_legacy_admin_dispatcher'
]