"""
DEPRECATED: Legacy Synthetic Data Service

This service has been replaced by the new modular implementation.
Use the new service from core_service.py instead.

This module is maintained for backward compatibility only.
"""

import warnings
from typing import Dict, List, Optional, Any, Union, TYPE_CHECKING

if TYPE_CHECKING:
    from app.schemas.Generation import SyntheticDataGenParams
    from app.schemas.data_ingestion_types import IngestionConfig

from sqlalchemy.orm import Session

from .core_service import SyntheticDataService as NewSyntheticDataService
from .core_service import synthetic_data_service as new_service_instance


class SyntheticDataService:
    """
    DEPRECATED: Legacy wrapper for backward compatibility.
    
    All methods delegate to the new modular implementation.
    Please migrate to using the new service directly.
    """
    
    def __init__(self):
        """Initialize deprecated service with warning."""
        warnings.warn(
            "SyntheticDataService from service_deprecated.py is deprecated. "
            "Use the new modular service from core_service.py instead.",
            DeprecationWarning,
            stacklevel=2
        )
        self._new_service = NewSyntheticDataService()
    
    def __getattr__(self, name: str):
        """Delegate all attribute access to new service."""
        if hasattr(self._new_service, name):
            attr = getattr(self._new_service, name)
            if callable(attr):
                # For methods, add deprecation warning
                def deprecated_wrapper(*args, **kwargs):
                    warnings.warn(
                        f"Method {name} from deprecated service is being used. "
                        f"Please migrate to the new modular service.",
                        DeprecationWarning,
                        stacklevel=2
                    )
                    return attr(*args, **kwargs)
                return deprecated_wrapper
            return attr
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
    
    async def generate_synthetic_data(
        self,
        config,
        db: Optional[Session] = None,
        user_id: Optional[str] = None,
        corpus_id: Optional[str] = None,
        job_id: Optional[str] = None
    ) -> Dict:
        """Delegate to new service with deprecation warning."""
        warnings.warn(
            "generate_synthetic_data from deprecated service. Use new modular service.",
            DeprecationWarning,
            stacklevel=2
        )
        return await self._new_service.generate_synthetic_data(
            config, db, user_id, corpus_id, job_id
        )
    
    async def generate_batch(
        self, 
        config: Union['SyntheticDataGenParams', 'IngestionConfig'], 
        batch_size: int = 100
    ) -> List[Dict[str, Any]]:
        """Delegate to new service with deprecation warning."""
        warnings.warn(
            "generate_batch from deprecated service. Use new modular service.",
            DeprecationWarning,
            stacklevel=2
        )
        return await self._new_service.generate_batch(config, batch_size)
    
    async def ingest_batch(self, records: List[Dict], table_name: str = None) -> Dict:
        """Delegate to new service with deprecation warning."""
        warnings.warn(
            "ingest_batch from deprecated service. Use new modular service.",
            DeprecationWarning,
            stacklevel=2
        )
        return await self._new_service.ingest_batch(records, table_name)


# Create a singleton instance for backward compatibility
synthetic_data_service = new_service_instance