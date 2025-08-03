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

# Assuming the other scripts are in a sibling directory
from ..data.synthetic.content_generator import META_PROMPTS, generate_content_sample
from ..data.synthetic.synthetic_data_v2 import DEFAULT_CONTENT_CORPUS, format_log_entry, get_config, main as generate_synthetic_data
from ..db.models_clickhouse import ContentCorpus, CONTENT_CORPUS_TABLE_NAME, CONTENT_CORPUS_TABLE_SCHEMA

# --- Job Management ---
# In a production system, this would be a database (e.g., Redis, Postgres)
GENERATION_JOBS = {}

def update_job_status(job_id: str, status: str, progress: dict = None):
    """Updates the status and progress of a generation job."""
    if job_id not in GENERATION_JOBS:
        GENERATION_JOBS[job_id] = {}
    
    GENERATION_JOBS[job_id]['status'] = status
    GENERATION_JOBS[job_id]['last_updated'] = time.time()
    if progress:
        GENERATION_JOBS[job_id]['progress'] = progress

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
        update_job_status(job_id, "failed", progress={'error': str(e)})
        return

    update_job_status(job_id, "running", progress={'completed_tasks': 0, 'total_tasks': len(list(META_PROMPTS.keys())) * params['samples_per_type']})

    generation_config = genai.types.GenerationConfig(
        temperature=params['temperature'],
        top_p=params.get('top_p'),
        top_k=params.get('top_k')
    )
    model = genai.GenerativeModel(settings.corpus_generation_model)

    workload_types = list(META_PROMPTS.keys())
    num_processes = min(cpu_count(), params['max_cores'])

    worker_func = partial(generate_content_sample, model=model, generation_config=generation_config)
    tasks = [w_type for w_type in workload_types for _ in range(params['samples_per_type'])]

    corpus = {key: [] for key in workload_types}
    
    completed_tasks = 0
    with Pool(processes=num_processes) as pool:
        for i, result in enumerate(pool.imap_unordered(worker_func, tasks)):
            if result and result.get('type') in corpus:
                corpus[result['type']].append(result['data'])
            
            completed_tasks += 1
            if i % 5 == 0 or completed_tasks == len(tasks): # Update every 5 tasks or at the end
                update_job_status(job_id, "running", progress={'completed_tasks': completed_tasks, 'total_tasks': len(tasks)})


    # Save to file
    output_dir = os.path.join("app", "data", "generated", "content_corpuses", job_id)
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "content_corpus.json")

    with open(output_path, 'w') as f:
        json.dump(corpus, f, indent=2)

    GENERATION_JOBS[job_id].update({
        "status": "completed",
        "finished_at": time.time(),
        "result_path": output_path,
        "summary": {w_type: len(samples) for w_type, samples in corpus.items()}
    })

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




from ..config import settings

def run_data_ingestion_job(job_id: str, params: dict):
    """The core worker process for ingesting data into ClickHouse."""
    update_job_status(job_id, "running")
    
    try:
        # This is a placeholder for the actual table schema
        table_schema = {
            "event_metadata": "String",
            "trace_context": "String",
            "identity_context": "String",
            "application_context": "String",
            "request": "String",
            "response": "String",
            "performance": "String",
            "finops": "String",
            "timestamp_utc": "UInt64"
        }

        ingestor = DataIngestor(
            clickhouse_creds=settings.clickhouse_native.model_dump(),
            table_name=params['table_name'],
            table_schema=table_schema
        )
        ingestor.create_table_if_not_exists()
        ingestor.ingest_data(params['data_path'])

        GENERATION_JOBS[job_id].update({
            "status": "completed",
            "finished_at": time.time(),
            "summary": {"message": f"Data from {params['data_path']} ingested into {params['table_name']}"}
        })

    except Exception as e:
        logging.exception("Error during data ingestion job")
        update_job_status(job_id, "failed", progress={'error': str(e)})


def run_synthetic_data_generation_job(job_id: str, params: dict):
    """The core worker process for generating a synthetic log set."""
    update_job_status(job_id, "running")
    
    try:
        class Args:
            def __init__(self, num_traces, output_file):
                self.num_traces = num_traces
                self.output_file = output_file
                self.config = "config.yaml"
                self.max_cores = cpu_count()
                self.corpus_file = "content_corpus.json"

        args = Args(params['num_traces'], params['output_file'])
        generate_synthetic_data(args)

        GENERATION_JOBS[job_id].update({
            "status": "completed",
            "finished_at": time.time(),
            "result_path": params['output_file'],
            "summary": {"logs_generated": params['num_traces']}
        })

    except Exception as e:
        logging.exception("Error during synthetic data generation job")
        update_job_status(job_id, "failed", progress={'error': str(e)})
