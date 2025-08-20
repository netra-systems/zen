"""E2E Tests for Example Message Functionality in DEV MODE

Tests all 9 example prompts from the specification with real message submission,
validation, processing, and response generation. Focuses on testing actual
functionality without mocks.

Business Value: Validates Free tier conversion demonstrations work correctly
"""

import pytest
import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, Any, List
from uuid import uuid4

from app.handlers.example_message_handler import handle_example_message, ExampleMessageHandler
from app.routes.example_messages import router
from app.db.repositories.agent_repository import ThreadRepository, MessageRepository
from app.database import get_async_db
from app.db.models_agent import Thread, Message
from tests.unified.e2e.database_consistency_fixtures import database_test_session


# Example prompts from SPEC/exampleNetraPrompts.xml
EXAMPLE_PROMPTS = [
    {
        "id": "cost_reduction_quality",
        "content": "I need to reduce costs but keep quality the same. For feature X, I can accept a latency of 500ms. For feature Y, I need to maintain the current latency of 200ms.",
        "category": "cost-optimization",
        "complexity": "intermediate"
    },
    {
        "id": "latency_3x_improvement", 
        "content": "My tools are too slow. I need to reduce the latency by 3x, but I can't spend more money.",
        "category": "latency-optimization",
        "complexity": "advanced"
    },
    {
        "id": "usage_increase_impact",
        "content": "I'm expecting a 50% increase in agent usage next month. How will this impact my costs and rate limits?",
        "category": "scaling",
        "complexity": "intermediate"
    },
    {
        "id": "function_optimization",
        "content": "I need to optimize the 'user_authentication' function. What advanced methods can I use?",
        "category": "advanced",
        "complexity": "advanced"
    },
    {
        "id": "model_effectiveness",
        "content": "I'm considering using the new 'gpt-4o' and 'claude-3-sonnet' models. How effective would they be in my current setup?",
        "category": "model-selection",
        "complexity": "intermediate"
    },
    {
        "id": "kv_cache_audit",
        "content": "I want to audit all uses of KV caching in my system to find optimization opportunities.",
        "category": "advanced",
        "complexity": "advanced"
    },
    {
        "id": "multi_objective_optimization",
        "content": "I need to reduce costs by 20% and improve latency by 2x. I'm also expecting a 30% increase in usage. What should I do?",
        "category": "cost-optimization",
        "complexity": "advanced"
    },
    {
        "id": "gpt5_migration",
        "content": "@Netra which of our Agent tools should switch to GPT-5? Which versions? What to set the verbosity to?",
        "category": "model-selection",
        "complexity": "advanced"
    },
    {
        "id": "upgrade_analysis",
        "content": "@Netra was the upgrade yesterday to GPT-5 worth it? Rollback anything where quality didn't improve much but cost was higher",
        "category": "model-selection",
        "complexity": "intermediate"
    }
]


@pytest.fixture
async def example_handler():
    """Get example message handler instance"""
    return ExampleMessageHandler()


@pytest.fixture 
async def test_user_id():
    """Generate test user ID"""
    return f"test_user_{uuid4()}"


@pytest.fixture
async def thread_repo(database_test_session):
    """Get thread repository"""
    return ThreadRepository(database_test_session)


@pytest.fixture
async def message_repo(database_test_session):
    """Get message repository"""
    return MessageRepository(database_test_session)


class TestExampleMessageBasicFlow:
    """Test basic example message processing flow"""

    async def test_cost_reduction_prompt(self, example_handler, test_user_id):
        """Test cost reduction with quality preservation prompt"""
        prompt = EXAMPLE_PROMPTS[0]
        message_id = str(uuid4())
        
        request = self._create_request(prompt, message_id, test_user_id)
        response = await example_handler.handle_example_message(request)
        
        assert response.status == "completed"
        assert response.message_id == message_id
        assert response.processing_time_ms is not None
        assert response.result is not None
        assert "cost" in response.result.get("optimization_type", "").lower()

    async def test_latency_optimization_prompt(self, example_handler, test_user_id):
        """Test 3x latency improvement prompt"""
        prompt = EXAMPLE_PROMPTS[1]
        message_id = str(uuid4())
        
        request = self._create_request(prompt, message_id, test_user_id)
        response = await example_handler.handle_example_message(request)
        
        assert response.status == "completed"
        assert response.processing_time_ms < 5000  # Should be fast
        assert "latency" in response.result.get("optimization_type", "").lower()

    async def test_scaling_analysis_prompt(self, example_handler, test_user_id):
        """Test 50% usage increase impact analysis"""
        prompt = EXAMPLE_PROMPTS[2]
        message_id = str(uuid4())
        
        request = self._create_request(prompt, message_id, test_user_id)
        response = await example_handler.handle_example_message(request)
        
        assert response.status == "completed"
        assert "scaling" in response.result.get("optimization_type", "").lower()

    async def test_function_optimization_prompt(self, example_handler, test_user_id):
        """Test advanced function optimization methods"""
        prompt = EXAMPLE_PROMPTS[3]
        message_id = str(uuid4())
        
        request = self._create_request(prompt, message_id, test_user_id)
        response = await example_handler.handle_example_message(request)
        
        assert response.status == "completed"
        assert response.result.get("agent_name") is not None

    def _create_request(self, prompt: Dict[str, Any], message_id: str, user_id: str) -> Dict[str, Any]:
        """Create example message request"""
        return {
            "content": prompt["content"],
            "example_message_id": message_id,
            "example_message_metadata": {
                "title": f"Test: {prompt['id']}",
                "category": prompt["category"],
                "complexity": prompt["complexity"],
                "businessValue": "conversion",
                "estimatedTime": "2-3 minutes"
            },
            "user_id": user_id,
            "timestamp": int(datetime.now(timezone.utc).timestamp())
        }


class TestExampleMessageAdvanced:
    """Test advanced example message scenarios"""

    async def test_model_selection_prompts(self, example_handler, test_user_id):
        """Test all model selection related prompts"""
        model_prompts = [p for p in EXAMPLE_PROMPTS if p["category"] == "model-selection"]
        
        for prompt in model_prompts:
            message_id = str(uuid4())
            request = self._create_request(prompt, message_id, test_user_id)
            response = await example_handler.handle_example_message(request)
            
            assert response.status == "completed"
            assert response.result is not None

    async def test_multi_objective_optimization(self, example_handler, test_user_id):
        """Test complex multi-objective optimization"""
        prompt = EXAMPLE_PROMPTS[6]  # Multi-objective prompt
        message_id = str(uuid4())
        
        request = self._create_request(prompt, message_id, test_user_id)
        response = await example_handler.handle_example_message(request)
        
        assert response.status == "completed"
        assert "multi" in response.result.get("optimization_type", "").lower()

    async def test_kv_cache_audit(self, example_handler, test_user_id):
        """Test KV cache audit functionality"""
        prompt = EXAMPLE_PROMPTS[5]  # KV cache audit
        message_id = str(uuid4())
        
        request = self._create_request(prompt, message_id, test_user_id)
        response = await example_handler.handle_example_message(request)
        
        assert response.status == "completed"
        assert response.result.get("agent_name") is not None

    def _create_request(self, prompt: Dict[str, Any], message_id: str, user_id: str) -> Dict[str, Any]:
        """Create example message request"""
        return {
            "content": prompt["content"],
            "example_message_id": message_id,
            "example_message_metadata": {
                "title": f"Test: {prompt['id']}",
                "category": prompt["category"],
                "complexity": prompt["complexity"],
                "businessValue": "conversion",
                "estimatedTime": "2-3 minutes"
            },
            "user_id": user_id,
            "timestamp": int(datetime.now(timezone.utc).timestamp())
        }


class TestExampleMessageValidation:
    """Test message validation and error handling"""

    async def test_invalid_message_structure(self, example_handler):
        """Test handling of invalid message structure"""
        invalid_request = {"invalid": "structure"}
        
        response = await example_handler.handle_example_message(invalid_request)
        
        assert response.status == "error"
        assert response.error is not None

    async def test_missing_required_fields(self, example_handler):
        """Test handling of missing required fields"""
        incomplete_request = {
            "content": "Test message",
            # Missing required fields
        }
        
        response = await example_handler.handle_example_message(incomplete_request)
        
        assert response.status == "error"

    async def test_invalid_category(self, example_handler, test_user_id):
        """Test handling of invalid category"""
        request = {
            "content": "Test message",
            "example_message_id": str(uuid4()),
            "example_message_metadata": {
                "title": "Test",
                "category": "invalid-category",  # Invalid
                "complexity": "basic",
                "businessValue": "conversion",
                "estimatedTime": "1 minute"
            },
            "user_id": test_user_id,
            "timestamp": int(datetime.now(timezone.utc).timestamp())
        }
        
        response = await example_handler.handle_example_message(request)
        
        assert response.status == "error"


class TestExampleMessageBusiness:
    """Test business value and insights generation"""

    async def test_business_insights_generation(self, example_handler, test_user_id):
        """Test business insights are generated correctly"""
        prompt = EXAMPLE_PROMPTS[0]
        message_id = str(uuid4())
        
        request = self._create_request(prompt, message_id, test_user_id)
        response = await example_handler.handle_example_message(request)
        
        assert response.status == "completed"
        assert response.business_insights is not None
        assert "business_value_type" in response.business_insights
        assert "performance_score" in response.business_insights

    async def test_conversion_tracking(self, example_handler, test_user_id):
        """Test conversion-focused business value tracking"""
        prompt = EXAMPLE_PROMPTS[1]
        message_id = str(uuid4())
        
        request = self._create_request(prompt, message_id, test_user_id)
        request["example_message_metadata"]["businessValue"] = "conversion"
        
        response = await example_handler.handle_example_message(request)
        
        assert response.business_insights["business_value_type"] == "conversion"
        assert response.business_insights["performance_score"] > 0

    def _create_request(self, prompt: Dict[str, Any], message_id: str, user_id: str) -> Dict[str, Any]:
        """Create example message request"""
        return {
            "content": prompt["content"],
            "example_message_id": message_id,
            "example_message_metadata": {
                "title": f"Test: {prompt['id']}",
                "category": prompt["category"],
                "complexity": prompt["complexity"],
                "businessValue": "conversion",
                "estimatedTime": "2-3 minutes"
            },
            "user_id": user_id,
            "timestamp": int(datetime.now(timezone.utc).timestamp())
        }