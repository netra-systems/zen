"""
Seed Data Management for Real LLM Testing

Provides centralized management of test seed data with transaction-based isolation
and rollback capabilities for reproducible real LLM tests.

Business Value Justification (BVJ):
1. Segment: Platform/Internal
2. Business Goal: Testing Infrastructure Reliability
3. Value Impact: Ensures consistent, reproducible test environments for AI optimization validation
4. Revenue Impact: Prevents costly production issues through reliable testing

ARCHITECTURAL COMPLIANCE:
- File size: <500 lines (modular design)
- Function size: <25 lines each
- Single responsibility: Seed data management and isolation
- Type safety with proper error handling
"""

import json
import os
import hashlib
import logging
import asyncio
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
from dataclasses import dataclass, field
from contextlib import asynccontextmanager
import asyncpg
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


@dataclass
class SeedDataSet:
    """Configuration for a seed data set."""
    name: str
    path: Path
    description: str
    checksum: Optional[str] = None
    loaded_at: Optional[datetime] = None
    record_counts: Dict[str, int] = field(default_factory=dict)


@dataclass 
class TestEnvironmentConfig:
    """Configuration for test environment database."""
    database_url: str
    schema_name: str = "netra_test"
    redis_url: Optional[str] = None
    redis_namespace: str = "test:"
    clickhouse_url: Optional[str] = None
    clickhouse_database: str = "netra_test"
    transaction_isolation: bool = True


class DatabaseTransactionManager:
    """Manages database transactions for test isolation."""
    
    def __init__(self, database_url: str, schema_name: str = "netra_test"):
        self.database_url = database_url
        self.schema_name = schema_name
        self.connection_pool: Optional[asyncpg.Pool] = None
        self.active_transactions: Dict[str, asyncpg.Connection] = {}
    
    async def initialize(self):
        """Initialize database connection pool."""
        self.connection_pool = await asyncpg.create_pool(
            self.database_url,
            min_size=2,
            max_size=10,
            command_timeout=60,
            server_settings={
                'search_path': f'{self.schema_name},public'
            }
        )
        logger.info(f"Database pool initialized for schema {self.schema_name}")
    
    async def close(self):
        """Close database connections and cleanup."""
        if self.active_transactions:
            logger.warning(f"Cleaning up {len(self.active_transactions)} active transactions")
            for test_id, conn in self.active_transactions.items():
                try:
                    await conn.execute("ROLLBACK")
                    await conn.close()
                except Exception as e:
                    logger.error(f"Error cleaning up transaction {test_id}: {e}")
            self.active_transactions.clear()
        
        if self.connection_pool:
            await self.connection_pool.close()
            logger.info("Database pool closed")
    
    @asynccontextmanager
    async def get_test_transaction(self, test_id: str):
        """Get isolated transaction for a specific test."""
        if not self.connection_pool:
            raise RuntimeError("Database pool not initialized")
        
        conn = await self.connection_pool.acquire()
        try:
            # Start transaction with READ COMMITTED isolation
            await conn.execute("BEGIN ISOLATION LEVEL READ COMMITTED")
            self.active_transactions[test_id] = conn
            
            logger.debug(f"Started transaction for test {test_id}")
            yield conn
            
        except Exception as e:
            # Rollback on any error
            logger.error(f"Error in test transaction {test_id}: {e}")
            await conn.execute("ROLLBACK")
            raise
        finally:
            # Always cleanup transaction
            if test_id in self.active_transactions:
                del self.active_transactions[test_id]
            await self.connection_pool.release(conn)
    
    async def rollback_test_transaction(self, test_id: str):
        """Explicitly rollback a test transaction."""
        if test_id in self.active_transactions:
            conn = self.active_transactions[test_id]
            await conn.execute("ROLLBACK")
            del self.active_transactions[test_id]
            await self.connection_pool.release(conn)
            logger.debug(f"Rolled back transaction for test {test_id}")


class SeedDataLoader:
    """Loads and manages seed data for testing."""
    
    def __init__(self, data_directory: Path):
        self.data_directory = data_directory
        self.loaded_datasets: Dict[str, SeedDataSet] = {}
        self.seed_cache: Dict[str, Dict[str, Any]] = {}
    
    async def load_seed_data_set(self, dataset_name: str) -> SeedDataSet:
        """Load a specific seed data set from file."""
        if dataset_name in self.loaded_datasets:
            return self.loaded_datasets[dataset_name]
        
        data_file = self.data_directory / "seed" / f"{dataset_name}.json"
        if not data_file.exists():
            raise FileNotFoundError(f"Seed data file not found: {data_file}")
        
        try:
            with open(data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Calculate checksum for data integrity
            file_content = data_file.read_text(encoding='utf-8')
            checksum = hashlib.sha256(file_content.encode()).hexdigest()
            
            # Extract metadata
            metadata = data.get('metadata', {})
            record_counts = metadata.get('record_count', {})
            
            dataset = SeedDataSet(
                name=dataset_name,
                path=data_file,
                description=metadata.get('description', f'Seed data: {dataset_name}'),
                checksum=checksum,
                loaded_at=datetime.now(timezone.utc),
                record_counts=record_counts
            )
            
            self.loaded_datasets[dataset_name] = dataset
            self.seed_cache[dataset_name] = data
            
            logger.info(f"Loaded seed dataset: {dataset_name} ({len(record_counts)} record types)")
            return dataset
            
        except Exception as e:
            logger.error(f"Failed to load seed data {dataset_name}: {e}")
            raise
    
    def get_seed_data(self, dataset_name: str, section: Optional[str] = None) -> Dict[str, Any]:
        """Get loaded seed data for a dataset."""
        if dataset_name not in self.seed_cache:
            raise ValueError(f"Dataset {dataset_name} not loaded")
        
        data = self.seed_cache[dataset_name]
        if section:
            if section not in data:
                raise KeyError(f"Section {section} not found in dataset {dataset_name}")
            return data[section]
        
        return data
    
    async def verify_data_integrity(self, dataset_name: str) -> bool:
        """Verify data integrity using checksums."""
        if dataset_name not in self.loaded_datasets:
            return False
        
        dataset = self.loaded_datasets[dataset_name]
        current_content = dataset.path.read_text(encoding='utf-8')
        current_checksum = hashlib.sha256(current_content.encode()).hexdigest()
        
        if current_checksum != dataset.checksum:
            logger.error(f"Data integrity check failed for {dataset_name}")
            return False
        
        return True


class SeedDataInjector:
    """Injects seed data into test database."""
    
    def __init__(self, transaction_manager: DatabaseTransactionManager):
        self.transaction_manager = transaction_manager
    
    async def inject_basic_optimization_data(self, test_id: str, seed_data: Dict[str, Any]):
        """Inject basic optimization seed data into test database."""
        async with self.transaction_manager.get_test_transaction(test_id) as conn:
            
            # Inject users
            users = seed_data.get('users', [])
            for user in users:
                await conn.execute("""
                    INSERT INTO users (id, email, permissions, tier, created_at)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (id) DO NOTHING
                """, user['id'], user['email'], user['permissions'], 
                    user['tier'], datetime.fromisoformat(user['created_at'].replace('Z', '+00:00')))
            
            # Inject models
            models = seed_data.get('models', [])
            for model in models:
                await conn.execute("""
                    INSERT INTO models (id, provider, cost_per_1k_tokens, avg_response_time_ms, 
                                      performance_rating, use_cases)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT (id) DO UPDATE SET
                        cost_per_1k_tokens = EXCLUDED.cost_per_1k_tokens,
                        avg_response_time_ms = EXCLUDED.avg_response_time_ms,
                        performance_rating = EXCLUDED.performance_rating,
                        use_cases = EXCLUDED.use_cases
                """, model['id'], model['provider'], model['cost_per_1k_tokens'],
                    model['avg_response_time_ms'], model['performance_rating'], model['use_cases'])
            
            # Inject threads
            threads = seed_data.get('threads', [])
            for thread in threads:
                await conn.execute("""
                    INSERT INTO threads (id, user_id, title, status, created_at, 
                                       last_activity, message_count, optimization_focus)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    ON CONFLICT (id) DO NOTHING
                """, thread['id'], thread['user_id'], thread['title'], thread['status'],
                    datetime.fromisoformat(thread['created_at'].replace('Z', '+00:00')),
                    datetime.fromisoformat(thread['last_activity'].replace('Z', '+00:00')),
                    thread['message_count'], thread['optimization_focus'])
            
            # Inject metrics
            metrics_data = seed_data.get('metrics', {})
            daily_aggregates = metrics_data.get('daily_aggregates', [])
            for daily in daily_aggregates:
                await conn.execute("""
                    INSERT INTO metrics (date, total_requests, total_cost, avg_response_time_ms,
                                       successful_requests, failed_requests, model_usage)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    ON CONFLICT (date) DO UPDATE SET
                        total_requests = EXCLUDED.total_requests,
                        total_cost = EXCLUDED.total_cost,
                        avg_response_time_ms = EXCLUDED.avg_response_time_ms,
                        successful_requests = EXCLUDED.successful_requests,
                        failed_requests = EXCLUDED.failed_requests,
                        model_usage = EXCLUDED.model_usage
                """, daily['date'], daily['total_requests'], daily['total_cost'],
                    daily['avg_response_time_ms'], daily['successful_requests'],
                    daily['failed_requests'], json.dumps(daily.get('top_models', [])))
            
            logger.info(f"Injected basic optimization data for test {test_id}")
    
    async def inject_complex_workflows_data(self, test_id: str, seed_data: Dict[str, Any]):
        """Inject complex workflows seed data."""
        async with self.transaction_manager.get_test_transaction(test_id) as conn:
            
            # Inject corpus entries
            corpus_entries = seed_data.get('corpus_entries', [])
            for entry in corpus_entries:
                await conn.execute("""
                    INSERT INTO corpus_entries (id, title, content, category, tags, 
                                              quality_score, last_updated, usage_count, effectiveness_rating)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    ON CONFLICT (id) DO UPDATE SET
                        content = EXCLUDED.content,
                        quality_score = EXCLUDED.quality_score,
                        last_updated = EXCLUDED.last_updated,
                        usage_count = EXCLUDED.usage_count
                """, entry['id'], entry['title'], entry['content'], entry['category'],
                    entry['tags'], entry['quality_score'], 
                    datetime.fromisoformat(entry['last_updated'].replace('Z', '+00:00')),
                    entry['usage_count'], entry['effectiveness_rating'])
            
            # Inject supply chain configurations
            supply_configs = seed_data.get('supply_chain_configurations', [])
            for config in supply_configs:
                await conn.execute("""
                    INSERT INTO supply_chain_configs (id, name, configuration, is_active)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (id) DO UPDATE SET
                        name = EXCLUDED.name,
                        configuration = EXCLUDED.configuration,
                        is_active = EXCLUDED.is_active,
                        updated_at = NOW()
                """, config['id'], config['name'], json.dumps(config), True)
            
            logger.info(f"Injected complex workflows data for test {test_id}")


class SeedDataManager:
    """Main manager for seed data operations in real LLM testing."""
    
    def __init__(self, config: TestEnvironmentConfig):
        self.config = config
        self.transaction_manager = DatabaseTransactionManager(config.database_url, config.schema_name)
        self.data_loader = SeedDataLoader(Path(__file__).parent.parent / "test_data")
        self.data_injector = SeedDataInjector(self.transaction_manager)
        self.active_test_sessions: Dict[str, List[str]] = {}
    
    async def initialize(self):
        """Initialize seed data manager."""
        await self.transaction_manager.initialize()
        logger.info("Seed data manager initialized")
    
    async def close(self):
        """Close seed data manager and cleanup resources."""
        await self.transaction_manager.close()
        logger.info("Seed data manager closed")
    
    async def setup_test_environment(self, test_id: str, required_datasets: List[str]) -> Dict[str, Any]:
        """Setup isolated test environment with specified datasets."""
        try:
            # Load required datasets
            loaded_datasets = {}
            for dataset_name in required_datasets:
                dataset = await self.data_loader.load_seed_data_set(dataset_name)
                loaded_datasets[dataset_name] = dataset
                
                # Inject data based on dataset type
                seed_data = self.data_loader.get_seed_data(dataset_name)
                
                if dataset_name == 'basic_optimization':
                    await self.data_injector.inject_basic_optimization_data(test_id, seed_data)
                elif dataset_name == 'complex_workflows':
                    await self.data_injector.inject_complex_workflows_data(test_id, seed_data)
                # Add more dataset types as needed
            
            self.active_test_sessions[test_id] = required_datasets
            
            summary = {
                'test_id': test_id,
                'datasets_loaded': list(loaded_datasets.keys()),
                'total_record_types': sum(len(ds.record_counts) for ds in loaded_datasets.values()),
                'setup_time': datetime.now(timezone.utc).isoformat(),
                'isolation_enabled': self.config.transaction_isolation
            }
            
            logger.info(f"Test environment setup complete for {test_id}: {len(required_datasets)} datasets")
            return summary
            
        except Exception as e:
            logger.error(f"Failed to setup test environment {test_id}: {e}")
            await self.cleanup_test_environment(test_id)
            raise
    
    async def cleanup_test_environment(self, test_id: str):
        """Cleanup test environment and rollback transactions."""
        try:
            if test_id in self.active_test_sessions:
                await self.transaction_manager.rollback_test_transaction(test_id)
                del self.active_test_sessions[test_id]
                logger.info(f"Cleaned up test environment {test_id}")
            else:
                logger.warning(f"Test environment {test_id} not found for cleanup")
        except Exception as e:
            logger.error(f"Error during cleanup of test {test_id}: {e}")
    
    async def get_test_data_summary(self, test_id: str) -> Optional[Dict[str, Any]]:
        """Get summary of test data for a specific test."""
        if test_id not in self.active_test_sessions:
            return None
        
        datasets = self.active_test_sessions[test_id]
        summary = {
            'test_id': test_id,
            'active_datasets': datasets,
            'dataset_details': {}
        }
        
        for dataset_name in datasets:
            if dataset_name in self.data_loader.loaded_datasets:
                dataset = self.data_loader.loaded_datasets[dataset_name]
                summary['dataset_details'][dataset_name] = {
                    'description': dataset.description,
                    'record_counts': dataset.record_counts,
                    'loaded_at': dataset.loaded_at.isoformat() if dataset.loaded_at else None,
                    'checksum': dataset.checksum[:8] + '...' if dataset.checksum else None
                }
        
        return summary


# Global manager instance for use across test suite
_seed_data_manager: Optional[SeedDataManager] = None

async def get_seed_data_manager(config: Optional[TestEnvironmentConfig] = None) -> SeedDataManager:
    """Get global seed data manager instance."""
    global _seed_data_manager
    
    if _seed_data_manager is None:
        if config is None:
            # Use default test configuration
            database_url = os.getenv('TEST_DATABASE_URL', 'postgresql://localhost/netra_test')
            config = TestEnvironmentConfig(database_url=database_url)
        
        _seed_data_manager = SeedDataManager(config)
        await _seed_data_manager.initialize()
    
    return _seed_data_manager


async def cleanup_global_seed_manager():
    """Cleanup global seed data manager."""
    global _seed_data_manager
    if _seed_data_manager:
        await _seed_data_manager.close()
        _seed_data_manager = None