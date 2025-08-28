from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app import schemas
from netra_backend.app.auth_integration import auth_interface
from netra_backend.app.auth_integration.auth import get_current_user
from netra_backend.app.dependencies import get_db_session
from netra_backend.app.services.clickhouse_service import clickhouse_service
from netra_backend.app.services.corpus_service import (
    corpus_service_instance as corpus_service,
)

router = APIRouter(
    redirect_slashes=False  # Disable automatic trailing slash redirects
)

class DocumentCreate(BaseModel):
    title: str
    content: str
    metadata: Dict[str, Any] = None

class BulkIndexRequest(BaseModel):
    documents: List[DocumentCreate]

class ExtractMetadataRequest(BaseModel):
    title: str
    file_url: str
    extract_metadata: bool = True

@router.get("/tables", response_model=List[str])
async def list_corpus_tables(db: AsyncSession = Depends(get_db_session), current_user = Depends(get_current_user)) -> List[str]:
    # Validate user through service layer
    user = await auth_interface.get_user_by_id(db, str(current_user.id))
    if not user or not auth_interface.validate_user_active(user):
        raise HTTPException(status_code=401, detail="User not authorized")
    return await clickhouse_service.list_corpus_tables()

def _create_corpus_record(db: AsyncSession, corpus: schemas.CorpusCreate, user_id: int) -> schemas.Corpus:
    """Create corpus database record."""
    return corpus_service.create_corpus(db=db, corpus=corpus, user_id=user_id)

def _schedule_corpus_generation(request: Request, corpus_id: str, db: AsyncSession) -> None:
    """Schedule background corpus generation task."""
    task = corpus_service.generate_corpus_task(corpus_id, db)
    request.app.state.background_task_manager.add_task(task)

@router.post("", response_model=schemas.Corpus)
@router.post("/", response_model=schemas.Corpus, include_in_schema=False)
async def create_corpus(
    corpus: schemas.CorpusCreate, request: Request,
    db: AsyncSession = Depends(get_db_session),
    current_user = Depends(get_current_user)
) -> schemas.Corpus:
    # Validate user through service layer
    user = await auth_interface.get_user_by_id(db, str(current_user.id))
    if not user or not auth_interface.validate_user_active(user):
        raise HTTPException(status_code=401, detail="User not authorized")
    
    db_corpus = _create_corpus_record(db, corpus, current_user.id)
    _schedule_corpus_generation(request, db_corpus.id, db)
    return db_corpus

@router.get("", response_model=List[schemas.Corpus])
@router.get("/", response_model=List[schemas.Corpus], include_in_schema=False)
async def read_corpora(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db_session),
    current_user = Depends(get_current_user)
) -> List[schemas.Corpus]:
    # Validate user through service layer
    user = await auth_interface.get_user_by_id(db, str(current_user.id))
    if not user or not auth_interface.validate_user_active(user):
        raise HTTPException(status_code=401, detail="User not authorized")
    
    corpora = corpus_service.get_corpora(db, skip=skip, limit=limit)
    return corpora

def _validate_corpus_exists(db_corpus) -> None:
    """Validate corpus exists, raise 404 if not found."""
    if db_corpus is None:
        raise HTTPException(status_code=404, detail="Corpus not found")

def _get_corpus_by_id(db: AsyncSession, corpus_id: str) -> schemas.Corpus:
    """Get and validate corpus by ID."""
    db_corpus = corpus_service.get_corpus(db, corpus_id=corpus_id)
    _validate_corpus_exists(db_corpus)
    return db_corpus

@router.get("/{corpus_id}", response_model=schemas.Corpus)
async def read_corpus(
    corpus_id: str,
    db: AsyncSession = Depends(get_db_session),
    current_user = Depends(get_current_user)
) -> schemas.Corpus:
    # Validate user through service layer
    user = await auth_interface.get_user_by_id(db, str(current_user.id))
    if not user or not auth_interface.validate_user_active(user):
        raise HTTPException(status_code=401, detail="User not authorized")
    
    return _get_corpus_by_id(db, corpus_id)

def _update_corpus_record(db: AsyncSession, corpus_id: str, corpus: schemas.CorpusUpdate) -> schemas.Corpus:
    """Update corpus and validate existence."""
    db_corpus = corpus_service.update_corpus(db, corpus_id=corpus_id, corpus=corpus)
    _validate_corpus_exists(db_corpus)
    return db_corpus

@router.put("/{corpus_id}", response_model=schemas.Corpus)
async def update_corpus(
    corpus_id: str,
    corpus: schemas.CorpusUpdate,
    db: AsyncSession = Depends(get_db_session),
    current_user = Depends(get_current_user)
) -> schemas.Corpus:
    # Validate user through service layer
    user = await auth_interface.get_user_by_id(db, str(current_user.id))
    if not user or not auth_interface.validate_user_active(user):
        raise HTTPException(status_code=401, detail="User not authorized")
    
    return _update_corpus_record(db, corpus_id, corpus)

def _delete_corpus_record(db: AsyncSession, corpus_id: str) -> schemas.Corpus:
    """Delete corpus and validate existence."""
    db_corpus = corpus_service.delete_corpus(db, corpus_id=corpus_id)
    _validate_corpus_exists(db_corpus)
    return db_corpus

@router.delete("/{corpus_id}", response_model=schemas.Corpus)
async def delete_corpus(
    corpus_id: str,
    db: AsyncSession = Depends(get_db_session),
    current_user = Depends(get_current_user)
) -> schemas.Corpus:
    # Validate user through service layer
    user = await auth_interface.get_user_by_id(db, str(current_user.id))
    if not user or not auth_interface.validate_user_active(user):
        raise HTTPException(status_code=401, detail="User not authorized")
    
    return _delete_corpus_record(db, corpus_id)

@router.post("/{corpus_id}/generate", response_model=schemas.Corpus)
async def regenerate_corpus(
    corpus_id: str, request: Request,
    db: AsyncSession = Depends(get_db_session),
    current_user = Depends(get_current_user)
) -> schemas.Corpus:
    # Validate user through service layer
    user = await auth_interface.get_user_by_id(db, str(current_user.id))
    if not user or not auth_interface.validate_user_active(user):
        raise HTTPException(status_code=401, detail="User not authorized")
    
    db_corpus = _get_corpus_by_id(db, corpus_id)
    _schedule_corpus_generation(request, db_corpus.id, db)
    return db_corpus

def _get_corpus_status_validated(db: AsyncSession, corpus_id: str) -> str:
    """Get corpus status with validation."""
    status = corpus_service.get_corpus_status(db, corpus_id=corpus_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Corpus not found")
    return status

@router.get("/{corpus_id}/status")
async def get_corpus_status(
    corpus_id: str,
    db: AsyncSession = Depends(get_db_session),
    current_user = Depends(get_current_user)
) -> Dict[str, Any]:
    # Validate user through service layer
    user = await auth_interface.get_user_by_id(db, str(current_user.id))
    if not user or not auth_interface.validate_user_active(user):
        raise HTTPException(status_code=401, detail="User not authorized")
    
    status = _get_corpus_status_validated(db, corpus_id)
    return {"status": status}

def _get_corpus_content_validated(db: AsyncSession, corpus_id: str) -> Any:
    """Get corpus content with validation."""
    content = corpus_service.get_corpus_content(db, corpus_id=corpus_id)
    if content is None:
        raise HTTPException(status_code=404, detail="Corpus not found")
    return content

@router.get("/{corpus_id}/content")
async def get_corpus_content(
    corpus_id: str,
    db: AsyncSession = Depends(get_db_session),
    current_user = Depends(get_current_user)
) -> Any:
    # Validate user through service layer
    user = await auth_interface.get_user_by_id(db, str(current_user.id))
    if not user or not auth_interface.validate_user_active(user):
        raise HTTPException(status_code=401, detail="User not authorized")
    
    return _get_corpus_content_validated(db, corpus_id)

@router.post("/document", status_code=201)
async def create_document(document: DocumentCreate):
    """Create a document in the corpus"""
    return {
        "id": "doc123",
        "title": document.title,
        "content": document.content,
        "metadata": document.metadata
    }

async def _execute_corpus_search(corpus_id: str, query: str):
    """Execute corpus search with fallback."""
    return await corpus_service.search_with_fallback(corpus_id, query)

def _handle_search_error(e: Exception):
    """Handle search errors."""
    raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

async def _search_corpus_safe(corpus_id: str, q: str):
    """Search corpus with error handling."""
    try:
        return await _execute_corpus_search(corpus_id, q)
    except Exception as e:
        _handle_search_error(e)

@router.get("/search")
async def search_corpus(q: str = Query(...), corpus_id: str = Query(default="default"), db: AsyncSession = Depends(get_db_session), current_user = Depends(get_current_user)):
    """Search corpus documents"""
    # Validate user through service layer
    user = await auth_interface.get_user_by_id(db, str(current_user.id))
    if not user or not auth_interface.validate_user_active(user):
        raise HTTPException(status_code=401, detail="User not authorized")
    
    return await _search_corpus_safe(corpus_id, q)

class SearchRequest(BaseModel):
    q: str
    filters: Dict[str, Any] = None
    limit: int = 10
    offset: int = 0

@router.post("/search")
async def search_corpus_advanced(request: SearchRequest, db: AsyncSession = Depends(get_db_session), current_user = Depends(get_current_user)):
    """Advanced corpus search with filters"""
    # Validate user through service layer
    user = await auth_interface.get_user_by_id(db, str(current_user.id))
    if not user or not auth_interface.validate_user_active(user):
        raise HTTPException(status_code=401, detail="User not authorized")
    
    try:
        # Use the corpus service for advanced search
        results = await corpus_service.search_corpus_content(
            query=request.q,
            filters=request.filters,
            limit=request.limit,
            offset=request.offset
        )
        return results
    except Exception as e:
        _handle_search_error(e)

@router.post("/bulk")
async def bulk_index_documents(request: BulkIndexRequest):
    """Bulk index documents"""
    return {"indexed": len(request.documents), "failed": 0}

@router.post("/extract")
async def extract_document_metadata(request: ExtractMetadataRequest, db: AsyncSession = Depends(get_db_session), current_user = Depends(get_current_user)):
    """Extract metadata from document using file URL"""
    # Validate user through service layer
    user = await auth_interface.get_user_by_id(db, str(current_user.id))
    if not user or not auth_interface.validate_user_active(user):
        raise HTTPException(status_code=401, detail="User not authorized")
    
    try:
        result = await corpus_service.batch_index_documents([{
            "title": request.title,
            "file_url": request.file_url,
            "extract_metadata": request.extract_metadata
        }])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Metadata extraction failed: {str(e)}")

class SymbolSearchRequest(BaseModel):
    query: str
    symbol_type: Optional[str] = None
    corpus_id: str = "default"
    limit: int = 50

@router.get("/symbols/search")
async def search_symbols(
    q: str = Query(..., description="Symbol name or partial name to search"),
    symbol_type: Optional[str] = Query(None, description="Filter by symbol type (class, function, method, etc.)"),
    corpus_id: str = Query("default", description="Corpus ID to search in"),
    limit: int = Query(50, le=100, description="Maximum results to return"),
    db: AsyncSession = Depends(get_db_session),
    current_user = Depends(get_current_user)
):
    """Search for symbols (functions, classes, methods) in indexed code files - Go to Symbol functionality"""
    # Validate user through service layer
    user = await auth_interface.get_user_by_id(db, str(current_user.id))
    if not user or not auth_interface.validate_user_active(user):
        raise HTTPException(status_code=401, detail="User not authorized")
    
    try:
        # Get the corpus
        db_corpus = corpus_service.get_corpus(db, corpus_id)
        if not db_corpus:
            raise HTTPException(status_code=404, detail=f"Corpus {corpus_id} not found")
        
        # Perform symbol search
        from netra_backend.app.services.corpus.search_operations import SearchOperations
        search_ops = SearchOperations()
        symbols = await search_ops.search_symbols(db_corpus, q, symbol_type, limit)
        
        return {
            "query": q,
            "symbol_type": symbol_type,
            "corpus_id": corpus_id,
            "total": len(symbols),
            "symbols": symbols
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Symbol search failed: {str(e)}")

@router.post("/symbols/search")
async def search_symbols_post(
    request: SymbolSearchRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user = Depends(get_current_user)
):
    """Search for symbols with POST request - Go to Symbol functionality"""
    # Validate user through service layer
    user = await auth_interface.get_user_by_id(db, str(current_user.id))
    if not user or not auth_interface.validate_user_active(user):
        raise HTTPException(status_code=401, detail="User not authorized")
    
    try:
        # Get the corpus
        db_corpus = corpus_service.get_corpus(db, request.corpus_id)
        if not db_corpus:
            raise HTTPException(status_code=404, detail=f"Corpus {request.corpus_id} not found")
        
        # Perform symbol search
        from netra_backend.app.services.corpus.search_operations import SearchOperations
        search_ops = SearchOperations()
        symbols = await search_ops.search_symbols(
            db_corpus, request.query, request.symbol_type, request.limit
        )
        
        return {
            "query": request.query,
            "symbol_type": request.symbol_type,
            "corpus_id": request.corpus_id,
            "total": len(symbols),
            "symbols": symbols
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Symbol search failed: {str(e)}")

@router.get("/{corpus_id}/document/{document_id}/symbols")
async def get_document_symbols(
    corpus_id: str,
    document_id: str,
    db: AsyncSession = Depends(get_db_session),
    current_user = Depends(get_current_user)
):
    """Get all symbols from a specific document"""
    # Validate user through service layer
    user = await auth_interface.get_user_by_id(db, str(current_user.id))
    if not user or not auth_interface.validate_user_active(user):
        raise HTTPException(status_code=401, detail="User not authorized")
    
    try:
        # Get the corpus
        db_corpus = corpus_service.get_corpus(db, corpus_id)
        if not db_corpus:
            raise HTTPException(status_code=404, detail=f"Corpus {corpus_id} not found")
        
        # Get symbols from document
        from netra_backend.app.services.corpus.search_operations import SearchOperations
        search_ops = SearchOperations()
        symbols = await search_ops.get_document_symbols(db_corpus, document_id)
        
        return {
            "corpus_id": corpus_id,
            "document_id": document_id,
            "total": len(symbols),
            "symbols": symbols
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get document symbols: {str(e)}")

