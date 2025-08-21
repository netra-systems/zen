#!/usr/bin/env python3
"""
Enhanced staging deployment script using modular architecture.
Provides comprehensive error handling, monitoring, and rollback capabilities.
"""

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from organized_root.deployment_configs.core import (
    CloudRunDeployer,
    DeploymentOrchestrator,
    DockerImageManager,
    HealthChecker,
)
from organized_root.deployment_configs.core.deployment_orchestrator import (
    DeploymentConfig,
    DeploymentPhase,
)
from organized_root.deployment_configs.monitoring import ErrorAnalyzer, ErrorCategory

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ANSI color codes for terminal output
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_colored(message: str, color: str = Colors.END):
    """Print colored message to terminal."""
    print(f"{color}{message}{Colors.END}")

def load_deployment_config() -> DeploymentConfig:
    """Load deployment configuration from files and environment."""
    config_file = Path(__file__).parent / "deployment_config.json"
    
    # Default configuration
    default_config = {
        "project_id": "neuralbridge-poc",
        "region": "us-central1",
        "services": [
            {
                "name": "netra-backend",
                "dockerfile": "Dockerfile",
                "context": ".",
                "port": 8000,
                "memory": "1Gi",
                "cpu": "2",
                "min_instances": 1,
                "max_instances": 10,
                "health_endpoint": "/health",
                "env_vars": {
                    "ENVIRONMENT": "staging",
                    "LOG_LEVEL": "INFO",
                    "PYTHONUNBUFFERED": "1"
                },
                "secrets": [
                    "DATABASE_URL=database-url:latest",
                    "REDIS_URL=redis-url:latest"
                ]
            },
            {
                "name": "netra-auth",
                "dockerfile": "Dockerfile.auth",
                "context": ".",
                "port": 8001,
                "memory": "512Mi",
                "cpu": "1",
                "min_instances": 1,
                "max_instances": 5,
                "health_endpoint": "/health",
                "env_vars": {
                    "ENVIRONMENT": "staging",
                    "LOG_LEVEL": "INFO"
                }
            },
            {
                "name": "netra-frontend",
                "dockerfile": "Dockerfile.frontend",
                "context": ".",
                "port": 3000,
                "memory": "512Mi",
                "cpu": "1",
                "min_instances": 1,
                "max_instances": 5,
                "health_endpoint": "/",
                "allow_unauthenticated": True,
                "env_vars": {
                    "NEXT_PUBLIC_API_URL": "https://netra-backend-staging.run.app"
                }
            }
        ]
    }
    
    # Load from file if exists
    if config_file.exists():
        with open(config_file, 'r') as f:
            file_config = json.load(f)
            # Merge configurations
            default_config.update(file_config)
    
    return DeploymentConfig(**default_config)

async def run_pre_deployment_tests() -> bool:
    """Run pre-deployment validation tests."""
    print_colored("[PRE-DEPLOY] Running validation tests...", Colors.CYAN)
    
    try:
        # Run critical path tests
        import subprocess
        result = subprocess.run(
            ["python", "-m", "test_framework.test_runner",
             "--level", "critical",
             "--fast-fail",
             "--no-coverage"],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print_colored("  ✗ Critical tests failed", Colors.RED)
            print(result.stdout)
            return False
            
        print_colored("  ✓ Critical tests passed", Colors.GREEN)
        return True
        
    except Exception as e:
        print_colored(f"  ✗ Test execution failed: {e}", Colors.RED)
        return False

async def monitor_deployment_logs(orchestrator: DeploymentOrchestrator) -> None:
    """Monitor deployment logs in real-time."""
    print_colored("\n[MONITORING] Real-time deployment monitoring active", Colors.CYAN)
    
    error_analyzer = ErrorAnalyzer()
    
    while orchestrator.current_phase not in [
        DeploymentPhase.POST_DEPLOYMENT, 
        DeploymentPhase.ROLLBACK
    ]:
        await asyncio.sleep(5)
        
        # Analyze recent errors
        if orchestrator.deployment_history:
            last_deployment = orchestrator.deployment_history[-1]
            if last_deployment.errors:
                for error in last_deployment.errors:
                    analyzed = error_analyzer.analyze_error(
                        error,
                        service="deployment",
                        timestamp=datetime.utcnow()
                    )
                    
                    if analyzed.auto_recovery:
                        print_colored(
                            f"  ⚠ Auto-recovery available: {analyzed.recovery_action}",
                            Colors.YELLOW
                        )

async def main():
    """Main deployment entry point."""
    parser = argparse.ArgumentParser(
        description="Enhanced Netra Staging Deployment"
    )
    parser.add_argument(
        "--skip-health-checks",
        action="store_true",
        help="Skip post-deployment health checks"
    )
    parser.add_argument(
        "--skip-auth",
        action="store_true",
        help="Skip authentication setup"
    )
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Skip pre-deployment tests (NOT RECOMMENDED)"
    )
    parser.add_argument(
        "--skip-error-monitoring",
        action="store_true",
        help="Skip post-deployment error monitoring"
    )
    parser.add_argument(
        "--no-rollback",
        action="store_true",
        help="Disable automatic rollback on failure"
    )
    parser.add_argument(
        "--services",
        nargs="+",
        help="Deploy only specified services"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform dry run without actual deployment"
    )
    
    args = parser.parse_args()
    
    print_colored("=" * 60, Colors.BLUE)
    print_colored("  NETRA ENHANCED STAGING DEPLOYMENT", Colors.BLUE)
    print_colored("=" * 60, Colors.BLUE)
    print()
    
    # Load configuration
    config = load_deployment_config()
    
    # Apply command-line overrides
    config.skip_health_checks = args.skip_health_checks
    config.skip_auth = args.skip_auth
    config.skip_tests = args.skip_tests
    config.skip_error_monitoring = args.skip_error_monitoring
    config.enable_rollback = not args.no_rollback
    
    # Filter services if specified
    if args.services:
        config.services = [
            s for s in config.services 
            if s["name"] in args.services
        ]
        if not config.services:
            print_colored("No matching services found", Colors.RED)
            sys.exit(1)
    
    # Display deployment plan
    print_colored("Deployment Configuration:", Colors.CYAN)
    print(f"  Project: {config.project_id}")
    print(f"  Region: {config.region}")
    print(f"  Services: {', '.join(s['name'] for s in config.services)}")
    print(f"  Rollback Enabled: {config.enable_rollback}")
    print()
    
    if args.dry_run:
        print_colored("DRY RUN MODE - No actual deployment will occur", Colors.YELLOW)
        return
    
    # Run pre-deployment tests
    if not config.skip_tests:
        if not await run_pre_deployment_tests():
            print_colored("\n❌ PRE-DEPLOYMENT TESTS FAILED", Colors.RED)
            print_colored("Fix issues or use --skip-tests to bypass", Colors.YELLOW)
            sys.exit(1)
    
    # Create orchestrator
    orchestrator = DeploymentOrchestrator(config)
    
    # Start monitoring task
    monitor_task = asyncio.create_task(monitor_deployment_logs(orchestrator))
    
    try:
        # Execute deployment
        print_colored("\n[DEPLOY] Starting deployment pipeline...", Colors.GREEN)
        result = await orchestrator.execute_deployment()
        
        # Cancel monitoring
        monitor_task.cancel()
        
        # Display results
        print()
        print_colored("=" * 60, Colors.BLUE)
        
        if result.success:
            print_colored("✅ DEPLOYMENT SUCCESSFUL", Colors.GREEN)
            print_colored(f"Duration: {result.duration_seconds:.2f} seconds", Colors.CYAN)
            
            if result.services_deployed:
                print_colored(f"Services: {', '.join(result.services_deployed)}", Colors.CYAN)
            
            # Display service URLs
            cloud_run = CloudRunDeployer(config.project_id, config.region)
            print_colored("\nService URLs:", Colors.CYAN)
            for service in result.services_deployed:
                url = cloud_run.get_service_url(service)
                if url:
                    print(f"  {service}: {url}")
            
            # Display health status
            if result.health_results:
                print_colored("\nHealth Status:", Colors.CYAN)
                for service, health in result.health_results.items():
                    status_icon = "✓" if health["status"] == "healthy" else "✗"
                    print(f"  {status_icon} {service}: {health['status']}")
            
        else:
            print_colored("❌ DEPLOYMENT FAILED", Colors.RED)
            print_colored(f"Phase: {result.phase.value}", Colors.YELLOW)
            
            if result.errors:
                print_colored("\nErrors:", Colors.RED)
                for error in result.errors:
                    print(f"  - {error}")
            
            if result.services_failed:
                print_colored(f"\nFailed Services: {', '.join(result.services_failed)}", Colors.RED)
            
            if result.rollback_performed:
                print_colored("\n🔄 Rollback was performed", Colors.YELLOW)
        
        print_colored("=" * 60, Colors.BLUE)
        
        # Generate deployment summary
        print()
        print(orchestrator.get_deployment_summary())
        
        # Save deployment info
        deployment_info = {
            "timestamp": datetime.utcnow().isoformat(),
            "success": result.success,
            "duration_seconds": result.duration_seconds,
            "services_deployed": result.services_deployed,
            "services_failed": result.services_failed,
            "phase": result.phase.value,
            "rollback_performed": result.rollback_performed
        }
        
        info_file = Path(__file__).parent / "deployment-info.json"
        with open(info_file, "w") as f:
            json.dump(deployment_info, f, indent=2)
        
        print_colored(f"\nDeployment info saved to {info_file}", Colors.CYAN)
        
        # Exit with appropriate code
        sys.exit(0 if result.success else 1)
        
    except KeyboardInterrupt:
        print_colored("\n\n⚠ Deployment interrupted by user", Colors.YELLOW)
        monitor_task.cancel()
        sys.exit(130)
    except Exception as e:
        print_colored(f"\n\n❌ Unexpected error: {e}", Colors.RED)
        monitor_task.cancel()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())