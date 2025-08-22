"""Compensation engine for handling partial failures in distributed operations.

Thin wrapper providing backward compatibility while delegating to modular components.
Maintains existing API while using focused modules under 300 lines each.
"""

# Re-export all types and classes for backward compatibility
from netra_backend.app.services.compensation_engine_core import CompensationEngine
from netra_backend.app.services.compensation_handlers_core import (
    CacheCompensationHandler,
    DatabaseCompensationHandler,
    ExternalServiceCompensationHandler,
    FileSystemCompensationHandler,
)
from netra_backend.app.services.compensation_models import (
    BaseCompensationHandler,
    CompensationAction,
    CompensationState,
    Saga,
    SagaState,
    SagaStep,
)
from netra_backend.app.services.saga_engine import SagaEngine

# Create global instances for backward compatibility
compensation_engine = CompensationEngine()
saga_engine = SagaEngine()

# Export instances and factory functions for backward compatibility
__all__ = [
    # Types and models
    'CompensationState', 'SagaState', 'CompensationAction', 'SagaStep', 'Saga',
    'BaseCompensationHandler',
    # Handler classes 
    'DatabaseCompensationHandler', 'FileSystemCompensationHandler',
    'CacheCompensationHandler', 'ExternalServiceCompensationHandler',
    # Engine classes
    'CompensationEngine', 'SagaEngine',
    # Global instances
    'compensation_engine', 'saga_engine'
]