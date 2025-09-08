"""Test fixtures and helpers for GCP Error Reporting integration testing.

Business Value Justification (BVJ):
- Segment: Mid & Enterprise
- Business Goal: Comprehensive test infrastructure for GCP integration
- Value Impact: Enables thorough validation of production error monitoring
- Strategic Impact: Critical for enterprise observability and reliability testing

This module provides SSOT fixtures, helpers, and mock data for testing
GCP Error Reporting integration with the logging system.
"""

import pytest
import os
import json
import time
from unittest.mock import Mock, MagicMock, patch
from typing import Dict, Any, List, Optional, Union
from contextlib import asynccontextmanager
import asyncio

from netra_backend.app.schemas.monitoring_schemas import ErrorSeverity
from netra_backend.app.services.monitoring.gcp_error_reporter import GCPErrorReporter, ErrorSeverity
from test_framework.isolated_environment_fixtures import isolated_env


# SSOT: GCP Error Test Scenarios
@pytest.fixture
def comprehensive_error_scenarios():
    """Comprehensive error scenarios covering all critical system paths."""
    return {
        # WebSocket errors (critical for chat functionality)
        'websocket_authentication_failure': {
            'message': 'WebSocket authentication failed: JWT token validation error',
            'service': 'websocket_manager',
            'error_type': 'authentication_failure',
            'severity': ErrorSeverity.ERROR,
            'business_impact': 'user_chat_blocked',
            'context': {
                'websocket_connection_id': 'ws_conn_auth_test_001',
                'auth_failure_reason': 'jwt_signature_invalid',
                'client_ip': '203.0.113.195',
                'user_agent': 'NetraApp/2.1 (iOS 17.0)',
                'connection_attempt': 3,
                'retry_allowed': True
            }
        },
        
        'websocket_message_routing_error': {
            'message': 'WebSocket message routing failed: Unknown message type received',
            'service': 'websocket_core',
            'error_type': 'message_routing_failure', 
            'severity': ErrorSeverity.WARNING,
            'business_impact': 'user_message_lost',
            'context': {
                'websocket_id': 'ws_msg_route_test_002',
                'message_type': 'unknown_agent_command',
                'message_size_bytes': 2048,
                'user_session_duration_minutes': 15,
                'previous_successful_messages': 12
            }
        },
        
        # Database errors (critical for data persistence)
        'database_connection_timeout': {
            'message': 'PostgreSQL connection timeout: Unable to establish connection within timeout',
            'service': 'database_manager',
            'error_type': 'connection_timeout',
            'severity': ErrorSeverity.CRITICAL,
            'business_impact': 'data_layer_unavailable',
            'context': {
                'database_type': 'postgresql',
                'host': 'postgres-primary.internal.gcp',
                'port': 5432,
                'database_name': 'netra_production',
                'timeout_seconds': 30,
                'connection_pool_size': 20,
                'active_connections': 18,
                'affected_operations': ['user_authentication', 'thread_persistence', 'agent_state_storage']
            }
        },
        
        'database_query_execution_error': {
            'message': 'SQL query execution failed: Syntax error in complex join operation',
            'service': 'database_operations',
            'error_type': 'query_execution_failure',
            'severity': ErrorSeverity.ERROR,
            'business_impact': 'user_data_retrieval_failed',
            'context': {
                'query_type': 'user_thread_history_lookup',
                'sql_error_code': '42601',  # PostgreSQL syntax error
                'execution_time_ms': 2500,
                'query_complexity': 'high',
                'affected_tables': ['users', 'threads', 'messages', 'agent_runs'],
                'query_hash': 'sha256_complex_join_query_hash_123'
            }
        },
        
        # Authentication service errors (security critical)
        'oauth_provider_validation_failure': {
            'message': 'OAuth token validation failed: Google provider returned invalid signature',
            'service': 'auth_service',
            'error_type': 'oauth_validation_failure',
            'severity': ErrorSeverity.WARNING,
            'business_impact': 'user_login_blocked',
            'context': {
                'oauth_provider': 'google',
                'error_code': 'INVALID_TOKEN_SIGNATURE',
                'token_expiry_minutes': 45,
                'user_email_hash': 'sha256_user_email_hash_456',
                'auth_attempt_id': 'auth_attempt_oauth_test_003',
                'security_context': 'oauth_token_validation',
                'requires_user_reauth': True
            }
        },
        
        'session_management_failure': {
            'message': 'User session storage failed: Redis cluster connection lost',
            'service': 'auth_service',
            'error_type': 'session_storage_failure',
            'severity': ErrorSeverity.ERROR,
            'business_impact': 'user_session_lost',
            'context': {
                'session_id': 'session_storage_test_004',
                'storage_backend': 'redis_cluster',
                'operation': 'session_persist',
                'redis_cluster_nodes': ['redis-1.internal', 'redis-2.internal', 'redis-3.internal'],
                'failed_nodes': ['redis-2.internal'],
                'session_data_size_bytes': 4096,
                'timeout_seconds': 10
            }
        },
        
        # Agent execution errors (core business functionality)
        'agent_llm_timeout': {
            'message': 'Agent execution failed: LLM request timeout exceeded',
            'service': 'agent_executor',
            'error_type': 'llm_request_timeout',
            'severity': ErrorSeverity.ERROR,
            'business_impact': 'user_waiting_for_ai_response',
            'context': {
                'agent_type': 'cost_optimization_agent',
                'llm_provider': 'openai',
                'model_name': 'gpt-4-turbo',
                'timeout_seconds': 120,
                'request_tokens': 3072,
                'max_response_tokens': 4096,
                'retry_count': 2,
                'estimated_cost_usd': 0.15,
                'user_plan': 'enterprise'  # Higher priority for enterprise
            }
        },
        
        'tool_execution_failure': {
            'message': 'Tool execution failed: AWS Cost API rate limit exceeded',
            'service': 'tool_dispatcher',
            'error_type': 'tool_api_rate_limit',
            'severity': ErrorSeverity.WARNING,
            'business_impact': 'agent_functionality_degraded',
            'context': {
                'tool_name': 'aws_cost_analyzer',
                'api_provider': 'aws',
                'api_endpoint': 'cost-explorer.amazonaws.com',
                'rate_limit_reset_seconds': 3600,
                'requests_per_hour_limit': 100,
                'current_requests_count': 101,
                'retry_after_seconds': 3600,
                'tool_parameters': {'aws_account': 'masked_account_id', 'time_period': '30_days'}
            }
        },
        
        # Cross-service cascading errors
        'cascading_failure_database_auth': {
            'message': 'Authentication cascade failure: Database unavailable for user validation',
            'service': 'auth_service',
            'error_type': 'cascading_failure',
            'severity': ErrorSeverity.CRITICAL,
            'business_impact': 'system_wide_authentication_failure',
            'context': {
                'root_cause_service': 'database_manager',
                'root_cause_error': 'connection_pool_exhausted',
                'cascade_sequence': 2,
                'affected_downstream_services': ['websocket_manager', 'agent_executor'],
                'estimated_affected_users': 500,
                'cascade_timeout_seconds': 30
            }
        },
        
        # Business-critical enterprise errors
        'enterprise_sla_breach': {
            'message': 'Enterprise SLA breach: Response time exceeded customer agreement',
            'service': 'performance_monitor',
            'error_type': 'sla_breach',
            'severity': ErrorSeverity.CRITICAL,
            'business_impact': 'enterprise_sla_violation',
            'context': {
                'customer_tier': 'enterprise',
                'sla_response_time_ms': 500,
                'actual_response_time_ms': 1250,
                'sla_breach_percentage': 150.0,
                'customer_contract_value_usd': 25000,
                'estimated_penalty_usd': 2500,
                'requires_customer_notification': True,
                'escalation_required': True
            }
        },
        
        # Security-related errors
        'suspicious_authentication_activity': {
            'message': 'Suspicious authentication activity: Multiple failed login attempts detected',
            'service': 'security_monitor',
            'error_type': 'security_threat_detected',
            'severity': ErrorSeverity.WARNING,
            'business_impact': 'potential_security_breach',
            'context': {
                'threat_level': 'medium',
                'source_ip': '203.0.113.42',
                'failed_attempts_count': 7,
                'failed_attempts_window_minutes': 5,
                'affected_accounts': ['test_account_1@example.com', 'test_account_2@example.com'],
                'geographic_location': 'Unknown',
                'account_lockout_triggered': True,
                'security_team_notified': True,
                'requires_investigation': True
            }
        }
    }


# SSOT: GCP Environment Configurations for Testing
@pytest.fixture
def gcp_environment_configurations():
    """GCP environment configurations for testing different deployment scenarios."""
    return {
        'cloud_run_production': {
            'K_SERVICE': 'netra-backend-prod',
            'K_REVISION': 'netra-backend-prod-00015',
            'GCP_PROJECT': 'netra-production',
            'ENVIRONMENT': 'production',
            'PORT': '8080',
            'expected_gcp_integration': True,
            'expected_error_reporting': True,
            'expected_severity_threshold': 'WARNING'
        },
        
        'cloud_run_staging': {
            'K_SERVICE': 'netra-backend-staging',
            'K_REVISION': 'netra-backend-staging-00032',
            'GCP_PROJECT': 'netra-staging',
            'ENVIRONMENT': 'staging',
            'PORT': '8080',
            'expected_gcp_integration': True,
            'expected_error_reporting': True,
            'expected_severity_threshold': 'INFO'
        },
        
        'local_development': {
            'ENVIRONMENT': 'development',
            'PORT': '8000',
            'DEBUG': 'true',
            'expected_gcp_integration': False,
            'expected_error_reporting': False,
            'expected_severity_threshold': 'DEBUG'
        },
        
        'local_with_gcp_override': {
            'ENVIRONMENT': 'development',
            'ENABLE_GCP_ERROR_REPORTING': 'true',
            'GCP_PROJECT': 'netra-development',
            'PORT': '8000',
            'expected_gcp_integration': True,
            'expected_error_reporting': True,
            'expected_severity_threshold': 'ERROR'
        },
        
        'ci_cd_testing': {
            'ENVIRONMENT': 'testing',
            'CI': 'true',
            'GCP_PROJECT': 'netra-ci-testing',
            'ENABLE_GCP_ERROR_REPORTING': 'false',  # Explicitly disabled in CI
            'expected_gcp_integration': False,
            'expected_error_reporting': False,
            'expected_severity_threshold': 'ERROR'
        }
    }


# SSOT: Mock GCP API Responses  
@pytest.fixture
def mock_gcp_api_responses():
    """Mock GCP Error Reporting API responses for testing."""
    return {
        'error_groups_list': {
            'errorGroupStats': [
                {
                    'group': {
                        'name': 'projects/netra-test/groups/websocket_auth_errors',
                        'groupId': 'websocket_auth_errors',
                        'resolutionStatus': 'OPEN'
                    },
                    'count': '15',
                    'affectedUsersCount': '8',
                    'timedCounts': [
                        {
                            'count': '15',
                            'startTime': '2025-01-08T10:00:00Z',
                            'endTime': '2025-01-08T11:00:00Z'
                        }
                    ],
                    'firstSeenTime': '2025-01-08T10:05:00Z',
                    'lastSeenTime': '2025-01-08T10:55:00Z',
                    'affectedServices': [
                        {
                            'service': 'netra-backend',
                            'version': 'latest'
                        }
                    ],
                    'numAffectedServices': 1
                },
                {
                    'group': {
                        'name': 'projects/netra-test/groups/database_connection_errors',
                        'groupId': 'database_connection_errors', 
                        'resolutionStatus': 'OPEN'
                    },
                    'count': '3',
                    'affectedUsersCount': '25',
                    'timedCounts': [
                        {
                            'count': '3',
                            'startTime': '2025-01-08T10:30:00Z',
                            'endTime': '2025-01-08T11:00:00Z'
                        }
                    ],
                    'firstSeenTime': '2025-01-08T10:30:00Z',
                    'lastSeenTime': '2025-01-08T10:45:00Z',
                    'affectedServices': [
                        {
                            'service': 'netra-backend',
                            'version': 'latest'
                        }
                    ],
                    'numAffectedServices': 1
                }
            ],
            'nextPageToken': '',
            'timeRangeBegin': '2025-01-08T10:00:00Z'
        },
        
        'error_events_list': {
            'errorEvents': [
                {
                    'eventTime': '2025-01-08T10:35:00Z',
                    'serviceContext': {
                        'service': 'netra-backend',
                        'version': 'latest',
                        'resourceType': 'cloud_run_revision'
                    },
                    'message': 'WebSocket authentication failed: JWT token validation error',
                    'context': {
                        'user': 'test_user_123',
                        'httpRequest': {
                            'method': 'GET',
                            'url': 'ws://api.netra.ai/ws',
                            'userAgent': 'NetraApp/2.1 (iOS)',
                            'remoteIp': '203.0.113.195',
                            'responseStatusCode': 401
                        },
                        'reportLocation': {
                            'filePath': 'netra_backend/app/websocket_core/authentication.py',
                            'lineNumber': 145,
                            'functionName': 'validate_jwt_token'
                        }
                    }
                },
                {
                    'eventTime': '2025-01-08T10:40:00Z', 
                    'serviceContext': {
                        'service': 'netra-backend',
                        'version': 'latest',
                        'resourceType': 'cloud_run_revision'
                    },
                    'message': 'PostgreSQL connection timeout: Unable to establish connection within timeout',
                    'context': {
                        'user': 'system_database_manager',
                        'reportLocation': {
                            'filePath': 'netra_backend/app/database/connection_manager.py',
                            'lineNumber': 89,
                            'functionName': 'acquire_connection'
                        }
                    }
                }
            ],
            'nextPageToken': '',
            'timeRangeBegin': '2025-01-08T10:00:00Z'
        }
    }


# SSOT: User Context Scenarios for Testing
@pytest.fixture
def user_context_scenarios():
    """User context scenarios covering different customer segments."""
    return {
        'free_tier_user': {
            'user_id': 'free_user_test_001',
            'email': 'free.user@example.com',
            'plan': 'free',
            'subscription_status': 'active',
            'monthly_usage': 50,  # requests
            'monthly_limit': 1000,
            'business_priority': 'low',
            'sla_response_time_ms': None,  # No SLA for free tier
            'error_notification_preference': 'none'
        },
        
        'early_tier_user': {
            'user_id': 'early_user_test_002',
            'email': 'early.adopter@startup.com',
            'plan': 'early',
            'subscription_status': 'active', 
            'monthly_usage': 2500,
            'monthly_limit': 5000,
            'business_priority': 'normal',
            'sla_response_time_ms': 2000,
            'error_notification_preference': 'critical_only'
        },
        
        'mid_tier_user': {
            'user_id': 'mid_user_test_003',
            'email': 'growth.team@midsize.com',
            'plan': 'mid',
            'subscription_status': 'active',
            'monthly_usage': 8500,
            'monthly_limit': 15000,
            'business_priority': 'high',
            'sla_response_time_ms': 1000,
            'error_notification_preference': 'all_errors',
            'account_manager': 'sarah.johnson@netra.ai'
        },
        
        'enterprise_user': {
            'user_id': 'enterprise_user_test_004',
            'email': 'ai.team@enterprise.com',
            'plan': 'enterprise',
            'subscription_status': 'active',
            'monthly_usage': 45000,
            'monthly_limit': 100000,
            'business_priority': 'critical',
            'sla_response_time_ms': 500,
            'contract_value_usd': 50000,
            'error_notification_preference': 'real_time',
            'account_manager': 'james.wilson@netra.ai',
            'dedicated_support': True,
            'escalation_phone': '+1-555-ENTERPRISE'
        }
    }


# GCP Error Client Fixtures
@pytest.fixture
async def mock_gcp_error_client():
    """Mock GCP Error Reporting client for unit/integration testing."""
    mock_client = Mock()
    
    # Mock the report_exception method
    mock_client.report_exception = Mock()
    
    # Mock the list methods for validation testing
    mock_client.list_group_stats = Mock()
    mock_client.list_events = Mock()
    
    return mock_client


@pytest.fixture
async def real_gcp_error_client():
    """Real GCP Error Reporting client for E2E testing (requires credentials)."""
    if not os.getenv('GCP_PROJECT'):
        pytest.skip("GCP credentials not available - set GCP_PROJECT environment variable")
    
    if os.getenv('TESTING') == '1' or os.getenv('ENVIRONMENT') == 'testing':
        pytest.skip("Real GCP client not available in test environment")
    
    try:
        from google.cloud import error_reporting
        client = error_reporting.Client()
        yield client
    except ImportError:
        pytest.skip("google-cloud-error-reporting package not installed")
    except Exception as e:
        pytest.skip(f"GCP Error Reporting client initialization failed: {e}")


# Context Manager Fixtures
@pytest.fixture
@asynccontextmanager
async def gcp_environment_context(gcp_environment_configurations, isolated_env):
    """Context manager for setting up GCP environment configurations."""
    async def _setup_environment(environment_name: str):
        if environment_name not in gcp_environment_configurations:
            raise ValueError(f"Unknown environment: {environment_name}")
        
        env_config = gcp_environment_configurations[environment_name]
        
        # Set environment variables
        for key, value in env_config.items():
            if not key.startswith('expected_'):
                isolated_env.set(key, value, source='test_fixture')
        
        # Return configuration for test validation
        return env_config
    
    yield _setup_environment


@pytest.fixture
async def error_correlation_tracker():
    """Fixture for tracking error correlation across services."""
    class ErrorCorrelationTracker:
        def __init__(self):
            self.errors = []
            self.correlations = {}
            self.trace_ids = set()
        
        def add_error(self, error_data: Dict[str, Any]):
            """Add an error to the correlation tracker."""
            self.errors.append(error_data)
            
            # Track correlations by trace_id
            trace_id = error_data.get('trace_id')
            if trace_id:
                self.trace_ids.add(trace_id)
                if trace_id not in self.correlations:
                    self.correlations[trace_id] = []
                self.correlations[trace_id].append(error_data)
        
        def get_correlated_errors(self, trace_id: str) -> List[Dict[str, Any]]:
            """Get all errors correlated by trace_id."""
            return self.correlations.get(trace_id, [])
        
        def get_cascade_sequence(self, trace_id: str) -> List[Dict[str, Any]]:
            """Get errors in cascade sequence order."""
            correlated = self.get_correlated_errors(trace_id)
            return sorted(correlated, key=lambda x: x.get('error_sequence', 0))
        
        def validate_correlation_completeness(self, expected_services: List[str]) -> bool:
            """Validate that all expected services reported errors."""
            for trace_id in self.trace_ids:
                correlated = self.get_correlated_errors(trace_id)
                reported_services = {err.get('service') for err in correlated}
                if not set(expected_services).issubset(reported_services):
                    return False
            return True
    
    return ErrorCorrelationTracker()


# Test Data Generators
def generate_test_trace_id(prefix: str = "trace_test") -> str:
    """Generate unique trace ID for testing."""
    return f"{prefix}_{int(time.time() * 1000)}"


def generate_test_request_id(prefix: str = "req_test") -> str:
    """Generate unique request ID for testing.""" 
    return f"{prefix}_{int(time.time() * 1000)}"


def generate_test_user_id(user_tier: str) -> str:
    """Generate test user ID based on tier."""
    return f"{user_tier}_user_test_{int(time.time() % 10000)}"


# Validation Helpers
class GCPErrorValidationHelper:
    """Helper class for validating GCP Error objects in tests."""
    
    @staticmethod
    def validate_error_structure(error_data: Dict[str, Any]) -> bool:
        """Validate basic error structure requirements."""
        required_fields = ['message', 'service', 'error_type', 'severity']
        return all(field in error_data for field in required_fields)
    
    @staticmethod
    def validate_context_preservation(error_data: Dict[str, Any], expected_context: Dict[str, Any]) -> bool:
        """Validate that expected context is preserved in error data."""
        error_context = error_data.get('context', {})
        for key, value in expected_context.items():
            if key not in error_context or error_context[key] != value:
                return False
        return True
    
    @staticmethod
    def validate_business_priority(error_data: Dict[str, Any], user_context: Dict[str, Any]) -> bool:
        """Validate business priority mapping based on user context."""
        user_plan = user_context.get('plan', 'free')
        expected_priority = {
            'free': 'low',
            'early': 'normal', 
            'mid': 'high',
            'enterprise': 'critical'
        }.get(user_plan, 'low')
        
        return error_data.get('business_priority') == expected_priority
    
    @staticmethod
    def validate_severity_mapping(log_level: str, gcp_severity: ErrorSeverity) -> bool:
        """Validate log level to GCP severity mapping."""
        expected_mapping = {
            'debug': ErrorSeverity.INFO,
            'info': ErrorSeverity.INFO,
            'warning': ErrorSeverity.WARNING,
            'error': ErrorSeverity.ERROR,
            'critical': ErrorSeverity.CRITICAL
        }
        
        return expected_mapping.get(log_level.lower()) == gcp_severity


# Export commonly used fixtures and helpers
__all__ = [
    'comprehensive_error_scenarios',
    'gcp_environment_configurations', 
    'mock_gcp_api_responses',
    'user_context_scenarios',
    'mock_gcp_error_client',
    'real_gcp_error_client',
    'gcp_environment_context',
    'error_correlation_tracker',
    'generate_test_trace_id',
    'generate_test_request_id', 
    'generate_test_user_id',
    'GCPErrorValidationHelper'
]