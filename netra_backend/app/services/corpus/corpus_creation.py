"""
Corpus creation operations - handles corpus creation logic
"""

import asyncio
import json
import uuid
from datetime import UTC, datetime
from typing import Any, Dict

from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app import schemas
from netra_backend.app.core.error_codes import ErrorCode
from netra_backend.app.core.exceptions_base import NetraException
from netra_backend.app.db import models_postgres as models
from netra_backend.app.services.corpus.base import ContentSource, CorpusStatus
from netra_backend.app.services.corpus.base_service import BaseCorpusService


class CorpusCreationService(BaseCorpusService):
    """Service for corpus creation operations"""
    
    def _prepare_and_create_corpus_model(self, corpus_data: schemas.CorpusCreate, 
                                        user_id: str, content_source: ContentSource) -> tuple[models.Corpus, str, str]:
        """Prepare identifiers and create corpus model."""
        corpus_id, table_name = self._prepare_corpus_identifiers(corpus_data)
        db_corpus = self._create_corpus_model(corpus_data, corpus_id, table_name, user_id, content_source)
        return db_corpus, corpus_id, table_name

    async def create_corpus(
        self,
        db: AsyncSession,
        corpus_data: schemas.CorpusCreate,
        user_id: str,
        content_source: ContentSource = ContentSource.UPLOAD
    ) -> models.Corpus:
        """Create a new corpus with ClickHouse table"""
        self._validate_corpus_data(corpus_data)
        db_corpus, corpus_id, table_name = self._prepare_and_create_corpus_model(corpus_data, user_id, content_source)
        await self._persist_and_schedule_creation(db, db_corpus, corpus_data.name, user_id, corpus_id, table_name)
        return db_corpus
    
    def _validate_corpus_data(self, corpus_data: schemas.CorpusCreate) -> None:
        """Validate corpus data for creation"""
        validation_result = self.validation_manager.validate_corpus_data(corpus_data)
        if not validation_result["valid"]:
            errors = '; '.join(validation_result['errors'])
            raise ValueError(f"Invalid corpus data: {errors}")
    
    def _prepare_corpus_identifiers(self, 
                                   corpus_data: schemas.CorpusCreate) -> tuple[str, str]:
        """Generate corpus ID and table name"""
        corpus_id = str(uuid.uuid4())
        table_name = self.validation_manager.sanitize_table_name(corpus_id)
        return corpus_id, table_name
    
    def _create_corpus_model(self, corpus_data: schemas.CorpusCreate, corpus_id: str, 
                           table_name: str, user_id: str, 
                           content_source: ContentSource) -> models.Corpus:
        """Create corpus model with metadata"""
        metadata = self._build_corpus_metadata(content_source)
        domain = getattr(corpus_data, 'domain', 'general')
        return self._build_corpus_instance(corpus_data, corpus_id, table_name, user_id, domain, metadata)
    
    def _build_corpus_instance(self, corpus_data: schemas.CorpusCreate, corpus_id: str,
                              table_name: str, user_id: str, domain: str, 
                              metadata: Dict[str, Any]) -> models.Corpus:
        """Build corpus instance with all attributes"""
        return models.Corpus(
            id=corpus_id, name=corpus_data.name, description=corpus_data.description,
            table_name=table_name, status=CorpusStatus.CREATING.value, created_by_id=user_id, 
            domain=domain, metadata_=json.dumps(metadata))
    
    def _build_corpus_metadata(self, content_source: ContentSource) -> Dict[str, Any]:
        """Build corpus metadata dictionary"""
        return {
            "content_source": content_source.value,
            "created_at": datetime.now(UTC).isoformat(),
            "version": 1
        }
    
    async def _persist_corpus_to_db(self, db: AsyncSession, db_corpus: models.Corpus, 
                                   corpus_name: str, user_id: str) -> None:
        """Persist corpus to database with error handling"""
        try:
            db.add(db_corpus)
            await db.commit()
            await db.refresh(db_corpus)
        except Exception as e:
            await db.rollback()
            raise self._create_persistence_error(corpus_name, user_id, str(e))
    
    def _create_persistence_error(self, corpus_name: str, user_id: str, 
                                 error: str) -> NetraException:
        """Create persistence error exception"""
        return NetraException(
            message=f"Database connection failure during corpus creation",
            code=ErrorCode.DATABASE_CONNECTION_FAILED,
            context={"corpus_name": corpus_name, "user_id": user_id, "error": error}
        )
    
    def _schedule_clickhouse_table_creation(self, corpus_id: str, table_name: str, 
                                          db: AsyncSession) -> None:
        """Schedule ClickHouse table creation asynchronously"""
        task = self.clickhouse_ops.create_corpus_table(corpus_id, table_name, db)
        asyncio.create_task(task)
    
    async def _persist_and_schedule_creation(self, db: AsyncSession, db_corpus: models.Corpus,
                                           corpus_name: str, user_id: str, corpus_id: str, 
                                           table_name: str) -> None:
        """Persist corpus to database and schedule ClickHouse table creation"""
        await self._persist_corpus_to_db(db, db_corpus, corpus_name, user_id)
        self._schedule_clickhouse_table_creation(corpus_id, table_name, db)