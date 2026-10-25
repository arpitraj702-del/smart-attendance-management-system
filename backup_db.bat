@echo off
setlocal enabledelayedexpansion

echo ===================================================
echo Smart Attendance Database Backup Utility
echo ===================================================

if not exist backups mkdir backups

:: Generate timestamp
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set dt=%%I
set TIMESTAMP=%dt:~0,8%_%dt:~8,6%
set BACKUP_FILE=backups\backup_smart_attendance_%TIMESTAMP%.sql

echo Backing up database to: %BACKUP_FILE%
echo Please enter MySQL password when prompted:
mysqldump -h localhost -P 3306 -u root -p --routines --triggers --single-transaction smart_attendance > "%BACKUP_FILE%"

if %ERRORLEVEL% equ 0 (
    echo [SUCCESS] Backup completed successfully: %BACKUP_FILE%
) else (
    echo [ERROR] Backup failed! Check MySQL credentials and status.
)
pause
