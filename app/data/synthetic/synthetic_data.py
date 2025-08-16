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
        async with get_clickhouse_client() as client:
            if not client.ping():
                console.print("[yellow]Warning: ClickHouse connection failed. Falling back to default corpus.[/yellow]")
                return DEFAULT_CONTENT_CORPUS
            
            query = f"SELECT workload_type, prompt, response FROM {CONTENT_CORPUS_TABLE_NAME}"
            query_result = await client.execute_query(query)

            corpus = {}
            for row in query_result:
                workload_type = row['workload_type']
                user_prompt = row['prompt']
                assistant_response = row['response']
                
                if workload_type not in corpus:
                    corpus[workload_type] = []
                corpus[workload_type].append((user_prompt, assistant_response))
            
            if not corpus:
                console.print("[yellow]Warning: Content corpus from ClickHouse is empty. Using default corpus.[/yellow]")
                return DEFAULT_CONTENT_CORPUS
                
            console.print("[green]Successfully loaded content corpus from ClickHouse.[/green]")
            return corpus

    except Exception as e:
        console.print(f"[red]Error connecting to ClickHouse: {e}. Falling back to default corpus.[/red]")
        return DEFAULT_CONTENT_CORPUS


def load_content_corpus(corpus_path: str) -> dict:
    """Loads the content corpus from a JSON file, falling back to the default."""
    if os.path.exists(corpus_path):
        try:
            with open(corpus_path, 'r') as f:
                console.print(f"[green]Loading content from external corpus: [cyan]{corpus_path}[/cyan][/green]")
                return json.load(f)
        except json.JSONDecodeError:
            console.print(f"[red]Error: Could not parse '{corpus_path}'. Falling back to default corpus.")
            return DEFAULT_CONTENT_CORPUS
    else:
        console.print("[yellow]Warning: External content corpus not found. Using default internal corpus.")
        return DEFAULT_CONTENT_CORPUS

# --- 2. CONFIGURATION MANAGEMENT (Identical to v1) ---
def get_config(config_path="config.yaml"):
    """Loads configuration from a YAML file, updating it if necessary."""
    if not os.path.exists(config_path):
        console.print(f"[yellow]Config file not found. Creating default '{config_path}'...[/yellow]")
        with open(config_path, "w") as f:
            # Load from the v1 default config string which is now updated
            f.write(DEFAULT_CONFIG)
    
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    # --- Auto-update logic for existing configs ---
    generation_settings = config.get('generation_settings', {})
    trace_distribution = generation_settings.get('trace_distribution', {})
    
    if 'multi_turn_tool_use' not in trace_distribution:
        console.print("[yellow]Updating config file to include 'multi_turn_tool_use' trace type...[/yellow]")
        trace_distribution['multi_turn_tool_use'] = 0.1 # Add the new key
        
        # Renormalize other weights
        total_weight = sum(trace_distribution.values())
        renormalization_factor = 0.9 / (total_weight - 0.1)
        
        for key, value in trace_distribution.items():
            if key != 'multi_turn_tool_use':
                trace_distribution[key] = value * renormalization_factor
        
        # Ensure it sums to 1.0
        total_sum = sum(trace_distribution.values())
        if total_sum != 1.0:
            trace_distribution['simple_chat'] += 1.0 - total_sum

        config['generation_settings']['trace_distribution'] = trace_distribution
        with open(config_path, "w") as f:
            yaml.dump(config, f)
        console.print("[green]Config file updated successfully.[/green]")

    return config

# --- 3. VECTORIZED & TRACE DATA GENERATION ---

def generate_data_chunk(args):
    """Generates a chunk of data as a Pandas DataFrame. Designed to be run in parallel."""
    num_logs, config, content_corpus = args
    
    # --- Applications and Models ---
    apps = config['realism']['applications']
    models = config['realism']['models']
    app_choices = np.random.choice(len(apps), num_logs)
    model_choices = np.random.choice(len(models), num_logs)

    # --- Content ---
    # Exclude multi-turn from vectorized generation
    simple_trace_types = [t for t in config['generation_settings']['trace_distribution'].keys() if t != 'multi_turn_tool_use']
    simple_weights = [config['generation_settings']['trace_distribution'][t] for t in simple_trace_types]
    normalized_weights = np.array(simple_weights) / np.sum(simple_weights)
    chosen_trace_types = np.random.choice(simple_trace_types, num_logs, p=normalized_weights)
    
    prompts = []
    responses = []
    for trace_type in chosen_trace_types:
        # Ensure the trace type exists in the corpus, otherwise default
        if trace_type in content_corpus and content_corpus[trace_type]:
            prompt, response = random.choice(content_corpus[trace_type])
        else:
            prompt, response = random.choice(DEFAULT_CONTENT_CORPUS[trace_type])
        prompts.append(prompt)
        responses.append(response)

    # --- Core Data Generation (Vectorized) ---
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
        'organization_id': [f"org_{hashlib.sha256(fake.company().encode()).hexdigest()[:12]}" for _ in range(num_logs)],
    })

    df['total_tokens'] = df['prompt_tokens'] + df['completion_tokens']
    df['prompt_cost'] = (df['prompt_tokens'] / 1_000_000) * df['model_pricing'].apply(lambda x: x[0])
    df['completion_cost'] = (df['completion_tokens'] / 1_000_000) * df['model_pricing'].apply(lambda x: x[1])
    df['total_cost'] = df['prompt_cost'] + df['completion_cost']

    return df

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
    all_logs = []
    num_simple_logs, num_multi_turn = _calculate_trace_distribution(args, config)
    
    if num_simple_logs > 0:
        simple_logs = await _generate_simple_logs(args, config, content_corpus, num_simple_logs)
        all_logs.extend(simple_logs)
    
    if num_multi_turn > 0:
        multi_turn_logs = await _generate_multi_turn_logs(config, content_corpus, num_multi_turn)
        all_logs.extend(multi_turn_logs)
    
    return all_logs

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
    
    console.print(f"Using [yellow]{num_processes}[/yellow] cores to generate simple logs...")
    with Pool(processes=num_processes) as pool:
        worker_args = [(chunk, config, content_corpus) for chunk in chunks]
        results = pool.map(generate_data_chunk, worker_args)
    
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