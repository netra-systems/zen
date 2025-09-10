"""
WebSocket Event Handling Integration Tests Package

This package contains comprehensive integration tests for WebSocket event handling
in the Netra Apex AI Optimization Platform.

Business Value: These tests ensure the reliability and performance of the WebSocket
infrastructure that delivers 90% of the platform's business value through real-time
AI-powered chat functionality.

Test Categories:
1. Event Delivery Reliability - Mission-critical WebSocket event delivery
2. Connection State Management - WebSocket lifecycle and health management  
3. Event Routing and Isolation - Multi-user event routing security
4. Error Handling and Recovery - Robust error handling and recovery patterns
5. Performance and Load Handling - Enterprise-scale performance validation

Usage:
    # Run all WebSocket event handling tests
    python tests/unified_test_runner.py --category integration --pattern websocket_event_handling
    
    # Run specific test category
    python tests/unified_test_runner.py --test-file tests/integration/websocket_event_handling/test_websocket_event_delivery_reliability.py
"""

__version__ = "1.0.0"
__author__ = "Netra Apex Development Team"

# Test category exports
from .test_websocket_event_delivery_reliability import TestWebSocketEventDeliveryReliability
from .test_websocket_connection_state_management import TestWebSocketConnectionStateManagement  
from .test_websocket_event_routing_isolation import TestWebSocketEventRoutingIsolation
from .test_websocket_error_handling_recovery import TestWebSocketErrorHandlingRecovery
from .test_websocket_performance_load_handling import TestWebSocketPerformanceLoadHandling

__all__ = [
    "TestWebSocketEventDeliveryReliability",
    "TestWebSocketConnectionStateManagement", 
    "TestWebSocketEventRoutingIsolation",
    "TestWebSocketErrorHandlingRecovery",
    "TestWebSocketPerformanceLoadHandling"
]