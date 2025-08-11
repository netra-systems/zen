#!/usr/bin/env python
"""
Generate OpenAPI/Swagger specification from FastAPI app and sync to ReadMe.

This script:
1. Loads the FastAPI application
2. Extracts the OpenAPI specification
3. Saves it to a JSON file
4. Optionally syncs it to ReadMe documentation platform

Usage:
    python generate_openapi_spec.py [--sync-readme] [--readme-api-key KEY] [--readme-version VERSION]
"""

import json
import sys
import os
import argparse
import requests
from typing import Optional
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Disable LLM calls during spec generation
os.environ["DEV_MODE_DISABLE_LLM"] = "true"
os.environ["SKIP_STARTUP_CHECKS"] = "true"

def get_openapi_spec():
    """Extract OpenAPI specification from FastAPI app."""
    try:
        # Import the FastAPI app
        from app.main import app
        
        # Get the OpenAPI schema
        openapi_schema = app.openapi()
        
        # Add additional metadata if needed
        openapi_schema["info"]["title"] = "Netra AI Optimization Platform API"
        openapi_schema["info"]["description"] = (
            "Enterprise-grade system for optimizing AI workloads. "
            "This API provides endpoints for agent orchestration, workflow management, "
            "and AI optimization tools."
        )
        openapi_schema["info"]["version"] = os.getenv("API_VERSION", "1.0.0")
        openapi_schema["info"]["contact"] = {
            "name": "Netra Support",
            "email": "support@netra.ai",
            "url": "https://netra.ai/support"
        }
        openapi_schema["info"]["license"] = {
            "name": "Proprietary",
            "url": "https://netra.ai/license"
        }
        
        # Add servers
        openapi_schema["servers"] = [
            {
                "url": "http://localhost:8000",
                "description": "Local development server"
            },
            {
                "url": "https://api.netra.ai",
                "description": "Production server"
            },
            {
                "url": "https://staging-api.netra.ai",
                "description": "Staging server"
            }
        ]
        
        # Add security schemes if not already present
        if "components" not in openapi_schema:
            openapi_schema["components"] = {}
        
        if "securitySchemes" not in openapi_schema["components"]:
            openapi_schema["components"]["securitySchemes"] = {
                "bearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT",
                    "description": "JWT authentication token"
                },
                "apiKey": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "X-API-Key",
                    "description": "API key for service-to-service authentication"
                }
            }
        
        # Add global security requirement
        if "security" not in openapi_schema:
            openapi_schema["security"] = [
                {"bearerAuth": []},
                {"apiKey": []}
            ]
        
        return openapi_schema
        
    except Exception as e:
        print(f"Error generating OpenAPI spec: {e}")
        sys.exit(1)


def save_spec_to_file(spec: dict, output_path: str = "openapi.json") -> str:
    """Save OpenAPI specification to a JSON file."""
    try:
        output_file = Path(output_path)
        
        # Create directory if it doesn't exist
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Save the spec
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(spec, f, indent=2, ensure_ascii=False)
        
        print(f"OpenAPI spec saved to: {output_file.absolute()}")
        return str(output_file.absolute())
        
    except Exception as e:
        print(f"Error saving OpenAPI spec: {e}")
        sys.exit(1)


def sync_to_readme(
    spec_file: str,
    api_key: str,
    version: str = "v1.0",
    readme_url: Optional[str] = None
) -> bool:
    """
    Sync OpenAPI specification to ReadMe documentation platform.
    
    Args:
        spec_file: Path to the OpenAPI JSON file
        api_key: ReadMe API key
        version: API version for ReadMe (e.g., "v1.0")
        readme_url: Custom ReadMe API URL (optional)
    
    Returns:
        True if sync was successful, False otherwise
    """
    try:
        # Default ReadMe API URL
        if not readme_url:
            readme_url = "https://dash.readme.com/api/v1"
        
        # Read the spec file
        with open(spec_file, 'r', encoding='utf-8') as f:
            spec_content = f.read()
        
        # Prepare the API request
        headers = {
            "Authorization": f"Basic {api_key}",
            "x-readme-version": version,
            "Content-Type": "application/json"
        }
        
        # First, check if the version exists
        version_check_url = f"{readme_url}/version/{version}"
        version_response = requests.get(version_check_url, headers=headers)
        
        if version_response.status_code == 404:
            # Create the version if it doesn't exist
            print(f"Creating new version '{version}' in ReadMe...")
            create_version_url = f"{readme_url}/version"
            version_data = {
                "version": version,
                "from": "1.0.0",  # Base version to fork from
                "is_stable": False,
                "is_beta": True
            }
            create_response = requests.post(
                create_version_url,
                headers=headers,
                json=version_data
            )
            
            if create_response.status_code not in [200, 201]:
                print(f"Warning: Could not create version: {create_response.text}")
        
        # Upload the OpenAPI spec
        print(f"Uploading OpenAPI spec to ReadMe (version: {version})...")
        
        # ReadMe expects the spec to be uploaded as a file
        files = {
            'spec': ('openapi.json', spec_content, 'application/json')
        }
        
        upload_url = f"{readme_url}/api-specification"
        upload_response = requests.post(
            upload_url,
            headers={
                "Authorization": f"Basic {api_key}",
                "x-readme-version": version
            },
            files=files
        )
        
        if upload_response.status_code in [200, 201]:
            print(f"Successfully synced OpenAPI spec to ReadMe!")
            response_data = upload_response.json()
            if "id" in response_data:
                print(f"   Specification ID: {response_data['id']}")
            return True
        else:
            print(f"Failed to sync to ReadMe: {upload_response.status_code}")
            print(f"   Response: {upload_response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"Network error while syncing to ReadMe: {e}")
        return False
    except Exception as e:
        print(f"Error syncing to ReadMe: {e}")
        return False


def validate_spec(spec: dict) -> bool:
    """Validate the OpenAPI specification."""
    required_fields = ["openapi", "info", "paths"]
    
    for field in required_fields:
        if field not in spec:
            print(f"Invalid spec: missing required field '{field}'")
            return False
    
    if not spec["paths"]:
        print("Warning: No API paths found in specification")
    
    print(f"OpenAPI spec validation passed")
    print(f"   Version: {spec.get('openapi', 'unknown')}")
    print(f"   Title: {spec.get('info', {}).get('title', 'unknown')}")
    print(f"   Paths: {len(spec.get('paths', {}))}")
    
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Generate OpenAPI spec from FastAPI app and optionally sync to ReadMe"
    )
    parser.add_argument(
        "--output",
        "-o",
        default="openapi.json",
        help="Output file path for the OpenAPI spec (default: openapi.json)"
    )
    parser.add_argument(
        "--sync-readme",
        action="store_true",
        help="Sync the generated spec to ReadMe documentation platform"
    )
    parser.add_argument(
        "--readme-api-key",
        help="ReadMe API key (can also be set via README_API_KEY env var)"
    )
    parser.add_argument(
        "--readme-version",
        default="v1.0",
        help="API version for ReadMe (default: v1.0)"
    )
    parser.add_argument(
        "--readme-url",
        help="Custom ReadMe API URL (optional)"
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate the spec without saving or syncing"
    )
    
    args = parser.parse_args()
    
    # Generate the OpenAPI spec
    print("Generating OpenAPI specification from FastAPI app...")
    spec = get_openapi_spec()
    
    # Validate the spec
    if not validate_spec(spec):
        sys.exit(1)
    
    if args.validate_only:
        print("Validation complete (--validate-only flag set)")
        sys.exit(0)
    
    # Save to file
    spec_file = save_spec_to_file(spec, args.output)
    
    # Sync to ReadMe if requested
    if args.sync_readme:
        # Get API key from args or environment
        api_key = args.readme_api_key or os.getenv("README_API_KEY")
        
        if not api_key:
            print("Error: ReadMe API key is required for syncing")
            print("   Provide it via --readme-api-key or set README_API_KEY environment variable")
            sys.exit(1)
        
        success = sync_to_readme(
            spec_file,
            api_key,
            args.readme_version,
            args.readme_url
        )
        
        if not success:
            sys.exit(1)
    
    print("\nDone!")


if __name__ == "__main__":
    main()