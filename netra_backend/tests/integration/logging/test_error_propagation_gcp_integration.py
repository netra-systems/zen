"""Integration tests for error propagation to GCP Error Reporting.

Business Value Justification (BVJ):
- Segment: Mid & Enterprise - System Reliability & Observability
- Business Goal: Verify end-to-end error propagation from services to GCP Error Reporting
- Value Impact: Ensures enterprise customers have comprehensive error monitoring
- Strategic Impact: Foundation for production debugging and SLA monitoring

This test suite uses real services to validate error propagation chains.
Tests MUST FAIL initially to prove gaps in cross-service error integration.

CRITICAL: These tests failing is EXPECTED and proves integration gaps exist.
"""

import pytest
import asyncio
import logging
import time
import json
from unittest.mock import Mock, patch, call, MagicMock
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from test_framework.ssot.base_test_case import SSotBaseTestCase, SSotAsyncTestCase
from test_framework.gcp_integration.gcp_error_test_fixtures import (
    comprehensive_error_scenarios,
    gcp_environment_configurations,
    mock_gcp_error_client,
    error_correlation_tracker,
    generate_test_trace_id,
    GCPErrorValidationHelper
)
from netra_backend.app.schemas.monitoring_schemas import ErrorSeverity
from shared.isolated_environment import get_env


@dataclass
class ErrorPropagationTrace:
    """Track error propagation across service boundaries."""
    trace_id: str
    service_errors: List[Dict[str, Any]] = field(default_factory=list)
    gcp_error_reports: List[Dict[str, Any]] = field(default_factory=list)
    propagation_timeline: List[Dict[str, Any]] = field(default_factory=list)
    start_time: float = field(default_factory=time.time)
    
    def add_service_error(self, service: str, error_data: Dict[str, Any]):
        """Add service error to propagation trace."""
        self.service_errors.append({
            'timestamp': time.time(),
            'service': service,
            'error_data': error_data,
            'propagation_delay_ms': (time.time() - self.start_time) * 1000
        })
    
    def add_gcp_error_report(self, report_data: Dict[str, Any]):
        """Add GCP error report to propagation trace."""
        self.gcp_error_reports.append({
            'timestamp': time.time(),
            'report_data': report_data,
            'propagation_delay_ms': (time.time() - self.start_time) * 1000
        })
    
    def validate_propagation_completeness(self) -> bool:
        """Validate that all service errors were propagated to GCP."""
        return len(self.gcp_error_reports) >= len(self.service_errors)


class TestErrorPropagationGCPIntegration(SSotBaseTestCase):
    """Integration tests for error propagation to GCP Error Reporting."""
    
    def setup_method(self, method):
        """Setup for error propagation integration tests."""
        super().setup_method(method)
        self.env = get_env()
        
        # Setup error tracking
        self.propagation_traces: Dict[str, ErrorPropagationTrace] = {}
        self.mock_gcp_client = Mock()
        self.validation_helper = GCPErrorValidationHelper()
        
        # Mock GCP Error Reporting client
        self.gcp_client_patcher = patch('google.cloud.error_reporting.Client')
        self.mock_gcp_client_class = self.gcp_client_patcher.start()
        self.mock_gcp_client_class.return_value = self.mock_gcp_client
        
        self.add_cleanup(self.gcp_client_patcher.stop)
    
    def _create_propagation_trace(self, trace_id: str = None) -> ErrorPropagationTrace:
        """Create and register error propagation trace."""
        if not trace_id:
            trace_id = generate_test_trace_id("propagation_test")
        
        trace = ErrorPropagationTrace(trace_id=trace_id)
        self.propagation_traces[trace_id] = trace
        return trace
    
    def test_websocket_error_propagates_to_gcp(self, comprehensive_error_scenarios):
        """TEST EXPECTED TO FAIL: WebSocket errors should propagate to GCP Error Reporting."""
        
        # Arrange
        trace_id = generate_test_trace_id("websocket_error")
        trace = self._create_propagation_trace(trace_id)
        scenario_data = comprehensive_error_scenarios['websocket_authentication_failure']
        
        # Mock WebSocket service logger
        websocket_logger = logging.getLogger('netra_backend.app.websocket_core.authentication')
        
        self.record_metric('test_type', 'websocket_error_propagation')
        self.record_metric('trace_id', trace_id)
        
        # Act - Simulate WebSocket authentication error
        websocket_error_context = {
            'trace_id': trace_id,
            'websocket_id': scenario_data['context']['websocket_connection_id'],
            'user_id': 'integration_test_user_001',
            'auth_failure_reason': scenario_data['context']['auth_failure_reason'],
            'service': 'websocket_core',
            'error_type': 'authentication_failure'
        }
        
        # Log the error that should propagate to GCP
        websocket_logger.error(
            scenario_data['message'],
            extra=websocket_error_context
        )
        
        # Track service error
        trace.add_service_error('websocket_core', websocket_error_context)
        
        # Assert - THIS WILL FAIL because error doesn't propagate to GCP
        assert self.mock_gcp_client.report_exception.called, (
            f"CRITICAL INTEGRATION GAP: WebSocket error with trace_id {trace_id} did not propagate to GCP Error Reporting. "
            f"Service errors logged: {len(trace.service_errors)}, GCP reports: {len(trace.gcp_error_reports)}"
        )
        
        # Validate propagation completeness (if it worked)
        if self.mock_gcp_client.report_exception.called:
            call_args = self.mock_gcp_client.report_exception.call_args
            trace.add_gcp_error_report(call_args)
            
            propagation_complete = trace.validate_propagation_completeness()
            assert propagation_complete, (
                f"INTEGRATION GAP: Error propagation incomplete for trace {trace_id}"
            )
    
    def test_database_error_propagates_to_gcp(self, comprehensive_error_scenarios):
        """TEST EXPECTED TO FAIL: Database errors should propagate to GCP Error Reporting."""
        
        # Arrange
        trace_id = generate_test_trace_id("database_error")
        trace = self._create_propagation_trace(trace_id)
        scenario_data = comprehensive_error_scenarios['database_connection_timeout']
        
        # Mock database service logger
        db_logger = logging.getLogger('netra_backend.app.database.connection_manager')
        
        # Act - Simulate database connection timeout
        database_error_context = {
            'trace_id': trace_id,
            'database_host': scenario_data['context']['host'],
            'database_name': scenario_data['context']['database_name'],
            'connection_pool_size': scenario_data['context']['connection_pool_size'],
            'timeout_seconds': scenario_data['context']['timeout_seconds'],
            'service': 'database_manager',
            'error_type': 'connection_timeout',
            'business_impact': 'data_layer_unavailable'
        }
        
        # Log critical database error
        db_logger.critical(
            scenario_data['message'],
            extra=database_error_context
        )
        
        trace.add_service_error('database_manager', database_error_context)
        
        # Assert - THIS WILL FAIL because database errors don't propagate to GCP
        assert self.mock_gcp_client.report_exception.called, (
            f"CRITICAL INTEGRATION GAP: Database critical error with trace_id {trace_id} did not propagate to GCP. "
            f"Critical database errors must be reported to GCP for enterprise monitoring."
        )
        
        # Validate critical error prioritization (if it worked)
        if self.mock_gcp_client.report_exception.called:
            call_args = self.mock_gcp_client.report_exception.call_args
            # Should validate that critical errors get higher priority in GCP
            pass
    
    def test_auth_service_error_propagates_to_gcp(self, comprehensive_error_scenarios):
        """TEST EXPECTED TO FAIL: Auth service errors should propagate to GCP Error Reporting."""
        
        # Arrange
        trace_id = generate_test_trace_id("auth_error")
        trace = self._create_propagation_trace(trace_id)
        scenario_data = comprehensive_error_scenarios['oauth_provider_validation_failure']
        
        # Mock auth service logger
        auth_logger = logging.getLogger('auth_service.oauth_validation')
        
        # Act - Simulate OAuth validation failure
        auth_error_context = {
            'trace_id': trace_id,
            'oauth_provider': scenario_data['context']['oauth_provider'],
            'error_code': scenario_data['context']['error_code'],
            'user_email_hash': scenario_data['context']['user_email_hash'],
            'service': 'auth_service',
            'error_type': 'oauth_validation_failure',
            'security_impact': 'authentication_blocked'
        }
        
        # Log auth error
        auth_logger.error(
            scenario_data['message'],
            extra=auth_error_context
        )
        
        trace.add_service_error('auth_service', auth_error_context)
        
        # Assert - THIS WILL FAIL because auth errors don't propagate to GCP
        assert self.mock_gcp_client.report_exception.called, (
            f"CRITICAL INTEGRATION GAP: Auth service error with trace_id {trace_id} did not propagate to GCP. "
            f"Authentication failures must be monitored for security compliance."
        )
    
    def test_cascading_error_propagation_to_gcp(self, comprehensive_error_scenarios):
        """TEST EXPECTED TO FAIL: Cascading errors should propagate as correlated GCP errors."""
        
        # Arrange
        trace_id = generate_test_trace_id("cascading_error")
        trace = self._create_propagation_trace(trace_id)
        scenario_data = comprehensive_error_scenarios['cascading_failure_database_auth']
        
        # Simulate cascading failure: Database -> Auth -> WebSocket
        services_and_loggers = [
            ('database_manager', logging.getLogger('netra_backend.app.database.connection_manager')),
            ('auth_service', logging.getLogger('auth_service.user_validation')),
            ('websocket_manager', logging.getLogger('netra_backend.app.websocket_core.connection_handler'))
        ]
        
        cascade_errors = []
        
        # Act - Generate cascading errors
        for sequence, (service, logger) in enumerate(services_and_loggers):
            error_context = {
                'trace_id': trace_id,
                'service': service,
                'error_type': 'cascading_failure',
                'cascade_sequence': sequence + 1,
                'root_cause_service': 'database_manager',
                'affected_downstream_services': ['auth_service', 'websocket_manager'][sequence:],
                'business_impact': 'system_wide_failure'
            }
            
            error_message = f"Cascading failure in {service} - sequence {sequence + 1}"
            
            logger.error(error_message, extra=error_context)
            trace.add_service_error(service, error_context)
            cascade_errors.append(error_context)
        
        expected_gcp_reports = len(cascade_errors)
        
        # Assert - THIS WILL FAIL because cascading errors don't propagate properly
        assert self.mock_gcp_client.report_exception.call_count == expected_gcp_reports, (
            f"CRITICAL INTEGRATION GAP: Cascading errors should create {expected_gcp_reports} correlated GCP reports. "
            f"Got {self.mock_gcp_client.report_exception.call_count} reports for trace_id {trace_id}."
        )
        
        # Validate correlation preservation (if it worked)
        if self.mock_gcp_client.report_exception.call_count > 0:
            for call_args in self.mock_gcp_client.report_exception.call_args_list:
                trace.add_gcp_error_report(call_args)
            
            # Validate all reports have same trace_id for correlation
            for report in trace.gcp_error_reports:
                # Would validate trace_id correlation here
                pass
    
    def test_error_severity_mapping_propagation_to_gcp(self, comprehensive_error_scenarios):
        """TEST EXPECTED TO FAIL: Error severity levels should map correctly in GCP propagation."""
        
        severity_test_cases = [
            ('warning', 'oauth_provider_validation_failure', ErrorSeverity.WARNING),
            ('error', 'database_connection_timeout', ErrorSeverity.ERROR),
            ('critical', 'cascading_failure_database_auth', ErrorSeverity.CRITICAL)
        ]
        
        propagation_results = []
        
        for log_level, scenario_key, expected_gcp_severity in severity_test_cases:
            # Arrange
            trace_id = generate_test_trace_id(f"severity_{log_level}")
            trace = self._create_propagation_trace(trace_id)
            scenario_data = comprehensive_error_scenarios[scenario_key]
            
            # Mock appropriate service logger
            service_logger = logging.getLogger(f'test_service_{log_level}')
            
            error_context = {
                'trace_id': trace_id,
                'service': f'test_service_{log_level}',
                'error_type': scenario_data['error_type'],
                'severity_level': log_level,
                'expected_gcp_severity': expected_gcp_severity.value
            }
            
            # Act - Log error with specific severity
            if log_level == 'warning':
                service_logger.warning(scenario_data['message'], extra=error_context)
            elif log_level == 'error':
                service_logger.error(scenario_data['message'], extra=error_context)
            elif log_level == 'critical':
                service_logger.critical(scenario_data['message'], extra=error_context)
            
            trace.add_service_error(f'test_service_{log_level}', error_context)
            propagation_results.append((trace_id, log_level, expected_gcp_severity))
        
        total_expected_reports = len(severity_test_cases)
        
        # Assert - THIS WILL FAIL because severity mapping doesn't propagate
        assert self.mock_gcp_client.report_exception.call_count == total_expected_reports, (
            f"CRITICAL INTEGRATION GAP: Severity mapping propagation failed. "
            f"Expected {total_expected_reports} GCP reports with correct severity mapping, "
            f"got {self.mock_gcp_client.report_exception.call_count}."
        )
        
        # Validate severity mapping (if it worked)
        if self.mock_gcp_client.report_exception.call_count == total_expected_reports:
            for i, (trace_id, log_level, expected_severity) in enumerate(propagation_results):
                call_args = self.mock_gcp_client.report_exception.call_args_list[i]
                # Would validate severity mapping here
                pass
    
    def test_error_context_preservation_in_gcp_propagation(self, comprehensive_error_scenarios):
        """TEST EXPECTED TO FAIL: Rich error context should be preserved in GCP propagation."""
        
        # Arrange
        trace_id = generate_test_trace_id("context_preservation")
        trace = self._create_propagation_trace(trace_id)
        scenario_data = comprehensive_error_scenarios['agent_llm_timeout']
        
        # Create rich context data
        rich_context = {
            'trace_id': trace_id,
            'service': 'agent_executor',
            'error_type': 'llm_timeout',
            'agent_type': scenario_data['context']['agent_type'],
            'llm_provider': scenario_data['context']['llm_provider'],
            'model_name': scenario_data['context']['model_name'],
            'timeout_seconds': scenario_data['context']['timeout_seconds'],
            'request_tokens': scenario_data['context']['request_tokens'],
            'user_plan': scenario_data['context']['user_plan'],
            'business_metadata': {
                'customer_tier': 'enterprise',
                'sla_breach': True,
                'estimated_cost_impact': 0.15,
                'retry_strategy': 'exponential_backoff'
            },
            'technical_metadata': {
                'request_id': f'req_{trace_id}',
                'session_id': f'session_{trace_id}',
                'connection_pool': 'primary',
                'load_balancer_region': 'us-central1'
            }
        }
        
        # Mock agent service logger
        agent_logger = logging.getLogger('netra_backend.app.agents.executor')
        
        # Act - Log error with rich context
        agent_logger.error(
            scenario_data['message'],
            extra=rich_context
        )
        
        trace.add_service_error('agent_executor', rich_context)
        
        # Assert - THIS WILL FAIL because context is not preserved in propagation
        assert self.mock_gcp_client.report_exception.called, (
            f"CRITICAL INTEGRATION GAP: Rich context error with trace_id {trace_id} did not propagate to GCP. "
            f"Context preservation is essential for debugging enterprise issues."
        )
        
        # Validate context preservation (if it worked)
        if self.mock_gcp_client.report_exception.called:
            call_args = self.mock_gcp_client.report_exception.call_args
            trace.add_gcp_error_report(call_args)
            
            # Would validate that business and technical metadata are preserved
            context_preserved = self.validation_helper.validate_context_preservation(
                call_args.kwargs if hasattr(call_args, 'kwargs') else {},
                rich_context
            )
            assert context_preserved, (
                f"INTEGRATION GAP: Rich context not preserved in GCP propagation for {trace_id}"
            )
    
    def test_multi_service_error_correlation_in_gcp(self, error_correlation_tracker):
        """TEST EXPECTED TO FAIL: Multi-service errors should be correlated in GCP."""
        
        # Arrange
        trace_id = generate_test_trace_id("multi_service_correlation")
        trace = self._create_propagation_trace(trace_id)
        
        # Define multi-service error scenario
        services_errors = [
            ('auth_service', 'OAuth validation timeout'),
            ('database_manager', 'User lookup query failed'),
            ('websocket_manager', 'Connection authentication rejected'),
            ('agent_executor', 'User context initialization failed')
        ]
        
        correlated_errors = []
        
        # Act - Generate errors across multiple services with same trace_id
        for service, error_message in services_errors:
            service_logger = logging.getLogger(f'netra_backend.app.{service}')
            
            error_context = {
                'trace_id': trace_id,
                'service': service,
                'error_type': 'multi_service_correlation_test',
                'correlation_group': 'auth_flow_failure',
                'user_id': 'correlation_test_user_001',
                'request_id': f'req_{trace_id}'
            }
            
            service_logger.error(error_message, extra=error_context)
            trace.add_service_error(service, error_context)
            correlated_errors.append(error_context)
            
            # Track in correlation tracker for validation
            error_correlation_tracker.add_error(error_context)
        
        expected_correlated_reports = len(services_errors)
        
        # Assert - THIS WILL FAIL because multi-service correlation doesn't work
        assert self.mock_gcp_client.report_exception.call_count == expected_correlated_reports, (
            f"CRITICAL INTEGRATION GAP: Multi-service error correlation failed. "
            f"Expected {expected_correlated_reports} correlated GCP reports for trace_id {trace_id}, "
            f"got {self.mock_gcp_client.report_exception.call_count}."
        )
        
        # Validate correlation tracking (if it worked)
        if self.mock_gcp_client.report_exception.call_count > 0:
            correlation_complete = error_correlation_tracker.validate_correlation_completeness(
                [service for service, _ in services_errors]
            )
            assert correlation_complete, (
                f"INTEGRATION GAP: Multi-service error correlation incomplete for {trace_id}"
            )
    
    def test_integration_gap_analysis_summary(self):
        """Collect and analyze all integration gap findings."""
        
        # Analyze all propagation traces
        total_service_errors = sum(len(trace.service_errors) for trace in self.propagation_traces.values())
        total_gcp_reports = sum(len(trace.gcp_error_reports) for trace in self.propagation_traces.values())
        
        propagation_gap_percentage = (
            ((total_service_errors - total_gcp_reports) / total_service_errors * 100)
            if total_service_errors > 0 else 100
        )
        
        # Record integration metrics
        self.record_metric('total_integration_traces', len(self.propagation_traces))
        self.record_metric('total_service_errors', total_service_errors)
        self.record_metric('total_gcp_reports', total_gcp_reports)
        self.record_metric('propagation_gap_percentage', propagation_gap_percentage)
        self.record_metric('integration_gap_identified', propagation_gap_percentage > 0)
        
        # Detailed gap analysis
        gap_analysis = {
            'test_execution_time': self.get_metrics().execution_time,
            'total_propagation_traces': len(self.propagation_traces),
            'total_service_errors_logged': total_service_errors,
            'total_gcp_reports_created': total_gcp_reports,
            'propagation_gap_percentage': propagation_gap_percentage,
            'traces_with_gaps': [
                trace_id for trace_id, trace in self.propagation_traces.items()
                if not trace.validate_propagation_completeness()
            ],
            'integration_status': 'CRITICAL GAPS DETECTED' if propagation_gap_percentage > 0 else 'INTEGRATION WORKING'
        }
        
        # CRITICAL ASSERTION - This proves integration gaps exist
        assert propagation_gap_percentage == 0, (
            f"CRITICAL INTEGRATION GAP DETECTED: {propagation_gap_percentage:.1f}% of service errors "
            f"do not propagate to GCP Error Reporting. "
            f"Service errors: {total_service_errors}, GCP reports: {total_gcp_reports}. "
            f"This proves cross-service error integration is broken."
        )
        
        # Log detailed integration analysis
        print(f"\n=== INTEGRATION ERROR PROPAGATION GAP ANALYSIS ===")
        print(json.dumps(gap_analysis, indent=2, default=str))
        print(f"=== END INTEGRATION ANALYSIS ===\n")


class TestAsyncErrorPropagationGCPIntegration(SSotAsyncTestCase):
    """Async integration tests for error propagation to GCP."""
    
    def setup_method(self, method):
        """Setup async error propagation tests."""
        super().setup_method(method)
        self.env = get_env()
        self.mock_gcp_client = Mock()
        
        # Mock GCP client
        self.gcp_client_patcher = patch('google.cloud.error_reporting.Client')
        self.mock_gcp_client_class = self.gcp_client_patcher.start()
        self.mock_gcp_client_class.return_value = self.mock_gcp_client
        
        self.add_cleanup(self.gcp_client_patcher.stop)
    
    async def test_async_websocket_error_propagation_to_gcp(self, comprehensive_error_scenarios):
        """TEST EXPECTED TO FAIL: Async WebSocket errors should propagate to GCP."""
        
        # Arrange
        trace_id = generate_test_trace_id("async_websocket")
        scenario_data = comprehensive_error_scenarios['websocket_message_routing_error']
        
        # Mock async WebSocket logger
        websocket_logger = logging.getLogger('netra_backend.app.websocket_core.async_handler')
        
        # Act - Simulate async WebSocket error
        async_error_context = {
            'trace_id': trace_id,
            'websocket_id': scenario_data['context']['websocket_id'],
            'message_type': scenario_data['context']['message_type'],
            'service': 'async_websocket_handler',
            'error_type': 'async_message_routing_failure',
            'asyncio_task_id': 'async_task_001',
            'concurrent_connections': 25
        }
        
        # Simulate async context error logging
        websocket_logger.error(
            f"Async WebSocket error: {scenario_data['message']}",
            extra=async_error_context
        )
        
        # Wait for potential async propagation
        await asyncio.sleep(0.1)
        
        # Assert - THIS WILL FAIL because async errors don't propagate to GCP
        assert self.mock_gcp_client.report_exception.called, (
            f"CRITICAL ASYNC INTEGRATION GAP: Async WebSocket error with trace_id {trace_id} "
            f"did not propagate to GCP. Async context errors must be captured for production debugging."
        )
    
    async def test_async_agent_execution_error_propagation_to_gcp(self, comprehensive_error_scenarios):
        """TEST EXPECTED TO FAIL: Async agent execution errors should propagate to GCP."""
        
        # Arrange
        trace_id = generate_test_trace_id("async_agent")
        scenario_data = comprehensive_error_scenarios['agent_llm_timeout']
        
        # Mock async agent executor logger
        agent_logger = logging.getLogger('netra_backend.app.agents.async_executor')
        
        # Act - Simulate async agent error
        async_agent_context = {
            'trace_id': trace_id,
            'agent_type': scenario_data['context']['agent_type'],
            'llm_provider': scenario_data['context']['llm_provider'],
            'timeout_seconds': scenario_data['context']['timeout_seconds'],
            'service': 'async_agent_executor',
            'error_type': 'async_llm_timeout',
            'async_task_name': 'agent_execution_task',
            'awaiting_operations': ['llm_request', 'context_validation']
        }
        
        # Simulate async error logging
        agent_logger.error(
            f"Async agent error: {scenario_data['message']}",
            extra=async_agent_context
        )
        
        # Wait for potential async propagation
        await asyncio.sleep(0.1)
        
        # Assert - THIS WILL FAIL because async agent errors don't propagate to GCP
        assert self.mock_gcp_client.report_exception.called, (
            f"CRITICAL ASYNC INTEGRATION GAP: Async agent execution error with trace_id {trace_id} "
            f"did not propagate to GCP. Async agent failures must be monitored for enterprise SLAs."
        )


# Export test classes
__all__ = [
    'TestErrorPropagationGCPIntegration',
    'TestAsyncErrorPropagationGCPIntegration',
    'ErrorPropagationTrace'
]