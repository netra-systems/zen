"""
Corpus Management Service - Refactored Modular Version
Maintains backward compatibility while providing modular architecture

This is the main entry point that orchestrates the modular corpus service components.
All original functionality is preserved through delegation to specialized modules.
"""

import asyncio
import warnings
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from app import schemas
from .corpus import (
    CorpusService as ModularCorpusService,
    corpus_service,
    CorpusStatus,
    ContentSource
)

# Re-export classes for backward compatibility
__all__ = [
    "CorpusStatus",
    "ContentSource", 
    "CorpusService",
    "corpus_service",
    # Legacy functions
    "get_corpus",
    "get_corpora", 
    "create_corpus",
    "update_corpus",
    "delete_corpus",
    "generate_corpus_task",
    "get_corpus_status",
    "get_corpus_content"
]

# Main service class - delegates to modular implementation
class CorpusService:
    """
    Main corpus service class - delegates to modular implementation
    Maintains backward compatibility with the original monolithic service
    """
    
    def __init__(self):
        self._modular_service = ModularCorpusService()
    
    # Delegate all methods to the modular implementation
    async def create_corpus(self, db: Session, corpus_data: schemas.CorpusCreate, user_id: str, content_source: ContentSource = ContentSource.UPLOAD):
        return await self._modular_service.create_corpus(db, corpus_data, user_id, content_source)
    
    async def upload_content(self, db: Session, corpus_id: str, records: List[Dict], batch_id: Optional[str] = None, is_final_batch: bool = False):
        return await self._modular_service.upload_content(db, corpus_id, records, batch_id, is_final_batch)
    
    async def get_corpus(self, db: Session, corpus_id: str):
        return await self._modular_service.get_corpus(db, corpus_id)
    
    async def get_corpora(self, db: Session, skip: int = 0, limit: int = 100, status: Optional[str] = None, user_id: Optional[str] = None):
        return await self._modular_service.get_corpora(db, skip, limit, status, user_id)
    
    async def update_corpus(self, db: Session, corpus_id: str, update_data: schemas.CorpusUpdate):
        return await self._modular_service.update_corpus(db, corpus_id, update_data)
    
    async def delete_corpus(self, db: Session, corpus_id: str):
        return await self._modular_service.delete_corpus(db, corpus_id)
    
    async def get_corpus_content(self, db: Session, corpus_id: str, limit: int = 100, offset: int = 0, workload_type: Optional[str] = None):
        return await self._modular_service.get_corpus_content(db, corpus_id, limit, offset, workload_type)
    
    async def get_corpus_statistics(self, db: Session, corpus_id: str):
        return await self._modular_service.get_corpus_statistics(db, corpus_id)
    
    async def clone_corpus(self, db: Session, source_corpus_id: str, new_name: str, user_id: str):
        return await self._modular_service.clone_corpus(db, source_corpus_id, new_name, user_id)
    
    async def search_corpus_content(self, db: Session, corpus_id: str, search_params: Dict):
        return await self._modular_service.search_corpus_content(db, corpus_id, search_params)
    
    async def get_corpus_sample(self, db: Session, corpus_id: str, sample_size: int = 10, workload_type: Optional[str] = None):
        return await self._modular_service.get_corpus_sample(db, corpus_id, sample_size, workload_type)
    
    async def get_workload_type_analytics(self, db: Session, corpus_id: str):
        return await self._modular_service.get_workload_type_analytics(db, corpus_id)


# Legacy functions for backward compatibility
# TODO: Migrate routes to use async CorpusService directly

def get_corpus(db: Session, corpus_id: str):
    """Legacy function to get corpus - DEPRECATED
    
    Use CorpusService.get_corpus() with async session instead.
    """
    warnings.warn(
        "get_corpus() is deprecated. Use CorpusService.get_corpus() with async session.",
        DeprecationWarning,
        stacklevel=2
    )
    return asyncio.run(corpus_service.get_corpus(db, corpus_id))


def get_corpora(db: Session, skip: int = 0, limit: int = 100):
    """Legacy function to get corpora list - DEPRECATED
    
    Use CorpusService.get_corpora() with async session instead.
    """
    warnings.warn(
        "get_corpora() is deprecated. Use CorpusService.get_corpora() with async session.",
        DeprecationWarning,
        stacklevel=2
    )
    return asyncio.run(corpus_service.get_corpora(db, skip, limit))


def create_corpus(db: Session, corpus: schemas.CorpusCreate, user_id: str):
    """Legacy function to create corpus - DEPRECATED
    
    Use CorpusService.create_corpus() with async session instead.
    """
    warnings.warn(
        "create_corpus() is deprecated. Use CorpusService.create_corpus() with async session.",
        DeprecationWarning,
        stacklevel=2
    )
    return asyncio.run(corpus_service.create_corpus(db, corpus, user_id))


def update_corpus(db: Session, corpus_id: str, corpus: schemas.CorpusUpdate):
    """Legacy function to update corpus - DEPRECATED
    
    Use CorpusService.update_corpus() with async session instead.
    """
    warnings.warn(
        "update_corpus() is deprecated. Use CorpusService.update_corpus() with async session.",
        DeprecationWarning,
        stacklevel=2
    )
    return asyncio.run(corpus_service.update_corpus(db, corpus_id, corpus))


def delete_corpus(db: Session, corpus_id: str):
    """Legacy function to delete corpus - DEPRECATED
    
    Use CorpusService.delete_corpus() with async session instead.
    """
    warnings.warn(
        "delete_corpus() is deprecated. Use CorpusService.delete_corpus() with async session.",
        DeprecationWarning,
        stacklevel=2
    )
    return asyncio.run(corpus_service.delete_corpus(db, corpus_id))


async def generate_corpus_task(corpus_id: str, db: Session):
    """Legacy task function - DEPRECATED
    
    Table creation is now handled directly in CorpusService.create_corpus().
    This function does nothing and should not be used.
    """
    warnings.warn(
        "generate_corpus_task() is deprecated and does nothing. Remove calls to this function.",
        DeprecationWarning,
        stacklevel=2
    )
    # Function intentionally does nothing - table creation handled in create_corpus


def get_corpus_status(db: Session, corpus_id: str):
    """Legacy function to get corpus status - DEPRECATED
    
    Use CorpusService.get_corpus() with async session instead.
    """
    warnings.warn(
        "get_corpus_status() is deprecated. Use CorpusService.get_corpus() with async session.",
        DeprecationWarning,
        stacklevel=2
    )
    db_corpus = asyncio.run(corpus_service.get_corpus(db, corpus_id))
    return db_corpus.status if db_corpus else None


async def get_corpus_content(db: Session, corpus_id: str):
    """Legacy function to get corpus content - DEPRECATED
    
    Use CorpusService.get_corpus_content() with async session instead.
    """
    warnings.warn(
        "get_corpus_content() is deprecated. Use CorpusService.get_corpus_content() with async session.",
        DeprecationWarning,
        stacklevel=2
    )
    return await corpus_service.get_corpus_content(db, corpus_id)