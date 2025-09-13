#!/usr/bin/env python3
"""
Secret Validation CLI Tool - Issue #683 Secret Injection Bridge

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Prevent deployment failures due to missing or invalid secrets
- Value Impact: Protects $500K+ ARR staging validation pipeline
- Strategic Impact: Enables reliable automated deployments with secret validation

This CLI tool validates that all required secrets exist in Google Secret Manager
before deployment, preventing secret-related deployment failures.

Usage:
    python scripts/validate_secrets_gsm.py --service backend --environment staging
    python scripts/validate_secrets_gsm.py --all-services --project netra-staging
    python scripts/validate_secrets_gsm.py --check-critical-only --service auth
"""

import argparse
import sys
import json
from pathlib import Path
from typing import Dict, List, Any

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from deployment.secrets_config import SecretConfig, validate_deployment_secrets
from shared.windows_encoding import setup_windows_encoding

# Fix Unicode encoding issues on Windows
setup_windows_encoding()


def validate_single_service(service_name: str, project_id: str, verbose: bool = False) -> Dict[str, Any]:
    """Validate secrets for a single service.

    Args:
        service_name: Name of the service to validate
        project_id: GCP project ID
        verbose: Whether to show detailed output

    Returns:
        Validation results dictionary
    """
    print(f"\n{'='*60}")
    print(f"Validating secrets for {service_name.upper()} service")
    print(f"Project: {project_id}")
    print(f"{'='*60}")

    # Use the enhanced SecretConfig validation
    result = SecretConfig.validate_deployment_readiness(service_name, project_id)

    # Display results
    if result["deployment_ready"]:
        print(f" ✅ SUCCESS: {service_name} is ready for deployment")
        print(f"    GSM accessible: {result['gsm_accessible']}")
        print(f"    All secrets valid: {result['valid']}")
    else:
        print(f" ❌ FAILURE: {service_name} is NOT ready for deployment")

        if not result["gsm_accessible"]:
            print(f"    ❌ GSM access failed")

        if result["missing_secrets"]:
            print(f"    ❌ Missing secrets ({len(result['missing_secrets'])}):")
            for secret in result["missing_secrets"]:
                print(f"      - {secret}")

        if result["invalid_secrets"]:
            print(f"    ❌ Invalid secrets ({len(result['invalid_secrets'])}):")
            for secret in result["invalid_secrets"]:
                print(f"      - {secret}")

        if result["validation_errors"]:
            print(f"    ❌ Validation errors ({len(result['validation_errors'])}):")
            for error in result["validation_errors"]:
                print(f"      - {error}")

    if verbose:
        print(f"\n📊 Detailed Information:")
        all_secrets = SecretConfig.get_all_service_secrets(service_name)
        critical_secrets = SecretConfig.CRITICAL_SECRETS.get(service_name, [])

        print(f"    Total secrets required: {len(all_secrets)}")
        print(f"    Critical secrets: {len(critical_secrets)}")
        print(f"    Secrets string length: {len(SecretConfig.generate_deployment_command_fragment(service_name))}")

    print(f"{'='*60}")
    return result


def validate_all_services(project_id: str, verbose: bool = False) -> Dict[str, Dict[str, Any]]:
    """Validate secrets for all services.

    Args:
        project_id: GCP project ID
        verbose: Whether to show detailed output

    Returns:
        Dictionary of validation results for each service
    """
    services = ["backend", "auth"]
    results = {}

    print(f"\n🔍 Validating secrets for ALL services")
    print(f"Project: {project_id}")
    print(f"Services: {', '.join(services)}")

    for service_name in services:
        results[service_name] = validate_single_service(service_name, project_id, verbose)

    # Summary
    print(f"\n📋 VALIDATION SUMMARY")
    print(f"{'='*60}")

    total_services = len(services)
    ready_services = sum(1 for result in results.values() if result["deployment_ready"])

    print(f"Services validated: {total_services}")
    print(f"Deployment ready: {ready_services}")
    print(f"Success rate: {(ready_services/total_services)*100:.1f}%")

    if ready_services == total_services:
        print(f" ✅ ALL SERVICES READY FOR DEPLOYMENT")
    else:
        print(f" ❌ {total_services - ready_services} SERVICES NOT READY")
        print(f"    Fix missing/invalid secrets before deployment")

    return results


def check_critical_secrets_only(service_name: str, project_id: str) -> Dict[str, Any]:
    """Check only critical secrets for a service.

    Args:
        service_name: Name of the service
        project_id: GCP project ID

    Returns:
        Validation results focusing on critical secrets only
    """
    print(f"\n🚨 Checking CRITICAL secrets for {service_name.upper()}")
    print(f"Project: {project_id}")
    print(f"{'='*60}")

    critical_secrets = SecretConfig.CRITICAL_SECRETS.get(service_name, [])

    if not critical_secrets:
        print(f" ℹ️  No critical secrets defined for {service_name}")
        return {"valid": True, "critical_secrets": [], "service_name": service_name}

    print(f"Critical secrets to validate: {len(critical_secrets)}")
    for secret in critical_secrets:
        print(f"  - {secret}: {SecretConfig.explain_secret(secret)}")

    # Run full validation but focus on critical secrets in results
    result = SecretConfig.validate_deployment_readiness(service_name, project_id)

    # Filter results to critical secrets only
    critical_missing = [s for s in result["missing_secrets"]
                       if any(crit in s for crit in critical_secrets)]
    critical_invalid = [s for s in result["invalid_secrets"]
                       if any(crit in s for crit in critical_secrets)]

    if not critical_missing and not critical_invalid:
        print(f" ✅ All critical secrets are valid and available")
    else:
        print(f" ❌ Critical secret issues found:")
        for secret in critical_missing:
            print(f"    ❌ Missing: {secret}")
        for secret in critical_invalid:
            print(f"    ❌ Invalid: {secret}")

    return {
        "valid": len(critical_missing) == 0 and len(critical_invalid) == 0,
        "critical_secrets": critical_secrets,
        "missing_critical": critical_missing,
        "invalid_critical": critical_invalid,
        "service_name": service_name
    }


def generate_deployment_fragments(project_id: str) -> None:
    """Generate deployment command fragments for all services.

    Args:
        project_id: GCP project ID
    """
    services = ["backend", "auth"]

    print(f"\n🚀 Deployment Command Fragments")
    print(f"Project: {project_id}")
    print(f"{'='*60}")

    for service_name in services:
        fragment = SecretConfig.generate_deployment_command_fragment(service_name, "staging")

        print(f"\n{service_name.upper()} Service:")
        print(f"--set-secrets {fragment}")

        # Count secrets
        secret_count = len(fragment.split(',')) if fragment else 0
        print(f"({secret_count} secrets, {len(fragment)} characters)")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Validate Google Secret Manager secrets for deployment readiness",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate backend service for staging
  python scripts/validate_secrets_gsm.py --service backend --project netra-staging

  # Validate all services
  python scripts/validate_secrets_gsm.py --all-services --project netra-staging

  # Check only critical secrets for auth service
  python scripts/validate_secrets_gsm.py --check-critical-only --service auth

  # Generate deployment command fragments
  python scripts/validate_secrets_gsm.py --generate-fragments --project netra-staging

  # Verbose output with detailed information
  python scripts/validate_secrets_gsm.py --service backend --verbose

Business Impact: Protects $500K+ ARR by preventing secret-related deployment failures
        """
    )

    parser.add_argument(
        "--service",
        choices=["backend", "auth"],
        help="Service to validate (backend or auth)"
    )

    parser.add_argument(
        "--project",
        default="netra-staging",
        help="GCP project ID (default: netra-staging)"
    )

    parser.add_argument(
        "--all-services",
        action="store_true",
        help="Validate all services"
    )

    parser.add_argument(
        "--check-critical-only",
        action="store_true",
        help="Check only critical secrets (faster validation)"
    )

    parser.add_argument(
        "--generate-fragments",
        action="store_true",
        help="Generate deployment command fragments"
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed output"
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results in JSON format"
    )

    args = parser.parse_args()

    # Validate arguments
    if not any([args.service, args.all_services, args.generate_fragments]):
        parser.error("Must specify --service, --all-services, or --generate-fragments")

    if args.service and args.all_services:
        parser.error("Cannot specify both --service and --all-services")

    if args.check_critical_only and not args.service:
        parser.error("--check-critical-only requires --service")

    try:
        # Execute requested operation
        if args.generate_fragments:
            generate_deployment_fragments(args.project)
            return 0

        elif args.all_services:
            results = validate_all_services(args.project, args.verbose)

            if args.json:
                print(json.dumps(results, indent=2))

            # Exit with error code if any service not ready
            all_ready = all(result["deployment_ready"] for result in results.values())
            return 0 if all_ready else 1

        elif args.check_critical_only:
            result = check_critical_secrets_only(args.service, args.project)

            if args.json:
                print(json.dumps(result, indent=2))

            return 0 if result["valid"] else 1

        else:  # Single service validation
            result = validate_single_service(args.service, args.project, args.verbose)

            if args.json:
                print(json.dumps(result, indent=2))

            return 0 if result["deployment_ready"] else 1

    except KeyboardInterrupt:
        print("\n❌ Validation interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ ERROR: Secret validation failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())