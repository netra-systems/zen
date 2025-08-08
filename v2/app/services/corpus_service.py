
from sqlalchemy.orm import Session
from ..db import models_postgres as models
from .. import schemas
from fastapi import HTTPException

def get_corpus(db: Session, corpus_id: str):
    return db.query(models.Corpus).filter(models.Corpus.id == corpus_id).first()

def get_corpora(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Corpus).offset(skip).limit(limit).all()

def create_corpus(db: Session, corpus: schemas.CorpusCreate, user_id: str):
    db_corpus = models.Corpus(**corpus.model_dump(), created_by_id=user_id)
    db.add(db_corpus)
    db.commit()
    db.refresh(db_corpus)
    # Here you would trigger a background task
    # For now, we'll just return the created object
    return db_corpus
