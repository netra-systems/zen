# AI-Powered Content Corpus Generator (V2 with Structured Generation)
#
# This script uses a powerful Large Language Model (Gemini) to generate a rich corpus
# of realistic prompts and responses. It leverages structured generation by providing
# Pydantic models as a scope, ensuring the LLM's output is always in the correct format.
#
# SETUP:
# 1. Install necessary libraries:
#    pip install google-generativeai rich pydantic clickhouse-connect
#
# 2. Set your Gemini API Key:
#    export GEMINI_API_KEY="YOUR_API_KEY"
#
# USAGE:
#    python -m app.data.synthetic.content_generator --samples-per-type 10

import os
import json
import time
import argparse
import sys
import uuid
from multiprocessing import Pool, cpu_count
from functools import partial
from typing import List, Tuple

from pydantic import BaseModel, Field
from rich.console import Console
from rich.progress import Progress
from dotenv import load_dotenv

from app.llm.llm_manager import LLMManager, LLMConfig
from app.db.clickhouse import get_clickhouse_client
from app.db.models_clickhouse import ContentCorpus, get_content_corpus_schema, CONTENT_CORPUS_TABLE_NAME
from app.data.content_corpus import DEFAULT_CONTENT_CORPUS

load_dotenv()

console = Console()

# --- Gemini Integration ---
try:
    import google.generativeai as genai
    from google.generativeai.types import GenerationConfig
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
    else:
        console.print("[red]GEMINI_API_KEY environment variable not set.[/red]")
        genai = None
except ImportError:
    console.print("[red]google.generativeai not installed. Please run `pip install google-generativeai`[/red]")
    genai = None

# --- 1. Structured Output Schemas (Pydantic) ---

class SingleTurn(BaseModel):
    """Schema for a single user prompt and assistant response."""
    user_prompt: str = Field(..., description="A realistic user prompt.")
    assistant_response: str = Field(..., description="A plausible response from an AI assistant.")

class Turn(BaseModel):
    """Schema for a single turn in a conversation."""
    user_prompt: str = Field(..., description="A realistic user prompt.")
    assistant_response: str = Field(..., description="A plausible response from an AI assistant.")

class MultiTurnConversation(BaseModel):
    """Schema for a multi-turn conversation, represented as a list of turns."""
    conversation: List[Turn] = Field(..., description="A list of user and assistant turns.")

# --- 2. Content Generation Prompts ---
META_PROMPTS = {
    "simple_chat": ("Generate a realistic user question and a corresponding helpful assistant response on technology or AI.", SingleTurn),
    "rag_pipeline": ("Generate a user question, a context paragraph with the answer, and an assistant response based only on the context.", SingleTurn),
    "tool_use": ("Generate a user request requiring a fictional API call and an assistant response confirming the parameters.", SingleTurn),
    "failed_request": ("Generate a user prompt that is impossible or unsafe to fulfill, and a polite refusal from the assistant.", SingleTurn),
    "multi_turn_tool_use": ("Generate a realistic, 3-5 turn conversation where an assistant uses tools to help a user plan a trip.", MultiTurnConversation)
}

# --- 3. Generation and Ingestion Logic ---

def generate_content_sample(workload_type: str, model, generation_config) -> dict:
    """Generates a single, schema-guaranteed sample for a given workload type using the LLM."""
    if not genai:
        return None

    instruction, schema = META_PROMPTS[workload_type]
    
    prompt = f"""
    You are a synthetic data generator. Your task is to create a realistic data sample for the workload type: '{workload_type}'.
    Instructions: {instruction}
    Now, call the provided tool with the generated content.
    """
    
    try:
        response = model.generate_content(prompt, generation_config=generation_config, tools=[schema])
        
        tool_call = response.candidates[0].content.parts[0].function_call
        args = tool_call.args

        if not args:
            return None

        if workload_type == 'multi_turn_tool_use':
            convo_tuples = [(turn['user_prompt'], turn.get('assistant_response', '')) for turn in args.get('conversation', [])]
            if not convo_tuples:
                return None
            # For multi-turn, we'll serialize the conversation into a single prompt/response pair for simplicity
            # This could be handled differently depending on the desired table structure
            return {"type": workload_type, "data": (json.dumps(convo_tuples), "Conversation")}
        else:
            user_prompt = args.get('user_prompt')
            if not user_prompt:
                return None
            return {"type": workload_type, "data": (user_prompt, args.get('assistant_response', '')) }
            
    except (ValueError, IndexError, AttributeError, KeyError) as e:
        return None

def insert_into_clickhouse(client, table_name: str, data: List[ContentCorpus]):
    """Inserts a list of ContentCorpus objects into the specified ClickHouse table."""
    if not data:
        return
    try:
        client.insert(table_name, [d.dict() for d in data])
    except Exception as e:
        console.print(f"[red]Error inserting data into ClickHouse: {e}[/red]")

def generate_and_ingest_for_type(task_args, model, generation_config, clickhouse_config):
    """Worker function to generate and ingest multiple samples for a single workload type."""
    workload_type, num_samples = task_args
    samples_to_insert = []
    
    # Each process needs its own ClickHouse client
    with get_clickhouse_client() as client:
        for _ in range(num_samples):
            sample = generate_content_sample(workload_type, model, generation_config)
            if sample:
                prompt, response = sample['data']
                corpus_item = ContentCorpus(
                    record_id=uuid.uuid4(),
                    workload_type=sample['type'],
                    prompt=prompt,
                    response=response
                )
                samples_to_insert.append(corpus_item)
        
        if samples_to_insert:
            insert_into_clickhouse(client, CONTENT_CORPUS_TABLE_NAME, samples_to_insert)
            
    return len(samples_to_insert)

async def get_all_existing_content_corpuses():
    """
    Retrieves all content corpuses from ClickHouse.
    If the query fails or returns no results, it populates the DB with the default corpus.
    """
    corpuses = {}
    try:
        async with get_clickhouse_client() as client:
            if not await client.table_exists(CONTENT_CORPUS_TABLE_NAME):
                console.print(f"[yellow]Table '{CONTENT_CORPUS_TABLE_NAME}' not found. Populating with default data.[/yellow]")
                await populate_with_default_data(client)

            result = await client.query(f"SELECT workload_type, prompt, response FROM {CONTENT_CORPUS_TABLE_NAME}")
            
            if not result.result_rows:
                console.print("[yellow]No content found in ClickHouse. Populating with default data.[/yellow]")
                await populate_with_default_data(client)
                result = await client.query(f"SELECT workload_type, prompt, response FROM {CONTENT_CORPUS_TABLE_NAME}")

            for row in result.result_rows:
                workload_type, prompt, response = row
                if workload_type not in corpuses:
                    corpuses[workload_type] = []
                corpuses[workload_type].append((prompt, response))

    except Exception as e:
        console.print(f"[red]Failed to fetch content from ClickHouse: {e}. Returning default corpus.[/red]")
        return DEFAULT_CONTENT_CORPUS
        
    return corpuses

async def populate_with_default_data(client):
    """Populates the ClickHouse database with the default content corpus."""
    await client.command(get_content_corpus_schema(CONTENT_CORPUS_TABLE_NAME))
    
    records_to_insert = []
    for workload_type, items in DEFAULT_CONTENT_CORPUS.items():
        for item in items:
            # Handle both single-turn (tuple) and multi-turn (list of tuples)
            if isinstance(item, list):
                prompt = json.dumps(item)
                response = "Conversation"
            else:
                prompt, response = item
                
            records_to_insert.append(ContentCorpus(
                record_id=uuid.uuid4(),
                workload_type=workload_type,
                prompt=prompt,
                response=response
            ).dict())

    if records_to_insert:
        await client.insert(CONTENT_CORPUS_TABLE_NAME, records_to_insert)
    console.print(f"Successfully inserted {len(records_to_insert)} default records into '{CONTENT_CORPUS_TABLE_NAME}'.")


# --- 4. Orchestration ---
def main(args):
    llm_manager = LLMManager({
        "default": LLMConfig(
            provider="google",
            model_name="gemini-2.5-flash-lite",
        )
    })
    # This script doesn't use the LLM manager, but it's here for consistency
    # llm = llm_manager.get_llm("default")

    console.print("[bold cyan]Starting AI-Powered Content Corpus Generation (Structured)...[/bold cyan]")
    start_time = time.time()

    generation_params = {
        "temperature": args.temperature,
        "top_p": args.top_p,
        "top_k": args.top_k
    }

    model = genai.GenerativeModel(settings.corpus_generation_model)
    generation_config = GenerationConfig(**generation_params)

    console.print(f"Generation Config: [yellow]temp={args.temperature}, top_p={args.top_p}, top_k={args.top_k}[/yellow]")

    workload_types = list(META_PROMPTS.keys())
    num_samples_per_type = args.samples_per_type
    num_processes = min(cpu_count(), args.max_cores)

    console.print(f"Using [yellow]{num_processes}[/yellow] cores to generate [yellow]{num_samples_per_type * len(workload_types)}[/yellow] total samples.")

    # Get ClickHouse config for worker processes
    from app.config import settings
    if settings.environment == "development":
        clickhouse_config = settings.clickhouse_https_dev.dict()
    else:
        clickhouse_config = settings.clickhouse_https.dict()


    worker_func = partial(generate_and_ingest_for_type, model=model, generation_config=generation_config, clickhouse_config=clickhouse_config)
    tasks_for_pool = [(w_type, num_samples_per_type) for w_type in workload_types]

    total_generated = 0
    with Pool(processes=num_processes) as pool:
        with Progress() as progress:
            task = progress.add_task("[green]Generating and ingesting content...", total=len(tasks_for_pool))
            for num_generated in pool.imap_unordered(worker_func, tasks_for_pool):
                total_generated += num_generated
                progress.update(task, advance=1)

    end_time = time.time()
    duration = end_time - start_time

    console.print(f"\n[bold green]Successfully generated and ingested content![/bold green]")
    console.print(f"  - Total Samples: {total_generated}")
    console.print(f"  - Table: [cyan]{CONTENT_CORPUS_TABLE_NAME}[/cyan]")
    console.print(f"Total time: [yellow]{duration:.2f}s[/yellow]")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI-Powered Content Corpus Generator (Structured)")
    parser.add_argument("--samples-per-type", type=int, default=10, help="Number of samples to generate for each workload type.")
    parser.add_argument("--max-cores", type=int, default=cpu_count(), help="Maximum number of CPU cores to use.")
    parser.add_argument("--temperature", type=float, default=0.8, help="Controls the randomness of the output.")
    parser.add_argument("--top-p", type=float, default=None, help="Nucleus sampling probability.")
    parser.add_argument("--top-k", type=int, default=None, help="Top-k sampling control.")

    if len(sys.argv) == 1:
        # Default run for convenience
        args = parser.parse_args(['--samples-per-type', '2'])
    else:
        args = parser.parse_args()

    main(args)
