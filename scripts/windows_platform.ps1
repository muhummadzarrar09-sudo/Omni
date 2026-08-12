# Shared platform detection for native Windows install and qualification paths.
# Windows build numbers alone do not distinguish Windows 11 from Windows Server.
# Keep architecture detection compatible with both Windows PowerShell 5.1/.NET
# Framework and modern PowerShell; RuntimeInformation.OSArchitecture is absent
# on some fully supported Windows PowerShell installations.

function ConvertTo-OmniWindowsArchitecture {
    param([AllowNull()][string]$Value)

    $normalized = ([string]$Value).Trim().ToUpperInvariant()
    switch ($normalized) {
        "AMD64" { return "X64" }
        "X64" { return "X64" }
        "X86_64" { return "X64" }
        "ARM64" { return "Arm64" }
        "AARCH64" { return "Arm64" }
        "X86" { return "X86" }
        default { return $normalized }
    }
}

function Get-OmniWindowsNativeArchitecture {
    # Under WOW/emulation, PROCESSOR_ARCHITEW6432 identifies the native OS
    # architecture while PROCESSOR_ARCHITECTURE identifies the current process.
    $candidate = if ($env:PROCESSOR_ARCHITEW6432) {
        $env:PROCESSOR_ARCHITEW6432
    } else {
        $env:PROCESSOR_ARCHITECTURE
    }
    $architecture = ConvertTo-OmniWindowsArchitecture $candidate
    if ($architecture -in @("X64", "Arm64", "X86")) {
        return $architecture
    }

    # Numeric Win32_Processor.Architecture values: 9 = x64, 12 = Arm64.
    try {
        $processor = Get-CimInstance -ClassName Win32_Processor -ErrorAction Stop |
            Select-Object -First 1
        switch ([int]$processor.Architecture) {
            9 { return "X64" }
            12 { return "Arm64" }
            0 { return "X86" }
        }
    } catch { }

    # Modern PowerShell fallback. Reflection avoids resolving a property that is
    # missing from Windows PowerShell 5.1's .NET Framework at parse/evaluation.
    try {
        $runtimeType = [System.Runtime.InteropServices.RuntimeInformation]
        $property = $runtimeType.GetProperty("OSArchitecture")
        if ($null -ne $property) {
            $architecture = ConvertTo-OmniWindowsArchitecture ([string]$property.GetValue($null, $null))
            if ($architecture) { return $architecture }
        }
    } catch { }

    throw "Could not determine the native Windows architecture from the environment, Win32_Processor, or RuntimeInformation."
}

function Get-OmniPowerShellProcessArchitecture {
    if (-not [Environment]::Is64BitProcess) {
        return "X86"
    }

    $architecture = ConvertTo-OmniWindowsArchitecture $env:PROCESSOR_ARCHITECTURE
    if ($architecture -in @("X64", "Arm64")) {
        return $architecture
    }

    try {
        $runtimeType = [System.Runtime.InteropServices.RuntimeInformation]
        $property = $runtimeType.GetProperty("ProcessArchitecture")
        if ($null -ne $property) {
            $architecture = ConvertTo-OmniWindowsArchitecture ([string]$property.GetValue($null, $null))
            if ($architecture) { return $architecture }
        }
    } catch { }

    throw "Could not determine the native architecture of the current PowerShell process."
}

function Get-OmniWindowsPlatform {
    if ($env:OS -ne "Windows_NT") {
        throw "The OMNI Windows path requires a Windows 11 workstation."
    }

    try {
        $operatingSystem = Get-CimInstance -ClassName Win32_OperatingSystem -ErrorAction Stop
    } catch {
        throw "Could not determine the Windows product type via Win32_OperatingSystem: $($_.Exception.Message)"
    }

    [PSCustomObject]@{
        Caption = [string]$operatingSystem.Caption
        Version = [string]$operatingSystem.Version
        Build = [int]$operatingSystem.BuildNumber
        ProductType = [int]$operatingSystem.ProductType
        Architecture = (Get-OmniWindowsNativeArchitecture)
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
