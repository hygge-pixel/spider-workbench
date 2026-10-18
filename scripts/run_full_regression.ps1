[CmdletBinding()]
param([string]$PythonExecutable, [string]$NodeExecutable)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$workspaceRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$entrypoint = Join-Path $PSScriptRoot 'run_full_regression.py'
$extra = @()
if ($NodeExecutable) { $extra += @('--node', $NodeExecutable) }
Push-Location -LiteralPath $workspaceRoot
try {
    if ($PythonExecutable) {
        & $PythonExecutable $entrypoint @extra
    } elseif (Test-Path -LiteralPath (Join-Path $workspaceRoot '.venv/Scripts/python.exe')) {
        & (Join-Path $workspaceRoot '.venv/Scripts/python.exe') $entrypoint @extra
    } else {
        & py -3.11 $entrypoint @extra
    }
    if ($LASTEXITCODE -ne 0) { throw "Full framework regression failed ($LASTEXITCODE)" }
} finally {
    Pop-Location
}
