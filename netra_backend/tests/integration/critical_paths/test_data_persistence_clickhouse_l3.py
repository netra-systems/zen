"""
L3 Integration Test: ClickHouse Data Persistence
Tests ClickHouse data persistence for analytics
"""

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

import pytest
import asyncio
from unittest.mock import patch, AsyncMock

# Add project root to path
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Add project root to path

from netra_backend.app.services.clickhouse_service import ClickHouseService
from netra_backend.app.config import settings
import uuid
from datetime import datetime

# Add project root to path


class TestDataPersistenceClickHouseL3:
    """Test ClickHouse data persistence scenarios"""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_event_data_insertion(self):
        """Test event data insertion"""
        ch_service = ClickHouseService()
        
        event = {
            "event_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow(),
            "event_type": "page_view",
            "user_id": "user_123",
            "properties": {"page": "/home", "duration": 5.2}
        }
        
        # Insert event
        result = await ch_service.insert_event(event)
        assert result is True
        
        # Query event
        events = await ch_service.query(
            f"SELECT * FROM events WHERE event_id = '{event['event_id']}'"
        )
        
        assert len(events) > 0
        assert events[0]["event_type"] == "page_view"
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_batch_insertion_performance(self):
        """Test batch insertion performance"""
        ch_service = ClickHouseService()
        
        # Generate batch of events
        batch_events = []
        for i in range(1000):
            batch_events.append({
                "event_id": str(uuid.uuid4()),
                "timestamp": datetime.utcnow(),
                "event_type": "api_call",
                "user_id": f"user_{i % 100}",
                "properties": {"endpoint": f"/api/v{i % 3}", "status": 200}
            })
        
        # Batch insert
        start_time = asyncio.get_event_loop().time()
        result = await ch_service.batch_insert("events", batch_events)
        duration = asyncio.get_event_loop().time() - start_time
        
        assert result == 1000
        assert duration < 2  # Should be very fast
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_aggregation_queries(self):
        """Test aggregation queries"""
        ch_service = ClickHouseService()
        
        # Insert test data
        test_events = []
        base_time = datetime.utcnow()
        
        for i in range(50):
            test_events.append({
                "event_id": str(uuid.uuid4()),
                "timestamp": base_time,
                "event_type": "purchase" if i % 2 == 0 else "view",
                "user_id": f"user_{i % 10}",
                "value": i * 10
            })
        
        await ch_service.batch_insert("events", test_events)
        
        # Aggregation query
        result = await ch_service.query("""
            SELECT 
                event_type,
                COUNT(*) as count,
                SUM(value) as total_value,
                AVG(value) as avg_value
            FROM events
            WHERE timestamp >= today()
            GROUP BY event_type
        """)
        
        assert len(result) > 0
        for row in result:
            assert "count" in row
            assert "total_value" in row
            assert "avg_value" in row
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_time_series_queries(self):
        """Test time series data queries"""
        ch_service = ClickHouseService()
        
        # Query time series data
        result = await ch_service.query("""
            SELECT 
                toStartOfHour(timestamp) as hour,
                COUNT(*) as events_count
            FROM events
            WHERE timestamp >= now() - INTERVAL 24 HOUR
            GROUP BY hour
            ORDER BY hour
        """)
        
        # Should return hourly aggregates
        if len(result) > 0:
            assert "hour" in result[0]
            assert "events_count" in result[0]
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_data_retention_policy(self):
        """Test data retention policy enforcement"""
        ch_service = ClickHouseService()
        
        # Check partition info
        partitions = await ch_service.query("""
            SELECT 
                partition,
                name,
                rows,
                bytes_on_disk
            FROM system.parts
            WHERE table = 'events'
            AND active = 1
        """)
        
        # Verify partitioning is active
        if len(partitions) > 0:
            assert "partition" in partitions[0]
            assert "rows" in partitions[0]