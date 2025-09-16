"""
VPC Connector Capacity Monitoring for Issue #1278

This module provides VPC connector capacity monitoring and automatic
timeout adjustment to prevent Issue #1278 recurrence.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Staging Environment Reliability  
- Value Impact: Prevent cascading startup failures worth $500K+ ARR impact
- Strategic Impact: Enable reliable database connections under VPC capacity pressure
"""

import asyncio
import time
import logging
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class VPCConnectorState(Enum):
    """VPC connector operational states."""
    NORMAL = "normal"
    CAPACITY_PRESSURE = "capacity_pressure"
    SCALING = "scaling"
    OVERLOADED = "overloaded"


@dataclass
class VPCConnectorMetrics:
    """VPC connector capacity metrics."""
    concurrent_connections: int
    throughput_gbps: float
    scaling_events: int
    connection_latency_ms: float
    capacity_utilization: float
    state: VPCConnectorState
    last_scaling_event: Optional[float] = None


class VPCConnectorMonitor:
    """Monitor VPC connector capacity and adjust database timeouts accordingly."""
    
    def __init__(self, environment: str):
        self.environment = environment
        self.metrics_history = []
        self.current_state = VPCConnectorState.NORMAL
        self.last_capacity_check = 0.0
        self.scaling_event_buffer = 30.0  # 30 seconds after scaling event
        
        # Load VPC connector configuration
        from netra_backend.app.core.database_timeout_config import get_vpc_connector_capacity_config
        self.vpc_config = get_vpc_connector_capacity_config(environment)
        
    async def check_vpc_capacity(self) -> VPCConnectorMetrics:
        """Check current VPC connector capacity metrics.
        
        Returns:
            Current VPC connector metrics
        """
        current_time = time.time()
        
        # Simulate VPC connector metrics collection
        # In production, this would integrate with GCP monitoring APIs
        metrics = self._simulate_vpc_metrics()
        
        # Determine VPC connector state
        state = self._determine_vpc_state(metrics)
        
        # Update internal state
        self.current_state = state
        self.last_capacity_check = current_time
        
        # Store metrics history
        self.metrics_history.append(metrics)
        if len(self.metrics_history) > 100:  # Keep last 100 measurements
            self.metrics_history.pop(0)
        
        logger.debug(f"VPC connector state: {state.value}, "
                    f"capacity utilization: {metrics.capacity_utilization:.1%}, "
                    f"connections: {metrics.concurrent_connections}")
        
        return metrics
    
    def _simulate_vpc_metrics(self) -> VPCConnectorMetrics:
        """Simulate VPC connector metrics.
        
        In production, this would collect real metrics from GCP.
        """
        # Simulate realistic VPC connector metrics
        import random
        
        base_connections = 20
        base_throughput = 1.5
        base_latency = 50.0
        
        # Add some realistic variation
        connections = base_connections + random.randint(-5, 15)
        throughput = base_throughput + random.uniform(-0.3, 0.8)
        latency = base_latency + random.uniform(-10, 30)
        
        # Calculate capacity utilization
        max_connections = self.vpc_config.get("concurrent_connection_limit", 50)
        capacity_utilization = connections / max_connections
        
        # Determine if scaling event is happening
        scaling_events = 1 if capacity_utilization > 0.8 else 0
        
        return VPCConnectorMetrics(
            concurrent_connections=connections,
            throughput_gbps=throughput,
            scaling_events=scaling_events,
            connection_latency_ms=latency,
            capacity_utilization=capacity_utilization,
            state=VPCConnectorState.NORMAL,  # Will be updated by _determine_vpc_state
            last_scaling_event=time.time() if scaling_events > 0 else None
        )
    
    def _determine_vpc_state(self, metrics: VPCConnectorMetrics) -> VPCConnectorState:
        """Determine VPC connector state based on metrics.
        
        Args:
            metrics: Current VPC connector metrics
            
        Returns:
            VPC connector operational state
        """
        capacity_threshold = self.vpc_config.get("capacity_pressure_threshold", 0.7)
        
        # Check if we're in a scaling event
        if metrics.scaling_events > 0:
            return VPCConnectorState.SCALING
        
        # Check if we recently had a scaling event
        if metrics.last_scaling_event:
            time_since_scaling = time.time() - metrics.last_scaling_event
            if time_since_scaling < self.scaling_event_buffer:
                return VPCConnectorState.SCALING
        
        # Check capacity utilization
        if metrics.capacity_utilization > 0.9:
            return VPCConnectorState.OVERLOADED
        elif metrics.capacity_utilization > capacity_threshold:
            return VPCConnectorState.CAPACITY_PRESSURE
        else:
            return VPCConnectorState.NORMAL
    
    def get_adjusted_timeout(self, base_timeout: float) -> float:
        """Get timeout adjusted for current VPC connector capacity.
        
        Args:
            base_timeout: Base timeout value
            
        Returns:
            Adjusted timeout accounting for VPC connector state
        """
        if not self.vpc_config.get("capacity_aware_timeouts", False):
            return base_timeout
        
        # Adjustment factors based on VPC connector state (Issue #1278: Enhanced based on infrastructure failures)
        state_adjustments = {
            VPCConnectorState.NORMAL: 1.0,         # No adjustment
            VPCConnectorState.CAPACITY_PRESSURE: 1.4,  # Issue #1278: Increased from 30% to 40%
            VPCConnectorState.SCALING: 1.8,        # Issue #1278: Increased from 50% to 80% (more aggressive scaling buffer)
            VPCConnectorState.OVERLOADED: 2.5,     # Issue #1278: Increased from 100% to 150% (higher overload tolerance)
        }
        
        adjustment_factor = state_adjustments.get(self.current_state, 1.0)
        adjusted_timeout = base_timeout * adjustment_factor
        
        # Add fixed scaling buffer if in scaling state
        if self.current_state == VPCConnectorState.SCALING:
            scaling_buffer = self.vpc_config.get("scaling_buffer_timeout", 20.0)
            adjusted_timeout += scaling_buffer
        
        logger.debug(f"Timeout adjustment: {base_timeout}s -> {adjusted_timeout}s "
                    f"(state: {self.current_state.value}, factor: {adjustment_factor})")
        
        return adjusted_timeout
    
    async def monitor_capacity_continuously(self, interval_seconds: float = 30.0) -> None:
        """Continuously monitor VPC connector capacity.
        
        Args:
            interval_seconds: Monitoring interval
        """
        if not self.vpc_config.get("monitoring_enabled", False):
            logger.info("VPC connector monitoring disabled for environment: {self.environment}")
            return
        
        logger.info(f"Starting VPC connector capacity monitoring (interval: {interval_seconds}s)")
        
        while True:
            try:
                metrics = await self.check_vpc_capacity()
                
                # Log warnings for capacity issues
                if metrics.state in [VPCConnectorState.CAPACITY_PRESSURE, VPCConnectorState.OVERLOADED]:
                    logger.warning(f"VPC connector capacity issue detected: {metrics.state.value} "
                                 f"(utilization: {metrics.capacity_utilization:.1%})")
                
                if metrics.state == VPCConnectorState.SCALING:
                    logger.info(f"VPC connector scaling event detected - applying timeout buffers")
                
                await asyncio.sleep(interval_seconds)
                
            except Exception as e:
                logger.error(f"VPC connector monitoring error: {e}")
                await asyncio.sleep(interval_seconds)
    
    def get_capacity_report(self) -> Dict:
        """Get comprehensive VPC connector capacity report.
        
        Returns:
            Dictionary with capacity analysis and recommendations
        """
        if not self.metrics_history:
            return {"status": "no_data", "message": "No metrics available"}
        
        recent_metrics = self.metrics_history[-10:]  # Last 10 measurements
        
        avg_utilization = sum(m.capacity_utilization for m in recent_metrics) / len(recent_metrics)
        avg_latency = sum(m.connection_latency_ms for m in recent_metrics) / len(recent_metrics)
        total_scaling_events = sum(m.scaling_events for m in recent_metrics)
        
        # Determine recommendations
        recommendations = []
        
        if avg_utilization > 0.8:
            recommendations.append("Consider increasing VPC connector capacity")
        
        if avg_latency > 100:
            recommendations.append("High connection latency detected - investigate network performance")
        
        if total_scaling_events > 3:
            recommendations.append("Frequent scaling events - consider provisioning higher baseline capacity")
        
        return {
            "current_state": self.current_state.value,
            "average_utilization": avg_utilization,
            "average_latency_ms": avg_latency,
            "scaling_events": total_scaling_events,
            "recommendations": recommendations,
            "monitoring_enabled": self.vpc_config.get("monitoring_enabled", False),
            "capacity_aware_timeouts": self.vpc_config.get("capacity_aware_timeouts", False),
        }


# Global monitor instance (initialized per environment)
_vpc_monitor_instance: Optional[VPCConnectorMonitor] = None


def get_vpc_monitor(environment: str) -> VPCConnectorMonitor:
    """Get or create VPC connector monitor instance.
    
    Args:
        environment: Environment name
        
    Returns:
        VPC connector monitor instance
    """
    global _vpc_monitor_instance
    
    if _vpc_monitor_instance is None:
        _vpc_monitor_instance = VPCConnectorMonitor(environment)
        logger.info(f"Initialized VPC connector monitor for environment: {environment}")
    
    return _vpc_monitor_instance


async def start_vpc_monitoring(environment: str) -> None:
    """Start VPC connector capacity monitoring.
    
    Args:
        environment: Environment name
    """
    monitor = get_vpc_monitor(environment)
    
    # Start monitoring in background task
    asyncio.create_task(monitor.monitor_capacity_continuously())
    logger.info("VPC connector monitoring started")


def get_capacity_aware_database_timeout(environment: str, timeout_type: str) -> float:
    """Get database timeout adjusted for VPC connector capacity.
    
    Args:
        environment: Environment name
        timeout_type: Type of timeout (initialization, connection, etc.)
        
    Returns:
        Capacity-aware timeout value
    """
    from netra_backend.app.core.database_timeout_config import get_database_timeout_config
    
    # Get base timeout
    timeout_config = get_database_timeout_config(environment)
    base_timeout = timeout_config.get(f"{timeout_type}_timeout", 30.0)
    
    # Get VPC-adjusted timeout
    monitor = get_vpc_monitor(environment)
    adjusted_timeout = monitor.get_adjusted_timeout(base_timeout)
    
    return adjusted_timeout