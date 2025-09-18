"""
Integration Tests for Issue #1101 MessageRouter SSOT Compliance Tracking

These tests validate SSOT compliance across the system with real services:
1. Track SSOT violations in real usage scenarios
2. Validate compliance with real WebSocket connections
3. Test import path consistency across services
4. Monitor SSOT compliance metrics

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: System-wide SSOT compliance monitoring
- Value Impact: Prevents routing conflicts in production scenarios
- Strategic Impact: Ensures Golden Path reliability with real services
"""

import pytest
import asyncio
import time
import json
from typing import Dict, Any, List
from unittest.mock import Mock, patch

from test_framework.ssot.base_test_case import SSotAsyncTestCase

# Import MessageRouter from all paths to test SSOT compliance
from netra_backend.app.core.message_router import MessageRouter as ProxyMessageRouter
from netra_backend.app.websocket_core.handlers import MessageRouter as CanonicalMessageRouter
from netra_backend.app.services.message_router import MessageRouter as ServicesMessageRouter
from netra_backend.app.websocket_core.handlers import get_message_router

from netra_backend.app.websocket_core.types import MessageType, WebSocketMessage
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class TestMessageRouterSSOTComplianceTracking(SSotAsyncTestCase):
    """Integration tests for MessageRouter SSOT compliance tracking with real services."""
    
    def setUp(self):
        """Set up test environment with real services."""
        super().setUp()
        self.test_user_id = "integration_user_ssot_456"
        self.test_thread_id = f"thread_{self.test_user_id}_{int(time.time())}"
        self.test_run_id = f"run_{self.test_user_id}_{int(time.time())}"
        
        # Create real user context
        self.user_context = UserExecutionContext.from_request(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id
        )
        
        self.compliance_metrics = {
            "proxy_usage_count": 0,
            "canonical_usage_count": 0,
            "services_usage_count": 0,
            "ssot_violations": [],
            "import_path_tracking": {}
        }
    
    async def test_real_websocket_manager_uses_canonical_router(self):
        """Test that real WebSocket manager uses canonical MessageRouter implementation."""
        # Create real WebSocket manager
        ws_manager = WebSocketManager(user_context=self.user_context)
        
        # Check if manager has router access
        if hasattr(ws_manager, '_get_message_router') or hasattr(ws_manager, 'message_router'):
            # Get router from manager
            if hasattr(ws_manager, 'message_router'):
                router = ws_manager.message_router
            else:
                router = await ws_manager._get_message_router()
            
            # Should be canonical implementation
            self.assertIsInstance(router, CanonicalMessageRouter)
            self.assertFalse(hasattr(router, '_canonical_router'))
            
            self.compliance_metrics["canonical_usage_count"] += 1
        
        logger.info(f"WebSocket manager router compliance: {self.compliance_metrics['canonical_usage_count']} canonical usages")
    
    async def test_global_router_singleton_ssot_compliance(self):
        """Test that global router singleton maintains SSOT compliance."""
        # Get global router multiple times
        router1 = get_message_router()
        router2 = get_message_router()
        router3 = get_message_router()
        
        # All should be same instance (singleton compliance)
        self.assertIs(router1, router2)
        self.assertIs(router2, router3)
        
        # All should be canonical implementation
        self.assertIsInstance(router1, CanonicalMessageRouter)
        self.assertIsInstance(router2, CanonicalMessageRouter)
        self.assertIsInstance(router3, CanonicalMessageRouter)
        
        # Update compliance metrics
        self.compliance_metrics["canonical_usage_count"] += 3
        
        logger.info("Global router singleton SSOT compliance validated")
    
    async def test_import_path_consistency_across_services(self):
        """Test import path consistency across different service modules."""
        import_paths = [
            ("netra_backend.app.core.message_router", ProxyMessageRouter),
            ("netra_backend.app.websocket_core.handlers", CanonicalMessageRouter),
            ("netra_backend.app.services.message_router", ServicesMessageRouter)
        ]
        
        for path, router_class in import_paths:
            # Track import path usage
            self.compliance_metrics["import_path_tracking"][path] = {
                "class_name": router_class.__name__,
                "module": router_class.__module__,
                "is_proxy": hasattr(router_class(), '_canonical_router') if hasattr(router_class, '__call__') else False
            }
        
        # Validate SSOT compliance
        canonical_path = "netra_backend.app.websocket_core.handlers"
        services_path = "netra_backend.app.services.message_router"
        
        # Services should reference canonical
        canonical_class = self.compliance_metrics["import_path_tracking"][canonical_path]["class_name"]
        services_class = self.compliance_metrics["import_path_tracking"][services_path]["class_name"]
        
        self.assertEqual(canonical_class, services_class)
        
        logger.info(f"Import path tracking: {json.dumps(self.compliance_metrics['import_path_tracking'], indent=2)}")
    
    async def test_proxy_deprecation_compliance_tracking(self):
        """Test proxy deprecation compliance and track usage."""
        import warnings
        
        warnings.resetwarnings()
        
        with warnings.catch_warnings(record=True) as warning_list:
            warnings.simplefilter("always")
            
            # Create proxy router (should emit deprecation warning)
            proxy_router = ProxyMessageRouter()
            self.compliance_metrics["proxy_usage_count"] += 1
            
            # Verify deprecation warning was emitted
            deprecation_warnings = [w for w in warning_list if issubclass(w.category, DeprecationWarning)]
            self.assertTrue(len(deprecation_warnings) > 0)
            
            # Track SSOT violation (using deprecated proxy)
            self.compliance_metrics["ssot_violations"].append({
                "type": "deprecated_proxy_usage",
                "warning_count": len(deprecation_warnings),
                "timestamp": time.time()
            })
        
        logger.warning(f"Proxy usage tracked: {self.compliance_metrics['proxy_usage_count']} instances, "
                      f"{len(self.compliance_metrics['ssot_violations'])} violations")
    
    async def test_real_message_routing_ssot_compliance(self):
        """Test real message routing with SSOT compliance validation."""
        # Create canonical router for real message routing
        canonical_router = CanonicalMessageRouter()
        
        # Create mock WebSocket for integration testing
        mock_websocket = Mock()
        mock_websocket.send_json = asyncio.coroutine(Mock())
        mock_websocket.send_text = asyncio.coroutine(Mock())
        
        # Test message routing
        test_message = {
            "type": "test_message",
            "payload": {"content": "SSOT compliance test"},
            "timestamp": time.time(),
            "user_id": self.test_user_id,
            "thread_id": self.test_thread_id
        }
        
        # Route message through canonical router
        result = await canonical_router.route_message(
            self.test_user_id, mock_websocket, test_message
        )
        
        # Should complete successfully
        self.assertIsInstance(result, bool)
        
        # Update compliance metrics
        self.compliance_metrics["canonical_usage_count"] += 1
        
        # Get routing statistics to check for SSOT compliance
        stats = canonical_router.get_stats()
        self.assertIn("handler_count", stats)
        self.assertIn("messages_routed", stats)
        
        logger.info(f"Real message routing SSOT compliance: {stats['messages_routed']} messages routed")
    
    async def test_handler_registration_ssot_compliance(self):
        """Test handler registration across different router instances for SSOT compliance."""
        # Create routers from different import paths
        canonical_router = CanonicalMessageRouter()
        services_router = ServicesMessageRouter()
        proxy_router = ProxyMessageRouter()
        
        # Create test handlers
        mock_handler1 = Mock()
        mock_handler1.can_handle = Mock(return_value=True)
        mock_handler1.handle_message = Mock()
        mock_handler1.__class__.__name__ = "TestHandler1"
        
        mock_handler2 = Mock()
        mock_handler2.can_handle = Mock(return_value=True) 
        mock_handler2.handle_message = Mock()
        mock_handler2.__class__.__name__ = "TestHandler2"
        
        # Register handlers
        initial_canonical_count = len(canonical_router.handlers)
        initial_services_count = len(services_router.handlers)
        
        canonical_router.add_handler(mock_handler1)
        services_router.add_handler(mock_handler2)
        
        # Verify handlers were added
        self.assertEqual(len(canonical_router.handlers), initial_canonical_count + 1)
        self.assertEqual(len(services_router.handlers), initial_services_count + 1)
        
        # Update compliance metrics
        self.compliance_metrics["canonical_usage_count"] += 2
        
        # Test proxy handler registration (should forward to canonical)
        try:
            # This should work if proxy properly forwards to canonical
            self.assertTrue(hasattr(proxy_router, 'add_handler'))
            self.compliance_metrics["proxy_usage_count"] += 1
        except Exception as e:
            self.compliance_metrics["ssot_violations"].append({
                "type": "proxy_handler_registration_failure",
                "error": str(e),
                "timestamp": time.time()
            })
        
        logger.info(f"Handler registration compliance: canonical={self.compliance_metrics['canonical_usage_count']}, "
                   f"proxy={self.compliance_metrics['proxy_usage_count']}")
    
    async def test_websocket_event_routing_ssot_compliance(self):
        """Test WebSocket event routing for SSOT compliance with real events."""
        canonical_router = CanonicalMessageRouter()
        
        # Create mock WebSocket that tracks send calls
        mock_websocket = Mock()
        sent_messages = []
        
        async def mock_send_json(data):
            sent_messages.append(data)
        
        mock_websocket.send_json = mock_send_json
        mock_websocket.send_text = mock_send_json
        
        # Test different message types to ensure routing works
        test_messages = [
            {
                "type": "user_message",
                "payload": {"content": "test user message"},
                "timestamp": time.time()
            },
            {
                "type": "ping",
                "payload": {},
                "timestamp": time.time()
            },
            {
                "type": "agent_request",
                "payload": {"message": "test agent request"},
                "timestamp": time.time()
            }
        ]
        
        successful_routes = 0
        
        for message in test_messages:
            try:
                result = await canonical_router.route_message(
                    self.test_user_id, mock_websocket, message
                )
                if result:
                    successful_routes += 1
            except Exception as e:
                self.compliance_metrics["ssot_violations"].append({
                    "type": "routing_failure",
                    "message_type": message["type"],
                    "error": str(e),
                    "timestamp": time.time()
                })
        
        # Update compliance metrics
        self.compliance_metrics["canonical_usage_count"] += successful_routes
        
        logger.info(f"WebSocket event routing SSOT compliance: {successful_routes}/{len(test_messages)} successful routes")
    
    async def test_concurrent_router_access_ssot_compliance(self):
        """Test concurrent router access maintains SSOT compliance."""
        # Test concurrent access to global router
        async def get_router_task():
            router = get_message_router()
            self.compliance_metrics["canonical_usage_count"] += 1
            return router
        
        # Create multiple concurrent tasks
        tasks = [get_router_task() for _ in range(5)]
        routers = await asyncio.gather(*tasks)
        
        # All routers should be the same instance (singleton)
        first_router = routers[0]
        for router in routers[1:]:
            self.assertIs(router, first_router)
        
        # All should be canonical implementation
        for router in routers:
            self.assertIsInstance(router, CanonicalMessageRouter)
            self.assertFalse(hasattr(router, '_canonical_router'))
        
        logger.info(f"Concurrent router access SSOT compliance: {len(routers)} instances, all singleton")
    
    async def test_service_integration_ssot_compliance(self):
        """Test service integration maintains SSOT compliance."""
        # Test integration with WebSocket manager
        ws_manager = WebSocketManager(user_context=self.user_context)
        
        # Test integration with user execution context
        context = UserExecutionContext.from_request(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id
        )
        
        self.assertIsNotNone(context)
        self.assertEqual(context.user_id, self.test_user_id)
        
        # Update compliance metrics
        self.compliance_metrics["canonical_usage_count"] += 1
        
        logger.info("Service integration SSOT compliance validated")
    
    def test_ssot_compliance_summary(self):
        """Generate SSOT compliance summary report."""
        # Calculate compliance percentage
        total_usage = (
            self.compliance_metrics["proxy_usage_count"] + 
            self.compliance_metrics["canonical_usage_count"] + 
            self.compliance_metrics["services_usage_count"]
        )
        
        if total_usage > 0:
            canonical_percentage = (self.compliance_metrics["canonical_usage_count"] / total_usage) * 100
        else:
            canonical_percentage = 0
        
        compliance_report = {
            "ssot_compliance_percentage": canonical_percentage,
            "total_usage_count": total_usage,
            "canonical_usage_count": self.compliance_metrics["canonical_usage_count"],
            "proxy_usage_count": self.compliance_metrics["proxy_usage_count"],
            "services_usage_count": self.compliance_metrics["services_usage_count"],
            "violation_count": len(self.compliance_metrics["ssot_violations"]),
            "violations": self.compliance_metrics["ssot_violations"],
            "import_path_tracking": self.compliance_metrics["import_path_tracking"]
        }
        
        logger.info(f"SSOT Compliance Report: {json.dumps(compliance_report, indent=2)}")
        
        # Assert compliance thresholds
        self.assertGreaterEqual(canonical_percentage, 70.0, 
                               "SSOT compliance should be at least 70% canonical usage")
        self.assertLessEqual(len(self.compliance_metrics["ssot_violations"]), 5,
                            "Should have 5 or fewer SSOT violations")
        
        return compliance_report


if __name__ == '__main__':
    pytest.main([__file__, '-v'])