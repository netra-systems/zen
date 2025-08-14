#!/bin/bash
# Quick Start Script for Terraform Development Database (Unix/Linux/Mac)
# This script automates the setup of the development database infrastructure

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
GRAY='\033[0;90m'
NC='\033[0m' # No Color

echo -e "\n${CYAN}==================================================${NC}"
echo -e "${MAGENTA}   Netra Development Database Quick Start${NC}"
echo -e "${CYAN}==================================================${NC}"
echo ""

# Check if Docker is running
echo -e "${YELLOW}Checking Docker...${NC}"
if command -v docker &> /dev/null && docker info &> /dev/null; then
    echo -e "${GREEN}✓ Docker is running${NC}"
else
    echo -e "${RED}✗ Docker is not running or not installed${NC}"
    echo -e "${GRAY}  Please install/start Docker:${NC}"
    echo -e "${GRAY}  • Mac: https://www.docker.com/products/docker-desktop/${NC}"
    echo -e "${GRAY}  • Linux: sudo systemctl start docker${NC}"
    exit 1
fi

# Check if Terraform is installed
echo -e "${YELLOW}Checking Terraform...${NC}"
if command -v terraform &> /dev/null; then
    echo -e "${GREEN}✓ Terraform is installed${NC}"
else
    echo -e "${RED}✗ Terraform is not installed${NC}"
    echo -e "${YELLOW}  Installing Terraform...${NC}"
    
    # Detect OS
    OS="$(uname -s)"
    case "${OS}" in
        Linux*)
            # Install on Linux
            if command -v apt-get &> /dev/null; then
                # Debian/Ubuntu
                wget -O- https://apt.releases.hashicorp.com/gpg | gpg --dearmor | sudo tee /usr/share/keyrings/hashicorp-archive-keyring.gpg
                echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
                sudo apt update && sudo apt install terraform
            elif command -v yum &> /dev/null; then
                # RHEL/CentOS
                sudo yum install -y yum-utils
                sudo yum-config-manager --add-repo https://rpm.releases.hashicorp.com/RHEL/hashicorp.repo
                sudo yum -y install terraform
            else
                echo -e "${RED}Please install Terraform manually from:${NC}"
                echo "https://www.terraform.io/downloads"
                exit 1
            fi
            ;;
        Darwin*)
            # Install on Mac
            if command -v brew &> /dev/null; then
                brew tap hashicorp/tap
                brew install hashicorp/tap/terraform
            else
                echo -e "${YELLOW}Installing Homebrew first...${NC}"
                /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
                brew tap hashicorp/tap
                brew install hashicorp/tap/terraform
            fi
            ;;
        *)
            echo -e "${RED}Unsupported OS: ${OS}${NC}"
            echo "Please install Terraform manually from:"
            echo "https://www.terraform.io/downloads"
            exit 1
            ;;
    esac
    
    # Verify installation
    if command -v terraform &> /dev/null; then
        echo -e "${GREEN}✓ Terraform installed successfully${NC}"
    else
        echo -e "${RED}Failed to install Terraform${NC}"
        exit 1
    fi
fi

echo ""
echo -e "${YELLOW}Initializing Terraform...${NC}"
terraform init

if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to initialize Terraform${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}Creating development database infrastructure...${NC}"
echo -e "${GRAY}This will create:${NC}"
echo -e "${GRAY}  • PostgreSQL 14 database on port 5432${NC}"
echo -e "${GRAY}  • Redis 7 cache on port 6379${NC}"
echo -e "${GRAY}  • ClickHouse analytics on ports 8123/9000${NC}"
echo -e "${GRAY}  • Persistent data volumes${NC}"
echo -e "${GRAY}  • Auto-generated .env.development.local file${NC}"
echo ""

read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Setup cancelled${NC}"
    exit 0
fi

echo ""
terraform apply -auto-approve

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}==================================================${NC}"
    echo -e "${GREEN}✓ Development Database Setup Complete!${NC}"
    echo -e "${GREEN}==================================================${NC}"
    echo ""
    echo -e "${CYAN}Database is now running with:${NC}"
    echo "  • PostgreSQL: localhost:5432"
    echo "  • Redis: localhost:6379"
    echo "  • ClickHouse: localhost:8123 (HTTP) / 9000 (native)"
    echo ""
    echo -e "${CYAN}Configuration files created:${NC}"
    echo "  • ../.env.development.local (auto-loaded by dev_launcher)"
    echo "  • connection_info.txt (all credentials)"
    echo ""
    echo -e "${YELLOW}Next steps:${NC}"
    echo "  1. Go back to project root: cd .."
    echo "  2. Start the application: python dev_launcher.py"
    echo ""
    echo -e "${YELLOW}To manage the database:${NC}"
    echo "  • View status: ./manage.sh status"
    echo "  • View logs: ./manage.sh logs"
    echo "  • Stop database: ./manage.sh stop"
    echo "  • Connect to DB: ./manage.sh connect"
    echo ""
else
    echo ""
    echo -e "${RED}✗ Setup failed. Please check the error messages above.${NC}"
    echo ""
    echo -e "${YELLOW}Common issues:${NC}"
    echo -e "${GRAY}  • Docker not running - Start Docker${NC}"
    echo -e "${GRAY}  • Port already in use - Check if another database is running${NC}"
    echo -e "${GRAY}  • Insufficient resources - Check Docker settings${NC}"
    echo ""
    exit 1
fi