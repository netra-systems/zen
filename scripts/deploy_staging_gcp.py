#!/usr/bin/env python3
"""
Deploy staging to GCP with proper caching and push like GitHub workflow
"""

import subprocess
import sys
import os
import json
import time
from pathlib import Path
import io
from typing import Tuple

# Fix encoding for Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def run_command(cmd, cwd=None, check=True):
    """Execute command and return result."""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"Error: {result.stderr}")
        return None
    return result

def setup_docker_buildx():
    """Setup Docker Buildx for advanced caching."""
    print("\n📦 Setting up Docker Buildx...")
    run_command(["docker", "buildx", "create", "--use", "--name", "staging-builder", "--driver", "docker-container"], check=False)
    run_command(["docker", "buildx", "inspect", "--bootstrap"])

def build_and_push_image(service, dockerfile, context, tag, cache_from=None, cache_to=None):
    """Build and push Docker image with caching."""
    print(f"\n🔨 Building {service}...")
    
    cmd = [
        "docker", "buildx", "build",
        "--platform", "linux/amd64",
        "-f", dockerfile,
        "-t", tag,
        "--build-arg", "BUILDKIT_INLINE_CACHE=1",
        "--progress", "plain"
    ]
    
    # Add multiple cache sources for better hit rate
    if cache_from:
        # Try registry cache first
        cmd.extend(["--cache-from", cache_from])
        # Also use local cache
        cmd.extend(["--cache-from", "type=local,src=/tmp/.buildx-cache"])
    
    if cache_to:
        # Export to both registry and local
        cmd.extend(["--cache-to", cache_to])
        cmd.extend(["--cache-to", "type=local,dest=/tmp/.buildx-cache-new,mode=max"])
    
    # For local testing, use --load instead of --push
    if os.getenv("LOCAL_BUILD", "false") == "true":
        cmd.append("--load")
    else:
        cmd.append("--push")
    
    cmd.append(context)
    
    result = run_command(cmd)
    
    # Move cache to permanent location
    if os.path.exists("/tmp/.buildx-cache-new"):
        import shutil
        if os.path.exists("/tmp/.buildx-cache"):
            shutil.rmtree("/tmp/.buildx-cache")
        shutil.move("/tmp/.buildx-cache-new", "/tmp/.buildx-cache")
    
    return result

def _setup_deployment_config() -> Tuple[str, str]:
    """Setup deployment configuration and return project_id and commit_sha."""
    project_root = Path(__file__).parent
    os.chdir(project_root)
    project_id = os.getenv("GCP_PROJECT_ID", "netra-staging")
    commit_sha = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()[:7]
    print("🚀 Staging Deployment to GCP")
    print(f"   Project: {project_id}\n   Commit: {commit_sha}")
    return project_id, commit_sha

def _configure_gcp_docker() -> None:
    """Configure Docker for GCP if not in local build mode."""
    if os.getenv("LOCAL_BUILD", "false") != "true":
        print("\n🔐 Configuring GCP Docker...")
        run_command(["gcloud", "auth", "configure-docker", "gcr.io", "--quiet"])

def _build_backend_image(project_id: str, commit_sha: str) -> str:
    """Build and push backend image."""
    backend_tag = f"gcr.io/{project_id}/backend:{commit_sha}"
    backend_cache = f"gcr.io/{project_id}/backend:buildcache"
    print("\n📦 Building Backend...")
    build_and_push_image("backend", "Dockerfile.backend", ".", backend_tag,
                          cache_from=f"type=registry,ref={backend_cache}",
                          cache_to=f"type=registry,ref={backend_cache},mode=max")
    return backend_tag

def _build_frontend_image(project_id: str, commit_sha: str) -> str:
    """Build and push frontend image with enhanced caching."""
    frontend_tag = f"gcr.io/{project_id}/frontend:{commit_sha}"
    frontend_cache = f"gcr.io/{project_id}/frontend:buildcache"
    print("\n📦 Building Frontend...")
    _execute_frontend_build(frontend_tag, frontend_cache)
    _update_buildx_cache()
    return frontend_tag

def _execute_frontend_build(frontend_tag: str, frontend_cache: str) -> None:
    """Execute frontend build with enhanced caching configuration."""
    frontend_api_url = os.getenv("NEXT_PUBLIC_API_URL", "https://api.staging.netrasystems.ai")
    cmd = _build_frontend_command(frontend_tag, frontend_cache, frontend_api_url)
    if os.getenv("LOCAL_BUILD", "false") == "true":
        cmd.append("--load")
    else:
        cmd.append("--push")
    cmd.append(".")
    run_command(cmd)

def _build_frontend_command(frontend_tag: str, frontend_cache: str, api_url: str) -> list:
    """Build frontend Docker command with caching options."""
    return [
        "docker", "buildx", "build", "--platform", "linux/amd64",
        "-f", "Dockerfile.frontend.staging", "-t", frontend_tag,
        "--build-arg", "BUILDKIT_INLINE_CACHE=1", "--build-arg", f"NEXT_PUBLIC_API_URL={api_url}",
        "--cache-from", f"type=registry,ref={frontend_cache}", "--cache-from", "type=local,src=/tmp/.buildx-cache",
        "--cache-to", f"type=registry,ref={frontend_cache},mode=max", "--cache-to", "type=local,dest=/tmp/.buildx-cache-new,mode=max",
        "--progress", "plain"
    ]

def _update_buildx_cache() -> None:
    """Update buildx cache by moving new cache to permanent location."""
    if os.path.exists("/tmp/.buildx-cache-new"):
        import shutil
        if os.path.exists("/tmp/.buildx-cache"):
            shutil.rmtree("/tmp/.buildx-cache")
        shutil.move("/tmp/.buildx-cache-new", "/tmp/.buildx-cache")

def _print_success_summary(backend_tag: str, frontend_tag: str) -> None:
    """Print deployment success summary."""
    print("\n✅ Images built and pushed successfully!")
    print(f"   Backend: {backend_tag}")
    print(f"   Frontend: {frontend_tag}")

def _setup_local_testing() -> None:
    """Setup local testing environment if in local build mode."""
    if os.getenv("LOCAL_BUILD", "false") == "true":
        print("\n🏃 Starting local services...")
        run_command(["docker-compose", "-f", "docker-compose.staging.yml", "up", "-d"])
        print("\n⏳ Waiting for services...")
        time.sleep(20)
        print("\n✅ Local staging ready!\n   Frontend: http://localhost:3000\n   Backend: http://localhost:8080")

def main() -> None:
    """Main deployment orchestration function."""
    project_id, commit_sha = _setup_deployment_config()
    setup_docker_buildx()
    _configure_gcp_docker()
    backend_tag = _build_backend_image(project_id, commit_sha)
    frontend_tag = _build_frontend_image(project_id, commit_sha)
    _print_success_summary(backend_tag, frontend_tag)
    _setup_local_testing()

if __name__ == "__main__":
    main()