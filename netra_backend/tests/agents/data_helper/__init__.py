"""
Data Helper Agent Test Suite

This package contains comprehensive unit tests for the DataHelperAgent and related
data collection functionality.

Test Coverage:
- Core functionality and initialization
- Tool request generation and LLM integration
- User isolation and factory patterns
- Integration patterns with other system components
- Error scenarios and resilience testing

Business Value: Platform/Internal - Ensures reliable data collection request
generation for AI optimization strategies, protecting $500K+ ARR functionality.

SSOT Compliance: All tests follow unified BaseTestCase patterns and real service integration.
"""

# Test discovery imports
from .test_data_helper_agent_core_functionality import DataHelperAgentCoreFunctionalityTests as TestDataHelperAgentCoreFunctionality
from .test_data_helper_tool_request_generation import TestDataHelperToolRequestGeneration
from .test_data_helper_agent_user_isolation import TestDataHelperAgentUserIsolation
from .test_data_helper_integration_patterns import TestDataHelperIntegrationPatterns
from .test_data_helper_error_scenarios import TestDataHelperErrorScenarios

__all__ = [
    'TestDataHelperAgentCoreFunctionality',
    'TestDataHelperToolRequestGeneration', 
    'TestDataHelperAgentUserIsolation',
    'TestDataHelperIntegrationPatterns',
    'TestDataHelperErrorScenarios'
]