@echo off
setlocal
set "APP=C:\AUTOFABRICADOR\APPS\AFD-4c3887b54a6e1767"
if not exist "%APP%\LAUNCH.cmd" (
 echo No se encuentra una instalacion original verificada.
 exit /b 3
)
call "%APP%\LAUNCH.cmd"
exit /b %ERRORLEVEL%
