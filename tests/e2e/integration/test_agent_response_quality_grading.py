"""
Test Agent Response Quality Grading

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure agents deliver high-quality, actionable responses
- Value Impact: Users receive substantive AI solutions meeting quality standards
- Strategic Impact: Core platform value delivery - quality responses drive retention

This comprehensive E2E test validates that the real system generates responses
that pass a quality threshold of 0.7 across multiple dimensions:
- Relevance (0-1 score): Does the response address the user's question?
- Completeness (0-1 score): Is the response complete and thorough?
- Actionability (0-1 score): Does it provide actionable insights/steps?

CRITICAL: Uses REAL services, REAL agents, REAL LLM responses - NO MOCKS
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pytest
try:
    import websockets
    from websockets.exceptions import ConnectionClosed
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False

from test_framework.base_e2e_test import BaseE2ETest
from test_framework.websocket_helpers import WebSocketTestHelpers, assert_websocket_events
from test_framework.fixtures.real_services import real_services_fixture
from test_framework.agent_test_helpers import create_test_execution_context
from shared.isolated_environment import get_env


class AgentResponseQualityGrader:
    """
    Quality grading system for agent responses.
    Evaluates responses on relevance, completeness, and actionability.
    """
    
    def __init__(self):
        self.grading_criteria = {
            "relevance": {
                "weight": 0.4,
                "description": "How well the response addresses the user's question"
            },
            "completeness": {
                "weight": 0.3,
                "description": "How complete and thorough the response is"
            },
            "actionability": {
                "weight": 0.3,
                "description": "How actionable the insights/recommendations are"
            }
        }
    
    def grade_response(self, 
                      user_query: str, 
                      agent_response: str, 
                      agent_type: str = "general") -> Dict[str, float]:
        """
        Grade agent response across multiple quality dimensions.
        
        Args:
            user_query: The original user query
            agent_response: The agent's response
            agent_type: Type of agent that generated response
            
        Returns:
            Dict with scores for each dimension and overall quality
        """
        if not agent_response or not user_query:
            return {
                "relevance": 0.0,
                "completeness": 0.0,
                "actionability": 0.0,
                "overall_quality": 0.0,
                "grading_details": {"error": "Empty response or query"}
            }
        
        # Grade relevance
        relevance_score = self._grade_relevance(user_query, agent_response, agent_type)
        
        # Grade completeness
        completeness_score = self._grade_completeness(user_query, agent_response, agent_type)
        
        # Grade actionability
        actionability_score = self._grade_actionability(agent_response, agent_type)
        
        # Calculate overall quality score
        overall_quality = (
            relevance_score * self.grading_criteria["relevance"]["weight"] +
            completeness_score * self.grading_criteria["completeness"]["weight"] +
            actionability_score * self.grading_criteria["actionability"]["weight"]
        )
        
        return {
            "relevance": relevance_score,
            "completeness": completeness_score,
            "actionability": actionability_score,
            "overall_quality": overall_quality,
            "grading_details": {
                "query_length": len(user_query),
                "response_length": len(agent_response),
                "agent_type": agent_type,
                "graded_at": datetime.now(timezone.utc).isoformat()
            }
        }
    
    def _grade_relevance(self, query: str, response: str, agent_type: str) -> float:
        """Grade how well the response addresses the query."""
        score = 0.5  # Base score
        
        # Check for direct query keywords in response
        query_words = set(query.lower().split())
        response_words = set(response.lower().split())
        keyword_overlap = len(query_words.intersection(response_words))
        
        # Relevance based on keyword overlap
        if len(query_words) > 0:
            overlap_ratio = keyword_overlap / len(query_words)
            score += 0.3 * overlap_ratio
        
        # Check for agent-type specific relevance
        if agent_type == "optimization" or "cost" in query.lower():
            if any(term in response.lower() for term in 
                   ["optimize", "cost", "savings", "efficiency", "improve"]):
                score += 0.2
        elif agent_type == "triage" or "analyze" in query.lower():
            if any(term in response.lower() for term in 
                   ["analysis", "data", "metrics", "insights", "report"]):
                score += 0.2
        elif agent_type == "data" or "data" in query.lower():
            if any(term in response.lower() for term in 
                   ["data", "database", "query", "information", "results"]):
                score += 0.2
        
        # Bonus for addressing specific question types
        if "how" in query.lower() and any(term in response.lower() for term in 
                                         ["steps", "process", "method", "way"]):
            score += 0.1
        if "what" in query.lower() and any(term in response.lower() for term in 
                                         ["is", "are", "definition", "explanation"]):
            score += 0.1
        if "why" in query.lower() and any(term in response.lower() for term in 
                                         ["because", "reason", "due to", "causes"]):
            score += 0.1
        
        return min(1.0, score)
    
    def _grade_completeness(self, query: str, response: str, agent_type: str) -> float:
        """Grade how complete and thorough the response is."""
        score = 0.3  # Base score
        
        # Response length indicates thoroughness
        if len(response) > 200:
            score += 0.2
        if len(response) > 500:
            score += 0.2
        if len(response) > 1000:
            score += 0.1
        
        # Check for structured content
        if any(marker in response for marker in ["1.", "2.", "•", "-", "*"]):
            score += 0.1  # Has list/structured format
        
        if any(section in response.lower() for section in 
               ["summary", "conclusion", "recommendation", "next steps"]):
            score += 0.1  # Has concluding sections
        
        # Check for comprehensive coverage based on agent type
        if agent_type == "optimization":
            if any(term in response.lower() for term in 
                   ["current state", "recommendations", "benefits", "implementation"]):
                score += 0.1
        elif agent_type == "triage":
            if any(term in response.lower() for term in 
                   ["priority", "urgency", "impact", "classification"]):
                score += 0.1
        elif agent_type == "data":
            if any(term in response.lower() for term in 
                   ["sources", "methodology", "results", "interpretation"]):
                score += 0.1
        
        return min(1.0, score)
    
    def _grade_actionability(self, response: str, agent_type: str) -> float:
        """Grade how actionable the response is."""
        score = 0.2  # Base score
        
        # Check for action-oriented language
        action_words = [
            "should", "can", "could", "recommend", "suggest", "consider",
            "implement", "execute", "start", "begin", "create", "update",
            "configure", "setup", "install", "run", "check", "review"
        ]
        
        action_count = sum(1 for word in action_words if word in response.lower())
        score += min(0.3, action_count * 0.05)  # Up to 0.3 for action words
        
        # Check for specific actionable elements
        if any(term in response.lower() for term in 
               ["step 1", "first", "next", "then", "finally"]):
            score += 0.2  # Sequential steps
        
        if any(term in response.lower() for term in 
               ["example", "for instance", "such as", "like"]):
            score += 0.1  # Concrete examples
        
        if any(term in response.lower() for term in 
               ["tool", "command", "script", "code", "configuration"]):
            score += 0.1  # Specific tools/methods
        
        # Agent-type specific actionability
        if agent_type == "optimization":
            if any(term in response.lower() for term in 
                   ["reduce", "increase", "optimize", "improve", "save"]):
                score += 0.1
        elif agent_type == "triage":
            if any(term in response.lower() for term in 
                   ["investigate", "escalate", "assign", "prioritize"]):
                score += 0.1
        
        return min(1.0, score)


class TestAgentResponseQualityGrading(BaseE2ETest):
    """Comprehensive E2E tests for agent response quality grading."""
    
    def __init__(self):
        super().__init__()
        self.quality_grader = AgentResponseQualityGrader()
        self.websocket_connections = {}
        self.test_users = []
    
    async def setup_method(self):
        """Set up method called before each test method."""
        await super().setup_method() if hasattr(super(), 'setup_method') else None
        await self.initialize_test_environment()
    
    async def cleanup_resources(self):
        """Clean up test resources."""
        # Close all WebSocket connections
        for conn_id, ws in self.websocket_connections.items():
            try:
                if not ws.closed:
                    await ws.close()
            except:
                pass
        
        await super().cleanup_resources()
    
    async def create_test_user(self, user_id: str = None) -> Dict[str, str]:
        """Create a test user for quality grading tests."""
        if not user_id:
            user_id = f"quality_test_user_{uuid.uuid4().hex[:8]}"
        
        user_data = {
            "id": user_id,
            "email": f"{user_id}@example.com",
            "name": f"Quality Test User {user_id[-4:]}",
            "subscription_tier": "mid",
            "is_active": True
        }
        
        self.test_users.append(user_data)
        return user_data
    
    async def create_authenticated_websocket_connection(self, user_data: Dict) -> str:
        """Create authenticated WebSocket connection for testing."""
        ws_url = "ws://localhost:8000/ws"
        
        # Create test token (simplified for testing)
        test_token = f"test_token_{user_data['id']}"
        headers = {"Authorization": f"Bearer {test_token}"}
        
        try:
            # Try authenticated connection
            ws = await WebSocketTestHelpers.create_test_websocket_connection(
                ws_url, headers=headers, timeout=10.0, user_id=user_data['id']
            )
        except Exception:
            # Fallback to test endpoint
            test_url = "ws://localhost:8000/ws/test"
            ws = await WebSocketTestHelpers.create_test_websocket_connection(
                test_url, timeout=10.0, user_id=user_data['id']
            )
        
        conn_id = str(uuid.uuid4())
        self.websocket_connections[conn_id] = ws
        return conn_id
    
    async def send_agent_request_and_collect_response(self, 
                                                    conn_id: str, 
                                                    agent_type: str, 
                                                    user_query: str,
                                                    timeout: float = 30.0) -> Dict[str, Any]:
        """
        Send agent request via WebSocket and collect complete response with events.
        
        Returns:
            Dict containing response data and WebSocket events
        """
        ws = self.websocket_connections[conn_id]
        
        # Send agent request
        agent_request = {
            "type": "agent_request",
            "agent_type": agent_type,
            "message": user_query,
            "context": {
                "request_id": str(uuid.uuid4()),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }
        
        await WebSocketTestHelpers.send_test_message(ws, agent_request)
        
        # Collect events and final response
        events_received = []
        final_response = None
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                event = await WebSocketTestHelpers.receive_test_message(ws, timeout=2.0)
                events_received.append(event)
                
                # Check for completion
                if event.get("type") == "agent_completed":
                    final_response = event.get("data", {}).get("result", "")
                    break
                
            except Exception as e:
                if "timeout" in str(e).lower():
                    continue
                else:
                    break
        
        return {
            "events": events_received,
            "final_response": final_response,
            "event_types": [e.get("type") for e in events_received],
            "agent_type": agent_type,
            "user_query": user_query
        }
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_optimization_agent_response_quality(self, real_services_fixture):
        """Test optimization agent delivers high-quality responses."""
        if not WEBSOCKETS_AVAILABLE:
            pytest.skip("WebSocket library not available")
        # Create test user
        user_data = await self.create_test_user()
        
        # Create WebSocket connection
        conn_id = await self.create_authenticated_websocket_connection(user_data)
        
        # Test query focused on cost optimization
        test_query = "How can I optimize my AWS costs? I'm spending $5000/month and want to reduce by 30%."
        
        # Send request and collect response
        result = await self.send_agent_request_and_collect_response(
            conn_id, "optimization", test_query, timeout=45.0
        )
        
        # Verify WebSocket events were sent (mission critical)
        expected_events = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
        received_event_types = result["event_types"]
        
        # Must have at least agent_started and agent_completed
        assert "agent_started" in received_event_types, f"Missing agent_started event. Received: {received_event_types}"
        assert "agent_completed" in received_event_types, f"Missing agent_completed event. Received: {received_event_types}"
        
        # Verify response was generated
        assert result["final_response"], "No final response received from optimization agent"
        
        # Grade response quality
        quality_scores = self.quality_grader.grade_response(
            test_query, result["final_response"], "optimization"
        )
        
        # Assert quality threshold
        assert quality_scores["overall_quality"] >= 0.7, (
            f"Optimization agent response quality {quality_scores['overall_quality']:.3f} "
            f"below threshold 0.7. Scores: {quality_scores}"
        )
        
        # Verify individual dimensions
        assert quality_scores["relevance"] >= 0.5, f"Low relevance score: {quality_scores['relevance']}"
        assert quality_scores["completeness"] >= 0.4, f"Low completeness score: {quality_scores['completeness']}"
        assert quality_scores["actionability"] >= 0.5, f"Low actionability score: {quality_scores['actionability']}"
        
        self.logger.info(f"Optimization agent quality scores: {quality_scores}")
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_triage_agent_response_quality(self, real_services_fixture):
        """Test triage agent delivers high-quality responses."""
        user_data = await self.create_test_user()
        conn_id = await self.create_authenticated_websocket_connection(user_data)
        
        test_query = "I need to analyze my infrastructure performance. What should I prioritize first?"
        
        result = await self.send_agent_request_and_collect_response(
            conn_id, "triage", test_query, timeout=45.0
        )
        
        # Verify critical WebSocket events
        assert "agent_started" in result["event_types"], "Missing agent_started event"
        assert "agent_completed" in result["event_types"], "Missing agent_completed event"
        
        # Verify response exists
        assert result["final_response"], "No response from triage agent"
        
        # Grade quality
        quality_scores = self.quality_grader.grade_response(
            test_query, result["final_response"], "triage"
        )
        
        # Assert quality threshold
        assert quality_scores["overall_quality"] >= 0.7, (
            f"Triage agent quality {quality_scores['overall_quality']:.3f} below threshold"
        )
        
        self.logger.info(f"Triage agent quality scores: {quality_scores}")
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_data_agent_response_quality(self, real_services_fixture):
        """Test data agent delivers high-quality responses."""
        user_data = await self.create_test_user()
        conn_id = await self.create_authenticated_websocket_connection(user_data)
        
        test_query = "Can you help me understand my database performance metrics and identify bottlenecks?"
        
        result = await self.send_agent_request_and_collect_response(
            conn_id, "data", test_query, timeout=45.0
        )
        
        # Verify WebSocket events
        assert "agent_started" in result["event_types"], "Missing agent_started event"
        assert "agent_completed" in result["event_types"], "Missing agent_completed event"
        
        # Verify response
        assert result["final_response"], "No response from data agent"
        
        # Grade quality
        quality_scores = self.quality_grader.grade_response(
            test_query, result["final_response"], "data"
        )
        
        # Assert quality threshold
        assert quality_scores["overall_quality"] >= 0.7, (
            f"Data agent quality {quality_scores['overall_quality']:.3f} below threshold"
        )
        
        self.logger.info(f"Data agent quality scores: {quality_scores}")
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_multiple_agent_quality_comparison(self, real_services_fixture):
        """Test and compare quality across multiple agent types."""
        user_data = await self.create_test_user()
        conn_id = await self.create_authenticated_websocket_connection(user_data)
        
        # Test scenarios for different agents
        test_scenarios = [
            {
                "agent": "optimization",
                "query": "How can I reduce my cloud infrastructure costs by 25%?",
                "expected_min_quality": 0.7
            },
            {
                "agent": "triage", 
                "query": "What are the most critical issues in my system that need immediate attention?",
                "expected_min_quality": 0.7
            },
            {
                "agent": "data",
                "query": "Show me the performance trends for my application over the last month.",
                "expected_min_quality": 0.7
            }
        ]
        
        quality_results = []
        
        for scenario in test_scenarios:
            self.logger.info(f"Testing {scenario['agent']} agent...")
            
            result = await self.send_agent_request_and_collect_response(
                conn_id, scenario["agent"], scenario["query"], timeout=45.0
            )
            
            # Verify basic WebSocket functionality
            assert "agent_started" in result["event_types"], f"Missing agent_started for {scenario['agent']}"
            assert "agent_completed" in result["event_types"], f"Missing agent_completed for {scenario['agent']}"
            
            if result["final_response"]:
                quality_scores = self.quality_grader.grade_response(
                    scenario["query"], result["final_response"], scenario["agent"]
                )
                
                quality_results.append({
                    "agent": scenario["agent"],
                    "quality_scores": quality_scores,
                    "query": scenario["query"],
                    "response_length": len(result["final_response"])
                })
                
                # Assert individual quality threshold
                assert quality_scores["overall_quality"] >= scenario["expected_min_quality"], (
                    f"{scenario['agent']} agent quality {quality_scores['overall_quality']:.3f} "
                    f"below threshold {scenario['expected_min_quality']}"
                )
            else:
                pytest.fail(f"{scenario['agent']} agent returned no response")
        
        # Verify all agents met quality standards
        assert len(quality_results) == len(test_scenarios), "Not all agents provided valid responses"
        
        # Log comparative results
        self.logger.info("Agent Quality Comparison:")
        for result in quality_results:
            self.logger.info(
                f"  {result['agent']}: {result['quality_scores']['overall_quality']:.3f} "
                f"(R:{result['quality_scores']['relevance']:.2f}, "
                f"C:{result['quality_scores']['completeness']:.2f}, "
                f"A:{result['quality_scores']['actionability']:.2f})"
            )
    
    @pytest.mark.e2e  
    @pytest.mark.real_services
    async def test_websocket_event_completeness_during_quality_grading(self, real_services_fixture):
        """Test that all 5 critical WebSocket events are sent during agent execution."""
        user_data = await self.create_test_user()
        conn_id = await self.create_authenticated_websocket_connection(user_data)
        
        test_query = "Provide a comprehensive analysis of my system performance and optimization opportunities."
        
        result = await self.send_agent_request_and_collect_response(
            conn_id, "optimization", test_query, timeout=60.0
        )
        
        # Check all 5 critical WebSocket events
        expected_events = [
            "agent_started",    # User must see agent began processing
            "agent_thinking",   # Real-time reasoning visibility  
            "tool_executing",   # Tool usage transparency
            "tool_completed",   # Tool results display
            "agent_completed"   # User must know when response is ready
        ]
        
        received_events = result["event_types"]
        
        # Verify all critical events (some may occur multiple times)
        for event_type in expected_events:
            assert event_type in received_events, (
                f"Missing critical WebSocket event: {event_type}. "
                f"Received events: {received_events}"
            )
        
        # Verify response quality
        if result["final_response"]:
            quality_scores = self.quality_grader.grade_response(
                test_query, result["final_response"], "optimization"
            )
            assert quality_scores["overall_quality"] >= 0.7
        else:
            pytest.fail("No final response despite WebSocket events")
        
        self.logger.info(f"All 5 critical WebSocket events verified: {set(received_events)}")
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_edge_case_quality_grading(self, real_services_fixture):
        """Test quality grading with edge cases and challenging queries."""
        user_data = await self.create_test_user()
        conn_id = await self.create_authenticated_websocket_connection(user_data)
        
        edge_case_queries = [
            "?",  # Minimal query
            "help me optimize everything possible in my entire infrastructure right now",  # Vague/broad
            "What is the exact ROI calculation for implementing Kubernetes vs Docker Swarm for a 50-node cluster with 200 microservices?",  # Highly specific
        ]
        
        for i, query in enumerate(edge_case_queries):
            self.logger.info(f"Testing edge case {i+1}: {query[:50]}...")
            
            result = await self.send_agent_request_and_collect_response(
                conn_id, "optimization", query, timeout=45.0
            )
            
            # Even edge cases should trigger basic WebSocket events
            assert "agent_started" in result["event_types"], f"Edge case {i+1} missing agent_started"
            
            if result["final_response"]:
                quality_scores = self.quality_grader.grade_response(
                    query, result["final_response"], "optimization"
                )
                
                # Edge cases may have lower quality, but should still be reasonable
                # For minimal queries, we expect lower scores
                if len(query.strip()) < 10:
                    min_quality = 0.3
                else:
                    min_quality = 0.5
                
                assert quality_scores["overall_quality"] >= min_quality, (
                    f"Edge case {i+1} quality {quality_scores['overall_quality']:.3f} "
                    f"below minimum {min_quality}"
                )
                
                self.logger.info(f"Edge case {i+1} quality: {quality_scores['overall_quality']:.3f}")