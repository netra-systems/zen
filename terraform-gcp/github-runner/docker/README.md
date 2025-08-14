# GitHub Runner on Cloud Run

A clean, containerized approach to running GitHub Actions warp-custom-default runners on Google Cloud Run, managed with Terraform.

## 🚀 Benefits Over VM + Startup Scripts

| Old Approach (VM + Scripts) | New Approach (Container + Cloud Run) |
|---------------------------|-------------------------------------|
| 800+ lines of complex bash scripts | Simple 50-line Dockerfile |
| Mutable infrastructure | Immutable container images |
| Manual error recovery | Automatic container restarts |
| Hard to test locally | Easy local Docker testing |
| Slow provisioning (5-10 min) | Fast scaling (seconds) |
| Complex state management | Stateless containers |
| Manual scaling | Auto-scaling built-in |

## 📋 Prerequisites

- GCP Project with billing enabled
- GitHub Personal Access Token (PAT) with:
  - `repo` scope (for repository runners)
  - `admin:org` scope (for organization runners)
- Tools installed:
  - `terraform` >= 1.0
  - `gcloud` CLI
  - `docker` (for building images)

## 🚀 Quick Start

### 1. Set Environment Variables

```bash
export GCP_PROJECT_ID="your-project-id"
export TF_VAR_github_token="ghp_your_github_pat_token"
export REGION="us-central1"  # Optional, defaults to us-central1
```

### 2. Deploy

```bash
# Full deployment (build image + deploy with Terraform)
./deploy.sh deploy

# Or step by step:
./deploy.sh build      # Build and push Docker image
./deploy.sh terraform  # Deploy with Terraform
```

### 3. Configuration

Edit `terraform.tfvars`:

```hcl
project_id = "your-gcp-project-id"
region     = "us-central1"

github_org  = "your-github-org"
github_repo = "your-repo"  # Optional for org-level runner

runner_name = "gcp-cloudrun-runner"
runner_labels = ["warp-custom-default", "linux", "x64", "docker", "cloud-run"]

# Resources
min_instances = 1
max_instances = 5
cpu           = "2"
memory        = "4Gi"
```

## 🏗️ Architecture

```
┌─────────────────┐
│   GitHub.com    │
│   Workflows     │
└────────┬────────┘
         │ Polls for jobs
         ▼
┌─────────────────┐
│   Cloud Run     │
│  ┌───────────┐  │
│  │ Container │  │ ◄── Auto-scales based on demand
│  │  Runner   │  │
│  └───────────┘  │
└─────────────────┘
         │
         ▼
┌─────────────────┐
│ Secret Manager  │ ◄── Stores GitHub token securely
└─────────────────┘
```

## 📦 What's Included

- **Dockerfile**: Ubuntu-based runner with all dependencies
- **Terraform Config**: Complete infrastructure as code
- **Auto-scaling**: Scales based on job queue
- **Secret Management**: Secure token storage
- **Health Checks**: Automatic container health monitoring
- **Cloud Build**: Automated image building on push

## 🔧 Customization

### Add More Tools to Runner

Edit `Dockerfile`:

```dockerfile
# Add your tools
RUN apt-get update && apt-get install -y \
    nodejs \
    npm \
    your-tool-here
```

### Enable Docker-in-Docker

In `terraform.tfvars`:

```hcl
enable_docker = true
```

### Adjust Resources

```hcl
cpu    = "4"     # 4 vCPUs
memory = "8Gi"   # 8GB RAM
```

## 🧪 Local Testing

```bash
# Build locally
docker build -t github-runner .

# Run locally (for testing)
docker run -it \
  -e GITHUB_ORG="your-org" \
  -e GITHUB_REPO="your-repo" \
  -e GITHUB_TOKEN="$TF_VAR_github_token" \
  github-runner
```

## 🛠️ Maintenance

### View Logs

```bash
gcloud run services logs read github-runner --region=$REGION
```

### Update Runner Version

Edit `Dockerfile`:

```dockerfile
ARG RUNNER_VERSION=2.312.0  # Update version here
```

Then rebuild and deploy:

```bash
./deploy.sh deploy
```

### Destroy Everything

```bash
./deploy.sh destroy
```

## 💰 Cost Optimization

Cloud Run charges only for:
- CPU/Memory while processing jobs
- Minimum instances (if configured)
- Network egress

Typical costs: ~$5-20/month for moderate usage vs $50-100/month for always-on VM

## 🔒 Security

- GitHub token stored in Secret Manager
- Service account with minimal permissions
- Container runs as non-root user
- Automatic security updates via container rebuilds

## 📊 Monitoring

View metrics in Cloud Console:
- CPU utilization
- Memory usage
- Request count (job runs)
- Cold starts
- Error rates

## 🚨 Troubleshooting

### Runner Not Appearing in GitHub

Check logs:
```bash
gcloud run services logs read github-runner --region=$REGION --limit=50
```

### Container Keeps Restarting

- Check GitHub token is valid
- Verify org/repo names are correct
- Check Cloud Run logs for errors

### Jobs Timing Out

Increase timeout in `main.tf`:
```hcl
timeout = "7200s"  # 2 hours
```

## 🔄 Migration from VM-based Runners

1. Deploy Cloud Run runners with different labels
2. Update workflows to use new labels
3. Monitor both for a few days
4. Decommission old VM runners
5. Update labels to match old ones if desired

## 📝 License

MIT