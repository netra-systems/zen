
import asyncio
from sqlalchemy.orm import Session
from ..db import models_postgres as models
from .. import schemas
from fastapi import HTTPException
from ..websockets import manager

def get_corpus(db: Session, corpus_id: str):
    return db.query(models.Corpus).filter(models.Corpus.id == corpus_id).first()

def get_corpora(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Corpus).offset(skip).limit(limit).all()

def create_corpus(db: Session, corpus: schemas.CorpusCreate, user_id: str):
    db_corpus = models.Corpus(**corpus.model_dump(), created_by_id=user_id)
    db.add(db_corpus)
    db.commit()
    db.refresh(db_corpus)
    return db_corpus

async def generate_corpus_task(corpus_id: str, db: Session):
    # Simulate a long-running task
    for i in range(10):
        await asyncio.sleep(1)
        progress = (i + 1) * 10
        db.query(models.Corpus).filter(models.Corpus.id == corpus_id).update({"status": f"running: {progress}%"})
        db.commit()
        await manager.broadcast(f"Corpus {corpus_id} progress: {progress}%")
    
    db.query(models.Corpus).filter(models.Corpus.id == corpus_id).update({"status": "completed"})
    db.commit()
    await manager.broadcast(f"Corpus {corpus_id} completed")
