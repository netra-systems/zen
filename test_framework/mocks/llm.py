"""
LLM Mock Module

Provides mock LLM implementations for testing.
"""

import asyncio
import json
import time
from typing import Dict, Any, List, Optional, Union, AsyncIterator
from unittest.mock import Mock, AsyncMock
import uuid
from dataclasses import dataclass
from enum import Enum


class MockLLMProvider(str, Enum):
    """Mock LLM providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    MOCK_LOCAL = "mock_local"


class MockLLMModel(str, Enum):
    """Mock LLM models."""
    GPT_3_5 = "gpt-3.5-turbo"
    GPT_4 = "gpt-4"
    CLAUDE_3_HAIKU = "claude-3-haiku"
    CLAUDE_3_SONNET = "claude-3-sonnet"
    MOCK_FAST = "mock-fast"
    MOCK_SLOW = "mock-slow"


@dataclass
class MockLLMUsage:
    """Mock LLM usage statistics."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    
    @property
    def cost_estimate(self) -> float:
        """Estimate cost based on token usage."""
        # Simplified cost calculation
        return (self.prompt_tokens * 0.0001) + (self.completion_tokens * 0.0002)


@dataclass
class MockLLMResponse:
    """Mock LLM response."""
    content: str
    model: str
    usage: MockLLMUsage
    response_id: str
    created_at: float
    finish_reason: str = "stop"
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        
        if not self.response_id:
            self.response_id = f"mock_resp_{uuid.uuid4().hex[:16]}"
        
        if not self.created_at:
            self.created_at = time.time()


class MockLLMClient:
    """Mock LLM client for testing."""
    
    def __init__(self, provider: MockLLMProvider = MockLLMProvider.MOCK_LOCAL,
                 model: MockLLMModel = MockLLMModel.MOCK_FAST):
        self.provider = provider
        self.model = model
        self.api_calls: List[Dict[str, Any]] = []
        self.response_delay = 0.1  # Default delay
        self.failure_rate = 0.0  # Failure rate (0.0 = never fail, 1.0 = always fail)
        
        # Predefined responses for testing
        self.predefined_responses: Dict[str, str] = {}
        self.response_templates: Dict[str, str] = {
            "default": "This is a mock response to your query: {prompt}",
            "error": "I'm sorry, I encountered an error processing your request.",
            "analysis": "Based on the provided data, I can see that {analysis_point}.",
            "code": "```python\n# Generated code for: {task}\nprint('Hello, World!')\n```",
            "optimization": "Here are my optimization recommendations: {recommendations}"
        }
        
        # Statistics
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.total_tokens_used = 0
    
    def set_response_delay(self, delay: float):
        """Set response delay for testing."""
        self.response_delay = delay
    
    def set_failure_rate(self, rate: float):
        """Set failure rate for testing."""
        self.failure_rate = max(0.0, min(1.0, rate))
    
    def add_predefined_response(self, prompt_key: str, response: str):
        """Add predefined response for specific prompt."""
        self.predefined_responses[prompt_key] = response
    
    async def generate(self, prompt: str, temperature: float = 0.7,
                      max_tokens: int = 1000, **kwargs) -> MockLLMResponse:
        """Generate mock LLM response."""
        self.total_requests += 1
        
        # Record API call
        call_data = {
            "prompt": prompt,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "kwargs": kwargs,
            "timestamp": time.time(),
            "model": self.model
        }
        self.api_calls.append(call_data)
        
        # Simulate processing delay
        if self.response_delay > 0:
            await asyncio.sleep(self.response_delay)
        
        # Simulate failures
        import random
        if random.random() < self.failure_rate:
            self.failed_requests += 1
            raise RuntimeError(f"Mock LLM failure (rate: {self.failure_rate})")
        
        # Generate response
        response_content = self._generate_response_content(prompt, kwargs)
        
        # Calculate mock usage
        prompt_tokens = len(prompt.split()) * 1.3  # Rough estimation
        completion_tokens = len(response_content.split()) * 1.3
        
        usage = MockLLMUsage(
            prompt_tokens=int(prompt_tokens),
            completion_tokens=int(completion_tokens),
            total_tokens=int(prompt_tokens + completion_tokens)
        )
        
        self.successful_requests += 1
        self.total_tokens_used += usage.total_tokens
        
        return MockLLMResponse(
            content=response_content,
            model=self.model,
            usage=usage,
            response_id=f"mock_{self.model}_{uuid.uuid4().hex[:8]}",
            created_at=time.time()
        )
    
    async def generate_stream(self, prompt: str, **kwargs) -> AsyncIterator[str]:
        """Generate streaming mock LLM response."""
        response = await self.generate(prompt, **kwargs)
        
        # Split response into chunks for streaming
        words = response.content.split()
        chunk_size = max(1, len(words) // 10)  # ~10 chunks
        
        for i in range(0, len(words), chunk_size):
            chunk = " ".join(words[i:i + chunk_size])
            if i + chunk_size < len(words):
                chunk += " "
            
            yield chunk
            await asyncio.sleep(0.05)  # Simulate streaming delay
    
    def _generate_response_content(self, prompt: str, kwargs: Dict[str, Any]) -> str:
        """Generate response content based on prompt."""
        # Check for predefined responses
        for key, response in self.predefined_responses.items():
            if key.lower() in prompt.lower():
                return response
        
        # Determine response type based on prompt content
        prompt_lower = prompt.lower()
        
        if any(word in prompt_lower for word in ["analyze", "analysis", "examine"]):
            return self.response_templates["analysis"].format(
                analysis_point="the key metrics show positive trends"
            )
        elif any(word in prompt_lower for word in ["code", "program", "function", "class"]):
            task = "the requested functionality"
            if "function" in prompt_lower:
                task = "function implementation"
            elif "class" in prompt_lower:
                task = "class definition"
            
            return self.response_templates["code"].format(task=task)
        elif any(word in prompt_lower for word in ["optimize", "improve", "better"]):
            return self.response_templates["optimization"].format(
                recommendations="1. Reduce complexity, 2. Improve caching, 3. Optimize queries"
            )
        elif "error" in prompt_lower:
            return self.response_templates["error"]
        else:
            return self.response_templates["default"].format(prompt=prompt[:50] + "...")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics."""
        success_rate = (self.successful_requests / self.total_requests) if self.total_requests > 0 else 0
        
        return {
            "provider": self.provider,
            "model": self.model,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": success_rate,
            "total_tokens_used": self.total_tokens_used,
            "average_tokens_per_request": self.total_tokens_used / max(1, self.successful_requests),
            "estimated_cost": sum(call.get("usage", MockLLMUsage()).cost_estimate 
                                 for call in self.api_calls if "usage" in call)
        }
    
    def reset_stats(self):
        """Reset statistics."""
        self.api_calls.clear()
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.total_tokens_used = 0


class MockLLMManager:
    """Mock LLM manager for handling multiple clients."""
    
    def __init__(self):
        self.clients: Dict[str, MockLLMClient] = {}
        self.default_client_id = "default"
        
        # Create default client
        self.clients[self.default_client_id] = MockLLMClient()
    
    def add_client(self, client_id: str, provider: MockLLMProvider, 
                   model: MockLLMModel) -> MockLLMClient:
        """Add a new LLM client."""
        client = MockLLMClient(provider, model)
        self.clients[client_id] = client
        return client
    
    def get_client(self, client_id: str = None) -> MockLLMClient:
        """Get LLM client by ID."""
        if client_id is None:
            client_id = self.default_client_id
        
        if client_id not in self.clients:
            raise ValueError(f"LLM client '{client_id}' not found")
        
        return self.clients[client_id]
    
    async def generate(self, prompt: str, client_id: str = None, **kwargs) -> MockLLMResponse:
        """Generate response using specified client."""
        client = self.get_client(client_id)
        return await client.generate(prompt, **kwargs)
    
    async def generate_with_fallback(self, prompt: str, 
                                   primary_client: str = None,
                                   fallback_clients: List[str] = None,
                                   **kwargs) -> MockLLMResponse:
        """Generate with fallback clients."""
        clients_to_try = [primary_client or self.default_client_id]
        if fallback_clients:
            clients_to_try.extend(fallback_clients)
        
        last_error = None
        
        for client_id in clients_to_try:
            try:
                client = self.get_client(client_id)
                return await client.generate(prompt, **kwargs)
            except Exception as e:
                last_error = e
                continue
        
        raise RuntimeError(f"All LLM clients failed. Last error: {last_error}")
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all clients."""
        return {
            client_id: client.get_stats()
            for client_id, client in self.clients.items()
        }


# Convenience functions and fixtures

def create_mock_llm_client(provider: MockLLMProvider = MockLLMProvider.MOCK_LOCAL,
                          model: MockLLMModel = MockLLMModel.MOCK_FAST) -> MockLLMClient:
    """Create a mock LLM client."""
    return MockLLMClient(provider, model)

def create_fast_llm_client() -> MockLLMClient:
    """Create a fast-responding mock LLM client."""
    client = MockLLMClient(MockLLMProvider.MOCK_LOCAL, MockLLMModel.MOCK_FAST)
    client.set_response_delay(0.01)
    return client

def create_slow_llm_client() -> MockLLMClient:
    """Create a slow-responding mock LLM client."""
    client = MockLLMClient(MockLLMProvider.MOCK_LOCAL, MockLLMModel.MOCK_SLOW)
    client.set_response_delay(1.0)
    return client

def create_unreliable_llm_client(failure_rate: float = 0.3) -> MockLLMClient:
    """Create an unreliable mock LLM client."""
    client = MockLLMClient()
    client.set_failure_rate(failure_rate)
    return client

def create_mock_llm_manager() -> MockLLMManager:
    """Create a mock LLM manager."""
    return MockLLMManager()

def setup_llm_test_scenario() -> Dict[str, Any]:
    """Set up a comprehensive LLM testing scenario."""
    manager = MockLLMManager()
    
    # Add different types of clients
    fast_client = manager.add_client("fast", MockLLMProvider.MOCK_LOCAL, MockLLMModel.MOCK_FAST)
    fast_client.set_response_delay(0.01)
    
    slow_client = manager.add_client("slow", MockLLMProvider.MOCK_LOCAL, MockLLMModel.MOCK_SLOW)
    slow_client.set_response_delay(1.0)
    
    unreliable_client = manager.add_client("unreliable", MockLLMProvider.OPENAI, MockLLMModel.GPT_3_5)
    unreliable_client.set_failure_rate(0.3)
    
    # Add predefined responses
    fast_client.add_predefined_response("hello", "Hello! How can I help you today?")
    fast_client.add_predefined_response("optimize", "Here are some optimization suggestions...")
    
    return {
        "manager": manager,
        "clients": {
            "fast": fast_client,
            "slow": slow_client,
            "unreliable": unreliable_client
        }
    }

# Test data generators

def generate_test_prompts(count: int = 10) -> List[str]:
    """Generate test prompts."""
    templates = [
        "Analyze the following data: {data}",
        "Write a function to {task}",
        "Optimize this code: {code}",
        "Explain the concept of {concept}",
        "Generate a report about {topic}",
        "Debug this error: {error}",
        "Create a plan for {objective}",
        "Summarize the following text: {text}",
        "Compare {item1} and {item2}",
        "What are the best practices for {domain}?"
    ]
    
    prompts = []
    for i in range(count):
        template = templates[i % len(templates)]
        prompt = template.format(
            data="sample data",
            task="process user input",
            code="def example(): pass",
            concept="machine learning",
            topic="system performance",
            error="ValueError: invalid input",
            objective="improving efficiency",
            text="sample text content",
            item1="approach A",
            item2="approach B",
            domain="software development"
        )
        prompts.append(prompt)
    
    return prompts

def create_llm_test_data() -> Dict[str, Any]:
    """Create comprehensive LLM test data."""
    return {
        "providers": [MockLLMProvider.OPENAI, MockLLMProvider.ANTHROPIC, MockLLMProvider.MOCK_LOCAL],
        "models": [MockLLMModel.GPT_3_5, MockLLMModel.GPT_4, MockLLMModel.CLAUDE_3_SONNET],
        "test_prompts": generate_test_prompts(20),
        "expected_responses": {
            "hello": "Hello! How can I help you today?",
            "analyze performance": "Based on the performance data, I can identify several key areas for improvement.",
            "write code": "```python\n# Here's the requested code implementation\npass\n```"
        },
        "failure_scenarios": [
            {"rate": 0.1, "description": "Occasional failures"},
            {"rate": 0.5, "description": "High failure rate"},
            {"rate": 1.0, "description": "Always fails"}
        ]
    }