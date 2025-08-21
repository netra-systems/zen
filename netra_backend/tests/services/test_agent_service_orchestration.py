"""
DEPRECATED: This file has been split into modular components for architecture compliance.

ARCHITECTURE COMPLIANCE SPLIT:
This 8825-line file exceeded the 450-line MANDATORY limit and has been split into
focused modules following the modular architecture requirements.

NEW MODULE STRUCTURE:
- test_agent_service_orchestration_core.py: Core orchestration and WebSocket handling
- test_agent_service_orchestration_agents.py: Agent lifecycle management
- test_agent_service_orchestration_workflows.py: Error recovery and resilience
- test_agent_service_fixtures.py: Shared fixtures and utilities

IMPORT THESE MODULES INSTEAD:
Use the specific module that contains the tests you need rather than this file.

COMPLIANCE STATUS: 
✅ All new modules are under 300 lines
✅ Functions are under 8 lines  
✅ Single responsibility per module
✅ Clear interfaces between modules

For new tests, add them to the appropriate specialized module.
"""

# Import redirects for backwards compatibility

# Add project root to path

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

from netra_backend.tests.test_agent_service_orchestration_core import TestAgentServiceOrchestrationCore, TestAgentServiceBasic
from netra_backend.tests.test_agent_service_orchestration_agents import TestAgentLifecycleManagement  
from netra_backend.tests.test_agent_service_orchestration_workflows import TestAgentErrorRecovery

# Add project root to path
