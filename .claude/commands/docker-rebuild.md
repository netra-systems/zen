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

### 1. Stop Target Containers
!echo "🔄 Stopping ${1:-all} containers..."
!if [ -z "$ARGUMENTS" ]; then docker compose down; else docker compose stop $ARGUMENTS; fi

### 2. Remove Old Images
!echo "🗑️ Removing old images for ${1:-all services}..."
!if [ -z "$ARGUMENTS" ]; then docker compose down --rmi local; else for service in $ARGUMENTS; do docker compose rm -s -f $service && docker rmi -f $(docker compose config | grep -A1 "^  $service:" | grep "image:" | cut -d: -f2 | tr -d ' ') 2>/dev/null || true; done; fi

### 3. Rebuild Without Cache
!echo "🏭 Building ${1:-all services} without cache..."
!if [ -z "$ARGUMENTS" ]; then docker compose build --no-cache; else docker compose build --no-cache $ARGUMENTS; fi

### 4. Start Fresh Containers
!echo "🚀 Starting ${1:-all} containers..."
!if [ -z "$ARGUMENTS" ]; then docker compose up -d; else docker compose up -d $ARGUMENTS; fi

### 5. Health Status Check
!echo "🧑‍⚕️ Checking health status..."
!sleep 5
!docker compose ps

## Usage Examples
- `/docker-rebuild` - Rebuild all services
- `/docker-rebuild backend` - Rebuild only backend
- `/docker-rebuild auth frontend` - Rebuild auth and frontend