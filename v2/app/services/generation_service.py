# app/services/generation_service.py

import os
import json
import time
import uuid
import logging
from multiprocessing import Pool, cpu_count
from functools import partial

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
        GENERATION_JOBS[job_id] = {"status": "failed", "error": str(e)}
        return

    GENERATION_JOBS[job_id]["status"] = "running"
    
    generation_config = genai.types.GenerationConfig(
        temperature=params['temperature'],
        top_p=params.get('top_p'),
        top_k=params.get('top_k')
    )
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    workload_types = list(META_PROMPTS.keys())
    num_processes = min(cpu_count(), params['max_cores'])
    
    worker_func = partial(generate_content_sample, model=model, generation_config=generation_config)
    tasks = [w_type for w_type in workload_types for _ in range(params['samples_per_type'])]

    corpus = {key: [] for key in workload_types}
    
    with Pool(processes=num_processes) as pool:
        results = pool.map(worker_func, tasks)

    for item in results:
        if item:
            corpus[item['type']].append(item['data'])

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
    GENERATION_JOBS[job_id]["status"] = "running"
    
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
        with Pool(processes=num_processes) as pool:
            results = pool.map(generate_data_chunk_for_service, worker_args)
        
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
        GENERATION_JOBS[job_id]["status"] = "failed"
        GENERATION_JOBS[job_id]["error"] = str(e)

from ..config import settings

def run_content_corpus_generation_job(job_id: str, params: dict):
    """The core worker process for generating a content corpus and storing it in ClickHouse."""
    try:
        import google.generativeai as genai
        GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not set")
        genai.configure(api_key=GEMINI_API_KEY)
    except (ImportError, ValueError) as e:
        GENERATION_JOBS[job_id] = {"status": "failed", "error": str(e)}
        return

    GENERATION_JOBS[job_id]["status"] = "running"
    
    generation_params = {
        "temperature": params['temperature'],
        "top_p": params.get('top_p'),
        "top_k": params.get('top_k')
    }
    
    workload_types = list(META_PROMPTS.keys())
    num_processes = min(cpu_count(), params['max_cores'])
    
    worker_func = partial(generate_content_sample, generation_params=generation_params)
    tasks = [w_type for w_type in workload_types for _ in range(params['samples_per_type'])]

    corpus = {key: [] for key in workload_types}
    
    with Pool(processes=num_processes) as pool:
        results = pool.map(worker_func, tasks)

    for item in results:
        if item:
            corpus[item['type']].append(item['data'])

    # Store in ClickHouse
    try:
        client = Client(**settings.clickhouse_native.model_dump())
        client.execute(CONTENT_CORPUS_TABLE_SCHEMA)
        
        corpus_id = uuid.uuid4()
        data_to_insert = []
        for workload_type, samples in corpus.items():
            for sample in samples:
                if isinstance(sample, list):
                    for s in sample:
                        data_to_insert.append({
                            "corpus_id": corpus_id,
                            "workload_type": workload_type,
                            "user_prompt": s[0],
                            "assistant_response": s[1]
                        })
                else:
                    data_to_insert.append({
                        "corpus_id": corpus_id,
                        "workload_type": workload_type,
                        "user_prompt": sample[0],
                        "assistant_response": sample[1]
                    })
        
        client.execute(f"INSERT INTO {CONTENT_CORPUS_TABLE_NAME} VALUES", data_to_insert)

        GENERATION_JOBS[job_id].update({
            "status": "completed",
            "finished_at": time.time(),
            "summary": {"message": f"Content corpus {corpus_id} generated and stored in ClickHouse."}
        })

    except Exception as e:
        logging.exception("Error during content corpus generation job")
        GENERATION_JOBS[job_id]["status"] = "failed"
        GENERATION_JOBS[job_id]["error"] = str(e)


from ..config import settings

def run_data_ingestion_job(job_id: str, params: dict):
    """The core worker process for ingesting data into ClickHouse."""
    GENERATION_JOBS[job_id]["status"] = "running"
    
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
        GENERATION_JOBS[job_id]["status"] = "failed"
        GENERATION_JOBS[job_id]["error"] = str(e)


def run_synthetic_data_generation_job(job_id: str, params: dict):
    """The core worker process for generating a synthetic log set."""
    GENERATION_JOBS[job_id]["status"] = "running"
    
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
        GENERATION_JOBS[job_id]["status"] = "failed"
        GENERATION_JOBS[job_id]["error"] = str(e)
