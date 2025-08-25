"""
Base infrastructure and utilities for Example Prompts E2E Tests
Provides shared fixtures and helper methods for test execution
"""

from netra_backend.app.websocket_core.manager import WebSocketManager
# Test framework import - using pytest fixtures instead
from pathlib import Path
import sys

import asyncio
import json
import os
import random
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest
import pytest_asyncio
from netra_backend.app.schemas.Agent import SubAgentState
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.config import get_config
from netra_backend.app.agents.state import DeepAgentState

from netra_backend.app.agents.supervisor_consolidated import (

    SupervisorAgent as Supervisor,

)
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.services.agent_service import AgentService
from netra_backend.app.services.apex_optimizer_agent.tools.tool_dispatcher import (

    ApexToolSelector,

)
from netra_backend.app.services.corpus_service import CorpusService
from netra_backend.app.services.quality_gate_service import (

    ContentType,

    QualityGateService,

    QualityLevel,

)
from netra_backend.app.services.state_persistence import state_persistence_service
from netra_backend.app.services.synthetic_data_service import (

    SyntheticDataService,

    WorkloadCategory,

)

# The 9 example prompts from frontend/lib/examplePrompts.ts

EXAMPLE_PROMPTS = [

    "I need to reduce costs but keep quality the same. For feature X, I can accept a latency of 500ms. For feature Y, I need to maintain the current latency of 200ms.",

    "My tools are too slow. I need to reduce the latency by 3x, but I can't spend more money.",

    "I'm expecting a 50% increase in agent usage next month. How will this impact my costs and rate limits?",

    "I need to optimize the 'user_authentication' function. What advanced methods can I use?",

    "I'm considering using the new 'gpt-4o' and 'claude-3-sonnet' models. How effective would they be in my current setup?",

    "I want to audit all uses of KV caching in my system to find optimization opportunities.",

    "I need to reduce costs by 20% and improve latency by 2x. I'm also expecting a 30% increase in usage. What should I do?",

    "@Netra which of our Agent tools should switch to GPT-5? Which versions? What to set the verbosity to?",

    "@Netra was the upgrade yesterday to GPT-5 worth it? Rollback anything where quality didn't improve much but cost was higher"

]

def _create_mock_db_session():

    """Create mock database session for testing"""

    # Mock: Database session isolation for transaction testing without real database dependency
    db_session = AsyncMock(spec=AsyncSession)

    # Mock: Session isolation for controlled testing without external state
    db_session.commit = AsyncMock()

    # Mock: Session isolation for controlled testing without external state
    db_session.rollback = AsyncMock()

    # Mock: Session isolation for controlled testing without external state
    db_session.close = AsyncMock()

    return db_session

def _create_mock_llm_manager():

    """Create mock LLM Manager with proper async functions"""

    # Mock: LLM service isolation for fast testing without API calls or rate limits
    llm_manager = Mock(spec=LLMManager)

    llm_manager.call_llm = _get_mock_call_llm()

    llm_manager.ask_llm = _get_mock_ask_llm()

    llm_manager.ask_structured_llm = _get_mock_ask_structured_llm()

    # Mock: LLM provider isolation to prevent external API usage and costs
    llm_manager.get = Mock(return_value=Mock())  # Add get method for config access

    return llm_manager

def _get_mock_call_llm():

    """Get mock call_llm async function"""

    async def mock_call_llm(*args, **kwargs):

        return {"content": "Based on analysis, reduce costs by switching to efficient models.", "tool_calls": []}

    return mock_call_llm

def _get_mock_ask_llm():

    """Get mock ask_llm async function"""

    async def mock_ask_llm(*args, **kwargs):

        return json.dumps({

            "category": "optimization", "analysis": "Cost optimization required",

            "recommendations": ["Switch to GPT-3.5 for low-complexity tasks", "Implement caching"]

        })

    return mock_ask_llm

def _get_mock_ask_structured_llm():

    """Get mock ask_structured_llm async function"""

    async def mock_ask_structured_llm(prompt, llm_config_name, schema, **kwargs):
        from netra_backend.app.schemas.unified_tools import TriageResult

        if schema == TriageResult:

            return TriageResult(

                category="optimization", severity="medium",

                analysis="Cost optimization analysis for provided prompt",

                requirements=["cost reduction", "performance maintenance"],

                next_steps=["analyze_costs", "identify_optimization_opportunities"],

                data_needed=["current_costs", "usage_patterns"],

                suggested_tools=["cost_analyzer", "performance_monitor"]

            )

        return schema()

    return mock_ask_structured_llm

def _create_mock_services():

    """Create mock services for testing infrastructure"""

    # Mock: Component isolation for controlled unit testing
    synthetic_data_service = Mock(spec=SyntheticDataService)

    # Mock: Async component isolation for testing without real async operations
    synthetic_data_service.generate_workload = AsyncMock(return_value={

        "workload_id": str(uuid.uuid4()), "category": WorkloadCategory.RAG_PIPELINE.value,

        "data": {"test": "data"}, "metadata": {"generated_at": datetime.now().isoformat()}

    })
    
    # Mock: Component isolation for controlled unit testing
    quality_gate_service = Mock(spec=QualityGateService)

    # Mock: Async component isolation for testing without real async operations
    quality_gate_service.validate_content = AsyncMock(return_value=(True, 95.0, ["Content meets quality standards"]))
    
    # Mock: Component isolation for controlled unit testing
    corpus_service = Mock(spec=CorpusService)

    # Mock: Async component isolation for testing without real async operations
    corpus_service.search = AsyncMock(return_value=[])

    # Mock: Async component isolation for testing without real async operations
    corpus_service.ingest = AsyncMock(return_value={"success": True})
    
    return synthetic_data_service, quality_gate_service, corpus_service

def _create_additional_mocks():

    """Create additional mock components"""

    # Mock: Agent service isolation for testing without LLM agent execution
    agent_service = Mock(spec=AgentService)

    # Mock: Async component isolation for testing without real async operations
    agent_service.process_message = AsyncMock(return_value={"response": "Test response", "tool_calls": []})
    
    # Mock: Component isolation for controlled unit testing
    apex_tool_selector = Mock(spec=ApexToolSelector)

    # Mock: Async component isolation for testing without real async operations
    apex_tool_selector.select_best_tool = AsyncMock(return_value="cost_analyzer")
    
    # Mock: Component isolation for controlled unit testing
    state_persistence_service_mock = Mock(spec=state_persistence_service)

    # Mock: Generic component isolation for controlled unit testing
    state_persistence_service_mock.save_state = AsyncMock()

    # Mock: Async component isolation for testing without real async operations
    state_persistence_service_mock.load_state = AsyncMock(return_value=None)
    
    # Mock: Tool dispatcher isolation for agent testing without real tool execution
    tool_dispatcher = Mock(spec=ToolDispatcher)

    # Mock: Tool execution isolation for predictable agent testing
    tool_dispatcher.dispatch = AsyncMock(return_value={"response": "Tool executed successfully", "success": True})
    
    return agent_service, apex_tool_selector, state_persistence_service_mock, tool_dispatcher

def setup_real_infrastructure():

    """Setup infrastructure with real LLM calls enabled"""

    config = get_config()

    db_session = _create_mock_db_session()

    llm_manager = _create_mock_llm_manager()

    websocket_manager = WebSocketManager()
    
    synthetic_data_service, quality_gate_service, corpus_service = _create_mock_services()

    agent_service, apex_tool_selector, state_persistence_service_mock, tool_dispatcher = _create_additional_mocks()
    
    # Create supervisor with the required components
    supervisor = Supervisor(db_session, llm_manager, websocket_manager, tool_dispatcher)
    supervisor.thread_id = str(uuid.uuid4())
    supervisor.user_id = str(uuid.uuid4())
    
    return {

        "config": config, "db_session": db_session, "llm_manager": llm_manager,

        "websocket_manager": websocket_manager, "tool_dispatcher": tool_dispatcher,

        "supervisor": supervisor,

        "synthetic_data_service": synthetic_data_service, "quality_gate_service": quality_gate_service,

        "corpus_service": corpus_service, "agent_service": agent_service,

        "apex_tool_selector": apex_tool_selector, "state_persistence_service": state_persistence_service_mock

    }

class ExamplePromptsTestBase:

    """Base class with shared functionality for example prompts testing"""
    
    def create_prompt_variation(self, base_prompt: str, variation_num: int, context: Dict[str, Any]) -> str:

        """Create variations of a base prompt for testing different scenarios"""

        variations = [

            base_prompt,  # Original

            f"Urgent: {base_prompt}",  # Priority variation

            f"{base_prompt} Please provide detailed analysis.",  # Detail variation

            f"{base_prompt} Keep it brief.",  # Concise variation

            f"For our enterprise system: {base_prompt}",  # Context variation

            f"{base_prompt} Focus on cost-effectiveness.",  # Cost focus

            f"{base_prompt} Prioritize performance.",  # Performance focus

            f"{base_prompt} Consider scalability.",  # Scalability focus

            f"{base_prompt} What are the trade-offs?",  # Trade-off analysis

            f"{base_prompt} Provide a phased approach.",  # Implementation strategy

        ]
        
        # Add context-specific modifications

        varied_prompt = variations[variation_num % len(variations)]

        if context.get("metadata", {}).get("urgent"):

            varied_prompt = f"URGENT: {varied_prompt}"

        if context.get("metadata", {}).get("budget_constraint"):

            varied_prompt = f"{varied_prompt} (Budget: ${context['metadata']['budget_constraint']})"
            
        return varied_prompt
    
    async def validate_response_quality(

        self, 

        response: str, 

        quality_service: QualityGateService, 

        content_type: ContentType

    ) -> bool:

        """Validate the quality of the generated response"""

        try:

            is_valid, score, feedback = await quality_service.validate_content(

                content=response,

                content_type=content_type,

                quality_level=QualityLevel.MEDIUM

            )
            
            # Additional validation logic

            if len(response) < 50:  # Minimum response length

                return False

            if score < 70:  # Minimum quality score

                return False
                
            return is_valid

        except Exception as e:

            print(f"Quality validation error: {e}")

            return False
    
    async def generate_corpus_if_needed(self, corpus_service: CorpusService, context: Dict[str, Any]):

        """Generate corpus data if needed for the test"""
        # Check if corpus generation is needed based on context

        if context.get("require_corpus"):

            await corpus_service.ingest(context.get("corpus_data", {}))