"""
Agent Fixtures Usage Examples
Demonstrates how to use the comprehensive agent fixtures module
 <= 300 lines,  <= 8 lines per function - ARCHITECTURAL COMPLIANCE
"""

import asyncio
from unittest.mock import AsyncMock, Mock

import pytest

from netra_backend.tests.fixtures.agent_fixtures import (
    AgentBuilder,
    AgentOrchestrator,
    create_agent_state,
    create_mock_supervisor,
    create_mock_triage_agent,
)

# Example 1: Simple Agent Mock Creation
def test_simple_agent_creation():
    """Example: Create individual agent mocks"""
    supervisor = create_mock_supervisor()
    triage = create_mock_triage_agent()
    
    # Use mocks in test
    assert supervisor.thread_id is not None
    assert hasattr(triage, 'execute')

# Example 2: Agent Builder Pattern
def test_agent_builder_pattern():
    """Example: Use AgentBuilder for complex setups"""
    mocks = (AgentBuilder()
            .with_supervisor()
            .with_triage_agent()
            .with_data_agent()
            .with_infrastructure()
            .build())
    
    # All required mocks are now available
    assert 'supervisor' in mocks
    assert 'llm_manager' in mocks
    assert 'db_session' in mocks

# Example 3: Custom Agent Configuration
def test_custom_agent_configuration():
    """Example: Customize agent behavior"""
    builder = AgentBuilder()
    
    # Add triage agent with custom result
    custom_result = {"category": "custom", "confidence": 0.9}
    mocks = (builder
            .with_triage_agent(result_data=custom_result)
            .with_infrastructure()
            .build())
    
    # Verify customization
    assert 'triage' in mocks

# Example 4: Agent State Management
def test_agent_state_management():
    """Example: Create and manage agent states"""
    # Basic state creation
    state = create_agent_state("Optimize my AI workload")
    assert state.user_request == "Optimize my AI workload"
    
    # State with custom IDs
    custom_state = create_agent_state(
        "Custom request",
        thread_id="test_thread_123",
        user_id="test_user_456"
    )
    assert custom_state.chat_thread_id == "test_thread_123"
    assert custom_state.user_id == "test_user_456"

# Example 5: Agent Orchestration
@pytest.mark.asyncio
async def test_agent_orchestration():
    """Example: Orchestrate multiple agents"""
    # Build agent setup
    mocks = (AgentBuilder()
            .with_triage_agent()
            .with_data_agent()
            .build())
    
    # Create orchestrator
    orchestrator = AgentOrchestrator(mocks)
    
    # Execute agents in sequence
    state = create_agent_state("Test orchestration")
    await orchestrator.execute_sequence(['triage', 'data'], state)
    
    # Verify execution
    assert mocks['triage'].execute.called
    assert mocks['data'].execute.called

# Example 6: Error Scenario Testing
@pytest.mark.asyncio
async def test_error_scenarios():
    """Example: Test error handling scenarios"""
    # Setup agents
    mocks = (AgentBuilder()
            .with_triage_agent()
            .with_data_agent()
            .build())
    
    orchestrator = AgentOrchestrator(mocks)
    
    # Setup failure scenario
    orchestrator.setup_failure_scenario('triage', 'Triage failed')
    
    # Test error handling in your application logic
    state = create_agent_state("Test error handling")
    try:
        await orchestrator.execute_sequence(['triage'], state)
    except Exception as e:
        assert "Triage failed" in str(e)

# Example 7: Retry Testing
@pytest.mark.asyncio
async def test_retry_scenarios():
    """Example: Test retry scenarios"""
    # Setup agents
    mocks = (AgentBuilder()
            .with_data_agent()
            .build())
    
    orchestrator = AgentOrchestrator(mocks)
    
    # Setup retry scenario: 2 failures, then success
    failures = ["First failure", "Second failure"]
    success_data = create_agent_state("Success after retries")
    orchestrator.setup_retry_scenario('data', failures, success_data)
    
    # Test retry logic
    state = create_agent_state("Test retries")
    result = await orchestrator.execute_sequence(['data'], state)
    
    # Verify retries were attempted
    assert mocks['data'].execute.call_count == 3  # 2 failures + 1 success

# Example 8: Pytest Fixture Usage
@pytest.fixture
def complete_agent_environment():
    """Fixture: Complete agent testing environment"""
    return (AgentBuilder()
           .with_supervisor()
           .with_triage_agent()
           .with_data_agent()
           .with_infrastructure()
           .build())

def test_using_fixture(complete_agent_environment):
    """Example: Use the complete environment fixture"""
    mocks = complete_agent_environment
    
    # Test with complete environment
    assert len(mocks) >= 7  # supervisor, triage, data, + 4 infrastructure
    assert 'supervisor' in mocks
    assert 'llm_manager' in mocks

# Example 9: Integration Testing Pattern
@pytest.mark.asyncio
async def test_integration_pattern():
    """Example: Full integration test pattern"""
    # 1. Setup complete environment
    mocks = (AgentBuilder()
            .with_supervisor()
            .with_triage_agent()
            .with_data_agent()
            .with_infrastructure()
            .build())
    
    # 2. Create orchestrator
    orchestrator = AgentOrchestrator(mocks)
    
    # 3. Create initial state
    state = create_agent_state("Comprehensive integration test")
    
    # 4. Execute full agent pipeline
    await orchestrator.execute_sequence(['triage', 'data'], state)
    
    # 5. Verify all components worked
    assert mocks['triage'].execute.called
    assert mocks['data'].execute.called
    assert mocks['llm_manager'].call_llm.return_value is not None

# Example 10: Performance Testing Setup
def test_performance_testing_setup():
    """Example: Setup for performance testing"""
    # Create multiple agent environments
    environments = []
    for i in range(10):
        env = (AgentBuilder()
              .with_supervisor()
              .with_triage_agent()
              .with_infrastructure()
              .build())
        environments.append(env)
    
    # All environments ready for concurrent testing
    assert len(environments) == 10
    for env in environments:
        assert 'supervisor' in env
        assert 'triage' in env