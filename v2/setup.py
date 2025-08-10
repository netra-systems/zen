#!/usr/bin/env python3
"""
Netra AI Platform - Quick Setup
One-command setup for developers
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    """Quick setup entry point"""
    print("\n🚀 Netra AI Platform - Quick Setup\n")
    print("This will install and configure your development environment.")
    print("Please ensure you have Python 3.9+ and Node.js 18+ installed.\n")
    
    response = input("Continue with setup? (y/n): ")
    if response.lower() != 'y':
        print("Setup cancelled.")
        return
    
    # Run the main installer
    installer_path = Path(__file__).parent / "install_dev_env.py"
    
    if not installer_path.exists():
        print("Error: install_dev_env.py not found!")
        print("Please ensure you're running this from the project root directory.")
        sys.exit(1)
    
    # Execute the installer
    try:
        subprocess.run([sys.executable, str(installer_path)], check=True)
    except subprocess.CalledProcessError:
        print("\n⚠️  Setup encountered some issues.")
        print("Please check the output above and resolve any errors.")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n⚠️  Setup interrupted.")
        sys.exit(1)

if __name__ == "__main__":
    main()