@echo off
setlocal
set "PYTHONUTF8=1"
python -B VERIFY_ALL.py
exit /b %errorlevel%
