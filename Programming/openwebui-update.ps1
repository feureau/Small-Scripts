Write-Host "--- Starting Open WebUI Update Process ---" -ForegroundColor Cyan

# 1. Pull the latest image from the official repository
Write-Host "Step 1: Pulling latest image..." -ForegroundColor Yellow
docker pull ghcr.io/open-webui/open-webui:main

# 2. Remove the existing container (Data is safe in the volume)
Write-Host "Step 2: Removing old container..." -ForegroundColor Yellow
docker rm -f open-webui

# 3. Start the new container with GPU support
Write-Host "Step 3: Starting new container with GPU support..." -ForegroundColor Yellow
docker run -d `
  -p 3000:8080 `
  --gpus all `
  --add-host=host.docker.internal:host-gateway `
  -v open-webui:/app/backend/data `
  --name open-webui `
  --restart always `
  ghcr.io/open-webui/open-webui:main

Write-Host "--- Update Complete! ---" -ForegroundColor Green
Write-Host "You can access Open WebUI at http://localhost:3000"
Read-Host "Press Enter to exit"