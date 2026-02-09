@echo off
setlocal

:: -----------------------------------------------------------------------------
:: TeraShell Windows Installer
::
:: This script installs TeraShell for either the current user or all users.
:: - User install: %LOCALAPPDATA%\TeraShell (No admin rights required)
:: - System install: %ProgramFiles%\TeraShell (Admin rights required)
:: -----------------------------------------------------------------------------

:: --- Configuration ---
set "PYTHON_MAJOR_REQ=3"
set "PYTHON_MINOR_REQ=8"
set "PROJECT_ROOT=%~dp0.."
set "REQUIREMENTS_FILE=%PROJECT_ROOT%\requirements.txt"
set "SRC_DIR=%PROJECT_ROOT%\src"

:: --- Helper Functions ---
:log
    set "level=%~1"
    set "message=%~2"
    if "%level%"=="INFO" echo [*] %message%
    if "%level%"=="SUCCESS" echo [+] %message%
    if "%level%"=="WARN" echo [!] %message%
    if "%level%"=="ERROR" echo [X] %message%
goto :eof

:: --- Pre-flight Checks ---

:check_python
    call :log "INFO" "Checking Python version..."
    python -c "import sys; sys.exit(0 if sys.version_info >= (%PYTHON_MAJOR_REQ%, %PYTHON_MINOR_REQ%) else 1)" >nul 2>&1
    if errorlevel 1 (
        call :log "ERROR" "Python %PYTHON_MAJOR_REQ%.%PYTHON_MINOR_REQ%+" is required. Please install it and ensure it's in your PATH."
        goto :fail
    )
    for /f "delims=" %%v in ('python --version') do set "PY_VERSION=%%v"
    call :log "SUCCESS" "Python version OK (%PY_VERSION%)"
goto :eof


:: --- Main Logic ---

:main
    echo.
    call :log "INFO" "TeraShell Installer for Windows"
    echo.
    echo   Choose installation scope:
    echo     1) For me only (Recommended)
    echo     2) For all users (Requires Admin privileges)
    echo.
    set /p "scope_choice=Selection [1/2]: "

    set "TARGET_DIR="
    if "%scope_choice%"=="1" (
        set "TARGET_DIR=%LOCALAPPDATA%\TeraShell"
        set "IS_SYSTEM_INSTALL=0"
    ) else if "%scope_choice%"=="2" (
        set "TARGET_DIR=%ProgramFiles%\TeraShell"
        set "IS_SYSTEM_INSTALL=1"
    ) else (
        call :log "ERROR" "Invalid choice. Aborting."
        goto :fail
    )

    :: Check for admin rights if doing a system install
    if "%IS_SYSTEM_INSTALL%"=="1" (
        net session >nul 2>&1
        if errorlevel 1 (
            call :log "INFO" "Admin rights required for system-wide install. Requesting elevation..."
            powershell -Command "Start-Process '%~f0' -Verb runAs"
            exit /b
        )
    )

    call :check_python
    if errorlevel 1 goto :eof

    echo.
    set /p "add_to_path=Add TeraShell to your PATH? (Recommended) [Y/n]: "
    if /i not "%add_to_path:~0,1%"=="N" set "add_to_path=Y"

    set /p "add_shortcut=Create a Start Menu shortcut? [Y/n]: "
    if /i not "%add_shortcut:~0,1%"=="N" set "add_shortcut=Y"
    
    echo.
    call :log "INFO" "Target directory: %TARGET_DIR%"
    call :log "INFO" "Starting installation..."
    
    :: 1. Copy files
    call :log "INFO" "Copying source files..."
    mkdir "%TARGET_DIR%" >nul 2>&1
    xcopy "%SRC_DIR%" "%TARGET_DIR%\" /E /I /Q /Y >nul
    if errorlevel 1 (
        call :log "ERROR" "Failed to copy source files."
        goto :fail
    )

    :: 2. Create virtual environment
    call :log "INFO" "Creating Python virtual environment..."
    python -m venv "%TARGET_DIR%\venv" >nul
    if errorlevel 1 (
        call :log "ERROR" "Failed to create virtual environment."
        goto :fail
    )

    :: 3. Install dependencies
    call :log "INFO" "Installing dependencies..."
    "%TARGET_DIR%\venv\Scripts\pip.exe" install --upgrade pip >nul
    "%TARGET_DIR%\venv\Scripts\pip.exe" install -r "%REQUIREMENTS_FILE%" >nul
    if errorlevel 1 (
        call :log "WARN" "Failed to install dependencies. You may need to run 'pip install -r requirements.txt' manually."
    )

    :: 4. Create launcher
    set "LAUNCHER_PATH=%TARGET_DIR%\terashell.cmd"
    call :log "INFO" "Creating launcher at %LAUNCHER_PATH%"
    (
        echo @echo off
        echo "%TARGET_DIR%\venv\Scripts\python.exe" "%TARGET_DIR%\TeraShell.py" %%*
    ) > "%LAUNCHER_PATH%"
    
    :: 5. Add to PATH if requested
    if /i "%add_to_path%"=="Y" (
        call :log "INFO" "Adding TeraShell directory to PATH..."
        if "%IS_SYSTEM_INSTALL%"=="1" (
            setx /M PATH "%%PATH%%;%TARGET_DIR%" >nul
        ) else (
            setx PATH "%%PATH%%;%TARGET_DIR%" >nul
        )
        call :log "SUCCESS" "PATH updated. Please restart your terminal for it to take effect."
    )

    :: 6. Create shortcut if requested
    if /i "%add_shortcut%"=="Y" (
        call :log "INFO" "Creating Start Menu shortcut..."
        set "SHORTCUT_NAME=TeraShell.lnk"
        if "%IS_SYSTEM_INSTALL%"=="1" (
            set "SHORTCUT_PATH=%ProgramData%\Microsoft\Windows\Start Menu\Programs\%SHORTCUT_NAME%"
        ) else (
            set "SHORTCUT_PATH=%APPDATA%\Microsoft\Windows\Start Menu\Programs\%SHORTCUT_NAME%"
        )
        
        powershell -Command "$s=(New-Object -COM WScript.Shell).CreateShortcut('%SHORTCUT_PATH%'); $s.TargetPath='%LAUNCHER_PATH%'; $s.WorkingDirectory='%TARGET_DIR%'; $s.Save()"
        call :log "SUCCESS" "Shortcut created."
    )

    echo.
    call :log "SUCCESS" "Installation complete!"
    call :log "INFO" "You can now run 'terashell.cmd' or use the Start Menu shortcut."
    call :log "INFO" "To uninstall, run the 'uninstall.bat' script from the '%~dp0' directory."
    echo.
    pause
goto :eof

:fail
    echo.
    call :log "ERROR" "Installation failed."
    pause
    exit /b 1

call :main
endlocal