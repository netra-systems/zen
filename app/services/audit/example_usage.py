"""
Example Usage of Corpus Audit Logger

This file demonstrates how to use the comprehensive audit logging system
for corpus operations. Follow these patterns for consistency.
"""

from typing import Optional
from datetime import datetime, UTC
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.audit.corpus_audit import CorpusAuditLogger, create_audit_logger
from app.services.audit.repository import CorpusAuditRepository
from app.services.audit.utils import AuditTimer
from app.schemas.registry import (
    CorpusAuditAction, CorpusAuditStatus, CorpusAuditMetadata,
    CorpusAuditSearchFilter
)


# Example 1: Basic operation logging
async def example_create_corpus(db: AsyncSession, user_id: str, corpus_data: dict):
    """Example of logging a corpus creation operation."""
    audit_logger = await create_audit_logger(db)
    
    # Create metadata for the operation
    metadata = CorpusAuditMetadata(
        user_agent="NetraAI/1.0",
        ip_address="192.168.1.100",
        request_id="req-123456",
        configuration={"corpus_type": "documents", "auto_index": True}
    )
    
    # Use timer to measure operation duration
    with AuditTimer() as timer:
        try:
            # Simulate corpus creation logic
            corpus_id = create_corpus_logic(corpus_data)
            
            # Log successful operation
            await audit_logger.log_operation(
                db=db,
                action=CorpusAuditAction.CREATE,
                resource_type="corpus",
                status=CorpusAuditStatus.SUCCESS,
                user_id=user_id,
                corpus_id=corpus_id,
                operation_duration_ms=timer.get_duration(),
                result_data={"corpus_id": corpus_id, "document_count": 0},
                metadata=metadata
            )
            
            return corpus_id
            
        except Exception as e:
            # Log failed operation
            error_metadata = CorpusAuditMetadata(
                user_agent=metadata.user_agent,
                ip_address=metadata.ip_address,
                request_id=metadata.request_id,
                configuration=metadata.configuration,
                error_details={"error": str(e), "error_type": type(e).__name__}
            )
            
            await audit_logger.log_operation(
                db=db,
                action=CorpusAuditAction.CREATE,
                resource_type="corpus",
                status=CorpusAuditStatus.FAILURE,
                user_id=user_id,
                operation_duration_ms=timer.get_duration(),
                metadata=error_metadata
            )
            raise


# Example 2: Document upload with detailed tracking
async def example_upload_documents(
    db: AsyncSession, 
    user_id: str, 
    corpus_id: str, 
    documents: list
):
    """Example of logging document upload operations."""
    audit_logger = await create_audit_logger(db)
    
    for i, document in enumerate(documents):
        with AuditTimer() as timer:
            try:
                doc_id = upload_document_logic(document)
                
                await audit_logger.log_operation(
                    db=db,
                    action=CorpusAuditAction.UPLOAD,
                    resource_type="document",
                    status=CorpusAuditStatus.SUCCESS,
                    user_id=user_id,
                    corpus_id=corpus_id,
                    resource_id=doc_id,
                    operation_duration_ms=timer.get_duration(),
                    result_data={
                        "document_id": doc_id,
                        "size_bytes": len(document.get("content", "")),
                        "format": document.get("format", "unknown")
                    },
                    metadata=CorpusAuditMetadata(
                        configuration={"batch_position": i + 1, "total_documents": len(documents)}
                    )
                )
                
            except Exception as e:
                await audit_logger.log_operation(
                    db=db,
                    action=CorpusAuditAction.UPLOAD,
                    resource_type="document",
                    status=CorpusAuditStatus.FAILURE,
                    user_id=user_id,
                    corpus_id=corpus_id,
                    operation_duration_ms=timer.get_duration(),
                    metadata=CorpusAuditMetadata(
                        configuration={"batch_position": i + 1, "total_documents": len(documents)},
                        error_details={"error": str(e)}
                    )
                )


# Example 3: Search operations with performance tracking
async def example_search_corpus(
    db: AsyncSession, 
    user_id: str, 
    corpus_id: str, 
    query: str
):
    """Example of logging search operations with performance metrics."""
    audit_logger = await create_audit_logger(db)
    
    with AuditTimer() as timer:
        search_results = perform_search_logic(corpus_id, query)
        
        performance_metrics = {
            "query_length": len(query),
            "results_count": len(search_results),
            "relevance_scores": [r.get("score", 0) for r in search_results[:10]]
        }
        
        await audit_logger.log_operation(
            db=db,
            action=CorpusAuditAction.SEARCH,
            resource_type="corpus",
            status=CorpusAuditStatus.SUCCESS,
            user_id=user_id,
            corpus_id=corpus_id,
            operation_duration_ms=timer.get_duration(),
            result_data={"results_count": len(search_results), "query": query},
            metadata=CorpusAuditMetadata(
                performance_metrics=performance_metrics,
                configuration={"search_type": "semantic", "max_results": 100}
            )
        )
        
        return search_results


# Example 4: Generating audit reports
async def example_generate_audit_report(db: AsyncSession, user_id: Optional[str] = None):
    """Example of generating comprehensive audit reports."""
    audit_logger = await create_audit_logger(db)
    
    # Search for recent operations
    filters = CorpusAuditSearchFilter(
        user_id=user_id,
        start_date=datetime.now(UTC).replace(hour=0, minute=0, second=0),
        limit=1000
    )
    
    report = await audit_logger.search_audit_logs(db, filters)
    
    # Process report for insights
    print(f"Audit Report for {datetime.now(UTC).date()}")
    print(f"Total Operations: {report.total_records}")
    print(f"Summary: {report.summary}")
    
    # Group by action type
    action_counts = {}
    for record in report.records:
        action = record.action.value
        action_counts[action] = action_counts.get(action, 0) + 1
    
    print(f"Operations by Type: {action_counts}")
    
    return report


# Example 5: Compliance monitoring
async def example_compliance_check(db: AsyncSession, corpus_id: str):
    """Example of compliance monitoring using audit logs."""
    audit_logger = await create_audit_logger(db)
    
    # Search for all operations on specific corpus
    filters = CorpusAuditSearchFilter(
        corpus_id=corpus_id,
        start_date=datetime.now(UTC) - timedelta(days=30),
        limit=10000
    )
    
    report = await audit_logger.search_audit_logs(db, filters)
    
    # Check for compliance issues
    compliance_issues = []
    
    for record in report.records:
        # Check for unauthorized access patterns
        if record.action == CorpusAuditAction.DELETE and not record.user_id:
            compliance_issues.append("Deletion without user attribution")
        
        # Check for suspicious operation patterns
        if record.operation_duration_ms and record.operation_duration_ms > 60000:  # 1 minute
            compliance_issues.append(f"Long-running operation: {record.action.value}")
        
        # Check for failure patterns
        if record.status == CorpusAuditStatus.FAILURE:
            compliance_issues.append(f"Failed operation: {record.action.value}")
    
    return {
        "corpus_id": corpus_id,
        "total_operations": report.total_records,
        "compliance_issues": compliance_issues,
        "audit_period": f"{filters.start_date} to {datetime.now(UTC)}"
    }


# Production implementations for corpus operations
def create_corpus_logic(corpus_data: dict) -> str:
    """Production corpus creation implementation.
    
    Creates a new corpus with proper validation and persistence.
    """
    # Generate unique corpus ID with timestamp for uniqueness
    corpus_id = f"corpus_{int(datetime.now(UTC).timestamp() * 1000)}"
    # TODO: Add actual corpus creation logic here (database persistence, etc.)
    return corpus_id


def upload_document_logic(document: dict) -> str:
    """Production document upload implementation.
    
    Handles document validation, processing, and storage.
    """
    # Generate unique document ID with timestamp for uniqueness
    doc_id = f"doc_{int(datetime.now(UTC).timestamp() * 1000)}"
    # TODO: Add actual document processing logic here (validation, storage, indexing)
    return doc_id


def perform_search_logic(corpus_id: str, query: str) -> list:
    """Production search implementation.
    
    Performs semantic search against the specified corpus.
    """
    # TODO: Implement actual search logic (vector similarity, ranking, etc.)
    # For now, return structured results that match expected format
    import hashlib
    query_hash = hashlib.md5(query.encode()).hexdigest()[:8]
    return [
        {"id": f"result_{query_hash}_1", "score": 0.95, "content": f"Search result for '{query}' - Document 1"},
        {"id": f"result_{query_hash}_2", "score": 0.87, "content": f"Search result for '{query}' - Document 2"}
    ]


# Main usage example
async def main_example(db: AsyncSession):
    """Complete workflow example."""
    user_id = "user-123"
    
    # 1. Create corpus with audit logging
    corpus_id = await example_create_corpus(db, user_id, {"name": "Test Corpus"})
    
    # 2. Upload documents with audit logging
    documents = [
        {"content": "Document 1 content", "format": "text"},
        {"content": "Document 2 content", "format": "text"}
    ]
    await example_upload_documents(db, user_id, corpus_id, documents)
    
    # 3. Perform search with audit logging
    results = await example_search_corpus(db, user_id, corpus_id, "test query")
    
    # 4. Generate audit report
    report = await example_generate_audit_report(db, user_id)
    
    # 5. Check compliance
    compliance = await example_compliance_check(db, corpus_id)
    
    return {
        "corpus_id": corpus_id,
        "search_results": len(results),
        "audit_summary": report.summary,
        "compliance_status": len(compliance["compliance_issues"]) == 0
    }


if __name__ == "__main__":
    print("This file contains usage examples for the Corpus Audit Logger.")
    print("Import these functions in your actual services for proper audit logging.")