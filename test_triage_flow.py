"""Test script to verify triage agent flow with example prompts"""

import asyncio
import json
import time
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, Mock

# Add path for imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "netra_backend"))

from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.triage_sub_agent.agent import TriageSubAgent
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.redis_manager import RedisManager

# Example prompts based on the triage_prompts.py template
EXAMPLE_PROMPTS = [
    "Optimize my GPT-4 costs by 30% while maintaining latency under 100ms",
    "Our chatbot uses a large LLM to provide helpful responses, but costs are rising fast with usage growth. How can we maintain response quality while reducing LLM invocation?",
    "We use RAG to synthesize information from many source documents. Searches and LLM calls are getting expensive. How can we optimize recall-quality trade-off?",
    "Our AI-powered news summarization platform needs to reduce LLM expenditure by 30% while keeping summarization coherence above acceptance thresholds",
    "False positives from our LLM-based transaction fraud classifier are spiking customer friction. Can we refine the model to reject fewer legitimate transactions?",
    "We're expanding our medical LLM across 5 new specialties with <500ms inference latency at 100 concurrent requests"
]

EXPECTED_TRIAGE_RESPONSE = {
    "category": "Cost Optimization",
    "secondary_categories": ["Performance Optimization"],
    "priority": "high",
    "key_parameters": {
        "workload_type": "inference",
        "optimization_focus": "cost",
        "time_sensitivity": "short-term",
        "scope": "specific-model"
    },
    "extracted_entities": {
        "models_mentioned": ["GPT-4"],
        "metrics_mentioned": ["30% cost reduction", "100ms latency"],
        "constraints_mentioned": ["maintain latency under 100ms"]
    },
    "requires_data_gathering": True,
    "suggested_tools": ["cost_analyzer", "performance_profiler"]
}

def create_mock_llm_manager():
    """Create a mock LLM manager that simulates triage responses"""
    mock = Mock(spec=LLMManager)
    
    # Simulate the LLM returning a proper JSON response
    async def mock_ask_llm(prompt, **kwargs):
        print(f"\n[LLM CALL] Prompt length: {len(prompt)} chars")
        print(f"[LLM CALL] First 200 chars: {prompt[:200]}...")
        return json.dumps(EXPECTED_TRIAGE_RESPONSE)
    
    mock.ask_llm = AsyncMock(side_effect=mock_ask_llm)
    
    # Mock structured LLM to simulate fallback scenario
    mock.ask_structured_llm = AsyncMock(side_effect=Exception("Structured generation not available"))
    
    return mock

def create_mock_tool_dispatcher():
    """Create a mock tool dispatcher"""
    return Mock(spec=ToolDispatcher)

def create_mock_redis_manager():
    """Create a mock Redis manager"""
    mock = Mock(spec=RedisManager)
    mock.get = AsyncMock(return_value=None)  # No cache hits
    mock.set = AsyncMock(return_value=True)
    return mock

async def test_single_prompt(prompt: str, agent: TriageSubAgent) -> Dict[str, Any]:
    """Test a single prompt through the triage agent"""
    print(f"\n{'='*60}")
    print(f"Testing prompt: {prompt[:100]}...")
    print(f"{'='*60}")
    
    # Create state
    state = DeepAgentState(user_request=prompt)
    run_id = f"test_run_{int(time.time())}"
    
    # Check entry conditions
    print("[STEP 1] Checking entry conditions...")
    can_execute = await agent.check_entry_conditions(state, run_id)
    print(f"  Can execute: {can_execute}")
    
    if not can_execute:
        print("  ERROR: Entry conditions not met!")
        return {"error": "Entry conditions not met"}
    
    # Execute triage
    print("[STEP 2] Executing triage workflow...")
    start_time = time.time()
    
    try:
        await agent.execute(state, run_id, stream_updates=False)
        elapsed_time = time.time() - start_time
        print(f"  Execution completed in {elapsed_time:.2f}s")
        
        # Check results
        if hasattr(state, 'triage_result') and state.triage_result:
            print("[STEP 3] Triage Result:")
            result = state.triage_result
            if isinstance(result, dict):
                print(f"  Category: {result.get('category', 'N/A')}")
                print(f"  Priority: {result.get('priority', 'N/A')}")
                print(f"  Requires data gathering: {result.get('requires_data_gathering', False)}")
                return result
            else:
                print(f"  Result type: {type(result)}")
                return {"result": str(result)}
        else:
            print("  ERROR: No triage result in state!")
            return {"error": "No triage result"}
            
    except Exception as e:
        elapsed_time = time.time() - start_time
        print(f"  ERROR after {elapsed_time:.2f}s: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}

async def main():
    """Main test function"""
    print("Starting Triage Agent Flow Test")
    print("================================\n")
    
    # Create mocked dependencies
    llm_manager = create_mock_llm_manager()
    tool_dispatcher = create_mock_tool_dispatcher()
    redis_manager = create_mock_redis_manager()
    
    # Create agent
    print("Creating TriageSubAgent with mocked dependencies...")
    agent = TriageSubAgent(llm_manager, tool_dispatcher, redis_manager)
    print(f"Agent created: {agent.name}")
    print(f"Cache TTL: {agent.cache_ttl}s")
    print(f"Max retries: {agent.max_retries}")
    
    # Test each prompt
    results = []
    for i, prompt in enumerate(EXAMPLE_PROMPTS, 1):
        print(f"\n\nTest {i}/{len(EXAMPLE_PROMPTS)}")
        result = await test_single_prompt(prompt, agent)
        results.append({
            "prompt": prompt[:50] + "...",
            "result": result
        })
        
        # Small delay between tests
        await asyncio.sleep(0.5)
    
    # Summary
    print("\n\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    successful = sum(1 for r in results if "error" not in r["result"])
    print(f"Successful: {successful}/{len(results)}")
    
    for i, result in enumerate(results, 1):
        status = "✓" if "error" not in result["result"] else "✗"
        print(f"{status} Test {i}: {result['prompt']}")
        if "error" in result["result"]:
            print(f"    Error: {result['result']['error']}")
    
    print("\nTest completed!")

if __name__ == "__main__":
    asyncio.run(main())