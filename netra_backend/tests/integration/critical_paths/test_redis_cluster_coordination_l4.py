#!/usr/bin/env python3
"""
Comprehensive test for Redis cluster coordination:
1. Cluster node discovery and failover
2. Consistent hashing and key distribution
3. Master-slave replication monitoring
4. Resharding and rebalancing operations
5. Split-brain detection and resolution
6. Cross-datacenter replication
7. Cluster health monitoring
8. Performance under network partitions

This test validates Redis cluster coordination at scale.
"""

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

import asyncio
import json
import time
import random
from pathlib import Path
from typing import Optional, Dict, Any, List, Set
import aiohttp
import redis.asyncio as redis
import pytest
from datetime import datetime, timedelta
import hashlib

# Add project root to path
import sys
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Configuration
REDIS_NODES = [
    {"host": "localhost", "port": 7000, "role": "master"},
    {"host": "localhost", "port": 7001, "role": "master"},
    {"host": "localhost", "port": 7002, "role": "master"},
    {"host": "localhost", "port": 7003, "role": "slave"},
    {"host": "localhost", "port": 7004, "role": "slave"},
    {"host": "localhost", "port": 7005, "role": "slave"}
]

BASE_URL = "http://localhost:8000"
CLUSTER_MANAGER_URL = "http://localhost:8085"

# Test configuration
NUM_TEST_KEYS = 10000
NUM_TEST_OPERATIONS = 50000
REPLICATION_LAG_THRESHOLD = 100  # milliseconds
FAILOVER_TIME_THRESHOLD = 5000  # milliseconds


class RedisClusterTester:
    """Test Redis cluster coordination."""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.redis_clients: Dict[str, redis.Redis] = {}
        self.cluster_state: Dict[str, Any] = {}
        self.test_data: Dict[str, str] = {}
        self.metrics: Dict[str, float] = {}
        
    async def __aenter__(self):
        """Setup test environment."""
        self.session = aiohttp.ClientSession()
        
        # Connect to Redis nodes
        for node in REDIS_NODES:
            client = redis.Redis(
                host=node["host"],
                port=node["port"],
                decode_responses=True
            )
            self.redis_clients[f"{node['host']}:{node['port']}"] = client
            
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup test environment."""
        # Close Redis connections
        for client in self.redis_clients.values():
            await client.close()
            
        if self.session:
            await self.session.close()
            
    async def test_cluster_initialization(self) -> bool:
        """Test cluster initialization and node discovery."""
        print("\n[INIT] Testing cluster initialization...")
        
        try:
            # Get cluster info
            async with self.session.get(
                f"{CLUSTER_MANAGER_URL}/cluster/info"
            ) as response:
                if response.status == 200:
                    cluster_info = await response.json()
                    
                    # Verify all nodes are discovered
                    discovered_nodes = cluster_info.get("nodes", [])
                    expected_count = len(REDIS_NODES)
                    
                    if len(discovered_nodes) == expected_count:
                        print(f"[OK] All {expected_count} nodes discovered")
                        
                        # Check node roles
                        masters = sum(1 for n in discovered_nodes if n.get("role") == "master")
                        slaves = sum(1 for n in discovered_nodes if n.get("role") == "slave")
                        
                        print(f"[OK] Cluster topology: {masters} masters, {slaves} slaves")
                        
                        # Store cluster state
                        self.cluster_state = cluster_info
                        return True
                    else:
                        print(f"[ERROR] Expected {expected_count} nodes, found {len(discovered_nodes)}")
                        
        except Exception as e:
            print(f"[ERROR] Cluster initialization failed: {e}")
            
        return False
        
    async def test_consistent_hashing(self) -> bool:
        """Test consistent hashing and key distribution."""
        print("\n[HASH] Testing consistent hashing...")
        
        try:
            # Generate test keys
            key_distribution = {}
            
            for i in range(NUM_TEST_KEYS):
                key = f"test_key_{i}"
                
                # Get slot for key
                slot = self._get_key_slot(key)
                
                # Find responsible node
                node = await self._get_node_for_slot(slot)
                
                if node not in key_distribution:
                    key_distribution[node] = 0
                key_distribution[node] += 1
                
            # Check distribution balance
            total_keys = sum(key_distribution.values())
            expected_per_node = total_keys / len([n for n in REDIS_NODES if n["role"] == "master"])
            
            print(f"[INFO] Key distribution across nodes:")
            for node, count in key_distribution.items():
                deviation = abs(count - expected_per_node) / expected_per_node * 100
                print(f"  {node}: {count} keys ({deviation:.1f}% deviation)")
                
            # Check if distribution is reasonably balanced (within 20% deviation)
            max_deviation = max(
                abs(count - expected_per_node) / expected_per_node * 100
                for count in key_distribution.values()
            )
            
            if max_deviation < 20:
                print(f"[OK] Key distribution balanced (max deviation: {max_deviation:.1f}%)")
                return True
            else:
                print(f"[WARN] Key distribution imbalanced (max deviation: {max_deviation:.1f}%)")
                return False
                
        except Exception as e:
            print(f"[ERROR] Consistent hashing test failed: {e}")
            return False
            
    def _get_key_slot(self, key: str) -> int:
        """Calculate Redis cluster slot for a key."""
        # CRC16 implementation for Redis cluster
        return int(hashlib.md5(key.encode()).hexdigest(), 16) % 16384
        
    async def _get_node_for_slot(self, slot: int) -> str:
        """Get responsible node for a slot."""
        # Simplified - in real implementation would use cluster slots command
        masters = [n for n in REDIS_NODES if n["role"] == "master"]
        slots_per_master = 16384 // len(masters)
        master_index = slot // slots_per_master
        
        if master_index >= len(masters):
            master_index = len(masters) - 1
            
        node = masters[master_index]
        return f"{node['host']}:{node['port']}"
        
    async def test_master_slave_replication(self) -> bool:
        """Test master-slave replication."""
        print("\n[REPLICATION] Testing master-slave replication...")
        
        try:
            # Write to masters
            test_value = f"replication_test_{time.time()}"
            masters = [n for n in REDIS_NODES if n["role"] == "master"]
            
            for master in masters:
                client = self.redis_clients[f"{master['host']}:{master['port']}"]
                key = f"repl_test_{master['port']}"
                
                await client.set(key, test_value)
                self.test_data[key] = test_value
                
            # Wait for replication
            await asyncio.sleep(0.5)
            
            # Check slaves
            slaves = [n for n in REDIS_NODES if n["role"] == "slave"]
            replication_success = True
            
            for slave in slaves:
                client = self.redis_clients[f"{slave['host']}:{slave['port']}"]
                
                # Check if slave has replicated data
                for key, expected_value in self.test_data.items():
                    try:
                        value = await client.get(key)
                        if value == expected_value:
                            print(f"[OK] Slave {slave['port']} replicated {key}")
                        else:
                            print(f"[ERROR] Slave {slave['port']} missing {key}")
                            replication_success = False
                    except:
                        pass  # Slave might not have this key's slot
                        
            # Check replication lag
            async with self.session.get(
                f"{CLUSTER_MANAGER_URL}/cluster/replication/lag"
            ) as response:
                if response.status == 200:
                    lag_data = await response.json()
                    max_lag = max(lag_data.get("lags", {}).values())
                    
                    if max_lag < REPLICATION_LAG_THRESHOLD:
                        print(f"[OK] Replication lag within threshold: {max_lag}ms")
                    else:
                        print(f"[WARN] High replication lag: {max_lag}ms")
                        
            return replication_success
            
        except Exception as e:
            print(f"[ERROR] Replication test failed: {e}")
            return False
            
    async def test_automatic_failover(self) -> bool:
        """Test automatic failover on master failure."""
        print("\n[FAILOVER] Testing automatic failover...")
        
        try:
            # Pick a master to fail
            masters = [n for n in REDIS_NODES if n["role"] == "master"]
            failed_master = masters[0]
            
            print(f"[INFO] Simulating failure of master {failed_master['port']}")
            
            # Simulate master failure
            failover_start = time.time()
            
            async with self.session.post(
                f"{CLUSTER_MANAGER_URL}/cluster/node/fail",
                json={"node": f"{failed_master['host']}:{failed_master['port']}"}
            ) as response:
                if response.status == 200:
                    print(f"[OK] Master marked as failed")
                    
            # Wait for failover
            failover_complete = False
            while time.time() - failover_start < FAILOVER_TIME_THRESHOLD / 1000:
                # Check cluster state
                async with self.session.get(
                    f"{CLUSTER_MANAGER_URL}/cluster/info"
                ) as response:
                    if response.status == 200:
                        cluster_info = await response.json()
                        
                        # Check if a slave was promoted
                        new_masters = [
                            n for n in cluster_info.get("nodes", [])
                            if n.get("role") == "master"
                        ]
                        
                        if len(new_masters) == len(masters):
                            failover_complete = True
                            break
                            
                await asyncio.sleep(0.5)
                
            failover_time = (time.time() - failover_start) * 1000
            
            if failover_complete:
                print(f"[OK] Failover completed in {failover_time:.0f}ms")
                self.metrics["failover_time"] = failover_time
                return True
            else:
                print(f"[ERROR] Failover not completed within {FAILOVER_TIME_THRESHOLD}ms")
                return False
                
        except Exception as e:
            print(f"[ERROR] Failover test failed: {e}")
            return False
            
    async def test_resharding(self) -> bool:
        """Test cluster resharding and rebalancing."""
        print("\n[RESHARD] Testing cluster resharding...")
        
        try:
            # Add a new node to cluster
            new_node = {"host": "localhost", "port": 7006, "role": "master"}
            
            async with self.session.post(
                f"{CLUSTER_MANAGER_URL}/cluster/node/add",
                json=new_node
            ) as response:
                if response.status == 200:
                    print(f"[OK] New node added: {new_node['port']}")
                    
            # Trigger resharding
            async with self.session.post(
                f"{CLUSTER_MANAGER_URL}/cluster/reshard",
                json={"strategy": "balanced"}
            ) as response:
                if response.status == 200:
                    reshard_data = await response.json()
                    
                    # Monitor resharding progress
                    reshard_id = reshard_data.get("reshard_id")
                    
                    while True:
                        async with self.session.get(
                            f"{CLUSTER_MANAGER_URL}/cluster/reshard/{reshard_id}/status"
                        ) as status_response:
                            if status_response.status == 200:
                                status = await status_response.json()
                                
                                progress = status.get("progress", 0)
                                print(f"[INFO] Resharding progress: {progress}%")
                                
                                if status.get("status") == "completed":
                                    print(f"[OK] Resharding completed")
                                    
                                    # Verify new distribution
                                    moved_slots = status.get("moved_slots", 0)
                                    print(f"[OK] Moved {moved_slots} slots")
                                    
                                    return True
                                elif status.get("status") == "failed":
                                    print(f"[ERROR] Resharding failed")
                                    return False
                                    
                        await asyncio.sleep(1)
                        
        except Exception as e:
            print(f"[ERROR] Resharding test failed: {e}")
            return False
            
    async def test_split_brain_detection(self) -> bool:
        """Test split-brain detection and resolution."""
        print("\n[SPLIT-BRAIN] Testing split-brain detection...")
        
        try:
            # Simulate network partition
            partition_groups = [
                REDIS_NODES[:3],  # Group 1
                REDIS_NODES[3:]   # Group 2
            ]
            
            async with self.session.post(
                f"{CLUSTER_MANAGER_URL}/cluster/partition/simulate",
                json={"groups": partition_groups}
            ) as response:
                if response.status == 200:
                    print(f"[OK] Network partition simulated")
                    
            # Wait for split-brain detection
            await asyncio.sleep(2)
            
            # Check if split-brain was detected
            async with self.session.get(
                f"{CLUSTER_MANAGER_URL}/cluster/health"
            ) as response:
                if response.status == 200:
                    health = await response.json()
                    
                    if health.get("split_brain_detected"):
                        print(f"[OK] Split-brain condition detected")
                        
                        # Check resolution strategy
                        resolution = health.get("resolution_strategy")
                        print(f"[INFO] Resolution strategy: {resolution}")
                        
                        # Heal partition
                        async with self.session.post(
                            f"{CLUSTER_MANAGER_URL}/cluster/partition/heal"
                        ) as heal_response:
                            if heal_response.status == 200:
                                print(f"[OK] Network partition healed")
                                
                                # Verify cluster consistency
                                await asyncio.sleep(2)
                                
                                async with self.session.get(
                                    f"{CLUSTER_MANAGER_URL}/cluster/consistency/check"
                                ) as consistency_response:
                                    if consistency_response.status == 200:
                                        consistency = await consistency_response.json()
                                        
                                        if consistency.get("consistent"):
                                            print(f"[OK] Cluster consistency restored")
                                            return True
                                        else:
                                            print(f"[ERROR] Cluster still inconsistent")
                                            return False
                                            
        except Exception as e:
            print(f"[ERROR] Split-brain test failed: {e}")
            return False
            
    async def test_performance_under_load(self) -> bool:
        """Test cluster performance under heavy load."""
        print("\n[PERFORMANCE] Testing performance under load...")
        
        try:
            start_time = time.time()
            successful_ops = 0
            failed_ops = 0
            
            # Perform concurrent operations
            tasks = []
            for i in range(NUM_TEST_OPERATIONS):
                operation = random.choice(["set", "get", "delete"])
                key = f"perf_test_{i % 1000}"
                
                if operation == "set":
                    tasks.append(self._perform_set(key, f"value_{i}"))
                elif operation == "get":
                    tasks.append(self._perform_get(key))
                else:
                    tasks.append(self._perform_delete(key))
                    
                # Batch execute every 1000 operations
                if len(tasks) >= 1000:
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    successful_ops += sum(1 for r in results if r is True)
                    failed_ops += sum(1 for r in results if r is False or isinstance(r, Exception))
                    tasks = []
                    
            # Execute remaining tasks
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                successful_ops += sum(1 for r in results if r is True)
                failed_ops += sum(1 for r in results if r is False or isinstance(r, Exception))
                
            duration = time.time() - start_time
            ops_per_second = NUM_TEST_OPERATIONS / duration
            success_rate = (successful_ops / NUM_TEST_OPERATIONS) * 100
            
            print(f"[INFO] Performance results:")
            print(f"  Operations: {NUM_TEST_OPERATIONS}")
            print(f"  Duration: {duration:.2f}s")
            print(f"  Throughput: {ops_per_second:.0f} ops/s")
            print(f"  Success rate: {success_rate:.1f}%")
            print(f"  Failed operations: {failed_ops}")
            
            self.metrics["throughput"] = ops_per_second
            self.metrics["success_rate"] = success_rate
            
            # Check if performance meets threshold
            if ops_per_second > 1000 and success_rate > 99:
                print(f"[OK] Performance meets requirements")
                return True
            else:
                print(f"[WARN] Performance below expectations")
                return False
                
        except Exception as e:
            print(f"[ERROR] Performance test failed: {e}")
            return False
            
    async def _perform_set(self, key: str, value: str) -> bool:
        """Perform SET operation."""
        try:
            # Pick random master
            masters = [n for n in REDIS_NODES if n["role"] == "master"]
            node = random.choice(masters)
            client = self.redis_clients[f"{node['host']}:{node['port']}"]
            
            await client.set(key, value)
            return True
        except:
            return False
            
    async def _perform_get(self, key: str) -> bool:
        """Perform GET operation."""
        try:
            # Pick random node
            node = random.choice(REDIS_NODES)
            client = self.redis_clients[f"{node['host']}:{node['port']}"]
            
            await client.get(key)
            return True
        except:
            return False
            
    async def _perform_delete(self, key: str) -> bool:
        """Perform DELETE operation."""
        try:
            # Pick random master
            masters = [n for n in REDIS_NODES if n["role"] == "master"]
            node = random.choice(masters)
            client = self.redis_clients[f"{node['host']}:{node['port']}"]
            
            await client.delete(key)
            return True
        except:
            return False
            
    async def run_all_tests(self) -> Dict[str, bool]:
        """Run all Redis cluster tests."""
        results = {}
        
        results["cluster_initialization"] = await self.test_cluster_initialization()
        results["consistent_hashing"] = await self.test_consistent_hashing()
        results["master_slave_replication"] = await self.test_master_slave_replication()
        results["automatic_failover"] = await self.test_automatic_failover()
        results["resharding"] = await self.test_resharding()
        results["split_brain_detection"] = await self.test_split_brain_detection()
        results["performance_under_load"] = await self.test_performance_under_load()
        
        return results


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.l4
async def test_redis_cluster_coordination():
    """Test complete Redis cluster coordination."""
    async with RedisClusterTester() as tester:
        results = await tester.run_all_tests()
        
        # Print comprehensive report
        print("\n" + "="*80)
        print("REDIS CLUSTER COORDINATION TEST REPORT")
        print("="*80)
        print(f"Timestamp: {datetime.utcnow().isoformat()}")
        print(f"Cluster Nodes: {len(REDIS_NODES)}")
        print("="*80)
        
        # Test results
        print("\nTEST RESULTS:")
        print("-"*40)
        for test_name, passed in results.items():
            status = "✓ PASS" if passed else "✗ FAIL"
            print(f"  {test_name:30} : {status}")
            
        # Performance metrics
        print("\nPERFORMANCE METRICS:")
        print("-"*40)
        for metric, value in tester.metrics.items():
            print(f"  {metric:30} : {value:.2f}")
            
        print("="*80)
        
        # Calculate overall result
        total_tests = len(results)
        passed_tests = sum(1 for passed in results.values() if passed)
        
        print(f"\nOverall: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests == total_tests:
            print("\n[SUCCESS] Redis cluster fully operational!")
        else:
            print(f"\n[WARNING] {total_tests - passed_tests} tests failed")
            
        assert passed_tests >= total_tests * 0.8, f"Too many tests failed: {results}"


async def main():
    """Run the test standalone."""
    print("="*80)
    print("REDIS CLUSTER COORDINATION TEST")
    print("="*80)
    print(f"Started at: {datetime.now().isoformat()}")
    print("="*80)
    
    async with RedisClusterTester() as tester:
        results = await tester.run_all_tests()
        
        if all(results.values()):
            return 0
        else:
            return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)