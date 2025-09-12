#!/usr/bin/env python3
"""Direct test of corpus admin agent initialization."""

import asyncio
import sys
import os
from shared.isolated_environment import IsolatedEnvironment

# Add the root directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from netra_backend.app.agents.corpus_admin.agent import CorpusAdminSubAgent
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from test_framework.real_llm_config import RealLLMConfig

async def test_corpus_admin_init():
    """Test corpus admin initialization."""
    print("Starting corpus admin initialization test...")
    
    try:
        # Create real LLM config
        print("Creating LLM config...")
        llm_config = RealLLMConfig()
        llm_manager = await llm_config.create_llm_manager()
        print("[U+2713] LLM manager created")
        
        # Create tool dispatcher
        print("Creating tool dispatcher...")
        tool_dispatcher = ToolDispatcher()
        print("[U+2713] Tool dispatcher created")
        
        # Create corpus admin agent
        print("Creating corpus admin agent...")
        corpus_admin_agent = CorpusAdminSubAgent(
            llm_manager=llm_manager,
            tool_dispatcher=tool_dispatcher,
        )
        print("[U+2713] Corpus admin agent created")
        
        # Test basic properties
        print(f"Agent name: {corpus_admin_agent.name}")
        print(f"Agent description: {corpus_admin_agent.description}")
        
        # Test health status
        print("Getting health status...")
        health_status = corpus_admin_agent.get_health_status()
        print(f"Health status: {health_status}")
        
        # Create deep state
        print("Creating deep state...")
        deep_state = DeepAgentState(
            user_request="Create a knowledge base for AI optimization",
            chat_thread_id="test_thread",
            user_id="test_user"
        )
        print("[U+2713] Deep state created")
        
        # Test entry conditions
        print("Testing entry conditions...")
        entry_check = await corpus_admin_agent.check_entry_conditions(
            deep_state, "test_run_001"
        )
        print(f"Entry check result: {entry_check}")
        
        print(" PASS:  All tests completed successfully!")
        return True
        
    except Exception as e:
        print(f" FAIL:  Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_corpus_admin_init())
    sys.exit(0 if result else 1)