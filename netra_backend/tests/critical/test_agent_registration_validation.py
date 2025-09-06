# REMOVED_SYNTAX_ERROR: '''
# REMOVED_SYNTAX_ERROR: Critical test to validate agent registration during startup.
# REMOVED_SYNTAX_ERROR: This test ensures all expected agents are properly registered and available.

# REMOVED_SYNTAX_ERROR: FIVE WHYS ROOT CAUSE FIX: This test addresses the process gap (WHY #4) where
# REMOVED_SYNTAX_ERROR: agent registration failures were not detected during testing.
""

import pytest
import logging
from typing import List, Set
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.agents.supervisor.agent_class_registry import get_agent_class_registry
# REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.agent_class_initialization import ( )
initialize_agent_class_registry,
list_available_agents


logger = logging.getLogger(__name__)


# REMOVED_SYNTAX_ERROR: class TestAgentRegistrationValidation:
    # REMOVED_SYNTAX_ERROR: """Validate agent registration works correctly and all expected agents are available."""

    # Core agents that MUST be registered for the system to function
    # REMOVED_SYNTAX_ERROR: CRITICAL_AGENTS = { )
    # REMOVED_SYNTAX_ERROR: 'triage',      # Initial request processing
    # REMOVED_SYNTAX_ERROR: 'data',        # Data operations
    # REMOVED_SYNTAX_ERROR: 'optimization', # Optimization logic
    # REMOVED_SYNTAX_ERROR: 'actions',     # Action planning
    # REMOVED_SYNTAX_ERROR: 'reporting'    # Report generation
    

    # Specialized agents that should be registered if their modules are available
    # REMOVED_SYNTAX_ERROR: SPECIALIZED_AGENTS = { )
    # REMOVED_SYNTAX_ERROR: 'synthetic_data',     # Data generation
    # REMOVED_SYNTAX_ERROR: 'corpus_admin',       # Corpus management
    # REMOVED_SYNTAX_ERROR: 'supply_researcher',  # Supply chain analysis
    # REMOVED_SYNTAX_ERROR: 'github_analyzer'     # GitHub integration
    

    # Auxiliary agents that enhance functionality
    # REMOVED_SYNTAX_ERROR: AUXILIARY_AGENTS = { )
    # REMOVED_SYNTAX_ERROR: 'goals_triage',   # Goal-based triage
    # REMOVED_SYNTAX_ERROR: 'data_helper',    # Data utilities
    # REMOVED_SYNTAX_ERROR: 'validation'      # Data validation
    

# REMOVED_SYNTAX_ERROR: def test_agent_registry_initialization(self):
    # REMOVED_SYNTAX_ERROR: """Test that the agent registry can be initialized successfully."""
    # Initialize registry
    # REMOVED_SYNTAX_ERROR: registry = initialize_agent_class_registry()

    # Verify registry is frozen (immutable)
    # REMOVED_SYNTAX_ERROR: assert registry.is_frozen(), "Registry must be frozen after initialization"

    # Verify registry has agents
    # REMOVED_SYNTAX_ERROR: agent_count = len(registry)
    # REMOVED_SYNTAX_ERROR: assert agent_count > 0, f"Registry is empty - no agents registered"

    # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")

# REMOVED_SYNTAX_ERROR: def test_critical_agents_registered(self):
    # REMOVED_SYNTAX_ERROR: """Test that all critical agents are registered."""
    # REMOVED_SYNTAX_ERROR: registry = get_agent_class_registry()

    # Ensure registry is initialized
    # REMOVED_SYNTAX_ERROR: if not registry.is_frozen():
        # REMOVED_SYNTAX_ERROR: registry = initialize_agent_class_registry()

        # REMOVED_SYNTAX_ERROR: available_agents = set(registry.list_agent_names())
        # REMOVED_SYNTAX_ERROR: missing_critical = self.CRITICAL_AGENTS - available_agents

        # REMOVED_SYNTAX_ERROR: assert not missing_critical, ( )
        # REMOVED_SYNTAX_ERROR: "formatted_string"
        # REMOVED_SYNTAX_ERROR: "formatted_string"
        

        # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")

# REMOVED_SYNTAX_ERROR: def test_agent_class_retrieval(self):
    # REMOVED_SYNTAX_ERROR: """Test that agent classes can be retrieved from registry."""
    # REMOVED_SYNTAX_ERROR: registry = get_agent_class_registry()

    # Ensure registry is initialized
    # REMOVED_SYNTAX_ERROR: if not registry.is_frozen():
        # REMOVED_SYNTAX_ERROR: registry = initialize_agent_class_registry()

        # Test retrieval of each critical agent
        # REMOVED_SYNTAX_ERROR: for agent_name in self.CRITICAL_AGENTS:
            # REMOVED_SYNTAX_ERROR: agent_class = registry.get_agent_class(agent_name)
            # REMOVED_SYNTAX_ERROR: assert agent_class is not None, "formatted_string"

            # Verify it's a class (not an instance)
            # REMOVED_SYNTAX_ERROR: assert isinstance(agent_class, type), "formatted_string"

            # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")

# REMOVED_SYNTAX_ERROR: def test_synthetic_data_agent_registration(self):
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: Specific test for synthetic_data agent registration.
    # REMOVED_SYNTAX_ERROR: This addresses the exact error from the Five Whys analysis.
    # REMOVED_SYNTAX_ERROR: """"
    # REMOVED_SYNTAX_ERROR: registry = get_agent_class_registry()

    # Ensure registry is initialized
    # REMOVED_SYNTAX_ERROR: if not registry.is_frozen():
        # REMOVED_SYNTAX_ERROR: registry = initialize_agent_class_registry()

        # Check if synthetic_data is registered
        # REMOVED_SYNTAX_ERROR: agent_class = registry.get_agent_class('synthetic_data')

        # REMOVED_SYNTAX_ERROR: if agent_class is None:
            # Provide detailed debugging information
            # REMOVED_SYNTAX_ERROR: available_agents = registry.list_agent_names()
            # REMOVED_SYNTAX_ERROR: import_error_msg = ""

            # Try to import the module to get specific error
            # REMOVED_SYNTAX_ERROR: try:
                # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.synthetic_data_sub_agent import SyntheticDataSubAgent
                # REMOVED_SYNTAX_ERROR: import_error_msg = "Module imports successfully but agent not registered"
                # REMOVED_SYNTAX_ERROR: except ImportError as e:
                    # REMOVED_SYNTAX_ERROR: import_error_msg = "formatted_string"

                    # REMOVED_SYNTAX_ERROR: pytest.fail( )
                    # REMOVED_SYNTAX_ERROR: f"synthetic_data agent not registered!\n"
                    # REMOVED_SYNTAX_ERROR: "formatted_string"
                    # REMOVED_SYNTAX_ERROR: "formatted_string"
                    # REMOVED_SYNTAX_ERROR: f"This is a known issue when opentelemetry is not installed.\n"
                    # REMOVED_SYNTAX_ERROR: f"Install with: pip install opentelemetry-api opentelemetry-sdk"
                    

                    # Verify the class is correct
                    # REMOVED_SYNTAX_ERROR: assert agent_class.__name__ == 'SyntheticDataSubAgent', ( )
                    # REMOVED_SYNTAX_ERROR: "formatted_string"
                    

                    # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")

# REMOVED_SYNTAX_ERROR: def test_agent_metadata_completeness(self):
    # REMOVED_SYNTAX_ERROR: """Test that all registered agents have complete metadata."""
    # REMOVED_SYNTAX_ERROR: registry = get_agent_class_registry()

    # Ensure registry is initialized
    # REMOVED_SYNTAX_ERROR: if not registry.is_frozen():
        # REMOVED_SYNTAX_ERROR: registry = initialize_agent_class_registry()

        # REMOVED_SYNTAX_ERROR: incomplete_metadata = []

        # REMOVED_SYNTAX_ERROR: for agent_name in registry.list_agent_names():
            # REMOVED_SYNTAX_ERROR: agent_info = registry.get_agent_info(agent_name)

            # Check required metadata fields
            # REMOVED_SYNTAX_ERROR: if not agent_info.description:
                # REMOVED_SYNTAX_ERROR: incomplete_metadata.append("formatted_string")
                # REMOVED_SYNTAX_ERROR: if not agent_info.version:
                    # REMOVED_SYNTAX_ERROR: incomplete_metadata.append("formatted_string")
                    # REMOVED_SYNTAX_ERROR: if 'category' not in agent_info.metadata:
                        # REMOVED_SYNTAX_ERROR: incomplete_metadata.append("formatted_string")
                        # REMOVED_SYNTAX_ERROR: if 'priority' not in agent_info.metadata:
                            # REMOVED_SYNTAX_ERROR: incomplete_metadata.append("formatted_string")

                            # REMOVED_SYNTAX_ERROR: assert not incomplete_metadata, ( )
                            # REMOVED_SYNTAX_ERROR: f"Agents with incomplete metadata:\n" + "\n".join(incomplete_metadata)
                            

                            # REMOVED_SYNTAX_ERROR: logger.info(" All agents have complete metadata")

# REMOVED_SYNTAX_ERROR: def test_registry_health_status(self):
    # REMOVED_SYNTAX_ERROR: """Test that the registry reports healthy status."""
    # REMOVED_SYNTAX_ERROR: registry = get_agent_class_registry()

    # Ensure registry is initialized
    # REMOVED_SYNTAX_ERROR: if not registry.is_frozen():
        # REMOVED_SYNTAX_ERROR: registry = initialize_agent_class_registry()

        # REMOVED_SYNTAX_ERROR: stats = registry.get_registry_stats()

        # REMOVED_SYNTAX_ERROR: assert stats['health_status'] == 'healthy', ( )
        # REMOVED_SYNTAX_ERROR: "formatted_string"
        # REMOVED_SYNTAX_ERROR: "formatted_string"
        

        # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")

# REMOVED_SYNTAX_ERROR: def test_no_import_errors_during_registration(self):
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: Test that agent registration completes without critical import errors.
    # REMOVED_SYNTAX_ERROR: This specifically addresses the opentelemetry import issue.
    # REMOVED_SYNTAX_ERROR: """"
    # REMOVED_SYNTAX_ERROR: import sys
    # REMOVED_SYNTAX_ERROR: from io import StringIO
    # REMOVED_SYNTAX_ERROR: import contextlib

    # Capture any errors during registration
    # REMOVED_SYNTAX_ERROR: error_stream = StringIO()

    # REMOVED_SYNTAX_ERROR: with contextlib.redirect_stderr(error_stream):
        # Force re-initialization to catch any import errors
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.agent_class_registry import AgentClassRegistry

        # REMOVED_SYNTAX_ERROR: test_registry = AgentClassRegistry()

        # Try to register all agent types
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.agent_class_initialization import ( )
        # REMOVED_SYNTAX_ERROR: _register_core_agents,
        # REMOVED_SYNTAX_ERROR: _register_specialized_agents,
        # REMOVED_SYNTAX_ERROR: _register_auxiliary_agents
        

        # REMOVED_SYNTAX_ERROR: try:
            # REMOVED_SYNTAX_ERROR: _register_core_agents(test_registry)
            # REMOVED_SYNTAX_ERROR: _register_specialized_agents(test_registry)
            # REMOVED_SYNTAX_ERROR: _register_auxiliary_agents(test_registry)
            # REMOVED_SYNTAX_ERROR: except Exception as e:
                # REMOVED_SYNTAX_ERROR: pytest.fail("formatted_string")

                # Check for critical errors in the error stream
                # REMOVED_SYNTAX_ERROR: errors = error_stream.getvalue()
                # REMOVED_SYNTAX_ERROR: if "ModuleNotFoundError" in errors and "opentelemetry" not in errors:
                    # Ignore opentelemetry errors as they're handled gracefully
                    # REMOVED_SYNTAX_ERROR: pytest.fail("formatted_string")

                    # REMOVED_SYNTAX_ERROR: logger.info(" No critical import errors during agent registration")


                    # REMOVED_SYNTAX_ERROR: if __name__ == "__main__":
                        # Run tests with verbose output
                        # REMOVED_SYNTAX_ERROR: pytest.main([__file__, "-v", "-s"])