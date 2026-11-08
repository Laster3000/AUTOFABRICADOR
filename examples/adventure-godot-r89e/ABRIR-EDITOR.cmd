@echo off
setlocal
cd /d "%~dp0"
start "" "%~dp0tools\\Godot_v4.6.3-stable_win64.exe" --editor --path "%~dp0game"
exit /b 0
