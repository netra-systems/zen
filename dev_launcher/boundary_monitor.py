"""
Real-time boundary monitoring for development environment.
Follows CLAUDE.md requirements: 300-line limit, 8-line functions.
"""

import time
import threading
import subprocess
import json
from pathlib import Path
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class BoundaryAlert:
    """Boundary violation alert."""
    alert_type: str
    severity: str
    message: str
    file_path: str
    violation_count: int
    timestamp: float


class BoundaryMonitor:
    """Real-time boundary monitoring for development."""
    
    def __init__(self, project_root: Path, check_interval: int = 30):
        """Initialize boundary monitor."""
        self.project_root = project_root
        self.check_interval = check_interval
        self.running = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.callbacks: List[Callable[[BoundaryAlert], None]] = []
        self.last_check_time = 0
        self.violation_history: List[Dict[str, Any]] = []
    
    def add_callback(self, callback: Callable[[BoundaryAlert], None]) -> None:
        """Add alert callback."""
        self.callbacks.append(callback)
        logger.debug("Boundary alert callback registered")
    
    def start_monitoring(self) -> None:
        """Start boundary monitoring thread."""
        if self.running:
            return
        
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        logger.info("Boundary monitoring started")
    
    def stop_monitoring(self) -> None:
        """Stop boundary monitoring."""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
        logger.info("Boundary monitoring stopped")
    
    def force_check(self) -> Dict[str, Any]:
        """Force immediate boundary check."""
        return self._run_boundary_check()
    
    def get_violation_history(self) -> List[Dict[str, Any]]:
        """Get violation history."""
        return self.violation_history.copy()
    
    def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        while self.running:
            try:
                self._check_boundaries()
                time.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Boundary monitoring error: {e}")
                time.sleep(5)  # Short delay on error
    
    def _check_boundaries(self) -> None:
        """Check boundaries and process results."""
        current_time = time.time()
        if current_time - self.last_check_time < self.check_interval:
            return
        
        results = self._run_boundary_check()
        self._process_results(results)
        self.last_check_time = current_time
    
    def _run_boundary_check(self) -> Dict[str, Any]:
        """Run boundary enforcement check."""
        try:
            cmd = [
                "python", "scripts/boundary_enforcer.py",
                "--enforce", "--json-output", "-"
            ]
            
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.stdout:
                return json.loads(result.stdout)
            return {"violations": [], "total_violations": 0}
            
        except Exception as e:
            logger.error(f"Boundary check failed: {e}")
            return {"error": str(e), "violations": [], "total_violations": 0}
    
    def _process_results(self, results: Dict[str, Any]) -> None:
        """Process boundary check results."""
        total_violations = results.get("total_violations", 0)
        violations = results.get("violations", [])
        
        if total_violations == 0:
            return
        
        # Track violation history
        self.violation_history.append({
            "timestamp": time.time(),
            "total_violations": total_violations,
            "violation_types": self._count_violation_types(violations)
        })
        
        # Keep only last 100 history entries
        if len(self.violation_history) > 100:
            self.violation_history.pop(0)
        
        # Generate alerts for critical violations
        self._generate_alerts(violations)
    
    def _count_violation_types(self, violations: List[Dict[str, Any]]) -> Dict[str, int]:
        """Count violations by type."""
        counts = {}
        for violation in violations:
            v_type = violation.get("violation_type", "unknown")
            counts[v_type] = counts.get(v_type, 0) + 1
        return counts
    
    def _generate_alerts(self, violations: List[Dict[str, Any]]) -> None:
        """Generate alerts for violations."""
        critical_violations = [
            v for v in violations 
            if v.get("severity") == "critical"
        ]
        
        if not critical_violations:
            return
        
        for violation in critical_violations[:5]:  # Limit alerts
            alert = BoundaryAlert(
                alert_type=violation.get("violation_type", "unknown"),
                severity=violation.get("severity", "unknown"),
                message=violation.get("description", "Unknown violation"),
                file_path=violation.get("file_path", "unknown"),
                violation_count=len(critical_violations),
                timestamp=time.time()
            )
            self._notify_callbacks(alert)
    
    def _notify_callbacks(self, alert: BoundaryAlert) -> None:
        """Notify all registered callbacks."""
        for callback in self.callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Boundary alert callback error: {e}")


class BoundaryMonitorIntegration:
    """Integration layer for boundary monitoring in dev launcher."""
    
    def __init__(self, config, print_func: Callable[[str, str, str], None]):
        """Initialize integration."""
        self.config = config
        self.print_func = print_func
        self.monitor: Optional[BoundaryMonitor] = None
        self.alert_count = 0
    
    def setup_monitoring(self) -> None:
        """Setup boundary monitoring if enabled."""
        if not self.config.watch_boundaries:
            return
        
        self.monitor = BoundaryMonitor(
            self.config.project_root,
            self.config.boundary_check_interval
        )
        self.monitor.add_callback(self._handle_boundary_alert)
        self.monitor.start_monitoring()
        self.print_func("🔍", "BOUNDARY", "Real-time monitoring enabled")
    
    def cleanup_monitoring(self) -> None:
        """Cleanup boundary monitoring."""
        if self.monitor:
            self.monitor.stop_monitoring()
            self.monitor = None
    
    def get_status(self) -> Dict[str, Any]:
        """Get monitoring status."""
        if not self.monitor:
            return {"enabled": False}
        
        return {
            "enabled": True,
            "alert_count": self.alert_count,
            "history": len(self.monitor.get_violation_history()),
            "last_check": self.monitor.last_check_time
        }
    
    def _handle_boundary_alert(self, alert: BoundaryAlert) -> None:
        """Handle boundary violation alert."""
        self.alert_count += 1
        
        if not self.config.show_boundary_warnings:
            return
        
        # Format alert message
        severity_emoji = "🚨" if alert.severity == "critical" else "⚠️"
        self.print_func(
            severity_emoji, 
            "BOUNDARY", 
            f"{alert.message} ({alert.file_path})"
        )
        
        # Stop services if configured
        if self.config.fail_on_boundary_violations and alert.severity == "critical":
            self.print_func("❌", "BOUNDARY", "Critical violations detected - stopping services")
            # This would trigger service shutdown in the main launcher