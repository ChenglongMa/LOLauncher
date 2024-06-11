Write-Output "Building LOLauncher..."
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
$UserDirectory = $env:USERPROFILE

Write-Output "Cleaning Up..."
Remove-Item -Path .\build\* -Recurse -Force
Remove-Item -Path .\dist\* -Recurse -Force

Write-Output "Creating Version File..."
$CreateVersionFileApp = Join-Path -Path $UserDirectory -ChildPath "\anaconda3\envs\py312\Scripts\create-version-file.exe"
& $CreateVersionFileApp metadata.yml --outfile file_version_info.txt

Write-Output "Building..."
.\venv\Scripts\pyinstaller.exe --log-level WARN --onefile --clean --icon .\icon.ico --name LOLauncher .\main.py

Write-Output "Setting Version..."
.\venv\Scripts\pyi-set_version.exe ./file_version_info.txt ./dist/LOLauncher.exe

Write-Output "Compressing Files..."
Compress-Archive -Path .\dist\LOLauncher.exe -DestinationPath .\dist\LOLauncher.zip

Write-Output "Done!"