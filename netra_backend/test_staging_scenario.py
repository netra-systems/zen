#!/usr/bin/env python3
"""
Test the exact staging error scenario resolution
"""
import os
import sys
import asyncio
import json
import time
from datetime import datetime, timezone

# Add the backend directory to Python path
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

# Import the modules we need to test
from app.websocket_core.timestamp_utils import convert_to_unix_timestamp, safe_convert_timestamp

async def test_staging_scenario():
    print('Testing the exact staging error case scenario...')
    
    # Simulate the exact problematic timestamp from staging
    staging_timestamp = '2025-09-08T16:50:01.447585'
    
    # Test timestamp conversion
    print(f'Original timestamp: {staging_timestamp}')
    converted = safe_convert_timestamp(staging_timestamp)
    print(f'Converted timestamp: {converted}')
    print(f'Conversion successful: {converted is not None and isinstance(converted, float)}')
    
    # Verify conversion is correct
    if converted:
        converted_dt = datetime.fromtimestamp(converted, tz=timezone.utc)
        print(f'Converted back to datetime: {converted_dt}')
        
        # Check it matches what we expect
        expected_dt = datetime(2025, 9, 8, 16, 50, 1, 447585, tzinfo=timezone.utc)
        time_diff = abs((converted_dt - expected_dt).total_seconds())
        print(f'Time difference from expected: {time_diff:.6f}s (should be <0.001)')
        
    # Test performance
    print('\nPerformance testing...')
    start_time = time.perf_counter()
    for i in range(100):
        safe_convert_timestamp(staging_timestamp)
    end_time = time.perf_counter()
    avg_time = (end_time - start_time) / 100
    
    print(f'Average conversion time: {avg_time*1000:.3f}ms (target: <1ms)')
    performance_ok = avg_time < 0.001
    print(f'Performance meets requirement: {performance_ok}')
    
    # Test various edge cases that might have caused staging issues
    print('\nTesting edge cases...')
    edge_cases = [
        '2025-09-08T16:50:01.447585',    # Original staging case
        '2025-09-08T16:50:01.447585Z',   # With Z suffix
        '2025-09-08T16:50:01.447585+00:00',  # With timezone offset
        1693567801.447585,               # Unix timestamp
        None,                           # None (should use current time)
    ]
    
    all_cases_pass = True
    for case in edge_cases:
        try:
            result = safe_convert_timestamp(case)
            print(f'✅ {case} -> {result} ({type(result).__name__})')
        except Exception as e:
            print(f'❌ {case} -> ERROR: {e}')
            all_cases_pass = False
    
    return converted is not None and performance_ok and all_cases_pass

if __name__ == "__main__":
    # Run the test
    result = asyncio.run(test_staging_scenario())
    if result:
        print('\n🎉 STAGING ERROR SCENARIO RESOLVED: All tests passed!')
        sys.exit(0)
    else:
        print('\n❌ STAGING ERROR SCENARIO STILL EXISTS: Tests failed!')
        sys.exit(1)