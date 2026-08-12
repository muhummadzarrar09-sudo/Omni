# Shared primary-platform detection for Windows install and qualification paths.
# Windows build numbers alone do not distinguish Windows 11 from Windows Server.

function Get-OmniWindowsPlatform {
    if ($env:OS -ne "Windows_NT") {
        throw "The OMNI primary path requires Windows 11 x64."
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

function Assert-OmniWindows11X64 {
    $platform = Get-OmniWindowsPlatform
    if (-not $platform.Is64Bit -or $platform.Architecture -ne "X64") {
        throw "The primary path requires Windows x64; found OS architecture $($platform.Architecture)."
    }
    if ($platform.ProductType -ne 1) {
        throw "The primary path requires the Windows 11 workstation product. Windows Server and domain-controller products are unsupported (caption '$($platform.Caption)', product type $($platform.ProductType))."
    }
    if ($platform.Build -lt 22000) {
        throw "The primary path requires Windows 11 x64 (build 22000 or newer); found build $($platform.Build)."
    }
    return $platform
}
