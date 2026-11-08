@echo off
cd /d "%~dp0"
if exist "C:\Users\user\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" (
  "C:\Users\user\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" demo_app.py
) else (
  py -3 demo_app.py
)
if errorlevel 1 pause
