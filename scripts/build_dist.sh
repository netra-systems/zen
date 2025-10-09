#!/bin/bash
# Build distribution packages for Zen Orchestrator
# Supports both development builds and release builds with embedded credentials

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored messages
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"

cd "$PROJECT_DIR"

# Parse command line arguments
RELEASE_MODE=false
PUBLISH=false
VERSION=""
CREATE_TAG=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --release)
            RELEASE_MODE=true
            shift
            ;;
        --publish)
            PUBLISH=true
            shift
            ;;
        --version)
            VERSION="$2"
            shift 2
            ;;
        --tag)
            CREATE_TAG=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --release          Build for release (embed telemetry credentials)"
            echo "  --version VERSION  Update version in pyproject.toml before building"
            echo "  --tag              Create and push git tag (requires --version)"
            echo "  --publish          Publish to PyPI after building (requires --release)"
            echo "  -h, --help         Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                                    # Development build"
            echo "  $0 --release                          # Release build with credentials"
            echo "  $0 --release --version 1.0.10 --tag   # Full release with tag"
            echo "  $0 --release --publish                # Build and publish to PyPI"
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Validate options
if [[ "$PUBLISH" == true ]] && [[ "$RELEASE_MODE" == false ]]; then
    print_error "--publish requires --release"
    exit 1
fi

if [[ "$CREATE_TAG" == true ]] && [[ -z "$VERSION" ]]; then
    print_error "--tag requires --version"
    exit 1
fi

# Display build mode
if [[ "$RELEASE_MODE" == true ]]; then
    print_info "🚀 Building Zen Orchestrator RELEASE packages..."
else
    print_info "🔧 Building Zen Orchestrator development packages..."
fi
echo ""

# Update version if specified
if [[ -n "$VERSION" ]]; then
    print_info "Updating version to $VERSION..."
    sed -i.bak "s/^version = .*/version = \"$VERSION\"/" pyproject.toml
    rm -f pyproject.toml.bak
    print_success "Version updated"

    # Commit version change if creating tag
    if [[ "$CREATE_TAG" == true ]]; then
        print_info "Committing version change..."
        git add pyproject.toml
        git commit -m "version = \"$VERSION\"" || print_warning "No changes to commit"
    fi
    echo ""
fi

# Clean previous builds
print_info "Cleaning previous builds..."
rm -rf dist/ build/ *.egg-info
echo ""

# Install/upgrade build tools
print_info "Installing build tools..."
pip install --upgrade build twine
if [[ "$RELEASE_MODE" == true ]]; then
    pip install opentelemetry-sdk opentelemetry-exporter-gcp-trace google-cloud-trace
fi
echo ""

# Embed credentials for release builds
CREDENTIALS_EMBEDDED=false
if [[ "$RELEASE_MODE" == true ]]; then
    print_info "Embedding telemetry credentials for release..."

    if [[ -z "$COMMUNITY_CREDENTIALS" ]]; then
        print_warning "COMMUNITY_CREDENTIALS not set. Checking for credential file..."

        if [[ -n "$ZEN_COMMUNITY_TELEMETRY_FILE" ]] && [[ -f "$ZEN_COMMUNITY_TELEMETRY_FILE" ]]; then
            print_info "Using credentials from $ZEN_COMMUNITY_TELEMETRY_FILE"
        else
            print_error "No credentials found!"
            echo ""
            echo "Set credentials with:"
            echo "  export COMMUNITY_CREDENTIALS=\"<base64-encoded-json>\""
            echo "  OR"
            echo "  export ZEN_COMMUNITY_TELEMETRY_FILE=\"/path/to/credentials.json\""
            exit 1
        fi
    fi

    python scripts/embed_release_credentials.py
    CREDENTIALS_EMBEDDED=true
    print_success "Credentials embedded"
    echo ""
fi

# Build the package
print_info "Building package..."
python -m build
echo ""

# Verify telemetry in release builds
if [[ "$RELEASE_MODE" == true ]]; then
    print_info "Verifying telemetry in build..."
    pip install --force-reinstall dist/*.whl > /dev/null 2>&1
    TELEMETRY_STATUS=$(python -c "from zen.telemetry import telemetry_manager; print(telemetry_manager.is_enabled())" 2>/dev/null || echo "False")

    if [[ "$TELEMETRY_STATUS" == "True" ]]; then
        print_success "Telemetry verified: ENABLED"
    else
        print_error "Telemetry verification FAILED: $TELEMETRY_STATUS"
        print_warning "Package will be built but telemetry may not work"
    fi
    echo ""
fi

# Restore credentials file if embedded
if [[ "$CREDENTIALS_EMBEDDED" == true ]]; then
    print_info "Restoring runtime credential loader..."
    git checkout -- zen/telemetry/embedded_credentials.py
    echo ""
fi

# Check the distribution
print_info "Checking distribution..."
twine check dist/*
echo ""

# Show package info
print_success "Build complete!"
echo ""
echo "📦 Built packages:"
ls -lh dist/
echo ""
echo "📋 Package contents:"
tar -tzf dist/*.tar.gz | head -20
echo "... (showing first 20 files)"
echo ""

# Create and push tag if requested
if [[ "$CREATE_TAG" == true ]] && [[ -n "$VERSION" ]]; then
    print_info "Creating git tag v$VERSION..."
    git tag -a "v$VERSION" -m "Release version $VERSION" || {
        print_error "Failed to create tag. It may already exist."
        print_info "Delete existing tag with: git tag -d v$VERSION && git push origin :refs/tags/v$VERSION"
        exit 1
    }
    print_success "Tag created"

    print_info "Pushing to GitHub..."
    git push origin main
    git push origin "v$VERSION"
    print_success "Tag pushed"
    echo ""
fi

# Publish if requested
if [[ "$PUBLISH" == true ]]; then
    print_warning "Publishing to PyPI..."
    echo ""

    if [[ -z "$PYPI_API_TOKEN" ]]; then
        print_error "PYPI_API_TOKEN not set!"
        echo "Set it with: export PYPI_API_TOKEN=\"pypi-...\""
        echo "Or publish manually with: twine upload dist/*"
        exit 1
    fi

    TWINE_USERNAME=__token__ TWINE_PASSWORD="$PYPI_API_TOKEN" twine upload dist/*
    print_success "Published to PyPI!"
    echo ""
fi

# Show next steps
echo "🚀 Next steps:"
if [[ "$RELEASE_MODE" == false ]]; then
    echo "  Development build:"
    echo "    Test locally: pip install dist/*.whl"
    echo ""
    echo "  For release build:"
    echo "    $0 --release --version 1.0.10 --tag"
elif [[ "$PUBLISH" == false ]]; then
    echo "  Test locally: pip install dist/*.whl"
    echo "  Verify telemetry: python -c 'from zen.telemetry import telemetry_manager; print(telemetry_manager.is_enabled())'"
    echo "  Upload to TestPyPI: twine upload --repository testpypi dist/*"
    echo "  Upload to PyPI: $0 --release --publish"
    if [[ "$CREATE_TAG" == false ]]; then
        echo "  Create release tag: $0 --release --version $VERSION --tag"
    fi
else
    echo "  ✅ Release complete!"
    echo "  Verify on PyPI: https://pypi.org/project/netra-zen/"
    echo "  Test installation: pip install --upgrade netra-zen"
fi
