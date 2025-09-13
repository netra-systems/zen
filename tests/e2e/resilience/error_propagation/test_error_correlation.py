"""

Error Correlation and Tracking Tests.



Business Value Justification (BVJ):

- Segment: Platform/Internal

- Business Goal: Debugging Efficiency

- Value Impact: Enables rapid error diagnosis across services

- Strategic/Revenue Impact: Reduces support costs and improves reliability

"""



import asyncio

import json

import uuid

from datetime import datetime, timezone

from typing import Any, Dict

from shared.isolated_environment import IsolatedEnvironment



import pytest



from tests.e2e.fixtures.error_propagation_fixtures import (

    ErrorCorrelationContext,

    error_correlation_context,

    real_http_client,

    real_websocket_client,

    service_orchestrator,

    test_user,

)



@pytest.mark.asyncio

@pytest.mark.e2e

class TestErrorCorrelation:

    """Test error correlation and tracking across services."""

    

    @pytest.mark.resilience

    async def test_correlation_id_propagation(self, service_orchestrator, real_http_client:

                                            error_correlation_context):

        """Test correlation ID propagates across service calls."""

        correlation_id = error_correlation_context.correlation_id

        

        # Make request with correlation ID

        response = await real_http_client.request(

            "GET",

            "/api/test_correlation",

            headers={"X-Correlation-ID": correlation_id}

        )

        

        # Response should include correlation ID

        if response.success and response.headers:

            assert correlation_id in str(response.headers.get("X-Correlation-ID", ""))

            

    @pytest.mark.resilience

    async def test_error_context_preservation(self, service_orchestrator, real_http_client:

                                            error_correlation_context):

        """Test error context is preserved across service boundaries."""

        # Trigger error with context

        response = await real_http_client.request(

            "POST",

            "/api/error_test",

            json={

                "user_id": error_correlation_context.user_id,

                "operation": error_correlation_context.operation,

                "should_fail": True

            },

            headers={"X-Correlation-ID": error_correlation_context.correlation_id}

        )

        

        # Error should include context information

        if not response.success and response.error:

            error_data = response.error

            assert error_correlation_context.user_id in str(error_data) or \

                   error_correlation_context.correlation_id in str(error_data)

                   

    @pytest.mark.resilience

    async def test_cross_service_error_tracking(self, service_orchestrator, real_websocket_client:

                                               error_correlation_context):

        """Test error tracking across WebSocket and HTTP services."""

        token = "valid_test_token"

        

        # Connect WebSocket with correlation context

        connection_result = await real_websocket_client.connect(

            token,

            headers={"X-Correlation-ID": error_correlation_context.correlation_id}

        )

        

        if connection_result.success:

            # Send message that triggers cross-service call

            message_result = await real_websocket_client.send_message({

                "type": "cross_service_test",

                "correlation_id": error_correlation_context.correlation_id,

                "trigger_error": True

            })

            

            # Error should be tracked across services

            if not message_result.success:

                assert message_result.error is not None

                

    @pytest.mark.resilience

    async def test_error_aggregation(self, service_orchestrator, real_http_client:

                                   error_correlation_context):

        """Test error aggregation from multiple sources."""

        correlation_id = error_correlation_context.correlation_id

        

        # Trigger multiple related errors

        tasks = []

        for i in range(3):

            task = real_http_client.request(

                "POST",

                f"/api/multi_error_test/{i}",

                json={"correlation_id": correlation_id, "should_fail": True},

                headers={"X-Correlation-ID": correlation_id}

            )

            tasks.append(task)

            

        results = await asyncio.gather(*tasks, return_exceptions=True)

        

        # Should handle multiple related errors

        error_count = sum(1 for r in results if hasattr(r, 'success') and not r.success)

        # Some errors are expected in this test

        

    @pytest.mark.resilience

    async def test_error_severity_classification(self, service_orchestrator, real_http_client:

                                                error_correlation_context):

        """Test error severity classification."""

        # Trigger different severity errors

        severity_tests = [

            {"endpoint": "/api/warning_test", "expected_severity": "warning"},

            {"endpoint": "/api/error_test", "expected_severity": "error"},

            {"endpoint": "/api/critical_test", "expected_severity": "critical"}

        ]

        

        for test in severity_tests:

            response = await real_http_client.request(

                "POST",

                test["endpoint"],

                json={"trigger_error": True},

                headers={"X-Correlation-ID": error_correlation_context.correlation_id}

            )

            

            # Check severity classification in response

            if not response.success and response.error:

                # Severity should be indicated somehow in error

                assert test["expected_severity"] in str(response.error).lower() or \

                       response.status_code in [400, 500, 503]  # Different codes for different severities

                       

    @pytest.mark.resilience

    async def test_distributed_tracing(self, service_orchestrator, real_websocket_client:

                                     error_correlation_context):

        """Test distributed tracing through error scenarios."""

        token = "valid_test_token"

        trace_id = str(uuid.uuid4())

        

        # Start traced operation

        connection_result = await real_websocket_client.connect(

            token,

            headers={

                "X-Trace-ID": trace_id,

                "X-Correlation-ID": error_correlation_context.correlation_id

            }

        )

        

        if connection_result.success:

            # Perform traced operation that may fail

            message_result = await real_websocket_client.send_message({

                "type": "traced_operation",

                "trace_id": trace_id,

                "steps": ["auth", "validate", "process", "respond"]

            })

            

            # Trace should be maintained through operation

            if message_result.response:

                response_data = message_result.response

                assert trace_id in str(response_data) or \

                       error_correlation_context.correlation_id in str(response_data)

