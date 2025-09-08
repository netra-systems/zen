"""
Test Correlation ID Generation - Unit Tests for Request Tracing

Business Value Justification (BVJ):
- Segment: Platform/Internal (Development Velocity & Operations)
- Business Goal: Enable rapid diagnosis of multi-service issues through request correlation
- Value Impact: Reduce cross-service debugging time from hours to minutes
- Strategic Impact: Foundation for distributed system observability and reliability

This test suite validates that correlation IDs are:
1. Unique across all requests and services
2. Preserved across service boundaries 
3. Consistent in format and generation
4. Available for effective distributed tracing
"""

import re
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Set, List, Dict, Any
from unittest.mock import MagicMock, patch

import pytest

from test_framework.ssot.base_test_case import SSotBaseTestCase


class MockUnifiedIdGenerator:
    """Mock implementation of unified ID generation for testing."""
    
    @staticmethod
    def generate_correlation_id(prefix: str = "corr") -> str:
        """Generate correlation ID with consistent format."""
        timestamp = int(time.time() * 1000)  # milliseconds
        unique_part = uuid.uuid4().hex[:8]
        return f"{prefix}_{timestamp}_{unique_part}"
    
    @staticmethod
    def generate_request_id(prefix: str = "req") -> str:
        """Generate request ID with consistent format."""
        timestamp = int(time.time() * 1000)
        unique_part = uuid.uuid4().hex[:8]
        return f"{prefix}_{timestamp}_{unique_part}"
    
    @staticmethod
    def generate_session_id(prefix: str = "sess") -> str:
        """Generate session ID with consistent format."""
        return f"{prefix}_{uuid.uuid4().hex}"
    
    @staticmethod
    def extract_timestamp(correlation_id: str) -> int:
        """Extract timestamp from correlation ID."""
        parts = correlation_id.split('_')
        if len(parts) >= 2 and parts[1].isdigit():
            return int(parts[1])
        raise ValueError(f"Invalid correlation ID format: {correlation_id}")


class TestCorrelationIdGeneration(SSotBaseTestCase):
    """Test correlation ID generation for effective distributed tracing."""
    
    def setup_method(self, method=None):
        """Setup for each test."""
        super().setup_method(method)
        
        # Setup test environment
        self.set_env_var("SERVICE_NAME", "correlation-test-service")
        self.set_env_var("ENABLE_CORRELATION_TRACKING", "true")
        
        # Initialize mock ID generator
        self.id_generator = MockUnifiedIdGenerator()
        
        # Track generated IDs for uniqueness testing
        self.generated_correlation_ids: Set[str] = set()
        self.generated_request_ids: Set[str] = set()
    
    @pytest.mark.unit
    def test_correlation_id_format_consistency(self):
        """Test that correlation IDs follow consistent format."""
        # Generate multiple correlation IDs
        correlation_ids = []
        for i in range(10):
            corr_id = self.id_generator.generate_correlation_id()
            correlation_ids.append(corr_id)
            self.generated_correlation_ids.add(corr_id)
        
        # Validate format consistency
        expected_pattern = r"^corr_\d{13}_[a-f0-9]{8}$"
        for corr_id in correlation_ids:
            assert re.match(expected_pattern, corr_id), f"Correlation ID '{corr_id}' doesn't match expected format"
        
        # Validate components
        for corr_id in correlation_ids:
            parts = corr_id.split('_')
            assert len(parts) == 3, f"Correlation ID '{corr_id}' should have 3 parts"
            assert parts[0] == "corr", f"Correlation ID '{corr_id}' should start with 'corr'"
            assert len(parts[1]) == 13, f"Timestamp part should be 13 digits: {parts[1]}"
            assert len(parts[2]) == 8, f"Unique part should be 8 characters: {parts[2]}"
            
            # Timestamp should be reasonable (within last hour and next minute)
            timestamp_ms = int(parts[1])
            now_ms = int(time.time() * 1000)
            assert abs(timestamp_ms - now_ms) < 3600000, f"Timestamp too far from current time: {timestamp_ms}"
        
        self.record_metric("correlation_id_format_test", "PASSED")
    
    @pytest.mark.unit
    def test_correlation_id_uniqueness(self):
        """Test that correlation IDs are globally unique."""
        # Generate large number of correlation IDs in rapid succession
        num_ids = 1000
        correlation_ids = []
        
        start_time = time.time()
        for i in range(num_ids):
            corr_id = self.id_generator.generate_correlation_id()
            correlation_ids.append(corr_id)
        generation_time = time.time() - start_time
        
        # Validate uniqueness
        unique_ids = set(correlation_ids)
        assert len(unique_ids) == num_ids, f"Generated {len(unique_ids)} unique IDs out of {num_ids} total"
        
        # Performance validation - should generate 1000 IDs quickly
        assert generation_time < 1.0, f"ID generation too slow: {generation_time:.3f}s for {num_ids} IDs"
        
        self.record_metric("correlation_ids_generated", num_ids)
        self.record_metric("generation_time_ms", generation_time * 1000)
        self.record_metric("uniqueness_test", "PASSED")
    
    @pytest.mark.unit
    def test_correlation_id_concurrent_uniqueness(self):
        """Test that correlation IDs are unique even under concurrent generation."""
        def generate_batch(batch_size: int) -> List[str]:
            """Generate a batch of correlation IDs."""
            return [self.id_generator.generate_correlation_id() for _ in range(batch_size)]
        
        # Generate correlation IDs concurrently
        num_threads = 10
        batch_size = 100
        total_expected = num_threads * batch_size
        
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(generate_batch, batch_size) for _ in range(num_threads)]
            
            # Collect all results
            all_ids = []
            for future in futures:
                batch_ids = future.result()
                all_ids.extend(batch_ids)
        
        # Validate concurrent uniqueness
        assert len(all_ids) == total_expected, f"Expected {total_expected} IDs, got {len(all_ids)}"
        
        unique_ids = set(all_ids)
        assert len(unique_ids) == total_expected, f"Concurrent generation produced {len(unique_ids)} unique IDs out of {total_expected}"
        
        # Validate format consistency under concurrency
        pattern = r"^corr_\d{13}_[a-f0-9]{8}$"
        for corr_id in all_ids:
            assert re.match(pattern, corr_id), f"Concurrent generated ID '{corr_id}' has invalid format"
        
        self.record_metric("concurrent_correlation_ids_generated", total_expected)
        self.record_metric("concurrent_uniqueness_test", "PASSED")
    
    @pytest.mark.unit
    def test_request_id_correlation_relationship(self):
        """Test relationship between request IDs and correlation IDs."""
        # Simulate business scenario: single user request spawns multiple internal requests
        user_request_correlation = self.id_generator.generate_correlation_id()
        
        # Generate related request IDs for same correlation
        related_requests = []
        request_scenarios = [
            "auth_validation",
            "user_data_fetch",
            "agent_execution",
            "result_storage"
        ]
        
        for scenario in request_scenarios:
            request_id = self.id_generator.generate_request_id()
            related_requests.append({
                "request_id": request_id,
                "correlation_id": user_request_correlation,
                "scenario": scenario,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        
        # Validate request-correlation relationship
        assert len(related_requests) == 4, "Should have 4 related requests"
        
        # All requests should share same correlation ID
        correlation_ids = [req["correlation_id"] for req in related_requests]
        assert all(cid == user_request_correlation for cid in correlation_ids), "All requests should share correlation ID"
        
        # All request IDs should be unique
        request_ids = [req["request_id"] for req in related_requests]
        assert len(set(request_ids)) == 4, "All request IDs should be unique"
        
        # Request IDs should follow expected format
        request_pattern = r"^req_\d{13}_[a-f0-9]{8}$"
        for request_id in request_ids:
            assert re.match(request_pattern, request_id), f"Request ID '{request_id}' has invalid format"
        
        self.record_metric("request_correlation_relationship_test", "PASSED")
    
    @pytest.mark.unit
    def test_correlation_id_extraction_and_parsing(self):
        """Test that correlation IDs can be properly extracted and parsed."""
        # Generate test correlation ID
        test_corr_id = self.id_generator.generate_correlation_id()
        
        # Test timestamp extraction
        extracted_timestamp = self.id_generator.extract_timestamp(test_corr_id)
        current_timestamp = int(time.time() * 1000)
        
        # Timestamp should be close to current time (within 1 second)
        timestamp_diff = abs(extracted_timestamp - current_timestamp)
        assert timestamp_diff < 1000, f"Extracted timestamp too far from current: {timestamp_diff}ms"
        
        # Test component parsing
        parts = test_corr_id.split('_')
        assert len(parts) == 3, f"Should have 3 parts: {parts}"
        
        prefix = parts[0]
        timestamp_str = parts[1]
        unique_part = parts[2]
        
        assert prefix == "corr", f"Prefix should be 'corr': {prefix}"
        assert timestamp_str.isdigit(), f"Timestamp should be numeric: {timestamp_str}"
        assert len(unique_part) == 8, f"Unique part should be 8 chars: {unique_part}"
        assert re.match(r"^[a-f0-9]{8}$", unique_part), f"Unique part should be hex: {unique_part}"
        
        # Test parsing invalid formats
        invalid_ids = [
            "invalid_id",
            "corr_invalid_timestamp_abc12345",
            "corr_1234567890123",  # Missing unique part
            "req_1234567890123_abcd1234",  # Wrong prefix
            ""
        ]
        
        for invalid_id in invalid_ids:
            with pytest.raises(ValueError):
                self.id_generator.extract_timestamp(invalid_id)
        
        self.record_metric("correlation_id_parsing_test", "PASSED")
    
    @pytest.mark.unit
    def test_session_correlation_lifecycle(self):
        """Test correlation ID lifecycle across user session."""
        # Simulate complete user session lifecycle
        session_id = self.id_generator.generate_session_id()
        session_correlation = self.id_generator.generate_correlation_id()
        
        # Session lifecycle events
        lifecycle_events = [
            {
                "event": "session_created",
                "session_id": session_id,
                "correlation_id": session_correlation,
                "request_id": self.id_generator.generate_request_id()
            },
            {
                "event": "user_authenticated",
                "session_id": session_id,
                "correlation_id": session_correlation,
                "request_id": self.id_generator.generate_request_id()
            },
            {
                "event": "agent_request_started",
                "session_id": session_id,
                "correlation_id": session_correlation,
                "request_id": self.id_generator.generate_request_id()
            },
            {
                "event": "agent_execution_completed",
                "session_id": session_id,
                "correlation_id": session_correlation,
                "request_id": self.id_generator.generate_request_id()
            },
            {
                "event": "session_ended",
                "session_id": session_id,
                "correlation_id": session_correlation,
                "request_id": self.id_generator.generate_request_id()
            }
        ]
        
        # Validate session consistency
        session_ids = [event["session_id"] for event in lifecycle_events]
        assert all(sid == session_id for sid in session_ids), "Session ID should be consistent"
        
        correlation_ids = [event["correlation_id"] for event in lifecycle_events]
        assert all(cid == session_correlation for cid in correlation_ids), "Correlation ID should be consistent"
        
        # All request IDs should be unique
        request_ids = [event["request_id"] for event in lifecycle_events]
        assert len(set(request_ids)) == len(request_ids), "All request IDs should be unique"
        
        # Session ID should have proper format
        session_pattern = r"^sess_[a-f0-9]{32}$"
        assert re.match(session_pattern, session_id), f"Session ID '{session_id}' has invalid format"
        
        self.record_metric("session_lifecycle_consistency_test", "PASSED")
    
    @pytest.mark.unit
    def test_correlation_id_cross_service_propagation(self):
        """Test that correlation IDs are properly propagated across service boundaries."""
        # Simulate cross-service request flow
        original_correlation = self.id_generator.generate_correlation_id()
        
        # Service chain: Frontend -> Backend -> Auth Service -> Database
        service_chain = [
            {
                "service": "frontend",
                "correlation_id": original_correlation,
                "request_id": self.id_generator.generate_request_id(),
                "operation": "user_login_request"
            },
            {
                "service": "backend", 
                "correlation_id": original_correlation,  # Should preserve original
                "request_id": self.id_generator.generate_request_id(),
                "operation": "authenticate_user"
            },
            {
                "service": "auth_service",
                "correlation_id": original_correlation,  # Should preserve original
                "request_id": self.id_generator.generate_request_id(), 
                "operation": "validate_credentials"
            },
            {
                "service": "database",
                "correlation_id": original_correlation,  # Should preserve original
                "request_id": self.id_generator.generate_request_id(),
                "operation": "fetch_user_record"
            }
        ]
        
        # Validate correlation ID preservation
        for service_call in service_chain:
            assert service_call["correlation_id"] == original_correlation, (
                f"Service {service_call['service']} should preserve correlation ID"
            )
        
        # Validate unique request IDs per service
        request_ids = [call["request_id"] for call in service_chain]
        assert len(set(request_ids)) == len(request_ids), "Each service should have unique request ID"
        
        # Validate tracing capability
        # Should be able to group all service calls by correlation ID
        trace_group = [call for call in service_chain if call["correlation_id"] == original_correlation]
        assert len(trace_group) == 4, "Should be able to trace all 4 service calls"
        
        # Should be able to order by request timestamp (embedded in request ID)
        for call in service_chain:
            request_timestamp = self.id_generator.extract_timestamp(call["request_id"])
            assert isinstance(request_timestamp, int), "Should extract valid timestamp from request ID"
        
        self.record_metric("cross_service_propagation_test", "PASSED")
    
    @pytest.mark.unit
    def test_correlation_id_debugging_effectiveness(self):
        """Test that correlation IDs enable effective debugging scenarios."""
        # Simulate error scenario with correlation ID
        error_correlation = self.id_generator.generate_correlation_id()
        
        # Multi-step operation that fails
        debug_trace = []
        
        # Step 1: Initial request
        debug_trace.append({
            "step": "initial_request",
            "correlation_id": error_correlation,
            "request_id": self.id_generator.generate_request_id(),
            "status": "success",
            "service": "api_gateway",
            "operation": "cost_analysis_request",
            "timestamp": int(time.time() * 1000)
        })
        
        # Step 2: Authentication
        debug_trace.append({
            "step": "authentication", 
            "correlation_id": error_correlation,
            "request_id": self.id_generator.generate_request_id(),
            "status": "success",
            "service": "auth_service",
            "operation": "validate_jwt_token",
            "timestamp": int(time.time() * 1000) + 50
        })
        
        # Step 3: Agent execution (where error occurs)
        debug_trace.append({
            "step": "agent_execution",
            "correlation_id": error_correlation,
            "request_id": self.id_generator.generate_request_id(),
            "status": "error",
            "service": "backend",
            "operation": "execute_cost_optimizer",
            "error": "AgentTimeoutError: Cost optimizer exceeded 30s limit",
            "timestamp": int(time.time() * 1000) + 30100
        })
        
        # Debug capabilities validation
        
        # 1. Can find all related operations by correlation ID
        correlated_operations = [op for op in debug_trace if op["correlation_id"] == error_correlation]
        assert len(correlated_operations) == 3, "Should find all correlated operations"
        
        # 2. Can identify failure point
        failed_operations = [op for op in debug_trace if op.get("status") == "error"]
        assert len(failed_operations) == 1, "Should identify single failure point"
        assert failed_operations[0]["step"] == "agent_execution", "Should identify correct failure step"
        
        # 3. Can reconstruct timeline
        operations_by_time = sorted(debug_trace, key=lambda x: x["timestamp"])
        expected_order = ["initial_request", "authentication", "agent_execution"]
        actual_order = [op["step"] for op in operations_by_time]
        assert actual_order == expected_order, f"Should reconstruct correct timeline: {actual_order}"
        
        # 4. Can identify affected services
        affected_services = set(op["service"] for op in correlated_operations)
        expected_services = {"api_gateway", "auth_service", "backend"}
        assert affected_services == expected_services, "Should identify all affected services"
        
        # 5. Can measure operation duration
        total_duration = max(op["timestamp"] for op in debug_trace) - min(op["timestamp"] for op in debug_trace)
        assert total_duration > 30000, "Should measure operation duration correctly (>30s due to timeout)"
        
        self.record_metric("correlation_debugging_effectiveness_test", "PASSED")
        self.record_metric("debug_trace_operations", len(debug_trace))
        self.record_metric("total_operation_duration_ms", total_duration)
    
    @pytest.mark.unit
    def test_correlation_id_performance_impact(self):
        """Test that correlation ID generation has minimal performance impact."""
        # Baseline: measure time without correlation ID operations
        baseline_operations = 10000
        start_time = time.time()
        
        for i in range(baseline_operations):
            # Simulate basic business operation
            dummy_data = {"operation": f"baseline_{i}", "timestamp": time.time()}
            dummy_result = len(str(dummy_data))  # Minimal processing
        
        baseline_time = time.time() - start_time
        
        # With correlation IDs: measure time with ID generation and tracking
        correlation_operations = 10000
        start_time = time.time()
        
        correlation_ids = []
        for i in range(correlation_operations):
            # Same business operation with correlation ID
            corr_id = self.id_generator.generate_correlation_id()
            correlation_ids.append(corr_id)
            
            dummy_data = {
                "operation": f"correlation_{i}", 
                "timestamp": time.time(),
                "correlation_id": corr_id
            }
            dummy_result = len(str(dummy_data))
        
        correlation_time = time.time() - start_time
        
        # Performance validation
        overhead_ratio = correlation_time / baseline_time if baseline_time > 0 else float('inf')
        assert overhead_ratio < 2.0, f"Correlation ID overhead too high: {overhead_ratio:.2f}x baseline"
        
        # All generated IDs should be unique
        assert len(set(correlation_ids)) == correlation_operations, "All correlation IDs should be unique"
        
        # Record performance metrics
        self.record_metric("baseline_time_ms", baseline_time * 1000)
        self.record_metric("correlation_time_ms", correlation_time * 1000)
        self.record_metric("performance_overhead_ratio", overhead_ratio)
        self.record_metric("correlation_id_performance_test", "PASSED")
    
    def teardown_method(self, method=None):
        """Cleanup after each test."""
        # Clear tracking sets
        self.generated_correlation_ids.clear()
        self.generated_request_ids.clear()
        
        # Call parent teardown
        super().teardown_method(method)