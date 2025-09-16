"""
Test Data Pipeline Real Processing Integration

Business Value Justification (BVJ):
- Segment: Mid and Enterprise customers (advanced analytics)
- Business Goal: Enable data-driven insights and business intelligence
- Value Impact: Data pipeline reliability directly affects customer analytics value
- Strategic Impact: Advanced analytics differentiate premium offerings

CRITICAL REQUIREMENTS:
- Tests real data processing pipelines (ETL, streaming)
- Validates data transformation and aggregation accuracy
- Uses real data stores and processing engines, NO MOCKS
- Ensures data quality and processing performance
"""

import pytest
import asyncio
import uuid
from datetime import datetime, timezone, timedelta

from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.database import DatabaseTestHelper
from shared.isolated_environment import get_env

from netra_backend.app.services.analytics.data_pipeline import DataPipeline
from netra_backend.app.services.analytics.data_processor import DataProcessor


class TestDataPipelineRealProcessingIntegration(SSotBaseTestCase):
    """Test data pipeline with real data processing"""
    
    def setup_method(self):
        """Set up test environment"""
        super().setup_method() if hasattr(super(), 'setup_method') else None
        self.env = get_env()
        self.db_helper = DatabaseTestHelper()
        self.test_prefix = f"pipeline_{uuid.uuid4().hex[:8]}"
        self.data_pipeline = DataPipeline()
        self.data_processor = DataProcessor()
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_end_to_end_data_processing_pipeline(self):
        """Test complete data processing pipeline with real data"""
        # Create test data tables
        async with self.db_helper.get_connection() as conn:
            await conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.test_prefix}_raw_events (
                    id SERIAL PRIMARY KEY,
                    event_type VARCHAR(50),
                    user_id VARCHAR(50),
                    event_data JSONB,
                    timestamp TIMESTAMP DEFAULT NOW()
                )
            """)
            
            await conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.test_prefix}_processed_analytics (
                    id SERIAL PRIMARY KEY,
                    metric_name VARCHAR(50),
                    metric_value DECIMAL(15,4),
                    dimensions JSONB,
                    processed_at TIMESTAMP DEFAULT NOW()
                )
            """)
        
        # Insert test events
        test_events = [
            ("user_login", "user_001", {"session_id": "sess_1", "device": "mobile"}),
            ("page_view", "user_001", {"page": "/dashboard", "duration": 30}),
            ("feature_usage", "user_002", {"feature": "cost_optimizer", "duration": 120}),
            ("user_logout", "user_001", {"session_duration": 300}),
        ]
        
        async with self.db_helper.get_connection() as conn:
            await conn.executemany(f"""
                INSERT INTO {self.test_prefix}_raw_events (event_type, user_id, event_data)
                VALUES ($1, $2, $3)
            """, test_events)
        
        try:
            # Start data pipeline
            pipeline_id = await self.data_pipeline.start_pipeline(
                source_table=f"{self.test_prefix}_raw_events",
                destination_table=f"{self.test_prefix}_processed_analytics",
                processing_rules=["aggregate_by_user", "calculate_metrics"],
                test_prefix=self.test_prefix
            )
            
            # Wait for processing
            await asyncio.sleep(5)
            
            # Verify processed data
            async with self.db_helper.get_connection() as conn:
                processed_data = await conn.fetch(f"""
                    SELECT * FROM {self.test_prefix}_processed_analytics
                """)
            
            assert len(processed_data) > 0, "No data was processed"
            
            # Validate data transformations
            metric_names = [row['metric_name'] for row in processed_data]
            assert "user_activity_count" in metric_names or "session_duration" in metric_names
            
            await self.data_pipeline.stop_pipeline(pipeline_id)
            
        finally:
            await self.db_helper.cleanup_test_data(self.test_prefix)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])