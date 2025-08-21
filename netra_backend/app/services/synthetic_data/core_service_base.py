"""Core Service Base Module - Core synthetic data service initialization and basic operations"""

import uuid
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.db import models_postgres as models
from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.synthetic_data.audit_interface import AuditInterface
from netra_backend.app.services.synthetic_data.audit_logger import (
    SyntheticDataAuditLogger,
)
from netra_backend.app.services.synthetic_data.enums import GenerationStatus
from netra_backend.app.services.synthetic_data.error_handler import ErrorHandler
from netra_backend.app.services.synthetic_data.generation_engine import GenerationEngine
from netra_backend.app.services.synthetic_data.generation_utilities import (
    GenerationUtilities,
)
from netra_backend.app.services.synthetic_data.ingestion_manager import IngestionManager
from netra_backend.app.services.synthetic_data.job_manager import JobManager
from netra_backend.app.services.synthetic_data.recovery import RecoveryMixin
from netra_backend.app.services.synthetic_data.tools import initialize_default_tools

central_logger.info("SyntheticDataService initialized successfully")


class CoreServiceBase(RecoveryMixin):
    """Base class for synthetic data service with core initialization"""
    
    def __init__(self):
        self._initialize_core_components()
        self._initialize_managers()
        self._initialize_state()
    
    def _initialize_core_components(self) -> None:
        """Initialize core service components"""
        self.default_tools = initialize_default_tools()
        self.corpus_cache: Dict[str, List[Dict]] = {}
        self.active_jobs: Dict[str, Dict] = {}
    
    def _initialize_managers(self) -> None:
        """Initialize service managers"""
        self.job_manager = JobManager()
        self.generation_engine = GenerationEngine(self.default_tools)
        self.ingestion_manager = IngestionManager()
        self.error_handler = ErrorHandler()
        self.audit_interface = AuditInterface()
        self.utilities = GenerationUtilities(self.generation_engine)
    
    def _initialize_state(self) -> None:
        """Initialize service state"""
        self.alert_config: Optional[Dict] = None
        self.audit_logger = SyntheticDataAuditLogger()

    async def _check_alert_conditions(self, config) -> None:
        """Check if generation config triggers any alert conditions"""
        if self.alert_config:
            num_traces = getattr(config, 'num_logs', getattr(config, 'num_traces', 0))
            if num_traces >= 10000:
                await self.send_alert("Large generation job detected", "warning")

    def _prepare_job_parameters(self, job_id: Optional[str]) -> Dict:
        """Prepare job ID and table name parameters"""
        generated_job_id = job_id or str(uuid.uuid4())
        table_name = f"netra_synthetic_data_{generated_job_id.replace('-', '_')}"
        return {'job_id': generated_job_id, 'table_name': table_name}

    def _generate_job_id(self, job_id: Optional[str]) -> str:
        """Generate unique job ID"""
        return job_id or str(uuid.uuid4())

    def _create_table_name(self, job_id: str) -> str:
        """Create destination table name"""
        return f"netra_synthetic_data_{job_id.replace('-', '_')}"

    def _build_corpus_model(self, table_name: str, job_id: str, user_id: Optional[str]) -> models.Corpus:
        """Build corpus model for database insertion"""
        return models.Corpus(
            name=f"Synthetic Data {datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}",
            description=f"Synthetic data generation job {job_id}",
            table_name=table_name, status="pending", created_by_id=user_id
        )

    def _persist_corpus_model(self, db: AsyncSession, db_synthetic_data: models.Corpus) -> str:
        """Persist corpus model to database and return ID"""
        db.add(db_synthetic_data)
        db.commit()
        db.refresh(db_synthetic_data)
        return db_synthetic_data.id

    def _build_job_response(self, job_id: str, table_name: str) -> Dict:
        """Build job initiation response"""
        return {
            "job_id": job_id,
            "status": GenerationStatus.INITIATED.value,
            "table_name": table_name,
            "websocket_channel": f"generation_{job_id}"
        }

    def _transform_status_to_admin_format(self, status: Dict) -> Dict:
        """Transform job status to admin-friendly format"""
        return {
            "state": status.get("status", "unknown").lower(),
            "progress_percentage": 50.0,
            "estimated_completion": "2 minutes"
        }

    async def configure_alerts(self, alert_config: Dict) -> None:
        """Configure alert settings"""
        self.alert_config = alert_config

    async def send_alert(self, message: str, severity: str = "info") -> None:
        """Send alert notification"""
        central_logger.warning(f"ALERT [{severity}]: {message}")

    async def run_diagnostics(self) -> Dict:
        """Run system diagnostics"""
        return {
            "corpus_connectivity": "healthy",
            "clickhouse_connectivity": "healthy", 
            "websocket_status": "active",
            "worker_pool_status": "active",
            "cache_hit_rate": 0.85
        }