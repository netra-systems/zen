"""
Resource-Aware Test Monitoring and Optimization

Real-time system resource monitoring for optimal test distribution
and hardware-aware performance optimization.

Business Value Justification (BVJ):
- Segment: All customer segments (infrastructure efficiency)
- Business Goal: Minimize resource costs while maximizing test throughput
- Value Impact: Reduces CI/CD costs and improves developer productivity
- Revenue Impact: Enables faster release cycles and reduced infrastructure spend
"""

import os
import sys
import time
import psutil
import threading
import subprocess
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from pathlib import Path
import json
import logging
from collections import deque, defaultdict
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class SystemMetrics:
    """Real-time system performance metrics"""
    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_available: int
    disk_io_read: int
    disk_io_write: int
    network_io_sent: int
    network_io_recv: int
    process_count: int
    load_average: Tuple[float, float, float] = field(default=(0.0, 0.0, 0.0))


@dataclass 
class TestResourceUsage:
    """Resource usage for individual test execution"""
    test_id: str
    start_time: float
    end_time: float
    peak_memory: int
    avg_cpu: float
    io_operations: int
    process_count: int
    success: bool


class ResourceMonitor:
    """Real-time system resource monitoring"""
    
    def __init__(self, sample_interval: float = 1.0, history_size: int = 300):
        self.sample_interval = sample_interval
        self.history_size = history_size
        self.metrics_history = deque(maxlen=history_size)
        self.monitoring_active = False
        self.monitoring_thread = None
        self.resource_alerts = defaultdict(list)
        
        # Resource thresholds for alerts
        self.thresholds = {
            'cpu_critical': 90.0,
            'cpu_warning': 80.0,
            'memory_critical': 95.0,
            'memory_warning': 85.0,
            'io_critical': 1000,  # MB/s
            'io_warning': 500     # MB/s
        }
    
    def start_monitoring(self):
        """Start resource monitoring in background thread"""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop)
        self.monitoring_thread.daemon = True
        self.monitoring_thread.start()
        logger.info("Resource monitoring started")
    
    def stop_monitoring(self):
        """Stop resource monitoring"""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5.0)
        logger.info("Resource monitoring stopped")
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        last_disk_io = psutil.disk_io_counters()
        last_net_io = psutil.net_io_counters()
        
        while self.monitoring_active:
            try:
                metrics = self._collect_system_metrics(last_disk_io, last_net_io)
                self.metrics_history.append(metrics)
                
                # Update for next iteration
                last_disk_io = psutil.disk_io_counters()
                last_net_io = psutil.net_io_counters()
                
                # Check for resource alerts
                self._check_resource_alerts(metrics)
                
                time.sleep(self.sample_interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(self.sample_interval)
    
    def _collect_system_metrics(self, last_disk_io, last_net_io) -> SystemMetrics:
        """Collect current system metrics"""
        memory = psutil.virtual_memory()
        disk_io = psutil.disk_io_counters()
        net_io = psutil.net_io_counters()
        
        # Calculate IO rates
        disk_read_rate = (disk_io.read_bytes - last_disk_io.read_bytes) if last_disk_io else 0
        disk_write_rate = (disk_io.write_bytes - last_disk_io.write_bytes) if last_disk_io else 0
        net_sent_rate = (net_io.bytes_sent - last_net_io.bytes_sent) if last_net_io else 0
        net_recv_rate = (net_io.bytes_recv - last_net_io.bytes_recv) if last_net_io else 0
        
        return SystemMetrics(
            timestamp=time.time(),
            cpu_percent=psutil.cpu_percent(interval=None),
            memory_percent=memory.percent,
            memory_available=memory.available,
            disk_io_read=disk_read_rate,
            disk_io_write=disk_write_rate,
            network_io_sent=net_sent_rate,
            network_io_recv=net_recv_rate,
            process_count=len(psutil.pids()),
            load_average=os.getloadavg() if hasattr(os, 'getloadavg') else (0.0, 0.0, 0.0)
        )
    
    def get_current_load(self) -> Dict[str, float]:
        """Get current system load summary"""
        if not self.metrics_history:
            return {'cpu': 0.0, 'memory': 0.0, 'io': 0.0, 'overall': 0.0}
        
        latest = self.metrics_history[-1]
        io_load = min((latest.disk_io_read + latest.disk_io_write) / (100 * 1024 * 1024), 100.0)
        
        overall_load = (latest.cpu_percent + latest.memory_percent + io_load) / 3.0
        
        return {
            'cpu': latest.cpu_percent,
            'memory': latest.memory_percent,
            'io': io_load,
            'overall': overall_load
        }
    
    def get_optimal_worker_count(self) -> int:
        """Calculate optimal worker count based on current load"""
        current_load = self.get_current_load()
        max_workers = psutil.cpu_count() - 1  # Reserve 1 core
        
        if current_load['overall'] > 80:
            return max(1, max_workers // 4)  # Heavily loaded system
        elif current_load['overall'] > 60:
            return max(2, max_workers // 2)  # Moderately loaded
        else:
            return max_workers  # Lightly loaded, use all cores
    
    def predict_resource_impact(self, test_count: int, test_type: str) -> Dict[str, float]:
        """Predict resource impact of running test batch"""
        # Base resource estimates by test type
        base_estimates = {
            'unit': {'cpu': 10, 'memory': 100, 'duration': 5},
            'integration': {'cpu': 25, 'memory': 250, 'duration': 15},
            'e2e': {'cpu': 40, 'memory': 500, 'duration': 30},
            'performance': {'cpu': 60, 'memory': 1000, 'duration': 60}
        }
        
        estimate = base_estimates.get(test_type, base_estimates['integration'])
        
        return {
            'estimated_cpu_increase': estimate['cpu'] * test_count / 100,
            'estimated_memory_mb': estimate['memory'] * test_count,
            'estimated_duration': estimate['duration'] * test_count / self.get_optimal_worker_count(),
            'recommended_workers': min(test_count, self.get_optimal_worker_count())
        }


class ProcessIsolationManager:
    """Manages process isolation for concurrent test execution"""
    
    def __init__(self, max_workers: int = None):
        self.max_workers = max_workers or (psutil.cpu_count() - 1)
        self.process_pool = {}
        self.resource_locks = defaultdict(threading.Lock)
        self.isolation_configs = {}
    
    def create_isolated_environment(self, test_id: str) -> Dict[str, str]:
        """Create isolated environment for test execution"""
        # Create unique temp directory
        temp_dir = Path(f"/tmp/test_isolation_{test_id}_{int(time.time())}")
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Create isolated environment variables
        env = os.environ.copy()
        env.update({
            'TEST_ISOLATION': '1',
            'TEST_ID': test_id,
            'TMPDIR': str(temp_dir),
            'TEMP': str(temp_dir),
            'TMP': str(temp_dir),
            'PYTEST_CURRENT_TEST': test_id,
            'DATABASE_URL': f'sqlite:///{temp_dir}/test_{test_id}.db',
            'REDIS_DB': str(hash(test_id) % 16),  # Use different Redis DB
            'LOG_LEVEL': 'ERROR'  # Reduce log noise
        })
        
        self.isolation_configs[test_id] = {
            'env': env,
            'temp_dir': temp_dir,
            'created_at': time.time()
        }
        
        return env
    
    def cleanup_isolation(self, test_id: str):
        """Clean up isolated environment"""
        if test_id not in self.isolation_configs:
            return
        
        config = self.isolation_configs[test_id]
        temp_dir = config['temp_dir']
        
        try:
            # Remove temporary directory
            if temp_dir.exists():
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
            
            del self.isolation_configs[test_id]
            
        except Exception as e:
            logger.warning(f"Failed to cleanup isolation for {test_id}: {e}")


class TestShardOptimizer:
    """Optimizes test distribution across workers"""
    
    def __init__(self, resource_monitor: ResourceMonitor):
        self.resource_monitor = resource_monitor
        self.execution_history = defaultdict(list)
        self.shard_performance = {}
    
    def optimize_test_distribution(self, test_files: List[str]) -> List[List[str]]:
        """Optimize test distribution across available workers"""
        worker_count = self.resource_monitor.get_optimal_worker_count()
        
        # Classify tests by estimated resource usage
        classified_tests = self._classify_tests(test_files)
        
        # Create balanced shards
        shards = self._create_balanced_shards(classified_tests, worker_count)
        
        return shards
    
    def _classify_tests(self, test_files: List[str]) -> Dict[str, List[str]]:
        """Classify tests by resource requirements"""
        classification = {
            'heavy': [],      # CPU/memory intensive
            'medium': [],     # Moderate resource usage
            'light': [],      # Quick unit tests
            'io_bound': []    # Network/disk intensive
        }
        
        for test_file in test_files:
            category = self._categorize_test(test_file)
            classification[category].append(test_file)
        
        return classification
    
    def _categorize_test(self, test_file: str) -> str:
        """Categorize test based on file patterns and history"""
        test_path = test_file.lower()
        
        # Heavy tests
        if any(keyword in test_path for keyword in ['performance', 'load', 'stress', 'benchmark']):
            return 'heavy'
        
        # IO bound tests
        if any(keyword in test_path for keyword in ['websocket', 'network', 'api', 'client']):
            return 'io_bound'
        
        # Light tests
        if any(keyword in test_path for keyword in ['unit', 'core', 'utils', 'helpers']):
            return 'light'
        
        # Default to medium
        return 'medium'
    
    def _create_balanced_shards(self, classified_tests: Dict[str, List[str]], worker_count: int) -> List[List[str]]:
        """Create balanced test shards"""
        shards = [[] for _ in range(worker_count)]
        shard_weights = [0] * worker_count
        
        # Weight factors for different test types
        weights = {'heavy': 4, 'medium': 2, 'light': 1, 'io_bound': 3}
        
        # Distribute tests using a greedy bin-packing approach
        for category, test_list in classified_tests.items():
            weight = weights[category]
            
            for test_file in test_list:
                # Find shard with minimum weight
                min_shard = min(range(worker_count), key=lambda i: shard_weights[i])
                shards[min_shard].append(test_file)
                shard_weights[min_shard] += weight
        
        return [shard for shard in shards if shard]  # Remove empty shards


class MemoryOptimizer:
    """Optimizes memory usage during test execution"""
    
    def __init__(self):
        self.memory_pools = {}
        self.allocation_tracker = defaultdict(int)
        self.gc_threshold = 0.8  # Trigger GC at 80% memory usage
    
    def create_memory_pool(self, pool_name: str, size_mb: int) -> str:
        """Create memory pool for test isolation"""
        pool_id = f"{pool_name}_{int(time.time())}"
        self.memory_pools[pool_id] = {
            'size_mb': size_mb,
            'allocated': 0,
            'created_at': time.time()
        }
        return pool_id
    
    def allocate_memory(self, pool_id: str, size_mb: int) -> bool:
        """Allocate memory from pool"""
        if pool_id not in self.memory_pools:
            return False
        
        pool = self.memory_pools[pool_id]
        if pool['allocated'] + size_mb > pool['size_mb']:
            return False
        
        pool['allocated'] += size_mb
        self.allocation_tracker[pool_id] += size_mb
        
        # Check if we need garbage collection
        memory_percent = psutil.virtual_memory().percent
        if memory_percent > self.gc_threshold * 100:
            self._trigger_garbage_collection()
        
        return True
    
    def _trigger_garbage_collection(self):
        """Trigger garbage collection to free memory"""
        import gc
        collected = gc.collect()
        logger.info(f"Triggered garbage collection, freed {collected} objects")


class CacheManager:
    """Intelligent test result caching with dependency tracking"""
    
    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(exist_ok=True)
        self.metadata_file = cache_dir / "cache_metadata.json"
        self.file_hashes = {}
        self.dependency_map = {}
        self._load_metadata()
    
    def _load_metadata(self):
        """Load cache metadata"""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r') as f:
                    data = json.load(f)
                    self.file_hashes = data.get('file_hashes', {})
                    self.dependency_map = data.get('dependency_map', {})
            except Exception as e:
                logger.warning(f"Failed to load cache metadata: {e}")
    
    def _save_metadata(self):
        """Save cache metadata"""
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump({
                    'file_hashes': self.file_hashes,
                    'dependency_map': self.dependency_map,
                    'last_updated': time.time()
                }, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save cache metadata: {e}")
    
    def get_file_hash(self, file_path: str) -> str:
        """Get hash of file content"""
        import hashlib
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            return hashlib.sha256(content).hexdigest()[:16]
        except Exception:
            return str(int(time.time()))  # Fallback to timestamp
    
    def is_cached_result_valid(self, test_file: str) -> bool:
        """Check if cached result is still valid"""
        current_hash = self.get_file_hash(test_file)
        cached_hash = self.file_hashes.get(test_file)
        
        if cached_hash != current_hash:
            return False
        
        # Check dependencies
        dependencies = self.dependency_map.get(test_file, [])
        for dep_file in dependencies:
            if not Path(dep_file).exists():
                continue
            dep_hash = self.get_file_hash(dep_file)
            cached_dep_hash = self.file_hashes.get(dep_file)
            if dep_hash != cached_dep_hash:
                return False
        
        return True
    
    def cache_test_result(self, test_file: str, result: Dict, dependencies: List[str] = None):
        """Cache test result with dependencies"""
        # Update file hashes
        self.file_hashes[test_file] = self.get_file_hash(test_file)
        
        if dependencies:
            self.dependency_map[test_file] = dependencies
            for dep_file in dependencies:
                if Path(dep_file).exists():
                    self.file_hashes[dep_file] = self.get_file_hash(dep_file)
        
        # Save result
        cache_file = self.cache_dir / f"{test_file.replace('/', '_')}.json"
        try:
            with open(cache_file, 'w') as f:
                json.dump({
                    'result': result,
                    'cached_at': time.time(),
                    'file_hash': self.file_hashes[test_file]
                }, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to cache result for {test_file}: {e}")
        
        self._save_metadata()


class HardwareAwareOptimizer:
    """Main coordinator for hardware-aware test optimization"""
    
    def __init__(self, cache_dir: Path = None):
        self.cache_dir = cache_dir or Path("test_optimization_cache")
        self.resource_monitor = ResourceMonitor()
        self.process_manager = ProcessIsolationManager()
        self.shard_optimizer = TestShardOptimizer(self.resource_monitor)
        self.memory_optimizer = MemoryOptimizer()
        self.cache_manager = CacheManager(self.cache_dir)
        
        # Performance tracking
        self.execution_stats = defaultdict(list)
        self.optimization_history = []
    
    def optimize_test_execution(self, test_files: List[str], **kwargs) -> Dict[str, Any]:
        """Main optimization pipeline"""
        start_time = time.time()
        
        # Start resource monitoring
        self.resource_monitor.start_monitoring()
        
        try:
            # Phase 1: Pre-execution optimization
            optimization_plan = self._create_optimization_plan(test_files)
            
            # Phase 2: Execute with monitoring
            results = self._execute_optimized(optimization_plan)
            
            # Phase 3: Post-execution analysis
            performance_metrics = self._analyze_performance(results, start_time)
            
            return {
                'results': results,
                'performance': performance_metrics,
                'optimization_plan': optimization_plan
            }
        
        finally:
            self.resource_monitor.stop_monitoring()
    
    def _create_optimization_plan(self, test_files: List[str]) -> Dict[str, Any]:
        """Create comprehensive optimization plan"""
        current_load = self.resource_monitor.get_current_load()
        optimal_workers = self.resource_monitor.get_optimal_worker_count()
        
        # Filter cached tests
        cached_tests = []
        uncached_tests = []
        
        for test_file in test_files:
            if self.cache_manager.is_cached_result_valid(test_file):
                cached_tests.append(test_file)
            else:
                uncached_tests.append(test_file)
        
        # Optimize test distribution
        test_shards = self.shard_optimizer.optimize_test_distribution(uncached_tests)
        
        return {
            'cached_tests': cached_tests,
            'test_shards': test_shards,
            'optimal_workers': optimal_workers,
            'current_load': current_load,
            'memory_allocation': self._calculate_memory_allocation(test_shards),
            'estimated_duration': self._estimate_execution_time(test_shards)
        }
    
    def _calculate_memory_allocation(self, test_shards: List[List[str]]) -> Dict[str, int]:
        """Calculate optimal memory allocation per shard"""
        total_memory = psutil.virtual_memory().total
        available_memory = int(total_memory * 0.8)  # Use 80% of available memory
        
        shard_count = len(test_shards)
        if shard_count == 0:
            return {}
        
        memory_per_shard = available_memory // shard_count
        
        return {
            'total_available_mb': available_memory // (1024 * 1024),
            'memory_per_shard_mb': memory_per_shard // (1024 * 1024),
            'reserved_memory_mb': (total_memory - available_memory) // (1024 * 1024)
        }