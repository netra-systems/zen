# Deploy Single GitHub Runner with Docker Fixes

This guide deploys a single new GitHub runner instance with all Docker fixes preloaded.

## Prerequisites

1. GCP project with billing enabled
2. GitHub Personal Access Token with appropriate permissions
3. Terraform installed (>= 1.0)
4. gcloud CLI configured

## Quick Deploy

### 1. Set up credentials

```bash
# Authenticate with GCP
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID
```

### 2. Configure variables

```bash
# Copy example variables
cp terraform.tfvars.example terraform.tfvars

# Edit with your values
nano terraform.tfvars
```

**Required changes in terraform.tfvars:**
- `project_id`: Your GCP project ID
- `github_org`: Your GitHub organization
- `github_repo`: Your repository (optional, leave empty for org-level)
- `github_token`: Your GitHub PAT (or set via environment variable)

### 3. Deploy the single runner

```bash
# Initialize Terraform
terraform init

# Plan the deployment (shows what will be created)
terraform plan -target=google_compute_instance.github_runner_fixed

# Deploy the single runner with Docker fixes
terraform apply -target=google_compute_instance.github_runner_fixed -auto-approve
```

### 4. Verify deployment

```bash
# Get instance details
terraform output fixed_runner_instance

# SSH into the instance (if SSH enabled)
gcloud compute ssh github-runner-fixed-* --zone=us-central1-a

# Check runner status
sudo systemctl status actions.runner.*

# Check Docker status
sudo docker version
sudo su - runner -c "docker version"
```

## What's Included

The single runner instance includes:

1. **Enhanced Docker Setup**
   - Proper daemon initialization with 60-second wait
   - Docker buildx pre-configured
   - Correct permissions for runner user

2. **Automatic Recovery**
   - Retry logic for all critical operations
   - Docker permission fixes
   - Service restart on failure

3. **Monitoring**
   - Google Cloud Ops Agent
   - Runner and Docker logs
   - Health status checks

## Troubleshooting

### Check installation logs
```bash
sudo tail -f /var/log/github-runner-install.log
```

### Run diagnostics
```bash
# Download and run diagnostic script
sudo bash /tmp/diagnose-runner.sh
```

### Fix Docker issues on running instance
```bash
# Download and run Docker fix script
sudo bash /tmp/fix-docker-daemon.sh
```

### Restart runner service
```bash
sudo systemctl restart actions.runner.*
```

## Configuration Options

Edit `single-runner.tf` to customize:

- **Machine type**: Default is `e2-standard-2` (2 vCPUs, 8GB RAM)
- **Disk size**: Default is 50GB
- **Labels**: Add custom runner labels
- **Preemptible**: Set to true for 70% cost savings (less reliable)

## Clean Up

To remove the single runner:

```bash
terraform destroy -target=google_compute_instance.github_runner_fixed
```

## Notes

- The runner name includes a timestamp to ensure uniqueness
- All Docker fixes are applied during startup
- The instance will auto-register with GitHub
- Logs are available in `/var/log/github-runner-install.log`