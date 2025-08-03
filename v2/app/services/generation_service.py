# app/services/generation_service.py

import os
import json
import time
import uuid
import logging
from multiprocessing import Pool, cpu_count
from functools import partial
import random
import hashlib

import pandas as pd
import numpy as np
from faker import Faker

from ..config import settings
from ..data.synthetic.content_generator import META_PROMPTS, generate_content_sample
from ..db.clickhouse import ClickHouseClient
from ..db.models_clickhouse import ContentCorpus, get_content_corpus_schema
from ..data.ingestion import ingest_records

# --- Job Management ---
GENERATION_JOBS = {}

def update_job_status(job_id: str, status: str, **kwargs):
    """Updates the status and other attributes of a generation job."""
    if job_id not in GENERATION_JOBS:
        GENERATION_JOBS[job_id] = {}
    
    job = GENERATION_JOBS[job_id]
    job['status'] = status
    job['last_updated'] = time.time()
    job.update(kwargs)

def save_corpus_to_clickhouse(corpus: dict, table_name: str):
    """Saves the generated content corpus to a specified ClickHouse table."""
    db = None  # Initialize db to None
    try:
        db = ClickHouseClient(
            host=settings.clickhouse_https.host,
            port=settings.clickhouse_https.port,
            user=settings.clickhouse_https.user,
            password=settings.clickhouse_https.password,
            database=settings.clickhouse_https.database
        )
        db.connect()
        
        table_schema = get_content_corpus_schema(table_name)
        db.command(table_schema)
        
        records = []
        for w_type, samples in corpus.items():
            for sample in samples:
                actual_sample = sample
                # Unpack if it's a list with a single tuple inside
                if isinstance(actual_sample, list) and len(actual_sample) == 1 and isinstance(actual_sample[0], tuple):
                    actual_sample = actual_sample[0]

                if isinstance(actual_sample, (list, tuple)) and len(actual_sample) == 2:
                    prompt_text, response_text = actual_sample
                    record = ContentCorpus(
                        workload_type=w_type,
                        prompt=prompt_text,
                        response=response_text,
                        record_id=str(uuid.uuid4())
                    )
                    records.append(record)
                else:
                    logging.warning(f"Skipping malformed sample for workload '{w_type}': {sample}")
                    continue

        if not records:
            logging.info(f"No valid records to insert into ClickHouse table: {table_name}")
            return

        db.insert_data(table_name, [list(record.model_dump().values()) for record in records], list(ContentCorpus.model_fields.keys()))
        logging.info(f"Successfully saved {len(records)} records to ClickHouse table: {table_name}")

    except Exception as e:
        logging.exception(f"Failed to save corpus to ClickHouse table {table_name}")
        raise
    finally:
        if db and db.is_connected():
            db.disconnect()


# --- Content Generation Service ---
def run_content_generation_job(job_id: str, params: dict):
    """The core worker process for generating a content corpus."""
    try:
        import google.generativeai as genai
        GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not set")
        genai.configure(api_key=GEMINI_API_KEY)
    except (ImportError, ValueError) as e:
        update_job_status(job_id, "failed", error=str(e))
        return

    total_tasks = len(list(META_PROMPTS.keys())) * params.get('samples_per_type', 10)
    update_job_status(job_id, "running", progress=0, total_tasks=total_tasks)

    generation_config = genai.types.GenerationConfig(
        temperature=params.get('temperature', 0.7),
        top_p=params.get('top_p'),
        top_k=params.get('top_k')
    )
    model = genai.GenerativeModel(settings.corpus_generation_model)

    workload_types = list(META_PROMPTS.keys())
    num_processes = min(cpu_count(), params.get('max_cores', 4))

    worker_func = partial(generate_content_sample, model=model, generation_config=generation_config)
    tasks = [w_type for w_type in workload_types for _ in range(params.get('samples_per_type', 10))]

    corpus = {key: [] for key in workload_types}
    
    completed_tasks = 0
    with Pool(processes=num_processes) as pool:
        for i, result in enumerate(pool.imap_unordered(worker_func, tasks)):
            if result and result.get('type') in corpus:
                corpus[result['type']].append(result['data'])
            
            completed_tasks += 1
            update_job_status(job_id, "running", progress=completed_tasks)

    # Save to ClickHouse
    clickhouse_table = params.get('clickhouse_table', 'content_corpus')
    try:
        save_corpus_to_clickhouse(corpus, clickhouse_table)
        summary = {
            "message": f"Corpus generated and saved to {clickhouse_table}",
            "counts": {w_type: len(samples) for w_type, samples in corpus.items()}
        }
        update_job_status(job_id, "completed", summary=summary)
    except Exception as e:
        update_job_status(job_id, "failed", error=f"Failed to save to ClickHouse: {e}")


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
        prompt, response = random.choice(corpus_to_use[trace_type])
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

def run_log_generation_job(job_id: str, params: dict):
    """The core worker process for generating a synthetic log set."""
    update_job_status(job_id, "running", progress={'completed_logs': 0, 'total_logs': params['num_logs']})
    
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
                update_job_status(job_id, "running", progress={'completed_logs': completed_logs, 'total_logs': num_logs})

        
        combined_df = pd.concat(results, ignore_index=True)
        all_logs = [format_log_entry(row) for _, row in combined_df.iterrows()]

        output_dir = os.path.join("app", "data", "generated", "log_sets", job_id)
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, "synthetic_logs.json")
        
        with open(output_path, 'w') as f:
            json.dump(all_logs, f, indent=2)

        GENERATION_JOBS[job_id].update({
            "status": "completed",
            "finished_at": time.time(),
            "result_path": output_path,
            "summary": {"logs_generated": len(all_logs)}
        })

    except Exception as e:
        logging.exception("Error during log generation job")
        update_job_status(job_id, "failed", progress={'error': str(e)})


def run_data_ingestion_job(job_id: str, params: dict):
    """The core worker process for ingesting data into ClickHouse."""
    update_job_status(job_id, "running")
    
    try:
        summary = ingest_data_from_file(params['data_path'])
        GENERATION_JOBS[job_id].update({
            "status": "completed",
            "finished_at": time.time(),
            "summary": summary
        })

    except Exception as e:
        logging.exception("Error during data ingestion job")
        update_job_status(job_id, "failed", error=str(e))

from app.data.synthetic.synthetic_data_v2 import main
from app.db.models_clickhouse import LLM_EVENTS_TABLE_SCHEMA

def run_synthetic_data_generation_job(job_id: str, params: dict):
    """Generates and ingests synthetic logs in batches."""
    batch_size = params.get('batch_size', 1000)
    total_logs_to_gen = params.get('num_traces', 10000)
    table_name = params.get('clickhouse_table', 'JSON_HYBRID_EVENTS4')
    
    update_job_status(job_id, "running", progress=0, total_tasks=total_logs_to_gen, records_ingested=0)

    client = ClickHouseClient(
        host=settings.clickhouse_https.host, port=settings.clickhouse_https.port,
        user=settings.clickhouse_https.user, password=settings.clickhouse_https.password,
        database=settings.clickhouse_https.database
    )
    client.connect()
    client.command(LLM_EVENTS_TABLE_SCHEMA) 

    try:
        class Args:
            def __init__(self, num_traces, output_file):
                self.num_traces = num_traces
                self.output_file = output_file
                self.config = "config.yaml"
                self.max_cores = cpu_count()
                self.corpus_file = "content_corpus.json"

        args = Args(total_logs_to_gen, params.get('output_file', 'generated_logs.json'))
        
        generated_logs = main(args)
        records_ingested = 0
        log_batch = []

        for i, log_record in enumerate(generated_logs):
            log_batch.append(log_record)
            if len(log_batch) >= batch_size:
                ingested_count = ingest_records(client, log_batch, table_name)
                records_ingested += ingested_count
                log_batch.clear()
                update_job_status(job_id, "running", progress=i + 1, records_ingested=records_ingested)

        if log_batch: # Ingest any remaining logs
            ingested_count = ingest_records(client, log_batch, table_name)
            records_ingested += ingested_count

        update_job_status(job_id, "completed", progress=total_logs_to_gen, records_ingested=records_ingested)

    except Exception as e:
        logging.exception("Error during synthetic data generation job")
        update_job_status(job_id, "failed", error=str(e))
    finally:
        client.disconnect()