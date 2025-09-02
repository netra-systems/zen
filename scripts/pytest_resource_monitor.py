#!/usr/bin/env python3
"""
PyTest Resource Monitor
Advanced monitoring and auto-adjustment for Docker containers during pytest execution.
Prevents OOM kills and container restarts during test collection and execution.
"""

import os
import sys
import time
import json
import logging
import subprocess
import threading
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('pytest_resource_monitor.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class ContainerStats:
    """Container resource statistics"""
    name: str
    memory_usage: int  # bytes
    memory_limit: int  # bytes
    memory_percent: float
    cpu_percent: float
    timestamp: datetime

@dataclass
class ResourceThresholds:
    """Resource alert thresholds"""
    memory_warning: float = 80.0  # %
    memory_critical: float = 90.0  # %
    cpu_warning: float = 80.0  # %
    cpu_critical: float = 90.0  # %

class PytestResourceMonitor:
    """Monitor and manage Docker container resources during pytest execution"""
    
    def __init__(self, compose_file: str = "docker-compose.pytest.yml"):
        self.compose_file = compose_file
        self.thresholds = ResourceThresholds()
        self.monitoring = True
        self.stats_history: Dict[str, List[ContainerStats]] = {}
        self.alerts_sent: Dict[str, set] = {}
        
        # Container configuration
        self.containers = {
            "pytest-backend": {
                "critical": True,
                "memory_base": "6G",
                "memory_max": "8G",
                "auto_adjust": True
            },
            "pytest-auth": {
                "critical": True,
                "memory_base": "3G", 
                "memory_max": "4G",
                "auto_adjust": True
            },
            "pytest-postgres": {
                "critical": True,
                "memory_base": "2G",
                "memory_max": "3G",
                "auto_adjust": False  # Database shouldn't be auto-adjusted
            },
            "pytest-redis": {
                "critical": False,
                "memory_base": "1G",
                "memory_max": "1.5G",
                "auto_adjust": True
            },
            "pytest-clickhouse": {
                "critical": False,
                "memory_base": "2G",
                "memory_max": "3G",
                "auto_adjust": True
            }
        }

    def run_command(self, cmd: List[str], capture_output: bool = True) -> subprocess.CompletedProcess:
        """Run shell command safely"""
        try:
            result = subprocess.run(
                cmd, 
                capture_output=capture_output, 
                text=True, 
                check=True,
                timeout=30
            )
            return result
        except subprocess.CalledProcessError as e:
            logger.error(f"Command failed: {' '.join(cmd)}, Error: {e}")
            raise
        except subprocess.TimeoutExpired as e:
            logger.error(f"Command timed out: {' '.join(cmd)}")
            raise

    def get_container_stats(self) -> Dict[str, ContainerStats]:
        """Get current container resource statistics"""
        stats = {}
        
        try:
            # Get stats for all running containers
            result = self.run_command([
                "docker", "stats", "--no-stream", "--format", 
                "table {{.Container}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.CPUPerc}}"
            ])
            
            lines = result.stdout.strip().split('\n')[1:]  # Skip header
            
            for line in lines:
                if not line.strip():
                    continue
                    
                parts = line.split('\t')
                if len(parts) < 4:
                    continue
                    
                container_name = parts[0].strip()
                
                # Only monitor our pytest containers
                if not any(container_name.startswith(name) for name in self.containers.keys()):
                    continue
                
                # Parse memory usage (e.g., "1.5GiB / 4GiB")
                memory_usage_str = parts[1].strip()
                memory_usage, memory_limit = self._parse_memory_usage(memory_usage_str)
                
                # Parse percentages
                memory_percent = float(parts[2].strip().rstrip('%'))
                cpu_percent = float(parts[3].strip().rstrip('%'))
                
                stats[container_name] = ContainerStats(
                    name=container_name,
                    memory_usage=memory_usage,
                    memory_limit=memory_limit,
                    memory_percent=memory_percent,
                    cpu_percent=cpu_percent,
                    timestamp=datetime.now()
                )
                
        except Exception as e:
            logger.error(f"Failed to get container stats: {e}")
            
        return stats

    def _parse_memory_usage(self, usage_str: str) -> Tuple[int, int]:
        """Parse memory usage string like '1.5GiB / 4GiB' to bytes"""
        try:
            usage_part, limit_part = usage_str.split(' / ')
            usage_bytes = self._parse_size_to_bytes(usage_part.strip())
            limit_bytes = self._parse_size_to_bytes(limit_part.strip())
            return usage_bytes, limit_bytes
        except Exception:
            return 0, 0

    def _parse_size_to_bytes(self, size_str: str) -> int:
        """Convert size string like '1.5GiB' to bytes"""
        size_str = size_str.strip()
        
        # Extract number and unit
        import re
        match = re.match(r'([0-9.]+)\s*([A-Za-z]*)', size_str)
        if not match:
            return 0
            
        number = float(match.group(1))
        unit = match.group(2).upper()
        
        # Convert to bytes
        multipliers = {
            'B': 1,
            'K': 1024, 'KB': 1024, 'KIB': 1024,
            'M': 1024**2, 'MB': 1024**2, 'MIB': 1024**2,
            'G': 1024**3, 'GB': 1024**3, 'GIB': 1024**3,
        }
        
        return int(number * multipliers.get(unit, 1))

    def check_alerts(self, stats: Dict[str, ContainerStats]) -> List[str]:
        """Check for resource threshold violations"""
        alerts = []
        
        for container_name, container_stats in stats.items():
            # Initialize alerts tracking for container
            if container_name not in self.alerts_sent:
                self.alerts_sent[container_name] = set()
            
            # Memory alerts
            if container_stats.memory_percent >= self.thresholds.memory_critical:
                alert_key = f"{container_name}_memory_critical"
                if alert_key not in self.alerts_sent[container_name]:
                    alert_msg = (f"CRITICAL: {container_name} memory usage at "
                               f"{container_stats.memory_percent:.1f}% "
                               f"({container_stats.memory_usage / 1024**3:.1f}GB)")
                    alerts.append(alert_msg)
                    self.alerts_sent[container_name].add(alert_key)
                    
            elif container_stats.memory_percent >= self.thresholds.memory_warning:
                alert_key = f"{container_name}_memory_warning"
                if alert_key not in self.alerts_sent[container_name]:
                    alert_msg = (f"WARNING: {container_name} memory usage at "
                               f"{container_stats.memory_percent:.1f}% "
                               f"({container_stats.memory_usage / 1024**3:.1f}GB)")
                    alerts.append(alert_msg)
                    self.alerts_sent[container_name].add(alert_key)
            
            # CPU alerts
            if container_stats.cpu_percent >= self.thresholds.cpu_critical:
                alert_key = f"{container_name}_cpu_critical"
                if alert_key not in self.alerts_sent[container_name]:
                    alert_msg = f"CRITICAL: {container_name} CPU usage at {container_stats.cpu_percent:.1f}%"
                    alerts.append(alert_msg)
                    self.alerts_sent[container_name].add(alert_key)
                    
        return alerts

    def auto_adjust_resources(self, stats: Dict[str, ContainerStats]) -> bool:
        """Automatically adjust container resources if needed"""
        adjusted = False
        
        for container_name, container_stats in stats.items():
            # Find base container name (remove instance suffix)
            base_name = None
            for name in self.containers.keys():
                if container_name.startswith(name):
                    base_name = name
                    break
                    
            if not base_name or not self.containers[base_name]["auto_adjust"]:
                continue
                
            # Check if memory usage is critical and we can increase limit
            if container_stats.memory_percent >= 85.0:  # Adjust before critical
                current_limit_gb = container_stats.memory_limit / (1024**3)
                max_limit_str = self.containers[base_name]["memory_max"]
                max_limit_gb = self._parse_size_to_bytes(max_limit_str) / (1024**3)
                
                if current_limit_gb < max_limit_gb:
                    new_limit_gb = min(current_limit_gb * 1.2, max_limit_gb)  # Increase by 20%
                    
                    try:
                        logger.info(f"Auto-adjusting {container_name} memory limit: "
                                  f"{current_limit_gb:.1f}GB -> {new_limit_gb:.1f}GB")
                        
                        # Update container memory limit
                        self.run_command([
                            "docker", "update", "--memory", f"{new_limit_gb:.0f}g", 
                            container_name
                        ])
                        adjusted = True
                        
                    except Exception as e:
                        logger.error(f"Failed to adjust memory for {container_name}: {e}")
                        
        return adjusted

    def save_stats_report(self, stats: Dict[str, ContainerStats]):
        """Save detailed stats report to file"""
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "containers": {}
        }
        
        for name, container_stats in stats.items():
            report_data["containers"][name] = {
                "memory_usage_gb": container_stats.memory_usage / (1024**3),
                "memory_limit_gb": container_stats.memory_limit / (1024**3),
                "memory_percent": container_stats.memory_percent,
                "cpu_percent": container_stats.cpu_percent,
                "timestamp": container_stats.timestamp.isoformat()
            }
        
        # Save to timestamped file
        report_file = f"pytest_resource_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report_data, f, indent=2)

    def monitor_loop(self, interval: int = 15):
        """Main monitoring loop"""
        logger.info("Starting PyTest resource monitor...")
        logger.info(f"Monitoring interval: {interval} seconds")
        logger.info(f"Compose file: {self.compose_file}")
        
        consecutive_errors = 0
        max_errors = 10
        
        while self.monitoring:
            try:
                # Get current stats
                stats = self.get_container_stats()
                
                if not stats:
                    logger.warning("No container stats retrieved")
                    consecutive_errors += 1
                    if consecutive_errors >= max_errors:
                        logger.error("Too many consecutive errors, stopping monitor")
                        break
                    time.sleep(interval)
                    continue
                
                consecutive_errors = 0  # Reset error counter
                
                # Store stats history
                for name, container_stats in stats.items():
                    if name not in self.stats_history:
                        self.stats_history[name] = []
                    self.stats_history[name].append(container_stats)
                    
                    # Keep only last 100 entries
                    if len(self.stats_history[name]) > 100:
                        self.stats_history[name] = self.stats_history[name][-100:]
                
                # Check for alerts
                alerts = self.check_alerts(stats)
                for alert in alerts:
                    logger.warning(alert)
                
                # Auto-adjust resources if needed
                if self.auto_adjust_resources(stats):
                    logger.info("Resources auto-adjusted")
                
                # Log current status
                logger.info("=== Resource Status ===")
                for name, container_stats in stats.items():
                    logger.info(f"{name}: Memory {container_stats.memory_percent:.1f}%, "
                              f"CPU {container_stats.cpu_percent:.1f}%")
                
                # Save periodic report
                if len(self.stats_history) > 0 and len(next(iter(self.stats_history.values()))) % 20 == 0:
                    self.save_stats_report(stats)
                
                time.sleep(interval)
                
            except KeyboardInterrupt:
                logger.info("Received interrupt signal, stopping monitor...")
                break
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                consecutive_errors += 1
                if consecutive_errors >= max_errors:
                    logger.error("Too many consecutive errors, stopping monitor")
                    break
                time.sleep(interval)
        
        logger.info("PyTest resource monitor stopped")

    def stop_monitoring(self):
        """Stop the monitoring loop"""
        self.monitoring = False

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="PyTest Resource Monitor")
    parser.add_argument("--compose-file", default="docker-compose.pytest.yml",
                       help="Docker compose file to monitor")
    parser.add_argument("--interval", type=int, default=15,
                       help="Monitoring interval in seconds")
    parser.add_argument("--memory-warning", type=float, default=80.0,
                       help="Memory warning threshold percentage")
    parser.add_argument("--memory-critical", type=float, default=90.0,
                       help="Memory critical threshold percentage")
    
    args = parser.parse_args()
    
    # Create monitor
    monitor = PytestResourceMonitor(args.compose_file)
    monitor.thresholds.memory_warning = args.memory_warning
    monitor.thresholds.memory_critical = args.memory_critical
    
    # Start monitoring
    try:
        monitor.monitor_loop(args.interval)
    except KeyboardInterrupt:
        logger.info("Monitor stopped by user")
    except Exception as e:
        logger.error(f"Monitor failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()