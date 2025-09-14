"""
Helper classes for supervisor agent tests.
Contains mock implementations of classes used in testing.
"""

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, List
from unittest.mock import AsyncMock

from netra_backend.app.schemas.agent_models import DeepAgentState

class QualitySupervisor:
    """Mock QualitySupervisor for testing."""
    
    def __init__(self, llm_manager, websocket_manager):
        self.llm_manager = llm_manager
        self.websocket_manager = websocket_manager
        self.quality_threshold = 0.7
    
    async def validate_response(self, response):
        """Validate response quality."""
        result = await self.llm_manager.ask_llm("validate", "quality")
        return json.loads(result)

# Import real UnifiedAdminToolDispatcher - tests should use actual implementation
# If mocking is needed, use unittest.mock.Mock or pytest fixtures
from netra_backend.app.admin.tools.unified_admin_dispatcher import UnifiedAdminToolDispatcher as AdminToolDispatcher

class MockAdminToolDispatcher:
    """Mock AdminToolDispatcher for testing with required methods"""
    
    def __init__(self, llm_manager, tool_dispatcher):
        self.llm_manager = llm_manager
        self.tool_dispatcher = tool_dispatcher
        # Mock: Generic component isolation for controlled unit testing
        self.audit_logger = AsyncMock()
    
    async def dispatch_admin_operation(self, operation):
        """Mock dispatch admin operation method"""
        self._validate_permissions(operation)
        tool_name = self._get_tool_name(operation.get("type"))
        result = await self.tool_dispatcher.execute_tool(tool_name, operation["params"])
        await self._log_operation_if_available(operation, result)
        return result
    
    def _validate_permissions(self, operation):
        """Validate user permissions for operation"""
        user_role = operation.get("user_role", "admin")
        operation_type = operation.get("type")
        if user_role == "viewer" and operation_type == "delete_all_data":
            raise PermissionError("Insufficient permissions")
    
    async def _log_operation_if_available(self, operation, result):
        """Log operation if audit logger is available"""
        has_logger = hasattr(self, 'audit_logger') and self.audit_logger
        if has_logger:
            await self.audit_logger.log_admin_operation(operation, result)
    
    def _get_tool_name(self, operation_type):
        """Map operation type to tool name"""
        mapping = {
            "create_user": "admin_user_management",
            "system_config": "admin_system_config",
            "delete_all_data": "admin_data_management"
        }
        return mapping.get(operation_type, "default_admin_tool")

class CorpusAdminSubAgent:
    """Mock CorpusAdminSubAgent for testing."""
    
    def __init__(self, llm_manager, tool_dispatcher):
        self.llm_manager = llm_manager
        self.tool_dispatcher = tool_dispatcher
        self.vector_store = None
    
    async def index_documents(self, documents):
        """Index documents in vector store."""
        return await self.vector_store.add_documents(documents)
    
    async def retrieve_documents(self, query, top_k=2):
        """Retrieve documents using similarity search."""
        return await self.vector_store.similarity_search(query)
    
    async def update_document(self, update):
        """Update document in vector store."""
        return await self.vector_store.update_document(update)

class SupplyResearcherSubAgent:
    """Mock SupplyResearcherSubAgent for testing."""
    
    def __init__(self, llm_manager, tool_dispatcher):
        self.llm_manager = llm_manager
        self.tool_dispatcher = tool_dispatcher
        self.data_sources = None
        self.enrichment_service = None
    
    async def collect_supply_data(self, query):
        """Collect supply chain data."""
        return await self.data_sources.fetch_supply_data(query)
    
    async def validate_and_enrich(self, raw_data):
        """Validate and enrich data."""
        return await self.enrichment_service.enrich(raw_data)

class DemoService:
    """Mock DemoService for testing."""
    
    def __init__(self, llm_manager, tool_dispatcher):
        self.llm_manager = llm_manager
        self.tool_dispatcher = tool_dispatcher
        self.random_seed = 0
    
    async def run_demo(self, scenario):
        """Run demo scenario."""
        return await self.generate_demo_data()
    
    async def generate_demo_data(self):
        """Generate demo data."""
        return {
            "metrics": {"accuracy": 0.95, "latency": 100},
            "recommendations": ["Increase batch size", "Use mixed precision"]
        }
    
    async def generate_synthetic_metrics(self):
        """Generate synthetic metrics with variety."""
        import random
        random.seed(self.random_seed)
        return {
            "timestamp": time.time(),
            "value": random.random()
        }

class AgentPrompts:
    """Mock AgentPrompts for testing."""
    
    def render_template(self, template, variables, strict=False):
        """Render template with variables."""
        if strict:
            self._validate_template_variables(template, variables)
        return template.format(**variables)
    
    def _validate_template_variables(self, template, variables):
        """Validate all template variables are provided."""
        for key in template.split("{")[1:]:
            key = key.split("}")[0]
            if key and key not in variables:
                raise KeyError(key)

class EnhancedPrompts:
    """Mock EnhancedPrompts for testing."""
    
    def __init__(self):
        self.max_context_tokens = 1000
    
    def build_context(self, base_context, history):
        """Build enhanced context."""
        return {
            **base_context,
            "conversation_history": history
        }
    
    def optimize_prompt(self, prompt, optimization_goals):
        """Optimize prompt based on goals."""
        optimized = prompt
        if "clarity" in optimization_goals:
            optimized += " Please be specific and detailed."
        if "specificity" in optimization_goals:
            optimized = optimized.replace("my model", "the specific model")
        return optimized
    
    def manage_context_window(self, history):
        """Manage context window size."""
        return history[-5:]  # Simple truncation

class AgentUtils:
    """Mock AgentUtils for testing."""
    
    async def retry_with_backoff(self, func, max_retries=3, backoff_factor=1):
        """Retry function with exponential backoff."""
        for attempt in range(max_retries):
            try:
                return await func()
            except Exception as e:
                await self._handle_retry_exception(e, attempt, max_retries, backoff_factor)
    
    async def _handle_retry_exception(self, exception, attempt, max_retries, backoff_factor):
        """Handle exception during retry attempt"""
        if attempt == max_retries - 1:
            raise
        sleep_time = backoff_factor * (2 ** attempt)
        await asyncio.sleep(sleep_time)
    
    async def execute_parallel(self, tasks):
        """Execute tasks in parallel."""
        return await asyncio.gather(*tasks)
    
    async def with_timeout(self, coro, timeout):
        """Execute coroutine with timeout."""
        return await asyncio.wait_for(coro, timeout)
    
    def merge_states(self, state1, state2):
        """Merge two agent states."""
        merged = DeepAgentState(user_request=state1.user_request)
        valid_fields = self._get_valid_fields(merged)
        self._merge_attributes(merged, state1, state2, valid_fields)
        return merged
    
    def _get_valid_fields(self, merged):
        """Get valid fields from Pydantic model."""
        return merged.__fields__.keys() if hasattr(merged, '__fields__') else merged.model_fields.keys()
    
    def _merge_attributes(self, merged, state1, state2, valid_fields):
        """Merge attributes from both states."""
        for attr in valid_fields:
            if attr == "user_request":
                continue
            self._merge_single_attribute(merged, state1, state2, attr)
    
    def _merge_single_attribute(self, merged, state1, state2, attr):
        """Merge a single attribute."""
        val1 = getattr(state1, attr, None)
        val2 = getattr(state2, attr, None)
        merged_value = self._determine_merged_value(val1, val2)
        if merged_value is not None:
            setattr(merged, attr, merged_value)
    
    def _determine_merged_value(self, val1, val2):
        """Determine the merged value from two attribute values"""
        if val1 is not None and val2 is not None:
            return self._merge_values(val1, val2)
        elif val1 is not None:
            return val1
        elif val2 is not None:
            return val2
        return None
    
    def _merge_values(self, val1, val2):
        """Merge two values based on their types."""
        if isinstance(val1, dict) and isinstance(val2, dict):
            return self._merge_dictionaries(val1, val2)
        elif isinstance(val1, list) and isinstance(val2, list):
            return val1 + val2
        else:
            return val1
    
    def _merge_dictionaries(self, dict1, dict2):
        """Merge two dictionaries recursively."""
        merged = dict1.copy()
        for k, v in dict2.items():
            merged[k] = self._merge_dictionary_value(merged.get(k), v)
        return merged
    
    def _merge_dictionary_value(self, existing_value, new_value):
        """Merge a single dictionary value"""
        both_dicts = isinstance(existing_value, dict) and isinstance(new_value, dict)
        if both_dicts:
            return {**existing_value, **new_value}
        return new_value

class PermissionError(Exception):
    """Permission error for testing."""
    pass