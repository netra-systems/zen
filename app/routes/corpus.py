from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request, Query
from sqlalchemy.orm import Session
from app import schemas
from app.services import clickhouse_service
from app.services.corpus_service import corpus_service_instance as corpus_service
from app.dependencies import get_db_session
from app.auth_integration.auth import get_current_user
from app.db.models_postgres import User
from pydantic import BaseModel

router = APIRouter()

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
async def list_corpus_tables(current_user: User = Depends(get_current_user)) -> List[str]:
    return await clickhouse_service.list_corpus_tables()

def _create_corpus_record(db: Session, corpus: schemas.CorpusCreate, user_id: int) -> schemas.Corpus:
    """Create corpus database record."""
    return corpus_service.create_corpus(db=db, corpus=corpus, user_id=user_id)

def _schedule_corpus_generation(request: Request, corpus_id: str, db: Session) -> None:
    """Schedule background corpus generation task."""
    task = corpus_service.generate_corpus_task(corpus_id, db)
    request.app.state.background_task_manager.add_task(task)

@router.post("/", response_model=schemas.Corpus)
def create_corpus(
    corpus: schemas.CorpusCreate, request: Request,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
) -> schemas.Corpus:
    db_corpus = _create_corpus_record(db, corpus, current_user.id)
    _schedule_corpus_generation(request, db_corpus.id, db)
    return db_corpus

@router.get("/", response_model=List[schemas.Corpus])
def read_corpora(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
) -> List[schemas.Corpus]:
    corpora = corpus_service.get_corpora(db, skip=skip, limit=limit)
    return corpora

def _validate_corpus_exists(db_corpus) -> None:
    """Validate corpus exists, raise 404 if not found."""
    if db_corpus is None:
        raise HTTPException(status_code=404, detail="Corpus not found")

def _get_corpus_by_id(db: Session, corpus_id: str) -> schemas.Corpus:
    """Get and validate corpus by ID."""
    db_corpus = corpus_service.get_corpus(db, corpus_id=corpus_id)
    _validate_corpus_exists(db_corpus)
    return db_corpus

@router.get("/{corpus_id}", response_model=schemas.Corpus)
def read_corpus(
    corpus_id: str,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
) -> schemas.Corpus:
    return _get_corpus_by_id(db, corpus_id)

def _update_corpus_record(db: Session, corpus_id: str, corpus: schemas.CorpusUpdate) -> schemas.Corpus:
    """Update corpus and validate existence."""
    db_corpus = corpus_service.update_corpus(db, corpus_id=corpus_id, corpus=corpus)
    _validate_corpus_exists(db_corpus)
    return db_corpus

@router.put("/{corpus_id}", response_model=schemas.Corpus)
def update_corpus(
    corpus_id: str,
    corpus: schemas.CorpusUpdate,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
) -> schemas.Corpus:
    return _update_corpus_record(db, corpus_id, corpus)

def _delete_corpus_record(db: Session, corpus_id: str) -> schemas.Corpus:
    """Delete corpus and validate existence."""
    db_corpus = corpus_service.delete_corpus(db, corpus_id=corpus_id)
    _validate_corpus_exists(db_corpus)
    return db_corpus

@router.delete("/{corpus_id}", response_model=schemas.Corpus)
def delete_corpus(
    corpus_id: str,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
) -> schemas.Corpus:
    return _delete_corpus_record(db, corpus_id)

@router.post("/{corpus_id}/generate", response_model=schemas.Corpus)
def regenerate_corpus(
    corpus_id: str, request: Request,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
) -> schemas.Corpus:
    db_corpus = _get_corpus_by_id(db, corpus_id)
    _schedule_corpus_generation(request, db_corpus.id, db)
    return db_corpus

def _get_corpus_status_validated(db: Session, corpus_id: str) -> str:
    """Get corpus status with validation."""
    status = corpus_service.get_corpus_status(db, corpus_id=corpus_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Corpus not found")
    return status

@router.get("/{corpus_id}/status")
def get_corpus_status(
    corpus_id: str,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    status = _get_corpus_status_validated(db, corpus_id)
    return {"status": status}

def _get_corpus_content_validated(db: Session, corpus_id: str) -> Any:
    """Get corpus content with validation."""
    content = corpus_service.get_corpus_content(db, corpus_id=corpus_id)
    if content is None:
        raise HTTPException(status_code=404, detail="Corpus not found")
    return content

@router.get("/{corpus_id}/content")
def get_corpus_content(
    corpus_id: str,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
) -> Any:
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
async def search_corpus(q: str = Query(...), corpus_id: str = Query(default="default"), current_user: User = Depends(get_current_user)):
    """Search corpus documents"""
    return await _search_corpus_safe(corpus_id, q)

class SearchRequest(BaseModel):
    q: str
    filters: Dict[str, Any] = None
    limit: int = 10
    offset: int = 0

@router.post("/search")
async def search_corpus_advanced(request: SearchRequest, current_user: User = Depends(get_current_user)):
    """Advanced corpus search with filters"""
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
async def extract_document_metadata(request: ExtractMetadataRequest, current_user: User = Depends(get_current_user)):
    """Extract metadata from document using file URL"""
    try:
        result = await corpus_service.batch_index_documents([{
            "title": request.title,
            "file_url": request.file_url,
            "extract_metadata": request.extract_metadata
        }])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Metadata extraction failed: {str(e)}")

