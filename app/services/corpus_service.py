"""
Corpus Management Service
Manages corpus lifecycle including creation, content upload, validation, and ClickHouse storage
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
from sqlalchemy.orm import Session

from ..db import models_postgres as models
from .. import schemas
from ..ws_manager import manager
from ..db.clickhouse import get_clickhouse_client
from ..db.models_clickhouse import get_content_corpus_schema
from app.logging_config import central_logger


class CorpusStatus(Enum):
    """Corpus lifecycle status"""
    CREATING = "creating"
    AVAILABLE = "available"
    FAILED = "failed"
    UPDATING = "updating"
    DELETING = "deleting"


class ContentSource(Enum):
    """Source of corpus content"""
    UPLOAD = "upload"
    GENERATE = "generate"
    IMPORT = "import"


class CorpusService:
    """Service for managing corpus lifecycle and content"""
    
    def __init__(self):
        self.validation_cache: Dict[str, bool] = {}
        self.content_buffer: Dict[str, List[Dict]] = {}
        
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
        # Generate unique table name
        corpus_id = str(uuid.uuid4())
        table_name = f"netra_content_corpus_{corpus_id.replace('-', '_')}"
        
        # Create PostgreSQL record
        db_corpus = models.Corpus(
            id=corpus_id,
            name=corpus_data.name,
            description=corpus_data.description,
            table_name=table_name,
            status=CorpusStatus.CREATING.value,
            created_by_id=user_id,
            domain=corpus_data.domain if hasattr(corpus_data, 'domain') else 'general',
            metadata=json.dumps({
                "content_source": content_source.value,
                "created_at": datetime.utcnow().isoformat(),
                "version": 1
            })
        )
        db.add(db_corpus)
        db.commit()
        db.refresh(db_corpus)
        
        # Create ClickHouse table asynchronously
        asyncio.create_task(self._create_clickhouse_table(corpus_id, table_name, db))
        
        return db_corpus
    
    async def _create_clickhouse_table(
        self,
        corpus_id: str,
        table_name: str,
        db: Session
    ):
        """Create ClickHouse table for corpus content"""
        try:
            async with get_clickhouse_client() as client:
                # Create table with comprehensive schema
                create_query = f"""
                    CREATE TABLE IF NOT EXISTS {table_name} (
                        record_id UUID,
                        workload_type String,
                        prompt String,
                        response String,
                        metadata String,
                        domain String,
                        created_at DateTime64(3) DEFAULT now(),
                        version UInt32 DEFAULT 1
                    ) ENGINE = MergeTree()
                    PARTITION BY toYYYYMM(created_at)
                    ORDER BY (workload_type, created_at, record_id)
                """
                
                await client.execute(create_query)
                
                # Update status to available
                db.query(models.Corpus).filter(
                    models.Corpus.id == corpus_id
                ).update({"status": CorpusStatus.AVAILABLE.value})
                db.commit()
                
                # Send WebSocket notification
                await manager.broadcast(json.dumps({
                    "type": "corpus:created",
                    "payload": {
                        "corpus_id": corpus_id,
                        "table_name": table_name,
                        "status": CorpusStatus.AVAILABLE.value
                    }
                }))
                
                central_logger.info(f"Created ClickHouse table {table_name} for corpus {corpus_id}")
                
        except Exception as e:
            central_logger.error(f"Failed to create ClickHouse table for corpus {corpus_id}: {str(e)}")
            
            # Update status to failed
            db.query(models.Corpus).filter(
                models.Corpus.id == corpus_id
            ).update({"status": CorpusStatus.FAILED.value})
            db.commit()
            
            # Send error notification
            await manager.broadcast(json.dumps({
                "type": "corpus:error",
                "payload": {
                    "corpus_id": corpus_id,
                    "error": str(e)
                }
            }))
    
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
        db_corpus = db.query(models.Corpus).filter(
            models.Corpus.id == corpus_id
        ).first()
        
        if not db_corpus:
            raise ValueError(f"Corpus {corpus_id} not found")
        
        if db_corpus.status != CorpusStatus.AVAILABLE.value:
            raise ValueError(f"Corpus {corpus_id} is not available for upload")
        
        # Validate records
        validation_result = self._validate_records(records)
        
        if not validation_result["valid"]:
            return {
                "records_uploaded": 0,
                "records_validated": 0,
                "validation_errors": validation_result["errors"]
            }
        
        # Buffer records if using batch upload
        if batch_id:
            if batch_id not in self.content_buffer:
                self.content_buffer[batch_id] = []
            self.content_buffer[batch_id].extend(records)
            
            if not is_final_batch:
                return {
                    "records_buffered": len(records),
                    "batch_id": batch_id,
                    "status": "buffering"
                }
            
            # Process all buffered records
            records = self.content_buffer.pop(batch_id, [])
        
        # Insert records to ClickHouse
        try:
            await self._insert_corpus_records(db_corpus.table_name, records)
            
            # Send progress notification
            await manager.broadcast(json.dumps({
                "type": "corpus:upload_progress",
                "payload": {
                    "corpus_id": corpus_id,
                    "records_uploaded": len(records),
                    "batch_id": batch_id
                }
            }))
            
            return {
                "records_uploaded": len(records),
                "records_validated": len(records),
                "validation_errors": []
            }
            
        except Exception as e:
            central_logger.error(f"Failed to upload content to corpus {corpus_id}: {str(e)}")
            return {
                "records_uploaded": 0,
                "records_validated": len(records),
                "validation_errors": [str(e)]
            }
    
    def _validate_records(self, records: List[Dict]) -> Dict:
        """Validate corpus records"""
        errors = []
        
        for i, record in enumerate(records):
            # Check required fields
            if "prompt" not in record:
                errors.append(f"Record {i}: missing 'prompt' field")
            if "response" not in record:
                errors.append(f"Record {i}: missing 'response' field")
            if "workload_type" not in record:
                errors.append(f"Record {i}: missing 'workload_type' field")
            
            # Validate workload type
            valid_types = [
                "simple_chat", "rag_pipeline", "tool_use",
                "multi_turn_tool_use", "failed_request", "custom_domain"
            ]
            if record.get("workload_type") not in valid_types:
                errors.append(f"Record {i}: invalid workload_type '{record.get('workload_type')}'")
            
            # Check field lengths
            if len(record.get("prompt", "")) > 100000:
                errors.append(f"Record {i}: prompt exceeds maximum length")
            if len(record.get("response", "")) > 100000:
                errors.append(f"Record {i}: response exceeds maximum length")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
    
    async def _insert_corpus_records(
        self,
        table_name: str,
        records: List[Dict]
    ):
        """Insert records into ClickHouse corpus table"""
        async with get_clickhouse_client() as client:
            # Prepare values for insertion
            values = []
            for record in records:
                values.append([
                    uuid.uuid4(),  # record_id
                    record.get("workload_type", "general"),
                    record.get("prompt", ""),
                    record.get("response", ""),
                    json.dumps(record.get("metadata", {})),
                    record.get("domain", "general"),
                    datetime.utcnow(),  # created_at
                    1  # version
                ])
            
            # Batch insert
            await client.execute(
                f"""INSERT INTO {table_name} 
                (record_id, workload_type, prompt, response, metadata, domain, created_at, version)
                VALUES""",
                values
            )
    
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
    
    async def update_corpus(
        self,
        db: Session,
        corpus_id: str,
        update_data: schemas.CorpusUpdate
    ) -> Optional[models.Corpus]:
        """Update corpus metadata"""
        db_corpus = await self.get_corpus(db, corpus_id)
        
        if not db_corpus:
            return None
        
        # Update fields
        for key, value in update_data.model_dump(exclude_unset=True).items():
            setattr(db_corpus, key, value)
        
        # Update metadata
        metadata = json.loads(db_corpus.metadata or "{}")
        metadata["updated_at"] = datetime.utcnow().isoformat()
        metadata["version"] = metadata.get("version", 1) + 1
        db_corpus.metadata = json.dumps(metadata)
        
        db.commit()
        db.refresh(db_corpus)
        
        return db_corpus
    
    async def delete_corpus(
        self,
        db: Session,
        corpus_id: str
    ) -> bool:
        """Delete corpus and associated ClickHouse table"""
        db_corpus = await self.get_corpus(db, corpus_id)
        
        if not db_corpus:
            return False
        
        try:
            # Update status to deleting
            db_corpus.status = CorpusStatus.DELETING.value
            db.commit()
            
            # Drop ClickHouse table
            async with get_clickhouse_client() as client:
                await client.execute(f"DROP TABLE IF EXISTS {db_corpus.table_name}")
            
            # Delete PostgreSQL record
            db.delete(db_corpus)
            db.commit()
            
            # Send deletion notification
            await manager.broadcast(json.dumps({
                "type": "corpus:deleted",
                "payload": {
                    "corpus_id": corpus_id
                }
            }))
            
            return True
            
        except Exception as e:
            central_logger.error(f"Failed to delete corpus {corpus_id}: {str(e)}")
            
            # Revert status
            db_corpus.status = CorpusStatus.FAILED.value
            db.commit()
            
            return False
    
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
        
        if not db_corpus or db_corpus.status != CorpusStatus.AVAILABLE.value:
            return None
        
        try:
            async with get_clickhouse_client() as client:
                # Build query
                query = f"""
                    SELECT record_id, workload_type, prompt, response, metadata
                    FROM {db_corpus.table_name}
                """
                
                if workload_type:
                    query += f" WHERE workload_type = '{workload_type}'"
                
                query += f" LIMIT {limit} OFFSET {offset}"
                
                result = await client.execute(query)
                
                # Convert to list of dicts
                content = []
                for row in result:
                    content.append({
                        "record_id": str(row[0]),
                        "workload_type": row[1],
                        "prompt": row[2],
                        "response": row[3],
                        "metadata": json.loads(row[4]) if row[4] else {}
                    })
                
                return content
                
        except Exception as e:
            central_logger.error(f"Failed to get content for corpus {corpus_id}: {str(e)}")
            return None
    
    async def get_corpus_statistics(
        self,
        db: Session,
        corpus_id: str
    ) -> Optional[Dict]:
        """Get corpus statistics from ClickHouse"""
        db_corpus = await self.get_corpus(db, corpus_id)
        
        if not db_corpus or db_corpus.status != CorpusStatus.AVAILABLE.value:
            return None
        
        try:
            async with get_clickhouse_client() as client:
                # Get statistics
                stats_query = f"""
                    SELECT 
                        COUNT(*) as total_records,
                        COUNT(DISTINCT workload_type) as unique_workload_types,
                        AVG(LENGTH(prompt)) as avg_prompt_length,
                        AVG(LENGTH(response)) as avg_response_length,
                        MIN(created_at) as first_record,
                        MAX(created_at) as last_record
                    FROM {db_corpus.table_name}
                """
                
                stats_result = await client.execute(stats_query)
                
                # Get workload distribution
                dist_query = f"""
                    SELECT workload_type, COUNT(*) as count
                    FROM {db_corpus.table_name}
                    GROUP BY workload_type
                """
                
                dist_result = await client.execute(dist_query)
                
                # Format statistics
                stats = {}
                if stats_result:
                    row = stats_result[0]
                    stats = {
                        "total_records": row[0],
                        "unique_workload_types": row[1],
                        "avg_prompt_length": row[2],
                        "avg_response_length": row[3],
                        "first_record": row[4].isoformat() if row[4] else None,
                        "last_record": row[5].isoformat() if row[5] else None
                    }
                
                # Add workload distribution
                stats["workload_distribution"] = {
                    row[0]: row[1] for row in dist_result
                }
                
                return stats
                
        except Exception as e:
            central_logger.error(f"Failed to get statistics for corpus {corpus_id}: {str(e)}")
            return None
    
    async def clone_corpus(
        self,
        db: Session,
        source_corpus_id: str,
        new_name: str,
        user_id: str
    ) -> Optional[models.Corpus]:
        """Clone an existing corpus"""
        source_corpus = await self.get_corpus(db, source_corpus_id)
        
        if not source_corpus or source_corpus.status != CorpusStatus.AVAILABLE.value:
            return None
        
        # Create new corpus
        new_corpus = await self.create_corpus(
            db,
            schemas.CorpusCreate(
                name=new_name,
                description=f"Clone of {source_corpus.name}",
                domain=source_corpus.domain
            ),
            user_id
        )
        
        # Copy content asynchronously
        asyncio.create_task(
            self._copy_corpus_content(
                source_corpus.table_name,
                new_corpus.table_name,
                new_corpus.id,
                db
            )
        )
        
        return new_corpus
    
    async def _copy_corpus_content(
        self,
        source_table: str,
        dest_table: str,
        corpus_id: str,
        db: Session
    ):
        """Copy content between corpus tables"""
        try:
            async with get_clickhouse_client() as client:
                # Wait for destination table to be ready
                await asyncio.sleep(2)
                
                # Copy data
                copy_query = f"""
                    INSERT INTO {dest_table}
                    SELECT * FROM {source_table}
                """
                
                await client.execute(copy_query)
                
                # Update status
                db.query(models.Corpus).filter(
                    models.Corpus.id == corpus_id
                ).update({"status": CorpusStatus.AVAILABLE.value})
                db.commit()
                
                # Send notification
                await manager.broadcast(json.dumps({
                    "type": "corpus:clone_complete",
                    "payload": {
                        "corpus_id": corpus_id
                    }
                }))
                
        except Exception as e:
            central_logger.error(f"Failed to copy corpus content: {str(e)}")
            
            # Update status to failed
            db.query(models.Corpus).filter(
                models.Corpus.id == corpus_id
            ).update({"status": CorpusStatus.FAILED.value})
            db.commit()


# Create singleton instance
corpus_service = CorpusService()


# Legacy functions for backward compatibility
def get_corpus(db: Session, corpus_id: str):
    """Legacy function to get corpus"""
    return asyncio.run(corpus_service.get_corpus(db, corpus_id))


def get_corpora(db: Session, skip: int = 0, limit: int = 100):
    """Legacy function to get corpora list"""
    return asyncio.run(corpus_service.get_corpora(db, skip, limit))


def create_corpus(db: Session, corpus: schemas.CorpusCreate, user_id: str):
    """Legacy function to create corpus"""
    return asyncio.run(corpus_service.create_corpus(db, corpus, user_id))


def update_corpus(db: Session, corpus_id: str, corpus: schemas.CorpusUpdate):
    """Legacy function to update corpus"""
    return asyncio.run(corpus_service.update_corpus(db, corpus_id, corpus))


def delete_corpus(db: Session, corpus_id: str):
    """Legacy function to delete corpus"""
    return asyncio.run(corpus_service.delete_corpus(db, corpus_id))


async def generate_corpus_task(corpus_id: str, db: Session):
    """Legacy task function - now just ensures table creation"""
    db_corpus = await corpus_service.get_corpus(db, corpus_id)
    if not db_corpus:
        return
    
    # Table creation is handled in create_corpus
    # This function is kept for backward compatibility


def get_corpus_status(db: Session, corpus_id: str):
    """Legacy function to get corpus status"""
    db_corpus = asyncio.run(corpus_service.get_corpus(db, corpus_id))
    return db_corpus.status if db_corpus else None


async def get_corpus_content(db: Session, corpus_id: str):
    """Legacy function to get corpus content"""
    return await corpus_service.get_corpus_content(db, corpus_id)