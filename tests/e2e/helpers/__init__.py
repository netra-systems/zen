import sys
import os
from pathlib import Path

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).resolve().parent

"""
E2E Test Helpers Package

This package contains helper utilities, validators, and test support classes
that were incorrectly named as test files but contain no actual test functions.

Modules:
- agent_orchestration_runner: Agent orchestration test runner utilities
- auth_service_helpers: Auth service independence validation helpers
- database_sync_helpers: Database synchronization utilities
- error_propagation_helpers: Error propagation chain validation helpers
- microservice_isolation_helpers: Microservice isolation validation utilities
- service_independence_helpers: Service independence validation utilities
"""
