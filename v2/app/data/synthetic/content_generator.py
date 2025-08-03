# AI-Powered Content Corpus Generator (V2 with Structured Generation)
#
# This script uses a powerful Large Language Model (Gemini) to generate a rich corpus
# of realistic prompts and responses. It leverages structured generation by providing
# Pydantic models as a schema, ensuring the LLM's output is always in the correct format.
#
# SETUP:
# 1. Install necessary libraries:
#    pip install google-generativeai rich pydantic
#
# 2. Set your Gemini API Key:
#    export GEMINI_API_KEY="YOUR_API_KEY"
#
# USAGE:
#    python -m app.data.synthetic.content_generator --samples-per-type 10 --output-file content_corpus.json

import os
import json
import time
import argparse
import sys
from multiprocessing import Pool, cpu_count
from functools import partial
from typing import List, Tuple

from pydantic import BaseModel, Field
from rich.console import Console
from rich.progress import Progress
from dotenv import load_dotenv

from ...config import settings

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

# --- 3. Generation Logic ---

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
        # Use the schema as a "tool" to enforce structured output
        response = model.generate_content(prompt, generation_config=generation_config, tools=[schema])
        
        # Extract the structured data from the tool call
        tool_call = response.candidates[0].content.parts[0].function_call
        args = tool_call.args

        if not args:
            # console.print(f"[yellow]Warning: Model returned empty arguments for '{workload_type}'.[/yellow]")
            return None

        if workload_type == 'multi_turn_tool_use':
            # Convert the list of dicts back to a list of tuples for the corpus
            convo_tuples = [(turn['user_prompt'], turn.get('assistant_response', '')) for turn in args.get('conversation', [])]
            if not convo_tuples:
                return None
            return {"type": workload_type, "data": convo_tuples}
        else:
            user_prompt = args.get('user_prompt')
            if not user_prompt:
                return None
            return {"type": workload_type, "data": (user_prompt, args.get('assistant_response', '')) }
            
    except (ValueError, IndexError, AttributeError, KeyError) as e:
        # This might happen if the model fails to call the tool correctly, though it's less likely with this method.
        # console.print(f"[yellow]Warning: Failed to generate content for '{workload_type}': {e}[/yellow]")
        return None

def generate_for_type(task_args, model, generation_config):
    """Worker function to generate multiple samples for a single workload type."""
    workload_type, num_samples = task_args
    samples = []
    for _ in range(num_samples):
        sample = generate_content_sample(workload_type, model, generation_config)
        if sample:
            samples.append(sample)
    return [s for s in samples if s]

# --- 4. Orchestration ---
def main(args):
    if not genai or not GEMINI_API_KEY:
        console.print("[bold red]Cannot proceed: Gemini API is not configured.[/bold red]")
        sys.exit(1)

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

    corpus = {key: [] for key in workload_types}

    worker_func = partial(generate_for_type, model=model, generation_config=generation_config)
    tasks_for_pool = [(w_type, num_samples_per_type) for w_type in workload_types]

    with Pool(processes=num_processes) as pool:
        with Progress() as progress:
            task = progress.add_task("[green]Generating content...", total=len(tasks_for_pool))
            for result in pool.imap_unordered(worker_func, tasks_for_pool):
                if result:
                    for item in result:
                        if item and item.get('type') in corpus:
                            corpus[item['type']].append(item['data'])
                progress.update(task, advance=1)

    # Save to file
    with open(args.output_file, 'w') as f:
        json.dump(corpus, f, indent=2)

    end_time = time.time()
    duration = end_time - start_time

    console.print(f"\n[bold green]Successfully generated content corpus![/bold green]")
    for w_type, samples in corpus.items():
        console.print(f"  - [cyan]{w_type}[/cyan]: {len(samples)} samples")
    console.print(f"Output saved to [cyan]{args.output_file}[/cyan]")
    console.print(f"Total time: [yellow]{duration:.2f}s[/yellow]")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI-Powered Content Corpus Generator (Structured)")
    parser.add_argument("--samples-per-type", type=int, default=10, help="Number of samples to generate for each workload type.")
    parser.add_argument("--output-file", default="content_corpus.json", help="Path to the output JSON file.")
    parser.add_argument("--max-cores", type=int, default=cpu_count(), help="Maximum number of CPU cores to use.")
    parser.add_argument("--temperature", type=float, default=0.8, help="Controls the randomness of the output.")
    parser.add_argument("--top-p", type=float, default=None, help="Nucleus sampling probability.")
    parser.add_argument("--top-k", type=int, default=None, help="Top-k sampling control.")

    if len(sys.argv) == 1:
        args = parser.parse_args(['--samples-per-type', '10'])
    else:
        args = parser.parse_args()

    main(args)