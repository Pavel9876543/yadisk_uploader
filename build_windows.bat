@echo off
setlocal EnableExtensions

set "APP_NAME=YadiskUploader"
set "EXE_NAME=%APP_NAME%.exe"
set "DIST_DIR=dist"
set "APP_DIST_DIR=%DIST_DIR%\%APP_NAME%"
set "INSTALLER_BAT=install_yadisk_uploader.bat"
set "README_CHAR_CODES=1063,1048,1058,1040,1058,1068"
set "PYTHON_CMD=python"

if exist ".venv\Scripts\python.exe" set "PYTHON_CMD=.venv\Scripts\python.exe"

echo Building %APP_NAME%...
%PYTHON_CMD% -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --windowed ^
  --name "%APP_NAME%" ^
  --contents-directory _internal ^
  --collect-submodules=yadisk ^
  --hidden-import=numpy ^
  --hidden-import=pygame ^
  --hidden-import=matplotlib ^
  --add-data "app/config/config.json;config" ^
  app/main.py
if errorlevel 1 exit /b 1

if not exist "%APP_DIST_DIR%\%EXE_NAME%" (
  echo Build finished, but "%APP_DIST_DIR%\%EXE_NAME%" was not found.
  exit /b 1
)

copy /Y "%INSTALLER_BAT%" "%APP_DIST_DIR%\%INSTALLER_BAT%" >nul
if errorlevel 1 exit /b 1

if exist "%APP_DIST_DIR%\_internal\%INSTALLER_BAT%" del /Q "%APP_DIST_DIR%\_internal\%INSTALLER_BAT%" >nul 2>nul

powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$readme=([string]::Concat(($env:README_CHAR_CODES -split ',' | ForEach-Object { [char][int]$_ })) + '.txt'); if (-not (Test-Path -LiteralPath $readme)) { Write-Error ('Missing ' + $readme); exit 1 }; Copy-Item -LiteralPath $readme -Destination (Join-Path '%APP_DIST_DIR%' $readme) -Force"
if errorlevel 1 exit /b 1

powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$readme=([string]::Concat(($env:README_CHAR_CODES -split ',' | ForEach-Object { [char][int]$_ })) + '.txt'); $allowed=@('%EXE_NAME%', '%INSTALLER_BAT%', '_internal', $readme); $bad=Get-ChildItem -LiteralPath '%APP_DIST_DIR%' | Where-Object { $allowed -notcontains $_.Name }; if ($bad) { $bad | ForEach-Object { Write-Host ('Unexpected top-level item in %APP_DIST_DIR%: ' + $_.Name) }; Write-Host ('Only %EXE_NAME%, %INSTALLER_BAT%, ' + $readme + ' and _internal should be at the package root.'); exit 1 }"
if errorlevel 1 exit /b 1

copy /Y "%INSTALLER_BAT%" "%DIST_DIR%\%INSTALLER_BAT%" >nul
if errorlevel 1 exit /b 1

powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$readme=([string]::Concat(($env:README_CHAR_CODES -split ',' | ForEach-Object { [char][int]$_ })) + '.txt'); Copy-Item -LiteralPath $readme -Destination (Join-Path '%DIST_DIR%' $readme) -Force"
if errorlevel 1 exit /b 1

powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "if (Test-Path 'dist\%APP_NAME%.zip') { Remove-Item 'dist\%APP_NAME%.zip' -Force }; Compress-Archive -LiteralPath 'dist\%APP_NAME%' -DestinationPath 'dist\%APP_NAME%.zip' -Force"
if errorlevel 1 exit /b 1

echo.
echo Build complete.
echo App folder: %APP_DIST_DIR%
echo Installer package: %DIST_DIR%\%APP_NAME%.zip
echo Installer launcher: %DIST_DIR%\%INSTALLER_BAT%
