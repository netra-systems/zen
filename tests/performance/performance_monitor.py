#!/usr/bin/env python3
"""
Real-time Performance Monitor for UserExecutionContext Migration

This module provides real-time monitoring capabilities for the UserExecutionContext
migration performance, allowing continuous observation of system metrics.

Features:
1. Real-time system resource monitoring
2. Performance trend analysis
3. Threshold violation detection
4. Automated alerts
5. Performance visualization
6. Historical data collection

Usage:
    python performance_monitor.py --duration 300 --interval 1
    python performance_monitor.py --monitor-user user123 --output metrics.json
"""

import argparse
import asyncio
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import deque, defaultdict

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    import psutil
    from netra_backend.app.logging_config import central_logger
except ImportError as e:
    print(f"Error importing required modules: {e}")
    sys.exit(1)

logger = central_logger.get_logger(__name__)


class PerformanceMonitor:
    """Real-time performance monitor for UserExecutionContext system."""
    
    def __init__(self, sample_interval: float = 1.0, max_samples: int = 1000):
        self.sample_interval = sample_interval
        self.max_samples = max_samples
        self.samples = deque(maxlen=max_samples)
        self.user_metrics = defaultdict(lambda: deque(maxlen=100))
        self.alerts_generated = []
        self.monitoring_start = None
        self.monitoring_active = False
        
        # Load performance thresholds
        self.thresholds = self._load_thresholds()
        
    def _load_thresholds(self) -> Dict[str, Any]:
        """Load performance thresholds from configuration."""
        try:
            thresholds_file = Path(__file__).parent / "performance_thresholds.json"
            if thresholds_file.exists():
                with open(thresholds_file, 'r') as f:
                    config = json.load(f)
                    return config.get('performance_thresholds', {})
        except Exception as e:
            logger.warning(f"Could not load performance thresholds: {e}")
        
        # Default thresholds
        return {
            'memory_management': {
                'baseline_memory_max_mb': 200,
                'peak_memory_max_mb': 500,
                'memory_growth_max_mb_per_1k_requests': 20
            },
            'concurrent_requests': {
                'min_success_rate_percent': 95,
                'max_p95_response_time_ms': 500
            }
        }
    
    def start_monitoring(self):
        """Start performance monitoring."""
        self.monitoring_start = time.time()
        self.monitoring_active = True
        logger.info("Performance monitoring started")
    
    def stop_monitoring(self):
        """Stop performance monitoring."""
        self.monitoring_active = False
        logger.info("Performance monitoring stopped")
    
    def take_system_sample(self) -> Dict[str, Any]:
        """Take comprehensive system performance sample."""
        timestamp = time.time()
        process = psutil.Process()
        
        # System metrics
        system_memory = psutil.virtual_memory()
        system_cpu = psutil.cpu_percent(interval=None)
        
        # Process metrics
        process_memory = process.memory_info()
        
        sample = {
            'timestamp': timestamp,
            'datetime': datetime.fromtimestamp(timestamp, timezone.utc).isoformat(),
            'system': {
                'memory_percent': system_memory.percent,
                'memory_available_mb': system_memory.available / 1024 / 1024,
                'memory_used_mb': system_memory.used / 1024 / 1024,
                'cpu_percent': system_cpu,
                'load_average': os.getloadavg() if hasattr(os, 'getloadavg') else [0, 0, 0]
            },
            'process': {
                'memory_rss_mb': process_memory.rss / 1024 / 1024,
                'memory_vms_mb': process_memory.vms / 1024 / 1024,
                'cpu_percent': process.cpu_percent(),
                'threads': process.num_threads(),
                'open_files': len(process.open_files()),
                'connections': len(process.connections())
            }
        }
        
        self.samples.append(sample)
        return sample
    
    def check_thresholds(self, sample: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check sample against performance thresholds."""
        alerts = []
        
        # Memory threshold checks
        process_memory_mb = sample['process']['memory_rss_mb']
        system_memory_percent = sample['system']['memory_percent']
        
        memory_thresholds = self.thresholds.get('memory_management', {})
        
        if process_memory_mb > memory_thresholds.get('baseline_memory_max_mb', 200):
            alerts.append({
                'level': 'WARNING',
                'category': 'memory',
                'message': f"Process memory high: {process_memory_mb:.2f}MB",
                'threshold': memory_thresholds.get('baseline_memory_max_mb', 200),
                'actual': process_memory_mb,
                'timestamp': sample['timestamp']
            })
        
        if process_memory_mb > memory_thresholds.get('peak_memory_max_mb', 500):
            alerts.append({
                'level': 'CRITICAL',
                'category': 'memory',
                'message': f"Process memory critical: {process_memory_mb:.2f}MB",
                'threshold': memory_thresholds.get('peak_memory_max_mb', 500),
                'actual': process_memory_mb,
                'timestamp': sample['timestamp']
            })
        
        if system_memory_percent > 90:
            alerts.append({
                'level': 'CRITICAL',
                'category': 'system_memory',
                'message': f"System memory critical: {system_memory_percent:.1f}%",
                'threshold': 90,
                'actual': system_memory_percent,
                'timestamp': sample['timestamp']
            })
        
        # CPU threshold checks
        process_cpu = sample['process']['cpu_percent']
        system_cpu = sample['system']['cpu_percent']
        
        if process_cpu > 80:
            alerts.append({
                'level': 'WARNING',
                'category': 'cpu',
                'message': f"Process CPU high: {process_cpu:.1f}%",
                'threshold': 80,
                'actual': process_cpu,
                'timestamp': sample['timestamp']
            })
        
        if system_cpu > 90:
            alerts.append({
                'level': 'CRITICAL',
                'category': 'system_cpu',
                'message': f"System CPU critical: {system_cpu:.1f}%",
                'threshold': 90,
                'actual': system_cpu,
                'timestamp': sample['timestamp']
            })
        
        # Resource leak checks
        open_files = sample['process']['open_files']
        connections = sample['process']['connections']
        
        if open_files > 500:
            alerts.append({
                'level': 'WARNING',
                'category': 'file_handles',
                'message': f"High file handle count: {open_files}",
                'threshold': 500,
                'actual': open_files,
                'timestamp': sample['timestamp']
            })
        
        if connections > 100:
            alerts.append({
                'level': 'WARNING',
                'category': 'connections',
                'message': f"High connection count: {connections}",
                'threshold': 100,
                'actual': connections,
                'timestamp': sample['timestamp']
            })
        
        return alerts
    
    async def monitor_continuously(self, duration_seconds: int) -> Dict[str, Any]:
        """Monitor performance continuously for specified duration."""
        self.start_monitoring()
        
        logger.info(f"Starting continuous monitoring for {duration_seconds} seconds...")
        
        try:
            end_time = time.time() + duration_seconds
            sample_count = 0
            
            while time.time() < end_time and self.monitoring_active:
                # Take performance sample
                sample = self.take_system_sample()
                sample_count += 1
                
                # Check thresholds
                alerts = self.check_thresholds(sample)
                for alert in alerts:
                    self.alerts_generated.append(alert)
                    logger.warning(f"Performance alert: {alert['message']}")
                
                # Log periodic status
                if sample_count % 30 == 0:  # Every 30 samples
                    logger.info(f"Monitoring sample {sample_count}: "
                               f"Memory {sample['process']['memory_rss_mb']:.1f}MB, "
                               f"CPU {sample['process']['cpu_percent']:.1f}%")
                
                # Wait for next sample
                await asyncio.sleep(self.sample_interval)
            
            logger.info(f"Continuous monitoring completed: {sample_count} samples collected")
            
        except KeyboardInterrupt:
            logger.info("Monitoring interrupted by user")
        except Exception as e:
            logger.error(f"Error during continuous monitoring: {e}")
        finally:
            self.stop_monitoring()
        
        return self.generate_monitoring_report()
    
    def generate_monitoring_report(self) -> Dict[str, Any]:
        """Generate comprehensive monitoring report."""
        if not self.samples:
            return {'error': 'No samples collected'}
        
        # Calculate summary statistics
        memory_values = [s['process']['memory_rss_mb'] for s in self.samples]
        cpu_values = [s['process']['cpu_percent'] for s in self.samples]
        
        duration = (self.samples[-1]['timestamp'] - self.samples[0]['timestamp'])
        
        report = {
            'monitoring_summary': {
                'duration_seconds': duration,
                'total_samples': len(self.samples),
                'sample_interval': self.sample_interval,
                'alerts_generated': len(self.alerts_generated),
                'monitoring_period': {
                    'start': self.samples[0]['datetime'],
                    'end': self.samples[-1]['datetime']
                }
            },
            'memory_analysis': {
                'min_mb': min(memory_values),
                'max_mb': max(memory_values),
                'avg_mb': sum(memory_values) / len(memory_values),
                'growth_mb': memory_values[-1] - memory_values[0],
                'peak_growth_mb': max(memory_values) - memory_values[0],
                'samples': len(memory_values)
            },
            'cpu_analysis': {
                'min_percent': min(cpu_values),
                'max_percent': max(cpu_values),
                'avg_percent': sum(cpu_values) / len(cpu_values),
                'samples': len(cpu_values)
            },
            'alerts': {
                'total': len(self.alerts_generated),
                'by_level': self._group_alerts_by_level(),
                'by_category': self._group_alerts_by_category(),
                'critical_alerts': [a for a in self.alerts_generated if a['level'] == 'CRITICAL'],
                'warning_alerts': [a for a in self.alerts_generated if a['level'] == 'WARNING']
            },
            'system_health': self._assess_system_health(),
            'recommendations': self._generate_monitoring_recommendations()
        }
        
        return report
    
    def _group_alerts_by_level(self) -> Dict[str, int]:
        """Group alerts by severity level."""
        levels = {}
        for alert in self.alerts_generated:
            level = alert.get('level', 'UNKNOWN')
            levels[level] = levels.get(level, 0) + 1
        return levels
    
    def _group_alerts_by_category(self) -> Dict[str, int]:
        """Group alerts by category."""
        categories = {}
        for alert in self.alerts_generated:
            category = alert.get('category', 'unknown')
            categories[category] = categories.get(category, 0) + 1
        return categories
    
    def _assess_system_health(self) -> Dict[str, Any]:
        """Assess overall system health based on samples."""
        if not self.samples:
            return {'status': 'NO_DATA'}
        
        recent_samples = list(self.samples)[-10:]  # Last 10 samples
        
        avg_memory = sum(s['process']['memory_rss_mb'] for s in recent_samples) / len(recent_samples)
        avg_cpu = sum(s['process']['cpu_percent'] for s in recent_samples) / len(recent_samples)
        
        # Determine health status
        health_status = 'HEALTHY'
        health_issues = []
        
        if avg_memory > 400:
            health_status = 'CRITICAL'
            health_issues.append(f"High memory usage: {avg_memory:.1f}MB")
        elif avg_memory > 250:
            health_status = 'WARNING'
            health_issues.append(f"Elevated memory usage: {avg_memory:.1f}MB")
        
        if avg_cpu > 90:
            health_status = 'CRITICAL'
            health_issues.append(f"High CPU usage: {avg_cpu:.1f}%")
        elif avg_cpu > 70:
            if health_status == 'HEALTHY':
                health_status = 'WARNING'
            health_issues.append(f"Elevated CPU usage: {avg_cpu:.1f}%")
        
        critical_alerts = len([a for a in self.alerts_generated if a['level'] == 'CRITICAL'])
        if critical_alerts > 0:
            health_status = 'CRITICAL'
            health_issues.append(f"{critical_alerts} critical alerts")
        
        return {
            'status': health_status,
            'avg_memory_mb': avg_memory,
            'avg_cpu_percent': avg_cpu,
            'health_issues': health_issues,
            'sample_count': len(recent_samples),
            'assessment_time': datetime.now(timezone.utc).isoformat()
        }
    
    def _generate_monitoring_recommendations(self) -> List[Dict[str, str]]:
        """Generate recommendations based on monitoring data."""
        recommendations = []
        
        if not self.samples:
            return [{'priority': 'HIGH', 'action': 'Collect monitoring data before assessment'}]
        
        # Memory trend analysis
        memory_values = [s['process']['memory_rss_mb'] for s in self.samples]
        memory_growth = memory_values[-1] - memory_values[0] if len(memory_values) > 1 else 0
        
        if memory_growth > 50:
            recommendations.append({
                'priority': 'HIGH',
                'category': 'memory',
                'action': f'Investigate memory growth: {memory_growth:.2f}MB over monitoring period'
            })
        
        # CPU trend analysis
        cpu_values = [s['process']['cpu_percent'] for s in self.samples]
        avg_cpu = sum(cpu_values) / len(cpu_values) if cpu_values else 0
        
        if avg_cpu > 60:
            recommendations.append({
                'priority': 'MEDIUM',
                'category': 'cpu',
                'action': f'High CPU utilization detected: {avg_cpu:.1f}% average'
            })
        
        # Alert analysis
        critical_alerts = len([a for a in self.alerts_generated if a['level'] == 'CRITICAL'])
        if critical_alerts > 0:
            recommendations.append({
                'priority': 'CRITICAL',
                'category': 'alerts',
                'action': f'Address {critical_alerts} critical performance alerts immediately'
            })
        
        # Resource leak analysis
        latest_sample = self.samples[-1]
        open_files = latest_sample['process']['open_files']
        connections = latest_sample['process']['connections']
        
        if open_files > 200:
            recommendations.append({
                'priority': 'MEDIUM',
                'category': 'resources',
                'action': f'High file handle count: {open_files} (possible leak)'
            })
        
        if connections > 50:
            recommendations.append({
                'priority': 'MEDIUM', 
                'category': 'resources',
                'action': f'High connection count: {connections} (possible leak)'
            })
        
        if not recommendations:
            recommendations.append({
                'priority': 'INFO',
                'category': 'status',
                'action': 'System performance within normal parameters'
            })
        
        return recommendations
    
    def save_monitoring_data(self, filename: Optional[str] = None) -> str:
        """Save monitoring data to file."""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"performance_monitoring_{timestamp}.json"
        
        report_path = Path(__file__).parent.parent.parent / filename
        
        monitoring_data = {
            'monitoring_metadata': {
                'start_time': self.monitoring_start,
                'sample_interval': self.sample_interval,
                'total_samples': len(self.samples),
                'monitoring_duration': time.time() - self.monitoring_start if self.monitoring_start else 0
            },
            'performance_report': self.generate_monitoring_report(),
            'raw_samples': list(self.samples),
            'threshold_configuration': self.thresholds
        }
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(monitoring_data, f, indent=2)
        
        logger.info(f"Monitoring data saved to: {report_path}")
        return str(report_path)
    
    def print_real_time_status(self):
        """Print current system status to console."""
        if not self.samples:
            print("No monitoring data available")
            return
        
        latest = self.samples[-1]
        health = self._assess_system_health()
        
        print(f"\n CHART:  Performance Monitor Status - {latest['datetime']}")
        print("-" * 60)
        print(f"[U+1F5A5][U+FE0F]  System Memory: {latest['system']['memory_percent']:.1f}% "
              f"({latest['system']['memory_used_mb']:.0f}MB used)")
        print(f"[U+1F527] Process Memory: {latest['process']['memory_rss_mb']:.1f}MB RSS")
        print(f" LIGHTNING:  System CPU: {latest['system']['cpu_percent']:.1f}%")
        print(f" TARGET:  Process CPU: {latest['process']['cpu_percent']:.1f}%")
        print(f"[U+1F517] Connections: {latest['process']['connections']}")
        print(f"[U+1F4C1] Open Files: {latest['process']['open_files']}")
        print(f"[U+1F9F5] Threads: {latest['process']['threads']}")
        
        # Health status
        status_emoji = {"HEALTHY": " PASS: ", "WARNING": " WARNING: [U+FE0F]", "CRITICAL": " FAIL: "}.get(health['status'], "[U+2753]")
        print(f"\n{status_emoji} Health Status: {health['status']}")
        
        if health['health_issues']:
            for issue in health['health_issues']:
                print(f"  - {issue}")
        
        # Alerts summary
        if self.alerts_generated:
            recent_alerts = [a for a in self.alerts_generated if time.time() - a['timestamp'] < 300]  # Last 5 minutes
            if recent_alerts:
                print(f"\n ALERT:  Recent Alerts (last 5 min): {len(recent_alerts)}")
                for alert in recent_alerts[-3:]:  # Show last 3
                    print(f"  {alert['level']}: {alert['message']}")
        
        print("-" * 60)


async def run_continuous_monitoring(duration: int, interval: float, output_file: Optional[str] = None):
    """Run continuous performance monitoring."""
    monitor = PerformanceMonitor(sample_interval=interval)
    
    try:
        print(f"[U+1F680] Starting performance monitoring for {duration} seconds (interval: {interval}s)")
        print("Press Ctrl+C to stop monitoring early\n")
        
        # Start monitoring
        monitor.start_monitoring()
        
        # Monitor for specified duration
        end_time = time.time() + duration
        
        while time.time() < end_time and monitor.monitoring_active:
            try:
                # Take sample
                sample = monitor.take_system_sample()
                
                # Check for alerts
                alerts = monitor.check_thresholds(sample)
                if alerts:
                    monitor.alerts_generated.extend(alerts)
                    for alert in alerts:
                        print(f" ALERT:  {alert['level']}: {alert['message']}")
                
                # Print periodic status
                if len(monitor.samples) % 60 == 0:  # Every 60 samples
                    monitor.print_real_time_status()
                
                # Wait for next sample
                await asyncio.sleep(interval)
                
            except KeyboardInterrupt:
                print("\n WARNING: [U+FE0F]  Monitoring interrupted by user")
                break
            except Exception as e:
                logger.error(f"Error during monitoring: {e}")
                break
        
        monitor.stop_monitoring()
        
        # Generate final report
        print("\n CHART:  Generating final monitoring report...")
        report_file = monitor.save_monitoring_data(output_file)
        
        # Print summary
        report = monitor.generate_monitoring_report()
        print(f"\n PASS:  Monitoring Complete")
        print(f"[U+1F4C8] Duration: {report['monitoring_summary']['duration_seconds']:.1f}s")
        print(f"[U+1F4CB] Samples: {report['monitoring_summary']['total_samples']}")
        print(f" ALERT:  Alerts: {report['monitoring_summary']['alerts_generated']}")
        print(f"[U+1F4BE] Report saved: {report_file}")
        
        return report
        
    except Exception as e:
        logger.error(f"Error in continuous monitoring: {e}")
        raise


def main():
    """Main entry point for performance monitor."""
    parser = argparse.ArgumentParser(
        description="Real-time Performance Monitor for UserExecutionContext Migration"
    )
    
    parser.add_argument(
        '--duration',
        type=int,
        default=300,
        help='Monitoring duration in seconds (default: 300)'
    )
    
    parser.add_argument(
        '--interval',
        type=float,
        default=1.0,
        help='Sampling interval in seconds (default: 1.0)'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        help='Output file for monitoring data (JSON format)'
    )
    
    parser.add_argument(
        '--realtime',
        action='store_true',
        help='Show real-time status updates'
    )
    
    args = parser.parse_args()
    
    try:
        # Run continuous monitoring
        report = asyncio.run(run_continuous_monitoring(
            duration=args.duration,
            interval=args.interval,
            output_file=args.output
        ))
        
        # Print final summary
        health = report.get('system_health', {})
        status = health.get('status', 'UNKNOWN')
        
        if status == 'HEALTHY':
            print("\n PASS:  System performance is healthy")
            return 0
        elif status == 'WARNING':
            print("\n WARNING: [U+FE0F]  System performance has warnings")
            return 1
        else:
            print("\n FAIL:  Critical performance issues detected")
            return 2
            
    except KeyboardInterrupt:
        print("\n WARNING: [U+FE0F]  Monitoring interrupted")
        return 130
    except Exception as e:
        logger.error(f"Error running performance monitor: {e}")
        print(f" FAIL:  Error: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)