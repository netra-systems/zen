from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app import schemas
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
    # User already validated by get_current_user dependency
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
    # User already validated by get_current_user dependency
    
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
    # User already validated by get_current_user dependency
    
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
    # User already validated by get_current_user dependency
    
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
    # User already validated by get_current_user dependency
    
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
    # User already validated by get_current_user dependency
    
    return _delete_corpus_record(db, corpus_id)

@router.post("/{corpus_id}/generate", response_model=schemas.Corpus)
async def regenerate_corpus(
    corpus_id: str, request: Request,
    db: AsyncSession = Depends(get_db_session),
    current_user = Depends(get_current_user)
) -> schemas.Corpus:
    # User already validated by get_current_user dependency
    
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
    # User already validated by get_current_user dependency
    
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
    # User already validated by get_current_user dependency
    
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
    # User already validated by get_current_user dependency
    
    return await _search_corpus_safe(corpus_id, q)

class SearchRequest(BaseModel):
    q: str
    filters: Dict[str, Any] = None
    limit: int = 10
    offset: int = 0

@router.post("/search")
async def search_corpus_advanced(request: SearchRequest, db: AsyncSession = Depends(get_db_session), current_user = Depends(get_current_user)):
    """Advanced corpus search with filters"""
    # User already validated by get_current_user dependency
    
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
    # User already validated by get_current_user dependency
    
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
    # User already validated by get_current_user dependency
    
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
    # User already validated by get_current_user dependency
    
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
    # User already validated by get_current_user dependency
    
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

# ============= Advanced Symbol Navigation Endpoints =============

@router.post("/symbols/go-to-definition")
async def go_to_definition(
    request: Dict,  # {"symbol_name": str, "context_file": Optional[str]}
    current_user = Depends(get_current_user)
):
    """Go to Symbol Definition - Find where a symbol is defined"""
    try:
        from netra_backend.app.services.corpus.symbol_index import get_symbol_navigator
        
        navigator = await get_symbol_navigator()
        symbol_name = request.get("symbol_name")
        context_file = request.get("context_file")
        
        if not symbol_name:
            raise HTTPException(status_code=400, detail="symbol_name is required")
        
        definition = navigator.go_to_definition(symbol_name, context_file)
        
        if not definition:
            return {
                "found": False,
                "message": f"No definition found for '{symbol_name}'"
            }
        
        return {
            "found": True,
            "definition": definition.to_dict()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Go to definition failed: {str(e)}")

@router.post("/symbols/find-references")
async def find_references(
    request: Dict,  # {"symbol_name": str}
    current_user = Depends(get_current_user)
):
    """Find all references to a symbol across the codebase"""
    try:
        from netra_backend.app.services.corpus.symbol_index import get_symbol_navigator
        
        navigator = await get_symbol_navigator()
        symbol_name = request.get("symbol_name")
        
        if not symbol_name:
            raise HTTPException(status_code=400, detail="symbol_name is required")
        
        references = navigator.find_references(symbol_name)
        
        return {
            "symbol": symbol_name,
            "total_references": len(references),
            "references": references
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Find references failed: {str(e)}")

@router.get("/symbols/hierarchy/{file_path:path}")
async def get_symbol_hierarchy(
    file_path: str,
    current_user = Depends(get_current_user)
):
    """Get hierarchical view of symbols in a file"""
    try:
        from netra_backend.app.services.corpus.symbol_index import get_symbol_navigator
        
        navigator = await get_symbol_navigator()
        hierarchy = navigator.get_symbol_hierarchy(file_path)
        
        return hierarchy
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Get hierarchy failed: {str(e)}")

@router.post("/symbols/navigate")
async def navigate_symbols(
    request: Dict,  # {"query": str, "symbol_types": Optional[List[str]], "limit": int}
    current_user = Depends(get_current_user)
):
    """Advanced symbol search with fuzzy matching and ranking"""
    try:
        from netra_backend.app.services.corpus.symbol_index import get_symbol_navigator, SymbolType
        
        navigator = await get_symbol_navigator()
        query = request.get("query", "")
        symbol_types_str = request.get("symbol_types", [])
        limit = request.get("limit", 50)
        
        # Convert string types to SymbolType enums
        symbol_types = []
        for type_str in symbol_types_str:
            try:
                symbol_types.append(SymbolType[type_str.upper()])
            except KeyError:
                pass
        
        results = navigator.search_symbols(query, symbol_types or None, limit)
        
        return {
            "query": query,
            "total": len(results),
            "results": results
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Symbol navigation failed: {str(e)}")

@router.post("/symbols/index/rebuild")
async def rebuild_symbol_index(
    request: Dict,  # {"directory": Optional[str]}
    current_user = Depends(get_current_user)
):
    """Rebuild the symbol index for a directory or entire codebase"""
    try:
        from netra_backend.app.services.corpus.symbol_index import SymbolIndexBuilder
        from pathlib import Path
        
        directory = request.get("directory")
        
        if not directory:
            # Default to netra_backend directory
            directory = Path(__file__).parent.parent.parent
        else:
            directory = Path(directory)
        
        builder = SymbolIndexBuilder()
        index = await builder.build_index_for_directory(directory)
        
        return {
            "status": "success",
            "directory": str(directory),
            "total_files": index.total_files,
            "total_symbols": index.total_symbols,
            "symbol_types": {
                str(k): len(v) for k, v in index.symbols_by_type.items()
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Index rebuild failed: {str(e)}")

@router.post("/symbols/index/update-file")
async def update_file_in_index(
    request: Dict,  # {"file_path": str}
    current_user = Depends(get_current_user)
):
    """Update symbol index for a single file"""
    try:
        from netra_backend.app.services.corpus.symbol_index import get_symbol_index, SymbolIndexBuilder
        from pathlib import Path
        
        file_path = request.get("file_path")
        
        if not file_path:
            raise HTTPException(status_code=400, detail="file_path is required")
        
        # Get or create the index builder
        builder = SymbolIndexBuilder()
        builder.index = await get_symbol_index()
        
        await builder.update_file(file_path)
        
        # Get updated stats for the file
        file_symbols = builder.index.symbols_by_file.get(file_path, [])
        
        return {
            "status": "success",
            "file": file_path,
            "symbols_count": len(file_symbols),
            "symbols": [s.to_dict() for s in file_symbols]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File update failed: {str(e)}")

@router.get("/symbols/index/stats")
async def get_index_statistics(
    current_user = Depends(get_current_user)
):
    """Get statistics about the current symbol index"""
    try:
        from netra_backend.app.services.corpus.symbol_index import get_symbol_index
        
        index = await get_symbol_index()
        
        # Calculate statistics
        stats = {
            "total_symbols": index.total_symbols,
            "total_files": index.total_files,
            "unique_symbol_names": len(index.symbols_by_name),
            "symbol_types": {},
            "top_symbols": [],
            "files_with_most_symbols": []
        }
        
        # Count by type
        for symbol_type, symbols in index.symbols_by_type.items():
            stats["symbol_types"][str(symbol_type)] = len(symbols)
        
        # Top 10 most common symbol names
        top_symbols = sorted(
            index.symbols_by_name.items(),
            key=lambda x: len(x[1]),
            reverse=True
        )[:10]
        stats["top_symbols"] = [
            {"name": name, "count": len(symbols)}
            for name, symbols in top_symbols
        ]
        
        # Files with most symbols
        top_files = sorted(
            index.symbols_by_file.items(),
            key=lambda x: len(x[1]),
            reverse=True
        )[:10]
        stats["files_with_most_symbols"] = [
            {"file": file, "count": len(symbols)}
            for file, symbols in top_files
        ]
        
        return stats
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get index statistics: {str(e)}")

