"""
LLM and AI service mock implementations.
Consolidates all AI/LLM-related mocks including structured response generation.
"""

import asyncio
from typing import Any, Dict, List, Optional, Type, TypeVar
from unittest.mock import AsyncMock, MagicMock
from pydantic import BaseModel
from netra_backend.app.llm.llm_defaults import LLMModel, LLMConfig


T = TypeVar('T', bound=BaseModel)


class MockLLMService:
    """Mock LLM service for testing AI interactions."""
    
    def __init__(self):
        """Initialize mock LLM service."""
        self.requests = []
        self.responses = []
        self.default_response = {
            "content": "Mock LLM response",
            "model": "mock-model",
            "tokens_used": 10,
            "cost": 0.001
        }
        self.should_fail = False
        self.response_delay = 0.1
        
    def set_response(self, response: Dict[str, Any]):
        """Set the response for next request."""
        self.responses.append(response)
        
    def set_responses(self, responses: List[Dict[str, Any]]):
        """Set multiple responses for subsequent requests."""
        self.responses.extend(responses)
        
    def set_failure_mode(self, enabled: bool, error_message: str = "Mock LLM failure"):
        """Enable/disable failure simulation."""
        self.should_fail = enabled
        self.error_message = error_message
        
    def set_response_delay(self, delay: float):
        """Set response delay to simulate processing time."""
        self.response_delay = delay
        
    async def generate_response(
        self, 
        prompt: str, 
        model: str = "default",
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs
    ) -> Dict[str, Any]:
        """Mock generate response."""
        # Simulate processing delay
        await asyncio.sleep(self.response_delay)
        
        # Record request
        self.requests.append({
            "prompt": prompt,
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "kwargs": kwargs
        })
        
        # Simulate failure if enabled
        if self.should_fail:
            raise Exception(self.error_message)
        
        # Return queued response or default
        if self.responses:
            response = self.responses.pop(0)
            # Add metadata
            response.setdefault("model", model)
            response.setdefault("tokens_used", len(prompt) // 4)  # Rough estimate
            response.setdefault("cost", response.get("tokens_used", 0) * 0.0001)
            return response
        
        # Return default response
        default = self.default_response.copy()
        default["model"] = model
        default["tokens_used"] = len(prompt) // 4
        default["cost"] = default["tokens_used"] * 0.0001
        return default
    
    async def analyze_optimization(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock optimization analysis."""
        await asyncio.sleep(self.response_delay)
        
        if self.should_fail:
            raise Exception(self.error_message)
            
        return {
            "optimization_suggestions": ["Mock suggestion 1", "Mock suggestion 2"],
            "confidence": 0.85,
            "potential_savings": 1000,
            "analysis_model": "mock-optimizer"
        }
        
    async def generate_structured_response(self, schema: Type[T], prompt: str, **kwargs) -> T:
        """Generate structured response matching Pydantic schema."""
        await asyncio.sleep(self.response_delay)
        
        if self.should_fail:
            raise Exception(self.error_message)
            
        # Create mock data based on schema
        mock_data = create_mock_structured_response(schema)
        return mock_data
        
    def get_request_history(self) -> List[Dict[str, Any]]:
        """Get history of all LLM requests."""
        return self.requests.copy()
        
    def clear_request_history(self):
        """Clear request history."""
        self.requests.clear()
        
    def get_total_cost(self) -> float:
        """Calculate total cost of all requests."""
        return sum(req.get("cost", 0) for req in self.requests)
        
    def get_total_tokens(self) -> int:
        """Calculate total tokens used."""
        return sum(req.get("tokens_used", 0) for req in self.requests)


class MockAgentService:
    """Mock agent service for testing multi-agent workflows."""
    
    def __init__(self):
        """Initialize mock agent service."""
        self.messages_processed = []
        self.agents = {}
        self.next_agent_id = 1
        self.processing_delay = 0.05
        
    async def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Mock process message through agent."""
        await asyncio.sleep(self.processing_delay)
        
        self.messages_processed.append(message)
        
        return {
            "response": f"Processed: {message.get('content', 'no content')}",
            "metadata": {"agent_id": f"agent_{self.next_agent_id}"},
            "status": "completed",
            "processing_time": self.processing_delay
        }
    
    async def start_agent(self, agent_config: Dict[str, Any]) -> Dict[str, str]:
        """Mock start agent."""
        agent_id = f"agent_{self.next_agent_id}"
        self.next_agent_id += 1
        self.agents[agent_id] = {
            "status": "running",
            "config": agent_config
        }
        return {"agent_id": agent_id}
    
    async def stop_agent(self, agent_id: str) -> bool:
        """Mock stop agent."""
        if agent_id in self.agents:
            self.agents[agent_id]["status"] = "stopped"
            return True
        return False
    
    def get_agent_status(self, agent_id: str) -> str:
        """Mock get agent status."""
        if agent_id in self.agents:
            return self.agents[agent_id]["status"]
        return "not_found"
        
    def get_processed_messages(self) -> List[Dict[str, Any]]:
        """Get history of processed messages."""
        return self.messages_processed.copy()
        
    def clear_message_history(self):
        """Clear processed message history."""
        self.messages_processed.clear()


def create_mock_structured_response(schema: Type[T]) -> T:
    """Create mock structured response for testing."""
    mock_data = {}
    for field_name, field_info in schema.model_fields.items():
        if field_info.is_required():
            mock_data[field_name] = get_mock_value_for_field(field_info)
    return schema(**mock_data)


def get_mock_value_for_field(field_info: Any) -> Any:
    """Get mock value based on field type annotation."""
    annotation = field_info.annotation
    if annotation == str:
        return f"Mock {field_info.alias or 'string'}"
    elif annotation == float:
        return 0.5
    elif annotation == int:
        return 1
    elif annotation == bool:
        return False
    return get_complex_mock_value(annotation)


def get_complex_mock_value(annotation: Any) -> Any:
    """Handle complex field types for mock values."""
    if annotation == dict:
        return {}
    elif annotation == list:
        return []
    elif hasattr(annotation, '__origin__'):
        return handle_generic_type(annotation)
    return {}


def handle_generic_type(annotation: Any) -> Any:
    """Handle generic types like List, Dict, Optional."""
    origin = getattr(annotation, '__origin__', None)
    if origin == list:
        return []
    elif origin == dict:
        return {}
    return None


class MockOpenAIClient:
    """Mock OpenAI client for testing."""
    
    def __init__(self):
        """Initialize mock OpenAI client."""
        self.llm_service = MockLLMService()
        
    def chat_completions_create(
        self, 
        messages: List[Dict[str, str]], 
        model: str = LLMModel.GEMINI_2_5_FLASH.value,
        **kwargs
    ) -> Dict[str, Any]:
        """Mock chat completion creation."""
        # Extract prompt from messages
        prompt = "\n".join([f"{msg['role']}: {msg['content']}" for msg in messages])
        
        # Use internal LLM service (sync version)
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            response = loop.run_until_complete(
                self.llm_service.generate_response(prompt, model=model, **kwargs)
            )
        finally:
            loop.close()
        
        # Format as OpenAI response
        return {
            "id": f"chatcmpl-mock-{len(self.llm_service.requests)}",
            "object": "chat.completion",
            "model": model,
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response["content"]
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": len(prompt) // 4,
                "completion_tokens": response["tokens_used"],
                "total_tokens": len(prompt) // 4 + response["tokens_used"]
            }
        }
        
    def set_response(self, content: str):
        """Set next response content."""
        self.llm_service.set_response({"content": content})
        
    def set_failure_mode(self, enabled: bool):
        """Enable/disable failure mode."""
        self.llm_service.set_failure_mode(enabled)


class MockEmbeddingService:
    """Mock embedding service for vector operations."""
    
    def __init__(self, embedding_dim: int = 1536):
        """Initialize mock embedding service."""
        self.embedding_dim = embedding_dim
        self.embedding_requests = []
        self.should_fail = False
        
    async def create_embedding(self, text: str, model: str = "text-embedding-ada-002") -> List[float]:
        """Create mock text embedding."""
        self.embedding_requests.append({"text": text, "model": model})
        
        if self.should_fail:
            raise Exception("Mock embedding service failure")
            
        # Generate deterministic "embedding" based on text hash
        import hashlib
        text_hash = hashlib.md5(text.encode()).hexdigest()
        
        # Convert hash to floats for embedding vector
        embedding = []
        for i in range(0, min(len(text_hash), self.embedding_dim // 8)):
            # Convert hex pairs to normalized floats
            hex_pair = text_hash[i*2:(i+1)*2] if i*2+1 < len(text_hash) else text_hash[i*2:] + '0'
            value = int(hex_pair, 16) / 255.0 * 2.0 - 1.0  # Normalize to [-1, 1]
            embedding.extend([value] * 8)  # Repeat to fill dimension
            
        # Pad or truncate to exact dimension
        embedding = (embedding + [0.0] * self.embedding_dim)[:self.embedding_dim]
        
        return embedding
        
    def set_failure_mode(self, enabled: bool):
        """Enable/disable failure simulation."""
        self.should_fail = enabled
        
    def get_embedding_history(self) -> List[Dict[str, Any]]:
        """Get history of embedding requests."""
        return self.embedding_requests.copy()
        
    def clear_embedding_history(self):
        """Clear embedding request history."""
        self.embedding_requests.clear()
