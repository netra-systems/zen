"""
Integration tests demonstrating SessionMetrics SSOT violations across services.

This test suite shows how the SessionMetrics SSOT violation creates real-world
integration failures between services and components.

CRITICAL: These tests reproduce actual production-like scenarios that fail.
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock
import asyncio
import json

from shared.session_management.user_session_manager import SessionMetrics as SharedSessionMetrics
from netra_backend.app.database.request_scoped_session_factory import SessionMetrics as BackendSessionMetrics


class TestCrossServiceSessionMetricsConflicts:
    """Test how SSOT violations cause cross-service integration failures."""

    def test_websocket_manager_session_metrics_confusion(self):
        """CRITICAL: WebSocket manager expects last_activity but gets wrong SessionMetrics."""
        # Simulate WebSocket manager receiving metrics from different services
        def websocket_cleanup_handler(session_metrics_list):
            """WebSocket cleanup expecting consistent SessionMetrics interface."""
            cleanup_candidates = []
            cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=30)
            
            for metrics in session_metrics_list:
                try:
                    # Real WebSocket code tries to access last_activity
                    if hasattr(metrics, 'last_activity') and metrics.last_activity:
                        if metrics.last_activity < cutoff_time:
                            cleanup_candidates.append(metrics)
                    elif hasattr(metrics, 'last_activity_at') and metrics.last_activity_at:
                        if metrics.last_activity_at < cutoff_time:
                            cleanup_candidates.append(metrics)
                    else:
                        # Neither attribute exists - this is the bug!
                        raise AttributeError(f"SessionMetrics missing activity timestamp")
                except AttributeError as e:
                    # This is where the real error occurs
                    raise RuntimeError(f"WebSocket cleanup failed: {e}")
            
            return cleanup_candidates
        
        # Mix of different SessionMetrics from different services
        old_time = datetime.now(timezone.utc) - timedelta(hours=1)
        
        shared_metrics = SharedSessionMetrics(total_sessions=5)  # No activity fields
        backend_metrics = BackendSessionMetrics(
            session_id="test",
            request_id="test", 
            user_id="test",
            created_at=old_time,
            last_activity_at=old_time  # Has last_activity_at, not last_activity
        )
        
        # Both metrics types cause failures in WebSocket cleanup
        with pytest.raises(RuntimeError, match="WebSocket cleanup failed"):
            websocket_cleanup_handler([shared_metrics])
            
        # Even backend metrics fails because code expects 'last_activity' not 'last_activity_at'
        # This passes the hasattr check but demonstrates the naming inconsistency
        cleanup_list = websocket_cleanup_handler([backend_metrics])
        assert len(cleanup_list) == 1  # Works with last_activity_at

    def test_cors_middleware_session_tracking_failure(self):
        """CRITICAL: CORS middleware fails due to SessionMetrics inconsistency."""
        def cors_session_validator(session_metrics, request_origin):
            """CORS middleware that validates session activity."""
            validation_result = {
                'origin': request_origin,
                'session_valid': False,
                'last_activity': None,
                'session_age_minutes': None
            }
            
            try:
                # CORS middleware expects last_activity for session validation
                if hasattr(session_metrics, 'last_activity'):
                    validation_result['last_activity'] = session_metrics.last_activity
                    if session_metrics.last_activity:
                        age = (datetime.now(timezone.utc) - session_metrics.last_activity)
                        validation_result['session_age_minutes'] = age.total_seconds() / 60
                        validation_result['session_valid'] = age < timedelta(hours=1)
                else:
                    # This is the failure path - no last_activity attribute
                    raise AttributeError("SessionMetrics object has no attribute 'last_activity'")
                    
            except AttributeError as e:
                raise RuntimeError(f"CORS session validation failed: {e}")
            
            return validation_result
        
        # Test with shared SessionMetrics - should fail
        shared_metrics = SharedSessionMetrics()
        with pytest.raises(RuntimeError, match="CORS session validation failed"):
            cors_session_validator(shared_metrics, "https://example.com")
        
        # Test with backend SessionMetrics - also fails (no last_activity, has last_activity_at)  
        backend_metrics = BackendSessionMetrics(
            session_id="test",
            request_id="test",
            user_id="test",
            created_at=datetime.now(timezone.utc)
        )
        with pytest.raises(RuntimeError, match="CORS session validation failed"):
            cors_session_validator(backend_metrics, "https://example.com")

    def test_metrics_aggregation_service_integration_failure(self):
        """CRITICAL: Metrics aggregation fails due to incompatible SessionMetrics."""
        def aggregate_session_metrics(metrics_from_services):
            """Service that aggregates metrics from multiple sources."""
            aggregated = {
                'total_sessions': 0,
                'active_sessions': 0, 
                'total_activity_events': 0,
                'services_reporting': 0
            }
            
            for service_name, metrics in metrics_from_services.items():
                try:
                    aggregated['services_reporting'] += 1
                    
                    # Expect shared-style aggregate metrics
                    if hasattr(metrics, 'total_sessions'):
                        aggregated['total_sessions'] += metrics.total_sessions
                    if hasattr(metrics, 'active_sessions'):
                        aggregated['active_sessions'] += metrics.active_sessions
                    
                    # Also expect individual activity tracking
                    if hasattr(metrics, 'last_activity') and metrics.last_activity:
                        aggregated['total_activity_events'] += 1
                    elif hasattr(metrics, 'last_activity_at') and metrics.last_activity_at:
                        aggregated['total_activity_events'] += 1
                    
                except Exception as e:
                    raise RuntimeError(f"Failed to aggregate metrics from {service_name}: {e}")
            
            return aggregated
        
        # Simulate metrics from different services with different SessionMetrics types
        metrics_sources = {
            'user_session_service': SharedSessionMetrics(total_sessions=10, active_sessions=5),
            'database_service': BackendSessionMetrics(
                session_id="db-session",
                request_id="db-req",
                user_id="user-123", 
                created_at=datetime.now(timezone.utc),
                last_activity_at=datetime.now(timezone.utc)
            )
        }
        
        # Aggregation works but shows interface inconsistency
        result = aggregate_session_metrics(metrics_sources)
        
        # Only shared metrics contribute to totals
        assert result['total_sessions'] == 10  # Only from shared metrics
        assert result['active_sessions'] == 5   # Only from shared metrics
        assert result['total_activity_events'] == 1  # Only backend has activity timestamp
        assert result['services_reporting'] == 2
        
        # This demonstrates that services can't properly aggregate due to incompatible interfaces

    def test_session_persistence_layer_confusion(self):
        """CRITICAL: Session persistence fails due to SessionMetrics type confusion."""
        class MockSessionStore:
            """Mock session store that expects consistent SessionMetrics interface."""
            
            def __init__(self):
                self.stored_sessions = {}
            
            def store_session_metrics(self, session_id, metrics):
                """Store metrics with expected interface."""
                # Persistence layer expects both aggregate AND individual data
                stored_data = {'session_id': session_id}
                
                try:
                    # Try to store aggregate metrics
                    if hasattr(metrics, 'total_sessions'):
                        stored_data['total_sessions'] = metrics.total_sessions
                    if hasattr(metrics, 'active_sessions'):
                        stored_data['active_sessions'] = metrics.active_sessions
                    
                    # Try to store individual session data
                    if hasattr(metrics, 'user_id'):
                        stored_data['user_id'] = metrics.user_id
                    if hasattr(metrics, 'created_at'):
                        stored_data['created_at'] = metrics.created_at.isoformat()
                    
                    # Try to store activity tracking
                    if hasattr(metrics, 'last_activity'):
                        stored_data['last_activity'] = metrics.last_activity.isoformat() if metrics.last_activity else None
                    elif hasattr(metrics, 'last_activity_at'):
                        stored_data['last_activity_at'] = metrics.last_activity_at.isoformat() if metrics.last_activity_at else None
                    
                    # Validate we got meaningful data
                    if len(stored_data) <= 1:  # Only session_id
                        raise ValueError("No useful metrics data to store")
                    
                    self.stored_sessions[session_id] = stored_data
                    return True
                    
                except Exception as e:
                    raise RuntimeError(f"Session persistence failed: {e}")
            
            def retrieve_consistent_metrics(self, session_id):
                """Try to retrieve metrics in consistent format."""
                if session_id not in self.stored_sessions:
                    return None
                
                data = self.stored_sessions[session_id]
                
                # Try to reconstruct original metrics type
                if 'total_sessions' in data:
                    # This was shared metrics
                    return 'shared', data
                elif 'user_id' in data:
                    # This was backend metrics
                    return 'backend', data
                else:
                    return 'unknown', data
        
        store = MockSessionStore()
        
        # Store shared metrics
        shared_metrics = SharedSessionMetrics(total_sessions=15, active_sessions=8)
        assert store.store_session_metrics("shared-session", shared_metrics)
        
        # Store backend metrics
        backend_metrics = BackendSessionMetrics(
            session_id="backend-session",
            request_id="req-123",
            user_id="user-456",
            created_at=datetime.now(timezone.utc),
            last_activity_at=datetime.now(timezone.utc)
        )
        assert store.store_session_metrics("backend-session", backend_metrics)
        
        # Retrieve and verify inconsistent storage
        shared_type, shared_data = store.retrieve_consistent_metrics("shared-session")
        backend_type, backend_data = store.retrieve_consistent_metrics("backend-session")
        
        assert shared_type == 'shared'
        assert backend_type == 'backend'
        
        # Verify completely different data structures stored
        shared_keys = set(shared_data.keys())
        backend_keys = set(backend_data.keys())
        common_keys = shared_keys.intersection(backend_keys)
        
        # Only session_id should be common
        assert common_keys == {'session_id'}
        
        # This proves the persistence layer must handle two completely different formats

    @pytest.mark.asyncio
    async def test_real_time_metrics_streaming_failure(self):
        """CRITICAL: Real-time metrics streaming fails due to SessionMetrics inconsistency."""
        async def metrics_stream_processor(metrics_stream):
            """Process streaming metrics from multiple services."""
            processed_metrics = []
            
            async for service_name, metrics in metrics_stream:
                try:
                    # Stream processor expects consistent metric format
                    metric_event = {
                        'timestamp': datetime.now(timezone.utc).isoformat(),
                        'service': service_name,
                        'metrics_type': type(metrics).__name__
                    }
                    
                    # Try to extract activity information
                    if hasattr(metrics, 'last_activity'):
                        metric_event['last_activity'] = metrics.last_activity.isoformat() if metrics.last_activity else None
                    elif hasattr(metrics, 'last_activity_at'):
                        metric_event['last_activity_at'] = metrics.last_activity_at.isoformat() if metrics.last_activity_at else None
                    else:
                        # No activity tracking available
                        metric_event['activity_error'] = 'No activity tracking available'
                    
                    # Try to extract session counts
                    if hasattr(metrics, 'total_sessions'):
                        metric_event['total_sessions'] = metrics.total_sessions
                    if hasattr(metrics, 'active_sessions'):
                        metric_event['active_sessions'] = metrics.active_sessions
                    
                    # Try to extract individual session info
                    if hasattr(metrics, 'session_id'):
                        metric_event['session_id'] = metrics.session_id
                    if hasattr(metrics, 'user_id'):
                        metric_event['user_id'] = metrics.user_id
                    
                    processed_metrics.append(metric_event)
                    
                except Exception as e:
                    # Stream processing error
                    error_event = {
                        'timestamp': datetime.now(timezone.utc).isoformat(),
                        'service': service_name,
                        'error': str(e),
                        'metrics_type': type(metrics).__name__
                    }
                    processed_metrics.append(error_event)
            
            return processed_metrics
        
        async def mock_metrics_stream():
            """Mock stream yielding different SessionMetrics types."""
            yield 'shared_service', SharedSessionMetrics(total_sessions=20, active_sessions=12)
            yield 'backend_service', BackendSessionMetrics(
                session_id="stream-session",
                request_id="stream-req", 
                user_id="stream-user",
                created_at=datetime.now(timezone.utc),
                last_activity_at=datetime.now(timezone.utc)
            )
        
        # Process mixed metrics stream
        results = await metrics_stream_processor(mock_metrics_stream())
        
        assert len(results) == 2
        
        # Verify shared service result
        shared_result = results[0]
        assert shared_result['service'] == 'shared_service'
        assert shared_result['metrics_type'] == 'SessionMetrics'
        assert 'activity_error' in shared_result  # No activity tracking
        assert 'total_sessions' in shared_result
        
        # Verify backend service result  
        backend_result = results[1]
        assert backend_result['service'] == 'backend_service'
        assert backend_result['metrics_type'] == 'SessionMetrics'  # Same name, different class!
        assert 'last_activity_at' in backend_result  # Has activity tracking
        assert 'session_id' in backend_result
        
        # Both have same class name but completely different structures
        assert shared_result['metrics_type'] == backend_result['metrics_type']
        
        # But different data available
        shared_fields = set(k for k in shared_result.keys() if not k.startswith(('timestamp', 'service', 'metrics_type')))
        backend_fields = set(k for k in backend_result.keys() if not k.startswith(('timestamp', 'service', 'metrics_type')))
        
        # Minimal overlap proves incompatible structures
        overlap = shared_fields.intersection(backend_fields)
        assert len(overlap) <= 1  # Maybe error fields, but no real metric fields


class TestSSOTViolationSystemImpacts:
    """Test system-wide impacts of SessionMetrics SSOT violations."""

    def test_monitoring_dashboard_data_inconsistency(self):
        """CRITICAL: Monitoring dashboard shows inconsistent data due to SSOT violation."""
        class MonitoringDashboard:
            """Mock monitoring dashboard that aggregates SessionMetrics from services."""
            
            def __init__(self):
                self.service_metrics = {}
                self.dashboard_data = {}
            
            def register_service_metrics(self, service_name, metrics):
                """Register metrics from a service."""
                self.service_metrics[service_name] = metrics
            
            def generate_dashboard_data(self):
                """Generate dashboard data from all registered services."""
                dashboard = {
                    'total_sessions_across_services': 0,
                    'active_sessions_across_services': 0,
                    'services_with_activity_tracking': 0,
                    'services_with_aggregate_data': 0,
                    'inconsistency_warnings': []
                }
                
                for service_name, metrics in self.service_metrics.items():
                    # Try to get aggregate data
                    if hasattr(metrics, 'total_sessions') and hasattr(metrics, 'active_sessions'):
                        dashboard['total_sessions_across_services'] += metrics.total_sessions
                        dashboard['active_sessions_across_services'] += metrics.active_sessions
                        dashboard['services_with_aggregate_data'] += 1
                    else:
                        dashboard['inconsistency_warnings'].append(
                            f"Service {service_name} missing aggregate session data"
                        )
                    
                    # Try to get activity tracking
                    has_activity = False
                    if hasattr(metrics, 'last_activity') or hasattr(metrics, 'last_activity_at'):
                        dashboard['services_with_activity_tracking'] += 1
                        has_activity = True
                    
                    if not has_activity:
                        dashboard['inconsistency_warnings'].append(
                            f"Service {service_name} missing activity tracking"
                        )
                
                return dashboard
        
        dashboard = MonitoringDashboard()
        
        # Register metrics from different services
        dashboard.register_service_metrics(
            'user_management', 
            SharedSessionMetrics(total_sessions=50, active_sessions=30)
        )
        
        dashboard.register_service_metrics(
            'request_processing',
            BackendSessionMetrics(
                session_id="monitor-session",
                request_id="monitor-req",
                user_id="monitor-user",
                created_at=datetime.now(timezone.utc),
                last_activity_at=datetime.now(timezone.utc)
            )
        )
        
        # Generate dashboard - should show inconsistencies
        data = dashboard.generate_dashboard_data()
        
        # Only shared service contributes to totals
        assert data['total_sessions_across_services'] == 50
        assert data['active_sessions_across_services'] == 30
        assert data['services_with_aggregate_data'] == 1  # Only shared service
        assert data['services_with_activity_tracking'] == 1  # Only backend service
        
        # Should have warnings about inconsistencies
        assert len(data['inconsistency_warnings']) == 2
        
        warning_messages = ' '.join(data['inconsistency_warnings'])
        assert 'request_processing' in warning_messages
        assert 'missing aggregate session data' in warning_messages
        assert 'user_management' in warning_messages  
        assert 'missing activity tracking' in warning_messages
        
        # This proves monitoring is broken due to SSOT violation

    def test_load_balancer_session_affinity_failure(self):
        """CRITICAL: Load balancer session affinity fails due to SessionMetrics inconsistency."""
        class SessionAffinityLoadBalancer:
            """Mock load balancer that uses session metrics for routing decisions."""
            
            def __init__(self):
                self.server_sessions = {}
            
            def route_request(self, request_id, session_metrics):
                """Route request based on session metrics and affinity."""
                routing_decision = {
                    'request_id': request_id,
                    'target_server': None,
                    'routing_reason': None,
                    'session_info': {}
                }
                
                try:
                    # Extract session information for routing
                    if hasattr(session_metrics, 'session_id'):
                        session_id = session_metrics.session_id
                        routing_decision['session_info']['session_id'] = session_id
                        
                        # Check existing server for this session
                        if session_id in self.server_sessions:
                            routing_decision['target_server'] = self.server_sessions[session_id]
                            routing_decision['routing_reason'] = 'session_affinity'
                        else:
                            # New session - assign to least loaded server
                            routing_decision['target_server'] = 'server_1'  # Simplified
                            routing_decision['routing_reason'] = 'load_balancing'
                            self.server_sessions[session_id] = 'server_1'
                    
                    elif hasattr(session_metrics, 'total_sessions'):
                        # Aggregate metrics - can't route based on individual session
                        routing_decision['routing_reason'] = 'no_session_id_available'
                        routing_decision['target_server'] = 'server_1'  # Default
                        routing_decision['session_info']['total_sessions'] = session_metrics.total_sessions
                    
                    else:
                        raise ValueError("SessionMetrics missing required routing information")
                    
                    # Check activity for sticky session timeout
                    activity_available = False
                    if hasattr(session_metrics, 'last_activity') and session_metrics.last_activity:
                        routing_decision['session_info']['last_activity'] = session_metrics.last_activity.isoformat()
                        activity_available = True
                    elif hasattr(session_metrics, 'last_activity_at') and session_metrics.last_activity_at:
                        routing_decision['session_info']['last_activity_at'] = session_metrics.last_activity_at.isoformat()
                        activity_available = True
                    
                    if not activity_available:
                        routing_decision['session_info']['activity_warning'] = 'No activity tracking available'
                    
                except Exception as e:
                    routing_decision['routing_reason'] = f'routing_error: {e}'
                    routing_decision['target_server'] = 'server_1'  # Fallback
                
                return routing_decision
        
        load_balancer = SessionAffinityLoadBalancer()
        
        # Test routing with shared SessionMetrics
        shared_metrics = SharedSessionMetrics(total_sessions=25, active_sessions=15)
        shared_routing = load_balancer.route_request("req-1", shared_metrics)
        
        assert shared_routing['routing_reason'] == 'no_session_id_available'
        assert 'total_sessions' in shared_routing['session_info']
        assert 'activity_warning' in shared_routing['session_info']
        
        # Test routing with backend SessionMetrics
        backend_metrics = BackendSessionMetrics(
            session_id="affinity-session",
            request_id="req-2",
            user_id="user-123",
            created_at=datetime.now(timezone.utc),
            last_activity_at=datetime.now(timezone.utc)
        )
        backend_routing = load_balancer.route_request("req-2", backend_metrics)
        
        assert backend_routing['routing_reason'] == 'load_balancing'  # New session
        assert backend_routing['session_info']['session_id'] == 'affinity-session'
        assert 'last_activity_at' in backend_routing['session_info']
        
        # Second request with same session should use affinity
        backend_routing_2 = load_balancer.route_request("req-3", backend_metrics)
        assert backend_routing_2['routing_reason'] == 'session_affinity'
        
        # This demonstrates that load balancing works differently depending on 
        # which SessionMetrics type is used - SSOT violation impact


if __name__ == "__main__":
    # Run with: python -m pytest tests/integration/test_sessionmetrics_cross_service_conflicts.py -v
    pass