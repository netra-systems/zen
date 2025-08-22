"""
Generation Engine Module - Core data generation and processing logic
"""

import asyncio
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, AsyncGenerator, Dict, List, Optional, Union

if TYPE_CHECKING:
    from netra_backend.app.schemas.data_ingestion_types import IngestionConfig
    from netra_backend.app.schemas.Generation import SyntheticDataGenParams

from netra_backend.app import schemas
from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.synthetic_data.advanced_generation_methods import (
    AdvancedGenerationMethods,
)
from netra_backend.app.services.synthetic_data.content_generator import (
    generate_child_spans,
    generate_content,
    generate_timestamp,
    select_agent_type,
    select_workload_type,
)
from netra_backend.app.services.synthetic_data.generation_patterns_helper import (
    GenerationPatternsHelper,
)
from netra_backend.app.services.synthetic_data.incremental_generation import (
    IncrementalGenerationHandler,
)
from netra_backend.app.services.synthetic_data.tool_generation import (
    ToolGenerationHelper,
)
from netra_backend.app.services.synthetic_data.tools import (
    calculate_metrics,
    generate_tool_invocations,
)


class GenerationEngine:
    """Core generation engine for synthetic data"""

    def __init__(self, default_tools: List[Dict]):
        self.default_tools = default_tools
        self.tool_helper = ToolGenerationHelper(default_tools)
        self.patterns_helper = GenerationPatternsHelper()
        self.advanced_methods = AdvancedGenerationMethods(self.patterns_helper, self.tool_helper)
        self.incremental_handler = IncrementalGenerationHandler()

    async def execute_batch_generation(
        self,
        job_id: str,
        config: schemas.LogGenParams,
        corpus_content: Optional[List[Dict]],
        active_jobs: Dict,
        ingestion_manager
    ) -> None:
        """Execute main batch generation process"""
        batch_config = self._prepare_batch_config(config, active_jobs, job_id)
        async for batch_num, batch in self._generate_batches(
            config, corpus_content, batch_config['batch_size'], batch_config['total_records']
        ):
            await self._process_batch(
                batch, batch_config['table_name'], job_id, batch_num, active_jobs, ingestion_manager
            )

    def _prepare_batch_config(self, config: schemas.LogGenParams, active_jobs: Dict, job_id: str) -> Dict:
        """Prepare batch configuration parameters"""
        return {
            'batch_size': 100,
            'total_records': config.num_logs,
            'table_name': active_jobs[job_id]["table_name"]
        }

    async def _process_batch(
        self,
        batch: List[Dict],
        table_name: str,
        job_id: str,
        batch_num: int,
        active_jobs: Dict,
        ingestion_manager
    ) -> None:
        """Process single batch through ingestion pipeline"""
        await ingestion_manager.ingest_batch_to_table(table_name, batch)
        self._update_job_counters(job_id, active_jobs, len(batch))
        await self._send_batch_progress(job_id, active_jobs, batch_num)

    def _update_job_counters(self, job_id: str, active_jobs: Dict, batch_size: int) -> None:
        """Update job progress counters"""
        active_jobs[job_id]["records_generated"] += batch_size
        active_jobs[job_id]["records_ingested"] += batch_size

    async def _send_batch_progress(
        self,
        job_id: str,
        active_jobs: Dict,
        batch_num: int
    ) -> None:
        """Send progress update for batch completion"""
        from .job_manager import JobManager
        job_manager = JobManager()
        await job_manager.send_progress_notification(job_id, active_jobs, batch_num)

    async def _generate_batches(
        self,
        config: schemas.LogGenParams,
        corpus_content: Optional[List[Dict]],
        batch_size: int,
        total_records: int
    ) -> AsyncGenerator[tuple[int, List[Dict]], None]:
        """Generate data in batches"""
        batch_state = self._init_batch_state()
        while batch_state['records_generated'] < total_records:
            batch = await self._generate_single_batch(
                config, corpus_content, batch_state['records_generated'], batch_size, total_records
            )
            yield batch_state['batch_num'], batch
            self._update_batch_state(batch_state, batch)
            await asyncio.sleep(0.01)

    def _init_batch_state(self) -> Dict:
        """Initialize batch generation state"""
        return {'records_generated': 0, 'batch_num': 0}

    def _update_batch_state(self, state: Dict, batch: List[Dict]) -> None:
        """Update batch generation state"""
        state['batch_num'] += 1
        state['records_generated'] += len(batch)

    async def _generate_single_batch(
        self,
        config: schemas.LogGenParams,
        corpus_content: Optional[List[Dict]],
        records_generated: int,
        batch_size: int,
        total_records: int
    ) -> List[Dict]:
        """Generate single batch of records"""
        batch_range = self._calculate_batch_range(records_generated, batch_size, total_records)
        batch = []
        for i in range(batch_range['start'], batch_range['end']):
            record = await self._generate_single_record(config, corpus_content, i)
            batch.append(record)
        return batch

    def _calculate_batch_range(self, records_generated: int, batch_size: int, total_records: int) -> Dict:
        """Calculate batch start and end indices"""
        return {
            'start': records_generated,
            'end': min(records_generated + batch_size, total_records)
        }

    async def _generate_single_record(
        self,
        config: schemas.LogGenParams,
        corpus_content: Optional[List[Dict]],
        index: int
    ) -> Dict:
        """Generate a single synthetic record"""
        record_components = self._generate_record_components(config, corpus_content, index)
        return self._build_record(
            record_components['trace_id'], record_components['span_id'], 
            record_components['timestamp'], record_components['workload_type'],
            record_components['tool_invocations'], record_components['request'], 
            record_components['response'], record_components['metrics']
        )

    def _generate_record_components(self, config: schemas.LogGenParams, corpus_content: Optional[List[Dict]], index: int) -> Dict:
        """Generate all components for a single record"""
        workload_type = select_workload_type()
        tool_invocations = generate_tool_invocations(workload_type, self.default_tools)
        request, response = generate_content(workload_type, corpus_content)
        record_ids = self._generate_record_ids()
        return self._assemble_record_components(
            record_ids, config, index, workload_type, tool_invocations, request, response
        )

    def _generate_record_ids(self) -> Dict:
        """Generate unique IDs for record"""
        return {'trace_id': str(uuid.uuid4()), 'span_id': str(uuid.uuid4())}

    def _assemble_record_components(
        self, record_ids: Dict, config: schemas.LogGenParams, index: int, 
        workload_type: str, tool_invocations: List[Dict], request: str, response: str
    ) -> Dict:
        """Assemble all record components into final dictionary"""
        return {
            **record_ids, 'timestamp': generate_timestamp(config, index), 'workload_type': workload_type,
            'tool_invocations': tool_invocations, 'request': request, 'response': response,
            'metrics': calculate_metrics(tool_invocations)
        }

    def _build_record(
        self,
        trace_id: str,
        span_id: str,
        timestamp: str,
        workload_type: str,
        tool_invocations: List[Dict],
        request: str,
        response: str,
        metrics: Dict
    ) -> Dict:
        """Build complete record structure"""
        record_metadata = self._build_record_metadata(trace_id, span_id, timestamp, workload_type)
        record_payload = self._build_record_payload(tool_invocations, request, response)
        return {**record_metadata, **record_payload, "metrics": metrics, "corpus_reference_id": None}

    def _build_record_metadata(self, trace_id: str, span_id: str, timestamp: str, workload_type: str) -> Dict:
        """Build record metadata components"""
        return {
            "event_id": str(uuid.uuid4()), "trace_id": trace_id, "span_id": span_id,
            "parent_span_id": None, "timestamp_utc": timestamp, "workload_type": workload_type,
            "agent_type": select_agent_type(workload_type)
        }

    def _build_record_payload(self, tool_invocations: List[Dict], request: str, response: str) -> Dict:
        """Build record payload components"""
        return {
            "tool_invocations": [t["name"] for t in tool_invocations],
            "request_payload": {"prompt": request},
            "response_payload": {"completion": response}
        }

    async def generate_preview(
        self,
        config: schemas.LogGenParams,
        corpus_id: Optional[str],
        workload_type: str,
        sample_size: int
    ) -> List[Dict]:
        """Generate preview samples"""
        samples = []
        corpus_content = None

        for i in range(sample_size):
            record = await self._generate_single_record(config, corpus_content, i)
            samples.append(record)

        return samples

    async def generate_batch(
        self,
        config: Union['SyntheticDataGenParams', 'IngestionConfig'],
        batch_size: int
    ) -> List[Dict[str, Any]]:
        """Generate single batch of records"""
        batch = []
        for i in range(batch_size):
            record = await self._generate_single_record(config, None, i)
            batch.append(record)
        return batch

    async def generate_incremental(
        self,
        config,
        checkpoint_callback=None
    ) -> Dict:
        """Generate data incrementally with checkpoints"""
        return await self.incremental_handler.generate_incremental(config, checkpoint_callback)

    # Advanced generation patterns - delegate to advanced methods
    async def generate_with_temporal_patterns(self, config) -> List[Dict]:
        """Generate with temporal patterns"""
        return await self.advanced_methods.generate_with_temporal_patterns(config)

    async def generate_with_errors(self, config) -> List[Dict]:
        """Generate with error scenarios"""
        return await self.advanced_methods.generate_with_errors(config)

    async def generate_domain_specific(self, config) -> List[Dict]:
        """Generate domain-specific data"""
        return await self.advanced_methods.generate_domain_specific(config)

    async def generate_tool_invocations(self, count: int, pattern: str) -> List[Dict]:
        """Generate synthetic tool invocation data"""
        return await self.advanced_methods.generate_tool_invocations(count, pattern)

    async def generate_trace_hierarchies(self, cnt: int, min_d: int, max_d: int) -> List[Dict]:
        """Generate trace hierarchies"""
        return await self.advanced_methods.generate_trace_hierarchies(cnt, min_d, max_d)

    async def generate_with_distribution(self, config) -> List[Dict]:
        """Generate with specific distributions"""
        return await self.advanced_methods.generate_with_distribution(config)

    async def generate_with_custom_tools(self, config) -> List[Dict]:
        """Generate with custom tool catalog"""
        return await self.advanced_methods.generate_with_custom_tools(config)

    async def generate_from_corpus(self, config, corpus_content: List[Dict]) -> List[Dict]:
        """Generate data from corpus content"""
        return await self.advanced_methods.generate_from_corpus(config, corpus_content)