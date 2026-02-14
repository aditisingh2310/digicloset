# Local Verification Script for Docker Builds

Write-Host "Verifying Docker builds..."

# Build model-service
Write-Host "Building digicloset-upgrade-pack/model-service..."
docker build -t model-service:test digicloset-upgrade-pack/model-service
if ($LASTEXITCODE -eq 0) {
    Write-Host "SUCCESS: model-service built successfully." -ForegroundColor Green
}
else {
    Write-Host "FAILURE: model-service failed to build." -ForegroundColor Red
}

# Build model-service-complete
Write-Host "Building digicloset-upgrade-pack-complete/model-service..."
docker build -t model-service-complete:test digicloset-upgrade-pack-complete/model-service
if ($LASTEXITCODE -eq 0) {
    Write-Host "SUCCESS: model-service-complete built successfully." -ForegroundColor Green
}
else {
    Write-Host "FAILURE: model-service-complete failed to build." -ForegroundColor Red
}

# Build backend
Write-Host "Building digicloset-upgrade-pack/backend..."
docker build -t backend:test digicloset-upgrade-pack/backend
if ($LASTEXITCODE -eq 0) {
    Write-Host "SUCCESS: backend built successfully." -ForegroundColor Green
}
else {
    Write-Host "FAILURE: backend failed to build." -ForegroundColor Red
}

# Build backend-complete
Write-Host "Building digicloset-upgrade-pack-complete/backend..."
docker build -t backend-complete:test digicloset-upgrade-pack-complete/backend
if ($LASTEXITCODE -eq 0) {
    Write-Host "SUCCESS: backend-complete built successfully." -ForegroundColor Green
}
else {
    Write-Host "FAILURE: backend-complete failed to build." -ForegroundColor Red
}
