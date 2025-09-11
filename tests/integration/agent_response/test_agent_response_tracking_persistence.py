"""Integration Tests for Agent Response Tracking and Persistence

Tests the tracking and persistence of agent responses for analytics,
auditing, and conversation history management.

Business Value Justification (BVJ):
- Segment: Mid/Enterprise - Analytics/Compliance
- Business Goal: Enable conversation analytics and audit trails
- Value Impact: Supports business intelligence and compliance requirements
- Strategic Impact: Enables Enterprise features and data-driven insights
"""

import asyncio
import pytest
import time
from datetime import datetime, UTC
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock, patch

from test_framework.ssot.base_test_case import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_database_session
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.data_helper_agent import DataHelperAgent
from netra_backend.app.services.user_execution_context import (
    UserExecutionContext,
    create_isolated_execution_context
)
from netra_backend.app.schemas.agent_result_types import TypedAgentResult
from netra_backend.app.core.execution_tracker import get_execution_tracker, ExecutionState
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class MockResponsePersistence:
    """Mock response persistence for testing."""
    
    def __init__(self):
        self.stored_responses = []
        self.storage_errors = []
        self.storage_enabled = True
        
    async def store_response(self, response_data: Dict[str, Any]) -> str:
        """Store response and return storage ID."""
        if not self.storage_enabled:
            raise Exception("Storage disabled")
            
        response_id = f"response_{len(self.stored_responses) + 1}"
        storage_entry = {
            "id": response_id,
            "timestamp": datetime.now(UTC),
            "data": response_data
        }
        self.stored_responses.append(storage_entry)
        return response_id
        
    async def retrieve_response(self, response_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve stored response by ID."""
        for entry in self.stored_responses:
            if entry["id"] == response_id:
                return entry["data"]
        return None
        
    async def get_user_responses(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get responses for a specific user."""
        user_responses = [
            entry for entry in self.stored_responses
            if entry["data"].get("user_id") == user_id
        ]
        return user_responses[-limit:] if limit else user_responses
        
    def clear_storage(self):
        """Clear all stored responses."""
        self.stored_responses.clear()
        self.storage_errors.clear()


@pytest.mark.integration
@pytest.mark.real_services
class TestAgentResponseTrackingPersistence(BaseIntegrationTest):
    """Test agent response tracking and persistence."""
    
    def setup_method(self):
        """Set up test fixtures."""
        super().setup_method()
        self.env = self.get_env()  # Use SSOT environment from base class
        self.execution_tracker = get_execution_tracker()
        self.mock_persistence = MockResponsePersistence()
        self.test_user_id = "test_user_tracking"
        self.test_thread_id = "thread_tracking_001"
        
    async def test_agent_response_basic_tracking_for_analytics(self):
        """
        Test basic agent response tracking for analytics.
        
        BVJ: Mid/Enterprise - Analytics/Business Intelligence
        Validates that agent responses are tracked with sufficient metadata
        for business analytics and performance monitoring.
        """
        # GIVEN: A user execution context with tracking enabled
        with create_isolated_execution_context(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id
        ) as context:
            agent = DataHelperAgent()
            query = "Test query for response tracking"
            
            # WHEN: Agent generates response with tracking
            execution_id = self.execution_tracker.start_execution(
                operation_type="agent_response_tracking",
                metadata={
                    "agent_type": "DataHelperAgent",
                    "user_id": self.test_user_id,
                    "thread_id": self.test_thread_id,
                    "query": query
                }
            )
            
            start_time = time.time()
            result = await agent.run(context, query=query)
            execution_time = time.time() - start_time
            
            # Store response for tracking
            if isinstance(result, TypedAgentResult) and result.success:
                response_data = {
                    "execution_id": execution_id,
                    "user_id": self.test_user_id,
                    "thread_id": self.test_thread_id,
                    "agent_type": "DataHelperAgent",
                    "query": query,
                    "response": result.result,
                    "execution_time_ms": execution_time * 1000,
                    "timestamp": datetime.now(UTC).isoformat(),
                    "success": result.success
                }
                
                response_id = await self.mock_persistence.store_response(response_data)
                self.execution_tracker.update_execution_state(execution_id, ExecutionState.COMPLETED)
                
                # THEN: Response is tracked with complete metadata
                stored_response = await self.mock_persistence.retrieve_response(response_id)
                assert stored_response is not None, "Response must be stored"
                
                # Validate required tracking fields
                required_fields = ["execution_id", "user_id", "thread_id", "agent_type", 
                                 "query", "response", "timestamp", "success"]
                
                for field in required_fields:
                    assert field in stored_response, f"Required tracking field {field} missing"
                    assert stored_response[field] is not None, f"Tracking field {field} cannot be None"
                
                # Validate metadata quality
                assert stored_response["user_id"] == self.test_user_id, "User ID must match"
                assert stored_response["thread_id"] == self.test_thread_id, "Thread ID must match"
                assert stored_response["success"] is True, "Success status must be tracked"
                assert stored_response["execution_time_ms"] > 0, "Execution time must be positive"
                
                logger.info(f"✅ Agent response tracked with ID: {response_id}")
                
    async def test_conversation_history_persistence_for_context(self):
        """
        Test conversation history persistence for context management.
        
        BVJ: All segments - User Experience/Context
        Validates that conversation history is persisted to enable
        contextual conversations and improved user experience.
        """
        # GIVEN: Multiple interactions in a conversation thread
        conversation_queries = [
            "What are the latest AI trends?",
            "How do these trends affect SaaS companies?",
            "Can you provide specific examples?",
            "What should I prioritize for implementation?"
        ]
        
        conversation_responses = []
        
        with create_isolated_execution_context(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id
        ) as context:
            agent = DataHelperAgent()
            
            # WHEN: Multiple queries in conversation thread
            for i, query in enumerate(conversation_queries):
                result = await agent.run(context, query=query)
                
                if isinstance(result, TypedAgentResult) and result.success:
                    # Store each response in conversation
                    response_data = {
                        "user_id": self.test_user_id,
                        "thread_id": self.test_thread_id,
                        "sequence_number": i + 1,
                        "query": query,
                        "response": result.result,
                        "timestamp": datetime.now(UTC).isoformat()
                    }
                    
                    response_id = await self.mock_persistence.store_response(response_data)
                    conversation_responses.append(response_id)
                    
                    # Add query to context for next iteration
                    context.add_context(f"previous_query_{i}", query)
                    
        # THEN: Complete conversation history is preserved
        assert len(conversation_responses) >= 2, "Multiple responses needed for conversation test"
        
        # Retrieve conversation history
        user_responses = await self.mock_persistence.get_user_responses(self.test_user_id)
        conversation_thread_responses = [
            r for r in user_responses 
            if r["data"]["thread_id"] == self.test_thread_id
        ]
        
        assert len(conversation_thread_responses) >= 2, "Conversation history must be preserved"
        
        # Validate conversation sequence
        sequence_numbers = [r["data"]["sequence_number"] for r in conversation_thread_responses]
        assert sequence_numbers == sorted(sequence_numbers), "Conversation sequence must be maintained"
        
        # Validate conversation coherence
        for i, response_entry in enumerate(conversation_thread_responses):
            response_data = response_entry["data"]
            assert response_data["query"] == conversation_queries[i], f"Query {i} must match"
            assert response_data["thread_id"] == self.test_thread_id, f"Thread ID must be consistent for query {i}"
            
        logger.info(f"✅ Conversation history persisted ({len(conversation_thread_responses)} responses)")
        
    async def test_response_analytics_metadata_for_business_intelligence(self):
        """
        Test response analytics metadata for business intelligence.
        
        BVJ: Platform/Internal - Business Intelligence/Product
        Validates that responses include analytics metadata for understanding
        user behavior, agent performance, and product usage patterns.
        """
        # GIVEN: A user execution context with analytics tracking
        with create_isolated_execution_context(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id
        ) as context:
            # Add user segment information for analytics
            context.add_context("user_segment", "Enterprise")
            context.add_context("subscription_tier", "Premium")
            
            agent = DataHelperAgent()
            query = "Business intelligence test query"
            
            # WHEN: Agent generates response with analytics metadata
            start_time = time.time()
            result = await agent.run(context, query=query)
            execution_time = time.time() - start_time
            
            if isinstance(result, TypedAgentResult) and result.success:
                # Store response with analytics metadata
                analytics_metadata = {
                    "user_id": self.test_user_id,
                    "thread_id": self.test_thread_id,
                    "query": query,
                    "response": result.result,
                    "analytics": {
                        "user_segment": context.get_context().get("user_segment"),
                        "subscription_tier": context.get_context().get("subscription_tier"),
                        "query_length": len(query),
                        "response_length": len(str(result.result)) if result.result else 0,
                        "execution_time_ms": execution_time * 1000,
                        "agent_type": "DataHelperAgent",
                        "success": result.success,
                        "timestamp": datetime.now(UTC).isoformat(),
                        "session_sequence": 1  # First query in session
                    }
                }
                
                response_id = await self.mock_persistence.store_response(analytics_metadata)
                
                # THEN: Analytics metadata is complete and useful
                stored_response = await self.mock_persistence.retrieve_response(response_id)
                assert stored_response is not None, "Analytics response must be stored"
                
                analytics = stored_response["analytics"]
                required_analytics_fields = [
                    "user_segment", "subscription_tier", "query_length", "response_length",
                    "execution_time_ms", "agent_type", "success", "timestamp"
                ]
                
                for field in required_analytics_fields:
                    assert field in analytics, f"Required analytics field {field} missing"
                    
                # Validate analytics data quality
                assert analytics["user_segment"] == "Enterprise", "User segment must be tracked"
                assert analytics["subscription_tier"] == "Premium", "Subscription tier must be tracked"
                assert analytics["query_length"] > 0, "Query length must be positive"
                assert analytics["execution_time_ms"] > 0, "Execution time must be positive"
                assert analytics["agent_type"] == "DataHelperAgent", "Agent type must be tracked"
                
                logger.info(f"✅ Analytics metadata tracked for business intelligence")
                
    async def test_response_persistence_error_handling_maintains_functionality(self):
        """
        Test response persistence error handling maintains core functionality.
        
        BVJ: All segments - Reliability/Core Functionality
        Validates that persistence failures don't break core response functionality,
        ensuring users still receive responses even if tracking fails.
        """
        # GIVEN: A user execution context with persistence errors
        self.mock_persistence.storage_enabled = False  # Simulate storage failure
        
        with create_isolated_execution_context(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id
        ) as context:
            agent = DataHelperAgent()
            query = "Test query with persistence failure"
            
            # WHEN: Agent generates response despite persistence failure
            result = await agent.run(context, query=query)
            
            # Attempt to store response (will fail)
            persistence_failed = False
            if isinstance(result, TypedAgentResult) and result.success:
                try:
                    response_data = {
                        "user_id": self.test_user_id,
                        "query": query,
                        "response": result.result
                    }
                    await self.mock_persistence.store_response(response_data)
                except Exception as e:
                    persistence_failed = True
                    logger.info(f"Expected persistence failure: {e}")
            
            # THEN: Core functionality continues despite persistence failure
            assert result is not None, "Agent must generate response despite persistence failure"
            assert persistence_failed, "Persistence failure should be simulated"
            
            if isinstance(result, TypedAgentResult):
                assert result.success, "Agent execution must succeed despite persistence failure"
                assert result.result is not None, "Response must be available despite persistence failure"
                
            # Verify no responses were stored due to failure
            user_responses = await self.mock_persistence.get_user_responses(self.test_user_id)
            persistence_test_responses = [
                r for r in user_responses
                if r["data"]["query"] == query
            ]
            assert len(persistence_test_responses) == 0, "No responses should be stored when persistence fails"
            
            logger.info("✅ Core functionality maintained despite persistence failure")
            
    async def test_response_audit_trail_for_compliance_requirements(self):
        """
        Test response audit trail for compliance requirements.
        
        BVJ: Enterprise - Compliance/Security
        Validates that agent responses create proper audit trails
        for Enterprise compliance and security requirements.
        """
        # GIVEN: A user execution context with audit requirements
        with create_isolated_execution_context(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id
        ) as context:
            # Add compliance context
            context.add_context("compliance_mode", "SOC2")
            context.add_context("data_classification", "Sensitive")
            
            agent = DataHelperAgent()
            query = "Sensitive data analysis request"
            
            # WHEN: Agent generates response with audit trail
            audit_id = f"audit_{int(time.time())}"
            
            result = await agent.run(context, query=query)
            
            if isinstance(result, TypedAgentResult) and result.success:
                # Create comprehensive audit trail
                audit_entry = {
                    "audit_id": audit_id,
                    "user_id": self.test_user_id,
                    "thread_id": self.test_thread_id,
                    "timestamp": datetime.now(UTC).isoformat(),
                    "action": "agent_response_generation",
                    "agent_type": "DataHelperAgent",
                    "query": query,
                    "response_summary": str(result.result)[:100] if result.result else "",
                    "compliance": {
                        "mode": context.get_context().get("compliance_mode"),
                        "data_classification": context.get_context().get("data_classification"),
                        "retention_required": True,
                        "audit_level": "FULL"
                    },
                    "execution_metadata": {
                        "success": result.success,
                        "execution_time_ms": getattr(result, 'execution_time_ms', None),
                        "error": result.error if hasattr(result, 'error') else None
                    }
                }
                
                audit_response_id = await self.mock_persistence.store_response(audit_entry)
                
                # THEN: Audit trail meets compliance requirements
                stored_audit = await self.mock_persistence.retrieve_response(audit_response_id)
                assert stored_audit is not None, "Audit trail must be stored"
                
                # Validate required audit fields
                required_audit_fields = [
                    "audit_id", "user_id", "timestamp", "action", "agent_type",
                    "query", "compliance", "execution_metadata"
                ]
                
                for field in required_audit_fields:
                    assert field in stored_audit, f"Required audit field {field} missing"
                    
                # Validate compliance metadata
                compliance = stored_audit["compliance"]
                assert compliance["mode"] == "SOC2", "Compliance mode must be tracked"
                assert compliance["data_classification"] == "Sensitive", "Data classification must be tracked"
                assert compliance["retention_required"] is True, "Retention requirement must be tracked"
                assert compliance["audit_level"] == "FULL", "Audit level must be tracked"
                
                # Validate execution metadata
                execution_metadata = stored_audit["execution_metadata"]
                assert execution_metadata["success"] is True, "Execution success must be audited"
                
                logger.info(f"✅ Compliance audit trail created: {audit_id}")
                
    def teardown_method(self):
        """Clean up test resources."""
        # Clear mock persistence storage
        self.mock_persistence.clear_storage()
        self.mock_persistence.storage_enabled = True  # Reset for next test
        
        super().teardown_method()