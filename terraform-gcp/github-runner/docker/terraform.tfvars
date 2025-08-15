# GCP Configuration
project_id = "cryptic-net-466001-n0"
region     = "us-central1"

# GitHub Configuration
github_org  = "netra-systems"
github_repo = "netra-apex"
# github_token set via environment variable: TF_VAR_github_token

# Runner Configuration
runner_name = "gcp-cloudrun-runner"
runner_labels = [
  "warp-custom-default",
  "linux", 
  "x64",
  "docker",
  "cloud-run",
  "netra"
]

# Cloud Run resources
min_instances = 1
max_instances = 5
cpu           = "2"
memory        = "4Gi"

# Features
enable_docker    = false  # Start without Docker-in-Docker
enable_keepalive = true   # Keep instances warm