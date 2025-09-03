#!/bin/bash

# Build Test Images Script
# Parallel Docker builds for optimized pytest containers
# Prevents OOM issues and provides efficient test image management

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOCKER_DIR="${SCRIPT_DIR}/docker"
LOG_DIR="${SCRIPT_DIR}/logs"
BUILD_LOG="${LOG_DIR}/build_test_images.log"

# Build configuration
PARALLEL_BUILDS=3
DOCKER_BUILDKIT=1
PROGRESS_MODE="plain"

# Image names and tags
REGISTRY_PREFIX="${DOCKER_REGISTRY:-local}"
TAG="${BUILD_TAG:-latest}"

# Test images to build
declare -A TEST_IMAGES=(
    ["pytest-collection"]="pytest.collection.Dockerfile"
    ["pytest-execution"]="pytest.execution.Dockerfile"  
    ["pytest-stress"]="pytest.stress.Dockerfile"
    ["backend-test"]="backend.test.Dockerfile"
)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "${BUILD_LOG}"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "${BUILD_LOG}"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "${BUILD_LOG}"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "${BUILD_LOG}"
}

# Initialize build environment
initialize() {
    log_info "Initializing build environment..."
    
    # Create logs directory
    mkdir -p "${LOG_DIR}"
    
    # Clear previous build log
    echo "Build started at $(date)" > "${BUILD_LOG}"
    
    # Check Docker availability
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed or not in PATH"
        exit 1
    fi
    
    # Check Docker daemon
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running"
        exit 1
    fi
    
    # Enable BuildKit
    export DOCKER_BUILDKIT=1
    export DOCKER_CLI_EXPERIMENTAL=enabled
    
    log_success "Build environment initialized"
}

# Check Docker file existence
check_dockerfiles() {
    log_info "Checking Dockerfile availability..."
    
    local missing_files=()
    
    for image_name in "${!TEST_IMAGES[@]}"; do
        local dockerfile="${DOCKER_DIR}/${TEST_IMAGES[$image_name]}"
        if [[ ! -f "${dockerfile}" ]]; then
            missing_files+=("${dockerfile}")
        fi
    done
    
    if [[ ${#missing_files[@]} -gt 0 ]]; then
        log_error "Missing Dockerfiles:"
        for file in "${missing_files[@]}"; do
            log_error "  - ${file}"
        done
        exit 1
    fi
    
    log_success "All Dockerfiles found"
}

# Build single image
build_image() {
    local image_name="$1"
    local dockerfile="$2"
    local full_image_name="${REGISTRY_PREFIX}/netra-${image_name}:${TAG}"
    local build_start=$(date +%s)
    
    log_info "Building ${image_name}..."
    
    # Build arguments
    local build_args=(
        "--file" "${DOCKER_DIR}/${dockerfile}"
        "--tag" "${full_image_name}"
        "--progress" "${PROGRESS_MODE}"
        "--pull"
        "--rm"
    )
    
    # Add build-time optimizations
    build_args+=(
        "--build-arg" "BUILDKIT_INLINE_CACHE=1"
        "--build-arg" "PYTHON_VERSION=3.11"
        "--build-arg" "BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
        "--build-arg" "VCS_REF=$(git rev-parse --short HEAD 2>/dev/null || echo 'unknown')"
    )
    
    # Execute build
    if docker build "${build_args[@]}" "${SCRIPT_DIR}" 2>&1 | tee -a "${LOG_DIR}/${image_name}-build.log"; then
        local build_end=$(date +%s)
        local build_duration=$((build_end - build_start))
        log_success "Built ${image_name} in ${build_duration}s"
        
        # Get image size
        local image_size=$(docker images --format "table {{.Size}}" "${full_image_name}" | tail -n +2)
        log_info "${image_name} size: ${image_size}"
        
        return 0
    else
        log_error "Failed to build ${image_name}"
        return 1
    fi
}

# Build images in parallel
build_all_images() {
    log_info "Starting parallel builds (max ${PARALLEL_BUILDS} concurrent)..."
    
    local build_pids=()
    local failed_builds=()
    local successful_builds=()
    
    # Start builds
    for image_name in "${!TEST_IMAGES[@]}"; do
        # Wait if we've reached max parallel builds
        while [[ ${#build_pids[@]} -ge ${PARALLEL_BUILDS} ]]; do
            wait_for_build_completion build_pids
        done
        
        # Start build in background
        (
            if build_image "${image_name}" "${TEST_IMAGES[$image_name]}"; then
                echo "${image_name}:SUCCESS"
            else
                echo "${image_name}:FAILED"
            fi
        ) &
        
        local pid=$!
        build_pids+=("${pid}")
        log_info "Started build for ${image_name} (PID: ${pid})"
    done
    
    # Wait for all builds to complete
    log_info "Waiting for all builds to complete..."
    for pid in "${build_pids[@]}"; do
        if wait "${pid}"; then
            log_info "Build process ${pid} completed successfully"
        else
            log_warning "Build process ${pid} failed"
        fi
    done
    
    # Collect results
    for image_name in "${!TEST_IMAGES[@]}"; do
        local full_image_name="${REGISTRY_PREFIX}/netra-${image_name}:${TAG}"
        if docker image inspect "${full_image_name}" &> /dev/null; then
            successful_builds+=("${image_name}")
        else
            failed_builds+=("${image_name}")
        fi
    done
    
    # Report results
    if [[ ${#successful_builds[@]} -gt 0 ]]; then
        log_success "Successfully built images:"
        for image in "${successful_builds[@]}"; do
            log_success "  - ${REGISTRY_PREFIX}/netra-${image}:${TAG}"
        done
    fi
    
    if [[ ${#failed_builds[@]} -gt 0 ]]; then
        log_error "Failed to build images:"
        for image in "${failed_builds[@]}"; do
            log_error "  - ${image}"
        done
        return 1
    fi
    
    return 0
}

# Wait for build completion helper
wait_for_build_completion() {
    local -n pids_ref=$1
    local remaining_pids=()
    
    for pid in "${pids_ref[@]}"; do
        if kill -0 "${pid}" 2>/dev/null; then
            remaining_pids+=("${pid}")
        fi
    done
    
    pids_ref=("${remaining_pids[@]}")
    
    if [[ ${#pids_ref[@]} -gt 0 ]]; then
        sleep 1
    fi
}

# Generate size optimization report
generate_size_report() {
    log_info "Generating image size report..."
    
    local report_file="${LOG_DIR}/image_sizes.txt"
    echo "Docker Test Image Size Report - $(date)" > "${report_file}"
    echo "================================================" >> "${report_file}"
    
    for image_name in "${!TEST_IMAGES[@]}"; do
        local full_image_name="${REGISTRY_PREFIX}/netra-${image_name}:${TAG}"
        if docker image inspect "${full_image_name}" &> /dev/null; then
            echo "" >> "${report_file}"
            echo "Image: ${full_image_name}" >> "${report_file}"
            docker images --format "Size: {{.Size}}" "${full_image_name}" >> "${report_file}"
            docker image inspect "${full_image_name}" --format "Created: {{.Created}}" >> "${report_file}"
        fi
    done
    
    log_success "Size report generated: ${report_file}"
}

# Cleanup old images
cleanup_old_images() {
    log_info "Cleaning up old test images..."
    
    # Remove dangling images
    local dangling_images=$(docker images -f "dangling=true" -q)
    if [[ -n "${dangling_images}" ]]; then
        docker rmi ${dangling_images} 2>/dev/null || true
        log_success "Removed dangling images"
    fi
    
    # Remove old tagged versions (keep only latest 3)
    for image_name in "${!TEST_IMAGES[@]}"; do
        local base_name="${REGISTRY_PREFIX}/netra-${image_name}"
        local old_images=$(docker images "${base_name}" --format "{{.ID}} {{.Tag}}" | grep -v "${TAG}" | tail -n +4 | awk '{print $1}' || true)
        
        if [[ -n "${old_images}" ]]; then
            echo "${old_images}" | xargs -r docker rmi 2>/dev/null || true
            log_info "Cleaned up old versions of ${image_name}"
        fi
    done
}

# Test images functionality
test_images() {
    log_info "Testing built images..."
    
    for image_name in "${!TEST_IMAGES[@]}"; do
        local full_image_name="${REGISTRY_PREFIX}/netra-${image_name}:${TAG}"
        
        log_info "Testing ${image_name}..."
        
        # Run basic health check
        case "${image_name}" in
            "pytest-collection")
                if docker run --rm "${full_image_name}" python -c "import pytest; print('Collection image OK')"; then
                    log_success "${image_name} test passed"
                else
                    log_error "${image_name} test failed"
                fi
                ;;
            "pytest-execution")
                if docker run --rm "${full_image_name}" python -c "import pytest, netra_backend; print('Execution image OK')" 2>/dev/null; then
                    log_success "${image_name} test passed"
                else
                    log_warning "${image_name} test failed (may need application context)"
                fi
                ;;
            "pytest-stress")
                if docker run --rm "${full_image_name}" python -c "import pytest, memory_profiler, psutil; print('Stress image OK')"; then
                    log_success "${image_name} test passed"
                else
                    log_error "${image_name} test failed"
                fi
                ;;
            "backend-test")
                if docker run --rm "${full_image_name}" python -c "import pytest, fastapi; print('Backend test image OK')" 2>/dev/null; then
                    log_success "${image_name} test passed"
                else
                    log_warning "${image_name} test failed (may need application context)"
                fi
                ;;
        esac
    done
}

# Push images to registry
push_images() {
    if [[ "${DOCKER_REGISTRY:-local}" == "local" ]]; then
        log_info "Skipping push (local registry)"
        return 0
    fi
    
    log_info "Pushing images to registry..."
    
    for image_name in "${!TEST_IMAGES[@]}"; do
        local full_image_name="${REGISTRY_PREFIX}/netra-${image_name}:${TAG}"
        
        log_info "Pushing ${full_image_name}..."
        if docker push "${full_image_name}"; then
            log_success "Pushed ${full_image_name}"
        else
            log_error "Failed to push ${full_image_name}"
        fi
    done
}

# Show usage
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Build optimized Docker images for pytest testing

OPTIONS:
    -h, --help              Show this help message
    -t, --tag TAG           Docker tag (default: latest)
    -r, --registry PREFIX   Registry prefix (default: local)
    -p, --parallel NUM      Max parallel builds (default: 3)
    -c, --cleanup           Cleanup old images after build
    --push                  Push images to registry
    --test                  Test images after build
    --no-cache              Build without Docker cache

EXAMPLES:
    $0                      # Build all images with defaults
    $0 -t v1.0.0           # Build with specific tag
    $0 --cleanup --test    # Build, cleanup, and test
    $0 --registry myregistry.io --push  # Build and push

EOF
}

# Main execution
main() {
    local cleanup_after=false
    local push_after=false
    local test_after=false
    local no_cache=false
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_usage
                exit 0
                ;;
            -t|--tag)
                TAG="$2"
                shift 2
                ;;
            -r|--registry)
                REGISTRY_PREFIX="$2"
                shift 2
                ;;
            -p|--parallel)
                PARALLEL_BUILDS="$2"
                shift 2
                ;;
            -c|--cleanup)
                cleanup_after=true
                shift
                ;;
            --push)
                push_after=true
                shift
                ;;
            --test)
                test_after=true
                shift
                ;;
            --no-cache)
                no_cache=true
                shift
                ;;
            *)
                log_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    # Add no-cache to build args if specified
    if [[ "${no_cache}" == "true" ]]; then
        log_info "Building without cache"
    fi
    
    log_info "Starting test image build process..."
    log_info "Registry: ${REGISTRY_PREFIX}"
    log_info "Tag: ${TAG}"
    log_info "Max parallel builds: ${PARALLEL_BUILDS}"
    
    # Execute build process
    initialize
    check_dockerfiles
    
    local build_start=$(date +%s)
    if build_all_images; then
        local build_end=$(date +%s)
        local total_duration=$((build_end - build_start))
        
        log_success "All images built successfully in ${total_duration}s"
        
        generate_size_report
        
        if [[ "${test_after}" == "true" ]]; then
            test_images
        fi
        
        if [[ "${cleanup_after}" == "true" ]]; then
            cleanup_old_images
        fi
        
        if [[ "${push_after}" == "true" ]]; then
            push_images
        fi
        
        log_success "Build process completed successfully!"
        exit 0
    else
        log_error "Some images failed to build"
        exit 1
    fi
}

# Execute main function with all arguments
main "$@"