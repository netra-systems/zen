#!/usr/bin/env python3
"""Debug script for ReportingSubAgent golden pattern test issues."""

import sys
sys.path.insert(0, '.')

# Test basic imports
try:
    from netra_backend.app.agents.reporting_sub_agent import ReportingSubAgent
    print("[OK] ReportingSubAgent import successful")
except Exception as e:
    print(f"[ERROR] ReportingSubAgent import failed: {e}")
    sys.exit(1)

try:
    from netra_backend.app.agents.base_agent import BaseAgent
    print("[OK] BaseAgent import successful")
except Exception as e:
    print(f"[ERROR] BaseAgent import failed: {e}")

# Test agent instantiation
try:
    agent = ReportingSubAgent()
    print("[OK] ReportingSubAgent instantiation successful")
    print(f"   - Name: {agent.name}")
    print(f"   - Description: {agent.description[:50]}...")
    print(f"   - Is BaseAgent: {isinstance(agent, BaseAgent)}")
    print(f"   - Has logger: {hasattr(agent, 'logger')}")
    print(f"   - Has emit_thinking: {hasattr(agent, 'emit_thinking')}")
    print(f"   - Has emit_progress: {hasattr(agent, 'emit_progress')}")
    print(f"   - Has websocket adapter: {hasattr(agent, '_websocket_adapter')}")
except Exception as e:
    print(f"[ERROR] ReportingSubAgent instantiation failed: {e}")
    import traceback
    traceback.print_exc()

# Test the test fixture approach
print("\n=== Testing Test Fixture Approach ===")
from unittest.mock import Mock
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher

try:
    # This is how the test tries to create the agent
    mock_llm = Mock(spec=LLMManager)
    mock_dispatcher = Mock(spec=ToolDispatcher)
    
    # The test fixture tries to pass these parameters
    agent_with_params = ReportingSubAgent(
        llm_manager=mock_llm,
        tool_dispatcher=mock_dispatcher
    )
    print("[ERROR] This should have failed - constructor doesn't accept parameters")
except TypeError as e:
    print(f"[OK] Expected TypeError: {e}")
except Exception as e:
    print(f"[ERROR] Unexpected error: {e}")

print("\n=== Testing Actual Dependencies ===")
try:
    agent = ReportingSubAgent()
    # Check if the agent has the dependencies it needs
    print(f"   - Has llm_manager: {hasattr(agent, 'llm_manager')}")
    print(f"   - Has tool_dispatcher: {hasattr(agent, 'tool_dispatcher')}")
    
    # Check BaseAgent infrastructure
    print(f"   - Has reliability manager: {hasattr(agent, '_unified_reliability_handler')}")
    print(f"   - Has execution engine: {hasattr(agent, '_execution_engine')}")
    print(f"   - Has timing collector: {hasattr(agent, 'timing_collector')}")
    
    # Check methods required by tests
    required_methods = [
        'validate_preconditions', 'execute_core_logic', 'emit_thinking', 
        'emit_progress', 'emit_agent_completed', 'emit_error',
        'set_websocket_bridge', 'has_websocket_context'
    ]
    
    for method in required_methods:
        has_method = hasattr(agent, method)
        print(f"   - Has {method}: {has_method}")
        
except Exception as e:
    print(f"[ERROR] Error checking agent: {e}")
    import traceback
    traceback.print_exc()