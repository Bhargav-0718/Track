# Track Backend — Local Development Setup
# Run from the backend/ directory: .\scripts\dev_setup.ps1

Write-Host "Track Backend — Development Setup" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan

# 1. Copy .env.example
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "[OK] Created .env from .env.example" -ForegroundColor Green
    Write-Host "[!]  Edit .env and set OPENAI_API_KEY and SECRET_KEY" -ForegroundColor Yellow
} else {
    Write-Host "[OK] .env already exists" -ForegroundColor Green
}

# 2. Create virtual environment
if (-not (Test-Path ".venv")) {
    Write-Host "Creating Python virtual environment..." -ForegroundColor Cyan
    python -m venv .venv
    Write-Host "[OK] Virtual environment created" -ForegroundColor Green
}

# 3. Install dependencies
Write-Host "Installing dependencies..." -ForegroundColor Cyan
.\.venv\Scripts\python.exe -m pip install -e ".[dev]" --quiet
Write-Host "[OK] Dependencies installed" -ForegroundColor Green

# 4. Start database
Write-Host "Starting PostgreSQL + pgvector via Docker..." -ForegroundColor Cyan
docker compose up db -d
Start-Sleep -Seconds 5
Write-Host "[OK] Database started" -ForegroundColor Green

# 5. Run migrations
Write-Host "Running Alembic migrations..." -ForegroundColor Cyan
.\.venv\Scripts\python.exe -m alembic upgrade head
Write-Host "[OK] Migrations applied" -ForegroundColor Green

Write-Host ""
Write-Host "Setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Start the API server:" -ForegroundColor Cyan
Write-Host "  .\.venv\Scripts\uvicorn.exe app.main:app --reload"
Write-Host ""
Write-Host "API Docs: http://localhost:8000/docs"
Write-Host "Health:   http://localhost:8000/health"
Write-Host ""
Write-Host "Run tests:" -ForegroundColor Cyan
Write-Host "  .\.venv\Scripts\pytest.exe -v"
