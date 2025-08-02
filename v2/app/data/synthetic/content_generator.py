# AI-Powered Content Corpus Generator
#
# This script uses a powerful Large Language Model (Gemini) to generate a rich corpus
# of realistic prompts and responses for various workload types. It leverages
# multiprocessing to generate content in parallel, making the process highly efficient.
#
# The output of this script is a JSON file (`content_corpus.json`) that can be
# used by the main `synthetic_data_v2.py` generator to create more varied and
# realistic synthetic log data.
#
# SETUP:
# 1. Install necessary libraries:
#    pip install google-generativeai rich
#
# 2. Set your Gemini API Key:
#    export GEMINI_API_KEY="YOUR_API_KEY"
#
# USAGE:
# Run the script from your terminal:
#    python -m app.data.synthetic.content_generator --samples-per-type 50 --output-file content_corpus.json

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
    "failed_request": "Generate a user prompt that is impossible or unsafe for an AI assistant to fulfill. Then, provide a polite but firm refusal as the assistant's response."
}

def generate_content_sample(workload_type: str, model) -> dict:
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

    try:
        response = model.generate_content(prompt_template)
        # Basic cleaning to handle markdown code blocks
        cleaned_text = response.text.strip().replace("```json", "").replace("```", "").strip()
        content = json.loads(cleaned_text)
        if "user_prompt" in content and "assistant_response" in content:
            return {"type": workload_type, "data": (content["user_prompt"], content["assistant_response"]) }
    except Exception as e:
        # This can happen due to API errors, rate limits, or invalid JSON output
        # console.print(f"[yellow]Warning: Failed to generate/parse content for '{workload_type}': {e}[/yellow]")
        return None
    return None

def generate_for_type(workload_type: str, num_samples: int, model):
    """Worker function to generate multiple samples for a single workload type."""
    samples = []
    for _ in range(num_samples):
        sample = generate_content_sample(workload_type, model)
        if sample:
            samples.append(sample)
    return samples

def main(args):
    if not genai or not GEMINI_API_KEY:
        console.print("[bold red]Cannot proceed: Gemini API is not configured.[/bold red]")
        sys.exit(1)

    console.print("[bold cyan]Starting AI-Powered Content Corpus Generation...[/bold cyan]")
    start_time = time.time()

    model = genai.GenerativeModel('gemini-1.5-flash')
    workload_types = list(META_PROMPTS.keys())
    num_samples_per_type = args.samples_per_type
    num_processes = min(cpu_count(), args.max_cores)

    tasks = [(w_type, num_samples_per_type, model) for w_type in workload_types]

    console.print(f"Using [yellow]{num_processes}[/yellow] cores to generate [yellow]{num_samples_per_type * len(workload_types)}[/yellow] total samples.")

    corpus = {key: [] for key in workload_types}

    # Use a partial function to pass the model to the worker without pickling issues
    worker_func = partial(generate_for_type, model=model)

    with Pool(processes=num_processes) as pool:
        with Progress() as progress:
            task = progress.add_task("[green]Generating content...", total=len(tasks))
            results = []
            # Using imap_unordered to process results as they complete
            for result in pool.imap_unordered(worker_func, [(t[0], t[1]) for t in tasks]):
                results.extend(result)
                progress.update(task, advance=1)

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

    if len(sys.argv) == 1:
        args = parser.parse_args(['--samples-per-type', '10'])
    else:
        args = parser.parse_args()

    main(args)
