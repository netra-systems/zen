"""

Import Independence Validation Module



BVJ: Enterprise | SOC2 Compliance | Import Isolation | Critical for service independence

SPEC: SPEC/independent_services.xml



This module validates that services have no direct code dependencies between each other.

Ensures microservice independence through static analysis of import statements.

"""



import asyncio

import time

from dataclasses import dataclass

from pathlib import Path

from typing import Any, Dict, List, Set





@dataclass

class ServiceConfig:

    """Configuration for each microservice."""

    name: str

    path: Path

    entry_point: str

    required_files: List[str]

    forbidden_patterns: List[str]

    allowed_external_deps: Set[str]

    api_endpoints: List[str]





class ImportIndependenceValidator:

    """Validates import independence between microservices."""

    

    def __init__(self, project_root: Path):

        self.project_root = project_root

        self.services = self._init_service_configs()

    

    def _init_service_configs(self) -> Dict[str, ServiceConfig]:

        """Initialize service configurations."""

        return {

            "auth_service": ServiceConfig(

                name="auth_service",

                path=self.project_root / "auth_service",

                entry_point="main.py",

                required_files=["main.py", "requirements.txt", "auth_core/__init__.py"],

                forbidden_patterns=["from netra_backend.app.", "import app.", "from app ", "import app "],

                allowed_external_deps={"fastapi", "uvicorn", "sqlalchemy", "pydantic", "httpx"},

                api_endpoints=["/health", "/docs", "/openapi.json"]

            ),

            "main_backend": ServiceConfig(

                name="main_backend", 

                path=self.project_root / "app",

                entry_point="main.py",

                required_files=["main.py", "core/__init__.py"],

                forbidden_patterns=["from auth_service.", "from frontend."],

                allowed_external_deps={"fastapi", "uvicorn", "sqlalchemy", "pydantic", "httpx"},

                api_endpoints=["/health", "/docs", "/api/health"]

            ),

            "frontend": ServiceConfig(

                name="frontend",

                path=self.project_root / "frontend", 

                entry_point="package.json",

                required_files=["package.json", "next.config.ts", "app/layout.tsx"],

                forbidden_patterns=["from netra_backend./app/", "from netra_backend./auth_service/", "import('../app", "import('../auth_service"],

                allowed_external_deps={"next", "react", "axios", "fetch"},

                api_endpoints=["/api/health", "/"]

            )

        }

    

    async def validate_import_independence(self) -> Dict[str, Any]:

        """Validate that services have no direct imports between each other."""

        results = self._init_results()

        

        try:

            all_services_clean = True

            total_files_scanned = 0

            

            for service_name, service_config in self.services.items():

                print(f"  Scanning {service_name}...")

                service_result = await self._scan_service_imports(service_config)

                results["service_results"][service_name] = service_result

                

                total_files_scanned += service_result.get("files_scanned", 0)

                violations = service_result.get("violations", [])

                results["total_violations"] += len(violations)

                

                if violations:

                    all_services_clean = False

                    print(f"    Found {len(violations)} violations in {service_name}")

            

            self._update_scan_stats(results, total_files_scanned)

            results["passed"] = all_services_clean and total_files_scanned > 0

            

        except Exception as e:

            results["error"] = str(e)

            results["passed"] = False

            

        return results

    

    def _init_results(self) -> Dict[str, Any]:

        """Initialize results structure."""

        return {

            "passed": False,

            "service_results": {},

            "total_violations": 0,

            "scan_stats": {}

        }

    

    def _update_scan_stats(self, results: Dict[str, Any], total_files: int):

        """Update scan statistics."""

        results["scan_stats"] = {

            "total_files_scanned": total_files,

            "services_scanned": len(self.services),

            "clean_services": sum(1 for sr in results["service_results"].values() 

                                 if not sr.get("violations", []))

        }

    

    async def _scan_service_imports(self, service_config: ServiceConfig) -> Dict[str, Any]:

        """Scan a single service for forbidden imports."""

        result = self._init_scan_result()

        start_time = time.time()

        

        try:

            if not service_config.path.exists():

                self._add_missing_service_violation(result, service_config)

                return result

            

            file_patterns = self._get_file_patterns(service_config)

            await self._scan_files_for_patterns(service_config, file_patterns, result)

            result["scan_time"] = round(time.time() - start_time, 2)

            

        except Exception as e:

            self._add_scan_error_violation(result, e)

            

        return result

    

    def _init_scan_result(self) -> Dict[str, Any]:

        """Initialize scan result structure."""

        return {

            "violations": [],

            "files_scanned": 0,

            "scan_time": 0

        }

    

    def _add_missing_service_violation(self, result: Dict[str, Any], service_config: ServiceConfig):

        """Add violation for missing service directory."""

        result["violations"].append({

            "file": "SERVICE_MISSING",

            "pattern": "SERVICE_NOT_FOUND",

            "line": f"Service directory {service_config.path} does not exist"

        })

    

    def _get_file_patterns(self, service_config: ServiceConfig) -> List[str]:

        """Get file patterns based on service type."""

        if service_config.name == "frontend":

            return ["*.ts", "*.tsx", "*.js", "*.jsx"]

        return ["*.py"]

    

    async def _scan_files_for_patterns(self, service_config: ServiceConfig, 

                                     file_patterns: List[str], result: Dict[str, Any]):

        """Scan files for forbidden import patterns."""

        for pattern in file_patterns:

            for file_path in service_config.path.rglob(pattern):

                if self._should_skip_file(file_path):

                    continue

                    

                result["files_scanned"] += 1

                await self._scan_file_for_violations(file_path, service_config, result)

    

    def _should_skip_file(self, file_path: Path) -> bool:

        """Check if file should be skipped during scanning."""

        skip_dirs = ["node_modules", ".git", "__pycache__", ".next", "dist", "build"]

        return any(skip_dir in str(file_path) for skip_dir in skip_dirs)

    

    async def _scan_file_for_violations(self, file_path: Path, 

                                      service_config: ServiceConfig, result: Dict[str, Any]):

        """Scan a single file for forbidden import patterns."""

        try:

            lines = self._read_file_lines(file_path)

            

            for line_num, line in enumerate(lines, 1):

                line_clean = line.strip()

                

                if self._should_skip_line(line_clean):

                    continue

                    

                violation = self._check_line_for_violations(

                    file_path, line_num, line_clean, service_config

                )

                if violation:

                    result["violations"].append(violation)

                        

        except Exception as e:

            self._add_file_read_error(result, file_path, e)

    

    def _read_file_lines(self, file_path: Path) -> List[str]:

        """Read file lines safely."""

        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:

            return f.readlines()

    

    def _should_skip_line(self, line_clean: str) -> bool:

        """Check if line should be skipped."""

        if not line_clean:

            return True

        if line_clean.startswith('#') or line_clean.startswith('//'):

            return True

        if line_clean.startswith('"""') or line_clean.startswith("'''"):

            return True

        return False

    

    def _check_line_for_violations(self, file_path: Path, line_num: int, 

                                 line_clean: str, service_config: ServiceConfig) -> Dict[str, Any]:

        """Check line for import violations."""

        for forbidden_pattern in service_config.forbidden_patterns:

            if self._is_import_violation(line_clean, forbidden_pattern, file_path, service_config):

                return {

                    "file": str(file_path.relative_to(self.project_root)),

                    "line_number": line_num,

                    "pattern": forbidden_pattern,

                    "line": line_clean[:150]  # Truncate long lines

                }

        return None

    

    def _is_import_violation(self, line_clean: str, forbidden_pattern: str, 

                           file_path: Path, service_config: ServiceConfig) -> bool:

        """Check if line contains an import violation."""

        if forbidden_pattern not in line_clean:

            return False

            

        # Must be at start of line or after whitespace to be a real import

        pattern_start = forbidden_pattern.split('.')[0]

        if not (line_clean.startswith(pattern_start) or 

               line_clean.lstrip().startswith(pattern_start)):

            return False

            

        # Check for allowed exceptions

        return not self._is_allowed_exception(file_path, line_clean, service_config)

    

    def _add_file_read_error(self, result: Dict[str, Any], file_path: Path, error: Exception):

        """Add file read error to violations."""

        result["violations"].append({

            "file": str(file_path.relative_to(self.project_root)),

            "pattern": "FILE_READ_ERROR", 

            "line": f"Could not read file: {str(error)}"

        })

    

    def _add_scan_error_violation(self, result: Dict[str, Any], error: Exception):

        """Add scan error to violations."""

        result["violations"].append({

            "file": "SCAN_ERROR",

            "pattern": "EXCEPTION",

            "line": f"Error scanning service: {str(error)}"

        })



    def _is_allowed_exception(self, file_path: Path, line: str, service_config: ServiceConfig) -> bool:

        """Check if an import violation is an allowed exception."""

        file_path_str = str(file_path)

        

        # Allow documented sync imports in specific files

        if "main_db_sync.py" in file_path_str and "from netra_backend.app.db.models_postgres" in line:

            return True

            

        # Allow test files to import from other services for testing purposes

        is_test_file = self._is_test_file(file_path, file_path_str)

        if is_test_file:

            return True

            

        # Allow mock files and test utilities

        if self._is_mock_or_utility_file(file_path):

            return True

            

        return False

    

    def _is_test_file(self, file_path: Path, file_path_str: str) -> bool:

        """Check if file is a test file."""

        return (

            "test_" in str(file_path.name) or

            "/tests/" in file_path_str or

            "\\tests\\" in file_path_str or

            "_test.py" in str(file_path.name) or

            file_path.name.endswith("_test.py") or

            file_path.name.startswith("test_")

        )

    

    def _is_mock_or_utility_file(self, file_path: Path) -> bool:

        """Check if file is a mock or utility file."""

        mock_keywords = ["mock", "fixture", "conftest", "test_data", "test_helper"]

        return any(word in file_path.name.lower() for word in mock_keywords)

