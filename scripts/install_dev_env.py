#!/usr/bin/env python3
"""
Netra AI Platform - Development Environment Installer
Orchestrates focused installer modules following 450-line/8-function limits.
CRITICAL: All functions MUST be  <= 8 lines, file  <= 300 lines.
"""

import platform
import sys
from pathlib import Path
from typing import List

# Add scripts directory to path for imports
script_dir = Path(__file__).parent

from config_setup import run_complete_configuration_setup
from dependency_installer import run_complete_dependency_installation
from env_checker import run_full_environment_check
from installer_types import (
    InstallerConfig,
    InstallerResult,
    VersionRequirements,
    create_installer_config,
    create_version_requirements,
)


class Colors:
    """Terminal colors for installer output"""
    HEADER = '\033[95m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

class DevEnvironmentInstaller:
    """Main installer orchestrating focused modules"""
    
    def __init__(self):
        self.config = create_installer_config()
        self.requirements = create_version_requirements()
        self.all_errors: List[str] = []
        self.all_warnings: List[str] = []
        self.all_messages: List[str] = []

    def print_header(self, text: str) -> None:
        """Print formatted header"""
        print(f"\n{Colors.HEADER}{'='*60}{Colors.ENDC}")
        print(f"{Colors.HEADER}{Colors.BOLD}{text.center(60)}{Colors.ENDC}")
        print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}\n")

    def print_step(self, text: str) -> None:
        """Print step indicator"""
        print(f"{Colors.CYAN}> {text}{Colors.ENDC}")

    def print_success(self, text: str) -> None:
        """Print success message"""
        print(f"{Colors.GREEN}[+] {text}{Colors.ENDC}")

    def print_warning(self, text: str) -> None:
        """Print warning message"""
        print(f"{Colors.WARNING}[!] {text}{Colors.ENDC}")

    def print_error(self, text: str) -> None:
        """Print error message"""
        print(f"{Colors.FAIL}[x] {text}{Colors.ENDC}")

    def print_info(self, text: str) -> None:
        """Print info message"""
        print(f"  {text}")

    def process_result(self, result: InstallerResult, step_name: str) -> None:
        """Process installer result and update state"""
        self.all_messages.extend(result.messages)
        self.all_errors.extend(result.errors)
        self.all_warnings.extend(result.warnings)
        
        if result.success:
            self.print_success(f"{step_name} completed successfully")
        else:
            self.print_error(f"{step_name} failed")

    def display_result_details(self, result: InstallerResult) -> None:
        """Display detailed results from installer operations"""
        for message in result.messages:
            self.print_success(message)
        
        for warning in result.warnings:
            self.print_warning(warning)
        
        for error in result.errors:
            self.print_error(error)

    def run_environment_check(self) -> bool:
        """Run environment prerequisites check"""
        self.print_step("Checking system prerequisites...")
        result = run_full_environment_check(self.config, self.requirements)
        self.process_result(result, "Environment check")
        self.display_result_details(result)
        return result.success

    def run_dependency_installation(self) -> bool:
        """Run complete dependency installation"""
        self.print_step("Installing dependencies...")
        result = run_complete_dependency_installation(self.config)
        self.process_result(result, "Dependency installation")
        self.display_result_details(result)
        return result.success

    def run_configuration_setup(self) -> bool:
        """Run configuration and finalization setup"""
        self.print_step("Setting up configuration...")
        result = run_complete_configuration_setup(self.config)
        self.process_result(result, "Configuration setup")
        self.display_result_details(result)
        return result.success

    def print_system_info(self) -> None:
        """Print system information"""
        print(f"Platform: {platform.system()} {platform.machine()}")
        print(f"Python: {sys.version}")
        print(f"Project: {self.config.project_root}")
        print()

    def print_final_summary(self) -> None:
        """Print installation summary and next steps"""
        self.print_header("Installation Summary")
        
        if self.all_messages:
            self.print_success("Installation completed with:")
            for message in self.all_messages[-5:]:  # Show last 5 messages
                self.print_info(f"  [U+2022] {message}")
        
        self.show_warnings_and_errors()

    def show_warnings_and_errors(self) -> None:
        """Display warnings and errors summary"""
        if self.all_warnings:
            print(f"\n{Colors.WARNING}Warnings:{Colors.ENDC}")
            for warning in self.all_warnings[-3:]:  # Show last 3
                self.print_info(f"  [U+2022] {warning}")
        
        if self.all_errors:
            print(f"\n{Colors.FAIL}Errors:{Colors.ENDC}")
            for error in self.all_errors[-3:]:  # Show last 3
                self.print_info(f"  [U+2022] {error}")

    def print_next_steps(self) -> None:
        """Print next steps for user"""
        print(f"\n{Colors.CYAN}{'='*60}{Colors.ENDC}\n")
        
        if not self.all_errors:
            print(f"{Colors.GREEN}{Colors.BOLD}[+] Installation completed!{Colors.ENDC}\n")
            self.show_success_next_steps()
        else:
            print(f"{Colors.WARNING}[!] Installation completed with issues{Colors.ENDC}\n")
            self.show_troubleshooting_steps()

    def show_success_next_steps(self) -> None:
        """Show next steps for successful installation"""
        print("Next steps:")
        if self.config.is_windows:
            print("  1. Run: start_dev.bat")
        else:
            print("  1. Run: ./start_dev.sh")
        
        print("  2. Open: http://localhost:3000")
        print("  3. Update .env file with your API keys")

    def show_troubleshooting_steps(self) -> None:
        """Show troubleshooting steps for failed installation"""
        print("Please address the errors above and try again.")
        print("For help, consult the README.md or CLAUDE.md files.")
        print("\nAlternative commands:")
        print("  [U+2022] Quick test: python test_runner.py --mode quick")
        print("  [U+2022] Backend only: python run_server.py")
        print("  [U+2022] Frontend only: cd frontend && npm run dev")

    def run(self) -> bool:
        """Run complete installation orchestration"""
        self.print_header("Netra AI Platform - Dev Environment Setup")
        self.print_system_info()
        
        # Step 1: Environment Check
        self.print_header("Step 1: Environment Prerequisites")
        env_success = self.run_environment_check()
        
        if not env_success:
            self.print_error("Environment prerequisites not met")
            return False
        
        # Step 2: Dependency Installation
        self.print_header("Step 2: Dependency Installation")
        deps_success = self.run_dependency_installation()
        
        # Step 3: Configuration Setup
        self.print_header("Step 3: Configuration & Testing")
        config_success = self.run_configuration_setup()
        
        # Final Summary
        self.print_final_summary()
        self.print_next_steps()
        
        return env_success and not self.all_errors



def main() -> None:
    """Main entry point for installer"""
    installer = DevEnvironmentInstaller()
    
    try:
        success = installer.run()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}Installation interrupted{Colors.ENDC}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.FAIL}Unexpected error: {e}{Colors.ENDC}")
        sys.exit(1)


if __name__ == "__main__":
    main()