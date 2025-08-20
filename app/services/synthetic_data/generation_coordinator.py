"""Generation Coordinator Module - Manages generation workflows and execution"""

import asyncio
from typing import Dict, List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.clickhouse import get_clickhouse_client
from app.logging_config import central_logger
from .core_service_base import CoreServiceBase


class GenerationCoordinator(CoreServiceBase):
    """Coordinates generation workflows and execution"""

    async def execute_generation_workflow(
        self,
        job_id: str,
        config,
        corpus_id: Optional[str],
        db: Optional[AsyncSession],
        synthetic_data_id: Optional[str]
    ) -> None:
        """Execute complete generation workflow"""
        try:
            await self._run_generation_pipeline(
                job_id, config, corpus_id, db, synthetic_data_id
            )
        except Exception as e:
            await self.error_handler.handle_generation_error(
                job_id, e, db, synthetic_data_id, self.active_jobs
            )

    async def _run_generation_pipeline(
        self,
        job_id: str,
        config,
        corpus_id: Optional[str],
        db: Optional[AsyncSession],
        synthetic_data_id: Optional[str]
    ) -> None:
        """Run the generation pipeline"""
        await self.job_manager.start_job(job_id, self.active_jobs)
        corpus_content = await self._prepare_generation_environment(job_id, corpus_id, db)
        await self.generation_engine.execute_batch_generation(
            job_id, config, corpus_content, self.active_jobs, self.ingestion_manager
        )
        await self.job_manager.complete_job(job_id, self.active_jobs, db, synthetic_data_id)
    
    async def _prepare_generation_environment(
        self, job_id: str, corpus_id: Optional[str], db: Optional[AsyncSession]
    ) -> Optional[List[Dict]]:
        """Prepare generation environment with corpus and destination"""
        corpus_content = await self._load_corpus(corpus_id, db)
        await self._setup_destination(job_id)
        return corpus_content

    async def _load_corpus(
        self,
        corpus_id: Optional[str],
        db: Optional[AsyncSession]
    ) -> Optional[List[Dict]]:
        """Load corpus content if specified"""
        if corpus_id:
            from .corpus_manager import load_corpus
            return await load_corpus(
                corpus_id, db, self.corpus_cache, get_clickhouse_client, central_logger
            )
        return None

    async def _setup_destination(self, job_id: str) -> None:
        """Setup destination table"""
        table_name = self.active_jobs[job_id]["table_name"]
        await self.ingestion_manager.create_destination_table(table_name)

    async def create_job_record(
        self,
        job_id: str,
        config,
        corpus_id: Optional[str],
        user_id: Optional[str],
        table_name: str,
        db: Optional[AsyncSession]
    ) -> Dict:
        """Create job tracking record"""
        job_data = self.job_manager.create_job(
            job_id, config, corpus_id, user_id, table_name
        )
        job_data = await self._enhance_job_with_database_record(job_data, job_id, db, table_name, user_id)
        self.active_jobs[job_id] = job_data
        return job_data

    async def _enhance_job_with_database_record(
        self, job_data: Dict, job_id: str, db: Optional[AsyncSession], table_name: str, user_id: Optional[str]
    ) -> Dict:
        """Enhance job data with database record if available"""
        if db is not None:
            synthetic_data_id = await self._create_database_record(
                db, table_name, job_id, user_id
            )
            job_data["synthetic_data_id"] = synthetic_data_id
        return job_data

    async def _create_database_record(
        self,
        db: AsyncSession,
        table_name: str,
        job_id: str,
        user_id: Optional[str]
    ) -> str:
        """Create database record for job"""
        db_synthetic_data = self._build_corpus_model(table_name, job_id, user_id)
        return self._persist_corpus_model(db, db_synthetic_data)

    async def start_generation_worker(
        self,
        job_id: str,
        config,
        corpus_id: Optional[str],
        db: Optional[AsyncSession],
        synthetic_data_id: Optional[str]
    ) -> None:
        """Start generation worker task"""
        asyncio.create_task(
            self.execute_generation_workflow(
                job_id, config, corpus_id, db, synthetic_data_id
            )
        )