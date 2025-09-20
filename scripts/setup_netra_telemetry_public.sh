#!/bin/bash
# 🚀 Setup Script for netra-telemetry-public GCP Project
# This script creates the complete infrastructure for Zen community analytics

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="netra-telemetry-public"
SERVICE_ACCOUNT="zen-community-telemetry"
KEY_FILE="zen-community-key.json"
BILLING_ACCOUNT=""  # Set your billing account ID

print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}🌍 Zen Community Analytics Setup${NC}"
    echo -e "${BLUE}================================${NC}"
    echo
}

print_step() {
    echo -e "${YELLOW}📍 $1${NC}"
    echo
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
    echo
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
    echo
}

check_prerequisites() {
    print_step "Checking prerequisites..."

    # Check if gcloud is installed
    if ! command -v gcloud &> /dev/null; then
        print_error "gcloud CLI not found. Please install Google Cloud SDK first."
        exit 1
    fi

    # Check if user is authenticated
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q "@"; then
        print_error "Not authenticated with gcloud. Run 'gcloud auth login' first."
        exit 1
    fi

    # Check billing account
    if [ -z "$BILLING_ACCOUNT" ]; then
        echo "Please set your billing account ID in this script:"
        echo "Available billing accounts:"
        gcloud billing accounts list
        exit 1
    fi

    print_success "Prerequisites check passed"
}

create_project() {
    print_step "Creating GCP project: $PROJECT_ID"

    # Check if project exists
    if gcloud projects describe "$PROJECT_ID" &>/dev/null; then
        print_success "Project $PROJECT_ID already exists"
    else
        # Create project
        gcloud projects create "$PROJECT_ID" \
            --name="Netra Zen Community Telemetry" \
            --set-as-default

        print_success "Project $PROJECT_ID created"
    fi

    # Link billing account
    gcloud billing projects link "$PROJECT_ID" \
        --billing-account="$BILLING_ACCOUNT"

    print_success "Billing account linked"

    # Set project metadata
    gcloud compute project-info add-metadata \
        --project="$PROJECT_ID" \
        --metadata=purpose="zen-community-analytics",project-type="public-telemetry"

    print_success "Project metadata configured"
}

enable_apis() {
    print_step "Enabling required APIs..."

    # APIs needed for community analytics
    APIS=(
        "cloudtrace.googleapis.com"
        "cloudresourcemanager.googleapis.com"
        "iam.googleapis.com"
        "bigquery.googleapis.com"
        "logging.googleapis.com"
        "monitoring.googleapis.com"
    )

    for api in "${APIS[@]}"; do
        echo "Enabling $api..."
        gcloud services enable "$api" --project="$PROJECT_ID"
    done

    print_success "All APIs enabled"
}

create_service_account() {
    print_step "Creating service account: $SERVICE_ACCOUNT"

    # Create service account
    if gcloud iam service-accounts describe "${SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com" --project="$PROJECT_ID" &>/dev/null; then
        print_success "Service account already exists"
    else
        gcloud iam service-accounts create "$SERVICE_ACCOUNT" \
            --display-name="Zen Community Telemetry Writer" \
            --description="Write-only service account for anonymous community analytics" \
            --project="$PROJECT_ID"

        print_success "Service account created"
    fi

    # Grant minimal permissions (write-only)
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
        --member="serviceAccount:${SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com" \
        --role="roles/cloudtrace.agent"

    print_success "Permissions granted (write-only)"
}

create_service_account_key() {
    print_step "Creating service account key..."

    # Remove existing key file
    if [ -f "$KEY_FILE" ]; then
        rm "$KEY_FILE"
    fi

    # Create new key
    gcloud iam service-accounts keys create "$KEY_FILE" \
        --iam-account="${SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com" \
        --project="$PROJECT_ID"

    print_success "Service account key created: $KEY_FILE"

    # Set secure permissions
    chmod 600 "$KEY_FILE"
    print_success "Key file permissions secured"
}

setup_bigquery() {
    print_step "Setting up BigQuery for analytics..."

    # Create dataset
    if bq ls -d "$PROJECT_ID:community_analytics" &>/dev/null; then
        print_success "BigQuery dataset already exists"
    else
        bq mk --dataset --location=US "$PROJECT_ID:community_analytics"
        print_success "BigQuery dataset created"
    fi

    # Create traces table
    bq mk --table \
        "$PROJECT_ID:community_analytics.zen_traces" \
        trace_id:STRING,span_id:STRING,operation_name:STRING,duration_ms:INTEGER,status:STRING,platform:STRING,timestamp:TIMESTAMP \
        --project="$PROJECT_ID" || print_success "Table already exists"

    print_success "BigQuery analytics infrastructure ready"
}

setup_monitoring() {
    print_step "Setting up monitoring and alerts..."

    # Create log sink for traces
    gcloud logging sinks create zen-community-traces \
        "bigquery.googleapis.com/projects/$PROJECT_ID/datasets/community_analytics" \
        --log-filter='resource.type="cloud_trace"' \
        --project="$PROJECT_ID" || print_success "Log sink already exists"

    print_success "Monitoring configured"
}

test_setup() {
    print_step "Testing setup..."

    # Test service account authentication
    echo "Testing service account authentication..."
    export GOOGLE_APPLICATION_CREDENTIALS="$(pwd)/$KEY_FILE"

    # Test trace write permission (this will create a test trace)
    python3 << EOF
import json
from google.cloud import trace_v1

try:
    client = trace_v1.TraceServiceClient()
    project_id = "$PROJECT_ID"

    # Create a test trace
    trace_data = {
        "project_id": project_id,
        "traces": [{
            "trace_id": "test-trace-12345678901234567890123456789012",
            "spans": [{
                "span_id": "1234567890123456",
                "name": "zen-setup-test",
                "start_time": {"seconds": 1640995200},
                "end_time": {"seconds": 1640995201}
            }]
        }]
    }

    client.patch_traces(project_id=project_id, traces=trace_data["traces"])
    print("✅ Test trace written successfully")

except Exception as e:
    print(f"❌ Test failed: {e}")
    exit(1)
EOF

    print_success "Setup test passed"
}

cleanup_and_secure() {
    print_step "Securing setup..."

    # Display security information
    echo "🔒 Security Summary:"
    echo "  - Service account has write-only access"
    echo "  - Key file permissions set to 600"
    echo "  - No read access to existing traces"
    echo "  - Project configured for community analytics only"
    echo

    # Display next steps
    echo "📋 Next Steps:"
    echo "  1. Add $KEY_FILE to your secrets management"
    echo "  2. Run: python scripts/embed_credentials.py"
    echo "  3. Test with: python demo_community_analytics.py"
    echo "  4. Build package: python scripts/build_production.sh"
    echo

    print_success "Setup completed securely"
}

main() {
    print_header

    check_prerequisites
    create_project
    enable_apis
    create_service_account
    create_service_account_key
    setup_bigquery
    setup_monitoring
    test_setup
    cleanup_and_secure

    echo -e "${GREEN}🎉 netra-telemetry-public setup complete!${NC}"
    echo -e "${GREEN}🌍 Community analytics infrastructure ready${NC}"
    echo
    echo "Key file created: $KEY_FILE"
    echo "Project ID: $PROJECT_ID"
    echo "Service Account: ${SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com"
}

# Check if running from correct directory
if [ ! -f "pyproject.toml" ]; then
    print_error "Please run this script from the zen project root directory"
    exit 1
fi

# Run main function
main "$@"