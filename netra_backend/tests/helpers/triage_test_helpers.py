"""
Helper functions for triage sub agent tests to ensure functions are  <= 8 lines
"""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List
from unittest.mock import AsyncMock

from netra_backend.app.llm.llm_defaults import LLMModel, LLMConfig
from netra_backend.app.agents.state import DeepAgentState

class TriageMockHelpers:
    """Mock helpers for triage tests"""
    
    @staticmethod
    def create_mock_llm_manager():
        """Create mock LLM manager"""
        mock = AsyncMock()
        config = LLMConfig()
        config.model = LLMModel.GPT_4
        mock.llm_config = config
        return mock
    
    @staticmethod 
    def create_mock_tool_dispatcher():
        """Create mock tool dispatcher"""
        return AsyncMock()
    
    @staticmethod
    def create_mock_redis():
        """Create mock Redis manager"""
        return AsyncMock()

class ValidationHelpers:
    """Validation helpers for triage tests"""
    pass

class EntityExtractionHelpers:
    """Entity extraction helpers"""
    pass

class IntentHelpers:
    """Intent helpers for tests"""
    pass

class AsyncTestHelpers:
    """Async test helpers"""
    pass

class AssertionHelpers:
    """Assertion helpers for triage tests"""
    pass

class PerformanceHelpers:
    """Performance test helpers"""
    pass

class EdgeCaseHelpers:
    """Edge case test helpers"""
    pass

# Legacy class names for compatibility
MockLLMManager = TriageMockHelpers.create_mock_llm_manager
MockToolDispatcher = TriageMockHelpers.create_mock_tool_dispatcher
MockRedisManager = TriageMockHelpers.create_mock_redis
