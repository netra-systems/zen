"""
Test Load Balancing Algorithms - Iteration 67

Business Value Justification:
- Segment: Enterprise/Mid
- Business Goal: High Availability & Performance
- Value Impact: Distributes load efficiently across resources
- Strategic Impact: Enables horizontal scaling and fault tolerance
"""

import pytest
import random
import statistics
from unittest.mock import MagicMock


class TestLoadBalancingAlgorithms:
    """Test various load balancing algorithm implementations"""
    
    def test_weighted_round_robin_performance(self):
        """Test weighted round-robin load balancing efficiency"""
        servers = [
            {"id": "server_1", "weight": 3, "capacity": 100, "current_load": 0},
            {"id": "server_2", "weight": 2, "capacity": 80, "current_load": 0},  
            {"id": "server_3", "weight": 1, "capacity": 50, "current_load": 0}
        ]
        
        def weighted_round_robin_select(servers, request_count):
            """Weighted round-robin server selection"""
            total_weight = sum(server["weight"] for server in servers)
            selections = []
            current_weights = [0] * len(servers)
            
            for request_id in range(request_count):
                # Increase current weights
                for i, server in enumerate(servers):
                    current_weights[i] += server["weight"]
                
                # Select server with highest current weight
                selected_index = current_weights.index(max(current_weights))
                selected_server = servers[selected_index]
                
                # Decrease selected server's current weight
                current_weights[selected_index] -= total_weight
                
                # Track selection
                selected_server["current_load"] += 1
                selections.append({
                    "request_id": request_id,
                    "selected_server": selected_server["id"],
                    "server_weight": selected_server["weight"]
                })
            
            return selections
        
        # Test distribution over 100 requests
        selections = weighted_round_robin_select(servers, 100)
        
        # Analyze distribution
        distribution = {}
        for selection in selections:
            server_id = selection["selected_server"]
            distribution[server_id] = distribution.get(server_id, 0) + 1
        
        # Verify weighted distribution
        total_requests = sum(distribution.values())
        expected_ratios = {
            "server_1": 3/6,  # 3 out of 6 total weight
            "server_2": 2/6,  # 2 out of 6 total weight
            "server_3": 1/6   # 1 out of 6 total weight
        }
        
        for server_id, expected_ratio in expected_ratios.items():
            actual_ratio = distribution[server_id] / total_requests
            assert abs(actual_ratio - expected_ratio) < 0.1  # Within 10% of expected
    
    def test_least_connections_algorithm(self):
        """Test least connections load balancing"""
        servers = [
            {"id": "server_1", "active_connections": 5, "max_connections": 100},
            {"id": "server_2", "active_connections": 3, "max_connections": 100},
            {"id": "server_3", "active_connections": 7, "max_connections": 100}
        ]
        
        def least_connections_select(servers):
            """Select server with least active connections"""
            # Filter available servers (not at capacity)
            available_servers = [
                s for s in servers 
                if s["active_connections"] < s["max_connections"]
            ]
            
            if not available_servers:
                return None
            
            # Select server with least connections
            return min(available_servers, key=lambda s: s["active_connections"])
        
        # Simulate request processing
        request_assignments = []
        
        for request_id in range(20):
            selected = least_connections_select(servers)
            if selected:
                selected["active_connections"] += 1
                request_assignments.append({
                    "request_id": request_id,
                    "server_id": selected["id"],
                    "connections_before": selected["active_connections"] - 1
                })
                
                # Simulate some requests completing (reduce connections)
                if request_id % 5 == 0:
                    for server in servers:
                        if server["active_connections"] > 0:
                            server["active_connections"] -= random.randint(0, 2)
        
        # Verify balanced connection distribution
        final_connections = [s["active_connections"] for s in servers]
        connection_variance = statistics.variance(final_connections)
        
        # Connections should be relatively balanced
        assert connection_variance < 10  # Low variance indicates good balancing
        assert all(conn < 50 for conn in final_connections)  # No server overloaded
    
    def test_consistent_hashing_distribution(self):
        """Test consistent hashing for sticky load balancing"""
        servers = ["server_1", "server_2", "server_3", "server_4"]
        virtual_nodes = 3  # Virtual nodes per server
        
        def build_hash_ring(servers, virtual_nodes):
            """Build consistent hash ring"""
            hash_ring = {}
            
            for server in servers:
                for i in range(virtual_nodes):
                    # Simple hash function (not cryptographically secure)
                    virtual_key = f"{server}:{i}"
                    hash_value = hash(virtual_key) % (2**32)
                    hash_ring[hash_value] = server
            
            return hash_ring
        
        def get_server_for_key(key, hash_ring):
            """Get server for given key using consistent hashing"""
            if not hash_ring:
                return None
            
            key_hash = hash(key) % (2**32)
            
            # Find the first server with hash >= key_hash
            sorted_hashes = sorted(hash_ring.keys())
            
            for ring_hash in sorted_hashes:
                if ring_hash >= key_hash:
                    return hash_ring[ring_hash]
            
            # Wrap around to first server
            return hash_ring[sorted_hashes[0]]
        
        hash_ring = build_hash_ring(servers, virtual_nodes)
        
        # Test distribution with various keys
        test_keys = [f"user_{i}" for i in range(1000)]
        key_assignments = {}
        
        for key in test_keys:
            server = get_server_for_key(key, hash_ring)
            if server not in key_assignments:
                key_assignments[server] = 0
            key_assignments[server] += 1
        
        # Analyze distribution
        distribution_values = list(key_assignments.values())
        distribution_mean = statistics.mean(distribution_values)
        distribution_std = statistics.stdev(distribution_values)
        
        # Should be relatively evenly distributed
        coefficient_of_variation = distribution_std / distribution_mean
        assert coefficient_of_variation < 0.3  # < 30% variation
        
        # Test consistency when adding/removing servers
        # Remove one server
        new_servers = servers[:-1]  # Remove last server
        new_hash_ring = build_hash_ring(new_servers, virtual_nodes)
        
        # Check how many keys moved
        moved_keys = 0
        for key in test_keys[:100]:  # Check first 100 keys
            old_server = get_server_for_key(key, hash_ring)
            new_server = get_server_for_key(key, new_hash_ring)
            
            if old_server != new_server:
                moved_keys += 1
        
        # Should minimize key movement (consistent hashing property)
        move_percentage = moved_keys / 100
        assert move_percentage < 0.4  # < 40% of keys should move