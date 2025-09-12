#!/usr/bin/env python3
"""
Frontend Build Script for Netra Apex AI Optimization Platform

Business Value: Ensures reliable frontend builds for staging and production deployment
Prevents $25K+ MRR loss from frontend availability issues and user access problems

Features:
- Multi-environment build configuration
- Build validation and optimization
- Error handling and recovery
- Integration with deployment pipeline

Each function  <= 8 lines, file  <= 300 lines.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional


class FrontendBuildError(Exception):
    """Raised when frontend build fails."""
    pass


class FrontendBuilder:
    """Enterprise-grade frontend build manager.
    
    Handles multi-environment builds with proper validation and optimization.
    """
    
    def __init__(self, project_root: Optional[Path] = None):
        """Initialize frontend builder with project configuration."""
        self.project_root = project_root or Path(__file__).parent.parent
        self.frontend_dir = self.project_root / "frontend"
        self.build_config = self._load_build_config()
        
    def _load_build_config(self) -> Dict[str, str]:
        """Load build configuration from environment and defaults."""
        return {
            "NODE_ENV": os.getenv("NODE_ENV", "production"),
            "ENVIRONMENT": os.getenv("ENVIRONMENT", "production"),
            "BUILD_TARGET": os.getenv("BUILD_TARGET", "production"),
            "NODE_OPTIONS": "--max-old-space-size=4096"
        }
        
    def validate_prerequisites(self) -> None:
        """Validate build prerequisites and dependencies."""
        if not self.frontend_dir.exists():
            raise FrontendBuildError(f"Frontend directory not found: {self.frontend_dir}")
            
        package_json = self.frontend_dir / "package.json"
        if not package_json.exists():
            raise FrontendBuildError("package.json not found in frontend directory")
            
        # Check Node.js and npm
        try:
            subprocess.run(["node", "--version"], check=True, capture_output=True)
            subprocess.run(["npm", "--version"], check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise FrontendBuildError("Node.js or npm not available")
    
    def clean_build_artifacts(self) -> None:
        """Clean previous build artifacts to ensure fresh build."""
        cleanup_dirs = [".next", "dist", "out", "build"]
        
        for dir_name in cleanup_dirs:
            dir_path = self.frontend_dir / dir_name
            if dir_path.exists():
                shutil.rmtree(dir_path)
                print(f"[U+1F9F9] Cleaned {dir_name} directory")
    
    def install_dependencies(self) -> None:
        """Install frontend dependencies with proper configuration."""
        print("[U+1F4E6] Installing frontend dependencies...")
        
        cmd = ["npm", "ci", "--production=false"]
        result = subprocess.run(
            cmd,
            cwd=self.frontend_dir,
            env={**os.environ, **self.build_config},
            check=True
        )
        
        if result.returncode != 0:
            raise FrontendBuildError("Failed to install dependencies")
    
    def run_type_check(self) -> None:
        """Run TypeScript type checking."""
        print(" SEARCH:  Running TypeScript type check...")
        
        try:
            subprocess.run(
                ["npm", "run", "type-check"],
                cwd=self.frontend_dir,
                env={**os.environ, **self.build_config},
                check=True
            )
        except subprocess.CalledProcessError as e:
            print(f" WARNING: [U+FE0F] Type check completed with warnings: {e}")
            # Don't fail build on type warnings in staging
            if self.build_config["ENVIRONMENT"] == "production":
                raise FrontendBuildError("Type check failed in production build")
    
    def build_application(self) -> None:
        """Build the frontend application."""
        print(f"[U+1F528] Building application for {self.build_config['ENVIRONMENT']}...")
        
        result = subprocess.run(
            ["npm", "run", "build"],
            cwd=self.frontend_dir,
            env={**os.environ, **self.build_config}
        )
        
        if result.returncode != 0:
            raise FrontendBuildError("Frontend build failed")
    
    def validate_build_output(self) -> None:
        """Validate that build produced required output files."""
        print(" PASS:  Validating build output...")
        
        # Check for Next.js build directory
        next_dir = self.frontend_dir / ".next"
        if next_dir.exists():
            build_manifest = next_dir / "build-manifest.json"
            if not build_manifest.exists():
                print(" WARNING: [U+FE0F] Warning: build-manifest.json not found")
            return
            
        # Check for alternative build outputs
        alt_dirs = ["dist", "out", "build"]
        for dir_name in alt_dirs:
            if (self.frontend_dir / dir_name).exists():
                print(f" PASS:  Found build output in {dir_name}")
                return
                
        raise FrontendBuildError("No build output directory found")
    
    def generate_build_report(self) -> Dict[str, str]:
        """Generate build report for monitoring and debugging."""
        report = {
            "environment": self.build_config["ENVIRONMENT"],
            "node_env": self.build_config["NODE_ENV"],
            "build_target": self.build_config["BUILD_TARGET"],
            "timestamp": str(subprocess.check_output(["date"], text=True).strip()),
            "status": "success"
        }
        
        # Add output directory info
        for dir_name in [".next", "dist", "out", "build"]:
            dir_path = self.frontend_dir / dir_name
            if dir_path.exists():
                report["output_directory"] = dir_name
                break
                
        return report
    
    def build(self, clean: bool = True, validate: bool = True) -> Dict[str, str]:
        """Execute complete frontend build process."""
        print("[U+1F680] Starting Netra Frontend Build Process...")
        
        try:
            self.validate_prerequisites()
            
            if clean:
                self.clean_build_artifacts()
                
            self.install_dependencies()
            
            if validate:
                self.run_type_check()
                
            self.build_application()
            self.validate_build_output()
            
            report = self.generate_build_report()
            print(" CELEBRATION:  Frontend build completed successfully!")
            return report
            
        except Exception as e:
            print(f" FAIL:  Frontend build failed: {e}")
            raise FrontendBuildError(f"Build process failed: {e}")


def main():
    """Main entry point for frontend build script."""
    parser = argparse.ArgumentParser(description="Build Netra Frontend")
    parser.add_argument("--environment", default="production", 
                       choices=["development", "staging", "production"],
                       help="Build environment")
    parser.add_argument("--no-clean", action="store_true",
                       help="Skip cleaning build artifacts")
    parser.add_argument("--no-validate", action="store_true", 
                       help="Skip type checking")
    parser.add_argument("--output-report", 
                       help="Path to write build report JSON")
    
    args = parser.parse_args()
    
    # Set environment variables from arguments
    os.environ["ENVIRONMENT"] = args.environment
    os.environ["BUILD_TARGET"] = args.environment
    
    try:
        builder = FrontendBuilder()
        report = builder.build(
            clean=not args.no_clean,
            validate=not args.no_validate
        )
        
        if args.output_report:
            with open(args.output_report, 'w') as f:
                json.dump(report, f, indent=2)
                
        print(f" PASS:  Build report: {report}")
        
    except FrontendBuildError as e:
        print(f" FAIL:  Build failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f" FAIL:  Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()