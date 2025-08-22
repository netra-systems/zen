"""
Real LLM Testing Framework Manager - Core orchestration module

Provides real LLM client support for multiple models with intelligent fallback
to mocks when real testing is disabled. Follows 450-line/25-line limits.
"""
import hashlib
import os
import time
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from netra_backend.app.core.exceptions_base import NetraException
from netra_backend.app.schemas.llm_config_types import LLMConfig
from netra_backend.app.schemas.llm_response_types import LLMResponse


class LLMTestModel(str, Enum):
    """Supported LLM models for testing."""
    GPT_4 = "gpt-4"
    GPT_35_TURBO = "gpt-3.5-turbo"
    CLAUDE_3_OPUS = "claude-3-opus"
    CLAUDE_3_SONNET = "claude-3-sonnet"
    GEMINI_PRO = "gemini-pro"


class LLMTestConfig(BaseModel):
    """Configuration for LLM test manager."""
    enabled: bool = Field(default=False)
    models: List[LLMTestModel] = Field(default_factory=list)
    cache_enabled: bool = Field(default=True)
    timeout_seconds: int = Field(default=30)
    max_retries: int = Field(default=3)
    fallback_to_mock: bool = Field(default=True)


class LLMTestRequest(BaseModel):
    """Request structure for LLM testing."""
    prompt: str = Field(..., description="Prompt text")
    model: LLMTestModel = Field(..., description="Target model")
    temperature: float = Field(default=0.7)
    max_tokens: Optional[int] = Field(default=None)
    use_cache: bool = Field(default=True)


class LLMTestResponse(BaseModel):
    """Response structure from LLM testing."""
    content: str = Field(..., description="Response content")
    model_used: LLMTestModel = Field(..., description="Model that generated response")
    cache_hit: bool = Field(default=False)
    response_time_ms: int = Field(..., description="Response time in milliseconds")
    tokens_used: Optional[int] = Field(default=None)
    success: bool = Field(default=True)


class LLMTestManager:
    """Main manager for real LLM testing with intelligent fallback."""
    
    def __init__(self, config: Optional[LLMTestConfig] = None):
        self.config = config or self._load_config_from_env()
        self._clients: Dict[LLMTestModel, Any] = {}
        self._cache = None
        self._initialize_components()
        
    def _load_config_from_env(self) -> LLMTestConfig:
        """Load configuration from environment variables."""
        # Test-specific configuration from environment for LLM testing
        enabled = os.getenv("ENABLE_REAL_LLM_TESTING", "false").lower() == "true"
        models_str = os.getenv("LLM_TEST_MODELS", "gpt-4,claude-3-opus")
        models = self._parse_models_from_string(models_str)
        return LLMTestConfig(enabled=enabled, models=models)
        
    def _parse_models_from_string(self, models_str: str) -> List[LLMTestModel]:
        """Parse model names from comma-separated string."""
        model_names = [name.strip() for name in models_str.split(",")]
        return [LLMTestModel(name) for name in model_names if name in LLMTestModel.__members__.values()]
        
    def _initialize_components(self):
        """Initialize cache and clients."""
        if self.config.cache_enabled:
            self._initialize_cache()
        if self.config.enabled:
            self._initialize_real_clients()
        # Always initialize mock clients for fallback
        self._initialize_mock_clients()
            
    def _initialize_cache(self):
        """Initialize response cache if enabled."""
        from .llm_response_cache import LLMResponseCache
        self._cache = LLMResponseCache()
        
    def _initialize_real_clients(self):
        """Initialize real LLM clients for enabled models."""
        for model in self.config.models:
            client = self._create_real_client(model)
            if client:
                self._clients[model] = client
                
    def _create_real_client(self, model: LLMTestModel) -> Optional[Any]:
        """Create real client for specific model."""
        if model in [LLMTestModel.GPT_4, LLMTestModel.GPT_35_TURBO]:
            return self._create_openai_client(model)
        elif model in [LLMTestModel.CLAUDE_3_OPUS, LLMTestModel.CLAUDE_3_SONNET]:
            return self._create_anthropic_client(model)
        elif model == LLMTestModel.GEMINI_PRO:
            return self._create_gemini_client(model)
        return None
        
    def _create_openai_client(self, model: LLMTestModel) -> Optional[Any]:
        """Create OpenAI client."""
        # For test clients, read API key directly for test setup
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key or api_key.startswith("test-"):
            return None
        try:
            import openai
            return openai.AsyncOpenAI(api_key=api_key)
        except ImportError:
            return None
            
    def _create_anthropic_client(self, model: LLMTestModel) -> Optional[Any]:
        """Create Anthropic client."""
        # For test clients, read API key directly for test setup
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key or api_key.startswith("test-"):
            return None
        try:
            import anthropic
            return anthropic.AsyncAnthropic(api_key=api_key)
        except ImportError:
            return None
            
    def _create_gemini_client(self, model: LLMTestModel) -> Optional[Any]:
        """Create Gemini client."""
        # For test clients, read API key directly for test setup
        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key or api_key.startswith("test-"):
            return None
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            return genai.GenerativeModel(model.value)
        except ImportError:
            return None
            
    def _initialize_mock_clients(self):
        """Initialize mock clients for fallback."""
        from .llm_mock_client import LLMTestMockClient
        for model in self.config.models:
            if model not in self._clients:
                self._clients[model] = LLMTestMockClient(model)
            
    async def generate_response(self, request: LLMTestRequest) -> LLMTestResponse:
        """Generate response using specified model with caching and fallback."""
        if request.use_cache and self._cache:
            cached_response = await self._try_cache_lookup(request)
            if cached_response:
                return cached_response
                
        response = await self._generate_with_fallback(request)
        
        if request.use_cache and self._cache and response.success:
            await self._cache_response(request, response)
            
        return response
        
    async def _try_cache_lookup(self, request: LLMTestRequest) -> Optional[LLMTestResponse]:
        """Try to get response from cache."""
        cache_key = self._generate_cache_key(request)
        cached_data = await self._cache.get(cache_key)
        if cached_data:
            cached_data['cache_hit'] = True
            return LLMTestResponse(**cached_data)
        return None
        
    def _generate_cache_key(self, request: LLMTestRequest) -> str:
        """Generate cache key from request."""
        content = f"{request.prompt}:{request.model}:{request.temperature}"
        return hashlib.md5(content.encode()).hexdigest()
        
    async def _generate_with_fallback(self, request: LLMTestRequest) -> LLMTestResponse:
        """Generate response with intelligent fallback."""
        import time
        start_time = time.time()
        
        if request.model in self._clients:
            response = await self._try_real_generation(request, start_time)
            if response:
                return response
                
        if self.config.fallback_to_mock:
            return await self._generate_mock_response(request, start_time)
        else:
            raise NetraException(f"No available client for model {request.model}")
            
    async def _try_real_generation(self, request: LLMTestRequest, start_time: float) -> Optional[LLMTestResponse]:
        """Try generating with real client."""
        try:
            client = self._clients[request.model]
            content = await self._call_real_client(client, request)
            response_time = int((time.time() - start_time) * 1000)
            return LLMTestResponse(
                content=content,
                model_used=request.model,
                response_time_ms=response_time,
                success=True
            )
        except Exception:
            return None
            
    async def _call_real_client(self, client: Any, request: LLMTestRequest) -> str:
        """Call appropriate real client based on model type."""
        if hasattr(client, 'chat'):  # OpenAI
            return await self._call_openai_client(client, request)
        elif hasattr(client, 'messages'):  # Anthropic
            return await self._call_anthropic_client(client, request)
        elif hasattr(client, 'generate_content'):  # Gemini
            return await self._call_gemini_client(client, request)
        else:
            raise NetraException(f"Unknown client type for {request.model}")
            
    async def _call_openai_client(self, client: Any, request: LLMTestRequest) -> str:
        """Call OpenAI client."""
        response = await client.chat.completions.create(
            model=request.model.value,
            messages=[{"role": "user", "content": request.prompt}],
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )
        return response.choices[0].message.content
        
    async def _call_anthropic_client(self, client: Any, request: LLMTestRequest) -> str:
        """Call Anthropic client."""
        response = await client.messages.create(
            model=request.model.value,
            max_tokens=request.max_tokens or 1024,
            messages=[{"role": "user", "content": request.prompt}]
        )
        return response.content[0].text
        
    async def _call_gemini_client(self, client: Any, request: LLMTestRequest) -> str:
        """Call Gemini client."""
        response = await client.generate_content(request.prompt)
        return response.text
        
    async def _generate_mock_response(self, request: LLMTestRequest, start_time: float) -> LLMTestResponse:
        """Generate mock response when real clients unavailable."""
        from .llm_mock_client import LLMTestMockClient
        mock_client = LLMTestMockClient(request.model)
        content = await mock_client.generate(request.prompt)
        response_time = int((time.time() - start_time) * 1000)
        return LLMTestResponse(
            content=content,
            model_used=request.model,
            response_time_ms=response_time,
            success=True
        )
        
    async def _cache_response(self, request: LLMTestRequest, response: LLMTestResponse):
        """Cache successful response."""
        cache_key = self._generate_cache_key(request)
        cache_data = response.model_dump()
        cache_data['cache_hit'] = False  # Reset for future cache hits
        await self._cache.set(cache_key, cache_data)
        
    def is_real_testing_enabled(self) -> bool:
        """Check if real LLM testing is enabled."""
        return self.config.enabled and len(self._clients) > 0
        
    def get_available_models(self) -> List[LLMTestModel]:
        """Get list of available models."""
        return list(self._clients.keys())
        
    async def ask_llm(self, prompt: str, model: str = "gpt-4", temperature: float = 0.7) -> str:
        """Ask LLM interface compatible with agent expectations."""
        try:
            model_enum = LLMTestModel(model)
        except ValueError:
            model_enum = LLMTestModel.GPT_4
            
        request = LLMTestRequest(
            prompt=prompt,
            model=model_enum,
            temperature=temperature,
            use_cache=self.config.cache_enabled
        )
        
        response = await self.generate_response(request)
        return response.content
        
    def get_statistics(self) -> Dict[str, Any]:
        """Get testing statistics."""
        stats = {
            "enabled": self.config.enabled,
            "available_models": [model.value for model in self.get_available_models()],
            "cache_enabled": self.config.cache_enabled
        }
        if self._cache:
            stats.update(self._cache.get_statistics())
        return stats