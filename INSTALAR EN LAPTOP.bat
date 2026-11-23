@echo off
title INSTALADOR ASISTA - Control de Asistencia Institucional
color 0B

set "SCRIPT_DIR=%~dp0"
set "APP_DIR=%SCRIPT_DIR%asista\"
cd /d "%APP_DIR%"

echo ===============================================================================
echo        SISTEMA ASISTA - INSTALADOR AUTOMATIZADO PORTABLE (SQLITE)
echo          U.E.P. Prof. Aristobulo Isturiz - Cabimas, Edo. Zulia
echo ===============================================================================
echo.

:: 1. Verificar si Python esta instalado en el sistema
echo [1/3] Verificando instalacion de Python en esta laptop...
python --version >nul 2>&1
if %errorlevel% equ 0 goto python_ok

py --version >nul 2>&1
if %errorlevel% equ 0 goto py_ok

echo.
echo ===========================================================================
echo [ERROR] No se detecto Python en esta computadora.
echo ===========================================================================
echo.
echo Para usar el sistema necesitas tener instalado Python:
echo 1. Descargalo gratis desde: https://www.python.org/downloads/
echo 2. IMPORTANTE AL INSTALAR: Marca la casilla "Add python.exe to PATH"
echo 3. Luego de instalarlo, vuelve a ejecutar este instalador.
echo.
pause
exit /b 1

:py_ok
set "PY_CMD=py"
goto continuar_install

:python_ok
set "PY_CMD=python"

:continuar_install
echo   [OK] Python detectado correctamente en el sistema.
echo.

:: 2. Crear entorno virtual local e instalar dependencias
echo [2/3] Configurando entorno e instalando librerias necesarias...
set "VENV_VALID=0"
if exist "%APP_DIR%.venv\Scripts\python.exe" (
    "%APP_DIR%.venv\Scripts\python.exe" -c "import sys" >nul 2>&1
    if %errorlevel% equ 0 (
        set "VENV_VALID=1"
    ) else (
        echo   - El entorno previo no corresponde a esta laptop. Reconfigurando...
        rmdir /s /q "%APP_DIR%.venv" >nul 2>&1
    )
)

if "%VENV_VALID%"=="0" (
    echo   - Creando entorno virtual aislado .venv...
    %PY_CMD% -m venv "%APP_DIR%.venv"
)

echo   - Instalando paquetes requeridos...
if exist "%APP_DIR%.venv\Scripts\python.exe" (
    "%APP_DIR%.venv\Scripts\python.exe" -m pip install -r "%APP_DIR%requirements.txt"
) else (
    %PY_CMD% -m pip install -r "%APP_DIR%requirements.txt"
)

echo   [OK] Dependencias verificadas con exito.
echo.

:: 3. Verificar base de datos SQLite integrada y crear acceso directo
echo [3/3] Verificando base de datos SQLite y preparando acceso directo...
if not exist "%APP_DIR%database" mkdir "%APP_DIR%database"

set "PY_CHECK=%APP_DIR%.venv\Scripts\python.exe"
if not exist "%PY_CHECK%" set "PY_CHECK=%PY_CMD%"

"%PY_CHECK%" -c "import sys; sys.path.insert(0, r'%APP_DIR%'); import db; d = db.Database(); d.connection(); print('  [OK] Base de datos verificada y lista con todas sus tablas.')"

:: Crear acceso directo en el Escritorio
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ws = New-Object -ComObject WScript.Shell; $dirs = @([System.Environment]::GetFolderPath('Desktop')); $od = [System.IO.Path]::Combine($env:USERPROFILE, 'OneDrive', 'Desktop'); if (Test-Path $od) { $dirs += $od }; foreach ($d in $dirs | Select-Object -Unique) { if (Test-Path $d) { $s = $ws.CreateShortcut((Join-Path $d 'ASISTA - Iniciar Sistema.lnk')); $s.TargetPath = '%SCRIPT_DIR%INICIAR SISTEMA.bat'; $s.WorkingDirectory = '%APP_DIR%'; if (Test-Path '%APP_DIR%assets\asista_icon.ico') { $s.IconLocation = '%APP_DIR%assets\asista_icon.ico,0' }; $s.Description = 'Sistema ASISTA - Control de Asistencia'; $s.Save() } }" >nul 2>&1

echo   [OK] Acceso directo con icono oficial creado en tu Escritorio.
echo.
echo ===============================================================================
echo                   INSTALACION COMPLETADA CON EXITO!
echo ===============================================================================
echo.
echo Ya puedes abrir el sistema desde tu Escritorio haciendo doble clic en el icono:
echo.
echo            [ ASISTA - Iniciar Sistema ]
echo.
echo Credenciales para ingresar a la demostracion:
echo   - Directora:      Usuario: directora  ^| Clave: Carmen123.
echo   - Administracion: Usuario: admin      ^| Clave: Admin123.
echo   - Profesores:     Usuario: prof.navarro / recepcion ^| Clave: Asista2026*
echo.
echo Presiona cualquier tecla para cerrar esta ventana...
pause >nul
