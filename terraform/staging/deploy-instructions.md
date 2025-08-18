# Terraform CLOUD STAGING Deployment Instructions

**⚠️ This is for CLOUD STAGING on Google Cloud Platform**  
**For LOCAL development, use `terraform-dev-postgres/` instead**

## Prerequisites for CLOUD Staging

1. Install Google Cloud SDK
2. Authenticate with GCP
3. Set up Terraform backend bucket

## Step 1: Deploy Shared Infrastructure (One-time setup)

First, deploy the shared infrastructure that all PR environments will use:

```bash
# Authenticate with GCP
gcloud auth login
gcloud config set project netra-staging

# Create Terraform state bucket if it doesn't exist
gsutil mb gs://netra-staging-terraform-state

# Deploy shared infrastructure
cd terraform/staging/shared-infrastructure
terraform init \
  -backend-config="bucket=netra-staging-terraform-state" \
  -backend-config="prefix=staging/shared-infrastructure"

terraform plan \
  -var="project_id=netra-staging" \
  -var="region=us-central1" \
  -var="staging_domain=staging.netrasystems.ai"

terraform apply \
  -var="project_id=netra-staging" \
  -var="region=us-central1" \
  -var="staging_domain=staging.netrasystems.ai"
```

## Step 2: Deploy PR Environment

After shared infrastructure is ready, deploy a PR environment:

```bash
cd terraform/staging

# Initialize Terraform
terraform init \
  -backend-config="bucket=netra-staging-terraform-state" \
  -backend-config="prefix=staging/pr-123"

# Plan the deployment
terraform plan \
  -var="project_id=netra-staging" \
  -var="region=us-central1" \
  -var="pr_number=123" \
  -var="backend_image=us-central1-docker.pkg.dev/netra-staging/staging/backend:pr-123" \
  -var="frontend_image=us-central1-docker.pkg.dev/netra-staging/staging/frontend:pr-123" \
  -var="postgres_password=YOUR_SECURE_PASSWORD"

# Apply the changes
terraform apply \
  -var="project_id=netra-staging" \
  -var="region=us-central1" \
  -var="pr_number=123" \
  -var="backend_image=us-central1-docker.pkg.dev/netra-staging/staging/backend:pr-123" \
  -var="frontend_image=us-central1-docker.pkg.dev/netra-staging/staging/frontend:pr-123" \
  -var="postgres_password=YOUR_SECURE_PASSWORD"
```

## Step 3: Access Your Environment

After deployment, you'll get output URLs:
- Frontend: https://frontend-pr-123-xxxxx.run.app
- Backend: https://backend-pr-123-xxxxx.run.app

## Step 4: Destroy PR Environment

When the PR is closed:

```bash
terraform destroy \
  -var="project_id=netra-staging" \
  -var="region=us-central1" \
  -var="pr_number=123" \
  -var="backend_image=us-central1-docker.pkg.dev/netra-staging/staging/backend:pr-123" \
  -var="frontend_image=us-central1-docker.pkg.dev/netra-staging/staging/frontend:pr-123" \
  -var="postgres_password=YOUR_SECURE_PASSWORD"
```

## Using terraform.tfvars file

Create a `terraform.tfvars` file to avoid typing variables:

```hcl
project_id        = "netra-staging"
region           = "us-central1"
pr_number        = "123"
backend_image    = "us-central1-docker.pkg.dev/netra-staging/staging/backend:pr-123"
frontend_image   = "us-central1-docker.pkg.dev/netra-staging/staging/frontend:pr-123"
postgres_password = "secure-password-here"
```

Then simply run:
```bash
terraform plan
terraform apply
```

## Troubleshooting

### State Lock Issues
If you get a state lock error:
```bash
# Check for stale locks
gsutil ls gs://netra-staging-terraform-state/staging/pr-123/

# Remove stale lock (if confirmed stale)
gsutil rm gs://netra-staging-terraform-state/staging/pr-123/default.tflock
```

### Missing Shared Infrastructure
If you get errors about missing shared infrastructure:
1. Ensure Step 1 (shared infrastructure) was completed
2. Check the state exists:
   ```bash
   gsutil ls gs://netra-staging-terraform-state/staging/shared-infrastructure/
   ```

### Permission Issues
Ensure your service account has these roles:
- Cloud Run Admin
- Cloud SQL Admin
- Compute Network Admin
- Service Account User