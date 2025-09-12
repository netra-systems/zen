"""
E2E GCP Staging Tests for UnifiedIDManager - FINAL PHASE
Real GCP Cloud SQL, performance at scale, and production ID generation

Business Value Protection:
- $500K+ ARR: Unique ID consistency prevents data corruption and system failures
- $15K+ MRR per Enterprise: High-performance ID generation for concurrent users
- Platform scalability: Distributed ID generation across GCP regions
- Data integrity: Prevents duplicate keys and referential integrity violations
"""

import asyncio
import pytest
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Set, Tuple
import psycopg2
from concurrent.futures import ThreadPoolExecutor
import threading
from collections import Counter, defaultdict

from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType, IDMetadata
from shared.isolated_environment import IsolatedEnvironment
from test_framework.ssot.base_test_case import SSotAsyncTestCase


class TestUnifiedIDManagerGCPStaging(SSotAsyncTestCase):
    """
    E2E GCP Staging tests for UnifiedIDManager protecting business value.
    Tests real GCP Cloud SQL performance, distributed generation, and production scale.
    """

    @classmethod
    async def asyncSetUpClass(cls):
        """Set up real GCP database services for ID testing."""
        await super().asyncSetUpClass()
        
        cls.env = IsolatedEnvironment()
        
        # Production ID generation configuration
        cls.id_config = IDConfig(
            enable_distributed_generation=True,
            generation_strategy=GenerationStrategy.HYBRID_UUID_SEQUENCE,
            distribution_mode=DistributionMode.GCP_REGIONAL,
            enable_collision_detection=True,
            enable_performance_monitoring=True,
            batch_generation_size=1000,
            max_concurrent_generators=50,
            enable_database_persistence=True,
            sequence_cache_size=10000,
            enable_cross_service_validation=True
        )
        
        # Initialize unified ID manager
        cls.id_manager = UnifiedIDManager(config=cls.id_config)
        
        # Real GCP Cloud SQL PostgreSQL connection
        cls.postgres_config = {
            'host': cls.env.get("POSTGRES_HOST", "postgres.cloud.google.com"),
            'port': int(cls.env.get("POSTGRES_PORT", 5432)),
            'database': cls.env.get("POSTGRES_DB", "netra_staging"),
            'user': cls.env.get("POSTGRES_USER", "netra_user"),
            'password': cls.env.get("POSTGRES_PASSWORD")
        }
        
        # Performance monitoring
        cls.performance_metrics = {
            "generation_times": [],
            "collision_counts": [],
            "throughput_measurements": [],
            "distribution_stats": defaultdict(int)
        }

    async def asyncTearDown(self):
        """Clean up test ID data from database."""
        # Clean test IDs from database
        try:
            with psycopg2.connect(**self.postgres_config) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("DELETE FROM id_generation_log WHERE test_session = %s", 
                                 (self.__class__.__name__,))
                    conn.commit()
        except Exception:
            pass  # Non-critical cleanup
        
        await super().asyncTearDown()

    @pytest.mark.e2e_gcp_staging
    @pytest.mark.high_difficulty
    async def test_distributed_id_generation_enterprise_scale(self):
        """
        HIGH DIFFICULTY: Test distributed ID generation at enterprise scale across GCP regions.
        
        Business Value: $15K+ MRR per Enterprise - supports massive concurrent user loads.
        Validates: Cross-region generation, collision avoidance, performance at scale.
        """
        # Simulate enterprise scale: 10,000 IDs generated concurrently across 5 regions
        gcp_regions = [
            "us-central1",    # Primary region  
            "us-east1",       # Secondary region
            "europe-west1",   # European region
            "asia-southeast1", # Asian region
            "australia-southeast1"  # Oceania region
        ]
        
        target_id_count = 10000
        batch_size = 200
        region_tasks = []
        
        # Configure distributed generators for each region
        for region in gcp_regions:
            region_generator = await self.id_manager.create_regional_generator(
                region=region,
                node_id=f"node_{region}_{int(time.time())}",
                shard_count=10,
                enable_local_caching=True
            )
            
            self.assertIsNotNone(region_generator, 
                               f"Failed to create generator for region {region}")
        
        # Generate IDs concurrently from all regions
        generation_start_time = time.time()
        
        for region in gcp_regions:
            region_task = self._generate_ids_for_region(
                region=region,
                id_count=target_id_count // len(gcp_regions),
                batch_size=batch_size,
                id_types=[IDType.USER, IDType.THREAD, IDType.RUN, IDType.EXECUTION]
            )
            region_tasks.append(region_task)
        
        # Execute all regional generation tasks concurrently
        region_results = await asyncio.gather(*region_tasks, return_exceptions=True)
        total_generation_time = time.time() - generation_start_time
        
        # Validate no exceptions occurred
        exceptions = [r for r in region_results if isinstance(r, Exception)]
        self.assertEqual(len(exceptions), 0, 
                        f"Distributed ID generation failures: {exceptions}")
        
        # Collect all generated IDs
        all_generated_ids = set()
        region_statistics = {}
        
        for i, result in enumerate(region_results):
            region = gcp_regions[i]
            region_ids = result["generated_ids"]
            generation_stats = result["stats"]
            
            all_generated_ids.update(region_ids)
            region_statistics[region] = {
                "ids_generated": len(region_ids),
                "avg_generation_time": generation_stats["avg_generation_time"],
                "collision_count": generation_stats["collision_count"],
                "throughput_per_second": generation_stats["throughput_per_second"]
            }
        
        # Validate enterprise-scale requirements
        total_ids_generated = len(all_generated_ids)
        self.assertGreater(total_ids_generated, target_id_count * 0.95, 
                          f"Insufficient IDs generated: {total_ids_generated}")
        
        # Performance requirement: Generate 10K IDs within 30 seconds
        self.assertLess(total_generation_time, 30.0, 
                       f"Distributed generation too slow: {total_generation_time}s")
        
        # Validate zero collisions across all regions
        expected_total = sum(stats["ids_generated"] for stats in region_statistics.values())
        self.assertEqual(total_ids_generated, expected_total, 
                        f"ID collisions detected: expected {expected_total}, got {total_ids_generated}")
        
        # Validate performance consistency across regions
        throughputs = [stats["throughput_per_second"] for stats in region_statistics.values()]
        min_throughput = min(throughputs)
        max_throughput = max(throughputs)
        throughput_variance = (max_throughput - min_throughput) / max_throughput
        
        # Regional performance should be within 30% variance
        self.assertLess(throughput_variance, 0.3, 
                       f"Excessive regional throughput variance: {throughput_variance}")
        
        # Test cross-region ID validation
        validation_sample = list(all_generated_ids)[:1000]  # Test subset
        
        cross_region_validation = await self.id_manager.validate_cross_region_consistency(
            id_list=validation_sample,
            regions=gcp_regions
        )
        
        self.assertTrue(cross_region_validation.get("consistent", False), 
                       "Cross-region ID consistency validation failed")
        self.assertEqual(cross_region_validation.get("conflicts", 0), 0, 
                        "Cross-region ID conflicts detected")

    async def _generate_ids_for_region(self, region: str, id_count: int, 
                                     batch_size: int, id_types: List[IDType]) -> Dict[str, Any]:
        """Helper method to generate IDs for a specific region."""
        generated_ids = set()
        generation_times = []
        collision_count = 0
        
        batches = (id_count + batch_size - 1) // batch_size
        
        for batch in range(batches):
            batch_start_time = time.time()
            batch_ids = []
            
            current_batch_size = min(batch_size, id_count - batch * batch_size)
            
            for i in range(current_batch_size):
                id_type = id_types[i % len(id_types)]
                
                try:
                    new_id = await self.id_manager.generate_id(
                        id_type=id_type,
                        region=region,
                        enable_collision_check=True
                    )
                    
                    if new_id in generated_ids:
                        collision_count += 1
                    else:
                        generated_ids.add(new_id)
                        batch_ids.append(new_id)
                        
                except Exception as e:
                    # Log error but continue generation
                    print(f"ID generation error in {region}: {e}")
                    collision_count += 1
            
            batch_time = time.time() - batch_start_time
            generation_times.append(batch_time)
            
            # Brief pause between batches to avoid overwhelming the system
            if batch < batches - 1:
                await asyncio.sleep(0.01)
        
        avg_generation_time = sum(generation_times) / len(generation_times)
        throughput_per_second = id_count / sum(generation_times) if generation_times else 0
        
        return {
            "generated_ids": generated_ids,
            "stats": {
                "avg_generation_time": avg_generation_time,
                "collision_count": collision_count,
                "throughput_per_second": throughput_per_second,
                "total_batches": batches
            }
        }

    @pytest.mark.e2e_gcp_staging
    @pytest.mark.high_difficulty
    async def test_cloud_sql_sequence_performance_scaling(self):
        """
        HIGH DIFFICULTY: Test Cloud SQL sequence performance under production load.
        
        Business Value: $500K+ ARR - database performance directly impacts user experience.
        Validates: Sequence generation, connection pooling, transaction isolation.
        """
        # Test various sequence types used in production
        sequence_types = [
            {"name": "user_sequence", "start": 1000000, "increment": 1, "cache": 100},
            {"name": "thread_sequence", "start": 2000000, "increment": 1, "cache": 500},
            {"name": "run_sequence", "start": 3000000, "increment": 1, "cache": 1000},
            {"name": "execution_sequence", "start": 4000000, "increment": 1, "cache": 2000},
            {"name": "message_sequence", "start": 5000000, "increment": 1, "cache": 5000}
        ]
        
        # Initialize all sequences in Cloud SQL
        sequence_initialization = await self.id_manager.initialize_sequences(
            sequences=sequence_types,
            database_host=self.postgres_config['host'],
            connection_pool_size=20,
            max_connections=100
        )
        
        self.assertTrue(sequence_initialization.get("success", False), 
                       "Sequence initialization failed")
        
        # Test concurrent sequence generation at production scale
        concurrent_clients = 50
        sequences_per_client = 1000
        
        client_tasks = []
        
        for client_id in range(concurrent_clients):
            client_task = self._test_sequence_client(
                client_id=client_id,
                sequences_to_generate=sequences_per_client,
                sequence_types=[seq["name"] for seq in sequence_types],
                enable_transaction_isolation=True
            )
            client_tasks.append(client_task)
        
        # Execute concurrent sequence generation
        concurrent_start_time = time.time()
        client_results = await asyncio.gather(*client_tasks, return_exceptions=True)
        total_concurrent_time = time.time() - concurrent_start_time
        
        # Validate concurrent execution results
        successful_clients = [r for r in client_results if not isinstance(r, Exception)]
        self.assertEqual(len(successful_clients), concurrent_clients, 
                        f"Client failures: {len(client_results) - len(successful_clients)}")
        
        # Collect all generated sequence numbers
        all_sequences = defaultdict(list)
        total_sequences_generated = 0
        
        for client_result in successful_clients:
            for seq_name, seq_numbers in client_result["sequences"].items():
                all_sequences[seq_name].extend(seq_numbers)
                total_sequences_generated += len(seq_numbers)
        
        # Validate sequence uniqueness and ordering
        for seq_name, seq_numbers in all_sequences.items():
            # All sequence numbers should be unique
            unique_count = len(set(seq_numbers))
            total_count = len(seq_numbers)
            self.assertEqual(unique_count, total_count, 
                           f"Duplicate sequence numbers in {seq_name}: {total_count - unique_count}")
            
            # Sequence numbers should be within expected range
            seq_config = next(s for s in sequence_types if s["name"] == seq_name)
            expected_min = seq_config["start"]
            expected_max = seq_config["start"] + total_count * seq_config["increment"] + 10000
            
            self.assertGreaterEqual(min(seq_numbers), expected_min, 
                                   f"Sequence {seq_name} below expected range")
            self.assertLessEqual(max(seq_numbers), expected_max, 
                                f"Sequence {seq_name} above expected range")
        
        # Performance validation
        expected_total = concurrent_clients * sequences_per_client * len(sequence_types)
        self.assertEqual(total_sequences_generated, expected_total, 
                        "Incorrect total sequence count")
        
        # Throughput requirement: >1000 sequences/second
        throughput = total_sequences_generated / total_concurrent_time
        self.assertGreater(throughput, 1000, 
                          f"Sequence generation throughput too low: {throughput}/sec")
        
        # Test sequence state recovery after connection failure
        recovery_test_sequences = ["user_sequence", "thread_sequence"]
        
        # Simulate connection failure and recovery
        recovery_start_time = time.time()
        
        for seq_name in recovery_test_sequences:
            # Generate sequences before "failure"
            pre_failure_sequences = await self.id_manager.generate_sequence_batch(
                sequence_name=seq_name,
                batch_size=100
            )
            
            # Simulate connection reset
            await self.id_manager.reset_database_connections()
            
            # Generate sequences after "recovery"
            post_recovery_sequences = await self.id_manager.generate_sequence_batch(
                sequence_name=seq_name,
                batch_size=100
            )
            
            # Validate continuity - no gaps or overlaps
            pre_max = max(pre_failure_sequences)
            post_min = min(post_recovery_sequences)
            
            self.assertLess(pre_max, post_min, 
                           f"Sequence {seq_name} continuity broken after recovery")
        
        recovery_time = time.time() - recovery_start_time
        
        # Recovery should complete within 10 seconds
        self.assertLess(recovery_time, 10.0, 
                       f"Sequence recovery too slow: {recovery_time}s")

    async def _test_sequence_client(self, client_id: int, sequences_to_generate: int, 
                                  sequence_types: List[str], enable_transaction_isolation: bool) -> Dict[str, Any]:
        """Helper method to simulate concurrent sequence generation client."""
        client_sequences = defaultdict(list)
        generation_times = []
        
        for i in range(sequences_to_generate):
            seq_type = sequence_types[i % len(sequence_types)]
            
            generation_start = time.time()
            
            try:
                seq_number = await self.id_manager.get_next_sequence(
                    sequence_name=seq_type,
                    client_id=f"client_{client_id}",
                    transaction_isolation=enable_transaction_isolation
                )
                
                client_sequences[seq_type].append(seq_number)
                
            except Exception as e:
                print(f"Client {client_id} sequence generation error: {e}")
                continue
            
            generation_time = time.time() - generation_start
            generation_times.append(generation_time)
            
            # Small random delay to simulate realistic usage patterns
            if i % 100 == 0:  # Periodic pause
                await asyncio.sleep(0.001)
        
        return {
            "client_id": client_id,
            "sequences": dict(client_sequences),
            "avg_generation_time": sum(generation_times) / len(generation_times) if generation_times else 0,
            "total_generated": sum(len(seq_list) for seq_list in client_sequences.values())
        }

    @pytest.mark.e2e_gcp_staging
    @pytest.mark.high_difficulty
    async def test_hybrid_uuid_sequence_collision_detection(self):
        """
        HIGH DIFFICULTY: Test hybrid UUID-sequence collision detection at massive scale.
        
        Business Value: Data integrity - prevents corrupted references and system failures.
        Validates: Collision detection algorithms, performance impact, accuracy.
        """
        # Generate massive dataset to stress collision detection
        test_scenarios = [
            {
                "name": "uuid_only_generation",
                "strategy": GenerationStrategy.UUID_ONLY,
                "count": 50000,
                "expected_collision_rate": 0.0
            },
            {
                "name": "sequence_only_generation", 
                "strategy": GenerationStrategy.SEQUENCE_ONLY,
                "count": 50000,
                "expected_collision_rate": 0.0
            },
            {
                "name": "hybrid_generation",
                "strategy": GenerationStrategy.HYBRID_UUID_SEQUENCE,
                "count": 100000,
                "expected_collision_rate": 0.0
            },
            {
                "name": "timestamp_based_generation",
                "strategy": GenerationStrategy.TIMESTAMP_BASED,
                "count": 75000,
                "expected_collision_rate": 0.0001  # Minimal collision rate acceptable
            }
        ]
        
        collision_test_results = []
        
        for scenario in test_scenarios:
            scenario_start_time = time.time()
            
            # Configure ID manager for specific strategy
            scenario_config = IDConfig(
                generation_strategy=scenario["strategy"],
                enable_collision_detection=True,
                collision_detection_algorithm="bloom_filter_plus_hash",
                collision_check_batch_size=10000,
                enable_statistical_analysis=True
            )
            
            scenario_id_manager = UnifiedIDManager(config=scenario_config)
            
            # Generate IDs with collision detection
            generated_ids = set()
            detected_collisions = []
            generation_times = []
            
            batch_size = 5000
            batches = (scenario["count"] + batch_size - 1) // batch_size
            
            for batch_num in range(batches):
                batch_start = time.time()
                current_batch_size = min(batch_size, scenario["count"] - batch_num * batch_size)
                
                batch_tasks = []
                for i in range(current_batch_size):
                    task = scenario_id_manager.generate_id_with_collision_check(
                        id_type=IDType.EXECUTION,  # Most collision-prone type
                        existing_ids=generated_ids if len(generated_ids) < 10000 else None,
                        enable_deep_check=True
                    )
                    batch_tasks.append(task)
                
                # Execute batch generation
                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                
                # Process batch results
                for result in batch_results:
                    if isinstance(result, Exception):
                        print(f"ID generation error in {scenario['name']}: {result}")
                        continue
                    
                    new_id = result.get("id")
                    collision_detected = result.get("collision_detected", False)
                    
                    if collision_detected:
                        detected_collisions.append({
                            "id": new_id,
                            "collision_type": result.get("collision_type"),
                            "collision_with": result.get("collision_with")
                        })
                    
                    if new_id and new_id not in generated_ids:
                        generated_ids.add(new_id)
                
                batch_time = time.time() - batch_start
                generation_times.append(batch_time)
                
                # Progress monitoring
                if batch_num % 10 == 0:
                    progress = (batch_num + 1) / batches * 100
                    print(f"Scenario {scenario['name']}: {progress:.1f}% complete")
            
            scenario_total_time = time.time() - scenario_start_time
            
            # Calculate collision statistics
            actual_collision_rate = len(detected_collisions) / scenario["count"]
            unique_ids_generated = len(generated_ids)
            theoretical_max_ids = scenario["count"]
            uniqueness_rate = unique_ids_generated / theoretical_max_ids
            
            # Validate collision detection accuracy
            self.assertLessEqual(actual_collision_rate, scenario["expected_collision_rate"] * 2, 
                               f"Collision rate too high for {scenario['name']}: {actual_collision_rate}")
            
            # Validate ID uniqueness
            self.assertGreater(uniqueness_rate, 0.999, 
                             f"Insufficient uniqueness for {scenario['name']}: {uniqueness_rate}")
            
            # Performance validation - collision detection should not significantly slow generation
            avg_generation_time = sum(generation_times) / len(generation_times)
            throughput = scenario["count"] / scenario_total_time
            
            # Should maintain >500 IDs/second even with collision detection
            self.assertGreater(throughput, 500, 
                             f"Collision detection slowing generation too much for {scenario['name']}: {throughput}/sec")
            
            collision_test_results.append({
                "scenario": scenario["name"],
                "strategy": scenario["strategy"].value,
                "total_time": scenario_total_time,
                "unique_ids": unique_ids_generated,
                "detected_collisions": len(detected_collisions),
                "collision_rate": actual_collision_rate,
                "uniqueness_rate": uniqueness_rate,
                "throughput": throughput,
                "avg_batch_time": avg_generation_time
            })
        
        # Test collision detection with intentionally duplicated IDs
        duplicate_detection_test = await self.id_manager.test_collision_detection_accuracy(
            test_set_size=10000,
            duplicate_injection_rate=0.01,  # 1% intentional duplicates
            detection_algorithms=["bloom_filter", "hash_set", "database_check"]
        )
        
        self.assertTrue(duplicate_detection_test.get("test_passed", False), 
                       "Collision detection accuracy test failed")
        
        # Detection accuracy should be >99.9%
        detection_accuracy = duplicate_detection_test.get("detection_accuracy", 0)
        self.assertGreater(detection_accuracy, 0.999, 
                          f"Collision detection accuracy too low: {detection_accuracy}")
        
        # False positive rate should be <0.1%
        false_positive_rate = duplicate_detection_test.get("false_positive_rate", 1)
        self.assertLess(false_positive_rate, 0.001, 
                       f"False positive rate too high: {false_positive_rate}")

    @pytest.mark.e2e_gcp_staging
    async def test_cross_service_id_validation_comprehensive(self):
        """
        Test cross-service ID validation and consistency.
        
        Business Value: System integrity - prevents orphaned references across services.
        Validates: Service boundary validation, referential integrity, consistency.
        """
        # Create IDs across multiple service boundaries
        service_boundaries = [
            {
                "service": "netra_backend",
                "id_types": [IDType.USER, IDType.THREAD, IDType.RUN],
                "namespace": "backend"
            },
            {
                "service": "auth_service",
                "id_types": [IDType.USER, IDType.SESSION],
                "namespace": "auth"
            },
            {
                "service": "analytics_service",
                "id_types": [IDType.EXECUTION, IDType.METRIC],
                "namespace": "analytics"
            }
        ]
        
        cross_service_ids = defaultdict(lambda: defaultdict(list))
        
        # Generate IDs for each service boundary
        for service in service_boundaries:
            for id_type in service["id_types"]:
                for i in range(100):  # 100 IDs per type per service
                    new_id = await self.id_manager.generate_id(
                        id_type=id_type,
                        service_namespace=service["namespace"],
                        enable_cross_service_validation=True
                    )
                    
                    cross_service_ids[service["service"]][id_type.value].append(new_id)
        
        # Test cross-service validation
        validation_scenarios = [
            {
                "name": "user_id_consistency",
                "primary_service": "netra_backend",
                "secondary_service": "auth_service",
                "id_type": IDType.USER,
                "validation_type": "shared_reference"
            },
            {
                "name": "execution_id_isolation",
                "primary_service": "netra_backend", 
                "secondary_service": "analytics_service",
                "id_type": IDType.EXECUTION,
                "validation_type": "namespace_isolation"
            },
            {
                "name": "thread_id_boundary",
                "primary_service": "netra_backend",
                "secondary_service": "auth_service",
                "id_type": IDType.THREAD,
                "validation_type": "boundary_enforcement"
            }
        ]
        
        validation_results = []
        
        for scenario in validation_scenarios:
            primary_ids = cross_service_ids[scenario["primary_service"]][scenario["id_type"].value]
            secondary_ids = cross_service_ids.get(scenario["secondary_service"], {}).get(scenario["id_type"].value, [])
            
            if scenario["validation_type"] == "shared_reference":
                # For shared references (like USER IDs), validate consistency
                validation_result = await self.id_manager.validate_shared_reference_consistency(
                    id_type=scenario["id_type"],
                    primary_service_ids=primary_ids[:50],  # Test subset
                    secondary_service_ids=secondary_ids[:50],
                    consistency_requirement="exact_match"
                )
                
                # Shared USER IDs should be consistent across services
                if scenario["id_type"] == IDType.USER:
                    self.assertTrue(validation_result.get("consistent", False), 
                                   "User ID consistency validation failed")
            
            elif scenario["validation_type"] == "namespace_isolation":
                # For isolated namespaces, validate no overlap
                validation_result = await self.id_manager.validate_namespace_isolation(
                    primary_namespace=scenario["primary_service"],
                    secondary_namespace=scenario["secondary_service"],
                    id_type=scenario["id_type"],
                    primary_ids=primary_ids,
                    secondary_ids=secondary_ids
                )
                
                # Different services should have isolated ID spaces
                overlap_count = validation_result.get("overlap_count", 0)
                self.assertEqual(overlap_count, 0, 
                               f"Namespace isolation violation: {overlap_count} overlapping IDs")
            
            elif scenario["validation_type"] == "boundary_enforcement":
                # For boundary enforcement, validate proper access controls
                validation_result = await self.id_manager.validate_service_boundary(
                    requesting_service=scenario["secondary_service"],
                    target_id_type=scenario["id_type"],
                    target_namespace=scenario["primary_service"],
                    access_type="read"
                )
                
                # Cross-service access should be properly controlled
                if scenario["id_type"] == IDType.THREAD:
                    # auth_service should not have direct access to backend thread IDs
                    self.assertFalse(validation_result.get("access_allowed", True), 
                                   "Service boundary violation: unauthorized access allowed")
            
            validation_results.append({
                "scenario": scenario["name"],
                "validation_passed": validation_result.get("consistent", False) or 
                                   validation_result.get("isolated", False) or
                                   not validation_result.get("access_allowed", True),
                "details": validation_result
            })
        
        # Overall cross-service validation success rate should be 100%
        successful_validations = sum(1 for r in validation_results if r["validation_passed"])
        validation_success_rate = successful_validations / len(validation_results)
        
        self.assertEqual(validation_success_rate, 1.0, 
                        f"Cross-service validation failures detected: {1 - validation_success_rate}")
        
        # Test referential integrity across services
        integrity_test_scenarios = [
            {
                "parent_service": "netra_backend",
                "parent_id_type": IDType.USER,
                "child_service": "netra_backend", 
                "child_id_type": IDType.THREAD,
                "relationship": "one_to_many"
            },
            {
                "parent_service": "netra_backend",
                "parent_id_type": IDType.THREAD,
                "child_service": "netra_backend",
                "child_id_type": IDType.RUN,
                "relationship": "one_to_many"
            },
            {
                "parent_service": "netra_backend",
                "parent_id_type": IDType.RUN,
                "child_service": "analytics_service",
                "child_id_type": IDType.EXECUTION,
                "relationship": "one_to_one"
            }
        ]
        
        for integrity_scenario in integrity_test_scenarios:
            parent_ids = cross_service_ids[integrity_scenario["parent_service"]][integrity_scenario["parent_id_type"].value]
            
            # Create child references for parent IDs
            child_references = []
            for parent_id in parent_ids[:20]:  # Test subset
                if integrity_scenario["relationship"] == "one_to_many":
                    # Create multiple child references
                    for i in range(3):
                        child_id = await self.id_manager.generate_id(
                            id_type=integrity_scenario["child_id_type"],
                            parent_reference=parent_id,
                            service_namespace=integrity_scenario["child_service"]
                        )
                        child_references.append((parent_id, child_id))
                else:
                    # Create single child reference
                    child_id = await self.id_manager.generate_id(
                        id_type=integrity_scenario["child_id_type"],
                        parent_reference=parent_id,
                        service_namespace=integrity_scenario["child_service"]
                    )
                    child_references.append((parent_id, child_id))
            
            # Validate referential integrity
            integrity_check = await self.id_manager.validate_referential_integrity(
                parent_child_pairs=child_references,
                parent_service=integrity_scenario["parent_service"],
                child_service=integrity_scenario["child_service"]
            )
            
            self.assertTrue(integrity_check.get("integrity_valid", False), 
                           f"Referential integrity check failed for {integrity_scenario['parent_id_type'].value} -> {integrity_scenario['child_id_type'].value}")
            
            # No orphaned references should exist
            orphaned_count = integrity_check.get("orphaned_references", 0)
            self.assertEqual(orphaned_count, 0, 
                           f"Orphaned references detected: {orphaned_count}")

    @pytest.mark.e2e_gcp_staging
    async def test_id_format_consistency_migration_compatibility(self):
        """
        Test ID format consistency and migration compatibility.
        
        Business Value: System evolution - supports gradual migration to new ID formats.
        Validates: Format validation, backward compatibility, migration paths.
        """
        # Test various ID format scenarios
        id_format_scenarios = [
            {
                "format_name": "legacy_uuid4",
                "pattern": r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
                "generation_method": "uuid4",
                "compatibility_level": "full"
            },
            {
                "format_name": "prefixed_uuid",
                "pattern": r"^(user|thread|run|exec)_[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
                "generation_method": "prefixed_uuid4",
                "compatibility_level": "backward"
            },
            {
                "format_name": "short_id_base62", 
                "pattern": r"^[0-9a-zA-Z]{8,12}$",
                "generation_method": "base62_encoded",
                "compatibility_level": "forward"
            },
            {
                "format_name": "timestamp_hybrid",
                "pattern": r"^[0-9]{13}_[0-9a-f]{8}$",
                "generation_method": "timestamp_plus_random",
                "compatibility_level": "limited"
            },
            {
                "format_name": "sequential_with_checksum",
                "pattern": r"^[0-9]{8}_[0-9a-f]{2}$",
                "generation_method": "sequence_plus_checksum",
                "compatibility_level": "none"
            }
        ]
        
        format_test_results = []
        
        for scenario in id_format_scenarios:
            scenario_start_time = time.time()
            
            # Configure ID manager for specific format
            format_config = IDConfig(
                id_format=scenario["format_name"],
                enable_format_validation=True,
                enable_migration_compatibility=True,
                backward_compatibility_level=scenario["compatibility_level"]
            )
            
            format_id_manager = UnifiedIDManager(config=format_config)
            
            # Generate IDs in specified format
            generated_ids = []
            format_violations = []
            
            for i in range(1000):
                try:
                    new_id = await format_id_manager.generate_formatted_id(
                        id_type=IDType.EXECUTION,
                        format_method=scenario["generation_method"],
                        validate_format=True
                    )
                    
                    # Validate format against pattern
                    import re
                    if re.match(scenario["pattern"], new_id):
                        generated_ids.append(new_id)
                    else:
                        format_violations.append({
                            "id": new_id,
                            "expected_pattern": scenario["pattern"],
                            "violation_type": "pattern_mismatch"
                        })
                        
                except Exception as e:
                    format_violations.append({
                        "error": str(e),
                        "violation_type": "generation_error"
                    })
            
            # Validate format consistency
            format_consistency_rate = len(generated_ids) / (len(generated_ids) + len(format_violations))
            self.assertGreater(format_consistency_rate, 0.99, 
                             f"Format consistency too low for {scenario['format_name']}: {format_consistency_rate}")
            
            # Test format validation function
            validation_sample = generated_ids[:100]
            validation_results = []
            
            for test_id in validation_sample:
                validation_result = await format_id_manager.validate_id_format(
                    id_value=test_id,
                    expected_format=scenario["format_name"],
                    strict_validation=True
                )
                validation_results.append(validation_result.get("valid", False))
            
            validation_success_rate = sum(validation_results) / len(validation_results)
            self.assertGreater(validation_success_rate, 0.99, 
                             f"ID format validation failing for {scenario['format_name']}")
            
            scenario_time = time.time() - scenario_start_time
            
            format_test_results.append({
                "format_name": scenario["format_name"],
                "generation_time": scenario_time,
                "ids_generated": len(generated_ids),
                "format_violations": len(format_violations),
                "consistency_rate": format_consistency_rate,
                "validation_success_rate": validation_success_rate
            })
        
        # Test cross-format compatibility and migration
        migration_test_scenarios = [
            {
                "source_format": "legacy_uuid4",
                "target_format": "prefixed_uuid",
                "migration_type": "gradual",
                "compatibility_required": True
            },
            {
                "source_format": "prefixed_uuid",
                "target_format": "short_id_base62",
                "migration_type": "mapping_based",
                "compatibility_required": True
            },
            {
                "source_format": "timestamp_hybrid",
                "target_format": "sequential_with_checksum",
                "migration_type": "conversion",
                "compatibility_required": False
            }
        ]
        
        migration_results = []
        
        for migration_scenario in migration_test_scenarios:
            migration_start_time = time.time()
            
            # Generate source format IDs
            source_ids = []
            source_config = IDConfig(id_format=migration_scenario["source_format"])
            source_manager = UnifiedIDManager(config=source_config)
            
            for i in range(500):
                source_id = await source_manager.generate_formatted_id(
                    id_type=IDType.USER,
                    format_method="legacy_uuid4" if "uuid" in migration_scenario["source_format"] else "default"
                )
                source_ids.append(source_id)
            
            # Test migration to target format
            target_config = IDConfig(id_format=migration_scenario["target_format"])
            target_manager = UnifiedIDManager(config=target_config)
            
            migration_results_batch = await target_manager.migrate_id_format(
                source_ids=source_ids,
                source_format=migration_scenario["source_format"],
                target_format=migration_scenario["target_format"],
                migration_strategy=migration_scenario["migration_type"],
                preserve_references=migration_scenario["compatibility_required"]
            )
            
            migration_success_rate = migration_results_batch.get("success_rate", 0)
            migrated_ids = migration_results_batch.get("migrated_ids", [])
            migration_errors = migration_results_batch.get("errors", [])
            
            # Validate migration success
            if migration_scenario["compatibility_required"]:
                self.assertGreater(migration_success_rate, 0.95, 
                                 f"Migration success rate too low for {migration_scenario['source_format']} -> {migration_scenario['target_format']}")
            
            # Validate migrated ID format
            if migrated_ids:
                target_pattern = next(s["pattern"] for s in id_format_scenarios 
                                    if s["format_name"] == migration_scenario["target_format"])
                
                format_compliance_count = 0
                for migrated_id in migrated_ids[:50]:  # Test subset
                    import re
                    if re.match(target_pattern, migrated_id):
                        format_compliance_count += 1
                
                format_compliance_rate = format_compliance_count / min(50, len(migrated_ids))
                self.assertGreater(format_compliance_rate, 0.95, 
                                 f"Migrated ID format compliance too low: {format_compliance_rate}")
            
            migration_time = time.time() - migration_start_time
            
            migration_results.append({
                "migration_scenario": f"{migration_scenario['source_format']} -> {migration_scenario['target_format']}",
                "migration_time": migration_time,
                "source_ids_count": len(source_ids),
                "migrated_ids_count": len(migrated_ids),
                "success_rate": migration_success_rate,
                "error_count": len(migration_errors)
            })
        
        # Validate overall migration capability
        overall_migration_success = sum(r["success_rate"] for r in migration_results) / len(migration_results)
        self.assertGreater(overall_migration_success, 0.9, 
                          f"Overall migration capability insufficient: {overall_migration_success}")

    @pytest.mark.e2e_gcp_staging
    async def test_id_performance_monitoring_analytics(self):
        """
        Test ID generation performance monitoring and analytics.
        
        Business Value: Operational excellence - enables performance optimization.
        Validates: Metrics collection, performance analysis, alerting.
        """
        # Enable comprehensive performance monitoring
        monitoring_config = await self.id_manager.enable_performance_monitoring(
            metrics_collection_level="detailed",
            sampling_rate=1.0,  # 100% sampling for test
            enable_real_time_analytics=True,
            enable_alerting=True,
            retention_days=30
        )
        
        self.assertTrue(monitoring_config.get("enabled", False), 
                       "Performance monitoring configuration failed")
        
        # Generate load with various patterns to test monitoring
        performance_test_scenarios = [
            {
                "name": "steady_load",
                "duration_seconds": 30,
                "requests_per_second": 100,
                "id_types": [IDType.USER, IDType.THREAD],
                "concurrency": 10
            },
            {
                "name": "burst_load",
                "duration_seconds": 15,
                "requests_per_second": 500,
                "id_types": [IDType.EXECUTION, IDType.RUN],
                "concurrency": 50
            },
            {
                "name": "mixed_load",
                "duration_seconds": 60,
                "requests_per_second": 200,
                "id_types": [IDType.USER, IDType.THREAD, IDType.RUN, IDType.EXECUTION],
                "concurrency": 25
            }
        ]
        
        monitoring_results = []
        
        for scenario in performance_test_scenarios:
            scenario_start_time = time.time()
            
            # Start performance monitoring for this scenario
            monitoring_session = await self.id_manager.start_monitoring_session(
                session_name=scenario["name"],
                expected_duration=scenario["duration_seconds"],
                expected_load=scenario["requests_per_second"]
            )
            
            # Generate load according to scenario
            total_requests = scenario["duration_seconds"] * scenario["requests_per_second"]
            batch_size = scenario["concurrency"]
            batches = (total_requests + batch_size - 1) // batch_size
            
            generated_ids = []
            performance_metrics = []
            
            for batch_num in range(batches):
                batch_start_time = time.time()
                
                # Create batch of concurrent ID generation tasks
                batch_tasks = []
                current_batch_size = min(batch_size, total_requests - batch_num * batch_size)
                
                for i in range(current_batch_size):
                    id_type = scenario["id_types"][i % len(scenario["id_types"])]
                    task = self.id_manager.generate_id(
                        id_type=id_type,
                        enable_performance_tracking=True
                    )
                    batch_tasks.append(task)
                
                # Execute batch
                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                batch_time = time.time() - batch_start_time
                
                # Process results
                successful_ids = [r for r in batch_results if not isinstance(r, Exception)]
                generated_ids.extend(successful_ids)
                
                # Record batch performance
                performance_metrics.append({
                    "batch_number": batch_num,
                    "batch_time": batch_time,
                    "batch_size": current_batch_size,
                    "successful_generations": len(successful_ids),
                    "batch_throughput": len(successful_ids) / batch_time if batch_time > 0 else 0
                })
                
                # Maintain target rate
                expected_batch_time = current_batch_size / scenario["requests_per_second"]
                if batch_time < expected_batch_time:
                    await asyncio.sleep(expected_batch_time - batch_time)
            
            scenario_total_time = time.time() - scenario_start_time
            
            # Stop monitoring session and get metrics
            monitoring_summary = await self.id_manager.stop_monitoring_session(
                session_id=monitoring_session["session_id"]
            )
            
            # Validate monitoring data
            self.assertTrue(monitoring_summary.get("session_completed", False), 
                           f"Monitoring session failed for {scenario['name']}")
            
            session_metrics = monitoring_summary.get("metrics", {})
            
            # Validate key performance metrics are captured
            required_metrics = [
                "total_requests", "successful_requests", "failed_requests",
                "average_response_time", "p95_response_time", "p99_response_time",
                "throughput_per_second", "error_rate"
            ]
            
            for metric in required_metrics:
                self.assertIn(metric, session_metrics, 
                             f"Missing performance metric: {metric}")
            
            # Validate metric accuracy
            expected_requests = len(generated_ids)
            actual_requests = session_metrics.get("successful_requests", 0)
            
            # Allow 5% variance due to timing
            request_accuracy = abs(actual_requests - expected_requests) / expected_requests
            self.assertLess(request_accuracy, 0.05, 
                           f"Performance monitoring request count inaccurate for {scenario['name']}")
            
            # Validate throughput calculation
            expected_throughput = expected_requests / scenario_total_time
            actual_throughput = session_metrics.get("throughput_per_second", 0)
            
            throughput_accuracy = abs(actual_throughput - expected_throughput) / expected_throughput
            self.assertLess(throughput_accuracy, 0.1, 
                           f"Performance monitoring throughput calculation inaccurate for {scenario['name']}")
            
            monitoring_results.append({
                "scenario": scenario["name"],
                "duration": scenario_total_time,
                "expected_requests": expected_requests,
                "actual_requests": actual_requests,
                "expected_throughput": expected_throughput,
                "actual_throughput": actual_throughput,
                "monitoring_accuracy": 1 - request_accuracy,
                "session_metrics": session_metrics
            })
        
        # Test performance analytics and alerting
        analytics_test_start = time.time()
        
        # Generate analytics report
        performance_analytics = await self.id_manager.generate_performance_analytics(
            time_range_minutes=120,  # Cover all test scenarios
            include_trends=True,
            include_anomalies=True,
            include_recommendations=True
        )
        
        analytics_generation_time = time.time() - analytics_test_start
        
        self.assertTrue(performance_analytics.get("success", False), 
                       "Performance analytics generation failed")
        
        # Validate analytics content
        analytics_data = performance_analytics.get("analytics", {})
        
        required_analytics_sections = [
            "performance_summary", "trend_analysis", "anomaly_detection", 
            "capacity_planning", "optimization_recommendations"
        ]
        
        for section in required_analytics_sections:
            self.assertIn(section, analytics_data, 
                         f"Missing analytics section: {section}")
        
        # Validate trend analysis
        trend_data = analytics_data.get("trend_analysis", {})
        self.assertIn("throughput_trend", trend_data, "Missing throughput trend analysis")
        self.assertIn("response_time_trend", trend_data, "Missing response time trend analysis")
        
        # Validate anomaly detection
        anomalies = analytics_data.get("anomaly_detection", {}).get("anomalies", [])
        # Should detect some anomalies during burst load scenario
        burst_anomalies = [a for a in anomalies if "burst_load" in a.get("context", "")]
        self.assertGreater(len(burst_anomalies), 0, 
                          "Anomaly detection should have identified burst load patterns")
        
        # Validate optimization recommendations
        recommendations = analytics_data.get("optimization_recommendations", [])
        self.assertGreater(len(recommendations), 0, 
                          "No optimization recommendations generated")
        
        # Test alerting system
        alert_test_result = await self.id_manager.test_performance_alerting(
            alert_conditions={
                "throughput_drop_percentage": 50,
                "response_time_increase_percentage": 200,
                "error_rate_threshold": 0.05
            },
            test_duration_seconds=30
        )
        
        self.assertTrue(alert_test_result.get("alerting_functional", False), 
                       "Performance alerting system not functional")
        
        # Analytics should be generated quickly for operational use
        self.assertLess(analytics_generation_time, 10.0, 
                       f"Performance analytics generation too slow: {analytics_generation_time}s")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])