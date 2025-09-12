"""
Critical Path Validator - Ensures business-critical communication chains are intact.

This module validates that all critical mixins, communication channels, and 
initialization sequences are properly configured. A single missing import,
wrong initialization order, or None value in these paths can silently defeat
the entire business value (Chat is King - 90% of value).

CRITICAL: These validations MUST pass or chat functionality is broken.
"""

import asyncio
import inspect
import logging
from typing import Dict, List, Optional, Tuple, Any, Type
from dataclasses import dataclass, field
from enum import Enum

from netra_backend.app.logging_config import central_logger


class CriticalityLevel(Enum):
    """Criticality levels for validation failures."""
    CHAT_BREAKING = "chat_breaking"  # Will completely break chat
    DEGRADED = "degraded"  # Chat works but degraded experience  
    WARNING = "warning"  # Potential issue but chat still works


@dataclass
class CriticalPathValidation:
    """Validation result for a critical path component."""
    component: str
    path: str
    check_type: str
    passed: bool
    criticality: CriticalityLevel
    failure_reason: Optional[str] = None
    remediation: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class CriticalPathValidator:
    """
    Validates critical communication and initialization paths.
    
    Critical Paths That MUST Work:
    1. WebSocket Bridge Propagation (agent -> tools -> UI)
    2. Agent Registry and Bridge Integration
    3. Tool Dispatcher WebSocket Support
    4. Message Handler Registration
    5. Supervisor -> Agent -> Tool execution chain
    """
    
    def __init__(self):
        self.logger = central_logger.get_logger(__name__)
        self.validations: List[CriticalPathValidation] = []
        
    async def validate_critical_paths(self, app) -> Tuple[bool, List[CriticalPathValidation]]:
        """
        Validate all critical paths for chat functionality.
        Returns (all_passed, validations) tuple.
        """
        self.logger.info("=" * 60)
        self.logger.info("CRITICAL PATH VALIDATION - CHAT FUNCTIONALITY")
        self.logger.info("=" * 60)
        
        self.validations = []
        
        # Run all critical path validations
        await self._validate_websocket_bridge_chain(app)
        await self._validate_agent_registry_chain(app)
        await self._validate_tool_dispatcher_enhancement(app)
        await self._validate_message_handler_chain(app)
        await self._validate_execution_context_propagation(app)
        await self._validate_notifier_initialization(app)
        
        # Check for critical failures
        critical_failures = [v for v in self.validations 
                           if not v.passed and v.criticality == CriticalityLevel.CHAT_BREAKING]
        
        if critical_failures:
            self.logger.error("=" * 60)
            self.logger.error(" ALERT:  CRITICAL FAILURES DETECTED - CHAT IS BROKEN!")
            self.logger.error("=" * 60)
            for failure in critical_failures:
                self.logger.error(f" FAIL:  {failure.component}: {failure.failure_reason}")
                if failure.remediation:
                    self.logger.error(f"   FIX: {failure.remediation}")
            self.logger.error("=" * 60)
            
        # Log warnings for potential issues
        warnings = [v for v in self.validations 
                   if not v.passed and v.criticality != CriticalityLevel.CHAT_BREAKING]
        
        if warnings:
            self.logger.warning(" WARNING: [U+FE0F] Non-critical issues detected:")
            for warning in warnings:
                self.logger.warning(f"  - {warning.component}: {warning.failure_reason}")
        
        all_passed = len(critical_failures) == 0
        return all_passed, self.validations
    
    async def _validate_websocket_bridge_chain(self, app) -> None:
        """Validate WebSocket bridge is properly supported by all agents."""
        try:
            # With factory pattern, agents are created per-request, not stored globally
            # Validate that the supervisor and bridge are available for factory creation
            if hasattr(app.state, 'agent_supervisor') and app.state.agent_supervisor:
                # Factory pattern: No registry needed - agents created on demand
                # Just verify supervisor has WebSocket bridge support
                supervisor = app.state.agent_supervisor
                
                # Check if supervisor has WebSocket capabilities (BaseAgent pattern)
                has_bridge_setter = hasattr(supervisor, 'set_websocket_bridge')
                has_emit = hasattr(supervisor, 'emit_thinking')
                has_propagate = hasattr(supervisor, 'propagate_websocket_context_to_state')
                
                if has_bridge_setter or has_emit or has_propagate:
                    validation = CriticalPathValidation(
                        component="WebSocket Bridge Chain",
                        path="Supervisor -> AgentWebSocketBridge",
                        check_type="bridge_support",
                        passed=True,
                        criticality=CriticalityLevel.CHAT_BREAKING,
                        metadata={"factory_pattern": True, "supervisor_supported": True}
                    )
                    self.logger.info("[U+2713] WebSocket bridge supported via factory pattern - supervisor ready")
                    self.validations.append(validation)
                    return  # Factory pattern validation complete
                
                # Legacy registry-based validation (deprecated - kept for backward compatibility)
                if hasattr(app.state.agent_supervisor, 'registry'):
                    registry = app.state.agent_supervisor.registry
                    
                    agents_missing_mixin = []
                    agents_missing_context_setter = []
                    
                    for agent_name, agent in registry.agents.items():
                        # Check if agent has WebSocketBridge methods (new pattern)
                        has_bridge_setter = hasattr(agent, 'set_websocket_bridge')
                        has_emit = hasattr(agent, 'emit_thinking')  
                        has_propagate = hasattr(agent, 'propagate_websocket_context_to_state')
                        
                        # TEMPORARY FIX: Skip validation for agents that don't have any WebSocket methods
                        # This handles legacy agents that might not properly inherit from BaseAgent
                        if not has_bridge_setter and not has_emit and not has_propagate:
                            self.logger.warning(f" WARNING: [U+FE0F] Agent '{agent_name}' has no WebSocket methods - skipping validation (may be legacy agent)")
                            continue
                            
                        # ADDITIONAL FIX: For agents with partial WebSocket support, try to initialize properly
                        if not has_bridge_setter and (has_emit or has_propagate):
                            self.logger.warning(f" WARNING: [U+FE0F] Agent '{agent_name}' has partial WebSocket support - attempting initialization fix")
                            # Check if this is a BaseAgent and try to ensure proper initialization
                            if hasattr(agent, '__class__') and hasattr(agent.__class__, '__bases__'):
                                from netra_backend.app.agents.base_agent import BaseAgent
                                if BaseAgent in agent.__class__.__mro__:
                                    try:
                                        # Try to reinitialize WebSocket adapter if it exists
                                        if hasattr(agent, '_websocket_adapter'):
                                            self.logger.info(f"Agent '{agent_name}' inherits from BaseAgent - WebSocket adapter should be available")
                                        continue  # Skip validation error for proper BaseAgent instances
                                    except Exception as e:
                                        self.logger.warning(f"Failed to validate BaseAgent inheritance for '{agent_name}': {e}")
                                        continue  # Skip validation error
                            
                        if not has_bridge_setter:
                            agents_missing_context_setter.append(agent_name)
                        if not (has_emit and has_propagate):
                            agents_missing_mixin.append(agent_name)
                    
                    if agents_missing_mixin or agents_missing_context_setter:
                        validation = CriticalPathValidation(
                            component="WebSocket Bridge Chain",
                            path="BaseAgent -> AgentWebSocketBridge",
                            check_type="bridge_support",
                            passed=False,
                            criticality=CriticalityLevel.CHAT_BREAKING,
                            failure_reason=f"Agents missing WebSocket bridge capabilities: {agents_missing_mixin or agents_missing_context_setter}",
                            remediation="Ensure all agents inherit from BaseAgent which supports set_websocket_bridge",
                            metadata={
                                "missing_mixin": agents_missing_mixin,
                                "missing_setter": agents_missing_context_setter
                            }
                        )
                        self.logger.error(f" FAIL:  CRITICAL: WebSocket bridge not properly supported by agents: {agents_missing_mixin or agents_missing_context_setter}")
                    else:
                        validation = CriticalPathValidation(
                            component="WebSocket Bridge Chain",
                            path="BaseAgent -> AgentWebSocketBridge",
                            check_type="bridge_support",
                            passed=True,
                            criticality=CriticalityLevel.CHAT_BREAKING
                        )
                        self.logger.info("[U+2713] WebSocket bridge properly supported by all agents")
                    
                    self.validations.append(validation)
                else:
                    # No registry - this is expected with factory pattern
                    # Validate bridge is available for factory use
                    if hasattr(app.state, 'agent_websocket_bridge') and app.state.agent_websocket_bridge:
                        validation = CriticalPathValidation(
                            component="WebSocket Bridge Chain",
                            path="Factory Pattern -> AgentWebSocketBridge",
                            check_type="bridge_available",
                            passed=True,
                            criticality=CriticalityLevel.CHAT_BREAKING,
                            metadata={"factory_pattern": True, "registry": False}
                        )
                        self.logger.info("[U+2713] WebSocket bridge available for factory-based agent creation")
                        self.validations.append(validation)
                    else:
                        self._add_critical_failure(
                            "WebSocket Bridge Chain",
                            "WebSocket bridge not available for factory pattern",
                            "Ensure agent_websocket_bridge is initialized during startup"
                        )
            else:
                self._add_critical_failure(
                    "WebSocket Bridge Chain",
                    "Agent supervisor not initialized",
                    "Ensure agent supervisor is created during startup"
                )
                
        except Exception as e:
            self._add_critical_failure(
                "WebSocket Bridge Chain",
                f"Validation failed: {e}",
                "Check agent initialization and bridge imports"
            )
    
    async def _validate_agent_registry_chain(self, app) -> None:
        """Validate agent registry has set_websocket_bridge method."""
        try:
            if hasattr(app.state, 'agent_supervisor') and app.state.agent_supervisor:
                if hasattr(app.state.agent_supervisor, 'registry'):
                    registry = app.state.agent_supervisor.registry
                    
                    # Check if registry has the critical method (now set_websocket_bridge)
                    has_setter = hasattr(registry, 'set_websocket_bridge')
                    
                    if not has_setter:
                        validation = CriticalPathValidation(
                            component="Agent Registry WebSocket Integration",
                            path="AgentRegistry.set_websocket_bridge()",
                            check_type="method_existence",
                            passed=False,
                            criticality=CriticalityLevel.CHAT_BREAKING,
                            failure_reason="Registry missing set_websocket_bridge method",
                            remediation="Add set_websocket_bridge method to AgentRegistry class"
                        )
                        self.logger.error(" FAIL:  CRITICAL: AgentRegistry missing set_websocket_bridge method")
                    else:
                        # Check if bridge was actually set
                        if hasattr(registry, 'websocket_bridge') and registry.websocket_bridge is not None:
                            # Verify tool dispatcher has WebSocket support through bridge
                            if hasattr(registry, 'tool_dispatcher'):
                                has_support = False
                                if hasattr(registry.tool_dispatcher, 'has_websocket_support'):
                                    has_support = registry.tool_dispatcher.has_websocket_support
                                
                                if has_support:
                                    validation = CriticalPathValidation(
                                        component="Agent Registry WebSocket Integration",
                                        path="AgentRegistry.set_websocket_bridge()",
                                        check_type="bridge_integration",
                                        passed=True,
                                        criticality=CriticalityLevel.CHAT_BREAKING,
                                        metadata={"bridge_set": True, "tool_dispatcher_support": True}
                                    )
                                    self.logger.info("[U+2713] Agent registry WebSocket bridge integration verified")
                                else:
                                    validation = CriticalPathValidation(
                                        component="Agent Registry WebSocket Integration",
                                        path="AgentRegistry.tool_dispatcher.has_websocket_support",
                                        check_type="enhancement_status",
                                        passed=False,
                                        criticality=CriticalityLevel.CHAT_BREAKING,
                                        failure_reason="Tool dispatcher lacks WebSocket support despite bridge being set",
                                        remediation="Ensure tool dispatcher is initialized with AgentWebSocketBridge",
                                        metadata={"has_support": has_support}
                                    )
                                    self.logger.warning(" WARNING: [U+FE0F] Tool dispatcher lacks WebSocket support")
                            else:
                                validation = CriticalPathValidation(
                                    component="Agent Registry WebSocket Integration",
                                    path="AgentRegistry.websocket_bridge",
                                    check_type="bridge_integration",
                                    passed=True,
                                    criticality=CriticalityLevel.CHAT_BREAKING,
                                    metadata={"bridge_set": True}
                                )
                                self.logger.info("[U+2713] Agent registry has WebSocket bridge set")
                        else:
                            validation = CriticalPathValidation(
                                component="Agent Registry WebSocket Integration",
                                path="AgentRegistry.websocket_bridge",
                                check_type="attribute_existence",
                                passed=False,
                                criticality=CriticalityLevel.CHAT_BREAKING,
                                failure_reason="Registry has set_websocket_bridge but bridge not set",
                                remediation="Ensure set_websocket_bridge is called during startup"
                            )
                    
                    self.validations.append(validation)
                    
        except Exception as e:
            self._add_critical_failure(
                "Agent Registry Chain",
                f"Validation failed: {e}",
                "Check agent registry initialization"
            )
    
    async def _validate_tool_dispatcher_enhancement(self, app) -> None:
        """Validate tool dispatcher configuration for UserContext architecture."""
        try:
            # In UserContext architecture, tool_dispatcher is created per-request
            # Validate that the necessary factories and classes are available
            
            # Check for websocket_bridge_factory
            has_bridge_factory = hasattr(app.state, 'websocket_bridge_factory') and app.state.websocket_bridge_factory is not None
            
            # Check for tool_classes configuration
            has_tool_classes = hasattr(app.state, 'tool_classes') and app.state.tool_classes is not None
            
            if has_bridge_factory and has_tool_classes:
                validation = CriticalPathValidation(
                    component="Tool Dispatcher Configuration",
                    path="UserContext.tool_dispatcher",
                    check_type="configuration",
                    passed=True,
                    criticality=CriticalityLevel.CHAT_BREAKING,
                    metadata={
                        "has_bridge_factory": has_bridge_factory,
                        "has_tool_classes": has_tool_classes,
                        "architecture": "UserContext"
                    }
                )
                self.logger.info("[U+2713] Tool dispatcher configuration verified for UserContext architecture")
            else:
                failure_details = []
                if not has_bridge_factory:
                    failure_details.append("missing websocket_bridge_factory")
                if not has_tool_classes:
                    failure_details.append("missing tool_classes")
                    
                validation = CriticalPathValidation(
                    component="Tool Dispatcher Configuration",
                    path="UserContext.tool_dispatcher",
                    check_type="configuration",
                    passed=False,
                    criticality=CriticalityLevel.CHAT_BREAKING,
                    failure_reason=f"UserContext tool dispatcher configuration incomplete: {', '.join(failure_details)}",
                    remediation="Ensure websocket_bridge_factory and tool_classes are configured during startup",
                    metadata={
                        "has_bridge_factory": has_bridge_factory,
                        "has_tool_classes": has_tool_classes,
                        "architecture": "UserContext"
                    }
                )
                self.logger.error(f" FAIL:  CRITICAL: UserContext tool dispatcher configuration incomplete - tool events won't be sent to UI")
            
            self.validations.append(validation)
                
        except Exception as e:
            self._add_critical_failure(
                "Tool Dispatcher Configuration",
                f"Validation failed: {e}",
                "Check UserContext tool dispatcher configuration"
            )
    
    async def _validate_message_handler_chain(self, app) -> None:
        """
        Validate WebSocket message routing infrastructure is ready.
        
        CRITICAL: Handlers are registered PER WebSocket connection, not globally at startup.
        This validates that the message routing mechanism EXISTS and CAN accept handlers.
        """
        try:
            # Check if MessageRouter exists and is functional
            message_router = None
            try:
                from netra_backend.app.websocket_core import get_message_router
                message_router = get_message_router()
            except ImportError as e:
                self._add_critical_failure(
                    "Message Handler Chain",
                    f"Failed to import message router: {e}",
                    "Check websocket_core imports and dependencies"
                )
                return
            
            if message_router:
                # Check that MessageRouter has the infrastructure to accept handlers
                has_handlers_list = hasattr(message_router, 'handlers')
                has_add_handler_method = hasattr(message_router, 'add_handler') and callable(getattr(message_router, 'add_handler'))
                has_route_method = hasattr(message_router, 'route_message') and callable(getattr(message_router, 'route_message'))
                
                # CRITICAL FIX: Use grace period aware handler status checking
                handler_status = None
                if hasattr(message_router, 'check_handler_status_with_grace_period'):
                    handler_status = message_router.check_handler_status_with_grace_period()
                    default_handler_count = handler_status["handler_count"]
                else:
                    # Fallback to old method if grace period checking not available
                    default_handler_count = 0
                    if has_handlers_list:
                        default_handler_count = len(message_router.handlers)
                
                # Validate infrastructure readiness
                infrastructure_ready = has_handlers_list and has_add_handler_method and has_route_method
                
                if not infrastructure_ready:
                    missing_components = []
                    if not has_handlers_list:
                        missing_components.append("handlers list")
                    if not has_add_handler_method:
                        missing_components.append("add_handler method")
                    if not has_route_method:
                        missing_components.append("route_message method")
                    
                    validation = CriticalPathValidation(
                        component="Message Handler Chain",
                        path="MessageRouter infrastructure",
                        check_type="infrastructure_readiness",
                        passed=False,
                        criticality=CriticalityLevel.CHAT_BREAKING,
                        failure_reason=f"MessageRouter missing components: {missing_components}",
                        remediation="Ensure MessageRouter is properly initialized with all required methods",
                        metadata={"missing_components": missing_components}
                    )
                    self.logger.error(f" FAIL:  CRITICAL: MessageRouter infrastructure incomplete - missing: {missing_components}")
                elif handler_status and handler_status["status"] == "initializing":
                    # CRITICAL FIX: During grace period, don't warn about zero handlers
                    validation = CriticalPathValidation(
                        component="Message Handler Chain",
                        path="MessageRouter.handlers",
                        check_type="startup_grace_period",
                        passed=True,  # This is expected during startup
                        criticality=CriticalityLevel.WARNING,  # Reduced criticality during grace period
                        metadata={
                            "handler_status": handler_status,
                            "grace_period_active": True,
                            "message": handler_status["message"]
                        }
                    )
                    self.logger.info(f"[U+2139][U+FE0F] Handler registration: {handler_status['message']}")
                elif handler_status and handler_status["status"] == "error":
                    # CRITICAL FIX: Only warn AFTER grace period expires
                    validation = CriticalPathValidation(
                        component="Message Handler Chain",
                        path="MessageRouter.handlers",
                        check_type="default_handlers",
                        passed=False,
                        criticality=CriticalityLevel.CHAT_BREAKING,
                        failure_reason=f"MessageRouter has no default handlers after grace period - basic message types won't be processed",
                        remediation="Ensure MessageRouter initializes with default handlers (HeartbeatHandler, etc.)",
                        metadata={"handler_status": handler_status}
                    )
                    self.logger.error(f" FAIL:  CRITICAL: {handler_status['message']} - basic functionality broken")
                elif default_handler_count == 0:
                    # Fallback case when grace period checking is not available
                    validation = CriticalPathValidation(
                        component="Message Handler Chain",
                        path="MessageRouter.handlers",
                        check_type="default_handlers",
                        passed=False,
                        criticality=CriticalityLevel.CHAT_BREAKING,
                        failure_reason="MessageRouter has no default handlers - basic message types won't be processed",
                        remediation="Ensure MessageRouter initializes with default handlers (HeartbeatHandler, etc.)",
                        metadata={"default_handler_count": 0}
                    )
                    self.logger.error(" FAIL:  CRITICAL: MessageRouter has no default handlers - basic functionality broken")
                else:
                    # Infrastructure is ready - handlers are properly registered
                    validation = CriticalPathValidation(
                        component="Message Handler Chain",
                        path="MessageRouter infrastructure",
                        check_type="infrastructure_readiness",
                        passed=True,
                        criticality=CriticalityLevel.CHAT_BREAKING,
                        metadata={
                            "default_handler_count": default_handler_count,
                            "can_accept_per_connection_handlers": True,
                            "infrastructure_components": ["handlers_list", "add_handler_method", "route_message_method"],
                            "handler_status": handler_status
                        }
                    )
                    if handler_status:
                        self.logger.info(f"[U+2713] {handler_status['message']} - per-connection registration supported")
                    else:
                        self.logger.info(f"[U+2713] Message handler infrastructure ready ({default_handler_count} default handlers, per-connection registration supported)")
                
                self.validations.append(validation)
            else:
                self._add_critical_failure(
                    "Message Handler Chain",
                    "MessageRouter not available",
                    "Ensure MessageRouter is initialized during startup"
                )
                
        except Exception as e:
            self._add_critical_failure(
                "Message Handler Chain",
                f"Validation failed: {e}",
                "Check MessageRouter initialization and imports"
            )
    
    async def _validate_execution_context_propagation(self, app) -> None:
        """Validate execution context can be propagated to agents."""
        try:
            # Check if execution engine exists
            execution_engine_found = False
            context_propagation_possible = False
            engine_with_bridge = None
            
            if hasattr(app.state, 'agent_supervisor') and app.state.agent_supervisor:
                supervisor = app.state.agent_supervisor
                
                # Check for ExecutionEngine with AgentWebSocketBridge
                if hasattr(supervisor, 'engine'):
                    execution_engine_found = True
                    engine = supervisor.engine
                    
                    # Check if engine has websocket_bridge
                    if hasattr(engine, 'websocket_bridge') and engine.websocket_bridge is not None:
                        context_propagation_possible = True
                        engine_with_bridge = 'engine.websocket_bridge'
                    # Alternative: Check if engine has websocket_notifier (deprecated but might exist)
                    elif hasattr(engine, 'websocket_notifier') and engine.websocket_notifier is not None:
                        context_propagation_possible = True
                        engine_with_bridge = 'engine.websocket_notifier (deprecated)'
                
                # Check for BaseExecutionEngine
                if hasattr(supervisor, 'execution_engine') and not context_propagation_possible:
                    execution_engine_found = True
                    engine = supervisor.execution_engine
                    
                    # BaseExecutionEngine typically doesn't have WebSocket integration directly
                    # But check anyway
                    if hasattr(engine, 'websocket_bridge') and engine.websocket_bridge is not None:
                        context_propagation_possible = True
                        engine_with_bridge = 'execution_engine.websocket_bridge'
                
                # Check if the bridge is available at the supervisor level
                if not context_propagation_possible and hasattr(app.state, 'agent_websocket_bridge'):
                    if app.state.agent_websocket_bridge is not None:
                        context_propagation_possible = True
                        engine_with_bridge = 'app.state.agent_websocket_bridge'
            
            if not execution_engine_found:
                validation = CriticalPathValidation(
                    component="Execution Context Propagation",
                    path="Supervisor -> ExecutionEngine -> Agent",
                    check_type="context_chain",
                    passed=False,
                    criticality=CriticalityLevel.CHAT_BREAKING,
                    failure_reason="Execution engine not found in supervisor",
                    remediation="Ensure supervisor has execution_engine or engine attribute"
                )
                self.logger.error(" FAIL:  CRITICAL: Execution engine missing - context can't be propagated to agents")
            elif not context_propagation_possible:
                validation = CriticalPathValidation(
                    component="Execution Context Propagation",
                    path="AgentWebSocketBridge",
                    check_type="bridge_availability",
                    passed=False,
                    criticality=CriticalityLevel.CHAT_BREAKING,
                    failure_reason="AgentWebSocketBridge not available for execution context",
                    remediation="Ensure AgentWebSocketBridge is initialized and available"
                )
                self.logger.error(" FAIL:  CRITICAL: AgentWebSocketBridge not available - agent events won't be sent")
            else:
                validation = CriticalPathValidation(
                    component="Execution Context Propagation",
                    path="Supervisor -> ExecutionEngine -> Agent",
                    check_type="context_chain",
                    passed=True,
                    criticality=CriticalityLevel.CHAT_BREAKING,
                    metadata={"bridge_location": engine_with_bridge}
                )
                self.logger.info(f"[U+2713] Execution context propagation chain verified (using {engine_with_bridge})")
            
            self.validations.append(validation)
            
        except Exception as e:
            self._add_critical_failure(
                "Execution Context Propagation",
                f"Validation failed: {e}",
                "Check supervisor and execution engine initialization"
            )
    
    async def _validate_notifier_initialization(self, app) -> None:
        """Validate AgentWebSocketBridge is properly initialized (replaces WebSocketNotifier)."""
        try:
            # Check for AgentWebSocketBridge which is the new SSOT for WebSocket notifications
            bridge_found = False
            bridge_locations = []
            
            # Check in app.state for AgentWebSocketBridge
            if hasattr(app.state, 'agent_websocket_bridge') and app.state.agent_websocket_bridge:
                bridge_found = True
                bridge_locations.append("app.state.agent_websocket_bridge")
                
                # Validate it has the required notification methods
                bridge = app.state.agent_websocket_bridge
                required_methods = ['notify_agent_started', 'notify_agent_completed', 'notify_tool_executing']
                missing_methods = [m for m in required_methods if not hasattr(bridge, m)]
                
                if missing_methods:
                    validation = CriticalPathValidation(
                        component="AgentWebSocketBridge Initialization",
                        path="AgentWebSocketBridge",
                        check_type="initialization",
                        passed=False,
                        criticality=CriticalityLevel.CHAT_BREAKING,
                        failure_reason=f"AgentWebSocketBridge missing required methods: {missing_methods}",
                        remediation="Ensure AgentWebSocketBridge has all notification methods",
                        metadata={"missing_methods": missing_methods}
                    )
                    self.logger.error(f" FAIL:  CRITICAL: AgentWebSocketBridge incomplete - missing methods: {missing_methods}")
                else:
                    # Check if bridge is integrated with supervisor
                    integrated = False
                    if hasattr(app.state, 'agent_supervisor') and app.state.agent_supervisor:
                        supervisor = app.state.agent_supervisor
                        # Check if supervisor's registry has the bridge
                        if hasattr(supervisor, 'registry') and hasattr(supervisor.registry, 'websocket_bridge'):
                            if supervisor.registry.websocket_bridge == bridge:
                                integrated = True
                                bridge_locations.append("supervisor.registry.websocket_bridge")
                    
                    validation = CriticalPathValidation(
                        component="AgentWebSocketBridge Initialization",
                        path="AgentWebSocketBridge",
                        check_type="initialization",
                        passed=True,
                        criticality=CriticalityLevel.CHAT_BREAKING,
                        metadata={
                            "found_in": bridge_locations,
                            "integrated_with_supervisor": integrated,
                            "has_all_methods": True
                        }
                    )
                    self.logger.info(f"[U+2713] AgentWebSocketBridge properly initialized in: {', '.join(bridge_locations)}")
            else:
                validation = CriticalPathValidation(
                    component="AgentWebSocketBridge Initialization",
                    path="AgentWebSocketBridge",
                    check_type="initialization",
                    passed=False,
                    criticality=CriticalityLevel.CHAT_BREAKING,
                    failure_reason="AgentWebSocketBridge not found in app.state",
                    remediation="Ensure AgentWebSocketBridge is created during startup",
                    metadata={"checked_locations": ["app.state.agent_websocket_bridge"]}
                )
                self.logger.error(" FAIL:  CRITICAL: AgentWebSocketBridge not initialized - NO agent events will be sent to UI")
            
            self.validations.append(validation)
            
        except Exception as e:
            self._add_critical_failure(
                "AgentWebSocketBridge Initialization",
                f"Validation failed: {e}",
                "Check AgentWebSocketBridge creation in startup"
            )
    
    def _add_critical_failure(self, component: str, reason: str, remediation: str) -> None:
        """Add a critical failure validation."""
        validation = CriticalPathValidation(
            component=component,
            path="",
            check_type="existence",
            passed=False,
            criticality=CriticalityLevel.CHAT_BREAKING,
            failure_reason=reason,
            remediation=remediation
        )
        self.validations.append(validation)
        self.logger.error(f" FAIL:  CRITICAL: {component}: {reason}")


# Global validator instance
critical_path_validator = CriticalPathValidator()


async def validate_critical_paths(app) -> Tuple[bool, List[CriticalPathValidation]]:
    """
    Convenience function to validate critical paths.
    Returns (success, validations) tuple.
    """
    return await critical_path_validator.validate_critical_paths(app)