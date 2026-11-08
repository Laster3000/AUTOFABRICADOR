@echo off
setlocal
set "APP=C:\AUTOFABRICADOR\APPS\AFD-37f62cb4959f565b"
if not exist "%APP%\LAUNCH.cmd" (
 echo App original no instalada o falta el recibo. Consulte ESTADO-TRES-APLICACIONES-R63.cmd
 exit /b 3
)
call "%APP%\LAUNCH.cmd"
exit /b %ERRORLEVEL%
