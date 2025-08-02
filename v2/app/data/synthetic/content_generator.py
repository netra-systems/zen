# AI-Powered Content Corpus Generator
#
# This script uses a powerful Large Language Model (Gemini) to generate a rich corpus
# of realistic prompts and responses for various workload types. It leverages
# multiprocessing to generate content in parallel, making the process highly efficient.
#
# The output of this script is a JSON file (`content_corpus.json`) that can be
# used by the main `synthetic_data_v2.py` generator to create more varied and
# realistic synthetic log data.
# python -m app.data.synthetic.content_generator --samples-per-type 50 --output-file content_corpus.json

import os
import json
import time
import argparse
import sys
from multiprocessing import Pool, cpu_count
from functools import partial

from rich.console import Console
from rich.progress import Progress
from dotenv import load_dotenv

load_dotenv()

console = Console()

# --- Gemini Integration ---
try:
    import google.generativeai as genai
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
    else:
        console.print("[red]GEMINI_API_KEY environment variable not set.[/red]")
        genai = None
except ImportError:
    console.print("[red]google.generativeai not installed. Please run `pip install google-generativeai`[/red]")
    genai = None

# --- Content Generation Prompts ---
# These are "meta-prompts" designed to instruct the LLM on what kind of content to generate.
META_PROMPTS = {
    "simple_chat": "Generate a realistic user question and a corresponding helpful assistant response. The topic should be related to technology, cloud computing, or artificial intelligence.",
    "rag_pipeline": "Generate a user question that requires a specific piece of information, a short context paragraph containing that information, and an assistant response that answers the question based *only* on the provided context.",
    "tool_use": "Generate a user request that requires calling a fictional API or tool (e.g., a weather API, a calculator, or a flight booking tool). Then, provide an assistant response that acknowledges the request and confirms the parameters before executing the tool call.",
    "failed_request": "Generate a user prompt that is impossible or unsafe for an AI assistant to fulfill. Then, provide a polite but firm refusal as the assistant's response.",
    "multi_turn_tool_use": "Generate a realistic, multi-turn conversation between a user and an AI assistant where the assistant uses tools to fulfill the user's request. The conversation should have between 3 and 5 turns. The final output should be a single JSON object with a key 'conversation' which contains a list of lists, where each inner list is a [user_prompt, assistant_response] pair."
}

def generate_content_sample(workload_type: str, model, generation_config) -> dict:
    """Generates a single sample for a given workload type using the LLM."""
    if not model:
        return None

    meta_prompt = META_PROMPTS[workload_type]
    
    prompt_template = f"""
    You are a synthetic data generator. Your task is to create a realistic data sample for the workload type: '{workload_type}'.

    Instructions: {meta_prompt}

    Return ONLY a JSON object with two keys: "user_prompt" and "assistant_response".
    If the instructions mention a "context", include the context within the user_prompt.
    """

    if workload_type == 'multi_turn_tool_use':
        prompt_template += "\nReturn ONLY a JSON object with a single key 'conversation'."
    else:
        prompt_template += "\nReturn ONLY a JSON object with two keys: \"user_prompt\" and \"assistant_response\"."
    
    try:
        response = model.generate_content(prompt_template, generation_config=generation_config)
        # Basic cleaning to handle markdown code blocks
        cleaned_text = response.text.strip().replace("```json", "").replace("```", "").strip()
        content = json.loads(cleaned_text)
        
        if workload_type == 'multi_turn_tool_use':
            if "conversation" in content and isinstance(content["conversation"], list):
                return {"type": workload_type, "data": content["conversation"]}
        elif "user_prompt" in content and "assistant_response" in content:
            return {"type": workload_type, "data": (content["user_prompt"], content["assistant_response"]) }
    except Exception as e:
        # This can happen due to API errors, rate limits, or invalid JSON output
        # console.print(f"[yellow]Warning: Failed to generate/parse content for '{workload_type}': {e}[/yellow]")
        return None
    return None

def generate_for_type(task_args, model, generation_config):
    """Worker function to generate multiple samples for a single workload type."""
    workload_type, num_samples = task_args
    samples = []
    for _ in range(num_samples):
        sample = generate_content_sample(workload_type, model, generation_config)
        if sample:
            samples.append(sample)
    return samples

def main(args):
    if not genai or not GEMINI_API_KEY:
        console.print("[bold red]Cannot proceed: Gemini API is not configured.[/bold red]")
        sys.exit(1)

    console.print("[bold cyan]Starting AI-Powered Content Corpus Generation...[/bold cyan]")
    start_time = time.time()

    generation_config = genai.types.GenerationConfig(
        temperature=args.temperature,
        top_p=args.top_p,
        top_k=args.top_k
    )

    console.print(f"Generation Config: [yellow]temp={args.temperature}, top_p={args.top_p}, top_k={args.top_k}[/yellow]")

    model = genai.GenerativeModel('gemini-2.5-flash')
    workload_types = list(META_PROMPTS.keys())
    num_samples_per_type = args.samples_per_type
    num_processes = min(cpu_count(), args.max_cores)

    tasks = [(w_type, num_samples_per_type, model, generation_config) for w_type in workload_types]

    console.print(f"Using [yellow]{num_processes}[/yellow] cores to generate [yellow]{num_samples_per_type * len(workload_types)}[/yellow] total samples.")

    corpus = {key: [] for key in workload_types}

    # Use a partial function to pass the model and config to the worker without pickling issues
    worker_func = partial(generate_for_type, model=model, generation_config=generation_config)

    with Pool(processes=num_processes) as pool:
        with Progress() as progress:
            task = progress.add_task("[green]Generating content...", total=len(workload_types) * num_samples_per_type)
            results = []
            # Create a flat list of tasks for the pool
            tasks_for_pool = [(w_type, num_samples_per_type) for w_type in workload_types]
            for result in pool.imap_unordered(worker_func, tasks_for_pool):
                results.extend(result)
                progress.update(task, advance=len(result))

    for item in results:
        if item:
            corpus[item['type']].append(item['data'])

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
    parser = argparse.ArgumentParser(description="AI-Powered Content Corpus Generator")
    parser.add_argument("--samples-per-type", type=int, default=10, help="Number of prompt/response pairs to generate for each workload type.")
    parser.add_argument("--output-file", default="content_corpus.json", help="Path to the output JSON file.")
    parser.add_argument("--max-cores", type=int, default=cpu_count(), help="Maximum number of CPU cores to use.")
    parser.add_argument("--temperature", type=float, default=0.9, help="Controls the randomness of the output. Higher is more creative.")
    parser.add_argument("--top-p", type=float, default=None, help="Nucleus sampling probability.")
    parser.add_argument("--top-k", type=int, default=None, help="Top-k sampling control.")


    if len(sys.argv) == 1:
        args = parser.parse_args(['--samples-per-type', '10'])
    else:
        args = parser.parse_args()

    main(args)