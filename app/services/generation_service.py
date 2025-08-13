# app/services/generation_service.py

import os
import json
import time
import uuid
from app.logging_config import central_logger
from multiprocessing import Pool, cpu_count
from functools import partial
import random
import hashlib
from collections import defaultdict
import asyncio

import pandas as pd
import numpy as np
from faker import Faker

from app.config import settings
from app.schemas import ContentGenParams, LogGenParams, SyntheticDataGenParams, ContentCorpus
from app.data.synthetic.content_generator import META_PROMPTS
from app.db.clickhouse_base import ClickHouseDatabase
from app.db.clickhouse_query_fixer import ClickHouseQueryInterceptor
from app.db.models_clickhouse import get_content_corpus_schema, get_llm_events_table_schema
from app.data.ingestion import ingest_records
from app.data.content_corpus import DEFAULT_CONTENT_CORPUS
from app.services.job_store import job_store
from app.ws_manager import manager

# --- Job Management ---

async def update_job_status(job_id: str, status: str, **kwargs):
    """Updates the status and other attributes of a generation job and sends a WebSocket message."""
    await job_store.update(job_id, status, **kwargs)
    await manager.broadcast({"job_id": job_id, "status": status, **kwargs})

async def get_corpus_from_clickhouse(table_name: str) -> dict:
    """Fetches the content corpus from a specified ClickHouse table."""
    db = None
    try:
        base_db = ClickHouseDatabase(
            host=settings.clickhouse_https.host,
            port=settings.clickhouse_https.port,
            user=settings.clickhouse_https.user,
            password=settings.clickhouse_https.password,
            database=settings.clickhouse_https.database
        )
        db = ClickHouseQueryInterceptor(base_db)
        
        query = f"SELECT workload_type, prompt, response FROM {table_name}"
        results = await db.execute_query(query)
        
        corpus = defaultdict(list)
        for row in results:
            corpus[row['workload_type']].append((row['prompt'], row['response']))
            
        central_logger.get_logger(__name__).info(f"Successfully loaded {len(results)} records from corpus table {table_name}")
        return dict(corpus)

    except Exception as e:
        central_logger.get_logger(__name__).exception(f"Failed to load corpus from ClickHouse table {table_name}")
        raise
    finally:
        if 'db' in locals() and db:
            db.disconnect()

async def save_corpus_to_clickhouse(corpus: dict, table_name: str, job_id: str = None):
    """Saves the generated content corpus to a specified ClickHouse table."""
    if job_id:
        output_dir = os.path.join("app", "data", "generated", "content_corpuses", job_id)
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, "content_corpus.json")
        with open(output_path, 'w') as f:
            json.dump(corpus, f, indent=2)

    db = None
    try:
        base_db = ClickHouseDatabase(
            host=settings.clickhouse_https.host,
            port=settings.clickhouse_https.port,
            user=settings.clickhouse_https.user,
            password=settings.clickhouse_https.password,
            database=settings.clickhouse_https.database
        )
        db = ClickHouseQueryInterceptor(base_db)
        
        table_schema = get_content_corpus_schema(table_name)
        await db.command(table_schema)
        
        records = []
        for w_type, samples in corpus.items():
            for sample in samples:
                actual_sample = sample
                if isinstance(actual_sample, list) and len(actual_sample) == 1 and isinstance(actual_sample[0], tuple):
                    actual_sample = actual_sample[0]

                if isinstance(actual_sample, (list, tuple)) and len(actual_sample) == 2:
                    prompt_text, response_text = actual_sample
                    record = ContentCorpus(
                        workload_type=w_type,
                        prompt=prompt_text,
                        response=response_text,
                        record_id=uuid.uuid4(),
                        created_at=pd.Timestamp.now().to_pydatetime()
                    )
                    records.append(record)
                else:
                    central_logger.get_logger(__name__).warning(f"Skipping malformed sample for workload '{w_type}': {sample}")
                    continue

        if not records:
            central_logger.get_logger(__name__).info(f"No valid records to insert into ClickHouse table: {table_name}")
            return

        await db.insert_data(table_name, [list(record.model_dump().values()) for record in records], list(ContentCorpus.model_fields.keys()))
        central_logger.get_logger(__name__).info(f"Successfully saved {len(records)} records to ClickHouse table: {table_name}")

    except Exception as e:
        central_logger.get_logger(__name__).exception(f"Failed to save corpus to ClickHouse table {table_name}")
        raise
    finally:
        if 'db' in locals() and db:
            db.disconnect()


# --- Content Generation Service ---
from .generation_worker import init_worker, generate_content_for_worker

# A sentinel value to signal the end of the generator
_sentinel = object()

def _next_item(it):
    """A helper function to safely get the next item from a generator."""
    try:
        return next(it)
    except StopIteration:
        return _sentinel

def run_generation_in_pool(tasks, num_processes):
    with Pool(processes=num_processes, initializer=init_worker) as pool:
        for result in pool.imap_unordered(generate_content_for_worker, tasks):
            yield result

async def run_content_generation_job(job_id: str, params: ContentGenParams):
    """The core worker process for generating a content corpus."""
    try:
        # Basic check to ensure the API key is available before starting the pool
        if not settings.llm_configs['default'].api_key:
            raise ValueError("GEMINI_API_KEY not set")
    except ValueError as e:
        await update_job_status(job_id, "failed", error=str(e))
        return

    total_tasks = len(list(META_PROMPTS.keys())) * params.samples_per_type
    await update_job_status(job_id, "running", progress=0, total_tasks=total_tasks)

    # Create a serializable dictionary for generation_config
    generation_config_dict = {
        'temperature': params.temperature,
        'top_p': params.top_p,
        'top_k': params.top_k
    }
    # Filter out None values so the Google API doesn't complain
    generation_config_dict = {k: v for k, v in generation_config_dict.items() if v is not None}


    workload_types = list(META_PROMPTS.keys())
    num_processes = min(cpu_count(), params.max_cores)

    # Prepare tasks with serializable data
    tasks = [(w_type, generation_config_dict) for w_type in workload_types for _ in range(params.samples_per_type)]

    corpus = {key: [] for key in workload_types}
    completed_tasks = 0

    try:
        loop = asyncio.get_event_loop()
        blocking_generator = run_generation_in_pool(tasks, num_processes)
        
        while True:
            result = await loop.run_in_executor(None, _next_item, blocking_generator)
            if result is _sentinel:
                break

            if result and result.get('type') in corpus:
                corpus[result['type']].append(result['data'])
            
            completed_tasks += 1
            await update_job_status(job_id, "running", progress=completed_tasks)

    except Exception as e:
        central_logger.get_logger(__name__).exception("An error occurred during content generation.")
        await update_job_status(job_id, "failed", error=f"A worker process failed: {e}")
        return


    clickhouse_table = params.get('clickhouse_table', 'content_corpus')
    try:
        await save_corpus_to_clickhouse(corpus, clickhouse_table, job_id=job_id)
        summary = {
            "message": f"Corpus generated and saved to {clickhouse_table}",
            "counts": {w_type: len(samples) for w_type, samples in corpus.items()}
        }
        await update_job_status(job_id, "completed", summary=summary, result_path=os.path.join("app", "data", "generated", "content_corpuses", job_id, "content_corpus.json"))
    except Exception as e:
        await update_job_status(job_id, "failed", error=f"Failed to save to ClickHouse: {e}")


# --- Synthetic Log Generation Service ---

def generate_data_chunk_for_service(args):
    """Slightly modified version for service-based execution."""
    num_logs, config, content_corpus = args
    apps = config['realism']['applications']
    models = config['realism']['models']
    app_choices = np.random.choice(len(apps), num_logs)
    model_choices = np.random.choice(len(models), num_logs)
    trace_types = list(config['generation_settings']['trace_distribution'].keys())
    weights = list(config['generation_settings']['trace_distribution'].values())
    chosen_trace_types = np.random.choice(trace_types, num_logs, p=weights)
    
    prompts, responses = [], []
    for trace_type in chosen_trace_types:
        corpus_to_use = content_corpus if trace_type in content_corpus and content_corpus[trace_type] else DEFAULT_CONTENT_CORPUS
        prompt, response = random.choice(corpus_to_use.get(trace_type, []))
        prompts.append(prompt)
        responses.append(response)

    df = pd.DataFrame({
        'trace_id': [str(uuid.uuid4()) for _ in range(num_logs)],
        'span_id': [str(uuid.uuid4()) for _ in range(num_logs)],
        'app_name': [apps[i]['app_name'] for i in app_choices],
        'service_name': [random.choice(apps[i]['services']) for i in app_choices],
        'model_provider': [models[i]['provider'] for i in model_choices],
        'model_name': [models[i]['name'] for i in model_choices],
        'model_pricing': [models[i]['pricing'] for i in model_choices],
        'user_prompt': prompts,
        'assistant_response': responses,
        'prompt_tokens': [len(p.split()) * 2 for p in prompts],
        'completion_tokens': [len(r.split()) * 2 for r in responses],
        'total_e2e_ms': np.random.randint(200, 2000, size=num_logs),
        'ttft_ms': np.random.randint(150, 800, size=num_logs),
        'user_id': [str(uuid.uuid4()) for _ in range(num_logs)],
        'organization_id': [f"org_{hashlib.sha256(Faker().company().encode()).hexdigest()[:12]}" for _ in range(num_logs)],
    })
    df['total_tokens'] = df['prompt_tokens'] + df['completion_tokens']
    df['prompt_cost'] = (df['prompt_tokens'] / 1_000_000) * df['model_pricing'].apply(lambda x: x[0])
    df['completion_cost'] = (df['completion_tokens'] / 1_000_000) * df['model_pricing'].apply(lambda x: x[1])
    df['total_cost'] = df['prompt_cost'] + df['completion_cost']
    return df

async def run_log_generation_job(job_id: str, params: LogGenParams):
    """The core worker process for generating a synthetic log set."""
    await update_job_status(job_id, "running", progress={'completed_logs': 0, 'total_logs': params['num_logs']})
    
    try:
        config = get_config()
        corpus_path = os.path.join("app", "data", "generated", "content_corpuses", params['corpus_id'], "content_corpus.json")
        if not os.path.exists(corpus_path):
            raise FileNotFoundError(f"Content corpus '{params['corpus_id']}' not found.")
        with open(corpus_path, 'r') as f:
            content_corpus = json.load(f)

        num_logs = params['num_logs']
        num_processes = min(cpu_count(), params['max_cores'])
        chunk_size = num_logs // num_processes
        chunks = [chunk_size] * num_processes
        remainder = num_logs % num_processes
        if remainder: chunks.append(remainder)

        worker_args = [(chunk, config, content_corpus) for chunk in chunks]
        
        results = []
        completed_logs = 0
        with Pool(processes=num_processes) as pool:
            for i, result_df in enumerate(pool.imap_unordered(generate_data_chunk_for_service, worker_args)):
                results.append(result_df)
                completed_logs += len(result_df)
                await update_job_status(job_id, "running", progress={'completed_logs': completed_logs, 'total_logs': num_logs})

        
        combined_df = pd.concat(results, ignore_index=True)
        all_logs = [format_log_entry(row) for _, row in combined_df.iterrows()]

        output_dir = os.path.join("app", "data", "generated", "log_sets", job_id)
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, "synthetic_logs.json")
        
        with open(output_path, 'w') as f:
            json.dump(all_logs, f, indent=2)

        await job_store.update(job_id, "completed", 
            finished_at=time.time(),
            result_path=output_path,
            summary={"logs_generated": len(all_logs)}
        )

    except Exception as e:
        central_logger.get_logger(__name__).exception("Error during log generation job")
        await update_job_status(job_id, "failed", error=str(e))


async def run_data_ingestion_job(job_id: str, params: dict):
    """The core worker process for ingesting data into ClickHouse."""
    await update_job_status(job_id, "running")
    
    try:
        summary = await ingest_data_from_file(params['data_path'])
        await job_store.update(job_id, "completed", 
            finished_at=time.time(),
            summary=summary
        )

    except Exception as e:
        central_logger.get_logger(__name__).exception("Error during data ingestion job")
        await update_job_status(job_id, "failed", error=str(e))

from app.data.synthetic.synthetic_data import main as synthetic_data_main

async def run_synthetic_data_generation_job(job_id: str, params: SyntheticDataGenParams):
    """Generates and ingests synthetic logs in batches from a ClickHouse corpus."""
    batch_size = params.get('batch_size', 1000)
    total_logs_to_gen = params.get('num_traces', 10000)
    source_table = params.get('source_table', 'content_corpus')
    destination_table = params.get('destination_table', 'synthetic_data')
    
    await update_job_status(job_id, "running", progress=0, total_tasks=total_logs_to_gen, records_ingested=0)

    base_client = ClickHouseDatabase(
        host=settings.clickhouse_https.host, port=settings.clickhouse_https.port,
        user=settings.clickhouse_https.user, password=settings.clickhouse_https.password,
        database=settings.clickhouse_https.database
    )
    client = ClickHouseQueryInterceptor(base_client)
    
    try:
        # Create the destination table
        table_schema = get_llm_events_table_schema(destination_table)
        await client.command(table_schema)

        content_corpus = await get_corpus_from_clickhouse(source_table)
        
        class Args:
            def __init__(self, num_traces, config, max_cores, corpus):
                self.num_traces = num_traces
                self.config = config
                self.max_cores = max_cores
                self.corpus = corpus

        args = Args(total_logs_to_gen, "config.yaml", cpu_count(), content_corpus)
        
        generated_logs = await synthetic_data_main(args)
        records_ingested = 0
        log_batch = []

        for i, log_record in enumerate(generated_logs):
            log_batch.append(log_record)
            if len(log_batch) >= batch_size:
                ingested_count = await ingest_records(client, log_batch, destination_table)
                records_ingested += ingested_count
                log_batch.clear()
                await update_job_status(job_id, "running", progress=i + 1, records_ingested=records_ingested)

        if log_batch:
            ingested_count = await ingest_records(client, log_batch, destination_table)
            records_ingested += ingested_count

        summary = {"message": f"Synthetic data generated and saved to {destination_table}", "records_ingested": records_ingested}
        await update_job_status(job_id, "completed", progress=total_logs_to_gen, records_ingested=records_ingested, summary=summary)

    except Exception as e:
        central_logger.get_logger(__name__).exception("Error during synthetic data generation job")
        await update_job_status(job_id, "failed", error=str(e))
    finally:
        if 'client' in locals() and client:
            client.disconnect()

def get_config():
    """Loads the application configuration from config.yaml."""
    import yaml
    with open("config.yaml", 'r') as f:
        return yaml.safe_load(f)

def format_log_entry(row):
    """Formats a DataFrame row into a structured log entry."""
    return {
        "timestamp": pd.Timestamp.now().isoformat(),
        "level": "INFO",
        "message": "API call processed",
        "trace_id": row['trace_id'],
        "span_id": row['span_id'],
        "metadata": {
            "app_name": row['app_name'],
            "service_name": row['service_name'],
            "model_provider": row['model_provider'],
            "model_name": row['model_name'],
            "user_id": row['user_id'],
            "organization_id": row['organization_id']
        },
        "llm_event": {
            "user_prompt": row['user_prompt'],
            "assistant_response": row['assistant_response'],
            "prompt_tokens": row['prompt_tokens'],
            "completion_tokens": row['completion_tokens'],
            "total_tokens": row['total_tokens'],
            "total_e2e_ms": row['total_e2e_ms'],
            "ttft_ms": row['ttft_ms'],
            "cost": {
                "prompt_cost": row['prompt_cost'],
                "completion_cost": row['completion_cost'],
                "total_cost": row['total_cost']
            }
        }
    }