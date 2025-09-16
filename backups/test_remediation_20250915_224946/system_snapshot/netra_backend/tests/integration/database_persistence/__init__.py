"""
Database Persistence Integration Tests

This module contains comprehensive integration tests for database persistence
during the golden path user journey, validating:

- User registration and data isolation
- Thread creation and message persistence  
- Agent execution tracking and results storage
- Multi-user concurrent operations
- Transaction consistency and rollback scenarios
- Redis-PostgreSQL cache coordination
- Database cleanup and resource management

All tests use REAL services (PostgreSQL, Redis) with no mocks to validate
actual business workflows and data integrity.
"""