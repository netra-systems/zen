from shared.isolated_environment import get_env
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

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional

import requests

# Add the project root to the Python path

# Disable LLM calls during spec generation
os.environ["DEV_MODE_DISABLE_LLM"] = "true"
os.environ["SKIP_STARTUP_CHECKS"] = "true"

def get_openapi_spec():
    """Extract OpenAPI specification from FastAPI app."""
    try:
        schema = _extract_base_schema()
        schema = _add_metadata(schema)
        schema = _add_servers(schema)
        schema = _add_security_schemes(schema)
        return _add_security_requirements(schema)
    except Exception as e:
        print(f"Error generating OpenAPI spec: {e}")
        sys.exit(1)


def _extract_base_schema() -> dict:
    """Extract base OpenAPI schema from FastAPI app."""
    from netra_backend.app.main import app
    return app.openapi()


def _add_metadata(schema: dict) -> dict:
    """Add metadata to OpenAPI schema."""
    schema["info"]["title"] = "Netra AI Optimization Platform API"
    schema["info"]["description"] = (
        "Enterprise-grade system for optimizing AI workloads. "
        "This API provides endpoints for agent orchestration, workflow management, "
        "and AI optimization tools."
    )
    schema["info"]["version"] = get_env().get("API_VERSION", "1.0.0")
    return _add_contact_info(schema)


def _add_contact_info(schema: dict) -> dict:
    """Add contact and license information."""
    schema["info"]["contact"] = {
        "name": "Netra Support",
        "email": "support@netrasystems.ai",
        "url": "https://netrasystems.ai/support"
    }
    schema["info"]["license"] = {
        "name": "Proprietary",
        "url": "https://netrasystems.ai/license"
    }
    return schema


def _add_servers(schema: dict) -> dict:
    """Add server configurations to schema."""
    schema["servers"] = [
        {"url": "http://localhost:8000", "description": "Local development server"},
        {"url": "https://api.netrasystems.ai", "description": "Production server"},
        {"url": "https://staging-api.netrasystems.ai", "description": "Staging server"}
    ]
    return schema


def _add_security_schemes(schema: dict) -> dict:
    """Add security schemes to schema."""
    if "components" not in schema:
        schema["components"] = {}
    if "securitySchemes" not in schema["components"]:
        schema["components"]["securitySchemes"] = _get_security_schemes()
    return schema


def _get_security_schemes() -> dict:
    """Get security scheme definitions."""
    return {
        "bearerAuth": {
            "type": "http", "scheme": "bearer", "bearerFormat": "JWT",
            "description": "JWT authentication token"
        },
        "apiKey": {
            "type": "apiKey", "in": "header", "name": "X-API-Key",
            "description": "API key for service-to-service authentication"
        }
    }


def _add_security_requirements(schema: dict) -> dict:
    """Add global security requirements."""
    if "security" not in schema:
        schema["security"] = [{"bearerAuth": []}, {"apiKey": []}]
    return schema


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


def get_readme_url(custom_url: Optional[str]) -> str:
    """Get ReadMe API URL with default fallback"""
    return custom_url or "https://dash.readme.com/api/v1"


def read_spec_file(spec_file: str) -> str:
    """Read OpenAPI spec file content"""
    with open(spec_file, 'r', encoding='utf-8') as f:
        return f.read()


def create_readme_headers(api_key: str, version: str) -> dict:
    """Create headers for ReadMe API requests"""
    return {
        "Authorization": f"Basic {api_key}",
        "x-readme-version": version,
        "Content-Type": "application/json"
    }


def check_version_exists(readme_url: str, version: str, headers: dict) -> bool:
    """Check if version exists in ReadMe"""
    version_check_url = f"{readme_url}/version/{version}"
    response = requests.get(version_check_url, headers=headers)
    return response.status_code != 404


def create_readme_version(readme_url: str, version: str, headers: dict) -> bool:
    """Create new version in ReadMe if it doesn't exist"""
    print(f"Creating new version '{version}' in ReadMe...")
    create_version_url = f"{readme_url}/version"
    version_data = {
        "version": version,
        "from": "1.0.0",
        "is_stable": False,
        "is_beta": True
    }
    response = requests.post(create_version_url, headers=headers, json=version_data)
    if response.status_code not in [200, 201]:
        print(f"Warning: Could not create version: {response.text}")
        return False
    return True


def upload_spec_to_readme(readme_url: str, api_key: str, version: str, spec_content: str) -> bool:
    """Upload OpenAPI spec to ReadMe"""
    print(f"Uploading OpenAPI spec to ReadMe (version: {version})...")
    files = {'spec': ('openapi.json', spec_content, 'application/json')}
    upload_headers = {"Authorization": f"Basic {api_key}", "x-readme-version": version}
    upload_url = f"{readme_url}/api-specification"
    response = requests.post(upload_url, headers=upload_headers, files=files)
    
    if response.status_code in [200, 201]:
        print("Successfully synced OpenAPI spec to ReadMe!")
        response_data = response.json()
        if "id" in response_data:
            print(f"   Specification ID: {response_data['id']}")
        return True
    else:
        print(f"Failed to sync to ReadMe: {response.status_code}")
        print(f"   Response: {response.text}")
        return False


def handle_readme_sync_error(error: Exception) -> bool:
    """Handle ReadMe sync errors with appropriate messages"""
    if isinstance(error, requests.exceptions.RequestException):
        print(f"Network error while syncing to ReadMe: {error}")
    else:
        print(f"Error syncing to ReadMe: {error}")
    return False


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
        readme_url = get_readme_url(readme_url)
        spec_content = read_spec_file(spec_file)
        headers = create_readme_headers(api_key, version)
        
        if not check_version_exists(readme_url, version, headers):
            create_readme_version(readme_url, version, headers)
        
        return upload_spec_to_readme(readme_url, api_key, version, spec_content)
        
    except Exception as e:
        return handle_readme_sync_error(e)


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
    """Main function to generate and optionally sync OpenAPI spec."""
    args = _parse_arguments()
    spec = _generate_and_validate_spec()
    if args.validate_only:
        _handle_validate_only()
    spec_file = save_spec_to_file(spec, args.output)
    if args.sync_readme:
        _handle_readme_sync(args, spec_file)
    print("\nDone!")


def _parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate OpenAPI spec from FastAPI app and optionally sync to ReadMe"
    )
    _add_output_args(parser)
    _add_readme_args(parser)
    return parser.parse_args()


def _add_output_args(parser: argparse.ArgumentParser) -> None:
    """Add output-related arguments to parser."""
    parser.add_argument(
        "--output", "-o", default="openapi.json",
        help="Output file path for the OpenAPI spec (default: openapi.json)"
    )
    parser.add_argument(
        "--validate-only", action="store_true",
        help="Only validate the spec without saving or syncing"
    )


def _add_readme_args(parser: argparse.ArgumentParser) -> None:
    """Add ReadMe-related arguments to parser."""
    parser.add_argument(
        "--sync-readme", action="store_true",
        help="Sync the generated spec to ReadMe documentation platform"
    )
    parser.add_argument(
        "--readme-api-key",
        help="ReadMe API key (can also be set via README_API_KEY env var)"
    )
    parser.add_argument(
        "--readme-version", default="v1.0",
        help="API version for ReadMe (default: v1.0)"
    )
    parser.add_argument(
        "--readme-url",
        help="Custom ReadMe API URL (optional)"
    )


def _generate_and_validate_spec() -> dict:
    """Generate and validate OpenAPI specification."""
    print("Generating OpenAPI specification from FastAPI app...")
    spec = get_openapi_spec()
    if not validate_spec(spec):
        sys.exit(1)
    return spec


def _handle_validate_only() -> None:
    """Handle validate-only mode."""
    print("Validation complete (--validate-only flag set)")
    sys.exit(0)


def _handle_readme_sync(args: argparse.Namespace, spec_file: str) -> None:
    """Handle ReadMe synchronization."""
    api_key = args.readme_api_key or get_env().get("README_API_KEY")
    if not api_key:
        _handle_missing_api_key()
    success = sync_to_readme(spec_file, api_key, args.readme_version, args.readme_url)
    if not success:
        sys.exit(1)


def _handle_missing_api_key() -> None:
    """Handle missing ReadMe API key."""
    print("Error: ReadMe API key is required for syncing")
    print("   Provide it via --readme-api-key or set README_API_KEY environment variable")
    sys.exit(1)


if __name__ == "__main__":
    main()
