#!/usr/bin/env python3
"""
Fix Staging Database Connection Issues

This script diagnoses and fixes database connection issues in the staging environment.
Specifically addresses Cloud SQL proxy configuration and service startup failures.
"""

import logging
import subprocess
import json
import sys
import time
from typing import Dict, List, Optional, Tuple

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class StagingDatabaseFixer:
    """Fix staging database connection issues."""
    
    def __init__(self):
        self.project_id = "netra-staging"
        self.region = "us-central1"
        self.instance_name = "staging-shared-postgres"
        self.service_name = "netra-backend-staging"
        
    def check_cloud_sql_instance(self) -> Tuple[bool, str]:
        """Check if Cloud SQL instance is running and accessible."""
        logger.info("Checking Cloud SQL instance status...")
        
        try:
            cmd = [
                "gcloud", "sql", "instances", "describe", self.instance_name,
                "--project", self.project_id,
                "--format", "json"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            instance_info = json.loads(result.stdout)
            
            state = instance_info.get("state", "UNKNOWN")
            backend_type = instance_info.get("backendType", "UNKNOWN")
            availability_type = instance_info.get("settings", {}).get("availabilityType", "UNKNOWN")
            
            logger.info(f"Instance state: {state}")
            logger.info(f"Backend type: {backend_type}")
            logger.info(f"Availability type: {availability_type}")
            
            if state == "RUNNABLE":
                return True, f"Instance is running ({backend_type}, {availability_type})"
            else:
                return False, f"Instance is not running - state: {state}"
                
        except subprocess.CalledProcessError as e:
            error_msg = f"Failed to check instance: {e.stderr}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Unexpected error checking instance: {e}"
            logger.error(error_msg)
            return False, error_msg
    
    def check_cloud_run_service(self) -> Tuple[bool, Dict]:
        """Check Cloud Run service status and configuration."""
        logger.info("Checking Cloud Run service status...")
        
        try:
            cmd = [
                "gcloud", "run", "services", "describe", self.service_name,
                "--region", self.region,
                "--project", self.project_id,
                "--format", "json"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            service_info = json.loads(result.stdout)
            
            # Extract key information
            status = service_info.get("status", {})
            conditions = status.get("conditions", [])
            url = status.get("url", "No URL")
            
            # Check if service is ready
            ready_condition = next(
                (c for c in conditions if c.get("type") == "Ready"), 
                {}
            )
            
            is_ready = ready_condition.get("status") == "True"
            ready_message = ready_condition.get("message", "No message")
            
            # Get environment variables
            spec = service_info.get("spec", {})
            template = spec.get("template", {})
            containers = template.get("spec", {}).get("containers", [])
            
            env_vars = {}
            if containers:
                env_vars = {
                    env.get("name"): env.get("value", "***") 
                    for env in containers[0].get("env", [])
                    if env.get("name", "").startswith("POSTGRES_")
                }
            
            service_status = {
                "ready": is_ready,
                "url": url,
                "message": ready_message,
                "postgres_env": env_vars
            }
            
            logger.info(f"Service ready: {is_ready}")
            logger.info(f"Service URL: {url}")
            logger.info(f"Ready message: {ready_message}")
            
            return is_ready, service_status
            
        except subprocess.CalledProcessError as e:
            error_msg = f"Failed to check service: {e.stderr}"
            logger.error(error_msg)
            return False, {"error": error_msg}
        except Exception as e:
            error_msg = f"Unexpected error checking service: {e}"
            logger.error(error_msg)
            return False, {"error": error_msg}
    
    def check_service_logs(self) -> List[str]:
        """Get recent service logs to diagnose startup issues."""
        logger.info("Checking service logs for database errors...")
        
        try:
            cmd = [
                "gcloud", "logs", "read",
                f'resource.type="cloud_run_revision" AND resource.labels.service_name="{self.service_name}"',
                "--project", self.project_id,
                "--limit", "50",
                "--format", "value(textPayload,jsonPayload.message)"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            logs = [line.strip() for line in result.stdout.split('\n') if line.strip()]
            
            # Filter for database-related errors
            db_logs = [
                log for log in logs 
                if any(keyword in log.lower() for keyword in [
                    'database', 'postgres', 'sql', 'connection', 'timeout', 'initialize'
                ])
            ]
            
            logger.info(f"Found {len(db_logs)} database-related log entries")
            for log in db_logs[:10]:  # Show first 10
                logger.info(f"LOG: {log}")
            
            return db_logs
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to get logs: {e.stderr}")
            return [f"Error getting logs: {e.stderr}"]
        except Exception as e:
            logger.error(f"Unexpected error getting logs: {e}")
            return [f"Unexpected error: {e}"]
    
    def fix_cloud_run_configuration(self) -> bool:
        """Update Cloud Run service with proper Cloud SQL configuration."""
        logger.info("Updating Cloud Run service configuration...")
        
        try:
            # Build the gcloud command to update the service
            cmd = [
                "gcloud", "run", "services", "update", self.service_name,
                "--region", self.region,
                "--project", self.project_id,
                # Add Cloud SQL connection
                "--add-cloudsql-instances", f"{self.project_id}:us-central1:staging-shared-postgres",
                # Set longer startup timeout for database initialization
                "--timeout", "300",
                # Increase memory for database operations
                "--memory", "1Gi",
                # Set environment-specific configuration
                "--set-env-vars", "ENVIRONMENT=staging",
                "--set-env-vars", "LOG_LEVEL=info",
                # Allow more time for container startup
                "--cpu-boost"
            ]
            
            logger.info("Executing: " + " ".join(cmd))
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            logger.info("Service configuration updated successfully")
            logger.info("Waiting for new revision to be ready...")
            
            # Wait for the service to be ready
            time.sleep(30)
            
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to update service: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error updating service: {e}")
            return False
    
    def verify_database_connectivity(self) -> bool:
        """Test database connectivity after fixes."""
        logger.info("Testing database connectivity...")
        
        # Wait a bit more for service to stabilize
        time.sleep(60)
        
        is_ready, service_info = self.check_cloud_run_service()
        
        if is_ready and "url" in service_info and service_info["url"] != "No URL":
            service_url = service_info["url"]
            logger.info(f"Testing health endpoint: {service_url}/health")
            
            try:
                import requests
                response = requests.get(f"{service_url}/health", timeout=30)
                
                if response.status_code == 200:
                    logger.info("✅ Service health check passed!")
                    return True
                else:
                    logger.error(f"❌ Health check failed: {response.status_code}")
                    logger.error(f"Response: {response.text}")
                    return False
                    
            except Exception as e:
                logger.error(f"❌ Failed to test connectivity: {e}")
                return False
        else:
            logger.error("❌ Service is not ready or has no URL")
            return False
    
    def run_diagnosis(self) -> Dict[str, any]:
        """Run complete diagnosis of staging database issues."""
        logger.info("🔍 Starting staging database diagnosis...")
        
        results = {}
        
        # Check Cloud SQL instance
        sql_ready, sql_message = self.check_cloud_sql_instance()
        results["cloud_sql"] = {"ready": sql_ready, "message": sql_message}
        
        # Check Cloud Run service
        service_ready, service_info = self.check_cloud_run_service()
        results["cloud_run"] = {"ready": service_ready, "info": service_info}
        
        # Get logs
        logs = self.check_service_logs()
        results["logs"] = logs
        
        return results
    
    def run_fix(self) -> bool:
        """Run complete fix process."""
        logger.info("🔧 Starting staging database fix...")
        
        # First, run diagnosis
        diagnosis = self.run_diagnosis()
        
        # If Cloud SQL is not ready, we can't proceed
        if not diagnosis["cloud_sql"]["ready"]:
            logger.error("❌ Cloud SQL instance is not ready - cannot fix")
            return False
        
        # If service is not ready, try to fix configuration
        if not diagnosis["cloud_run"]["ready"]:
            logger.info("🔧 Service is not ready - attempting configuration fix...")
            
            if not self.fix_cloud_run_configuration():
                logger.error("❌ Failed to fix Cloud Run configuration")
                return False
            
            # Verify the fix worked
            if self.verify_database_connectivity():
                logger.info("✅ Database connectivity fix successful!")
                return True
            else:
                logger.error("❌ Database connectivity still not working after fix")
                return False
        else:
            logger.info("✅ Service appears to be ready already")
            return self.verify_database_connectivity()

def main():
    """Main function."""
    if len(sys.argv) > 1 and sys.argv[1] == "--fix":
        # Run fix
        fixer = StagingDatabaseFixer()
        success = fixer.run_fix()
        sys.exit(0 if success else 1)
    else:
        # Run diagnosis only
        fixer = StagingDatabaseFixer()
        diagnosis = fixer.run_diagnosis()
        
        print("\n" + "="*60)
        print("STAGING DATABASE DIAGNOSIS SUMMARY")
        print("="*60)
        
        print(f"Cloud SQL Instance: {'✅ Ready' if diagnosis['cloud_sql']['ready'] else '❌ Not Ready'}")
        print(f"  Message: {diagnosis['cloud_sql']['message']}")
        
        print(f"Cloud Run Service: {'✅ Ready' if diagnosis['cloud_run']['ready'] else '❌ Not Ready'}")
        service_info = diagnosis['cloud_run']['info']
        if isinstance(service_info, dict):
            print(f"  URL: {service_info.get('url', 'No URL')}")
            print(f"  Message: {service_info.get('message', 'No message')}")
            
            postgres_env = service_info.get('postgres_env', {})
            if postgres_env:
                print("  Database Environment Variables:")
                for key, value in postgres_env.items():
                    print(f"    {key}: {value}")
        
        print(f"Recent Database Logs: {len(diagnosis['logs'])} entries")
        for log in diagnosis['logs'][:5]:  # Show first 5
            print(f"  • {log}")
        
        print("\n" + "="*60)
        print("RECOMMENDATIONS:")
        
        if not diagnosis['cloud_sql']['ready']:
            print("❌ Start the Cloud SQL instance first")
        elif not diagnosis['cloud_run']['ready']:
            print("🔧 Run with --fix to update Cloud Run configuration")
        else:
            print("✅ Both services appear ready - check application logs for specific errors")
        
        print("="*60)
        
        return 0 if diagnosis['cloud_sql']['ready'] and diagnosis['cloud_run']['ready'] else 1

if __name__ == "__main__":
    sys.exit(main())