"""
SSOT Service Initializer - Follows Phase 5 patterns from smd.py

This module provides SSOT service initialization that replicates the exact
patterns used in the deterministic startup sequence (smd.py Phase 5).

CRITICAL: This eliminates fallback handler creation by providing authentic
service initialization using the same patterns as system startup.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from fastapi import FastAPI

from netra_backend.app.logging_config import central_logger


class SSOTServiceInitializationError(Exception):
    """Raised when SSOT service initialization fails."""
    pass


async def initialize_service_ssot(app: FastAPI, service_name: str) -> bool:
    """
    Initialize a single service using SSOT patterns from smd.py Phase 5.
    
    This function replicates the exact initialization patterns used in
    the deterministic startup sequence to ensure consistency.
    
    Args:
        app: FastAPI application instance
        service_name: Name of the service to initialize
        
    Returns:
        True if successful, False otherwise
    """
    logger = central_logger.get_logger(__name__)
    logger.info(f" CYCLE:  Starting SSOT initialization for service: {service_name}")
    
    try:
        if service_name == 'agent_supervisor':
            success = await _initialize_agent_supervisor_ssot(app, logger)
        elif service_name == 'thread_service':
            success = await _initialize_thread_service_ssot(app, logger)
        elif service_name == 'agent_websocket_bridge':
            success = await _initialize_agent_websocket_bridge_ssot(app, logger)
        elif service_name == 'tool_classes':
            success = await _initialize_tool_classes_ssot(app, logger)
        else:
            logger.warning(f" WARNING: [U+FE0F] Unknown service for SSOT initialization: {service_name}")
            return False
        
        if success:
            logger.info(f" PASS:  SSOT initialization successful for: {service_name}")
        else:
            logger.error(f" FAIL:  SSOT initialization failed for: {service_name}")
            
        return success
        
    except Exception as e:
        logger.error(f" FAIL:  SSOT initialization exception for {service_name}: {e}", exc_info=True)
        return False


async def _initialize_agent_websocket_bridge_ssot(app: FastAPI, logger: logging.Logger) -> bool:
    """
    Initialize AgentWebSocketBridge using SSOT patterns from smd.py.
    
    Replicates _initialize_agent_websocket_bridge_basic() from Phase 5.
    """
    try:
        # Check if already initialized
        if (hasattr(app.state, 'agent_websocket_bridge') and 
            app.state.agent_websocket_bridge is not None):
            logger.info("[U+2713] AgentWebSocketBridge already initialized")
            return True
        
        logger.info("Initializing AgentWebSocketBridge using SSOT patterns...")
        
        from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
        
        # Create bridge instance (non-singleton) - proper user isolation pattern
        logger.info("  Creating AgentWebSocketBridge instance...")
        bridge = AgentWebSocketBridge()
        if bridge is None:
            logger.error("   FAIL:  AgentWebSocketBridge() returned None")
            raise SSOTServiceInitializationError("Failed to create AgentWebSocketBridge instance")
        
        # Store bridge in app state for later integration
        app.state.agent_websocket_bridge = bridge
        
        # Verify the bridge has required methods for validation
        required_methods = ['notify_agent_started', 'notify_agent_completed', 'notify_tool_executing']
        missing_methods = [m for m in required_methods if not hasattr(bridge, m)]
        if missing_methods:
            logger.error(f"   FAIL:  AgentWebSocketBridge missing methods: {missing_methods}")
            raise SSOTServiceInitializationError(f"AgentWebSocketBridge missing required methods: {missing_methods}")
        
        logger.info("[U+2713] AgentWebSocketBridge instance created with all required methods")
        return True
        
    except Exception as e:
        logger.error(f" FAIL:  Failed to initialize AgentWebSocketBridge: {e}")
        raise SSOTServiceInitializationError(f"Critical failure in AgentWebSocketBridge initialization: {e}") from e


async def _initialize_tool_classes_ssot(app: FastAPI, logger: logging.Logger) -> bool:
    """
    Initialize tool_classes using SSOT patterns from smd.py.
    
    Replicates _initialize_tool_registry() tool classes configuration from Phase 5.
    """
    try:
        # Check if already initialized
        if (hasattr(app.state, 'tool_classes') and 
            app.state.tool_classes is not None and
            len(app.state.tool_classes) > 0):
            logger.info("[U+2713] Tool classes already initialized")
            return True
        
        logger.info("Initializing tool classes using SSOT patterns...")
        
        # Import required tool classes
        from netra_backend.app.agents.tools.langchain_wrappers import (
            DataHelperTool, DeepResearchTool, ReliabilityScorerTool, SandboxedInterpreterTool
        )
        
        # CRITICAL FIX: WebSocket bridge MUST exist before tool initialization
        if not hasattr(app.state, 'agent_websocket_bridge') or app.state.agent_websocket_bridge is None:
            logger.error(" FAIL:  AgentWebSocketBridge not available for tool dispatcher initialization")
            # Try to initialize it first
            bridge_success = await _initialize_agent_websocket_bridge_ssot(app, logger)
            if not bridge_success:
                raise SSOTServiceInitializationError(
                    "AgentWebSocketBridge not available for tool dispatcher initialization. "
                    "Bridge must be created before tool dispatcher to prevent notification failures."
                )
        
        websocket_bridge = app.state.agent_websocket_bridge
        logger.info("  Using AgentWebSocketBridge for tool dispatcher")
        
        # Define available tools for user registry creation (not instantiated globally)
        available_tool_classes = [
            DataHelperTool,
            DeepResearchTool, 
            ReliabilityScorerTool,
            SandboxedInterpreterTool
        ]
        
        logger.info(f"  Configured {len(available_tool_classes)} tool classes for per-user registry creation")
        
        # Store tool factory configuration (NOT instances) for UserContext-based creation
        app.state.tool_classes = available_tool_classes
        
        # NO MORE GLOBAL TOOL DISPATCHER OR REGISTRY
        # These will be created per-user via UserExecutionContext
        app.state.tool_dispatcher = None  # Signals: use UserContext-based creation
        app.state.tool_registry = None   # Signals: use UserContext-based creation
        
        logger.info("  Configured UserContext-based tool system (no global singletons)")
        
        # Validate UserContext-based configuration
        if not hasattr(app.state, 'tool_classes') or not app.state.tool_classes:
            raise SSOTServiceInitializationError(
                "Tool classes configuration missing - "
                "cannot create UserContext-based tool dispatchers"
            )
        
        logger.info("[U+2713] UserContext-based tool system validated and ready")
        return True
        
    except Exception as e:
        logger.error(f" FAIL:  Failed to initialize tool classes: {e}")
        raise SSOTServiceInitializationError(f"Critical failure in tool classes initialization: {e}") from e


async def _initialize_agent_supervisor_ssot(app: FastAPI, logger: logging.Logger) -> bool:
    """
    Initialize agent_supervisor using SSOT patterns from smd.py.
    
    Replicates _initialize_agent_supervisor() from Phase 5.
    """
    try:
        # Check if already initialized
        if (hasattr(app.state, 'agent_supervisor') and 
            app.state.agent_supervisor is not None):
            logger.info("[U+2713] Agent supervisor already initialized")
            # Also ensure thread_service is initialized
            if not hasattr(app.state, 'thread_service') or app.state.thread_service is None:
                logger.info("  Initializing thread_service as part of supervisor initialization...")
                thread_success = await _initialize_thread_service_ssot(app, logger)
                if not thread_success:
                    return False
            return True
        
        logger.info("Initializing agent supervisor using SSOT patterns...")
        
        from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
        from netra_backend.app.services.agent_service import AgentService
        from netra_backend.app.services.thread_service import ThreadService
        from netra_backend.app.services.corpus_service import CorpusService
        from netra_backend.app.core.agent_execution_tracker import initialize_tracker
        
        # Initialize execution tracker for death detection - CRITICAL
        logger.info("  Initializing agent execution tracker for death detection...")
        try:
            execution_tracker = await initialize_tracker()
            app.state.execution_tracker = execution_tracker
            logger.info("    [U+2713] Agent execution tracker initialized")
        except Exception as e:
            raise SSOTServiceInitializationError(f"Failed to initialize execution tracker: {e}")
        
        # Ensure required dependencies exist
        required_deps = ['llm_manager', 'agent_websocket_bridge']
        missing_deps = []
        for dep in required_deps:
            if not hasattr(app.state, dep) or getattr(app.state, dep) is None:
                missing_deps.append(dep)
        
        if missing_deps:
            logger.error(f" FAIL:  Missing required dependencies for agent supervisor: {missing_deps}")
            # Try to initialize agent_websocket_bridge if missing
            if 'agent_websocket_bridge' in missing_deps:
                logger.info("  Attempting to initialize missing agent_websocket_bridge...")
                bridge_success = await _initialize_agent_websocket_bridge_ssot(app, logger)
                if not bridge_success:
                    raise SSOTServiceInitializationError(f"Failed to initialize required dependency: agent_websocket_bridge")
                missing_deps.remove('agent_websocket_bridge')
            
            # If still missing deps, fail
            if missing_deps:
                raise SSOTServiceInitializationError(f"Missing required dependencies: {missing_deps}")
        
        # Get AgentWebSocketBridge - CRITICAL for agent notifications
        agent_websocket_bridge = app.state.agent_websocket_bridge
        if not agent_websocket_bridge:
            raise SSOTServiceInitializationError("AgentWebSocketBridge not available for supervisor initialization")
        
        # Create supervisor with bridge for proper WebSocket integration
        # Note: SupervisorAgent uses UserExecutionContext pattern - no database sessions in constructor
        # SupervisorAgent expects 2 args: llm_manager and websocket_bridge (no tool_dispatcher)
        supervisor = SupervisorAgent(
            app.state.llm_manager,
            agent_websocket_bridge
        )
        
        if supervisor is None:
            raise SSOTServiceInitializationError("Supervisor creation returned None")
        
        # Set state - NEVER set to None
        app.state.agent_supervisor = supervisor
        app.state.agent_service = AgentService(supervisor)
        app.state.thread_service = ThreadService()
        # NOTE: CorpusService now requires user context for WebSocket notifications
        # This will be created per-request with user context instead of singleton
        app.state.corpus_service = CorpusService()  # Default without user context for backward compatibility
        
        # CRITICAL VALIDATION: Ensure services are never None
        critical_services = [
            ('agent_supervisor', app.state.agent_supervisor),
            ('agent_service', app.state.agent_service),
            ('thread_service', app.state.thread_service),
            ('corpus_service', app.state.corpus_service)
        ]
        
        for service_name, service_instance in critical_services:
            if service_instance is None:
                raise SSOTServiceInitializationError(
                    f"CRITICAL: {service_name} is None after initialization. "
                    f"This violates deterministic startup requirements."
                )
        
        logger.info("  [U+2713] All critical services validated as non-None")
        logger.info("[U+2713] Agent supervisor initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f" FAIL:  Failed to initialize agent supervisor: {e}")
        raise SSOTServiceInitializationError(f"Critical failure in agent supervisor initialization: {e}") from e


async def _initialize_thread_service_ssot(app: FastAPI, logger: logging.Logger) -> bool:
    """
    Initialize thread_service using SSOT patterns from smd.py.
    
    Thread service is normally initialized as part of agent supervisor initialization.
    """
    try:
        # Check if already initialized
        if (hasattr(app.state, 'thread_service') and 
            app.state.thread_service is not None):
            logger.info("[U+2713] Thread service already initialized")
            return True
        
        logger.info("Initializing thread service using SSOT patterns...")
        
        from netra_backend.app.services.thread_service import ThreadService
        
        # Create thread service
        app.state.thread_service = ThreadService()
        
        # Validate initialization
        if app.state.thread_service is None:
            raise SSOTServiceInitializationError("Thread service creation returned None")
        
        logger.info("[U+2713] Thread service initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f" FAIL:  Failed to initialize thread service: {e}")
        raise SSOTServiceInitializationError(f"Critical failure in thread service initialization: {e}") from e


async def initialize_missing_services_ssot(
    app: FastAPI,
    missing_services: List[str],
    max_wait_time: float = 30.0
) -> Dict[str, Any]:
    """
    Initialize multiple missing services using SSOT patterns.
    
    This is the main entry point for SSOT service initialization that eliminates
    the need for fallback handlers.
    
    Args:
        app: FastAPI application instance
        missing_services: List of service names to initialize
        max_wait_time: Maximum time to wait for initialization
        
    Returns:
        Dictionary with initialization results
    """
    logger = central_logger.get_logger(__name__)
    logger.info(f" CYCLE:  Starting SSOT initialization for services: {missing_services}")
    
    results = {
        'success': True,
        'services_initialized': [],
        'services_failed': [],
        'errors': [],
        'total_time': 0.0
    }
    
    start_time = asyncio.get_event_loop().time()
    
    try:
        for service_name in missing_services:
            try:
                logger.info(f" CYCLE:  Initializing service: {service_name}")
                success = await initialize_service_ssot(app, service_name)
                
                if success:
                    results['services_initialized'].append(service_name)
                    logger.info(f" PASS:  Service '{service_name}' initialized successfully")
                else:
                    results['services_failed'].append(service_name)
                    results['errors'].append(f"Service '{service_name}' initialization returned False")
                    logger.error(f" FAIL:  Service '{service_name}' initialization failed")
                    
            except Exception as e:
                results['services_failed'].append(service_name)
                error_msg = f"Service '{service_name}' initialization exception: {e}"
                results['errors'].append(error_msg)
                logger.error(f" FAIL:  {error_msg}", exc_info=True)
        
        # Calculate total time
        results['total_time'] = asyncio.get_event_loop().time() - start_time
        
        # Determine overall success
        results['success'] = len(results['services_failed']) == 0
        
        if results['success']:
            logger.info(f" PASS:  All services initialized successfully in {results['total_time']:.2f}s")
        else:
            logger.error(f" FAIL:  Some services failed initialization: {results['services_failed']}")
        
        return results
        
    except Exception as e:
        results['total_time'] = asyncio.get_event_loop().time() - start_time
        results['success'] = False
        error_msg = f"SSOT service initialization critical failure: {e}"
        results['errors'].append(error_msg)
        logger.error(f" ALERT:  {error_msg}", exc_info=True)
        return results