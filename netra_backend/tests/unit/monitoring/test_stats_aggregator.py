"""Unit tests for StatsAggregator (Issue #966)

Tests the stats aggregator functionality for the new monitoring API endpoints.
Follows existing test patterns and uses SSOT test infrastructure.
"""

import asyncio
import time
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.monitoring.stats_aggregator import (
    StatsAggregator,
    RequestStats,
    AgentStats,
    WebSocketStats,
    ErrorRateStats,
    get_stats_aggregator,
    record_request_stats,
    record_agent_execution_stats,
    record_websocket_stats
)


class TestStatsAggregator(SSotAsyncTestCase):
    """Test StatsAggregator functionality."""
    
    async def asyncSetUp(self):
        """Set up test environment."""
        await super().asyncSetUp()
        self.aggregator = StatsAggregator(retention_hours=1)
    
    async def asyncTearDown(self):
        """Clean up test environment."""
        await self.aggregator.stop_aggregation()
        await super().asyncTearDown()
    
    async def test_aggregator_initialization(self):
        """Test StatsAggregator initializes correctly."""
        self.assertEqual(self.aggregator.retention_hours, 1)
        self.assertEqual(len(self.aggregator.request_buckets), 0)
        self.assertEqual(len(self.aggregator.agent_executions), 0)
        self.assertEqual(len(self.aggregator.websocket_events), 0)
        self.assertEqual(len(self.aggregator.error_events), 0)
        self.assertEqual(len(self.aggregator.active_connections), 0)
    
    async def test_start_stop_aggregation(self):
        """Test starting and stopping background aggregation."""
        # Start aggregation
        await self.aggregator.start_aggregation()
        self.assertTrue(self.aggregator._is_aggregating)
        self.assertIsNotNone(self.aggregator._aggregation_task)
        
        # Stop aggregation
        await self.aggregator.stop_aggregation()
        self.assertFalse(self.aggregator._is_aggregating)
    
    async def test_record_request(self):
        """Test recording request statistics."""
        # Record successful request
        await self.aggregator.record_request("/api/test", 200, 250.5)
        
        # Check current hour requests
        self.assertEqual(self.aggregator.current_hour_requests["/api/test"], 1)
        
        # Record error request
        await self.aggregator.record_request("/api/error", 500, 1000.0)
        
        # Check error was recorded
        self.assertEqual(len(self.aggregator.error_events), 1)
        error = self.aggregator.error_events[0]
        self.assertEqual(error['category'], 'api')
        self.assertIn('HTTP 500', error['error_type'])
    
    async def test_record_agent_execution(self):
        """Test recording agent execution statistics."""
        # Record successful agent execution
        await self.aggregator.record_agent_execution(
            "supervisor", 1500.0, True, "test-correlation-123"
        )
        
        # Check execution was recorded
        self.assertEqual(len(self.aggregator.agent_executions), 1)
        execution = self.aggregator.agent_executions[0]
        self.assertEqual(execution['agent_type'], "supervisor")
        self.assertEqual(execution['execution_time_ms'], 1500.0)
        self.assertTrue(execution['success'])
        self.assertEqual(execution['correlation_id'], "test-correlation-123")
        
        # Record failed agent execution
        await self.aggregator.record_agent_execution("triage", 500.0, False)
        
        # Check failure was recorded as error
        self.assertEqual(len(self.aggregator.error_events), 1)
        error = self.aggregator.error_events[0]
        self.assertEqual(error['category'], 'agent')
    
    async def test_record_websocket_event(self):
        """Test recording WebSocket event statistics."""
        # Record connection event
        await self.aggregator.record_websocket_event(
            "connect", "conn-123", True, {"user_id": "user-456"}
        )
        
        # Check event was recorded
        self.assertEqual(len(self.aggregator.websocket_events), 1)
        event = self.aggregator.websocket_events[0]
        self.assertEqual(event['event_type'], "connect")
        self.assertEqual(event['connection_id'], "conn-123")
        self.assertTrue(event['success'])
        
        # Check connection is tracked as active
        self.assertIn("conn-123", self.aggregator.active_connections)
        
        # Record disconnect event
        await self.aggregator.record_websocket_event("disconnect", "conn-123", True)
        
        # Check connection is no longer active
        self.assertNotIn("conn-123", self.aggregator.active_connections)
        
        # Record failed event
        await self.aggregator.record_websocket_event("message", "conn-456", False)
        
        # Check error was recorded
        error_found = any(
            error['category'] == 'websocket' for error in self.aggregator.error_events
        )
        self.assertTrue(error_found)
    
    async def test_record_error(self):
        """Test recording error statistics."""
        # Record different types of errors
        await self.aggregator.record_error("database", "connection_timeout", "Could not connect")
        await self.aggregator.record_error("api", "validation_error", "Invalid input")
        await self.aggregator.record_error("agent", "execution_timeout")
        
        # Check errors were recorded
        self.assertEqual(len(self.aggregator.error_events), 3)
        
        # Check error categories
        categories = [error['category'] for error in self.aggregator.error_events]
        self.assertIn("database", categories)
        self.assertIn("api", categories)
        self.assertIn("agent", categories)
    
    async def test_hour_rollover(self):
        """Test hour bucket rollover functionality."""
        # Record some requests
        await self.aggregator.record_request("/api/test1", 200, 100)
        await self.aggregator.record_request("/api/test2", 200, 200)
        
        # Mock current hour change
        original_hour = self.aggregator.current_hour_start
        new_hour = original_hour + timedelta(hours=1)
        
        with patch.object(self.aggregator, '_get_current_hour', return_value=new_hour):
            await self.aggregator._roll_over_hour()
        
        # Check bucket was created
        self.assertEqual(len(self.aggregator.request_buckets), 1)
        bucket = self.aggregator.request_buckets[0]
        self.assertEqual(bucket['total'], 2)
        self.assertEqual(bucket['by_endpoint']['/api/test1'], 1)
        self.assertEqual(bucket['by_endpoint']['/api/test2'], 1)
        
        # Check current hour requests were cleared
        self.assertEqual(len(self.aggregator.current_hour_requests), 0)
    
    async def test_calculate_request_stats(self):
        """Test request statistics calculation."""
        # Add some historical data
        test_bucket = {
            'timestamp': datetime.now() - timedelta(hours=1),
            'total': 100,
            'by_endpoint': {'/api/users': 60, '/api/posts': 40}
        }
        self.aggregator.request_buckets.append(test_bucket)
        
        # Add current hour data
        await self.aggregator.record_request("/api/current", 200, 100)
        await self.aggregator.record_request("/api/current", 500, 200)  # Error
        
        # Calculate stats
        stats = self.aggregator._calculate_request_stats()
        
        # Verify calculations
        self.assertIsInstance(stats, RequestStats)
        self.assertEqual(stats.total_requests, 101)  # 100 + 1 success
        self.assertEqual(stats.failed_requests, 1)  # 1 error
        self.assertGreater(stats.error_rate, 0)
    
    async def test_calculate_agent_stats(self):
        """Test agent statistics calculation."""
        # Add agent execution data
        await self.aggregator.record_agent_execution("supervisor", 1000, True)
        await self.aggregator.record_agent_execution("triage", 500, True)
        await self.aggregator.record_agent_execution("supervisor", 1500, False)
        await self.aggregator.record_agent_execution("data_helper", 800, True)
        
        # Calculate stats
        stats = self.aggregator._calculate_agent_stats()
        
        # Verify calculations
        self.assertIsInstance(stats, AgentStats)
        self.assertEqual(stats.total_executions, 4)
        self.assertEqual(stats.successful_executions, 3)
        self.assertEqual(stats.failed_executions, 1)
        self.assertEqual(stats.avg_execution_time_ms, 950.0)  # (1000+500+1500+800)/4
        
        # Check agent type breakdown
        self.assertEqual(stats.agents_by_type['supervisor'], 2)
        self.assertEqual(stats.agents_by_type['triage'], 1)
        self.assertEqual(stats.agents_by_type['data_helper'], 1)
    
    async def test_calculate_websocket_stats(self):
        """Test WebSocket statistics calculation."""
        # Add WebSocket event data
        await self.aggregator.record_websocket_event("connect", "conn-1", True)
        await self.aggregator.record_websocket_event("connect", "conn-2", True)
        await self.aggregator.record_websocket_event("connect", "conn-3", False)  # Failed
        await self.aggregator.record_websocket_event("message", "conn-1", True)
        await self.aggregator.record_websocket_event("disconnect", "conn-1", True)
        
        # Calculate stats
        stats = self.aggregator._calculate_websocket_stats()
        
        # Verify calculations
        self.assertIsInstance(stats, WebSocketStats)
        self.assertEqual(stats.total_connections, 3)  # 3 connect attempts
        self.assertEqual(stats.active_connections, 1)  # conn-2 still active
        self.assertEqual(stats.connection_failures, 1)  # 1 failed connect
        self.assertEqual(stats.messages_sent, 1)  # 1 message event
        self.assertEqual(stats.events_dispatched, 5)  # Total events
    
    async def test_calculate_error_rates(self):
        """Test error rate statistics calculation."""
        # Add various errors
        await self.aggregator.record_error("api", "validation_error")
        await self.aggregator.record_error("api", "auth_error")
        await self.aggregator.record_error("agent", "timeout")
        await self.aggregator.record_error("websocket", "connection_failed")
        await self.aggregator.record_error("database", "query_timeout")
        await self.aggregator.record_error("agent", "execution_failed")
        
        # Calculate stats
        stats = self.aggregator._calculate_error_rates()
        
        # Verify calculations
        self.assertIsInstance(stats, ErrorRateStats)
        self.assertEqual(stats.errors_by_type['validation_error'], 1)
        self.assertEqual(stats.errors_by_type['timeout'], 1)
        self.assertGreater(stats.api_error_rate, 0)
        self.assertGreater(stats.agent_error_rate, 0)
    
    async def test_get_24h_stats(self):
        """Test comprehensive 24-hour statistics generation."""
        # Add sample data across all categories
        await self.aggregator.record_request("/api/test", 200, 100)
        await self.aggregator.record_agent_execution("supervisor", 1000, True)
        await self.aggregator.record_websocket_event("connect", "conn-1", True)
        await self.aggregator.record_error("api", "test_error")
        
        # Get comprehensive stats
        stats = await self.aggregator.get_24h_stats()
        
        # Verify structure
        self.assertIn('request_counts', stats)
        self.assertIn('agent_stats', stats)
        self.assertIn('websocket_metrics', stats)
        self.assertIn('error_rates', stats)
        self.assertIn('timestamp', stats)
        self.assertIn('retention_hours', stats)
        
        # Verify request counts
        request_stats = stats['request_counts']
        self.assertIn('total_requests', request_stats)
        self.assertIn('hourly_breakdown', request_stats)
        
        # Verify agent stats
        agent_stats = stats['agent_stats']
        self.assertIn('total_executions', agent_stats)
        self.assertIn('success_rate', agent_stats)
        self.assertIn('agents_by_type', agent_stats)
        
        # Verify WebSocket metrics
        websocket_stats = stats['websocket_metrics']
        self.assertIn('active_connections', websocket_stats)
        self.assertIn('connection_success_rate', websocket_stats)
        
        # Verify error rates
        error_stats = stats['error_rates']
        self.assertIn('overall_error_rate', error_stats)
        self.assertIn('errors_by_type', error_stats)
    
    async def test_reset_stats(self):
        """Test statistics reset functionality."""
        # Add some data
        await self.aggregator.record_request("/api/test", 200, 100)
        await self.aggregator.record_agent_execution("supervisor", 1000, True)
        await self.aggregator.record_websocket_event("connect", "conn-1", True)
        await self.aggregator.record_error("api", "test_error")
        
        # Verify data exists
        self.assertGreater(len(self.aggregator.current_hour_requests), 0)
        self.assertGreater(len(self.aggregator.agent_executions), 0)
        self.assertGreater(len(self.aggregator.websocket_events), 0)
        self.assertGreater(len(self.aggregator.error_events), 0)
        self.assertGreater(len(self.aggregator.active_connections), 0)
        
        # Reset stats
        await self.aggregator.reset_stats()
        
        # Verify data is cleared
        self.assertEqual(len(self.aggregator.current_hour_requests), 0)
        self.assertEqual(len(self.aggregator.agent_executions), 0)
        self.assertEqual(len(self.aggregator.websocket_events), 0)
        self.assertEqual(len(self.aggregator.error_events), 0)
        self.assertEqual(len(self.aggregator.active_connections), 0)
    
    @patch('netra_backend.app.monitoring.websocket_metrics.get_websocket_metrics')
    async def test_aggregate_websocket_stats_external(self, mock_websocket_metrics):
        """Test aggregation from external WebSocket metrics."""
        # Mock external metrics
        mock_websocket_metrics.return_value = {
            'active_connections': ['conn-1', 'conn-2', 'conn-3']
        }
        
        # Run aggregation
        await self.aggregator._aggregate_websocket_stats()
        
        # Check that connections were recorded
        self.assertEqual(len(self.aggregator.websocket_events), 3)
        self.assertEqual(len(self.aggregator.active_connections), 3)
    
    @patch('netra_backend.app.core.registry.universal_registry.get_global_registry')
    async def test_aggregate_agent_stats_external(self, mock_registry):
        """Test aggregation from external agent registry."""
        # Mock agent registry
        mock_agent_registry = MagicMock()
        mock_agent_registry.get_stats.return_value = {
            'registered_count': 5,
            'active_count': 3
        }
        mock_registry.return_value = mock_agent_registry
        
        # Run aggregation (should not raise exception)
        await self.aggregator._aggregate_agent_stats()
        
        # Verify registry was called
        mock_registry.assert_called_with("agent")


class TestStatsAggregatorGlobal(SSotAsyncTestCase):
    """Test global stats aggregator functionality."""
    
    async def asyncTearDown(self):
        """Clean up global state."""
        # Reset global aggregator
        import netra_backend.app.monitoring.stats_aggregator as module
        module._stats_aggregator = None
        await super().asyncTearDown()
    
    async def test_get_stats_aggregator_singleton(self):
        """Test global stats aggregator singleton pattern."""
        # Get aggregator twice
        aggregator1 = await get_stats_aggregator()
        aggregator2 = await get_stats_aggregator()
        
        # Should be the same instance
        self.assertIs(aggregator1, aggregator2)
        self.assertTrue(aggregator1._is_aggregating)
    
    async def test_convenience_functions(self):
        """Test convenience functions for recording stats."""
        # Use convenience functions
        await record_request_stats("/api/test", 200, 150.5)
        await record_agent_execution_stats("supervisor", 1000.0, True, "corr-123")
        await record_websocket_stats("connect", "conn-456", True, {"user": "test"})
        
        # Get aggregator and verify data was recorded
        aggregator = await get_stats_aggregator()
        self.assertEqual(aggregator.current_hour_requests["/api/test"], 1)
        self.assertEqual(len(aggregator.agent_executions), 1)
        self.assertEqual(len(aggregator.websocket_events), 1)


class TestStatsAggregatorErrorHandling(SSotAsyncTestCase):
    """Test error handling in StatsAggregator."""
    
    async def asyncSetUp(self):
        """Set up test environment."""
        await super().asyncSetUp()
        self.aggregator = StatsAggregator()
    
    async def asyncTearDown(self):
        """Clean up test environment."""
        await self.aggregator.stop_aggregation()
        await super().asyncTearDown()
    
    async def test_aggregation_loop_error_recovery(self):
        """Test that aggregation loop recovers from errors."""
        # Mock an error in periodic aggregation
        with patch.object(self.aggregator, '_aggregate_periodic_stats',
                         side_effect=Exception("Aggregation error")):
            
            # Start aggregation
            await self.aggregator.start_aggregation()
            
            # Wait briefly for loop to handle error
            await asyncio.sleep(0.1)
            
            # Aggregation should still be running
            self.assertTrue(self.aggregator._is_aggregating)
    
    async def test_empty_data_calculations(self):
        """Test calculations with empty data sets."""
        # Test with no data
        request_stats = self.aggregator._calculate_request_stats()
        self.assertEqual(request_stats.total_requests, 0)
        
        agent_stats = self.aggregator._calculate_agent_stats()
        self.assertEqual(agent_stats.total_executions, 0)
        
        websocket_stats = self.aggregator._calculate_websocket_stats()
        self.assertEqual(websocket_stats.total_connections, 0)
        
        error_stats = self.aggregator._calculate_error_rates()
        self.assertEqual(error_stats.overall_error_rate, 0.0)
    
    @patch('netra_backend.app.monitoring.websocket_metrics.get_websocket_metrics',
           side_effect=Exception("WebSocket error"))
    async def test_external_aggregation_failure(self, mock_websocket):
        """Test graceful handling of external aggregation failures."""
        # Should not raise exception
        await self.aggregator._aggregate_websocket_stats()
        
        # Should not have recorded any events
        self.assertEqual(len(self.aggregator.websocket_events), 0)


if __name__ == '__main__':
    # Run tests
    import unittest
    unittest.main()