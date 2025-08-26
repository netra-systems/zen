"""
LLM Mock Client for Testing - Intelligent mock responses

Provides realistic mock responses for LLM testing when real clients are unavailable.
Follows 450-line/25-line limits and provides model-specific response patterns.
"""
import asyncio
import random
from typing import Any, Dict, Optional

from netra_backend.tests.e2e.infrastructure.llm_test_manager import LLMTestModel

class LLMTestMockClient:
    """Mock LLM client providing realistic responses for testing."""
    
    def __init__(self, model: LLMTestModel):
        self.model = model
        self._response_patterns = self._initialize_patterns()
        self._call_count = 0
        self._total_response_time = 0
        
    def _initialize_patterns(self) -> Dict[str, Any]:
        """Initialize model-specific response patterns."""
        return {
            "cost_optimization": self._get_cost_optimization_patterns(),
            "performance_analysis": self._get_performance_patterns(),
            "general": self._get_general_patterns()
        }
        
    def _get_cost_optimization_patterns(self) -> Dict[str, str]:
        """Get cost optimization response patterns."""
        return {
            "analysis": "Based on the current configuration, I identify 3 key cost optimization opportunities",
            "recommendations": "I recommend implementing caching strategies and optimizing batch processing",
            "projections": "These changes could reduce costs by 20-30% while maintaining performance"
        }
        
    def _get_performance_patterns(self) -> Dict[str, str]:
        """Get performance analysis response patterns."""
        return {
            "latency": "Current latency metrics indicate bottlenecks in database queries and API calls",
            "optimization": "Implementing connection pooling and async processing can improve performance",
            "monitoring": "Continuous monitoring shows P99 latency can be reduced from 500ms to 200ms"
        }
        
    def _get_general_patterns(self) -> Dict[str, str]:
        """Get general response patterns."""
        return {
            "analysis": "I've analyzed the provided information and identified several key patterns",
            "summary": "The data shows clear trends that require attention and optimization",
            "action": "I recommend taking the following steps to address these issues"
        }
        
    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate mock response based on prompt analysis."""
        await self._simulate_processing_delay()
        response_type = self._analyze_prompt_type(prompt)
        content = self._generate_response_content(prompt, response_type)
        self._update_metrics()
        return content
        
    async def _simulate_processing_delay(self):
        """Simulate realistic processing delay."""
        base_delay = self._get_model_base_delay()
        variation = random.uniform(0.8, 1.2)
        delay = base_delay * variation
        await asyncio.sleep(delay)
        
    def _get_model_base_delay(self) -> float:
        """Get base delay for model simulation."""
        delays = {
            LLMTestModel.GEMINI_2_5_FLASH: 0.05,
            LLMTestModel.GEMINI_2_5_PRO: 0.08,
            LLMTestModel.GEMINI_PRO: 0.06,
            LLMTestModel.CLAUDE_3_SONNET: 0.08
        }
        return delays.get(self.model, 0.08)
        
    def _analyze_prompt_type(self, prompt: str) -> str:
        """Analyze prompt to determine response type."""
        prompt_lower = prompt.lower()
        if any(word in prompt_lower for word in ["cost", "reduce", "money", "budget"]):
            return "cost_optimization"
        elif any(word in prompt_lower for word in ["latency", "performance", "speed", "optimization"]):
            return "performance_analysis"
        else:
            return "general"
            
    def _generate_response_content(self, prompt: str, response_type: str) -> str:
        """Generate response content based on type and model."""
        patterns = self._response_patterns[response_type]
        base_response = random.choice(list(patterns.values()))
        model_specific = self._add_model_specific_details(base_response)
        return self._customize_for_prompt(model_specific, prompt)
        
    def _add_model_specific_details(self, base_response: str) -> str:
        """Add model-specific details to response."""
        model_traits = {
            LLMTestModel.GEMINI_2_5_FLASH: "fast and efficient analysis with practical insights",
            LLMTestModel.GEMINI_2_5_PRO: "deep reasoning with multi-step problem solving",
            LLMTestModel.GEMINI_PRO: "data-driven insights with quantitative metrics",
            LLMTestModel.CLAUDE_3_SONNET: "balanced analysis with practical suggestions"
        }
        trait = model_traits.get(self.model, "general analysis")
        return f"{base_response} This {trait} approach ensures optimal results."
        
    def _customize_for_prompt(self, response: str, prompt: str) -> str:
        """Customize response based on specific prompt content."""
        if len(prompt) > 200:
            response += " Given the complexity of your request, I've provided a comprehensive analysis."
        if "?" in prompt:
            response += " Let me know if you need clarification on any aspect."
        return response
        
    def _update_metrics(self):
        """Update call metrics."""
        self._call_count += 1
        simulated_time = random.randint(50, 300)
        self._total_response_time += simulated_time
        
    def get_metrics(self) -> Dict[str, Any]:
        """Get client metrics."""
        avg_time = self._total_response_time / max(self._call_count, 1)
        return {
            "model": self.model.value,
            "call_count": self._call_count,
            "average_response_time_ms": round(avg_time, 2),
            "total_response_time_ms": self._total_response_time,
            "is_mock": True
        }
        
    def reset_metrics(self):
        """Reset client metrics."""
        self._call_count = 0
        self._total_response_time = 0

class MockClientFactory:
    """Factory for creating mock clients with consistent configuration."""
    
    @staticmethod
    def create_client(model: LLMTestModel, **kwargs) -> LLMTestMockClient:
        """Create mock client for specified model."""
        return LLMTestMockClient(model)
        
    @staticmethod
    def create_clients_for_models(models: list) -> Dict[LLMTestModel, LLMTestMockClient]:
        """Create mock clients for multiple models."""
        clients = {}
        for model in models:
            if isinstance(model, str):
                model = LLMTestModel(model)
            clients[model] = MockClientFactory.create_client(model)
        return clients
        
    @staticmethod
    def get_realistic_response_for_prompt(prompt: str, model: LLMTestModel) -> str:
        """Get realistic response for specific prompt and model."""
        client = MockClientFactory.create_client(model)
        response_type = client._analyze_prompt_type(prompt)
        return client._generate_response_content(prompt, response_type)