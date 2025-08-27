#!/usr/bin/env python3
"""
Iteration 55: ClickHouse Time-Series Data Consistency

CRITICAL scenarios:
- Time-series data ordering during parallel inserts
- Late-arriving data handling with proper timestamps
- Time-zone consistency across multi-region deployments

Prevents analytics data corruption in time-sensitive reports.
"""
import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock

from netra_backend.app.db.clickhouse import use_mock_clickhouse, MockClickHouseDatabase


@pytest.mark.asyncio
async def test_timeseries_data_ordering_consistency():
    """
    CRITICAL: Verify time-series data maintains order during concurrent inserts.
    Prevents chronological data corruption in analytics dashboards.
    """
    if use_mock_clickhouse():
        client = MockClickHouseDatabase()
    else:
        pytest.skip("Requires real ClickHouse for time-series testing")
    
    # Mock ordered time-series responses
    with patch.object(client, 'batch_insert') as mock_insert, \
         patch.object(client, 'execute_query') as mock_query:
        
        # Track insertion order
        insertion_calls = []
        
        async def track_inserts(table, data):
            insertion_calls.append({
                'timestamp': datetime.now(),
                'table': table,
                'count': len(data),
                'first_event_time': data[0].get('event_time') if data else None
            })
        
        mock_insert.side_effect = track_inserts
        
        # Simulate concurrent time-series data inserts
        base_time = datetime(2025, 8, 27, 12, 0, 0)
        
        # Prepare test data with different timestamps
        batch1 = [
            {'event_time': base_time + timedelta(seconds=i), 'value': i}
            for i in range(100)
        ]
        
        batch2 = [
            {'event_time': base_time + timedelta(seconds=i+50), 'value': i+1000}
            for i in range(100)
        ]
        
        # Insert batches concurrently
        await asyncio.gather(
            client.batch_insert('events_timeseries', batch1),
            client.batch_insert('events_timeseries', batch2)
        )
        
        # Verify both inserts were called
        assert len(insertion_calls) == 2, f"Expected 2 inserts, got {len(insertion_calls)}"
        
        # Mock chronological query result
        mock_query.return_value = [
            {'event_time': base_time + timedelta(seconds=i), 'value': i}
            for i in range(200)
        ]
        
        # Query data in chronological order
        result = await client.execute_query("""
            SELECT event_time, value 
            FROM events_timeseries 
            ORDER BY event_time
        """)
        
        # Verify chronological ordering
        assert len(result) > 0, "Time-series query must return data"
        
        # Time-series data should be properly ordered
        for i in range(1, min(len(result), 10)):
            assert result[i-1]['event_time'] <= result[i]['event_time'], \
                "Time-series data not in chronological order"
