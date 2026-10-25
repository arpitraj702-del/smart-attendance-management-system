# PowerShell Database Backup Utility for Smart Attendance Management System
param (
    [string]$DbName = "smart_attendance",
    [string]$DbUser = "root",
    [string]$DbHost = "localhost",
    [int]$DbPort = 3306,
    [string]$OutputDir = "backups"
)

Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "  Smart Attendance - Database Backup Utility       " -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan

if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir | Out-Null
}

$Timestamp = (Get-Date).ToString("yyyyMMdd_HHmmss")
$OutputFile = Join-Path $OutputDir "backup_${DbName}_${Timestamp}.sql"

Write-Host "Destination: $OutputFile" -ForegroundColor Yellow
Write-Host "Executing mysqldump (including stored routines and triggers)..."

# Test for mysqldump
$mysqldump = Get-Command mysqldump -ErrorAction SilentlyContinue
if (-not $mysqldump) {
    # Check default MySQL installation paths on Windows
    $possible = @(
        "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqldump.exe",
        "C:\Program Files\MySQL\MySQL Server 8.4\bin\mysqldump.exe"
    )
    foreach ($p in $possible) {
        if (Test-Path $p) {
            $mysqldump = $p
            break
        }
    }
}

if (-not $mysqldump) {
    Write-Host "[ERROR] 'mysqldump' command not found in PATH or standard installation directories." -ForegroundColor Red
    Write-Host "Please ensure MySQL Server is installed and its bin directory is added to PATH."
    exit 1
}

& $mysqldump -h $DbHost -P $DbPort -u $DbUser -p --routines --triggers --single-transaction --databases $DbName --result-file="$OutputFile"

if ($LASTEXITCODE -eq 0 -and (Test-Path $OutputFile)) {
    $size = (Get-Item $OutputFile).Length / 1KB
    Write-Host "[SUCCESS] Backup created successfully!" -ForegroundColor Green
    Write-Host "File: $OutputFile ($([Math]::Round($size, 2)) KB)" -ForegroundColor Green
} else {
    Write-Host "[ERROR] Database backup failed!" -ForegroundColor Red
}
