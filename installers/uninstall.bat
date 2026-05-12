@echo off
setlocal enabledelayedexpansion

REM -------------------------
REM Define installation paths
REM -------------------------
set "USER_TARGET=%LocalAppData%\TeraShell"
set "ALL_USERS_TARGET=%ProgramFiles%\TeraShell"
set "USER_SHORTCUT=%APPDATA%\Microsoft\Windows\Start Menu\Programs\TeraShell.lnk"
set "ALL_USERS_SHORTCUT=%ProgramData%\Microsoft\Windows\Start Menu\Programs\TeraShell.lnk"

echo [*] Starting TeraShell uninstaller...
echo.

REM -------------------------
REM Remove current user installation
REM -------------------------
if exist "%USER_TARGET%" (
    echo [*] Removing TeraShell for current user...
    rmdir /S /Q "%USER_TARGET%"
    if exist "%USER_TARGET%" (
        echo [!] Could not remove some files.
    ) else (
        echo [*] Files removed successfully.
    )

    if exist "%USER_SHORTCUT%" (
        echo [*] Removing Start Menu shortcut...
        del /F /Q "%USER_SHORTCUT%"
        echo [*] Shortcut removed.
    )
) else (
    echo [*] No TeraShell installation found for current user.
)

echo [*] Removing current user PATH entry...
set "PATH_SCOPE=User"
set "REMOVE_TARGET=%USER_TARGET%"
call :RemovePathEntry


REM -----------------------------------------------------
REM If no all-users installation exists, skip this block
REM -----------------------------------------------------
if not exist "%ALL_USERS_TARGET%" goto finish

echo.
echo [*] Detected all-users installation at:
echo     %ALL_USERS_TARGET%
echo.

REM -----------------------------------------------------
REM Check admin. If not admin, elevate.
REM -----------------------------------------------------
net session >nul 2>&1
if errorlevel 1 (
    echo [!] Admin rights required to uninstall for all users.
    echo [*] Elevating to admin...
    powershell -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

REM -----------------------------------------------------
REM Ask user
REM -----------------------------------------------------
set /p RESPONSE="Do you want to uninstall TeraShell for ALL users? [y/N]: "

if /I "%RESPONSE%" NEQ "Y" (
    echo [*] Skipping all users uninstall.
    goto finish
)

echo.
echo [*] Removing TeraShell for all users...

rmdir /S /Q "%ALL_USERS_TARGET%"
if exist "%ALL_USERS_TARGET%" (
    echo [!] Some files could not be removed
) else (
    echo [*] Files removed successfully
)

if exist "%ALL_USERS_SHORTCUT%" (
    echo [*] Removing Start Menu shortcut...
    del /F /Q "%ALL_USERS_SHORTCUT%"
    echo [*] Shortcut removed
)

echo [*] Removing all users PATH entry...
set "PATH_SCOPE=Machine"
set "REMOVE_TARGET=%ALL_USERS_TARGET%"
call :RemovePathEntry

goto finish

:finish
echo.
echo [*] TeraShell uninstall finished
pause
exit /b

:RemovePathEntry
powershell -NoProfile -ExecutionPolicy Bypass -Command "$target=$env:REMOVE_TARGET; $scope=$env:PATH_SCOPE; $path=[Environment]::GetEnvironmentVariable('Path',$scope); if ([string]::IsNullOrWhiteSpace($path)) { exit 0 }; $parts=$path -split ';' | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }; $filtered=$parts | Where-Object { $_.TrimEnd('\') -ine $target.TrimEnd('\') }; if ($filtered.Count -ne $parts.Count) { [Environment]::SetEnvironmentVariable('Path', ($filtered -join ';'), $scope) }"
if errorlevel 1 echo [!] Failed to remove PATH entry for %REMOVE_TARGET%.
exit /b 0
