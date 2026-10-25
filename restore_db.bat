@echo off
setlocal enabledelayedexpansion

echo ===================================================
echo Smart Attendance Database Restore Utility
echo ===================================================

if "%~1"=="" (
    echo [ERROR] No backup file specified!
    echo Usage: restore_db.bat path\to\backup_file.sql
    echo Example: restore_db.bat backups\backup_smart_attendance_20261025.sql
    exit /b 1
)

set BACKUP_FILE=%~1
if not exist "%BACKUP_FILE%" (
    echo [ERROR] Backup file not found: %BACKUP_FILE%
    exit /b 1
)

echo.
echo [WARNING] Restoring will OVERWRITE and REPLACE data in database 'smart_attendance'!
echo Backup file to restore: %BACKUP_FILE%
echo.
set /p CONFIRM="Type YES to confirm restore: "
if not "%CONFIRM%"=="YES" (
    echo [CANCELLED] Restore aborted by user.
    exit /b 0
)

echo Restoring database...
mysql -h localhost -P 3306 -u root -p smart_attendance < "%BACKUP_FILE%"

if %ERRORLEVEL% equ 0 (
    echo [SUCCESS] Database restored successfully from %BACKUP_FILE%!
) else (
    echo [ERROR] Restore failed! Check credentials and SQL syntax.
)
pause
