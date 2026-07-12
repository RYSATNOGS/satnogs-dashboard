<#
  First-run setup for the community deploy (native Windows without WSL2).
  Collects the three optional API tokens into a root .env, then starts the
  stack. Every token may be skipped (press Enter) — the stack runs tokenless
  without them. Plain `docker compose up` still works and is unaffected.

    .\scripts\setup.ps1                # prompt if .env is missing, then up
    .\scripts\setup.ps1 -d --build     # extra args are passed through to compose
    .\scripts\setup.ps1 -Reconfigure   # re-enter tokens even if .env exists

  If Windows blocks the script, run it via:
    powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1
#>

$ErrorActionPreference = 'Stop'

# Parse arguments by hand from the automatic $args. This script intentionally
# declares NO param() block: an advanced-function param() would add PowerShell
# common parameters (e.g. -Debug), and a bare compose flag like -d would bind
# to -Debug via prefix-matching and be swallowed instead of passed through.
# Working from $args keeps every compose flag intact.
$Reconfigure = $false
$Forward = @()
foreach ($a in $args) {
    if ($a -ieq '-Reconfigure' -or $a -ieq '--reconfigure') { $Reconfigure = $true }
    else { $Forward += $a }
}

# Repo root is the parent of this script's directory, so the script works
# regardless of the caller's working directory.
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root      = Split-Path -Parent $ScriptDir
$EnvFile   = Join-Path $Root '.env'
$Example   = Join-Path $Root '.env.example'

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Error 'Docker is required but was not found on PATH. Install Docker, then re-run this script.'
    exit 1
}

function Read-Token {
    param($Key, $Desc, $Url)
    Write-Host ''
    Write-Host "$Key - $Desc"
    Write-Host "  Get it: $Url"
    return (Read-Host "  $Key (press Enter to skip)")
}

if ((Test-Path -LiteralPath $EnvFile) -and -not $Reconfigure) {
    Write-Host 'Using existing .env (pass -Reconfigure to re-enter tokens).'
}
else {
    Write-Host 'Setting up API tokens. All three are optional - press Enter to skip any.'
    $network = Read-Token 'satnogs_network_api_key' 'queue polling' 'https://network.satnogs.org (Profile -> API key)'
    $db      = Read-Token 'satnogs_db_api_key' 'decoder evidence frames' 'https://db.satnogs.org (Profile -> API key)'
    $hf      = Read-Token 'HUGGING_FACE_HUB_TOKEN' 'model downloads' 'https://huggingface.co/settings/tokens'

    # Base the file on .env.example so comments and the tuning block are kept.
    if (Test-Path -LiteralPath $Example) {
        $lines = Get-Content -LiteralPath $Example
    }
    else {
        $lines = @('satnogs_db_api_key=', 'satnogs_network_api_key=', 'HUGGING_FACE_HUB_TOKEN=')
    }

    $out = foreach ($line in $lines) {
        if ($line -match '^satnogs_network_api_key=')  { "satnogs_network_api_key=$network" }
        elseif ($line -match '^satnogs_db_api_key=')   { "satnogs_db_api_key=$db" }
        elseif ($line -match '^HUGGING_FACE_HUB_TOKEN=') { "HUGGING_FACE_HUB_TOKEN=$hf" }
        else { $line }
    }

    # Write UTF-8 without BOM and with LF line endings. PowerShell's default
    # Out-File / > can emit a BOM and CRLF; a BOM corrupts the first key name
    # and Docker's env_file parser passes a trailing \r into the containers as
    # part of the token value.
    $text = ($out -join "`n") + "`n"
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($EnvFile, $text, $utf8NoBom)
    Write-Host ''
    Write-Host "Wrote $EnvFile"
}

$composeCmd = @('compose', 'up') + $Forward
Write-Host ''
Write-Host "Starting the stack: docker $($composeCmd -join ' ')"
& docker @composeCmd
exit $LASTEXITCODE
