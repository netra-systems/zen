"""
Critical test to validate agent registration during startup.
This test ensures all expected agents are properly registered and available.

FIVE WHYS ROOT CAUSE FIX: This test addresses the process gap (WHY #4) where
agent registration failures were not detected during testing.
"""

import pytest
import logging
from typing import List, Set

from netra_backend.app.agents.supervisor.agent_class_registry import get_agent_class_registry
from netra_backend.app.agents.supervisor.agent_class_initialization import (
    initialize_agent_class_registry,
    list_available_agents
)

logger = logging.getLogger(__name__)


class TestAgentRegistrationValidation:
    """Validate agent registration works correctly and all expected agents are available."""
    
    # Core agents that MUST be registered for the system to function
    CRITICAL_AGENTS = {
        'triage',      # Initial request processing
        'data',        # Data operations
        'optimization', # Optimization logic
        'actions',     # Action planning
        'reporting'    # Report generation
    }
    
    # Specialized agents that should be registered if their modules are available
    SPECIALIZED_AGENTS = {
        'synthetic_data',     # Data generation
        'corpus_admin',       # Corpus management
        'supply_researcher',  # Supply chain analysis
        'github_analyzer'     # GitHub integration
    }
    
    # Auxiliary agents that enhance functionality
    AUXILIARY_AGENTS = {
        'goals_triage',   # Goal-based triage
        'data_helper',    # Data utilities
        'validation'      # Data validation
    }
    
    def test_agent_registry_initialization(self):
        """Test that the agent registry can be initialized successfully."""
        # Initialize registry
        registry = initialize_agent_class_registry()
        
        # Verify registry is frozen (immutable)
        assert registry.is_frozen(), "Registry must be frozen after initialization"
        
        # Verify registry has agents
        agent_count = len(registry)
        assert agent_count > 0, f"Registry is empty - no agents registered"
        
        logger.info(f"Registry initialized with {agent_count} agents")
    
    def test_critical_agents_registered(self):
        """Test that all critical agents are registered."""
        registry = get_agent_class_registry()
        
        # Ensure registry is initialized
        if not registry.is_frozen():
            registry = initialize_agent_class_registry()
        
        available_agents = set(registry.list_agent_names())
        missing_critical = self.CRITICAL_AGENTS - available_agents
        
        assert not missing_critical, (
            f"Critical agents missing from registry: {missing_critical}. "
            f"Available agents: {sorted(available_agents)}"
        )
        
        logger.info(f"✅ All {len(self.CRITICAL_AGENTS)} critical agents registered")
    
    def test_agent_class_retrieval(self):
        """Test that agent classes can be retrieved from registry."""
        registry = get_agent_class_registry()
        
        # Ensure registry is initialized
        if not registry.is_frozen():
            registry = initialize_agent_class_registry()
        
        # Test retrieval of each critical agent
        for agent_name in self.CRITICAL_AGENTS:
            agent_class = registry.get_agent_class(agent_name)
            assert agent_class is not None, f"Failed to retrieve class for critical agent: {agent_name}"
            
            # Verify it's a class (not an instance)
            assert isinstance(agent_class, type), f"Retrieved object for {agent_name} is not a class"
            
            logger.info(f"✅ Retrieved class for {agent_name}: {agent_class.__name__}")
    
    def test_synthetic_data_agent_registration(self):
        """
        Specific test for synthetic_data agent registration.
        This addresses the exact error from the Five Whys analysis.
        """
        registry = get_agent_class_registry()
        
        # Ensure registry is initialized
        if not registry.is_frozen():
            registry = initialize_agent_class_registry()
        
        # Check if synthetic_data is registered
        agent_class = registry.get_agent_class('synthetic_data')
        
        if agent_class is None:
            # Provide detailed debugging information
            available_agents = registry.list_agent_names()
            import_error_msg = ""
            
            # Try to import the module to get specific error
            try:
                from netra_backend.app.agents.synthetic_data_sub_agent import SyntheticDataSubAgent
                import_error_msg = "Module imports successfully but agent not registered"
            except ImportError as e:
                import_error_msg = f"Import error: {e}"
            
            pytest.fail(
                f"synthetic_data agent not registered!\n"
                f"Available agents: {sorted(available_agents)}\n"
                f"Import status: {import_error_msg}\n"
                f"This is a known issue when opentelemetry is not installed.\n"
                f"Install with: pip install opentelemetry-api opentelemetry-sdk"
            )
        
        # Verify the class is correct
        assert agent_class.__name__ == 'SyntheticDataSubAgent', (
            f"Wrong class registered for synthetic_data: {agent_class.__name__}"
        )
        
        logger.info(f"✅ synthetic_data agent properly registered: {agent_class}")
    
    def test_agent_metadata_completeness(self):
        """Test that all registered agents have complete metadata."""
        registry = get_agent_class_registry()
        
        # Ensure registry is initialized
        if not registry.is_frozen():
            registry = initialize_agent_class_registry()
        
        incomplete_metadata = []
        
        for agent_name in registry.list_agent_names():
            agent_info = registry.get_agent_info(agent_name)
            
            # Check required metadata fields
            if not agent_info.description:
                incomplete_metadata.append(f"{agent_name}: missing description")
            if not agent_info.version:
                incomplete_metadata.append(f"{agent_name}: missing version")
            if 'category' not in agent_info.metadata:
                incomplete_metadata.append(f"{agent_name}: missing category")
            if 'priority' not in agent_info.metadata:
                incomplete_metadata.append(f"{agent_name}: missing priority")
        
        assert not incomplete_metadata, (
            f"Agents with incomplete metadata:\n" + "\n".join(incomplete_metadata)
        )
        
        logger.info("✅ All agents have complete metadata")
    
    def test_registry_health_status(self):
        """Test that the registry reports healthy status."""
        registry = get_agent_class_registry()
        
        # Ensure registry is initialized
        if not registry.is_frozen():
            registry = initialize_agent_class_registry()
        
        stats = registry.get_registry_stats()
        
        assert stats['health_status'] == 'healthy', (
            f"Registry health check failed: {stats['health_status']}\n"
            f"Stats: {stats}"
        )
        
        logger.info(f"✅ Registry health status: {stats['health_status']}")
    
    def test_no_import_errors_during_registration(self):
        """
        Test that agent registration completes without critical import errors.
        This specifically addresses the opentelemetry import issue.
        """
        import sys
        from io import StringIO
        import contextlib
        
        # Capture any errors during registration
        error_stream = StringIO()
        
        with contextlib.redirect_stderr(error_stream):
            # Force re-initialization to catch any import errors
            from netra_backend.app.agents.supervisor.agent_class_registry import AgentClassRegistry
            
            test_registry = AgentClassRegistry()
            
            # Try to register all agent types
            from netra_backend.app.agents.supervisor.agent_class_initialization import (
                _register_core_agents,
                _register_specialized_agents,
                _register_auxiliary_agents
            )
            
            try:
                _register_core_agents(test_registry)
                _register_specialized_agents(test_registry)
                _register_auxiliary_agents(test_registry)
            except Exception as e:
                pytest.fail(f"Agent registration failed with error: {e}")
        
        # Check for critical errors in the error stream
        errors = error_stream.getvalue()
        if "ModuleNotFoundError" in errors and "opentelemetry" not in errors:
            # Ignore opentelemetry errors as they're handled gracefully
            pytest.fail(f"Critical import errors during registration:\n{errors}")
        
        logger.info("✅ No critical import errors during agent registration")


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s"])