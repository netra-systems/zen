# GCP Configuration
project_id = "304612253870"
region     = "us-central1"
zone       = "us-central1-a"

# GitHub Configuration
# github_token should be set via environment variable: TF_VAR_github_token
github_org  = "netra-systems"
github_repo = "netra-apex"  # Optional: leave empty for org-level runner
github_token = "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"

# Runner Configuration
runner_name   = "gcp-runner"
runner_count  = 2
runner_labels = ["warp-custom-default", "linux", "x64", "gcp", "netra"]
runner_group  = ""  # Optional: runner group name

# Instance Configuration
machine_type     = "e2-standard-2"  # 2 vCPUs, 8GB RAM
boot_disk_size   = 50
boot_disk_type   = "pd-standard"    # Use "pd-ssd" for better performance
use_preemptible  = false             # Set to true for cost savings (70% cheaper)

# Autoscaling Configuration
enable_autoscaling = false
min_runners        = 1
max_runners        = 5

# Network Configuration
enable_ssh        = false  # Enable for debugging
ssh_source_ranges = ["0.0.0.0/0"]  # Restrict in production

# Storage Configuration
artifact_retention_days = 3

# Environment
environment = "production"