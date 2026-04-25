param (
    [Parameter(Mandatory = $false)]
    [switch]$Dev
)

####################################################################

function Remove-Folders {
    param (
        [Parameter(Mandatory=$true)]
        [string[]]$Paths
    )

    foreach ($Path in $Paths) {
        if (Test-Path $Path) {
            Write-Output "Removing $Path..."
            Remove-Item -Path $Path -Recurse -Force
        } else {
            Write-Output "Skipping $Path as it does not exist."
        }
    }
}

####################################################################

Write-Output "Building LOLauncher..."
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

Write-Output "Cleaning Up..."
Remove-Folders -Paths @(".\dist", ".\build")

Write-Output "Syncing Dependencies..."
& uv sync --locked --python 3.11 --group dev

Write-Output "Building Executable..."

$InstallerArgsDebug = @(
    "--noconsole",
    "--add-data",
    ".\src\assets\*.png;.\assets",
    "--add-data",
    ".\src\assets\*.ico;.\assets",
#    "--add-data",
#    ".\src\assets\*.pdf;.\assets",
    "--collect-data",
    "qfluentwidgets",
    "--collect-submodules",
    "qfluentwidgets",
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
    & uv run --locked --group dev pyinstaller @InstallerArgsDebug
}
else
{
    & uv run --locked --group dev pyinstaller @InstallerArgs
}

if ($Dev)
{
    Write-Output "Debug mode enabled, skipping compression..."
    & .\dist\LOLauncher\LOLauncher.exe
}
else
{
    Write-Output "Creating Version File..."
    & uv run --locked --group dev create-version-file metadata.yml --outfile file_version_info.txt

    Write-Output "Setting Version..."
    & uv run --locked --group dev pyi-set_version .\file_version_info.txt .\dist\LOLauncher.exe

    Write-Output "Compressing Files..."
    Compress-Archive -Path .\dist\LOLauncher.exe -DestinationPath .\dist\LOLauncher.zip
}

Write-Output "Done!"
