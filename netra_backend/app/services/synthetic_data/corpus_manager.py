from netra_backend.app.logging_config import central_logger
"""
Corpus management for synthetic data generation
"""

import asyncio
import uuid
from datetime import UTC, datetime
from typing import Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession


def _check_corpus_cache(corpus_id: str, corpus_cache: Dict) -> Optional[List[Dict]]:
    """Check if corpus is already cached"""
    if corpus_id in corpus_cache:
        return corpus_cache[corpus_id]
    return None


def _get_corpus_metadata(corpus_id: str, db: AsyncSession):
    """Get corpus metadata from PostgreSQL"""
    from netra_backend.app.db import models_postgres as models
    db_corpus = db.query(models.Corpus).filter(models.Corpus.id == corpus_id).first()
    if not db_corpus or db_corpus.status != "completed":
        return None
    return db_corpus


async def _query_clickhouse_data(table_name: str, get_clickhouse_client):
    """Query corpus data from ClickHouse"""
    async with get_clickhouse_client() as client:
        query = f"""SELECT workload_type, prompt, response, metadata FROM {table_name} LIMIT 10000"""
        result = await client.execute(query)
        return result


def _process_corpus_rows(result) -> List[Dict]:
    """Convert ClickHouse rows to list of dicts"""
    corpus_data = []
    for row in result:
        corpus_data.append({"workload_type": row[0], "prompt": row[1], "response": row[2], "metadata": row[3]})
    return corpus_data


def _cache_and_return(corpus_id: str, corpus_data: List[Dict], corpus_cache: Dict) -> List[Dict]:
    """Cache corpus data and return it"""
    corpus_cache[corpus_id] = corpus_data
    return corpus_data


async def load_corpus(corpus_id: str, db: AsyncSession, corpus_cache: Dict, 
                     get_clickhouse_client, central_logger) -> Optional[List[Dict]]:
    """Load corpus content from database or ClickHouse"""
    cached_result = _check_corpus_cache(corpus_id, corpus_cache)
    if cached_result:
        return cached_result
    
    try:
        db_corpus = _get_corpus_metadata(corpus_id, db)
        if not db_corpus:
            return None
        result = await _query_clickhouse_data(db_corpus.table_name, get_clickhouse_client)
        if result:
            corpus_data = _process_corpus_rows(result)
            return _cache_and_return(corpus_id, corpus_data, corpus_cache)
    except Exception as e:
        central_logger.warning(f"Failed to load corpus {corpus_id}: {str(e)}")
    return None


async def get_corpus_cached(corpus_id: str, corpus_cache: Dict) -> List[Dict]:
    """Get corpus with caching"""
    if corpus_id in corpus_cache:
        return corpus_cache[corpus_id]
    
    # Simulate loading corpus
    await asyncio.sleep(0.1)  # Simulate network delay
    corpus_data = [{"prompt": f"Prompt {i}", "response": f"Response {i}"} for i in range(100)]
    
    corpus_cache[corpus_id] = corpus_data
    return corpus_data


async def create_corpus_version(corpus_name: str, version: int = 1, changes: Dict = None) -> Dict:
    """Create a versioned corpus"""
    version_id = str(uuid.uuid4())
    return {
        'corpus_name': corpus_name,
        'version': version,
        'version_id': version_id,
        'changes': changes or {},
        'created_at': datetime.now(UTC).isoformat()
    }


def _get_num_traces(config, default: int = 1000) -> int:
    """Get number of traces from config"""
    return getattr(config, 'num_traces', default)

async def _generate_records(config, corpus_content: List[Dict], generate_single_record_fn, num_traces: int) -> List[Dict]:
    """Generate records using single record function"""
    records = []
    for i in range(num_traces):
        record = await generate_single_record_fn(config, corpus_content, i)
        records.append(record)
    return records

async def generate_from_corpus(config, corpus_content: List[Dict], generate_single_record_fn) -> List[Dict]:
    """Generate data using corpus content sampling"""
    num_traces = _get_num_traces(config, 1000)
    return await _generate_records(config, corpus_content, generate_single_record_fn, num_traces)


def _add_version_pattern(record: Dict, corpus_version: int, index: int) -> None:
    """Add version-specific pattern to record"""
    if corpus_version == 1:
        record['pattern_id'] = f"v1_pattern_{index % 10}"
    else:
        record['pattern_id'] = f"v{corpus_version}_pattern_{index % 15}"

async def _generate_versioned_record(config, generate_single_record_fn, corpus_version: int, index: int) -> Dict:
    """Generate a single versioned record"""
    record = await generate_single_record_fn(config, None, index)
    _add_version_pattern(record, corpus_version, index)
    return record

async def generate_from_corpus_version(config, corpus_version: int, generate_single_record_fn) -> List[Dict]:
    """Generate data from specific corpus version"""
    num_traces = _get_num_traces(config, 100)
    records = []
    for i in range(num_traces):
        record = await _generate_versioned_record(config, generate_single_record_fn, corpus_version, i)
        records.append(record)
    return records