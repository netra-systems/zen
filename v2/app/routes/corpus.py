from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from sqlalchemy.orm import Session
from .. import schemas
from ..services import corpus_service, clickhouse_service
from ..dependencies import get_db_session
from ..auth.auth_dependencies import get_current_user
from ..db.models_postgres import User

router = APIRouter()

class CorpusRoutes:

    @router.get("/tables", response_model=List[str])
    async def list_corpus_tables(self, current_user: User = Depends(get_current_user)) -> List[str]:
        return await clickhouse_service.list_corpus_tables()

    @router.post("/", response_model=schemas.Corpus)
    def create_corpus(
        self,
        corpus: schemas.CorpusCreate,
        request: Request,
        db: Session = Depends(get_db_session),
        current_user: User = Depends(get_current_user),
    ) -> schemas.Corpus:
        db_corpus = corpus_service.create_corpus(db=db, corpus=corpus, user_id=current_user.id)
        request.app.state.background_task_manager.add_task(corpus_service.generate_corpus_task(db_corpus.id, db))
        return db_corpus

    @router.get("/", response_model=List[schemas.Corpus])
    def read_corpora(
        self,
        skip: int = 0,
        limit: int = 100,
        db: Session = Depends(get_db_session),
        current_user: User = Depends(get_current_user)
    ) -> List[schemas.Corpus]:
        corpora = corpus_service.get_corpora(db, skip=skip, limit=limit)
        return corpora

    @router.get("/{corpus_id}", response_model=schemas.Corpus)
    def read_corpus(
        self,
        corpus_id: str,
        db: Session = Depends(get_db_session),
        current_user: User = Depends(get_current_user)
    ) -> schemas.Corpus:
        db_corpus = corpus_service.get_corpus(db, corpus_id=corpus_id)
        if db_corpus is None:
            raise HTTPException(status_code=404, detail="Corpus not found")
        return db_corpus

    @router.put("/{corpus_id}", response_model=schemas.Corpus)
    def update_corpus(
        self,
        corpus_id: str,
        corpus: schemas.CorpusUpdate,
        db: Session = Depends(get_db_session),
        current_user: User = Depends(get_current_user)
    ) -> schemas.Corpus:
        db_corpus = corpus_service.update_corpus(db, corpus_id=corpus_id, corpus=corpus)
        if db_corpus is None:
            raise HTTPException(status_code=404, detail="Corpus not found")
        return db_corpus

    @router.delete("/{corpus_id}", response_model=schemas.Corpus)
    def delete_corpus(
        self,
        corpus_id: str,
        db: Session = Depends(get_db_session),
        current_user: User = Depends(get_current_user)
    ) -> schemas.Corpus:
        db_corpus = corpus_service.delete_corpus(db, corpus_id=corpus_id)
        if db_corpus is None:
            raise HTTPException(status_code=404, detail="Corpus not found")
        return db_corpus

    @router.post("/{corpus_id}/generate", response_model=schemas.Corpus)
    def regenerate_corpus(
        self,
        corpus_id: str,
        request: Request,
        db: Session = Depends(get_db_session),
        current_user: User = Depends(get_current_user)
    ) -> schemas.Corpus:
        db_corpus = corpus_service.get_corpus(db, corpus_id=corpus_id)
        if db_corpus is None:
            raise HTTPException(status_code=404, detail="Corpus not found")
        
        request.app.state.background_task_manager.add_task(corpus_service.generate_corpus_task(db_corpus.id, db))
        return db_corpus

    @router.get("/{corpus_id}/status")
    def get_corpus_status(
        self,
        corpus_id: str,
        db: Session = Depends(get_db_session),
        current_user: User = Depends(get_current_user)
    ) -> Dict[str, Any]:
        status = corpus_service.get_corpus_status(db, corpus_id=corpus_id)
        if status is None:
            raise HTTPException(status_code=404, detail="Corpus not found")
        return {"status": status}

    @router.get("/{corpus_id}/content")
    def get_corpus_content(
        self,
        corpus_id: str,
        db: Session = Depends(get_db_session),
        current_user: User = Depends(get_current_user)
    ) -> Any:
        content = corpus_service.get_corpus_content(db, corpus_id=corpus_id)
        if content is None:
            raise HTTPException(status_code=404, detail="Corpus not found")
        return content
