#!/usr/bin/env python3
"""
Docker Resource Monitoring Script
Based on DOCKER_CRASH_DEEP_10_WHYS_ANALYSIS.md recommendations

This script monitors actual resource usage of running containers and provides
recommendations to prevent resource exhaustion crashes.

Usage:
    python scripts/monitor_docker_resources.py              # One-time check
    python scripts/monitor_docker_resources.py --continuous # Continuous monitoring
    python scripts/monitor_docker_resources.py --analyze    # Deep analysis with recommendations
"""

import subprocess
import json
import time
import sys
import platform
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime

class DockerResourceMonitor:
    """Monitor and analyze Docker container resource usage"""
    
    # Resource limits from our optimized configuration
    RESOURCE_LIMITS = {
        'backend': {'memory_mb': 1024, 'cpu': 0.3},
        'auth': {'memory_mb': 512, 'cpu': 0.2},
        'frontend': {'memory_mb': 256, 'cpu': 0.2},
        'postgres': {'memory_mb': 256, 'cpu': 0.15},
        'redis': {'memory_mb': 128, 'cpu': 0.05},
        'clickhouse': {'memory_mb': 512, 'cpu': 0.1},
    }
    
    # WSL2 recommended limit (from analysis)
    WSL2_MEMORY_LIMIT_GB = 6
    
    def __init__(self, runtime: str = None):
        """Initialize monitor with Docker or Podman runtime"""
        self.runtime = runtime or self._detect_runtime()
        self.is_windows = platform.system() == 'Windows'
        
    def _detect_runtime(self) -> str:
        """Detect available container runtime"""
        for cmd in ['docker', 'podman']:
            try:
                subprocess.run([cmd, 'version'], capture_output=True, timeout=2)
                return cmd
            except:
                continue
        raise RuntimeError("No container runtime (Docker/Podman) found")
    
    def get_container_stats(self) -> Dict[str, Dict]:
        """Get current resource usage for all containers"""
        try:
            # Get container stats in JSON format
            cmd = [self.runtime, 'stats', '--no-stream', '--format', 'json']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                print(f"Error getting stats: {result.stderr}")
                return {}
            
            stats = {}
            for line in result.stdout.strip().split('\n'):
                if line:
                    data = json.loads(line)
                    
                    # Parse memory usage
                    mem_usage = data.get('MemUsage', '0MiB / 0MiB')
                    if ' / ' in mem_usage:
                        current, limit = mem_usage.split(' / ')
                        current_mb = self._parse_memory(current)
                        limit_mb = self._parse_memory(limit)
                    else:
                        current_mb = 0
                        limit_mb = 0
                    
                    # Parse CPU percentage
                    cpu_percent = data.get('CPUPerc', '0%').rstrip('%')
                    try:
                        cpu_percent = float(cpu_percent)
                    except:
                        cpu_percent = 0.0
                    
                    stats[data['Name']] = {
                        'memory_mb': current_mb,
                        'memory_limit_mb': limit_mb,
                        'memory_percent': float(data.get('MemPerc', '0%').rstrip('%')),
                        'cpu_percent': cpu_percent,
                        'network_io': data.get('NetIO', 'N/A'),
                        'block_io': data.get('BlockIO', 'N/A'),
                    }
            
            return stats
        except Exception as e:
            print(f"Error getting container stats: {e}")
            return {}
    
    def _parse_memory(self, mem_str: str) -> float:
        """Parse memory string to MB"""
        mem_str = mem_str.strip()
        if 'GiB' in mem_str:
            return float(mem_str.replace('GiB', '')) * 1024
        elif 'MiB' in mem_str:
            return float(mem_str.replace('MiB', ''))
        elif 'KiB' in mem_str:
            return float(mem_str.replace('KiB', '')) / 1024
        elif 'GB' in mem_str:
            return float(mem_str.replace('GB', '')) * 1000
        elif 'MB' in mem_str:
            return float(mem_str.replace('MB', ''))
        elif 'KB' in mem_str:
            return float(mem_str.replace('KB', '')) / 1000
        return 0.0
    
    def get_wsl_memory_usage(self) -> Optional[Dict]:
        """Get WSL2 memory usage on Windows"""
        if not self.is_windows:
            return None
        
        try:
            # Get memory info from WSL2
            result = subprocess.run(
                ['wsl', '-e', 'sh', '-c', 'free -m'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) >= 2:
                    # Parse the memory line
                    mem_line = lines[1].split()
                    if len(mem_line) >= 3:
                        total_mb = int(mem_line[1])
                        used_mb = int(mem_line[2])
                        free_mb = int(mem_line[3]) if len(mem_line) > 3 else total_mb - used_mb
                        
                        return {
                            'total_mb': total_mb,
                            'used_mb': used_mb,
                            'free_mb': free_mb,
                            'percent': (used_mb / total_mb * 100) if total_mb > 0 else 0
                        }
        except:
            pass
        
        return None
    
    def analyze_resources(self, stats: Dict) -> Dict:
        """Analyze resource usage and provide recommendations"""
        analysis = {
            'total_memory_mb': 0,
            'total_cpu_percent': 0,
            'warnings': [],
            'critical': [],
            'recommendations': [],
            'container_details': {}
        }
        
        for container, usage in stats.items():
            # Get expected limits for this container type
            container_type = self._get_container_type(container)
            expected = self.RESOURCE_LIMITS.get(container_type, {})
            
            memory_mb = usage['memory_mb']
            cpu_percent = usage['cpu_percent']
            
            analysis['total_memory_mb'] += memory_mb
            analysis['total_cpu_percent'] += cpu_percent
            
            # Check if exceeding expected limits
            if expected:
                expected_mem = expected.get('memory_mb', 0)
                expected_cpu = expected.get('cpu', 0) * 100
                
                if expected_mem > 0 and memory_mb > expected_mem:
                    excess = ((memory_mb - expected_mem) / expected_mem) * 100
                    if excess > 50:
                        analysis['critical'].append(
                            f"{container}: Using {memory_mb:.0f}MB (limit: {expected_mem}MB) - {excess:.0f}% over!"
                        )
                    else:
                        analysis['warnings'].append(
                            f"{container}: Using {memory_mb:.0f}MB (limit: {expected_mem}MB) - {excess:.0f}% over"
                        )
                
                if expected_cpu > 0 and cpu_percent > expected_cpu * 1.5:
                    analysis['warnings'].append(
                        f"{container}: CPU at {cpu_percent:.1f}% (expected: {expected_cpu:.0f}%)"
                    )
            
            analysis['container_details'][container] = {
                'memory_mb': memory_mb,
                'cpu_percent': cpu_percent,
                'expected_memory_mb': expected.get('memory_mb', 0),
                'status': self._get_status(memory_mb, cpu_percent, expected)
            }
        
        # Check total memory usage
        if analysis['total_memory_mb'] > 3000:  # 3GB threshold
            analysis['critical'].append(
                f"Total memory usage: {analysis['total_memory_mb']:.0f}MB exceeds safe threshold (3GB)"
            )
        elif analysis['total_memory_mb'] > 2500:  # 2.5GB warning
            analysis['warnings'].append(
                f"Total memory usage: {analysis['total_memory_mb']:.0f}MB approaching limit"
            )
        
        # Generate recommendations
        if analysis['critical']:
            analysis['recommendations'].append(" ALERT:  CRITICAL: Reduce memory limits or stop non-essential services")
            analysis['recommendations'].append("Consider using Alpine-based images for lower memory usage")
        
        if analysis['total_memory_mb'] > 2000:
            analysis['recommendations'].append("Enable swap file in WSL2 for stability")
            analysis['recommendations'].append("Use staged startup to prevent simultaneous resource peaks")
        
        # WSL2 specific recommendations
        if self.is_windows:
            wsl_mem = self.get_wsl_memory_usage()
            if wsl_mem:
                wsl_percent = wsl_mem['percent']
                analysis['wsl_memory'] = wsl_mem
                
                if wsl_percent > 80:
                    analysis['critical'].append(
                        f"WSL2 memory at {wsl_percent:.1f}% - system crash imminent!"
                    )
                    analysis['recommendations'].append("Run: wsl --shutdown && docker system prune -a")
                elif wsl_percent > 60:
                    analysis['warnings'].append(
                        f"WSL2 memory at {wsl_percent:.1f}% - consider cleanup"
                    )
        
        return analysis
    
    def _get_container_type(self, container_name: str) -> str:
        """Extract container type from name"""
        for key in self.RESOURCE_LIMITS.keys():
            if key in container_name.lower():
                return key
        return 'unknown'
    
    def _get_status(self, memory_mb: float, cpu_percent: float, expected: Dict) -> str:
        """Determine container health status"""
        if not expected:
            return '[U+2753]'
        
        mem_limit = expected.get('memory_mb', 0)
        if mem_limit > 0:
            if memory_mb > mem_limit * 1.5:
                return '[U+1F534]'  # Critical
            elif memory_mb > mem_limit:
                return '[U+1F7E1]'  # Warning
        
        return '[U+1F7E2]'  # OK
    
    def print_report(self, analysis: Dict):
        """Print formatted resource analysis report"""
        print("\n" + "="*60)
        print(" CHART:  DOCKER RESOURCE MONITORING REPORT")
        print("="*60)
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Runtime: {self.runtime}")
        
        # Container details
        print("\n[U+1F4E6] Container Resource Usage:")
        print("-" * 60)
        print(f"{'Container':<20} {'Memory (MB)':<15} {'CPU %':<10} {'Status':<10}")
        print("-" * 60)
        
        for container, details in analysis['container_details'].items():
            mem_str = f"{details['memory_mb']:.0f}"
            if details['expected_memory_mb'] > 0:
                mem_str += f"/{details['expected_memory_mb']}"
            
            print(f"{container:<20} {mem_str:<15} {details['cpu_percent']:<10.1f} {details['status']:<10}")
        
        # Totals
        print("-" * 60)
        print(f"{'TOTAL':<20} {analysis['total_memory_mb']:<15.0f} {analysis['total_cpu_percent']:<10.1f}")
        
        # WSL2 Memory (if Windows)
        if 'wsl_memory' in analysis:
            wsl = analysis['wsl_memory']
            print(f"\n[U+1F5A5][U+FE0F] WSL2 Memory: {wsl['used_mb']}/{wsl['total_mb']}MB ({wsl['percent']:.1f}%)")
        
        # Warnings and Critical issues
        if analysis['critical']:
            print("\n ALERT:  CRITICAL ISSUES:")
            for issue in analysis['critical']:
                print(f"  - {issue}")
        
        if analysis['warnings']:
            print("\n WARNING: [U+FE0F]  WARNINGS:")
            for warning in analysis['warnings']:
                print(f"  - {warning}")
        
        # Recommendations
        if analysis['recommendations']:
            print("\n IDEA:  RECOMMENDATIONS:")
            for rec in analysis['recommendations']:
                print(f"  - {rec}")
        
        # Success message if all good
        if not analysis['critical'] and not analysis['warnings']:
            print("\n PASS:  All containers within resource limits!")
        
        print("\n" + "="*60)
    
    def continuous_monitor(self, interval: int = 30):
        """Continuously monitor resources"""
        print(f"Starting continuous monitoring (interval: {interval}s)")
        print("Press Ctrl+C to stop...")
        
        try:
            while True:
                stats = self.get_container_stats()
                if stats:
                    analysis = self.analyze_resources(stats)
                    self.print_report(analysis)
                    
                    # Alert if critical
                    if analysis['critical']:
                        print("\n[U+1F514] ALERT: Critical resource issues detected!")
                else:
                    print(f"\nNo containers running. Checking again in {interval}s...")
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n\nMonitoring stopped by user")
    
    def deep_analysis(self):
        """Perform deep analysis with system checks"""
        print("\n SEARCH:  DEEP RESOURCE ANALYSIS")
        print("="*60)
        
        # 1. Check Docker/Podman system info
        print("\n1. Container Runtime Info:")
        try:
            result = subprocess.run(
                [self.runtime, 'system', 'info', '--format', 'json'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                info = json.loads(result.stdout)
                print(f"  - Total Memory: {info.get('MemTotal', 'N/A')}")
                print(f"  - Available Memory: {info.get('MemFree', 'N/A')}")
                print(f"  - Containers: {info.get('Containers', 0)}")
                print(f"  - Images: {info.get('Images', 0)}")
        except:
            print("  Unable to get system info")
        
        # 2. Check disk usage
        print("\n2. Disk Usage:")
        try:
            result = subprocess.run(
                [self.runtime, 'system', 'df'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                print(result.stdout)
        except:
            print("  Unable to get disk usage")
        
        # 3. Check for dangling resources
        print("\n3. Dangling Resources:")
        for resource in ['volume', 'image', 'container']:
            try:
                cmd = [self.runtime, resource, 'ls', '-qf', 'dangling=true']
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    count = len(result.stdout.strip().split('\n')) if result.stdout.strip() else 0
                    print(f"  - Dangling {resource}s: {count}")
            except:
                pass
        
        # 4. Memory cleanup potential
        print("\n4. Cleanup Potential:")
        try:
            result = subprocess.run(
                [self.runtime, 'system', 'prune', '--dry-run', '--all'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0 and 'reclaim' in result.stdout.lower():
                print(f"  {result.stdout.strip()}")
        except:
            pass
        
        print("\n" + "="*60)


def main():
    parser = argparse.ArgumentParser(
        description="Monitor Docker container resource usage"
    )
    parser.add_argument(
        '--continuous',
        action='store_true',
        help='Continuously monitor resources'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=30,
        help='Monitoring interval in seconds (default: 30)'
    )
    parser.add_argument(
        '--analyze',
        action='store_true',
        help='Perform deep analysis with recommendations'
    )
    parser.add_argument(
        '--runtime',
        choices=['docker', 'podman'],
        help='Specify container runtime'
    )
    
    args = parser.parse_args()
    
    try:
        monitor = DockerResourceMonitor(runtime=args.runtime)
    except RuntimeError as e:
        print(f"Error: {e}")
        sys.exit(1)
    
    if args.analyze:
        # Deep analysis mode
        monitor.deep_analysis()
        stats = monitor.get_container_stats()
        if stats:
            analysis = monitor.analyze_resources(stats)
            monitor.print_report(analysis)
    elif args.continuous:
        # Continuous monitoring
        monitor.continuous_monitor(interval=args.interval)
    else:
        # One-time check
        stats = monitor.get_container_stats()
        if stats:
            analysis = monitor.analyze_resources(stats)
            monitor.print_report(analysis)
        else:
            print("No containers are currently running")
            print("\nTo start containers with resource limits:")
            print("  docker compose -f docker-compose.resource-optimized.yml up -d")
            print("\nThen run this script again to monitor resources")


if __name__ == "__main__":
    main()