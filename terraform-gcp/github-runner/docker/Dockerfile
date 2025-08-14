# GitHub Actions warp-custom-default Runner Container
FROM ubuntu:22.04

# Build arguments
ARG RUNNER_VERSION=2.311.0
ARG BUILDX_VERSION=0.11.2

# Runtime arguments (provided at container start)
ENV GITHUB_ORG=""
ENV GITHUB_REPO=""
ENV GITHUB_TOKEN=""
ENV RUNNER_NAME="docker-runner"
ENV RUNNER_LABELS="docker,warp-custom-default,linux"
ENV RUNNER_GROUP="default"

# Install dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        jq \
        git \
        sudo \
        ca-certificates \
        gnupg \
        lsb-release \
        build-essential \
        libssl-dev \
        libffi-dev \
        python3 \
        python3-venv \
        python3-dev \
        python3-pip && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Docker CLI (for Docker-in-Docker or socket mounting)
RUN curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | \
    tee /etc/apt/sources.list.d/docker.list > /dev/null && \
    apt-get update && \
    apt-get install -y docker-ce-cli && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Docker buildx
RUN mkdir -p /usr/local/lib/docker/cli-plugins && \
    curl -SL https://github.com/docker/buildx/releases/download/v${BUILDX_VERSION}/buildx-v${BUILDX_VERSION}.linux-amd64 \
    -o /usr/local/lib/docker/cli-plugins/docker-buildx && \
    chmod +x /usr/local/lib/docker/cli-plugins/docker-buildx

# Create runner user
RUN useradd -m -s /bin/bash runner && \
    usermod -aG sudo runner && \
    echo "runner ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Switch to runner user
USER runner
WORKDIR /home/runner

# Download and extract GitHub Actions runner
RUN mkdir actions-runner && \
    cd actions-runner && \
    curl -o actions-runner.tar.gz -L \
    https://github.com/actions/runner/releases/download/v${RUNNER_VERSION}/actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz && \
    tar xzf actions-runner.tar.gz && \
    rm actions-runner.tar.gz && \
    sudo ./bin/installdependencies.sh

# Copy entrypoint script
COPY --chown=runner:runner entrypoint.sh /home/runner/entrypoint.sh
RUN chmod +x /home/runner/entrypoint.sh

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD pgrep -f "Runner.Listener" || exit 1

ENTRYPOINT ["/home/runner/entrypoint.sh"]