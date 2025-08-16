"""
Corpus management operations - CRUD operations for corpus metadata
"""

import json
from datetime import datetime, UTC
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from ...db import models_postgres as models
from ... import schemas
from ...ws_manager import manager
from .base import CorpusNotFoundError
from app.logging_config import central_logger


class CorpusManager:
    """Handles CRUD operations for corpus metadata"""
    
    async def get_corpus(
        self,
        db: Session,
        corpus_id: str
    ) -> Optional[models.Corpus]:
        """Get corpus by ID"""
        return db.query(models.Corpus).filter(
            models.Corpus.id == corpus_id
        ).first()
    
    async def get_corpora(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> List[models.Corpus]:
        """Get list of corpora with filtering"""
        query = db.query(models.Corpus)
        
        if status:
            query = query.filter(models.Corpus.status == status)
        if user_id:
            query = query.filter(models.Corpus.created_by_id == user_id)
        
        return query.offset(skip).limit(limit).all()
    
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

    def _commit_corpus_update(self, db: Session, db_corpus) -> models.Corpus:
        """Commit corpus update and refresh model"""
        db.commit()
        db.refresh(db_corpus)
        return db_corpus

    async def update_corpus(
        self, db: Session, corpus_id: str, update_data: schemas.CorpusUpdate
    ) -> Optional[models.Corpus]:
        """Update corpus metadata"""
        db_corpus = await self.get_corpus(db, corpus_id)
        self._validate_corpus_exists(db_corpus, corpus_id)
        self._apply_update_fields(db_corpus, update_data)
        metadata = self._load_existing_metadata(db_corpus)
        updated_metadata = self._update_metadata_version(metadata)
        self._save_updated_metadata(db_corpus, updated_metadata)
        return self._commit_corpus_update(db, db_corpus)
    
    async def clone_corpus(
        self,
        db: Session,
        source_corpus: models.Corpus,
        new_name: str,
        user_id: str
    ) -> models.Corpus:
        """
        Create a new corpus record for cloning
        
        Args:
            db: Database session
            source_corpus: Source corpus to clone
            new_name: Name for the new corpus
            user_id: User creating the clone
            
        Returns:
            Created corpus model
        """
        import uuid
        from .base import CorpusStatus, ContentSource
        
        # Generate unique table name
        corpus_id = str(uuid.uuid4())
        table_name = f"netra_content_corpus_{corpus_id.replace('-', '_')}"
        
        # Create PostgreSQL record
        db_corpus = models.Corpus(
            id=corpus_id,
            name=new_name,
            description=f"Clone of {source_corpus.name}",
            table_name=table_name,
            status=CorpusStatus.CREATING.value,
            created_by_id=user_id,
            domain=source_corpus.domain,
            metadata_=json.dumps({
                "content_source": ContentSource.IMPORT.value,
                "cloned_from": source_corpus.id,
                "created_at": datetime.now(UTC).isoformat(),
                "version": 1
            })
        )
        db.add(db_corpus)
        db.commit()
        db.refresh(db_corpus)
        
        return db_corpus
    
    async def set_corpus_status(
        self,
        db: Session,
        corpus_id: str,
        status: str
    ) -> bool:
        """
        Update corpus status
        
        Args:
            db: Database session
            corpus_id: Corpus ID
            status: New status
            
        Returns:
            True if updated successfully
        """
        try:
            updated = db.query(models.Corpus).filter(
                models.Corpus.id == corpus_id
            ).update({"status": status})
            
            if updated:
                db.commit()
                central_logger.info(f"Updated corpus {corpus_id} status to {status}")
                return True
            
            return False
            
        except Exception as e:
            central_logger.error(f"Failed to update corpus {corpus_id} status: {str(e)}")
            db.rollback()
            return False
    
    async def delete_corpus_record(
        self,
        db: Session,
        corpus_id: str
    ) -> bool:
        """
        Delete corpus record from PostgreSQL
        
        Args:
            db: Database session
            corpus_id: Corpus ID
            
        Returns:
            True if deleted successfully
        """
        try:
            db_corpus = await self.get_corpus(db, corpus_id)
            
            if not db_corpus:
                return False
            
            db.delete(db_corpus)
            db.commit()
            
            # Send deletion notification
            await manager.broadcasting.broadcast_to_all({
                "type": "corpus:deleted",
                "payload": {
                    "corpus_id": corpus_id
                }
            })
            
            central_logger.info(f"Deleted corpus record {corpus_id}")
            return True
            
        except Exception as e:
            central_logger.error(f"Failed to delete corpus record {corpus_id}: {str(e)}")
            db.rollback()
            return False