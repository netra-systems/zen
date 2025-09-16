---
allowed-tools: ["Bash", "Read", "Task"]
description: "Deploy to GCP following project norms and standards"
argument-hint: "<environment> [options]"
---

# 🚀 GCP Deployment

Deploy to Google Cloud Platform following Netra Apex standards.

## Configuration
- **Environment:** ${1:-staging}
- **Project:** ${2:-netra-staging}
- **Build Mode:** ${3:---build-local}

## Pre-Deployment Checklist

### 1. Authenticate with GCP (REQUIRED)
!echo "🔐 GCP Authentication Check:"
!echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
!gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>/dev/null | head -1 || echo "❌ Not authenticated"
!echo ""
!echo "⚠️  IMPORTANT: If not authenticated, please run:"
!echo "   gcloud auth login"
!echo ""
!echo "Press Ctrl+C to cancel and authenticate if needed."
!echo "Waiting 5 seconds before continuing..."
!sleep 5

### 2. Verify CLAUDE.md Compliance
!echo "\n🔍 Pre-Deployment Compliance Check:"
!python scripts/check_architecture_compliance.py | grep -E "PASS|FAIL" | tail -5

### 3. Run Tests
!echo "\n🧪 Running smoke tests before deployment..."
!python tests/unified_test_runner.py --real-services --category smoke --fast-fail 2>&1 | tail -10

### 4. Check Git Status
!echo "\n📦 Git Status Check:"
!git status --short
!echo "\nLatest commit:"
!git log -1 --oneline

## Deployment Process

### 5. Set GCP Project
!echo "\n⚙️ Setting GCP project to ${2:-netra-staging}..."
!gcloud config set project ${2:-netra-staging}

### 6. Verify Authentication
!echo "\n🔐 Verifying GCP authentication..."
!gcloud auth list --filter=status:ACTIVE --format="table(ACCOUNT,STATUS)" || (echo "❌ Authentication failed. Please run: gcloud auth login" && exit 1)

### 7. Deploy Using Official Script
!echo "\n🚀 Deploying to ${1:-staging} environment..."
!echo "Command: python scripts/deploy_to_gcp.py --project ${2:-netra-staging} ${3:---build-local}"
!python scripts/deploy_to_gcp.py --project ${2:-netra-staging} ${3:---build-local}

### 8. Verify Deployment
!echo "\n✅ Verifying deployment..."
!gcloud run services list --region us-central1 --format="table(SERVICE,REGION,URL,LAST_DEPLOYED_BY,LAST_DEPLOYED_AT)"

### 9. Check Service Health
!echo "\n🎯 Checking service health endpoints..."
if [[ "${1:-staging}" == "staging" ]]; then
    !echo "Backend Health:"
    !curl -s https://backend-staging-[hash].run.app/health | head -1 || echo "Check URL"
    !echo "\nAuth Health:"
    !curl -s https://auth-[hash].run.app/health | head -1 || echo "Check URL"
fi

### 10. Post-Deployment Logs
!echo "\n📄 Recent deployment logs:"
!gcloud run services describe backend-${1:-staging} --region us-central1 --format="value(status.conditions[0])" 2>/dev/null

### 11. Deployment Summary
!echo "\n📋 DEPLOYMENT SUMMARY:"
!echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
!echo "Environment: ${1:-staging}"
!echo "Project: ${2:-netra-staging}"
!echo "Timestamp: $(date)"
!echo "Deployed by: $(gcloud config get-value account)"

## Rollback Instructions
If deployment fails:
```bash
gcloud run services update-traffic backend-${1:-staging} --to-revisions=PREVIOUS=100
```

## Usage Examples
- `/deploy-gcp` - Deploy to staging (default)
- `/deploy-gcp staging netra-staging` - Explicit staging deployment
- `/deploy-gcp production netra-prod --no-build` - Production deployment

## Prerequisites
1. **MUST** authenticate first: `gcloud auth login`
2. GCP CLI installed: `brew install google-cloud-sdk`
3. Proper permissions for the GCP project
4. Docker running for local builds

## Notes
- Always prompts for authentication first
- Runs compliance checks before deployment
- Follows SPEC/deployment standards
- Creates deployment logs for audit