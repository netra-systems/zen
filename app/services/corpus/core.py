"""
Core corpus service class - main orchestrator for corpus operations
"""

import asyncio
import json
import uuid
from datetime import datetime, UTC
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from ...db import models_postgres as models
from ... import schemas
from ...ws_manager import manager
from .base import CorpusStatus, ContentSource, CorpusNotFoundError, ClickHouseOperationError
from .document_manager import DocumentManager
from .search_operations import SearchOperations
from .validation import ValidationManager
from .clickhouse_operations import ClickHouseOperations
from .corpus_manager import CorpusManager
from app.logging_config import central_logger


class CorpusService:
    """Main corpus service orchestrating all corpus operations"""
    
    def __init__(self):
        self.document_manager = DocumentManager()
        self.search_operations = SearchOperations()
        self.validation_manager = ValidationManager()
        self.clickhouse_ops = ClickHouseOperations()
        self.corpus_manager = CorpusManager()
    
    async def create_corpus(
        self,
        db: Session,
        corpus_data: schemas.CorpusCreate,
        user_id: str,
        content_source: ContentSource = ContentSource.UPLOAD
    ) -> models.Corpus:
        """
        Create a new corpus with ClickHouse table
        
        Args:
            db: Database session
            corpus_data: Corpus creation data
            user_id: User creating the corpus
            content_source: Source of corpus content
            
        Returns:
            Created corpus model
        """
        # Validate corpus data
        validation_result = self.validation_manager.validate_corpus_data(corpus_data)
        if not validation_result["valid"]:
            raise ValueError(f"Invalid corpus data: {'; '.join(validation_result['errors'])}")
        
        # Generate unique table name
        corpus_id = str(uuid.uuid4())
        table_name = self.validation_manager.sanitize_table_name(corpus_id)
        
        # Create PostgreSQL record
        db_corpus = models.Corpus(
            id=corpus_id,
            name=corpus_data.name,
            description=corpus_data.description,
            table_name=table_name,
            status=CorpusStatus.CREATING.value,
            created_by_id=user_id,
            domain=corpus_data.domain if hasattr(corpus_data, 'domain') else 'general',
            metadata_=json.dumps({
                "content_source": content_source.value,
                "created_at": datetime.now(UTC).isoformat(),
                "version": 1
            })
        )
        db.add(db_corpus)
        db.commit()
        db.refresh(db_corpus)
        
        # Create ClickHouse table asynchronously
        asyncio.create_task(self.clickhouse_ops.create_corpus_table(corpus_id, table_name, db))
        
        return db_corpus
    
    
    async def upload_content(
        self,
        db: Session,
        corpus_id: str,
        records: List[Dict],
        batch_id: Optional[str] = None,
        is_final_batch: bool = False
    ) -> Dict:
        """
        Upload content to corpus
        
        Args:
            db: Database session
            corpus_id: Corpus ID
            records: List of corpus records
            batch_id: Optional batch identifier
            is_final_batch: Whether this is the final batch
            
        Returns:
            Upload result with validation info
        """
        # Get corpus
        db_corpus = await self.get_corpus(db, corpus_id)
        
        if not db_corpus:
            raise CorpusNotFoundError(f"Corpus {corpus_id} not found")
        
        # Use document manager for upload
        return await self.document_manager.upload_content(
            db_corpus, records, batch_id, is_final_batch
        )
    
    async def get_corpus(
        self,
        db: Session,
        corpus_id: str
    ) -> Optional[models.Corpus]:
        """Get corpus by ID"""
        return await self.corpus_manager.get_corpus(db, corpus_id)
    
    async def get_corpora(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> List[models.Corpus]:
        """Get list of corpora with filtering"""
        return await self.corpus_manager.get_corpora(db, skip, limit, status, user_id)
    
    async def update_corpus(
        self,
        db: Session,
        corpus_id: str,
        update_data: schemas.CorpusUpdate
    ) -> Optional[models.Corpus]:
        """Update corpus metadata"""
        return await self.corpus_manager.update_corpus(db, corpus_id, update_data)
    
    async def delete_corpus(
        self,
        db: Session,
        corpus_id: str
    ) -> bool:
        """Delete corpus and associated ClickHouse table"""
        db_corpus = await self.get_corpus(db, corpus_id)
        
        if not db_corpus:
            raise CorpusNotFoundError(f"Corpus {corpus_id} not found")
        
        try:
            # Update status to deleting
            await self.corpus_manager.set_corpus_status(db, corpus_id, CorpusStatus.DELETING.value)
            
            # Drop ClickHouse table
            await self.clickhouse_ops.delete_corpus_table(db_corpus.table_name)
            
            # Delete PostgreSQL record
            return await self.corpus_manager.delete_corpus_record(db, corpus_id)
            
        except Exception as e:
            central_logger.error(f"Failed to delete corpus {corpus_id}: {str(e)}")
            
            # Revert status
            await self.corpus_manager.set_corpus_status(db, corpus_id, CorpusStatus.FAILED.value)
            
            raise ClickHouseOperationError(f"Failed to delete corpus: {str(e)}")
    
    async def get_corpus_content(
        self,
        db: Session,
        corpus_id: str,
        limit: int = 100,
        offset: int = 0,
        workload_type: Optional[str] = None
    ) -> Optional[List[Dict]]:
        """Get corpus content from ClickHouse"""
        db_corpus = await self.get_corpus(db, corpus_id)
        
        if not db_corpus:
            raise CorpusNotFoundError(f"Corpus {corpus_id} not found")
        
        return await self.document_manager.get_corpus_content(
            db_corpus, limit, offset, workload_type
        )
    
    async def get_corpus_statistics(
        self,
        db: Session,
        corpus_id: str
    ) -> Optional[Dict]:
        """Get corpus statistics from ClickHouse"""
        db_corpus = await self.get_corpus(db, corpus_id)
        
        if not db_corpus:
            raise CorpusNotFoundError(f"Corpus {corpus_id} not found")
        
        return await self.search_operations.get_corpus_statistics(db_corpus)
    
    async def clone_corpus(
        self,
        db: Session,
        source_corpus_id: str,
        new_name: str,
        user_id: str
    ) -> Optional[models.Corpus]:
        """Clone an existing corpus"""
        source_corpus = await self.get_corpus(db, source_corpus_id)
        
        if not source_corpus:
            raise CorpusNotFoundError(f"Source corpus {source_corpus_id} not found")
        
        if source_corpus.status != CorpusStatus.AVAILABLE.value:
            raise ValueError(f"Source corpus {source_corpus_id} is not available for cloning")
        
        # Create new corpus record
        new_corpus = await self.corpus_manager.clone_corpus(
            db, source_corpus, new_name, user_id
        )
        
        # Create ClickHouse table asynchronously
        asyncio.create_task(self.clickhouse_ops.create_corpus_table(new_corpus.id, new_corpus.table_name, db))
        
        # Copy content asynchronously
        asyncio.create_task(
            self.document_manager.copy_corpus_content(
                source_corpus.table_name,
                new_corpus.table_name,
                new_corpus.id,
                db
            )
        )
        
        return new_corpus
    
    # Delegate search operations to search_operations module
    async def search_corpus_content(self, db: Session, corpus_id: str, search_params: Dict):
        """Search corpus content with advanced filtering"""
        db_corpus = await self.get_corpus(db, corpus_id)
        if not db_corpus:
            raise CorpusNotFoundError(f"Corpus {corpus_id} not found")
        
        return await self.search_operations.search_corpus_content(db_corpus, search_params)
    
    async def get_corpus_sample(self, db: Session, corpus_id: str, sample_size: int = 10, workload_type: Optional[str] = None):
        """Get a random sample of corpus content"""
        db_corpus = await self.get_corpus(db, corpus_id)
        if not db_corpus:
            raise CorpusNotFoundError(f"Corpus {corpus_id} not found")
        
        return await self.search_operations.get_corpus_sample(db_corpus, sample_size, workload_type)
    
    async def get_workload_type_analytics(self, db: Session, corpus_id: str):
        """Get detailed analytics by workload type"""
        db_corpus = await self.get_corpus(db, corpus_id)
        if not db_corpus:
            raise CorpusNotFoundError(f"Corpus {corpus_id} not found")
        
        return await self.search_operations.get_workload_type_analytics(db_corpus)