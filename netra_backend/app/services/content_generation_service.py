"""Content generation service for creating synthetic content corpora.

Provides parallel content generation using LLM APIs with proper
job management, progress tracking, and result persistence.
"""

import os
import asyncio
from multiprocessing import Pool, cpu_count
from typing import Dict, Any

from netra_backend.app.config import settings
from netra_backend.app.data.synthetic.content_generator import META_PROMPTS
from netra_backend.app.services.generation_worker import init_worker, generate_content_for_worker
from netra_backend.app.services.generation_job_manager import (
    update_job_status,
    save_corpus_to_clickhouse,
    validate_job_params,
    create_output_directory,
    save_job_result_to_file
)
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

# A sentinel value to signal the end of the generator
_sentinel = object()


def _next_item(it):
    """A helper function to safely get the next item from a generator."""
    try:
        return next(it)
    except StopIteration:
        return _sentinel


def _process_result_batch(corpus, batch):
    """Process a batch of results efficiently."""
    for result in batch:
        if result and result.get('type') in corpus:
            corpus[result['type']].append(result['data'])


def run_generation_in_pool(tasks, num_processes):
    """Run content generation tasks in process pool."""
    with Pool(processes=num_processes, initializer=init_worker) as pool:
        for result in pool.imap_unordered(generate_content_for_worker, tasks):
            yield result


def _calculate_total_tasks(params: dict) -> int:
    """Calculate total number of generation tasks."""
    workload_count = len(list(META_PROMPTS.keys()))
    samples_per_type = getattr(params, 'samples_per_type', 10)
    return workload_count * samples_per_type


def _build_generation_config(params: dict) -> dict:
    """Build generation configuration from parameters."""
    config = {
        'temperature': getattr(params, 'temperature', 0.7),
        'top_p': getattr(params, 'top_p', None),
        'top_k': getattr(params, 'top_k', None)
    }
    return {k: v for k, v in config.items() if v is not None}


async def _prepare_generation_config(job_id: str, params: dict):
    """Prepares generation configuration and task setup."""
    total_tasks = _calculate_total_tasks(params)
    await update_job_status(job_id, "running", progress=0, total_tasks=total_tasks)
    generation_config = _build_generation_config(params)
    return generation_config, total_tasks


async def _create_generation_tasks(params: dict, generation_config: dict):
    """Creates tasks for content generation pool."""
    workload_types = list(META_PROMPTS.keys())
    num_processes = min(cpu_count(), getattr(params, 'max_cores', 4))
    samples_per_type = getattr(params, 'samples_per_type', 10)
    tasks = [(w_type, generation_config) for w_type in workload_types for _ in range(samples_per_type)]
    corpus = {key: [] for key in workload_types}
    return tasks, corpus, num_processes


async def _execute_generation_pool(job_id: str, tasks: list, num_processes: int, corpus: dict):
    """Executes the generation pool and processes results."""
    loop = asyncio.get_event_loop()
    blocking_generator = run_generation_in_pool(tasks, num_processes)
    batch_size = min(50, num_processes * 10)
    return await _process_generation_results(job_id, loop, blocking_generator, batch_size, corpus)


async def _process_batch_results(job_id: str, corpus: dict, batch: list, completed_tasks: int):
    """Processes a single batch of results and updates status."""
    if not batch:
        return completed_tasks
    _process_result_batch(corpus, batch)
    completed_tasks += len(batch)
    await update_job_status(job_id, "running", progress=completed_tasks)
    return completed_tasks


async def _get_next_generation_result(loop, generator):
    """Get next result from generation pool."""
    return await loop.run_in_executor(None, _next_item, generator)


def _should_include_result(result: dict, corpus: dict) -> bool:
    """Check if result should be included in corpus."""
    return result and result.get('type') in corpus


async def _collect_batch_item(batch: list, result: dict, corpus: dict) -> list:
    """Collect valid result item into batch."""
    if _should_include_result(result, corpus):
        batch.append(result)
    return batch

async def _process_when_batch_full(job_id: str, corpus: dict, batch: list, completed_tasks: int, batch_size: int) -> tuple:
    """Process batch when it reaches capacity."""
    if len(batch) >= batch_size:
        completed_tasks = await _process_batch_results(job_id, corpus, batch, completed_tasks)
        return [], completed_tasks
    return batch, completed_tasks

async def _process_generation_results(job_id: str, loop, generator, batch_size: int, corpus: dict):
    """Processes generation results in batches."""
    batch, completed_tasks = [], 0
    while True:
        result = await _get_next_generation_result(loop, generator)
        if result is _sentinel:
            break
        batch = await _collect_batch_item(batch, result, corpus)
        batch, completed_tasks = await _process_when_batch_full(job_id, corpus, batch, completed_tasks, batch_size)
    return await _process_batch_results(job_id, corpus, batch, completed_tasks)


def _build_corpus_summary(corpus: dict, table_name: str) -> dict:
    """Build summary of corpus generation results."""
    return {
        "message": f"Corpus generated and saved to {table_name}",
        "counts": {w_type: len(samples) for w_type, samples in corpus.items()}
    }


def _build_result_path(job_id: str) -> str:
    """Build file path for corpus results."""
    return os.path.join("app", "data", "generated", "content_corpuses", job_id, "content_corpus.json")


async def _save_generation_results(job_id: str, params: dict, corpus: dict):
    """Saves generation results to ClickHouse and updates job status."""
    clickhouse_table = getattr(params, 'clickhouse_table', 'content_corpus')
    await save_corpus_to_clickhouse(corpus, clickhouse_table, job_id=job_id)
    summary = _build_corpus_summary(corpus, clickhouse_table)
    result_path = _build_result_path(job_id)
    await update_job_status(job_id, "completed", summary=summary, result_path=result_path)


async def _handle_generation_error(job_id: str, error: Exception, context: str):
    """Handles errors during content generation."""
    logger.exception(f"Error in {context}")
    error_msg = f"A worker process failed: {error}" if "generation" in context else f"Failed to save to ClickHouse: {error}"
    await update_job_status(job_id, "failed", error=error_msg)


async def _execute_content_generation_workflow(job_id: str, params: dict):
    """Execute the core content generation workflow."""
    generation_config, total_tasks = await _prepare_generation_config(job_id, params)
    tasks, corpus, num_processes = await _create_generation_tasks(params, generation_config)
    await _execute_generation_pool(job_id, tasks, num_processes, corpus)
    await _save_generation_results(job_id, params, corpus)


async def run_content_generation_job(job_id: str, params: dict):
    """The core worker process for generating a content corpus."""
    if not await validate_job_params(job_id):
        return
    try:
        await _execute_content_generation_workflow(job_id, params)
    except Exception as e:
        await _handle_generation_error(job_id, e, "content generation")