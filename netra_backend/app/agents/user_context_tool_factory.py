"""UserContext-Based Tool Registry Factory

This module provides factory functions to create completely isolated tool registries
and dispatchers for each UserExecutionContext, eliminating global state and ensuring
proper user isolation.

ARCHITECTURAL PRINCIPLE: No Global Singletons
- Each user gets their own tool registry
- Each user gets their own tool dispatcher  
- Each user gets their own WebSocket bridge
- Zero shared state between users
"""

import time
from typing import List, Type, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext
    from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge

from netra_backend.app.core.registry.universal_registry import ToolRegistry
from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcherFactory
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class UserContextToolFactory:
    """Factory for creating per-user isolated tool systems.
    
    This factory eliminates global state by creating separate tool registries,
    dispatchers, and WebSocket bridges for each UserExecutionContext.
    
    Key Benefits:
    1. Complete user isolation - no shared state
    2. No global singletons - everything per-request
    3. Proper cleanup - resources tied to request lifecycle
    4. Security - users cannot access other users' tools
    """
    
    @staticmethod
    async def create_user_tool_system(
        context: 'UserExecutionContext',
        tool_classes: List[Type],
        websocket_bridge_factory = None
    ) -> dict:
        """Create complete isolated tool system for a user.
        
        Args:
            context: UserExecutionContext for complete isolation
            tool_classes: List of tool classes to instantiate for this user
            websocket_bridge_factory: Factory function for creating WebSocket bridge
            
        Returns:
            dict: {
                'registry': ToolRegistry,
                'dispatcher': UnifiedToolDispatcher, 
                'tools': List[BaseTool],
                'bridge': AgentWebSocketBridge
            }
        """
        correlation_id = context.get_correlation_id()
        logger.info(f"🏭 Creating isolated tool system for {correlation_id}")
        
        # Create user-specific registry ID
        registry_id = f"user_{context.user_id}_{context.run_id}_{int(time.time()*1000)}"
        
        # Create isolated tool registry for this user
        registry = ToolRegistry()
        logger.info(f"🗃️ Created isolated registry {registry_id} for {correlation_id}")
        
        # Create isolated tool instances for this user
        user_tools = []
        for tool_class in tool_classes:
            try:
                tool_instance = tool_class()
                user_tools.append(tool_instance)
                logger.debug(f"✅ Created tool {tool_class.__name__} for {correlation_id}")
            except Exception as e:
                logger.error(f"❌ Failed to create tool {tool_class.__name__} for {correlation_id}: {e}")
                # Continue with other tools - partial tool availability is better than total failure
                
        logger.info(f"🔧 Created {len(user_tools)} isolated tools for {correlation_id}")
        
        # Create isolated WebSocket bridge for this user
        bridge = None
        if websocket_bridge_factory:
            try:
                bridge = websocket_bridge_factory()
                logger.info(f"🌐 Created isolated WebSocket bridge for {correlation_id}")
            except Exception as e:
                logger.error(f"❌ Failed to create WebSocket bridge for {correlation_id}: {e}")
        
        # Create isolated tool dispatcher for this user using factory
        dispatcher = await UnifiedToolDispatcherFactory.create_request_scoped(
            user_context=context,
            tools=user_tools,
            websocket_manager=None,  # We use bridge instead
            permission_service=None
        )
        
        # Override dispatcher registry with our pre-created registry to prevent duplication
        dispatcher.registry = registry
        
        # Register tools in the isolated registry
        registry.register_tools(user_tools)
        
        logger.info(f"🚀 Completed isolated tool system for {correlation_id}")
        logger.info(f"   - Registry: {registry_id} ({len(user_tools)} tools)")  
        logger.info(f"   - Dispatcher: {dispatcher.dispatcher_id}")
        logger.info(f"   - Bridge: {'✓ Available' if bridge else '✗ None'}")
        
        return {
            'registry': registry,
            'dispatcher': dispatcher,
            'tools': user_tools,
            'bridge': bridge,
            'correlation_id': correlation_id
        }
    
    @staticmethod
    async def create_minimal_tool_system(
        context: 'UserExecutionContext'
    ) -> dict:
        """Create minimal tool system with basic tools only.
        
        Used for lightweight operations or fallback scenarios.
        """
        from netra_backend.app.agents.tools.data_helper_tool import DataHelperTool
        
        basic_tools = [DataHelperTool]
        
        return await UserContextToolFactory.create_user_tool_system(
            context=context,
            tool_classes=basic_tools,
            websocket_bridge_factory=None
        )
    
    @staticmethod
    def validate_tool_system(tool_system: dict) -> bool:
        """Validate that tool system has all required components.
        
        Args:
            tool_system: Result from create_user_tool_system()
            
        Returns:
            bool: True if valid, False otherwise
        """
        required_keys = ['registry', 'dispatcher', 'tools', 'correlation_id']
        
        for key in required_keys:
            if key not in tool_system:
                logger.error(f"❌ Tool system missing required key: {key}")
                return False
                
        if not isinstance(tool_system['tools'], list):
            logger.error("❌ Tool system 'tools' must be a list")
            return False
            
        if len(tool_system['tools']) == 0:
            logger.warning("⚠️ Tool system has no tools - this may limit functionality")
            
        return True


def get_app_tool_classes():
    """Get available tool classes from app state.
    
    This function retrieves the tool classes configuration set during startup,
    enabling UserContext-based tool creation without global instances.
    
    Returns:
        List[Type]: Available tool classes for per-user instantiation
    """
    try:
        from fastapi import Request
        # This will work during request processing when app state is available
        # For startup/testing, this might not be available
        return []  # Fallback - implement request context lookup if needed
    except Exception:
        # Fallback to default tool classes
        from netra_backend.app.agents.tools.data_helper_tool import DataHelperTool
        from netra_backend.app.agents.tools.deep_research_tool import DeepResearchTool
        from netra_backend.app.agents.tools.reliability_scorer_tool import ReliabilityScorerTool
        from netra_backend.app.agents.tools.sandboxed_interpreter_tool import SandboxedInterpreterTool
        
        return [DataHelperTool, DeepResearchTool, ReliabilityScorerTool, SandboxedInterpreterTool]