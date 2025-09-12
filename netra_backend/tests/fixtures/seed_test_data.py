"""
Test Database Seeding Script
Populates test databases with small, fast-loading datasets.
Maximum 300 lines, functions  <= 8 lines.
"""

import asyncio
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from netra_backend.app.core.exceptions import NetraException
from netra_backend.tests.small_datasets import get_all_small_datasets

class TestDataSeeder:
    """Fast test database seeding service"""
    
    def __init__(self):
        self.datasets = get_all_small_datasets()
        self.seed_start_time = 0.0
        
    async def seed_all_databases(self, target_dbs: Optional[List[str]] = None) -> Dict[str, bool]:
        """Seed all configured test databases"""
        self.seed_start_time = time.time()
        target_dbs = target_dbs or ["postgres", "clickhouse", "redis"]
        
        results = {}
        for db_name in target_dbs:
            try:
                results[db_name] = await self._seed_database(db_name)
            except Exception as e:
                results[db_name] = False
                print(f"Failed to seed {db_name}: {e}")
        
        return results

    async def _seed_database(self, db_name: str) -> bool:
        """Seed specific database with test data"""
        seeder_map = {
            "postgres": self._seed_postgres,
            "clickhouse": self._seed_clickhouse, 
            "redis": self._seed_redis
        }
        
        if db_name not in seeder_map:
            raise NetraException(f"Unknown database: {db_name}")
        
        return await seeder_map[db_name]()

    async def _seed_postgres(self) -> bool:
        """Seed PostgreSQL with relational test data"""
        try:
            # Agent requests and supply options
            await self._insert_agent_requests()
            await self._insert_supply_options()
            await self._insert_cost_constraints()
            return True
        except Exception as e:
            print(f"PostgreSQL seeding failed: {e}")
            return False

    async def _seed_clickhouse(self) -> bool:
        """Seed ClickHouse with time-series test data"""
        try:
            # Performance metrics and multi-constraint data
            await self._insert_performance_metrics()
            await self._insert_multi_constraint_data()
            return True
        except Exception as e:
            print(f"ClickHouse seeding failed: {e}")
            return False

    async def _seed_redis(self) -> bool:
        """Seed Redis with cache test data"""
        try:
            # KV cache configurations
            await self._insert_kv_cache_configs()
            await self._insert_edge_case_data()
            return True
        except Exception as e:
            print(f"Redis seeding failed: {e}")
            return False

    async def _insert_agent_requests(self):
        """Insert agent optimization requests"""
        requests = self.datasets["agent_requests"]
        # Mock database insertion - replace with actual DB calls
        await self._mock_insert("agent_requests", requests)

    async def _insert_supply_options(self):
        """Insert supply option configurations"""
        # Generate supply options from agent requests
        supply_data = self._transform_to_supply_options()
        await self._mock_insert("supply_options", supply_data)

    async def _insert_cost_constraints(self):
        """Insert cost/latency constraint data"""
        constraints = self.datasets["cost_constraints"]
        await self._mock_insert("cost_constraints", constraints)

    async def _insert_performance_metrics(self):
        """Insert performance metric time-series data"""
        metrics = self.datasets["performance_metrics"]
        await self._mock_insert("performance_metrics", metrics)

    async def _insert_multi_constraint_data(self):
        """Insert multi-constraint scenario data"""
        scenarios = self.datasets["multi_constraint_scenarios"]
        await self._mock_insert("multi_constraint_scenarios", scenarios)

    async def _insert_kv_cache_configs(self):
        """Insert KV cache configuration data"""
        configs = self.datasets["kv_cache_configs"]
        await self._mock_insert("kv_cache_configs", configs)

    async def _insert_edge_case_data(self):
        """Insert edge case test data"""
        edge_cases = self.datasets["edge_cases"]
        for category, cases in edge_cases.items():
            await self._mock_insert(f"edge_cases_{category}", cases)

    def _transform_to_supply_options(self) -> List[Dict[str, Any]]:
        """Transform agent requests to supply options"""
        requests = self.datasets["agent_requests"]
        return [
            {
                "id": i + 1,
                "name": f"{req['model_provider']}_{req['model_name']}",
                "description": f"Supply option for {req['model_name']} via {req['model_provider']}"
            }
            for i, req in enumerate(requests[:10])  # Limit to 10
        ]

    async def _mock_insert(self, table_name: str, data: List[Dict[str, Any]]):
        """Mock database insertion with performance tracking"""
        insert_start = time.time()
        
        # Simulate database operations
        await asyncio.sleep(0.001 * len(data))  # 1ms per record
        
        insert_time = time.time() - insert_start
        print(f"Inserted {len(data)} records into {table_name} in {insert_time:.3f}s")

    def get_seed_performance_stats(self) -> Dict[str, Any]:
        """Get seeding performance statistics"""
        total_time = time.time() - self.seed_start_time
        total_records = sum(len(dataset) if isinstance(dataset, list) else 
                          sum(len(v) for v in dataset.values()) 
                          for dataset in self.datasets.values())
        
        return {
            "total_time_seconds": round(total_time, 3),
            "total_records": total_records,
            "records_per_second": round(total_records / max(total_time, 0.001), 1),
            "performance_target_met": total_time < 1.0
        }

class FastTestDataLoader:
    """Ultra-fast test data loader for unit tests"""
    
    def __init__(self):
        self.cache = {}
        
    def load_dataset(self, dataset_name: str) -> List[Dict[str, Any]]:
        """Load specific dataset with caching"""
        if dataset_name not in self.cache:
            datasets = get_all_small_datasets()
            if dataset_name not in datasets:
                raise NetraException(f"Unknown dataset: {dataset_name}")
            self.cache[dataset_name] = datasets[dataset_name]
        
        return self.cache[dataset_name]

    def load_sample_data(self, dataset_name: str, count: int = 5) -> List[Dict[str, Any]]:
        """Load sample subset of dataset"""
        full_dataset = self.load_dataset(dataset_name)
        return full_dataset[:count]

    def clear_cache(self):
        """Clear dataset cache"""
        self.cache.clear()

# CLI interface for manual seeding
async def main():
    """Main seeding interface"""
    import sys
    
    seeder = TestDataSeeder()
    
    if len(sys.argv) > 1:
        target_dbs = sys.argv[1].split(',')
    else:
        target_dbs = ["postgres", "clickhouse", "redis"]
    
    print(f"Seeding databases: {', '.join(target_dbs)}")
    results = await seeder.seed_all_databases(target_dbs)
    
    print("\nSeeding Results:")
    for db, success in results.items():
        status = "[U+2713] SUCCESS" if success else "[U+2717] FAILED"
        print(f"  {db}: {status}")
    
    stats = seeder.get_seed_performance_stats()
    print(f"\nPerformance Stats:")
    print(f"  Total time: {stats['total_time_seconds']}s")
    print(f"  Total records: {stats['total_records']}")
    print(f"  Speed: {stats['records_per_second']} records/sec")
    print(f"  Target met (<1s): {'[U+2713]' if stats['performance_target_met'] else '[U+2717]'}")

# Export instances
test_seeder = TestDataSeeder()
fast_loader = FastTestDataLoader()

# Convenience functions
async def seed_test_databases(databases: Optional[List[str]] = None) -> Dict[str, bool]:
    """Quick database seeding function"""
    return await test_seeder.seed_all_databases(databases)

def load_test_dataset(name: str) -> List[Dict[str, Any]]:
    """Quick dataset loading function"""
    return fast_loader.load_dataset(name)

def load_sample_data(name: str, count: int = 5) -> List[Dict[str, Any]]:
    """Quick sample data loading function"""
    return fast_loader.load_sample_data(name, count)

if __name__ == "__main__":
    asyncio.run(main())