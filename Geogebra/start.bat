@echo off
cd /d "%~dp0"
if exist "C:\Users\Administrator\.workbuddy\binaries\python\versions\3.13.12\python.exe" (
  "C:\Users\Administrator\.workbuddy\binaries\python\versions\3.13.12\python.exe" serve.py
) else (
  python serve.py
)
pause
