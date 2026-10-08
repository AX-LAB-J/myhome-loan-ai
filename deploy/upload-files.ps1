# Copy the private runtime files (not in Git or the image) and deploy scripts to the EC2 instance.
#   powershell -ExecutionPolicy Bypass -File deploy\upload-files.ps1 -Server 3.35.0.10 -Key C:\keys\housing.pem
# Uploads: .env, data/housing.sqlite, the CSVs the app reads at startup, models/, deploy files.
param(
    [Parameter(Mandatory = $true)][string]$Server,
    [Parameter(Mandatory = $true)][string]$Key,
    [string]$User = "ec2-user",
    [string]$AppDir = "/opt/housing",
    [switch]$SkipData
)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
$target = "${User}@${Server}"
$ssh = @("-i", $Key, "-o", "StrictHostKeyChecking=accept-new")

function Copy-ToServer([string[]]$Files, [string]$Destination) {
    scp @ssh @Files "${target}:$Destination"
    if ($LASTEXITCODE -ne 0) { throw "scp failed: $Files" }
}

ssh @ssh $target "sudo mkdir -p $AppDir/data/raw $AppDir/models && sudo chown -R ${User}:${User} $AppDir"
if ($LASTEXITCODE -ne 0) { throw "ssh failed: check -Server, -Key and the security group (port 22 from your IP)." }
Copy-ToServer @("deploy/compose.aws.yaml", "deploy/Caddyfile", "deploy/update.sh", "deploy/ec2-setup.sh", "deploy/deploy.env.example") "$AppDir/"
Copy-ToServer @(".env") "$AppDir/.env"
if (-not $SkipData) {
    $csv = "home_purchases", "loans_raw", "customer_financial_profiles", "customer_debt_summary", "accounts" |
        ForEach-Object { "data/raw/$_.csv" }
    Copy-ToServer $csv "$AppDir/data/raw/"
    Copy-ToServer @("data/housing.sqlite") "$AppDir/data/"
    Copy-ToServer @("models/home_loan_models.joblib") "$AppDir/models/"
}
Write-Host "Uploaded to ${target}:$AppDir"
