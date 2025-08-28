"""
Generation Utilities - Utility methods for synthetic data generation
"""

from typing import TYPE_CHECKING, Dict, List, Optional, Union

if TYPE_CHECKING:
    from netra_backend.app.schemas.data_ingestion_types import IngestionConfig
    from netra_backend.app.schemas.generation import SyntheticDataGenParams

from netra_backend.app import schemas


class GenerationUtilities:
    """Utility methods for generation operations"""

    def __init__(self, generation_engine):
        self.generation_engine = generation_engine

    async def get_job_status(self, job_id: str, active_jobs: Dict) -> Optional[Dict]:
        """Get job status"""
        return active_jobs.get(job_id)

    async def get_preview(
        self,
        corpus_id: Optional[str],
        workload_type: str,
        sample_size: int = 10
    ) -> List[Dict]:
        """Generate preview samples"""
        config = schemas.LogGenParams(
            num_logs=sample_size,
            corpus_id=corpus_id or "preview"
        )
        
        return await self.generation_engine.generate_preview(
            config, corpus_id, workload_type, sample_size
        )

    async def generate_batch(
        self,
        config: Union['SyntheticDataGenParams', 'IngestionConfig'],
        batch_size: int = 100
    ) -> List[Dict]:
        """Generate single batch"""
        return await self.generation_engine.generate_batch(config, batch_size)

    async def generate_incremental(
        self,
        config,
        checkpoint_callback=None
    ) -> Dict:
        """Generate data incrementally with checkpoints"""
        return await self.generation_engine.generate_incremental(config, checkpoint_callback)

    async def get_corpus_analytics(self) -> Dict:
        """Get corpus usage analytics for admin visibility"""
        return {
            "most_used_corpora": [],
            "corpus_coverage": 0.0,
            "content_distribution": {},
            "access_patterns": []
        }