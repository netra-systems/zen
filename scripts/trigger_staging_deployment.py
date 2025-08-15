#!/usr/bin/env python3
"""
Trigger staging deployment workflow via GitHub API
Deploys PR to GCP netra-staging environment
"""

import os
import json
import sys
import time
import requests
from pathlib import Path
from typing import Optional


class StagingDeployer:
    """Deploy PR to GCP staging via GitHub API"""
    
    def __init__(self, token: Optional[str] = None):
        self.owner = "netra-systems"
        self.repo = "netra-apex"
        self.token = token or os.environ.get("GITHUB_TOKEN", "")
        
        if not self.token:
            raise ValueError(
                "GitHub token required. Set GITHUB_TOKEN env var or pass token"
            )
        
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"token {self.token}",
            "X-GitHub-Api-Version": "2022-11-28"
        }
        self.api_base = f"https://api.github.com/repos/{self.owner}/{self.repo}"
        
    def trigger_workflow(
        self, 
        pr_number: int,
        action: str = "deploy",
        branch: Optional[str] = None
    ) -> dict:
        """Trigger staging-environment workflow"""
        
        # Workflow dispatch endpoint
        workflow_id = "staging-environment.yml"
        url = f"{self.api_base}/actions/workflows/{workflow_id}/dispatches"
        
        # Prepare payload
        payload = {
            "ref": branch or "main",
            "inputs": {
                "action": action,
                "pr_number": str(pr_number),
                "force": "false"
            }
        }
        
        if branch:
            payload["inputs"]["branch"] = branch
            
        print(f"🚀 Triggering staging deployment for PR #{pr_number}")
        print(f"   Action: {action}")
        print(f"   Branch: {payload['ref']}")
        
        # Send request
        response = requests.post(url, headers=self.headers, json=payload)
        
        if response.status_code == 204:
            print("✅ Workflow triggered successfully!")
            return {"status": "triggered", "pr": pr_number}
        else:
            print(f"❌ Failed to trigger workflow: {response.status_code}")
            print(f"   Response: {response.text}")
            return {"status": "failed", "error": response.text}
            
    def get_workflow_runs(self, limit: int = 5) -> list:
        """Get recent workflow runs"""
        url = f"{self.api_base}/actions/workflows/staging-environment.yml/runs"
        params = {"per_page": limit}
        
        response = requests.get(url, headers=self.headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            return data.get("workflow_runs", [])
        return []
        
    def wait_for_deployment(
        self, 
        pr_number: int, 
        timeout: int = 600,
        check_interval: int = 30
    ) -> bool:
        """Wait for deployment to complete"""
        
        print(f"\n⏳ Waiting for deployment to start...")
        start_time = time.time()
        
        # Wait for workflow to appear
        workflow_run = None
        while time.time() - start_time < 60:
            runs = self.get_workflow_runs(limit=3)
            for run in runs:
                # Check if this run is for our PR
                if f"pr_number={pr_number}" in str(run) or \
                   f"PR #{pr_number}" in run.get("display_title", ""):
                    workflow_run = run
                    break
            if workflow_run:
                break
            time.sleep(5)
            
        if not workflow_run:
            print("⚠️  Workflow not found in recent runs")
            return False
            
        run_id = workflow_run["id"]
        print(f"📋 Monitoring workflow run #{run_id}")
        print(f"   URL: {workflow_run['html_url']}")
        
        # Monitor workflow progress
        while time.time() - start_time < timeout:
            url = f"{self.api_base}/actions/runs/{run_id}"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                run_data = response.json()
                status = run_data["status"]
                conclusion = run_data.get("conclusion")
                
                print(f"   Status: {status}", end="\r")
                
                if status == "completed":
                    if conclusion == "success":
                        print(f"\n✅ Deployment completed successfully!")
                        self._print_deployment_urls(pr_number)
                        return True
                    else:
                        print(f"\n❌ Deployment failed: {conclusion}")
                        return False
                        
            time.sleep(check_interval)
            
        print(f"\n⏱️  Timeout reached after {timeout} seconds")
        return False
        
    def _print_deployment_urls(self, pr_number: int):
        """Print deployment URLs"""
        env_name = f"netra-staging-pr-{pr_number}"
        print(f"\n🌐 Deployment URLs:")
        print(f"   Environment: {env_name}")
        print(f"   Frontend: https://{env_name}-frontend.netra-staging.com")
        print(f"   Backend: https://{env_name}-backend.netra-staging.com")
        print(f"   API Docs: https://{env_name}-backend.netra-staging.com/docs")
        

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Deploy PR to GCP staging environment"
    )
    parser.add_argument(
        "--pr", 
        type=int, 
        default=9,
        help="PR number to deploy (default: 9)"
    )
    parser.add_argument(
        "--action",
        choices=["deploy", "destroy", "restart", "status"],
        default="deploy",
        help="Action to perform"
    )
    parser.add_argument(
        "--branch",
        help="Branch to deploy (optional)"
    )
    parser.add_argument(
        "--token",
        help="GitHub token (or set GITHUB_TOKEN env var)"
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        help="Wait for deployment to complete"
    )
    
    args = parser.parse_args()
    
    try:
        deployer = StagingDeployer(token=args.token)
        
        # Trigger workflow
        result = deployer.trigger_workflow(
            pr_number=args.pr,
            action=args.action,
            branch=args.branch
        )
        
        if result["status"] == "triggered" and args.wait:
            # Wait for deployment
            success = deployer.wait_for_deployment(args.pr)
            sys.exit(0 if success else 1)
        elif result["status"] == "triggered":
            print(f"\n📌 Check workflow progress at:")
            print(f"   https://github.com/{deployer.owner}/{deployer.repo}/actions")
            sys.exit(0)
        else:
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()