"""
Corpus management for synthetic data generation
"""

import uuid
import asyncio
from datetime import datetime, UTC
from typing import Dict, List, Optional
from sqlalchemy.orm import Session


async def load_corpus(corpus_id: str, db: Session, corpus_cache: Dict, 
                     get_clickhouse_client, central_logger) -> Optional[List[Dict]]:
    """Load corpus content from database or ClickHouse"""
    if corpus_id in corpus_cache:
        return corpus_cache[corpus_id]
    
    try:
        # Import models locally to avoid circular imports
        from ...db import models_postgres as models
        
        # First check PostgreSQL for corpus metadata
        db_corpus = db.query(models.Corpus).filter(models.Corpus.id == corpus_id).first()
        if not db_corpus or db_corpus.status != "completed":
            return None
        
        # Query corpus table from ClickHouse
        table_name = db_corpus.table_name
        
        async with get_clickhouse_client() as client:
            query = f"""
                SELECT workload_type, prompt, response, metadata
                FROM {table_name}
                LIMIT 10000
            """
            
            result = await client.execute(query)
            
            if result:
                # Convert to list of dicts
                corpus_data = []
                for row in result:
                    corpus_data.append({
                        "workload_type": row[0],
                        "prompt": row[1],
                        "response": row[2],
                        "metadata": row[3]
                    })
                
                corpus_cache[corpus_id] = corpus_data
                return corpus_data
            
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


async def generate_from_corpus(config, corpus_content: List[Dict], generate_single_record_fn) -> List[Dict]:
    """Generate data using corpus content sampling"""
    records = []
    num_traces = getattr(config, 'num_traces', 1000)
    
    for i in range(num_traces):
        record = await generate_single_record_fn(config, corpus_content, i)
        records.append(record)
    
    return records


async def generate_from_corpus_version(config, corpus_version: int, generate_single_record_fn) -> List[Dict]:
    """Generate data from specific corpus version"""
    records = []
    num_traces = getattr(config, 'num_traces', 100)
    
    for i in range(num_traces):
        record = await generate_single_record_fn(config, None, i)
        
        # Add version-specific pattern
        if corpus_version == 1:
            record['pattern_id'] = f"v1_pattern_{i % 10}"
        else:
            record['pattern_id'] = f"v{corpus_version}_pattern_{i % 15}"  # More patterns in v2+
        
        records.append(record)
    
    return records