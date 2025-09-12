"""
Agent Class Registry Initialization Helper.

CRITICAL: This module demonstrates how to properly initialize the AgentClassRegistry
during application startup. This is the ONLY place where agent classes should be
registered - ensuring immutability after startup.

Business Value: Centralized agent class registration that:
- Ensures all agent types are available system-wide
- Prevents runtime registration that could destabilize the system
- Provides a single point for agent type management
- Enables predictable agent instantiation patterns

Usage: Called once during application startup to populate the registry.
"""

from typing import Optional, Dict, Any, List
from netra_backend.app.agents.supervisor.agent_class_registry import (
    get_agent_class_registry,
    AgentClassRegistry
)
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


def initialize_agent_class_registry() -> AgentClassRegistry:
    """
    Initialize the global agent class registry with all available agent types.
    
    CRITICAL: This function should be called ONCE during application startup,
    before any agent instantiation occurs. After this function completes,
    the registry becomes immutable.
    
    Returns:
        The initialized and frozen AgentClassRegistry
        
    Raises:
        RuntimeError: If registry initialization fails
    """
    try:
        registry = get_agent_class_registry()
        
        if registry.is_frozen():
            logger.info("AgentClassRegistry already initialized and frozen")
            return registry
        
        logger.info("Initializing AgentClassRegistry with core agent types...")
        
        # Register core workflow agents
        _register_core_agents(registry)
        
        # Register specialized agents  
        _register_specialized_agents(registry)
        
        # Register auxiliary agents
        _register_auxiliary_agents(registry)
        
        # Freeze registry to make it immutable
        registry.freeze()
        
        # Validate the registry
        _validate_registry(registry)
        
        logger.info(f"AgentClassRegistry successfully initialized with {len(registry)} agent types")
        return registry
        
    except Exception as e:
        logger.error(f"Failed to initialize AgentClassRegistry: {e}")
        raise RuntimeError(f"Agent class registry initialization failed: {e}")


def _register_core_agents(registry: AgentClassRegistry) -> None:
    """Register core workflow agents."""
    try:
        # Import core agents - using delayed imports to avoid circular dependencies
        from netra_backend.app.agents.triage.unified_triage_agent import UnifiedTriageAgent
        from netra_backend.app.agents.data_sub_agent import DataSubAgent
        from netra_backend.app.agents.optimizations_core_sub_agent import OptimizationsCoreSubAgent
        from netra_backend.app.agents.actions_to_meet_goals_sub_agent import ActionsToMeetGoalsSubAgent
        from netra_backend.app.agents.reporting_sub_agent import ReportingSubAgent
        from netra_backend.app.agents.supervisor_ssot import SupervisorAgent
        
        # Register core workflow agents
        registry.register(
            "triage",
            UnifiedTriageAgent,
            "Handles user request triage and classification",
            version="2.0.0",
            dependencies=[],
            metadata={
                "category": "core",
                "priority": "critical",
                "workflow_stage": "initial"
            }
        )
        
        registry.register(
            "data",
            DataSubAgent,
            "Processes data operations and analysis requests",
            version="2.1.0", 
            dependencies=["triage"],
            metadata={
                "category": "core",
                "priority": "critical",
                "workflow_stage": "processing"
            }
        )
        
        registry.register(
            "optimization",
            OptimizationsCoreSubAgent,
            "Provides AI optimization recommendations and analysis",
            version="1.5.0",
            dependencies=["data"],
            metadata={
                "category": "core",
                "priority": "high",
                "workflow_stage": "optimization"
            }
        )
        
        registry.register(
            "actions",
            ActionsToMeetGoalsSubAgent,
            "Generates actionable steps to meet user goals",
            version="1.3.0",
            dependencies=["optimization"],
            metadata={
                "category": "core",
                "priority": "high", 
                "workflow_stage": "action_planning"
            }
        )
        
        registry.register(
            "reporting",
            ReportingSubAgent,
            "Creates comprehensive reports and summaries",
            version="1.2.0",
            dependencies=["actions"],
            metadata={
                "category": "core",
                "priority": "medium",
                "workflow_stage": "reporting"
            }
        )
        
        registry.register(
            "supervisor_orchestration",
            SupervisorAgent,
            "Orchestrates agent workflows and manages execution coordination",
            version="2.0.0",
            dependencies=[],
            metadata={
                "category": "core",
                "priority": "critical",
                "workflow_stage": "orchestration"
            }
        )
        
        logger.info("Core agents registered successfully")
        
    except ImportError as e:
        logger.error(f"Failed to import core agent: {e}")
        raise
    except Exception as e:
        logger.error(f"Failed to register core agents: {e}")
        raise


def _register_specialized_agents(registry: AgentClassRegistry) -> None:
    """Register specialized domain agents."""
    registration_failures = []
    
    # Try to import and register each specialized agent individually
    # This ensures partial failures don't prevent other agents from registering
    
    # Corpus Admin Agent
    try:
        from netra_backend.app.admin.corpus import CorpusAdminSubAgent
        
        registry.register(
            "corpus_admin",
            CorpusAdminSubAgent,
            "Manages corpus administration and document processing",
            version="1.4.0",
            dependencies=["data"],
            metadata={
                "category": "specialized",
                "priority": "medium",
                "domain": "corpus_management"
            }
        )
        logger.info("  [U+2713] Registered corpus_admin agent")
    except ImportError as e:
        registration_failures.append(f"corpus_admin: {e}")
        logger.warning(f"   WARNING:  Failed to import corpus_admin agent: {e}")
    except Exception as e:
        registration_failures.append(f"corpus_admin: {e}")
        logger.error(f"   FAIL:  Failed to register corpus_admin agent: {e}")
        
    # Supply Researcher Agent
    try:
        from netra_backend.app.agents.supply_researcher.agent import SupplyResearcherAgent
        registry.register(
            "supply_researcher",
            SupplyResearcherAgent,
            "Researches supply chain and market intelligence",
            version="1.1.0",
            dependencies=["data"],
            metadata={
                "category": "specialized", 
                "priority": "medium",
                "domain": "supply_research"
            }
        )
        logger.info("  [U+2713] Registered supply_researcher agent")
    except ImportError as e:
        registration_failures.append(f"supply_researcher: {e}")
        logger.warning(f"   WARNING:  Failed to import supply_researcher agent: {e}")
    except Exception as e:
        registration_failures.append(f"supply_researcher: {e}")
        logger.error(f"   FAIL:  Failed to register supply_researcher agent: {e}")
        
    # GitHub Analyzer Agent
    try:
        from netra_backend.app.agents.github_analyzer.agent import GitHubAnalyzerAgent
        registry.register(
            "github_analyzer",
            GitHubAnalyzerAgent,
            "Analyzes GitHub repositories and code patterns",
            version="1.0.0",
            dependencies=["data"],
            metadata={
                "category": "specialized",
                "priority": "low",
                "domain": "code_analysis"
            }
        )
        logger.info("  [U+2713] Registered github_analyzer agent")
    except ImportError as e:
        registration_failures.append(f"github_analyzer: {e}")
        logger.warning(f"   WARNING:  Failed to import github_analyzer agent: {e}")
    except Exception as e:
        registration_failures.append(f"github_analyzer: {e}")
        logger.error(f"   FAIL:  Failed to register github_analyzer agent: {e}")
        
    # Synthetic Data Agent - CRITICAL for data generation workflows
    try:
        from netra_backend.app.agents.synthetic_data_sub_agent import SyntheticDataSubAgent
        registry.register(
            "synthetic_data",
            SyntheticDataSubAgent,
            "Generates synthetic data for testing and training",
            version="1.2.0",
            dependencies=["data"],
            metadata={
                "category": "specialized",
                "priority": "high",  # Elevated priority - required for data workflows
                "domain": "data_generation",
                "critical": True  # Mark as critical agent
            }
        )
        logger.info("  [U+2713] Registered synthetic_data agent")
    except ImportError as e:
        registration_failures.append(f"synthetic_data (CRITICAL): {e}")
        logger.error(f"   FAIL:  CRITICAL: Failed to import synthetic_data agent: {e}")
        # Log detailed import error for debugging
        import traceback
        logger.error(f"  Import traceback:\n{traceback.format_exc()}")
    except Exception as e:
        registration_failures.append(f"synthetic_data (CRITICAL): {e}")
        logger.error(f"   FAIL:  CRITICAL: Failed to register synthetic_data agent: {e}")
    
    # Summary of registration results
    if registration_failures:
        logger.warning(f"Specialized agent registration completed with {len(registration_failures)} failures:")
        for failure in registration_failures:
            logger.warning(f"    - {failure}")
        
        # Check if any critical agents failed
        critical_failures = [f for f in registration_failures if "CRITICAL" in f]
        if critical_failures:
            logger.error(f"CRITICAL agents failed to register: {critical_failures}")
            # Note: Not raising here to allow partial functionality
            # but logging prominently for monitoring
    else:
        logger.info("All specialized agents registered successfully")


def _register_auxiliary_agents(registry: AgentClassRegistry) -> None:
    """Register auxiliary helper agents."""
    try:
        # Import auxiliary agents
        from netra_backend.app.agents.goals_triage_sub_agent import GoalsTriageSubAgent
        from netra_backend.app.agents.data_helper_agent import DataHelperAgent
        from netra_backend.app.agents.validation_sub_agent import ValidationSubAgent
        
        registry.register(
            "goals_triage",
            GoalsTriageSubAgent,
            "Performs goal-based triage and prioritization",
            version="1.1.0",
            dependencies=["triage"],
            metadata={
                "category": "auxiliary",
                "priority": "medium",
                "helper_type": "triage_support"
            }
        )
        
        registry.register(
            "data_helper",
            DataHelperAgent,
            "Provides data processing assistance and utilities",
            version="1.0.0",
            dependencies=["data"],
            metadata={
                "category": "auxiliary",
                "priority": "low",
                "helper_type": "data_support"
            }
        )
        
        registry.register(
            "validation",
            ValidationSubAgent,
            "Validates data quality and processing results",
            version="1.0.0",
            dependencies=["data"],
            metadata={
                "category": "auxiliary",
                "priority": "low",
                "helper_type": "validation_support"
            }
        )
        
        logger.info("Auxiliary agents registered successfully")
        
    except ImportError as e:
        logger.warning(f"Some auxiliary agents not available: {e}")
        # Continue initialization - auxiliary agents are optional
    except Exception as e:
        logger.error(f"Failed to register auxiliary agents: {e}")
        raise


def _validate_registry(registry: AgentClassRegistry) -> None:
    """Validate the initialized registry."""
    # Check minimum required agents
    required_agents = ["triage", "data", "optimization", "actions", "reporting", "supervisor_orchestration"]
    missing_required = []
    
    for agent_name in required_agents:
        if not registry.has_agent_class(agent_name):
            missing_required.append(agent_name)
    
    if missing_required:
        raise RuntimeError(f"Required agents not registered: {missing_required}")
    
    # Validate dependencies
    missing_deps = registry.validate_dependencies()
    if missing_deps:
        logger.warning(f"Some agents have missing dependencies: {missing_deps}")
        # Don't fail initialization - log warning instead
    
    # Check registry health
    stats = registry.get_registry_stats()
    if stats["health_status"] != "healthy":
        logger.warning(f"Registry health status: {stats['health_status']}")
    
    logger.info(f"Registry validation passed: {len(registry)} agents registered")


def get_agent_types_summary() -> Dict[str, Any]:
    """
    Get a summary of all registered agent types.
    
    Returns:
        Dictionary with agent type information organized by category
    """
    registry = get_agent_class_registry()
    
    if not registry.is_frozen():
        logger.warning("Registry not yet initialized - returning empty summary")
        return {"status": "not_initialized", "agents": {}}
    
    summary = {
        "status": "initialized",
        "total_agents": len(registry),
        "categories": {},
        "workflow_stages": {},
        "dependency_graph": {}
    }
    
    # Organize by category
    for name in registry.list_agent_names():
        agent_info = registry.get_agent_info(name)
        if not agent_info:
            continue
            
        category = agent_info.metadata.get("category", "unknown")
        if category not in summary["categories"]:
            summary["categories"][category] = []
        
        summary["categories"][category].append({
            "name": name,
            "class": agent_info.agent_class.__name__,
            "description": agent_info.description,
            "version": agent_info.version,
            "priority": agent_info.metadata.get("priority", "unknown")
        })
        
        # Workflow stages
        workflow_stage = agent_info.metadata.get("workflow_stage")
        if workflow_stage:
            if workflow_stage not in summary["workflow_stages"]:
                summary["workflow_stages"][workflow_stage] = []
            summary["workflow_stages"][workflow_stage].append(name)
        
        # Dependency relationships
        if agent_info.dependencies:
            summary["dependency_graph"][name] = list(agent_info.dependencies)
    
    return summary


def list_available_agents() -> List[str]:
    """
    Get a list of all available agent types.
    
    Returns:
        List of agent names sorted alphabetically
    """
    registry = get_agent_class_registry()
    return registry.list_agent_names()


def get_agent_class_by_name(name: str):
    """
    Get an agent class by name for instantiation.
    
    Args:
        name: Name of the agent class
        
    Returns:
        Agent class if found, None otherwise
    """
    registry = get_agent_class_registry()
    return registry.get_agent_class(name)


def is_agent_type_available(name: str) -> bool:
    """
    Check if an agent type is available.
    
    Args:
        name: Name of the agent type to check
        
    Returns:
        True if agent type is available, False otherwise
    """
    registry = get_agent_class_registry()
    return registry.has_agent_class(name)


# Utility functions for integration with existing AgentRegistry

def populate_agent_registry_from_class_registry(agent_registry, llm_manager, tool_dispatcher) -> None:
    """
    Populate an existing AgentRegistry with instances from the AgentClassRegistry.
    
    This function bridges the new AgentClassRegistry (infrastructure) with the 
    existing AgentRegistry (runtime instances).
    
    Args:
        agent_registry: The runtime AgentRegistry to populate
        llm_manager: LLM manager for agent initialization
        tool_dispatcher: Tool dispatcher for agent initialization
    """
    class_registry = get_agent_class_registry()
    
    if not class_registry.is_frozen():
        logger.warning("AgentClassRegistry not initialized - cannot populate AgentRegistry")
        return
    
    logger.info("Populating AgentRegistry from AgentClassRegistry...")
    
    # Get all agent classes and instantiate them
    success_count = 0
    error_count = 0
    
    for agent_name in class_registry.list_agent_names():
        try:
            agent_class = class_registry.get_agent_class(agent_name)
            if not agent_class:
                logger.error(f"Failed to get agent class for {agent_name}")
                error_count += 1
                continue
            
            # Create agent instance - handle different constructor patterns
            # Try UserExecutionContext pattern first (new agents like TriageSubAgent)
            try:
                agent_instance = agent_class()  # UserExecutionContext pattern
            except TypeError:
                # Fallback to legacy pattern for older agents
                agent_instance = agent_class(llm_manager, tool_dispatcher)
            
            # Register with runtime registry
            agent_registry.register(agent_name, agent_instance)
            success_count += 1
            
        except Exception as e:
            logger.error(f"Failed to instantiate agent {agent_name}: {e}")
            error_count += 1
    
    logger.info(f"AgentRegistry population complete: {success_count} success, {error_count} errors")


def validate_agent_registry_consistency(agent_registry) -> Dict[str, Any]:
    """
    Validate consistency between AgentClassRegistry and runtime AgentRegistry.
    
    Args:
        agent_registry: The runtime AgentRegistry to validate
        
    Returns:
        Dictionary with validation results
    """
    class_registry = get_agent_class_registry()
    
    if not class_registry.is_frozen():
        return {"status": "error", "message": "AgentClassRegistry not initialized"}
    
    validation_results = {
        "status": "success",
        "class_registry_agents": set(class_registry.list_agent_names()),
        "runtime_registry_agents": set(agent_registry.list_agents()),
        "missing_in_runtime": [],
        "extra_in_runtime": [],
        "type_mismatches": []
    }
    
    class_agents = validation_results["class_registry_agents"]
    runtime_agents = validation_results["runtime_registry_agents"]
    
    # Find missing and extra agents
    validation_results["missing_in_runtime"] = list(class_agents - runtime_agents)
    validation_results["extra_in_runtime"] = list(runtime_agents - class_agents)
    
    # Check type consistency for common agents
    common_agents = class_agents & runtime_agents
    for agent_name in common_agents:
        expected_class = class_registry.get_agent_class(agent_name)
        runtime_agent = agent_registry.get(agent_name)
        
        if runtime_agent and not isinstance(runtime_agent, expected_class):
            validation_results["type_mismatches"].append({
                "name": agent_name,
                "expected": expected_class.__name__,
                "actual": type(runtime_agent).__name__
            })
    
    # Determine overall status
    if (validation_results["missing_in_runtime"] or 
        validation_results["extra_in_runtime"] or 
        validation_results["type_mismatches"]):
        validation_results["status"] = "inconsistent"
    
    return validation_results