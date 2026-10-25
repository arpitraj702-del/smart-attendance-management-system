# PowerShell Database Restore Utility for Smart Attendance Management System
param (
    [Parameter(Mandatory=$true, HelpMessage="Path to the SQL backup file")]
    [string]$BackupFile,
    [string]$DbName = "smart_attendance",
    [string]$DbUser = "root",
    [string]$DbHost = "localhost",
    [int]$DbPort = 3306
)

Write-Host "===================================================" -ForegroundColor Red
Write-Host "  Smart Attendance - Database Restore Utility      " -ForegroundColor Red
Write-Host "===================================================" -ForegroundColor Red

if (-not (Test-Path $BackupFile)) {
    Write-Host "[ERROR] Backup file not found: $BackupFile" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "[CRITICAL WARNING] Restoring will OVERWRITE and REPLACE data in '$DbName'!" -ForegroundColor Yellow
Write-Host "Target Backup File: $BackupFile" -ForegroundColor Yellow
Write-Host ""

$confirmation = Read-Host "Type 'YES' to proceed with overwrite and restore"
if ($confirmation -ne "YES") {
    Write-Host "[CANCELLED] Restore operation aborted by user." -ForegroundColor Gray
    exit 0
}

# Locate mysql.exe
$mysql = Get-Command mysql -ErrorAction SilentlyContinue
if (-not $mysql) {
    $possible = @(
        "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe",
        "C:\Program Files\MySQL\MySQL Server 8.4\bin\mysql.exe"
    )
    foreach ($p in $possible) {
        if (Test-Path $p) {
            $mysql = $p
            break
        }
    }
}

if (-not $mysql) {
    Write-Host "[ERROR] 'mysql' CLI command not found in PATH or standard installation directories." -ForegroundColor Red
    exit 1
}

Write-Host "Restoring database from $BackupFile ..." -ForegroundColor Cyan
Get-Content -Path $BackupFile -Encoding UTF8 | & $mysql -h $DbHost -P $DbPort -u $DbUser -p $DbName

if ($LASTEXITCODE -eq 0) {
    Write-Host "[SUCCESS] Database '$DbName' restored successfully from $BackupFile!" -ForegroundColor Green
} else {
    Write-Host "[ERROR] Database restore failed!" -ForegroundColor Red
}
