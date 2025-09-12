#!/usr/bin/env python
"""
Container Local Build Script - Supports Docker and Podman
==========================================================
This script ensures container builds use only local images and never pull from registries.
Automatically detects and uses either Docker or Podman based on availability.

CRITICAL LEARNING: Docker hits rate limits when trying to pull base images during builds.
Solution: Use --pull never flag and ensure base images are cached locally.

Business Value: Prevents development blockage due to registry rate limits and enables
flexibility in container runtime choice.
"""

import subprocess
import sys
import logging
import shutil
from pathlib import Path
from typing import Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent

def detect_container_runtime():
    """Detect available container runtime (Docker or Podman)."""
    if shutil.which("docker"):
        if shutil.which("docker-compose"):
            return "docker", "docker-compose"
        elif subprocess.run(["docker", "compose", "version"], capture_output=True).returncode == 0:
            return "docker", "docker compose"
    if shutil.which("podman"):
        if shutil.which("podman-compose"):
            return "podman", "podman-compose"
    raise RuntimeError("No container runtime found! Install Docker or Podman.")

def build_with_local_cache(service_name: str, dockerfile: str, compose_file: str = "docker-compose.test.yml", runtime: Optional[str] = None):
    """
    Build container image using only local cache, no pulls from registries.
    
    Args:
        service_name: Name of the service to build
        dockerfile: Path to Dockerfile
        compose_file: Docker compose file to use
        runtime: Force specific runtime, or None for auto-detect
    """
    compose_path = PROJECT_ROOT / compose_file
    
    # Detect runtime if not specified
    if runtime:
        container_cmd = runtime
        compose_cmd = f"{runtime}-compose" if runtime in ["docker", "podman"] else runtime
    else:
        container_cmd, compose_cmd = detect_container_runtime()
        logger.info(f"Using container runtime: {container_cmd}, compose: {compose_cmd}")
    
    # Build compose command
    if compose_cmd == "docker compose":
        cmd = ["docker", "compose"]
    else:
        cmd = [compose_cmd]
    
    # Add compose file and build command
    cmd.extend([
        "-f", str(compose_path),
        "build",
        "--pull", "never",  # CRITICAL: Never pull from registries
        "--no-cache",       # Fresh build but use local base images
        service_name
    ])
    
    logger.info(f"Building {service_name} with local cache only...")
    logger.info(f"Command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=PROJECT_ROOT)
        if result.returncode != 0:
            logger.error(f"Build failed: {result.stderr}")
            
            # Check if it's a missing base image
            if "pull access denied" in result.stderr or "not found" in result.stderr:
                runtime = container_cmd if 'container_cmd' in locals() else "docker"
                logger.error("\n" + "="*60)
                logger.error("MISSING BASE IMAGE DETECTED!")
                logger.error(f"{runtime.title()} is trying to pull from registry but we blocked it.")
                logger.error("Solutions:")
                logger.error("1. Pull the base image manually when not rate limited:")
                logger.error(f"   {runtime} pull python:3.11-alpine")
                logger.error(f"   {runtime} pull node:18-alpine")
                logger.error("2. Use existing cached images")
                logger.error("3. Build from a Dockerfile with FROM scratch")
                if runtime == "podman":
                    logger.error("4. For Podman: Use fully qualified names (docker.io/python:3.11-alpine)")
                logger.error("="*60 + "\n")
            
            return False
        
        logger.info(f" PASS:  Successfully built {service_name} using local cache")
        return True
        
    except Exception as e:
        logger.error(f"Build error: {e}")
        return False


def ensure_base_images(runtime: Optional[str] = None):
    """Check and report on available base images."""
    logger.info("Checking available base images...")
    
    # Detect runtime
    if not runtime:
        try:
            runtime, _ = detect_container_runtime()
        except:
            runtime = "docker"  # Fallback
    
    required_images = [
        "python:3.11-alpine",
        "python:3.11-alpine3.19", 
        "node:18-alpine",
        "postgres:15-alpine",
        "redis:7-alpine",
        "rabbitmq:3-alpine",
        "clickhouse/clickhouse-server:23-alpine"
    ]
    
    available = []
    missing = []
    
    for image in required_images:
        cmd = [runtime, "images", "-q", image]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.stdout.strip():
            available.append(image)
        else:
            missing.append(image)
    
    logger.info(f" PASS:  Available images: {len(available)}")
    for img in available:
        logger.info(f"   - {img}")
    
    if missing:
        logger.warning(f" FAIL:  Missing images: {len(missing)}")
        for img in missing:
            logger.warning(f"   - {img}")
        logger.warning(f"\nTo fix: Wait for rate limit reset then run:")
        for img in missing:
            logger.warning(f"   {runtime} pull {img}")
    
    return len(missing) == 0


def build_all_services(runtime: Optional[str] = None):
    """Build all services using local cache."""
    services = [
        ("test-backend", "backend.Dockerfile"),
        ("test-auth", "auth.Dockerfile"),
        ("test-frontend", "frontend.Dockerfile")
    ]
    
    if not ensure_base_images(runtime):
        logger.error("Cannot build without base images. Please pull them when rate limit resets.")
        return False
    
    success = True
    for service, dockerfile in services:
        if not build_with_local_cache(service, dockerfile, runtime=runtime):
            success = False
            logger.error(f"Failed to build {service}")
    
    return success


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Build container images using local cache only")
    parser.add_argument("--service", help="Build specific service")
    parser.add_argument("--check-images", action="store_true", help="Just check base images")
    parser.add_argument("--runtime", choices=["docker", "podman"], help="Force specific runtime")
    
    args = parser.parse_args()
    
    if args.check_images:
        sys.exit(0 if ensure_base_images(args.runtime) else 1)
    elif args.service:
        sys.exit(0 if build_with_local_cache(args.service, f"{args.service}.Dockerfile", runtime=args.runtime) else 1)
    else:
        sys.exit(0 if build_all_services(args.runtime) else 1)