"""Agent registry and management for supervisor."""

import asyncio
import time
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Type

if TYPE_CHECKING:
    from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
    from netra_backend.app.llm.llm_manager import LLMManager
    from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
    from netra_backend.app.websocket_core.manager import WebSocketManager
    from netra_backend.app.services.factory_adapter import FactoryAdapter
    from netra_backend.app.agents.supervisor.execution_factory import UserExecutionContext
    from netra_backend.app.agents.state import DeepAgentState
    from netra_backend.app.agents.supervisor.execution_context import AgentExecutionResult
    from netra_backend.app.agents.actions_to_meet_goals_sub_agent import ActionsToMeetGoalsSubAgent
    from netra_backend.app.agents.base_agent import BaseAgent
    from netra_backend.app.agents.corpus_admin_sub_agent import CorpusAdminSubAgent
    from netra_backend.app.agents.data_helper_agent import DataHelperAgent
    from netra_backend.app.agents.optimizations_core_sub_agent import OptimizationsCoreSubAgent
    from netra_backend.app.agents.reporting_sub_agent import ReportingSubAgent
    from netra_backend.app.agents.synthetic_data_sub_agent import SyntheticDataSubAgent
    from netra_backend.app.agents.triage_sub_agent.agent import TriageSubAgent
    from netra_backend.app.agents.goals_triage_sub_agent import GoalsTriageSubAgent

# All agent imports moved to TYPE_CHECKING to avoid circular dependencies
# Agents are imported lazily when needed in registration methods
from netra_backend.app.core.agent_execution_tracker import get_execution_tracker
from netra_backend.app.core.reliability.unified_reliability_manager import (
    get_reliability_manager,
    create_agent_reliability_manager
)
from netra_backend.app.logging_config import central_logger
from netra_backend.app.agents.supervisor.agent_class_registry import AgentClassRegistry, get_agent_class_registry

logger = central_logger.get_logger(__name__)


class AgentRegistry:
    """
    DEPRECATED: Legacy agent registration and lifecycle management.
    
    This registry is maintained for backward compatibility during the transition to
    the new architecture using AgentClassRegistry and AgentInstanceFactory.
    
    New code should use:
    - AgentClassRegistry for storing agent classes (infrastructure)
    - AgentInstanceFactory for creating per-request agent instances
    
    CRITICAL: This registry still manages global singleton WebSocket state which
    causes user context leakage. Use AgentInstanceFactory for proper isolation.
    """
    
    def __init__(self, llm_manager: 'LLMManager', tool_dispatcher: 'ToolDispatcher'):
        # Issue deprecation warning
        import warnings
        warnings.warn(
            "AgentRegistry is deprecated. Use AgentClassRegistry + AgentInstanceFactory for "
            "proper user isolation. This registry shares WebSocket state between users.",
            DeprecationWarning,
            stacklevel=2
        )
        
        self.llm_manager = llm_manager
        self.tool_dispatcher = tool_dispatcher
        self.agents: Dict[str, 'BaseAgent'] = {}
        self.websocket_bridge: Optional['AgentWebSocketBridge'] = None
        self.websocket_manager: Optional['WebSocketManager'] = None
        self._agents_registered = False
        self.registration_errors: Dict[str, str] = {}
        self.execution_tracker = get_execution_tracker()
        
        # Delegate to AgentClassRegistry for infrastructure-level class storage
        self._agent_class_registry: Optional[AgentClassRegistry] = None
        try:
            self._agent_class_registry = get_agent_class_registry()
            logger.debug("Connected AgentRegistry to AgentClassRegistry for class delegation")
        except Exception as e:
            logger.warning(f"Could not connect to AgentClassRegistry: {e}")
        
        # Unified reliability manager for agent operations
        self.reliability_manager = None
        self._setup_reliability_manager()
    
    def _setup_reliability_manager(self) -> None:
        """Setup unified reliability manager with WebSocket integration."""
        try:
            self.reliability_manager = create_agent_reliability_manager(
                service_name="agent_registry",
                websocket_manager=self.websocket_manager,
                websocket_notifier=None  # Will be set when websocket_bridge is available
            )
            logger.info("Agent registry reliability manager initialized")
        except Exception as e:
            logger.error(f"Failed to setup reliability manager: {e}")
            # Fallback to basic reliability manager
            self.reliability_manager = get_reliability_manager("agent_registry")
        
    def register_default_agents(self) -> None:
        """Register default sub-agents"""
        if self._agents_registered:
            logger.debug("Agents already registered, skipping re-registration")
            return
        
        self._register_core_agents()
        self._register_auxiliary_agents()
        self._agents_registered = True
        
        # Validate agent registration counts
        agent_count = len(self.agents)
        expected_agents = ["triage", "data", "optimization", "actions", 
                          "reporting", "goals_triage", "data_helper", "synthetic_data", "corpus_admin"]
        expected_min = len(expected_agents)
        
        if agent_count == 0:
            logger.warning(f"⚠️ CRITICAL: ZERO AGENTS REGISTERED - Expected {expected_min} agents")
            logger.warning(f"   Expected agents: {', '.join(expected_agents)}")
            logger.warning("   Chat functionality will be broken!")
        elif agent_count < expected_min:
            logger.warning(f"⚠️ WARNING: Only {agent_count}/{expected_min} agents registered")
            missing = set(expected_agents) - set(self.agents.keys())
            if missing:
                logger.warning(f"   Missing agents: {', '.join(missing)}")
        else:
            logger.info(f"✓ Successfully registered {agent_count} agents")
    
    def _register_core_agents(self) -> None:
        """Register core workflow agents."""
        # Import DataSubAgent here to avoid circular dependency - GOLDEN PATTERN SSOT IMPLEMENTATION
        from netra_backend.app.agents.data_sub_agent.data_sub_agent import DataSubAgent
        
        self._register_workflow_agents(DataSubAgent)
    
    def _register_workflow_agents(self, DataSubAgent) -> None:
        """Register workflow agents with manager and dispatcher."""
        self._register_core_workflow_agents(DataSubAgent)
        self._register_optimization_agents()
    
    def _register_core_workflow_agents(self, DataSubAgent) -> None:
        """Register core workflow agents."""
        # Lazy import to avoid circular dependency
        from netra_backend.app.agents.triage_sub_agent.agent import TriageSubAgent
        self.register("triage", TriageSubAgent())
        self.register("data", DataSubAgent(
            self.llm_manager, self.tool_dispatcher))
    
    def _register_optimization_agents(self) -> None:
        """Register optimization and action agents."""
        # Lazy import to avoid circular dependency
        from netra_backend.app.agents.optimizations_core_sub_agent import OptimizationsCoreSubAgent
        self.register("optimization", OptimizationsCoreSubAgent(
            self.llm_manager, self.tool_dispatcher))
        
        # Lazy import to avoid circular dependency
        from netra_backend.app.agents.actions_to_meet_goals_sub_agent import ActionsToMeetGoalsSubAgent
        self.register("actions", ActionsToMeetGoalsSubAgent(
            self.llm_manager, self.tool_dispatcher))
    
    def _register_auxiliary_agents(self) -> None:
        """Register auxiliary agents."""
        self._register_reporting_agent()
        self._register_goals_triage_agent()
        self._register_data_helper_agent()
        self._register_synthetic_data_agent()
        self._register_corpus_admin_agent()
    
    def register(self, name: str, agent: 'BaseAgent') -> None:
        """
        Register a sub-agent (DEPRECATED - causes user context leakage).
        
        WARNING: This method sets WebSocket bridge with None run_id which
        breaks per-user isolation and causes WebSocket events to be mixed.
        
        Use AgentInstanceFactory.create_agent_instance() instead for proper
        per-user isolation with real run_id from UserExecutionContext.
        """
        if name in self.agents:
            logger.debug(f"Agent {name} already registered, skipping")
            return
            
        # CRITICAL ISSUE: Setting WebSocket bridge with None run_id
        # This causes placeholder 'registry' run_id and breaks user isolation
        if self.websocket_bridge and hasattr(agent, 'set_websocket_bridge'):
            logger.warning(
                f"⚠️ DEPRECATED: Setting WebSocket bridge on {name} with None run_id - "
                f"this breaks user isolation! Use AgentInstanceFactory instead."
            )
            # Note: This is the problematic line that uses placeholder run_id
            agent.set_websocket_bridge(self.websocket_bridge, None)
        
        self.agents[name] = agent
        
        # NEW: Also register agent class in AgentClassRegistry for new architecture
        if self._agent_class_registry and not self._agent_class_registry.has_agent_class(name):
            try:
                agent_class = type(agent)
                self._agent_class_registry.register(
                    name=name,
                    agent_class=agent_class,
                    description=getattr(agent, 'description', f"{agent_class.__name__} agent"),
                    version=getattr(agent, 'version', '1.0.0')
                )
                logger.debug(f"Registered agent class {name} in AgentClassRegistry")
            except Exception as e:
                logger.warning(f"Failed to register agent class {name} in AgentClassRegistry: {e}")
        
        # Clear any previous registration errors
        self.registration_errors.pop(name, None)
        logger.debug(f"Registered agent: {name} (with deprecation warning)")
    
    async def register_agent_safely(self, name: str, agent_class: Type['BaseAgent'], **kwargs) -> bool:
        """Register an agent safely with error handling.
        
        Args:
            name: Name of the agent
            agent_class: The agent class to instantiate
            **kwargs: Additional keyword arguments for agent initialization
            
        Returns:
            bool: True if registration was successful, False otherwise
        """
        try:
            logger.info(f"Attempting to register agent: {name}")
            
            # Create agent instance
            agent = agent_class(
                self.llm_manager,
                self.tool_dispatcher,
                **kwargs
            )
            
            # Set websocket bridge if available and agent supports it
            if self.websocket_bridge and hasattr(agent, 'set_websocket_bridge'):
                # Note: run_id will be set dynamically during execution, not during registration
                agent.set_websocket_bridge(self.websocket_bridge, None)
                
            # Store the agent
            self.agents[name] = agent
            
            # Clear any previous registration errors
            self.registration_errors.pop(name, None)
            
            logger.info(f"Successfully registered agent: {name}")
            return True
            
        except Exception as e:
            error_msg = f"Failed to register agent {name}: {str(e)}"
            logger.error(error_msg)
            self.registration_errors[name] = error_msg
            return False
    
    def get(self, name: str) -> Optional['BaseAgent']:
        """Get agent by name"""
        return self.agents.get(name)
    
    def get_registry_health(self) -> Dict[str, Any]:
        """Get the health status of the registry.
        
        Returns:
            Dictionary containing health information
        """
        healthy_agents = 0
        agent_health_details = {}
        
        for name, agent in self.agents.items():
            try:
                if hasattr(agent, 'get_health_status'):
                    health_status = agent.get_health_status()
                    agent_health_details[name] = health_status
                    # Consider agent healthy if it has a 'status' field that's not 'error' or 'failed'
                    if isinstance(health_status, dict):
                        status = health_status.get('status', 'unknown')
                        if status not in ['error', 'failed', 'critical']:
                            healthy_agents += 1
                    else:
                        healthy_agents += 1
                else:
                    # Agent doesn't have health status method, assume healthy if it exists
                    healthy_agents += 1
                    agent_health_details[name] = {"status": "unknown"}
            except Exception as e:
                logger.warning(f"Failed to get health status for agent {name}: {e}")
                agent_health_details[name] = {"status": "error", "error": str(e)}
        
        # Add execution tracker metrics
        execution_metrics = {}
        dead_agents = []
        if self.execution_tracker:
            execution_metrics = self.execution_tracker.get_metrics()
            # Check for dead agents
            dead_executions = self.execution_tracker.detect_dead_executions()
            dead_agents = [
                {
                    "agent": ex.agent_name,
                    "execution_id": ex.execution_id,
                    "death_cause": "timeout" if ex.is_timed_out() else "no_heartbeat",
                    "time_since_heartbeat": ex.time_since_heartbeat.total_seconds()
                }
                for ex in dead_executions
            ]
        
        return {
            "total_agents": len(self.agents),
            "healthy_agents": healthy_agents,
            "failed_registrations": len(self.registration_errors),
            "agent_health": agent_health_details,
            "registration_errors": self.registration_errors.copy(),
            "execution_metrics": execution_metrics,
            "dead_agents": dead_agents,
            "death_detection_enabled": True
        }

    def remove_agent(self, name: str) -> bool:
        """Remove an agent from the registry.
        
        Args:
            name: Name of the agent to remove
            
        Returns:
            bool: True if agent was removed, False if not found
        """
        if name in self.agents:
            del self.agents[name]
            logger.info(f"Removed agent: {name}")
            return True
        return False
    
    def list_agents(self) -> List[str]:
        """List registered agent names"""
        return list(self.agents.keys())
    
    def get_all_agents(self) -> List['BaseAgent']:
        """Get all registered agents"""
        return list(self.agents.values())
    
    def _register_reporting_agent(self) -> None:
        """Register reporting agent."""
        # Lazy import to avoid circular dependency
        from netra_backend.app.agents.reporting_sub_agent import ReportingSubAgent
        self.register("reporting", ReportingSubAgent())
    
    def _register_goals_triage_agent(self) -> None:
        """Register goals triage agent."""
        # Lazy import to avoid circular dependency
        from netra_backend.app.agents.goals_triage_sub_agent import GoalsTriageSubAgent
        self.register("goals_triage", GoalsTriageSubAgent())
    
    def _register_synthetic_data_agent(self) -> None:
        """Register synthetic data agent."""
        # Lazy import to avoid circular dependency
        from netra_backend.app.agents.synthetic_data_sub_agent import SyntheticDataSubAgent
        self.register("synthetic_data", SyntheticDataSubAgent(
            self.llm_manager, self.tool_dispatcher))
    
    def _register_data_helper_agent(self) -> None:
        """Register data helper agent."""
        # Lazy import to avoid circular dependency
        from netra_backend.app.agents.data_helper_agent import DataHelperAgent
        self.register("data_helper", DataHelperAgent(self.llm_manager, self.tool_dispatcher))
    
    def _register_corpus_admin_agent(self) -> None:
        """Register corpus admin agent."""
        # Lazy import to avoid circular dependency
        from netra_backend.app.agents.corpus_admin_sub_agent import CorpusAdminSubAgent
        self.register("corpus_admin", CorpusAdminSubAgent(
            self.llm_manager, self.tool_dispatcher))

    def set_websocket_manager(self, websocket_manager: 'WebSocketManager') -> None:
        """Set WebSocket manager for reliability events and enhance tool dispatcher."""
        self.websocket_manager = websocket_manager
        
        # CRITICAL: Enhance tool dispatcher with WebSocket notifications
        if self.tool_dispatcher and websocket_manager:
            try:
                # Check if tool dispatcher supports modern WebSocket enhancement
                if hasattr(self.tool_dispatcher, 'set_websocket_manager'):
                    # Modern tool dispatcher with WebSocket support
                    self.tool_dispatcher.set_websocket_manager(websocket_manager)
                    logger.info("✅ Tool dispatcher enhanced with WebSocket manager (modern pattern)")
                elif hasattr(self.tool_dispatcher, 'enhance_with_websocket'):
                    # Alternative modern enhancement method
                    self.tool_dispatcher.enhance_with_websocket(websocket_manager)
                    logger.info("✅ Tool dispatcher enhanced with WebSocket (alternative pattern)")
                else:
                    # Fallback to legacy enhancement
                    from netra_backend.app.agents.websocket_tool_enhancement import enhance_tool_dispatcher_with_notifications
                    enhance_tool_dispatcher_with_notifications(self.tool_dispatcher, websocket_manager)
                    logger.info("✅ Tool dispatcher enhanced with WebSocket notifications (legacy pattern)")
                    logger.warning("⚠️ Using legacy WebSocket enhancement - consider upgrading tool dispatcher")
            except ImportError as e:
                logger.error(f"WebSocket enhancement module not available: {e}")
            except Exception as e:
                logger.error(f"Failed to enhance tool dispatcher with WebSocket: {e}")
        else:
            if not self.tool_dispatcher:
                logger.warning("Cannot enhance tool dispatcher: tool_dispatcher is None")
            if not websocket_manager:
                logger.warning("Cannot enhance tool dispatcher: websocket_manager is None")
        
        # Update reliability manager with WebSocket capabilities
        if self.reliability_manager:
            try:
                self.reliability_manager = create_agent_reliability_manager(
                    service_name="agent_registry",
                    websocket_manager=websocket_manager,
                    websocket_notifier=getattr(self, 'websocket_bridge', None)
                )
                logger.info("Agent registry reliability manager updated with WebSocket manager")
            except Exception as e:
                logger.error(f"Failed to update reliability manager with WebSocket: {e}")
    
    def set_websocket_bridge(self, bridge: 'AgentWebSocketBridge') -> None:
        """Set AgentWebSocketBridge on registry and agents."""
        # CRITICAL: Prevent None bridge from breaking agent events
        if bridge is None:
            logger.error("🚨 CRITICAL: Attempting to set AgentWebSocketBridge to None - this breaks agent events!")
            logger.error("🚨 This prevents real-time chat notifications and agent execution updates")
            logger.error("🚨 WebSocket events are CRITICAL for 90% of chat functionality")
            raise ValueError(
                "AgentWebSocketBridge cannot be None. This breaks agent WebSocket events and prevents "
                "real-time chat updates. Check AgentWebSocketBridge initialization in startup sequence."
            )
        
        # Validate the bridge has required methods before setting
        required_methods = ['notify_agent_started', 'notify_agent_completed', 'notify_tool_executing']
        missing_methods = [method for method in required_methods if not hasattr(bridge, method)]
        if missing_methods:
            logger.error(f"🚨 CRITICAL: AgentWebSocketBridge missing required methods: {missing_methods}")
            raise ValueError(f"AgentWebSocketBridge incomplete - missing methods: {missing_methods}")
        
        self.websocket_bridge = bridge
        
        # Update reliability manager with WebSocket bridge
        if self.reliability_manager and hasattr(bridge, 'websocket_manager'):
            try:
                self.reliability_manager = create_agent_reliability_manager(
                    service_name="agent_registry",
                    websocket_manager=getattr(bridge, 'websocket_manager', self.websocket_manager),
                    websocket_notifier=bridge
                )
                logger.info("Agent registry reliability manager updated with WebSocket bridge")
            except Exception as e:
                logger.error(f"Failed to update reliability manager with WebSocket bridge: {e}")
        
        # CRITICAL: Set WebSocket bridge on tool dispatcher
        if hasattr(self, 'tool_dispatcher') and self.tool_dispatcher:
            if hasattr(self.tool_dispatcher, 'set_websocket_bridge'):
                # Use the proper method to set the bridge
                self.tool_dispatcher.set_websocket_bridge(bridge)
                logger.info("✅ Set WebSocket bridge on tool dispatcher via proper method")
            elif hasattr(self.tool_dispatcher, 'executor') and hasattr(self.tool_dispatcher.executor, 'websocket_bridge'):
                # Fallback: set directly on executor
                old_bridge = self.tool_dispatcher.executor.websocket_bridge
                self.tool_dispatcher.executor.websocket_bridge = bridge
                if old_bridge is None:
                    logger.info("✅ Set WebSocket bridge on tool dispatcher executor (fallback)")
                else:
                    logger.info("Tool dispatcher executor already has WebSocket bridge")
            else:
                logger.error("🚨 CRITICAL: Tool dispatcher doesn't support WebSocket bridge pattern")
            
            # Verify WebSocket support after setting
            if hasattr(self.tool_dispatcher, 'has_websocket_support'):
                if self.tool_dispatcher.has_websocket_support:
                    logger.info("✅ Tool dispatcher confirms WebSocket support is available")
                else:
                    logger.warning("⚠️ Tool dispatcher created without WebSocket support - may need reconfiguration")
        
        # Set WebSocket bridge on all registered agents that support it
        agent_count = 0
        for agent_name, agent in self.agents.items():
            try:
                if hasattr(agent, 'set_websocket_bridge'):
                    # Note: run_id will be set dynamically during execution, not during registration
                    agent.set_websocket_bridge(bridge, None)
                    agent_count += 1
                else:
                    logger.debug(f"Agent {agent_name} does not support WebSocket bridge pattern")
            except Exception as e:
                logger.warning(f"Failed to set WebSocket bridge for agent {agent_name}: {e}")
        
        logger.info(f"✅ WebSocket bridge set for {agent_count}/{len(self.agents)} agents")
    
    def get_websocket_bridge(self) -> Optional['AgentWebSocketBridge']:
        """Get the current AgentWebSocketBridge instance.
        
        Returns:
            The AgentWebSocketBridge instance if set, None otherwise.
        """
        return getattr(self, 'websocket_bridge', None)
    
    def diagnose_websocket_wiring(self) -> Dict[str, Any]:
        """Comprehensive diagnosis of WebSocket wiring for debugging silent failures.
        
        Returns detailed information about WebSocket integration status to help
        identify why WebSocket events might not be working.
        """
        diagnosis = {
            "registry_has_websocket_bridge": self.websocket_bridge is not None,
            "websocket_bridge_type": type(self.websocket_bridge).__name__ if self.websocket_bridge else None,
            "tool_dispatcher_present": hasattr(self, 'tool_dispatcher') and self.tool_dispatcher is not None,
            "tool_dispatcher_diagnosis": None,
            "agents_with_websocket_support": [],
            "agents_without_websocket_support": [],
            "critical_issues": []
        }
        
        # Check WebSocket bridge status
        if self.websocket_bridge is None:
            diagnosis["critical_issues"].append("AgentRegistry has no WebSocket bridge - all events will be lost")
        else:
            # Validate bridge has required methods
            required_methods = ['notify_agent_started', 'notify_agent_completed', 'notify_tool_executing']
            missing_methods = [method for method in required_methods if not hasattr(self.websocket_bridge, method)]
            if missing_methods:
                diagnosis["critical_issues"].append(f"WebSocket bridge missing methods: {missing_methods}")
        
        # Check tool dispatcher wiring
        if hasattr(self, 'tool_dispatcher') and self.tool_dispatcher:
            if hasattr(self.tool_dispatcher, 'diagnose_websocket_wiring'):
                diagnosis["tool_dispatcher_diagnosis"] = self.tool_dispatcher.diagnose_websocket_wiring()
                if diagnosis["tool_dispatcher_diagnosis"]["critical_issues"]:
                    diagnosis["critical_issues"].extend([
                        f"ToolDispatcher: {issue}" for issue in diagnosis["tool_dispatcher_diagnosis"]["critical_issues"]
                    ])
            else:
                diagnosis["critical_issues"].append("ToolDispatcher doesn't support WebSocket diagnostics")
        else:
            diagnosis["critical_issues"].append("AgentRegistry missing tool_dispatcher")
        
        # Check agent WebSocket support
        for agent_name, agent in self.agents.items():
            if hasattr(agent, 'set_websocket_bridge'):
                diagnosis["agents_with_websocket_support"].append(agent_name)
            else:
                diagnosis["agents_without_websocket_support"].append(agent_name)
        
        diagnosis["total_agents"] = len(self.agents)
        diagnosis["agents_with_support_count"] = len(diagnosis["agents_with_websocket_support"])
        diagnosis["agents_without_support_count"] = len(diagnosis["agents_without_websocket_support"])
        
        # Overall health assessment
        diagnosis["websocket_health"] = "HEALTHY" if not diagnosis["critical_issues"] else "CRITICAL"
        
        return diagnosis
    
    def create_request_scoped_factory(self) -> 'AgentInstanceFactory':
        """
        Create a request-scoped AgentInstanceFactory for proper user isolation.
        
        This method provides a migration path from the legacy AgentRegistry
        to the new architecture that prevents user context leakage.
        
        Returns:
            AgentInstanceFactory: Factory configured with this registry's components
            
        Usage:
            # Instead of: agent = registry.get("triage")
            # Use:
            factory = registry.create_request_scoped_factory()
            async with factory.user_execution_scope(user_id, thread_id, run_id) as context:
                agent = await factory.create_agent_instance("triage", context)
        """
        try:
            from netra_backend.app.agents.supervisor.agent_instance_factory import AgentInstanceFactory
            
            factory = AgentInstanceFactory()
            factory.configure(
                agent_class_registry=self._agent_class_registry,
                agent_registry=self,  # Fallback for compatibility
                websocket_bridge=self.websocket_bridge,
                websocket_manager=self.websocket_manager
            )
            
            logger.info("✅ Created request-scoped AgentInstanceFactory from legacy AgentRegistry")
            return factory
            
        except Exception as e:
            logger.error(f"Failed to create request-scoped factory: {e}")
            raise RuntimeError(f"Cannot create request-scoped factory: {e}")
    
    def get_agent_class_registry(self) -> Optional[AgentClassRegistry]:
        """Get the underlying AgentClassRegistry for new architecture migration."""
        return self._agent_class_registry
    
    # === Migration Helper Methods ===
    
    def get_infrastructure_registry(self) -> Optional[AgentClassRegistry]:
        """Get the infrastructure-only registry (migration helper).
        
        Returns the global singleton AgentClassRegistry that stores agent classes
        without per-user state. This is the preferred registry for new architecture.
        
        Returns:
            AgentClassRegistry instance if available, None otherwise
        """
        if self._agent_class_registry:
            return self._agent_class_registry
        
        try:
            return get_agent_class_registry()
        except Exception as e:
            logger.warning(f"Could not get infrastructure registry: {e}")
            return None
    
    def create_request_factory(self, user_context: 'UserExecutionContext') -> 'AgentInstanceFactory':
        """Create per-request factory for user isolation (migration helper).
        
        Creates an AgentInstanceFactory configured for the specific user context.
        This factory creates fresh agent instances per request with complete isolation.
        
        Args:
            user_context: User execution context for the request
            
        Returns:
            Configured AgentInstanceFactory for the request
            
        Raises:
            ImportError: If AgentInstanceFactory not available
            ValueError: If configuration fails
        """
        try:
            from netra_backend.app.agents.supervisor.agent_instance_factory import (
                AgentInstanceFactory, 
                get_agent_instance_factory
            )
            
            # Get or create factory instance
            factory = get_agent_instance_factory()
            
            # Configure factory with current infrastructure components
            if not hasattr(factory, '_websocket_bridge') or not factory._websocket_bridge:
                factory.configure(
                    agent_class_registry=self._agent_class_registry,
                    agent_registry=self,  # Provide legacy registry for compatibility
                    websocket_bridge=self.websocket_bridge,
                    websocket_manager=self.websocket_manager
                )
                logger.info("✅ Configured AgentInstanceFactory with legacy AgentRegistry components")
            
            return factory
            
        except ImportError as e:
            logger.error(f"AgentInstanceFactory not available: {e}")
            raise ImportError("Cannot create request factory - AgentInstanceFactory not available")
        except Exception as e:
            logger.error(f"Failed to create request factory: {e}")
            raise ValueError(f"Request factory creation failed: {e}")
    
    def migrate_to_new_architecture(self) -> Dict[str, Any]:
        """Migrate agent registrations to new architecture (migration helper).
        
        This method helps transition from the old AgentRegistry to the new
        AgentClassRegistry + AgentInstanceFactory pattern by:
        1. Registering all agent classes in AgentClassRegistry
        2. Providing migration status and recommendations
        
        Returns:
            Dictionary with migration status and recommendations
        """
        from datetime import datetime, timezone
        
        migration_status = {
            'agent_classes_migrated': 0,
            'migration_errors': [],
            'recommendations': [],
            'infrastructure_registry_available': False,
            'legacy_agents_count': len(self.agents),
            'migration_complete': False
        }
        
        # Check if infrastructure registry is available - use instance registry first
        infrastructure_registry = self._agent_class_registry
        if not infrastructure_registry:
            # Fallback to get_infrastructure_registry
            infrastructure_registry = self.get_infrastructure_registry()
        
        if not infrastructure_registry:
            migration_status['migration_errors'].append("AgentClassRegistry not available")
            return migration_status
        
        migration_status['infrastructure_registry_available'] = True
        
        # Migrate agent classes
        for agent_name, agent_instance in self.agents.items():
            try:
                agent_class = type(agent_instance)
                
                # Skip if already registered
                if infrastructure_registry.has_agent_class(agent_name):
                    logger.debug(f"Agent class {agent_name} already registered in infrastructure registry")
                    migration_status['agent_classes_migrated'] += 1
                    continue
                
                # Register agent class
                infrastructure_registry.register(
                    name=agent_name,
                    agent_class=agent_class,
                    description=getattr(agent_instance, 'description', f"{agent_class.__name__} agent"),
                    version=getattr(agent_instance, 'version', '1.0.0'),
                    dependencies=getattr(agent_instance, 'dependencies', []),
                    metadata={
                        'migrated_from_legacy_registry': True,
                        'migration_timestamp': datetime.now(timezone.utc).isoformat(),
                        'original_instance_id': id(agent_instance)
                    }
                )
                
                migration_status['agent_classes_migrated'] += 1
                logger.info(f"✅ Migrated agent class {agent_name} to infrastructure registry")
                
            except Exception as e:
                error_msg = f"Failed to migrate agent {agent_name}: {e}"
                migration_status['migration_errors'].append(error_msg)
                logger.error(error_msg)
        
        # Provide recommendations
        if migration_status['agent_classes_migrated'] == migration_status['legacy_agents_count']:
            migration_status['migration_complete'] = True
            migration_status['recommendations'].extend([
                "All agent classes successfully migrated to AgentClassRegistry",
                "Update calling code to use AgentInstanceFactory.create_agent_instance()",
                "Stop using AgentRegistry.get() for agent instances",
                "Use UserExecutionContext for proper user isolation",
                "Consider freezing AgentClassRegistry after startup with .freeze()"
            ])
        else:
            migration_status['recommendations'].extend([
                f"Only {migration_status['agent_classes_migrated']}/{migration_status['legacy_agents_count']} agents migrated",
                "Review migration errors and fix agent class registration issues",
                "Some agents may require manual migration"
            ])
        
        if migration_status['migration_errors']:
            migration_status['recommendations'].append(
                "Address migration errors before fully transitioning to new architecture"
            )
        
        logger.info(f"Agent registry migration status: {migration_status['agent_classes_migrated']} classes migrated, "
                   f"{len(migration_status['migration_errors'])} errors")
        
        return migration_status
    
    # === Factory Pattern Integration Methods ===
    
    def configure_factory_adapter(self, factory_adapter: 'FactoryAdapter') -> None:
        """Configure registry to work with FactoryAdapter for seamless migration.
        
        Args:
            factory_adapter: FactoryAdapter instance for migration support
        """
        try:
            self._factory_adapter = factory_adapter
            logger.info("✅ AgentRegistry configured with FactoryAdapter for seamless migration")
        except Exception as e:
            logger.error(f"Failed to configure FactoryAdapter: {e}")
            raise RuntimeError(f"FactoryAdapter configuration failed: {e}")
    
    def get_factory_compatible_execution_engine(self, 
                                               user_context: Optional['UserExecutionContext'] = None,
                                               **legacy_kwargs) -> 'ExecutionEngine':
        """Get execution engine compatible with factory patterns.
        
        This method provides a bridge for existing code to get execution engines
        that work with both legacy and factory patterns.
        
        Args:
            user_context: Optional UserExecutionContext for factory pattern
            **legacy_kwargs: Legacy parameters for backward compatibility
            
        Returns:
            ExecutionEngine: Engine instance compatible with factory patterns
        """
        try:
            # If we have a factory adapter, use it to get the appropriate engine
            if hasattr(self, '_factory_adapter') and self._factory_adapter:
                request_context = None
                if user_context:
                    request_context = {
                        'user_id': user_context.user_id,
                        'request_id': user_context.run_id,
                        'thread_id': user_context.thread_id,
                        'registry': self,
                        'websocket_bridge': self.websocket_bridge
                    }
                
                # Use factory adapter to get appropriate engine
                return self._factory_adapter.get_execution_engine(
                    request_context=request_context,
                    **legacy_kwargs
                )
            else:
                # Create legacy execution engine
                from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
                return ExecutionEngine(self, self.websocket_bridge, user_context)
                
        except Exception as e:
            logger.error(f"Failed to get factory-compatible execution engine: {e}")
            # Fallback to direct creation
            from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
            return ExecutionEngine(self, self.websocket_bridge, user_context)
    
    def create_user_execution_context(self, 
                                    user_id: str, 
                                    thread_id: str,
                                    run_id: Optional[str] = None,
                                    session_id: Optional[str] = None) -> 'UserExecutionContext':
        """Create a UserExecutionContext for factory pattern migration.
        
        Args:
            user_id: Unique user identifier
            thread_id: Thread identifier for WebSocket routing
            run_id: Optional run identifier
            session_id: Optional session identifier
            
        Returns:
            UserExecutionContext: Context for user-isolated execution
        """
        try:
            from netra_backend.app.agents.supervisor.execution_factory import UserExecutionContext
            import uuid
            
            if not run_id:
                run_id = f"run_{user_id}_{int(time.time() * 1000)}"
            
            context = UserExecutionContext(
                user_id=user_id,
                request_id=run_id,
                thread_id=thread_id,
                session_id=session_id
            )
            
            logger.debug(f"Created UserExecutionContext for user {user_id}")
            return context
            
        except ImportError as e:
            logger.error(f"UserExecutionContext not available: {e}")
            raise ImportError("Factory patterns not available - ensure execution_factory.py is present")
        except Exception as e:
            logger.error(f"Failed to create UserExecutionContext: {e}")
            raise ValueError(f"UserExecutionContext creation failed: {e}")
    
    async def execute_with_user_isolation(self, 
                                        agent_name: str,
                                        user_id: str,
                                        thread_id: str,
                                        state: 'DeepAgentState',
                                        run_id: Optional[str] = None) -> 'AgentExecutionResult':
        """Execute agent with complete user isolation using factory patterns.
        
        This method provides a high-level interface for executing agents with
        complete user isolation, automatically handling context creation and cleanup.
        
        Args:
            agent_name: Name of the agent to execute
            user_id: Unique user identifier
            thread_id: Thread identifier for WebSocket routing
            state: Agent state containing user message, context, etc.
            run_id: Optional run identifier
            
        Returns:
            AgentExecutionResult: Results of agent execution
        """
        try:
            # Create user execution context
            user_context = self.create_user_execution_context(
                user_id=user_id,
                thread_id=thread_id,
                run_id=run_id
            )
            
            # Get factory-compatible execution engine
            execution_engine = self.get_factory_compatible_execution_engine(
                user_context=user_context
            )
            
            # Create execution context
            from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
            from datetime import datetime, timezone
            
            execution_context = AgentExecutionContext(
                run_id=user_context.request_id,
                agent_name=agent_name,
                state=state,
                user_id=user_id,
                thread_id=thread_id,
                started_at=datetime.now(timezone.utc)
            )
            
            # Execute agent with isolation
            result = await execution_engine.execute_agent(execution_context, state)
            
            logger.info(f"✅ Agent {agent_name} executed with user isolation for user {user_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to execute agent {agent_name} with user isolation: {e}")
            raise RuntimeError(f"User-isolated agent execution failed: {e}")
        finally:
            # Clean up user context if it was created
            if 'user_context' in locals():
                try:
                    await user_context.cleanup()
                except Exception as cleanup_error:
                    logger.warning(f"User context cleanup failed: {cleanup_error}")
    
    def get_factory_integration_status(self) -> Dict[str, Any]:
        """Get status of factory pattern integration.
        
        Returns:
            Dictionary with integration status and recommendations
        """
        from datetime import datetime, timezone
        
        status = {
            'factory_adapter_configured': hasattr(self, '_factory_adapter') and self._factory_adapter is not None,
            'infrastructure_registry_available': self._agent_class_registry is not None,
            'websocket_bridge_available': self.websocket_bridge is not None,
            'agents_count': len(self.agents),
            'integration_features': {
                'user_execution_context': True,  # Always available through import
                'factory_compatible_engine': True,
                'user_isolated_execution': True
            },
            'migration_recommendations': [],
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        # Provide recommendations
        if not status['factory_adapter_configured']:
            status['migration_recommendations'].append(
                "Configure FactoryAdapter with configure_factory_adapter() for seamless migration"
            )
        
        if not status['infrastructure_registry_available']:
            status['migration_recommendations'].append(
                "Infrastructure registry not available - some factory features may be limited"
            )
        
        if status['factory_adapter_configured'] and status['infrastructure_registry_available']:
            status['migration_recommendations'].extend([
                "Factory pattern integration is ready",
                "Use execute_with_user_isolation() for user-isolated agent execution",
                "Consider migrating existing code to factory patterns",
                "Use get_factory_compatible_execution_engine() for gradual migration"
            ])
        
        return status