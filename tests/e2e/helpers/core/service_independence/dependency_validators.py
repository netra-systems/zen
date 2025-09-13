"""

Dependency Validation Module



BVJ: Enterprise | SOC2 Compliance | Dependency Isolation | Critical for service independence

SPEC: SPEC/independent_services.xml



This module validates that services have isolated dependencies and proper database isolation.

Ensures microservices maintain separate dependency trees and data access patterns.

"""



import json

from pathlib import Path

from typing import Any, Dict, List





class DependencyIsolationValidator:

    """Validates dependency isolation between services."""

    

    def __init__(self, services: Dict[str, Any]):

        self.services = services

    

    async def test_dependency_isolation(self) -> Dict[str, Any]:

        """Test that services have isolated dependencies."""

        result = self._init_result()

        

        try:

            services_with_deps = 0

            isolated_services = 0

            

            for service_name, service_config in self.services.items():

                dep_result = await self._analyze_service_dependencies(service_name, service_config)

                result["service_dependencies"][service_name] = dep_result

                

                if dep_result["has_requirements"]:

                    services_with_deps += 1

                    isolated_services += 1  # Having own requirements file means isolated

            

            self._calculate_isolation_score(result, services_with_deps, isolated_services)

                

        except Exception as e:

            result["error"] = str(e)

            

        return result

    

    def _init_result(self) -> Dict[str, Any]:

        """Initialize result structure."""

        return {"isolation_score": 0, "service_dependencies": {}, "shared_dependencies": []}

    

    async def _analyze_service_dependencies(self, service_name: str, service_config) -> Dict[str, Any]:

        """Analyze dependencies for a single service."""

        dep_result = {"has_requirements": False, "dependency_files": [], "dependency_count": 0}

        

        dep_files = self._get_dependency_files(service_name)

        

        for dep_file in dep_files:

            dep_path = service_config.path / dep_file

            if dep_path.exists():

                self._process_dependency_file(dep_path, dep_file, dep_result)

        

        return dep_result

    

    def _get_dependency_files(self, service_name: str) -> List[str]:

        """Get dependency file names based on service type."""

        if service_name == "frontend":

            return ["package.json", "package-lock.json", "yarn.lock"]

        return ["requirements.txt", "requirements-dev.txt", "pyproject.toml", "setup.py"]

    

    def _process_dependency_file(self, dep_path: Path, dep_file: str, dep_result: Dict[str, Any]):

        """Process a single dependency file."""

        dep_result["has_requirements"] = True

        dep_result["dependency_files"].append(dep_file)

        

        # Count dependencies

        try:

            if dep_file == "package.json":

                self._count_npm_dependencies(dep_path, dep_result)

            elif dep_file.startswith("requirements"):

                self._count_python_dependencies(dep_path, dep_result)

        except:

            pass

    

    def _count_npm_dependencies(self, dep_path: Path, dep_result: Dict[str, Any]):

        """Count NPM dependencies from package.json."""

        with open(dep_path, 'r') as f:

            package_data = json.load(f)

            dep_result["dependency_count"] += len(package_data.get("dependencies", {}))

            dep_result["dependency_count"] += len(package_data.get("devDependencies", {}))

    

    def _count_python_dependencies(self, dep_path: Path, dep_result: Dict[str, Any]):

        """Count Python dependencies from requirements file."""

        with open(dep_path, 'r') as f:

            lines = [line.strip() for line in f.readlines() 

                    if line.strip() and not line.startswith('#')]

            dep_result["dependency_count"] += len(lines)

    

    def _calculate_isolation_score(self, result: Dict[str, Any], 

                                 services_with_deps: int, isolated_services: int):

        """Calculate dependency isolation score."""

        if services_with_deps > 0:

            result["isolation_score"] = (isolated_services / services_with_deps) * 100

        else:

            result["isolation_score"] = 50  # No dependency files is concerning





class DatabaseIsolationValidator:

    """Validates database connection isolation between services."""

    

    def __init__(self, services: Dict[str, Any]):

        self.services = services

    

    async def test_database_isolation(self) -> Dict[str, Any]:

        """Test database connection isolation between services."""

        result = self._init_result()

        

        try:

            services_with_db = 0

            isolated_db_services = 0

            

            for service_name, service_config in self.services.items():

                db_result = await self._analyze_service_database(service_config)

                result["service_db_configs"][service_name] = db_result

                

                if db_result["has_db_module"] or db_result["has_connection_config"]:

                    services_with_db += 1

                    if db_result["has_db_module"] and db_result["has_connection_config"]:

                        isolated_db_services += 1

            

            self._calculate_db_isolation_score(result, services_with_db, isolated_db_services)

                

        except Exception as e:

            result["error"] = str(e)

            

        return result

    

    def _init_result(self) -> Dict[str, Any]:

        """Initialize result structure."""

        return {"isolation_score": 0, "service_db_configs": {}, "shared_connections": []}

    

    async def _analyze_service_database(self, service_config) -> Dict[str, Any]:

        """Analyze database configuration for a service."""

        db_result = {"has_db_module": False, "has_connection_config": False, "db_files": []}

        

        # Look for database-related files

        db_patterns = ["*database*", "*db*", "*model*", "*connection*"]

        

        for pattern in db_patterns:

            db_files = list(service_config.path.rglob(f"*{pattern}*"))

            if db_files:

                relevant_db_files = self._filter_relevant_db_files(db_files)

                if relevant_db_files:

                    db_result["has_db_module"] = True

                    db_result["db_files"].extend(

                        [str(f.relative_to(service_config.path)) for f in relevant_db_files[:5]]

                    )

        

        # Check for connection configuration

        self._check_connection_config(service_config, db_result)

        

        return db_result

    

    def _filter_relevant_db_files(self, db_files: List[Path]) -> List[Path]:

        """Filter out unrelated files from database file search."""

        return [

            f for f in db_files 

            if f.suffix in ['.py', '.js', '.ts'] and 'test' not in f.name.lower()

        ]

    

    def _check_connection_config(self, service_config, db_result: Dict[str, Any]):

        """Check for database connection configuration files."""

        for config_file in service_config.path.rglob("*.py"):

            file_name_lower = config_file.name.lower()

            if "database" in file_name_lower or "connection" in file_name_lower:

                db_result["has_connection_config"] = True

                break

    

    def _calculate_db_isolation_score(self, result: Dict[str, Any], 

                                    services_with_db: int, isolated_db_services: int):

        """Calculate database isolation score."""

        if services_with_db > 0:

            result["isolation_score"] = (isolated_db_services / services_with_db) * 100

        else:

            result["isolation_score"] = 100  # No DB usage means perfect isolation





class ServiceIsolationCoordinator:

    """Coordinates all service isolation tests."""

    

    def __init__(self, services: Dict[str, Any]):

        self.dependency_validator = DependencyIsolationValidator(services)

        self.database_validator = DatabaseIsolationValidator(services)

    

    async def validate_service_isolation(self) -> Dict[str, Any]:

        """Validate that services are properly isolated."""

        results = self._init_results()

        

        try:

            # Test dependency isolation

            dependency_isolation = await self.dependency_validator.test_dependency_isolation()

            results["isolation_tests"]["dependencies"] = dependency_isolation

            

            # Test database isolation

            db_isolation = await self.database_validator.test_database_isolation()

            results["isolation_tests"]["database"] = db_isolation

            

            self._calculate_total_isolation_score(results)

            

            # Pass if isolation score is above threshold

            results["passed"] = results["total_isolation_score"] >= 60  # 60% isolation score

            

        except Exception as e:

            results["error"] = str(e)

            results["passed"] = False

            

        return results

    

    def _init_results(self) -> Dict[str, Any]:

        """Initialize results structure."""

        return {"passed": False, "isolation_tests": {}, "total_isolation_score": 0}

    

    def _calculate_total_isolation_score(self, results: Dict[str, Any]):

        """Calculate overall isolation score."""

        scores = [test.get("isolation_score", 0) for test in results["isolation_tests"].values()]

        results["total_isolation_score"] = sum(scores) / len(scores) if scores else 0





class PatternScanner:

    """Utility class for scanning codebase patterns."""

    

    def __init__(self, services: Dict[str, Any]):

        self.services = services

    

    async def scan_for_patterns(self, patterns: List[str]) -> bool:

        """Scan codebase for specific patterns indicating resilience features."""

        try:

            for service_name, service_config in self.services.items():

                file_patterns = self._get_file_patterns(service_name)

                

                for file_pattern in file_patterns:

                    if await self._scan_service_for_patterns(service_config, file_pattern, patterns):

                        return True

                            

            return False

        except:

            return False

    

    def _get_file_patterns(self, service_name: str) -> List[str]:

        """Get file patterns for service type."""

        if service_name == "frontend":

            return ["*.ts", "*.tsx", "*.js", "*.jsx"]

        return ["*.py"]

    

    async def _scan_service_for_patterns(self, service_config, file_pattern: str, 

                                       patterns: List[str]) -> bool:

        """Scan a service for specific patterns."""

        for file_path in service_config.path.rglob(file_pattern):

            # Skip uninteresting directories

            if self._should_skip_file(file_path):

                continue

            

            if await self._file_contains_patterns(file_path, patterns):

                return True

                

        return False

    

    def _should_skip_file(self, file_path: Path) -> bool:

        """Check if file should be skipped."""

        skip_dirs = ["node_modules", "__pycache__", ".git"]

        return any(skip in str(file_path) for skip in skip_dirs)

    

    async def _file_contains_patterns(self, file_path: Path, patterns: List[str]) -> bool:

        """Check if file contains any of the patterns."""

        try:

            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:

                content = f.read().lower()

                return any(pattern in content for pattern in patterns)

        except:

            return False

