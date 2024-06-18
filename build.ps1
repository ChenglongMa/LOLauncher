param (
    [Parameter(Mandatory = $false)]
    [switch]$Dev
)

Write-Output "Building LOLauncher..."
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
$UserDirectory = $env:USERPROFILE

Write-Output "Cleaning Up..."
Remove-Item -Path .\build\* -Recurse -Force
Remove-Item -Path .\dist\* -Recurse -Force

Write-Output "Building..."

$InstallerArgsDebug = @(
    "--noconsole",
    "--add-data",
    ".\src\assets\*.png;.\assets",
    "--add-data",
    ".\src\assets\*.ico;.\assets",
    "--paths",
    ".\src",
    "--clean",
    "--icon",
    ".\src\assets\icon.ico",
    "--name",
    "LOLauncher",
    ".\src\main.py"
)

$InstallerArgs = $InstallerArgsDebug + @(
    "--log-level",
    "WARN",
    "--onefile"
)

if ($Dev)
{
    .\venv\Scripts\pyinstaller.exe $InstallerArgsDebug
}
else
{
    .\venv\Scripts\pyinstaller.exe $InstallerArgs
}

if ($Dev)
{
    Write-Output "Debug mode enabled, skipping compression..."
    & .\dist\LOLauncher\LOLauncher.exe
}
else
{
    Write-Output "Creating Version File..."
    $CreateVersionFileApp = Join-Path -Path $UserDirectory -ChildPath "\anaconda3\envs\py312\Scripts\create-version-file.exe"
    & $CreateVersionFileApp metadata.yml --outfile file_version_info.txt

    Write-Output "Setting Version..."
    .\venv\Scripts\pyi-set_version.exe ./file_version_info.txt ./dist/LOLauncher.exe

    Write-Output "Compressing Files..."
    Compress-Archive -Path .\dist\LOLauncher.exe -DestinationPath .\dist\LOLauncher.zip
}

Write-Output "Done!"