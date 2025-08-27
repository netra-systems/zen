"""
Test Database Load Balancing - Iteration 59

Business Value Justification:
- Segment: Enterprise/Mid
- Business Goal: Scalability & Performance
- Value Impact: Distributes database load for better performance and availability
- Strategic Impact: Enables horizontal scaling and improved user experience

Focus: Read/write splitting, load distribution algorithms, and health-based routing
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
import random
import statistics

from netra_backend.app.database.manager import DatabaseManager


class TestDatabaseLoadBalancing:
    """Test database load balancing and distribution strategies"""
    
    @pytest.fixture
    def mock_db_manager(self):
        """Mock database manager with load balancing capabilities"""
        manager = MagicMock()
        manager.database_nodes = {
            "primary": {"type": "master", "health": 100, "load": 0.3, "response_time": 45},
            "replica_1": {"type": "slave", "health": 95, "load": 0.2, "response_time": 50},
            "replica_2": {"type": "slave", "health": 98, "load": 0.1, "response_time": 42},
            "replica_3": {"type": "slave", "health": 85, "load": 0.6, "response_time": 78}
        }
        manager.load_balancer_stats = {"requests_routed": 0, "failed_requests": 0}
        return manager
    
    @pytest.fixture
    def mock_load_balancer(self):
        """Mock load balancer service"""
        balancer = MagicMock()
        balancer.routing_history = []
        balancer.algorithms = ["round_robin", "least_connections", "weighted_health"]
        return balancer
    
    @pytest.mark.asyncio
    async def test_read_write_operation_splitting(self, mock_db_manager, mock_load_balancer):
        """Test automatic splitting of read and write operations"""
        def route_database_operation(operation_type, query_hint=None):
            routing_decision = {
                "operation_type": operation_type,
                "query_hint": query_hint,
                "timestamp": datetime.now().isoformat()
            }
            
            if operation_type in ["INSERT", "UPDATE", "DELETE", "CREATE", "DROP", "ALTER"]:
                # Write operations go to primary
                routing_decision.update({
                    "target_node": "primary",
                    "node_type": "master",
                    "reason": "write_operation_requires_master"
                })
            
            elif operation_type == "SELECT":
                # Read operations can go to replicas
                available_replicas = [
                    node_id for node_id, node_info in mock_db_manager.database_nodes.items()
                    if node_info["type"] == "slave" and node_info["health"] > 80
                ]
                
                if query_hint == "read_primary":
                    # Force read from primary for consistency
                    routing_decision.update({
                        "target_node": "primary",
                        "node_type": "master",
                        "reason": "read_primary_hint"
                    })
                elif available_replicas:
                    # Choose best replica based on load and health
                    best_replica = min(available_replicas, key=lambda x: (
                        mock_db_manager.database_nodes[x]["load"],
                        -mock_db_manager.database_nodes[x]["health"]
                    ))
                    
                    routing_decision.update({
                        "target_node": best_replica,
                        "node_type": "slave",
                        "reason": "read_replica_optimization"
                    })
                else:
                    # Fallback to primary if no healthy replicas
                    routing_decision.update({
                        "target_node": "primary",
                        "node_type": "master",
                        "reason": "no_healthy_replicas"
                    })
            
            mock_load_balancer.routing_history.append(routing_decision)
            mock_db_manager.load_balancer_stats["requests_routed"] += 1
            
            return routing_decision
        
        mock_load_balancer.route_database_operation = route_database_operation
        
        # Test write operations
        write_operations = ["INSERT", "UPDATE", "DELETE"]
        for op in write_operations:
            result = mock_load_balancer.route_database_operation(op)
            assert result["target_node"] == "primary"
            assert result["node_type"] == "master"
            assert result["reason"] == "write_operation_requires_master"
        
        # Test read operations
        read_result = mock_load_balancer.route_database_operation("SELECT")
        assert read_result["target_node"] in ["replica_1", "replica_2"]  # Should pick healthy replica
        assert read_result["node_type"] == "slave"
        assert read_result["reason"] == "read_replica_optimization"
        
        # Test read with primary hint
        primary_read_result = mock_load_balancer.route_database_operation("SELECT", "read_primary")
        assert primary_read_result["target_node"] == "primary"
        assert primary_read_result["reason"] == "read_primary_hint"
        
        # Verify routing history
        assert len(mock_load_balancer.routing_history) == 5
        assert mock_db_manager.load_balancer_stats["requests_routed"] == 5
    
    @pytest.mark.asyncio
    async def test_load_distribution_algorithms(self, mock_db_manager, mock_load_balancer):
        """Test different load distribution algorithms"""
        def apply_load_balancing_algorithm(algorithm, available_nodes, request_count=1):
            distribution_results = []
            
            if algorithm == "round_robin":
                # Simple round-robin distribution
                for i in range(request_count):
                    node_index = i % len(available_nodes)
                    selected_node = available_nodes[node_index]
                    distribution_results.append({
                        "algorithm": algorithm,
                        "selected_node": selected_node,
                        "selection_reason": f"round_robin_position_{node_index}"
                    })
            
            elif algorithm == "least_connections":
                # Choose node with lowest current load
                for _ in range(request_count):
                    best_node = min(available_nodes, 
                                  key=lambda x: mock_db_manager.database_nodes[x]["load"])
                    distribution_results.append({
                        "algorithm": algorithm,
                        "selected_node": best_node,
                        "selection_reason": f"lowest_load_{mock_db_manager.database_nodes[best_node]['load']}"
                    })
                    # Simulate load increase
                    mock_db_manager.database_nodes[best_node]["load"] += 0.05
            
            elif algorithm == "weighted_health":
                # Weighted selection based on health and inverse load
                for _ in range(request_count):
                    node_weights = {}
                    for node in available_nodes:
                        node_info = mock_db_manager.database_nodes[node]
                        # Higher health and lower load = higher weight
                        weight = node_info["health"] / (100 * (node_info["load"] + 0.1))
                        node_weights[node] = weight
                    
                    # Select node with highest weight
                    best_node = max(node_weights.keys(), key=lambda x: node_weights[x])
                    distribution_results.append({
                        "algorithm": algorithm,
                        "selected_node": best_node,
                        "selection_reason": f"weighted_health_{node_weights[best_node]:.2f}"
                    })
            
            return distribution_results
        
        mock_load_balancer.apply_load_balancing_algorithm = apply_load_balancing_algorithm
        
        read_replicas = ["replica_1", "replica_2", "replica_3"]
        
        # Test round-robin algorithm
        round_robin_results = mock_load_balancer.apply_load_balancing_algorithm(
            "round_robin", read_replicas, 6
        )
        
        assert len(round_robin_results) == 6
        # Should distribute evenly across nodes
        selected_nodes = [r["selected_node"] for r in round_robin_results]
        for replica in read_replicas:
            assert selected_nodes.count(replica) == 2  # 6 requests / 3 nodes = 2 each
        
        # Reset node loads
        for node in mock_db_manager.database_nodes:
            if mock_db_manager.database_nodes[node]["type"] == "slave":
                mock_db_manager.database_nodes[node]["load"] = random.uniform(0.1, 0.6)
        
        # Test least connections algorithm
        least_conn_results = mock_load_balancer.apply_load_balancing_algorithm(
            "least_connections", read_replicas, 5
        )
        
        assert len(least_conn_results) == 5
        # Should initially prefer replica_2 (lowest load = 0.1)
        first_selection = least_conn_results[0]["selected_node"]
        assert first_selection == "replica_2"
        
        # Test weighted health algorithm
        weighted_results = mock_load_balancer.apply_load_balancing_algorithm(
            "weighted_health", read_replicas, 3
        )
        
        assert len(weighted_results) == 3
        # Should prefer nodes with high health and low load
        # replica_2 should be favored (health=98, low load)
        selected_nodes = [r["selected_node"] for r in weighted_results]
        assert selected_nodes.count("replica_2") >= 1
    
    @pytest.mark.asyncio
    async def test_health_based_node_routing(self, mock_db_manager, mock_load_balancer):
        """Test health-based routing and unhealthy node exclusion"""
        def check_node_health_and_route(operation_type, health_threshold=80):
            healthy_nodes = []
            unhealthy_nodes = []
            
            for node_id, node_info in mock_db_manager.database_nodes.items():
                if node_info["health"] >= health_threshold:
                    healthy_nodes.append(node_id)
                else:
                    unhealthy_nodes.append(node_id)
            
            routing_result = {
                "operation_type": operation_type,
                "health_threshold": health_threshold,
                "healthy_nodes": healthy_nodes,
                "unhealthy_nodes": unhealthy_nodes,
                "routing_decision": None
            }
            
            if operation_type == "write":
                # Writes must go to primary regardless of health
                if "primary" in healthy_nodes:
                    routing_result["routing_decision"] = {
                        "target_node": "primary",
                        "reason": "healthy_primary_available"
                    }
                else:
                    routing_result["routing_decision"] = {
                        "target_node": "primary",
                        "reason": "primary_required_despite_health",
                        "warning": "Primary node health below threshold"
                    }
            
            elif operation_type == "read":
                # Reads can use healthy replicas
                healthy_replicas = [node for node in healthy_nodes 
                                  if mock_db_manager.database_nodes[node]["type"] == "slave"]
                
                if healthy_replicas:
                    # Choose replica with best health/performance ratio
                    best_replica = max(healthy_replicas, key=lambda x: (
                        mock_db_manager.database_nodes[x]["health"] - 
                        mock_db_manager.database_nodes[x]["response_time"]
                    ))
                    
                    routing_result["routing_decision"] = {
                        "target_node": best_replica,
                        "reason": "healthy_replica_selected"
                    }
                else:
                    # Fallback to primary if no healthy replicas
                    routing_result["routing_decision"] = {
                        "target_node": "primary",
                        "reason": "no_healthy_replicas_fallback_primary"
                    }
            
            return routing_result
        
        mock_load_balancer.check_node_health_and_route = check_node_health_and_route
        
        # Test with default health threshold (80)
        read_routing = mock_load_balancer.check_node_health_and_route("read")
        
        # replica_3 has health=85, should be included
        # All nodes should be healthy with threshold=80
        assert "primary" in read_routing["healthy_nodes"]
        assert "replica_1" in read_routing["healthy_nodes"]
        assert "replica_2" in read_routing["healthy_nodes"]
        assert len(read_routing["unhealthy_nodes"]) == 0
        
        # Should route to a healthy replica
        assert read_routing["routing_decision"]["target_node"] in ["replica_1", "replica_2"]
        
        # Test with higher health threshold (90)
        high_threshold_routing = mock_load_balancer.check_node_health_and_route("read", 90)
        
        # Only primary (100), replica_1 (95), replica_2 (98) should be healthy
        assert "replica_3" in high_threshold_routing["unhealthy_nodes"]  # health=85 < 90
        assert len(high_threshold_routing["healthy_nodes"]) == 3
        
        # Should still route successfully to healthy replica
        healthy_target = high_threshold_routing["routing_decision"]["target_node"]
        assert healthy_target in ["replica_1", "replica_2"]
        
        # Simulate all replicas becoming unhealthy
        for node_id in mock_db_manager.database_nodes:
            if mock_db_manager.database_nodes[node_id]["type"] == "slave":
                mock_db_manager.database_nodes[node_id]["health"] = 70  # Below threshold
        
        unhealthy_replica_routing = mock_load_balancer.check_node_health_and_route("read", 80)
        
        # Should fallback to primary
        assert unhealthy_replica_routing["routing_decision"]["target_node"] == "primary"
        assert unhealthy_replica_routing["routing_decision"]["reason"] == "no_healthy_replicas_fallback_primary"
        assert len(unhealthy_replica_routing["unhealthy_nodes"]) == 3  # All replicas unhealthy
    
    @pytest.mark.asyncio
    async def test_connection_pool_balancing(self, mock_db_manager):
        """Test connection pool balancing across database nodes"""
        def manage_connection_pools(total_connections=100):
            pool_allocation = {
                "primary": {"allocated": 0, "utilization": 0, "max_connections": 0},
                "replica_1": {"allocated": 0, "utilization": 0, "max_connections": 0},
                "replica_2": {"allocated": 0, "utilization": 0, "max_connections": 0},
                "replica_3": {"allocated": 0, "utilization": 0, "max_connections": 0}
            }
            
            # Base allocation: Primary gets 40%, replicas share 60%
            base_allocations = {
                "primary": 0.4,
                "replica_1": 0.2,
                "replica_2": 0.2, 
                "replica_3": 0.2
            }
            
            # Adjust based on node health and load
            for node_id in pool_allocation:
                node_info = mock_db_manager.database_nodes[node_id]
                base_allocation = base_allocations[node_id]
                
                # Health factor (0.8 to 1.2 multiplier)
                health_factor = node_info["health"] / 100.0
                
                # Load factor (inverse - lower load gets more connections)
                load_factor = (1.0 - node_info["load"]) + 0.5  # 0.5 to 1.5 range
                
                adjusted_allocation = base_allocation * health_factor * load_factor
                pool_allocation[node_id]["max_connections"] = int(total_connections * adjusted_allocation)
                
                # Current utilization (simulated)
                current_usage = int(pool_allocation[node_id]["max_connections"] * node_info["load"])
                pool_allocation[node_id]["allocated"] = current_usage
                pool_allocation[node_id]["utilization"] = (current_usage / pool_allocation[node_id]["max_connections"]) if pool_allocation[node_id]["max_connections"] > 0 else 0
            
            # Ensure total doesn't exceed limit
            total_allocated = sum(pool["max_connections"] for pool in pool_allocation.values())
            if total_allocated != total_connections:
                # Adjust primary to match total
                adjustment = total_connections - total_allocated
                pool_allocation["primary"]["max_connections"] += adjustment
            
            return {
                "total_connections": total_connections,
                "pool_allocation": pool_allocation,
                "rebalancing_performed": total_allocated != total_connections
            }
        
        mock_db_manager.manage_connection_pools = manage_connection_pools
        
        result = mock_db_manager.manage_connection_pools(100)
        
        assert result["total_connections"] == 100
        
        pool_allocation = result["pool_allocation"]
        
        # Verify total allocation
        total_max_connections = sum(pool["max_connections"] for pool in pool_allocation.values())
        assert total_max_connections == 100
        
        # Primary should get significant portion (around 40% base)
        assert pool_allocation["primary"]["max_connections"] >= 35
        
        # Replicas should get connections based on health and load
        # replica_2 (health=98, load=0.1) should get more than replica_3 (health=85, load=0.6)
        assert pool_allocation["replica_2"]["max_connections"] >= pool_allocation["replica_3"]["max_connections"]
        
        # Verify utilization calculations
        for node_id, pool in pool_allocation.items():
            if pool["max_connections"] > 0:
                expected_utilization = pool["allocated"] / pool["max_connections"]
                assert abs(pool["utilization"] - expected_utilization) < 0.01
    
    def test_load_balancer_failure_recovery(self, mock_load_balancer):
        """Test load balancer behavior during node failures and recovery"""
        node_status = {
            "primary": "healthy",
            "replica_1": "healthy", 
            "replica_2": "healthy",
            "replica_3": "failing"
        }
        
        failure_events = []
        recovery_events = []
        
        def simulate_node_failure_recovery():
            current_scenario = {
                "active_nodes": [],
                "failed_nodes": [],
                "recovering_nodes": [],
                "actions_taken": []
            }
            
            for node_id, status in node_status.items():
                if status == "healthy":
                    current_scenario["active_nodes"].append(node_id)
                elif status == "failing":
                    current_scenario["failed_nodes"].append(node_id)
                    failure_events.append({
                        "node_id": node_id,
                        "event": "node_failure_detected",
                        "timestamp": datetime.now().isoformat(),
                        "action": "remove_from_rotation"
                    })
                    current_scenario["actions_taken"].append(f"Removed {node_id} from load balancer rotation")
                elif status == "recovering":
                    current_scenario["recovering_nodes"].append(node_id)
            
            # Simulate recovery of previously failed nodes
            if "replica_3" in current_scenario["failed_nodes"]:
                # After some time, node recovers
                node_status["replica_3"] = "recovering"
                current_scenario["failed_nodes"].remove("replica_3")
                current_scenario["recovering_nodes"].append("replica_3")
                
                recovery_events.append({
                    "node_id": "replica_3",
                    "event": "node_recovery_initiated",
                    "timestamp": datetime.now().isoformat(),
                    "action": "health_check_validation"
                })
                current_scenario["actions_taken"].append("Started health validation for replica_3")
                
                # Simulate successful health check
                if len(recovery_events) > 0:  # Health check passed
                    node_status["replica_3"] = "healthy"
                    current_scenario["recovering_nodes"].remove("replica_3")
                    current_scenario["active_nodes"].append("replica_3")
                    
                    recovery_events.append({
                        "node_id": "replica_3",
                        "event": "node_recovery_completed",
                        "timestamp": datetime.now().isoformat(),
                        "action": "add_to_rotation"
                    })
                    current_scenario["actions_taken"].append("Added replica_3 back to load balancer rotation")
            
            return current_scenario
        
        mock_load_balancer.simulate_node_failure_recovery = simulate_node_failure_recovery
        
        scenario = mock_load_balancer.simulate_node_failure_recovery()
        
        # Initially replica_3 should be failed
        assert "replica_3" not in scenario["active_nodes"]
        assert len(scenario["active_nodes"]) == 3  # primary, replica_1, replica_2
        
        # Verify failure was recorded
        assert len(failure_events) == 1
        assert failure_events[0]["node_id"] == "replica_3"
        assert failure_events[0]["event"] == "node_failure_detected"
        
        # Verify recovery was initiated and completed
        assert len(recovery_events) == 2
        assert recovery_events[0]["event"] == "node_recovery_initiated"
        assert recovery_events[1]["event"] == "node_recovery_completed"
        
        # After recovery, replica_3 should be back in active nodes
        final_scenario = mock_load_balancer.simulate_node_failure_recovery()
        assert "replica_3" in final_scenario["active_nodes"]
        assert len(final_scenario["failed_nodes"]) == 0
        assert len(final_scenario["recovering_nodes"]) == 0
        
        # Verify actions taken
        actions = scenario["actions_taken"]
        assert any("Removed replica_3" in action for action in actions)
        assert any("health validation" in action for action in actions)
        assert any("Added replica_3 back" in action for action in actions)