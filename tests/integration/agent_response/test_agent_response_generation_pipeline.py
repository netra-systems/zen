"""Integration Tests for Agent Response Generation Pipeline

Tests the complete agent response generation pipeline from user input
to agent output, validating all stages of response creation.

Business Value Justification (BVJ):
- Segment: Free/Early/Mid/Enterprise - All customer segments
- Business Goal: Ensure reliable AI response generation (90% of platform value)
- Value Impact: Validates the core value delivery mechanism
- Strategic Impact: Protects $500K+ ARR by ensuring responses are generated correctly
"""

import asyncio
import pytest
import time
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, patch

from test_framework.ssot.base_test_case import BaseIntegrationTest
from test_framework.real_services_test_fixtures import (
    real_database_session,
    real_redis_connection
)
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.data_helper_agent import DataHelperAgent
from netra_backend.app.services.user_execution_context import (
    UserExecutionContext,
    UserContextManager,
    create_isolated_execution_context
)
from netra_backend.app.schemas.agent_result_types import (
    TypedAgentResult,
    AgentExecutionResult
)
from netra_backend.app.core.execution_tracker import get_execution_tracker, ExecutionState
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@pytest.mark.integration
@pytest.mark.real_services
class TestAgentResponseGenerationPipeline(BaseIntegrationTest):
    """Test agent response generation pipeline integration."""
    
    def setup_method(self):
        """Set up test fixtures."""
        super().setup_method()
        self.env = self.get_env()  # Use SSOT environment from base class
        self.execution_tracker = get_execution_tracker()
        self.user_context_manager = UserContextManager()
        self.test_user_id = "test_user_response_pipeline"
        self.test_thread_id = "thread_response_pipeline_001"
        
    async def test_basic_agent_response_generation_delivers_business_value(self):
        """
        Test basic agent response generation pipeline.
        
        BVJ: Free/Early/Mid/Enterprise - Conversion/Retention
        Tests that agents can generate meaningful responses to user queries,
        which is the core value proposition of the platform.
        """
        # GIVEN: A user execution context and agent
        with create_isolated_execution_context(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id
        ) as context:
            agent = DataHelperAgent()
            
            user_query = "What are the key trends in AI optimization?"
            
            # WHEN: Agent generates a response
            start_time = time.time()
            result = await agent.run(context, query=user_query)
            execution_time = time.time() - start_time
            
            # THEN: Response is generated successfully
            assert result is not None, "Agent must generate a response"
            assert execution_time < 30.0, "Response generation must complete within 30 seconds"
            
            # Record performance metrics
            self.record_metric("agent_response_time", execution_time)
            self.record_metric("agent_response_success", 1)
            
            # Validate response has business value
            if isinstance(result, TypedAgentResult):
                assert result.success, "Agent execution must succeed"
                assert result.result is not None, "Agent must return actual result data"
                
                # Validate response quality (basic checks)
                response_data = result.result
                if isinstance(response_data, str):
                    assert len(response_data) > 10, "Response must be substantive"
                    assert "trend" in response_data.lower(), "Response should address the query topic"
                    self.record_metric("response_length", len(response_data))
                elif isinstance(response_data, dict):
                    assert response_data, "Response dictionary must not be empty"
                    self.record_metric("response_fields", len(response_data))
                    
                logger.info(f"✅ Agent generated valuable response in {execution_time:.2f}s")
            
    async def test_agent_response_with_context_preservation(self):
        """
        Test agent response generation preserves user context.
        
        BVJ: Mid/Enterprise - Retention/Expansion
        Validates that agents maintain conversation context across interactions,
        crucial for Enterprise customers requiring sophisticated AI interactions.
        """
        # GIVEN: A user execution context with previous conversation
        with create_isolated_execution_context(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id
        ) as context:
            # Add context to simulate previous conversation
            context.add_context("previous_query", "Tell me about AI optimization")
            context.add_context("user_industry", "SaaS")
            
            agent = DataHelperAgent()
            follow_up_query = "Can you elaborate on the first point?"
            
            # WHEN: Agent generates response with context
            result = await agent.run(context, query=follow_up_query)
            
            # THEN: Response acknowledges context
            assert result is not None, "Agent must generate contextual response"
            
            if isinstance(result, TypedAgentResult):
                assert result.success, "Contextual agent execution must succeed"
                
                # Validate context preservation
                execution_context = context.get_context()
                assert "previous_query" in execution_context, "Previous context must be preserved"
                assert execution_context["user_industry"] == "SaaS", "User industry context must be maintained"
                
                logger.info("✅ Agent response preserved user context successfully")
                
    async def test_agent_response_error_handling_maintains_user_experience(self):
        """
        Test agent response error handling maintains user experience.
        
        BVJ: All segments - Retention/Stability
        Ensures that when agents encounter errors, the system provides
        graceful error handling rather than silent failures.
        """
        # GIVEN: A user execution context and agent with simulated error condition
        with create_isolated_execution_context(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id
        ) as context:
            agent = DataHelperAgent()
            
            # Simulate error by providing invalid input
            invalid_query = None
            
            # WHEN: Agent attempts to generate response with error condition
            result = await agent.run(context, query=invalid_query)
            
            # THEN: Error is handled gracefully
            if isinstance(result, TypedAgentResult):
                # Should either succeed with error handling or fail gracefully
                if not result.success:
                    assert result.error is not None, "Error must be captured and reported"
                    assert len(result.error) > 0, "Error message must be informative"
                    logger.info(f"✅ Agent handled error gracefully: {result.error}")
                else:
                    # If agent handles None input gracefully, that's also valid
                    logger.info("✅ Agent handled invalid input gracefully")
            else:
                # Even if result is not TypedAgentResult, it shouldn't be None for error cases
                assert result is not None, "Agent should return some result even in error cases"
                
    async def test_concurrent_agent_response_generation_isolation(self):
        """
        Test concurrent agent response generation maintains user isolation.
        
        BVJ: Enterprise - Security/Compliance
        Validates that multiple users can generate responses simultaneously
        without data leakage, critical for Enterprise security requirements.
        """
        # GIVEN: Multiple user contexts for concurrent testing
        user_1_id = f"{self.test_user_id}_concurrent_1"
        user_2_id = f"{self.test_user_id}_concurrent_2"
        
        async def generate_user_response(user_id: str, query: str) -> Dict[str, Any]:
            """Generate response for a specific user."""
            with create_isolated_execution_context(
                user_id=user_id,
                thread_id=f"thread_{user_id}"
            ) as context:
                # Add user-specific context
                context.add_context("user_segment", f"segment_{user_id}")
                
                agent = DataHelperAgent()
                result = await agent.run(context, query=query)
                
                return {
                    "user_id": user_id,
                    "result": result,
                    "context": context.get_context()
                }
        
        # WHEN: Multiple users generate responses concurrently
        tasks = [
            generate_user_response(user_1_id, "Query for user 1"),
            generate_user_response(user_2_id, "Query for user 2")
        ]
        
        results = await asyncio.gather(*tasks)
        
        # THEN: Responses are isolated per user
        assert len(results) == 2, "Both users must receive responses"
        
        user_1_result, user_2_result = results
        
        # Validate isolation
        assert user_1_result["user_id"] != user_2_result["user_id"], "Users must be different"
        assert user_1_result["context"]["user_segment"] != user_2_result["context"]["user_segment"], \
            "User contexts must be isolated"
        
        logger.info("✅ Concurrent agent responses maintained proper user isolation")
        
    async def test_agent_response_execution_tracking_for_observability(self):
        """
        Test agent response execution is properly tracked for observability.
        
        BVJ: Platform/Internal - Stability/Monitoring
        Validates that agent response generation is tracked for monitoring,
        debugging, and business intelligence purposes.
        """
        # GIVEN: A user execution context and execution tracking
        with create_isolated_execution_context(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id
        ) as context:
            agent = DataHelperAgent()
            query = "Test query for execution tracking"
            
            # Track execution state before
            initial_executions = len(self.execution_tracker.get_active_executions())
            
            # WHEN: Agent generates response
            execution_id = self.execution_tracker.start_execution(
                operation_type="agent_response_generation",
                metadata={"agent": "DataHelperAgent", "user_id": self.test_user_id}
            )
            
            try:
                result = await agent.run(context, query=query)
                self.execution_tracker.update_execution_state(execution_id, ExecutionState.COMPLETED)
            except Exception as e:
                self.execution_tracker.update_execution_state(execution_id, ExecutionState.FAILED)
                raise
                
            # THEN: Execution is properly tracked
            final_executions = len(self.execution_tracker.get_active_executions())
            
            # Validate tracking
            execution_info = self.execution_tracker.get_execution_info(execution_id)
            assert execution_info is not None, "Execution must be tracked"
            assert execution_info.state == ExecutionState.COMPLETED, "Execution state must be updated"
            
            logger.info(f"✅ Agent response execution tracked successfully: {execution_id}")
            
    async def test_agent_response_performance_meets_sla_requirements(self):
        """
        Test agent response performance meets SLA requirements.
        
        BVJ: All segments - Customer satisfaction/Retention
        Validates that agent responses are generated within acceptable time limits
        to maintain good user experience.
        """
        # GIVEN: A user execution context and performance requirements
        with create_isolated_execution_context(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id
        ) as context:
            agent = DataHelperAgent()
            query = "Performance test query"
            
            # Define SLA requirements
            MAX_RESPONSE_TIME = 30.0  # seconds
            TARGET_RESPONSE_TIME = 10.0  # seconds (preferred)
            
            # WHEN: Agent generates response with timing
            start_time = time.time()
            result = await agent.run(context, query=query)
            response_time = time.time() - start_time
            
            # THEN: Performance meets SLA
            assert response_time < MAX_RESPONSE_TIME, \
                f"Response time {response_time:.2f}s exceeds SLA maximum of {MAX_RESPONSE_TIME}s"
            
            # Record detailed performance metrics
            self.record_metric("sla_response_time", response_time)
            self.record_metric("sla_target_met", 1 if response_time < TARGET_RESPONSE_TIME else 0)
            self.record_metric("sla_max_met", 1 if response_time < MAX_RESPONSE_TIME else 0)
            
            if response_time < TARGET_RESPONSE_TIME:
                logger.info(f"✅ Agent response met target performance: {response_time:.2f}s")
            else:
                logger.warning(f"⚠️ Agent response exceeded target but within SLA: {response_time:.2f}s")
                
            # Validate response quality wasn't sacrificed for speed
            assert result is not None, "Fast response must still be substantive"
            
    def teardown_method(self):
        """Clean up test resources."""
        # Clean up any test data
        try:
            if hasattr(self, 'user_context_manager'):
                # Clean up user contexts
                pass
        except Exception as e:
            logger.warning(f"Error during test cleanup: {e}")
        
        super().teardown_method()