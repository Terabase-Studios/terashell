@echo off
setlocal

:: -----------------------------------------------------------------------------
:: TeraShell Windows Uninstaller
::
:: This script uninstalls TeraShell. It automatically detects whether a
:: user-level or system-level installation exists and removes it completely.
:: -----------------------------------------------------------------------------

:: --- Configuration ---
set "USER_INSTALL_DIR=%LOCALAPPDATA%\TeraShell"
set "SYSTEM_INSTALL_DIR=%ProgramFiles%\TeraShell"

:: --- Helper Functions ---
:log
    set "level=%~1"
    set "message=%~2"
    if "%level%"=="INFO" echo [*] %message%
    if "%level%"=="SUCCESS" echo [+] %message%
    if "%level%"=="WARN" echo [!] %message%
    if "%level%"=="ERROR" echo [X] %message%
goto :eof

:: --- Main Logic ---
:main
    echo.
    call :log "INFO" "TeraShell Uninstaller for Windows"
    echo.

    :: 1. Detect installation type
    set "INSTALL_DIR="
    set "IS_SYSTEM_INSTALL=0"
    if exist "%SYSTEM_INSTALL_DIR%\" (
        call :log "INFO" "Detected a system-wide installation."
        set "INSTALL_DIR=%SYSTEM_INSTALL_DIR%"
        set "IS_SYSTEM_INSTALL=1"
    ) else if exist "%USER_INSTALL_DIR%\" (
        call :log "INFO" "Detected a user-level installation."
        set "INSTALL_DIR=%USER_INSTALL_DIR%"
        set "IS_SYSTEM_INSTALL=0"
    )

    if not defined INSTALL_DIR (
        call :log "INFO" "No TeraShell installation found. Nothing to do."
        goto :end
    )

    :: 2. Handle admin elevation for system uninstall
    if "%IS_SYSTEM_INSTALL%"=="1" (
        net session >nul 2>&1
        if errorlevel 1 (
            call :log "INFO" "Admin rights required for system-wide uninstall. Requesting elevation..."
            powershell -Command "Start-Process '%~f0' -Verb runAs"
            exit /b
        )
    )

    :: 3. Confirm with user
    echo.
    call :log "WARN" "This will permanently remove TeraShell from: %INSTALL_DIR%"
    set /p "confirm=Are you sure you want to continue? [y/N]: "
    if /i not "%confirm:~0,1%"=="Y" (
        call :log "WARN" "Uninstallation cancelled."
        goto :end
    )
    echo.

    :: 4. Perform uninstallation steps
    
    :: 4a. Remove from PATH
    call :log "INFO" "Removing TeraShell from PATH environment variable..."
    set "SCOPE=User"
    if "%IS_SYSTEM_INSTALL%"=="1" set "SCOPE=Machine"
    
    powershell -NoProfile -Command ^
        $Target = [EnvironmentVariableTarget]::%SCOPE%; ^
        $OldPath = [Environment]::GetEnvironmentVariable('Path', $Target); ^
        $NewPath = ($OldPath.Split(';') | Where-Object { $_ -ne '%INSTALL_DIR%' }) -join ';'; ^
        [Environment]::SetEnvironmentVariable('Path', $NewPath, $Target); ^
        Write-Host "PATH for %SCOPE% has been updated."
    
    :: 4b. Remove Start Menu shortcut
    call :log "INFO" "Removing Start Menu shortcut..."
    set "SHORTCUT_NAME=TeraShell.lnk"
     if "%IS_SYSTEM_INSTALL%"=="1" (
        set "SHORTCUT_PATH=%ProgramData%\Microsoft\Windows\Start Menu\Programs\%SHORTCUT_NAME%"
    ) else (
        set "SHORTCUT_PATH=%APPDATA%\Microsoft\Windows\Start Menu\Programs\%SHORTCUT_NAME%"
    )
    if exist "%SHORTCUT_PATH%" (
        del "%SHORTCAT_PATH%" >nul 2>&1
    )

    :: 4c. Remove installation directory
    call :log "INFO" "Removing installation directory: %INSTALL_DIR%"
    if exist "%INSTALL_DIR%\" (
        rmdir /s /q "%INSTALL_DIR%"
    )

    echo.
    call :log "SUCCESS" "TeraShell has been successfully uninstalled."
    call :log "WARN" "Please restart any open terminal windows for PATH changes to take full effect."

:end
    echo.
    pause
goto :eof

call :main
endlocal
