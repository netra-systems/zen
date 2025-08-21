"""
Corpus CRUD operations - basic corpus management operations
"""

import asyncio
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app...db import models_postgres as models
from netra_backend.app... import schemas
from netra_backend.app.base import CorpusStatus, CorpusNotFoundError, ClickHouseOperationError
from netra_backend.app.base_service import BaseCorpusService
from netra_backend.app.logging_config import central_logger


class CorpusCrudService(BaseCorpusService):
    """Service for basic corpus CRUD operations"""
    
    async def get_corpus(self, db: AsyncSession, corpus_id: str) -> Optional[models.Corpus]:
        """Get corpus by ID"""
        return await self.corpus_manager.get_corpus(db, corpus_id)
    
    async def get_corpora(self, db: AsyncSession, skip: int = 0, limit: int = 100,
                         status: Optional[str] = None, 
                         user_id: Optional[str] = None) -> List[models.Corpus]:
        """Get list of corpora with filtering"""
        return await self.corpus_manager.get_corpora(db, skip, limit, status, user_id)
    
    async def update_corpus(self, db: AsyncSession, corpus_id: str, 
                          update_data: schemas.CorpusUpdate) -> Optional[models.Corpus]:
        """Update corpus metadata"""
        return await self.corpus_manager.update_corpus(db, corpus_id, update_data)
    
    async def delete_corpus(self, db: AsyncSession, corpus_id: str) -> bool:
        """Delete corpus and associated ClickHouse table"""
        db_corpus = await self._get_corpus_for_delete(db, corpus_id)
        try:
            return await self._execute_corpus_deletion(db, corpus_id, db_corpus)
        except Exception as e:
            await self._handle_deletion_failure(db, corpus_id, e)
    
    async def _get_corpus_for_delete(self, db: AsyncSession, 
                                   corpus_id: str) -> models.Corpus:
        """Get and validate corpus for deletion"""
        db_corpus = await self.get_corpus(db, corpus_id)
        if not db_corpus:
            raise CorpusNotFoundError(f"Corpus {corpus_id} not found")
        return db_corpus
    
    async def _execute_corpus_deletion(self, db: AsyncSession, corpus_id: str, 
                                     db_corpus: models.Corpus) -> bool:
        """Execute complete corpus deletion process"""
        await self.corpus_manager.set_corpus_status(
            db, corpus_id, CorpusStatus.DELETING.value
        )
        await self.clickhouse_ops.delete_corpus_table(db_corpus.table_name)
        return await self.corpus_manager.delete_corpus_record(db, corpus_id)
    
    async def _handle_deletion_failure(self, db: AsyncSession, corpus_id: str, 
                                     e: Exception) -> None:
        """Handle corpus deletion failure with status reversion"""
        central_logger.error(f"Failed to delete corpus {corpus_id}: {str(e)}")
        await self.corpus_manager.set_corpus_status(
            db, corpus_id, CorpusStatus.FAILED.value
        )
        raise ClickHouseOperationError(f"Failed to delete corpus: {str(e)}")
    
    async def clone_corpus(self, db: AsyncSession, source_corpus_id: str, 
                         new_name: str, user_id: str) -> Optional[models.Corpus]:
        """Clone an existing corpus"""
        source_corpus = await self._get_and_validate_source_corpus(db, source_corpus_id)
        new_corpus = await self._create_cloned_corpus_record(db, source_corpus, new_name, user_id)
        self._schedule_clone_operations(source_corpus, new_corpus, db)
        return new_corpus
    
    async def _get_and_validate_source_corpus(self, db: AsyncSession, 
                                            source_corpus_id: str) -> models.Corpus:
        """Get and validate source corpus for cloning"""
        source_corpus = await self.get_corpus(db, source_corpus_id)
        if not source_corpus:
            raise CorpusNotFoundError(f"Source corpus {source_corpus_id} not found")
        self._validate_corpus_availability(source_corpus, source_corpus_id)
        return source_corpus
    
    def _validate_corpus_availability(self, source_corpus: models.Corpus, 
                                    source_corpus_id: str) -> None:
        """Validate corpus is available for cloning"""
        if source_corpus.status != CorpusStatus.AVAILABLE.value:
            msg = f"Source corpus {source_corpus_id} is not available for cloning"
            raise ValueError(msg)
    
    async def _create_cloned_corpus_record(self, db: AsyncSession, 
                                         source_corpus: models.Corpus, 
                                         new_name: str, 
                                         user_id: str) -> models.Corpus:
        """Create new corpus record for clone"""
        return await self.corpus_manager.clone_corpus(
            db, source_corpus, new_name, user_id
        )
    
    def _schedule_clone_operations(self, source_corpus: models.Corpus, 
                                 new_corpus: models.Corpus, db: AsyncSession) -> None:
        """Schedule asynchronous clone operations"""
        self._schedule_table_creation(new_corpus, db)
        self._schedule_content_copy(source_corpus, new_corpus, db)
    
    def _schedule_table_creation(self, new_corpus: models.Corpus, db: AsyncSession) -> None:
        """Schedule ClickHouse table creation"""
        table_creation = self.clickhouse_ops.create_corpus_table(
            new_corpus.id, new_corpus.table_name, db
        )
        asyncio.create_task(table_creation)
    
    def _schedule_content_copy(self, source_corpus: models.Corpus, 
                             new_corpus: models.Corpus, db: AsyncSession) -> None:
        """Schedule content copy operation"""
        content_copy = self.document_manager.copy_corpus_content(
            source_corpus.table_name, new_corpus.table_name, new_corpus.id, db
        )
        asyncio.create_task(content_copy)