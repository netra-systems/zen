#!/usr/bin/env python3
"""
Architecture Health Monitoring Dashboard
Main orchestrator using focused modules for monitoring architecture compliance
"""

import sys
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from architecture_scanner import ArchitectureScanner
from architecture_metrics import ArchitectureMetrics
from architecture_reporter import ArchitectureReporter
from architecture_dashboard import ArchitectureDashboard


class ArchitectureHealthMonitor:
    """Main orchestrator for architecture health monitoring"""
    
    def __init__(self, root_path: str = "."):
        self.root_path = Path(root_path)
        self.scan_timestamp = datetime.now()
        self.metrics = {}
        self.violations = {}
        self.trends = {}
        
        # Initialize focused modules
        self.scanner = ArchitectureScanner(root_path)
        self.metrics_calculator = ArchitectureMetrics(root_path)
        self.reporter = ArchitectureReporter(root_path)
        self.dashboard_generator = ArchitectureDashboard(root_path)
    
    def scan_all_violations(self) -> Dict[str, Any]:
        """Comprehensive scan using scanner module"""
        print("Scanning codebase for architecture violations...")
        self.violations = self.scanner.scan_all_violations()
        return self.violations
    
    def calculate_health_metrics(self) -> Dict[str, Any]:
        """Calculate metrics using metrics module"""
        self.metrics = self.metrics_calculator.calculate_health_metrics(self.violations)
        return self.metrics
    
    def generate_html_dashboard(self, output_path: str = None) -> str:
        """Generate dashboard using dashboard module"""
        return self.dashboard_generator.generate_html_dashboard(
            self.metrics, self.violations, self.scan_timestamp, output_path
        )
    
    def export_json_report(self, output_path: str = None) -> str:
        """Export report using reporter module"""
        return self.reporter.export_json_report(
            self.metrics, self.violations, self.trends, self.scan_timestamp, output_path
        )
    
    def print_cli_summary(self):
        """Print summary using reporter module"""
        self.reporter.print_cli_summary(self.metrics, self.violations)


def main():
    """Main entry point for architecture health monitoring"""
    parser = argparse.ArgumentParser(description='Architecture Health Monitoring Dashboard')
    parser.add_argument('--path', default='.', help='Root path to scan')
    parser.add_argument('--output-html', help='HTML dashboard output path')
    parser.add_argument('--output-json', help='JSON report output path')
    parser.add_argument('--cli-only', action='store_true', help='Only show CLI summary')
    parser.add_argument('--fail-on-violations', action='store_true', help='Exit with error code on violations')
    
    args = parser.parse_args()
    
    # Initialize monitor
    monitor = ArchitectureHealthMonitor(args.path)
    
    # Scan for violations
    print("Starting comprehensive architecture health scan...")
    monitor.scan_all_violations()
    
    # Calculate metrics
    print("Calculating health metrics...")
    monitor.calculate_health_metrics()
    
    # Generate outputs
    if not args.cli_only:
        print("Generating HTML dashboard...")
        monitor.generate_html_dashboard(args.output_html)
        
        print("Exporting JSON report...")
        monitor.export_json_report(args.output_json)
    
    # Print CLI summary
    monitor.print_cli_summary()
    
    # Exit with error if requested
    if args.fail_on_violations and monitor.metrics['violation_counts']['total_violations'] > 0:
        print("\nExiting with error code due to violations")
        sys.exit(1)
    
    print("\nArchitecture health scan completed successfully!")


if __name__ == "__main__":
    main()