"""
Incremental Generation Module - Handles incremental data generation with checkpoints
"""

import asyncio
import uuid
from datetime import datetime, UTC
from typing import Dict, List, Optional, Callable

from netra_backend.app.logging_config import central_logger


class IncrementalGenerationHandler:
    """Handler for incremental data generation with checkpoints"""

    async def generate_incremental(
        self,
        config,
        checkpoint_callback: Optional[Callable] = None
    ) -> Dict:
        """Generate data incrementally with checkpoints"""
        state = self._init_incremental_state(config)
        while state['total_generated'] < state['num_traces']:
            await self._process_incremental_batch(config, state, checkpoint_callback)
        return self._build_result(state['total_generated'], state['checkpoints'])

    def _init_incremental_state(self, config) -> Dict:
        """Initialize incremental generation state"""
        return {
            'num_traces': getattr(config, 'num_traces', 100),
            'checkpoint_interval': getattr(config, 'checkpoint_interval', 25),
            'total_generated': 0,
            'checkpoints': [],
            'job_id': str(uuid.uuid4())
        }

    async def _process_incremental_batch(self, config, state: Dict, callback) -> None:
        """Process single incremental batch with checkpoint"""
        batch = await self._generate_incremental_batch(
            config, state['total_generated'], state['checkpoint_interval'], state['num_traces']
        )
        checkpoint_data = self._create_checkpoint_data(
            batch, state['total_generated'], len(state['checkpoints'])
        )
        state['checkpoints'].append(checkpoint_data)
        state['total_generated'] += len(batch)
        
        if callback:
            await self._execute_callback_safely(callback, checkpoint_data)
        await asyncio.sleep(0.01)

    async def _generate_incremental_batch(
        self,
        config,
        total_generated: int,
        checkpoint_interval: int,
        num_traces: int
    ) -> List[Dict]:
        """Generate batch for incremental processing"""
        batch_size = min(checkpoint_interval, num_traces - total_generated)
        return [self._create_record(total_generated + i) for i in range(batch_size)]

    def _create_record(self, index: int) -> Dict:
        """Create single incremental record"""
        return {
            "index": index,
            "timestamp": datetime.now(UTC).isoformat(),
            "trace_id": str(uuid.uuid4()),
            "data": f"incremental_record_{index}"
        }

    def _create_checkpoint_data(
        self,
        batch: List[Dict],
        total_generated: int,
        checkpoint_count: int
    ) -> Dict:
        """Create checkpoint data structure"""
        return {
            "batch_number": checkpoint_count + 1,
            "records_in_batch": len(batch),
            "total_generated": total_generated + len(batch),
            "timestamp": datetime.now(UTC).isoformat(),
            "data": batch
        }

    async def _execute_callback_safely(self, callback, checkpoint_data: Dict) -> None:
        """Execute checkpoint callback safely"""
        try:
            await callback(checkpoint_data)
        except Exception as e:
            central_logger.warning(f"Checkpoint callback failed: {str(e)}")

    def _build_result(self, total_generated: int, checkpoints: List) -> Dict:
        """Build final incremental generation result"""
        return {
            "total_generated": total_generated,
            "checkpoints": len(checkpoints),
            "completion_time": datetime.now(UTC).isoformat()
        }