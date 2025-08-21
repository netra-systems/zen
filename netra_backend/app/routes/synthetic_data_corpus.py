"""
Synthetic Data Corpus Management Routes
Handles corpus creation, upload, and management operations
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict

from netra_backend.app.services.corpus_service import corpus_service, ContentSource
from netra_backend.app.dependencies import get_db_session, get_db_dependency
from netra_backend.app.auth_integration.auth import get_current_user
from netra_backend.app.db.models_postgres import User
from netra_backend.app import schemas
from sqlalchemy.ext.asyncio import AsyncSession
from netra_backend.app.services.synthetic_data_service import SyntheticDataService

router = APIRouter(prefix="/api/synthetic/corpus", tags=["synthetic_corpus"])


def _build_corpus_response(corpus) -> Dict:
    """Build corpus creation response."""
    return {"corpus_id": corpus.id, "table_name": corpus.table_name, "status": corpus.status}

async def _create_corpus_with_source(corpus_data: schemas.CorpusCreate, content_source: str, db: Session, current_user: User) -> Dict:
    """Create corpus with specified source."""
    source = ContentSource[content_source.upper()]
    corpus = await corpus_service.create_corpus(db=db, corpus_data=corpus_data, user_id=current_user.id, content_source=source)
    return _build_corpus_response(corpus)

@router.post("/create")
async def create_corpus(corpus_data: schemas.CorpusCreate, content_source: str = Query("upload", pattern="^(upload|generate|import)$"), db: Session = Depends(get_db_session), current_user: User = Depends(get_current_user)):
    """Create new corpus table in ClickHouse"""
    return await _create_corpus_with_source(corpus_data, content_source, db, current_user)


async def _upload_content_safe(corpus_id: str, records: List[Dict], batch_id: Optional[str], is_final_batch: bool, db: Session, current_user: User):
    """Upload content with ownership verification."""
    await _verify_corpus_ownership(db, corpus_id, current_user.id)
    return await corpus_service.upload_content(db=db, corpus_id=corpus_id, records=records, batch_id=batch_id, is_final_batch=is_final_batch)

@router.post("/{corpus_id}/upload")
async def upload_corpus_content(corpus_id: str, records: List[Dict], batch_id: Optional[str] = None, is_final_batch: bool = False, db: Session = Depends(get_db_session), current_user: User = Depends(get_current_user)):
    """Upload content to corpus"""
    return await _upload_content_safe(corpus_id, records, batch_id, is_final_batch, db, current_user)


async def _get_content_safe(corpus_id: str, limit: int, offset: int, workload_type: Optional[str], db: Session, current_user: User) -> Dict:
    """Get corpus content with ownership verification."""
    await _verify_corpus_ownership(db, corpus_id, current_user.id)
    content = await corpus_service.get_corpus_content(db=db, corpus_id=corpus_id, limit=limit, offset=offset, workload_type=workload_type)
    return {"content": content}

@router.get("/{corpus_id}/content")
async def get_corpus_content(corpus_id: str, limit: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0), workload_type: Optional[str] = None, db: Session = Depends(get_db_session), current_user: User = Depends(get_current_user)):
    """Get corpus content with optional filtering"""
    return await _get_content_safe(corpus_id, limit, offset, workload_type, db, current_user)


async def _get_statistics_safe(corpus_id: str, db: Session, current_user: User):
    """Get corpus statistics with ownership verification."""
    await _verify_corpus_ownership(db, corpus_id, current_user.id)
    stats = await corpus_service.get_corpus_statistics(db, corpus_id)
    if not stats:
        raise HTTPException(status_code=500, detail="Failed to get statistics")
    return stats

@router.get("/{corpus_id}/statistics")
async def get_corpus_statistics(corpus_id: str, db: Session = Depends(get_db_session), current_user: User = Depends(get_current_user)):
    """Get corpus statistics"""
    return await _get_statistics_safe(corpus_id, db, current_user)


async def _delete_corpus_safe(corpus_id: str, db: Session, current_user: User) -> Dict:
    """Delete corpus with ownership verification."""
    await _verify_corpus_ownership(db, corpus_id, current_user.id)
    success = await corpus_service.delete_corpus(db, corpus_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete corpus")
    return {"message": "Corpus deleted successfully"}

@router.delete("/{corpus_id}")
async def delete_corpus(corpus_id: str, db: Session = Depends(get_db_session), current_user: User = Depends(get_current_user)):
    """Delete corpus and its ClickHouse table"""
    return await _delete_corpus_safe(corpus_id, db, current_user)


async def _clone_corpus_safe(corpus_id: str, new_name: str, db: Session, current_user: User) -> Dict:
    """Clone corpus with ownership verification."""
    await _verify_corpus_ownership(db, corpus_id, current_user.id)
    new_corpus = await corpus_service.clone_corpus(db=db, source_corpus_id=corpus_id, new_name=new_name, user_id=current_user.id)
    if not new_corpus:
        raise HTTPException(status_code=500, detail="Failed to clone corpus")
    return {"corpus_id": new_corpus.id, "table_name": new_corpus.table_name, "status": new_corpus.status}

@router.post("/{corpus_id}/clone")
async def clone_corpus(corpus_id: str, new_name: str, db: Session = Depends(get_db_session), current_user: User = Depends(get_current_user)):
    """Clone an existing corpus"""
    return await _clone_corpus_safe(corpus_id, new_name, db, current_user)


async def _get_and_validate_corpus(db: Session, corpus_id: str, user_id: int):
    """Get and validate corpus ownership."""
    corpus = await corpus_service.get_corpus(db, corpus_id)
    if not corpus:
        raise HTTPException(status_code=404, detail="Corpus not found")
    if corpus.created_by_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

async def _verify_corpus_ownership(db: Session, corpus_id: str, user_id: int):
    """Verify corpus ownership"""
    await _get_and_validate_corpus(db, corpus_id, user_id)