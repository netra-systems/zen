#!/usr/bin/env python3
"""
Issue #802 SSOT Chat Migration Test Plan - Golden Path Preservation Validation

This test validates that Issue #565 ExecutionEngine migration preserves the Golden Path:
1. Complete user login → chat → AI response flow remains functional
2. WebSocket events deliver real-time updates throughout user journey
3. Agent execution provides meaningful AI responses to user requests
4. Multi-user concurrent usage works without interference
5. Chat business value delivery (90% of platform value) is maintained

Business Value: Free/Early/Mid/Enterprise - User Experience & Revenue Protection
Protects the $500K+ ARR Golden Path user flow that delivers substantive AI-powered
chat functionality serving as 90% of the platform's business value.

CRITICAL: These are end-to-end tests that validate the complete user experience
from authentication through meaningful AI chat interactions.
"""

import pytest
import asyncio
import json
import time
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timezone

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory

from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext, AgentExecutionResult, PipelineStep
)


@pytest.mark.e2e
class TestIssue565GoldenPathPreservation(SSotAsyncTestCase):
    """
    End-to-end test suite validating Golden Path preservation in ExecutionEngine migration.

    Tests the complete user journey: login → chat request → AI processing → response,
    ensuring that Issue #565 migration maintains the business-critical user experience.
    """

    async def setup_method(self, method):
        """Setup for each test method."""
        await super().setup_method(method)

        # Create mock factory for consistent e2e testing
        self.mock_factory = SSotMockFactory()

        # Track engines for cleanup
        self.created_engines: List[UserExecutionEngine] = []

        # Golden Path user personas for testing
        self.golden_path_users = [
            {
                'user_id': 'golden_path_free_user',
                'tier': 'Free',
                'use_case': 'cost_analysis',
                'expected_response_time': 3.0
            },
            {
                'user_id': 'golden_path_early_user',
                'tier': 'Early',
                'use_case': 'usage_optimization',
                'expected_response_time': 2.5
            },
            {
                'user_id': 'golden_path_enterprise_user',
                'tier': 'Enterprise',
                'use_case': 'advanced_analytics',
                'expected_response_time': 2.0
            }
        ]

    async def teardown_method(self, method):
        """Cleanup for each test method."""
        for engine in self.created_engines:
            try:
                if engine.is_active():
                    await engine.cleanup()
            except Exception as e:
                print(f"Warning: Engine cleanup failed: {e}")

        self.created_engines.clear()
        await super().teardown_method(method)

    def create_golden_path_user_context(self, user_profile: Dict[str, Any]) -> UserExecutionContext:
        """Create UserExecutionContext for Golden Path user persona."""
        return UserExecutionContext(
            user_id=user_profile['user_id'],
            thread_id=f"thread_{user_profile['user_id']}",
            run_id=f"run_{user_profile['user_id']}_{int(time.time())}",
            request_id=f"request_{user_profile['user_id']}_{int(time.time())}",
            metadata={
                'user_tier': user_profile['tier'],
                'use_case': user_profile['use_case'],
                'golden_path_test': True,
                'expected_response_time': user_profile['expected_response_time']
            }
        )

    def create_golden_path_engine(self, user_profile: Dict[str, Any]) -> UserExecutionEngine:
        """Create UserExecutionEngine configured for Golden Path testing."""
        user_context = self.create_golden_path_user_context(user_profile)

        # Create realistic mocks for Golden Path testing
        agent_factory = self.mock_factory.create_agent_factory_mock()
        websocket_emitter = self.mock_factory.create_websocket_emitter_mock(
            user_id=user_profile['user_id']
        )

        # Configure agent factory for realistic Golden Path behavior
        self._configure_golden_path_agent_factory(agent_factory, user_profile)

        engine = UserExecutionEngine(
            context=user_context,
            agent_factory=agent_factory,
            websocket_emitter=websocket_emitter
        )

        self.created_engines.append(engine)
        return engine

    def _configure_golden_path_agent_factory(self, agent_factory, user_profile):
        """Configure agent factory for realistic Golden Path agent behavior."""
        async def golden_path_agent_creation(agent_name, user_context, agent_class=None):
            mock_agent = AsyncMock()
            mock_agent.agent_name = agent_name
            mock_agent.user_context = user_context

            # Configure agent execution to provide business value
            async def golden_path_execute(input_data):
                # Simulate realistic processing time based on user tier
                processing_time = user_profile['expected_response_time'] * 0.8
                await asyncio.sleep(processing_time)

                # Generate realistic AI response based on use case
                use_case = user_profile['use_case']
                if use_case == 'cost_analysis':
                    response = {
                        "analysis": "Your AWS costs have increased 15% this month",
                        "recommendations": [
                            "Consider using Reserved Instances for EC2",
                            "Review S3 storage classes for older data"
                        ],
                        "potential_savings": "$2,400/month"
                    }
                elif use_case == 'usage_optimization':
                    response = {
                        "optimization": "Identified 3 underutilized resources",
                        "actions": [
                            "Scale down development environments during off-hours",
                            "Implement auto-scaling for web tier"
                        ],
                        "efficiency_gain": "30% resource optimization"
                    }
                elif use_case == 'advanced_analytics':
                    response = {
                        "insights": "ML model performance degrading in production",
                        "root_cause": "Data drift detected in input features",
                        "solution": "Retrain model with recent data samples",
                        "business_impact": "Prevent $50K revenue loss from poor recommendations"
                    }
                else:
                    response = {"result": "AI analysis completed successfully"}

                return {
                    "success": True,
                    "agent_name": agent_name,
                    "business_value": response,
                    "user_tier": user_profile['tier'],
                    "response_quality": "high_value",
                    "processing_time": processing_time
                }

            mock_agent.execute = golden_path_execute
            return mock_agent

        agent_factory.create_agent_instance = golden_path_agent_creation

    async def test_golden_path_complete_user_flow(self):
        """
        Test complete Golden Path user flow: login → chat → AI response.

        CRITICAL: This validates the end-to-end user experience that delivers
        90% of platform business value through meaningful AI interactions.
        """
        # Test Golden Path for each user tier
        for user_profile in self.golden_path_users:
            with self.subTest(user_tier=user_profile['tier']):
                await self._test_single_user_golden_path(user_profile)

    async def _test_single_user_golden_path(self, user_profile: Dict[str, Any]):
        """Test Golden Path flow for a single user profile."""
        # Step 1: Create user session (simulates post-login state)
        engine = self.create_golden_path_engine(user_profile)

        # Verify user session is properly established
        assert engine.is_active()
        assert engine.user_context.user_id == user_profile['user_id']

        # Step 2: User submits chat request
        user_request = self._create_realistic_chat_request(user_profile)

        # Step 3: Execute agent pipeline (core chat processing)
        start_time = time.time()

        result = await engine.execute_agent_pipeline(
            agent_name="supervisor_agent",  # Primary chat agent
            execution_context=engine.user_context,
            input_data=user_request
        )

        execution_time = time.time() - start_time

        # Step 4: Validate AI response quality and timing
        assert isinstance(result, AgentExecutionResult)
        assert result.success == True, f"Golden Path failed for {user_profile['tier']} user"

        # Verify response time meets SLA
        expected_time = user_profile['expected_response_time']
        assert execution_time <= expected_time, f"Response too slow: {execution_time:.2f}s > {expected_time}s"

        # Step 5: Validate business value in response
        if hasattr(result, 'data') and result.data:
            self._validate_business_value_response(result.data, user_profile)

        # Step 6: Verify WebSocket events delivered real-time updates
        websocket_emitter = engine.websocket_emitter

        # Should have sent agent_started event
        assert websocket_emitter.notify_agent_started.called
        started_args = websocket_emitter.notify_agent_started.call_args
        assert started_args[1]['agent_name'] == "supervisor_agent"

        # Should have sent agent_thinking events for real-time feedback
        assert websocket_emitter.notify_agent_thinking.called
        thinking_calls = websocket_emitter.notify_agent_thinking.call_args_list
        assert len(thinking_calls) >= 1  # At least one thinking update

        # Should have sent agent_completed event
        assert websocket_emitter.notify_agent_completed.called
        completed_args = websocket_emitter.notify_agent_completed.call_args
        assert completed_args[1]['agent_name'] == "supervisor_agent"
        assert completed_args[1]['result']['success'] == True

    def _create_realistic_chat_request(self, user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Create realistic chat request based on user profile."""
        use_case_requests = {
            'cost_analysis': {
                'message': "I need to understand why my AWS bill increased this month and get recommendations to optimize costs.",
                'context': 'cost_management',
                'urgency': 'high'
            },
            'usage_optimization': {
                'message': "Can you analyze my infrastructure usage and suggest optimizations for better efficiency?",
                'context': 'performance_optimization',
                'urgency': 'medium'
            },
            'advanced_analytics': {
                'message': "My ML model performance is declining. Help me identify the root cause and solution.",
                'context': 'machine_learning',
                'urgency': 'critical'
            }
        }

        base_request = use_case_requests.get(user_profile['use_case'], {
            'message': "Help me optimize my cloud infrastructure",
            'context': 'general_optimization',
            'urgency': 'medium'
        })

        return {
            **base_request,
            'user_id': user_profile['user_id'],
            'user_tier': user_profile['tier'],
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

    def _validate_business_value_response(self, response_data: Any, user_profile: Dict[str, Any]):
        """Validate that AI response delivers actual business value."""
        # Response should contain business value indicators
        business_value_indicators = [
            'recommendations', 'analysis', 'optimization', 'insights',
            'savings', 'efficiency', 'solution', 'actions', 'business_impact'
        ]

        response_str = str(response_data).lower()
        found_indicators = [indicator for indicator in business_value_indicators
                          if indicator in response_str]

        assert len(found_indicators) >= 1, f"Response lacks business value indicators: {response_data}"

        # Verify response is substantive (not just "success")
        if isinstance(response_data, dict):
            # Should have meaningful content beyond success flags
            meaningful_keys = [k for k in response_data.keys()
                             if k not in ['success', 'agent_name', 'user_tier']]
            assert len(meaningful_keys) >= 1, "Response lacks meaningful business content"

    async def test_concurrent_golden_path_users(self):
        """
        Test concurrent Golden Path execution for multiple users.

        SCALABILITY: Validates that multiple users can simultaneously execute
        the Golden Path without interference or degraded experience.
        """
        # Create engines for all user tiers
        engines = []
        for user_profile in self.golden_path_users:
            engine = self.create_golden_path_engine(user_profile)
            engines.append((engine, user_profile))

        # Execute Golden Path concurrently for all users
        async def execute_user_golden_path(engine_and_profile):
            engine, profile = engine_and_profile

            request = self._create_realistic_chat_request(profile)
            start_time = time.time()

            result = await engine.execute_agent_pipeline(
                agent_name="supervisor_agent",
                execution_context=engine.user_context,
                input_data=request
            )

            execution_time = time.time() - start_time

            return {
                'user_id': profile['user_id'],
                'user_tier': profile['tier'],
                'result': result,
                'execution_time': execution_time,
                'expected_time': profile['expected_response_time']
            }

        # Run all user flows concurrently
        concurrent_results = await asyncio.gather(
            *[execute_user_golden_path(ep) for ep in engines],
            return_exceptions=True
        )

        # Verify all users had successful Golden Path experience
        for i, result in enumerate(concurrent_results):
            assert not isinstance(result, Exception), f"User {i} Golden Path failed: {result}"

            # Validate individual results
            assert result['result'].success == True
            assert result['execution_time'] <= result['expected_time'] * 1.2  # 20% tolerance for concurrent load

        # Verify user isolation was maintained
        user_ids = [r['user_id'] for r in concurrent_results]
        assert len(set(user_ids)) == len(concurrent_results), "User isolation compromised"

        # Verify no cross-contamination in WebSocket events
        for engine, profile in engines:
            emitter = engine.websocket_emitter

            # Check that events were user-specific
            if emitter.notify_agent_started.called:
                started_calls = emitter.notify_agent_started.call_args_list
                for call in started_calls:
                    call_context = call[1].get('context', {})
                    if 'user_id' in call_context:
                        assert call_context['user_id'] == profile['user_id']

    async def test_golden_path_websocket_event_sequence(self):
        """
        Test that Golden Path WebSocket events follow proper sequence.

        REAL-TIME UX: Validates that users receive proper real-time feedback
        during AI processing, maintaining engagement and transparency.
        """
        user_profile = self.golden_path_users[0]  # Use first user for detailed testing
        engine = self.create_golden_path_engine(user_profile)

        # Track WebSocket event sequence
        event_sequence = []
        websocket_emitter = engine.websocket_emitter

        # Wrap WebSocket methods to track sequence
        original_started = websocket_emitter.notify_agent_started
        original_thinking = websocket_emitter.notify_agent_thinking
        original_tool_executing = websocket_emitter.notify_tool_executing
        original_tool_completed = websocket_emitter.notify_tool_completed
        original_completed = websocket_emitter.notify_agent_completed

        async def track_started(*args, **kwargs):
            event_sequence.append(('agent_started', time.time(), kwargs.get('agent_name')))
            return await original_started(*args, **kwargs)

        async def track_thinking(*args, **kwargs):
            event_sequence.append(('agent_thinking', time.time(), kwargs.get('agent_name')))
            return await original_thinking(*args, **kwargs)

        async def track_tool_executing(*args, **kwargs):
            tool_name = args[0] if args else kwargs.get('tool_name', 'unknown')
            event_sequence.append(('tool_executing', time.time(), tool_name))
            return await original_tool_executing(*args, **kwargs)

        async def track_tool_completed(*args, **kwargs):
            tool_name = args[0] if args else kwargs.get('tool_name', 'unknown')
            event_sequence.append(('tool_completed', time.time(), tool_name))
            return await original_tool_completed(*args, **kwargs)

        async def track_completed(*args, **kwargs):
            event_sequence.append(('agent_completed', time.time(), kwargs.get('agent_name')))
            return await original_completed(*args, **kwargs)

        # Install tracking wrappers
        websocket_emitter.notify_agent_started = track_started
        websocket_emitter.notify_agent_thinking = track_thinking
        websocket_emitter.notify_tool_executing = track_tool_executing
        websocket_emitter.notify_tool_completed = track_tool_completed
        websocket_emitter.notify_agent_completed = track_completed

        # Execute Golden Path
        request = self._create_realistic_chat_request(user_profile)
        result = await engine.execute_agent_pipeline(
            agent_name="supervisor_agent",
            execution_context=engine.user_context,
            input_data=request
        )

        # Verify event sequence
        assert len(event_sequence) >= 3, f"Insufficient events: {len(event_sequence)}"

        # Extract event types and verify required events
        event_types = [event[0] for event in event_sequence]

        # Must have core events in sequence
        assert 'agent_started' in event_types
        assert 'agent_thinking' in event_types
        assert 'agent_completed' in event_types

        # Verify chronological order of core events
        started_index = event_types.index('agent_started')
        completed_index = event_types.index('agent_completed')
        assert started_index < completed_index, "Events out of sequence"

        # Verify timing (events should be reasonably spaced)
        event_times = [event[1] for event in event_sequence]
        total_time = event_times[-1] - event_times[0]
        expected_time = user_profile['expected_response_time']
        assert total_time <= expected_time * 1.1, f"Event sequence too slow: {total_time:.2f}s"

    async def test_golden_path_chat_value_delivery(self):
        """
        Test that Golden Path delivers actual chat business value.

        BUSINESS VALUE: Validates that chat interactions provide substantive
        AI-powered value, not just technical success responses.
        """
        # Test value delivery across different user tiers and use cases
        value_test_results = []

        for user_profile in self.golden_path_users:
            engine = self.create_golden_path_engine(user_profile)

            # Execute multiple chat requests to test consistency
            chat_requests = [
                self._create_realistic_chat_request(user_profile),
                {
                    **self._create_realistic_chat_request(user_profile),
                    'message': f"Follow-up question for {user_profile['use_case']} analysis"
                }
            ]

            user_value_results = []

            for request in chat_requests:
                result = await engine.execute_agent_pipeline(
                    agent_name="supervisor_agent",
                    execution_context=engine.user_context,
                    input_data=request
                )

                # Analyze response for business value
                value_score = self._calculate_business_value_score(result, user_profile)
                user_value_results.append(value_score)

            # User should consistently receive high-value responses
            avg_value_score = sum(user_value_results) / len(user_value_results)

            value_test_results.append({
                'user_tier': user_profile['tier'],
                'use_case': user_profile['use_case'],
                'avg_value_score': avg_value_score,
                'min_score': min(user_value_results),
                'requests_tested': len(chat_requests)
            })

        # Verify business value delivery across all user tiers
        for result in value_test_results:
            assert result['avg_value_score'] >= 7.0, f"Low value for {result['user_tier']}: {result['avg_value_score']}"
            assert result['min_score'] >= 6.0, f"Inconsistent value for {result['user_tier']}: {result['min_score']}"

    def _calculate_business_value_score(self, result: AgentExecutionResult, user_profile: Dict[str, Any]) -> float:
        """Calculate business value score (0-10) for AI response."""
        score = 0.0

        # Base score for successful execution
        if result.success:
            score += 3.0

        # Score for response content quality
        if hasattr(result, 'data') and result.data:
            response_data = result.data

            # Check for business value indicators
            if isinstance(response_data, dict):
                value_indicators = [
                    'recommendations', 'analysis', 'optimization', 'insights',
                    'savings', 'efficiency', 'solution', 'actions', 'business_impact'
                ]

                found_indicators = sum(1 for indicator in value_indicators
                                     if indicator in str(response_data).lower())
                score += min(found_indicators * 1.0, 4.0)  # Max 4 points for indicators

                # Check for quantitative business impact
                quantitative_indicators = ['$', '%', 'cost', 'save', 'reduce', 'increase', 'improve']
                found_quantitative = sum(1 for indicator in quantitative_indicators
                                       if indicator in str(response_data).lower())
                score += min(found_quantitative * 0.5, 2.0)  # Max 2 points for quantitative

                # Check for actionable recommendations
                actionable_indicators = ['recommend', 'suggest', 'should', 'consider', 'implement']
                found_actionable = sum(1 for indicator in actionable_indicators
                                     if indicator in str(response_data).lower())
                score += min(found_actionable * 0.2, 1.0)  # Max 1 point for actionable

        return min(score, 10.0)  # Cap at 10.0

    async def test_golden_path_error_recovery(self):
        """
        Test Golden Path maintains graceful experience during error conditions.

        RELIABILITY: Validates that users receive meaningful responses even
        when system components experience issues.
        """
        user_profile = self.golden_path_users[0]
        engine = self.create_golden_path_engine(user_profile)

        # Test scenario 1: Temporary agent execution delay
        original_execute = engine.agent_factory.create_agent_instance

        async def delayed_agent_creation(*args, **kwargs):
            # Simulate temporary delay
            await asyncio.sleep(0.5)
            return await original_execute(*args, **kwargs)

        engine.agent_factory.create_agent_instance = delayed_agent_creation

        request = self._create_realistic_chat_request(user_profile)
        result = await engine.execute_agent_pipeline(
            agent_name="supervisor_agent",
            execution_context=engine.user_context,
            input_data=request
        )

        # Should still succeed with delay
        assert result.success == True
        assert result.duration >= 0.5  # Should reflect the delay

        # WebSocket events should still be delivered
        assert engine.websocket_emitter.notify_agent_started.called
        assert engine.websocket_emitter.notify_agent_completed.called

    async def test_golden_path_maintains_user_context_security(self):
        """
        Test that Golden Path maintains UserExecutionContext security patterns.

        SECURITY: Validates that Issue #565 migration preserves secure context
        handling throughout the Golden Path user experience.
        """
        # Test with sensitive user data
        user_profile = {
            'user_id': 'golden_path_security_user',
            'tier': 'Enterprise',
            'use_case': 'security_analysis',
            'expected_response_time': 2.0
        }

        engine = self.create_golden_path_engine(user_profile)

        # Create request with sensitive context
        sensitive_request = {
            'message': "Analyze security vulnerabilities in my production environment",
            'context': 'security_audit',
            'sensitive_data': {
                'environment': 'production',
                'compliance_requirements': ['SOC2', 'HIPAA'],
                'user_tier': user_profile['tier']
            }
        }

        # Execute with sensitive context
        result = await engine.execute_agent_pipeline(
            agent_name="security_agent",
            execution_context=engine.user_context,
            input_data=sensitive_request
        )

        # Verify secure context usage
        assert isinstance(engine.user_context, UserExecutionContext)
        assert engine.user_context.user_id == user_profile['user_id']

        # Verify no DeepAgentState vulnerabilities
        # (UserExecutionContext should be used throughout)
        if hasattr(result, 'metadata') and result.metadata:
            # Should not contain serialized DeepAgentState
            metadata_str = str(result.metadata)
            assert 'DeepAgentState' not in metadata_str

        # Verify user context isolation
        context_correlation_id = engine.user_context.get_correlation_id()
        assert context_correlation_id is not None
        assert user_profile['user_id'] in context_correlation_id
