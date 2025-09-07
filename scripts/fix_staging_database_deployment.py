#!/usr/bin/env python3
"""
Fix Staging Database Deployment Issues

This script provides the correct Cloud Run deployment command to fix the database initialization
timeout issue by properly configuring the Cloud SQL proxy connection.
"""

import sys
import os

def generate_cloud_run_fix_commands():
    """Generate the gcloud commands needed to fix the staging database connection."""
    
    project_id = "netra-staging"
    region = "us-central1"
    cloud_sql_instance = f"{project_id}:us-central1:staging-shared-postgres"
    
    print("="*80)
    print("STAGING DATABASE CONNECTION FIX")
    print("="*80)
    print()
    print("PROBLEM ANALYSIS:")
    print("- The backend service is timing out during database initialization")
    print("- The Cloud SQL proxy connection is not properly configured")
    print("- The service needs the --add-cloudsql-instances flag")
    print()
    print("SOLUTION:")
    print("Run the following commands to fix the Cloud Run configuration:")
    print()
    
    # Backend service fix
    backend_cmd = f"""gcloud run services update netra-backend-staging \\
    --region {region} \\
    --project {project_id} \\
    --add-cloudsql-instances {cloud_sql_instance} \\
    --timeout 300 \\
    --memory 1Gi \\
    --set-env-vars ENVIRONMENT=staging \\
    --set-env-vars LOG_LEVEL=info \\
    --cpu-boost"""
    
    print("1. Fix Backend Service:")
    print(backend_cmd)
    print()
    
    # Auth service fix
    auth_cmd = f"""gcloud run services update netra-auth-service \\
    --region {region} \\
    --project {project_id} \\
    --add-cloudsql-instances {cloud_sql_instance} \\
    --timeout 300 \\
    --memory 512Mi \\
    --set-env-vars ENVIRONMENT=staging \\
    --set-env-vars LOG_LEVEL=info"""
    
    print("2. Fix Auth Service:")
    print(auth_cmd)
    print()
    
    # Verification commands
    print("3. Verify the fix:")
    print(f"gcloud run services describe netra-backend-staging --region {region} --project {project_id}")
    print()
    print("4. Check service health:")
    print("# Get the service URL and test:")
    print("curl -f $(gcloud run services describe netra-backend-staging --region us-central1 --project netra-staging --format 'value(status.url)')/health")
    print()
    
    print("EXPECTED RESULT:")
    print("- Services will restart with Cloud SQL proxy enabled")
    print("- Database initialization will succeed")
    print("- Services will return URLs and become accessible")
    print("- Health checks will pass")
    print()
    
    print("CRITICAL CONFIGURATION DETAILS:")
    print(f"- Cloud SQL Instance: {cloud_sql_instance}")
    print("- Expected POSTGRES_HOST: /cloudsql/netra-staging:us-central1:staging-shared-postgres")
    print("- Database: netra_staging (as configured in secrets)")
    print("- Connection: Unix socket via Cloud SQL Proxy")
    print()
    
    return backend_cmd, auth_cmd

def generate_deployment_script_update():
    """Generate the deployment script update to include Cloud SQL proxy by default."""
    
    print("="*80)
    print("DEPLOYMENT SCRIPT UPDATE")
    print("="*80)
    print()
    print("To prevent this issue in future deployments, update scripts/deploy_to_gcp.py")
    print("to include Cloud SQL proxy configuration by default for staging services.")
    print()
    
    script_fix = '''
    # In the deploy_service method, add Cloud SQL configuration for staging
    if self.environment == "staging" and service_name in ["backend", "auth"]:
        cloud_sql_instance = f"{self.project_id}:us-central1:staging-shared-postgres"
        deploy_cmd.extend([
            "--add-cloudsql-instances", cloud_sql_instance,
            "--timeout", "300",
            "--cpu-boost"  # For faster cold starts with database connections
        ])
    '''
    
    print("Add this code block in the deploy_service method:")
    print(script_fix)
    print()

def main():
    """Main function to generate fix commands."""
    
    if len(sys.argv) > 1 and sys.argv[1] == "--script-update":
        generate_deployment_script_update()
        return 0
    
    # Generate the fix commands
    backend_cmd, auth_cmd = generate_cloud_run_fix_commands()
    
    # Option to write commands to files for easy execution
    if len(sys.argv) > 1 and sys.argv[1] == "--save":
        with open("fix_backend_staging.sh", "w") as f:
            f.write("#!/bin/bash\n")
            f.write("# Fix backend staging database connection\n")
            f.write(backend_cmd + "\n")
        
        with open("fix_auth_staging.sh", "w") as f:
            f.write("#!/bin/bash\n") 
            f.write("# Fix auth staging database connection\n")
            f.write(auth_cmd + "\n")
        
        print("Commands saved to:")
        print("- fix_backend_staging.sh")
        print("- fix_auth_staging.sh")
        print()
        print("Make them executable and run:")
        print("chmod +x fix_*.sh")
        print("./fix_backend_staging.sh")
        print("./fix_auth_staging.sh")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())