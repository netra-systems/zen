"""Saga pattern implementation for distributed transaction management.

Provides saga execution with automatic compensation on failure.
All functions strictly adhere to 25-line limit.
"""

import uuid
from typing import Dict, List, Any, Optional

from netra_backend.app.logging_config import central_logger

from netra_backend.app.services.compensation_models import Saga, SagaStep, SagaState

logger = central_logger.get_logger(__name__)


class SagaEngine:
    """Engine for executing saga transactions."""
    
    def __init__(self):
        """Initialize saga engine."""
        self.active_sagas: Dict[str, Saga] = {}
    
    def _create_saga_instance(self, name: str, steps: List[SagaStep]) -> Saga:
        """Create new saga instance."""
        saga_id = str(uuid.uuid4())
        return Saga(saga_id=saga_id, name=name, steps=steps)
    
    def _register_saga(self, saga: Saga) -> str:
        """Register saga in active sagas."""
        self.active_sagas[saga.saga_id] = saga
        logger.debug(f"Created saga: {saga.saga_id}")
        return saga.saga_id
    
    def create_saga(self, name: str, steps: List[SagaStep]) -> str:
        """Create and register a new saga."""
        saga = self._create_saga_instance(name, steps)
        return self._register_saga(saga)
    
    def _log_step_start(self, step: SagaStep) -> None:
        """Log saga step execution start."""
        logger.debug(f"Executing saga step: {step.name}")
    
    def _log_step_completion(self, step: SagaStep) -> None:
        """Log saga step completion."""
        logger.debug(f"Saga step completed: {step.name}")
    
    def _log_step_failure(self, step: SagaStep, error: Exception) -> None:
        """Log saga step failure."""
        logger.error(f"Saga step failed: {step.name}: {error}")
    
    async def _execute_saga_step(self, step: SagaStep) -> None:
        """Execute single saga step."""
        self._log_step_start(step)
        step.result = await step.forward_action(**step.forward_params)
        step.executed = True
        self._log_step_completion(step)
    
    def _handle_step_failure(self, step: SagaStep, error: Exception, saga: Saga) -> None:
        """Handle saga step execution failure."""
        step.error = str(error)
        self._log_step_failure(step, error)
        saga.state = SagaState.COMPENSATING
    
    async def _execute_saga_forward_steps(self, saga: Saga) -> bool:
        """Execute all saga forward steps."""
        for step_idx, step in enumerate(saga.steps):
            try:
                await self._execute_saga_step(step)
            except Exception as e:
                self._handle_step_failure(step, e, saga)
                compensation_success = await self._compensate_saga(saga, step_idx - 1)
                saga.state = SagaState.ABORTED if compensation_success else SagaState.FAILED
                return False
        return True
    
    def _finalize_saga_success(self, saga: Saga) -> None:
        """Finalize successful saga execution."""
        saga.state = SagaState.COMPLETED
        logger.info(f"Saga completed successfully: {saga.saga_id}")
    
    def _finalize_saga_failure(self, saga: Saga, error: Exception) -> None:
        """Finalize failed saga execution."""
        saga.state = SagaState.FAILED
        logger.error(f"Saga execution error: {saga.saga_id}: {error}")
    
    async def execute_saga(self, saga_id: str) -> bool:
        """Execute saga by ID."""
        saga = self.active_sagas.get(saga_id)
        if not saga:
            logger.error(f"Saga not found: {saga_id}")
            return False
        
        try:
            success = await self._execute_saga_forward_steps(saga)
            if success:
                self._finalize_saga_success(saga)
            return success
        except Exception as e:
            self._finalize_saga_failure(saga, e)
            return False
        finally:
            await self._cleanup_saga(saga_id)
    
    def _log_compensation_start(self, saga_id: str) -> None:
        """Log saga compensation start."""
        logger.info(f"Starting saga compensation: {saga_id}")
    
    def _log_step_compensation_start(self, step: SagaStep) -> None:
        """Log step compensation start."""
        logger.debug(f"Compensating saga step: {step.name}")
    
    def _log_step_compensation_result(self, step: SagaStep, success: bool) -> bool:
        """Log step compensation result and return success."""
        if success:
            logger.debug(f"Saga step compensation completed: {step.name}")
        else:
            logger.error(f"Saga step compensation failed: {step.name}")
        return success
    
    async def _compensate_saga_step(self, step: SagaStep) -> bool:
        """Compensate single saga step."""
        self._log_step_compensation_start(step)
        success = await step.compensation_action(**step.compensation_params)
        step.compensated = success
        return self._log_step_compensation_result(step, success)
    
    def _should_compensate_step(self, step: SagaStep) -> bool:
        """Check if step should be compensated."""
        return step.executed
    
    async def _execute_step_compensation(self, step: SagaStep) -> bool:
        """Execute compensation for single step with error handling."""
        try:
            return await self._compensate_saga_step(step)
        except Exception as e:
            logger.error(f"Saga step compensation error: {step.name}: {e}")
            return False
    
    async def _compensate_saga_steps(self, saga: Saga, last_executed_step: int) -> bool:
        """Compensate saga steps in reverse order."""
        compensation_success = True
        
        for step_idx in range(last_executed_step, -1, -1):
            step = saga.steps[step_idx]
            if not self._should_compensate_step(step):
                continue
            success = await self._execute_step_compensation(step)
            if not success:
                compensation_success = False
        
        return compensation_success
    
    def _log_compensation_result(self, saga_id: str, success: bool) -> bool:
        """Log compensation result."""
        if success:
            logger.info(f"Saga compensation completed successfully: {saga_id}")
        else:
            logger.error(f"Saga compensation had failures: {saga_id}")
        return success
    
    async def _compensate_saga(self, saga: Saga, last_executed_step: int) -> bool:
        """Execute compensation for executed steps in reverse order."""
        self._log_compensation_start(saga.saga_id)
        compensation_success = await self._compensate_saga_steps(saga, last_executed_step)
        return self._log_compensation_result(saga.saga_id, compensation_success)
    
    async def _cleanup_saga(self, saga_id: str) -> None:
        """Clean up saga resources."""
        if saga_id in self.active_sagas:
            del self.active_sagas[saga_id]
    
    def _build_saga_status(self, saga: Saga) -> Dict[str, Any]:
        """Build saga status dictionary."""
        return {
            'saga_id': saga.saga_id,
            'name': saga.name,
            'state': saga.state.value,
            'total_steps': len(saga.steps),
            'executed_steps': len(saga.executed_steps),
            'failed_steps': len(saga.failed_steps),
            'created_at': saga.created_at.isoformat(),
            'is_expired': saga.is_expired
        }
    
    def get_saga_status(self, saga_id: str) -> Optional[Dict[str, Any]]:
        """Get status of saga execution."""
        saga = self.active_sagas.get(saga_id)
        if not saga:
            return None
        return self._build_saga_status(saga)
    
    def get_active_sagas(self) -> List[Dict[str, Any]]:
        """Get list of all active sagas."""
        return [
            self._build_saga_status(saga)
            for saga in self.active_sagas.values()
        ]