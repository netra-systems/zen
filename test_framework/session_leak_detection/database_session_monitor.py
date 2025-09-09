"""
Database Session Monitor - Real-Time Session Pool Monitoring

This monitor tracks the database connection pool state and provides
metrics about session usage patterns to detect potential leaks.

CRITICAL: Designed to expose session management issues by monitoring
actual database connection pool statistics.
"""

import asyncio
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.pool import Pool

logger = logging.getLogger(__name__)


@dataclass
class ConnectionPoolSnapshot:
    """Snapshot of connection pool state at a point in time."""
    timestamp: datetime
    pool_size: int
    checked_in: int
    checked_out: int
    overflow: int
    total_connections: int
    
    @property
    def utilization_percent(self) -> float:
        """Calculate pool utilization percentage."""
        if self.pool_size == 0:
            return 0.0
        return (self.checked_out / self.pool_size) * 100.0


class DatabaseSessionMonitor:
    """
    Monitors database session pool for leak detection.
    
    This monitor provides real-time insights into:
    1. Connection pool utilization
    2. Session checkout/checkin patterns
    3. Long-running sessions
    4. Pool exhaustion indicators
    
    CRITICAL: Used to detect session leaks by monitoring pool state changes.
    """
    
    def __init__(self, engine: AsyncEngine, monitoring_interval: float = 1.0):
        """
        Initialize database session monitor.
        
        Args:
            engine: SQLAlchemy AsyncEngine to monitor
            monitoring_interval: How often to snapshot pool state (seconds)
        """
        self.engine = engine
        self.monitoring_interval = monitoring_interval
        self.snapshots: List[ConnectionPoolSnapshot] = []
        self.monitoring = False
        self.monitor_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        
    async def start_monitoring(self):
        """Start real-time pool monitoring."""
        if self.monitoring:
            return
            
        self.monitoring = True
        self.monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("Started database session pool monitoring")
    
    async def stop_monitoring(self):
        """Stop pool monitoring."""
        if not self.monitoring:
            return
            
        self.monitoring = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
            
        logger.info("Stopped database session pool monitoring")
    
    async def _monitor_loop(self):
        """Main monitoring loop."""
        while self.monitoring:
            try:
                await self._take_snapshot()
                await asyncio.sleep(self.monitoring_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
                await asyncio.sleep(self.monitoring_interval)
    
    async def _take_snapshot(self):
        """Take a snapshot of current pool state."""
        try:
            pool = self.engine.pool
            
            # Get pool statistics
            snapshot = ConnectionPoolSnapshot(
                timestamp=datetime.now(timezone.utc),
                pool_size=pool.size(),
                checked_in=pool.checkedin(),
                checked_out=pool.checkedout(),
                overflow=pool.overflow(),
                total_connections=pool.size() + pool.overflow()
            )
            
            async with self._lock:
                self.snapshots.append(snapshot)
                
                # Keep only last 1000 snapshots to prevent memory issues
                if len(self.snapshots) > 1000:
                    self.snapshots = self.snapshots[-500:]
                    
        except Exception as e:
            logger.error(f"Failed to take pool snapshot: {e}")
    
    async def get_current_pool_state(self) -> Optional[ConnectionPoolSnapshot]:
        """Get current pool state."""
        await self._take_snapshot()
        async with self._lock:
            return self.snapshots[-1] if self.snapshots else None
    
    async def detect_session_leaks(self, baseline_duration: float = 5.0) -> Dict[str, Any]:
        """
        Detect potential session leaks by analyzing pool usage patterns.
        
        Args:
            baseline_duration: Duration to analyze for leak patterns (seconds)
            
        Returns:
            Dictionary with leak analysis results
        """
        async with self._lock:
            if len(self.snapshots) < 2:
                return {'leak_detected': False, 'reason': 'insufficient_data'}
            
            current_time = datetime.now(timezone.utc)
            baseline_cutoff = current_time.timestamp() - baseline_duration
            
            # Filter snapshots within baseline duration
            relevant_snapshots = [
                snapshot for snapshot in self.snapshots
                if snapshot.timestamp.timestamp() >= baseline_cutoff
            ]
            
            if len(relevant_snapshots) < 2:
                return {'leak_detected': False, 'reason': 'insufficient_baseline_data'}
            
            # Analyze patterns
            first_snapshot = relevant_snapshots[0]
            last_snapshot = relevant_snapshots[-1]
            
            # Detect increasing checked_out connections without corresponding checkin
            checkout_increase = last_snapshot.checked_out - first_snapshot.checked_out
            
            # Detect high utilization sustained over time
            high_utilization_snapshots = [
                snapshot for snapshot in relevant_snapshots
                if snapshot.utilization_percent > 80.0
            ]
            high_utilization_ratio = len(high_utilization_snapshots) / len(relevant_snapshots)
            
            # Detect overflow usage (indicates pool exhaustion)
            overflow_snapshots = [
                snapshot for snapshot in relevant_snapshots
                if snapshot.overflow > 0
            ]
            
            analysis = {
                'leak_detected': False,
                'leak_indicators': [],
                'checkout_increase': checkout_increase,
                'high_utilization_ratio': high_utilization_ratio,
                'overflow_events': len(overflow_snapshots),
                'max_utilization': max(s.utilization_percent for s in relevant_snapshots),
                'current_checked_out': last_snapshot.checked_out,
                'snapshots_analyzed': len(relevant_snapshots),
                'analysis_duration': baseline_duration
            }
            
            # Leak indicators
            if checkout_increase > 2:
                analysis['leak_detected'] = True
                analysis['leak_indicators'].append(
                    f"Session checkout increased by {checkout_increase} without corresponding returns"
                )
            
            if high_utilization_ratio > 0.7:  # 70% of time in high utilization
                analysis['leak_detected'] = True
                analysis['leak_indicators'].append(
                    f"High pool utilization ({high_utilization_ratio:.1%} of time above 80%)"
                )
            
            if len(overflow_snapshots) > 0:
                analysis['leak_detected'] = True
                analysis['leak_indicators'].append(
                    f"Connection pool overflow detected in {len(overflow_snapshots)} snapshots"
                )
            
            return analysis
    
    async def get_monitoring_report(self) -> Dict[str, Any]:
        """
        Get comprehensive monitoring report.
        
        Returns:
            Dictionary with monitoring statistics and analysis
        """
        async with self._lock:
            if not self.snapshots:
                return {'error': 'no_monitoring_data'}
            
            current_snapshot = self.snapshots[-1]
            
            # Calculate statistics
            utilizations = [s.utilization_percent for s in self.snapshots]
            checked_outs = [s.checked_out for s in self.snapshots]
            
            report = {
                'monitoring_active': self.monitoring,
                'total_snapshots': len(self.snapshots),
                'monitoring_duration_seconds': (
                    self.snapshots[-1].timestamp - self.snapshots[0].timestamp
                ).total_seconds() if len(self.snapshots) > 1 else 0,
                
                'current_state': {
                    'pool_size': current_snapshot.pool_size,
                    'checked_out': current_snapshot.checked_out,
                    'checked_in': current_snapshot.checked_in,
                    'overflow': current_snapshot.overflow,
                    'utilization_percent': current_snapshot.utilization_percent
                },
                
                'statistics': {
                    'max_utilization': max(utilizations) if utilizations else 0,
                    'min_utilization': min(utilizations) if utilizations else 0,
                    'avg_utilization': sum(utilizations) / len(utilizations) if utilizations else 0,
                    'max_checked_out': max(checked_outs) if checked_outs else 0,
                    'peak_overflow': max(s.overflow for s in self.snapshots) if self.snapshots else 0
                }
            }
            
            return report
    
    def assert_healthy_pool_state(self, max_utilization: float = 90.0):
        """
        Assert that pool state is healthy. FAILS if session leaks detected.
        
        Args:
            max_utilization: Maximum allowed pool utilization percentage
        
        This method implements CLAUDE.md testing principle:
        "Tests MUST raise errors" and "CHEATING ON TESTS = ABOMINATION"
        """
        if not self.snapshots:
            raise AssertionError("No monitoring data available to assess pool health")
        
        current_snapshot = self.snapshots[-1]
        
        # Check for pool exhaustion
        if current_snapshot.overflow > 0:
            raise AssertionError(
                f"CONNECTION POOL EXHAUSTION DETECTED!\n"
                f"Pool overflow: {current_snapshot.overflow} connections\n"
                f"This indicates session leaks causing pool depletion.\n"
                f"Total pool size: {current_snapshot.pool_size}\n"
                f"Checked out: {current_snapshot.checked_out}\n"
                f"CRITICAL: Fix session management to prevent production failures."
            )
        
        # Check for high utilization
        if current_snapshot.utilization_percent > max_utilization:
            raise AssertionError(
                f"HIGH CONNECTION POOL UTILIZATION DETECTED!\n"
                f"Current utilization: {current_snapshot.utilization_percent:.1f}%\n"
                f"Maximum allowed: {max_utilization}%\n"
                f"Checked out: {current_snapshot.checked_out}/{current_snapshot.pool_size}\n"
                f"This may indicate session leaks or insufficient pool size.\n"
                f"Review session management in thread handlers."
            )
    
    async def cleanup(self):
        """Clean up monitor state."""
        await self.stop_monitoring()
        async with self._lock:
            self.snapshots.clear()