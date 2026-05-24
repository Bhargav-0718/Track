# Generate a new Alembic migration
# Usage: .\scripts\create_migration.ps1 "add_user_weight_history"

param(
    [Parameter(Mandatory=$true)]
    [string]$MigrationName
)

Write-Host "Generating migration: $MigrationName" -ForegroundColor Cyan
.\.venv\Scripts\python.exe -m alembic revision --autogenerate -m $MigrationName
Write-Host "[OK] Migration file created in migrations/versions/" -ForegroundColor Green
Write-Host "[!]  Review the generated file before applying!" -ForegroundColor Yellow
