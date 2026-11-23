@echo off
title Sistema ASISTA - Control de Asistencias
color 0B
setlocal EnableDelayedExpansion

set "ROOT_DIR=%~dp0"
set "APP_DIR=%ROOT_DIR%asista\"
cd /d "%APP_DIR%"

:: 1. Verificar si existe un entorno virtual previo y si funciona en esta laptop
set "VENV_OK=0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -c "import sys" >nul 2>&1
    if !errorlevel! equ 0 (
        set "VENV_OK=1"
    ) else (
        echo [AVISO] El entorno previo fue creado en otra computadora.
        echo Limpiando entorno incompatible para configurarlo en esta laptop...
        rmdir /s /q ".venv" >nul 2>&1
    )
)

:: 2. Si el entorno es 100% funcional en esta laptop, iniciar el sistema directamente
if "!VENV_OK!"=="1" (
    taskkill /f /im pythonw.exe >nul 2>&1
    ".venv\Scripts\python.exe" -c "import db; d = db.Database(); d.connection()" >nul 2>&1
    start "" ".venv\Scripts\pythonw.exe" app.py
    exit /b 0
)

:: 3. Si no hay entorno valido, verificar si esta laptop tiene Python instalado
set "PY_CMD="
python --version >nul 2>&1
if !errorlevel! equ 0 set "PY_CMD=python"
if not defined PY_CMD (
    py --version >nul 2>&1
    if !errorlevel! equ 0 set "PY_CMD=py"
)

if not defined PY_CMD (
    cls
    echo ===============================================================================
    echo      SISTEMA ASISTA - U.E.P. PROF. ARISTOBULO IZTURIZ
    echo ===============================================================================
    echo.
    echo  [!] ATENCION: Esta laptop aun no tiene Python instalado en el sistema.
    echo.
    echo  Para ejecutar el sistema en esta computadora necesitas tener Python:
    echo.
    echo  1. Descargalo gratis desde: https://www.python.org/downloads/
    echo  2. IMPORTANTE AL INSTALAR: Marca la casilla [x] "Add python.exe to PATH"
    echo  3. Al terminar la instalacion de Python, vuelve a hacer doble clic aqui.
    echo.
    echo ===============================================================================
    echo.
    pause
    exit /b 1
)

:: 4. Si tiene Python instalado, configurar automaticamente el entorno
cls
echo ===============================================================================
echo     Configurando ASISTA por primera vez en esta laptop...
echo ===============================================================================
echo.
call "%ROOT_DIR%INSTALAR EN LAPTOP.bat"
if exist ".venv\Scripts\pythonw.exe" (
    start "" ".venv\Scripts\pythonw.exe" app.py
)
exit /b 0
