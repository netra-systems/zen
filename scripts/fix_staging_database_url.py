#!/usr/bin/env python3
"""
Fix the staging #removed-legacysecret in Google Cloud.

This script generates the correct #removed-legacyformat for staging
and provides the command to update it in Google Secret Manager.

**UPDATED**: Now uses DatabaseURLBuilder for centralized URL construction.
"""

import sys
import subprocess
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.database_url_builder import DatabaseURLBuilder

# Configuration for staging
PROJECT_ID = "netra-staging"
REGION = "us-central1"
INSTANCE_NAME = "staging-shared-postgres"
DATABASE_NAME = "postgres"
USERNAME = "postgres"


def fetch_password_from_secret():
    """Fetch the PostgreSQL password from Google Secret Manager."""
    try:
        cmd = [
            "gcloud", "secrets", "versions", "access", "latest",
            "--secret", "postgres-password-staging",
            "--project", PROJECT_ID
        ]
        
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            check=True
        )
        
        return result.stdout.strip()
        
    except subprocess.CalledProcessError as e:
        print(f"Failed to fetch password from secret manager: {e}")
        print("Using fallback password (may be outdated)")
        return "qNdlZRHu(Mlc#)6K8LHm-lYi[7sc}25K"


def generate_correct_database_url():
    """Generate the correct #removed-legacyfor staging Cloud SQL using DatabaseURLBuilder."""
    
    # Fetch the password from secret manager
    password = fetch_password_from_secret()
    
    # Build environment variables dict for DatabaseURLBuilder
    env_vars = {
        "ENVIRONMENT": "staging",
        "POSTGRES_HOST": f"/cloudsql/{PROJECT_ID}:{REGION}:{INSTANCE_NAME}",
        "POSTGRES_USER": USERNAME,
        "POSTGRES_PASSWORD": password,
        "POSTGRES_DB": DATABASE_NAME,
        # Don't set #removed-legacyto force builder to construct from parts
    }
    
    # Create builder
    builder = DatabaseURLBuilder(env_vars)
    
    # Validate configuration
    is_valid, error_msg = builder.validate()
    if not is_valid:
        print(f"Configuration error: {error_msg}")
        sys.exit(1)
    
    # Get URL for staging environment (sync version for the secret)
    database_url = builder.get_url_for_environment(sync=True)
    
    if not database_url:
        print("Failed to generate database URL")
        sys.exit(1)
    
    return database_url


def main():
    """Generate and display the correct DATABASE_URL."""
    
    print("\n" + "="*70)
    print("STAGING #removed-legacyFIX")
    print("="*70)
    
    # Generate the correct URL using DatabaseURLBuilder
    database_url = generate_correct_database_url()
    
    # Use DatabaseURLBuilder's masking utility
    masked_url = DatabaseURLBuilder.mask_url_for_logging(database_url)
    
    print("\n1. CORRECT #removed-legacyFORMAT:")
    print("-" * 40)
    print(f"postgresql://{USERNAME}:[ENCODED_PASSWORD]@/{DATABASE_NAME}?host=/cloudsql/{PROJECT_ID}:{REGION}:{INSTANCE_NAME}")
    
    print("\n2. GENERATED #removed-legacy(masked):")
    print("-" * 40)
    print(masked_url)
    
    print("\n3. KEY POINTS:")
    print("-" * 40)
    print("- Username: postgres")
    print("- Database: postgres")
    print("- Connection: Unix socket (/cloudsql/...)")
    print("- SSL: NOT needed for Unix socket connections")
    print("- Password: URL-encoded by DatabaseURLBuilder")
    print("- Using centralized DatabaseURLBuilder for consistency")
    
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
    print("- Root cause: #removed-legacysecret has incorrect format or credentials")
    print("- Solution: Use Unix socket format without SSL parameters")
    print("- The deployment script expects 'database-url-staging' secret to exist")
    print()
    
    # Create a file with the URL for easy access
    output_file = Path("staging_database_url.txt")
    with open(output_file, 'w') as f:
        f.write(database_url)
    print(f"#removed-legacysaved to: {output_file}")
    print()


if __name__ == "__main__":
    main()