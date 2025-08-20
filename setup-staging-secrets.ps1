# Setup All Required Secrets for Staging Environment
# This script creates/updates all required secrets in Google Secret Manager

param(
    [Parameter(Mandatory=$false)]
    [switch]$Force = $false,
    
    [Parameter(Mandatory=$false)]
    [string]$GeminiApiKey = "",
    
    [Parameter(Mandatory=$false)]
    [string]$JwtSecret = "",
    
    [Parameter(Mandatory=$false)]
    [string]$FernetKey = "",
    
    [Parameter(Mandatory=$false)]
    [string]$GoogleClientId = "",
    
    [Parameter(Mandatory=$false)]
    [string]$GoogleClientSecret = ""
)

Write-Host "================================================" -ForegroundColor Blue
Write-Host "  STAGING SECRETS SETUP                        " -ForegroundColor Blue  
Write-Host "================================================" -ForegroundColor Blue
Write-Host ""

# Configuration
$PROJECT_ID = "netra-staging"
$PROJECT_ID_NUMERICAL = "701982941522"
$REGION = "us-central1"

# Function to create or update a secret
function Set-Secret {
    param(
        [string]$SecretName,
        [string]$SecretValue,
        [bool]$Required = $true
    )
    
    if (-not $SecretValue -and $Required) {
        Write-Host "  ERROR: $SecretName is required but no value provided" -ForegroundColor Red
        return $false
    }
    
    if (-not $SecretValue) {
        Write-Host "  Skipping $SecretName (optional, no value provided)" -ForegroundColor Yellow
        return $true
    }
    
    Write-Host "  Setting up $SecretName..." -ForegroundColor Cyan
    
    # Check if secret exists
    $secretExists = gcloud secrets describe $SecretName --project=$PROJECT_ID_NUMERICAL 2>$null
    
    if ($secretExists) {
        # Update existing secret
        echo $SecretValue | gcloud secrets versions add $SecretName --data-file=- --project=$PROJECT_ID_NUMERICAL 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "    ✓ Updated successfully" -ForegroundColor Green
        } else {
            Write-Host "    ✗ Failed to update" -ForegroundColor Red
            return $false
        }
    } else {
        # Create new secret
        gcloud secrets create $SecretName --project=$PROJECT_ID_NUMERICAL --replication-policy="automatic" 2>$null
        if ($LASTEXITCODE -eq 0) {
            echo $SecretValue | gcloud secrets versions add $SecretName --data-file=- --project=$PROJECT_ID_NUMERICAL 2>$null
            if ($LASTEXITCODE -eq 0) {
                Write-Host "    ✓ Created successfully" -ForegroundColor Green
            } else {
                Write-Host "    ✗ Failed to add version" -ForegroundColor Red
                return $false
            }
        } else {
            Write-Host "    ✗ Failed to create" -ForegroundColor Red
            return $false
        }
    }
    
    # Grant access to Cloud Run service accounts
    $serviceAccounts = @(
        "netra-cloudrun@$PROJECT_ID.iam.gserviceaccount.com",
        "netra-staging-deploy@$PROJECT_ID.iam.gserviceaccount.com"
    )
    
    foreach ($sa in $serviceAccounts) {
        gcloud secrets add-iam-policy-binding $SecretName `
            --member="serviceAccount:$sa" `
            --role="roles/secretmanager.secretAccessor" `
            --project=$PROJECT_ID_NUMERICAL `
            --quiet 2>$null
    }
    
    return $true
}

# Ensure authentication
Write-Host "Checking authentication..." -ForegroundColor Yellow
$currentProject = gcloud config get-value project 2>$null
if ($currentProject -ne $PROJECT_ID) {
    Write-Host "Setting project to $PROJECT_ID..." -ForegroundColor Yellow
    gcloud config set project $PROJECT_ID --quiet
}

# Generate secrets if not provided
Write-Host ""
Write-Host "Preparing secrets..." -ForegroundColor Yellow

# Generate JWT secret if not provided
if (-not $JwtSecret) {
    Write-Host "  Generating JWT secret..." -ForegroundColor Cyan
    $bytes = New-Object byte[] 32
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    $JwtSecret = [System.Convert]::ToBase64String($bytes)
    Write-Host "    ✓ Generated 256-bit JWT secret" -ForegroundColor Green
}

# Generate Fernet key if not provided
if (-not $FernetKey) {
    Write-Host "  Generating Fernet key..." -ForegroundColor Cyan
    # Fernet keys are 32 bytes (256 bits) URL-safe base64 encoded
    $bytes = New-Object byte[] 32
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    $FernetKey = [System.Convert]::ToBase64String($bytes).Replace('+', '-').Replace('/', '_')
    Write-Host "    ✓ Generated Fernet encryption key" -ForegroundColor Green
}

# Prompt for required keys if not provided
if (-not $GeminiApiKey) {
    Write-Host ""
    Write-Host "GEMINI API KEY REQUIRED" -ForegroundColor Red
    Write-Host "Please provide your Gemini API key (required for LLM operations):" -ForegroundColor Yellow
    Write-Host "You can get one from: https://makersuite.google.com/app/apikey" -ForegroundColor Cyan
    $GeminiApiKey = Read-Host "Gemini API Key"
    
    if (-not $GeminiApiKey) {
        Write-Host "ERROR: Gemini API key is required for staging deployment" -ForegroundColor Red
        exit 1
    }
}

# Setup secrets
Write-Host ""
Write-Host "Setting up secrets in Google Secret Manager..." -ForegroundColor Yellow

$success = $true

# Required secrets
$success = $success -and (Set-Secret -SecretName "gemini-api-key-staging" -SecretValue $GeminiApiKey -Required $true)
$success = $success -and (Set-Secret -SecretName "jwt-secret-staging" -SecretValue $JwtSecret -Required $true)
$success = $success -and (Set-Secret -SecretName "fernet-key-staging" -SecretValue $FernetKey -Required $true)

# Optional OAuth secrets
$success = $success -and (Set-Secret -SecretName "google-client-id-staging" -SecretValue $GoogleClientId -Required $false)
$success = $success -and (Set-Secret -SecretName "google-client-secret-staging" -SecretValue $GoogleClientSecret -Required $false)

# Check if database secret exists
Write-Host ""
Write-Host "Checking database secret..." -ForegroundColor Yellow
$dbSecretExists = gcloud secrets describe "database-url-staging" --project=$PROJECT_ID_NUMERICAL 2>$null
if (-not $dbSecretExists) {
    Write-Host "  WARNING: database-url-staging does not exist!" -ForegroundColor Red
    Write-Host "  Run: .\setup-staging-database-secret.ps1" -ForegroundColor Yellow
} else {
    Write-Host "  ✓ database-url-staging exists" -ForegroundColor Green
}

if ($success) {
    Write-Host ""
    Write-Host "================================================" -ForegroundColor Green
    Write-Host "  SECRETS SETUP COMPLETED                      " -ForegroundColor Green
    Write-Host "================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "All required secrets have been configured in Google Secret Manager." -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Created/Updated secrets:" -ForegroundColor Yellow
    Write-Host "  - gemini-api-key-staging (REQUIRED)" -ForegroundColor Green
    Write-Host "  - jwt-secret-staging (REQUIRED)" -ForegroundColor Green
    Write-Host "  - fernet-key-staging (REQUIRED)" -ForegroundColor Green
    if ($GoogleClientId) {
        Write-Host "  - google-client-id-staging (optional)" -ForegroundColor Blue
    }
    if ($GoogleClientSecret) {
        Write-Host "  - google-client-secret-staging (optional)" -ForegroundColor Blue
    }
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "  1. Ensure database-url-staging exists (run setup-staging-database-secret.ps1 if needed)" -ForegroundColor Cyan
    Write-Host "  2. Run: .\deploy-staging-reliable.ps1" -ForegroundColor Cyan
} else {
    Write-Host ""
    Write-Host "================================================" -ForegroundColor Red
    Write-Host "  SECRETS SETUP FAILED                         " -ForegroundColor Red
    Write-Host "================================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "Some secrets could not be created or updated." -ForegroundColor Red
    Write-Host "Please check the errors above and try again." -ForegroundColor Yellow
    exit 1
}