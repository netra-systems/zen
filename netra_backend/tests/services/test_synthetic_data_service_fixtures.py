"""
Shared Fixtures for Synthetic Data Service Tests
Common fixtures and mock classes used across all test modules
"""

# Add project root to path
import sys
from pathlib import Path

from tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.corpus_service import CorpusService

# Add project root to path
from app.services.synthetic_data_service import SyntheticDataService
from app.services.websocket.ws_manager import manager as ws_manager

# Add project root to path


# ==================== Mock Classes ====================

class GenerationConfig:
    def __init__(self, **kwargs):
        self.num_traces = kwargs.get('num_traces', 1000)
        self.num_logs = kwargs.get('num_logs', kwargs.get('num_traces', 1000))  # Support both names
        self.workload_distribution = kwargs.get('workload_distribution', {})
        self.time_window_hours = kwargs.get('time_window_hours', 24)
        self.domain_focus = kwargs.get('domain_focus', 'general')
        self.error_rate = kwargs.get('error_rate', 0.01)
        self.corpus_id = kwargs.get('corpus_id', None)
        self.batch_size = kwargs.get('batch_size', 100)
        self.__dict__.update(kwargs)


class ValidationResult:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class IngestionMetrics:
    def __init__(self):
        self.records_processed = 0
        self.backpressure_events = 0
        self.total_records = 0
        self.total_batches = 0
        self.avg_latency_ms = 0
        self.max_latency_ms = 0
        self.min_latency_ms = float('inf')


class ClickHouseService:
    async def query(self, query):
        return []
    async def insert(self, data):
        return True
    async def count_records(self, table):
        return 0


# ==================== Fixtures ====================

@pytest.fixture
def corpus_service():
    return CorpusService()


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.add = MagicMock()
    db.commit = MagicMock()
    db.refresh = MagicMock()
    return db


@pytest.fixture
def mock_clickhouse_client():
    client = AsyncMock()
    client.execute = AsyncMock(return_value=None)
    client.query = AsyncMock(return_value=[])
    return client


@pytest.fixture
def generation_service():
    return SyntheticDataService()


@pytest.fixture
def generation_config():
    return GenerationConfig(
        num_traces=1000,
        workload_distribution={
            "simple_chat": 0.3,
            "tool_use": 0.3,
            "rag_pipeline": 0.2,
            "failed_request": 0.2
        },
        time_window_hours=24,
        domain_focus="e-commerce"
    )


@pytest.fixture
def ingestion_service():
    return SyntheticDataService()


@pytest.fixture
def mock_clickhouse():
    client = AsyncMock()
    client.execute = AsyncMock()
    client.query = AsyncMock()
    return client


@pytest.fixture
def ws_service():
    return ws_manager


@pytest.fixture
def mock_websocket():
    ws = AsyncMock()
    ws.send_json = AsyncMock()
    ws.receive_json = AsyncMock()
    return ws


@pytest.fixture
def validation_service():
    return SyntheticDataService()


@pytest.fixture
def perf_service():
    return SyntheticDataService()


@pytest.fixture
def recovery_service():
    return SyntheticDataService()


@pytest.fixture
def admin_service():
    return SyntheticDataService()


@pytest.fixture
def full_stack():
    """Setup full stack for integration testing"""
    services = {
        "corpus": CorpusService(),
        "generation": SyntheticDataService(),
        "clickhouse": ClickHouseService(),
        "websocket": ws_manager
    }
    return services


@pytest.fixture
def advanced_service():
    return SyntheticDataService()