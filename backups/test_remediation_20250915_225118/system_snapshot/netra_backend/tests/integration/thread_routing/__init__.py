"""
Thread Routing Integration Tests Module

This module contains comprehensive integration tests for thread routing functionality
that validate the core multi-user chat infrastructure with real services.

Test Coverage:
- Thread creation and retrieval with PostgreSQL database isolation
- WebSocket connection to thread mapping with Redis state management  
- Message delivery precision across full infrastructure stack

Business Value:
These tests ensure the fundamental chat platform reliability that enables
multi-user AI conversations with proper isolation and message routing.

CRITICAL: All tests use REAL services (PostgreSQL, Redis, WebSocket) 
- NO mocks allowed in integration testing
- Tests expected to initially FAIL to reveal real system issues
- Focus on thread isolation, message precision, and routing accuracy
"""