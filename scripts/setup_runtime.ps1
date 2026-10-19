# Agent-only bootstrap: works before Python exists. Never changes system PATH.
[CmdletBinding()]
param([string]$PythonExecutable, [switch]$Plan)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
$env:PYTHONIOENCODING = 'utf-8'
$projectRoot = Split-Path -Parent $PSScriptRoot

function Test-Python311([string]$Executable) {
    if (-not $Executable -or -not (Test-Path -LiteralPath $Executable -PathType Leaf)) { return $false }
    # Store execution aliases are not interpreters; never open the Store during unattended setup.
    if ($Executable -match '[\\/]Microsoft[\\/]WindowsApps[\\/]') { return $false }
    try {
        $version = & $Executable -c 'import sys; print(str(sys.version_info[0])+chr(46)+str(sys.version_info[1]))' 2>$null
        return ($LASTEXITCODE -eq 0 -and "$version".Trim() -eq '3.11')
    } catch { return $false }
}

function Find-Python311 {
    if ($PythonExecutable) {
        if (-not (Test-Python311 $PythonExecutable)) { throw 'explicit_python_311_required' }
        return $PythonExecutable
    }
    $config = Join-Path $projectRoot 'config/agent_tools.local.json'
    if (Test-Path -LiteralPath $config) {
        $settings = Get-Content -LiteralPath $config -Raw -Encoding UTF8 | ConvertFrom-Json
        $configured = $settings.browser_toolchain.python_executable
        if ($configured) {
            if (-not (Test-Python311 $configured)) { throw 'configured_python_requires_review; preserve_settings' }
            return $configured
        }
    }
    $candidates = @((Join-Path $projectRoot '.venv-toolchain/Scripts/python.exe'), (Join-Path $projectRoot 'tmp/runtimes/python/3.11.9/python.exe'))
    foreach ($command in @('python.exe', 'python3.exe')) {
        $found = Get-Command $command -ErrorAction SilentlyContinue
        if ($found) { $candidates += $found.Source }
    }
    $launcher = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($launcher) {
        try { $path = & $launcher.Source -3.11 -c 'import sys; print(sys.executable)' 2>$null; if ($LASTEXITCODE -eq 0) { $candidates += "$path".Trim() } } catch {}
    }
    foreach ($candidate in $candidates) { if (Test-Python311 $candidate) { return $candidate } }
    return $null
}

try {
    $selected = Find-Python311
    $architecture = if ($env:PROCESSOR_ARCHITECTURE -eq 'AMD64' -or $env:PROCESSOR_ARCHITEW6432 -eq 'AMD64') { 'x64' } elseif ($env:PROCESSOR_ARCHITECTURE -eq 'x86') { 'x86' } else { throw 'windows_x64_or_x86_baseline_required' }
    $target = Join-Path $projectRoot 'tmp/runtimes/python/3.11.9'
    $suffix = if ($architecture -eq 'x64') { '-amd64' } else { '' }
    $url = "https://www.python.org/ftp/python/3.11.9/python-3.11.9$suffix.exe"
    if ($Plan) {
        [pscustomobject]@{ passed=$true; python=$selected; install_python=(-not $selected); python_url=$url; target=$target; changes_system_path=$false } | ConvertTo-Json -Compress
        exit 0
    }
    if (-not $selected) {
        if (Test-Path -LiteralPath $target) { throw 'incomplete_python_install_requires_review; preserve_directory' }
        $cache = Join-Path $projectRoot 'tmp/downloads'
        New-Item -ItemType Directory -Force -Path $cache | Out-Null
        $installer = Join-Path $cache "python-3.11.9$suffix.exe"
        if (-not (Test-Path -LiteralPath $installer)) {
            $partial = "$installer.partial"
            $curl = Get-Command curl.exe -ErrorAction Stop
            & $curl.Source --silent --show-error --fail --proto '=https' --max-redirs 0 --connect-timeout 20 --max-time 300 --retry 2 --output $partial $url
            if ($LASTEXITCODE -ne 0) { throw 'official_python_download_failed' }
            Move-Item -LiteralPath $partial -Destination $installer
        }
        $signature = Get-AuthenticodeSignature -LiteralPath $installer
        if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch 'Python Software Foundation') { throw 'python_installer_signature_failed' }
        $arguments = @('/quiet', '/norestart', 'InstallAllUsers=0', 'PrependPath=0', 'Include_launcher=0', 'AssociateFiles=0', 'Shortcuts=0', 'Include_test=0', 'Include_pip=1', "TargetDir=`"$target`"")
        $process = Start-Process -FilePath $installer -ArgumentList $arguments -WindowStyle Hidden -Wait -PassThru
        if ($process.ExitCode -notin @(0,3010)) { throw 'python_installer_failed; preserve_directory_and_review' }
        $selected = Join-Path $target 'python.exe'
        if (-not (Test-Python311 $selected)) { throw 'python_311_post_install_probe_failed' }
        [pscustomobject]@{url=$url; installer_sha256=(Get-FileHash -LiteralPath $installer -Algorithm SHA256).Hash; signature='Valid/Python Software Foundation'; executable=$selected} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $target 'installation.json') -Encoding UTF8
    }
    & $selected (Join-Path $PSScriptRoot 'setup_runtime.py') --python $selected --architecture $architecture
    exit $LASTEXITCODE
} catch {
    [pscustomobject]@{passed=$false;code='runtime_bootstrap_failed';detail=$_.Exception.Message} | ConvertTo-Json -Compress
    exit 1
}
