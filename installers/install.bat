@echo off
setlocal enabledelayedexpansion

REM -------------------------
REM Configuration
REM -------------------------
set "USER_TARGET=%LocalAppData%\TeraShell"
set "ALL_USERS_TARGET=%ProgramFiles%\TeraShell"
set "PY_SRC_DIR=%~dp0\.."
set "REQUIREMENTS=%PY_SRC_DIR%\requirements.txt"
set "PYTHON_MAJOR_REQ=3"
set "PYTHON_MINOR_REQ=11"

REM -------------------------
REM Ask installation scope
REM -------------------------
echo Choose installation scope:
echo   1) Install for CURRENT user only
echo   2) Install for ALL users (requires admin)
set /p scope_choice=Selection [1/2]:

if "%scope_choice%"=="1" (
    set "TARGET_DIR=%USER_TARGET%"
) else if "%scope_choice%"=="2" (
    REM Relaunch as admin if not already elevated
    net session >nul 2>&1
    if errorlevel 1 (
        echo [*] Elevation required for all users installation...
        powershell -Command "Start-Process '%~f0' -Verb runAs"
        exit /b
    )
    set "TARGET_DIR=%ALL_USERS_TARGET%"
) else (
    echo [!] Invalid choice, aborting.
    pause
    exit /b 1
)

REM -------------------------
REM Ask about adding to PATH
REM -------------------------
set /p add_path=Do you want to add TeraShell to your PATH? [y/N]:
set "ADD_PATH=%add_path:~0,1%"
if /i not "%ADD_PATH%"=="y" set "ADD_PATH=n"


REM -------------------------
REM Ask about creating Start Menu shortcut
REM -------------------------
set /p create_shortcut=Do you want to create a Start Menu shortcut? [y/N]:
set "CREATE_SHORTCUT=%create_shortcut:~0,1%"
if /i not "%CREATE_SHORTCUT%"=="y" set "CREATE_SHORTCUT=n"

REM -------------------------
REM Check for Python >= 3.11
REM -------------------------
python --version >nul 2>&1
if errorlevel 1 (
    echo [!] Python not found. Please install Python >= 3.11
    pause
    exit /b 1
)

for /f "delims=" %%a in ('python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"') do set "PY_VERSION=%%a"
for /f "tokens=1,2 delims=." %%a in ("%PY_VERSION%") do (
    set "PY_MAJOR=%%a"
    set "PY_MINOR=%%b"
)
if "%PY_MAJOR%"=="" set "PY_MAJOR=0"
if "%PY_MINOR%"=="" set "PY_MINOR=0"

if %PY_MAJOR% LSS %PYTHON_MAJOR_REQ% (
    echo [!] Python version too old. Need >= %PYTHON_MAJOR_REQ%.%PYTHON_MINOR_REQ%
    pause
    exit /b 1
)
if %PY_MAJOR%==%PYTHON_MAJOR_REQ% (
    if %PY_MINOR% LSS %PYTHON_MINOR_REQ% (
        echo [!] Python version too old. Need >= %PYTHON_MAJOR_REQ%.%PYTHON_MINOR_REQ%
        pause
        exit /b 1
    )
)
echo [*] Python version OK: %PY_VERSION%

REM -------------------------
REM Copy files
REM -------------------------
echo [*] Copying TeraShell files to %TARGET_DIR%...
if not exist "%TARGET_DIR%" mkdir "%TARGET_DIR%"
xcopy /E /I /Y "%PY_SRC_DIR%\src\*" "%TARGET_DIR%\" >nul
if errorlevel 1 (
    echo [!] Failed to copy TeraShell files.
    pause
    exit /b 1
)

REM -------------------------
REM Create virtual environment
REM -------------------------
echo [*] Creating virtual environment...
python -m venv "%TARGET_DIR%\venv"
if errorlevel 1 (
    echo [!] Failed to create virtual environment.
    pause
    exit /b 1
)

REM Install requirements
if exist "%REQUIREMENTS%" (
    echo [*] Installing dependencies...
    "%TARGET_DIR%\venv\Scripts\pip.exe" install -r "%REQUIREMENTS%"
    if errorlevel 1 (
        echo [!] Failed to install dependencies.
        pause
        exit /b 1
    )
)

REM -------------------------
REM Create launcher
REM -------------------------
set "WRAPPER=%TARGET_DIR%\TeraShell.cmd"
echo [*] Creating TeraShell launcher...
(
echo @echo off
echo "%TARGET_DIR%\venv\Scripts\python.exe" "%TARGET_DIR%\TeraShell.py" %%*
) > "%WRAPPER%"

REM -------------------------
REM Create Start Menu shortcut if requested
REM -------------------------
if /i "%CREATE_SHORTCUT%"=="y" (
    if "%scope_choice%"=="1" (
        set "START_MENU=%APPDATA%\Microsoft\Windows\Start Menu\Programs\TeraShell.lnk"
    ) else (
        set "START_MENU=%ProgramData%\Microsoft\Windows\Start Menu\Programs\TeraShell.lnk"
    )

    REM Make sure folder exists
    for %%F in ("%START_MENU%") do if not exist "%%~dpF" mkdir "%%~dpF"

    echo [*] Creating Start Menu shortcut...

    REM Use delayed expansion to safely expand variables with spaces
    setlocal enabledelayedexpansion
    set "psCommand=$s=(New-Object -COM WScript.Shell).CreateShortcut('!START_MENU!'); $s.TargetPath='!WRAPPER!'; $s.WorkingDirectory='!TARGET_DIR!'; $s.Save()"
    powershell -NoProfile -Command "!psCommand!"
    endlocal

    echo [*] Shortcut created: %START_MENU%
)

REM -------------------------
REM Add to PATH
REM -------------------------
if /i "%ADD_PATH%"=="y" (
    echo [*] Updating PATH...

    if "%scope_choice%"=="1" (
        set "PATH_SCOPE=User"
    ) else (
        set "PATH_SCOPE=Machine"
    )

    powershell -NoProfile -ExecutionPolicy Bypass -Command "$target=$env:TARGET_DIR; $scope=$env:PATH_SCOPE; $path=[Environment]::GetEnvironmentVariable('Path',$scope); $parts=@(); if (-not [string]::IsNullOrWhiteSpace($path)) { $parts=$path -split ';' | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } }; $exists=$parts | Where-Object { $_.TrimEnd('\') -ieq $target.TrimEnd('\') }; if ($exists) { exit 10 }; [Environment]::SetEnvironmentVariable('Path', (($parts + $target) -join ';'), $scope)"
    if !errorlevel! EQU 10 (
        echo [*] PATH already contains TeraShell.
    ) else if errorlevel 1 (
        echo [!] Failed to update PATH.
        pause
        exit /b 1
    ) else (
        echo [*] Added TeraShell to PATH.
    )
)

REM -------------------------
REM Done
REM -------------------------
echo.
echo [*] TeraShell installation complete!
echo Launcher created: %WRAPPER%
if /i "%ADD_PATH%"=="y" echo TeraShell added to PATH.

pause
