#!/usr/bin/env python3
"""Monitor for configuration loops in Netra backend services.

This script can be used in CI/CD pipelines or as a health check to detect
configuration loop issues that could impact performance and stability.

Usage:
    python scripts/monitor_configuration_loops.py [--container NAME] [--duration SECONDS]
    
Examples:
    # Monitor dev backend for 30 seconds
    python scripts/monitor_configuration_loops.py --container netra-dev-backend --duration 30
    
    # Monitor all backends
    python scripts/monitor_configuration_loops.py --all
    
Exit codes:
    0 - No configuration loops detected
    1 - Configuration loop detected
    2 - Error accessing containers
"""
import argparse
import subprocess
import time
import sys
import json
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional


class ConfigurationLoopMonitor:
    """Monitor for configuration loop issues in backend services."""
    
    # Thresholds for different environments
    THRESHOLDS = {
        'development': 10,  # Allow more in dev due to hot reload
        'test': 20,         # Test environments may clear more often
        'staging': 5,       # Staging should be stable
        'production': 2,    # Production should have minimal clears
        'default': 10       # Default threshold
    }
    
    def __init__(self, verbose: bool = False):
        """Initialize the monitor."""
        self.verbose = verbose
        self.results: Dict[str, Dict] = {}
    
    def log(self, message: str, level: str = "INFO"):
        """Log a message if verbose mode is enabled."""
        if self.verbose:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{timestamp}] [{level}] {message}")
    
    def get_container_environment(self, container_name: str) -> str:
        """Get the environment setting from a container."""
        try:
            result = subprocess.run(
                ["docker", "exec", container_name, "printenv", "ENVIRONMENT"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip().lower()
        except Exception as e:
            self.log(f"Could not get environment for {container_name}: {e}", "WARNING")
        return "default"
    
    def get_container_logs(self, container_name: str, since_seconds: int) -> List[str]:
        """Get container logs from the last N seconds."""
        try:
            result = subprocess.run(
                ["docker", "logs", "--since", f"{since_seconds}s", container_name],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return result.stdout.split('\n')
            else:
                self.log(f"Failed to get logs for {container_name}: {result.stderr}", "ERROR")
                return []
        except subprocess.TimeoutExpired:
            self.log(f"Timeout getting logs for {container_name}", "ERROR")
            return []
        except Exception as e:
            self.log(f"Error getting logs for {container_name}: {e}", "ERROR")
            return []
    
    def count_configuration_events(self, logs: List[str]) -> Dict[str, int]:
        """Count configuration-related events in logs."""
        events = {
            'cache_clears': 0,
            'config_reloads': 0,
            'config_errors': 0,
            'populate_calls': 0
        }
        
        for line in logs:
            if "All configuration caches cleared" in line:
                events['cache_clears'] += 1
            elif "Configuration reloaded" in line:
                events['config_reloads'] += 1
            elif "Configuration loading failed" in line:
                events['config_errors'] += 1
            elif "Populated" in line and "config" in line.lower():
                events['populate_calls'] += 1
        
        return events
    
    def analyze_container(self, container_name: str, duration: int) -> Tuple[bool, Dict]:
        """Analyze a single container for configuration loops.
        
        Returns:
            Tuple of (has_loop, details)
        """
        self.log(f"Analyzing container: {container_name}")
        
        # Get environment
        environment = self.get_container_environment(container_name)
        threshold = self.THRESHOLDS.get(environment, self.THRESHOLDS['default'])
        
        self.log(f"  Environment: {environment}, Threshold: {threshold}")
        
        # Get initial logs to establish baseline
        initial_logs = self.get_container_logs(container_name, duration)
        initial_events = self.count_configuration_events(initial_logs)
        
        # Monitor for specified duration
        self.log(f"  Monitoring for {duration} seconds...")
        time.sleep(duration)
        
        # Get logs again
        final_logs = self.get_container_logs(container_name, duration)
        final_events = self.count_configuration_events(final_logs)
        
        # Calculate rate (events per minute)
        rate_per_minute = (final_events['cache_clears'] / duration) * 60
        
        # Determine if there's a loop
        has_loop = final_events['cache_clears'] > threshold
        
        details = {
            'container': container_name,
            'environment': environment,
            'duration': duration,
            'threshold': threshold,
            'cache_clears': final_events['cache_clears'],
            'rate_per_minute': rate_per_minute,
            'config_reloads': final_events['config_reloads'],
            'config_errors': final_events['config_errors'],
            'populate_calls': final_events['populate_calls'],
            'has_loop': has_loop,
            'severity': self._calculate_severity(final_events['cache_clears'], threshold)
        }
        
        return has_loop, details
    
    def _calculate_severity(self, clears: int, threshold: int) -> str:
        """Calculate severity of the issue."""
        if clears <= threshold:
            return "OK"
        elif clears <= threshold * 2:
            return "WARNING"
        elif clears <= threshold * 5:
            return "ERROR"
        else:
            return "CRITICAL"
    
    def monitor_all_backends(self, duration: int) -> bool:
        """Monitor all backend containers.
        
        Returns:
            True if any loops detected, False otherwise
        """
        containers = [
            "netra-dev-backend",
            "netra-test-backend",
            "netra-staging-backend",
            "netra-prod-backend"
        ]
        
        any_loops = False
        
        for container in containers:
            # Check if container exists
            result = subprocess.run(
                ["docker", "ps", "--filter", f"name={container}", "--format", "{{.Names}}"],
                capture_output=True,
                text=True
            )
            
            if container in result.stdout:
                has_loop, details = self.analyze_container(container, duration)
                self.results[container] = details
                if has_loop:
                    any_loops = True
            else:
                self.log(f"Container {container} not found, skipping", "INFO")
        
        return any_loops
    
    def monitor_container(self, container_name: str, duration: int) -> bool:
        """Monitor a specific container.
        
        Returns:
            True if loop detected, False otherwise
        """
        has_loop, details = self.analyze_container(container_name, duration)
        self.results[container_name] = details
        return has_loop
    
    def print_report(self):
        """Print a detailed report of findings."""
        print("\n" + "="*60)
        print("Configuration Loop Monitoring Report")
        print("="*60)
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        if not self.results:
            print("No containers analyzed.")
            return
        
        # Summary
        total_containers = len(self.results)
        affected_containers = sum(1 for r in self.results.values() if r['has_loop'])
        
        print(f"Summary: {affected_containers}/{total_containers} containers affected")
        print()
        
        # Detailed results
        for container, details in self.results.items():
            status_icon = "[FAIL]" if details['has_loop'] else "[PASS]"
            print(f"{status_icon} {container}")
            print(f"    Environment: {details['environment']}")
            print(f"    Cache clears: {details['cache_clears']} (threshold: {details['threshold']})")
            print(f"    Rate: {details['rate_per_minute']:.1f} clears/minute")
            print(f"    Severity: {details['severity']}")
            
            if details['config_errors'] > 0:
                print(f"    [WARNING] Config errors: {details['config_errors']}")
            
            print()
        
        # Recommendations
        if affected_containers > 0:
            print("Recommendations:")
            print("  1. Check environment variables (TEST_MODE, TESTING)")
            print("  2. Verify _is_test_context() logic in configuration/base.py")
            print("  3. Review recent configuration changes")
            print("  4. Run: python netra_backend/tests/core/test_configuration_regression.py")
    
    def export_json(self, filename: str):
        """Export results to JSON file."""
        output = {
            'timestamp': datetime.now().isoformat(),
            'results': self.results,
            'summary': {
                'total_containers': len(self.results),
                'affected_containers': sum(1 for r in self.results.values() if r['has_loop'])
            }
        }
        
        with open(filename, 'w') as f:
            json.dump(output, f, indent=2)
        
        print(f"Results exported to {filename}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Monitor Netra backend services for configuration loops"
    )
    parser.add_argument(
        "--container",
        help="Specific container to monitor"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Monitor all backend containers"
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=30,
        help="Monitoring duration in seconds (default: 30)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    parser.add_argument(
        "--export",
        help="Export results to JSON file"
    )
    parser.add_argument(
        "--ci",
        action="store_true",
        help="CI mode - minimal output, exit code indicates status"
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.container and not args.all:
        parser.error("Either --container or --all must be specified")
    
    # Create monitor
    monitor = ConfigurationLoopMonitor(verbose=args.verbose and not args.ci)
    
    # Run monitoring
    try:
        if args.all:
            has_loops = monitor.monitor_all_backends(args.duration)
        else:
            has_loops = monitor.monitor_container(args.container, args.duration)
        
        # Output results
        if args.ci:
            # CI mode - minimal output
            if has_loops:
                print("FAIL: Configuration loops detected")
            else:
                print("PASS: No configuration loops detected")
        else:
            # Normal mode - detailed report
            monitor.print_report()
        
        # Export if requested
        if args.export:
            monitor.export_json(args.export)
        
        # Exit with appropriate code
        sys.exit(1 if has_loops else 0)
        
    except KeyboardInterrupt:
        print("\nMonitoring cancelled by user")
        sys.exit(2)
    except Exception as e:
        print(f"Error during monitoring: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(2)


if __name__ == "__main__":
    main()