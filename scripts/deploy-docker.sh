#!/bin/bash

# DEPRECATION WARNING: This Docker deployment script is deprecated.
#
# WEEK 1 SSOT REMEDIATION (GitHub Issue #245): 
# This script is deprecated in favor of canonical Docker Compose usage.
#
# CANONICAL SOURCES:
#   - Development: docker-compose --profile dev up
#   - Testing: docker-compose --profile test up
#   - Staging GCP: scripts/deploy_to_gcp_actual.py --project netra-staging
#
# Migration Paths:
#   OLD: ./scripts/deploy-docker.sh -p dev -a up
#   NEW: docker-compose --profile dev up
#
#   OLD: ./scripts/deploy-docker.sh -p test -a up --build
#   NEW: docker-compose --profile test up --build
#
# This wrapper will be removed in Week 2 after validation of the transition.

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_color() {
    color=$1
    message=$2
    echo -e "${color}${message}${NC}"
}

# Show deprecation warning
show_deprecation_warning() {
    print_color $YELLOW "================================================================================"
    print_color $RED "🚨 DEPRECATION WARNING - WEEK 1 SSOT REMEDIATION"
    print_color $YELLOW "================================================================================"
    print_color $YELLOW "GitHub Issue #245: Deployment canonical source conflicts"
    echo ""
    print_color $YELLOW "This Docker deployment script is deprecated."
    echo ""
    print_color $GREEN "For local Docker development:"
    print_color $BLUE "  CANONICAL: docker-compose --profile dev up"
    echo ""
    print_color $GREEN "For local Docker testing:"
    print_color $BLUE "  CANONICAL: docker-compose --profile test up"
    echo ""
    print_color $GREEN "For GCP staging deployment:"
    print_color $BLUE "  CANONICAL: python scripts/deploy_to_gcp_actual.py --project netra-staging"
    echo ""
    print_color $YELLOW "================================================================================"
    echo ""
}

# Parse command line arguments to maintain compatibility
PROFILE="dev"
ACTION="up"
BUILD=""
EXTRA_ARGS=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -p|--profile)
            PROFILE="$2"
            shift 2
            ;;
        -a|--action)
            ACTION="$2"
            shift 2
            ;;
        -b|--build)
            BUILD="--build"
            shift
            ;;
        -d|--detach)
            EXTRA_ARGS="$EXTRA_ARGS -d"
            shift
            ;;
        *)
            EXTRA_ARGS="$EXTRA_ARGS $1"
            shift
            ;;
    esac
done

# Redirect to canonical docker-compose usage
redirect_to_docker_compose() {
    local profile=$1
    local action=$2
    local build_flag=$3
    local extra=$4
    
    if [[ "$action" == "up" ]]; then
        cmd="docker-compose --profile $profile up $build_flag $extra"
    elif [[ "$action" == "down" ]]; then
        cmd="docker-compose down -v"
    elif [[ "$action" == "build" ]]; then
        cmd="docker-compose --profile $profile build"
    elif [[ "$action" == "logs" ]]; then
        cmd="docker-compose logs --tail=50"
    else
        cmd="docker-compose --profile $profile $action $extra"
    fi
    
    print_color $BLUE "🔄 Redirecting to Docker Compose:"
    print_color $GREEN "   $cmd"
    echo ""
    
    # Execute the canonical command
    eval $cmd
    exit_code=$?
    
    if [[ $exit_code -eq 0 && "$action" == "up" ]]; then
        echo ""
        print_color $GREEN "✅ Services started successfully!"
        print_color $BLUE "   Frontend: http://localhost:3000"
        print_color $BLUE "   Backend API: http://localhost:8080"
        print_color $BLUE "   API Docs: http://localhost:8080/docs"
    fi
    
    return $exit_code
}

# Main execution
main() {
    show_deprecation_warning
    
    print_color $YELLOW "💡 HINT: For GCP staging deployment:"
    print_color $BLUE "   python scripts/deploy_to_gcp_actual.py --project netra-staging --build-local"
    echo ""
    
    redirect_to_docker_compose "$PROFILE" "$ACTION" "$BUILD" "$EXTRA_ARGS"
}

# Execute main function
main "$@"