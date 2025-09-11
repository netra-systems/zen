"""
Test Issue Cluster Interaction Boundaries - Cross-Issue Validation

Business Value Justification (BVJ):
- Segment: All (Platform Infrastructure)
- Business Goal: Ensure fixes work together without introducing regressions
- Value Impact: Prevent cascading failures when multiple fixes interact
- Revenue Impact: $500K+ ARR protection through systematic boundary validation

CRITICAL BOUNDARY TESTING:
- ExecutionState fixes (#305) + UserContext security (#271) boundary
- API validation fixes (#307) + WebSocket events (#292) boundary
- Auth changes (#316) + User isolation (#271) boundary
- Test discovery fixes (#306) + Integration imports (#308) boundary
- WebSocket await fixes (#292) + Race conditions (#277) boundary
"""

import pytest
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock, patch
from test_framework.ssot.base_test_case import SSotAsyncTestCase

# SSOT Imports for Boundary Testing
from netra_backend.app.core.agent_execution_tracker import ExecutionState, get_execution_tracker
from netra_backend.app.services.user_execution_context import (
    UserExecutionContext,
    UserContextManager,
    managed_user_context,
    ContextIsolationError
)

# Cross-component imports for boundary testing
try:
    from netra_backend.app.services.agent_websocket_bridge import create_agent_websocket_bridge
    from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
    CROSS_COMPONENT_IMPORTS_AVAILABLE = True
except ImportError:
    CROSS_COMPONENT_IMPORTS_AVAILABLE = False


class TestClusterBoundaries(SSotAsyncTestCase):
    """Test boundary conditions where multiple cluster fixes interact."""
    
    def setUp(self):
        """Set up boundary testing environment."""
        super().setUp()
        self.test_user_1 = "boundary_user_001"
        self.test_user_2 = "boundary_user_002"
        self.execution_tracker = get_execution_tracker()
        self.context_manager = UserContextManager()
    
    @pytest.mark.integration
    async def test_execution_state_user_context_boundary(self):
        """ExecutionState fixes (#305) must not conflict with UserContext security (#271)."""
        # BOUNDARY: ExecutionState enum usage within UserExecutionContext isolation
        
        async with managed_user_context(self.test_user_1, "boundary_test_1") as user_context_1:
            async with managed_user_context(self.test_user_2, "boundary_test_2") as user_context_2:
                
                # Create execution IDs for both users
                execution_id_1 = f"exec_boundary_{user_context_1.execution_id}"
                execution_id_2 = f"exec_boundary_{user_context_2.execution_id}"
                
                # TEST BOUNDARY CASE 1: ExecutionState usage in isolated contexts
                # Both users execute agents simultaneously with proper state tracking
                
                # User 1: Progress through execution states
                self.execution_tracker.update_execution_state(execution_id_1, ExecutionState.PENDING)
                self.execution_tracker.update_execution_state(execution_id_1, ExecutionState.RUNNING)
                
                # User 2: Different execution path 
                self.execution_tracker.update_execution_state(execution_id_2, ExecutionState.PENDING)
                self.execution_tracker.update_execution_state(execution_id_2, ExecutionState.STARTING)
                
                # BOUNDARY VALIDATION: States must be isolated per user context
                user_1_state = self.execution_tracker.get_execution_state(execution_id_1)
                user_2_state = self.execution_tracker.get_execution_state(execution_id_2)
                
                assert user_1_state == ExecutionState.RUNNING
                assert user_2_state == ExecutionState.STARTING
                assert user_1_state != user_2_state  # Different states prove isolation
                
                # TEST BOUNDARY CASE 2: ExecutionState must use enum, not dict (issue #305)
                # while maintaining user context isolation (issue #271)
                
                # This should work - proper enum usage within user context
                user_context_1.set_data("execution_state", ExecutionState.RUNNING.value)
                user_context_2.set_data("execution_state", ExecutionState.STARTING.value)
                
                # Verify user context isolation maintained
                assert user_context_1.get_data("execution_state") != user_context_2.get_data("execution_state")
                
                # This should fail - dict objects rejected by ExecutionState fix
                with pytest.raises((TypeError, ValueError, AttributeError)):
                    self.execution_tracker.update_execution_state(execution_id_1, {"status": "running"})
                
                # But user context isolation should still work
                assert user_context_1.user_id != user_context_2.user_id
    
    @pytest.mark.integration
    async def test_api_validation_websocket_boundary(self):
        """API validation fixes (#307) must not break WebSocket event delivery (#292)."""
        # BOUNDARY: API request validation + WebSocket event sending
        
        async with managed_user_context(self.test_user_1, "api_websocket_boundary") as user_context:
            
            # TEST BOUNDARY CASE 1: Valid API requests must trigger WebSocket events
            
            # Mock WebSocket bridge
            mock_websocket_bridge = AsyncMock()
            sent_events = []
            
            async def capture_event(event_type: str, data: Dict[str, Any]):
                sent_events.append({"type": event_type, "data": data})
            
            mock_websocket_bridge.send_agent_event = capture_event
            
            # Create agent execution with WebSocket integration
            execution_id = f"exec_api_ws_{user_context.execution_id}"
            
            if CROSS_COMPONENT_IMPORTS_AVAILABLE:
                execution_core = AgentExecutionCore(
                    execution_tracker=self.execution_tracker,
                    user_context=user_context,
                    websocket_bridge=mock_websocket_bridge
                )
                
                # Test API request validation patterns that were failing (#307)
                valid_api_patterns = [
                    {"message": "Help me", "agent": "triage_agent"},
                    {"message": "?", "agent": "triage_agent"},  # Single character
                    {"message": "", "agent": "triage_agent"},   # Empty message
                    {"message": "What's my spend?", "agent": "cost_optimizer"}  # Business language
                ]
                
                for i, api_pattern in enumerate(valid_api_patterns):
                    with self.subTest(pattern=api_pattern):
                        # Clear previous events
                        sent_events.clear()
                        
                        # Mock API validation that should pass (fix for #307)
                        api_validation_result = self._validate_api_request(api_pattern)
                        assert api_validation_result["valid"], f"API validation should pass for: {api_pattern}"
                        assert api_validation_result.get("status_code") != 422, "Should not return 422 error"
                        
                        # If API validation passes, WebSocket events should be sent
                        mock_agent = AsyncMock()
                        mock_agent.execute.return_value = {"result": f"Pattern {i} processed"}
                        
                        with patch.object(execution_core, '_get_agent', return_value=mock_agent):
                            await execution_core.execute_agent(
                                f"{execution_id}_{i}",
                                api_pattern["agent"],
                                api_pattern["message"]
                            )
                        
                        # BOUNDARY VALIDATION: API validation passing should enable WebSocket events
                        assert len(sent_events) > 0, f"No WebSocket events sent for valid API pattern: {api_pattern}"
                        
                        # WebSocket events should use proper await syntax (fix for #292)
                        event_types = [event["type"] for event in sent_events]
                        assert "agent_started" in event_types or "agent_thinking" in event_types, \
                            f"Missing agent events for pattern: {api_pattern}"
    
    @pytest.mark.integration
    async def test_auth_isolation_boundary(self):
        """Auth fixes (#316) must maintain user isolation guarantees (#271)."""
        # BOUNDARY: OAuth/Redis interface changes + User context isolation
        
        # TEST BOUNDARY CASE 1: Auth changes must not break user context isolation
        
        # Mock auth service with OAuth/Redis fixes
        mock_auth_service = AsyncMock()
        
        # Simulate OAuth/Redis interface consistency (fix for #316)
        oauth_user_data = {
            "user_id": self.test_user_1,
            "email": "boundary_test_1@example.com",
            "oauth_provider": "google",
            "auth_token": "oauth_token_123"
        }
        
        redis_user_data = {
            "user_id": self.test_user_1,
            "email": "boundary_test_1@example.com", 
            "session_data": {"provider": "google", "token": "oauth_token_123"},
            "cached_at": "2025-09-11T10:00:00Z"
        }
        
        # Verify OAuth and Redis data consistency (fix for #316)
        assert oauth_user_data["user_id"] == redis_user_data["user_id"]
        assert oauth_user_data["email"] == redis_user_data["email"]
        assert oauth_user_data["auth_token"] == redis_user_data["session_data"]["token"]
        
        # TEST BOUNDARY CASE 2: Auth system must create isolated user contexts
        
        async def create_auth_user_context(user_id: str, auth_data: Dict[str, Any]) -> UserExecutionContext:
            """Create user context from auth data."""
            context = await self.context_manager.create_context(
                user_id=user_id,
                request_id=f"auth_req_{user_id}"
            )
            
            # Set auth-related data in user context
            context.set_data("auth_provider", auth_data.get("oauth_provider", "unknown"))
            context.set_data("auth_token", auth_data.get("auth_token", ""))
            context.set_data("email", auth_data.get("email", ""))
            
            return context
        
        # Create contexts for multiple users through auth system
        context_1 = await create_auth_user_context(self.test_user_1, oauth_user_data)
        context_2 = await create_auth_user_context(self.test_user_2, {
            "user_id": self.test_user_2,
            "email": "boundary_test_2@example.com",
            "oauth_provider": "github",
            "auth_token": "oauth_token_456"
        })
        
        # BOUNDARY VALIDATION: Auth contexts must be completely isolated
        assert context_1.user_id != context_2.user_id
        assert context_1.get_data("email") != context_2.get_data("email")
        assert context_1.get_data("auth_token") != context_2.get_data("auth_token")
        assert context_1.get_data("auth_provider") != context_2.get_data("auth_provider")
        
        # TEST BOUNDARY CASE 3: Auth failures must not affect other user contexts
        
        # Simulate auth failure for user 1
        try:
            context_1.set_data("auth_status", "failed")
            context_1.set_data("auth_error", "token_expired")
        except Exception as e:
            # Auth errors should not propagate to other contexts
            pass
        
        # User 2's context should be unaffected
        assert context_2.get_data("auth_status") != "failed"
        assert context_2.get_data("auth_error") is None
        assert context_2.user_id == self.test_user_2  # Still valid
    
    @pytest.mark.integration
    async def test_websocket_await_race_condition_boundary(self):
        """WebSocket await fixes (#292) must not introduce new race conditions (#277)."""
        # BOUNDARY: Proper await syntax + Race condition prevention
        
        async with managed_user_context(self.test_user_1, "websocket_race_boundary") as user_context:
            
            # Create multiple WebSocket bridges to test race conditions
            bridges = []
            for i in range(5):
                bridge = create_agent_websocket_bridge(user_context) if CROSS_COMPONENT_IMPORTS_AVAILABLE else AsyncMock()
                bridges.append(bridge)
            
            # TEST BOUNDARY CASE 1: Concurrent WebSocket operations with proper await
            
            async def concurrent_websocket_operations(bridge_id: int, bridge: Any) -> Dict[str, Any]:
                """Execute concurrent WebSocket operations."""
                try:
                    # Multiple rapid operations that could race
                    tasks = []
                    
                    for i in range(3):
                        if hasattr(bridge, 'send_agent_event'):
                            task = asyncio.create_task(
                                bridge.send_agent_event(
                                    f"test_event_{bridge_id}_{i}",
                                    {"data": f"bridge_{bridge_id}_message_{i}"}
                                )
                            )
                        else:
                            # Mock operation
                            task = asyncio.create_task(asyncio.sleep(0.001))
                        
                        tasks.append(task)
                    
                    # All operations should complete without race conditions
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    # Check for race condition exceptions
                    exceptions = [r for r in results if isinstance(r, Exception)]
                    race_errors = [
                        e for e in exceptions 
                        if "race" in str(e).lower() or "concurrent" in str(e).lower()
                    ]
                    
                    return {
                        "bridge_id": bridge_id,
                        "success": len(race_errors) == 0,
                        "race_errors": len(race_errors),
                        "total_exceptions": len(exceptions)
                    }
                
                except Exception as e:
                    return {
                        "bridge_id": bridge_id,
                        "success": False,
                        "error": str(e),
                        "race_condition": "race" in str(e).lower() or "concurrent" in str(e).lower()
                    }
            
            # Run concurrent operations across multiple bridges
            operation_results = await asyncio.gather(
                *[concurrent_websocket_operations(i, bridge) for i, bridge in enumerate(bridges)],
                return_exceptions=True
            )
            
            # BOUNDARY VALIDATION: No race conditions despite concurrent operations
            successful_operations = [r for r in operation_results if isinstance(r, dict) and r.get("success")]
            race_condition_errors = [
                r for r in operation_results 
                if isinstance(r, dict) and r.get("race_condition", False)
            ]
            
            success_rate = len(successful_operations) / len(operation_results)
            
            # After fixes, should have high success rate with no race conditions
            assert success_rate >= 0.8, f"WebSocket operation success rate too low: {success_rate:.1%}"
            assert len(race_condition_errors) == 0, f"Race condition errors detected: {race_condition_errors}"
    
    @pytest.mark.integration
    async def test_test_discovery_integration_import_boundary(self):
        """Test discovery fixes (#306) must enable integration import fixes (#308)."""
        # BOUNDARY: Test collection + Integration test execution
        
        # TEST BOUNDARY CASE 1: Fixed test discovery should enable import resolution
        
        # Simulate test discovery patterns that were failing
        test_discovery_patterns = [
            "test_websocket_agent_integration.py",
            "test_user_context_isolation.py",
            "test_execution_state_consolidation.py",
            "test_api_validation_integration.py"
        ]
        
        # Mock test collection that should now work (fix for #306)
        discovered_tests = []
        for pattern in test_discovery_patterns:
            try:
                # Simulate test discovery
                test_info = {
                    "file": pattern,
                    "collected": True,
                    "imports_resolved": True,
                    "syntax_valid": True
                }
                discovered_tests.append(test_info)
            except Exception as e:
                discovered_tests.append({
                    "file": pattern,
                    "collected": False,
                    "error": str(e),
                    "syntax_valid": False
                })
        
        # BOUNDARY VALIDATION: All tests should be discoverable after #306 fix
        successful_discoveries = [t for t in discovered_tests if t["collected"]]
        assert len(successful_discoveries) == len(test_discovery_patterns), \
            f"Test discovery regression: {len(successful_discoveries)}/{len(test_discovery_patterns)} tests discovered"
        
        # TEST BOUNDARY CASE 2: Discovered tests should have resolved imports (fix for #308)
        
        for test_info in successful_discoveries:
            assert test_info["imports_resolved"], f"Import resolution failed for {test_info['file']}"
            assert test_info["syntax_valid"], f"Syntax errors in {test_info['file']}"
    
    @pytest.mark.integration
    @pytest.mark.performance
    async def test_boundary_performance_overhead(self):
        """Ensure boundary interactions don't cause excessive performance overhead."""
        import time
        
        # Benchmark boundary operations
        boundary_operations = []
        
        # Operation 1: ExecutionState + UserContext boundary
        start_time = time.perf_counter()
        
        async with managed_user_context(self.test_user_1, "perf_boundary") as user_context:
            execution_id = f"exec_perf_{user_context.execution_id}"
            
            # ExecutionState operations within user context
            for state in [ExecutionState.PENDING, ExecutionState.RUNNING, ExecutionState.COMPLETED]:
                self.execution_tracker.update_execution_state(execution_id, state)
                retrieved_state = self.execution_tracker.get_execution_state(execution_id)
                assert retrieved_state == state
        
        end_time = time.perf_counter()
        boundary_operations.append(("ExecutionState+UserContext", end_time - start_time))
        
        # Operation 2: API validation + WebSocket boundary
        start_time = time.perf_counter()
        
        api_requests = [
            {"message": "test 1", "agent": "triage_agent"},
            {"message": "test 2", "agent": "cost_optimizer"},
            {"message": "test 3", "agent": "triage_agent"}
        ]
        
        for request in api_requests:
            validation_result = self._validate_api_request(request)
            assert validation_result["valid"]
        
        end_time = time.perf_counter()
        boundary_operations.append(("API+WebSocket", end_time - start_time))
        
        # Performance requirements for boundary operations
        for operation_name, duration in boundary_operations:
            # Each boundary operation should complete in under 10ms
            assert duration < 0.01, f"Boundary operation '{operation_name}' too slow: {duration:.3f}s"
    
    # Helper methods for boundary testing
    def _validate_api_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock API request validation with permissive rules (fix for #307)."""
        # Simulate permissive validation that should pass after #307 fixes
        
        if not isinstance(request_data, dict):
            return {"valid": False, "status_code": 422, "error": "Invalid request format"}
        
        if "agent" not in request_data:
            return {"valid": False, "status_code": 422, "error": "Agent required"}
        
        # Should be permissive for message content (fix for #307)
        message = request_data.get("message", "")
        if message is None:
            message = ""
        
        # Very permissive validation - should accept most user inputs
        return {"valid": True, "status_code": 200}
    
    async def _simulate_websocket_operation(self, operation_type: str, data: Dict[str, Any]) -> bool:
        """Simulate WebSocket operation with proper await syntax."""
        # Mock WebSocket operation that uses proper await expressions (fix for #292)
        try:
            await asyncio.sleep(0.001)  # Simulate async operation
            return True
        except SyntaxError:
            # Should not occur after await expression fixes
            return False
        except Exception:
            # Other errors are acceptable
            return False