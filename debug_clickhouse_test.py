#!/usr/bin/env python3
"""Debug script to isolate ClickHouse performance test issue"""

import asyncio
import sys
import time
from pathlib import Path

# Add netra_backend to path
sys.path.insert(0, str(Path(__file__).parent / "netra_backend"))

async def debug_clickhouse_client():
    """Debug ClickHouse client creation and basic operations"""
    try:
        # Set up test environment similar to pytest
        import os
        os.environ["TESTING"] = "1"
        os.environ["NETRA_ENV"] = "testing"
        os.environ["ENVIRONMENT"] = "testing"
        os.environ["DEV_MODE_DISABLE_CLICKHOUSE"] = "true"
        os.environ["CLICKHOUSE_ENABLED"] = "false"
        
        print("Environment setup complete")
        print(f"TESTING: {os.environ.get('TESTING')}")
        print(f"DEV_MODE_DISABLE_CLICKHOUSE: {os.environ.get('DEV_MODE_DISABLE_CLICKHOUSE')}")
        print(f"CLICKHOUSE_ENABLED: {os.environ.get('CLICKHOUSE_ENABLED')}")
        
        # Import after environment setup
        from netra_backend.app.database import get_clickhouse_client
        from netra_backend.app.db.clickhouse_init import create_workload_events_table_if_missing
        
        print("\nTesting ClickHouse client creation...")
        start_time = time.time()
        
        # This is what the performance test does
        async with get_clickhouse_client() as client:
            creation_time = time.time() - start_time
            print(f"Client created in {creation_time:.2f} seconds")
            print(f"Client type: {type(client)}")
            
            # Check if it's mock
            if hasattr(client, 'is_mock'):
                print(f"Is mock client: {client.is_mock}")
            
            # Test table creation (what the test does next)
            print("\nTesting table creation...")
            table_start = time.time()
            await create_workload_events_table_if_missing()
            table_time = time.time() - table_start
            print(f"Table creation took {table_time:.2f} seconds")
            
            # Test a simple query
            print("\nTesting simple query...")
            query_start = time.time()
            result = await client.execute_query("SELECT 1")
            query_time = time.time() - query_start
            print(f"Simple query took {query_time:.2f} seconds")
            print(f"Result: {result}")
        
        print("\nAll operations completed successfully!")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

async def debug_batch_insert():
    """Debug the specific batch insert operation that's timing out"""
    import os
    os.environ["TESTING"] = "1"
    os.environ["NETRA_ENV"] = "testing"  
    os.environ["ENVIRONMENT"] = "testing"
    os.environ["DEV_MODE_DISABLE_CLICKHOUSE"] = "true"
    os.environ["CLICKHOUSE_ENABLED"] = "false"
    
    from netra_backend.app.database import get_clickhouse_client
    
    print("Testing batch insert operation...")
    
    async with get_clickhouse_client() as client:
        print(f"Client type: {type(client)}")
        
        # Create small test data (like the performance test does)
        events = []
        for i in range(5):  # Much smaller batch for debugging
            events.append([
                f"trace_{i}",
                f"span_{i}", 
                f"user_{i}",
                f"session_{i}",
                "2024-08-29 10:00:00",
                "simple_chat",
                "completed",
                100,
                ["latency_ms"],
                [50.0],
                ["ms"],
                f"input {i}",
                f"output {i}",
                '{"test": true}'
            ])
        
        column_names = [
            'trace_id', 'span_id', 'user_id', 'session_id', 'timestamp',
            'workload_type', 'status', 'duration_ms',
            'metrics.name', 'metrics.value', 'metrics.unit',
            'input_text', 'output_text', 'metadata'
        ]
        
        print(f"Attempting to insert {len(events)} events...")
        print(f"Column names: {column_names}")
        
        start_time = time.time()
        
        # This is the exact operation that's timing out
        if hasattr(client, 'base_client'):
            base_client = client.base_client
        else:
            base_client = client
        
        print(f"Base client type: {type(base_client)}")
        
        # The problematic call
        await base_client.insert_data('workload_events', events, column_names=column_names)
        
        insert_time = time.time() - start_time
        print(f"Insert took {insert_time:.2f} seconds")

if __name__ == "__main__":
    print("=== ClickHouse Client Debug ===")
    result = asyncio.run(debug_clickhouse_client())
    
    print("\n=== Batch Insert Debug ===") 
    try:
        asyncio.run(debug_batch_insert())
    except Exception as e:
        print(f"Batch insert failed: {e}")
        import traceback
        traceback.print_exc()
    
    sys.exit(result)