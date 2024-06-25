param (
    [Parameter(Mandatory = $false)]
    [switch]$Dev
)

Write-Output "Building LOLauncher..."
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

Write-Output "Cleaning Up..."
Remove-Item -Path .\build\* -Recurse -Force
Remove-Item -Path .\dist\* -Recurse -Force

Write-Output "Building..."

Write-Output "Creating Virtual Environment..."
$EnvName = "prod_venv"

.\venv\Scripts\python.exe -m venv $EnvName

Write-Output "Activating Virtual Environment..."
$ActivateScript = Join-Path -Path ".\" -ChildPath "$EnvName\Scripts\Activate.ps1"
. $ActivateScript

Write-Output "Installing Dependencies..."
& .\$EnvName\Scripts\python.exe -m pip install --upgrade pip
& .\$EnvName\Scripts\pip.exe install -r requirements.txt

Write-Output "Building Executable..."

$InstallerArgsDebug = @(
    "--noconsole",
    "--add-data",
    ".\src\assets\*.png;.\assets",
    "--add-data",
    ".\src\assets\*.ico;.\assets",
    "--add-data",
    ".\src\assets\*.pdf;.\assets",
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
    & .\$EnvName\Scripts\pyinstaller.exe $InstallerArgsDebug
}
else
{
    & .\$EnvName\Scripts\pyinstaller.exe $InstallerArgs
}

if ($Dev)
{
    Write-Output "Debug mode enabled, skipping compression..."
    & .\dist\LOLauncher\LOLauncher.exe
}
else
{
    Write-Output "Creating Version File..."
    & .\venv\Scripts\create-version-file.exe metadata.yml --outfile file_version_info.txt

    Write-Output "Setting Version..."
    & .\$EnvName\Scripts\pyi-set_version.exe ./file_version_info.txt ./dist/LOLauncher.exe

    Write-Output "Compressing Files..."
    Compress-Archive -Path .\dist\LOLauncher.exe -DestinationPath .\dist\LOLauncher.zip
}

Write-Output "Done!"