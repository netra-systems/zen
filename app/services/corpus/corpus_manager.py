"""
Corpus management operations - CRUD operations for corpus metadata
"""

import json
from datetime import datetime, UTC
from typing import Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from ...db import models_postgres as models
from ... import schemas
from ...ws_manager import manager
from .base import CorpusNotFoundError
from app.logging_config import central_logger


class CorpusManager:
    """Handles CRUD operations for corpus metadata"""
    
    async def get_corpus(
        self,
        db: AsyncSession,
        corpus_id: str
    ) -> Optional[models.Corpus]:
        """Get corpus by ID"""
        return db.query(models.Corpus).filter(
            models.Corpus.id == corpus_id
        ).first()
    
    def _apply_filters(self, query, status: Optional[str], user_id: Optional[str]):
        """Apply filters to corpus query"""
        if status:
            query = query.filter(models.Corpus.status == status)
        if user_id:
            query = query.filter(models.Corpus.created_by_id == user_id)
        return query

    async def get_corpora(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> List[models.Corpus]:
        """Get list of corpora with filtering"""
        query = db.query(models.Corpus)
        filtered_query = self._apply_filters(query, status, user_id)
        return filtered_query.offset(skip).limit(limit).all()
    
    def _validate_corpus_exists(self, db_corpus, corpus_id: str) -> None:
        """Validate that corpus exists for update"""
        if not db_corpus:
            raise CorpusNotFoundError(f"Corpus {corpus_id} not found")

    def _apply_update_fields(self, db_corpus, update_data: schemas.CorpusUpdate) -> None:
        """Apply update fields to corpus model"""
        for key, value in update_data.model_dump(exclude_unset=True).items():
            setattr(db_corpus, key, value)

    def _load_existing_metadata(self, db_corpus) -> Dict:
        """Load existing metadata from corpus"""
        return json.loads(db_corpus.metadata_ or "{}")

    def _update_metadata_version(self, metadata: Dict) -> Dict:
        """Update metadata with new timestamp and version"""
        metadata["updated_at"] = datetime.now(UTC).isoformat()
        metadata["version"] = metadata.get("version", 1) + 1
        return metadata

    def _save_updated_metadata(self, db_corpus, metadata: Dict) -> None:
        """Save updated metadata to corpus model"""
        db_corpus.metadata_ = json.dumps(metadata)

    def _commit_corpus_update(self, db: AsyncSession, db_corpus) -> models.Corpus:
        """Commit corpus update and refresh model"""
        db.commit()
        db.refresh(db_corpus)
        return db_corpus

    async def update_corpus(
        self, db: AsyncSession, corpus_id: str, update_data: schemas.CorpusUpdate
    ) -> Optional[models.Corpus]:
        """Update corpus metadata"""
        db_corpus = await self.get_corpus(db, corpus_id)
        self._validate_corpus_exists(db_corpus, corpus_id)
        self._apply_update_fields(db_corpus, update_data)
        metadata = self._load_existing_metadata(db_corpus)
        updated_metadata = self._update_metadata_version(metadata)
        self._save_updated_metadata(db_corpus, updated_metadata)
        return self._commit_corpus_update(db, db_corpus)
    
    def _generate_clone_ids(self) -> tuple[str, str]:
        """Generate corpus ID and table name for cloning"""
        import uuid
        corpus_id = str(uuid.uuid4())
        table_name = f"netra_content_corpus_{corpus_id.replace('-', '_')}"
        return corpus_id, table_name

    def _create_clone_metadata(self, source_corpus: models.Corpus) -> str:
        """Create metadata for cloned corpus"""
        from .base import ContentSource
        metadata = {
            "content_source": ContentSource.IMPORT.value, "cloned_from": source_corpus.id,
            "created_at": datetime.now(UTC).isoformat(), "version": 1
        }
        return json.dumps(metadata)

    def _create_corpus_model(self, corpus_id: str, table_name: str, new_name: str, 
                           source_corpus: models.Corpus, user_id: str, metadata: str) -> models.Corpus:
        """Create corpus model instance"""
        from .base import CorpusStatus
        return models.Corpus(
            id=corpus_id, name=new_name, description=f"Clone of {source_corpus.name}",
            table_name=table_name, status=CorpusStatus.CREATING.value, created_by_id=user_id,
            domain=source_corpus.domain, metadata_=metadata)

    def _save_corpus(self, db: AsyncSession, db_corpus: models.Corpus) -> models.Corpus:
        """Save corpus to database"""
        db.add(db_corpus)
        db.commit()
        db.refresh(db_corpus)
        return db_corpus

    async def clone_corpus(
        self,
        db: AsyncSession,
        source_corpus: models.Corpus,
        new_name: str,
        user_id: str
    ) -> models.Corpus:
        """Create a new corpus record for cloning"""
        corpus_id, table_name = self._generate_clone_ids()
        metadata = self._create_clone_metadata(source_corpus)
        db_corpus = self._create_corpus_model(corpus_id, table_name, new_name, source_corpus, user_id, metadata)
        return self._save_corpus(db, db_corpus)
    
    def _update_corpus_status_query(self, db: AsyncSession, corpus_id: str, status: str) -> int:
        """Execute corpus status update query"""
        return db.query(models.Corpus).filter(
            models.Corpus.id == corpus_id
        ).update({"status": status})

    def _handle_successful_status_update(self, db: AsyncSession, corpus_id: str, status: str) -> bool:
        """Handle successful status update"""
        db.commit()
        central_logger.info(f"Updated corpus {corpus_id} status to {status}")
        return True

    def _handle_status_update_error(self, db: AsyncSession, corpus_id: str, error: Exception) -> bool:
        """Handle status update error"""
        central_logger.error(f"Failed to update corpus {corpus_id} status: {str(error)}")
        db.rollback()
        return False

    async def set_corpus_status(
        self,
        db: AsyncSession,
        corpus_id: str,
        status: str
    ) -> bool:
        """Update corpus status"""
        try:
            updated = self._update_corpus_status_query(db, corpus_id, status)
            if updated:
                return self._handle_successful_status_update(db, corpus_id, status)
            return False
        except Exception as e:
            return self._handle_status_update_error(db, corpus_id, e)
    
    def _delete_corpus_from_db(self, db: AsyncSession, db_corpus: models.Corpus) -> None:
        """Delete corpus from database"""
        db.delete(db_corpus)
        db.commit()

    async def _send_deletion_notification(self, corpus_id: str) -> None:
        """Send corpus deletion notification"""
        await manager.broadcasting.broadcast_to_all({
            "type": "corpus:deleted", "payload": {"corpus_id": corpus_id}
        })

    def _handle_deletion_error(self, db: AsyncSession, corpus_id: str, error: Exception) -> bool:
        """Handle corpus deletion error"""
        central_logger.error(f"Failed to delete corpus record {corpus_id}: {str(error)}")
        db.rollback()
        return False

    async def _perform_corpus_deletion(self, db: AsyncSession, db_corpus: models.Corpus, corpus_id: str) -> bool:
        """Perform corpus deletion with notification"""
        self._delete_corpus_from_db(db, db_corpus)
        await self._send_deletion_notification(corpus_id)
        central_logger.info(f"Deleted corpus record {corpus_id}")
        return True

    async def delete_corpus_record(
        self,
        db: AsyncSession,
        corpus_id: str
    ) -> bool:
        """Delete corpus record from PostgreSQL"""
        try:
            db_corpus = await self.get_corpus(db, corpus_id)
            if not db_corpus:
                return False
            return await self._perform_corpus_deletion(db, db_corpus, corpus_id)
        except Exception as e:
            return self._handle_deletion_error(db, corpus_id, e)