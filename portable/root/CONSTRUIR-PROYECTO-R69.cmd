@echo off
setlocal
set "BASE=%~dp0"
if not exist "%BASE%runtime\python.exe" ( echo FALTA_PYTHON_PORTABLE & exit /b 4 )
"%BASE%runtime\python.exe" -B "%BASE%CONSTRUIR-MULTIMODULO-R69.py" %*
exit /b %ERRORLEVEL%
