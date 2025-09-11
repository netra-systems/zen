"""
Golden Path Integration Tests

This package contains comprehensive integration tests that validate the complete
golden path user flow as described in the documentation. These tests ensure
the critical data persistence and flow components work correctly to protect
the $500K+ ARR chat functionality.

Test Focus Areas:
- PostgreSQL database persistence (threads, messages, users, runs)
- Redis caching and session management  
- 3-tier persistence architecture (Redis, PostgreSQL, ClickHouse)
- State persistence optimization and performance
- Data consistency and transaction management
- Cross-service data flow and synchronization
- Real-time data synchronization
- Performance monitoring and SLA compliance
"""