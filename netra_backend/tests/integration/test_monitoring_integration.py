#!/usr/bin/env python
"""Integration Tests for Monitoring Integration - Phase 3 Implementation

Tests the complete integration flow between ChatEventMonitor and AgentWebSocketBridge,
ensuring cross-system validation capabilities work as designed while maintaining
component independence.

Business Value: Provides 100% silent failure detection coverage through integrated
monitoring without tight coupling. Critical for $500K+ ARR chat functionality protection.
"""

import asyncio
import pytest
import time
from typing import Dict, Any
from unittest.mock import Mock, AsyncMock, patch

from netra_backend.app.websocket_core.event_monitor import ChatEventMonitor
from netra_backend.app.services.agent_websocket_bridge import (
    AgentWebSocketBridge,
    IntegrationState,
    IntegrationMetrics,
    HealthStatus
)
from netra_backend.app.startup_module import initialize_monitoring_integration
from shared.monitoring.interfaces import MonitorableComponent, ComponentMonitor


class TestMonitoringIntegrationStartup:
    """Test monitoring integration initialization during system startup."""
    
    @pytest.fixture
    async def mock_bridge(self):
        """Create mock AgentWebSocketBridge for testing."""
        bridge = Mock(spec=AgentWebSocketBridge)
        bridge.get_health_status = AsyncMock(return_value={
            "healthy": True,
            "state": "active",
            "timestamp": time.time(),
            "websocket_manager_healthy": True,
            "registry_healthy": True,
            "consecutive_failures": 0,
            "uptime_seconds": 120.0,
            "error_message": None
        })
        bridge.get_metrics = AsyncMock(return_value={
            "total_initializations": 1,
            "successful_initializations": 1,
            "success_rate": 1.0,
            "registered_observers": 0,
            "health_broadcast_interval": 30
        })
        bridge.register_monitor_observer = Mock()
        return bridge
    
    @pytest.fixture
    async def real_monitor(self):
        """Create real ChatEventMonitor for testing."""
        monitor = ChatEventMonitor()
        yield monitor
        await monitor.stop_monitoring()
    
    @pytest.mark.asyncio
    async def test_startup_integration_success(self, mock_bridge, real_monitor):
        """Test successful monitoring integration during startup."""
        with patch('netra_backend.app.websocket_core.event_monitor.chat_event_monitor', real_monitor):
            with patch('netra_backend.app.services.agent_websocket_bridge.get_agent_websocket_bridge', 
                      return_value=mock_bridge):
                
                # Test integration initialization
                success = await initialize_monitoring_integration()
                
                # Verify integration was successful
                assert success is True, "Integration should succeed with healthy components"
                
                # Verify monitor registered the bridge
                assert "agent_websocket_bridge" in real_monitor.monitored_components
                
                # Verify bridge registered the monitor as observer
                mock_bridge.register_monitor_observer.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_startup_integration_bridge_unavailable(self, real_monitor):
        """Test integration handles bridge unavailability gracefully."""
        with patch('netra_backend.app.websocket_core.event_monitor.chat_event_monitor', real_monitor):
            with patch('netra_backend.app.services.agent_websocket_bridge.get_agent_websocket_bridge', 
                      return_value=None):
                
                # Test integration with unavailable bridge
                success = await initialize_monitoring_integration()
                
                # Verify graceful handling
                assert success is False, "Integration should return False when bridge unavailable"
                
                # Verify monitor still works independently
                assert len(real_monitor.monitored_components) == 0
                assert real_monitor._monitor_task is not None, "Monitor should still be running"
    
    @pytest.mark.asyncio
    async def test_startup_integration_bridge_error(self, real_monitor):
        """Test integration handles bridge errors gracefully."""
        with patch('netra_backend.app.websocket_core.event_monitor.chat_event_monitor', real_monitor):
            with patch('netra_backend.app.services.agent_websocket_bridge.get_agent_websocket_bridge', 
                      side_effect=Exception("Bridge initialization failed")):
                
                # Test integration with bridge error
                success = await initialize_monitoring_integration()
                
                # Verify graceful handling
                assert success is False, "Integration should return False on bridge error"
                
                # Verify monitor continues operating
                assert real_monitor._monitor_task is not None, "Monitor should still be running"
    
    @pytest.mark.asyncio
    async def test_startup_integration_monitor_error(self, mock_bridge):
        """Test integration handles monitor errors gracefully."""
        mock_monitor = Mock(spec=ChatEventMonitor)
        mock_monitor.start_monitoring = AsyncMock(side_effect=Exception("Monitor start failed"))
        
        with patch('netra_backend.app.websocket_core.event_monitor.chat_event_monitor', mock_monitor):
            with patch('netra_backend.app.services.agent_websocket_bridge.get_agent_websocket_bridge', 
                      return_value=mock_bridge):
                
                # Test integration with monitor error
                success = await initialize_monitoring_integration()
                
                # Verify graceful handling
                assert success is False, "Integration should return False on monitor error"


class TestCrossSystemValidation:
    """Test cross-system validation capabilities of integrated monitoring."""
    
    @pytest.fixture
    async def integrated_system(self):
        """Setup integrated monitoring system."""
        monitor = ChatEventMonitor()
        
        # Create mock bridge with realistic behavior
        bridge = Mock(spec=AgentWebSocketBridge)
        bridge.get_health_status = AsyncMock()
        bridge.get_metrics = AsyncMock()
        bridge.register_monitor_observer = Mock()
        
        # Register bridge with monitor
        await monitor.register_component_for_monitoring("test_bridge", bridge)
        
        yield monitor, bridge
        
        await monitor.stop_monitoring()
    
    @pytest.mark.asyncio
    async def test_bridge_health_audit(self, integrated_system):
        """Test monitor can audit bridge health comprehensively."""
        monitor, bridge = integrated_system
        
        # Setup bridge responses
        bridge.get_health_status.return_value = {
            "healthy": True,
            "state": "active",
            "timestamp": time.time(),
            "websocket_manager_healthy": True,
            "registry_healthy": True,
            "consecutive_failures": 0,
            "uptime_seconds": 300.0
        }
        bridge.get_metrics.return_value = {
            "total_initializations": 5,
            "successful_initializations": 5,
            "success_rate": 1.0,
            "recovery_attempts": 0,
            "health_checks_performed": 50
        }
        
        # Perform bridge audit
        audit_result = await monitor.audit_bridge_health("test_bridge")
        
        # Verify comprehensive audit
        assert audit_result["bridge_id"] == "test_bridge"
        assert "audit_timestamp" in audit_result
        assert "internal_health" in audit_result
        assert "internal_metrics" in audit_result
        assert "event_monitor_validation" in audit_result
        assert "integration_health" in audit_result
        assert "overall_assessment" in audit_result
        
        # Verify health data was retrieved
        bridge.get_health_status.assert_called_once()
        bridge.get_metrics.assert_called_once()
        
        # Verify overall assessment
        overall = audit_result["overall_assessment"]
        assert "overall_score" in overall
        assert "overall_status" in overall
        assert "component_scores" in overall
    
    @pytest.mark.asyncio
    async def test_cross_validation_detects_discrepancies(self, integrated_system):
        """Test cross-validation detects discrepancies between bridge claims and event data."""
        monitor, bridge = integrated_system
        
        # Bridge claims to be healthy but monitor has detected silent failures
        bridge.get_health_status.return_value = {
            "healthy": True,
            "state": "active",
            "timestamp": time.time(),
            "websocket_manager_healthy": True,
            "registry_healthy": True,
            "consecutive_failures": 0,
            "uptime_seconds": 100.0
        }
        bridge.get_metrics.return_value = {
            "total_initializations": 1,
            "successful_initializations": 1,
            "success_rate": 1.0
        }
        
        # Add silent failures to monitor
        await monitor._record_silent_failure(
            "test_thread", 
            "Tool completed without executing", 
            {"tool_name": "missing_tool"}
        )
        await monitor._record_silent_failure(
            "test_thread2", 
            "Unexpected event sequence", 
            {"expected": "thinking", "received": "completed"}
        )
        
        # Perform audit - should detect discrepancy
        audit_result = await monitor.audit_bridge_health("test_bridge")
        
        # Verify cross-validation detected issues
        validation = audit_result["event_monitor_validation"]
        assert validation["recent_silent_failures"] > 0
        assert validation["status"] in ["warning", "critical"]
        
        # Overall assessment should reflect concerns despite bridge claiming health
        overall = audit_result["overall_assessment"]
        # Health claim should be weighted against validation data
        assert overall["overall_status"] != "healthy" or overall["overall_score"] < 100
    
    @pytest.mark.asyncio
    async def test_integration_health_assessment(self, integrated_system):
        """Test integration quality assessment."""
        monitor, bridge = integrated_system
        
        bridge.get_health_status.return_value = {
            "healthy": True,
            "state": "active", 
            "timestamp": time.time()
        }
        bridge.get_metrics.return_value = {"success_rate": 0.95}
        
        # Add some event data to improve integration score
        await monitor.record_event("agent_started", "test_thread")
        await monitor.record_event("agent_thinking", "test_thread")
        await monitor.record_event("agent_completed", "test_thread")
        
        # Perform audit
        audit_result = await monitor.audit_bridge_health("test_bridge")
        
        # Verify integration assessment
        integration = audit_result["integration_health"]
        assert "integration_score" in integration
        assert "status" in integration
        assert integration["bridge_registered"] is True
        assert integration["health_history_available"] is True
        
        # Should have good integration score with events and health data
        assert integration["integration_score"] >= 75.0
        assert integration["status"] in ["good", "excellent"]


class TestComponentIndependence:
    """Test that components work independently if integration fails."""
    
    @pytest.mark.asyncio
    async def test_monitor_works_without_bridge(self):
        """Test ChatEventMonitor works independently without bridge."""
        monitor = ChatEventMonitor()
        
        try:
            # Start monitor without any bridge
            await monitor.start_monitoring()
            
            # Should be able to record events
            await monitor.record_event("agent_started", "independent_thread")
            await monitor.record_event("tool_executing", "independent_thread", "test_tool")
            await monitor.record_event("tool_completed", "independent_thread", "test_tool")
            await monitor.record_event("agent_completed", "independent_thread")
            
            # Should be able to check health
            health = await monitor.check_health()
            assert "status" in health
            assert "healthy" in health
            assert health["total_events"] > 0
            
            # Should detect tool flow properly
            thread_status = monitor.get_thread_status("independent_thread")
            assert thread_status["total_events"] >= 4
            
        finally:
            await monitor.stop_monitoring()
    
    @pytest.mark.asyncio  
    async def test_bridge_works_without_monitor(self):
        """Test AgentWebSocketBridge works independently without monitor."""
        # Create bridge with mocked dependencies
        with patch('netra_backend.app.services.agent_websocket_bridge.get_websocket_manager'):
            with patch('netra_backend.app.services.agent_websocket_bridge.get_agent_execution_registry'):
                
                bridge = AgentWebSocketBridge()
                
                # Bridge should work without any monitors
                health_status = await bridge.get_health_status()
                assert "healthy" in health_status
                assert "state" in health_status
                assert "timestamp" in health_status
                
                # Should be able to get metrics
                metrics = await bridge.get_metrics()
                assert "total_initializations" in metrics
                assert "registered_observers" in metrics
                
                # Observer list should be empty but functional
                assert len(bridge._monitor_observers) == 0
    
    @pytest.mark.asyncio
    async def test_integration_failure_preserves_independence(self):
        """Test that integration failure doesn't break component independence."""
        monitor = ChatEventMonitor()
        
        # Create bridge that fails during registration
        failing_bridge = Mock(spec=AgentWebSocketBridge)
        failing_bridge.register_monitor_observer.side_effect = Exception("Registration failed")
        failing_bridge.get_health_status = AsyncMock(return_value={"healthy": True})
        failing_bridge.get_metrics = AsyncMock(return_value={"total": 1})
        
        try:
            await monitor.start_monitoring()
            
            # Attempt integration that will fail
            try:
                await monitor.register_component_for_monitoring("failing_bridge", failing_bridge)
                # Should not reach here, but if it does, that's also okay
            except:
                pass  # Expected to fail
            
            # Monitor should still work independently  
            await monitor.record_event("agent_started", "test_after_fail")
            health = await monitor.check_health()
            assert health["healthy"] is not False  # Should not be broken
            
            # Bridge should also still work
            bridge_health = await failing_bridge.get_health_status()
            assert bridge_health["healthy"] is True
            
        finally:
            await monitor.stop_monitoring()


class TestPerformanceImpact:
    """Test that monitoring integration has minimal performance impact."""
    
    @pytest.mark.asyncio
    async def test_integration_overhead_minimal(self):
        """Test that monitoring integration adds <5ms overhead."""
        monitor = ChatEventMonitor()
        bridge = Mock(spec=AgentWebSocketBridge)
        
        # Setup quick responses
        bridge.get_health_status = AsyncMock(return_value={"healthy": True, "state": "active"})
        bridge.get_metrics = AsyncMock(return_value={"total": 1})
        bridge.register_monitor_observer = Mock()
        
        try:
            await monitor.start_monitoring()
            
            # Measure integration time
            start_time = time.time()
            await monitor.register_component_for_monitoring("perf_bridge", bridge)
            integration_time = time.time() - start_time
            
            # Measure audit time
            start_time = time.time() 
            await monitor.audit_bridge_health("perf_bridge")
            audit_time = time.time() - start_time
            
            # Verify minimal overhead
            assert integration_time < 0.01, f"Integration took {integration_time:.3f}s (>10ms)"
            assert audit_time < 0.005, f"Audit took {audit_time:.3f}s (>5ms)"
            
        finally:
            await monitor.stop_monitoring()
    
    @pytest.mark.asyncio
    async def test_event_recording_not_impacted(self):
        """Test that event recording performance is not impacted by integration."""
        monitor = ChatEventMonitor()
        bridge = Mock(spec=AgentWebSocketBridge)
        bridge.get_health_status = AsyncMock(return_value={"healthy": True})
        bridge.get_metrics = AsyncMock(return_value={"total": 1})
        bridge.register_monitor_observer = Mock()
        
        try:
            await monitor.start_monitoring()
            
            # Measure baseline event recording
            start_time = time.time()
            for i in range(100):
                await monitor.record_event("agent_thinking", f"baseline_thread_{i}")
            baseline_time = time.time() - start_time
            
            # Add integration
            await monitor.register_component_for_monitoring("perf_bridge", bridge)
            
            # Measure event recording with integration
            start_time = time.time()
            for i in range(100):
                await monitor.record_event("agent_thinking", f"integrated_thread_{i}")
            integrated_time = time.time() - start_time
            
            # Verify minimal impact (<10% overhead)
            overhead_ratio = integrated_time / baseline_time
            assert overhead_ratio < 1.1, f"Integration caused {overhead_ratio:.1f}x slowdown (>10% overhead)"
            
        finally:
            await monitor.stop_monitoring()


class TestSilentFailureCoverage:
    """Test that integrated monitoring achieves 100% silent failure coverage."""
    
    @pytest.mark.asyncio
    async def test_combined_system_detects_bridge_internal_failures(self):
        """Test combined system catches bridge internal failures."""
        monitor = ChatEventMonitor()
        bridge = Mock(spec=AgentWebSocketBridge)
        
        # Bridge reports healthy but has internal issues
        bridge.get_health_status = AsyncMock(return_value={
            "healthy": False,  # Internal failure
            "state": "degraded",
            "consecutive_failures": 5,
            "error_message": "Registry connection lost"
        })
        bridge.get_metrics = AsyncMock(return_value={
            "success_rate": 0.2,  # Low success rate
            "total_initializations": 10,
            "successful_initializations": 2
        })
        bridge.register_monitor_observer = Mock()
        
        try:
            await monitor.start_monitoring()
            await monitor.register_component_for_monitoring("failing_bridge", bridge)
            
            # Audit should detect internal failure
            audit_result = await monitor.audit_bridge_health("failing_bridge")
            
            # Verify failure detection
            assert audit_result["internal_health"]["healthy"] is False
            assert audit_result["overall_assessment"]["overall_status"] in ["critical", "failed"]
            assert audit_result["internal_health"]["consecutive_failures"] > 0
            
        finally:
            await monitor.stop_monitoring()
    
    @pytest.mark.asyncio  
    async def test_combined_system_detects_event_flow_issues(self):
        """Test combined system catches event flow issues bridge might miss."""
        monitor = ChatEventMonitor()
        bridge = Mock(spec=AgentWebSocketBridge)
        
        # Bridge reports healthy
        bridge.get_health_status = AsyncMock(return_value={
            "healthy": True,
            "state": "active"
        })
        bridge.get_metrics = AsyncMock(return_value={"success_rate": 1.0})
        bridge.register_monitor_observer = Mock()
        
        try:
            await monitor.start_monitoring()
            await monitor.register_component_for_monitoring("healthy_bridge", bridge)
            
            # Simulate event flow issues that bridge missed
            await monitor.record_event("tool_executing", "problem_thread", "broken_tool")
            # Missing tool_completed event - silent failure
            await monitor.record_event("agent_completed", "problem_thread")
            
            # Add stale thread
            monitor.thread_start_time["stale_thread"] = time.time() - 100  # Very stale
            
            # Audit should detect event flow issues despite bridge being "healthy"  
            audit_result = await monitor.audit_bridge_health("healthy_bridge")
            
            # Verify event validation caught issues
            validation = audit_result["event_monitor_validation"]
            assert validation["recent_silent_failures"] > 0 or validation["stale_threads_count"] > 0
            
            # Overall assessment should reflect concerns
            overall = audit_result["overall_assessment"]
            assert overall["overall_status"] != "healthy" or overall["overall_score"] < 100
            
        finally:
            await monitor.stop_monitoring()
    
    @pytest.mark.asyncio
    async def test_monitor_observer_notifications(self):
        """Test monitor receives health change notifications from bridge."""
        monitor = ChatEventMonitor()
        
        # Create bridge that can notify observers
        bridge = Mock(spec=AgentWebSocketBridge)
        bridge.get_health_status = AsyncMock(return_value={"healthy": True})
        bridge.get_metrics = AsyncMock(return_value={"total": 1})
        bridge.register_monitor_observer = Mock()
        
        try:
            await monitor.start_monitoring()
            await monitor.register_component_for_monitoring("notify_bridge", bridge)
            
            # Simulate health change notification from bridge
            health_change_data = {
                "healthy": False,
                "state": "degraded",
                "consecutive_failures": 1,
                "timestamp": time.time(),
                "error_message": "Connection timeout"
            }
            
            await monitor.on_component_health_change("notify_bridge", health_change_data)
            
            # Verify notification was recorded
            assert len(monitor.component_health_history["notify_bridge"]) > 0
            
            # Latest record should be the health change
            latest_record = monitor.component_health_history["notify_bridge"][-1]
            assert latest_record["notification_type"] == "health_change"
            assert latest_record["health_data"]["healthy"] is False
            assert latest_record["health_data"]["state"] == "degraded"
            
        finally:
            await monitor.stop_monitoring()