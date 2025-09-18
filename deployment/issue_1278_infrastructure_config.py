"""
Infrastructure Configuration Updates for Issue #1278

This module provides infrastructure configuration updates to address
VPC connector capacity constraints and Cloud SQL optimization identified
in Issue #1278 comprehensive testing.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Staging Environment Infrastructure Resilience  
- Value Impact: Prevent $500K+ ARR impact from infrastructure-related startup failures
- Strategic Impact: Enable reliable service deployment under GCP resource constraints
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class InfrastructureUpdate:
    """Infrastructure configuration update definition."""
    component: str
    configuration_type: str
    current_value: Any
    recommended_value: Any
    rationale: str
    priority: str  # critical, high, medium, low
    environment: str  # staging, production, all


class Issue1278InfrastructureConfig:
    """Manages infrastructure configuration updates for Issue #1278."""
    
    def __init__(self):
        self.updates = self._define_infrastructure_updates()
        self.deployment_configs = self._load_deployment_configurations()
        
    def _define_infrastructure_updates(self) -> List[InfrastructureUpdate]:
        """Define all infrastructure configuration updates needed for Issue #1278."""
        return [
            # Database Timeout Configurations
            InfrastructureUpdate(
                component="database_timeouts",
                configuration_type="timeout_values",
                current_value={"initialization_timeout": 25.0, "connection_timeout": 15.0},
                recommended_value={"initialization_timeout": 45.0, "connection_timeout": 25.0},
                rationale="Issue #1278 testing shows VPC connector capacity pressure adds 10-20s delay",
                priority="critical",
                environment="staging"
            ),
            
            # Cloud SQL Connection Pool
            InfrastructureUpdate(
                component="cloud_sql_pool",
                configuration_type="connection_limits",
                current_value={"pool_size": 15, "max_overflow": 25},
                recommended_value={"pool_size": 10, "max_overflow": 15},
                rationale="Respect Cloud SQL instance connection limits (80% safety margin)",
                priority="critical",
                environment="staging"
            ),
            
            # VPC Connector Configuration
            InfrastructureUpdate(
                component="vpc_connector",
                configuration_type="capacity_monitoring",
                current_value={"monitoring_enabled": False},
                recommended_value={"monitoring_enabled": True, "capacity_threshold": 0.7},
                rationale="Enable proactive monitoring to prevent capacity pressure failures",
                priority="high",
                environment="staging"
            ),
            
            # Cloud Run Resource Allocation
            InfrastructureUpdate(
                component="cloud_run_backend",
                configuration_type="resource_allocation",
                current_value={"memory": "2Gi", "cpu": "2"},
                recommended_value={"memory": "4Gi", "cpu": "4"},
                rationale="Increased resources to handle VPC connector overhead and timeout extensions",
                priority="high",
                environment="staging"
            ),
            
            # Service Authentication
            InfrastructureUpdate(
                component="service_authentication",
                configuration_type="service_id_configuration",
                current_value={"SERVICE_ID": "netra-auth-1757260376"},
                recommended_value={"SERVICE_ID": "netra-backend"},
                rationale="Fix SERVICE_ID misconfiguration causing 100% E2E test failures",
                priority="critical",
                environment="staging"
            ),
            
            # Health Check Configuration
            InfrastructureUpdate(
                component="health_checks",
                configuration_type="timeout_extension",
                current_value={"timeout": 30, "check_interval": 10},
                recommended_value={"timeout": 60, "check_interval": 15},
                rationale="Extended timeouts for capacity-aware startup procedures",
                priority="medium",
                environment="staging"
            ),
        ]
    
    def _load_deployment_configurations(self) -> Dict[str, Any]:
        """Load current deployment configurations for comparison."""
        project_root = Path(__file__).parent.parent
        
        configs = {}
        
        # Load GCP deployment script configuration
        deploy_script_path = project_root / "scripts" / "deploy_to_gcp_actual.py"
        if deploy_script_path.exists():
            configs["gcp_deploy_script"] = self._extract_deploy_script_config(deploy_script_path)
        
        # Load Docker Compose staging configuration
        docker_staging_path = project_root / "docker" / "docker-compose.staging.yml"
        if docker_staging_path.exists():
            configs["docker_staging"] = self._extract_docker_config(docker_staging_path)
        
        return configs
    
    def _extract_deploy_script_config(self, script_path: Path) -> Dict[str, Any]:
        """Extract configuration from GCP deployment script."""
        try:
            with open(script_path, 'r') as f:
                content = f.read()
            
            # Extract resource allocation patterns
            config = {}
            
            if 'backend_memory = "4Gi"' in content:
                config["backend_memory"] = "4Gi"
            elif 'backend_memory = "2Gi"' in content:
                config["backend_memory"] = "2Gi"
            
            if 'backend_cpu = "4"' in content:
                config["backend_cpu"] = "4"
            elif 'backend_cpu = "2"' in content:
                config["backend_cpu"] = "2"
            
            return config
            
        except Exception as e:
            logger.warning(f"Failed to extract deploy script config: {e}")
            return {}
    
    def _extract_docker_config(self, docker_path: Path) -> Dict[str, Any]:
        """Extract configuration from Docker Compose file."""
        try:
            with open(docker_path, 'r') as f:
                content = f.read()
            
            config = {}
            
            # Extract SERVICE_ID configuration
            if 'SERVICE_ID: netra-backend' in content:
                config["service_id"] = "netra-backend"
            elif 'SERVICE_ID: netra-auth' in content:
                config["service_id"] = "netra-auth"
            
            return config
            
        except Exception as e:
            logger.warning(f"Failed to extract Docker config: {e}")
            return {}
    
    def get_critical_updates(self, environment: str = "staging") -> List[InfrastructureUpdate]:
        """Get critical infrastructure updates for specified environment.
        
        Args:
            environment: Target environment
            
        Returns:
            List of critical infrastructure updates
        """
        return [
            update for update in self.updates
            if update.priority == "critical" and (update.environment == environment or update.environment == "all")
        ]
    
    def get_staging_remediation_plan(self) -> Dict[str, Any]:
        """Get comprehensive staging environment remediation plan.
        
        Returns:
            Detailed remediation plan for staging environment
        """
        staging_updates = [
            update for update in self.updates
            if update.environment in ["staging", "all"]
        ]
        
        # Group updates by priority
        by_priority = {}
        for update in staging_updates:
            if update.priority not in by_priority:
                by_priority[update.priority] = []
            by_priority[update.priority].append(update)
        
        # Generate implementation steps
        implementation_steps = []
        
        # Critical updates first
        critical_updates = by_priority.get("critical", [])
        if critical_updates:
            implementation_steps.append({
                "phase": "Phase 1: Critical Infrastructure Fixes",
                "priority": "critical",
                "updates": [
                    {
                        "component": update.component,
                        "description": f"Update {update.configuration_type}",
                        "current": update.current_value,
                        "recommended": update.recommended_value,
                        "rationale": update.rationale
                    }
                    for update in critical_updates
                ],
                "estimated_downtime": "5-10 minutes",
                "rollback_required": True
            })
        
        # High priority updates
        high_updates = by_priority.get("high", [])
        if high_updates:
            implementation_steps.append({
                "phase": "Phase 2: Performance and Monitoring",
                "priority": "high",
                "updates": [
                    {
                        "component": update.component,
                        "description": f"Update {update.configuration_type}",
                        "current": update.current_value,
                        "recommended": update.recommended_value,
                        "rationale": update.rationale
                    }
                    for update in high_updates
                ],
                "estimated_downtime": "2-5 minutes",
                "rollback_required": False
            })
        
        return {
            "environment": "staging",
            "total_updates": len(staging_updates),
            "critical_updates": len(critical_updates),
            "implementation_phases": len(implementation_steps),
            "phases": implementation_steps,
            "validation_steps": self._generate_validation_steps(),
            "rollback_plan": self._generate_rollback_plan(),
            "monitoring_requirements": self._generate_monitoring_requirements()
        }
    
    def _generate_validation_steps(self) -> List[Dict[str, str]]:
        """Generate validation steps for infrastructure updates."""
        return [
            {
                "step": "Database Connection Validation",
                "command": "Test database connection with new timeout configuration",
                "expected_result": "Connection successful within 45s timeout"
            },
            {
                "step": "VPC Connector Capacity Check",
                "command": "Monitor VPC connector utilization during startup",
                "expected_result": "Utilization remains below 70% threshold"
            },
            {
                "step": "Service Authentication Validation",
                "command": "Verify SERVICE_ID configuration in staging",
                "expected_result": "SERVICE_ID=netra-backend, authentication successful"
            },
            {
                "step": "End-to-End Startup Test",
                "command": "Run complete startup sequence with new configuration",
                "expected_result": "All startup phases complete without timeout failures"
            },
            {
                "step": "Load Testing",
                "command": "Simulate concurrent startup scenarios",
                "expected_result": "No capacity pressure failures under load"
            }
        ]
    
    def _generate_rollback_plan(self) -> Dict[str, Any]:
        """Generate rollback plan for infrastructure updates."""
        return {
            "rollback_triggers": [
                "Startup timeout failures persist after updates",
                "Service availability drops below 95%",
                "Database connection failures increase"
            ],
            "rollback_steps": [
                {
                    "step": 1,
                    "action": "Revert database timeout configuration to 25.0s",
                    "verification": "Check startup time returns to baseline"
                },
                {
                    "step": 2, 
                    "action": "Restore original connection pool limits",
                    "verification": "Monitor for pool exhaustion issues"
                },
                {
                    "step": 3,
                    "action": "Disable VPC connector monitoring",
                    "verification": "Confirm no performance impact"
                }
            ],
            "rollback_time_estimate": "5-10 minutes",
            "data_loss_risk": "None - configuration changes only"
        }
    
    def _generate_monitoring_requirements(self) -> List[Dict[str, str]]:
        """Generate monitoring requirements for infrastructure updates."""
        return [
            {
                "metric": "Database connection time",
                "threshold": "< 30 seconds for 95% of connections",
                "alert_condition": "Connection time > 40 seconds"
            },
            {
                "metric": "VPC connector utilization",
                "threshold": "< 70% average utilization",
                "alert_condition": "Utilization > 80% for 5+ minutes"
            },
            {
                "metric": "Startup phase completion rate",
                "threshold": "100% success rate for all phases",
                "alert_condition": "Any phase failure"
            },
            {
                "metric": "Service authentication success rate",
                "threshold": "100% authentication success",
                "alert_condition": "Authentication failure"
            },
            {
                "metric": "Cloud SQL connection pool health",
                "threshold": "< 80% pool utilization",
                "alert_condition": "Pool exhaustion events"
            }
        ]
    
    def generate_configuration_files(self, output_dir: Path) -> Dict[str, str]:
        """Generate updated configuration files for deployment.
        
        Args:
            output_dir: Directory to write configuration files
            
        Returns:
            Dictionary mapping file names to file paths
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        generated_files = {}
        
        # Generate updated database timeout configuration
        db_config = self._generate_database_config()
        db_config_path = output_dir / "database_timeout_config_issue_1278.py"
        with open(db_config_path, 'w') as f:
            f.write(db_config)
        generated_files["database_config"] = str(db_config_path)
        
        # Generate VPC connector monitoring configuration
        vpc_config = self._generate_vpc_config()
        vpc_config_path = output_dir / "vpc_connector_config_issue_1278.yaml"
        with open(vpc_config_path, 'w') as f:
            f.write(vpc_config)
        generated_files["vpc_config"] = str(vpc_config_path)
        
        # Generate deployment script updates
        deploy_updates = self._generate_deploy_script_updates()
        deploy_path = output_dir / "deploy_script_updates_issue_1278.py"
        with open(deploy_path, 'w') as f:
            f.write(deploy_updates)
        generated_files["deploy_updates"] = str(deploy_path)
        
        return generated_files
    
    def _generate_database_config(self) -> str:
        """Generate updated database configuration code."""
        return '''# Database configuration updates for Issue #1278
# Updated timeout values to handle VPC connector capacity constraints

STAGING_DATABASE_CONFIG = {
    "initialization_timeout": 45.0,  # Increased from 25.0s
    "connection_timeout": 25.0,      # Increased from 15.0s
    "pool_timeout": 30.0,            # Increased from 15.0s
    "health_check_timeout": 15.0,    # Increased from 10.0s
    "table_setup_timeout": 15.0,     # Increased from 10.0s
}

CLOUD_SQL_POOL_CONFIG = {
    "pool_size": 10,                 # Reduced from 15
    "max_overflow": 15,              # Reduced from 25
    "pool_timeout": 90.0,            # Increased from 60.0s
    "capacity_safety_margin": 0.8,   # New: 80% safety margin
}
'''
    
    def _generate_vpc_config(self) -> str:
        """Generate VPC connector monitoring configuration."""
        return '''# VPC Connector monitoring configuration for Issue #1278
vpc_connector:
  monitoring:
    enabled: true
    capacity_threshold: 0.7
    scaling_buffer_timeout: 20.0
    monitoring_interval: 30
  
  capacity_limits:
    concurrent_connections: 50
    throughput_baseline_gbps: 2.0
    throughput_max_gbps: 10.0
    
  alerting:
    capacity_pressure_threshold: 70%
    scaling_event_notification: true
    performance_degradation_threshold: 100ms
'''
    
    def _generate_deploy_script_updates(self) -> str:
        """Generate deployment script configuration updates."""
        return '''# Deployment script updates for Issue #1278
# Resource allocation updates for staging environment

# Backend service resource allocation (Updated for Issue #1278)
BACKEND_MEMORY = "4Gi"  # Increased from 2Gi
BACKEND_CPU = "4"       # Increased from 2

# Service configuration updates
SERVICE_CONFIG_UPDATES = {
    "SERVICE_ID": "netra-backend",  # Fixed from problematic staging ID
    "HEALTH_CHECK_TIMEOUT": 60,     # Extended from 30s
    "STARTUP_TIMEOUT": 600,         # 10 minutes for capacity-aware startup
}

# VPC connector specific configuration
VPC_CONNECTOR_CONFIG = {
    "min_instances": 1,             # Ensure baseline capacity
    "max_instances": 10,            # Allow scaling for demand
    "concurrency": 1000,            # Per-instance concurrency
}
'''


def get_issue_1278_remediation_plan() -> Dict[str, Any]:
    """Get complete Issue #1278 infrastructure remediation plan.
    
    Returns:
        Comprehensive remediation plan
    """
    config_manager = Issue1278InfrastructureConfig()
    return config_manager.get_staging_remediation_plan()


def generate_infrastructure_configs(output_directory: str = "deployment/issue_1278_configs") -> Dict[str, str]:
    """Generate infrastructure configuration files for Issue #1278.
    
    Args:
        output_directory: Directory to write configuration files
        
    Returns:
        Dictionary of generated file paths
    """
    config_manager = Issue1278InfrastructureConfig()
    return config_manager.generate_configuration_files(Path(output_directory))


if __name__ == "__main__":
    # Generate remediation plan and configuration files
    plan = get_issue_1278_remediation_plan()
    
    print("Issue #1278 Infrastructure Remediation Plan")
    print("=" * 50)
    print(f"Environment: {plan['environment']}")
    print(f"Total Updates: {plan['total_updates']}")
    print(f"Critical Updates: {plan['critical_updates']}")
    print(f"Implementation Phases: {plan['implementation_phases']}")
    
    for phase in plan['phases']:
        print(f"\n{phase['phase']} (Priority: {phase['priority']})")
        for update in phase['updates']:
            print(f"  - {update['component']}: {update['description']}")
    
    # Generate configuration files
    generated_files = generate_infrastructure_configs()
    print(f"\nGenerated {len(generated_files)} configuration files:")
    for config_type, file_path in generated_files.items():
        print(f"  - {config_type}: {file_path}")