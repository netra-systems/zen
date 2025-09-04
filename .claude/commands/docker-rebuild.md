---
allowed-tools: ["Bash"]
description: "Rebuild Docker containers from scratch"
argument-hint: "[service-name]"
---

# 🐳 Docker Rebuild - Clean State

Completely rebuild Docker containers for a fresh development environment.

## Target Service
**Service:** ${1:-all services}

## Execution Steps

### 1. Stop Existing Containers
!echo "🔄 Stopping existing containers..."
!docker compose down

### 2. Rebuild Without Cache
!echo "🏭 Building ${1:-all services} without cache..."
!docker compose build --no-cache $ARGUMENTS

### 3. Start Fresh Containers
!echo "🚀 Starting containers..."
!docker compose up -d $ARGUMENTS

### 4. Health Status Check
!echo "🧑‍⚕️ Checking health status..."
!sleep 5
!docker compose ps

## Usage Examples
- `/docker-rebuild` - Rebuild all services
- `/docker-rebuild backend` - Rebuild only backend
- `/docker-rebuild auth frontend` - Rebuild auth and frontend