"""
Unified core corpus service - combines all corpus operations under 300 lines
"""

from typing import Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app import schemas
from netra_backend.app.db import models_postgres as models
from netra_backend.app.services.corpus.base import ContentSource
from netra_backend.app.services.corpus.content_operations import (
    ContentOperationsService,
)
from netra_backend.app.services.corpus.corpus_creation import CorpusCreationService
from netra_backend.app.services.corpus.corpus_crud import CorpusCrudService
from netra_backend.app.models.user_execution_context import UserExecutionContext


class CorpusService:
    """Unified corpus service combining all operations"""
    
    def __init__(self, user_context: Optional[UserExecutionContext] = None):
        """Initialize component services
        
        Args:
            user_context: Optional user context for WebSocket isolation.
                         If provided, enables WebSocket notifications.
                         If None, notifications are logged only.
        """
        self.user_context = user_context
        self.creation_service = CorpusCreationService(user_context=user_context)
        self.crud_service = CorpusCrudService(user_context=user_context)
        self.content_service = ContentOperationsService(user_context=user_context)
    
    # Corpus creation operations
    async def create_corpus(self, db: AsyncSession, corpus_data: schemas.CorpusCreate,
                          user_id: str, 
                          content_source: ContentSource = ContentSource.UPLOAD) -> models.Corpus:
        """Create a new corpus with ClickHouse table"""
        return await self.creation_service.create_corpus(
            db, corpus_data, user_id, content_source
        )
    
    # Basic CRUD operations
    async def get_corpus(self, db: AsyncSession, corpus_id: str) -> Optional[models.Corpus]:
        """Get corpus by ID"""
        return await self.crud_service.get_corpus(db, corpus_id)
    
    async def get_corpora(self, db: AsyncSession, skip: int = 0, limit: int = 100,
                         status: Optional[str] = None, 
                         user_id: Optional[str] = None) -> List[models.Corpus]:
        """Get list of corpora with filtering"""
        return await self.crud_service.get_corpora(db, skip, limit, status, user_id)
    
    async def update_corpus(self, db: AsyncSession, corpus_id: str,
                          update_data: schemas.CorpusUpdate) -> Optional[models.Corpus]:
        """Update corpus metadata"""
        return await self.crud_service.update_corpus(db, corpus_id, update_data)
    
    async def delete_corpus(self, db: AsyncSession, corpus_id: str) -> bool:
        """Delete corpus and associated ClickHouse table"""
        return await self.crud_service.delete_corpus(db, corpus_id)
    
    async def clone_corpus(self, db: AsyncSession, source_corpus_id: str,
                         new_name: str, user_id: str) -> Optional[models.Corpus]:
        """Clone an existing corpus"""
        return await self.crud_service.clone_corpus(
            db, source_corpus_id, new_name, user_id
        )
    
    # Content operations
    async def upload_content(self, db: AsyncSession, corpus_id: str, records: List[Dict],
                           batch_id: Optional[str] = None,
                           is_final_batch: bool = False) -> Dict:
        """Upload content to corpus"""
        return await self.content_service.upload_content(
            db, corpus_id, records, batch_id, is_final_batch
        )
    
    async def get_corpus_content(self, db: AsyncSession, corpus_id: str,
                               limit: int = 100, offset: int = 0,
                               workload_type: Optional[str] = None) -> Optional[List[Dict]]:
        """Get corpus content from ClickHouse"""
        return await self.content_service.get_corpus_content(
            db, corpus_id, limit, offset, workload_type
        )
    
    async def get_corpus_statistics(self, db: AsyncSession, 
                                  corpus_id: str) -> Optional[Dict]:
        """Get corpus statistics from ClickHouse"""
        return await self.content_service.get_corpus_statistics(db, corpus_id)
    
    async def search_corpus_content(self, db: AsyncSession, corpus_id: str,
                                  search_params: Dict):
        """Search corpus content with advanced filtering"""
        return await self.content_service.search_corpus_content(
            db, corpus_id, search_params
        )
    
    async def get_corpus_sample(self, db: AsyncSession, corpus_id: str,
                              sample_size: int = 10,
                              workload_type: Optional[str] = None):
        """Get a random sample of corpus content"""
        return await self.content_service.get_corpus_sample(
            db, corpus_id, sample_size, workload_type
        )
    
    async def get_workload_type_analytics(self, db: AsyncSession, corpus_id: str):
        """Get detailed analytics by workload type"""
        return await self.content_service.get_workload_type_analytics(db, corpus_id)
    
    async def incremental_index(self, corpus_id: str, 
                              new_documents: List[Dict]) -> Dict:
        """Incrementally index new documents into existing corpus"""
        return await self.content_service.incremental_index(corpus_id, new_documents)
    
    async def index_with_deduplication(self, corpus_id: str,
                                     documents: List[Dict]) -> Dict:
        """Index documents with deduplication"""
        return await self.content_service.index_with_deduplication(corpus_id, documents)