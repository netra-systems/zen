"""
Content corpus and configuration loading for synthetic data generation.
Handles loading from ClickHouse, file system, and configuration management.
"""

import json
import os
import yaml
import asyncio
from rich.console import Console

from netra_backend.app.db.clickhouse import get_clickhouse_client
from netra_backend.app.db.models_clickhouse import CONTENT_CORPUS_TABLE_NAME
from netra_backend.app.default_synthetic_config import DEFAULT_CONFIG
from netra_backend.app.content_corpus import DEFAULT_CONTENT_CORPUS

console = Console()


class ClickHouseCorpusLoader:
    """Loads content corpus from ClickHouse database."""
    
    async def load_content_corpus_from_clickhouse(self) -> dict:
        """Load corpus from ClickHouse with fallback to default."""
        try:
            return await self._load_corpus_from_clickhouse_client()
        except Exception as e:
            return self._handle_clickhouse_connection_error(e)
    
    def _handle_clickhouse_connection_error(self, e: Exception) -> dict:
        """Handle ClickHouse connection errors."""
        console.print(f"[red]Error connecting to ClickHouse: {e}. Falling back to default corpus.[/red]")
        return DEFAULT_CONTENT_CORPUS
    
    async def _load_corpus_from_clickhouse_client(self) -> dict:
        """Handle ClickHouse client operations for corpus loading."""
        async with get_clickhouse_client() as client:
            if not client.ping():
                console.print("[yellow]Warning: ClickHouse connection failed. Falling back to default corpus.[/yellow]")
                return DEFAULT_CONTENT_CORPUS
            return await self._fetch_and_process_corpus_data(client)
    
    async def _fetch_and_process_corpus_data(self, client) -> dict:
        """Fetch and process corpus data from ClickHouse."""
        query = f"SELECT workload_type, prompt, response FROM {CONTENT_CORPUS_TABLE_NAME}"
        query_result = await client.execute_query(query)
        corpus = self._build_corpus_from_query_result(query_result)
        return self._validate_corpus_result(corpus)
    
    def _build_corpus_from_query_result(self, query_result) -> dict:
        """Build corpus dictionary from query results."""
        corpus = {}
        for row in query_result:
            workload_type = row['workload_type']
            self._add_row_to_corpus(corpus, workload_type, row)
        return corpus
    
    def _add_row_to_corpus(self, corpus: dict, workload_type: str, row: dict) -> None:
        """Add single row to corpus dictionary."""
        if workload_type not in corpus:
            corpus[workload_type] = []
        corpus[workload_type].append((row['prompt'], row['response']))
    
    def _validate_corpus_result(self, corpus: dict) -> dict:
        """Validate corpus result and return appropriate fallback."""
        if not corpus:
            console.print("[yellow]Warning: Content corpus from ClickHouse is empty. Using default corpus.[/yellow]")
            return DEFAULT_CONTENT_CORPUS
        console.print("[green]Successfully loaded content corpus from ClickHouse.[/green]")
        return corpus


class FileCorpusLoader:
    """Loads content corpus from file system."""
    
    def load_content_corpus(self, corpus_path: str) -> dict:
        """Load corpus from JSON file with fallback to default."""
        if os.path.exists(corpus_path):
            return self._load_existing_corpus_file(corpus_path)
        return self._handle_missing_corpus_file()
    
    def _load_existing_corpus_file(self, corpus_path: str) -> dict:
        """Load and parse existing corpus file."""
        try:
            return self._read_and_parse_corpus_file(corpus_path)
        except json.JSONDecodeError:
            return self._handle_corpus_parse_error(corpus_path)
    
    def _read_and_parse_corpus_file(self, corpus_path: str) -> dict:
        """Read and parse corpus file content."""
        with open(corpus_path, 'r') as f:
            console.print(f"[green]Loading content from external corpus: [cyan]{corpus_path}[/cyan][/green]")
            return json.load(f)
    
    def _handle_corpus_parse_error(self, corpus_path: str) -> dict:
        """Handle corpus file parsing errors."""
        console.print(f"[red]Error: Could not parse '{corpus_path}'. Falling back to default corpus.")
        return DEFAULT_CONTENT_CORPUS
    
    def _handle_missing_corpus_file(self) -> dict:
        """Handle case when corpus file is missing."""
        console.print("[yellow]Warning: External content corpus not found. Using default internal corpus.")
        return DEFAULT_CONTENT_CORPUS


class ConfigurationManager:
    """Manages YAML configuration loading and updating."""
    
    def get_config(self, config_path: str = "config.yaml") -> dict:
        """Load configuration from YAML file, updating if necessary."""
        config = self._load_or_create_config(config_path)
        return self._update_config_if_needed(config, config_path)
    
    def _load_or_create_config(self, config_path: str) -> dict:
        """Load existing config or create default one."""
        if not os.path.exists(config_path):
            self._create_default_config(config_path)
        
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    
    def _create_default_config(self, config_path: str) -> None:
        """Create default configuration file."""
        console.print(f"[yellow]Config file not found. Creating default '{config_path}'...[/yellow]")
        with open(config_path, "w") as f:
            f.write(DEFAULT_CONFIG)
    
    def _update_config_if_needed(self, config: dict, config_path: str) -> dict:
        """Update config with new trace types if needed."""
        generation_settings = config.get('generation_settings', {})
        trace_distribution = generation_settings.get('trace_distribution', {})
        
        if 'multi_turn_tool_use' not in trace_distribution:
            return self._update_trace_distribution(config, config_path, trace_distribution)
        return config
    
    def _update_trace_distribution(self, config: dict, config_path: str, trace_distribution: dict) -> dict:
        """Update trace distribution with new multi-turn tool use."""
        console.print("[yellow]Updating config file to include 'multi_turn_tool_use' trace type...[/yellow]")
        self._add_multi_turn_tool_use(trace_distribution)
        self._renormalize_trace_weights(trace_distribution)
        config['generation_settings']['trace_distribution'] = trace_distribution
        self._save_updated_config(config, config_path)
        return config
    
    def _add_multi_turn_tool_use(self, trace_distribution: dict) -> None:
        """Add multi-turn tool use to trace distribution."""
        trace_distribution['multi_turn_tool_use'] = 0.1
    
    def _renormalize_trace_weights(self, trace_distribution: dict) -> None:
        """Renormalize trace weights to maintain total of 1.0."""
        total_weight = sum(trace_distribution.values())
        renormalization_factor = 0.9 / (total_weight - 0.1)
        self._apply_renormalization_factor(trace_distribution, renormalization_factor)
        self._ensure_weight_sum_equals_one(trace_distribution)
    
    def _apply_renormalization_factor(self, trace_distribution: dict, renormalization_factor: float) -> None:
        """Apply renormalization factor to trace weights."""
        for key, value in trace_distribution.items():
            if key != 'multi_turn_tool_use':
                trace_distribution[key] = value * renormalization_factor
    
    def _ensure_weight_sum_equals_one(self, trace_distribution: dict) -> None:
        """Ensure trace distribution weights sum to 1.0."""
        total_sum = sum(trace_distribution.values())
        if total_sum != 1.0:
            trace_distribution['simple_chat'] += 1.0 - total_sum
    
    def _save_updated_config(self, config: dict, config_path: str) -> None:
        """Save updated configuration to file."""
        with open(config_path, "w") as f:
            yaml.dump(config, f)
        console.print("[green]Config file updated successfully.[/green]")


class ContentCorpusManager:
    """Manages content corpus loading from multiple sources."""
    
    def __init__(self):
        self.clickhouse_loader = ClickHouseCorpusLoader()
        self.file_loader = FileCorpusLoader()
    
    async def load_content_corpus_auto(self) -> dict:
        """Load content corpus automatically from ClickHouse."""
        return await self.clickhouse_loader.load_content_corpus_from_clickhouse()
    
    def load_content_corpus_from_file(self, corpus_path: str) -> dict:
        """Load content corpus from file path."""
        return self.file_loader.load_content_corpus(corpus_path)