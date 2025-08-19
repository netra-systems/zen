# Setup Database URL Secret for Staging Environment
# This script creates/updates the database-url-staging secret in Google Secret Manager

param(
    [Parameter(Mandatory=$false)]
    [string]$DatabaseUrl = "",
    
    [Parameter(Mandatory=$false)]
    [switch]$UseDefaultUrl = $false
)

Write-Host "================================================" -ForegroundColor Blue
Write-Host "  STAGING DATABASE SECRET SETUP                " -ForegroundColor Blue  
Write-Host "================================================" -ForegroundColor Blue
Write-Host ""

# Configuration
$PROJECT_ID = "netra-staging"
$PROJECT_ID_NUMERICAL = "701982941522"
$SECRET_NAME = "database-url-staging"

# Ensure authentication
Write-Host "Checking authentication..." -ForegroundColor Yellow
$currentProject = gcloud config get-value project 2>$null
if ($currentProject -ne $PROJECT_ID) {
    Write-Host "Setting project to $PROJECT_ID..." -ForegroundColor Yellow
    gcloud config set project $PROJECT_ID --quiet
}

# Get or construct database URL
if (-not $DatabaseUrl) {
    if ($UseDefaultUrl) {
        # Use a default development URL for staging (not recommended for production)
        Write-Host "Using default database URL for staging..." -ForegroundColor Yellow
        $DatabaseUrl = "postgresql://netra_user:staging_password@localhost:5432/netra"
        Write-Host "  WARNING: Using default URL - replace with actual staging database!" -ForegroundColor Red
    } else {
        # Try to get from Terraform state or existing Cloud SQL instance
        Write-Host "Looking for Cloud SQL instance..." -ForegroundColor Yellow
        
        # List Cloud SQL instances
        $instances = gcloud sql instances list --format="value(name)" 2>$null
        if ($instances) {
            $instanceName = $instances | Select-Object -First 1
            Write-Host "  Found Cloud SQL instance: $instanceName" -ForegroundColor Green
            
            # Get instance details
            $instanceIp = gcloud sql instances describe $instanceName --format="value(ipAddresses[0].ipAddress)" 2>$null
            
            if ($instanceIp) {
                Write-Host "  Instance IP: $instanceIp" -ForegroundColor Green
                
                # Check if we have the password in existing secrets
                $dbPasswordExists = gcloud secrets describe netra-db-password --project=$PROJECT_ID_NUMERICAL 2>$null
                if ($dbPasswordExists) {
                    Write-Host "  Found existing database password secret" -ForegroundColor Green
                    $dbPassword = gcloud secrets versions access latest --secret=netra-db-password --project=$PROJECT_ID_NUMERICAL 2>$null
                    
                    if ($dbPassword) {
                        $DatabaseUrl = "postgresql://netra_user:$dbPassword@$instanceIp:5432/netra"
                        Write-Host "  Constructed database URL from Cloud SQL instance" -ForegroundColor Green
                    }
                }
            }
        }
        
        if (-not $DatabaseUrl) {
            Write-Host ""
            Write-Host "Could not auto-detect database URL." -ForegroundColor Yellow
            Write-Host "Please provide the database URL manually:" -ForegroundColor Yellow
            Write-Host "  Example: .\setup-staging-database-secret.ps1 -DatabaseUrl 'postgresql://user:pass@host:5432/netra'" -ForegroundColor Cyan
            exit 1
        }
    }
}

Write-Host ""
Write-Host "Database URL configured (connection string hidden for security)" -ForegroundColor Green

# Check if secret exists
Write-Host ""
Write-Host "Checking if secret exists..." -ForegroundColor Yellow
$secretExists = gcloud secrets describe $SECRET_NAME --project=$PROJECT_ID_NUMERICAL 2>$null

if ($secretExists) {
    Write-Host "  Secret exists, updating with new version..." -ForegroundColor Yellow
    
    # Create new version
    echo $DatabaseUrl | gcloud secrets versions add $SECRET_NAME --data-file=- --project=$PROJECT_ID_NUMERICAL
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ Secret updated successfully" -ForegroundColor Green
    } else {
        Write-Host "  Failed to update secret!" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "  Secret does not exist, creating..." -ForegroundColor Yellow
    
    # Create secret
    gcloud secrets create $SECRET_NAME --project=$PROJECT_ID_NUMERICAL --replication-policy="automatic"
    
    if ($LASTEXITCODE -eq 0) {
        # Add initial version
        echo $DatabaseUrl | gcloud secrets versions add $SECRET_NAME --data-file=- --project=$PROJECT_ID_NUMERICAL
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  ✓ Secret created successfully" -ForegroundColor Green
        } else {
            Write-Host "  Failed to add secret version!" -ForegroundColor Red
            exit 1
        }
    } else {
        Write-Host "  Failed to create secret!" -ForegroundColor Red
        exit 1
    }
}

# Grant access to Cloud Run service account
Write-Host ""
Write-Host "Granting access to Cloud Run service account..." -ForegroundColor Yellow

$serviceAccount = "netra-cloudrun@$PROJECT_ID.iam.gserviceaccount.com"
gcloud secrets add-iam-policy-binding $SECRET_NAME `
    --member="serviceAccount:$serviceAccount" `
    --role="roles/secretmanager.secretAccessor" `
    --project=$PROJECT_ID_NUMERICAL `
    --quiet

if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✓ Access granted to $serviceAccount" -ForegroundColor Green
} else {
    Write-Host "  Warning: Could not grant access (may already exist)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "================================================" -ForegroundColor Green
Write-Host "  DATABASE SECRET SETUP COMPLETED              " -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
Write-Host ""
Write-Host "The database URL secret has been configured in Google Secret Manager." -ForegroundColor Cyan
Write-Host "The Cloud Run deployment will now be able to access it." -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Run: .\deploy-staging-reliable.ps1" -ForegroundColor Cyan
Write-Host "  2. The backend will use the database URL from Secret Manager" -ForegroundColor Cyan
Write-Host ""