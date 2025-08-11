# 🚀 Complete Staging Environment Setup Guide

This guide will help you set up automatic staging environments step-by-step. Follow each section in order - don't skip ahead!

## 📋 What You'll Need Before Starting

- [ ] A Google Cloud account with billing enabled
- [ ] A GitHub repository (the Netra project)
- [ ] A domain name you own (like `netra-ai.dev`)
- [ ] About 2 hours to complete everything

---

## Step 1: Google Cloud Setup 🌐

### 1.1 Create a New Google Cloud Project

1. Go to: https://console.cloud.google.com
2. Click the project dropdown at the top
3. Click "New Project"
4. Name it: `netra-staging`
5. Write down your Project ID (looks like: `netra-staging-`)
   ```
   My Project ID: netra-staging
   ```

### 1.2 Enable Required APIs

 1.gcloud auth login 

 run 
 ```
gcloud services enable run.googleapis.com sqladmin.googleapis.com compute.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com dns.googleapis.com redis.googleapis.com secretmanager.googleapis.com cloudresourcemanager.googleapis.com --project=netra-staging
```

OR Click each link and press the big "ENABLE" button:

1. [Cloud Run API](https://console.cloud.google.com/apis/library/run.googleapis.com)
2. [Cloud SQL Admin API](https://console.cloud.google.com/apis/library/sqladmin.googleapis.com)
3. [Compute Engine API](https://console.cloud.google.com/apis/library/compute.googleapis.com)
4. [Cloud Build API](https://console.cloud.google.com/apis/library/cloudbuild.googleapis.com)
5. [Artifact Registry API](https://console.cloud.google.com/apis/library/artifactregistry.googleapis.com)
6. [Cloud DNS API](https://console.cloud.google.com/apis/library/dns.googleapis.com)
7. [Redis API](https://console.cloud.google.com/apis/library/redis.googleapis.com)
8. [Secret Manager API](https://console.cloud.google.com/apis/library/secretmanager.googleapis.com)
9. [Cloud Resource Manager API](https://console.cloud.google.com/apis/library/cloudresourcemanager.googleapis.com)

✅ Check: All 9 APIs should show "API Enabled" ✅


### 1.3 Create Artifact Registry for Docker Images

1. Go to: https://console.cloud.google.com/artifacts
2. Click "CREATE REPOSITORY"
3. Fill in:
   - Name: `staging`
   - Format: `Docker`
   - Region: `us-central1`
4. Click "CREATE"

### 1.4 Set Up Billing Alerts (Important!)

1. Go to: https://console.cloud.google.com/billing
2. Click "Budgets & alerts" in the left menu
3. Click "CREATE BUDGET"
4. Set:
   - Name: `Staging Environments`
   - Amount: `$200` (monthly)
   - Alert at: `50%`, `90%`, `100%`
5. Click "FINISH"

---

## Step 2: Create Service Account & Get Key 🔑

### 2.1 Create Service Account

1. Go to: https://console.cloud.google.com/iam-admin/serviceaccounts
2. Click "CREATE SERVICE ACCOUNT"
3. Fill in:
   - Name: `github-staging-deployer`
   - ID: `github-staging-deployer`
4. Click "CREATE AND CONTINUE"

### 2.2 Add Permissions

run this command 
windows PS
```
"run.admin","cloudsql.admin","compute.admin","iam.serviceAccountUser","secretmanager.admin","dns.admin","artifactregistry.admin","cloudbuild.builds.editor","redis.admin","monitoring.viewer" | ForEach-Object { gcloud projects add-iam-policy-binding netra-staging --member="serviceAccount:github-staging-deployer@netra-staging.iam.gserviceaccount.com" --role="roles/$_" }
```
bash
```
for role in run.admin cloudsql.admin compute.admin iam.serviceAccountUser secretmanager.admin dns.admin artifactregistry.admin cloudbuild.builds.editor redis.admin monitoring.viewer; do gcloud projects add-iam-policy-binding netra-staging --member="serviceAccount:github-staging-deployer@netra-staging.iam.gserviceaccount.com" --role="roles/$role"; done
```
OR
Click "ADD ROLE" and add each of these roles (one at a time):

1. `Cloud Run Admin`
2. `Cloud SQL Admin`
3. `Compute Admin`
4. `Service Account User`
5. `Secret Manager Admin`
6. `DNS Administrator`
7. `Artifact Registry Administrator`
8. `Cloud Build Editor`
9. `Redis Admin`
10. `Monitoring Viewer`

Click "CONTINUE" then "DONE"

### 2.3 Download the Key

1. Find `github-staging-deployer@netra-staging-123456.iam.gserviceaccount.com` in the list
2. Click the three dots menu (...) 
3. Click "Manage keys"
4. Click "ADD KEY" → "Create new key"
5. Choose "JSON"
6. Click "CREATE"
7. **SAVE THIS FILE!** Name it: `gcp-key.json`

---

## Step 3: Domain Setup 🌍

### 3.1 Create a Subdomain for Staging

You need to create a subdomain `staging.yourdomain.com`. Here's how for common providers:

#### If using Cloudflare:
1. Go to your domain in Cloudflare
2. Click "DNS"
3. Add record:
   - Type: `CNAME`
   - Name: `staging`
   - Target: `ghs.googlehosted.com`
   - Proxy: OFF (click the orange cloud so it's gray)

#### If using GoDaddy:
1. Go to your domain settings
2. Click "DNS"
3. Add:
   - Type: `CNAME`
   - Name: `staging`
   - Value: `ghs.googlehosted.com`

#### If using Namecheap:
1. Go to Domain List → Manage
2. Click "Advanced DNS"
3. Add:
   - Type: `CNAME`
   - Host: `staging`
   - Value: `ghs.googlehosted.com`

### 3.2 Set Up Wildcard DNS

Add another record for wildcard subdomains:

1. Add record:
   - Type: `CNAME`
   - Name: `*.staging`
   - Target: `ghs.googlehosted.com`

### 3.3 Create Cloud DNS Zone

1. Go to: https://console.cloud.google.com/net-services/dns
2. Click "CREATE ZONE"
3. Fill in:
   - Zone name: `staging`
   - DNS name: `staging.netrasystems.ai`
4. Click "CREATE"
5. **IMPORTANT**: Copy the nameservers shown (you might need these)

	staging.netrasystems.ai.	SOA	21600	
ns-cloud-b1.googledomains.com. cloud-dns-hostmaster.google.com. 1 21600 3600 259200 300

staging.netrasystems.ai.	NS	21600	
ns-cloud-b1.googledomains.com.

---

## Step 4: GitHub Secrets Setup 🔒

### 4.1 Go to Your Repository Settings

1. Go to your GitHub repository
2. Click "Settings" tab
3. Click "Secrets and variables" → "Actions"

### 4.2 Add These Secrets (One by One)

Click "New repository secret" for each:

#### Secret 1: GCP_STAGING_SA_KEY
1. Name: `GCP_STAGING_SA_KEY`
2. Value: Open `gcp-key.json` in Notepad, copy EVERYTHING, paste it here
3. Click "Add secret"

#### Secret 2: GCP_PROJECT_ID
1. Name: `GCP_PROJECT_ID`  
2. Value: Your project ID from Step 1.1 (like `netra-staging`)
3. Click "Add secret"

#### Secret 3: STAGING_DB_PASSWORD
1. Name: `STAGING_DB_PASSWORD`
2. Value: `StagingPass123!@#` (or make your own strong password)
3. Click "Add secret"

#### Secret 4: GITHUB_TOKEN
1. Name: `GH_TOKEN` (GitHub already has GITHUB_TOKEN)
2. How to get it:
   - Go to: https://github.com/settings/tokens
   - Click "Generate new token" → "Classic"
   - Name: `Staging Environment Manager`
   - Check these boxes:
     - ✅ repo (all)
     - ✅ workflow
   - Click "Generate token"
   - COPY THE TOKEN NOW (you won't see it again!)
3. Paste the token as the value
4. Click "Add secret"

---

## Step 5: Create Required Files 📁

### 5.1 Create Terraform State Bucket

1. Go to: https://console.cloud.google.com/storage
2. Click "CREATE BUCKET"
3. Name: `netra-staging-terraform-state`
4. Location: `us-central1`
5. Click "CREATE"

### 5.2 Create Docker Files

Create these two files in your repository root:

#### File 1: `Dockerfile.backend`
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY alembic.ini .
COPY alembic/ ./alembic/

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### File 2: `Dockerfile.frontend`
```dockerfile
FROM node:18-alpine AS builder

WORKDIR /app

# Copy package files
COPY frontend/package*.json ./
RUN npm ci

# Copy application code
COPY frontend/ .

# Build the application
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
RUN npm run build

# Production image
FROM node:18-alpine
WORKDIR /app

COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/package*.json ./
COPY --from=builder /app/node_modules ./node_modules

EXPOSE 3000

CMD ["npm", "start"]
```

### 5.3 Update Configuration File

Edit `.github/staging.yml` and update this section:

```yaml
# Change this line:
domain: staging.netrasystems.ai  # PUT YOUR ACTUAL DOMAIN HERE!

# Example:
# domain: staging.netra-ai.dev
```

---

## Step 6: Initialize Terraform 🏗️

### 6.1 Install Terraform Locally (One Time)

1. Go to: https://www.terraform.io/downloads
2. Download for your system (Windows/Mac/Linux)
3. Install it

### 6.2 Create Initial Terraform Resources

Run these commands in your terminal:

```bash
# Go to terraform directory
cd terraform/staging

# Login to Google Cloud
gcloud auth application-default login

# Set your project
gcloud config set project netra-staging

# Initialize Terraform
terraform init

# Create a workspace for initial setup
terraform workspace new init

# Just validate everything works
terraform plan
```

---

## Step 7: Test Everything! 🧪

### 7.1 Create a Test Pull Request

1. Create a new branch:
   ```bash
   git checkout -b test-staging-setup
   ```

2. Make a small change (like edit README.md)

3. Commit and push:
   ```bash
   git add .
   git commit -m "Test staging deployment"
   git push origin test-staging-setup
   ```

4. Go to GitHub and create a Pull Request

### 7.2 Watch the Magic Happen

1. Go to the Pull Request page
2. Click "Actions" tab
3. Watch the "Staging Environment Management" workflow
4. After ~10 minutes, check the PR comments for your staging URL!

---

## Step 8: Troubleshooting 🔧

### If Deployment Fails

#### Error: "API not enabled"
- Go back to Step 1.2 and enable the missing API

#### Error: "Permission denied"
- Check Step 2.2 - make sure all roles are added
- Check Step 4.2 - make sure GCP_SA_KEY is correct

#### Error: "Invalid domain"
- Check Step 3 - DNS setup
- Wait 15 minutes for DNS to propagate

#### Error: "Quota exceeded"
1. Go to: https://console.cloud.google.com/iam-admin/quotas
2. Filter by: "Cloud Run"
3. Select your region
4. Click "EDIT QUOTAS"
5. Request increase to 20

### Common Issues & Fixes

**GitHub Action not running?**
- Check: Settings → Actions → General → Actions permissions = "Allow all actions"

**Can't access staging URL?**
- Wait 5 minutes after deployment
- Check if DNS is working: `nslookup pr-1.staging.yourdomain.com`
- Try: `https://` not `http://`

**Database connection failing?**
- Check STAGING_DB_PASSWORD secret is set
- Verify Cloud SQL API is enabled

**Container build failing?**
- Make sure Dockerfile.backend and Dockerfile.frontend exist
- Check if requirements.txt (backend) and package.json (frontend) exist

---

## Step 9: Configure Cleanup (Important!) 🧹

### 9.1 Enable Scheduled Cleanup

The cleanup workflow should already be set up, but verify:

1. Go to: Your repo → Actions
2. Find "Staging Environment Cleanup"
3. It should run daily at 2 AM UTC

### 9.2 Manual Cleanup (If Needed)

To manually clean up a staging environment:

```bash
# From Actions tab, run workflow manually
# OR use GitHub CLI:
gh workflow run staging-environment.yml -f action=destroy -f pr_number=123
```

---

## Step 10: Final Checklist ✅

Before considering setup complete:

- [ ] Created GCP project with billing enabled
- [ ] Enabled all 9 required APIs
- [ ] Created service account with key
- [ ] Added all 4 GitHub secrets
- [ ] Set up domain with wildcard DNS
- [ ] Created Dockerfiles
- [ ] Updated staging.yml with your domain
- [ ] Created test PR and saw staging URL
- [ ] Verified cleanup works

---

## 🎉 Congratulations!

Your staging environment system is now working! 

### What Happens Now:

1. **Every PR** automatically gets a staging environment
2. **URLs** are posted as PR comments
3. **Tests** run automatically
4. **Cleanup** happens when PR closes
5. **Costs** are monitored and limited

### Quick Commands:

```bash
# Skip staging for a PR
# Add label: "no-staging"

# Keep staging longer
# Add label: "keep-staging"

# Force redeploy
git commit --amend --no-edit
git push --force

# Check costs
# Go to: https://console.cloud.google.com/billing
```

### Cost Expectations:

- **Per PR**: $1-5/day when active
- **Monthly**: ~$50-200 total for all PRs
- **Idle**: $0 (scales to zero)

---

## Need Help? 🆘

1. **Check logs**: Actions tab → Click failed workflow
2. **Check GCP**: https://console.cloud.google.com/logs
3. **Common fixes**: Re-run the workflow (sometimes it's temporary)
4. **Still stuck?**: Create an issue with:
   - Error message
   - Screenshot of failing action
   - Your domain name
   - Which step you're on

---

## Optional: Advanced Features 🚀

Once basic setup works, you can:

### Add Slack Notifications
1. Create Slack webhook: https://api.slack.com/messaging/webhooks
2. Add secret: `SLACK_WEBHOOK_URL`
3. Update `.github/staging.yml`:
   ```yaml
   notifications:
     slack:
       enabled: true
   ```

### Increase Resource Limits
Edit `.github/staging.yml`:
```yaml
resource_limits:
  compute:
    cpu_limit: "4"      # More CPU
    memory_limit: "8Gi" # More RAM
```

### Add More Test Data
Edit `scripts/seed_staging_data.py` defaults

### Custom Domain per Customer
Add more DNS records for customer-specific demos

---

## Security Notes 🔐

**NEVER**:
- Commit the GCP key file to git
- Share the staging DB password
- Use production data in staging

**ALWAYS**:
- Rotate keys every 90 days
- Monitor costs weekly
- Clean up old environments

---

*Last Updated: 2025-08-11*
*Guide Version: 1.0*