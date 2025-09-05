"""Agent registry using UniversalRegistry SSOT pattern.

This module now uses the UniversalRegistry pattern for ALL agent registration
and management, providing thread-safe operations and factory pattern support.
"""

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Type
import time
from datetime import datetime, timezone

# SSOT: Import from UniversalRegistry
from netra_backend.app.core.registry.universal_registry import (
    AgentRegistry as UniversalAgentRegistry,
    get_global_registry
)

if TYPE_CHECKING:
    from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
    from netra_backend.app.llm.llm_manager import LLMManager
    from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
    from netra_backend.app.websocket_core.manager import WebSocketManager
    from netra_backend.app.agents.supervisor.execution_factory import UserExecutionContext
    from netra_backend.app.agents.base_agent import BaseAgent

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class AgentRegistry(UniversalAgentRegistry):
    """Agent registry using UniversalRegistry SSOT pattern.
    
    This class extends the UniversalAgentRegistry from universal_registry.py,
    adding backward compatibility methods while using the SSOT implementation.
    """
    
    def __init__(self, llm_manager: 'LLMManager', tool_dispatcher: 'ToolDispatcher'):
        """Initialize agent registry with SSOT pattern."""
        # Initialize UniversalAgentRegistry
        super().__init__()
        
        self.llm_manager = llm_manager
        self.tool_dispatcher = tool_dispatcher
        self._agents_registered = False
        self.registration_errors: Dict[str, str] = {}
        
        logger.info("AgentRegistry initialized with UniversalRegistry SSOT pattern")
    
    def register_default_agents(self) -> None:
        """Register default sub-agents."""
        if self._agents_registered:
            logger.debug("Agents already registered, skipping re-registration")
            return
        
        self._register_core_agents()
        self._register_auxiliary_agents()
        self._agents_registered = True
        
        logger.info(f"✅ Registered {len(self.list_keys())} default agents using UniversalRegistry")
    
    def _register_core_agents(self) -> None:
        """Register core workflow agents."""
        try:
            # Import agents lazily to avoid circular dependencies
            from netra_backend.app.agents.data.unified_data_agent import UnifiedDataAgent
            from netra_backend.app.agents.triage.unified_triage_agent import UnifiedTriageAgent
            from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext
            
            # Create mock context for factory registration
            def create_triage_agent(context: UserExecutionContext):
                return UnifiedTriageAgent(
                    llm_manager=self.llm_manager,
                    tool_dispatcher=self.tool_dispatcher,
                    context=context,
                    execution_priority=0
                )
            
            def create_data_agent(context: UserExecutionContext):
                return UnifiedDataAgent(
                    context=context,
                    llm_manager=self.llm_manager
                )
            
            # Register factories for user isolation
            self.register_factory("triage", create_triage_agent, 
                                tags=["core", "workflow"],
                                description="Triage agent for request routing")
            self.register_factory("data", create_data_agent,
                                tags=["core", "workflow"],
                                description="Data processing agent")
            
            self._register_optimization_agents()
            
        except Exception as e:
            logger.error(f"Failed to register core agents: {e}")
            self.registration_errors["core_agents"] = str(e)
    
    def _register_optimization_agents(self) -> None:
        """Register optimization and action agents."""
        try:
            from netra_backend.app.agents.optimizations_core_sub_agent import OptimizationsCoreSubAgent
            from netra_backend.app.agents.actions_to_meet_goals_sub_agent import ActionsToMeetGoalsSubAgent
            
            def create_optimization_agent(context: UserExecutionContext):
                return OptimizationsCoreSubAgent(
                    self.llm_manager,
                    self.tool_dispatcher
                )
            
            def create_actions_agent(context: UserExecutionContext):
                return ActionsToMeetGoalsSubAgent(
                    self.llm_manager,
                    self.tool_dispatcher
                )
            
            self.register_factory("optimization", create_optimization_agent,
                                tags=["optimization"],
                                description="Optimization strategy agent")
            self.register_factory("actions", create_actions_agent,
                                tags=["execution"],
                                description="Action execution agent")
            
        except Exception as e:
            logger.error(f"Failed to register optimization agents: {e}")
            self.registration_errors["optimization_agents"] = str(e)
    
    def _register_auxiliary_agents(self) -> None:
        """Register auxiliary agents."""
        self._register_reporting_agent()
        self._register_goals_triage_agent()
        self._register_data_helper_agent()
        self._register_synthetic_data_agent()
        self._register_corpus_admin_agent()
    
    def _register_reporting_agent(self) -> None:
        """Register reporting agent."""
        try:
            from netra_backend.app.agents.reporting_sub_agent import ReportingSubAgent
            
            def create_reporting_agent(context: UserExecutionContext):
                return ReportingSubAgent(self.llm_manager, self.tool_dispatcher)
            
            self.register_factory("reporting", create_reporting_agent,
                                tags=["auxiliary", "reporting"],
                                description="Report generation agent")
        except Exception as e:
            logger.error(f"Failed to register reporting agent: {e}")
            self.registration_errors["reporting"] = str(e)
    
    def _register_goals_triage_agent(self) -> None:
        """Register goals triage agent."""
        try:
            from netra_backend.app.agents.goals_triage_sub_agent import GoalsTriageSubAgent
            
            def create_goals_agent(context: UserExecutionContext):
                return GoalsTriageSubAgent(self.llm_manager, self.tool_dispatcher)
            
            self.register_factory("goals_triage", create_goals_agent,
                                tags=["auxiliary", "triage"],
                                description="Goals triage agent")
        except Exception as e:
            logger.error(f"Failed to register goals triage agent: {e}")
            self.registration_errors["goals_triage"] = str(e)
    
    def _register_synthetic_data_agent(self) -> None:
        """Register synthetic data agent."""
        try:
            from netra_backend.app.agents.synthetic_data_sub_agent import SyntheticDataSubAgent
            
            def create_synthetic_agent(context: UserExecutionContext):
                return SyntheticDataSubAgent(self.llm_manager, self.tool_dispatcher)
            
            self.register_factory("synthetic_data", create_synthetic_agent,
                                tags=["auxiliary", "data"],
                                description="Synthetic data generation agent")
        except Exception as e:
            logger.error(f"Failed to register synthetic data agent: {e}")
            self.registration_errors["synthetic_data"] = str(e)
    
    def _register_data_helper_agent(self) -> None:
        """Register data helper agent."""
        try:
            from netra_backend.app.agents.data_helper_agent import DataHelperAgent
            
            def create_helper_agent(context: UserExecutionContext):
                return DataHelperAgent(self.llm_manager, self.tool_dispatcher)
            
            self.register_factory("data_helper", create_helper_agent,
                                tags=["auxiliary", "data"],
                                description="Data helper agent")
        except Exception as e:
            logger.error(f"Failed to register data helper agent: {e}")
            self.registration_errors["data_helper"] = str(e)
    
    def _register_corpus_admin_agent(self) -> None:
        """Register corpus admin agent."""
        try:
            from netra_backend.app.admin.corpus import CorpusAdminSubAgent
            
            def create_corpus_agent(context: UserExecutionContext):
                return CorpusAdminSubAgent(self.llm_manager, self.tool_dispatcher)
            
            self.register_factory("corpus_admin", create_corpus_agent,
                                tags=["auxiliary", "admin"],
                                description="Corpus administration agent")
        except Exception as e:
            logger.error(f"Failed to register corpus admin agent: {e}")
            self.registration_errors["corpus_admin"] = str(e)
    
    # ===================== BACKWARD COMPATIBILITY =====================
    
    def register(self, name: str, agent: 'BaseAgent') -> None:
        """Register agent for backward compatibility.
        
        NOTE: This now uses UniversalRegistry's register method.
        """
        try:
            # Register as singleton in UniversalRegistry
            super().register(name, agent, source="legacy_register")
            
            # Clear registration errors
            self.registration_errors.pop(name, None)
            logger.debug(f"Registered agent '{name}' using UniversalRegistry SSOT")
            
        except Exception as e:
            logger.error(f"Failed to register agent {name}: {e}")
            self.registration_errors[name] = str(e)
    
    async def register_agent_safely(self, name: str, agent_class: Type['BaseAgent'], **kwargs) -> bool:
        """Register an agent safely with error handling."""
        try:
            logger.info(f"Attempting to register agent: {name}")
            
            # Create agent instance
            agent = agent_class(
                self.llm_manager,
                self.tool_dispatcher,
                **kwargs
            )
            
            # Register using UniversalRegistry
            self.register(name, agent)
            
            logger.info(f"Successfully registered agent: {name}")
            return True
            
        except Exception as e:
            error_msg = f"Failed to register agent {name}: {str(e)}"
            logger.error(error_msg)
            self.registration_errors[name] = error_msg
            return False
    
    def get_registry_health(self) -> Dict[str, Any]:
        """Get registry health using UniversalRegistry's health check."""
        # Get health from UniversalRegistry
        health = self.validate_health()
        
        # Add legacy compatibility fields
        health.update({
            "total_agents": len(self.list_keys()),
            "failed_registrations": len(self.registration_errors),
            "registration_errors": self.registration_errors.copy(),
            "death_detection_enabled": True,
            "using_universal_registry": True
        })
        
        return health
    
    def list_agents(self) -> List[str]:
        """List registered agent names."""
        return self.list_keys()
    
    def remove_agent(self, name: str) -> bool:
        """Remove an agent from registry."""
        return self.remove(name)
    
    async def get_agent(self, name: str, context: Optional['UserExecutionContext'] = None) -> Optional['BaseAgent']:
        """Get agent with optional context for factory creation."""
        return self.get(name, context)
    
    async def reset_all_agents(self) -> Dict[str, Any]:
        """Reset is not needed with factory pattern - returns success."""
        return {
            'total_agents': len(self.list_keys()),
            'successful_resets': len(self.list_keys()),
            'failed_resets': 0,
            'agents_without_reset': 0,
            'reset_details': {
                name: {'status': 'factory_pattern', 'note': 'Fresh instances per request'}
                for name in self.list_keys()
            },
            'using_universal_registry': True
        }
    
    def diagnose_websocket_wiring(self) -> Dict[str, Any]:
        """Comprehensive diagnosis of WebSocket wiring."""
        diagnosis = {
            "registry_has_websocket_bridge": self.websocket_bridge is not None,
            "registry_has_websocket_manager": self.websocket_manager is not None,
            "total_agents": len(self.list_keys()),
            "using_universal_registry": True,
            "critical_issues": []
        }
        
        if self.websocket_bridge is None:
            diagnosis["critical_issues"].append("No WebSocket bridge configured")
        
        if self.websocket_manager is None:
            diagnosis["critical_issues"].append("No WebSocket manager configured")
        
        diagnosis["websocket_health"] = "HEALTHY" if not diagnosis["critical_issues"] else "CRITICAL"
        
        return diagnosis
    
    def get_factory_integration_status(self) -> Dict[str, Any]:
        """Get factory pattern status."""
        return {
            'using_universal_registry': True,
            'factory_patterns_enabled': True,
            'total_factories': len([k for k in self.list_keys()]),
            'thread_safe': True,
            'metrics_enabled': self.enable_metrics,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }


# ===================== MODULE EXPORTS =====================

def get_agent_registry(llm_manager: 'LLMManager', tool_dispatcher: 'ToolDispatcher') -> AgentRegistry:
    """Get or create agent registry using SSOT pattern.
    
    This uses the global registry from UniversalRegistry.
    """
    try:
        # Try to get existing global registry
        global_registry = get_global_registry('agent')
        
        # Ensure it has the required attributes
        if not hasattr(global_registry, 'llm_manager'):
            global_registry.llm_manager = llm_manager
            global_registry.tool_dispatcher = tool_dispatcher
        
        # Return as AgentRegistry for compatibility
        if isinstance(global_registry, AgentRegistry):
            return global_registry
        else:
            # Wrap if needed
            registry = AgentRegistry(llm_manager, tool_dispatcher)
            return registry
            
    except Exception:
        # Create new registry
        return AgentRegistry(llm_manager, tool_dispatcher)


__all__ = ['AgentRegistry', 'get_agent_registry']