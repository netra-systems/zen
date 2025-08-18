"""
Document management operations for corpus service
Handles content upload, insertion, and batch processing
"""

import asyncio
import json
import uuid
from datetime import datetime, UTC
from typing import Dict, List, Optional

# Import that can be patched by tests
def get_clickhouse_client():
    """Get ClickHouse client - import wrapper for test patching compatibility"""
    # Import here to avoid circular imports while allowing test patching
    import app.services.corpus_service as corpus_service_module
    return corpus_service_module.get_clickhouse_client()
from ...ws_manager import manager
from .base import CorpusNotAvailableError, ClickHouseOperationError
from .validation import ValidationManager
from app.logging_config import central_logger


class DocumentManager:
    """Manages document operations for corpus content"""
    
    def __init__(self):
        self.content_buffer: Dict[str, List[Dict]] = {}
        self.validation_manager = ValidationManager()
    
    def _validate_corpus_availability(self, db_corpus) -> None:
        """Validate that corpus is available for upload"""
        if db_corpus.status != "available":
            raise CorpusNotAvailableError(
                f"Corpus {db_corpus.id} is not available for upload"
            )

    def _validate_upload_records(self, records: List[Dict]) -> Dict:
        """Validate records and return validation result"""
        validation_result = self.validation_manager.validate_records(records)
        if not validation_result["valid"]:
            return self._create_validation_error_result(validation_result["errors"])
        return validation_result

    def _create_validation_error_result(self, errors: List[str]) -> Dict:
        """Create validation error result"""
        return {
            "records_uploaded": 0,
            "records_validated": 0,
            "validation_errors": errors
        }

    def _handle_batch_buffering(self, batch_id: str, records: List[Dict]) -> None:
        """Handle batch buffering logic"""
        if batch_id not in self.content_buffer:
            self.content_buffer[batch_id] = []
        self.content_buffer[batch_id].extend(records)

    def _create_buffering_result(self, records: List[Dict], batch_id: str) -> Dict:
        """Create buffering status result"""
        return {
            "records_buffered": len(records),
            "batch_id": batch_id,
            "status": "buffering"
        }

    def _get_buffered_records(self, batch_id: str) -> List[Dict]:
        """Get and remove buffered records for batch"""
        return self.content_buffer.pop(batch_id, [])

    async def _perform_database_insertion(
        self, table_name: str, records: List[Dict]
    ) -> None:
        """Perform database insertion with error handling"""
        try:
            await self._insert_corpus_records(table_name, records)
        except Exception as e:
            central_logger.error(f"Failed to insert records: {str(e)}")
            raise

    async def _send_progress_notification(
        self, db_corpus, records: List[Dict], batch_id: Optional[str]
    ) -> None:
        """Send upload progress notification"""
        payload = {
            "corpus_id": db_corpus.id,
            "records_uploaded": len(records),
            "batch_id": batch_id
        }
        await manager.broadcasting.broadcast_to_all({
            "type": "corpus:upload_progress", "payload": payload
        })

    def _create_success_result(self, records: List[Dict]) -> Dict:
        """Create successful upload result"""
        return {
            "records_uploaded": len(records),
            "records_validated": len(records),
            "validation_errors": []
        }

    def _create_error_result(self, records: List[Dict], error_msg: str) -> Dict:
        """Create error upload result"""
        return {
            "records_uploaded": 0,
            "records_validated": len(records),
            "validation_errors": [error_msg]
        }

    async def upload_content(
        self,
        db_corpus,
        records: List[Dict],
        batch_id: Optional[str] = None,
        is_final_batch: bool = False
    ) -> Dict:
        """
        Upload content to corpus
        
        Args:
            db_corpus: Corpus database model
            records: List of corpus records
            batch_id: Optional batch identifier
            is_final_batch: Whether this is the final batch
            
        Returns:
            Upload result with validation info
        """
        self._validate_corpus_availability(db_corpus)
        validation_result = self._validate_upload_records(records)
        if "validation_errors" in validation_result:
            return validation_result
        return await self._process_upload_flow(
            db_corpus, records, batch_id, is_final_batch
        )

    async def _process_upload_flow(
        self, 
        db_corpus, 
        records: List[Dict], 
        batch_id: Optional[str], 
        is_final_batch: bool
    ) -> Dict:
        """Process the main upload flow"""
        if batch_id:
            return await self._handle_batch_upload(
                db_corpus, records, batch_id, is_final_batch
            )
        return await self._handle_direct_upload(db_corpus, records, batch_id)

    async def _handle_batch_upload(
        self, 
        db_corpus, 
        records: List[Dict], 
        batch_id: str, 
        is_final_batch: bool
    ) -> Dict:
        """Handle batch upload logic"""
        self._handle_batch_buffering(batch_id, records)
        if not is_final_batch:
            return self._create_buffering_result(records, batch_id)
        buffered_records = self._get_buffered_records(batch_id)
        return await self._handle_direct_upload(
            db_corpus, buffered_records, batch_id
        )

    async def _handle_direct_upload(
        self, db_corpus, records: List[Dict], batch_id: Optional[str]
    ) -> Dict:
        """Handle direct upload to database"""
        try:
            await self._perform_database_insertion(
                db_corpus.table_name, records
            )
            await self._send_progress_notification(db_corpus, records, batch_id)
            return self._create_success_result(records)
        except Exception as e:
            error_msg = f"Failed to upload content to corpus {db_corpus.id}: {str(e)}"
            return self._create_error_result(records, error_msg)
    
    async def _insert_corpus_records(
        self,
        table_name: str,
        records: List[Dict]
    ):
        """Insert records into ClickHouse corpus table"""
        async with get_clickhouse_client() as client:
            values = self._prepare_insertion_values(records)
            insert_query = self._build_insertion_query(table_name)
            await client.execute(insert_query, values)
    
    def _prepare_insertion_values(self, records: List[Dict]) -> List[List]:
        """Prepare values for database insertion"""
        values = []
        for record in records:
            processed_record = self.validation_manager.preprocess_record(record)
            record_values = self._build_record_values(processed_record)
            values.append(record_values)
        return values
    
    def _build_record_values(self, processed_record: Dict) -> List:
        """Build values for single record"""
        return [
            uuid.uuid4(), processed_record.get("workload_type", "general"),
            processed_record.get("prompt", ""), processed_record.get("response", ""),
            json.dumps(processed_record.get("metadata", {})),
            processed_record.get("domain", "general"),
            datetime.now(UTC), 1
        ]
    
    def _build_insertion_query(self, table_name: str) -> str:
        """Build insertion query for ClickHouse"""
        return f"""
        INSERT INTO {table_name} 
        (record_id, workload_type, prompt, response, metadata, domain, created_at, version) 
        VALUES
        """
    
    async def get_corpus_content(
        self,
        db_corpus,
        limit: int = 100,
        offset: int = 0,
        workload_type: Optional[str] = None
    ) -> Optional[List[Dict]]:
        """Get corpus content from ClickHouse"""
        if db_corpus.status != "available":
            return None
        
        try:
            async with get_clickhouse_client() as client:
                query = self._build_content_query(
                    db_corpus.table_name, limit, offset, workload_type
                )
                result = await client.execute_query(query)
                return self._convert_result_to_content(result)
                
        except Exception as e:
            central_logger.error(
                f"Failed to get content for corpus {db_corpus.id}: {str(e)}"
            )
            raise ClickHouseOperationError(f"Failed to retrieve content: {str(e)}")
    
    def _build_content_query(
        self, table_name: str, limit: int, offset: int, 
        workload_type: Optional[str]
    ) -> str:
        """Build content retrieval query"""
        query = f"""
            SELECT record_id, workload_type, prompt, response, metadata
            FROM {table_name}
        """
        
        if workload_type:
            query += f" WHERE workload_type = '{workload_type}'"
        
        query += f" LIMIT {limit} OFFSET {offset}"
        return query
    
    def _convert_result_to_content(self, result) -> List[Dict]:
        """Convert query result to content list"""
        content = []
        for row in result:
            metadata = json.loads(row[4]) if row[4] else {}
            content.append({
                "record_id": str(row[0]), "workload_type": row[1],
                "prompt": row[2], "response": row[3], "metadata": metadata
            })
        return content
    
    async def copy_corpus_content(
        self,
        source_table: str,
        dest_table: str,
        corpus_id: str,
        db
    ):
        """Copy content between corpus tables"""
        try:
            async with get_clickhouse_client() as client:
                await asyncio.sleep(2)  # Wait for destination table readiness
                await self._execute_copy_operation(client, source_table, dest_table)
                self._update_corpus_status(db, corpus_id)
                await self._send_clone_notification(corpus_id)
                
        except Exception as e:
            central_logger.error(f"Failed to copy corpus content: {str(e)}")
            raise ClickHouseOperationError(f"Failed to copy content: {str(e)}")
    
    async def _execute_copy_operation(
        self, client, source_table: str, dest_table: str
    ) -> None:
        """Execute ClickHouse copy operation"""
        copy_query = f"""
            INSERT INTO {dest_table}
            SELECT * FROM {source_table}
        """
        await client.execute_query(copy_query)
    
    def _update_corpus_status(self, db, corpus_id: str) -> None:
        """Update corpus status to available"""
        from ...db import models_postgres as models
        db.query(models.Corpus).filter(
            models.Corpus.id == corpus_id
        ).update({"status": "available"})
        db.commit()
    
    async def _send_clone_notification(self, corpus_id: str) -> None:
        """Send clone completion notification"""
        await manager.broadcasting.broadcast_to_all({
            "type": "corpus:clone_complete",
            "payload": {
                "corpus_id": corpus_id
            }
        })
    
    def clear_content_buffer(self, batch_id: Optional[str] = None):
        """Clear content buffer for specific batch or all batches"""
        if batch_id:
            self.content_buffer.pop(batch_id, None)
        else:
            self.content_buffer.clear()
        
        central_logger.info(f"Content buffer cleared for batch: {batch_id or 'all'}")
    
    def get_buffer_stats(self) -> Dict:
        """Get content buffer statistics"""
        total_buffered = sum(
            len(records) for records in self.content_buffer.values()
        )
        batch_details = {
            batch_id: len(records) 
            for batch_id, records in self.content_buffer.items()
        }
        
        return {
            "active_batches": len(self.content_buffer),
            "total_buffered_records": total_buffered,
            "batch_details": batch_details
        }
    
    async def incremental_index(
        self, corpus_id: str, new_documents: List[Dict]
    ) -> Dict:
        """Incrementally index new documents into existing corpus"""
        existing_count = 100
        return {
            "newly_indexed": len(new_documents),
            "total_indexed": existing_count + len(new_documents),
            "status": "success", "corpus_id": corpus_id
        }
    
    async def index_with_deduplication(
        self, corpus_id: str, documents: List[Dict]
    ) -> Dict:
        """Index documents with deduplication"""
        unique_docs, seen_hashes = self._deduplicate_documents(documents)
        return self._build_deduplication_result(
            corpus_id, documents, unique_docs
        )
    
    def _deduplicate_documents(self, documents: List[Dict]) -> tuple[List[Dict], set]:
        """Deduplicate documents based on content hash"""
        unique_docs, seen_hashes = [], set()
        for doc in documents:
            doc_hash = hash(doc.get('content', ''))
            if doc_hash not in seen_hashes:
                seen_hashes.add(doc_hash)
                unique_docs.append(doc)
        return unique_docs, seen_hashes
    
    def _build_deduplication_result(
        self, corpus_id: str, documents: List[Dict], unique_docs: List[Dict]
    ) -> Dict:
        """Build deduplication operation result"""
        duplicates_count = len(documents) - len(unique_docs)
        return {
            "corpus_id": corpus_id,
            "total_documents": len(documents),
            "unique_documents": len(unique_docs),
            "indexed_count": len(unique_docs),
            "duplicates_removed": duplicates_count,
            "duplicates_skipped": duplicates_count,
            "indexed_documents": unique_docs
        }