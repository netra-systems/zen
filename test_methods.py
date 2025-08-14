#!/usr/bin/env python3

"""Simple test script to verify the added methods work."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

try:
    from app.agents.data_sub_agent.agent import DataSubAgent
    import asyncio
    from unittest.mock import Mock, AsyncMock
    
    print("SUCCESS: DataSubAgent imported successfully")
    
    # Create instance with mocked dependencies
    mock_llm_manager = Mock()
    mock_tool_dispatcher = Mock()
    
    agent = DataSubAgent(mock_llm_manager, mock_tool_dispatcher)
    print("SUCCESS: DataSubAgent instantiated successfully")
    
    async def test_methods():
        # Test handle_supervisor_request
        print("\n=== Testing handle_supervisor_request ===")
        callback = AsyncMock()
        request = {
            "action": "process_data",
            "data": {"content": "supervisor data"},
            "callback": callback
        }
        
        result = await agent.handle_supervisor_request(request)
        print(f"Result: {result}")
        assert result["status"] == "completed", f"Expected 'completed', got {result['status']}"
        callback.assert_called_once()
        print("SUCCESS: handle_supervisor_request test passed!")
        
        # Test _analyze_performance
        print("\n=== Testing _analyze_performance ===")
        test_data = [
            {"value": 10.0},
            {"value": 20.0},
            {"value": 30.0}
        ]
        
        result = await agent._analyze_performance(test_data, "latency_ms")
        print(f"Result: {result}")
        assert "average" in result, f"Expected 'average' in result, got {result}"
        assert result["average"] == 20.0, f"Expected average 20.0, got {result['average']}"
        assert result["data_points"] == 3, f"Expected 3 data points, got {result['data_points']}"
        print("SUCCESS: _analyze_performance test passed!")
        
        # Test with insufficient data
        print("\n=== Testing _analyze_performance with insufficient data ===")
        insufficient_data = [{"value": 10.0}]
        result = await agent._analyze_performance(insufficient_data, "latency_ms")
        print(f"Result: {result}")
        assert result["status"] == "insufficient_data", f"Expected 'insufficient_data', got {result['status']}"
        print("SUCCESS: _analyze_performance insufficient data test passed!")
        
        print("\n=== ALL TESTS PASSED! ===")
    
    # Run the async tests
    asyncio.run(test_methods())
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()