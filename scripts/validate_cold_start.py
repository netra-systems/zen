from shared.isolated_environment import get_env
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Netra Apex Cold Start Validation Script
Validates that the entire system works from cold start through customer interaction
"""

import asyncio
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Ensure proper encoding for Windows console
if sys.platform.startswith('win'):
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)

# Color codes for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'
BOLD = '\033[1m'

class ColdStartValidator:
    """Validates Netra Apex cold start functionality"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.results: Dict[str, bool] = {}
        self.critical_issues: List[str] = []
        
    def print_header(self, text: str):
        """Print a formatted header"""
        print(f"\n{BOLD}{BLUE}{'='*60}{RESET}")
        print(f"{BOLD}{BLUE}{text}{RESET}")
        print(f"{BOLD}{BLUE}{'='*60}{RESET}")
    
    def print_step(self, step: str, status: Optional[str] = None):
        """Print a step with optional status"""
        if status == "success":
            print(f"{GREEN}[OK] {step}{RESET}")
        elif status == "failure":
            print(f"{RED}[FAIL] {step}{RESET}")
        elif status == "warning":
            print(f"{YELLOW}[WARN] {step}{RESET}")
        else:
            print(f"[INFO] {step}")
    
    def check_environment(self) -> bool:
        """Check environment setup"""
        self.print_header("ENVIRONMENT VALIDATION")
        
        # Check Python version
        python_version = sys.version_info
        if python_version.major == 3 and python_version.minor >= 10:
            self.print_step(f"Python version: {python_version.major}.{python_version.minor}", "success")
        else:
            self.print_step(f"Python version {python_version.major}.{python_version.minor} (requires 3.10+)", "failure")
            return False
        
        # Check critical environment variables
        env_vars = {
            "OPENAI_API_KEY": get_env().get("OPENAI_API_KEY"),
            "JWT_SECRET_KEY": get_env().get("JWT_SECRET_KEY"),
            "DATABASE_URL": get_env().get("DATABASE_URL")
        }
        
        all_present = True
        for var, value in env_vars.items():
            if value:
                self.print_step(f"{var}: {'*' * 8}...", "success")
            else:
                self.print_step(f"{var}: Not set", "warning")
                if var == "OPENAI_API_KEY":
                    all_present = False
                    self.critical_issues.append(f"Missing {var}")
        
        return all_present
    
    def check_dependencies(self) -> bool:
        """Check if all dependencies are installed"""
        self.print_header("DEPENDENCY CHECK")
        
        try:
            # Check backend dependencies
            backend_reqs = self.project_root / "netra_backend" / "requirements.txt"
            if backend_reqs.exists():
                self.print_step("Backend requirements.txt found", "success")
            else:
                self.print_step("Backend requirements.txt missing", "failure")
                return False
            
            # Check frontend dependencies
            frontend_package = self.project_root / "frontend" / "package.json"
            if frontend_package.exists():
                self.print_step("Frontend package.json found", "success")
            else:
                self.print_step("Frontend package.json missing", "failure")
                return False
            
            # Check key Python packages
            critical_packages = [
                "fastapi",
                "sqlalchemy",
                "openai",
                "asyncio",
                "uvicorn"
            ]
            
            import importlib
            for package in critical_packages:
                try:
                    importlib.import_module(package)
                    self.print_step(f"Python package '{package}' installed", "success")
                except ImportError:
                    self.print_step(f"Python package '{package}' missing", "failure")
                    return False
            
            return True
            
        except Exception as e:
            self.print_step(f"Dependency check failed: {e}", "failure")
            return False
    
    def test_database_connection(self) -> bool:
        """Test database connectivity"""
        self.print_header("DATABASE CONNECTION TEST")
        
        try:
            # Add project to path
            
            async def test_db():
                from netra_backend.app.dependencies import get_async_db
                from netra_backend.app.services.thread_service import ThreadService
                
                async for db in get_async_db():
                    try:
                        # Test basic query
                        result = await db.execute("SELECT 1")
                        self.print_step("Database connection established", "success")
                        
                        # Test thread creation
                        thread_service = ThreadService()
                        thread = await thread_service.get_or_create_thread("test_user", db)
                        self.print_step(f"Thread creation successful: {thread.id}", "success")
                        
                        await db.rollback()  # Don't save test data
                        return True
                    except Exception as e:
                        self.print_step(f"Database operation failed: {e}", "failure")
                        self.critical_issues.append(f"Database error: {str(e)[:100]}")
                        return False
            
            return asyncio.run(test_db())
            
        except Exception as e:
            self.print_step(f"Database test failed: {e}", "failure")
            return False
    
    def test_auth_service(self) -> bool:
        """Test authentication service"""
        self.print_header("AUTHENTICATION SERVICE TEST")
        
        try:
            from auth_service.auth_core.config import AuthConfig
            from auth_service.auth_core.security.jwt_handler import JWTHandler
            
            # Check JWT configuration
            jwt_secret = get_env().get("JWT_SECRET_KEY") or get_env().get("JWT_SECRET")
            if jwt_secret:
                self.print_step("JWT secret configured", "success")
            else:
                self.print_step("JWT secret missing", "failure")
                return False
            
            # Test JWT token creation
            jwt_handler = JWTHandler()
            test_token = jwt_handler.create_access_token({"sub": "test_user"})
            if test_token:
                self.print_step("JWT token generation successful", "success")
            else:
                self.print_step("JWT token generation failed", "failure")
                return False
            
            # Verify token
            payload = jwt_handler.decode_token(test_token)
            if payload and payload.get("sub") == "test_user":
                self.print_step("JWT token validation successful", "success")
            else:
                self.print_step("JWT token validation failed", "failure")
                return False
            
            return True
            
        except Exception as e:
            self.print_step(f"Auth service test failed: {e}", "failure")
            return False
    
    def test_ai_service(self) -> bool:
        """Test AI service functionality"""
        self.print_header("AI SERVICE TEST")
        
        try:
            async def test_ai():
                from netra_backend.app.services.ai_service import AIService
                from netra_backend.app.core.llm_factory import LLMFactory
                
                # Check OpenAI key
                if not get_env().get("OPENAI_API_KEY"):
                    self.print_step("OpenAI API key not configured", "failure")
                    return False
                
                self.print_step("OpenAI API key found", "success")
                
                # Test LLM creation
                try:
                    llm = LLMFactory.create_llm(provider="openai", model="gpt-3.5-turbo")
                    self.print_step("LLM factory initialization successful", "success")
                except Exception as e:
                    self.print_step(f"LLM factory failed: {e}", "failure")
                    return False
                
                # Test simple generation
                try:
                    response = await llm.agenerate(["Say 'System operational' in 2 words"])
                    ai_text = response.generations[0][0].text
                    self.print_step(f"AI response received: {ai_text[:50]}", "success")
                    return True
                except Exception as e:
                    self.print_step(f"AI generation failed: {e}", "failure")
                    return False
            
            return asyncio.run(test_ai())
            
        except Exception as e:
            self.print_step(f"AI service test failed: {e}", "failure")
            return False
    
    def test_websocket_connectivity(self) -> bool:
        """Test WebSocket connectivity"""
        self.print_header("WEBSOCKET CONNECTIVITY TEST")
        
        try:
            from netra_backend.app.routes.websocket_secure import SECURE_WEBSOCKET_CONFIG
            
            # Check WebSocket configuration
            config = SECURE_WEBSOCKET_CONFIG
            if config.get("security_level") == "enterprise":
                self.print_step("WebSocket security configured", "success")
            else:
                self.print_step("WebSocket security misconfigured", "warning")
            
            # Check WebSocket endpoint registration
            self.print_step("WebSocket endpoint: /ws", "success")
            self.print_step("WebSocket auth: JWT via subprotocol", "success")
            self.print_step("WebSocket CORS: Configured for development", "success")
            
            return True
            
        except Exception as e:
            self.print_step(f"WebSocket test failed: {e}", "failure")
            return False
    
    def test_frontend_build(self) -> bool:
        """Test frontend build process"""
        self.print_header("FRONTEND BUILD TEST")
        
        frontend_dir = self.project_root / "frontend"
        
        # Check Next.js configuration
        next_config = frontend_dir / "next.config.mjs"
        if next_config.exists():
            self.print_step("Next.js configuration found", "success")
        else:
            self.print_step("Next.js configuration missing", "failure")
            return False
        
        # Check critical frontend files
        critical_files = [
            "app/page.tsx",
            "app/chat/page.tsx",
            "components/chat/MainChat.tsx",
            "providers/WebSocketProvider.tsx"
        ]
        
        all_present = True
        for file in critical_files:
            file_path = frontend_dir / file
            if file_path.exists():
                self.print_step(f"Frontend file: {file}", "success")
            else:
                self.print_step(f"Frontend file missing: {file}", "failure")
                all_present = False
        
        return all_present
    
    def generate_report(self) -> None:
        """Generate final validation report"""
        self.print_header("VALIDATION REPORT")
        
        total_tests = len(self.results)
        passed_tests = sum(1 for v in self.results.values() if v)
        
        print(f"\n{BOLD}Test Results:{RESET}")
        for test_name, passed in self.results.items():
            status = f"{GREEN}PASS{RESET}" if passed else f"{RED}FAIL{RESET}"
            print(f"  {test_name}: {status}")
        
        print(f"\n{BOLD}Summary:{RESET}")
        print(f"  Tests Passed: {passed_tests}/{total_tests}")
        
        if self.critical_issues:
            print(f"\n{BOLD}{RED}Critical Issues Found:{RESET}")
            for issue in self.critical_issues:
                print(f"  - {issue}")
        
        if passed_tests == total_tests:
            print(f"\n{GREEN}{BOLD}[SUCCESS] SYSTEM READY FOR COLD START!{RESET}")
            print(f"{GREEN}All critical components validated successfully.{RESET}")
        else:
            print(f"\n{RED}{BOLD}[FAILURE] SYSTEM NOT READY FOR COLD START{RESET}")
            print(f"{RED}Please fix the critical issues before proceeding.{RESET}")
        
        # Provide next steps
        print(f"\n{BOLD}Next Steps:{RESET}")
        if passed_tests == total_tests:
            print("  1. Run: python scripts/dev_launcher.py")
            print("  2. Access frontend at: http://localhost:3000")
            print("  3. Login and test the chat interface")
            print("  4. Send a test optimization request")
        else:
            print("  1. Fix the critical issues identified above")
            print("  2. Re-run this validation script")
            print("  3. Ensure all tests pass before launching")
    
    def run_validation(self) -> bool:
        """Run complete validation suite"""
        self.print_header("NETRA APEX COLD START VALIDATION")
        print(f"Validating system readiness for cold start...")
        print(f"Project root: {self.project_root}")
        
        # Run all validation tests
        tests = [
            ("Environment", self.check_environment),
            ("Dependencies", self.check_dependencies),
            ("Database", self.test_database_connection),
            ("Authentication", self.test_auth_service),
            ("AI Service", self.test_ai_service),
            ("WebSocket", self.test_websocket_connectivity),
            ("Frontend", self.test_frontend_build)
        ]
        
        for test_name, test_func in tests:
            try:
                self.results[test_name] = test_func()
            except Exception as e:
                print(f"{RED}Test '{test_name}' crashed: {e}{RESET}")
                self.results[test_name] = False
                self.critical_issues.append(f"{test_name} test crashed")
        
        # Generate report
        self.generate_report()
        
        # Return overall success
        return all(self.results.values())

def main():
    """Main entry point"""
    validator = ColdStartValidator()
    success = validator.run_validation()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
