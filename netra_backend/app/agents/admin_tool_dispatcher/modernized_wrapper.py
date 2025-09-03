"""
AdminToolDispatcher Modernized Wrapper

This wrapper provides the modern request-scoped interface over the existing
AdminToolDispatcher while maintaining backward compatibility during migration.

Business Value: Smooth migration path with immediate user isolation benefits.
"""

import asyncio
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from datetime import datetime, timezone

if TYPE_CHECKING:
    from netra_backend.app.websocket_core.manager import WebSocketManager

from langchain_core.tools import BaseTool
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.agents.admin_tool_dispatcher.dispatcher_core import AdminToolDispatcher
from netra_backend.app.agents.supervisor.user_execution_context import (
    UserExecutionContext,
    validate_user_context
)
from netra_backend.app.db.models_postgres import User
from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.permission_service import PermissionService

logger = central_logger.get_logger(__name__)


class ModernizedAdminToolDispatcher:
    """Modernized wrapper for AdminToolDispatcher with request-scoped user isolation.
    
    This wrapper provides the modern request-scoped interface while maintaining
    compatibility with the existing AdminToolDispatcher implementation.
    
    Key Features:
    - Complete UserExecutionContext integration
    - Per-request user isolation 
    - WebSocket event routing
    - Backward compatibility with existing AdminToolDispatcher API
    - Enhanced error handling and logging
    """
    
    def __init__(
        self,
        user_context: UserExecutionContext,
        admin_user: User,
        db_session: AsyncSession,
        tools: List[BaseTool] = None,
        websocket_manager: Optional['WebSocketManager'] = None,
        llm_manager = None
    ):
        """Initialize modernized admin tool dispatcher.
        
        Args:
            user_context: UserExecutionContext for complete request isolation (REQUIRED)
            admin_user: User performing admin operations (must have admin permissions) 
            db_session: Database session for admin operations (REQUIRED)
            tools: Optional list of tools to register initially
            websocket_manager: Optional WebSocket manager for event routing
            llm_manager: Optional LLM manager (legacy compatibility)
            
        Raises:
            PermissionError: If admin_user lacks admin permissions
            ValueError: If required parameters are missing
        """
        # Validate inputs
        if not admin_user:
            raise ValueError("admin_user is required")
        if not db_session:
            raise ValueError("db_session is required")
            
        # Validate admin permissions early
        if not PermissionService.is_developer_or_higher(admin_user):
            raise PermissionError(f"User {admin_user.id} lacks admin permissions")
        
        # Validate and enhance user context
        self.user_context = validate_user_context(user_context)
        self.admin_context = self.user_context.create_child_context(
            operation_name="modernized_admin_dispatch",
            additional_metadata={
                'admin_user_id': admin_user.id,
                'admin_permissions': PermissionService.get_user_permissions(admin_user),
                'modernized_wrapper': True,
                'operation_type': 'admin_dispatch_modernized'
            }
        )
        
        # Store admin-specific data
        self.admin_user = admin_user
        self.db_session = db_session
        self.websocket_manager = websocket_manager
        self.llm_manager = llm_manager
        
        # Create underlying AdminToolDispatcher with legacy constructor
        self._create_underlying_dispatcher(tools)
        
        # Track modern usage
        self._is_request_scoped = True
        self._created_at = datetime.now(timezone.utc)
        self._dispatch_count = 0
        
        logger.info(f"🔧✨ Created ModernizedAdminToolDispatcher for admin {admin_user.id} "
                   f"in context {self.admin_context.get_correlation_id()}")
    
    def _create_underlying_dispatcher(self, tools: List[BaseTool]) -> None:
        """Create the underlying AdminToolDispatcher with legacy constructor."""
        try:
            # Create with existing constructor signature
            self._underlying_dispatcher = AdminToolDispatcher(
                llm_manager=self.llm_manager,
                tool_dispatcher=None,  # Self-reference pattern
                tools=tools or [],
                db=self.db_session,
                user=self.admin_user,
                websocket_manager=self.websocket_manager
            )
            
            # Enhance with modern context attributes
            self._underlying_dispatcher._admin_context = self.admin_context
            self._underlying_dispatcher._is_request_scoped = True
            self._underlying_dispatcher._modernized_wrapper = True
            
            # Try to set user_context if the underlying dispatcher supports it
            if hasattr(self._underlying_dispatcher, 'user_context'):
                try:
                    object.__setattr__(self._underlying_dispatcher, 'user_context', self.admin_context)
                    logger.debug(f"✅ Enhanced underlying dispatcher with admin context")
                except Exception as e:
                    logger.warning(f"Could not set user_context on underlying dispatcher: {e}")
            
            logger.debug(f"✅ Created underlying AdminToolDispatcher with modernization enhancements")
            
        except Exception as e:
            logger.error(f"Failed to create underlying AdminToolDispatcher: {e}")
            raise
    
    # Delegate all AdminToolDispatcher methods to the underlying instance
    async def dispatch(self, tool_name: str, **kwargs) -> Any:
        """Dispatch admin tool with request-scoped context tracking."""
        self._dispatch_count += 1
        
        logger.debug(f"🔧 ModernizedAdminToolDispatcher dispatching {tool_name} "
                    f"(count: {self._dispatch_count}) in context {self.admin_context.get_correlation_id()}")
        
        try:
            result = await self._underlying_dispatcher.dispatch(tool_name, **kwargs)
            logger.debug(f"✅ Admin tool {tool_name} completed successfully")
            return result
        except Exception as e:
            logger.error(f"🚨 Admin tool {tool_name} failed: {e}")
            raise
    
    def has_admin_access(self) -> bool:
        """Check if current user has admin access."""
        return self._underlying_dispatcher.has_admin_access()
    
    def list_all_tools(self) -> List[Any]:
        """List all available admin tools."""
        return self._underlying_dispatcher.list_all_tools()
    
    def get_tool_info(self, tool_name: str) -> Any:
        """Get information about a specific admin tool."""
        return self._underlying_dispatcher.get_tool_info(tool_name)
    
    def get_dispatcher_stats(self) -> Dict[str, Any]:
        """Get comprehensive dispatcher statistics."""
        stats = self._underlying_dispatcher.get_dispatcher_stats()
        
        # Enhance with modernization info
        stats.update({
            'modernized_wrapper': True,
            'request_scoped': self._is_request_scoped,
            'admin_context_id': self.admin_context.get_correlation_id(),
            'admin_user_id': self.admin_user.id,
            'dispatch_count': self._dispatch_count,
            'created_at': self._created_at.isoformat(),
            'user_isolation': 'COMPLETE'
        })
        
        return stats
    
    async def dispatch_admin_operation(self, operation: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch admin operation with context tracking."""
        return await self._underlying_dispatcher.dispatch_admin_operation(operation)
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status including modernization information."""
        health = self._underlying_dispatcher.get_health_status()
        
        # Add modernization health info
        health.update({
            'modernization_status': 'COMPLETE',
            'user_isolation_status': 'ACTIVE',
            'request_scoped_pattern': 'ENABLED',
            'admin_context_healthy': bool(self.admin_context),
            'admin_permissions_validated': PermissionService.is_developer_or_higher(self.admin_user)
        })
        
        return health
    
    async def cleanup(self) -> None:
        """Clean up modernized dispatcher resources."""
        logger.info(f"🧹 Cleaning up ModernizedAdminToolDispatcher for admin {self.admin_user.id}")
        
        try:
            # Cleanup underlying dispatcher if it supports it
            if hasattr(self._underlying_dispatcher, 'cleanup'):
                await self._underlying_dispatcher.cleanup()
            
            # Clear references
            self._underlying_dispatcher = None
            
            logger.info(f"✅ ModernizedAdminToolDispatcher cleanup complete")
        except Exception as e:
            logger.error(f"Error during ModernizedAdminToolDispatcher cleanup: {e}")
            raise
    
    # Context manager support
    async def __aenter__(self) -> 'ModernizedAdminToolDispatcher':
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit with cleanup."""
        await self.cleanup()
    
    # Backward compatibility properties
    @property
    def user(self) -> User:
        """Get admin user for backward compatibility."""
        return self.admin_user
    
    @property 
    def db(self) -> AsyncSession:
        """Get database session for backward compatibility."""
        return self.db_session
    
    @property
    def tool_dispatcher(self) -> 'ModernizedAdminToolDispatcher':
        """Get self reference for backward compatibility."""
        return self
    
    # Modern interface properties
    @property
    def correlation_id(self) -> str:
        """Get correlation ID for logging and tracing."""
        return self.admin_context.get_correlation_id()
    
    @property
    def is_request_scoped(self) -> bool:
        """Check if dispatcher is using request-scoped pattern."""
        return self._is_request_scoped
    
    def __str__(self) -> str:
        return f"ModernizedAdminToolDispatcher(admin={self.admin_user.id}, context={self.correlation_id})"
    
    def __repr__(self) -> str:
        return (f"ModernizedAdminToolDispatcher(admin_user_id={self.admin_user.id}, "
                f"context={self.correlation_id}, dispatches={self._dispatch_count})")