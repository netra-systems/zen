"""
System Startup Integration Tests

This package contains comprehensive integration tests for different phases of the system startup sequence:

1. WebSocket Phase Tests (test_websocket_phase_comprehensive.py):
   - WebSocket Core Manager initialization
   - WebSocket Factory setup  
   - Agent Handler integration
   - Authentication & CORS middleware
   - Rate limiting & performance monitoring
   - Multi-user isolation
   - Critical chat events validation

Business Value:
These tests ensure that the system startup sequence properly configures all components
required for delivering real-time chat-based AI business value to users.

Key Focus Areas:
- Component initialization validation
- Multi-user isolation testing
- Chat infrastructure readiness
- Performance and reliability validation
- Security and authentication setup
- Error recovery and monitoring capabilities

Usage:
Run with pytest: `pytest netra_backend/tests/integration/startup/ -v`
"""

__all__ = []