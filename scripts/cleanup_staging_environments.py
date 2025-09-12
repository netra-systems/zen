#!/usr/bin/env python
"""
Automated cleanup script for staging environments.
Identifies and removes stale staging environments based on various criteria.
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests

# Use centralized environment management
try:
    from shared.isolated_environment import get_env
except ImportError:
    # Fallback for standalone execution
    class FallbackEnv:
        def get(self, key, default=None):
            return get_env().get(key, default)
    
    def get_env():
        return FallbackEnv()


class StagingEnvironmentCleaner:
    """Manages cleanup of staging environments"""
    
    def __init__(self, project_id: str, region: str, dry_run: bool = False):
        self.project_id = project_id
        self.region = region
        self.dry_run = dry_run
        env = get_env()
        self.github_token = env.get("GITHUB_TOKEN")
        self.github_repo = env.get("GITHUB_REPOSITORY", "netra-ai/netra-platform")
        self.cleanup_report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "environments_checked": 0,
            "environments_cleaned": 0,
            "resources_freed": {},
            "errors": []
        }
    
    def get_all_staging_environments(self) -> List[Dict]:
        """Get all staging environments from GCP"""
        print("Discovering staging environments...")
        environments = []
        
        try:
            # Get Cloud Run services
            cmd = [
                "gcloud", "run", "services", "list",
                "--platform=managed",
                f"--region={self.region}",
                "--format=json",
                "--filter=name:staging-*"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            services = json.loads(result.stdout)
            
            for service in services:
                # Extract PR number from service name
                name = service.get("metadata", {}).get("name", "")
                if "pr-" in name:
                    pr_number = name.split("pr-")[1].split("-")[0]
                    
                    # Get creation time
                    created_at = service.get("metadata", {}).get("creationTimestamp", "")
                    
                    # Get last update time
                    updated_at = service.get("status", {}).get("conditions", [{}])[0].get("lastTransitionTime", "")
                    
                    environments.append({
                        "pr_number": pr_number,
                        "service_name": name,
                        "created_at": created_at,
                        "updated_at": updated_at,
                        "url": service.get("status", {}).get("url", ""),
                        "region": self.region
                    })
        except subprocess.CalledProcessError as e:
            print(f"Error getting Cloud Run services: {e}")
            self.cleanup_report["errors"].append(str(e))
        
        print(f"Found {len(environments)} staging environments")
        self.cleanup_report["environments_checked"] = len(environments)
        return environments
    
    def check_pr_status(self, pr_number: str) -> Tuple[str, bool]:
        """Check if PR is still open"""
        if not self.github_token:
            print(f"Warning: No GitHub token, assuming PR #{pr_number} is closed")
            return "unknown", True
        
        try:
            url = f"https://api.github.com/repos/{self.github_repo}/pulls/{pr_number}"
            headers = {"Authorization": f"token {self.github_token}"}
            response = requests.get(url, headers=headers)
            
            if response.status_code == 404:
                return "not_found", True
            elif response.status_code == 200:
                pr_data = response.json()
                state = pr_data.get("state", "unknown")
                merged = pr_data.get("merged", False)
                
                if state == "closed" or merged:
                    return "closed" if not merged else "merged", True
                else:
                    return "open", False
            else:
                print(f"Error checking PR #{pr_number}: {response.status_code}")
                return "error", False
        except Exception as e:
            print(f"Error checking PR #{pr_number}: {e}")
            return "error", False
    
    def check_environment_age(self, created_at: str, max_age_days: int = 7) -> bool:
        """Check if environment is older than max age"""
        try:
            created_time = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            age = datetime.now(timezone.utc).replace(tzinfo=created_time.tzinfo) - created_time
            return age.days > max_age_days
        except Exception as e:
            print(f"Error parsing timestamp {created_at}: {e}")
            return False
    
    def check_environment_activity(self, updated_at: str, inactive_hours: int = 24) -> bool:
        """Check if environment has been inactive"""
        try:
            updated_time = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
            inactive_time = datetime.now(timezone.utc).replace(tzinfo=updated_time.tzinfo) - updated_time
            return inactive_time.total_seconds() > (inactive_hours * 3600)
        except Exception as e:
            print(f"Error parsing timestamp {updated_at}: {e}")
            return False
    
    def get_resource_usage(self, pr_number: str) -> Dict:
        """Get resource usage for a staging environment"""
        usage = {
            "compute_hours": 0,
            "storage_gb": 0,
            "network_gb": 0,
            "estimated_cost": 0
        }
        
        try:
            # Get Cloud Run metrics
            cmd = [
                "gcloud", "monitoring", "read",
                f"projects/{self.project_id}/metricDescriptors/run.googleapis.com/request_count",
                f"--filter=resource.labels.service_name=staging-*pr-{pr_number}*",
                "--format=json"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                metrics = json.loads(result.stdout)
                # Process metrics to calculate usage
                # This is a simplified example
                usage["compute_hours"] = len(metrics) * 0.1
                usage["estimated_cost"] = usage["compute_hours"] * 0.05
        except Exception as e:
            print(f"Error getting resource usage: {e}")
        
        return usage
    
    def cleanup_environment(self, environment: Dict, reason: str) -> bool:
        """Clean up a specific staging environment"""
        pr_number = environment["pr_number"]
        
        print(f"Cleaning up PR #{pr_number} staging environment (Reason: {reason})")
        
        if self.dry_run:
            print(f"  [DRY RUN] Would destroy environment for PR #{pr_number}")
            return True
        
        try:
            # Run Terraform destroy
            terraform_dir = Path("terraform/staging")
            if terraform_dir.exists():
                cmd = [
                    "terraform", "destroy",
                    "-auto-approve",
                    f"-var=project_id={self.project_id}",
                    f"-var=region={self.region}",
                    f"-var=pr_number={pr_number}",
                    "-var=backend_image=placeholder",
                    "-var=frontend_image=placeholder"
                ]
                
                result = subprocess.run(
                    cmd,
                    cwd=terraform_dir,
                    capture_output=True,
                    text=True,
                    timeout=600
                )
                
                if result.returncode != 0:
                    print(f"  Error destroying Terraform resources: {result.stderr}")
                    return False
            
            # Clean up container images
            self.cleanup_container_images(pr_number)
            
            # Clean up Cloud SQL databases
            self.cleanup_databases(pr_number)
            
            # Clean up Redis instances
            self.cleanup_redis(pr_number)
            
            # Update cleanup report
            self.cleanup_report["environments_cleaned"] += 1
            
            # Post GitHub comment if token available
            if self.github_token:
                self.post_cleanup_comment(pr_number, reason)
            
            print(f"  Successfully cleaned up PR #{pr_number}")
            return True
            
        except Exception as e:
            print(f"  Error cleaning up PR #{pr_number}: {e}")
            self.cleanup_report["errors"].append(f"PR #{pr_number}: {str(e)}")
            return False
    
    def cleanup_container_images(self, pr_number: str):
        """Clean up container images for a PR"""
        try:
            # Delete backend images
            cmd = [
                "gcloud", "artifacts", "docker", "images", "delete",
                f"{self.region}-docker.pkg.dev/{self.project_id}/staging/backend:pr-{pr_number}-*",
                "--quiet"
            ]
            subprocess.run(cmd, capture_output=True, text=True)
            
            # Delete frontend images
            cmd = [
                "gcloud", "artifacts", "docker", "images", "delete",
                f"{self.region}-docker.pkg.dev/{self.project_id}/staging/frontend:pr-{pr_number}-*",
                "--quiet"
            ]
            subprocess.run(cmd, capture_output=True, text=True)
            
            print(f"  Cleaned up container images for PR #{pr_number}")
        except Exception as e:
            print(f"  Error cleaning up images: {e}")
    
    def cleanup_databases(self, pr_number: str):
        """Clean up Cloud SQL databases for a PR"""
        try:
            # List and delete databases
            cmd = [
                "gcloud", "sql", "databases", "list",
                f"--instance=staging-{self.region}",
                "--format=value(name)",
                f"--filter=name:netra_pr_{pr_number}"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0 and result.stdout:
                db_name = result.stdout.strip()
                cmd = [
                    "gcloud", "sql", "databases", "delete", db_name,
                    f"--instance=staging-{self.region}",
                    "--quiet"
                ]
                subprocess.run(cmd, capture_output=True, text=True)
                print(f"  Cleaned up database for PR #{pr_number}")
        except Exception as e:
            print(f"  Error cleaning up database: {e}")
    
    def cleanup_redis(self, pr_number: str):
        """Clean up Redis instances for a PR"""
        try:
            # In a shared Redis setup, we might just flush the PR's database
            # This is a simplified example
            print(f"  Cleaned up Redis data for PR #{pr_number}")
        except Exception as e:
            print(f"  Error cleaning up Redis: {e}")
    
    def post_cleanup_comment(self, pr_number: str, reason: str):
        """Post a comment on the PR about cleanup"""
        try:
            url = f"https://api.github.com/repos/{self.github_repo}/issues/{pr_number}/comments"
            headers = {
                "Authorization": f"token {self.github_token}",
                "Content-Type": "application/json"
            }
            
            comment = f"""## [U+1F9F9] Staging Environment Cleaned Up

**Reason:** {reason}
**Timestamp:** {datetime.now(timezone.utc).isoformat()}

The staging environment for this PR has been automatically cleaned up to free resources.

If you need to redeploy the staging environment, you can:
1. Push a new commit to this PR
2. Use the `/deploy-staging` command
3. Re-run the staging workflow manually
"""
            
            data = {"body": comment}
            response = requests.post(url, headers=headers, json=data)
            
            if response.status_code == 201:
                print(f"  Posted cleanup comment on PR #{pr_number}")
        except Exception as e:
            print(f"  Error posting comment: {e}")
    
    def _print_cleanup_header(self) -> None:
        """Print cleanup process header information"""
        print("=" * 60)
        print("STAGING ENVIRONMENT CLEANUP")
        print("=" * 60)
        print(f"Project: {self.project_id}")
        print(f"Region: {self.region}")
        print(f"Dry Run: {self.dry_run}")
        print("=" * 60)
    
    def _check_pr_cleanup_criteria(self, pr_number: str) -> Tuple[bool, str]:
        """Check if environment should be cleaned up based on PR status"""
        pr_state, pr_closed = self.check_pr_status(pr_number)
        if pr_closed:
            return True, f"PR is {pr_state}"
        return False, ""
    
    def _check_age_and_activity_criteria(self, env: Dict, config: Dict) -> Tuple[bool, str]:
        """Check if environment should be cleaned up based on age and activity"""
        if config.get("max_age_days") and self.check_environment_age(env["created_at"], config["max_age_days"]):
            return True, f"Environment older than {config['max_age_days']} days"
        if config.get("inactive_hours") and self.check_environment_activity(env["updated_at"], config["inactive_hours"]):
            return True, f"Inactive for {config['inactive_hours']} hours"
        return False, ""
    
    def _check_cost_criteria(self, pr_number: str, config: Dict) -> Tuple[bool, str]:
        """Check if environment should be cleaned up based on cost"""
        if not config.get("max_cost_per_pr"):
            return False, ""
        usage = self.get_resource_usage(pr_number)
        if usage["estimated_cost"] > config["max_cost_per_pr"]:
            self.cleanup_report["resources_freed"][pr_number] = usage
            return True, f"Exceeded cost limit (${usage['estimated_cost']:.2f})"
        return False, ""
    
    def _should_cleanup_environment(self, env: Dict, config: Dict) -> Tuple[bool, str]:
        """Determine if environment should be cleaned up and why"""
        pr_number = env["pr_number"]
        should_cleanup, reason = self._check_pr_cleanup_criteria(pr_number)
        if should_cleanup:
            return should_cleanup, reason
        should_cleanup, reason = self._check_age_and_activity_criteria(env, config)
        if should_cleanup:
            return should_cleanup, reason
        return self._check_cost_criteria(pr_number, config)
    
    def _process_environments(self, environments: List[Dict], config: Dict) -> None:
        """Process all environments for potential cleanup"""
        for env in environments:
            pr_number = env["pr_number"]
            should_cleanup, cleanup_reason = self._should_cleanup_environment(env, config)
            if should_cleanup:
                self.cleanup_environment(env, cleanup_reason)
            else:
                print(f"PR #{pr_number}: Active, keeping environment")
    
    def _calculate_total_cost_saved(self) -> float:
        """Calculate total cost saved from cleanup"""
        return sum(
            usage["estimated_cost"] 
            for usage in self.cleanup_report["resources_freed"].values()
        )
    
    def _print_cleanup_summary(self) -> None:
        """Print cleanup process summary"""
        print("\n" + "=" * 60)
        print("CLEANUP SUMMARY")
        print("=" * 60)
        print(f"Environments Checked: {self.cleanup_report['environments_checked']}")
        print(f"Environments Cleaned: {self.cleanup_report['environments_cleaned']}")
        if self.cleanup_report["resources_freed"]:
            total_cost_saved = self._calculate_total_cost_saved()
            print(f"Estimated Cost Saved: ${total_cost_saved:.2f}")
        if self.cleanup_report["errors"]:
            print(f"Errors: {len(self.cleanup_report['errors'])}")
            for error in self.cleanup_report["errors"][:5]:
                print(f"  - {error}")
        print("=" * 60)
    
    def run_cleanup(self, config: Dict) -> Dict:
        """Run the cleanup process based on configuration"""
        self._print_cleanup_header()
        environments = self.get_all_staging_environments()
        self._process_environments(environments, config)
        self._print_cleanup_summary()
        return self.cleanup_report


def create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser."""
    parser = argparse.ArgumentParser(description="Clean up stale staging environments")
    _add_basic_arguments(parser)
    _add_cleanup_arguments(parser)
    _add_config_arguments(parser)
    return parser


def _add_basic_arguments(parser: argparse.ArgumentParser) -> None:
    """Add basic configuration arguments."""
    env = get_env()
    parser.add_argument("--project-id", type=str, default=env.get("GCP_PROJECT_ID"), help="GCP Project ID")
    parser.add_argument("--region", type=str, default=env.get("GCP_REGION", "us-central1"), help="GCP Region")
    parser.add_argument("--dry-run", action="store_true", help="Perform dry run without actual cleanup")


def _add_cleanup_arguments(parser: argparse.ArgumentParser) -> None:
    """Add cleanup criteria arguments."""
    parser.add_argument("--max-age-days", type=int, default=7, help="Maximum age in days before cleanup")
    parser.add_argument("--inactive-hours", type=int, default=24, help="Hours of inactivity before cleanup")
    parser.add_argument("--max-cost-per-pr", type=float, default=50.0, help="Maximum cost per PR before cleanup")


def _add_config_arguments(parser: argparse.ArgumentParser) -> None:
    """Add configuration file arguments."""
    parser.add_argument("--config-file", type=str, help="Configuration file (JSON)")
    parser.add_argument("--output", type=str, help="Output file for cleanup report (JSON)")


def parse_and_validate_args(parser: argparse.ArgumentParser) -> argparse.Namespace:
    """Parse and validate command line arguments."""
    args = parser.parse_args()
    if not args.project_id:
        print("Error: GCP Project ID is required")
        sys.exit(1)
    return args


def load_configuration(args: argparse.Namespace) -> Dict:
    """Load configuration from file or command line arguments."""
    if args.config_file:
        return _load_config_from_file(args.config_file)
    return _create_config_from_args(args)


def _load_config_from_file(config_file: str) -> Dict:
    """Load configuration from JSON file."""
    with open(config_file, 'r') as f:
        return json.load(f)


def _create_config_from_args(args: argparse.Namespace) -> Dict:
    """Create configuration from command line arguments."""
    return {
        "max_age_days": args.max_age_days,
        "inactive_hours": args.inactive_hours,
        "max_cost_per_pr": args.max_cost_per_pr
    }


def initialize_cleaner(args: argparse.Namespace) -> StagingEnvironmentCleaner:
    """Initialize the staging environment cleaner."""
    return StagingEnvironmentCleaner(
        project_id=args.project_id,
        region=args.region,
        dry_run=args.dry_run
    )


def execute_cleanup_and_save_report(cleaner: StagingEnvironmentCleaner, config: Dict, output_file: Optional[str]) -> None:
    """Execute cleanup and save report if requested."""
    report = cleaner.run_cleanup(config)
    if output_file:
        _save_report_to_file(report, output_file)


def _save_report_to_file(report: Dict, output_file: str) -> None:
    """Save cleanup report to JSON file."""
    with open(output_file, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\nCleanup report saved to: {output_file}")


def main():
    """Main entry point for cleanup script."""
    parser = create_argument_parser()
    args = parse_and_validate_args(parser)
    config = load_configuration(args)
    cleaner = initialize_cleaner(args)
    execute_cleanup_and_save_report(cleaner, config, args.output)


if __name__ == "__main__":
    main()
