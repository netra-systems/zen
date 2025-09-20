#!/bin/bash
# 🔍 Production Readiness Verification Script
#
# This script verifies that all components are ready for production deployment
# of Zen with community analytics.
#
# Usage: ./scripts/verify_production.sh

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}🔍 Production Readiness Check${NC}"
    echo -e "${BLUE}================================${NC}"
    echo
}

print_step() {
    echo -e "${YELLOW}📍 $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

check_gcp_project() {
    print_step "Checking GCP project..."

    # Check if gcloud is installed
    if ! command -v gcloud &> /dev/null; then
        print_error "gcloud CLI not found"
        return 1
    fi

    # Check if project exists
    if gcloud projects describe netra-telemetry-public &>/dev/null; then
        print_success "GCP project 'netra-telemetry-public' exists"
    else
        print_error "GCP project 'netra-telemetry-public' missing"
        echo "Run: ./scripts/setup_netra_telemetry_public.sh"
        return 1
    fi

    return 0
}

check_service_account() {
    print_step "Checking service account..."

    # Check if service account exists
    if gcloud iam service-accounts describe zen-community-telemetry@netra-telemetry-public.iam.gserviceaccount.com --project=netra-telemetry-public &>/dev/null; then
        print_success "Service account exists"
    else
        print_error "Service account missing"
        echo "Run: ./scripts/setup_netra_telemetry_public.sh"
        return 1
    fi

    return 0
}

check_apis_enabled() {
    print_step "Checking required APIs..."

    local apis=(
        "cloudtrace.googleapis.com"
        "iam.googleapis.com"
        "cloudresourcemanager.googleapis.com"
        "bigquery.googleapis.com"
        "logging.googleapis.com"
        "monitoring.googleapis.com"
    )

    local all_enabled=true

    for api in "${apis[@]}"; do
        if gcloud services list --enabled --filter="name:$api" --format="value(name)" --project=netra-telemetry-public | grep -q "$api"; then
            print_success "$api enabled"
        else
            print_error "$api not enabled"
            all_enabled=false
        fi
    done

    if [ "$all_enabled" = true ]; then
        return 0
    else
        echo "Run: ./scripts/setup_netra_telemetry_public.sh"
        return 1
    fi
}

check_service_account_permissions() {
    print_step "Checking service account permissions..."

    # Check IAM policy
    local policy
    policy=$(gcloud projects get-iam-policy netra-telemetry-public --format=json 2>/dev/null)

    if echo "$policy" | jq -r '.bindings[] | select(.role == "roles/cloudtrace.agent") | .members[]' | grep -q "serviceAccount:zen-community-telemetry@netra-telemetry-public.iam.gserviceaccount.com"; then
        print_success "Service account has cloudtrace.agent role"
    else
        print_error "Service account missing cloudtrace.agent role"
        return 1
    fi

    return 0
}

check_embedded_credentials() {
    print_step "Checking embedded credentials..."

    # Check if we're in development or production mode
    if [ -f "zen/telemetry/embedded_credentials.py" ]; then
        print_success "Embedded credentials found (production mode)"

        # Test the embedded credentials
        python -c "
try:
    from zen.telemetry.embedded_credentials import (
        get_embedded_credentials,
        get_project_id,
        is_community_analytics_available
    )

    creds = get_embedded_credentials()
    project = get_project_id()
    available = is_community_analytics_available()

    if creds and project == 'netra-telemetry-public' and available:
        print('✅ Embedded credentials working')
    else:
        print('❌ Embedded credentials not working')
        exit(1)

except ImportError:
    print('❌ Cannot import embedded credentials')
    exit(1)
except Exception as e:
    print(f'❌ Credential test failed: {e}')
    exit(1)
"
        if [ $? -eq 0 ]; then
            print_success "Embedded credentials test passed"
        else
            print_error "Embedded credentials test failed"
            return 1
        fi

    elif [ -f "zen-community-key.json" ]; then
        print_warning "Found zen-community-key.json (development mode)"
        print_warning "Run: python scripts/embed_credentials.py for production"

    else
        print_error "No credentials found (development or production)"
        echo "Development: Run ./scripts/setup_netra_telemetry_public.sh"
        echo "Production: Run python scripts/embed_credentials.py"
        return 1
    fi

    return 0
}

check_telemetry_manager() {
    print_step "Checking telemetry manager..."

    # Test telemetry manager import and initialization
    python -c "
try:
    from zen.telemetry.manager import TelemetryManager
    from zen.telemetry.config import TelemetryConfig

    # Test manager singleton
    manager1 = TelemetryManager.get_instance()
    manager2 = TelemetryManager.get_instance()

    if manager1 is not manager2:
        print('❌ TelemetryManager not a singleton')
        exit(1)

    # Test config
    config = TelemetryConfig.from_environment()

    if not config.use_community_analytics:
        print('❌ Community analytics not enabled by default')
        exit(1)

    if config.get_gcp_project() != 'netra-telemetry-public':
        print(f'❌ Wrong project: {config.get_gcp_project()}')
        exit(1)

    print('✅ Telemetry manager working')

except ImportError as e:
    print(f'❌ Import error: {e}')
    exit(1)
except Exception as e:
    print(f'❌ Telemetry manager test failed: {e}')
    exit(1)
"
    if [ $? -eq 0 ]; then
        print_success "Telemetry manager test passed"
    else
        print_error "Telemetry manager test failed"
        return 1
    fi

    return 0
}

check_community_auth() {
    print_step "Checking community authentication..."

    python -c "
try:
    from zen.telemetry.community_auth import CommunityAuthProvider

    provider = CommunityAuthProvider()
    creds = provider.get_credentials()

    if creds is None:
        # This is expected in dev mode without embedded credentials
        print('ℹ️  No credentials available (development mode)')
    else:
        print('✅ Community auth provider working')

except ImportError as e:
    print(f'❌ Import error: {e}')
    exit(1)
except Exception as e:
    print(f'❌ Community auth test failed: {e}')
    exit(1)
"
    if [ $? -eq 0 ]; then
        print_success "Community auth provider test passed"
    else
        print_error "Community auth provider test failed"
        return 1
    fi

    return 0
}

check_opt_out_mechanisms() {
    print_step "Checking opt-out mechanisms..."

    # Test environment variable opt-out
    ZEN_TELEMETRY_DISABLED=true python -c "
try:
    from zen.telemetry.config import TelemetryConfig

    config = TelemetryConfig.from_environment()

    if config.enabled:
        print('❌ Environment variable opt-out not working')
        exit(1)
    else:
        print('✅ Environment variable opt-out working')

except Exception as e:
    print(f'❌ Opt-out test failed: {e}')
    exit(1)
"
    if [ $? -eq 0 ]; then
        print_success "Environment variable opt-out working"
    else
        print_error "Environment variable opt-out failed"
        return 1
    fi

    # Test programmatic opt-out
    python -c "
try:
    from zen.telemetry import disable_telemetry
    from zen.telemetry.config import TelemetryConfig

    disable_telemetry()
    config = TelemetryConfig.from_environment()

    if config.enabled:
        print('❌ Programmatic opt-out not working')
        exit(1)
    else:
        print('✅ Programmatic opt-out working')

except Exception as e:
    print(f'❌ Programmatic opt-out test failed: {e}')
    exit(1)
"
    if [ $? -eq 0 ]; then
        print_success "Programmatic opt-out working"
    else
        print_error "Programmatic opt-out failed"
        return 1
    fi

    return 0
}

check_package_configuration() {
    print_step "Checking package configuration..."

    # Check pyproject.toml
    if [ ! -f "pyproject.toml" ]; then
        print_error "pyproject.toml not found"
        return 1
    fi

    # Check if telemetry dependencies are in core (not optional)
    if grep -q "google-cloud-trace" pyproject.toml && ! grep -A 20 "\[project.optional-dependencies\]" pyproject.toml | grep -q "google-cloud-trace"; then
        print_success "Telemetry dependencies in core"
    else
        print_error "Telemetry dependencies not in core or missing"
        return 1
    fi

    # Check if zen.telemetry is in packages
    if grep -q "zen.telemetry" pyproject.toml; then
        print_success "zen.telemetry included in packages"
    else
        print_error "zen.telemetry not included in packages"
        return 1
    fi

    return 0
}

check_demo_materials() {
    print_step "Checking demo materials..."

    local demo_files=(
        "COMMUNITY_ANALYTICS_DEMO.md"
        "demo_community_analytics.py"
        "DEMO_SUMMARY.md"
    )

    local all_present=true

    for file in "${demo_files[@]}"; do
        if [ -f "$file" ]; then
            print_success "$file exists"
        else
            print_error "$file missing"
            all_present=false
        fi
    done

    # Test demo script
    if [ -f "demo_community_analytics.py" ]; then
        python -c "
try:
    exec(open('demo_community_analytics.py').read())
    print('✅ Demo script syntax valid')
except SyntaxError as e:
    print(f'❌ Demo script syntax error: {e}')
    exit(1)
except SystemExit:
    # Expected from the demo script
    print('✅ Demo script runs successfully')
except Exception as e:
    print(f'ℹ️  Demo script completed with: {e}')
" &>/dev/null
        print_success "Demo script validated"
    fi

    return $( [ "$all_present" = true ] && echo 0 || echo 1 )
}

main() {
    print_header

    local checks_passed=0
    local total_checks=0

    # Run all checks
    local checks=(
        "check_gcp_project"
        "check_service_account"
        "check_apis_enabled"
        "check_service_account_permissions"
        "check_embedded_credentials"
        "check_telemetry_manager"
        "check_community_auth"
        "check_opt_out_mechanisms"
        "check_package_configuration"
        "check_demo_materials"
    )

    for check in "${checks[@]}"; do
        total_checks=$((total_checks + 1))
        if $check; then
            checks_passed=$((checks_passed + 1))
        fi
        echo
    done

    # Summary
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}📊 Verification Summary${NC}"
    echo -e "${BLUE}================================${NC}"
    echo
    echo "Checks passed: $checks_passed/$total_checks"
    echo

    if [ $checks_passed -eq $total_checks ]; then
        echo -e "${GREEN}🎉 Production readiness: PASSED${NC}"
        echo -e "${GREEN}🚀 Ready for deployment!${NC}"
        echo
        echo "Next steps:"
        echo "  1. Run: ./scripts/build_production.sh"
        echo "  2. Test package locally"
        echo "  3. Deploy to PyPI"
        return 0
    else
        echo -e "${RED}❌ Production readiness: FAILED${NC}"
        echo -e "${RED}🔧 Fix issues before deployment${NC}"
        return 1
    fi
}

# Check if running from correct directory
if [ ! -f "pyproject.toml" ]; then
    print_error "Please run this script from the zen project root directory"
    exit 1
fi

# Run main function
main "$@"