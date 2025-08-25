#!/usr/bin/env python3
"""
Fix the staging DATABASE_URL secret in Google Cloud.

This script generates the correct DATABASE_URL format for staging
and provides the command to update it in Google Secret Manager.
"""

import sys
from pathlib import Path
from urllib.parse import quote

# Configuration for staging
PROJECT_ID = "netra-staging"
REGION = "us-central1"
INSTANCE_NAME = "staging-shared-postgres"
DATABASE_NAME = "postgres"
USERNAME = "postgres"

# The correct password (from debug script)
# This should be replaced with the actual password from the secret manager
PASSWORD = "qNdlZRHu(Mlc#)6K8LHm-lYi[7sc}25K"


def generate_correct_database_url():
    """Generate the correct DATABASE_URL for staging Cloud SQL."""
    
    # URL-encode the password to handle special characters
    encoded_password = quote(PASSWORD, safe='')
    
    # Build the Unix socket path for Cloud SQL
    socket_path = f"/cloudsql/{PROJECT_ID}:{REGION}:{INSTANCE_NAME}"
    
    # Format: postgresql://username:password@/database?host=socket_path
    # This is the correct format for Cloud SQL Unix socket connections
    database_url = f"postgresql://{USERNAME}:{encoded_password}@/{DATABASE_NAME}?host={socket_path}"
    
    return database_url


def main():
    """Generate and display the correct DATABASE_URL."""
    
    print("\n" + "="*70)
    print("STAGING DATABASE_URL FIX")
    print("="*70)
    
    # Generate the correct URL
    database_url = generate_correct_database_url()
    
    print("\n1. CORRECT DATABASE_URL FORMAT:")
    print("-" * 40)
    print(f"postgresql://{USERNAME}:[ENCODED_PASSWORD]@/{DATABASE_NAME}?host=/cloudsql/{PROJECT_ID}:{REGION}:{INSTANCE_NAME}")
    
    print("\n2. GENERATED DATABASE_URL:")
    print("-" * 40)
    # Show first part and mask the password
    url_parts = database_url.split(':')
    if len(url_parts) >= 3:
        masked_url = f"{url_parts[0]}:{url_parts[1]}:***@{url_parts[2].split('@')[1]}"
        print(masked_url)
    
    print("\n3. KEY POINTS:")
    print("-" * 40)
    print("- Username: postgres")
    print("- Database: postgres")
    print("- Connection: Unix socket (/cloudsql/...)")
    print("- SSL: NOT needed for Unix socket connections")
    print("- Password: URL-encoded to handle special characters")
    
    print("\n4. UPDATE SECRET IN GOOGLE CLOUD:")
    print("-" * 40)
    print("Run this command to update the secret:")
    print()
    print(f"echo '{database_url}' | gcloud secrets versions add database-url-staging --data-file=- --project={PROJECT_ID}")
    
    print("\n5. VERIFY THE SECRET:")
    print("-" * 40)
    print("After updating, verify with:")
    print(f"gcloud secrets versions access latest --secret=database-url-staging --project={PROJECT_ID}")
    
    print("\n6. REDEPLOY SERVICES:")
    print("-" * 40)
    print("After updating the secret, redeploy services:")
    print(f"python scripts/deploy_to_gcp.py --project {PROJECT_ID} --build-local")
    
    print("\n7. IMPORTANT NOTES:")
    print("-" * 40)
    print("WARNING: The password shown here is from the debug script")
    print("WARNING: If this password is incorrect, get the correct one from:")
    print(f"    gcloud secrets versions access latest --secret=postgres-password-staging --project={PROJECT_ID}")
    print("WARNING: Make sure to URL-encode the password before using it in the DATABASE_URL")
    
    print("\n" + "="*70)
    print("LEARNINGS FROM PREVIOUS ISSUES:")
    print("="*70)
    print("- This issue has occurred before (see SPEC/learnings/auth_service_staging_errors_five_whys.xml)")
    print("- Root cause: DATABASE_URL secret has incorrect format or credentials")
    print("- Solution: Use Unix socket format without SSL parameters")
    print("- The deployment script expects 'database-url-staging' secret to exist")
    print()
    
    # Create a file with the URL for easy access
    output_file = Path("staging_database_url.txt")
    with open(output_file, 'w') as f:
        f.write(database_url)
    print(f"DATABASE_URL saved to: {output_file}")
    print()


if __name__ == "__main__":
    main()