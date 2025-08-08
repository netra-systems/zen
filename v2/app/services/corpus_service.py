import asyncio
import uuid
from sqlalchemy.orm import Session
from ..db import models_postgres as models
from .. import schemas
from ..ws_manager import manager
from ..db.clickhouse import get_clickhouse_client
from ..db.models_clickhouse import get_content_corpus_schema

def get_corpus(db: Session, corpus_id: str):
    return db.query(models.Corpus).filter(models.Corpus.id == corpus_id).first()

def get_corpora(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Corpus).offset(skip).limit(limit).all()

def create_corpus(db: Session, corpus: schemas.CorpusCreate, user_id: str):
    table_name = f"netra_content_corpus_{uuid.uuid4().hex}"
    db_corpus = models.Corpus(**corpus.model_dump(), created_by_id=user_id, table_name=table_name)
    db.add(db_corpus)
    db.commit()
    db.refresh(db_corpus)
    return db_corpus

def update_corpus(db: Session, corpus_id: str, corpus: schemas.CorpusUpdate):
    db_corpus = get_corpus(db, corpus_id)
    if db_corpus:
        for key, value in corpus.model_dump().items():
            setattr(db_corpus, key, value)
        db.commit()
        db.refresh(db_corpus)
    return db_corpus

def delete_corpus(db: Session, corpus_id: str):
    db_corpus = get_corpus(db, corpus_id)
    if db_corpus:
        db.delete(db_corpus)
        db.commit()
    return db_corpus

async def generate_corpus_task(corpus_id: str, db: Session):
    db_corpus = get_corpus(db, corpus_id)
    if not db_corpus:
        return

    table_name = db_corpus.table_name
    schema = get_content_corpus_schema(table_name)

    try:
        async with get_clickhouse_client() as client:
            await client.execute(schema)
            # Simulate data generation
            for i in range(10):
                await asyncio.sleep(1)
                progress = (i + 1) * 10
                db.query(models.Corpus).filter(models.Corpus.id == corpus_id).update({"status": f"running: {progress}%"})
                db.commit()
                await manager.broadcast(f"Corpus {corpus_id} progress: {progress}%")
                
                # Insert dummy data
                await client.execute(
                    f"INSERT INTO {table_name} (record_id, workload_type, prompt, response) VALUES",
                    [[uuid.uuid4(), 'test', f'prompt {i}', f'response {i}']]
                )

        db.query(models.Corpus).filter(models.Corpus.id == corpus_id).update({"status": "completed"})
        db.commit()
        await manager.broadcast(f"Corpus {corpus_id} completed")

    except Exception as e:
        db.query(models.Corpus).filter(models.Corpus.id == corpus_id).update({"status": "failed"})
        db.commit()
        await manager.broadcast(f"Corpus {corpus_id} failed: {e}")


def get_corpus_status(db: Session, corpus_id: str):
    db_corpus = get_corpus(db, corpus_id)
    return db_corpus.status if db_corpus else None

async def get_corpus_content(db: Session, corpus_id: str):
    db_corpus = get_corpus(db, corpus_id)
    if not db_corpus or db_corpus.status != "completed":
        return None

    async with get_clickhouse_client() as client:
        return await client.fetch(f"SELECT * FROM {db_corpus.table_name}")