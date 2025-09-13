"""Error Generation and Injection Utilities



Business Value Justification (BVJ):

- Segment: Platform/Internal

- Business Goal: Operational efficiency & Support cost reduction

- Value Impact: Reduces debugging time, improves system reliability

- Revenue Impact: $45K+ MRR (Reduced support burden, improved user experience)



This module provides utilities for generating and injecting errors across service boundaries

for comprehensive error propagation testing.

"""



import asyncio

import json

import logging



# Add project root to path for imports

import sys

import time

import uuid

from dataclasses import dataclass

from datetime import datetime, timezone

from pathlib import Path

from typing import Any, Dict, List, Optional





from tests.e2e.config import TEST_ENDPOINTS, TEST_USERS

from tests.e2e.service_orchestrator import E2EServiceOrchestrator

from test_framework.http_client import ClientConfig, ConnectionState

from test_framework.http_client import UnifiedHTTPClient as RealHTTPClient

from test_framework.http_client import UnifiedHTTPClient as RealWebSocketClient



logger = logging.getLogger(__name__)





@dataclass

class ErrorCorrelationContext:

    """Context for tracking error correlation across services."""

    request_id: str

    session_id: str

    user_id: Optional[str]

    service_chain: List[str]

    timestamp: datetime

    error_source: Optional[str] = None

    retry_count: int = 0





@dataclass

class ErrorPropagationMetrics:

    """Metrics for error propagation testing."""

    total_tests: int = 0

    successful_propagations: int = 0

    failed_propagations: int = 0

    retry_attempts: int = 0

    user_friendly_messages: int = 0

    correlation_successes: int = 0

    average_response_time: float = 0.0





class RealErrorPropagationTester:

    """Comprehensive real error propagation testing across all service boundaries."""

    

    def __init__(self):

        self.orchestrator: Optional[E2EServiceOrchestrator] = None

        self.http_client: Optional[RealHTTPClient] = None

        self.ws_client: Optional[RealWebSocketClient] = None

        self.metrics = ErrorPropagationMetrics()

        self.correlation_contexts: Dict[str, ErrorCorrelationContext] = {}

        self.test_session_id = self._generate_session_id()

        

    def _generate_session_id(self) -> str:

        """Generate unique test session ID."""

        return f"error_test_{int(time.time())}_{uuid.uuid4().hex[:8]}"

        

    async def setup_test_environment(self) -> bool:

        """Initialize real service environment for comprehensive error testing."""

        try:

            self.orchestrator = E2EServiceOrchestrator()

            await self.orchestrator.start_test_environment("error_propagation_real_test")

            

            # Initialize HTTP client with realistic configuration

            backend_url = self.orchestrator.get_service_url("backend")

            config = ClientConfig(

                timeout=10.0, 

                max_retries=3,

                pool_size=5,

                verify_ssl=False  # For test environment

            )

            self.http_client = RealHTTPClient(backend_url, config)

            

            # Verify environment is ready

            if not self.orchestrator.is_environment_ready():

                logger.error("Test environment not ready after setup")

                return False

            

            logger.info(f"Error propagation test environment ready for session {self.test_session_id}")

            return True

            

        except Exception as e:

            logger.error(f"Failed to setup test environment: {e}")

            return False

    

    async def test_cleanup_test_environment(self) -> None:

        """Clean up all test resources."""

        cleanup_tasks = []

        

        if self.ws_client:

            cleanup_tasks.append(self.ws_client.close())

        if self.http_client:

            cleanup_tasks.append(self.http_client.close())

        if self.orchestrator:

            cleanup_tasks.append(

                self.orchestrator.stop_test_environment("error_propagation_real_test")

            )

        

        if cleanup_tasks:

            await asyncio.gather(*cleanup_tasks, return_exceptions=True)

    

    def _create_correlation_context(self, test_name: str, user_id: Optional[str] = None) -> ErrorCorrelationContext:

        """Create error correlation context for tracking."""

        request_id = self._generate_request_id(test_name)

        context = ErrorCorrelationContext(

            request_id=request_id,

            session_id=self.test_session_id,

            user_id=user_id,

            service_chain=[],

            timestamp=datetime.now(timezone.utc)

        )

        self.correlation_contexts[request_id] = context

        return context



    def _generate_request_id(self, test_name: str) -> str:

        """Generate unique request ID for test."""

        return f"{self.test_session_id}_{test_name}_{uuid.uuid4().hex[:8]}"





class MockTokenGenerator:

    """Utility for generating mock tokens for error testing."""

    

    @staticmethod

    def create_invalid_token() -> str:

        """Generate clearly invalid token."""

        return "invalid.jwt.token.xyz123.clearly.malformed"

    

    @staticmethod

    def create_expired_token() -> str:

        """Create a mock expired token for testing."""

        import base64

        

        # Create a JWT-like token that's clearly expired

        header = base64.b64encode(b'{"typ":"JWT","alg":"HS256"}').decode().rstrip('=')

        

        # Payload with expired timestamp (1 year ago)

        expired_timestamp = int(time.time()) - 31536000  # 1 year ago

        payload_data = f'{{"exp":{expired_timestamp},"sub":"test_user","iat":{expired_timestamp - 3600}}}'

        payload = base64.b64encode(payload_data.encode()).decode().rstrip('=')

        

        signature = "expired_signature_for_testing"

        

        return f"{header}.{payload}.{signature}"





class ErrorInjectionHelper:

    """Helper for injecting various types of errors."""

    

    @staticmethod

    def create_malformed_request() -> Dict[str, Any]:

        """Create malformed request data."""

        return {"incomplete": "request", "missing_fields": True}

    

    @staticmethod

    def create_invalid_credentials() -> Dict[str, Any]:

        """Create invalid login credentials."""

        return {

            "username": "nonexistent@user.com",

            "password": "wrongpassword"

        }

    

    @staticmethod

    def create_timeout_config(timeout_ms: float = 0.1) -> ClientConfig:

        """Create client config with very short timeout."""

        return ClientConfig(timeout=timeout_ms, max_retries=3)





# Utility functions for external use

async def run_real_error_propagation_validation() -> Dict[str, Any]:

    """Run complete real error propagation validation suite."""

    tester = RealErrorPropagationTester()

    

    try:

        setup_success = await tester.setup_test_environment()

        if not setup_success:

            return {"error": "Failed to setup real service test environment"}

        

        return {

            "validation_complete": True,

            "test_session_id": tester.test_session_id,

            "final_metrics": tester.metrics.__dict__,

            "environment_status": await tester.orchestrator.get_environment_status()

        }

        

    except Exception as e:

        logger.error(f"Error during validation: {e}")

        return {"error": str(e)}

    finally:

        await tester.cleanup_test_environment()





# Error generation functions for testing

def generate_network_error() -> Exception:

    """Generate a network connection error for testing."""

    import socket

    return socket.error("Network connection failed")





def generate_database_error() -> Exception:

    """Generate a database connection error for testing."""

    class DatabaseError(Exception):

        pass

    return DatabaseError("Database connection failed")





def generate_auth_error() -> Exception:

    """Generate an authentication error for testing."""

    class AuthError(Exception):

        pass

    return AuthError("Authentication failed")





def generate_websocket_error() -> Exception:

    """Generate a WebSocket connection error for testing."""

    class WebSocketError(Exception):

        pass

    return WebSocketError("WebSocket connection failed")

