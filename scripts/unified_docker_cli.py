#!/usr/bin/env python3
"""
Unified Docker CLI - SSOT Compliant Command Line Interface

This replaces all individual Docker management scripts with a single,
comprehensive CLI that uses UnifiedDockerManager as the core engine.

Business Value Justification (BVJ):
1. Segment: Platform/Internal - Development Velocity
2. Business Goal: Eliminate CLI tool fragmentation  
3. Value Impact: Consistent Docker operations, improved developer experience
4. Revenue Impact: Reduced training time, faster debugging

Replaces:
- docker_health_manager.py
- docker_env_manager.py  
- test_docker_manager.py
- docker_services.py
- docker_compose_log_introspector.py
- All other Docker CLI tools
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import List, Optional

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# SSOT imports
from test_framework.unified_docker_manager import UnifiedDockerManager, ServiceMode, EnvironmentType
from test_framework.docker_introspection import DockerIntrospector


class UnifiedDockerCLI:
    """Unified command-line interface for all Docker operations."""
    
    def __init__(self):
        self.manager = None
        self.introspector = None
    
    def get_manager(self, 
                   environment: str = "cli",
                   environment_type: EnvironmentType = EnvironmentType.DEDICATED) -> UnifiedDockerManager:
        """Get or create UnifiedDockerManager instance."""
        if self.manager is None:
            self.manager = UnifiedDockerManager(
                environment=environment,
                environment_type=environment_type
            )
        return self.manager
    
    def get_introspector(self, compose_file: str, project_name: str) -> DockerIntrospector:
        """Get or create DockerIntrospector instance."""
        if self.introspector is None:
            self.introspector = DockerIntrospector(compose_file, project_name)
        return self.introspector
    
    async def cmd_start(self, args) -> int:
        """Start Docker services with smart container reuse."""
        manager = self.get_manager(args.environment, getattr(EnvironmentType, args.env_type.upper()))
        
        services = args.services or ["postgres", "redis", "backend", "auth"]
        
        print(f"🚀 Starting services: {', '.join(services)}")
        
        try:
            success = await manager.start_services_smart(
                services=services,
                wait_healthy=args.wait_healthy
            )
            
            if success:
                print("✅ Services started successfully")
                
                if args.show_urls:
                    # Show service URLs
                    state = manager._load_state()
                    current_env = getattr(manager, '_current_env', 'default')
                    
                    if current_env in state.get('environments', {}):
                        ports = state['environments'][current_env].get('ports', {})
                        print("\\n🌐 Service URLs:")
                        for service, port in ports.items():
                            print(f"  {service}: http://localhost:{port}")
                
                return 0
            else:
                print("❌ Failed to start services")
                return 1
                
        except Exception as e:
            print(f"❌ Error starting services: {e}")
            return 1
    
    async def cmd_stop(self, args) -> int:
        """Stop Docker services gracefully."""
        manager = self.get_manager(args.environment)
        
        print(f"🛑 Stopping services: {args.services or 'all'}")
        
        try:
            success = await manager.graceful_shutdown(
                services=args.services,
                timeout=args.timeout
            )
            
            if success:
                print("✅ Services stopped successfully")
                return 0
            else:
                print("❌ Failed to stop services gracefully")
                return 1
                
        except Exception as e:
            print(f"❌ Error stopping services: {e}")
            return 1
    
    async def cmd_status(self, args) -> int:
        """Show detailed service status."""
        manager = self.get_manager(args.environment)
        
        print("📊 Service Status:")
        
        try:
            # Get container status
            containers = manager.get_enhanced_container_status(args.services)
            
            if not containers:
                print("No containers found")
                return 1
            
            for service, info in containers.items():
                status_emoji = {
                    "healthy": "✅",
                    "running": "🟡", 
                    "stopped": "❌",
                    "starting": "🟠",
                    "unhealthy": "🔴"
                }.get(info.state.value, "❓")
                
                print(f"  {status_emoji} {service}: {info.state.value}")
                if info.uptime:
                    print(f"    Uptime: {info.uptime}")
                if info.health and info.health != info.state.value:
                    print(f"    Health: {info.health}")
            
            # Show statistics if requested
            if args.detailed:
                stats = manager.get_statistics()
                print(f"\\n📈 Statistics:")
                print(f"  Active environments: {stats['active_environments']}")
                print(f"  Healthy services: {stats['health_summary']['healthy_services']}")
                print(f"  Average response time: {stats['health_summary']['average_response_time']:.2f}ms")
            
            return 0
            
        except Exception as e:
            print(f"❌ Error getting service status: {e}")
            return 1
    
    async def cmd_logs(self, args) -> int:
        """Analyze service logs with issue detection."""
        introspector = self.get_introspector(args.compose_file, args.project_name)
        
        print(f"🔍 Analyzing logs for: {args.services or 'all services'}")
        
        try:
            report = introspector.analyze_services(
                services=args.services,
                since=args.since,
                max_lines=args.max_lines
            )
            
            # Print summary
            print(f"\\n📊 Log Analysis Summary:")
            print(f"Services analyzed: {len(report.services_analyzed)}")
            print(f"Log lines processed: {report.total_log_lines}")
            print(f"Issues found: {len(report.issues_found)}")
            
            # Show critical issues
            if report.critical_issues:
                print(f"\\n🚨 CRITICAL ISSUES ({len(report.critical_issues)}):")
                for issue in report.critical_issues:
                    print(f"  ❗ {issue.service}: {issue.title}")
            
            # Show error issues
            error_issues = report.error_issues
            if error_issues and len(error_issues) <= 10:
                print(f"\\n⚠️ ERROR ISSUES ({len(error_issues)}):")
                for issue in error_issues:
                    print(f"  ❌ {issue.service}: {issue.title}")
            elif len(error_issues) > 10:
                print(f"\\n⚠️ ERROR ISSUES ({len(error_issues)} total, showing first 5):")
                for issue in error_issues[:5]:
                    print(f"  ❌ {issue.service}: {issue.title}")
                print(f"  ... and {len(error_issues) - 5} more")
            
            # Show recommendations
            if report.recommendations:
                print(f"\\n💡 RECOMMENDATIONS:")
                for rec in report.recommendations[:5]:  # Top 5
                    print(f"  - {rec}")
            
            # Export detailed report if requested
            if args.output:
                output_file = introspector.export_report(report, Path(args.output))
                print(f"\\n📄 Detailed report exported to: {output_file}")
            
            return 0
            
        except Exception as e:
            print(f"❌ Error analyzing logs: {e}")
            return 1
    
    async def cmd_health(self, args) -> int:
        """Perform comprehensive health check with auto-remediation."""
        manager = self.get_manager(args.environment)
        
        print("🏥 Performing health analysis...")
        
        try:
            results = await manager.detect_and_remediate_issues(
                services=args.services,
                auto_fix=args.auto_fix
            )
            
            print(f"\\n📊 Health Check Results:")
            print(f"Services analyzed: {len(results['services_analyzed'])}")
            print(f"Issues detected: {results['issues_detected']}")
            print(f"Critical issues: {results['critical_issues']}")
            
            if results.get('remediation_attempted'):
                print(f"\\n🔧 Auto-remediation Results:")
                for result in results['remediation_results']:
                    status_emoji = "✅" if result['remediation_success'] else "❌"
                    print(f"  {status_emoji} {result['service']}: {result['issue'][:80]}...")
                    if result['actions_taken']:
                        for action in result['actions_taken']:
                            print(f"    → {action}")
            
            elif 'recommendations' in results:
                print(f"\\n💡 Recommendations (run with --auto-fix to attempt remediation):")
                for rec in results['recommendations'][:5]:
                    print(f"  - {rec}")
            
            return 0
            
        except Exception as e:
            print(f"❌ Error during health check: {e}")
            return 1
    
    async def cmd_cleanup(self, args) -> int:
        """Clean up Docker resources."""
        manager = self.get_manager(args.environment)
        
        print("🧹 Cleaning up Docker resources...")
        
        try:
            # Clean up orphaned containers
            success = manager.cleanup_orphaned_containers()
            
            if args.deep_clean:
                # Additional cleanup with introspector
                introspector = self.get_introspector(args.compose_file, args.project_name)
                cleanup_results = introspector.cleanup_docker_resources()
                
                print("🧹 Deep cleanup results:")
                for resource_type, result in cleanup_results.items():
                    if resource_type != 'error':
                        status = "✅" if result else "❌"
                        print(f"  {status} {resource_type.title()}")
                
                if 'disk_usage' in cleanup_results:
                    print(f"\\n💾 Current disk usage:")
                    print(cleanup_results['disk_usage'])
            
            if success:
                print("✅ Cleanup completed successfully")
                return 0
            else:
                print("⚠️ Cleanup completed with issues")
                return 1
                
        except Exception as e:
            print(f"❌ Error during cleanup: {e}")
            return 1
    
    async def cmd_reset_data(self, args) -> int:
        """Reset test data without restarting containers."""
        manager = self.get_manager(args.environment)
        
        services = args.services or ["postgres", "redis"]
        print(f"🔄 Resetting test data for: {', '.join(services)}")
        
        try:
            success = await manager.reset_test_data(services)
            
            if success:
                print("✅ Test data reset completed successfully")
                return 0
            else:
                print("❌ Test data reset failed")
                return 1
                
        except Exception as e:
            print(f"❌ Error resetting test data: {e}")
            return 1


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Unified Docker Management CLI - SSOT Compliant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s start --services postgres redis backend
  %(prog)s stop --timeout 30
  %(prog)s status --detailed
  %(prog)s logs --since 1h --services backend
  %(prog)s health --auto-fix
  %(prog)s cleanup --deep-clean
  %(prog)s reset-data --services postgres
        """
    )
    
    # Global options
    parser.add_argument("--environment", default="cli", help="Environment name")
    parser.add_argument("--env-type", default="shared", 
                       choices=["shared", "dedicated", "production", "development"],
                       help="Environment type")
    parser.add_argument("--compose-file", default="docker-compose.test.yml",
                       help="Docker Compose file")
    parser.add_argument("--project-name", default="netra-test",
                       help="Docker Compose project name")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Start command
    start_parser = subparsers.add_parser("start", help="Start Docker services")
    start_parser.add_argument("--services", nargs="+", help="Services to start")
    start_parser.add_argument("--wait-healthy", action="store_true", 
                             help="Wait for services to become healthy")
    start_parser.add_argument("--show-urls", action="store_true",
                             help="Show service URLs after starting")
    
    # Stop command  
    stop_parser = subparsers.add_parser("stop", help="Stop Docker services")
    stop_parser.add_argument("--services", nargs="+", help="Services to stop")
    stop_parser.add_argument("--timeout", type=int, default=30,
                            help="Graceful shutdown timeout")
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Show service status")
    status_parser.add_argument("--services", nargs="+", help="Services to check")
    status_parser.add_argument("--detailed", action="store_true",
                              help="Show detailed statistics")
    
    # Logs command
    logs_parser = subparsers.add_parser("logs", help="Analyze service logs")
    logs_parser.add_argument("--services", nargs="+", help="Services to analyze")
    logs_parser.add_argument("--since", default="1h", help="Time window (e.g., '1h', '30m')")
    logs_parser.add_argument("--max-lines", type=int, default=1000,
                            help="Maximum log lines to analyze")
    logs_parser.add_argument("--output", help="Export detailed report to file")
    
    # Health command
    health_parser = subparsers.add_parser("health", help="Perform health check")
    health_parser.add_argument("--services", nargs="+", help="Services to check")
    health_parser.add_argument("--auto-fix", action="store_true",
                              help="Attempt automatic issue remediation")
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser("cleanup", help="Clean up Docker resources")
    cleanup_parser.add_argument("--deep-clean", action="store_true",
                               help="Perform deep cleanup including system resources")
    
    # Reset data command
    reset_parser = subparsers.add_parser("reset-data", help="Reset test data")
    reset_parser.add_argument("--services", nargs="+", 
                             help="Services to reset data for (default: postgres, redis)")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Create CLI instance and run command
    cli = UnifiedDockerCLI()
    
    try:
        # Map commands to methods
        command_map = {
            "start": cli.cmd_start,
            "stop": cli.cmd_stop,
            "status": cli.cmd_status,
            "logs": cli.cmd_logs,
            "health": cli.cmd_health,
            "cleanup": cli.cmd_cleanup,
            "reset-data": cli.cmd_reset_data,
        }
        
        command_func = command_map.get(args.command)
        if command_func:
            return asyncio.run(command_func(args))
        else:
            print(f"❌ Unknown command: {args.command}")
            return 1
            
    except KeyboardInterrupt:
        print("\\n⚠️ Operation cancelled by user")
        return 130
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())