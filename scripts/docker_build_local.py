#!/usr/bin/env python
"""
Docker Local Build Script - Prevents Docker Hub pulls
======================================================
This script ensures Docker builds use only local images and never pull from Docker Hub.

CRITICAL LEARNING: Docker hits rate limits when trying to pull base images during builds.
Solution: Use --pull never flag and ensure base images are cached locally.

Business Value: Prevents development blockage due to Docker Hub rate limits.
"""

import subprocess
import sys
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent

def build_with_local_cache(service_name: str, dockerfile: str, compose_file: str = "docker-compose.test.yml"):
    """
    Build Docker image using only local cache, no pulls from Docker Hub.
    
    Args:
        service_name: Name of the service to build
        dockerfile: Path to Dockerfile
        compose_file: Docker compose file to use
    """
    compose_path = PROJECT_ROOT / compose_file
    
    # Build with --pull never to prevent Docker Hub access
    cmd = [
        "docker-compose",
        "-f", str(compose_path),
        "build",
        "--pull", "never",  # CRITICAL: Never pull from Docker Hub
        "--no-cache",       # Fresh build but use local base images
        service_name
    ]
    
    logger.info(f"Building {service_name} with local cache only...")
    logger.info(f"Command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=PROJECT_ROOT)
        if result.returncode != 0:
            logger.error(f"Build failed: {result.stderr}")
            
            # Check if it's a missing base image
            if "pull access denied" in result.stderr or "not found" in result.stderr:
                logger.error("\n" + "="*60)
                logger.error("MISSING BASE IMAGE DETECTED!")
                logger.error("Docker is trying to pull from Docker Hub but we blocked it.")
                logger.error("Solutions:")
                logger.error("1. Pull the base image manually when not rate limited:")
                logger.error("   docker pull python:3.11-alpine")
                logger.error("   docker pull node:18-alpine")
                logger.error("2. Use existing cached images")
                logger.error("3. Build from a Dockerfile with FROM scratch")
                logger.error("="*60 + "\n")
            
            return False
        
        logger.info(f"✅ Successfully built {service_name} using local cache")
        return True
        
    except Exception as e:
        logger.error(f"Build error: {e}")
        return False


def ensure_base_images():
    """Check and report on available base images."""
    logger.info("Checking available base images...")
    
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
        cmd = ["docker", "images", "-q", image]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.stdout.strip():
            available.append(image)
        else:
            missing.append(image)
    
    logger.info(f"✅ Available images: {len(available)}")
    for img in available:
        logger.info(f"   - {img}")
    
    if missing:
        logger.warning(f"❌ Missing images: {len(missing)}")
        for img in missing:
            logger.warning(f"   - {img}")
        logger.warning("\nTo fix: Wait for rate limit reset then run:")
        for img in missing:
            logger.warning(f"   docker pull {img}")
    
    return len(missing) == 0


def build_all_services():
    """Build all services using local cache."""
    services = [
        ("test-backend", "backend.Dockerfile"),
        ("test-auth", "auth.Dockerfile"),
        ("test-frontend", "frontend.Dockerfile")
    ]
    
    if not ensure_base_images():
        logger.error("Cannot build without base images. Please pull them when rate limit resets.")
        return False
    
    success = True
    for service, dockerfile in services:
        if not build_with_local_cache(service, dockerfile):
            success = False
            logger.error(f"Failed to build {service}")
    
    return success


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Build Docker images using local cache only")
    parser.add_argument("--service", help="Build specific service")
    parser.add_argument("--check-images", action="store_true", help="Just check base images")
    
    args = parser.parse_args()
    
    if args.check_images:
        sys.exit(0 if ensure_base_images() else 1)
    elif args.service:
        sys.exit(0 if build_with_local_cache(args.service, f"{args.service}.Dockerfile") else 1)
    else:
        sys.exit(0 if build_all_services() else 1)