"""
High-Performance Synthetic Data Generation System for the Unified LLM Operations Schema.
Entry point for synthetic data generation with modular architecture.
"""

# Import core functionality
# Maintain backward compatibility
import argparse
import asyncio
import sys
from multiprocessing import cpu_count

from netra_backend.app.agents.synthetic_data_generator import (
    ContentPairGenerator,
    DataFrameBuilder,
    DataGenerationHelper,
    MultiTurnGenerator,
    ParallelProcessor,
    generate_data_chunk,
)
from netra_backend.app.synthetic_data_core import (
    SyntheticDataCLI,
    SyntheticDataOrchestrator,
    main,
)
from netra_backend.app.synthetic_data_loader import (
    ClickHouseCorpusLoader,
    ConfigurationManager,
    ContentCorpusManager,
    FileCorpusLoader,
)


# Re-export main function for backward compatibility
async def load_content_corpus_from_clickhouse():
    """Load content corpus from ClickHouse - backward compatibility."""
    loader = ClickHouseCorpusLoader()
    return await loader.load_content_corpus_from_clickhouse()

def load_content_corpus(corpus_path: str):
    """Load content corpus from file - backward compatibility."""
    loader = FileCorpusLoader()
    return loader.load_content_corpus(corpus_path)

def get_config(config_path: str = "config.yaml"):
    """Get configuration - backward compatibility."""
    manager = ConfigurationManager()
    return manager.get_config(config_path)

# CLI execution for standalone usage
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="High-Performance Synthetic Log Generator")
    parser.add_argument("--config", default="config.yaml", help="Path to the configuration YAML file.")
    parser.add_argument("--num-traces", type=int, default=1000, help="Total number of traces to generate.")
    parser.add_argument("--output-file", default="generated_logs.json", help="Path to the output JSON file.")
    parser.add_argument("--max-cores", type=int, default=cpu_count(), help="Maximum number of CPU cores to use.")
    parser.add_argument("--corpus-file", default="content_corpus.json", help="Path to the AI-generated content corpus file.")
    
    # Handle empty argv
    if len(sys.argv) == 1:
        args = parser.parse_args(['--num-traces', '1000'])
    else:
        args = parser.parse_args()

    asyncio.run(main(args))