"""
Realistic ClickHouse Test Fixtures
Provides production-like test data for ClickHouse testing
"""

import pytest

from netra_backend.tests.clickhouse.data_generator import RealisticDataGenerator
from netra_backend.tests.test_data_manager import ClickHouseTestData

# Pytest fixtures
@pytest.fixture
async def clickhouse_test_data():
    """Provide test data manager"""
    yield ClickHouseTestData()

@pytest.fixture
async def realistic_llm_events():
    """Generate realistic LLM events"""
    generator = RealisticDataGenerator()
    yield generator.generate_llm_events(100)

@pytest.fixture
async def realistic_workload_metrics():
    """Generate realistic workload metrics"""
    generator = RealisticDataGenerator()
    yield generator.generate_workload_metrics(100)

@pytest.fixture
async def realistic_logs():
    """Generate realistic log entries"""
    generator = RealisticDataGenerator()
    yield generator.generate_log_entries(1000)

@pytest.fixture
async def realistic_corpus():
    """Generate realistic corpus data"""
    generator = RealisticDataGenerator()
    yield generator.generate_corpus_data(50)

@pytest.fixture
async def data_generator():
    """Provide data generator instance"""
    yield RealisticDataGenerator(seed=42)