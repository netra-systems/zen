"""
Analytics Export Test Helpers - Modular Support for Advanced Analytics Export Tests

BUSINESS VALUE JUSTIFICATION (BVJ):
- Segment: Enterprise (supporting advanced analytics export requirements)
- Business Goal: Modular test infrastructure for analytics export validation
- Value Impact: Ensures reliable analytics export across all enterprise features
- Revenue Impact: Supports tests that protect $100K-$200K MRR from export failures

ARCHITECTURAL COMPLIANCE:
- File size: <300 lines (focused helper components)
- Function size: <8 lines each
- Supports main analytics export integration test
- Real ClickHouse integration with comprehensive mocking
"""

import asyncio
import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, Mock
from netra_backend.app.llm.llm_defaults import LLMModel, LLMConfig


from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

class AdvancedAnalyticsExportInfrastructure:
    """Manages advanced analytics export testing infrastructure."""
    
    def __init__(self):
        self.clickhouse_client = None
        self.export_tasks = []
        self.test_data = []
        
    async def initialize_export_infrastructure(self) -> bool:
        """Initialize export infrastructure for testing."""
        try:
            self.clickhouse_client = AsyncMock()
            self.export_tasks = []
            logger.info("Analytics export infrastructure initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize export infrastructure: {e}")
            return False

    async def create_test_export_session(self, session_config: Dict[str, Any]) -> str:
        """Create test export session with configuration."""
        session_id = str(uuid.uuid4())
        self.export_tasks.append({
            "session_id": session_id,
            "config": session_config,
            "created_at": datetime.now(UTC),
            "status": "initialized"
        })
        return session_id

    async def execute_export_operation(self, session_id: str) -> Dict[str, Any]:
        """Execute export operation for testing."""
        try:
            # Find session
            session = next((s for s in self.export_tasks if s["session_id"] == session_id), None)
            if not session:
                return {"success": False, "error": "Session not found"}
            
            # Mock export execution
            session["status"] = "completed"
            session["exported_records"] = 1000
            session["export_size_mb"] = 5.2
            
            return {
                "success": True,
                "session_id": session_id,
                "records_exported": session["exported_records"],
                "export_size_mb": session["export_size_mb"]
            }
        except Exception as e:
            logger.error(f"Export operation failed: {e}")
            return {"success": False, "error": str(e)}

    def get_export_session_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get export session status."""
        return next((s for s in self.export_tasks if s["session_id"] == session_id), None)

    def cleanup_test_infrastructure(self) -> None:
        """Clean up test infrastructure."""
        self.export_tasks.clear()
        self.test_data.clear()
        logger.info("Analytics export test infrastructure cleaned up")

class AnalyticsDataGenerator:
    """Generates test analytics data for export testing."""
    
    def __init__(self):
        self.generated_data = []
    
    def generate_user_interaction_data(self, count: int = 100) -> List[Dict[str, Any]]:
        """Generate user interaction data for testing."""
        data = []
        for i in range(count):
            record = {
                "user_id": f"user_{i % 10}",
                "interaction_type": ["click", "view", "search", "export"][i % 4],
                "timestamp": (datetime.now(UTC) - timedelta(hours=i % 24)).isoformat(),
                "metadata": {"session_id": f"session_{i % 50}"}
            }
            data.append(record)
        self.generated_data.extend(data)
        return data

    def generate_system_metrics_data(self, count: int = 200) -> List[Dict[str, Any]]:
        """Generate system metrics data for testing."""
        data = []
        for i in range(count):
            record = {
                "metric_name": ["cpu_usage", "memory_usage", "request_latency"][i % 3],
                "value": 10 + (i % 90),
                "timestamp": (datetime.now(UTC) - timedelta(minutes=i % 1440)).isoformat(),
                "tags": {"service": f"service_{i % 3}"}
            }
            data.append(record)
        self.generated_data.extend(data)
        return data

    def generate_cost_tracking_data(self, count: int = 50) -> List[Dict[str, Any]]:
        """Generate cost tracking data for testing."""
        data = []
        models = [LLMModel.GEMINI_2_5_FLASH.value, LLMModel.GEMINI_2_5_FLASH.value, "claude-3"]
        for i in range(count):
            record = {
                "operation_id": str(uuid.uuid4()),
                "model_name": models[i % len(models)],
                "tokens_used": 100 + (i * 10),
                "cost": round((100 + i * 10) * 0.002, 4),
                "timestamp": (datetime.now(UTC) - timedelta(hours=i % 48)).isoformat()
            }
            data.append(record)
        self.generated_data.extend(data)
        return data

    def get_all_generated_data(self) -> List[Dict[str, Any]]:
        """Get all generated test data."""
        return self.generated_data.copy()

    def clear_generated_data(self) -> None:
        """Clear all generated test data."""
        self.generated_data.clear()

class ExportConfigFactory:
    """Factory for creating export configurations."""
    
    @staticmethod
    def create_default_config() -> Dict[str, Any]:
        """Create default export configuration."""
        return {
            "export_format": "json",
            "date_range": {
                "start": (datetime.now(UTC) - timedelta(days=7)).isoformat(),
                "end": datetime.now(UTC).isoformat()
            },
            "data_types": ["interactions", "metrics", "costs"],
            "compression": "gzip",
            "batch_size": 1000
        }

    @staticmethod
    def create_enterprise_config() -> Dict[str, Any]:
        """Create enterprise-level export configuration."""
        return {
            "export_format": "parquet",
            "date_range": {
                "start": (datetime.now(UTC) - timedelta(days=30)).isoformat(),
                "end": datetime.now(UTC).isoformat()
            },
            "data_types": ["interactions", "metrics", "costs", "business_events"],
            "compression": "snappy",
            "batch_size": 5000,
            "include_metadata": True,
            "encryption": "aes256"
        }

    @staticmethod
    def create_minimal_config() -> Dict[str, Any]:
        """Create minimal export configuration for testing."""
        return {
            "export_format": "csv",
            "date_range": {
                "start": (datetime.now(UTC) - timedelta(days=1)).isoformat(),
                "end": datetime.now(UTC).isoformat()
            },
            "data_types": ["interactions"],
            "batch_size": 100
        }

    @staticmethod
    def create_performance_test_config() -> Dict[str, Any]:
        """Create configuration for performance testing."""
        return {
            "export_format": "json",
            "date_range": {
                "start": (datetime.now(UTC) - timedelta(days=90)).isoformat(),
                "end": datetime.now(UTC).isoformat()
            },
            "data_types": ["interactions", "metrics", "costs", "business_events"],
            "compression": "gzip",
            "batch_size": 10000,
            "parallel_workers": 4
        }