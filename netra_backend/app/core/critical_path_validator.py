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
    1. WebSocket Context Propagation (agent -> tools -> UI)
    2. Agent Registry and Enhancement Chain
    3. Tool Dispatcher WebSocket Enhancement
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
        await self._validate_websocket_mixin_chain(app)
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
            self.logger.error("🚨 CRITICAL FAILURES DETECTED - CHAT IS BROKEN!")
            self.logger.error("=" * 60)
            for failure in critical_failures:
                self.logger.error(f"❌ {failure.component}: {failure.failure_reason}")
                if failure.remediation:
                    self.logger.error(f"   FIX: {failure.remediation}")
            self.logger.error("=" * 60)
            
        # Log warnings for potential issues
        warnings = [v for v in self.validations 
                   if not v.passed and v.criticality != CriticalityLevel.CHAT_BREAKING]
        
        if warnings:
            self.logger.warning("⚠️ Non-critical issues detected:")
            for warning in warnings:
                self.logger.warning(f"  - {warning.component}: {warning.failure_reason}")
        
        all_passed = len(critical_failures) == 0
        return all_passed, self.validations
    
    async def _validate_websocket_mixin_chain(self, app) -> None:
        """Validate WebSocket mixin is properly inherited and callable."""
        try:
            # Check if agents have the mixin
            if hasattr(app.state, 'agent_supervisor') and app.state.agent_supervisor:
                if hasattr(app.state.agent_supervisor, 'registry'):
                    registry = app.state.agent_supervisor.registry
                    
                    agents_missing_mixin = []
                    agents_missing_context_setter = []
                    
                    for agent_name, agent in registry.agents.items():
                        # Check if agent has WebSocketContextMixin methods
                        has_mixin = hasattr(agent, 'set_websocket_context')
                        has_emit = hasattr(agent, 'emit_thinking')
                        has_propagate = hasattr(agent, 'propagate_websocket_context_to_state')
                        
                        if not has_mixin:
                            agents_missing_context_setter.append(agent_name)
                        if not (has_emit and has_propagate):
                            agents_missing_mixin.append(agent_name)
                    
                    if agents_missing_mixin or agents_missing_context_setter:
                        validation = CriticalPathValidation(
                            component="WebSocket Mixin Chain",
                            path="BaseSubAgent -> WebSocketContextMixin",
                            check_type="inheritance",
                            passed=False,
                            criticality=CriticalityLevel.CHAT_BREAKING,
                            failure_reason=f"Agents missing WebSocket capabilities: {agents_missing_mixin or agents_missing_context_setter}",
                            remediation="Ensure all agents inherit from BaseSubAgent which includes WebSocketContextMixin",
                            metadata={
                                "missing_mixin": agents_missing_mixin,
                                "missing_setter": agents_missing_context_setter
                            }
                        )
                        self.logger.error(f"❌ CRITICAL: WebSocket mixin not properly inherited by agents: {agents_missing_mixin or agents_missing_context_setter}")
                    else:
                        validation = CriticalPathValidation(
                            component="WebSocket Mixin Chain",
                            path="BaseSubAgent -> WebSocketContextMixin",
                            check_type="inheritance",
                            passed=True,
                            criticality=CriticalityLevel.CHAT_BREAKING
                        )
                        self.logger.info("✓ WebSocket mixin properly inherited by all agents")
                    
                    self.validations.append(validation)
                else:
                    self._add_critical_failure(
                        "WebSocket Mixin Chain",
                        "Registry not found - cannot validate mixin inheritance",
                        "Ensure agent_supervisor has registry attribute"
                    )
            else:
                self._add_critical_failure(
                    "WebSocket Mixin Chain",
                    "Agent supervisor not initialized",
                    "Ensure agent supervisor is created during startup"
                )
                
        except Exception as e:
            self._add_critical_failure(
                "WebSocket Mixin Chain",
                f"Validation failed: {e}",
                "Check agent initialization and mixin imports"
            )
    
    async def _validate_agent_registry_chain(self, app) -> None:
        """Validate agent registry has set_websocket_manager method."""
        try:
            if hasattr(app.state, 'agent_supervisor') and app.state.agent_supervisor:
                if hasattr(app.state.agent_supervisor, 'registry'):
                    registry = app.state.agent_supervisor.registry
                    
                    # Check if registry has the critical method
                    has_setter = hasattr(registry, 'set_websocket_manager')
                    
                    if not has_setter:
                        validation = CriticalPathValidation(
                            component="Agent Registry WebSocket Integration",
                            path="AgentRegistry.set_websocket_manager()",
                            check_type="method_existence",
                            passed=False,
                            criticality=CriticalityLevel.CHAT_BREAKING,
                            failure_reason="Registry missing set_websocket_manager method",
                            remediation="Add set_websocket_manager method to AgentRegistry class"
                        )
                        self.logger.error("❌ CRITICAL: AgentRegistry missing set_websocket_manager method")
                    else:
                        # Check if it was actually called (tool_dispatcher should be enhanced)
                        if hasattr(registry, 'tool_dispatcher'):
                            enhanced = getattr(registry.tool_dispatcher, '_websocket_enhanced', False)
                            if not enhanced:
                                validation = CriticalPathValidation(
                                    component="Agent Registry WebSocket Integration",
                                    path="AgentRegistry.set_websocket_manager() -> tool_dispatcher enhancement",
                                    check_type="enhancement_status",
                                    passed=False,
                                    criticality=CriticalityLevel.CHAT_BREAKING,
                                    failure_reason="set_websocket_manager exists but was not called or failed",
                                    remediation="Ensure set_websocket_manager is called during startup",
                                    metadata={"enhanced": enhanced}
                                )
                                self.logger.warning("⚠️ set_websocket_manager method exists but enhancement not applied")
                            else:
                                validation = CriticalPathValidation(
                                    component="Agent Registry WebSocket Integration",
                                    path="AgentRegistry.set_websocket_manager()",
                                    check_type="method_existence",
                                    passed=True,
                                    criticality=CriticalityLevel.CHAT_BREAKING
                                )
                                self.logger.info("✓ Agent registry WebSocket integration verified")
                        else:
                            validation = CriticalPathValidation(
                                component="Agent Registry WebSocket Integration",
                                path="AgentRegistry.tool_dispatcher",
                                check_type="attribute_existence",
                                passed=False,
                                criticality=CriticalityLevel.CHAT_BREAKING,
                                failure_reason="Registry has no tool_dispatcher attribute",
                                remediation="Ensure registry is initialized with tool_dispatcher"
                            )
                    
                    self.validations.append(validation)
                    
        except Exception as e:
            self._add_critical_failure(
                "Agent Registry Chain",
                f"Validation failed: {e}",
                "Check agent registry initialization"
            )
    
    async def _validate_tool_dispatcher_enhancement(self, app) -> None:
        """Validate tool dispatcher is enhanced with WebSocket notifications."""
        try:
            if hasattr(app.state, 'tool_dispatcher') and app.state.tool_dispatcher:
                dispatcher = app.state.tool_dispatcher
                
                # Check for enhancement flag
                enhanced = getattr(dispatcher, '_websocket_enhanced', False)
                
                # Check for WebSocket manager
                has_ws_manager = hasattr(dispatcher, '_websocket_manager')
                ws_manager_not_none = has_ws_manager and dispatcher._websocket_manager is not None
                
                # Check for notification wrapper
                has_wrapper = hasattr(dispatcher, '_original_invoke_tool')
                
                if not enhanced:
                    failure_details = []
                    if not has_ws_manager:
                        failure_details.append("missing _websocket_manager attribute")
                    elif not ws_manager_not_none:
                        failure_details.append("_websocket_manager is None")
                    if not has_wrapper:
                        failure_details.append("tool invocation not wrapped")
                    
                    validation = CriticalPathValidation(
                        component="Tool Dispatcher Enhancement",
                        path="ToolDispatcher._enhance_with_websocket()",
                        check_type="enhancement",
                        passed=False,
                        criticality=CriticalityLevel.CHAT_BREAKING,
                        failure_reason=f"Tool dispatcher not enhanced: {', '.join(failure_details)}",
                        remediation="Call AgentRegistry.set_websocket_manager() during startup",
                        metadata={
                            "enhanced": enhanced,
                            "has_ws_manager": has_ws_manager,
                            "ws_manager_not_none": ws_manager_not_none,
                            "has_wrapper": has_wrapper
                        }
                    )
                    self.logger.error(f"❌ CRITICAL: Tool dispatcher not enhanced - tool events won't be sent to UI")
                else:
                    validation = CriticalPathValidation(
                        component="Tool Dispatcher Enhancement",
                        path="ToolDispatcher._enhance_with_websocket()",
                        check_type="enhancement",
                        passed=True,
                        criticality=CriticalityLevel.CHAT_BREAKING
                    )
                    self.logger.info("✓ Tool dispatcher properly enhanced with WebSocket")
                
                self.validations.append(validation)
            else:
                self._add_critical_failure(
                    "Tool Dispatcher Enhancement",
                    "Tool dispatcher not initialized",
                    "Ensure tool_dispatcher is created during startup"
                )
                
        except Exception as e:
            self._add_critical_failure(
                "Tool Dispatcher Enhancement",
                f"Validation failed: {e}",
                "Check tool dispatcher initialization"
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
                
                # Count default handlers (should include HeartbeatHandler, etc.)
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
                    self.logger.error(f"❌ CRITICAL: MessageRouter infrastructure incomplete - missing: {missing_components}")
                elif default_handler_count == 0:
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
                    self.logger.error("❌ CRITICAL: MessageRouter has no default handlers - basic functionality broken")
                else:
                    # Infrastructure is ready - this is what we expect during startup
                    validation = CriticalPathValidation(
                        component="Message Handler Chain",
                        path="MessageRouter infrastructure",
                        check_type="infrastructure_readiness",
                        passed=True,
                        criticality=CriticalityLevel.CHAT_BREAKING,
                        metadata={
                            "default_handler_count": default_handler_count,
                            "can_accept_per_connection_handlers": True,
                            "infrastructure_components": ["handlers_list", "add_handler_method", "route_message_method"]
                        }
                    )
                    self.logger.info(f"✓ Message handler infrastructure ready ({default_handler_count} default handlers, per-connection registration supported)")
                
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
            engine_with_notifier = None
            
            if hasattr(app.state, 'agent_supervisor') and app.state.agent_supervisor:
                supervisor = app.state.agent_supervisor
                
                # CRITICAL FIX: Check all possible execution engines and prioritize the one with WebSocket notifier
                # Check for newer ExecutionEngine instance first (has WebSocket notifier)
                if hasattr(supervisor, 'engine'):
                    execution_engine_found = True
                    engine = supervisor.engine
                    
                    # Check if engine has websocket_notifier
                    if hasattr(engine, 'websocket_notifier') and engine.websocket_notifier is not None:
                        context_propagation_possible = True
                        engine_with_notifier = 'engine'
                
                # Check for execution engine (old BaseExecutionEngine, usually without WebSocket notifier)
                if hasattr(supervisor, 'execution_engine') and not context_propagation_possible:
                    execution_engine_found = True
                    engine = supervisor.execution_engine
                    
                    # Check if engine has websocket_notifier
                    if hasattr(engine, 'websocket_notifier') and engine.websocket_notifier is not None:
                        context_propagation_possible = True
                        engine_with_notifier = 'execution_engine'
                
                # Alternative: Check for agent_manager
                if hasattr(supervisor, 'agent_manager') and not context_propagation_possible:
                    execution_engine_found = True
                    manager = supervisor.agent_manager
                    
                    if hasattr(manager, 'websocket_notifier') and manager.websocket_notifier is not None:
                        context_propagation_possible = True
                        engine_with_notifier = 'agent_manager'
            
            if not execution_engine_found:
                validation = CriticalPathValidation(
                    component="Execution Context Propagation",
                    path="Supervisor -> ExecutionEngine -> Agent",
                    check_type="context_chain",
                    passed=False,
                    criticality=CriticalityLevel.CHAT_BREAKING,
                    failure_reason="Execution engine not found in supervisor",
                    remediation="Ensure supervisor has execution_engine, engine, or agent_manager"
                )
                self.logger.error("❌ CRITICAL: Execution engine missing - context can't be propagated to agents")
            elif not context_propagation_possible:
                validation = CriticalPathValidation(
                    component="Execution Context Propagation",
                    path="ExecutionEngine.websocket_notifier",
                    check_type="notifier_existence",
                    passed=False,
                    criticality=CriticalityLevel.CHAT_BREAKING,
                    failure_reason="WebSocket notifier not initialized in any execution engine",
                    remediation="Ensure WebSocketNotifier is created in ExecutionEngine (supervisor.engine)"
                )
                self.logger.error("❌ CRITICAL: WebSocket notifier missing - agent events won't be sent")
            else:
                validation = CriticalPathValidation(
                    component="Execution Context Propagation",
                    path="Supervisor -> ExecutionEngine -> Agent",
                    check_type="context_chain",
                    passed=True,
                    criticality=CriticalityLevel.CHAT_BREAKING,
                    metadata={"engine_with_notifier": engine_with_notifier}
                )
                self.logger.info(f"✓ Execution context propagation chain verified (using {engine_with_notifier})")
            
            self.validations.append(validation)
            
        except Exception as e:
            self._add_critical_failure(
                "Execution Context Propagation",
                f"Validation failed: {e}",
                "Check supervisor and execution engine initialization"
            )
    
    async def _validate_notifier_initialization(self, app) -> None:
        """Validate WebSocketNotifier is properly initialized."""
        try:
            # Check multiple possible locations for WebSocketNotifier
            notifier_found = False
            notifier_locations = []
            
            # Check in supervisor
            if hasattr(app.state, 'agent_supervisor') and app.state.agent_supervisor:
                supervisor = app.state.agent_supervisor
                
                # PRIORITIZE newer ExecutionEngine instance (has WebSocket notifier)
                if hasattr(supervisor, 'engine'):
                    if hasattr(supervisor.engine, 'websocket_notifier'):
                        if supervisor.engine.websocket_notifier is not None:
                            notifier_found = True
                            notifier_locations.append("engine")
                
                # Check execution engine (older BaseExecutionEngine, usually without WebSocket notifier)
                if hasattr(supervisor, 'execution_engine'):
                    if hasattr(supervisor.execution_engine, 'websocket_notifier'):
                        if supervisor.execution_engine.websocket_notifier is not None:
                            notifier_found = True
                            if "engine" not in notifier_locations:  # Avoid duplicates
                                notifier_locations.append("execution_engine")
                
                # Check agent manager
                if hasattr(supervisor, 'agent_manager'):
                    if hasattr(supervisor.agent_manager, 'websocket_notifier'):
                        if supervisor.agent_manager.websocket_notifier is not None:
                            notifier_found = True
                            notifier_locations.append("agent_manager")
                
                # Check agent execution core
                if hasattr(supervisor, 'agent_execution_core'):
                    if hasattr(supervisor.agent_execution_core, 'websocket_notifier'):
                        if supervisor.agent_execution_core.websocket_notifier is not None:
                            notifier_found = True
                            notifier_locations.append("agent_execution_core")
            
            if not notifier_found:
                validation = CriticalPathValidation(
                    component="WebSocketNotifier Initialization",
                    path="WebSocketNotifier",
                    check_type="initialization",
                    passed=False,
                    criticality=CriticalityLevel.CHAT_BREAKING,
                    failure_reason="WebSocketNotifier not found in any expected location",
                    remediation="Ensure WebSocketNotifier is created in ExecutionEngine during supervisor initialization",
                    metadata={"checked_locations": ["execution_engine", "engine", "agent_manager", "agent_execution_core"]}
                )
                self.logger.error("❌ CRITICAL: WebSocketNotifier not initialized - NO agent events will be sent to UI")
            else:
                validation = CriticalPathValidation(
                    component="WebSocketNotifier Initialization",
                    path="WebSocketNotifier",
                    check_type="initialization",
                    passed=True,
                    criticality=CriticalityLevel.CHAT_BREAKING,
                    metadata={"found_in": notifier_locations}
                )
                self.logger.info(f"✓ WebSocketNotifier found in: {', '.join(notifier_locations)}")
            
            self.validations.append(validation)
            
        except Exception as e:
            self._add_critical_failure(
                "WebSocketNotifier Initialization",
                f"Validation failed: {e}",
                "Check WebSocketNotifier creation in supervisor"
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
        self.logger.error(f"❌ CRITICAL: {component}: {reason}")


# Global validator instance
critical_path_validator = CriticalPathValidator()


async def validate_critical_paths(app) -> Tuple[bool, List[CriticalPathValidation]]:
    """
    Convenience function to validate critical paths.
    Returns (success, validations) tuple.
    """
    return await critical_path_validator.validate_critical_paths(app)