from shared.isolated_environment import get_env
#!/usr/bin/env python3
"""
Deploy to GCP Staging with Service Account Authentication
This script simplifies deployment by using service account authentication by default.
"""

import os
import sys
import subprocess
import json
from pathlib import Path
import argparse
import io

# Fix Unicode encoding issues on Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def find_service_account_key():
    """Find service account key in common locations."""
    # Check environment variable first
    env_key = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if env_key and Path(env_key).exists():
        return Path(env_key)
    
    # Check common locations
    possible_locations = [
        Path.home() / ".netra" / "service-account.json",
        Path.home() / ".gcp" / "netra-deployer.json",
        Path("netra-deployer-netra-staging.json"),
        Path("service-account.json"),
        Path("gcp-key.json"),
    ]
    
    for location in possible_locations:
        if location.exists():
            return location
    
    # Check for any JSON file with "netra" in the name
    for json_file in Path(".").glob("*netra*.json"):
        # Quick check if it looks like a service account key
        try:
            with open(json_file) as f:
                data = json.load(f)
                if "type" in data and data["type"] == "service_account":
                    return json_file
        except:
            continue
    
    return None


def main():
    parser = argparse.ArgumentParser(
        description="Deploy Netra to GCP Staging with service account authentication",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Default deployment (with checks):
    python scripts/deploy_staging_with_sa.py
    
  Quick deployment (no checks):
    python scripts/deploy_staging_with_sa.py --no-checks
    
  Specify service account key:
    python scripts/deploy_staging_with_sa.py --key path/to/key.json
        """
    )
    
    parser.add_argument("--key", help="Path to service account JSON key file")
    parser.add_argument("--no-checks", action="store_true", 
                       help="Skip pre-deployment checks")
    parser.add_argument("--cloud-build", action="store_true",
                       help="Use Cloud Build instead of local build")
    parser.add_argument("--cleanup", action="store_true",
                       help="Clean up deployments")
    
    args = parser.parse_args()
    
    # Find service account key
    if args.key:
        key_path = Path(args.key)
        if not key_path.exists():
            print(f" FAIL:  Service account key not found: {key_path}")
            sys.exit(1)
    else:
        key_path = find_service_account_key()
        if not key_path:
            print(" FAIL:  No service account key found!")
            print("\n[U+1F4CB] Please provide a service account key using one of these methods:")
            print("  1. Set GOOGLE_APPLICATION_CREDENTIALS environment variable")
            print("  2. Place key file in current directory as 'service-account.json'")
            print("  3. Use --key flag to specify the path")
            print("\n[U+1F510] To create a new service account:")
            print("  python scripts/setup_gcp_service_account.py")
            sys.exit(1)
    
    print(f"[U+1F510] Using service account key: {key_path}")
    
    # Build deployment command
    command = [
        sys.executable,
        "scripts/deploy_to_gcp.py",
        "--project", "netra-staging",
        "--service-account", str(key_path)
    ]
    
    if args.cleanup:
        command.append("--cleanup")
    else:
        # Default to local build unless specified otherwise
        if not args.cloud_build:
            command.append("--build-local")
        
        # Add checks by default unless --no-checks is specified
        if not args.no_checks:
            command.append("--run-checks")
    
    print(f"\n[U+1F680] Deploying to GCP Staging...")
    print(f"   Command: {' '.join(command)}\n")
    
    # Execute deployment
    try:
        result = subprocess.run(command, check=False)
        sys.exit(result.returncode)
    except KeyboardInterrupt:
        print("\n WARNING: [U+FE0F] Deployment interrupted")
        sys.exit(1)
    except Exception as e:
        print(f" FAIL:  Deployment failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
