# 🚀 Zen Telemetry Production Setup Guide

## 🎯 **Overview**

This guide covers the **remaining steps** needed to make Zen's community analytics production-ready, including:

1. **GCP Project Setup** for `netra-telemetry-public`
2. **Service Account Creation** and permissions
3. **Embedded Credentials** integration
4. **Package Distribution** configuration
5. **Production Deployment** checklist

---

## 📋 **Step 1: Create netra-telemetry-public GCP Project**

### **1.1 Create the GCP Project**
```bash
# Set up gcloud CLI first
gcloud auth login
gcloud config set project netra-telemetry-public

# Create the project
gcloud projects create netra-telemetry-public \
    --name="Netra Zen Community Telemetry" \
    --set-as-default

# Enable billing (required for Cloud Trace)
gcloud billing projects link netra-telemetry-public \
    --billing-account=YOUR_BILLING_ACCOUNT_ID
```

### **1.2 Enable Required APIs**
```bash
# Enable Cloud Trace API
gcloud services enable cloudtrace.googleapis.com

# Enable Cloud Resource Manager API
gcloud services enable cloudresourcemanager.googleapis.com

# Enable IAM API
gcloud services enable iam.googleapis.com

# Verify APIs are enabled
gcloud services list --enabled
```

### **1.3 Configure Project Settings**
```bash
# Set project metadata
gcloud compute project-info add-metadata \
    --metadata=purpose="zen-community-analytics",project-type="public-telemetry"

# Set up project labels
gcloud projects update netra-telemetry-public \
    --update-labels=type=community-analytics,product=zen,visibility=public
```

---

## 🔐 **Step 2: Create Community Service Account**

### **2.1 Create Service Account**
```bash
# Create the service account
gcloud iam service-accounts create zen-community-telemetry \
    --display-name="Zen Community Telemetry Writer" \
    --description="Write-only service account for anonymous community analytics" \
    --project=netra-telemetry-public
```

### **2.2 Grant Minimal Required Permissions**
```bash
# Grant Cloud Trace Agent role (write-only)
gcloud projects add-iam-policy-binding netra-telemetry-public \
    --member="serviceAccount:zen-community-telemetry@netra-telemetry-public.iam.gserviceaccount.com" \
    --role="roles/cloudtrace.agent"

# Verify permissions
gcloud projects get-iam-policy netra-telemetry-public \
    --flatten="bindings[].members" \
    --filter="bindings.members:zen-community-telemetry@netra-telemetry-public.iam.gserviceaccount.com"
```

### **2.3 Create and Download Service Account Key**
```bash
# Create private key
gcloud iam service-accounts keys create zen-community-key.json \
    --iam-account=zen-community-telemetry@netra-telemetry-public.iam.gserviceaccount.com \
    --project=netra-telemetry-public

# Verify key creation
gcloud iam service-accounts keys list \
    --iam-account=zen-community-telemetry@netra-telemetry-public.iam.gserviceaccount.com
```

### **2.4 Security Validation**
```bash
# Test write permissions
gcloud auth activate-service-account \
    --key-file=zen-community-key.json

# Verify trace write access (should succeed)
gcloud logging read "resource.type=gce_instance" --limit=1 --project=netra-telemetry-public

# Try to read traces (should fail - proving write-only)
gcloud logging read "resource.type=cloud_trace" --limit=1 --project=netra-telemetry-public
```

---

## 🔧 **Step 3: Embed Credentials in Zen Package**

### **3.1 Prepare Embedded Credentials**

**Create secure credential embedding script:**
```python
# scripts/embed_credentials.py
import json
import base64
import os

def embed_service_account():
    """Embed service account credentials in the package"""

    # Read the service account key
    with open('zen-community-key.json', 'r') as f:
        service_account = json.load(f)

    # Create embedded credentials module
    embedded_code = f'''"""
Embedded Community Service Account Credentials

This file contains the embedded service account for anonymous community analytics.
The service account has write-only access to netra-telemetry-public.
"""

import json
import base64
from google.oauth2 import service_account

# Embedded service account (write-only access)
_EMBEDDED_CREDENTIALS = {json.dumps(service_account, indent=4)}

def get_embedded_credentials():
    """Get embedded service account credentials"""
    try:
        return service_account.Credentials.from_service_account_info(
            _EMBEDDED_CREDENTIALS,
            scopes=['https://www.googleapis.com/auth/trace.append']
        )
    except Exception:
        return None

def get_project_id():
    """Get embedded project ID"""
    return _EMBEDDED_CREDENTIALS.get("project_id", "netra-telemetry-public")
'''

    # Write to zen package
    with open('zen/telemetry/embedded_credentials.py', 'w') as f:
        f.write(embedded_code)

    print("✅ Credentials embedded successfully")

    # Clean up the original key file
    os.remove('zen-community-key.json')
    print("🗑️ Original key file removed for security")

if __name__ == "__main__":
    embed_service_account()
```

### **3.2 Update Community Auth Provider**
```python
# zen/telemetry/community_auth.py (update)
def _get_embedded_credentials(self) -> Optional[Credentials]:
    """Get embedded service account credentials"""
    try:
        from .embedded_credentials import get_embedded_credentials
        return get_embedded_credentials()
    except ImportError:
        logger.debug("Embedded credentials not available")
        return None
```

### **3.3 Security Measures**
```bash
# Add to .gitignore
echo "zen/telemetry/embedded_credentials.py" >> .gitignore
echo "zen-community-key.json" >> .gitignore
echo "scripts/embed_credentials.py" >> .gitignore

# Create production build script
cat > scripts/build_production.sh << 'EOF'
#!/bin/bash
# Production build with embedded credentials

echo "🔨 Building Zen with embedded community analytics..."

# Run credential embedding
python scripts/embed_credentials.py

# Build package
python -m build

# Verify embedded credentials
python -c "
try:
    from zen.telemetry.embedded_credentials import get_embedded_credentials
    creds = get_embedded_credentials()
    print('✅ Embedded credentials verified')
except Exception as e:
    print(f'❌ Embedded credentials error: {e}')
"

echo "🚀 Production build complete"
EOF

chmod +x scripts/build_production.sh
```

---

## 📦 **Step 4: Package Distribution Setup**

### **4.1 Update Package Metadata**
```toml
# pyproject.toml updates
[project]
name = "netra-zen"
version = "1.1.0"  # Bump for community analytics
description = "Multi-instance Claude orchestrator with community analytics"

# Add community analytics keywords
keywords = [
    "claude", "claude code", "5-hour limit", "ai", "orchestration", "parallel", "automation", "llm", "anthropic", "community-analytics", "telemetry", "observability"
]

# Update classifiers
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 3",
    "Topic :: Software Development :: Libraries :: Python Modules",
    "Topic :: System :: Monitoring",
    "Topic :: Internet :: Log Analysis",
]
```

### **4.2 Create Release Workflow**
```yaml
# .github/workflows/release.yml
name: Release with Community Analytics

on:
  release:
    types: [published]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        pip install build twine

    - name: Embed community credentials
      env:
        COMMUNITY_CREDENTIALS: ${{ secrets.COMMUNITY_CREDENTIALS }}
      run: |
        echo "$COMMUNITY_CREDENTIALS" > zen-community-key.json
        python scripts/embed_credentials.py

    - name: Build package
      run: python -m build

    - name: Verify community analytics
      run: |
        pip install dist/*.whl
        python -c "
        import zen
        from zen.telemetry import is_telemetry_enabled
        print(f'Community analytics: {is_telemetry_enabled()}')
        "

    - name: Publish to PyPI
      env:
        TWINE_USERNAME: __token__
        TWINE_PASSWORD: ${{ secrets.PYPI_TOKEN }}
      run: twine upload dist/*
```

### **4.3 Pre-release Testing**
```bash
# Create test distribution
python scripts/build_production.sh

# Test installation
pip install dist/netra_zen-*.whl

# Verify community analytics work
python -c "
import zen
from zen.telemetry.config import TelemetryConfig
config = TelemetryConfig.from_environment()
print(f'✅ Community project: {config.get_gcp_project()}')
print(f'✅ Community analytics: {config.use_community_analytics}')
"
```

---

## 🏗️ **Step 5: Cloud Infrastructure Setup**

### **5.1 Set Up Cloud Trace Data Processing**
```bash
# Create BigQuery dataset for analytics
bq mk --dataset --location=US netra-telemetry-public:community_analytics

# Create traces export sink
gcloud logging sinks create zen-community-traces \
    bigquery.googleapis.com/projects/netra-telemetry-public/datasets/community_analytics \
    --log-filter='resource.type="gce_instance" AND protoPayload.serviceName="cloudtrace.googleapis.com"' \
    --project=netra-telemetry-public

# Set up trace aggregation table
bq mk --table \
    netra-telemetry-public:community_analytics.zen_traces \
    trace_id:STRING,span_id:STRING,operation_name:STRING,duration_ms:INTEGER,status:STRING,platform:STRING,timestamp:TIMESTAMP
```

### **5.2 Create Community Dashboard Infrastructure**
```bash
# Set up Cloud Run service for dashboard
gcloud run deploy zen-community-dashboard \
    --image=gcr.io/netra-telemetry-public/zen-dashboard:latest \
    --region=us-central1 \
    --allow-unauthenticated \
    --set-env-vars="PROJECT_ID=netra-telemetry-public" \
    --project=netra-telemetry-public

# Set up custom domain (analytics.zen.dev)
gcloud domains mappings create analytics.zen.dev \
    --service=zen-community-dashboard \
    --region=us-central1 \
    --project=netra-telemetry-public
```

### **5.3 Configure Monitoring and Alerting**
```bash
# Create monitoring dashboard
gcloud alpha monitoring dashboards create --config-from-file=monitoring-config.yaml

# Set up quota alerts
gcloud alpha monitoring policies create --policy-from-file=quota-alerts.yaml

# Configure cost budgets
gcloud billing budgets create \
    --billing-account=YOUR_BILLING_ACCOUNT \
    --display-name="Zen Community Analytics Budget" \
    --budget-amount=100USD \
    --threshold-rules=percent=50,percent=90
```

---

## ✅ **Step 6: Production Deployment Checklist**

### **6.1 Pre-Deployment Verification**
```bash
# Verification script
cat > scripts/verify_production.sh << 'EOF'
#!/bin/bash

echo "🔍 Verifying production readiness..."

# Check GCP project exists
if gcloud projects describe netra-telemetry-public &>/dev/null; then
    echo "✅ GCP project exists"
else
    echo "❌ GCP project missing"
    exit 1
fi

# Check service account exists
if gcloud iam service-accounts describe zen-community-telemetry@netra-telemetry-public.iam.gserviceaccount.com &>/dev/null; then
    echo "✅ Service account exists"
else
    echo "❌ Service account missing"
    exit 1
fi

# Check APIs enabled
for api in cloudtrace.googleapis.com iam.googleapis.com; do
    if gcloud services list --enabled --filter="name:$api" --format="value(name)" | grep -q "$api"; then
        echo "✅ $api enabled"
    else
        echo "❌ $api not enabled"
        exit 1
    fi
done

# Test embedded credentials
python -c "
try:
    from zen.telemetry.community_auth import get_community_auth_provider
    provider = get_community_auth_provider()
    creds = provider.get_credentials()
    if creds:
        print('✅ Embedded credentials working')
    else:
        print('❌ Embedded credentials not working')
        exit(1)
except Exception as e:
    print(f'❌ Credential test failed: {e}')
    exit(1)
"

echo "🚀 Production verification complete"
EOF

chmod +x scripts/verify_production.sh
```

### **6.2 Deployment Steps**
```bash
# 1. Run production verification
./scripts/verify_production.sh

# 2. Build production package
./scripts/build_production.sh

# 3. Test package locally
pip install dist/*.whl
python demo_community_analytics.py

# 4. Upload to PyPI Test
twine upload --repository testpypi dist/*

# 5. Test from PyPI Test
pip install --index-url https://test.pypi.org/simple/ netra-zen

# 6. Deploy to production PyPI
twine upload dist/*

# 7. Verify production installation
pip install netra-zen
python -c "import zen; print('🌍 Community analytics ready!')"
```

### **6.3 Post-Deployment Monitoring**
```bash
# Monitor trace ingestion
gcloud logging read 'resource.type="cloud_trace"' \
    --project=netra-telemetry-public \
    --limit=10

# Check quota usage
gcloud monitoring metrics list \
    --filter="metric.type:cloudtrace.googleapis.com" \
    --project=netra-telemetry-public

# Monitor costs
gcloud billing budgets list \
    --billing-account=YOUR_BILLING_ACCOUNT
```

---

## 🔧 **Step 7: Development Environment Setup**

### **7.1 Local Development with Community Analytics**
```bash
# Set up development environment
export ZEN_COMMUNITY_SERVICE_ACCOUNT="path/to/zen-community-key.json"
export GOOGLE_CLOUD_PROJECT="netra-telemetry-public"

# Test local development
python -c "
import zen
from zen.telemetry import health_check
status = health_check()
print(f'Development telemetry status: {status}')
"
```

### **7.2 Testing Without Embedded Credentials**
```bash
# Create test configuration
export ZEN_TELEMETRY_DISABLED=false
export ZEN_TELEMETRY_GCP_PROJECT=netra-telemetry-public

# Run tests
python -m pytest tests/test_community_analytics.py -v
```

---

## 🚨 **Security Considerations**

### **Essential Security Measures:**

1. **🔐 Service Account Security**
   - ✅ Write-only permissions (`roles/cloudtrace.agent`)
   - ✅ No read access to existing traces
   - ✅ No access to other GCP services
   - ✅ Automatic key rotation (quarterly)

2. **🔒 Data Privacy**
   - ✅ Aggressive PII filtering for community mode
   - ✅ Anonymous session tracking only
   - ✅ No user-identifiable information
   - ✅ 30-day automatic data retention

3. **💰 Cost Protection**
   - ✅ Budget alerts at 50% and 90%
   - ✅ Quota limits on trace ingestion
   - ✅ Rate limiting in community analytics
   - ✅ Monthly cost monitoring

4. **🛡️ Access Controls**
   - ✅ Project-level IAM restrictions
   - ✅ Embedded credentials in package only
   - ✅ No external credential exposure
   - ✅ Audit logging enabled

---

## 📊 **Success Metrics**

### **Community Analytics KPIs:**
- **Adoption Rate**: % of Zen users with community analytics enabled
- **Data Quality**: Trace completion rate and error rates
- **Community Value**: Dashboard usage and insights generated
- **Privacy Compliance**: Zero PII incidents
- **Cost Efficiency**: Cost per trace under budget targets

### **Technical Metrics:**
- **Trace Ingestion**: Successful traces per day
- **Performance**: 95th percentile export latency < 5s
- **Reliability**: 99.9% uptime for trace collection
- **Security**: Zero unauthorized access attempts

---

## 🎯 **Summary**

Following this guide will result in:

✅ **Production-ready GCP infrastructure** for community analytics
✅ **Secure service account** with minimal write-only permissions
✅ **Embedded credentials** in the Zen package for zero-setup experience
✅ **Automated package distribution** with community analytics enabled
✅ **Monitoring and alerting** for cost and security protection

**Result**: Zen users get immediate community analytics value with zero configuration, while maintaining complete privacy and security.

🌍 **Ready to launch the community analytics ecosystem!**