"""
Agent Response Pipeline Mock Utilities

Business Value Justification (BVJ):
- Segment: ALL (core functionality for Free, Early, Mid, Enterprise)
- Business Goal: Protect $35K MRR from core functionality failures
- Value Impact: Validates complete agent response pipeline from WebSocket to delivery
- Revenue Impact: Prevents platform outages that would cause immediate customer churn

Mock utilities for agent response pipeline testing.
"""

from datetime import datetime, timezone
from fastapi import WebSocket
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.redis_manager import RedisManager
from netra_backend.app.websocket_core import WebSocketManager
from netra_backend.app.websocket_core import WebSocketManager as WebSocketManager
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, Mock
import asyncio
import json
import uuid
from netra_backend.app.llm.llm_defaults import LLMModel, LLMConfig


def mock_justified(reason: str):

    """Mock justification decorator per SPEC/testing.xml"""

    def decorator(func):

        func._mock_justification = reason

        return func

    return decorator

class AgentPipelineMocks:

    """Collection of mocks for agent pipeline testing."""
    
    @staticmethod
    def create_llm_manager_mock():
        """Mock LLM manager for agent response testing"""

        llm_mock = Mock(spec=LLMManager)
        
        response_templates = {

            "triage": {

                "high_quality": "Based on your request for optimization analysis, I'll route this to our Performance Optimization Specialist. This requires technical analysis of GPU memory usage, latency patterns, and cost optimization strategies.",

                "medium_quality": "I'll forward your optimization request to the appropriate specialist for detailed analysis.",

                "low_quality": "Routing your request to a specialist."

            },

            "optimization": {

                "high_quality": "GPU memory optimization analysis:\n1. Current usage: 24GB peak allocation\n2. Recommended reduction: 33% through gradient checkpointing\n3. Expected savings: $2,400/month\n4. Implementation: 2-week timeline\n5. Risk assessment: Low impact to model performance",

                "medium_quality": "GPU memory can be optimized by reducing allocation and implementing checkpointing strategies. Expected savings around $2,000/month.",

                "low_quality": "Memory optimization is possible through various techniques."

            },

            "data_analysis": {

                "high_quality": "Performance analysis results:\n[U+2022] Query latency: 450ms  ->  180ms (60% improvement)\n[U+2022] Throughput: 1,200  ->  3,400 QPS (183% increase)\n[U+2022] Error rate: 0.02% (within SLA)\n[U+2022] Cost impact: $1,800/month savings",

                "medium_quality": "Database performance improved significantly with query optimization and indexing changes.",

                "low_quality": "Performance has been improved through optimization."

            }

        }
        
        async def mock_generate_response(prompt, agent_type="triage", quality_level="high_quality"):

            await asyncio.sleep(0.1)
            
            template_key = agent_type if agent_type in response_templates else "triage"

            quality_key = quality_level if quality_level in response_templates[template_key] else "high_quality"
            
            response = response_templates[template_key][quality_key]
            
            return {"content": response, "usage": {"prompt_tokens": len(prompt), "completion_tokens": len(response)}, "model": LLMModel.GEMINI_2_5_FLASH.value, "finish_reason": "stop"}

        llm_mock.generate_response = AsyncMock(side_effect=mock_generate_response)

        llm_mock._response_templates = response_templates
        
        return llm_mock

    @staticmethod
    def create_websocket_mock():
        """Mock WebSocket for message delivery testing"""

        ws_mock = Mock(spec=WebSocket)

        ws_mock.state = "connected"
        
        sent_messages = []
        
        async def mock_send_text(message):

            sent_messages.append({"content": message, "timestamp": datetime.now(timezone.utc), "type": "text"})

            return True

        async def mock_send_json(data):

            sent_messages.append({"content": data, "timestamp": datetime.now(timezone.utc), "type": "json"})

            return True

        ws_mock.send_text = AsyncMock(side_effect=mock_send_text)

        ws_mock.send_json = AsyncMock(side_effect=mock_send_json)

        ws_mock._sent_messages = sent_messages
        
        return ws_mock

    @staticmethod
    def create_redis_manager_mock():
        """Mock Redis manager for agent state management"""

        redis_mock = Mock(spec=RedisManager)

        redis_mock.enabled = True
        
        state_store = {}
        
        async def mock_set(key, value, ex=None):

            state_store[key] = value

            return True

        async def mock_get(key):

            return state_store.get(key)

        redis_mock.set = AsyncMock(side_effect=mock_set)

        redis_mock.get = AsyncMock(side_effect=mock_get)

        redis_mock._state_store = state_store
        
        return redis_mock

    @staticmethod
    def create_websocket_manager_mock():
        """Mock WebSocket manager for connection management"""

        ws_manager_mock = Mock(spec=WebSocketManager)
        
        active_connections = {}
        
        async def mock_send_to_user(user_id, message):

            if user_id in active_connections:

                websocket = active_connections[user_id]["websocket"]

                if isinstance(message, dict):

                    await websocket.send_json(message)

                else:

                    await websocket.send_text(str(message))

                return True

            return False

        async def mock_add_connection(user_id, websocket):

            active_connections[user_id] = {"websocket": websocket, "connected_at": datetime.now(timezone.utc)}

            return True

        ws_manager_mock.send_to_user = AsyncMock(side_effect=mock_send_to_user)

        ws_manager_mock.add_connection = AsyncMock(side_effect=mock_add_connection)

        ws_manager_mock._active_connections = active_connections
        
        return ws_manager_mock

    @staticmethod

    def create_intelligent_triage_agent():

        """Create intelligent triage agent mock with routing logic."""

        triage_agent = Mock()
        
        async def mock_intelligent_triage(message_content):

            await asyncio.sleep(0.05)
            
            content_lower = message_content.lower()
            
            if any(keyword in content_lower for keyword in ["optimize", "gpu", "memory", "cost", "performance"]):

                if "database" in content_lower or "query" in content_lower:

                    return {"agent": "data_analysis_specialist", "confidence": 0.85}

                else:

                    return {"agent": "optimization_specialist", "confidence": 0.90}

            elif any(keyword in content_lower for keyword in ["deploy", "scale", "infrastructure", "nodes"]):

                return {"agent": "infrastructure_specialist", "confidence": 0.80}

            elif any(keyword in content_lower for keyword in ["debug", "error", "bug", "leak"]):

                return {"agent": "debugging_specialist", "confidence": 0.75}

            elif any(keyword in content_lower for keyword in ["analyze", "analysis", "data", "metrics"]):

                return {"agent": "data_analysis_specialist", "confidence": 0.85}

            else:

                return {"agent": "general_assistant", "confidence": 0.60}

        triage_agent.route_message = AsyncMock(side_effect=mock_intelligent_triage)

        return triage_agent

    @staticmethod

    def create_quality_assessment_function():

        """Create quality assessment function for response evaluation."""

        def assess_response_quality(response_content, request_context):

            """Assess response quality based on content analysis"""

            content_lower = response_content.lower()
            
            specific_indicators = ["gb", "ms", "%", "$", "step", "implement", "analysis", "optimize"]

            specificity_score = min(1.0, sum(1 for indicator in specific_indicators if indicator in content_lower) / 4)
            
            actionable_indicators = ["reduce", "implement", "deploy", "configure", "set", "use", "apply"]

            actionability_score = min(1.0, sum(1 for indicator in actionable_indicators if indicator in content_lower) / 3)
            
            technical_accuracy = 0.85 if len(response_content) > 100 else 0.65
            
            return {"specificity_score": specificity_score, "actionability_score": actionability_score, "technical_accuracy": technical_accuracy, "overall_score": (specificity_score + actionability_score + technical_accuracy) / 3}

        return assess_response_quality
