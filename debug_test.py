"""Debug test to understand the async mock issue"""

import asyncio
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncEngine

async def debug_test():
    from netra_backend.app.services.schema_validation_service import SchemaValidationService
    
    # Create mock engine
    mock_engine = MagicMock(spec=AsyncEngine)
    mock_conn = AsyncMock()
    
    # Create a mock result where scalar() is NOT async
    mock_result = MagicMock()  # Use MagicMock instead of AsyncMock
    mock_result.scalar.return_value = 1
    
    print("Setting up mock...")
    
    # Method 1: Assigning AsyncMock
    mock_conn.execute = AsyncMock(return_value=mock_result)
    
    # Mock the context manager properly
    mock_engine.connect.return_value.__aenter__.return_value = mock_conn
    mock_engine.connect.return_value.__aexit__.return_value = None
    
    print("About to call check_database_connectivity...")
    
    try:
        result = await SchemaValidationService.check_database_connectivity(mock_engine)
        print(f"Result: {result}")
        print(f"Type of result: {type(result)}")
        print("Execute called?", mock_conn.execute.called)
        print("Execute call count:", mock_conn.execute.call_count)
        
        if mock_conn.execute.called:
            print("Execute call args:", mock_conn.execute.call_args)
            
        # Debug the mock result chain
        print(f"mock_result: {mock_result}")
        print(f"mock_result.scalar: {mock_result.scalar}")
        print(f"mock_result.scalar(): {mock_result.scalar()}")
        print(f"mock_result.scalar() == 1: {mock_result.scalar() == 1}")
        
    except Exception as e:
        print(f"Error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_test())