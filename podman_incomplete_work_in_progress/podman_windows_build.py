#!/usr/bin/env python3
"""
Podman Build Helper for Windows
================================
Handles Podman builds on Windows by managing context size issues.
"""

import subprocess
import sys
import logging
import shutil
import tempfile
from pathlib import Path
from typing import Optional, List

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent


class PodmanWindowsBuilder:
    """
    Optimized Podman builder for Windows that handles large context issues.
    """
    
    def __init__(self):
        """Initialize the builder."""
        self.project_root = PROJECT_ROOT
        self.temp_dirs = []
    
    def cleanup(self):
        """Clean up temporary directories."""
        for temp_dir in self.temp_dirs:
            try:
                if temp_dir.exists():
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    logger.debug(f"Cleaned up {temp_dir}")
            except Exception as e:
                logger.warning(f"Failed to clean up {temp_dir}: {e}")
    
    def create_minimal_context(self, service_name: str) -> Optional[Path]:
        """
        Create minimal build context for a service.
        
        Args:
            service_name: Name of the service to build
            
        Returns:
            Path to temporary build context, or None on error
        """
        # Create temporary directory
        temp_dir = Path(tempfile.mkdtemp(prefix=f"podman_build_{service_name}_"))
        self.temp_dirs.append(temp_dir)
        logger.info(f"Created temporary build context: {temp_dir}")
        
        try:
            # Map service names to their source directories
            service_dirs = {
                "backend": "netra_backend",
                "auth": "auth_service",
                "frontend": "frontend"
            }
            
            # Determine which service we're building
            service_key = None
            for key in service_dirs:
                if key in service_name.lower():
                    service_key = key
                    break
            
            if not service_key:
                logger.error(f"Unknown service: {service_name}")
                return None
            
            # Copy only necessary files
            source_dir = self.project_root / service_dirs[service_key]
            if source_dir.exists():
                # Copy service directory
                dest_service_dir = temp_dir / service_dirs[service_key]
                shutil.copytree(
                    source_dir, 
                    dest_service_dir,
                    ignore=shutil.ignore_patterns(
                        '__pycache__', '*.pyc', '*.pyo', 
                        'node_modules', '.next', 'dist', 'build',
                        '*.log', '.pytest_cache', '.coverage'
                    )
                )
                logger.info(f"Copied {service_dirs[service_key]} to build context")
            
            # Copy shared directory if it exists
            shared_dir = self.project_root / "shared"
            if shared_dir.exists():
                dest_shared = temp_dir / "shared"
                shutil.copytree(
                    shared_dir,
                    dest_shared,
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '*.pyo')
                )
                logger.info("Copied shared directory to build context")
            
            # Copy requirements files to root for Dockerfile compatibility
            # Backend and auth need requirements.txt in root
            if service_key in ["backend", "auth"]:
                # Copy main requirements.txt to root
                src_req = self.project_root / "requirements.txt"
                if src_req.exists():
                    shutil.copy2(src_req, temp_dir / "requirements.txt")
                    logger.debug("Copied requirements.txt to root")
                
                # Each service is independent - no cross-service requirements needed
                
                # Also copy service-specific requirements if different
                service_req = source_dir / "requirements.txt"
                if service_req.exists() and service_req != src_req:
                    dest_file = temp_dir / service_dirs[service_key] / "requirements.txt"
                    shutil.copy2(service_req, dest_file)
                    logger.debug(f"Copied service-specific requirements.txt")
            
            # Frontend needs package.json
            elif service_key == "frontend":
                for req_file in ["package.json", "package-lock.json"]:
                    src_file = source_dir / req_file
                    if src_file.exists():
                        # Copy to service directory
                        dest_file = temp_dir / service_dirs[service_key] / req_file
                        shutil.copy2(src_file, dest_file)
                        # Also copy to root for some Dockerfiles
                        shutil.copy2(src_file, temp_dir / req_file)
                        logger.debug(f"Copied {req_file}")
            
            # Copy wait scripts
            scripts_to_copy = ["wait_for_db.py", "wait_for_auth.py"]
            scripts_dir = self.project_root / "scripts"
            dest_scripts = temp_dir / "scripts"
            dest_scripts.mkdir(exist_ok=True)
            
            for script in scripts_to_copy:
                src = scripts_dir / script
                if src.exists():
                    shutil.copy2(src, dest_scripts / script)
                    logger.debug(f"Copied script: {script}")
            
            # Copy Dockerfile
            dockerfile_name = f"{service_key}.Dockerfile"
            src_dockerfile = self.project_root / "docker" / dockerfile_name
            dest_dockerfile = temp_dir / "docker" / dockerfile_name
            
            if src_dockerfile.exists():
                dest_dockerfile.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_dockerfile, dest_dockerfile)
                logger.info(f"Copied Dockerfile: {dockerfile_name}")
            else:
                logger.error(f"Dockerfile not found: {src_dockerfile}")
                return None
            
            return temp_dir
            
        except Exception as e:
            logger.error(f"Failed to create minimal context: {e}")
            return None
    
    def build_service(
        self, 
        service_name: str,
        image_name: Optional[str] = None,
        no_cache: bool = False
    ) -> bool:
        """
        Build a service with Podman using minimal context.
        
        Args:
            service_name: Name of the service
            image_name: Docker image name (defaults to netra-{service_name})
            no_cache: Build without cache
            
        Returns:
            True if build succeeded
        """
        # Determine image name
        if not image_name:
            image_name = f"netra-{service_name}:latest"
        
        logger.info(f"Building {service_name} as {image_name}")
        
        # Create minimal context
        context_dir = self.create_minimal_context(service_name)
        if not context_dir:
            return False
        
        try:
            # Determine dockerfile path
            service_key = None
            for key in ["backend", "auth", "frontend"]:
                if key in service_name.lower():
                    service_key = key
                    break
            
            dockerfile = context_dir / "docker" / f"{service_key}.Dockerfile"
            
            if not dockerfile.exists():
                logger.error(f"Dockerfile not found: {dockerfile}")
                return False
            
            # Build command
            cmd = [
                "podman", "build",
                "-f", str(dockerfile),
                "-t", image_name
            ]
            
            if no_cache:
                cmd.append("--no-cache")
            
            # Add build context
            cmd.append(str(context_dir))
            
            logger.info(f"Executing: {' '.join(cmd)}")
            
            # Run build
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=context_dir  # Use temp dir as working directory
            )
            
            if result.returncode != 0:
                logger.error(f"Build failed:\n{result.stderr}")
                return False
            
            logger.info(f"✅ Successfully built {image_name}")
            return True
            
        except Exception as e:
            logger.error(f"Build error: {e}")
            return False
        finally:
            # Clean up is done in __del__ or manually
            pass
    
    def build_all(self) -> bool:
        """Build all services."""
        services = [
            ("test-backend", "netra-test-backend:latest"),
            ("test-auth", "netra-test-auth:latest"),
            ("test-frontend", "netra-test-frontend:latest")
        ]
        
        success = True
        for service_name, image_name in services:
            logger.info(f"\n{'='*60}")
            logger.info(f"Building {service_name}")
            logger.info(f"{'='*60}")
            
            if not self.build_service(service_name, image_name):
                logger.error(f"Failed to build {service_name}")
                success = False
            else:
                logger.info(f"✅ {service_name} built successfully")
        
        return success
    
    def __del__(self):
        """Clean up on deletion."""
        self.cleanup()


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Podman Windows Build Helper")
    parser.add_argument(
        "service",
        nargs="?",
        default="all",
        help="Service to build (backend, auth, frontend, or all)"
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Build without cache"
    )
    parser.add_argument(
        "--image",
        help="Custom image name"
    )
    
    args = parser.parse_args()
    
    builder = PodmanWindowsBuilder()
    
    try:
        if args.service == "all":
            success = builder.build_all()
        else:
            success = builder.build_service(
                args.service,
                args.image,
                args.no_cache
            )
        
        if success:
            logger.info("\n✅ Build completed successfully!")
            sys.exit(0)
        else:
            logger.error("\n❌ Build failed!")
            sys.exit(1)
    
    finally:
        builder.cleanup()


if __name__ == "__main__":
    main()