"""
WebSocket Auth Integration Tests Package - Complete Test Suite (100+ Tests)

This package contains comprehensive integration tests for WebSocket authentication systems,
covering the full spectrum from basic authentication flows to advanced error handling
and edge cases. These tests validate the integration between WebSocket authentication, 
user plan enforcement, tool permissions, rate limiting, and system resilience.

Test Categories (5 Batches - 20 Tests Each):

BATCH 1: Core Authentication & User Context (20 tests)
- Basic JWT authentication flows and validation
- User context extraction and management
- Security boundary validation

BATCH 2: JWT Token Lifecycle Management (20 tests)
- Token registration, refresh, and connection management
- Lifecycle integration across system components

BATCH 3: Cross-Service Integration (20 tests)
- Service communication validation
- Real-time communication integration
- Security and error handling across services

BATCH 4: Business Logic Integration (20 tests)
- User plan integration and subscription enforcement
- Tool permission authorization
- Rate limiting and usage control

BATCH 5: Error Handling & Edge Cases (20 tests)
- Authentication failure edge cases
- WebSocket connection failure scenarios
- System resilience and recovery mechanisms

Business Value:
- Protects $500K+ ARR through comprehensive Golden Path validation
- Validates monetization mechanisms and plan differentiation
- Ensures secure tool execution and usage tracking
- Drives conversion through contextual upgrade messaging
- Protects system stability through robust error handling
- Maintains service availability during component failures

Test Execution:
Run all tests: python -m pytest tests/integration/websocket_auth/ -v
Run specific batch: python -m pytest tests/integration/websocket_auth/test_*_batch_name.py -v

Total Integration Tests: 100+ covering complete WebSocket authentication system
"""