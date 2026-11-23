@echo off
title Habilitar Acceso de Celulares a ASISTA
color 0B

:: Auto-elevacion a Administrador si no tiene permisos
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Solicitando permisos de Administrador para configurar el Firewall...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

echo ====================================================================
echo           ASISTA - HABILITAR ACCESO DE CELULARES EN WI-FI
echo ====================================================================
echo.
echo Configurando reglas del Firewall de Windows para conexion movil...
echo.

netsh advfirewall firewall delete rule name="Asista Servidor 8080" >nul 2>&1
netsh advfirewall firewall delete rule name="Asista Servidor 8443" >nul 2>&1
netsh advfirewall firewall delete rule name="Asista Servidor 80" >nul 2>&1

netsh advfirewall firewall add rule name="Asista Servidor 8080" dir=in action=allow protocol=TCP localport=8080 profile=any >nul 2>&1
netsh advfirewall firewall add rule name="Asista Servidor 8443" dir=in action=allow protocol=TCP localport=8443 profile=any >nul 2>&1
netsh advfirewall firewall add rule name="Asista Servidor 80" dir=in action=allow protocol=TCP localport=80 profile=any >nul 2>&1

echo ====================================================================
echo   [OK] LISTO: Puertos 8080 (HTTP) y 8443 (HTTPS Camara en Vivo)
echo   han sido habilitados con exito en tu red.
echo.
echo   Tus telefonos celulares ya pueden conectarse y escanear
echo   en tiempo real sin bloqueos.
echo ====================================================================
echo.
pause
