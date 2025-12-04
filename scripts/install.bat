@echo off
setlocal enabledelayedexpansion

REM -------------------------
REM Configuration
REM -------------------------
set "USER_TARGET=%LocalAppData%\TeraShell"
set "ALL_USERS_TARGET=%ProgramFiles%\TeraShell"
set "PY_SRC_DIR=%~dp0\..\py"
set "REQUIREMENTS=%PY_SRC_DIR%\requirements.txt"
set "PYTHON_MAJOR_REQ=3"
set "PYTHON_MINOR_REQ=6"

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

REM -------------------------
REM Create virtual environment
REM -------------------------
echo [*] Creating virtual environment...
python -m venv "%TARGET_DIR%\venv"

REM Install requirements
if exist "%REQUIREMENTS%" (
    echo [*] Installing dependencies...
    "%TARGET_DIR%\venv\Scripts\pip.exe" install -r "%REQUIREMENTS%"
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

    REM Read the current PATH depending on scope
    if "%scope_choice%"=="1" (
        for /f "tokens=2*" %%A in ('reg query HKCU\Environment /v PATH 2^>nul') do set "CUR_PATH=%%B"
    ) else (
        for /f "tokens=2*" %%A in ('reg query HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment /v PATH 2^>nul') do set "CUR_PATH=%%B"
    )

    if not defined CUR_PATH set "CUR_PATH="

    REM Check for existing entry (case-insensitive)
    echo %CUR_PATH% | findstr /I /C:"%TARGET_DIR%" >nul
    if %errorlevel%==0 (
        echo [*] PATH already contains TeraShell =)
    ) else (
        echo [*] Adding TeraShell to PATH...
        if "%scope_choice%"=="1" (
            setx PATH "%CUR_PATH%;%TARGET_DIR%" >nul
        ) else (
            setx /M PATH "%CUR_PATH%;%TARGET_DIR%" >nul
        )
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
