"""
Main orchestration and CLI functionality for synthetic data generation.
Coordinates the entire data generation pipeline and handles command-line interface.
"""

import argparse
import asyncio
import json
import random
import sys
import time
from multiprocessing import cpu_count

from rich.console import Console

from netra_backend.app.agents.synthetic_data_generator import (
    MultiTurnGenerator,
    ParallelProcessor,
    TraceDistributionCalculator,
)
from netra_backend.app.synthetic_data_loader import (
    ConfigurationManager,
    ContentCorpusManager,
)

console = Console()


class SyntheticDataOrchestrator:
    """Main orchestrator for synthetic data generation."""
    
    def __init__(self):
        self.config_manager = ConfigurationManager()
        self.corpus_manager = ContentCorpusManager()
        self.parallel_processor = ParallelProcessor()
        self.multi_turn_generator = MultiTurnGenerator()
        self.distribution_calculator = TraceDistributionCalculator()
    
    async def generate_synthetic_data(self, args) -> list:
        """Main function to generate synthetic logs."""
        start_time = time.time()
        config, content_corpus = await self._setup_generation_environment(args)
        all_logs = await self._generate_all_logs(args, config, content_corpus)
        await self._finalize_generation(args, all_logs, start_time)
        return all_logs
    
    async def _setup_generation_environment(self, args) -> tuple:
        """Setup configuration and content corpus for generation."""
        console.print("[bold cyan]Starting High-Performance Synthetic Log Generation...[/bold cyan]")
        config_path = args.config if hasattr(args, 'config') else "config.yaml"
        config = self.config_manager.get_config(config_path)
        content_corpus = await self._load_content_corpus(args)
        return config, content_corpus
    
    async def _load_content_corpus(self, args) -> dict:
        """Load content corpus from args or ClickHouse."""
        if hasattr(args, 'corpus') and args.corpus:
            console.print("[green]Using content corpus provided in arguments.[/green]")
            return args.corpus
        else:
            return await self.corpus_manager.load_content_corpus_auto()
    
    async def _generate_all_logs(self, args, config: dict, content_corpus: dict) -> list:
        """Generate both simple and multi-turn logs."""
        num_simple_logs, num_multi_turn = self.distribution_calculator._calculate_trace_distribution(args.num_traces, config)
        simple_logs = await self._generate_simple_logs_if_needed(args, config, content_corpus, num_simple_logs)
        multi_turn_logs = await self._generate_multi_turn_logs_if_needed(config, content_corpus, num_multi_turn)
        return self._combine_all_logs(simple_logs, multi_turn_logs)
    
    def _combine_all_logs(self, simple_logs: list, multi_turn_logs: list) -> list:
        """Combine simple and multi-turn logs into single list."""
        all_logs = []
        all_logs.extend(simple_logs)
        all_logs.extend(multi_turn_logs)
        return all_logs
    
    async def _generate_simple_logs_if_needed(self, args, config: dict, content_corpus: dict, num_simple_logs: int) -> list:
        """Generate simple logs if needed."""
        if num_simple_logs > 0:
            return await self._generate_simple_logs(args, config, content_corpus, num_simple_logs)
        return []
    
    async def _generate_multi_turn_logs_if_needed(self, config: dict, content_corpus: dict, num_multi_turn: int) -> list:
        """Generate multi-turn logs if needed."""
        if num_multi_turn > 0:
            return await self._generate_multi_turn_logs(config, content_corpus, num_multi_turn)
        return []
    
    async def _generate_simple_logs(self, args, config: dict, content_corpus: dict, num_simple_logs: int) -> list:
        """Generate simple logs in parallel."""
        max_cores = args.max_cores if hasattr(args, 'max_cores') else cpu_count()
        return self.parallel_processor.generate_simple_logs_parallel(num_simple_logs, config, content_corpus, max_cores)
    
    async def _generate_multi_turn_logs(self, config: dict, content_corpus: dict, num_multi_turn: int) -> list:
        """Generate multi-turn traces sequentially."""
        return self.multi_turn_generator._generate_multi_turn_logs(config, content_corpus, num_multi_turn)
    
    async def _finalize_generation(self, args, all_logs: list, start_time: float) -> None:
        """Finalize generation with shuffling, stats, and optional output."""
        console.print("Shuffling all generated logs for realism...")
        random.shuffle(all_logs)
        self._print_generation_stats(all_logs, start_time)
        await self._save_output_if_standalone(args, all_logs)
    
    def _print_generation_stats(self, all_logs: list, start_time: float) -> None:
        """Print generation performance statistics."""
        duration = time.time() - start_time
        logs_per_second = len(all_logs) / duration if duration > 0 else 0
        console.print(f"[bold green]Successfully generated {len(all_logs)} total log entries.[/bold green]")
        console.print(f"Total time: [yellow]{duration:.2f}s[/yellow]")
        console.print(f"Performance: [bold yellow]{logs_per_second:.2f} logs/second[/bold yellow]")
    
    async def _save_output_if_standalone(self, args, all_logs: list) -> None:
        """Save output to file if running as standalone script."""
        is_standalone = hasattr(args, 'output_file')
        if is_standalone:
            console.print(f"Saving output to [cyan]{args.output_file}[/cyan]...")
            with open(args.output_file, 'w') as f:
                json.dump(all_logs, f, indent=2)


class CLIArgumentParser:
    """Handles command-line argument parsing for the synthetic data generator."""
    
    def create_argument_parser(self) -> argparse.ArgumentParser:
        """Create and configure argument parser."""
        parser = argparse.ArgumentParser(description="High-Performance Synthetic Log Generator")
        parser.add_argument("--config", default="config.yaml", help="Path to the configuration YAML file.")
        parser.add_argument("--num-traces", type=int, default=1000, help="Total number of traces to generate.")
        parser.add_argument("--output-file", default="generated_logs.json", help="Path to the output JSON file.")
        parser.add_argument("--max-cores", type=int, default=cpu_count(), help="Maximum number of CPU cores to use.")
        parser.add_argument("--corpus-file", default="content_corpus.json", help="Path to the AI-generated content corpus file.")
        return parser
    
    def parse_arguments(self, parser: argparse.ArgumentParser):
        """Parse command-line arguments with fallback for empty argv."""
        if len(sys.argv) == 1:
            return parser.parse_args(['--num-traces', '1000'])
        else:
            return parser.parse_args()


class SyntheticDataCLI:
    """Command-line interface for synthetic data generation."""
    
    def __init__(self):
        self.orchestrator = SyntheticDataOrchestrator()
        self.arg_parser = CLIArgumentParser()
    
    async def run_cli(self) -> list:
        """Run the CLI application."""
        parser = self.arg_parser.create_argument_parser()
        args = self.arg_parser.parse_arguments(parser)
        return await self.orchestrator.generate_synthetic_data(args)


# Main entry point function
async def main(args) -> list:
    """Main function to generate synthetic logs. Can be called from other modules."""
    orchestrator = SyntheticDataOrchestrator()
    return await orchestrator.generate_synthetic_data(args)


# CLI execution
if __name__ == "__main__":
    async def run_main():
        cli = SyntheticDataCLI()
        await cli.run_cli()
    
    asyncio.run(run_main())