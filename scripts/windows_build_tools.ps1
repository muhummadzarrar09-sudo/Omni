# Native Visual Studio Build Tools discovery and architecture proof for B02.
# Dot-source this file, then call Enter-OmniWindowsNativeBuildEnvironment.

Set-StrictMode -Version 3.0

function Get-OmniBuildContract {
    $root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
    $path = Join-Path $root "quality\windows-native-build-contract.json"
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Native build contract is absent: $path"
    }
    return (Get-Content -Raw -LiteralPath $path) | ConvertFrom-Json
}

function Import-OmniBatchEnvironment {
    param(
        [Parameter(Mandatory = $true)][string]$BatchFile,
        [Parameter(Mandatory = $true)][string]$Arguments
    )

    if (-not (Test-Path -LiteralPath $BatchFile -PathType Leaf)) {
        throw "Visual Studio environment script is absent: $BatchFile"
    }
    $command = '"{0}" {1} >nul && set' -f $BatchFile, $Arguments
    $lines = @(& $env:ComSpec /d /s /c $command)
    if ($LASTEXITCODE -ne 0 -or $lines.Count -eq 0) {
        throw "Visual Studio environment initialization failed: $BatchFile $Arguments"
    }
    foreach ($line in $lines) {
        # cmd.exe emits pseudo variables such as '=C:=C:\path'; they cannot be
        # represented by PowerShell's Env: provider and are not build inputs.
        if ($line -match '^([^=][^=]*)=(.*)$') {
            [Environment]::SetEnvironmentVariable($matches[1], $matches[2], "Process")
        }
    }
}

function Enter-OmniWindowsNativeBuildEnvironment {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [ValidateSet("x86_64", "arm64")]
        [string]$ArchitectureSlug
    )

    $contract = Get-OmniBuildContract
    $architectureContract = $contract.visual_studio.architectures.$ArchitectureSlug
    if ($null -eq $architectureContract) {
        throw "Native build contract has no $ArchitectureSlug architecture entry."
    }

    $vswhere = Join-Path ${env:ProgramFiles(x86)} "Microsoft Visual Studio\Installer\vswhere.exe"
    if (-not (Test-Path -LiteralPath $vswhere -PathType Leaf)) {
        throw "Visual Studio 2022 Build Tools were not found. Install the documented C++ workload and Windows 11 SDK before running an all-profile build."
    }
    $requiredComponents = @(
        [string]$contract.visual_studio.workload_component,
        [string]$architectureContract.msvc_component,
        [string]$contract.visual_studio.windows_sdk_component
    )
    $vswhereArguments = @("-latest", "-products", "*", "-requires") + $requiredComponents + @("-format", "json", "-utf8")
    $installationJson = (& $vswhere @vswhereArguments | Out-String)
    $installations = @($installationJson | ConvertFrom-Json)
    if ($LASTEXITCODE -ne 0 -or $installations.Count -ne 1) {
        throw "Visual Studio Build Tools do not provide the required components for native $ArchitectureSlug: $($requiredComponents -join ', ')"
    }
    $installation = $installations[0]
    $installationVersion = [version][string]$installation.installationVersion
    if ($installationVersion.Major -ne 17) {
        throw "Visual Studio 2022 (17.x) is required; found installation version $installationVersion."
    }
    $installationPath = [string]$installation.installationPath
    $vcvarsall = Join-Path $installationPath "VC\Auxiliary\Build\vcvarsall.bat"
    $vcvarsArgument = if ($ArchitectureSlug -eq "arm64") { "arm64" } else { "x64" }
    $windowsSdkContractVersion = [string]$contract.visual_studio.windows_sdk_version
    # Select the governed SDK explicitly. Merely requiring the component does
    # not stop vcvarsall from choosing a newer installed SDK by default.
    $vcvarsArguments = "$vcvarsArgument $windowsSdkContractVersion"
    Import-OmniBatchEnvironment -BatchFile $vcvarsall -Arguments $vcvarsArguments

    $compiler = Get-Command cl.exe -ErrorAction SilentlyContinue
    if ($null -eq $compiler) {
        throw "vcvarsall completed but cl.exe is absent from PATH."
    }
    $compilerPath = (Resolve-Path -LiteralPath $compiler.Source).Path
    $expectedFragment = [string]$architectureContract.compiler_path_fragment
    if ($compilerPath.IndexOf($expectedFragment, [StringComparison]::OrdinalIgnoreCase) -lt 0) {
        throw "Compiler host/target architecture mismatch: expected path fragment '$expectedFragment', found '$compilerPath'. Emulated or cross-host compiler evidence is rejected."
    }
    $linker = Get-Command link.exe -ErrorAction SilentlyContinue
    if ($null -eq $linker) {
        throw "vcvarsall completed but link.exe is absent from PATH."
    }
    $linkerPath = (Resolve-Path -LiteralPath $linker.Source).Path
    $expectedLinkerFragment = [string]$architectureContract.linker_path_fragment
    if ($linkerPath.IndexOf($expectedLinkerFragment, [StringComparison]::OrdinalIgnoreCase) -lt 0) {
        throw "Linker host/target architecture mismatch: expected path fragment '$expectedLinkerFragment', found '$linkerPath'."
    }
    if ([string]::IsNullOrWhiteSpace([string]$env:WindowsSDKVersion)) {
        throw "vcvarsall did not select a Windows SDK version."
    }
    $windowsSdkVersion = ([string]$env:WindowsSDKVersion).Trim().TrimEnd([char]'\')
    if ($windowsSdkVersion -ne $windowsSdkContractVersion) {
        throw "Selected Windows SDK version '$windowsSdkVersion' does not match the governed version '$windowsSdkContractVersion'."
    }

    $probeRoot = Join-Path ([IO.Path]::GetTempPath()) "omni-native-toolchain-$PID-$([Guid]::NewGuid().ToString('N'))"
    New-Item -ItemType Directory -Force -Path $probeRoot | Out-Null
    $source = Join-Path $probeRoot "probe.c"
    $executable = Join-Path $probeRoot "probe.exe"
    [IO.File]::WriteAllText($source, "int main(void) { return 0; }`r`n", [Text.UTF8Encoding]::new($false))
    try {
        $compilerOutput = (& $compilerPath /nologo /W4 /WX "/Fe:$executable" $source 2>&1 | Out-String).Trim()
        if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $executable -PathType Leaf)) {
            throw "Native compiler/SDK/linker probe failed: $compilerOutput"
        }
        $bytes = [IO.File]::ReadAllBytes($executable)
        if ($bytes.Length -lt 256) {
            throw "Native compiler probe emitted an invalid PE image."
        }
        $peOffset = [BitConverter]::ToInt32($bytes, 0x3c)
        if ($peOffset -lt 0 -or ($peOffset + 6) -gt $bytes.Length) {
            throw "Native compiler probe emitted an invalid PE header."
        }
        $machine = [BitConverter]::ToUInt16($bytes, $peOffset + 4)
        $expectedMachine = [Convert]::ToUInt16([string]$architectureContract.target_machine, 16)
        if ($machine -ne $expectedMachine) {
            throw ("Compiler emitted PE machine 0x{0:X4}; expected native {1} machine 0x{2:X4}." -f $machine, $ArchitectureSlug, $expectedMachine)
        }
        & $executable
        if ($LASTEXITCODE -ne 0) {
            throw "Native compiler probe executable returned $LASTEXITCODE."
        }
        return [pscustomobject][ordered]@{
            architecture_slug = $ArchitectureSlug
            visual_studio_installation = $installationPath
            visual_studio_installation_version = [string]$installationVersion
            visual_studio_product_id = [string]$installation.productId
            required_components = $requiredComponents
            vcvarsall = $vcvarsall
            compiler = $compilerPath
            compiler_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $compilerPath).Hash.ToLowerInvariant()
            linker = $linkerPath
            linker_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $linkerPath).Hash.ToLowerInvariant()
            compiler_output = $compilerOutput
            windows_sdk_version = $windowsSdkVersion
            pe_machine = ("0x{0:X4}" -f $machine)
            native_probe = "pass"
        }
    } finally {
        Remove-Item -LiteralPath $probeRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
}
