"""Issue #620 SSOT ExecutionEngine Migration Test Suite.

This package contains comprehensive tests for validating the SSOT ExecutionEngine
migration from multiple deprecated implementations to UserExecutionEngine.

Test Categories:
1. Reproduction Tests: Demonstrate SSOT violations (MUST FAIL before migration)
2. Migration Validation: Verify successful migration (MUST PASS after migration)
3. Golden Path Protection: Core business value protection (MUST ALWAYS PASS)
4. WebSocket Event Validation: Real-time functionality (MUST ALWAYS PASS)
5. E2E Staging: Production-like validation (MUST PASS after migration)

Business Impact: Protects $500K+ ARR during critical SSOT migration.
"""