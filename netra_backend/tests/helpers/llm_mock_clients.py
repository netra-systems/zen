"""
LLM Mock Clients - Mock implementations for LLM testing
Extracted from test_llm_manager_provider_switching.py for 25-line function compliance
"""

import asyncio
import logging
import os
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel

from netra_backend.tests.helpers.llm_manager_helpers import LLMProvider, MockLLMResponse

logger = logging.getLogger(__name__)

class MockLLMClient:
    """Mock LLM client that can simulate different provider behaviors"""
    
    def __init__(self, provider: LLMProvider, model_name: str):
        self.provider = provider
        self.model_name = model_name
        self._init_default_settings()
    
    def _init_default_settings(self):
        """Initialize default client settings"""
        self.response_time = 0.1
        self.should_fail = False
        self.failure_rate = 0.0
        self.failure_message = f"Mock {self.provider.value} LLM failure"
        self.use_real_error_types = False
        self._init_counters()
    
    def _init_counters(self):
        """Initialize request counters"""
        self.request_count = 0
        self.successful_requests = 0
        self.failed_requests = 0
        
    async def ainvoke(self, prompt: str):
        """Mock async invoke with enhanced error handling"""
        self.request_count += 1
        
        try:
            await asyncio.sleep(self.response_time)
            
            if self._should_fail_request():
                self.failed_requests += 1
                self._raise_realistic_error()
            
            self.successful_requests += 1
            return self._create_response(prompt)
            
        except Exception as e:
            logger.warning(f"Mock LLM {self.provider.value} invoke failed: {e}")
            self.failed_requests += 1
            raise
    
    def _should_fail_request(self) -> bool:
        """Check if request should fail"""
        if self.should_fail:
            return True
        if self.failure_rate > 0:
            return __import__('random').random() < self.failure_rate
        return False
    
    def _raise_realistic_error(self):
        """Raise realistic errors based on provider type"""
        if self.use_real_error_types:
            if self.provider == LLMProvider.OPENAI:
                raise ConnectionError("OpenAI API connection failed")
            elif self.provider == LLMProvider.GOOGLE:
                raise TimeoutError("Google API request timed out")
            elif self.provider == LLMProvider.ANTHROPIC:
                raise ValueError("Anthropic API rate limit exceeded")
        
        raise Exception(self.failure_message)
    
    def _create_response(self, prompt: str) -> MockLLMResponse:
        """Create mock response"""
        content = f"[{self.provider.value}] Response to: {prompt[:50]}..."
        return MockLLMResponse(content, self.provider.value)
    
    async def astream(self, prompt: str):
        """Mock async stream"""
        self.request_count += 1
        
        if self.should_fail:
            self.failed_requests += 1
            raise Exception(self.failure_message)
        
        async for word in self._stream_words(prompt):
            yield word
        self.successful_requests += 1
    
    async def _stream_words(self, prompt: str):
        """Stream response words"""
        words = f"[{self.provider.value}] Streaming: {prompt[:30]}...".split()
        for word in words:
            await asyncio.sleep(0.01)
            yield type('obj', (object,), {'content': word + ' '})()
    
    def with_structured_output(self, schema: Type[BaseModel], **kwargs):
        """Mock structured output"""
        return MockStructuredLLMClient(self.provider, self.model_name, schema)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get client metrics"""
        return self._build_metrics_dict()
    
    def _build_metrics_dict(self) -> Dict[str, Any]:
        """Build metrics dictionary"""
        return {
            'provider': self.provider.value,
            'model_name': self.model_name,
            'request_count': self.request_count,
            'successful_requests': self.successful_requests,
            'failed_requests': self.failed_requests,
            'success_rate': self.successful_requests / max(self.request_count, 1),
            'response_time': self.response_time
        }

class MockStructuredLLMClient:
    """Mock structured LLM client"""
    
    def __init__(self, provider: LLMProvider, model_name: str, schema: Type[BaseModel]):
        self.provider = provider
        self.model_name = model_name
        self.schema = schema
        self.should_fail = False
    
    async def ainvoke(self, prompt: str):
        """Mock structured invoke"""
        if self.should_fail:
            raise Exception("Mock structured LLM failure")
        
        mock_data = self._create_mock_data()
        return self.schema(**mock_data)
    
    def _create_mock_data(self) -> Dict[str, Any]:
        """Create mock structured response data"""
        mock_data = {}
        for field_name, field_info in self.schema.model_fields.items():
            if self._is_required_field(field_info):
                mock_data[field_name] = self._get_mock_value(field_name, field_info)
        return mock_data
    
    def _is_required_field(self, field_info) -> bool:
        """Check if field is required"""
        return hasattr(field_info, 'is_required') and field_info.is_required()
    
    def _get_mock_value(self, field_name: str, field_info) -> Any:
        """Get mock value for field based on type"""
        annotation = field_info.annotation
        return self._create_typed_mock_value(field_name, annotation)
    
    def _create_typed_mock_value(self, field_name: str, annotation) -> Any:
        """Create mock value based on type annotation"""
        type_map = {
            str: f"Mock {field_name} from {self.provider.value}",
            int: 42,
            float: 3.14,
            bool: True,
            list: ["mock", "list"],
            dict: {"mock": "dict"}
        }
        return type_map.get(annotation, f"mock_{field_name}")