"""Corpus service helper functions for function decomposition.

Decomposes large functions into 25-line focused helpers.
"""

from typing import Dict, List, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app import schemas
from app.logging_config import central_logger as logger


def validate_corpus_creation_params(db: AsyncSession, corpus_data: schemas.CorpusCreate, user_id: str) -> None:
    """Validate corpus creation parameters."""
    if not db:
        raise ValueError("Database session is required")
    if not corpus_data:
        raise ValueError("Corpus data is required") 
    if not user_id:
        raise ValueError("User ID is required")


def validate_content_upload_params(db: AsyncSession, corpus_id: str, content_data: Dict) -> None:
    """Validate content upload parameters."""
    if not db:
        raise ValueError("Database session is required")
    if not corpus_id:
        raise ValueError("Corpus ID is required")
    if not content_data:
        raise ValueError("Content data is required")


def validate_document_indexing_params(document: Dict) -> None:
    """Validate document indexing parameters."""
    document_id = document.get("id")
    if not document_id:
        raise ValueError("Document must have an 'id' field")
    
    content = document.get("content", "")
    if not content:
        raise ValueError("Document must have non-empty 'content' field")


async def check_modular_service_indexing(modular_service, document: Dict) -> Optional[Dict]:
    """Check if modular service supports document indexing."""
    if hasattr(modular_service, 'index_document'):
        return await modular_service.index_document(document)
    return None


async def try_document_manager_processing(modular_service, document: Dict) -> Optional[Dict]:
    """Try document processing through document manager."""
    document_manager = getattr(modular_service, 'document_manager', None)
    if document_manager and hasattr(document_manager, 'process_document'):
        return await document_manager.process_document(document)
    return None


def validate_batch_documents(documents: List[Dict]) -> None:
    """Validate batch documents list."""
    if not documents:
        raise ValueError("Documents list cannot be empty")


def calculate_relevance_score(result: Dict, query_terms: List[str]) -> int:
    """Calculate relevance score for search result."""
    score = 0
    content = str(result.get('content', '')).lower()
    for term in query_terms:
        score += content.count(term)
    return score


def prepare_ranked_result(result: Dict, score: int) -> Dict:
    """Prepare ranked search result."""
    new_result = result.copy()
    new_result['score'] = score * 0.1 + result.get('score', 0)
    return new_result


def validate_search_parameters(corpus_id: str, query: str) -> None:
    """Validate search parameters."""
    if not corpus_id:
        raise ValueError("Corpus ID is required")
    if not query:
        raise ValueError("Search query is required")


async def check_modular_keyword_search(modular_service, corpus_id: str, query: str) -> Optional[List[Dict]]:
    """Check if modular service supports keyword search."""
    if hasattr(modular_service, 'keyword_search'):
        return await modular_service.keyword_search(corpus_id, query)
    return None


def validate_filter_keys(filters: Dict, allowed_filter_types: set) -> None:
    """Validate and clean unknown filter keys."""
    unknown_filters = set(filters.keys()) - allowed_filter_types
    if unknown_filters:
        logger.warning(f"Unknown filter types ignored: {unknown_filters}")
        for key in unknown_filters:
            filters.pop(key, None)


def get_allowed_filter_types() -> set:
    """Get set of allowed filter types."""
    return {
        'date_range', 'content_type', 'workload_type', 'score_threshold',
        'tags', 'created_by', 'status', 'metadata_fields'
    }


def apply_modular_search_filters(modular_service, filters: Dict) -> None:
    """Apply filters through modular service if available."""
    if hasattr(modular_service, 'apply_search_filters'):
        modular_service.apply_search_filters(filters)


def validate_document_creation_params(db: AsyncSession, corpus_id: str, document_data: schemas.DocumentCreate) -> None:
    """Validate document creation parameters."""
    if not db:
        raise ValueError("Database session is required")
    if not corpus_id:
        raise ValueError("Corpus ID is required")
    if not document_data:
        raise ValueError("Document data is required")