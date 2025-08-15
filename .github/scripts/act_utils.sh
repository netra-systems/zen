#!/bin/bash

# ACT Utility Functions for GitHub Actions Workflows
# Provides common functions for detecting ACT environment and creating mock data

# Function to detect if running in ACT
is_act_environment() {
    local act_detected="false"
    
    # Check for ACT environment variable
    if [[ "${ACT}" == "true" || "${ACT_DETECTION}" == "true" ]]; then
        act_detected="true"
    fi
    
    # Check for common ACT indicators
    if [[ -n "${ACT}" || "${GITHUB_ACTIONS}" == "true" && "${CI}" == "true" && -z "${GITHUB_SERVER_URL}" ]]; then
        act_detected="true"
    fi
    
    echo "${act_detected}"
}

# Function to print ACT debug information
print_act_debug() {
    if [[ "$(is_act_environment)" == "true" ]]; then
        echo "🧪 ACT LOCAL RUN DETECTED"
        echo "Debug: ACT environment variables:"
        env | grep -E "^(ACT|GITHUB_|CI)" | sort || true
        echo "=========================="
    fi
}

# Function to create mock HTTP response for ACT
mock_http_response() {
    local url="$1"
    local expected_status="${2:-200}"
    local response_time="${3:-$((RANDOM % 500 + 100))}"  # Random 100-600ms
    
    if [[ "$(is_act_environment)" == "true" ]]; then
        echo "🧪 ACT MOCK HTTP: ${url} -> ${expected_status} (${response_time}ms)"
        echo "${expected_status},$(echo "scale=3; ${response_time}/1000" | bc -l)"
    else
        # Real HTTP request
        curl -s -o /dev/null -w "%{http_code},%{time_total}" "$url" --max-time 30
    fi
}

# Function to create mock JSON data
create_mock_json() {
    local file_path="$1"
    local data_type="$2"
    
    case "$data_type" in
        "health_check")
            cat > "$file_path" << 'EOF'
{
  "status": "healthy",
  "timestamp": "2024-01-15T12:00:00Z",
  "services": {
    "database": {"status": "healthy", "response_time": 45},
    "cache": {"status": "healthy", "hit_rate": 0.95},
    "storage": {"status": "healthy", "free_space": "85%"}
  },
  "act_mock": true
}
EOF
            ;;
        "workflow_runs")
            cat > "$file_path" << 'EOF'
{
  "total_count": 25,
  "workflow_runs": [
    {
      "id": 1001,
      "name": "CI Pipeline",
      "conclusion": "success", 
      "status": "completed",
      "created_at": "2024-01-15T10:00:00Z",
      "updated_at": "2024-01-15T10:15:00Z"
    },
    {
      "id": 1002,
      "name": "Test Suite",
      "conclusion": "success",
      "status": "completed", 
      "created_at": "2024-01-15T11:00:00Z",
      "updated_at": "2024-01-15T11:08:00Z"
    },
    {
      "id": 1003,
      "name": "Deploy Staging",
      "conclusion": "failure",
      "status": "completed",
      "created_at": "2024-01-15T12:00:00Z", 
      "updated_at": "2024-01-15T12:05:00Z"
    }
  ],
  "act_mock": true
}
EOF
            ;;
        "architecture_health")
            cat > "$file_path" << 'EOF'
{
  "timestamp": "2024-01-15T12:00:00Z",
  "metrics": {
    "compliance_scores": {
      "overall_compliance": 85.5,
      "file_size_compliance": 90.0,
      "function_complexity_compliance": 82.0,
      "type_safety_compliance": 88.0
    },
    "violation_counts": {
      "total_violations": 15,
      "file_size_violations": 3,
      "function_complexity_violations": 8,
      "duplicate_types": 2,
      "test_stubs": 2
    }
  },
  "files_analyzed": 125,
  "act_mock": true
}
EOF
            ;;
        *)
            echo "Unknown mock data type: $data_type"
            return 1
            ;;
    esac
    
    echo "🧪 Created mock ${data_type} data at: ${file_path}"
}

# Function to log ACT notifications instead of sending real ones
log_act_notification() {
    local service="$1"    # slack, discord, email, etc.
    local message="$2"
    local level="${3:-info}"  # info, warning, error
    
    local timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    local log_file="act_notifications_${service}.json"
    
    cat >> "$log_file" << EOF
{
  "timestamp": "$timestamp",
  "service": "$service", 
  "level": "$level",
  "message": "$message",
  "act_mock": true
}
EOF
    
    echo "🧪 ACT: Would send ${service} notification (${level}): ${message}"
    echo "📝 Logged to: ${log_file}"
}

# Function to skip external service calls in ACT
skip_external_service() {
    local service_name="$1"
    local alternative_action="$2"
    
    if [[ "$(is_act_environment)" == "true" ]]; then
        echo "🧪 ACT: Skipping ${service_name} (external service)"
        if [[ -n "$alternative_action" ]]; then
            echo "🔄 ACT: Running alternative: ${alternative_action}"
            eval "$alternative_action"
        fi
        return 0
    else
        return 1
    fi
}

# Function to create minimal mock dashboard
create_mock_dashboard() {
    local output_file="$1"
    local title="${2:-ACT Mock Dashboard}"
    local content="${3:-This is a mock dashboard for ACT local testing.}"
    
    cat > "$output_file" << EOF
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>${title}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
        .container { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .act-badge { background: #ff6b35; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; }
        .metric { display: inline-block; margin: 10px; padding: 10px; background: #e3f2fd; border-radius: 4px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🧪 ${title} <span class="act-badge">ACT LOCAL</span></h1>
        <p>${content}</p>
        <div class="metrics">
            <div class="metric">📊 Mock Metric 1: 85.5%</div>
            <div class="metric">🎯 Mock Metric 2: 15 items</div>
            <div class="metric">⚡ Mock Metric 3: 125 files</div>
        </div>
        <p><small>Generated for ACT local testing at $(date)</small></p>
    </div>
</body>
</html>
EOF
    
    echo "🧪 Created mock dashboard: ${output_file}"
}

# Export functions for use in workflows
export -f is_act_environment
export -f print_act_debug
export -f mock_http_response
export -f create_mock_json
export -f log_act_notification
export -f skip_external_service
export -f create_mock_dashboard