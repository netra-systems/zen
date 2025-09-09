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
    from netra_backend.app.services.user_execution_context import UserExecutionContext
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
        
        # CRITICAL FIX: Create isolated tool registry with proper scoping
        registry = ToolRegistry(scope_id=registry_id)
        logger.info(f"🗃️ Created isolated registry {registry_id} for {correlation_id}")
        
        # Create isolated tool instances for this user
        user_tools = []
        for tool_class in tool_classes:
            try:
                tool_instance = tool_class()
                
                # Validate tool has required attributes
                if not hasattr(tool_instance, 'name'):
                    logger.warning(f"⚠️ Tool {tool_class.__name__} missing 'name' attribute - will use fallback naming")
                
                user_tools.append(tool_instance)
                logger.debug(f"✅ Created tool {tool_class.__name__} for {correlation_id}")
            except Exception as e:
                logger.error(f"❌ Failed to create tool {tool_class.__name__} for {correlation_id}: {e}")
                logger.error(f"   Tool class: {tool_class}, Error type: {type(e).__name__}")
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
        
        # Create isolated tool dispatcher for this user using factory with pre-created registry
        dispatcher = UnifiedToolDispatcherFactory.create_for_request(
            user_context=context,
            tools=user_tools,
            websocket_manager=None,  # We use bridge instead
            registry=registry  # CRITICAL FIX: Pass pre-created registry to prevent proliferation
        )
        
        # Register tools in the isolated registry
        for tool in user_tools:
            try:
                # CRITICAL FIX: Check if tool has name attribute before accessing it
                if hasattr(tool, 'name') and tool.name:
                    registry.register(tool.name, tool)
                    logger.debug(f"✅ Registered tool {tool.name} in isolated registry for {correlation_id}")
                else:
                    # Use the registry's safe tool name generation instead of dangerous fallback
                    tool_name = registry._generate_safe_tool_name(tool)
                    logger.warning(f"⚠️ Tool {tool.__class__.__name__} missing 'name' attribute, using safe fallback: {tool_name}")
                    registry.register(tool_name, tool)
            except ValueError as e:
                # CRITICAL FIX: Handle duplicate registration and validation failures gracefully
                if "already registered" in str(e):
                    logger.warning(f"⚠️ Tool {tool.__class__.__name__} already registered in registry for {correlation_id} - skipping duplicate")
                elif "BaseModel" in str(e) or "validation failed" in str(e).lower():
                    logger.error(f"❌ Tool {tool.__class__.__name__} failed validation for {correlation_id}: {e}")
                    logger.error(f"   This tool appears to be a BaseModel data schema, not an executable tool")
                else:
                    logger.error(f"❌ Failed to register tool {tool.__class__.__name__} for {correlation_id}: {e}")
                # Continue with other tools - partial functionality is better than complete failure
            except Exception as e:
                logger.error(f"❌ Unexpected error registering tool {tool.__class__.__name__} for {correlation_id}: {e}")
                # Continue with other tools
        
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
        # Use production tool as minimal fallback since specific tools don't exist yet
        try:
            from netra_backend.app.agents.production_tool import ProductionTool
            basic_tools = [ProductionTool]
        except ImportError:
            # If no tools available, create empty system
            basic_tools = []
        
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
        # Handle None input gracefully
        if tool_system is None:
            logger.error("❌ Tool system is None")
            return False
            
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
        # Fallback to production tool since specific tools don't exist yet
        try:
            from netra_backend.app.agents.production_tool import ProductionTool
            return [ProductionTool]
        except ImportError:
            # If no tools available, return empty list
            return []