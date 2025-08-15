"""
Comprehensive unit tests for ExternalAPIClient.

This module imports all modularized test classes to maintain compatibility
while ensuring each module is ≤300 lines and each function is ≤8 lines.
"""

# Import all test classes from modularized test modules
from app.tests.services.test_external_api_config import TestExternalAPIConfig
from app.tests.services.test_http_error import TestHTTPError
from app.tests.services.test_resilient_client_init import TestResilientHTTPClientInit
from app.tests.services.test_resilient_client_url_headers import TestResilientHTTPClientUrlHeaders
from app.tests.services.test_resilient_client_session import TestResilientHTTPClientSession
from app.tests.services.test_resilient_client_circuit import TestResilientHTTPClientCircuit
from app.tests.services.test_resilient_client_response import TestResilientHTTPClientResponse
from app.tests.services.test_resilient_client_methods import TestResilientHTTPClientMethods
from app.tests.services.test_resilient_client_health import TestResilientHTTPClientHealth
from app.tests.services.test_retryable_client import TestRetryableHTTPClient
from app.tests.services.test_http_client_manager import (
    TestHTTPClientManager,
    TestGetHTTPClient,
    TestGlobalClientManager
)
from app.tests.services.test_api_convenience_functions import TestConvenienceFunctions
from app.tests.services.test_external_api_integration import TestIntegrationScenarios

# Re-export all test classes for compatibility
__all__ = [
    "TestExternalAPIConfig",
    "TestHTTPError", 
    "TestResilientHTTPClientInit",
    "TestResilientHTTPClientUrlHeaders",
    "TestResilientHTTPClientSession",
    "TestResilientHTTPClientCircuit",
    "TestResilientHTTPClientResponse",
    "TestResilientHTTPClientMethods",
    "TestResilientHTTPClientHealth",
    "TestRetryableHTTPClient",
    "TestHTTPClientManager",
    "TestGetHTTPClient",
    "TestGlobalClientManager",
    "TestConvenienceFunctions",
    "TestIntegrationScenarios"
]