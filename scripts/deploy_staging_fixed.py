#!/usr/bin/env python3
"""
Fixed staging deployment with proper caching and local/cloud support
"""

import subprocess
import sys
import os
import json
import time
import shutil
from pathlib import Path
import io

# Fix encoding for Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def run_command(cmd, cwd=None, check=True, env=None):
    """Execute command and return result."""
    print(f"Running: {' '.join(cmd)}")
    env_vars = os.environ.copy()
    if env:
        env_vars.update(env)
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, env=env_vars)
    if result.stdout:
        print(result.stdout)
    if check and result.returncode != 0:
        print(f"Error: {result.stderr}")
        return None
    return result

def setup_docker_buildx():
    """Setup Docker Buildx for advanced caching."""
    print("\n📦 Setting up Docker Buildx...")
    # Check if builder exists
    result = run_command(["docker", "buildx", "ls"], check=False)
    if result and "staging-builder" in result.stdout:
        print("Builder already exists, using existing one")
        run_command(["docker", "buildx", "use", "staging-builder"])
    else:
        run_command(["docker", "buildx", "create", "--use", "--name", "staging-builder", "--driver", "docker-container"], check=False)
    run_command(["docker", "buildx", "inspect", "--bootstrap"])
    
    # Create cache directory
    cache_dir = Path("/tmp/.buildx-cache")
    cache_dir.mkdir(exist_ok=True)
    print(f"Cache directory ready: {cache_dir}")

def build_frontend_local():
    """Build frontend locally first for faster iteration."""
    print("\n🏗️ Building frontend locally...")
    frontend_dir = Path("frontend")
    
    # Check if we need to install dependencies
    node_modules = frontend_dir / "node_modules"
    if not node_modules.exists():
        print("Installing frontend dependencies...")
        run_command(["npm", "ci", "--legacy-peer-deps"], cwd=str(frontend_dir))
    
    # Build Next.js app
    print("Building Next.js application...")
    env = {
        "NEXT_PUBLIC_API_URL": os.getenv("NEXT_PUBLIC_API_URL", "http://localhost:8080"),
        "NODE_OPTIONS": "--max-old-space-size=4096"
    }
    run_command(["npm", "run", "build"], cwd=str(frontend_dir), env=env)
    print("✅ Frontend built successfully")

def build_docker_image(service, dockerfile, tag, use_cache=True):
    """Build Docker image with proper caching."""
    print(f"\n🔨 Building {service}...")
    
    cmd = [
        "docker", "buildx", "build",
        "--platform", "linux/amd64",
        "-f", dockerfile,
        "-t", tag,
        "--build-arg", "BUILDKIT_INLINE_CACHE=1",
        "--progress", "plain"
    ]
    
    # Add caching options
    if use_cache:
        cache_dir = "/tmp/.buildx-cache"
        cmd.extend([
            "--cache-from", f"type=local,src={cache_dir}",
            "--cache-to", f"type=local,dest={cache_dir}-new,mode=max"
        ])
    
    # Use --load for local deployment
    cmd.append("--load")
    cmd.append(".")
    
    result = run_command(cmd)
    
    # Update cache
    if use_cache and Path(f"/tmp/.buildx-cache-new").exists():
        if Path("/tmp/.buildx-cache").exists():
            shutil.rmtree("/tmp/.buildx-cache")
        shutil.move("/tmp/.buildx-cache-new", "/tmp/.buildx-cache")
    
    return result

def deploy_with_compose():
    """Deploy using docker-compose."""
    print("\n🚀 Deploying with docker-compose...")
    
    # Stop existing containers
    print("Stopping existing containers...")
    run_command(["docker-compose", "-f", "docker-compose.staging.yml", "down"], check=False)
    
    # Start services
    print("Starting services...")
    run_command([
        "docker-compose", "-f", "docker-compose.staging.yml", 
        "up", "-d", "--build"
    ])
    
    print("\n⏳ Waiting for services to be healthy...")
    time.sleep(15)
    
    # Check status
    run_command(["docker-compose", "-f", "docker-compose.staging.yml", "ps"])

def deploy_with_act():
    """Deploy using ACT to simulate GitHub Actions."""
    print("\n🎭 Deploying with ACT (GitHub Actions locally)...")
    
    # Create event.json if not exists
    event_file = Path("event.json")
    if not event_file.exists():
        event_data = {
            "action": "deploy",
            "inputs": {
                "action": "deploy",
                "force": True
            }
        }
        event_file.write_text(json.dumps(event_data, indent=2))
    
    # Create .env.act for secrets
    env_act = Path(".env.act")
    if not env_act.exists():
        print("Creating .env.act with default values...")
        env_act.write_text("""
LOCAL_DEPLOY=true
ACT=true
DOCKER_BUILDKIT=1
""")
    
    # Run ACT
    cmd = [
        "act", 
        "-W", ".github/workflows/staging-environment.yml",
        "--env-file", ".env.act",
        "--container-architecture", "linux/amd64",
        "-e", "event.json",
        "--verbose",
        "workflow_dispatch"
    ]
    
    run_command(cmd, check=False)

def main():
    """Main deployment orchestrator."""
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    print("🚀 Netra Staging Deployment")
    print("=" * 50)
    
    # Parse arguments
    mode = sys.argv[1] if len(sys.argv) > 1 else "compose"
    
    if mode == "local":
        print("\n📍 Mode: Local Build + Docker Compose")
        setup_docker_buildx()
        build_frontend_local()
        
        # Build optimized Docker images
        build_docker_image(
            "backend",
            "Dockerfile.backend",
            "netra-backend:staging"
        )
        
        # Use optimized frontend Dockerfile
        dockerfile = "Dockerfile.frontend.optimized"
        if not Path(dockerfile).exists():
            dockerfile = "Dockerfile.frontend.staging"
        
        build_docker_image(
            "frontend",
            dockerfile,
            "netra-frontend:staging"
        )
        
        deploy_with_compose()
        
    elif mode == "act":
        print("\n🎭 Mode: ACT (GitHub Actions locally)")
        deploy_with_act()
        
    elif mode == "compose":
        print("\n🐳 Mode: Docker Compose")
        setup_docker_buildx()
        deploy_with_compose()
        
    else:
        print(f"Unknown mode: {mode}")
        print("Usage: python deploy_staging_fixed.py [local|act|compose]")
        sys.exit(1)
    
    print("\n✅ Deployment complete!")
    print("\n📋 Access points:")
    print("   Frontend: http://localhost:3000")
    print("   Backend: http://localhost:8080")
    print("\n🛠️ Useful commands:")
    print("   Logs: docker-compose -f docker-compose.staging.yml logs -f")
    print("   Stop: docker-compose -f docker-compose.staging.yml down")
    print("   Status: docker-compose -f docker-compose.staging.yml ps")

if __name__ == "__main__":
    main()