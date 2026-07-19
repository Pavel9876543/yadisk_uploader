@echo off
setlocal EnableExtensions

set "APP_NAME=YadiskUploader"
set "EXE_NAME=YadiskUploader.exe"
set "SCRIPT_DIR=%~dp0"
set "SOURCE_DIR=%SCRIPT_DIR%"
set "ARCHIVE_PATH=%SCRIPT_DIR%%APP_NAME%.zip"
set "ARCHIVE_BASENAME=%APP_NAME%"
set "TEMP_EXTRACT="
set "INSTALL_MODE=folder"

for %%I in ("%EXE_NAME%") do set "SHORTCUT_NAME=%%~nI"

if exist "%SOURCE_DIR%%EXE_NAME%" goto source_ready

if exist "%ARCHIVE_PATH%" (
    set "INSTALL_MODE=archive"
    for %%I in ("%ARCHIVE_PATH%") do set "ARCHIVE_BASENAME=%%~nI"
    goto source_ready
)

set "ZIP_COUNT=0"
for %%I in ("%SCRIPT_DIR%*.zip") do if exist "%%~fI" call :remember_zip "%%~fI"
if "%ZIP_COUNT%"=="1" (
    set "INSTALL_MODE=archive"
    goto source_ready
)

echo %APP_NAME% installer
echo.
echo Cannot find "%EXE_NAME%" or "%APP_NAME%.zip" next to this script.
echo Put this file next to the compiled app folder or next to the app archive.
echo.
pause
exit /b 1

:source_ready
if "%INSTALL_MODE%"=="archive" (
    set "DEFAULT_INSTALL_NAME=%ARCHIVE_BASENAME%"
) else (
    set "DEFAULT_INSTALL_NAME=%APP_NAME%"
)

if defined LOCALAPPDATA (
    set "DEFAULT_PARENT=%LOCALAPPDATA%\Programs"
) else (
    set "DEFAULT_PARENT=%USERPROFILE%"
)
set "DEFAULT_TARGET=%DEFAULT_PARENT%\%DEFAULT_INSTALL_NAME%"
set "DIALOG_TITLE=%APP_NAME% installer"

call :choose_target_dialog
if errorlevel 2 goto cancelled
if errorlevel 1 goto prompt_target_console
goto normalize_target

:prompt_target_console
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

:normalize_target
if not defined TARGET_DIR goto cancelled
for %%I in ("%TARGET_DIR%") do set "TARGET_DIR=%%~fI"

if "%INSTALL_MODE%"=="archive" goto extract_archive
goto copy_app

:extract_archive
set "TEMP_EXTRACT=%TEMP%\%APP_NAME%_extract_%RANDOM%%RANDOM%"
mkdir "%TEMP_EXTRACT%" >nul 2>nul
if errorlevel 1 goto extract_prepare_failed

set "ARCHIVE_PATH_ENV=%ARCHIVE_PATH%"
set "TEMP_EXTRACT_ENV=%TEMP_EXTRACT%"
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -LiteralPath $env:ARCHIVE_PATH_ENV -DestinationPath $env:TEMP_EXTRACT_ENV -Force"
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
for %%I in ("%SOURCE_DIR%.") do set "SOURCE_DIR_FULL=%%~fI"

if /i "%SOURCE_DIR_FULL%"=="%TARGET_DIR%" goto create_shortcut

set "SOURCE_DIR_ENV=%SOURCE_DIR%"
set "TARGET_DIR_ENV=%TARGET_DIR%"
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $source=[System.IO.Path]::GetFullPath($env:SOURCE_DIR_ENV).TrimEnd('\','/'); $target=[System.IO.Path]::GetFullPath($env:TARGET_DIR_ENV).TrimEnd('\','/'); if ([string]::Equals($source, $target, [System.StringComparison]::OrdinalIgnoreCase)) { exit 10 }; if ($target.StartsWith($source + '\', [System.StringComparison]::OrdinalIgnoreCase)) { exit 11 }; New-Item -ItemType Directory -Force -LiteralPath $target | Out-Null; Get-ChildItem -LiteralPath $source -Force | ForEach-Object { Copy-Item -LiteralPath $_.FullName -Destination $target -Recurse -Force }"
set "COPY_CODE=%ERRORLEVEL%"
if "%COPY_CODE%"=="10" goto create_shortcut
if "%COPY_CODE%"=="11" goto target_inside_source
if not "%COPY_CODE%"=="0" goto copy_failed

goto create_shortcut

:create_shortcut
if defined TEMP_EXTRACT rmdir /s /q "%TEMP_EXTRACT%" >nul 2>nul

set "TARGET_EXE=%TARGET_DIR%\%EXE_NAME%"
if not exist "%TARGET_EXE%" goto installed_exe_not_found

set "SHORTCUT_TARGET=%TARGET_EXE%"
set "SHORTCUT_NAME_ENV=%SHORTCUT_NAME%"
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$target=$env:SHORTCUT_TARGET; $name=$env:SHORTCUT_NAME_ENV; $desktop=[Environment]::GetFolderPath('Desktop'); $shortcutPath=Join-Path $desktop ($name + '.lnk'); $shell=New-Object -ComObject WScript.Shell; $shortcut=$shell.CreateShortcut($shortcutPath); $shortcut.TargetPath=$target; $shortcut.WorkingDirectory=Split-Path -Parent $target; $shortcut.IconLocation=$target + ',0'; $shortcut.Save()"
if errorlevel 1 goto shortcut_failed

echo.
echo Installed to:
echo %TARGET_DIR%
echo.
echo Desktop shortcut created:
echo %SHORTCUT_NAME%.lnk
echo.
pause
exit /b 0

:choose_target_dialog
set "TARGET_DIR="
where powershell.exe >nul 2>nul
if errorlevel 1 exit /b 1

set "DIALOG_PS=%TEMP%\%APP_NAME%_select_target_%RANDOM%%RANDOM%.ps1"
> "%DIALOG_PS%" echo $ErrorActionPreference = 'Stop'
>> "%DIALOG_PS%" echo Add-Type -AssemblyName System.Windows.Forms
>> "%DIALOG_PS%" echo Add-Type -AssemblyName System.Drawing
>> "%DIALOG_PS%" echo [System.Windows.Forms.Application]::EnableVisualStyles()
>> "%DIALOG_PS%" echo $form = New-Object System.Windows.Forms.Form
>> "%DIALOG_PS%" echo $form.Text = $env:DIALOG_TITLE
>> "%DIALOG_PS%" echo $form.StartPosition = 'CenterScreen'
>> "%DIALOG_PS%" echo $form.FormBorderStyle = 'FixedDialog'
>> "%DIALOG_PS%" echo $form.MaximizeBox = $false
>> "%DIALOG_PS%" echo $form.MinimizeBox = $false
>> "%DIALOG_PS%" echo $form.ClientSize = New-Object System.Drawing.Size(620, 145)
>> "%DIALOG_PS%" echo $label = New-Object System.Windows.Forms.Label
>> "%DIALOG_PS%" echo $label.Text = 'Extraction folder:'
>> "%DIALOG_PS%" echo $label.AutoSize = $true
>> "%DIALOG_PS%" echo $label.Location = New-Object System.Drawing.Point(12, 18)
>> "%DIALOG_PS%" echo $form.Controls.Add($label)
>> "%DIALOG_PS%" echo $pathBox = New-Object System.Windows.Forms.TextBox
>> "%DIALOG_PS%" echo $pathBox.Text = $env:DEFAULT_TARGET
>> "%DIALOG_PS%" echo $pathBox.Location = New-Object System.Drawing.Point(12, 42)
>> "%DIALOG_PS%" echo $pathBox.Size = New-Object System.Drawing.Size(500, 23)
>> "%DIALOG_PS%" echo $form.Controls.Add($pathBox)
>> "%DIALOG_PS%" echo $browseButton = New-Object System.Windows.Forms.Button
>> "%DIALOG_PS%" echo $browseButton.Text = 'Browse...'
>> "%DIALOG_PS%" echo $browseButton.Location = New-Object System.Drawing.Point(522, 40)
>> "%DIALOG_PS%" echo $browseButton.Size = New-Object System.Drawing.Size(86, 27)
>> "%DIALOG_PS%" echo $form.Controls.Add($browseButton)
>> "%DIALOG_PS%" echo $okButton = New-Object System.Windows.Forms.Button
>> "%DIALOG_PS%" echo $okButton.Text = 'OK'
>> "%DIALOG_PS%" echo $okButton.Location = New-Object System.Drawing.Point(416, 98)
>> "%DIALOG_PS%" echo $okButton.Size = New-Object System.Drawing.Size(92, 30)
>> "%DIALOG_PS%" echo $okButton.DialogResult = [System.Windows.Forms.DialogResult]::OK
>> "%DIALOG_PS%" echo $form.Controls.Add($okButton)
>> "%DIALOG_PS%" echo $cancelButton = New-Object System.Windows.Forms.Button
>> "%DIALOG_PS%" echo $cancelButton.Text = 'Cancel'
>> "%DIALOG_PS%" echo $cancelButton.Location = New-Object System.Drawing.Point(516, 98)
>> "%DIALOG_PS%" echo $cancelButton.Size = New-Object System.Drawing.Size(92, 30)
>> "%DIALOG_PS%" echo $cancelButton.DialogResult = [System.Windows.Forms.DialogResult]::Cancel
>> "%DIALOG_PS%" echo $form.Controls.Add($cancelButton)
>> "%DIALOG_PS%" echo $form.AcceptButton = $okButton
>> "%DIALOG_PS%" echo $form.CancelButton = $cancelButton
>> "%DIALOG_PS%" echo $browseButton.Add_Click({
>> "%DIALOG_PS%" echo     $folderDialog = New-Object System.Windows.Forms.FolderBrowserDialog
>> "%DIALOG_PS%" echo     $folderDialog.Description = 'Select parent folder'
>> "%DIALOG_PS%" echo     $folderDialog.ShowNewFolderButton = $true
>> "%DIALOG_PS%" echo     $current = $pathBox.Text.Trim()
>> "%DIALOG_PS%" echo     $leaf = $env:DEFAULT_INSTALL_NAME
>> "%DIALOG_PS%" echo     $parent = $env:DEFAULT_PARENT
>> "%DIALOG_PS%" echo     try {
>> "%DIALOG_PS%" echo         if (-not [string]::IsNullOrWhiteSpace($current)) {
>> "%DIALOG_PS%" echo             $trimmed = $current.TrimEnd('\', '/')
>> "%DIALOG_PS%" echo             $currentLeaf = [System.IO.Path]::GetFileName($trimmed)
>> "%DIALOG_PS%" echo             if (-not [string]::IsNullOrWhiteSpace($currentLeaf)) { $leaf = $currentLeaf }
>> "%DIALOG_PS%" echo             $currentParent = [System.IO.Path]::GetDirectoryName($trimmed)
>> "%DIALOG_PS%" echo             if ([System.IO.Directory]::Exists($currentParent)) { $parent = $currentParent }
>> "%DIALOG_PS%" echo         }
>> "%DIALOG_PS%" echo     } catch {}
>> "%DIALOG_PS%" echo     if ([System.IO.Directory]::Exists($parent)) { $folderDialog.SelectedPath = $parent }
>> "%DIALOG_PS%" echo     if ($folderDialog.ShowDialog($form) -eq [System.Windows.Forms.DialogResult]::OK) {
>> "%DIALOG_PS%" echo         $pathBox.Text = [System.IO.Path]::Combine($folderDialog.SelectedPath, $leaf)
>> "%DIALOG_PS%" echo     }
>> "%DIALOG_PS%" echo })
>> "%DIALOG_PS%" echo if ($form.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK) { exit 2 }
>> "%DIALOG_PS%" echo $target = $pathBox.Text.Trim()
>> "%DIALOG_PS%" echo if ([string]::IsNullOrWhiteSpace($target)) { exit 2 }
>> "%DIALOG_PS%" echo try { $fullTarget = [System.IO.Path]::GetFullPath($target) } catch { [System.Windows.Forms.MessageBox]::Show('Invalid path.', $env:DIALOG_TITLE, 'OK', 'Error'); exit 1 }
>> "%DIALOG_PS%" echo $fullTarget

for /f "usebackq delims=" %%I in (`powershell.exe -NoProfile -STA -ExecutionPolicy Bypass -File "%DIALOG_PS%" 2^>nul`) do set "TARGET_DIR=%%I"
set "DIALOG_CODE=%ERRORLEVEL%"
del "%DIALOG_PS%" >nul 2>nul

if "%DIALOG_CODE%"=="0" (
    if defined TARGET_DIR exit /b 0
    exit /b 2
)
exit /b %DIALOG_CODE%

:remember_zip
set /a ZIP_COUNT+=1
set "ARCHIVE_PATH=%~1"
for %%Z in ("%~1") do set "ARCHIVE_BASENAME=%%~nZ"
exit /b 0

:cancelled
if defined TEMP_EXTRACT rmdir /s /q "%TEMP_EXTRACT%" >nul 2>nul
echo.
echo Installation cancelled.
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

:target_inside_source
echo.
echo The target folder cannot be inside the source folder:
echo %TARGET_DIR%
echo.
echo Choose another folder, for example:
echo C:\yadisk_uploader
goto fail

:copy_failed
echo.
echo Cannot copy app files. Copy exit code: %COPY_CODE%
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
