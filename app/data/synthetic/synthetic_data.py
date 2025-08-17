# A High-Performance Synthetic Data Generation System for the Unified LLM Operations Schema .0

# USAGE:
# 1. A default `config.yaml` will be created on first run. Customize it as needed.
# 2. Run the script from your terminal:
#    python synthetic_data.py --num-traces 10000 --output-file generated_logs.json

import json
import random
import uuid
import time
import hashlib
import os
import yaml
import argparse
import numpy as np
import pandas as pd
from multiprocessing import Pool, cpu_count
import sys
 
from faker import Faker
from rich.console import Console
from rich.progress import Progress
from app.db.clickhouse import get_clickhouse_client
from app.db.models_clickhouse import CONTENT_CORPUS_TABLE_NAME, UnifiedLogEntry


# Import the same Pydantic schemas from v1 to ensure compatibility

from .default_synthetic_config import DEFAULT_CONFIG
from ..content_corpus import DEFAULT_CONTENT_CORPUS

console = Console()
fake = Faker()

# --- 1. HIGH-PERFORMANCE CONTENT ENGINE ---
# This is the default, fallback corpus. The script will prioritize loading
# an external corpus if available.



from app.config import settings

import asyncio

async def load_content_corpus_from_clickhouse() -> dict:
    """Loads the content corpus from the ClickHouse database via HTTPS,
    with a fallback to the default corpus if the connection fails.
    """
    try:
        return await _load_corpus_from_clickhouse_client()
    except Exception as e:
        return _handle_clickhouse_connection_error(e)

def _handle_clickhouse_connection_error(e: Exception) -> dict:
    """Handle ClickHouse connection errors."""
    console.print(f"[red]Error connecting to ClickHouse: {e}. Falling back to default corpus.[/red]")
    return DEFAULT_CONTENT_CORPUS

async def _load_corpus_from_clickhouse_client() -> dict:
    """Handle ClickHouse client operations for corpus loading."""
    async with get_clickhouse_client() as client:
        if not client.ping():
            console.print("[yellow]Warning: ClickHouse connection failed. Falling back to default corpus.[/yellow]")
            return DEFAULT_CONTENT_CORPUS
        return await _fetch_and_process_corpus_data(client)

async def _fetch_and_process_corpus_data(client) -> dict:
    """Fetch and process corpus data from ClickHouse."""
    query = f"SELECT workload_type, prompt, response FROM {CONTENT_CORPUS_TABLE_NAME}"
    query_result = await client.execute_query(query)
    corpus = _build_corpus_from_query_result(query_result)
    return _validate_corpus_result(corpus)

def _build_corpus_from_query_result(query_result) -> dict:
    """Build corpus dictionary from query results."""
    corpus = {}
    for row in query_result:
        workload_type = row['workload_type']
        _add_row_to_corpus(corpus, workload_type, row)
    return corpus

def _add_row_to_corpus(corpus: dict, workload_type: str, row: dict) -> None:
    """Add single row to corpus dictionary."""
    if workload_type not in corpus:
        corpus[workload_type] = []
    corpus[workload_type].append((row['prompt'], row['response']))

def _validate_corpus_result(corpus: dict) -> dict:
    """Validate corpus result and return appropriate fallback."""
    if not corpus:
        console.print("[yellow]Warning: Content corpus from ClickHouse is empty. Using default corpus.[/yellow]")
        return DEFAULT_CONTENT_CORPUS
    console.print("[green]Successfully loaded content corpus from ClickHouse.[/green]")
    return corpus


def load_content_corpus(corpus_path: str) -> dict:
    """Loads the content corpus from a JSON file, falling back to the default."""
    if os.path.exists(corpus_path):
        return _load_existing_corpus_file(corpus_path)
    return _handle_missing_corpus_file()

def _load_existing_corpus_file(corpus_path: str) -> dict:
    """Load and parse existing corpus file."""
    try:
        return _read_and_parse_corpus_file(corpus_path)
    except json.JSONDecodeError:
        return _handle_corpus_parse_error(corpus_path)

def _read_and_parse_corpus_file(corpus_path: str) -> dict:
    """Read and parse corpus file content."""
    with open(corpus_path, 'r') as f:
        console.print(f"[green]Loading content from external corpus: [cyan]{corpus_path}[/cyan][/green]")
        return json.load(f)

def _handle_corpus_parse_error(corpus_path: str) -> dict:
    """Handle corpus file parsing errors."""
    console.print(f"[red]Error: Could not parse '{corpus_path}'. Falling back to default corpus.")
    return DEFAULT_CONTENT_CORPUS

def _handle_missing_corpus_file() -> dict:
    """Handle case when corpus file is missing."""
    console.print("[yellow]Warning: External content corpus not found. Using default internal corpus.")
    return DEFAULT_CONTENT_CORPUS

# --- 2. CONFIGURATION MANAGEMENT (Identical to v1) ---
def get_config(config_path="config.yaml"):
    """Loads configuration from a YAML file, updating it if necessary."""
    config = _load_or_create_config(config_path)
    return _update_config_if_needed(config, config_path)

def _load_or_create_config(config_path: str) -> dict:
    """Load existing config or create default one."""
    if not os.path.exists(config_path):
        _create_default_config(config_path)
    
    with open(config_path, "r") as f:
        return yaml.safe_load(f)

def _create_default_config(config_path: str) -> None:
    """Create default configuration file."""
    console.print(f"[yellow]Config file not found. Creating default '{config_path}'...[/yellow]")
    with open(config_path, "w") as f:
        f.write(DEFAULT_CONFIG)

def _update_config_if_needed(config: dict, config_path: str) -> dict:
    """Update config with new trace types if needed."""
    generation_settings = config.get('generation_settings', {})
    trace_distribution = generation_settings.get('trace_distribution', {})
    
    if 'multi_turn_tool_use' not in trace_distribution:
        return _update_trace_distribution(config, config_path, trace_distribution)
    return config

def _update_trace_distribution(config: dict, config_path: str, trace_distribution: dict) -> dict:
    """Update trace distribution with new multi-turn tool use."""
    console.print("[yellow]Updating config file to include 'multi_turn_tool_use' trace type...[/yellow]")
    _add_multi_turn_tool_use(trace_distribution)
    _renormalize_trace_weights(trace_distribution)
    config['generation_settings']['trace_distribution'] = trace_distribution
    _save_updated_config(config, config_path)
    return config

def _add_multi_turn_tool_use(trace_distribution: dict) -> None:
    """Add multi-turn tool use to trace distribution."""
    trace_distribution['multi_turn_tool_use'] = 0.1

def _renormalize_trace_weights(trace_distribution: dict) -> None:
    """Renormalize trace weights to maintain total of 1.0."""
    total_weight = sum(trace_distribution.values())
    renormalization_factor = 0.9 / (total_weight - 0.1)
    _apply_renormalization_factor(trace_distribution, renormalization_factor)
    _ensure_weight_sum_equals_one(trace_distribution)

def _apply_renormalization_factor(trace_distribution: dict, renormalization_factor: float) -> None:
    """Apply renormalization factor to trace weights."""
    for key, value in trace_distribution.items():
        if key != 'multi_turn_tool_use':
            trace_distribution[key] = value * renormalization_factor

def _ensure_weight_sum_equals_one(trace_distribution: dict) -> None:
    """Ensure trace distribution weights sum to 1.0."""
    total_sum = sum(trace_distribution.values())
    if total_sum != 1.0:
        trace_distribution['simple_chat'] += 1.0 - total_sum

def _save_updated_config(config: dict, config_path: str) -> None:
    """Save updated configuration to file."""
    with open(config_path, "w") as f:
        yaml.dump(config, f)
    console.print("[green]Config file updated successfully.[/green]")

# --- 3. VECTORIZED & TRACE DATA GENERATION ---

def _generate_app_model_choices(num_logs: int, config: dict) -> tuple[np.ndarray, np.ndarray, list, list]:
    """Generate app and model selections for data chunk."""
    apps = config['realism']['applications']
    models = config['realism']['models']
    app_choices = np.random.choice(len(apps), num_logs)
    model_choices = np.random.choice(len(models), num_logs)
    return app_choices, model_choices, apps, models

def _generate_trace_type_weights(config: dict) -> tuple[list, np.ndarray]:
    """Generate normalized weights for simple trace types."""
    trace_dist = config['generation_settings']['trace_distribution']
    simple_types = [t for t in trace_dist.keys() if t != 'multi_turn_tool_use']
    simple_weights = [trace_dist[t] for t in simple_types]
    normalized_weights = np.array(simple_weights) / np.sum(simple_weights)
    return simple_types, normalized_weights

def _generate_content_pairs(num_logs: int, config: dict, content_corpus: dict) -> tuple[list, list]:
    """Generate prompt and response pairs for data chunk."""
    simple_types, weights = _generate_trace_type_weights(config)
    chosen_types = np.random.choice(simple_types, num_logs, p=weights)
    return _build_prompt_response_pairs(chosen_types, content_corpus)

def _build_prompt_response_pairs(chosen_types: np.ndarray, content_corpus: dict) -> tuple[list, list]:
    """Build prompt and response pairs from chosen trace types."""
    prompts, responses = [], []
    for trace_type in chosen_types:
        prompt, response = _get_random_content_pair(trace_type, content_corpus)
        prompts.append(prompt)
        responses.append(response)
    return prompts, responses

def _get_random_content_pair(trace_type: str, content_corpus: dict) -> tuple[str, str]:
    """Get random prompt-response pair for trace type."""
    corpus_source = _select_corpus_source(trace_type, content_corpus)
    return random.choice(corpus_source[trace_type])

def _select_corpus_source(trace_type: str, content_corpus: dict) -> dict:
    """Select appropriate corpus source for trace type."""
    if trace_type in content_corpus and content_corpus[trace_type]:
        return content_corpus
    return DEFAULT_CONTENT_CORPUS

def _generate_trace_identifiers(num_logs: int) -> dict:
    """Generate trace and span identifiers for DataFrame."""
    return {
        'trace_id': [str(uuid.uuid4()) for _ in range(num_logs)],
        'span_id': [str(uuid.uuid4()) for _ in range(num_logs)]
    }

def _generate_app_service_data(app_choices: np.ndarray, apps: list) -> dict:
    """Generate application and service data for DataFrame."""
    return {
        'app_name': [apps[i]['app_name'] for i in app_choices],
        'service_name': [random.choice(apps[i]['services']) for i in app_choices]
    }

def _generate_model_data(model_choices: np.ndarray, models: list) -> dict:
    """Generate model provider and configuration data for DataFrame."""
    return {
        'model_provider': [models[i]['provider'] for i in model_choices],
        'model_name': [models[i]['name'] for i in model_choices],
        'model_pricing': [models[i]['pricing'] for i in model_choices]
    }

def _create_base_dataframe(num_logs: int, app_choices: np.ndarray, model_choices: np.ndarray, 
                          apps: list, models: list, prompts: list, responses: list) -> pd.DataFrame:
    """Create base DataFrame with core data."""
    base_data = {**_generate_trace_identifiers(num_logs), **_generate_app_service_data(app_choices, apps)}
    base_data.update({**_generate_model_data(model_choices, models), 'user_prompt': prompts})
    return pd.DataFrame(base_data)

def _add_response_data(df: pd.DataFrame, responses: list, num_logs: int) -> pd.DataFrame:
    """Add response and timing data to DataFrame."""
    df['assistant_response'] = responses
    df['prompt_tokens'] = [len(p.split()) * 2 for p in df['user_prompt']]
    df['completion_tokens'] = [len(r.split()) * 2 for r in responses]
    df['total_e2e_ms'] = np.random.randint(200, 2000, size=num_logs)
    df['ttft_ms'] = np.random.randint(150, 800, size=num_logs)
    return df

def _add_user_data(df: pd.DataFrame, num_logs: int) -> pd.DataFrame:
    """Add user and organization data to DataFrame."""
    df['user_id'] = [str(uuid.uuid4()) for _ in range(num_logs)]
    df['organization_id'] = [f"org_{hashlib.sha256(fake.company().encode()).hexdigest()[:12]}" for _ in range(num_logs)]
    return df

def _calculate_token_costs(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate token costs and totals for DataFrame."""
    df['total_tokens'] = df['prompt_tokens'] + df['completion_tokens']
    df['prompt_cost'] = (df['prompt_tokens'] / 1_000_000) * df['model_pricing'].apply(lambda x: x[0])
    df['completion_cost'] = (df['completion_tokens'] / 1_000_000) * df['model_pricing'].apply(lambda x: x[1])
    df['total_cost'] = df['prompt_cost'] + df['completion_cost']
    return df

def generate_data_chunk(args) -> pd.DataFrame:
    """Generates a chunk of data as a Pandas DataFrame. Designed to be run in parallel."""
    num_logs, config, content_corpus = args
    app_choices, model_choices, apps, models = _generate_app_model_choices(num_logs, config)
    prompts, responses = _generate_content_pairs(num_logs, config, content_corpus)
    return _build_complete_dataframe(num_logs, app_choices, model_choices, apps, models, prompts, responses)

def _build_complete_dataframe(num_logs: int, app_choices: np.ndarray, model_choices: np.ndarray, 
                             apps: list, models: list, prompts: list, responses: list) -> pd.DataFrame:
    """Build complete DataFrame with all data elements."""
    df = _create_base_dataframe(num_logs, app_choices, model_choices, apps, models, prompts, responses)
    df = _add_response_data(df, responses, num_logs)
    df = _add_user_data(df, num_logs)
    return _calculate_token_costs(df)

from .log_formatter import format_log_entry, _generate_contextual_response
from .multi_turn_generator import generate_multi_turn_tool_trace





# --- 4. ORCHESTRATION ---
async def main(args):
    """Main function to generate synthetic logs. Can be called from other modules."""
    start_time = time.time()
    config, content_corpus = await _setup_generation_environment(args)
    all_logs = await _generate_all_logs(args, config, content_corpus)
    await _finalize_generation(args, all_logs, start_time)
    return all_logs

async def _setup_generation_environment(args):
    """Setup configuration and content corpus for generation"""
    console.print("[bold cyan]Starting High-Performance Synthetic Log Generation...[/bold cyan]")
    config_path = args.config if hasattr(args, 'config') else "config.yaml"
    config = get_config(config_path)
    content_corpus = await _load_content_corpus(args)
    return config, content_corpus

async def _load_content_corpus(args):
    """Load content corpus from args or ClickHouse"""
    if hasattr(args, 'corpus') and args.corpus:
        console.print("[green]Using content corpus provided in arguments.[/green]")
        return args.corpus
    else:
        return await load_content_corpus_from_clickhouse()

async def _generate_all_logs(args, config, content_corpus):
    """Generate both simple and multi-turn logs"""
    num_simple_logs, num_multi_turn = _calculate_trace_distribution(args, config)
    simple_logs = await _generate_simple_logs_if_needed(args, config, content_corpus, num_simple_logs)
    multi_turn_logs = await _generate_multi_turn_logs_if_needed(config, content_corpus, num_multi_turn)
    return _combine_all_logs(simple_logs, multi_turn_logs)

def _combine_all_logs(simple_logs: list, multi_turn_logs: list) -> list:
    """Combine simple and multi-turn logs into single list."""
    all_logs = []
    all_logs.extend(simple_logs)
    all_logs.extend(multi_turn_logs)
    return all_logs

async def _generate_simple_logs_if_needed(args, config, content_corpus, num_simple_logs):
    """Generate simple logs if needed."""
    if num_simple_logs > 0:
        return await _generate_simple_logs(args, config, content_corpus, num_simple_logs)
    return []

async def _generate_multi_turn_logs_if_needed(config, content_corpus, num_multi_turn):
    """Generate multi-turn logs if needed."""
    if num_multi_turn > 0:
        return await _generate_multi_turn_logs(config, content_corpus, num_multi_turn)
    return []

def _calculate_trace_distribution(args, config):
    """Calculate number of each trace type to generate"""
    total_traces = args.num_traces
    trace_dist = config['generation_settings']['trace_distribution']
    num_multi_turn = round(total_traces * trace_dist.get('multi_turn_tool_use', 0.0))
    num_simple_logs = total_traces - num_multi_turn
    console.print(f"Planning to generate [yellow]{num_simple_logs}[/yellow] simple logs and [yellow]{num_multi_turn}[/yellow] multi-turn traces.")
    return num_simple_logs, num_multi_turn

async def _generate_simple_logs(args, config, content_corpus, num_simple_logs):
    """Generate simple logs in parallel"""
    max_cores = args.max_cores if hasattr(args, 'max_cores') else cpu_count()
    num_processes = min(cpu_count(), max_cores)
    chunks = _calculate_worker_chunks(num_simple_logs, num_processes)
    
    results = _execute_parallel_generation(chunks, config, content_corpus, num_processes)
    return _format_generation_results(results)

def _execute_parallel_generation(chunks, config, content_corpus, num_processes):
    """Execute parallel data generation using multiprocessing."""
    console.print(f"Using [yellow]{num_processes}[/yellow] cores to generate simple logs...")
    with Pool(processes=num_processes) as pool:
        worker_args = [(chunk, config, content_corpus) for chunk in chunks]
        return pool.map(generate_data_chunk, worker_args)

def _format_generation_results(results):
    """Format parallel generation results into log entries."""
    combined_df = pd.concat(results, ignore_index=True)
    return [format_log_entry(row) for _, row in combined_df.iterrows()]

def _calculate_worker_chunks(num_simple_logs, num_processes):
    """Calculate chunks for parallel processing"""
    chunk_size = num_simple_logs // num_processes
    chunks = [chunk_size] * num_processes
    remainder = num_simple_logs % num_processes
    if remainder:
        chunks.append(remainder)
    return chunks

async def _generate_multi_turn_logs(config, content_corpus, num_multi_turn):
    """Generate multi-turn traces sequentially"""
    console.print(f"Generating [yellow]{num_multi_turn}[/yellow] multi-turn traces...")
    all_multi_turn_logs = []
    return _generate_traces_with_progress(config, content_corpus, num_multi_turn, all_multi_turn_logs)

def _generate_traces_with_progress(config, content_corpus, num_multi_turn, all_multi_turn_logs):
    """Generate traces with progress tracking."""
    with Progress() as progress:
        task = progress.add_task("[magenta]Generating complex traces...", total=num_multi_turn)
        for _ in range(num_multi_turn):
            all_multi_turn_logs.extend(generate_multi_turn_tool_trace(config, content_corpus))
            progress.update(task, advance=1)
    return all_multi_turn_logs

async def _finalize_generation(args, all_logs, start_time):
    """Finalize generation with shuffling, stats, and optional output"""
    console.print("Shuffling all generated logs for realism...")
    random.shuffle(all_logs)
    _print_generation_stats(all_logs, start_time)
    await _save_output_if_standalone(args, all_logs)

def _print_generation_stats(all_logs, start_time):
    """Print generation performance statistics"""
    duration = time.time() - start_time
    logs_per_second = len(all_logs) / duration if duration > 0 else 0
    console.print(f"[bold green]Successfully generated {len(all_logs)} total log entries.[/bold green]")
    console.print(f"Total time: [yellow]{duration:.2f}s[/yellow]")
    console.print(f"Performance: [bold yellow]{logs_per_second:.2f} logs/second[/bold yellow]")

async def _save_output_if_standalone(args, all_logs):
    """Save output to file if running as standalone script"""
    is_standalone = hasattr(args, 'output_file')
    if is_standalone:
        console.print(f"Saving output to [cyan]{args.output_file}[/cyan]...")
        with open(args.output_file, 'w') as f:
            json.dump(all_logs, f, indent=2)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="High-Performance Synthetic Log Generator")
    parser.add_argument("--config", default="config.yaml", help="Path to the configuration YAML file.")
    parser.add_argument("--num-traces", type=int, default=1000, help="Total number of traces to generate.")
    parser.add_argument("--output-file", default="generated_logs.json", help="Path to the output JSON file.")
    parser.add_argument("--max-cores", type=int, default=cpu_count(), help="Maximum number of CPU cores to use.")
    parser.add_argument("--corpus-file", default="content_corpus.json", help="Path to the AI-generated content corpus file.")

    
    # In some environments, sys.argv might be empty.
    if len(sys.argv) == 1:
        args = parser.parse_args(['--num-traces', '1000'])
    else:
        args = parser.parse_args()

    asyncio.run(main(args))