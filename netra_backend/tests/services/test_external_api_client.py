"""
Comprehensive unit tests for ExternalAPIClient.

This module imports all modularized test classes to maintain compatibility
while ensuring each module is ≤300 lines and each function is ≤8 lines.
"""

import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

import sys
from pathlib import Path

from netra_backend.tests.services.test_api_convenience_functions import (
    TestConvenienceFunctions,
)
from netra_backend.tests.services.test_external_api_config import TestExternalAPIConfig
from netra_backend.tests.services.test_external_api_integration import (
    TestIntegrationScenarios,
)
from netra_backend.tests.services.test_http_client_manager import (
    TestGetHTTPClient,
    TestGlobalClientManager,
    TestHTTPClientManager,
)
from netra_backend.tests.services.test_http_error import TestHTTPError
from netra_backend.tests.services.test_resilient_client_circuit import (
    TestResilientHTTPClientCircuit,
)
from netra_backend.tests.services.test_resilient_client_health import (
    TestResilientHTTPClientHealth,
)
from netra_backend.tests.services.test_resilient_client_init import (
    TestResilientHTTPClientInit,
)
from netra_backend.tests.services.test_resilient_client_methods import (
    TestResilientHTTPClientMethods,
)
from netra_backend.tests.services.test_resilient_client_response import (
    TestResilientHTTPClientResponse,
)
from netra_backend.tests.services.test_resilient_client_session import (
    TestResilientHTTPClientSession,
)
from netra_backend.tests.services.test_resilient_client_url_headers import (
    TestResilientHTTPClientUrlHeaders,
)
from netra_backend.tests.services.test_retryable_client import TestRetryableHTTPClient

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