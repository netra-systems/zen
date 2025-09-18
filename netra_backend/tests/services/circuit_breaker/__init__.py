"""
Circuit Breaker Service Tests Package

This package contains comprehensive unit tests for circuit breaker functionality
including configuration validation, health checks, rate limiting, resilience,
state transitions, and timeout handling.

All tests use the correct CircuitBreakerConfig API without deprecated parameters
like 'retry_after' which caused TypeError issues.
"""