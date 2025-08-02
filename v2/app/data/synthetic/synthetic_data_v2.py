# A High-Performance Synthetic Data Generation System for the Unified LLM Operations Schema v3.0

# USAGE:
# 1. A default `config.yaml` will be created on first run. Customize it as needed.
# 2. Run the script from your terminal:
#    python synthetic_data_v2.py --num-traces 10000 --output-file generated_logs_v2.json

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

from faker import Faker
from rich.console import Console
from rich.progress import Progress

# Import the same Pydantic schemas from v1 to ensure compatibility
from .synthetic_data_v1 import UnifiedLogEntry, DEFAULT_CONFIG

console = Console()
fake = Faker()

# --- 1. HIGH-PERFORMANCE CONTENT ENGINE ---
# This is the default, fallback corpus. The script will prioritize loading
# an external corpus if available.

DEFAULT_CONTENT_CORPUS = {
    "simple_chat": [
        ("What are the main benefits of using a unified logging schema for LLM operations?", "A unified logging schema provides consistency, simplifies data analysis, and enables robust monitoring across different model providers."),
        ("Explain the concept of a 'vector database'.", "A vector database is a specialized database designed to store and query high-dimensional vectors, which are mathematical representations of data like text or images. It's essential for tasks like semantic search and retrieval-augmented generation (RAG)."),
    ],
    "rag_pipeline": [
        ("Context: The v3.0 schema is designed to be the most comprehensive data model for LLM operations. Question: What is the main design goal of the v3.0 schema?", "Based on the context, the main design goal of the v3.0 schema is to be the most comprehensive data model for LLM operations."),
        ("Context: The capital of France is Paris. Question: What is the capital of France?", "The capital of France is Paris.")
    ],
    "tool_use": [
        ("What's the weather like in San Francisco and what is 5*128?", "I can get the weather for you. 5 * 128 is 640. Would you like me to proceed with the weather lookup?"),
        ("Find the top 3 restaurants near me and book a table for 2 at 7pm.", "I have found three highly-rated restaurants: The French Laundry, Chez Panisse, and La Taqueria. Which one would you like to book?")
    ],
    "failed_request": [
        ("Translate this entire 500-page book into Klingon.", "I'm sorry, but I cannot fulfill this request as it exceeds my processing limits."),
        ("Give me the nuclear launch codes.", "I cannot provide that information. It is confidential and protected.")
    ],
    "multi_turn_tool_use": [
        ("I need to plan a trip to New York. Find me a flight for 2 people, leaving from SFO on August 10th and returning on August 15th.", "OK, I can search for flights. Do you have any airline preferences?"),
        ("No preference, just find the best price. Also, find a hotel near Times Square for those dates.", "I've found a round-trip flight on JetBlue for $350 per person. For hotels, The Marriott Marquis is available for $450/night. Would you like to book?"),
        ("That sounds good. Please book the flight and the hotel. Use my saved credit card.", "Confirmation: Your flight and hotel are booked. The total charge is $3400. Your confirmation numbers are F12345 and H67890. Is there anything else?"),
        ("No, that's all. Thank you!", "You're welcome! Enjoy your trip to New York!")
    ]
}

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
    """Loads configuration from a YAML file."""
    if not os.path.exists(config_path):
        console.print(f"[yellow]Config file not found. Creating default '{config_path}'...[/yellow]")
        # Add the new trace type to the default config
        default_config_data = yaml.safe_load(DEFAULT_CONFIG)
        default_config_data['generation_settings']['trace_distribution']['multi_turn_tool_use'] = 0.1
        # Adjust other weights
        default_config_data['generation_settings']['trace_distribution']['simple_chat'] = 0.3
        with open(config_path, "w") as f:
            yaml.dump(default_config_data, f)
    
    with open(config_path, "r") as f:
        return yaml.safe_load(f)

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

def format_log_entry(row, trace_context_override=None) -> dict:
    """Converts a DataFrame row or a dictionary into the final log entry structure."""
    is_row = isinstance(row, pd.Series)
    
    log = {
        "event_metadata": {
            "log_schema_version": "3.0.0",
            "event_id": str(uuid.uuid4()),
            "timestamp_utc": int(time.time() * 1000),
            "ingestion_source": "synthetic_generator_v2"
        },
        "trace_context": trace_context_override or {
            "trace_id": row['trace_id'],
            "span_id": row['span_id'],
            "span_name": "ChatCompletion",
            "span_kind": "llm"
        },
        "identity_context": {
            "user_id": row['user_id'],
            "organization_id": row['organization_id']
        },
        "application_context": {
            "app_name": row['app_name'],
            "service_name": row['service_name'],
            "sdk_version": "python-sdk-2.0.0",
            "environment": "production"
        },
        "request": {
            "model": {
                "provider": row['model_provider'],
                "name": row['model_name'],
                "family": ""
            },
            "prompt": {
                "messages": [{"role": "user", "content": row['user_prompt']}]
            },
            "generation_config": {"max_tokens_to_sample": 2048, "is_streaming": False}
        },
        "response": {
            "completion": {
                "choices": [{
                    "index": 0,
                    "finish_reason": "stop_sequence",
                    "message": {"role": "assistant", "content": row['assistant_response']}
                }]
            },
            "usage": {
                "prompt_tokens": row['prompt_tokens'],
                "completion_tokens": row['completion_tokens'],
                "total_tokens": row['total_tokens']
            },
            "system": {"provider_request_id": f"req_{str(uuid.uuid4())}"}
        },
        "performance": {
            "latency_ms": {
                "total_e2e": row['total_e2e_ms'],
                "time_to_first_token": row['ttft_ms']
            }
        },
        "finops": {
            "cost": {
                "total_cost_usd": row['total_cost'],
                "prompt_cost_usd": row['prompt_cost'],
                "completion_cost_usd": row['completion_cost']
            },
            "pricing_info": {
                "provider_rate_id": "rate_abc123",
                "prompt_token_rate_usd_per_million": row['model_pricing'][0] if is_row else row['model_pricing'][0],
                "completion_token_rate_usd_per_million": row['model_pricing'][1] if is_row else row['model_pricing'][1]
            }
        }
    }
    # Modify prompt for multi-turn
    if trace_context_override and trace_context_override.get("parent_span_id"):
        log["request"]["prompt"]["messages"] = [
            {"role": "user", "content": row["user_prompt"]},
            {"role": "assistant", "content": "Previous turn response..."} # Placeholder
        ]
    return log

def generate_multi_turn_tool_trace(config, content_corpus) -> list:
    """Generates a single, complex multi-turn trace with a shared trace_id."""
    trace_id = str(uuid.uuid4())
    conversation = content_corpus.get('multi_turn_tool_use')
    if not conversation:
        return []
    
    trace_logs = []
    parent_span_id = None
    
    # Pick a random model and app for the whole trace
    app_config = random.choice(config['realism']['applications'])
    model_config = random.choice(config['realism']['models'])

    for i, (prompt, response) in enumerate(random.choice(conversation)):
        span_id = str(uuid.uuid4())
        
        # Create a dictionary with the same structure as a DataFrame row for format_log_entry
        log_data = {
            'user_id': str(uuid.uuid4()),
            'organization_id': f"org_{hashlib.sha256(fake.company().encode()).hexdigest()[:12]}",
            'app_name': app_config['app_name'],
            'service_name': random.choice(app_config['services']),
            'model_provider': model_config['provider'],
            'model_name': model_config['name'],
            'model_pricing': model_config['pricing'],
            'user_prompt': prompt,
            'assistant_response': response,
            'prompt_tokens': len(prompt.split()) * 2,
            'completion_tokens': len(response.split()) * 2,
            'total_e2e_ms': random.randint(300, 2500),
            'ttft_ms': random.randint(150, 900),
        }
        log_data['total_tokens'] = log_data['prompt_tokens'] + log_data['completion_tokens']
        log_data['prompt_cost'] = (log_data['prompt_tokens'] / 1_000_000) * log_data['model_pricing'][0]
        log_data['completion_cost'] = (log_data['completion_tokens'] / 1_000_000) * log_data['model_pricing'][1]
        log_data['total_cost'] = log_data['prompt_cost'] + log_data['completion_cost']

        trace_context = {
            "trace_id": trace_id,
            "span_id": span_id,
            "parent_span_id": parent_span_id,
            "span_name": f"AgentTurn-{i+1}",
            "span_kind": "tool" if i % 2 != 0 else "llm" # Alternate between tool and llm
        }
        
        formatted_log = format_log_entry(log_data, trace_context_override=trace_context)
        trace_logs.append(formatted_log)
        parent_span_id = span_id # The next span will be a child of this one
        
    return trace_logs

# --- 4. ORCHESTRATION ---
def main(args):
    console.print("[bold cyan]Starting High-Performance Synthetic Log Generation (v2)...[/bold cyan]")
    start_time = time.time()

    config = get_config(args.config)
    content_corpus = load_content_corpus(args.corpus_file)
    total_traces = args.num_traces

    # --- Calculate number of each trace type ---
    trace_dist = config['generation_settings']['trace_distribution']
    num_multi_turn = int(total_traces * trace_dist.get('multi_turn_tool_use', 0.0))
    num_simple_logs = total_traces - num_multi_turn

    console.print(f"Planning to generate [yellow]{num_simple_logs}[/yellow] simple logs and [yellow]{num_multi_turn}[/yellow] multi-turn traces.")

    # --- Generate Simple Logs in Parallel ---
    all_logs = []
    if num_simple_logs > 0:
        num_processes = min(cpu_count(), args.max_cores)
        chunk_size = num_simple_logs // num_processes
        chunks = [chunk_size] * num_processes
        remainder = num_simple_logs % num_processes
        if remainder: chunks.append(remainder)

        console.print(f"Using [yellow]{num_processes}[/yellow] cores to generate simple logs...")
        with Pool(processes=num_processes) as pool:
            worker_args = [(chunk, config, content_corpus) for chunk in chunks]
            results = pool.map(generate_data_chunk, worker_args)
        
        combined_df = pd.concat(results, ignore_index=True)
        all_logs.extend([format_log_entry(row) for _, row in combined_df.iterrows()])

    # --- Generate Complex Traces Sequentially ---
    if num_multi_turn > 0:
        console.print(f"Generating [yellow]{num_multi_turn}[/yellow] multi-turn traces...")
        with Progress() as progress:
            task = progress.add_task("[magenta]Generating complex traces...", total=num_multi_turn)
            for _ in range(num_multi_turn):
                all_logs.extend(generate_multi_turn_tool_trace(config, content_corpus))
                progress.update(task, advance=1)

    # --- Finalize and Save ---
    console.print("Shuffling all generated logs for realism...")
    random.shuffle(all_logs)

    console.print(f"Saving output to [cyan]{args.output_file}[/cyan]...")
    with open(args.output_file, 'w') as f:
        json.dump(all_logs, f, indent=2)

    end_time = time.time()
    duration = end_time - start_time
    logs_per_second = len(all_logs) / duration if duration > 0 else 0

    console.print(f"
[bold green]Successfully generated {len(all_logs)} total log entries.[/bold green]")
    console.print(f"Total time: [yellow]{duration:.2f}s[/yellow]")
    console.print(f"Performance: [bold yellow]{logs_per_second:.2f} logs/second[/bold yellow]")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="High-Performance Synthetic Log Generator v2")
    parser.add_argument("--config", default="config.yaml", help="Path to the configuration YAML file.")
    parser.add_argument("--num-traces", type=int, default=1000, help="Total number of traces to generate.")
    parser.add_argument("--output-file", default="generated_logs_v2.json", help="Path to the output JSON file.")
    parser.add_argument("--max-cores", type=int, default=cpu_count(), help="Maximum number of CPU cores to use.")
    parser.add_argument("--corpus-file", default="content_corpus.json", help="Path to the AI-generated content corpus file.")

    
    # In some environments, sys.argv might be empty.
    if len(sys.argv) == 1:
        args = parser.parse_args(['--num-traces', '1000'])
    else:
        args = parser.parse_args()

    main(args)


def load_content_corpus(corpus_path: str) -> dict:
    """Loads the content corpus from a JSON file, falling back to the default."""
    if os.path.exists(corpus_path):
        try:
            with open(corpus_path, 'r') as f:
                console.print(f"[green]Loading content from external corpus: [cyan]{corpus_path}[/cyan][/green]")
                return json.load(f)
        except json.JSONDecodeError:
            console.print(f"[red]Error: Could not parse '{corpus_path}'. Falling back to default corpus.[/red]")
            return DEFAULT_CONTENT_CORPUS
    else:
        console.print("[yellow]Warning: External content corpus not found. Using default internal corpus.[/yellow]")
        return DEFAULT_CONTENT_CORPUS

# --- 2. CONFIGURATION MANAGEMENT (Identical to v1) ---
def get_config(config_path="config.yaml"):
    """Loads configuration from a YAML file."""
    if not os.path.exists(config_path):
        console.print(f"[yellow]Config file not found. Creating default '{config_path}'...[/yellow]")
        with open(config_path, "w") as f:
            f.write(DEFAULT_CONFIG)
    
    with open(config_path, "r") as f:
        return yaml.safe_load(f)

# --- 3. VECTORIZED DATA GENERATION ---

def generate_data_chunk(args):
    """Generates a chunk of data as a Pandas DataFrame. Designed to be run in parallel."""
    num_logs, config, content_corpus = args
    
    # --- Applications and Models ---
    apps = config['realism']['applications']
    models = config['realism']['models']
    app_choices = np.random.choice(len(apps), num_logs)
    model_choices = np.random.choice(len(models), num_logs)

    # --- Content ---
    trace_types = list(config['generation_settings']['trace_distribution'].keys())
    weights = list(config['generation_settings']['trace_distribution'].values())
    chosen_trace_types = np.random.choice(trace_types, num_logs, p=weights)
    
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

def format_log_entry(row) -> dict:
    """Converts a DataFrame row into the final, nested UnifiedLogEntry dictionary structure."""
    # This function is the bridge between the flat DataFrame and the nested JSON output.
    # It carefully reconstructs the schema from the generated columns.
    return {
        "event_metadata": {
            "log_schema_version": "3.0.0",
            "event_id": str(uuid.uuid4()),
            "timestamp_utc": int(time.time() * 1000),
            "ingestion_source": "synthetic_generator_v2"
        },
        "trace_context": {
            "trace_id": row['trace_id'],
            "span_id": row['span_id'],
            "span_name": "ChatCompletion",
            "span_kind": "llm"
        },
        "identity_context": {
            "user_id": row['user_id'],
            "organization_id": row['organization_id']
        },
        "application_context": {
            "app_name": row['app_name'],
            "service_name": row['service_name'],
            "sdk_version": "python-sdk-2.0.0",
            "environment": "production"
        },
        "request": {
            "model": {
                "provider": row['model_provider'],
                "name": row['model_name'],
                "family": ""
            },
            "prompt": {
                "messages": [{"role": "user", "content": row['user_prompt']}]
            },
            "generation_config": {"max_tokens_to_sample": 2048, "is_streaming": False}
        },
        "response": {
            "completion": {
                "choices": [{
                    "index": 0,
                    "finish_reason": "stop_sequence",
                    "message": {"role": "assistant", "content": row['assistant_response']}
                }]
            },
            "usage": {
                "prompt_tokens": row['prompt_tokens'],
                "completion_tokens": row['completion_tokens'],
                "total_tokens": row['total_tokens']
            },
            "system": {"provider_request_id": f"req_{str(uuid.uuid4())}"}
        },
        "performance": {
            "latency_ms": {
                "total_e2e": row['total_e2e_ms'],
                "time_to_first_token": row['ttft_ms']
            }
        },
        "finops": {
            "cost": {
                "total_cost_usd": row['total_cost'],
                "prompt_cost_usd": row['prompt_cost'],
                "completion_cost_usd": row['completion_cost']
            },
            "pricing_info": {
                "provider_rate_id": "rate_abc123",
                "prompt_token_rate_usd_per_million": row['model_pricing'][0],
                "completion_token_rate_usd_per_million": row['model_pricing'][1]
            }
        }
    }

# --- 4. ORCHESTRATION --- 
def main(args):
    console.print("[bold cyan]Starting High-Performance Synthetic Log Generation (v2)...[/bold cyan]")
    start_time = time.time()

    config = get_config(args.config)
    content_corpus = load_content_corpus(args.corpus_file)
    num_traces = args.num_traces

    # Determine the number of processes and chunk size
    num_processes = min(cpu_count(), args.max_cores)
    chunk_size = num_traces // num_processes
    chunks = [chunk_size] * num_processes
    remainder = num_traces % num_processes
    if remainder:
        chunks.append(remainder)

    console.print(f"Using [yellow]{num_processes}[/yellow] cores to generate [yellow]{num_traces}[/yellow] logs in [yellow]{len(chunks)}[/yellow] chunks.")

    # Parallel data generation
    with Pool(processes=num_processes) as pool:
        with Progress() as progress:
            task = progress.add_task("[green]Generating data chunks...", total=len(chunks))
            results = []
            # Pass the content corpus to the worker function
            worker_args = [(chunk, config, content_corpus) for chunk in chunks]
            for result in pool.imap_unordered(generate_data_chunk, worker_args):
                results.append(result)
                progress.update(task, advance=1)
    
    # Combine results
    console.print("Combining generated data chunks...")
    combined_df = pd.concat(results, ignore_index=True)

    # Format into final JSON structure
    console.print("Formatting data into final JSON structure...")
    all_traces = [] # In v2, we generate logs, not traces, for performance.
    with Progress() as progress:
        task = progress.add_task("[blue]Formatting logs...", total=len(combined_df))
        # This part is still sequential, but much faster than the original generation
        for _, row in combined_df.iterrows():
            all_traces.append(format_log_entry(row))
            progress.update(task, advance=1)

    # Save to file
    console.print(f"Saving output to [cyan]{args.output_file}[/cyan]...")
    with open(args.output_file, 'w') as f:
        # We dump a list of log entries, not traces, as the primary structure
        json.dump(all_traces, f, indent=2)

    end_time = time.time()
    duration = end_time - start_time
    logs_per_second = num_traces / duration

    console.print(f"\n[bold green]Successfully generated {num_traces} logs.[/bold green]")
    console.print(f"Total time: [yellow]{duration:.2f}s[/yellow]")
    console.print(f"Performance: [bold yellow]{logs_per_second:.2f} logs/second[/bold yellow]")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="High-Performance Synthetic Log Generator v2")
    parser.add_argument("--config", default="config.yaml", help="Path to the configuration YAML file.")
    parser.add_argument("--num-traces", type=int, default=10000, help="Number of log entries to generate.")
    parser.add_argument("--output-file", default="generated_logs_v2.json", help="Path to the output JSON file.")
    parser.add_argument("--max-cores", type=int, default=cpu_count(), help="Maximum number of CPU cores to use.")
    parser.add_argument("--corpus-file", default="content_corpus.json", help="Path to the AI-generated content corpus file.")

    
    # In some environments, sys.argv might be empty.
    if len(sys.argv) == 1:
        args = parser.parse_args(['--num-traces', '10000'])
    else:
        args = parser.parse_args()

    main(args)