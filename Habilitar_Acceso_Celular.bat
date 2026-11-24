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
netsh advfirewall firewall delete rule name="Asista HTTP LAN" >nul 2>&1
netsh advfirewall firewall delete rule name="Asista HTTPS LAN" >nul 2>&1

netsh advfirewall firewall add rule name="Asista HTTP LAN" dir=in action=allow protocol=TCP localport=8080-8089 profile=private >nul 2>&1
if errorlevel 1 goto error
netsh advfirewall firewall add rule name="Asista HTTPS LAN" dir=in action=allow protocol=TCP localport=8443 profile=private >nul 2>&1
if errorlevel 1 goto error

echo ====================================================================
echo   [OK] LISTO: Puertos TCP 8080-8089 (HTTP) y 8443 (HTTPS)
echo   habilitados solo para redes privadas.
echo.
echo   Confirma que el perfil de esta red Wi-Fi sea "Privada".
echo ====================================================================
echo.
pause
exit /b 0

:error
echo.
echo [ERROR] Windows no pudo crear una de las reglas del Firewall.
echo Ejecuta este archivo como Administrador y verifica el perfil de red.
pause
exit /b 1
