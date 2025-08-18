$errors = $null
$tokens = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile('.\deploy-staging-automated.ps1', [ref]$tokens, [ref]$errors)
if ($errors) {
    Write-Host "Syntax errors found:" -ForegroundColor Red
    $errors | ForEach-Object { 
        Write-Host "Line $($_.Extent.StartLineNumber): $($_.Message)" -ForegroundColor Red
    }
} else {
    Write-Host "Script syntax is valid" -ForegroundColor Green
}