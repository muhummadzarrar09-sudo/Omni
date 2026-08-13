# Remove OMNI checkout-generated installation assets.
# User data is preserved unless -RemoveUserData is explicitly supplied.

[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = "High")]
param(
    [switch]$RemoveUserData
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version 3.0
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $root
$python = Join-Path $root ".venv\Scripts\python.exe"

function Get-OmniDataDirFallback {
    if ($env:OMNI_DATA_DIR) {
        if (-not [IO.Path]::IsPathRooted($env:OMNI_DATA_DIR)) {
            throw "OMNI_DATA_DIR must be an absolute path for safe uninstall."
        }
        return [IO.Path]::GetFullPath($env:OMNI_DATA_DIR)
    }
    $localData = [Environment]::GetFolderPath([Environment+SpecialFolder]::LocalApplicationData)
    if (-not $localData) {
        $localData = $env:LOCALAPPDATA
    }
    if (-not $localData) {
        throw "The canonical Windows user-data root could not be resolved."
    }
    return [IO.Path]::GetFullPath((Join-Path $localData "OMNI"))
}

function Assert-NotReparsePoint {
    param([Parameter(Mandatory = $true)][string]$Path)
    $attributes = [IO.File]::GetAttributes($Path)
    if (($attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw "Refusing deletion through a filesystem reparse point: $Path"
    }
}

function Assert-SafeDataTree {
    param([Parameter(Mandatory = $true)][string]$Path)

    # Reject a reparse-point target or ancestor before traversing anything.
    $cursor = [IO.DirectoryInfo]::new($Path)
    while ($null -ne $cursor) {
        if ($cursor.Exists) {
            Assert-NotReparsePoint $cursor.FullName
        }
        $cursor = $cursor.Parent
    }

    # Recurse manually without ever entering a reparse point. Unknown or
    # inaccessible entries fail closed instead of allowing a partial deletion.
    $pending = [System.Collections.Generic.Stack[string]]::new()
    $pending.Push($Path)
    while ($pending.Count -gt 0) {
        $directory = $pending.Pop()
        foreach ($entry in [IO.Directory]::GetFileSystemEntries($directory)) {
            Assert-NotReparsePoint $entry
            $attributes = [IO.File]::GetAttributes($entry)
            if (($attributes -band [IO.FileAttributes]::Directory) -ne 0) {
                $pending.Push($entry)
            }
        }
    }
}

$dataDir = Get-OmniDataDirFallback
if (Test-Path $python) {
    $configJson = (& $python -m omni_v2.core.runtime_cli --json config show | Out-String)
    if ($LASTEXITCODE -ne 0) {
        throw "The canonical user-data path could not be resolved from the managed environment."
    }
    $dataDir = [string](($configJson | ConvertFrom-Json).data_dir)

    if (-not $PSCmdlet.ShouldProcess("OMNI owned runtime", "Stop before uninstall")) {
        Write-Host "No installation assets or user data were removed because runtime shutdown was skipped."
        return
    }
    & $python -m omni_v2.core.runtime_cli stop
    if ($LASTEXITCODE -ne 0) {
        throw "Uninstall refused because the owned process tree could not be stopped safely."
    }
} else {
    $runtimeState = Join-Path $dataDir "run\runtime.json"
    $lifecycleLock = Join-Path $dataDir "run\lifecycle.lock"
    if ((Test-Path -LiteralPath $runtimeState) -or (Test-Path -LiteralPath $lifecycleLock)) {
        throw "Managed runtime state exists but .venv is unavailable. Restore the environment and stop OMNI before uninstalling."
    }
}

$removedGenerated = [System.Collections.Generic.List[string]]::new()
$skippedGenerated = [System.Collections.Generic.List[string]]::new()
$generated = @(
    (Join-Path $root ".venv"),
    (Join-Path $root "frontend_next\node_modules"),
    (Join-Path $root "frontend_next\.next")
)
foreach ($path in $generated) {
    if (-not (Test-Path -LiteralPath $path)) {
        continue
    }
    Assert-SafeDataTree $path
    if ($PSCmdlet.ShouldProcess($path, "Remove generated installation asset")) {
        Remove-Item -LiteralPath $path -Recurse -Force
        if (Test-Path -LiteralPath $path) {
            throw "Generated installation asset still exists after removal: $path"
        }
        [void]$removedGenerated.Add($path)
    } else {
        [void]$skippedGenerated.Add($path)
    }
}

$userDataRemoved = $false
$userDataSkipped = $false
$userDataMissing = $false
if ($RemoveUserData) {
    if (-not $dataDir -or -not [IO.Path]::IsPathRooted($dataDir)) {
        throw "The canonical user-data path is absent or not absolute."
    }
    $fullData = [IO.Path]::GetFullPath($dataDir).TrimEnd("\")
    if ($fullData.Split([IO.Path]::DirectorySeparatorChar) -match "~") {
        throw "Refusing a short-name-like or tilde-containing user-data path: $fullData"
    }
    if (Test-Path -LiteralPath $fullData) {
        $dataItem = Get-Item -LiteralPath $fullData -Force
        if (-not $dataItem.PSIsContainer) {
            throw "Canonical user data is not a directory: $fullData"
        }
        $fullData = [IO.Path]::GetFullPath($dataItem.FullName).TrimEnd("\")
    }

    $fullRoot = [IO.Path]::GetFullPath($root).TrimEnd("\")
    $homePath = [Environment]::GetFolderPath([Environment+SpecialFolder]::UserProfile)
    if (-not $homePath) {
        throw "The current user's home directory could not be resolved safely."
    }
    $fullHome = [IO.Path]::GetFullPath($homePath).TrimEnd("\")
    $driveRoot = [IO.Path]::GetPathRoot($fullData).TrimEnd("\")
    $comparison = [StringComparison]::OrdinalIgnoreCase
    $separator = [string][IO.Path]::DirectorySeparatorChar
    $insideRepository = $fullData.StartsWith($fullRoot + $separator, $comparison)
    $containsRepository = $fullRoot.StartsWith($fullData + $separator, $comparison)
    $containsHome = $fullHome.StartsWith($fullData + $separator, $comparison)
    if (
        $fullData -eq $fullRoot -or
        $fullData -eq $fullHome -or
        $fullData -eq $driveRoot -or
        $insideRepository -or
        $containsRepository -or
        $containsHome
    ) {
        throw "Refusing unsafe user-data deletion target (repository, home, or an enclosing path): $fullData"
    }
    if (-not (Test-Path -LiteralPath $fullData)) {
        $userDataMissing = $true
    } else {
        Assert-SafeDataTree $fullData
        if ($PSCmdlet.ShouldProcess($fullData, "Permanently remove OMNI user data")) {
            Remove-Item -LiteralPath $fullData -Recurse -Force
            if (Test-Path -LiteralPath $fullData) {
                throw "OMNI user data still exists after removal: $fullData"
            }
            $userDataRemoved = $true
        } else {
            $userDataSkipped = $true
        }
    }
}

if ($removedGenerated.Count -gt 0) {
    Write-Host "Removed generated installation assets: $($removedGenerated -join ', ')"
} else {
    Write-Host "No generated installation assets were removed."
}
if ($skippedGenerated.Count -gt 0) {
    Write-Host "Skipped generated installation assets: $($skippedGenerated -join ', ')"
}

if ($RemoveUserData) {
    if ($userDataRemoved) {
        Write-Host "Removed OMNI user data: $fullData"
    } elseif ($userDataSkipped) {
        Write-Host "OMNI user data was not removed because deletion was skipped: $fullData"
    } elseif ($userDataMissing) {
        Write-Host "OMNI user data was already absent: $fullData"
    }
} elseif ($dataDir) {
    Write-Host "Preserved OMNI user data at: $dataDir"
    Write-Host "To remove it explicitly, rerun with -RemoveUserData."
}
