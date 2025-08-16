"""Synthetic log generation service.

Provides synthetic log data generation using realistic parameters
and content corpus for creating training datasets.
"""

import hashlib
import random
import uuid
from multiprocessing import Pool, cpu_count
from typing import Dict, Any

import numpy as np
import pandas as pd
from faker import Faker

from app.data.content_corpus import DEFAULT_CONTENT_CORPUS
from app.services.generation_job_manager import (
    update_job_status,
    load_corpus_from_file,
    create_output_directory,
    save_job_result_to_file,
    finalize_job_completion
)
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


def _extract_generation_config(config, num_logs):
    """Extract configuration and generate random choices."""
    apps = config['realism']['applications']
    models = config['realism']['models']
    app_choices = np.random.choice(len(apps), num_logs)
    model_choices = np.random.choice(len(models), num_logs)
    return apps, models, app_choices, model_choices


def _generate_trace_types_and_content(config, content_corpus, num_logs):
    """Generate trace types and extract prompts/responses."""
    trace_types = list(config['generation_settings']['trace_distribution'].keys())
    weights = list(config['generation_settings']['trace_distribution'].values())
    chosen_trace_types = np.random.choice(trace_types, num_logs, p=weights)
    prompts, responses = [], []
    for trace_type in chosen_trace_types:
        corpus_to_use = content_corpus if trace_type in content_corpus and content_corpus[trace_type] else DEFAULT_CONTENT_CORPUS
        prompt, response = random.choice(corpus_to_use.get(trace_type, []))
        prompts.append(prompt)
        responses.append(response)
    return prompts, responses


def _create_base_dataframe(num_logs, apps, models, app_choices, model_choices, prompts, responses):
    """Create base DataFrame with core columns."""
    return pd.DataFrame({
        'trace_id': [str(uuid.uuid4()) for _ in range(num_logs)],
        'span_id': [str(uuid.uuid4()) for _ in range(num_logs)],
        'app_name': [apps[i]['app_name'] for i in app_choices],
        'service_name': [random.choice(apps[i]['services']) for i in app_choices],
        'model_provider': [models[i]['provider'] for i in model_choices],
        'model_name': [models[i]['name'] for i in model_choices],
        'model_pricing': [models[i]['pricing'] for i in model_choices],
        'user_prompt': prompts, 'assistant_response': responses,
        'prompt_tokens': [len(p.split()) * 2 for p in prompts],
        'completion_tokens': [len(r.split()) * 2 for r in responses],
        'total_e2e_ms': np.random.randint(200, 2000, size=num_logs),
        'ttft_ms': np.random.randint(150, 800, size=num_logs),
        'user_id': [str(uuid.uuid4()) for _ in range(num_logs)],
        'organization_id': [f"org_{hashlib.sha256(Faker().company().encode()).hexdigest()[:12]}" for _ in range(num_logs)]
    })


def _calculate_costs_and_totals(df):
    """Calculate token totals and costs."""
    df['total_tokens'] = df['prompt_tokens'] + df['completion_tokens']
    df['prompt_cost'] = (df['prompt_tokens'] / 1_000_000) * df['model_pricing'].apply(lambda x: x[0])
    df['completion_cost'] = (df['completion_tokens'] / 1_000_000) * df['model_pricing'].apply(lambda x: x[1])
    df['total_cost'] = df['prompt_cost'] + df['completion_cost']
    return df


def generate_data_chunk_for_service(args):
    """Generate synthetic data chunk using multiprocessing."""
    num_logs, config, content_corpus = args
    apps, models, app_choices, model_choices = _extract_generation_config(config, num_logs)
    prompts, responses = _generate_trace_types_and_content(config, content_corpus, num_logs)
    df = _create_base_dataframe(num_logs, apps, models, app_choices, model_choices, prompts, responses)
    return _calculate_costs_and_totals(df)


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


def get_config():
    """Loads the application configuration from config.yaml."""
    import yaml
    with open("config.yaml", 'r') as f:
        return yaml.safe_load(f)


async def run_log_generation_job(job_id: str, params: dict):
    """The core worker process for generating a synthetic log set."""
    await update_job_status(job_id, "running", progress={'completed_logs': 0, 'total_logs': params['num_logs']})
    try:
        config = get_config()
        content_corpus = load_corpus_from_file(params['corpus_id'])
        all_logs = await _generate_synthetic_logs(job_id, params, config, content_corpus)
        output_dir = create_output_directory(job_id, "log_sets")
        output_path = save_job_result_to_file(output_dir, "synthetic_logs.json", all_logs)
        summary = {"logs_generated": len(all_logs)}
        await finalize_job_completion(job_id, output_path, summary)
    except Exception as e:
        logger.exception("Error during log generation job")
        await update_job_status(job_id, "failed", error=str(e))


async def _generate_synthetic_logs(job_id: str, params: dict, config: dict, content_corpus: dict):
    """Generate synthetic logs using multiprocessing."""
    num_logs = params['num_logs']
    num_processes = min(cpu_count(), params['max_cores'])
    chunk_size = num_logs // num_processes
    chunks = [chunk_size] * num_processes
    remainder = num_logs % num_processes
    if remainder:
        chunks.append(remainder)
    worker_args = [(chunk, config, content_corpus) for chunk in chunks]
    results = []
    completed_logs = 0
    with Pool(processes=num_processes) as pool:
        for i, result_df in enumerate(pool.imap_unordered(generate_data_chunk_for_service, worker_args)):
            results.append(result_df)
            completed_logs += len(result_df)
            await update_job_status(job_id, "running", progress={'completed_logs': completed_logs, 'total_logs': num_logs})
    combined_df = pd.concat(results, ignore_index=True)
    return [format_log_entry(row) for _, row in combined_df.iterrows()]