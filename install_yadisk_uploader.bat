@echo off
setlocal EnableExtensions

set "APP_NAME=YadiskUploader"
set "EXE_NAME=YadiskUploader.exe"
set "SCRIPT_DIR=%~dp0"
set "SOURCE_DIR=%SCRIPT_DIR%"
set "ARCHIVE_PATH=%SCRIPT_DIR%%APP_NAME%.zip"
set "TEMP_EXTRACT="
set "INSTALL_MODE=folder"

if exist "%SOURCE_DIR%%EXE_NAME%" goto prompt_target

if exist "%ARCHIVE_PATH%" (
    set "INSTALL_MODE=archive"
    goto prompt_target
)

echo %APP_NAME% installer
echo.
echo Cannot find "%EXE_NAME%" or "%APP_NAME%.zip" next to this script.
echo Put this file next to the compiled app folder or next to %APP_NAME%.zip.
echo.
pause
exit /b 1

:prompt_target
set "DEFAULT_TARGET=%LOCALAPPDATA%\Programs\%APP_NAME%"

echo %APP_NAME% installer
echo.
if "%INSTALL_MODE%"=="archive" (
    echo Source archive:
    echo %ARCHIVE_PATH%
) else (
    echo Source folder:
    echo %SOURCE_DIR%
)
echo.
echo Enter the folder where the compiled app should be saved.
echo Press Enter to use:
echo %DEFAULT_TARGET%
echo.
set /p "TARGET_DIR=> "
if "%TARGET_DIR%"=="" set "TARGET_DIR=%DEFAULT_TARGET%"
for %%I in ("%TARGET_DIR%") do set "TARGET_DIR=%%~fI"

if "%INSTALL_MODE%"=="archive" goto extract_archive
goto copy_app

:extract_archive
set "TEMP_EXTRACT=%TEMP%\%APP_NAME%_extract_%RANDOM%%RANDOM%"
mkdir "%TEMP_EXTRACT%" >nul 2>nul
if errorlevel 1 goto extract_prepare_failed

set "ARCHIVE_PATH_ENV=%ARCHIVE_PATH%"
set "TEMP_EXTRACT_ENV=%TEMP_EXTRACT%"
powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -LiteralPath $env:ARCHIVE_PATH_ENV -DestinationPath $env:TEMP_EXTRACT_ENV -Force"
if errorlevel 1 goto extract_failed

set "SOURCE_DIR="
if exist "%TEMP_EXTRACT%\%APP_NAME%\%EXE_NAME%" (
    set "SOURCE_DIR=%TEMP_EXTRACT%\%APP_NAME%\"
) else (
    if exist "%TEMP_EXTRACT%\%EXE_NAME%" (
        set "SOURCE_DIR=%TEMP_EXTRACT%\"
    )
)

if not defined SOURCE_DIR (
    for /f "delims=" %%I in ('dir /s /b "%TEMP_EXTRACT%\%EXE_NAME%" 2^>nul') do if not defined SOURCE_DIR set "SOURCE_DIR=%%~dpI"
)

if not defined SOURCE_DIR goto exe_not_found

goto copy_app

:copy_app
if not exist "%TARGET_DIR%" mkdir "%TARGET_DIR%" >nul 2>nul
if errorlevel 1 goto target_prepare_failed

for %%I in ("%SOURCE_DIR%.") do set "SOURCE_DIR_FULL=%%~fI"

if /i "%SOURCE_DIR_FULL%"=="%TARGET_DIR%" goto create_shortcut

robocopy "%SOURCE_DIR%" "%TARGET_DIR%" /E /NFL /NDL /NJH /NJS /NP /XD "%TARGET_DIR%"
set "ROBOCOPY_CODE=%ERRORLEVEL%"
if %ROBOCOPY_CODE% GEQ 8 goto copy_failed

goto create_shortcut

:create_shortcut
if defined TEMP_EXTRACT rmdir /s /q "%TEMP_EXTRACT%" >nul 2>nul

set "TARGET_EXE=%TARGET_DIR%\%EXE_NAME%"
if not exist "%TARGET_EXE%" goto installed_exe_not_found

set "SHORTCUT_TARGET=%TARGET_EXE%"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$target=$env:SHORTCUT_TARGET; $desktop=[Environment]::GetFolderPath('Desktop'); $shortcutPath=Join-Path $desktop 'YadiskUploader.lnk'; $shell=New-Object -ComObject WScript.Shell; $shortcut=$shell.CreateShortcut($shortcutPath); $shortcut.TargetPath=$target; $shortcut.WorkingDirectory=Split-Path -Parent $target; $shortcut.IconLocation=$target + ',0'; $shortcut.Save()"
if errorlevel 1 goto shortcut_failed

echo.
echo Installed to:
echo %TARGET_DIR%
echo.
echo Desktop shortcut created.
echo.
pause
exit /b 0

:extract_prepare_failed
echo.
echo Cannot create temporary extraction folder:
echo %TEMP_EXTRACT%
goto fail

:extract_failed
echo.
echo Cannot extract archive:
echo %ARCHIVE_PATH%
goto fail

:exe_not_found
echo.
echo The archive does not contain %EXE_NAME%.
goto fail

:target_prepare_failed
echo.
echo Cannot create target folder:
echo %TARGET_DIR%
goto fail

:copy_failed
echo.
echo Cannot copy app files. Robocopy exit code: %ROBOCOPY_CODE%
goto fail

:installed_exe_not_found
echo.
echo Installed executable was not found:
echo %TARGET_EXE%
goto fail

:shortcut_failed
echo.
echo App files were copied, but the desktop shortcut was not created.
goto fail

:fail
if defined TEMP_EXTRACT rmdir /s /q "%TEMP_EXTRACT%" >nul 2>nul
echo.
pause
exit /b 1
