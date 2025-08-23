"""
Data generation and processing logic for synthetic data.
Handles vectorized data generation, trace creation, and parallel processing.
"""

import hashlib
import random
import uuid
from multiprocessing import Pool, cpu_count

import numpy as np
import pandas as pd
from faker import Faker
from rich.progress import Progress

from netra_backend.app.content_corpus import DEFAULT_CONTENT_CORPUS

fake = Faker()


class DataGenerationHelper:
    """Helper functions for data generation."""
    
    @staticmethod
    def _generate_app_model_choices(num_logs: int, config: dict) -> tuple:
        """Generate app and model selections for data chunk."""
        apps = config['realism']['applications']
        models = config['realism']['models']
        app_choices = np.random.choice(len(apps), num_logs)
        model_choices = np.random.choice(len(models), num_logs)
        return app_choices, model_choices, apps, models
    
    @staticmethod
    def _generate_trace_type_weights(config: dict) -> tuple:
        """Generate normalized weights for simple trace types."""
        trace_dist = config['generation_settings']['trace_distribution']
        simple_types = [t for t in trace_dist.keys() if t != 'multi_turn_tool_use']
        simple_weights = [trace_dist[t] for t in simple_types]
        normalized_weights = np.array(simple_weights) / np.sum(simple_weights)
        return simple_types, normalized_weights
    
    @staticmethod
    def _generate_trace_identifiers(num_logs: int) -> dict:
        """Generate trace and span identifiers for DataFrame."""
        return {
            'trace_id': [str(uuid.uuid4()) for _ in range(num_logs)],
            'span_id': [str(uuid.uuid4()) for _ in range(num_logs)]
        }
    
    @staticmethod
    def _generate_app_service_data(app_choices: np.ndarray, apps: list) -> dict:
        """Generate application and service data for DataFrame."""
        return {
            'app_name': [apps[i]['app_name'] for i in app_choices],
            'service_name': [random.choice(apps[i]['services']) for i in app_choices]
        }
    
    @staticmethod
    def _generate_model_data(model_choices: np.ndarray, models: list) -> dict:
        """Generate model provider and configuration data for DataFrame."""
        return {
            'model_provider': [models[i]['provider'] for i in model_choices],
            'model_name': [models[i]['name'] for i in model_choices],
            'model_pricing': [models[i]['pricing'] for i in model_choices]
        }


class ContentPairGenerator:
    """Generates content pairs for different trace types."""
    
    def _generate_content_pairs(self, num_logs: int, config: dict, content_corpus: dict) -> tuple:
        """Generate prompt and response pairs for data chunk."""
        simple_types, weights = DataGenerationHelper._generate_trace_type_weights(config)
        chosen_types = np.random.choice(simple_types, num_logs, p=weights)
        return self._build_prompt_response_pairs(chosen_types, content_corpus)
    
    def _build_prompt_response_pairs(self, chosen_types: np.ndarray, content_corpus: dict) -> tuple:
        """Build prompt and response pairs from chosen trace types."""
        prompts, responses = [], []
        for trace_type in chosen_types:
            prompt, response = self._get_random_content_pair(trace_type, content_corpus)
            prompts.append(prompt)
            responses.append(response)
        return prompts, responses
    
    def _get_random_content_pair(self, trace_type: str, content_corpus: dict) -> tuple:
        """Get random prompt-response pair for trace type."""
        corpus_source = self._select_corpus_source(trace_type, content_corpus)
        return random.choice(corpus_source[trace_type])
    
    def _select_corpus_source(self, trace_type: str, content_corpus: dict) -> dict:
        """Select appropriate corpus source for trace type."""
        if trace_type in content_corpus and content_corpus[trace_type]:
            return content_corpus
        return DEFAULT_CONTENT_CORPUS


class DataFrameBuilder:
    """Builds complete DataFrames with all required fields."""
    
    def __init__(self):
        self.content_generator = ContentPairGenerator()
    
    def _create_base_dataframe(self, num_logs: int, app_choices: np.ndarray, model_choices: np.ndarray,
                              apps: list, models: list, prompts: list, responses: list) -> pd.DataFrame:
        """Create base DataFrame with core data."""
        base_data = self._build_base_data_dict(num_logs, app_choices, apps, model_choices, models, prompts)
        return pd.DataFrame(base_data)

    def _build_base_data_dict(self, num_logs: int, app_choices: np.ndarray, apps: list, 
                             model_choices: np.ndarray, models: list, prompts: list) -> dict:
        """Build the base data dictionary for DataFrame creation."""
        base_data = {
            **DataGenerationHelper._generate_trace_identifiers(num_logs),
            **DataGenerationHelper._generate_app_service_data(app_choices, apps)
        }
        base_data.update({
            **DataGenerationHelper._generate_model_data(model_choices, models),
            'user_prompt': prompts
        })
        return base_data
    
    def _add_response_data(self, df: pd.DataFrame, responses: list, num_logs: int) -> pd.DataFrame:
        """Add response and timing data to DataFrame."""
        df['assistant_response'] = responses
        df['prompt_tokens'] = [len(p.split()) * 2 for p in df['user_prompt']]
        df['completion_tokens'] = [len(r.split()) * 2 for r in responses]
        df['total_e2e_ms'] = np.random.randint(200, 2000, size=num_logs)
        df['ttft_ms'] = np.random.randint(150, 800, size=num_logs)
        return df
    
    def _add_user_data(self, df: pd.DataFrame, num_logs: int) -> pd.DataFrame:
        """Add user and organization data to DataFrame."""
        df['user_id'] = [str(uuid.uuid4()) for _ in range(num_logs)]
        df['organization_id'] = [f"org_{hashlib.sha256(fake.company().encode()).hexdigest()[:12]}" for _ in range(num_logs)]
        return df
    
    def _calculate_token_costs(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate token costs and totals for DataFrame."""
        df['total_tokens'] = df['prompt_tokens'] + df['completion_tokens']
        df['prompt_cost'] = (df['prompt_tokens'] / 1_000_000) * df['model_pricing'].apply(lambda x: x[0])
        df['completion_cost'] = (df['completion_tokens'] / 1_000_000) * df['model_pricing'].apply(lambda x: x[1])
        df['total_cost'] = df['prompt_cost'] + df['completion_cost']
        return df
    
    def _build_complete_dataframe(self, num_logs: int, app_choices: np.ndarray, model_choices: np.ndarray,
                                 apps: list, models: list, prompts: list, responses: list) -> pd.DataFrame:
        """Build complete DataFrame with all data elements."""
        df = self._create_base_dataframe(num_logs, app_choices, model_choices, apps, models, prompts, responses)
        df = self._add_response_data(df, responses, num_logs)
        df = self._add_user_data(df, num_logs)
        return self._calculate_token_costs(df)


class ChunkDataGenerator(DataFrameBuilder):
    """Generates data chunks for parallel processing."""
    
    def generate_data_chunk(self, args) -> pd.DataFrame:
        """Generate chunk of data as Pandas DataFrame for parallel processing."""
        num_logs, config, content_corpus = args
        app_choices, model_choices, apps, models = DataGenerationHelper._generate_app_model_choices(num_logs, config)
        prompts, responses = self.content_generator._generate_content_pairs(num_logs, config, content_corpus)
        return self._build_complete_dataframe(num_logs, app_choices, model_choices, apps, models, prompts, responses)


class ParallelProcessor:
    """Handles parallel processing of data generation."""
    
    def __init__(self):
        self.chunk_generator = ChunkDataGenerator()
    
    def _calculate_worker_chunks(self, num_simple_logs: int, num_processes: int) -> list:
        """Calculate chunks for parallel processing."""
        chunk_size = num_simple_logs // num_processes
        chunks = [chunk_size] * num_processes
        remainder = num_simple_logs % num_processes
        if remainder:
            chunks.append(remainder)
        return chunks
    
    def _execute_parallel_generation(self, chunks: list, config: dict, content_corpus: dict, num_processes: int) -> list:
        """Execute parallel data generation using multiprocessing."""
        from rich.console import Console
        console = Console()
        console.print(f"Using [yellow]{num_processes}[/yellow] cores to generate simple logs...")
        with Pool(processes=num_processes) as pool:
            worker_args = [(chunk, config, content_corpus) for chunk in chunks]
            return pool.map(self.chunk_generator.generate_data_chunk, worker_args)
    
    def _format_generation_results(self, results: list) -> list:
        """Format parallel generation results into log entries."""
        from netra_backend.app.data.synthetic.log_formatter import format_log_entry
        combined_df = pd.concat(results, ignore_index=True)
        return [format_log_entry(row) for _, row in combined_df.iterrows()]
    
    def generate_simple_logs_parallel(self, num_simple_logs: int, config: dict, content_corpus: dict, max_cores: int) -> list:
        """Generate simple logs using parallel processing."""
        num_processes = min(cpu_count(), max_cores)
        chunks = self._calculate_worker_chunks(num_simple_logs, num_processes)
        results = self._execute_parallel_generation(chunks, config, content_corpus, num_processes)
        return self._format_generation_results(results)


class MultiTurnGenerator:
    """Generates multi-turn conversation traces."""
    
    def _generate_multi_turn_logs(self, config: dict, content_corpus: dict, num_multi_turn: int) -> list:
        """Generate multi-turn traces sequentially."""
        from rich.console import Console
        console = Console()
        console.print(f"Generating [yellow]{num_multi_turn}[/yellow] multi-turn traces...")
        all_multi_turn_logs = []
        return self._generate_traces_with_progress(config, content_corpus, num_multi_turn, all_multi_turn_logs)
    
    def _generate_traces_with_progress(self, config: dict, content_corpus: dict, num_multi_turn: int, all_multi_turn_logs: list) -> list:
        """Generate traces with progress tracking."""
        from netra_backend.app.data.synthetic.multi_turn_generator import generate_multi_turn_tool_trace
        with Progress() as progress:
            task = progress.add_task("[magenta]Generating complex traces...", total=num_multi_turn)
            for _ in range(num_multi_turn):
                all_multi_turn_logs.extend(generate_multi_turn_tool_trace(config, content_corpus))
                progress.update(task, advance=1)
        return all_multi_turn_logs


class TraceDistributionCalculator:
    """Calculates trace distribution for generation."""
    
    def _calculate_trace_distribution(self, total_traces: int, config: dict) -> tuple:
        """Calculate number of each trace type to generate."""
        from rich.console import Console
        console = Console()
        trace_dist = config['generation_settings']['trace_distribution']
        num_multi_turn = round(total_traces * trace_dist.get('multi_turn_tool_use', 0.0))
        num_simple_logs = total_traces - num_multi_turn
        console.print(f"Planning to generate [yellow]{num_simple_logs}[/yellow] simple logs and [yellow]{num_multi_turn}[/yellow] multi-turn traces.")
        return num_simple_logs, num_multi_turn


# Create global instances for module functions
chunk_generator = ChunkDataGenerator()

def generate_data_chunk(args) -> pd.DataFrame:
    """Module-level function for multiprocessing compatibility."""
    return chunk_generator.generate_data_chunk(args)