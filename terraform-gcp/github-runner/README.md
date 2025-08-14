# GitHub Actions warp-custom-default Runner on Google Cloud Platform

This Terraform module deploys warp-custom-default GitHub Actions runners on Google Cloud Platform (GCP) with automatic configuration, monitoring, and optional auto-scaling.

## Features

- Automated GitHub Actions runner installation and registration
- Support for both repository and organization-level runners
- Optional auto-scaling based on CPU utilization
- Preemptible instance support for cost optimization
- Automatic cleanup on instance termination
- Google Cloud Operations monitoring and logging
- Secure token management using Secret Manager
- Artifact storage with lifecycle management

## Prerequisites

1. **GCP Project**: An active GCP project with billing enabled
2. **GitHub Token**: Personal Access Token with the following scopes:
   - `repo` (full control of private repositories)
   - `admin:org` (for organization runners)
3. **Terraform**: Version 1.0 or later
4. **gcloud CLI**: Authenticated with appropriate permissions

## Setup Instructions

### 1. Enable Required APIs

```bash
gcloud services enable compute.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable logging.googleapis.com
gcloud services enable monitoring.googleapis.com
```

### 2. Create GitHub Personal Access Token

1. Go to GitHub Settings → Developer settings → Personal access tokens
2. Click "Generate new token (classic)"
3. Select scopes:
   - `repo` (all)
   - `admin:org` → `manage_runners:org` (for org runners)
4. Save the token securely

### 3. Configure Terraform Variables

Copy the example variables file:

```bash
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` with your configuration:

```hcl
project_id  = "your-gcp-project-id"
github_org  = "your-github-org"
github_repo = "your-repo"  # Optional for org-level runners
```

### 4. Set GitHub Token

Export the token as an environment variable:

```bash
export TF_VAR_github_token="your-github-personal-access-token"
```

### 5. Deploy the Infrastructure

```bash
# Initialize Terraform
terraform init

# Review the plan
terraform plan

# Apply the configuration
terraform apply
```

## Configuration Options

### Basic Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `project_id` | GCP Project ID | Required |
| `github_org` | GitHub organization name | Required |
| `github_repo` | GitHub repository (optional) | `""` |
| `runner_count` | Number of runners | `1` |
| `runner_labels` | Runner labels | `["warp-custom-default", "linux", "x64", "gcp"]` |

### Instance Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `machine_type` | GCP machine type | `e2-standard-2` |
| `boot_disk_size` | Disk size in GB | `50` |
| `use_preemptible` | Use preemptible instances | `false` |

### Cost Optimization

#### Preemptible Instances
Enable preemptible instances for up to 70% cost savings:

```hcl
use_preemptible = true
```

Note: Preemptible instances can be terminated at any time and last maximum 24 hours.

#### Machine Type Selection

| Type | vCPUs | Memory | Monthly Cost* |
|------|-------|--------|--------------|
| `e2-micro` | 2 | 1GB | ~$6 |
| `e2-small` | 2 | 2GB | ~$12 |
| `e2-medium` | 2 | 4GB | ~$24 |
| `e2-standard-2` | 2 | 8GB | ~$48 |
| `e2-standard-4` | 4 | 16GB | ~$96 |

*Approximate costs for us-central1 region

### Auto-scaling Configuration

Enable auto-scaling for dynamic workloads:

```hcl
enable_autoscaling = true
min_runners        = 1
max_runners        = 5
```

## Monitoring

### View Logs

```bash
# View runner logs
gcloud compute ssh github-runner-1 --command "sudo journalctl -u actions.runner.*"

# View startup script logs
gcloud compute instances get-serial-port-output github-runner-1
```

### Cloud Console URLs

After deployment, Terraform outputs monitoring URLs:

- **Logs Explorer**: View all runner logs
- **Metrics Explorer**: Monitor CPU, memory, and disk usage
- **Compute Instances**: Manage runner instances

## Maintenance

### Update Runners

The runners automatically update when restarted:

```bash
# Restart a specific runner
gcloud compute instances reset github-runner-1

# Restart all runners
terraform apply -replace="google_compute_instance.github_runner"
```

### Remove Runners

Runners automatically unregister when instances are terminated:

```bash
terraform destroy
```

## Security Considerations

1. **Token Security**: GitHub token is stored in Secret Manager
2. **Network Security**: Runners use default VPC; customize firewall rules as needed
3. **IAM Permissions**: Service account has minimal required permissions
4. **SSH Access**: Disabled by default; enable only for debugging

### Enable SSH for Debugging

```hcl
enable_ssh        = true
ssh_source_ranges = ["YOUR_IP/32"]  # Restrict to your IP
```

## Troubleshooting

### Runner Not Appearing in GitHub

1. Check instance logs:
```bash
gcloud compute ssh github-runner-1 --command "sudo journalctl -u actions.runner.* -n 100"
```

2. Verify token permissions:
- Repository runners: Need `repo` scope
- Organization runners: Need `admin:org` scope

3. Check Secret Manager:
```bash
gcloud secrets versions access latest --secret="github-runner-token"
```

### Runner Offline

1. Check instance status:
```bash
gcloud compute instances list --filter="name:github-runner*"
```

2. Restart the service:
```bash
gcloud compute ssh github-runner-1 --command "sudo systemctl restart actions.runner.*"
```

### High Costs

1. Enable preemptible instances
2. Reduce machine type
3. Decrease boot disk size
4. Set up auto-scaling with appropriate limits

## Advanced Configuration

### Custom Runner Image

Create a custom image with pre-installed dependencies:

```hcl
boot_disk_image = "projects/YOUR_PROJECT/global/images/custom-runner-image"
```

### Multiple Runner Pools

Deploy different runner configurations for different workloads:

```bash
# Deploy CPU-optimized runners
terraform apply -var="runner_name=cpu-runner" -var="machine_type=c2-standard-4"

# Deploy memory-optimized runners  
terraform apply -var="runner_name=memory-runner" -var="machine_type=n2-highmem-2"
```

## Cleanup

To remove all resources:

```bash
terraform destroy
```

This will:
1. Unregister runners from GitHub
2. Delete compute instances
3. Remove storage buckets
4. Clean up IAM bindings
5. Delete secrets

## Support

For issues or questions:
1. Check the [GitHub Actions documentation](https://docs.github.com/en/actions/hosting-your-own-runners)
2. Review [GCP Compute Engine docs](https://cloud.google.com/compute/docs)
3. Open an issue in the repository