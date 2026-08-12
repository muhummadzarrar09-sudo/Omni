# Shared platform detection for native Windows install and qualification paths.
# Windows build numbers alone do not distinguish Windows 11 from Windows Server.

function Get-OmniWindowsPlatform {
    if ($env:OS -ne "Windows_NT") {
        throw "The OMNI Windows path requires a Windows 11 workstation."
    }

    try {
        $operatingSystem = Get-CimInstance -ClassName Win32_OperatingSystem -ErrorAction Stop
    } catch {
        throw "Could not determine the Windows product type via Win32_OperatingSystem: $($_.Exception.Message)"
    }

    $architecture = [System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture.ToString()
    [PSCustomObject]@{
        Caption = [string]$operatingSystem.Caption
        Version = [string]$operatingSystem.Version
        Build = [int]$operatingSystem.BuildNumber
        ProductType = [int]$operatingSystem.ProductType
        Architecture = $architecture
        Is64Bit = [bool][Environment]::Is64BitOperatingSystem
    }
}

function Get-OmniWindowsArchitectureSlug {
    param([Parameter(Mandatory = $true)]$Platform)
    switch ([string]$Platform.Architecture) {
        "X64" { return "x86_64" }
        "Arm64" { return "arm64" }
        default { throw "Unsupported Windows architecture $($Platform.Architecture); OMNI requires native X64 or Arm64." }
    }
}

function Get-OmniPythonMachineNames {
    param([Parameter(Mandatory = $true)]$Platform)
    switch ([string]$Platform.Architecture) {
        "X64" { return @("amd64", "x86_64") }
        "Arm64" { return @("arm64", "aarch64") }
        default { throw "Unsupported Windows architecture $($Platform.Architecture)." }
    }
}

function Assert-OmniWindows11 {
    $platform = Get-OmniWindowsPlatform
    if (-not $platform.Is64Bit -or $platform.Architecture -notin @("X64", "Arm64")) {
        throw "The Windows path requires native 64-bit X64 or Arm64 Windows; found OS architecture $($platform.Architecture)."
    }
    if ($platform.ProductType -ne 1) {
        throw "The Windows path requires the Windows 11 workstation product. Windows Server and domain-controller products are unsupported (caption '$($platform.Caption)', product type $($platform.ProductType))."
    }
    if ($platform.Build -lt 22000) {
        throw "The Windows path requires Windows 11 build 22000 or newer; found build $($platform.Build)."
    }
    return $platform
}
