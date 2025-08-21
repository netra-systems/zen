"""Service Mesh Routing and Load Balancing Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal (infrastructure reliability for all tiers)
- Business Goal: Effective load distribution and traffic routing
- Value Impact: Ensures optimal resource utilization and response times
- Strategic Impact: $3K MRR protection through routing efficiency

Critical Path: Instance selection -> Load distribution -> Algorithm effectiveness -> Zone awareness
Coverage: Load balancing algorithms, traffic distribution, zone affinity
L4 Realism: Tests against staging service mesh infrastructure with real microservices
"""

import pytest
import asyncio
import time
import logging
import random
from typing import Dict, List, Optional, Any

# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

from netra_backend.tests.service_mesh_fixtures import service_mesh_l4, calculate_backoff_accuracy

# Add project root to path

logger = logging.getLogger(__name__)

# L4 Staging environment markers
pytestmark = [
    pytest.mark.l4,
    pytest.mark.staging,
    pytest.mark.service_mesh,
    pytest.mark.slow
]


class LoadBalancingL4Tests:
    """Load balancing specific test implementations."""
    
    async def test_load_balancing_algorithms_l4(self, manager, service_name: str) -> Dict[str, Any]:
        """Test load balancing algorithms with L4 realism."""
        try:
            if service_name not in manager.staging_services:
                return {"success": False, "error": f"Service {service_name} not available"}
            
            service_config = manager.staging_services[service_name]
            instances = service_config["instances"]
            
            if len(instances) < 2:
                return {"success": False, "error": "Need at least 2 instances for load balancing test"}
            
            load_balancing_results = {
                "round_robin": await self.test_round_robin_lb(manager, service_name, instances),
                "weighted_round_robin": await self.test_weighted_round_robin_lb(manager, service_name, instances),
                "least_connections": await self.test_least_connections_lb(manager, service_name, instances),
                "random": await self.test_random_lb(manager, service_name, instances),
                "zone_aware": await self.test_zone_aware_lb(manager, service_name, instances)
            }
            
            # Analyze load distribution
            distribution_analysis = self.analyze_load_distribution(load_balancing_results)
            
            manager.load_balancing_results.append({
                "service_name": service_name,
                "algorithms_tested": list(load_balancing_results.keys()),
                "results": load_balancing_results,
                "distribution_analysis": distribution_analysis,
                "timestamp": time.time()
            })
            
            successful_algorithms = [alg for alg, result in load_balancing_results.items() if result["success"]]
            
            return {
                "success": len(successful_algorithms) > 0,
                "service_name": service_name,
                "algorithms_tested": len(load_balancing_results),
                "successful_algorithms": len(successful_algorithms),
                "load_balancing_results": load_balancing_results,
                "distribution_analysis": distribution_analysis
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def test_round_robin_lb(self, manager, service_name: str, instances: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Test round-robin load balancing."""
        try:
            requests_per_instance = {}
            total_requests = 20
            
            for i in range(total_requests):
                # Get next instance using round-robin
                selected_instance = await manager.load_balancer.select_instance(
                    service_name, algorithm="round_robin", instances=instances
                )
                
                if selected_instance["success"]:
                    instance_id = selected_instance["instance"]["instance_id"]
                    requests_per_instance[instance_id] = requests_per_instance.get(instance_id, 0) + 1
                    
                    # Make actual request to test connectivity
                    request_result = await manager.make_test_request(selected_instance["instance"])
                    
                await asyncio.sleep(0.1)  # Small delay between requests
            
            # Calculate distribution evenness
            expected_per_instance = total_requests / len(instances)
            distribution_variance = 0
            for count in requests_per_instance.values():
                distribution_variance += (count - expected_per_instance) ** 2
            distribution_variance /= len(requests_per_instance)
            
            return {
                "success": True,
                "algorithm": "round_robin",
                "total_requests": total_requests,
                "requests_per_instance": requests_per_instance,
                "distribution_variance": distribution_variance,
                "evenness_score": 1.0 / (1.0 + distribution_variance)  # Higher is better
            }
            
        except Exception as e:
            return {"success": False, "algorithm": "round_robin", "error": str(e)}
    
    async def test_weighted_round_robin_lb(self, manager, service_name: str, instances: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Test weighted round-robin load balancing."""
        try:
            # Assign weights based on zone (simulate different instance capabilities)
            instance_weights = {}
            for instance in instances:
                zone = instance.get("zone", "unknown")
                # Simulate different weights based on zone
                if zone.endswith("-a"):
                    weight = 3
                elif zone.endswith("-b"):
                    weight = 2
                else:
                    weight = 1
                
                instance_id = f"{instance['host']}:{instance['port']}"
                instance_weights[instance_id] = weight
            
            requests_per_instance = {}
            total_requests = 30
            
            for i in range(total_requests):
                selected_instance = await manager.load_balancer.select_instance(
                    service_name, algorithm="weighted_round_robin", 
                    instances=instances, weights=instance_weights
                )
                
                if selected_instance["success"]:
                    instance_id = selected_instance["instance"]["instance_id"]
                    requests_per_instance[instance_id] = requests_per_instance.get(instance_id, 0) + 1
                    
                    request_result = await manager.make_test_request(selected_instance["instance"])
                
                await asyncio.sleep(0.1)
            
            # Verify requests are distributed according to weights
            total_weight = sum(instance_weights.values())
            weight_compliance = {}
            
            for instance_id, actual_requests in requests_per_instance.items():
                expected_ratio = instance_weights.get(instance_id, 1) / total_weight
                actual_ratio = actual_requests / total_requests
                weight_compliance[instance_id] = abs(expected_ratio - actual_ratio)
            
            avg_weight_compliance = sum(weight_compliance.values()) / len(weight_compliance)
            
            return {
                "success": True,
                "algorithm": "weighted_round_robin",
                "total_requests": total_requests,
                "instance_weights": instance_weights,
                "requests_per_instance": requests_per_instance,
                "weight_compliance": weight_compliance,
                "avg_weight_compliance": avg_weight_compliance
            }
            
        except Exception as e:
            return {"success": False, "algorithm": "weighted_round_robin", "error": str(e)}
    
    async def test_least_connections_lb(self, manager, service_name: str, instances: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Test least connections load balancing."""
        try:
            # Simulate connection tracking
            connection_counts = {f"{inst['host']}:{inst['port']}": 0 for inst in instances}
            requests_per_instance = {}
            total_requests = 25
            
            for i in range(total_requests):
                selected_instance = await manager.load_balancer.select_instance(
                    service_name, 
                    algorithm="least_connections",
                    instances=instances,
                    connection_counts=connection_counts
                )
                
                if selected_instance["success"]:
                    instance_id = selected_instance["instance"]["instance_id"]
                    requests_per_instance[instance_id] = requests_per_instance.get(instance_id, 0) + 1
                    
                    # Simulate connection increase
                    connection_counts[instance_id] = connection_counts.get(instance_id, 0) + 1
                    
                    request_result = await manager.make_test_request(selected_instance["instance"])
                    
                    # Simulate random connection cleanup (some connections finish)
                    if random.random() < 0.3:  # 30% chance a connection finishes
                        for conn_id in connection_counts:
                            if connection_counts[conn_id] > 0 and random.random() < 0.5:
                                connection_counts[conn_id] -= 1
                
                await asyncio.sleep(0.1)
            
            return {
                "success": True,
                "algorithm": "least_connections",
                "total_requests": total_requests,
                "requests_per_instance": requests_per_instance,
                "final_connection_counts": connection_counts
            }
            
        except Exception as e:
            return {"success": False, "algorithm": "least_connections", "error": str(e)}
    
    async def test_random_lb(self, manager, service_name: str, instances: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Test random load balancing."""
        try:
            requests_per_instance = {}
            total_requests = 20
            
            for i in range(total_requests):
                selected_instance = await manager.load_balancer.select_instance(
                    service_name, algorithm="random", instances=instances
                )
                
                if selected_instance["success"]:
                    instance_id = selected_instance["instance"]["instance_id"]
                    requests_per_instance[instance_id] = requests_per_instance.get(instance_id, 0) + 1
                    
                    request_result = await manager.make_test_request(selected_instance["instance"])
                
                await asyncio.sleep(0.1)
            
            # Calculate randomness quality (standard deviation should be within reasonable bounds)
            values = list(requests_per_instance.values())
            mean = sum(values) / len(values)
            variance = sum((x - mean) ** 2 for x in values) / len(values)
            std_dev = variance ** 0.5
            
            return {
                "success": True,
                "algorithm": "random",
                "total_requests": total_requests,
                "requests_per_instance": requests_per_instance,
                "distribution_std_dev": std_dev,
                "distribution_quality": 1.0 / (1.0 + std_dev)  # Lower std_dev is better for randomness
            }
            
        except Exception as e:
            return {"success": False, "algorithm": "random", "error": str(e)}
    
    async def test_zone_aware_lb(self, manager, service_name: str, instances: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Test zone-aware load balancing."""
        try:
            # Group instances by zone
            zones = {}
            for instance in instances:
                zone = instance.get("zone", "unknown")
                if zone not in zones:
                    zones[zone] = []
                zones[zone].append(instance)
            
            requests_per_zone = {}
            requests_per_instance = {}
            total_requests = 30
            
            for i in range(total_requests):
                # Simulate client zone preference
                preferred_zone = list(zones.keys())[i % len(zones)]
                
                selected_instance = await manager.load_balancer.select_instance(
                    service_name,
                    algorithm="zone_aware",
                    instances=instances,
                    preferred_zone=preferred_zone,
                    zones=zones
                )
                
                if selected_instance["success"]:
                    instance_id = selected_instance["instance"]["instance_id"]
                    instance_zone = selected_instance["instance"].get("zone", "unknown")
                    
                    requests_per_instance[instance_id] = requests_per_instance.get(instance_id, 0) + 1
                    requests_per_zone[instance_zone] = requests_per_zone.get(instance_zone, 0) + 1
                    
                    request_result = await manager.make_test_request(selected_instance["instance"])
                
                await asyncio.sleep(0.1)
            
            # Calculate zone affinity compliance
            zone_preference_compliance = 0
            total_zones = len(zones)
            
            for zone, request_count in requests_per_zone.items():
                expected_ratio = 1.0 / total_zones  # Assuming equal zone distribution
                actual_ratio = request_count / total_requests
                zone_preference_compliance += abs(expected_ratio - actual_ratio)
            
            zone_preference_compliance /= total_zones
            
            return {
                "success": True,
                "algorithm": "zone_aware",
                "total_requests": total_requests,
                "zones": list(zones.keys()),
                "requests_per_zone": requests_per_zone,
                "requests_per_instance": requests_per_instance,
                "zone_preference_compliance": zone_preference_compliance
            }
            
        except Exception as e:
            return {"success": False, "algorithm": "zone_aware", "error": str(e)}
    
    def analyze_load_distribution(self, load_balancing_results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze load distribution across all algorithms."""
        try:
            analysis = {
                "algorithm_performance": {},
                "overall_metrics": {
                    "algorithms_tested": 0,
                    "successful_algorithms": 0,
                    "avg_distribution_quality": 0
                }
            }
            
            distribution_qualities = []
            
            for algorithm, result in load_balancing_results.items():
                if result["success"]:
                    analysis["algorithm_performance"][algorithm] = {
                        "success": True,
                        "total_requests": result.get("total_requests", 0)
                    }
                    
                    # Algorithm-specific analysis
                    if algorithm == "round_robin":
                        analysis["algorithm_performance"][algorithm]["evenness_score"] = result.get("evenness_score", 0)
                        distribution_qualities.append(result.get("evenness_score", 0))
                    
                    elif algorithm == "weighted_round_robin":
                        analysis["algorithm_performance"][algorithm]["weight_compliance"] = 1.0 - result.get("avg_weight_compliance", 1.0)
                        distribution_qualities.append(1.0 - result.get("avg_weight_compliance", 1.0))
                    
                    elif algorithm == "random":
                        analysis["algorithm_performance"][algorithm]["distribution_quality"] = result.get("distribution_quality", 0)
                        distribution_qualities.append(result.get("distribution_quality", 0))
                    
                    elif algorithm == "zone_aware":
                        analysis["algorithm_performance"][algorithm]["zone_compliance"] = 1.0 - result.get("zone_preference_compliance", 1.0)
                        distribution_qualities.append(1.0 - result.get("zone_preference_compliance", 1.0))
                    
                    analysis["overall_metrics"]["successful_algorithms"] += 1
                else:
                    analysis["algorithm_performance"][algorithm] = {
                        "success": False,
                        "error": result.get("error", "Unknown error")
                    }
                
                analysis["overall_metrics"]["algorithms_tested"] += 1
            
            if distribution_qualities:
                analysis["overall_metrics"]["avg_distribution_quality"] = sum(distribution_qualities) / len(distribution_qualities)
            
            return analysis
            
        except Exception as e:
            return {"error": str(e)}


@pytest.mark.asyncio
async def test_load_balancing_algorithms_l4_staging(service_mesh_l4):
    """Test load balancing algorithms with L4 realism."""
    lb_tests = LoadBalancingL4Tests()
    
    # Test load balancing for services with multiple instances
    multi_instance_services = [
        name for name, info in service_mesh_l4.staging_services.items()
        if info["accessible_instances"] >= 2
    ]
    
    if not multi_instance_services:
        pytest.skip("No services with multiple instances available for load balancing testing")
    
    load_balancing_results = []
    
    for service_name in multi_instance_services[:2]:  # Test first 2 services to limit test time
        lb_result = await lb_tests.test_load_balancing_algorithms_l4(service_mesh_l4, service_name)
        load_balancing_results.append(lb_result)
        
        if lb_result["success"]:
            # Verify load balancing effectiveness
            assert lb_result["successful_algorithms"] >= 3, "Too few load balancing algorithms working"
            
            # Check distribution analysis
            distribution_analysis = lb_result["distribution_analysis"]
            assert distribution_analysis["overall_metrics"]["avg_distribution_quality"] > 0.5, "Load distribution quality too low"
    
    # Verify overall load balancing success
    successful_lb_tests = [r for r in load_balancing_results if r["success"]]
    assert len(successful_lb_tests) > 0, "No successful load balancing tests"


@pytest.mark.asyncio
async def test_round_robin_distribution_fairness(service_mesh_l4):
    """Test round-robin algorithm distribution fairness."""
    lb_tests = LoadBalancingL4Tests()
    
    multi_instance_services = [
        name for name, info in service_mesh_l4.staging_services.items()
        if info["accessible_instances"] >= 2
    ]
    
    if not multi_instance_services:
        pytest.skip("No services with multiple instances available")
    
    service_name = multi_instance_services[0]
    instances = service_mesh_l4.staging_services[service_name]["instances"]
    
    # Test round-robin distribution
    rr_result = await lb_tests.test_round_robin_lb(service_mesh_l4, service_name, instances)
    
    assert rr_result["success"], f"Round-robin test failed: {rr_result.get('error')}"
    assert rr_result["evenness_score"] > 0.8, f"Round-robin distribution not fair enough: {rr_result['evenness_score']}"
    
    # Verify all instances received requests
    requests_per_instance = rr_result["requests_per_instance"]
    assert len(requests_per_instance) >= len(instances), "Not all instances received requests"
    
    logger.info(f"Round-robin fairness: evenness score {rr_result['evenness_score']:.3f}, "
               f"distribution: {requests_per_instance}")


@pytest.mark.asyncio
async def test_weighted_load_balancing_compliance(service_mesh_l4):
    """Test weighted load balancing weight compliance."""
    lb_tests = LoadBalancingL4Tests()
    
    multi_instance_services = [
        name for name, info in service_mesh_l4.staging_services.items()
        if info["accessible_instances"] >= 2
    ]
    
    if not multi_instance_services:
        pytest.skip("No services with multiple instances available")
    
    service_name = multi_instance_services[0]
    instances = service_mesh_l4.staging_services[service_name]["instances"]
    
    # Test weighted round-robin
    weighted_result = await lb_tests.test_weighted_round_robin_lb(service_mesh_l4, service_name, instances)
    
    assert weighted_result["success"], f"Weighted round-robin test failed: {weighted_result.get('error')}"
    assert weighted_result["avg_weight_compliance"] < 0.3, f"Weight compliance poor: {weighted_result['avg_weight_compliance']}"
    
    # Verify weights were considered
    instance_weights = weighted_result["instance_weights"]
    requests_per_instance = weighted_result["requests_per_instance"]
    
    # Higher weight instances should generally get more requests
    weight_request_correlation = []
    for instance_id in requests_per_instance:
        weight = instance_weights.get(instance_id, 1)
        requests = requests_per_instance[instance_id]
        weight_request_correlation.append((weight, requests))
    
    # Sort by weight and verify general trend
    weight_request_correlation.sort(key=lambda x: x[0])
    prev_weight, prev_requests = weight_request_correlation[0]
    
    for weight, requests in weight_request_correlation[1:]:
        # Allow some variance but expect general upward trend
        if weight > prev_weight:
            assert requests >= prev_requests * 0.7, "Higher weight instance got significantly fewer requests"
        prev_weight, prev_requests = weight, requests
    
    logger.info(f"Weighted load balancing: avg compliance {weighted_result['avg_weight_compliance']:.3f}, "
               f"weights: {instance_weights}, requests: {requests_per_instance}")


@pytest.mark.asyncio
async def test_zone_aware_routing(service_mesh_l4):
    """Test zone-aware routing preferences."""
    lb_tests = LoadBalancingL4Tests()
    
    multi_instance_services = [
        name for name, info in service_mesh_l4.staging_services.items()
        if info["accessible_instances"] >= 2
    ]
    
    if not multi_instance_services:
        pytest.skip("No services with multiple instances available")
    
    service_name = multi_instance_services[0]
    instances = service_mesh_l4.staging_services[service_name]["instances"]
    
    # Check if instances span multiple zones
    zones = set(inst.get("zone", "unknown") for inst in instances)
    if len(zones) < 2:
        pytest.skip("Need instances in multiple zones for zone-aware testing")
    
    # Test zone-aware routing
    zone_result = await lb_tests.test_zone_aware_lb(service_mesh_l4, service_name, instances)
    
    assert zone_result["success"], f"Zone-aware test failed: {zone_result.get('error')}"
    
    # Verify zone distribution
    requests_per_zone = zone_result["requests_per_zone"]
    assert len(requests_per_zone) >= 2, "Requests not distributed across multiple zones"
    
    # Each zone should receive some requests
    for zone, requests in requests_per_zone.items():
        assert requests > 0, f"Zone {zone} received no requests"
    
    zone_compliance = zone_result["zone_preference_compliance"]
    assert zone_compliance < 0.5, f"Zone preference compliance poor: {zone_compliance}"
    
    logger.info(f"Zone-aware routing: {len(zones)} zones, compliance {zone_compliance:.3f}, "
               f"distribution: {requests_per_zone}")


@pytest.mark.asyncio
async def test_load_balancing_under_concurrent_load(service_mesh_l4):
    """Test load balancing behavior under concurrent load."""
    lb_tests = LoadBalancingL4Tests()
    
    multi_instance_services = [
        name for name, info in service_mesh_l4.staging_services.items()
        if info["accessible_instances"] >= 2
    ]
    
    if not multi_instance_services:
        pytest.skip("No services with multiple instances available")
    
    service_name = multi_instance_services[0]
    instances = service_mesh_l4.staging_services[service_name]["instances"]
    concurrent_clients = 10
    
    # Simulate concurrent clients using round-robin
    tasks = []
    for i in range(concurrent_clients):
        task = lb_tests.test_round_robin_lb(service_mesh_l4, service_name, instances)
        tasks.append(task)
    
    # Execute concurrently
    start_time = time.time()
    results = await asyncio.gather(*tasks, return_exceptions=True)
    total_time = time.time() - start_time
    
    # Analyze results
    successful_results = [r for r in results if isinstance(r, dict) and r.get("success")]
    success_rate = len(successful_results) / len(results) * 100
    
    assert success_rate >= 90.0, f"Load balancing success rate under load too low: {success_rate}%"
    assert total_time < 60.0, f"Load balancing under load too slow: {total_time}s"
    
    # Verify distribution remained fair under load
    combined_requests = {}
    total_requests = 0
    
    for result in successful_results:
        for instance_id, count in result["requests_per_instance"].items():
            combined_requests[instance_id] = combined_requests.get(instance_id, 0) + count
            total_requests += count
    
    # Check distribution fairness
    expected_per_instance = total_requests / len(combined_requests)
    max_deviation = max(abs(count - expected_per_instance) for count in combined_requests.values())
    deviation_ratio = max_deviation / expected_per_instance
    
    assert deviation_ratio < 0.5, f"Load distribution under concurrent load unfair: {deviation_ratio:.3f}"
    
    logger.info(f"Concurrent load balancing: {len(successful_results)}/{len(results)} clients successful, "
               f"{success_rate:.1f}% success rate, {deviation_ratio:.3f} deviation ratio")


@pytest.mark.asyncio
async def test_load_balancing_algorithm_performance(service_mesh_l4):
    """Test performance characteristics of different load balancing algorithms."""
    lb_tests = LoadBalancingL4Tests()
    
    multi_instance_services = [
        name for name, info in service_mesh_l4.staging_services.items()
        if info["accessible_instances"] >= 2
    ]
    
    if not multi_instance_services:
        pytest.skip("No services with multiple instances available")
    
    service_name = multi_instance_services[0]
    instances = service_mesh_l4.staging_services[service_name]["instances"]
    
    # Test each algorithm's performance
    algorithm_performance = {}
    algorithms = ["round_robin", "random", "least_connections"]
    
    for algorithm in algorithms:
        performance_start = time.time()
        
        if algorithm == "round_robin":
            result = await lb_tests.test_round_robin_lb(service_mesh_l4, service_name, instances)
        elif algorithm == "random":
            result = await lb_tests.test_random_lb(service_mesh_l4, service_name, instances)
        elif algorithm == "least_connections":
            result = await lb_tests.test_least_connections_lb(service_mesh_l4, service_name, instances)
        
        algorithm_time = time.time() - performance_start
        
        algorithm_performance[algorithm] = {
            "success": result.get("success", False),
            "execution_time": algorithm_time,
            "requests_processed": result.get("total_requests", 0)
        }
        
        if result.get("success"):
            throughput = result.get("total_requests", 0) / algorithm_time
            algorithm_performance[algorithm]["throughput"] = throughput
    
    # Verify all algorithms performed reasonably
    for algorithm, perf in algorithm_performance.items():
        assert perf["success"], f"Algorithm {algorithm} failed"
        assert perf["execution_time"] < 30.0, f"Algorithm {algorithm} too slow: {perf['execution_time']}s"
        
        if "throughput" in perf:
            assert perf["throughput"] > 0.5, f"Algorithm {algorithm} throughput too low: {perf['throughput']} req/s"
    
    logger.info(f"Algorithm performance: {algorithm_performance}")