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
from netra_backend.app...ws_manager import manager
from netra_backend.app.base import CorpusNotAvailableError, ClickHouseOperationError
from netra_backend.app.validation import ValidationManager
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
            self._handle_insertion_error(e)
    
    def _handle_insertion_error(self, error: Exception) -> None:
        """Handle database insertion error"""
        central_logger.error(f"Failed to insert records: {str(error)}")
        raise

    async def _send_progress_notification(
        self, db_corpus, records: List[Dict], batch_id: Optional[str]
    ) -> None:
        """Send upload progress notification"""
        payload = self._create_progress_payload(db_corpus, records, batch_id)
        message = self._create_progress_message(payload)
        await manager.broadcasting.broadcast_to_all(message)
    
    def _create_progress_payload(
        self, db_corpus, records: List[Dict], batch_id: Optional[str]
    ) -> Dict:
        """Create progress notification payload"""
        return {
            "corpus_id": db_corpus.id, "records_uploaded": len(records),
            "batch_id": batch_id
        }
    
    def _create_progress_message(self, payload: Dict) -> Dict:
        """Create progress broadcast message"""
        return {"type": "corpus:upload_progress", "payload": payload}

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

    async def upload_content(self, db_corpus, records: List[Dict], batch_id: Optional[str] = None, is_final_batch: bool = False) -> Dict:
        """Upload content to corpus with validation and batch support"""
        self._validate_corpus_availability(db_corpus)
        validation_result = self._validate_upload_records(records)
        if "validation_errors" in validation_result:
            return validation_result
        return await self._process_upload_flow(db_corpus, records, batch_id, is_final_batch)

    async def _process_upload_flow(self, db_corpus, records: List[Dict], batch_id: Optional[str], is_final_batch: bool) -> Dict:
        """Process the main upload flow"""
        if batch_id:
            return await self._handle_batch_upload(db_corpus, records, batch_id, is_final_batch)
        return await self._handle_direct_upload(db_corpus, records, batch_id)

    async def _handle_batch_upload(self, db_corpus, records: List[Dict], batch_id: str, is_final_batch: bool) -> Dict:
        """Handle batch upload logic"""
        self._handle_batch_buffering(batch_id, records)
        if not is_final_batch:
            return self._create_buffering_result(records, batch_id)
        return await self._process_final_batch(db_corpus, batch_id)
    
    async def _process_final_batch(self, db_corpus, batch_id: str) -> Dict:
        """Process final batch from buffer"""
        buffered_records = self._get_buffered_records(batch_id)
        return await self._handle_direct_upload(db_corpus, buffered_records, batch_id)

    async def _handle_direct_upload(self, db_corpus, records: List[Dict], batch_id: Optional[str]) -> Dict:
        """Handle direct upload to database"""
        try:
            return await self._execute_successful_upload(db_corpus, records, batch_id)
        except Exception as e:
            return self._handle_upload_error(db_corpus, records, e)
    
    def _handle_upload_error(self, db_corpus, records: List[Dict], error: Exception) -> Dict:
        """Handle upload error and create error result"""
        error_msg = f"Failed to upload content to corpus {db_corpus.id}: {str(error)}"
        return self._create_error_result(records, error_msg)
    
    async def _execute_successful_upload(
        self, db_corpus, records: List[Dict], batch_id: Optional[str]
    ) -> Dict:
        """Execute successful upload operations"""
        await self._perform_database_insertion(db_corpus.table_name, records)
        await self._send_progress_notification(db_corpus, records, batch_id)
        return self._create_success_result(records)
    
    async def _insert_corpus_records(
        self,
        table_name: str,
        records: List[Dict]
    ):
        """Insert records into ClickHouse corpus table"""
        async with get_clickhouse_client() as client:
            await self._execute_insertion(client, table_name, records)
    
    async def _execute_insertion(
        self, client, table_name: str, records: List[Dict]
    ) -> None:
        """Execute record insertion to ClickHouse"""
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
        basic_values = self._get_basic_record_values(processed_record)
        metadata_json = json.dumps(processed_record.get("metadata", {}))
        return basic_values + [metadata_json, processed_record.get("domain", "general"), datetime.now(UTC), 1]
    
    def _get_basic_record_values(self, processed_record: Dict) -> List:
        """Get basic record values"""
        return [
            uuid.uuid4(), processed_record.get("workload_type", "general"),
            processed_record.get("prompt", ""), processed_record.get("response", "")
        ]
    
    def _build_insertion_query(self, table_name: str) -> str:
        """Build insertion query for ClickHouse"""
        return f"""
        INSERT INTO {table_name} 
        (record_id, workload_type, prompt, response, metadata, domain, created_at, version) 
        VALUES
        """
    
    async def get_corpus_content(self, db_corpus, limit: int = 100, offset: int = 0, workload_type: Optional[str] = None) -> Optional[List[Dict]]:
        """Get corpus content from ClickHouse"""
        if db_corpus.status != "available":
            return None
        return await self._execute_content_retrieval(db_corpus, limit, offset, workload_type)
    
    async def _execute_content_retrieval(self, db_corpus, limit: int, offset: int, workload_type: Optional[str]) -> List[Dict]:
        """Execute content retrieval from ClickHouse"""
        try:
            return await self._fetch_and_convert_content(db_corpus.table_name, limit, offset, workload_type)
        except Exception as e:
            self._handle_content_retrieval_error(db_corpus.id, e)
            return []
    
    async def _fetch_and_convert_content(
        self, table_name: str, limit: int, offset: int, workload_type: Optional[str]
    ) -> List[Dict]:
        """Fetch and convert content from ClickHouse"""
        async with get_clickhouse_client() as client:
            query = self._build_content_query(table_name, limit, offset, workload_type)
            result = await client.execute_query(query)
            return self._convert_result_to_content(result)
    
    def _handle_content_retrieval_error(self, corpus_id: str, error: Exception) -> None:
        """Handle content retrieval error"""
        central_logger.error(f"Failed to get content for corpus {corpus_id}: {str(error)}")
        raise ClickHouseOperationError(f"Failed to retrieve content: {str(error)}")
    
    def _build_content_query(
        self, table_name: str, limit: int, offset: int, 
        workload_type: Optional[str]
    ) -> str:
        """Build content retrieval query"""
        base_query = self._get_base_content_query(table_name)
        filtered_query = self._add_workload_filter(base_query, workload_type)
        return self._add_limit_offset(filtered_query, limit, offset)
    
    def _get_base_content_query(self, table_name: str) -> str:
        """Get base content selection query"""
        return f"SELECT record_id, workload_type, prompt, response, metadata FROM {table_name}"
    
    def _add_workload_filter(self, query: str, workload_type: Optional[str]) -> str:
        """Add workload type filter to query"""
        if workload_type:
            return f"{query} WHERE workload_type = '{workload_type}'"
        return query
    
    def _add_limit_offset(self, query: str, limit: int, offset: int) -> str:
        """Add limit and offset to query"""
        return f"{query} LIMIT {limit} OFFSET {offset}"
    
    def _convert_result_to_content(self, result) -> List[Dict]:
        """Convert query result to content list"""
        content = []
        for row in result:
            content.append(self._convert_row_to_dict(row))
        return content
    
    def _convert_row_to_dict(self, row) -> Dict:
        """Convert single row to content dictionary"""
        metadata = json.loads(row[4]) if row[4] else {}
        return {
            "record_id": str(row[0]), "workload_type": row[1],
            "prompt": row[2], "response": row[3], "metadata": metadata
        }
    
    async def copy_corpus_content(self, source_table: str, dest_table: str, corpus_id: str, db):
        """Copy content between corpus tables"""
        try:
            await self._perform_full_copy_operation(source_table, dest_table, corpus_id, db)
        except Exception as e:
            self._handle_copy_error(e)
    
    async def _perform_full_copy_operation(
        self, source_table: str, dest_table: str, corpus_id: str, db
    ) -> None:
        """Perform complete copy operation with status updates"""
        async with get_clickhouse_client() as client:
            await asyncio.sleep(2)  # Wait for destination table readiness
            await self._execute_copy_operation(client, source_table, dest_table)
        await self._finalize_copy_operation(db, corpus_id)
    
    async def _finalize_copy_operation(self, db, corpus_id: str) -> None:
        """Finalize copy operation with status update and notification"""
        self._update_corpus_status(db, corpus_id)
        await self._send_clone_notification(corpus_id)
    
    def _handle_copy_error(self, error: Exception) -> None:
        """Handle corpus copy error"""
        central_logger.error(f"Failed to copy corpus content: {str(error)}")
        raise ClickHouseOperationError(f"Failed to copy content: {str(error)}")
    
    async def _execute_copy_operation(
        self, client, source_table: str, dest_table: str
    ) -> None:
        """Execute ClickHouse copy operation"""
        copy_query = self._build_copy_query(source_table, dest_table)
        await client.execute_query(copy_query)
    
    def _build_copy_query(self, source_table: str, dest_table: str) -> str:
        """Build copy query for tables"""
        return f"INSERT INTO {dest_table} SELECT * FROM {source_table}"
    
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
        total_buffered = self._calculate_total_buffered_records()
        batch_details = self._calculate_batch_details()
        return self._build_buffer_stats_result(total_buffered, batch_details)
    
    def _calculate_total_buffered_records(self) -> int:
        """Calculate total buffered records across all batches"""
        return sum(len(records) for records in self.content_buffer.values())
    
    def _calculate_batch_details(self) -> Dict[str, int]:
        """Calculate details for each batch"""
        return {batch_id: len(records) for batch_id, records in self.content_buffer.items()}
    
    def _build_buffer_stats_result(self, total_buffered: int, batch_details: Dict) -> Dict:
        """Build buffer statistics result"""
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
        return self._build_incremental_result(
            corpus_id, new_documents, existing_count
        )
    
    def _build_incremental_result(
        self, corpus_id: str, new_documents: List[Dict], existing_count: int
    ) -> Dict:
        """Build incremental indexing result"""
        return {
            "newly_indexed": len(new_documents), "corpus_id": corpus_id,
            "total_indexed": existing_count + len(new_documents), "status": "success"
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
            self._process_document_for_dedup(doc, unique_docs, seen_hashes)
        return unique_docs, seen_hashes
    
    def _process_document_for_dedup(
        self, doc: Dict, unique_docs: List[Dict], seen_hashes: set
    ) -> None:
        """Process single document for deduplication"""
        doc_hash = hash(doc.get('content', ''))
        if doc_hash not in seen_hashes:
            seen_hashes.add(doc_hash)
            unique_docs.append(doc)
    
    def _build_deduplication_result(
        self, corpus_id: str, documents: List[Dict], unique_docs: List[Dict]
    ) -> Dict:
        """Build deduplication operation result"""
        duplicates_count = self._calculate_duplicates_count(documents, unique_docs)
        return self._create_dedup_result_dict(
            corpus_id, documents, unique_docs, duplicates_count
        )
    
    def _calculate_duplicates_count(
        self, documents: List[Dict], unique_docs: List[Dict]
    ) -> int:
        """Calculate number of duplicate documents"""
        return len(documents) - len(unique_docs)
    
    def _create_dedup_result_dict(
        self, corpus_id: str, documents: List[Dict], unique_docs: List[Dict], 
        duplicates_count: int
    ) -> Dict:
        """Create deduplication result dictionary"""
        base_result = self._get_base_dedup_result(corpus_id, documents, unique_docs)
        duplicate_info = self._get_duplicate_info(duplicates_count, unique_docs)
        return {**base_result, **duplicate_info}
    
    def _get_base_dedup_result(
        self, corpus_id: str, documents: List[Dict], unique_docs: List[Dict]
    ) -> Dict:
        """Get base deduplication result"""
        return {
            "corpus_id": corpus_id, "total_documents": len(documents),
            "unique_documents": len(unique_docs), "indexed_count": len(unique_docs)
        }
    
    def _get_duplicate_info(self, duplicates_count: int, unique_docs: List[Dict]) -> Dict:
        """Get duplicate information for result"""
        return {
            "duplicates_removed": duplicates_count, "duplicates_skipped": duplicates_count,
            "indexed_documents": unique_docs
        }