@echo off
chcp 65001 >nul
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

echo Установка %APP_NAME%
echo.
echo Не найден файл "%EXE_NAME%" или архив "%APP_NAME%.zip" рядом с установщиком.
echo Положите этот файл рядом с распакованной программой или рядом с архивом программы.
echo.
echo Нажмите любую клавишу, чтобы закрыть окно.
pause >nul
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
set "DIALOG_TITLE=Установка %APP_NAME%"

where powershell.exe >nul 2>nul
if errorlevel 1 goto powershell_missing

call :choose_target_dialog
if errorlevel 2 goto cancelled
if errorlevel 1 goto prompt_target_console
goto normalize_target

:prompt_target_console
echo Установка %APP_NAME%
echo.
if "%INSTALL_MODE%"=="archive" (
    echo Архив:
    echo %ARCHIVE_PATH%
) else (
    echo Папка программы:
    echo %SOURCE_DIR%
)
echo.
echo Введите папку, куда установить программу.
echo Например: C:\yadisk_uploader
echo.
echo Нажмите Enter, чтобы использовать:
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
set "TEMP_EXTRACT_ENV=%TEMP_EXTRACT%"
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; try { [System.IO.Directory]::CreateDirectory($env:TEMP_EXTRACT_ENV) | Out-Null } catch { Write-Host ('Не удалось создать временную папку: ' + $_.Exception.Message); exit 1 }"
if errorlevel 1 goto extract_prepare_failed

set "ARCHIVE_PATH_ENV=%ARCHIVE_PATH%"
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; try { Add-Type -AssemblyName System.IO.Compression.FileSystem; [System.IO.Compression.ZipFile]::ExtractToDirectory($env:ARCHIVE_PATH_ENV, $env:TEMP_EXTRACT_ENV) } catch { Write-Host ('Не удалось распаковать архив: ' + $_.Exception.Message); exit 1 }"
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
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; function Copy-Directory($from,$to){ [System.IO.Directory]::CreateDirectory($to) | Out-Null; foreach($dir in [System.IO.Directory]::GetDirectories($from)){ Copy-Directory $dir ([System.IO.Path]::Combine($to,[System.IO.Path]::GetFileName($dir))) }; foreach($file in [System.IO.Directory]::GetFiles($from)){ [System.IO.File]::Copy($file,[System.IO.Path]::Combine($to,[System.IO.Path]::GetFileName($file)),$true) } }; try { $source=[System.IO.Path]::GetFullPath($env:SOURCE_DIR_ENV).TrimEnd([char[]]@('\','/')); $target=[System.IO.Path]::GetFullPath($env:TARGET_DIR_ENV).TrimEnd([char[]]@('\','/')); if ([string]::Equals($source,$target,[System.StringComparison]::OrdinalIgnoreCase)) { exit 10 }; if ($target.StartsWith($source + '\',[System.StringComparison]::OrdinalIgnoreCase)) { exit 11 }; Copy-Directory $source $target } catch { Write-Host ('Не удалось скопировать файлы программы: ' + $_.Exception.Message); exit 1 }"
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
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; try { $target=$env:SHORTCUT_TARGET; $name=$env:SHORTCUT_NAME_ENV; $desktop=[Environment]::GetFolderPath('Desktop'); $shortcutPath=Join-Path $desktop ($name + '.lnk'); $shell=New-Object -ComObject WScript.Shell; $shortcut=$shell.CreateShortcut($shortcutPath); $shortcut.TargetPath=$target; $shortcut.WorkingDirectory=Split-Path -Parent $target; $shortcut.IconLocation=$target + ',0'; $shortcut.Save() } catch { Write-Host ('Не удалось создать ярлык на рабочем столе: ' + $_.Exception.Message); exit 1 }"
if errorlevel 1 goto shortcut_failed

echo.
echo Программа установлена в папку:
echo %TARGET_DIR%
echo.
echo На рабочем столе создан ярлык:
echo %SHORTCUT_NAME%.lnk
echo.
echo Нажмите любую клавишу, чтобы закрыть окно.
pause >nul
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
>> "%DIALOG_PS%" echo $form.ClientSize = New-Object System.Drawing.Size(660, 145)
>> "%DIALOG_PS%" echo $label = New-Object System.Windows.Forms.Label
>> "%DIALOG_PS%" echo $label.Text = 'Папка установки:'
>> "%DIALOG_PS%" echo $label.AutoSize = $true
>> "%DIALOG_PS%" echo $label.Location = New-Object System.Drawing.Point(12, 18)
>> "%DIALOG_PS%" echo $form.Controls.Add($label)
>> "%DIALOG_PS%" echo $pathBox = New-Object System.Windows.Forms.TextBox
>> "%DIALOG_PS%" echo $pathBox.Text = $env:DEFAULT_TARGET
>> "%DIALOG_PS%" echo $pathBox.Location = New-Object System.Drawing.Point(12, 42)
>> "%DIALOG_PS%" echo $pathBox.Size = New-Object System.Drawing.Size(530, 23)
>> "%DIALOG_PS%" echo $form.Controls.Add($pathBox)
>> "%DIALOG_PS%" echo $browseButton = New-Object System.Windows.Forms.Button
>> "%DIALOG_PS%" echo $browseButton.Text = 'Обзор...'
>> "%DIALOG_PS%" echo $browseButton.Location = New-Object System.Drawing.Point(552, 40)
>> "%DIALOG_PS%" echo $browseButton.Size = New-Object System.Drawing.Size(96, 27)
>> "%DIALOG_PS%" echo $form.Controls.Add($browseButton)
>> "%DIALOG_PS%" echo $okButton = New-Object System.Windows.Forms.Button
>> "%DIALOG_PS%" echo $okButton.Text = 'Установить'
>> "%DIALOG_PS%" echo $okButton.Location = New-Object System.Drawing.Point(424, 98)
>> "%DIALOG_PS%" echo $okButton.Size = New-Object System.Drawing.Size(108, 30)
>> "%DIALOG_PS%" echo $okButton.DialogResult = [System.Windows.Forms.DialogResult]::OK
>> "%DIALOG_PS%" echo $form.Controls.Add($okButton)
>> "%DIALOG_PS%" echo $cancelButton = New-Object System.Windows.Forms.Button
>> "%DIALOG_PS%" echo $cancelButton.Text = 'Отмена'
>> "%DIALOG_PS%" echo $cancelButton.Location = New-Object System.Drawing.Point(540, 98)
>> "%DIALOG_PS%" echo $cancelButton.Size = New-Object System.Drawing.Size(108, 30)
>> "%DIALOG_PS%" echo $cancelButton.DialogResult = [System.Windows.Forms.DialogResult]::Cancel
>> "%DIALOG_PS%" echo $form.Controls.Add($cancelButton)
>> "%DIALOG_PS%" echo $form.AcceptButton = $okButton
>> "%DIALOG_PS%" echo $form.CancelButton = $cancelButton
>> "%DIALOG_PS%" echo $browseButton.Add_Click({
>> "%DIALOG_PS%" echo     $folderDialog = New-Object System.Windows.Forms.FolderBrowserDialog
>> "%DIALOG_PS%" echo     $folderDialog.Description = 'Выберите папку, внутри которой будет создана папка программы'
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
>> "%DIALOG_PS%" echo try { $fullTarget = [System.IO.Path]::GetFullPath($target) } catch { [System.Windows.Forms.MessageBox]::Show('Указан некорректный путь установки.', $env:DIALOG_TITLE, 'OK', 'Error'); exit 1 }
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
echo Установка отменена.
echo.
echo Нажмите любую клавишу, чтобы закрыть окно.
pause >nul
exit /b 0

:powershell_missing
echo.
echo Не найден Windows PowerShell.
echo Установщик использует встроенный powershell.exe, чтобы показать окно выбора
echo папки, распаковать архив, скопировать файлы и создать ярлык.
echo.
echo Запустите установщик на обычной Windows-системе или включите Windows PowerShell.
goto fail

:extract_prepare_failed
echo.
echo Не удалось создать временную папку для распаковки:
echo %TEMP_EXTRACT%
echo.
echo Проверьте, что папка TEMP существует и доступна для записи:
echo %TEMP%
goto fail

:extract_failed
echo.
echo Не удалось распаковать архив:
echo %ARCHIVE_PATH%
echo.
echo Проверьте, что архив существует, не поврежден и не заблокирован Windows.
goto fail

:exe_not_found
echo.
echo В архиве не найден основной файл программы:
echo %EXE_NAME%
echo.
echo В архиве должна быть папка программы или файл %EXE_NAME%.
goto fail

:target_prepare_failed
echo.
echo Не удалось создать папку установки:
echo %TARGET_DIR%
echo.
echo Проверьте права на запись в выбранную папку.
goto fail

:target_inside_source
echo.
echo Нельзя устанавливать программу внутрь папки, из которой запущен установщик:
echo %TARGET_DIR%
echo.
echo Выберите другую папку, например:
echo C:\yadisk_uploader
goto fail

:copy_failed
echo.
echo Не удалось скопировать файлы программы.
echo Откуда копируем:
echo %SOURCE_DIR%
echo Куда копируем:
echo %TARGET_DIR%
echo.
echo Код ошибки копирования: %COPY_CODE%
echo Проверьте права на запись, свободное место на диске и закрыты ли файлы программы.
goto fail

:installed_exe_not_found
echo.
echo После копирования не найден основной файл программы:
echo %TARGET_EXE%
echo.
echo Возможно, архив собран неправильно или файлы программы были удалены.
goto fail

:shortcut_failed
echo.
echo Файлы программы скопированы, но ярлык на рабочем столе создать не удалось.
echo Файл программы:
echo %TARGET_EXE%
echo.
echo Проверьте доступ к рабочему столу. Программу можно запустить вручную из папки установки.
goto fail

:fail
if defined TEMP_EXTRACT rmdir /s /q "%TEMP_EXTRACT%" >nul 2>nul
echo.
echo Нажмите любую клавишу, чтобы закрыть окно.
pause >nul
exit /b 1
