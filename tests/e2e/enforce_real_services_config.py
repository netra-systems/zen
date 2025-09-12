"""
Real Services Enforcement Configuration for E2E Tests

This module enforces the CLAUDE.md principle: "MOCKS are FORBIDDEN in dev, staging or production"
All E2E tests MUST use real services, real network calls, and real timing.

Business Value Justification (BVJ):
- Segment: Platform/Internal - Development Velocity, Risk Reduction  
- Business Goal: Prevent fake tests that mask real system failures
- Value Impact: Ensures tests actually validate business functionality
- Revenue Impact: Prevents production failures that could cost $100K+ in downtime

CRITICAL: Any test using Mock, patch, AsyncMock, or similar MUST be fixed to use real services.
"""

import os
import sys
import inspect
import warnings
from typing import Dict, List, Any
from shared.isolated_environment import get_env

env = get_env()

class MockDetectionError(Exception):
    """Raised when mock usage is detected in E2E tests."""
    pass

class RealServicesEnforcer:
    """Enforces real service usage in E2E tests."""
    
    FORBIDDEN_IMPORTS = [
        'unittest.mock',
        'mock', 
        'AsyncMock',
        'MagicMock',
        'Mock',
        'patch'
    ]
    
    FORBIDDEN_PATTERNS = [
        'with patch(',
        '@patch(',
        'Mock(',
        'AsyncMock(',
        'MagicMock(',
        'mock_',
        'mock.',
        'return_value =',
        'side_effect ='
    ]
    
    @classmethod
    def validate_no_mocks(cls, test_function):
        """Decorator to validate no mocks are used in test."""
        source = inspect.getsource(test_function)
        
        for pattern in cls.FORBIDDEN_PATTERNS:
            if pattern in source:
                raise MockDetectionError(
                    f" ALERT:  MOCK DETECTED in {test_function.__name__}: '{pattern}'\n"
                    f"Per CLAUDE.md: 'MOCKS are FORBIDDEN in E2E tests'\n"
                    f"Use real services with Docker or staging environment."
                )
        
        return test_function
    
    @classmethod
    def check_imports(cls, module):
        """Check for forbidden mock imports in module."""
        module_source = inspect.getsource(module)
        
        for forbidden in cls.FORBIDDEN_IMPORTS:
            if f"import {forbidden}" in module_source or f"from {forbidden}" in module_source:
                raise MockDetectionError(
                    f" ALERT:  FORBIDDEN IMPORT in {module.__name__}: '{forbidden}'\n"
                    f"Per CLAUDE.md: 'MOCKS are FORBIDDEN in E2E tests'\n"
                    f"Remove all mock imports and use real services."
                )

def enforce_real_services():
    """Enforce real services are used in E2E environment."""
    # Set environment flag to indicate real services required
    os.environ['E2E_ENFORCE_REAL_SERVICES'] = 'true'
    os.environ['USE_REAL_SERVICES'] = 'true'
    os.environ['NO_MOCKS_ALLOWED'] = 'true'
    
    # Override any test environment that might use mocks
    if os.environ.get('TEST_ENV') == 'mock':
        os.environ['TEST_ENV'] = 'e2e'
        
    # Warn about mock usage
    warnings.filterwarnings('error', message='.*mock.*', category=DeprecationWarning)

def get_real_service_config() -> Dict[str, Any]:
    """Get configuration for real services in E2E tests."""
    return {
        'use_real_llm': True,
        'use_real_database': True,
        'use_real_redis': True,
        'use_real_websockets': True,
        'use_real_http_clients': True,
        'docker_services': ['postgres', 'redis', 'backend', 'auth'],
        'service_timeout': 120,  # 2 minutes for service startup
        'network_timeout': 30,   # 30 seconds for network calls
        'min_response_time': 0.1,  # Minimum time for real network calls
        'staging_url': 'https://staging.netrasystems.ai',
        'websocket_url': 'wss://staging.netrasystems.ai/ws',
        'auth_url': 'https://staging.netrasystems.ai/auth'
    }

def validate_real_network_timing(start_time: float, end_time: float, min_time: float = 0.1):
    """Validate that network call took real time (not mocked)."""
    duration = end_time - start_time
    if duration < min_time:
        raise MockDetectionError(
            f" ALERT:  FAKE NETWORK CALL DETECTED: Completed in {duration:.3f}s (min: {min_time}s)\n"
            f"Per CLAUDE.md: All E2E tests must use real network calls.\n"
            f"This response was too fast to be a real network call."
        )
    return True

# Automatically enforce real services when this module is imported
if __name__ != "__main__":
    enforce_real_services()

# Export main enforcement functions
__all__ = [
    'RealServicesEnforcer',
    'MockDetectionError', 
    'enforce_real_services',
    'get_real_service_config',
    'validate_real_network_timing'
]