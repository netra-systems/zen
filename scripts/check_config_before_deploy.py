#!/usr/bin/env python3
"""
Pre-deployment Configuration Validation Script

This script validates configuration before deployment to prevent
configuration-related issues in production.
"""

import sys
import os

# Fix Unicode encoding issues on Windows - MUST be done early
if sys.platform == "win32":
    import io
    # Set UTF-8 for subprocess and all Python I/O
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    os.environ['PYTHONUTF8'] = '1'
    
    # Force Windows console to use UTF-8
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleCP(65001)
        kernel32.SetConsoleOutputCP(65001)
    except Exception:
        pass
    
    # Reconfigure stdout/stderr for UTF-8
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import argparse
import difflib

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from netra_backend.app.core.config_dependencies import ConfigDependencyMap, ConfigImpactLevel
from shared.isolated_environment import get_env
from netra_backend.app.core.configuration.base import get_unified_config


class ConfigurationChecker:
    """Pre-deployment configuration validation"""
    
    def __init__(self, environment: str = "staging", verbose: bool = False):
        self.environment = environment
        self.verbose = verbose
        self.errors = []
        self.warnings = []
        self.info = []
        
    def check_missing_configs(self) -> List[str]:
        """Check for missing critical configurations"""
        missing = []
        env = get_env()
        
        # Get all required configs
        required_configs = ConfigDependencyMap.get_required_configs()
        
        for config_key, metadata in required_configs.items():
            value = env.get(config_key)
            
            if not value and not metadata.get("fallback_allowed", False):
                missing.append(config_key)
                self.errors.append(f"Missing critical config: {config_key}")
                if self.verbose:
                    impact = metadata.get("deletion_impact", "Unknown impact")
                    print(f"  [FAIL] {config_key}: {impact}")
        
        return missing
    
    def validate_config_values(self) -> List[str]:
        """Validate configuration values against rules"""
        invalid = []
        env = get_env()
        
        # Check all configs that have validation rules
        all_configs = {
            **ConfigDependencyMap.CRITICAL_DEPENDENCIES,
            **ConfigDependencyMap.HIGH_PRIORITY_DEPENDENCIES,
            **ConfigDependencyMap.SERVICE_SPECIFIC_DEPENDENCIES
        }
        
        for config_key in all_configs:
            value = env.get(config_key)
            if value:
                is_valid, message = ConfigDependencyMap.validate_config_value(config_key, value)
                if not is_valid:
                    invalid.append(f"{config_key}: {message}")
                    self.errors.append(f"Invalid config value for {config_key}: {message}")
                    if self.verbose:
                        print(f"  [FAIL] {config_key}: {message}")
        
        return invalid
    
    def detect_breaking_changes(self) -> List[Dict[str, Any]]:
        """Detect potential breaking configuration changes"""
        breaking_changes = []
        
        # Load previous configuration if available
        prev_config_file = Path(f".config_snapshot_{self.environment}.json")
        current_config = self._snapshot_current_config()
        
        if prev_config_file.exists():
            with open(prev_config_file, "r") as f:
                prev_config = json.load(f)
            
            # Compare configurations
            for key in prev_config:
                if key not in current_config:
                    # Config was removed
                    can_delete, reason = ConfigDependencyMap.can_delete_config(key)
                    if not can_delete:
                        breaking_changes.append({
                            "type": "deletion",
                            "key": key,
                            "reason": reason,
                            "severity": "CRITICAL"
                        })
                        self.errors.append(f"Breaking change: Deletion of {key} - {reason}")
                elif prev_config[key] != current_config[key]:
                    # Config was modified
                    impact = ConfigDependencyMap.get_impact_analysis(key)
                    if impact["impact_level"] == ConfigImpactLevel.CRITICAL:
                        breaking_changes.append({
                            "type": "modification",
                            "key": key,
                            "old_value": self._sanitize_value(prev_config[key]),
                            "new_value": self._sanitize_value(current_config[key]),
                            "impact": impact["deletion_impact"],
                            "severity": "HIGH"
                        })
                        self.warnings.append(f"Critical config modified: {key}")
        
        return breaking_changes
    
    def test_configuration_isolated(self) -> bool:
        """Test configuration in isolation"""
        try:
            # Enable isolation
            env = get_env()
            env.enable_isolation()
            
            # Try to load configuration
            config = get_unified_config()
            
            # Basic validation
            if not config.database_url:
                self.errors.append("Configuration test failed: No database URL")
                return False
            
            if not config.jwt_secret_key:
                self.errors.append("Configuration test failed: No JWT secret")
                return False
            
            # Check consistency
            issues = ConfigDependencyMap.check_config_consistency(config.__dict__)
            if issues:
                for issue in issues:
                    if "CRITICAL" in issue:
                        self.errors.append(issue)
                    elif "WARNING" in issue:
                        self.warnings.append(issue)
                    else:
                        self.info.append(issue)
            
            return len([i for i in issues if "CRITICAL" in i]) == 0
            
        except Exception as e:
            self.errors.append(f"Configuration test failed: {str(e)}")
            return False
    
    def verify_backward_compatibility(self) -> bool:
        """Verify backward compatibility with existing code"""
        compatible = True
        
        # Test different access patterns
        env = get_env()
        
        # Pattern 1: Direct environment access
        critical_keys = ["DATABASE_URL", "JWT_SECRET_KEY", "ENVIRONMENT"]
        for key in critical_keys:
            if not env.get(key):
                alternatives = ConfigDependencyMap.get_alternatives(key)
                if not any(env.get(alt) for alt in alternatives):
                    self.warnings.append(f"Backward compatibility issue: {key} and alternatives missing")
                    compatible = False
        
        # Pattern 2: Config object access
        try:
            config = get_unified_config()
            required_attrs = ["database_url", "jwt_secret_key", "environment"]
            for attr in required_attrs:
                if not hasattr(config, attr):
                    self.warnings.append(f"Config object missing attribute: {attr}")
                    compatible = False
        except Exception as e:
            self.errors.append(f"Cannot load unified config: {str(e)}")
            compatible = False
        
        return compatible
    
    def check_environment_specific_requirements(self) -> bool:
        """Check environment-specific configuration requirements"""
        env = get_env()
        current_env = env.get("ENVIRONMENT", "development")
        
        if current_env == "production":
            # Production-specific checks
            required_prod_configs = [
                "DATABASE_URL",
                "REDIS_URL", 
                "JWT_SECRET_KEY",
                "SECRET_KEY",
                "ANTHROPIC_API_KEY"
            ]
            
            for config in required_prod_configs:
                if not env.get(config):
                    self.errors.append(f"Production requires {config}")
                    return False
            
            # Check for debug flags
            if env.get("DEBUG", "").lower() == "true":
                self.errors.append("DEBUG must be disabled in production")
                return False
                
        elif current_env == "staging":
            # Staging should mirror production
            if not env.get("DATABASE_URL"):
                self.warnings.append("Staging should have DATABASE_URL configured")
        
        return True
    
    def _snapshot_current_config(self) -> Dict[str, str]:
        """Create a snapshot of current configuration"""
        env = get_env()
        snapshot = {}
        
        # Get all relevant configs
        all_configs = {
            **ConfigDependencyMap.CRITICAL_DEPENDENCIES,
            **ConfigDependencyMap.HIGH_PRIORITY_DEPENDENCIES,
            **ConfigDependencyMap.SERVICE_SPECIFIC_DEPENDENCIES
        }
        
        for config_key in all_configs:
            value = env.get(config_key)
            if value:
                snapshot[config_key] = self._sanitize_value(value)
        
        return snapshot
    
    def _sanitize_value(self, value: Any) -> str:
        """Sanitize sensitive configuration values"""
        value_str = str(value)
        if any(s in value_str.lower() for s in ["secret", "key", "password", "token"]):
            return "***REDACTED***"
        return value_str[:50] + "..." if len(value_str) > 50 else value_str
    
    def save_snapshot(self):
        """Save current configuration snapshot for future comparison"""
        snapshot = self._snapshot_current_config()
        snapshot["timestamp"] = datetime.now().isoformat()
        snapshot["environment"] = self.environment
        
        snapshot_file = Path(f".config_snapshot_{self.environment}.json")
        with open(snapshot_file, "w") as f:
            json.dump(snapshot, f, indent=2)
        
        if self.verbose:
            print(f"Configuration snapshot saved to {snapshot_file}")
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive validation report"""
        return {
            "timestamp": datetime.now().isoformat(),
            "environment": self.environment,
            "validation_passed": len(self.errors) == 0,
            "errors": self.errors,
            "warnings": self.warnings,
            "info": self.info,
            "summary": {
                "error_count": len(self.errors),
                "warning_count": len(self.warnings),
                "info_count": len(self.info)
            }
        }
    
    def run_all_checks(self) -> bool:
        """Run all configuration checks"""
        print(f"[CHECK] Pre-deployment Configuration Check for {self.environment}")
        print("=" * 60)
        
        # 1. Check for missing critical configs
        print("\n1. Checking for missing critical configurations...")
        missing = self.check_missing_configs()
        if missing:
            print(f"   [FAIL] Missing {len(missing)} critical configs")
        else:
            print("   [PASS] All critical configs present")
        
        # 2. Validate configuration values
        print("\n2. Validating configuration values...")
        invalid = self.validate_config_values()
        if invalid:
            print(f"   [FAIL] {len(invalid)} invalid configuration values")
        else:
            print("   [PASS] All configuration values valid")
        
        # 3. Check for breaking changes
        print("\n3. Checking for breaking changes...")
        breaking = self.detect_breaking_changes()
        if breaking:
            print(f"   [WARN] {len(breaking)} potential breaking changes detected")
            if not self.confirm_breaking_changes(breaking):
                return False
        else:
            print("   [PASS] No breaking changes detected")
        
        # 4. Test configuration in isolation
        print("\n4. Testing configuration in isolation...")
        if self.test_configuration_isolated():
            print("   [PASS] Configuration tests passed")
        else:
            print("   [FAIL] Configuration tests failed")
        
        # 5. Verify backward compatibility
        print("\n5. Verifying backward compatibility...")
        if self.verify_backward_compatibility():
            print("   [PASS] Backward compatibility verified")
        else:
            print("   [WARN] Backward compatibility issues detected")
        
        # 6. Check environment-specific requirements
        print("\n6. Checking environment-specific requirements...")
        if self.check_environment_specific_requirements():
            print("   [PASS] Environment requirements met")
        else:
            print("   [FAIL] Environment requirements not met")
        
        # Generate report
        report = self.generate_report()
        
        print("\n" + "=" * 60)
        print(f"[SUMMARY] Validation Summary for {self.environment}:")
        print(f"   Errors: {report['summary']['error_count']}")
        print(f"   Warnings: {report['summary']['warning_count']}")
        print(f"   Info: {report['summary']['info_count']}")
        
        if report["validation_passed"]:
            print("\n[PASS] Configuration check PASSED")
            
            # Save snapshot for future comparison
            self.save_snapshot()
            return True
        else:
            print("\n[FAIL] Configuration check FAILED")
            print("\nErrors that must be fixed:")
            for error in self.errors:
                print(f"  * {error}")
            return False
    
    def confirm_breaking_changes(self, breaking_changes: List[Dict]) -> bool:
        """Prompt for confirmation of breaking changes"""
        print("\n[WARNING] BREAKING CHANGES DETECTED:")
        for change in breaking_changes:
            print(f"\n  Type: {change['type']}")
            print(f"  Key: {change['key']}")
            if change['type'] == 'deletion':
                print(f"  Reason: {change['reason']}")
            else:
                print(f"  Impact: {change.get('impact', 'Unknown')}")
            print(f"  Severity: {change['severity']}")
        
        if not sys.stdin.isatty():
            # Non-interactive mode
            print("\n[WARNING] Running in non-interactive mode. Breaking changes not confirmed.")
            return False
        
        response = input("\nDo you want to proceed with these breaking changes? (yes/no): ")
        return response.lower() in ["yes", "y"]


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Pre-deployment configuration validation")
    parser.add_argument(
        "--environment",
        choices=["development", "testing", "staging", "production"],
        default="staging",
        help="Target environment"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "--save-report",
        help="Save validation report to file"
    )
    
    args = parser.parse_args()
    
    # Set environment
    os.environ["ENVIRONMENT"] = args.environment
    
    # Run checks
    checker = ConfigurationChecker(
        environment=args.environment,
        verbose=args.verbose
    )
    
    success = checker.run_all_checks()
    
    # Save report if requested
    if args.save_report:
        report = checker.generate_report()
        with open(args.save_report, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\nReport saved to {args.save_report}")
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()