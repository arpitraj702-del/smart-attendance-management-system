@echo off
REM Starts the Smart Attendance app using the project's virtual environment.
cd /d "%~dp0"
if not exist venv\Scripts\python.exe (
  echo Virtual environment not found. Follow README step 4 first.
  pause
  exit /b 1
)
call venv\Scripts\activate.bat
python app.py
pause
