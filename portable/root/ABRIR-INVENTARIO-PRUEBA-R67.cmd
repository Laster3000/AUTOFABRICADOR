@echo off
setlocal
set "BASE=%~dp0"
if not exist "%BASE%APPS\AFD-fbfef1f9bef11533\LAUNCH.cmd" (
 echo No existe la aplicacion de inventario verificada R67.
 exit /b 4
)
call "%BASE%APPS\AFD-fbfef1f9bef11533\LAUNCH.cmd" %*
exit /b %ERRORLEVEL%
