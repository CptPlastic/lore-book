[CmdletBinding()]
param(
    [ValidateSet("pipx", "pip")]
    [string]$Mode = "pipx",
    [string]$SourcePath
)

$ErrorActionPreference = "Stop"

function Test-Command {
    param([Parameter(Mandatory = $true)][string]$Name)
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

function Invoke-Py {
    param([Parameter(Mandatory = $true)][string[]]$Args)
    if (Test-Command "py") {
        & py @Args
        return
    }
    if (Test-Command "python") {
        & python @Args
        return
    }
    throw "Python was not found. Install Python 3.10+ from https://www.python.org/downloads/windows/ and re-run this script."
}

Write-Host "[lore/windows] Bootstrap starting (mode=$Mode)"

if ($Mode -eq "pipx") {
    Write-Host "[lore/windows] Installing/upgrading pip + pipx"
    Invoke-Py -Args @("-m", "pip", "install", "--user", "--upgrade", "pip", "pipx")

    Write-Host "[lore/windows] Ensuring pipx path"
    Invoke-Py -Args @("-m", "pipx", "ensurepath")

    if ([string]::IsNullOrWhiteSpace($SourcePath)) {
        Write-Host "[lore/windows] Installing lore-book from PyPI via pipx"
        Invoke-Py -Args @("-m", "pipx", "install", "--force", "lore-book")
    }
    else {
        Write-Host "[lore/windows] Installing lore-book from source path: $SourcePath"
        Invoke-Py -Args @("-m", "pipx", "install", "--force", $SourcePath)
    }

    Write-Host "[lore/windows] Verifying CLI"
    Invoke-Py -Args @("-m", "pipx", "run", "--spec", "lore-book", "lore", "version")
}
else {
    if ([string]::IsNullOrWhiteSpace($SourcePath)) {
        Write-Host "[lore/windows] Installing lore-book from PyPI via pip"
        Invoke-Py -Args @("-m", "pip", "install", "--user", "--upgrade", "lore-book")
    }
    else {
        Write-Host "[lore/windows] Installing lore-book from source path: $SourcePath"
        Invoke-Py -Args @("-m", "pip", "install", "--user", "--upgrade", $SourcePath)
    }

    Write-Host "[lore/windows] Verifying package import"
    Invoke-Py -Args @("-c", "import lore; print(f'lore {lore.__version__}')")
}

Write-Host "[lore/windows] Install complete."
Write-Host "[lore/windows] If 'lore' is not recognized yet, open a new terminal session."
