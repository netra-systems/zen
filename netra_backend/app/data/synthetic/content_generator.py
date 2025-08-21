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

from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.routes.unified_tools.schemas import LLMConfig

console = Console()

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

def _create_generation_prompt(workload_type: str, instruction: str) -> str:
    """Create the prompt for content generation."""
    return f"""    You are a synthetic data generator. Your task is to create a realistic data sample for the workload type: '{workload_type}'.
    Instructions: {instruction}
    Now, call the provided tool with the generated content.
    """

def _invoke_model_with_schema(model, prompt: str, schema):
    """Invoke the model with the given prompt and schema tool."""
    try:
        return model.invoke(prompt, tools=[schema])
    except (ValueError, IndexError, AttributeError, KeyError) as e:
        return None

def _extract_tool_call_args(response) -> dict:
    """Extract arguments from model response tool calls."""
    if not response or not response.tool_calls:
        return None
    tool_call = response.tool_calls[0]
    args = tool_call['args']
    return args if args else None

def _process_multi_turn_response(args: dict, workload_type: str) -> dict:
    """Process multi-turn conversation response format."""
    convo_tuples = [(turn['user_prompt'], turn.get('assistant_response', '')) for turn in args.get('conversation', [])]
    if not convo_tuples:
        return None
    return {"type": workload_type, "data": convo_tuples}

def _process_single_turn_response(args: dict, workload_type: str) -> dict:
    """Process single-turn response format."""
    user_prompt = args.get('user_prompt')
    if not user_prompt:
        return None
    return {"type": workload_type, "data": (user_prompt, args.get('assistant_response', ''))}

def _determine_response_processor(workload_type: str, args: dict) -> dict:
    """Determine which response processor to use based on workload type."""
    if workload_type == 'multi_turn_tool_use':
        return _process_multi_turn_response(args, workload_type)
    return _process_single_turn_response(args, workload_type)

def generate_content_sample(workload_type: str, model) -> dict:
    """Generates a single, schema-guaranteed sample for a given workload type using the LLM."""
    instruction, schema = META_PROMPTS[workload_type]
    prompt = _create_generation_prompt(workload_type, instruction)
    response = _invoke_model_with_schema(model, prompt, schema)
    args = _extract_tool_call_args(response)
    if not args:
        return None
    return _determine_response_processor(workload_type, args)

def generate_for_type(task_args, llm):
    """Worker function to generate multiple samples for a single workload type."""
    workload_type, num_samples = task_args
    samples = []
    for _ in range(num_samples):
        sample = generate_content_sample(workload_type, llm)
        if sample:
            samples.append(sample)
    return samples

# --- 4. Orchestration ---

def _create_llm_config() -> dict:
    """Create LLM configuration dictionary."""
    return {
        "default": LLMConfig(
            provider="google",
            model_name="gemini-2.5-flash-lite",
        )
    }

def setup_llm_manager() -> object:
    """Initialize and return LLM manager with default configuration."""
    llm_manager = LLMManager(_create_llm_config())
    return llm_manager.get_llm("default")

def setup_generation_config(args) -> dict:
    """Create generation parameters from command line arguments."""
    return {
        "temperature": args.temperature,
        "top_p": args.top_p,
        "top_k": args.top_k
    }

def print_generation_info(args, num_processes: int, total_samples: int) -> None:
    """Print generation configuration and processing information."""
    console.print(f"Generation Config: [yellow]temp={args.temperature}, top_p={args.top_p}, top_k={args.top_k}[/yellow]")
    console.print(f"Using [yellow]{num_processes}[/yellow] cores to generate [yellow]{total_samples}[/yellow] total samples.")

def initialize_corpus_data(args) -> Tuple[List[str], int, int, dict]:
    """Initialize workload types, processing parameters, and corpus structure."""
    workload_types = list(META_PROMPTS.keys())
    num_samples_per_type = args.samples_per_type
    num_processes = min(cpu_count(), args.max_cores)
    corpus = {key: [] for key in workload_types}
    return workload_types, num_samples_per_type, num_processes, corpus

def _create_worker_tasks(workload_types: List[str], num_samples_per_type: int) -> List[Tuple]:
    """Create task tuples for multiprocessing worker pool."""
    return [(w_type, num_samples_per_type) for w_type in workload_types]

def _execute_pool_generation(worker_func, tasks_for_pool: List[Tuple], num_processes: int, corpus: dict) -> dict:
    """Execute generation tasks using multiprocessing pool with progress tracking."""
    with Pool(processes=num_processes) as pool:
        with Progress() as progress:
            task = progress.add_task("[green]Generating content...", total=len(tasks_for_pool))
            for result in pool.imap_unordered(worker_func, tasks_for_pool):
                _process_generation_result(result, corpus)
                progress.update(task, advance=1)
    return corpus

def generate_content_with_pool(llm, workload_types: List[str], num_samples_per_type: int, num_processes: int, corpus: dict) -> dict:
    """Execute multiprocessing content generation with progress tracking."""
    worker_func = partial(generate_for_type, llm=llm)
    tasks_for_pool = _create_worker_tasks(workload_types, num_samples_per_type)
    return _execute_pool_generation(worker_func, tasks_for_pool, num_processes, corpus)

def _process_generation_result(result, corpus: dict) -> None:
    """Process individual generation result and add to corpus."""
    if result:
        for item in result:
            if item and item.get('type') in corpus:
                corpus[item['type']].append(item['data'])

def save_corpus_results(corpus: dict, output_file: str) -> None:
    """Save generated corpus to JSON file."""
    with open(output_file, 'w') as f:
        json.dump(corpus, f, indent=2)

def print_completion_stats(corpus: dict, output_file: str, duration: float) -> None:
    """Print final generation statistics and completion message."""
    console.print(f"\n[bold green]Successfully generated content corpus![/bold green]")
    for w_type, samples in corpus.items():
        console.print(f"  - [cyan]{w_type}[/cyan]: {len(samples)} samples")
    console.print(f"Output saved to [cyan]{output_file}[/cyan]")
    console.print(f"Total time: [yellow]{duration:.2f}s[/yellow]")

def _setup_generation_environment(args):
    """Setup LLM manager and print initialization message."""
    llm = setup_llm_manager()
    console.print("[bold cyan]Starting AI-Powered Content Corpus Generation (Structured)...[/bold cyan]")
    return llm, time.time()

def _execute_generation_workflow(args, llm, workload_types, num_samples_per_type, num_processes, corpus):
    """Execute the core generation workflow and return updated corpus."""
    print_generation_info(args, num_processes, num_samples_per_type * len(workload_types))
    return generate_content_with_pool(llm, workload_types, num_samples_per_type, num_processes, corpus)

def main(args):
    """Main orchestration function - coordinates content generation workflow."""
    llm, start_time = _setup_generation_environment(args)
    generation_params = setup_generation_config(args)
    workload_types, num_samples_per_type, num_processes, corpus = initialize_corpus_data(args)
    corpus = _execute_generation_workflow(args, llm, workload_types, num_samples_per_type, num_processes, corpus)
    save_corpus_results(corpus, args.output_file)
    print_completion_stats(corpus, args.output_file, time.time() - start_time)

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