
from typing import List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from .. import schemas
from ..services import corpus_service
from ..dependencies import get_db
from ..auth.auth_dependencies import get_current_user
from ..db.models_postgres import User

router = APIRouter()

@router.post("/", response_model=schemas.Corpus)
def create_corpus(
    corpus: schemas.CorpusCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    background_tasks: BackgroundTasks = None
):
    # In a real application, you would add this to a background task queue
    # background_tasks.add_task(some_long_running_task, args)
    return corpus_service.create_corpus(db=db, corpus=corpus, user_id=current_user.id)

@router.get("/", response_model=List[schemas.Corpus])
def read_corpora(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    corpora = corpus_service.get_corpora(db, skip=skip, limit=limit)
    return corpora

@router.get("/{corpus_id}", response_model=schemas.Corpus)
def read_corpus(
    corpus_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_corpus = corpus_service.get_corpus(db, corpus_id=corpus_id)
    if db_corpus is None:
        raise HTTPException(status_code=404, detail="Corpus not found")
    return db_corpus
