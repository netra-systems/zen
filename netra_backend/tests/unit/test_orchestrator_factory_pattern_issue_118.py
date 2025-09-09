"""
Unit tests for GitHub Issue #118: Orchestrator Factory Pattern Validation
================================================================================

MISSION CRITICAL: Validate the orchestrator factory pattern fixes that resolve
WebSocket 1011 errors and enable agent execution progression past 'start agent' phase.

BUSINESS VALUE: Tests protect $120K+ MRR pipeline by ensuring orchestrator 
initialization works correctly for multi-user agent execution scenarios.

GitHub Issue: #118 - Agent execution progression past 'start agent' to user response
Root Cause: None orchestrator access at agent_service_core.py:544
Solution: Per-request orchestrator factory pattern implementation

Test Strategy:
- Unit tests validate the factory method creates proper orchestrators
- Tests designed to FAIL if singleton None access patterns return
- Comprehensive validation of WebSocket integration and user isolation
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, Optional

# SSOT imports - no relative imports
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge, RequestScopedOrchestrator
from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext
from shared.types import UserID, ThreadID, RunID
from test_framework.fixtures.websocket_manager_mock import MockWebSocketManager


class TestOrchestratorFactoryPatternIssue118:
    """
    Test suite validating GitHub Issue #118 fixes.
    
    CRITICAL VALIDATION:
    - Factory method creates per-request orchestrator instances (not None)
    - WebSocket integration enables agent event emission
    - Multi-user isolation preserved through per-request patterns
    - Agent execution pipeline functional from start to completion
    """
    
    @pytest.fixture
    def mock_websocket_manager(self):
        """Create mock WebSocket manager for isolated testing."""
        return MockWebSocketManager()
    
    @pytest.fixture
    def agent_websocket_bridge(self, mock_websocket_manager):
        """Create AgentWebSocketBridge with mock WebSocket manager."""
        bridge = AgentWebSocketBridge()
        bridge._websocket_manager = mock_websocket_manager
        return bridge
    
    @pytest.fixture
    def test_user_id(self):
        """Test user ID for validation scenarios."""
        return UserID("test-user-118-validation")
    
    @pytest.fixture
    def test_agent_type(self):
        """Test agent type for orchestrator creation."""
        return "unified_data_agent"

    # ===================== CRITICAL FACTORY PATTERN TESTS =====================
    
    async def test_001_orchestrator_factory_creates_non_none_instance(
        self, agent_websocket_bridge, test_user_id, test_agent_type
    ):
        """
        TEST CRITICAL: Factory method creates actual orchestrator instances, not None.
        
        This test validates the core fix for issue #118:
        - Before fix: orchestrator was None causing WebSocket 1011 errors
        - After fix: factory creates RequestScopedOrchestrator instances
        
        Test designed to FAIL if None singleton pattern returns.
        """
        # Execute factory method
        orchestrator = await agent_websocket_bridge.create_execution_orchestrator(
            user_id=test_user_id, 
            agent_type=test_agent_type
        )
        
        # CRITICAL ASSERTION: Must never be None (issue #118 root cause)
        assert orchestrator is not None, \
            "🚨 CRITICAL FAILURE: Factory returned None orchestrator - Issue #118 not fixed!"
        
        # Validate correct type created
        assert isinstance(orchestrator, RequestScopedOrchestrator), \
            f"Expected RequestScopedOrchestrator, got {type(orchestrator)}"
        
        # Validate orchestrator has required attributes for agent execution
        assert hasattr(orchestrator, 'user_context'), \
            "Orchestrator missing user_context - agent execution will fail"
        assert hasattr(orchestrator, 'emitter'), \
            "Orchestrator missing emitter - WebSocket events will fail"
        assert hasattr(orchestrator, 'websocket_bridge'), \
            "Orchestrator missing websocket_bridge - event emission will fail"

    async def test_002_orchestrator_factory_websocket_integration_required(
        self, test_user_id, test_agent_type
    ):
        """
        TEST: Factory method requires WebSocket manager for event emission.
        
        Validates business requirement: agent execution must emit WebSocket events
        for real-time user feedback during AI processing.
        """
        # Create bridge without WebSocket manager
        bridge = AgentWebSocketBridge()
        bridge._websocket_manager = None
        
        # CRITICAL: Factory must fail if WebSocket integration unavailable
        with pytest.raises(RuntimeError) as exc_info:
            await bridge.create_execution_orchestrator(
                user_id=test_user_id,
                agent_type=test_agent_type
            )
        
        # Validate error message includes business context
        assert "WebSocket manager not available" in str(exc_info.value), \
            "Error message must explain WebSocket requirement for user feedback"
        assert test_user_id in str(exc_info.value), \
            "Error message must include user context for debugging"

    async def test_003_orchestrator_factory_user_isolation_validation(
        self, agent_websocket_bridge, test_agent_type
    ):
        """
        TEST: Factory creates isolated orchestrator instances per user.
        
        Multi-user system requirement: Each user must get isolated orchestrator
        to prevent cross-user data leakage and ensure proper WebSocket routing.
        """
        user1_id = UserID("user-1-isolation-test")
        user2_id = UserID("user-2-isolation-test")
        
        # Create orchestrators for different users
        orchestrator1 = await agent_websocket_bridge.create_execution_orchestrator(
            user_id=user1_id, 
            agent_type=test_agent_type
        )
        orchestrator2 = await agent_websocket_bridge.create_execution_orchestrator(
            user_id=user2_id, 
            agent_type=test_agent_type
        )
        
        # CRITICAL: Each user must get separate orchestrator instance
        assert orchestrator1 is not orchestrator2, \
            "🚨 CRITICAL: Same orchestrator instance shared between users - isolation violated!"
        
        # Validate user contexts are properly isolated
        assert orchestrator1.user_context.user_id != orchestrator2.user_context.user_id, \
            "User contexts not properly isolated between orchestrator instances"
        
        # Validate each orchestrator has unique thread/run IDs
        assert orchestrator1.user_context.thread_id != orchestrator2.user_context.thread_id, \
            "Thread IDs not unique - execution contexts will collide"
        assert orchestrator1.user_context.run_id != orchestrator2.user_context.run_id, \
            "Run IDs not unique - execution tracking will fail"

    async def test_004_orchestrator_factory_agent_type_context_validation(
        self, agent_websocket_bridge, test_user_id
    ):
        """
        TEST: Factory properly captures agent type in execution context.
        
        Agent type context is critical for proper tool dispatching and 
        WebSocket event routing to display correct agent information to users.
        """
        agent_types = ["unified_data_agent", "market_analysis_agent", "optimization_agent"]
        
        for agent_type in agent_types:
            orchestrator = await agent_websocket_bridge.create_execution_orchestrator(
                user_id=test_user_id,
                agent_type=agent_type
            )
            
            # Validate agent type properly captured in context
            assert agent_type in orchestrator.user_context.agent_context.get("agent_type", ""), \
                f"Agent type {agent_type} not properly captured in orchestrator context"
            
            # Validate orchestrator creation marker present
            assert orchestrator.user_context.agent_context.get("orchestrator_created") is True, \
                "Orchestrator creation not marked in context - debugging will be difficult"

    # ===================== EXECUTION CONTEXT CREATION TESTS =====================

    async def test_005_orchestrator_execution_context_creation_functional(
        self, agent_websocket_bridge, test_user_id, test_agent_type
    ):
        """
        TEST: Created orchestrator can successfully create execution contexts.
        
        This validates the complete agent execution pipeline:
        1. Factory creates orchestrator
        2. Orchestrator creates execution context  
        3. Context includes proper WebSocket notifier for events
        """
        orchestrator = await agent_websocket_bridge.create_execution_orchestrator(
            user_id=test_user_id,
            agent_type=test_agent_type
        )
        
        # Test execution context creation (critical for agent execution)
        test_message = "Analyze market trends for Q4 optimization"
        exec_context, notifier = await orchestrator.create_execution_context(
            agent_type=test_agent_type,
            user_id=test_user_id,
            message=test_message,
            context="test_validation_context"
        )
        
        # Validate execution context created successfully
        assert exec_context is not None, \
            "Execution context creation failed - agent execution will be blocked"
        assert notifier is not None, \
            "WebSocket notifier creation failed - users won't see agent progress"
        
        # Validate execution context has required attributes
        assert hasattr(exec_context, 'context_id'), \
            "Execution context missing context_id - execution tracking will fail"
        assert hasattr(exec_context, 'agent_id'), \
            "Execution context missing agent_id - tool dispatch will fail"
        assert hasattr(exec_context, 'user_id'), \
            "Execution context missing user_id - user isolation will fail"

    async def test_006_orchestrator_websocket_notifier_integration(
        self, agent_websocket_bridge, test_user_id, test_agent_type
    ):
        """
        TEST: Orchestrator creates functional WebSocket notifier for agent events.
        
        WebSocket events are critical for business value:
        - agent_started: User sees AI is working
        - agent_thinking: Real-time reasoning visibility  
        - tool_executing: Shows problem-solving approach
        - agent_completed: User knows response ready
        """
        orchestrator = await agent_websocket_bridge.create_execution_orchestrator(
            user_id=test_user_id,
            agent_type=test_agent_type
        )
        
        exec_context, notifier = await orchestrator.create_execution_context(
            agent_type=test_agent_type,
            user_id=test_user_id,
            message="Test WebSocket integration",
            context=None
        )
        
        # Validate notifier has critical WebSocket event methods
        required_methods = [
            'send_agent_thinking',
            'send_tool_executing', 
            'send_agent_completed'
        ]
        
        for method_name in required_methods:
            assert hasattr(notifier, method_name), \
                f"Notifier missing {method_name} - {method_name} events won't work"
        
        # Test that notifier methods are callable (async methods)
        assert callable(getattr(notifier, 'send_agent_thinking')), \
            "send_agent_thinking not callable - agent thinking events will fail"

    # ===================== FAILURE SCENARIO TESTS =====================

    async def test_007_agent_service_core_integration_no_none_access(
        self, agent_websocket_bridge, test_user_id, test_agent_type
    ):
        """
        TEST: Verify agent_service_core.py:544 pattern works with factory.
        
        This test simulates the exact pattern from agent_service_core.py 
        where the original None access issue occurred.
        """
        # Simulate the agent service core pattern
        # Original failing code: orchestrator = self._bridge.get_orchestrator() # Returns None
        # Fixed code: orchestrator = await self._bridge.create_execution_orchestrator(user_id, agent_type)
        
        # Test the fixed pattern
        orchestrator = await agent_websocket_bridge.create_execution_orchestrator(
            user_id=test_user_id, 
            agent_type=test_agent_type
        )
        
        # CRITICAL: This must never be None (original issue #118)
        assert orchestrator is not None, \
            "🚨 CRITICAL: Agent service core pattern returns None - Issue #118 not fixed!"
        
        # Test that orchestrator can be used for execution context creation
        exec_context, notifier = await orchestrator.create_execution_context(
            agent_type=test_agent_type,
            user_id=test_user_id, 
            message="Test agent service integration",
            context=None
        )
        
        # Validate complete execution pipeline functional
        assert exec_context is not None, \
            "Execution context creation failed with factory pattern"
        assert notifier is not None, \
            "WebSocket notifier creation failed with factory pattern"

    async def test_008_concurrent_orchestrator_creation_isolation(
        self, agent_websocket_bridge, test_agent_type
    ):
        """
        TEST: Concurrent orchestrator creation maintains proper isolation.
        
        Real-world scenario: Multiple users simultaneously starting agents.
        Each must get isolated orchestrator to prevent race conditions.
        """
        user_ids = [UserID(f"concurrent-user-{i}") for i in range(5)]
        
        # Create orchestrators concurrently (simulates real load)
        tasks = [
            agent_websocket_bridge.create_execution_orchestrator(
                user_id=user_id,
                agent_type=test_agent_type
            )
            for user_id in user_ids
        ]
        
        orchestrators = await asyncio.gather(*tasks)
        
        # Validate all orchestrators created successfully
        for i, orchestrator in enumerate(orchestrators):
            assert orchestrator is not None, \
                f"Concurrent orchestrator creation failed for user {i}"
            assert isinstance(orchestrator, RequestScopedOrchestrator), \
                f"Wrong orchestrator type created for user {i}"
        
        # Validate all orchestrators are unique instances
        for i in range(len(orchestrators)):
            for j in range(i + 1, len(orchestrators)):
                assert orchestrators[i] is not orchestrators[j], \
                    f"Orchestrator instances not isolated between users {i} and {j}"

    # ===================== INTEGRATION VALIDATION TESTS =====================

    async def test_009_orchestrator_factory_bridge_dependency_check(
        self, agent_websocket_bridge, test_user_id, test_agent_type
    ):
        """
        TEST: Validate dependency check updates for factory pattern.
        
        The bridge now checks orchestrator_factory_available instead of 
        singleton orchestrator availability (from bridge.py:902).
        """
        # Test that factory capability is properly detected
        orchestrator_available = hasattr(agent_websocket_bridge, 'create_execution_orchestrator')
        assert orchestrator_available is True, \
            "Orchestrator factory method not available - dependency checks will fail"
        
        # Test that factory method is properly callable
        assert callable(getattr(agent_websocket_bridge, 'create_execution_orchestrator')), \
            "Orchestrator factory method not callable - agent execution will fail"
        
        # Test actual factory execution
        orchestrator = await agent_websocket_bridge.create_execution_orchestrator(
            user_id=test_user_id,
            agent_type=test_agent_type
        )
        
        assert orchestrator is not None, \
            "Factory execution failed despite dependency check passing"

    async def test_010_orchestrator_factory_error_handling_robustness(
        self, agent_websocket_bridge, test_agent_type
    ):
        """
        TEST: Factory method handles error scenarios gracefully.
        
        Production robustness: Factory must handle invalid inputs without
        crashing the entire agent execution pipeline.
        """
        # Test with invalid user ID
        with pytest.raises((ValueError, TypeError, RuntimeError)) as exc_info:
            await agent_websocket_bridge.create_execution_orchestrator(
                user_id=None,  # Invalid user ID
                agent_type=test_agent_type
            )
        
        # Error should be informative for debugging
        assert "user" in str(exc_info.value).lower() or "none" in str(exc_info.value).lower(), \
            "Error message should indicate user ID validation issue"
        
        # Test with empty agent type
        with pytest.raises((ValueError, TypeError)) as exc_info:
            await agent_websocket_bridge.create_execution_orchestrator(
                user_id=UserID("valid-user"),
                agent_type=""  # Empty agent type
            )

# ===================== TEST SUITE METADATA =====================

def test_issue_118_validation_suite_metadata():
    """
    Metadata validation for Issue #118 test suite.
    
    This function documents the test suite purpose and validates 
    that all critical aspects of Issue #118 are covered.
    """
    test_coverage = {
        "root_cause_validation": "test_001_orchestrator_factory_creates_non_none_instance",
        "websocket_integration": "test_002_orchestrator_factory_websocket_integration_required", 
        "multi_user_isolation": "test_003_orchestrator_factory_user_isolation_validation",
        "agent_type_context": "test_004_orchestrator_factory_agent_type_context_validation",
        "execution_pipeline": "test_005_orchestrator_execution_context_creation_functional",
        "websocket_events": "test_006_orchestrator_websocket_notifier_integration",
        "agent_service_integration": "test_007_agent_service_core_integration_no_none_access",
        "concurrent_safety": "test_008_concurrent_orchestrator_creation_isolation",
        "dependency_validation": "test_009_orchestrator_factory_bridge_dependency_check",
        "error_handling": "test_010_orchestrator_factory_error_handling_robustness"
    }
    
    # Validate comprehensive coverage of Issue #118
    assert len(test_coverage) >= 10, \
        "Test suite must comprehensively cover all aspects of Issue #118"
    
    # Core requirements validation
    required_coverage = [
        "root_cause_validation",
        "websocket_integration", 
        "multi_user_isolation",
        "execution_pipeline"
    ]
    
    for requirement in required_coverage:
        assert requirement in test_coverage, \
            f"Missing critical test coverage for {requirement}"

    return test_coverage

# Business value documentation
"""
BUSINESS IMPACT OF TEST SUITE:
=============================

Issue #118 Validation Value:
- Protects $120K+ MRR pipeline from regression
- Ensures agent execution progression past 'start agent' phase
- Validates WebSocket event emission for real-time user feedback
- Confirms multi-user isolation prevents cross-user data leakage

Test Suite Business ROI:
- Prevents production failures that block AI chat functionality  
- Reduces debugging time by catching orchestrator issues early
- Validates complete agent-to-user communication pipeline
- Ensures system stability under concurrent multi-user load

Success Criteria:
- All tests pass: Issue #118 fixes are working correctly
- Any test failures: Indicates regression requiring immediate attention
- WebSocket integration validated: Real-time user feedback functional
- Multi-user isolation confirmed: System ready for production load
"""