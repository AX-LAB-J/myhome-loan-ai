# Build the linux/amd64 image on this PC and push it to Amazon ECR.
#   powershell -ExecutionPolicy Bypass -File deploy\push-image.ps1
# Requires: Docker Desktop running, AWS CLI logged in (aws configure).
param(
    [string]$Region = "ap-northeast-2",
    [string]$Repository = "housing-side"
)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

$account = aws sts get-caller-identity --query Account --output text
if (-not $account) { throw "AWS CLI is not configured. Run 'aws configure' first." }
$registry = "$account.dkr.ecr.$Region.amazonaws.com"
$tag = (git rev-parse --short HEAD)
if (git status --porcelain) { $tag = "$tag-dirty" }

aws ecr describe-repositories --region $Region --repository-names $Repository *> $null
if ($LASTEXITCODE -ne 0) {
    aws ecr create-repository --region $Region --repository-name $Repository `
        --image-scanning-configuration scanOnPush=true | Out-Null
}

aws ecr get-login-password --region $Region | docker login --username AWS --password-stdin $registry
if ($LASTEXITCODE -ne 0) { throw "ECR login failed." }

$image = "$registry/$Repository"
docker build --platform linux/amd64 -t "${image}:$tag" -t "${image}:latest" .
if ($LASTEXITCODE -ne 0) { throw "docker build failed." }
docker push "${image}:$tag"
docker push "${image}:latest"
Write-Host "Pushed ${image}:$tag (also :latest)"
Write-Host "Set APP_IMAGE=${image}:latest in /opt/housing/deploy.env on the server."
