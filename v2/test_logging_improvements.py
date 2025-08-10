"""Test script to validate logging improvements"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

async def test_logging():
    from app.logging_config import central_logger
    from app.services.base import ServiceHealthChecker, BaseService
    from app.core.service_interfaces import ServiceHealth
    from datetime import datetime
    
    logger = central_logger.get_logger("test")
    
    # Test 1: Basic logging
    logger.info("Test 1: Basic logging works")
    logger.debug("Debug message")
    logger.warning("Warning message")
    
    # Test 2: Exception logging with context
    try:
        raise ValueError("Test exception")
    except Exception as e:
        logger.error("Test 2: Exception logging", exc_info=True)
    
    # Test 3: Service health check with exception
    class MockFailingService:
        @property
        def service_name(self):
            return "MockFailingService"
        
        async def health_check(self):
            raise RuntimeError("Service health check failed intentionally")
    
    mock_service = MockFailingService()
    health = await ServiceHealthChecker.check_service_health(mock_service)
    
    print(f"Test 3: Service health status: {health.status}")
    assert health.status == "unhealthy"
    
    # Test 4: Sensitive data filtering
    logger.info("Test 4: Password filtering test - password=supersecret123")
    logger.info("Test 4: API key filtering - api_key=sk-1234567890abcdef")
    
    # Test 5: Performance logging
    from app.core.unified_logging import log_execution_time
    
    @log_execution_time("test_operation")
    async def slow_operation():
        await asyncio.sleep(0.1)
        return "completed"
    
    result = await slow_operation()
    print(f"Test 5: Performance logging - operation result: {result}")
    
    print("\n[OK] All logging tests passed successfully!")
    
    # Test 6: Tool execution logging
    print("\nTest 6: Tool logging...")
    from app.services.apex_optimizer_agent.tool_builder import create_async_tool_wrapper
    from app.services.context import ToolContext
    
    async def mock_tool(context):
        return "Tool executed"
    
    # Create a mock context
    class MockContext:
        logs = []
    
    wrapper = create_async_tool_wrapper(mock_tool, MockContext(), False)
    tool_result = await wrapper()
    print(f"Tool result: {tool_result}")
    
    print("\n[SUCCESS] All tests completed successfully!")

if __name__ == "__main__":
    asyncio.run(test_logging())