"""Network Failure Simulator - Modular Component for Network Resilience Testing

Dedicated module for simulating various network failure scenarios to test system resilience.
Supports network partitions, packet loss, DNS failures, and CDN failures.

Business Value Justification (BVJ):
1. Segment: Enterprise & Growth  
2. Business Goal: Provide comprehensive network failure simulation for testing
3. Value Impact: Enables thorough testing of network resilience mechanisms
4. Revenue Impact: Prevents costly network-related outages through better testing

ARCHITECTURAL COMPLIANCE:
- File size: <300 lines
- Function size: <8 lines each
- Modular design for reusability
- Single responsibility principle
"""

import time
from datetime import UTC, datetime
from typing import Any, Dict, List


class NetworkFailureSimulator:
    """Simulate various network failure scenarios for testing resilience."""
    
    def __init__(self):
        self.active_failures: Dict[str, Any] = {}
        self.failure_history: List[Dict[str, Any]] = []
        
    def simulate_network_partition(self, duration_seconds: float = 5.0) -> Dict[str, Any]:
        """Simulate network partition scenario."""
        partition_id = f"partition_{int(time.time() * 1000)}"
        failure_data = self._create_partition_failure(partition_id, duration_seconds)
        self.active_failures[partition_id] = failure_data
        return failure_data
    
    def simulate_packet_loss(self, loss_percentage: float = 50.0) -> Dict[str, Any]:
        """Simulate packet loss scenario."""
        loss_id = f"packet_loss_{int(time.time() * 1000)}"
        failure_data = self._create_packet_loss_failure(loss_id, loss_percentage)
        self.active_failures[loss_id] = failure_data
        return failure_data
    
    def simulate_dns_failure(self, affected_domains: List[str]) -> Dict[str, Any]:
        """Simulate DNS resolution failure."""
        dns_failure_id = f"dns_fail_{int(time.time() * 1000)}"
        failure_data = self._create_dns_failure(dns_failure_id, affected_domains)
        self.active_failures[dns_failure_id] = failure_data
        return failure_data
    
    def simulate_cdn_failure(self, primary_cdn: str, backup_cdn: str) -> Dict[str, Any]:
        """Simulate CDN failure requiring fallback."""
        cdn_failure_id = f"cdn_fail_{int(time.time() * 1000)}"
        failure_data = self._create_cdn_failure(cdn_failure_id, primary_cdn, backup_cdn)
        self.active_failures[cdn_failure_id] = failure_data
        return failure_data
    
    def get_active_failures(self) -> Dict[str, Any]:
        """Get currently active failure simulations."""
        return self.active_failures.copy()
    
    def clear_failure(self, failure_id: str) -> bool:
        """Clear specific failure simulation."""
        if failure_id in self.active_failures:
            cleared_failure = self.active_failures.pop(failure_id)
            self.failure_history.append(cleared_failure)
            return True
        return False
    
    def clear_all_failures(self) -> int:
        """Clear all active failure simulations."""
        count = len(self.active_failures)
        for failure_id in list(self.active_failures.keys()):
            self.clear_failure(failure_id)
        return count
    
    def _create_partition_failure(self, partition_id: str, duration: float) -> Dict[str, Any]:
        """Create network partition failure configuration."""
        base_config = self._get_base_failure_config("network_partition", partition_id)
        partition_specific = self._get_partition_specific_config(duration)
        return {**base_config, **partition_specific}
    
    def _create_packet_loss_failure(self, loss_id: str, percentage: float) -> Dict[str, Any]:
        """Create packet loss failure configuration."""
        base_config = self._get_base_failure_config("packet_loss", loss_id)
        packet_loss_specific = self._get_packet_loss_config(percentage)
        return {**base_config, **packet_loss_specific}
    
    def _create_dns_failure(self, dns_id: str, domains: List[str]) -> Dict[str, Any]:
        """Create DNS failure configuration."""
        base_config = self._get_base_failure_config("dns_failure", dns_id)
        dns_specific = self._get_dns_failure_config(domains)
        return {**base_config, **dns_specific}
    
    def _create_cdn_failure(self, cdn_id: str, primary: str, backup: str) -> Dict[str, Any]:
        """Create CDN failure configuration."""
        base_config = self._get_base_failure_config("cdn_failure", cdn_id)
        cdn_specific = self._get_cdn_failure_config(primary, backup)
        return {**base_config, **cdn_specific}
    
    def _get_base_failure_config(self, failure_type: str, failure_id: str) -> Dict[str, Any]:
        """Get base configuration for all failure types."""
        return {
            "type": failure_type,
            "id": failure_id,
            "start_time": datetime.now(UTC),
            "status": "active"
        }
    
    def _get_partition_specific_config(self, duration: float) -> Dict[str, Any]:
        """Get partition-specific configuration."""
        return {
            "duration_seconds": duration,
            "affected_nodes": ["node_a", "node_b"],
            "split_brain_risk": True,
            "isolation_type": "complete"
        }
    
    def _get_packet_loss_config(self, percentage: float) -> Dict[str, Any]:
        """Get packet loss specific configuration."""
        return {
            "loss_percentage": percentage,
            "pattern": "random",
            "affected_protocols": ["tcp", "udp"],
            "burst_loss": False
        }
    
    def _get_dns_failure_config(self, domains: List[str]) -> Dict[str, Any]:
        """Get DNS failure specific configuration."""
        return {
            "affected_domains": domains,
            "failure_mode": "timeout",
            "backup_dns_enabled": True,
            "resolution_delay_ms": 5000
        }
    
    def _get_cdn_failure_config(self, primary: str, backup: str) -> Dict[str, Any]:
        """Get CDN failure specific configuration."""
        return {
            "primary_cdn": primary,
            "backup_cdn": backup,
            "failover_enabled": True,
            "asset_types": ["js", "css", "images"],
            "cache_invalidation": True
        }


class NetworkResilienceMetrics:
    """Track and analyze network resilience test metrics."""
    
    def __init__(self):
        self.test_results: List[Dict[str, Any]] = []
        
    def record_test_result(self, test_name: str, result: Dict[str, Any]) -> None:
        """Record network resilience test result."""
        test_record = self._create_test_record(test_name, result)
        self.test_results.append(test_record)
        
    def get_success_rate(self, test_type: str = None) -> float:
        """Calculate success rate for network resilience tests."""
        filtered_results = self._filter_results_by_type(test_type)
        if not filtered_results:
            return 0.0
        successful = sum(1 for r in filtered_results if r.get("success", False))
        return (successful / len(filtered_results)) * 100
    
    def get_average_recovery_time(self, test_type: str = None) -> float:
        """Get average recovery time for resilience tests."""
        filtered_results = self._filter_results_by_type(test_type)
        recovery_times = [r.get("recovery_time_ms", 0) for r in filtered_results]
        return sum(recovery_times) / len(recovery_times) if recovery_times else 0.0
    
    def _create_test_record(self, test_name: str, result: Dict[str, Any]) -> Dict[str, Any]:
        """Create test record with metadata."""
        return {
            "test_name": test_name,
            "timestamp": datetime.now(UTC),
            "result": result,
            "success": result.get("success", False)
        }
    
    def _filter_results_by_type(self, test_type: str) -> List[Dict[str, Any]]:
        """Filter test results by type."""
        if test_type is None:
            return self.test_results
        return [r for r in self.test_results if test_type in r.get("test_name", "")]