"""
Example Usage of Corpus Audit Logger

This file demonstrates how to use the comprehensive audit logging system
for corpus operations. Follow these patterns for consistency.
"""

from typing import Optional, Dict, List, Any
from datetime import datetime, UTC, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.audit.corpus_audit import CorpusAuditLogger, create_audit_logger
from app.services.audit.repository import CorpusAuditRepository
from app.services.audit.utils import AuditTimer
from app.schemas.registry import (
    CorpusAuditAction, CorpusAuditStatus, CorpusAuditMetadata,
    CorpusAuditSearchFilter
)


def _create_corpus_metadata() -> CorpusAuditMetadata:
    """Create base metadata for corpus operations."""
    config = {"corpus_type": "documents", "auto_index": True}
    return CorpusAuditMetadata(
        user_agent="NetraAI/1.0", ip_address="192.168.1.100",
        request_id="req-123456", configuration=config
    )

async def _log_corpus_success(
    audit_logger: CorpusAuditLogger, db: AsyncSession, user_id: str,
    corpus_id: str, duration_ms: int, metadata: CorpusAuditMetadata
) -> None:
    """Log successful corpus creation."""
    result_data = {"corpus_id": corpus_id, "document_count": 0}
    log_params = _build_corpus_log_params(db, user_id, corpus_id, duration_ms, result_data, metadata)
    await audit_logger.log_operation(**log_params)

def _build_corpus_log_params(db: AsyncSession, user_id: str, corpus_id: str, duration_ms: int, 
                           result_data: Dict[str, Any], metadata: CorpusAuditMetadata) -> Dict[str, Any]:
    """Build parameters for corpus logging operation."""
    return {
        "db": db, "action": CorpusAuditAction.CREATE, "resource_type": "corpus",
        "status": CorpusAuditStatus.SUCCESS, "user_id": user_id, "corpus_id": corpus_id,
        "operation_duration_ms": duration_ms, "result_data": result_data, "metadata": metadata
    }

async def _log_corpus_error(
    audit_logger: CorpusAuditLogger, db: AsyncSession, user_id: str,
    error: Exception, duration_ms: int, base_metadata: CorpusAuditMetadata
) -> None:
    """Log corpus creation error."""
    error_metadata = _create_error_metadata(error, base_metadata)
    error_log_params = _build_error_log_params(db, user_id, duration_ms, error_metadata)
    await audit_logger.log_operation(**error_log_params)

def _create_error_metadata(error: Exception, base_metadata: CorpusAuditMetadata) -> CorpusAuditMetadata:
    """Create error metadata from exception and base metadata."""
    error_details = {"error": str(error), "error_type": type(error).__name__}
    return CorpusAuditMetadata(
        user_agent=base_metadata.user_agent, ip_address=base_metadata.ip_address,
        request_id=base_metadata.request_id, configuration=base_metadata.configuration,
        error_details=error_details
    )

def _build_error_log_params(db: AsyncSession, user_id: str, duration_ms: int, 
                          error_metadata: CorpusAuditMetadata) -> Dict[str, Any]:
    """Build parameters for error logging operation."""
    return {
        "db": db, "action": CorpusAuditAction.CREATE, "resource_type": "corpus",
        "status": CorpusAuditStatus.FAILURE, "user_id": user_id,
        "operation_duration_ms": duration_ms, "metadata": error_metadata
    }

# Example 1: Basic operation logging
async def example_create_corpus(db: AsyncSession, user_id: str, corpus_data: Dict[str, Any]) -> str:
    """Example of logging a corpus creation operation."""
    audit_logger = await create_audit_logger(db)
    metadata = _create_corpus_metadata()
    with AuditTimer() as timer:
        return await _execute_corpus_creation(audit_logger, db, user_id, corpus_data, timer, metadata)

async def _execute_corpus_creation(
    audit_logger: CorpusAuditLogger, db: AsyncSession, user_id: str,
    corpus_data: Dict[str, Any], timer: AuditTimer, metadata: CorpusAuditMetadata
) -> str:
    """Execute corpus creation with error handling."""
    try:
        return await _handle_successful_creation(audit_logger, db, user_id, corpus_data, timer, metadata)
    except Exception as e:
        await _handle_creation_error(audit_logger, db, user_id, e, timer, metadata)
        raise

async def _handle_successful_creation(
    audit_logger: CorpusAuditLogger, db: AsyncSession, user_id: str,
    corpus_data: Dict[str, Any], timer: AuditTimer, metadata: CorpusAuditMetadata
) -> str:
    """Handle successful corpus creation."""
    corpus_id = create_corpus_logic(corpus_data)
    await _log_corpus_success(audit_logger, db, user_id, corpus_id, timer.get_duration(), metadata)
    return corpus_id

async def _handle_creation_error(
    audit_logger: CorpusAuditLogger, db: AsyncSession, user_id: str,
    error: Exception, timer: AuditTimer, metadata: CorpusAuditMetadata
) -> None:
    """Handle corpus creation error."""
    await _log_corpus_error(audit_logger, db, user_id, error, timer.get_duration(), metadata)


async def _log_document_success(
    audit_logger: CorpusAuditLogger, db: AsyncSession, user_id: str, corpus_id: str,
    doc_id: str, document: Dict[str, Any], duration_ms: int, batch_pos: int, total_docs: int
) -> None:
    """Log successful document upload."""
    result_data = _create_document_result_data(doc_id, document)
    metadata = _create_batch_metadata(batch_pos, total_docs)
    await audit_logger.log_operation(
        db=db, action=CorpusAuditAction.UPLOAD, resource_type="document",
        status=CorpusAuditStatus.SUCCESS, user_id=user_id, corpus_id=corpus_id,
        resource_id=doc_id, operation_duration_ms=duration_ms,
        result_data=result_data, metadata=metadata
    )

def _create_document_result_data(doc_id: str, document: Dict[str, Any]) -> Dict[str, Any]:
    """Create result data for document upload."""
    return {
        "document_id": doc_id,
        "size_bytes": len(document.get("content", "")),
        "format": document.get("format", "unknown")
    }

def _create_batch_metadata(batch_pos: int, total_docs: int) -> CorpusAuditMetadata:
    """Create metadata for batch operations."""
    config = {"batch_position": batch_pos, "total_documents": total_docs}
    return CorpusAuditMetadata(configuration=config)

async def _log_document_error(
    audit_logger: CorpusAuditLogger, db: AsyncSession, user_id: str, corpus_id: str,
    error: Exception, duration_ms: int, batch_pos: int, total_docs: int
) -> None:
    """Log document upload error."""
    config = {"batch_position": batch_pos, "total_documents": total_docs}
    error_details = {"error": str(error)}
    metadata = CorpusAuditMetadata(configuration=config, error_details=error_details)
    await audit_logger.log_operation(
        db=db, action=CorpusAuditAction.UPLOAD, resource_type="document",
        status=CorpusAuditStatus.FAILURE, user_id=user_id, corpus_id=corpus_id,
        operation_duration_ms=duration_ms, metadata=metadata
    )

# Example 2: Document upload with detailed tracking
async def example_upload_documents(
    db: AsyncSession, user_id: str, corpus_id: str, documents: List[Dict[str, Any]]
) -> None:
    """Example of logging document upload operations."""
    audit_logger = await create_audit_logger(db)
    for i, document in enumerate(documents):
        batch_info = {"position": i + 1, "total": len(documents)}
        await _process_single_document(audit_logger, db, user_id, corpus_id, document, batch_info)

async def _process_single_document(
    audit_logger: CorpusAuditLogger, db: AsyncSession, user_id: str, corpus_id: str,
    document: Dict[str, Any], batch_info: Dict[str, int]
) -> None:
    """Process single document upload with logging."""
    with AuditTimer() as timer:
        try:
            doc_id = upload_document_logic(document)
            await _log_document_success(
                audit_logger, db, user_id, corpus_id, doc_id, document,
                timer.get_duration(), batch_info["position"], batch_info["total"]
            )
        except Exception as e:
            await _log_document_error(
                audit_logger, db, user_id, corpus_id, e,
                timer.get_duration(), batch_info["position"], batch_info["total"]
            )


def _create_performance_metrics(query: str, search_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Create performance metrics for search operation."""
    scores = [r.get("score", 0) for r in search_results[:10]]
    return {
        "query_length": len(query),
        "results_count": len(search_results),
        "relevance_scores": scores
    }

async def _log_search_operation(
    audit_logger: CorpusAuditLogger, db: AsyncSession, user_id: str, corpus_id: str,
    query: str, search_results: List[Dict[str, Any]], duration_ms: int
) -> None:
    """Log search operation with metrics."""
    performance_metrics = _create_performance_metrics(query, search_results)
    result_data = {"results_count": len(search_results), "query": query}
    config = {"search_type": "semantic", "max_results": 100}
    metadata = CorpusAuditMetadata(performance_metrics=performance_metrics, configuration=config)
    await audit_logger.log_operation(
        db=db, action=CorpusAuditAction.SEARCH, resource_type="corpus",
        status=CorpusAuditStatus.SUCCESS, user_id=user_id, corpus_id=corpus_id,
        operation_duration_ms=duration_ms, result_data=result_data, metadata=metadata
    )

# Example 3: Search operations with performance tracking
async def example_search_corpus(
    db: AsyncSession, user_id: str, corpus_id: str, query: str
) -> List[Dict[str, Any]]:
    """Example of logging search operations with performance metrics."""
    audit_logger = await create_audit_logger(db)
    with AuditTimer() as timer:
        search_results = perform_search_logic(corpus_id, query)
        await _log_search_operation(audit_logger, db, user_id, corpus_id, query, search_results, timer.get_duration())
        return search_results


def _create_audit_filters(user_id: Optional[str]) -> CorpusAuditSearchFilter:
    """Create audit search filters."""
    start_date = datetime.now(UTC).replace(hour=0, minute=0, second=0)
    return CorpusAuditSearchFilter(
        user_id=user_id, start_date=start_date, limit=1000
    )

def _process_audit_report(report: Any) -> Dict[str, int]:
    """Process and print audit report insights."""
    _print_report_header(report)
    action_counts = _count_actions_by_type(report.records)
    print(f"Operations by Type: {action_counts}")
    return action_counts

def _print_report_header(report: Any) -> None:
    """Print audit report header."""
    print(f"Audit Report for {datetime.now(UTC).date()}")
    print(f"Total Operations: {report.total_records}")
    print(f"Summary: {report.summary}")

def _count_actions_by_type(records: List[Any]) -> Dict[str, int]:
    """Count actions by type from records."""
    action_counts = {}
    for record in records:
        action = record.action.value
        action_counts[action] = action_counts.get(action, 0) + 1
    return action_counts

# Example 4: Generating audit reports
async def example_generate_audit_report(db: AsyncSession, user_id: Optional[str] = None) -> Any:
    """Example of generating comprehensive audit reports."""
    audit_logger = await create_audit_logger(db)
    filters = _create_audit_filters(user_id)
    report = await audit_logger.search_audit_logs(db, filters)
    _process_audit_report(report)
    return report


def _create_compliance_filters(corpus_id: str) -> CorpusAuditSearchFilter:
    """Create compliance check filters."""
    start_date = datetime.now(UTC) - timedelta(days=30)
    return CorpusAuditSearchFilter(
        corpus_id=corpus_id, start_date=start_date, limit=10000
    )

def _check_record_compliance(record: Any) -> List[str]:
    """Check individual record for compliance issues."""
    issues = []
    _check_deletion_attribution(record, issues)
    _check_operation_duration(record, issues)
    _check_operation_status(record, issues)
    return issues

def _check_deletion_attribution(record: Any, issues: List[str]) -> None:
    """Check deletion attribution compliance."""
    if record.action == CorpusAuditAction.DELETE and not record.user_id:
        issues.append("Deletion without user attribution")

def _check_operation_duration(record: Any, issues: List[str]) -> None:
    """Check operation duration compliance."""
    if record.operation_duration_ms and record.operation_duration_ms > 60000:
        issues.append(f"Long-running operation: {record.action.value}")

def _check_operation_status(record: Any, issues: List[str]) -> None:
    """Check operation status compliance."""
    if record.status == CorpusAuditStatus.FAILURE:
        issues.append(f"Failed operation: {record.action.value}")

def _build_compliance_result(corpus_id: str, report: Any, compliance_issues: List[str], filters: CorpusAuditSearchFilter) -> Dict[str, Any]:
    """Build compliance check result."""
    audit_period = f"{filters.start_date} to {datetime.now(UTC)}"
    return {
        "corpus_id": corpus_id, "total_operations": report.total_records,
        "compliance_issues": compliance_issues, "audit_period": audit_period
    }

# Example 5: Compliance monitoring
async def example_compliance_check(db: AsyncSession, corpus_id: str) -> Dict[str, Any]:
    """Example of compliance monitoring using audit logs."""
    audit_logger = await create_audit_logger(db)
    filters = _create_compliance_filters(corpus_id)
    report = await audit_logger.search_audit_logs(db, filters)
    compliance_issues = _collect_compliance_issues(report.records)
    return _build_compliance_result(corpus_id, report, compliance_issues, filters)

def _collect_compliance_issues(records: List[Any]) -> List[str]:
    """Collect compliance issues from all records."""
    compliance_issues = []
    for record in records:
        compliance_issues.extend(_check_record_compliance(record))
    return compliance_issues


def _validate_corpus_data(corpus_data: Dict[str, Any]) -> None:
    """Validate corpus data requirements."""
    if not corpus_data.get("name"):
        raise ValueError("Corpus name is required")

def _generate_corpus_id() -> str:
    """Generate unique corpus ID."""
    import uuid
    return f"corpus_{uuid.uuid4().hex[:12]}"

# Production implementations for corpus operations
def create_corpus_logic(corpus_data: Dict[str, Any]) -> str:
    """Production corpus creation implementation."""
    _validate_corpus_data(corpus_data)
    corpus_id = _generate_corpus_id()
    # In production, this would persist to database
    return corpus_id


def _validate_document(document: Dict[str, Any]) -> None:
    """Validate document requirements."""
    if not document.get("content"):
        raise ValueError("Document content is required")
    if len(document.get("content", "")) > 10_000_000:
        raise ValueError("Document too large")

def _generate_document_id() -> str:
    """Generate unique document ID."""
    import uuid
    return f"doc_{uuid.uuid4().hex[:12]}"

def upload_document_logic(document: Dict[str, Any]) -> str:
    """Production document upload implementation."""
    _validate_document(document)
    doc_id = _generate_document_id()
    # In production, this would persist to database
    return doc_id


def _validate_search_params(corpus_id: str, query: str) -> None:
    """Validate search parameters."""
    if not corpus_id or not query:
        raise ValueError("Corpus ID and query are required")
    if len(query) > 1000:
        raise ValueError("Query too long")

def _generate_mock_results(query: str) -> List[Dict[str, Any]]:
    """Generate mock search results based on query."""
    import hashlib
    query_hash = hashlib.md5(query.encode()).hexdigest()[:8]
    return _build_mock_result_list(query, query_hash)

def _build_mock_result_list(query: str, query_hash: str) -> List[Dict[str, Any]]:
    """Build list of mock search results."""
    return [
        {"id": f"result_{query_hash}_1", "score": 0.95, "content": f"Search result for '{query}' - Document 1"},
        {"id": f"result_{query_hash}_2", "score": 0.87, "content": f"Search result for '{query}' - Document 2"}
    ]

def perform_search_logic(corpus_id: str, query: str) -> List[Dict[str, Any]]:
    """Production search implementation."""
    _validate_search_params(corpus_id, query)
    # In production: would use vector database for semantic search
    return _generate_mock_results(query)


# Main usage example
async def main_example(db: AsyncSession) -> Dict[str, Any]:
    """Complete workflow example."""
    user_id = "user-123"
    workflow_results = await _execute_complete_workflow(db, user_id)
    return _build_workflow_summary(workflow_results)

async def _execute_complete_workflow(db: AsyncSession, user_id: str) -> Dict[str, Any]:
    """Execute complete audit workflow."""
    corpus_id = await example_create_corpus(db, user_id, {"name": "Test Corpus"})
    documents = [{"content": "Document 1 content", "format": "text"}, {"content": "Document 2 content", "format": "text"}]
    await example_upload_documents(db, user_id, corpus_id, documents)
    results = await example_search_corpus(db, user_id, corpus_id, "test query")
    report = await example_generate_audit_report(db, user_id)
    compliance = await example_compliance_check(db, corpus_id)
    return {"corpus_id": corpus_id, "results": results, "report": report, "compliance": compliance}

def _build_workflow_summary(workflow_results: Dict[str, Any]) -> Dict[str, Any]:
    """Build summary from workflow results."""
    compliance_clean = len(workflow_results["compliance"]["compliance_issues"]) == 0
    return {
        "corpus_id": workflow_results["corpus_id"],
        "search_results": len(workflow_results["results"]),
        "audit_summary": workflow_results["report"].summary,
        "compliance_status": compliance_clean
    }


if __name__ == "__main__":
    print("This file contains usage examples for the Corpus Audit Logger.")
    print("Import these functions in your actual services for proper audit logging.")