"""Agent Orchestration Tester - Phase 4 of Unified System Testing

Multi-agent system testing that validates the AI agent system that differentiates 
our product. This is the main orchestration module that imports all specialized
agent testing modules.

Business Value Justification (BVJ):
- Segment: All tiers (Free, Early, Mid, Enterprise)
- Business Goal: Validate AI optimization value delivery system
- Value Impact: Ensures agents deliver measurable AI cost savings to customers
- Revenue Impact: Agent reliability enables value-based pricing model (20% of savings)

Architecture Compliance:
- 450-line file limit enforced through modular design
- Specialized test modules for each orchestration aspect
- Shared fixtures for consistency and reduced duplication
- Comprehensive coverage through focused test suites

Test Modules:
1. test_supervisor_routing.py - Agent routing decision validation
2. test_multi_agent_coordination.py - Parallel execution and coordination  
3. test_agent_failure_recovery.py - Failure scenarios and resilience
4. test_agent_response_streaming.py - Real-time response delivery
"""

# Import all modular agent orchestration tests
# Import shared fixtures
from tests.agent_orchestration_fixtures import (
    coordination_test_data,
    failure_recovery_data,
    health_monitoring_data,
    mock_sub_agents,
    mock_supervisor_agent,
    performance_metrics_data,
    routing_test_data,
    sample_agent_state,
    streaming_test_data,
    websocket_mock,
)
from tests.test_agent_failure_recovery import (
    TestAgentFailureRecovery,
    TestFailureDetection,
    TestFailureRecoveryStrategies,
    TestRecoveryValidation,
)
from tests.test_agent_response_streaming import (
    TestAgentResponseStreaming,
    TestStreamingIntegration,
    TestStreamingPerformance,
    TestStreamingReliability,
)
from tests.test_multi_agent_coordination import (
    TestAgentSynchronization,
    TestDataFlowOrchestration,
    TestMultiAgentCoordination,
)
from tests.test_supervisor_routing import (
    TestRoutingPerformance,
    TestRoutingValidation,
    TestSupervisorRouting,
)

# Re-export test classes for pytest discovery
__all__ = [
    # Supervisor Routing Tests
    'TestSupervisorRouting',
    'TestRoutingValidation',
    'TestRoutingPerformance',
    
    # Multi-Agent Coordination Tests
    'TestMultiAgentCoordination',
    'TestAgentSynchronization', 
    'TestDataFlowOrchestration',
    
    # Failure Recovery Tests
    'TestAgentFailureRecovery',
    'TestFailureDetection',
    'TestFailureRecoveryStrategies',
    'TestRecoveryValidation',
    
    # Response Streaming Tests
    'TestAgentResponseStreaming',
    'TestStreamingReliability',
    'TestStreamingPerformance',
    'TestStreamingIntegration',
    
    # Shared Fixtures
    'mock_supervisor_agent',
    'mock_sub_agents',
    'sample_agent_state',
    'websocket_mock',
    'routing_test_data',
    'coordination_test_data',
    'failure_recovery_data',
    'streaming_test_data',
    'health_monitoring_data',
    'performance_metrics_data'
]

"""
Agent Orchestration Test Coverage Summary:

1. Supervisor Routing (18 tests):
   - Basic routing decisions for different request types
   - Tier-based routing for enterprise features
   - Priority and conditional routing
   - Routing validation and error handling
   - Performance and load balancing

2. Multi-Agent Coordination (12 tests):
   - Parallel agent execution and result aggregation
   - Sequential dependency execution
   - Data flow and transformation pipelines
   - Agent synchronization and barriers
   - Context preservation across agents

3. Failure Recovery (16 tests):
   - Graceful degradation on single agent failures
   - Fallback agent activation
   - Pipeline recovery and continuation
   - Cascade failure prevention
   - Various recovery strategies (retry, circuit breaker, degraded mode)
   - Recovery validation and monitoring

4. Response Streaming (16 tests):
   - Real-time WebSocket streaming to frontend
   - Progress indicators and lifecycle events
   - Error streaming and reliability
   - High-frequency and memory-efficient streaming
   - Cross-agent streaming coordination

Total: 62 comprehensive tests validating multi-agent orchestration
"""