"""Integration Tests for Agent Response Personalization and Context Awareness

Tests the agent response personalization mechanisms and context-aware
response generation to ensure relevant and tailored user experiences.

Business Value Justification (BVJ):
- Segment: Early/Mid/Enterprise - Personalized experiences increase engagement
- Business Goal: Improve user satisfaction and retention through relevant responses
- Value Impact: Higher user engagement and reduced churn through personalization
- Strategic Impact: Enables premium pricing for personalized AI experiences
"""

import asyncio
import pytest
import time
from typing import Dict, Any, Optional, List
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
class TestAgentResponsePersonalizationContext(BaseIntegrationTest):
    """Test agent response personalization and context awareness."""
    
    def setup_method(self):
        """Set up test fixtures."""
        super().setup_method()
        
        # BVJ: Real database for user preference storage
        self.db_session = real_database_session()
        
        # BVJ: Real Redis for session context management
        self.redis_client = real_redis_connection()
        
        # Test user profiles for personalization testing
        self.user_profiles = {
            "beginner_user": {
                "experience_level": "beginner",
                "preferences": {
                    "explanation_style": "detailed",
                    "technical_depth": "basic",
                    "examples_preference": "practical"
                },
                "learning_goals": ["understanding_basics", "hands_on_practice"]
            },
            "expert_user": {
                "experience_level": "expert",
                "preferences": {
                    "explanation_style": "concise",
                    "technical_depth": "advanced",
                    "examples_preference": "complex_scenarios"
                },
                "learning_goals": ["optimization", "advanced_techniques"]
            },
            "enterprise_user": {
                "experience_level": "intermediate",
                "preferences": {
                    "explanation_style": "business_focused",
                    "technical_depth": "moderate",
                    "examples_preference": "real_world_cases"
                },
                "learning_goals": ["roi_optimization", "scalability"]
            }
        }

    async def test_experience_level_personalization(self):
        """
        Test response personalization based on user experience level.
        
        BVJ: All segments - Tailored complexity improves learning outcomes
        and user satisfaction across different skill levels.
        """
        logger.info("Testing experience level personalization")
        
        env = self.get_env()
        query = "Explain AI optimization strategies"
        
        # Test beginner user response
        beginner_user_id = "personalization_beginner_001"
        with create_isolated_execution_context(beginner_user_id) as beginner_context:
            beginner_context.context_data.update(self.user_profiles["beginner_user"])
            
            beginner_agent = DataHelperAgent()
            
            beginner_result = await beginner_agent.arun(
                input_data=query,
                user_context=beginner_context
            )
        
        # Test expert user response
        expert_user_id = "personalization_expert_001"
        with create_isolated_execution_context(expert_user_id) as expert_context:
            expert_context.context_data.update(self.user_profiles["expert_user"])
            
            expert_agent = DataHelperAgent()
            
            expert_result = await expert_agent.arun(
                input_data=query,
                user_context=expert_context
            )
        
        # Validate personalized responses
        beginner_response = str(beginner_result.result_data).lower()
        expert_response = str(expert_result.result_data).lower()
        
        # Beginner response should be more detailed and explanatory
        assert len(beginner_response) > len(expert_response) * 0.8, \
            "Beginner response should be more detailed"
        
        # Look for personalization indicators
        beginner_indicators = ["step by step", "for example", "let's start", "basic"]
        expert_indicators = ["advanced", "optimize", "efficient", "performance"]
        
        beginner_score = sum(1 for indicator in beginner_indicators if indicator in beginner_response)
        expert_score = sum(1 for indicator in expert_indicators if indicator in expert_response)
        
        assert beginner_score >= 1, \
            "Beginner response should contain beginner-friendly language"
        assert expert_score >= 1, \
            "Expert response should contain advanced terminology"

    async def test_context_aware_follow_up_responses(self):
        """
        Test context-aware responses that build on previous interactions.
        
        BVJ: Mid/Enterprise segment - Conversational continuity improves
        user experience and enables complex multi-turn assistance.
        """
        logger.info("Testing context-aware follow-up responses")
        
        env = self.get_env()
        user_id = "context_aware_user_001"
        
        with create_isolated_execution_context(user_id) as context:
            context.context_data.update(self.user_profiles["enterprise_user"])
            
            agent = DataHelperAgent()
            
            # Initial query
            initial_query = "What are the key performance metrics for AI optimization?"
            initial_result = await agent.arun(
                input_data=initial_query,
                user_context=context
            )
            
            # Store conversation history
            context.context_data["conversation_history"] = [
                {"query": initial_query, "response": initial_result.result_data}
            ]
            
            # Follow-up query that requires context
            followup_query = "How can I implement the third metric you mentioned?"
            followup_result = await agent.arun(
                input_data=followup_query,
                user_context=context
            )
            
            # Validate context awareness
            initial_response = str(initial_result.result_data).lower()
            followup_response = str(followup_result.result_data).lower()
            
            # Follow-up should reference previous context
            assert len(followup_response) > 100, \
                "Follow-up response should be substantial"
            
            # Should not ask for clarification if context is clear
            clarification_phrases = ["which metric", "could you specify", "more details about"]
            has_clarification = any(phrase in followup_response for phrase in clarification_phrases)
            
            # Should provide specific implementation details
            implementation_indicators = ["implement", "configure", "set up", "measure"]
            has_implementation = any(indicator in followup_response for indicator in implementation_indicators)
            
            assert has_implementation, \
                "Follow-up response should provide implementation guidance"

    async def test_user_preference_adaptation(self):
        """
        Test adaptation to user communication preferences.
        
        BVJ: All segments - Matching communication style preferences
        improves user satisfaction and engagement metrics.
        """
        logger.info("Testing user preference adaptation")
        
        env = self.get_env()
        query = "Analyze my optimization results"
        
        # Test business-focused preference
        business_user_id = "preference_business_001"
        with create_isolated_execution_context(business_user_id) as business_context:
            business_context.context_data.update(self.user_profiles["enterprise_user"])
            business_context.context_data["preferences"]["explanation_style"] = "business_focused"
            
            business_agent = DataHelperAgent()
            
            business_result = await business_agent.arun(
                input_data=query,
                user_context=business_context
            )
        
        # Test technical-focused preference
        technical_user_id = "preference_technical_001"
        with create_isolated_execution_context(technical_user_id) as technical_context:
            technical_context.context_data.update(self.user_profiles["expert_user"])
            technical_context.context_data["preferences"]["explanation_style"] = "technical_detailed"
            
            technical_agent = DataHelperAgent()
            
            technical_result = await technical_agent.arun(
                input_data=query,
                user_context=technical_context
            )
        
        # Validate preference adaptation
        business_response = str(business_result.result_data).lower()
        technical_response = str(technical_result.result_data).lower()
        
        # Business response indicators
        business_terms = ["roi", "cost", "efficiency", "revenue", "business impact"]
        business_score = sum(1 for term in business_terms if term in business_response)
        
        # Technical response indicators
        technical_terms = ["algorithm", "latency", "throughput", "optimization", "performance"]
        technical_score = sum(1 for term in technical_terms if term in technical_response)
        
        assert business_score >= 2, \
            "Business-focused response should contain business terminology"
        assert technical_score >= 2, \
            "Technical response should contain technical terminology"

    async def test_learning_goal_alignment(self):
        """
        Test response alignment with user learning goals.
        
        BVJ: Early/Mid segment - Goal-aligned responses improve learning
        outcomes and increase platform engagement.
        """
        logger.info("Testing learning goal alignment")
        
        env = self.get_env()
        query = "Help me improve my AI optimization approach"
        
        # User with ROI optimization goals
        roi_user_id = "learning_roi_user_001"
        with create_isolated_execution_context(roi_user_id) as roi_context:
            roi_context.context_data.update(self.user_profiles["enterprise_user"])
            roi_context.context_data["learning_goals"] = ["roi_optimization", "cost_reduction"]
            
            roi_agent = DataHelperAgent()
            
            roi_result = await roi_agent.arun(
                input_data=query,
                user_context=roi_context
            )
        
        # User with technical mastery goals
        mastery_user_id = "learning_mastery_user_001"
        with create_isolated_execution_context(mastery_user_id) as mastery_context:
            mastery_context.context_data.update(self.user_profiles["expert_user"])
            mastery_context.context_data["learning_goals"] = ["advanced_techniques", "cutting_edge_methods"]
            
            mastery_agent = DataHelperAgent()
            
            mastery_result = await mastery_agent.arun(
                input_data=query,
                user_context=mastery_context
            )
        
        # Validate goal alignment
        roi_response = str(roi_result.result_data).lower()
        mastery_response = str(mastery_result.result_data).lower()
        
        # ROI-focused response validation
        roi_keywords = ["return on investment", "cost savings", "efficiency gains", "budget"]
        roi_alignment = sum(1 for keyword in roi_keywords if keyword in roi_response)
        
        # Technical mastery response validation
        mastery_keywords = ["advanced algorithms", "state-of-the-art", "cutting edge", "research"]
        mastery_alignment = sum(1 for keyword in mastery_keywords if keyword in mastery_response)
        
        assert roi_alignment >= 1, \
            "ROI-focused response should address financial benefits"
        assert mastery_alignment >= 1, \
            "Technical mastery response should address advanced techniques"

    async def test_historical_interaction_learning(self):
        """
        Test learning from historical user interactions.
        
        BVJ: Mid/Enterprise segment - Improves response relevance over time
        and increases user satisfaction with personalized AI.
        """
        logger.info("Testing historical interaction learning")
        
        env = self.get_env()
        user_id = "historical_learning_user_001"
        
        with create_isolated_execution_context(user_id) as context:
            context.context_data.update(self.user_profiles["enterprise_user"])
            
            # Simulate historical interactions
            historical_queries = [
                "What are GPU optimization techniques?",
                "How to reduce inference latency?",
                "Best practices for model deployment?"
            ]
            
            historical_interactions = []
            
            agent = DataHelperAgent()
            
            # Build interaction history
            for i, query in enumerate(historical_queries):
                result = await agent.arun(
                    input_data=query,
                    user_context=context
                )
                
                historical_interactions.append({
                    "timestamp": time.time() - (len(historical_queries) - i) * 3600,  # Hours ago
                    "query": query,
                    "response": result.result_data,
                    "user_satisfaction": 0.8 + (i * 0.1)  # Increasing satisfaction
                })
            
            # Add historical context
            context.context_data["interaction_history"] = historical_interactions
            
            # Test if new responses incorporate learning
            current_query = "What optimization approach would work best for my use case?"
            
            learned_result = await agent.arun(
                input_data=current_query,
                user_context=context
            )
            
            learned_response = str(learned_result.result_data).lower()
            
            # Should reference or build on historical context
            gpu_mentioned = "gpu" in learned_response
            latency_mentioned = "latency" in learned_response or "performance" in learned_response
            deployment_mentioned = "deploy" in learned_response or "production" in learned_response
            
            # At least 2 out of 3 historical themes should be referenced
            historical_relevance = sum([gpu_mentioned, latency_mentioned, deployment_mentioned])
            
            assert historical_relevance >= 2, \
                "Response should incorporate learning from historical interactions"

    async def test_multi_modal_context_awareness(self):
        """
        Test context awareness across different interaction modalities.
        
        BVJ: Enterprise segment - Seamless experience across devices
        and interaction types improves user engagement.
        """
        logger.info("Testing multi-modal context awareness")
        
        env = self.get_env()
        user_id = "multimodal_user_001"
        
        with create_isolated_execution_context(user_id) as context:
            context.context_data.update(self.user_profiles["enterprise_user"])
            
            agent = DataHelperAgent()
            
            # Text-based interaction
            text_query = "Show me optimization metrics dashboard"
            text_context = context.copy()
            text_context.context_data["interaction_mode"] = "text"
            text_context.context_data["device_type"] = "desktop"
            
            text_result = await agent.arun(
                input_data=text_query,
                user_context=text_context
            )
            
            # Voice-based interaction simulation
            voice_query = "Give me a summary of those metrics"
            voice_context = context.copy()
            voice_context.context_data["interaction_mode"] = "voice"
            voice_context.context_data["device_type"] = "mobile"
            voice_context.context_data["previous_interaction"] = {
                "type": "text",
                "query": text_query,
                "response": text_result.result_data
            }
            
            voice_result = await agent.arun(
                input_data=voice_query,
                user_context=voice_context
            )
            
            # Validate multi-modal awareness
            text_response = str(text_result.result_data).lower()
            voice_response = str(voice_result.result_data).lower()
            
            # Voice response should be more concise
            assert len(voice_response) <= len(text_response) * 1.2, \
                "Voice response should be more concise than text response"
            
            # Voice response should reference the previous text interaction
            reference_indicators = ["those metrics", "the dashboard", "as shown", "previously"]
            has_reference = any(indicator in voice_response for indicator in reference_indicators)
            
            assert has_reference, \
                "Voice response should reference previous text interaction"

    async def test_real_time_preference_updating(self):
        """
        Test real-time updating of user preferences during interaction.
        
        BVJ: All segments - Dynamic preference adaptation improves
        user experience and response relevance in real-time.
        """
        logger.info("Testing real-time preference updating")
        
        env = self.get_env()
        user_id = "realtime_preference_user_001"
        
        with create_isolated_execution_context(user_id) as context:
            context.context_data.update(self.user_profiles["beginner_user"])
            
            agent = DataHelperAgent()
            
            # Initial query with beginner preferences
            initial_query = "Explain machine learning optimization"
            initial_result = await agent.arun(
                input_data=initial_query,
                user_context=context
            )
            
            # User indicates preference for more technical depth
            context.context_data["preferences"]["technical_depth"] = "advanced"
            context.context_data["feedback"] = {
                "last_response": "too_basic",
                "preferred_style": "more_technical"
            }
            
            # Follow-up query should reflect updated preferences
            followup_query = "Tell me more about optimization algorithms"
            updated_result = await agent.arun(
                input_data=followup_query,
                user_context=context
            )
            
            # Validate preference adaptation
            initial_response = str(initial_result.result_data).lower()
            updated_response = str(updated_result.result_data).lower()
            
            # Updated response should be more technical
            technical_terms = ["algorithm", "gradient", "optimization", "convergence", "parameter"]
            
            initial_technical_score = sum(1 for term in technical_terms if term in initial_response)
            updated_technical_score = sum(1 for term in technical_terms if term in updated_response)
            
            assert updated_technical_score > initial_technical_score, \
                "Updated response should be more technical based on preference change"
            
            # Should also be longer/more detailed
            assert len(updated_response) > len(initial_response) * 0.8, \
                "Updated response should provide more technical depth"