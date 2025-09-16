#!/usr/bin/env python3
"""
Deploy Staging Infrastructure Script
CRITICAL: Deploys missing GCP infrastructure for staging environment

Addresses:
- Missing Redis Memory Store (causing 45+ P0 incidents)
- VPC connector issues (preventing Cloud Run connectivity)
- Database timeout configuration
- Load balancer WebSocket support

Business Impact: Restores $500K+ ARR systems and Golden Path functionality
"""

import subprocess
import sys
import json
import time
from pathlib import Path
from typing import Dict, List, Optional

def run_command(cmd: List[str], description: str, cwd: Optional[Path] = None) -> tuple[bool, str]:
    """Run a command and return success status and output."""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=300  # 5 minute timeout
        )

        if result.returncode == 0:
            print(f"✅ {description} - SUCCESS")
            return True, result.stdout
        else:
            print(f"❌ {description} - FAILED")
            print(f"Error: {result.stderr}")
            return False, result.stderr

    except subprocess.TimeoutExpired:
        print(f"⏰ {description} - TIMEOUT")
        return False, "Command timed out"
    except Exception as e:
        print(f"💥 {description} - EXCEPTION: {e}")
        return False, str(e)

def check_terraform_status(terraform_dir: Path) -> Dict[str, any]:
    """Check current Terraform state and plan."""
    print("📋 Checking Terraform status...")

    # Initialize Terraform
    success, output = run_command(
        ["terraform", "init"],
        "Terraform initialization",
        cwd=terraform_dir
    )
    if not success:
        return {"initialized": False, "error": output}

    # Validate configuration
    success, output = run_command(
        ["terraform", "validate"],
        "Terraform validation",
        cwd=terraform_dir
    )
    if not success:
        return {"initialized": True, "valid": False, "error": output}

    # Plan infrastructure
    success, output = run_command(
        ["terraform", "plan", "-var-file=staging.tfvars", "-out=staging.tfplan"],
        "Terraform planning",
        cwd=terraform_dir
    )

    return {
        "initialized": True,
        "valid": True,
        "plan_success": success,
        "plan_output": output
    }

def deploy_infrastructure(terraform_dir: Path) -> bool:
    """Deploy the infrastructure using Terraform."""
    print("🚀 Deploying infrastructure...")

    # Apply the plan
    success, output = run_command(
        ["terraform", "apply", "-auto-approve", "staging.tfplan"],
        "Terraform infrastructure deployment",
        cwd=terraform_dir
    )

    if success:
        print("🎉 Infrastructure deployment completed successfully!")

        # Get outputs
        success, outputs = run_command(
            ["terraform", "output", "-json"],
            "Getting Terraform outputs",
            cwd=terraform_dir
        )

        if success:
            try:
                output_data = json.loads(outputs)
                print("📊 Infrastructure Outputs:")
                for key, value in output_data.items():
                    print(f"  {key}: {value.get('value', 'N/A')}")
            except json.JSONDecodeError:
                print("⚠️ Could not parse Terraform outputs")

        return True
    else:
        print("❌ Infrastructure deployment failed!")
        return False

def validate_infrastructure_health() -> Dict[str, bool]:
    """Validate that deployed infrastructure is healthy."""
    print("🏥 Validating infrastructure health...")

    health_checks = {}

    # Check VPC connector
    success, output = run_command(
        ["gcloud", "compute", "networks", "vpc-access", "connectors", "list",
         "--region=us-central1", "--project=netra-staging"],
        "VPC connector status check"
    )
    health_checks["vpc_connector"] = success and "staging-connector" in output

    # Check Redis instance
    success, output = run_command(
        ["gcloud", "redis", "instances", "list",
         "--region=us-central1", "--project=netra-staging"],
        "Redis instance status check"
    )
    health_checks["redis"] = success and "staging-redis" in output

    # Check Cloud SQL instance
    success, output = run_command(
        ["gcloud", "sql", "instances", "list", "--project=netra-staging"],
        "Cloud SQL instance status check"
    )
    health_checks["cloud_sql"] = success and "staging-postgres" in output

    # Print health summary
    print("📊 Infrastructure Health Summary:")
    for component, healthy in health_checks.items():
        status = "✅ HEALTHY" if healthy else "❌ UNHEALTHY"
        print(f"  {component}: {status}")

    return health_checks

def main():
    """Main deployment function."""
    print("🚨 STAGING INFRASTRUCTURE DEPLOYMENT")
    print("===================================")
    print("CRITICAL: Fixing missing infrastructure causing P0 incidents")
    print("Business Impact: Restoring $500K+ ARR systems")
    print()

    # Paths
    project_root = Path(__file__).parent.parent
    terraform_dir = project_root / "terraform-gcp-staging"

    if not terraform_dir.exists():
        print(f"❌ Terraform directory not found: {terraform_dir}")
        sys.exit(1)

    if not (terraform_dir / "staging.tfvars").exists():
        print(f"❌ Staging tfvars file not found: {terraform_dir}/staging.tfvars")
        sys.exit(1)

    # Phase 1: Check Terraform status
    print("📋 PHASE 1: Terraform Status Check")
    status = check_terraform_status(terraform_dir)

    if not status["initialized"]:
        print("❌ Terraform initialization failed!")
        sys.exit(1)

    if not status["valid"]:
        print("❌ Terraform configuration invalid!")
        sys.exit(1)

    if not status["plan_success"]:
        print("❌ Terraform planning failed!")
        print("This could indicate missing resources or configuration issues.")
        print("Output:", status.get("plan_output", "No output"))
        sys.exit(1)

    # Phase 2: Deploy infrastructure
    print("\\n🚀 PHASE 2: Infrastructure Deployment")
    deployment_success = deploy_infrastructure(terraform_dir)

    if not deployment_success:
        print("❌ Infrastructure deployment failed!")
        sys.exit(1)

    # Phase 3: Validate infrastructure health
    print("\\n🏥 PHASE 3: Infrastructure Health Validation")
    health_results = validate_infrastructure_health()

    # Check if all components are healthy
    all_healthy = all(health_results.values())

    if all_healthy:
        print("\\n🎉 SUCCESS: All infrastructure components are healthy!")
        print("✅ VPC connector deployed")
        print("✅ Redis Memory Store operational")
        print("✅ Cloud SQL instance running")
        print("\\n🚀 Ready for application deployment and Golden Path testing")

    else:
        print("\\n⚠️ WARNING: Some infrastructure components are not healthy")
        print("This may require manual intervention or additional configuration")

        unhealthy = [comp for comp, healthy in health_results.items() if not healthy]
        print(f"Unhealthy components: {unhealthy}")

    print("\\n📋 NEXT STEPS:")
    print("1. Redeploy applications with new infrastructure")
    print("2. Run Golden Path validation tests")
    print("3. Monitor for error reduction (target: <5 incidents/hour)")
    print("4. Validate WebSocket connectivity and agent execution")

if __name__ == "__main__":
    main()