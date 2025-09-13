"""
Communication Systems Integration Tests Package

This package contains comprehensive integration tests for communication systems
and real-time messaging in the Netra AI platform.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure reliable communication systems enable AI value delivery
- Value Impact: Communication reliability directly impacts user experience and engagement
- Strategic Impact: Communication foundation for $500K+ ARR chat functionality

Test Coverage:
- WebSocket connection lifecycle and authentication
- Message routing, delivery, and user isolation
- Real-time event streaming and performance
- Cross-service communication and API contracts
- Message persistence, queuing, and reliability patterns
- Performance testing under load and scaling scenarios

All tests follow SSOT patterns and use real service integration without requiring
Docker containers, enabling reliable test execution in various environments.
"""

# Communication test modules
from .test_websocket_connection_integration import (
    TestWebSocketConnectionEstablishment,
    TestWebSocketAuthentication,
    TestWebSocketConnectionLifecycle,
)

from .test_message_routing_integration import (
    TestMessageRoutingBasics,
    TestMessageDeliveryReliability,
    TestMessageRoutingPerformance,
)

from .test_event_streaming_integration import (
    TestRealTimeEventStreaming,
    TestEventStreamingReliability,
    TestEventStreamingPerformance,
)

from .test_cross_service_communication_integration import (
    TestCrossServiceMessaging,
    TestServiceCommunicationReliability,
)

from .test_message_persistence_integration import (
    TestMessagePersistence,
    TestMessageQueuing,
)

from .test_websocket_performance_integration import (
    TestWebSocketThroughput,
    TestWebSocketScaling,
    TestWebSocketLatencyOptimization,
)

from .test_communication_reliability_integration import (
    TestCommunicationFaultTolerance,
    TestMessageDeliveryGuarantees,
    TestCommunicationMonitoring,
)

__all__ = [
    # WebSocket Connection Tests
    "TestWebSocketConnectionEstablishment",
    "TestWebSocketAuthentication", 
    "TestWebSocketConnectionLifecycle",
    
    # Message Routing Tests
    "TestMessageRoutingBasics",
    "TestMessageDeliveryReliability",
    "TestMessageRoutingPerformance",
    
    # Event Streaming Tests
    "TestRealTimeEventStreaming",
    "TestEventStreamingReliability", 
    "TestEventStreamingPerformance",
    
    # Cross-Service Communication Tests
    "TestCrossServiceMessaging",
    "TestServiceCommunicationReliability",
    
    # Message Persistence Tests
    "TestMessagePersistence",
    "TestMessageQueuing",
    
    # Performance Tests
    "TestWebSocketThroughput",
    "TestWebSocketScaling",
    "TestWebSocketLatencyOptimization",
    
    # Reliability Tests
    "TestCommunicationFaultTolerance",
    "TestMessageDeliveryGuarantees",
    "TestCommunicationMonitoring",
]