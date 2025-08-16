"""
Environment Variable Validation Core Module
Validates all required environment variables and configurations.
"""

import os
import re
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from dotenv import load_dotenv


class EnvironmentValidatorCore:
    """Core environment variable validation logic."""
    
    def __init__(self):
        """Initialize core validator."""
        self.project_root = Path(__file__).parent.parent
        self.env_files = self._discover_env_files()
        self.required_vars = self._define_required_variables()
        
    async def validate_environment_variables(self) -> Dict[str, Any]:
        """Validate all environment variables."""
        results = {
            "status": "success",
            "env_files": {},
            "variables": {},
            "missing": [],
            "recommendations": []
        }
        
        self._load_environment_files(results)
        self._validate_required_variables(results)
        self._validate_security_keys(results)
        self._update_overall_status(results)
        
        return results
    
    def _discover_env_files(self) -> List[Path]:
        """Discover all .env files in project."""
        env_patterns = [".env", ".env.development", ".env.staging", ".env.production"]
        found_files = []
        
        for pattern in env_patterns:
            env_path = self.project_root / pattern
            if env_path.exists():
                found_files.append(env_path)
        
        return found_files
    
    def _define_required_variables(self) -> Dict[str, Dict[str, Any]]:
        """Define required environment variables with validation rules."""
        return {
            "DATABASE_URL": {
                "description": "PostgreSQL connection string",
                "pattern": r"postgresql\+asyncpg://.*",
                "critical": True
            },
            "GEMINI_API_KEY": {
                "description": "Google Gemini API key",
                "pattern": r"AIza[0-9A-Za-z-_]{35}",
                "critical": True
            },
            "GOOGLE_CLIENT_ID": {
                "description": "Google OAuth client ID",
                "pattern": r".*\.apps\.googleusercontent\.com",
                "critical": True
            },
            "GOOGLE_CLIENT_SECRET": {
                "description": "Google OAuth client secret",
                "pattern": r"GOCSPX-.*",
                "critical": True
            },
            "JWT_SECRET_KEY": {
                "description": "JWT signing secret (32+ chars)",
                "min_length": 32,
                "critical": True
            },
            "FERNET_KEY": {
                "description": "Fernet encryption key",
                "pattern": r"[A-Za-z0-9+/]+=*",
                "critical": True
            },
            "CLICKHOUSE_HOST": {
                "description": "ClickHouse server host",
                "critical": False
            },
            "LANGFUSE_PUBLIC_KEY": {
                "description": "Langfuse public key",
                "pattern": r"pk-lf-.*",
                "critical": False
            },
            "ENVIRONMENT": {
                "description": "Application environment",
                "allowed_values": ["development", "staging", "production"],
                "critical": True
            }
        }
    
    def _load_environment_files(self, results: Dict[str, Any]) -> None:
        """Load and validate .env files."""
        for env_file in self.env_files:
            file_result = self._validate_env_file(env_file)
            results["env_files"][str(env_file)] = file_result
            
            if file_result["exists"]:
                load_dotenv(env_file, override=False)
    
    def _validate_env_file(self, env_file: Path) -> Dict[str, Any]:
        """Validate individual .env file."""
        return {
            "exists": env_file.exists(),
            "readable": env_file.is_file() if env_file.exists() else False,
            "size": env_file.stat().st_size if env_file.exists() else 0,
            "variables_count": self._count_variables_in_file(env_file)
        }
    
    def _count_variables_in_file(self, env_file: Path) -> int:
        """Count variables in .env file."""
        if not env_file.exists():
            return 0
            
        try:
            with open(env_file) as f:
                lines = [line.strip() for line in f.readlines()]
                return len([line for line in lines if '=' in line and not line.startswith('#')])
        except Exception:
            return 0
    
    def _validate_required_variables(self, results: Dict[str, Any]) -> None:
        """Validate all required environment variables."""
        for var_name, config in self.required_vars.items():
            var_result = self._validate_single_variable(var_name, config)
            results["variables"][var_name] = var_result
            
            if not var_result["exists"] and config.get("critical", False):
                results["missing"].append(var_name)
    
    def _validate_single_variable(self, var_name: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate single environment variable."""
        value = os.getenv(var_name)
        
        return {
            "exists": value is not None,
            "value_length": len(value) if value else 0,
            "valid_format": self._validate_variable_format(value, config),
            "critical": config.get("critical", False),
            "description": config.get("description", "")
        }
    
    def _validate_variable_format(self, value: Optional[str], config: Dict[str, Any]) -> bool:
        """Validate variable format against configuration rules."""
        if not value:
            return False
            
        if "pattern" in config:
            return bool(re.match(config["pattern"], value))
        
        if "min_length" in config:
            return len(value) >= config["min_length"]
        
        if "allowed_values" in config:
            return value in config["allowed_values"]
        
        return True
    
    def _validate_security_keys(self, results: Dict[str, Any]) -> None:
        """Validate security key strength and format."""
        security_vars = ["JWT_SECRET_KEY", "FERNET_KEY", "SECRET_KEY"]
        
        for var_name in security_vars:
            if var_name in results["variables"] and results["variables"][var_name]["exists"]:
                self._check_security_key_strength(var_name, results)
    
    def _check_security_key_strength(self, var_name: str, results: Dict[str, Any]) -> None:
        """Check security key strength and add recommendations."""
        value = os.getenv(var_name, "")
        
        if len(value) < 32:
            results["recommendations"].append(f"{var_name} should be at least 32 characters")
        
        if "dev" in value.lower() or "test" in value.lower():
            results["recommendations"].append(f"{var_name} appears to be a development key")
    
    def _update_overall_status(self, results: Dict[str, Any]) -> None:
        """Update overall validation status."""
        if results["missing"]:
            results["status"] = "error"
            results["summary"] = f"{len(results['missing'])} critical variables missing"
        elif results["recommendations"]:
            results["status"] = "warning"
            results["summary"] = f"{len(results['recommendations'])} recommendations"
        else:
            results["status"] = "success"
            results["summary"] = "All environment variables validated"