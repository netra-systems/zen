"""
Test Orchestration Module - Agent-based test execution coordination
"""

from .test_orchestrator_agent import (
    TestOrchestratorAgent,
    OrchestrationConfig,
    BackgroundE2EAgent,
    ProgressStreamingAgent,
    AgentCommunicationProtocol
)

from .resource_management_agent import (
    ResourceManagementAgent,
    create_resource_manager,
    ensure_layer_resources_available,
    ResourceStatus,
    ServiceStatus,
    ResourcePool,
    ServiceHealth,
    ResourceAllocation,
    SystemMetrics
)

from .layer_execution_agent import (
    LayerExecutionAgent,
    LayerExecutionConfig,
    LayerExecutionResult,
    ExecutionStrategy
)

__all__ = [
    'TestOrchestratorAgent',
    'OrchestrationConfig', 
    'LayerExecutionAgent',
    'LayerExecutionConfig',
    'LayerExecutionResult',
    'ExecutionStrategy',
    'BackgroundE2EAgent',
    'ProgressStreamingAgent',
    'ResourceManagementAgent',
    'create_resource_manager',
    'ensure_layer_resources_available',
    'ResourceStatus',
    'ServiceStatus',
    'ResourcePool',
    'ServiceHealth',
    'ResourceAllocation', 
    'SystemMetrics',
    'AgentCommunicationProtocol'
]