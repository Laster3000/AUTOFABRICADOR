@echo off
setlocal
set "BASE=%~dp0"
if not exist "%BASE%runtime\python.exe" (echo ERROR: Python portable faltante & exit /b 4)
"%BASE%runtime\python.exe" -B "%BASE%portable_control.py" status %*
exit /b %ERRORLEVEL%
