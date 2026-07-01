#!/usr/bin/env pwsh
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Set-Location -Path $PSScriptRoot

$envFile = ".env"
$exampleFile = ".env.example"

function Show-Help {
    @"
NeuroGolf Lab startup

Required for export:
  HF_TOKEN    Hugging Face token with write access to your model repo.
  HF_REPO_ID  Hugging Face model repo, for example username/neurogolf-handcrafted.

Runtime:
  HOST        Bind host. Use 127.0.0.1 behind a tunnel. Default: 127.0.0.1.
  PORT        Bind port. Default: 8081.

Optional:
  PUBLIC_HOSTNAME        Public tunnel hostname, if any.
  CLOUDFLARE_API_TOKEN   Optional deployment automation token.
  GITHUB_TOKEN           Optional token for git automation on private machines.

Secrets stay in .env. Do not commit .env.
"@
}

function Ensure-Env {
    if (Test-Path $envFile) {
        return
    }
    if (Test-Path $exampleFile) {
        Copy-Item $exampleFile $envFile
    } else {
        @'
HF_TOKEN=""
HF_REPO_ID="your-hf-username/neurogolf-handcrafted"
HOST="127.0.0.1"
PORT="8081"
PUBLIC_HOSTNAME=""
CLOUDFLARE_API_TOKEN=""
GITHUB_TOKEN=""
'@ | Set-Content -Path $envFile -NoNewline
        Add-Content -Path $envFile -Value ""
    }
    Write-Host "Created .env from template."
    Show-Help
}

function Read-EnvValue {
    param([string]$Key)
    if (-not (Test-Path $envFile)) {
        return ""
    }
    foreach ($line in Get-Content $envFile) {
        if ($line.StartsWith("$Key=")) {
            return $line.Split("=", 2)[1].Trim().Trim('"').Trim("'")
        }
    }
    return ""
}

function Set-EnvValue {
    param([string]$Key, [string]$Value)
    $lines = @()
    if (Test-Path $envFile) {
        $lines = @(Get-Content $envFile)
    }
    $newLine = '{0}="{1}"' -f $Key, $Value
    $found = $false
    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i].StartsWith("$Key=")) {
            $lines[$i] = $newLine
            $found = $true
            break
        }
    }
    if (-not $found) {
        $lines += $newLine
    }
    Set-Content -Path $envFile -Value $lines
}

function Prompt-Missing {
    $hfToken = Read-EnvValue "HF_TOKEN"
    $hfRepo = Read-EnvValue "HF_REPO_ID"

    if ([string]::IsNullOrEmpty($hfToken)) {
        $hfToken = Read-Host "Enter HF_TOKEN for artifact upload, or press Enter to skip exports"
        if (-not [string]::IsNullOrEmpty($hfToken)) {
            Set-EnvValue "HF_TOKEN" $hfToken
        }
    }

    if ([string]::IsNullOrEmpty($hfRepo) -or $hfRepo -eq "your-hf-username/neurogolf-handcrafted") {
        $hfRepo = Read-Host "Enter HF_REPO_ID, for example username/neurogolf-handcrafted"
        if (-not [string]::IsNullOrEmpty($hfRepo)) {
            Set-EnvValue "HF_REPO_ID" $hfRepo
        }
    }
}

Ensure-Env
Prompt-Missing

foreach ($line in Get-Content $envFile) {
    if ($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)="?([^"]*)"?\s*$') {
        Set-Item -Path "Env:$($Matches[1])" -Value $Matches[2]
    }
}

$hostname = if ($env:HOST) { $env:HOST } else { "127.0.0.1" }
$port = if ($env:PORT) { $env:PORT } else { "8081" }

Write-Host ""
Write-Host "Starting NeuroGolf Lab"
Write-Host "  URL: http://${hostname}:${port}"
Write-Host "  HF_REPO_ID: $(if ($env:HF_REPO_ID) { $env:HF_REPO_ID } else { 'not set' })"
Write-Host ""
Write-Host "Run headless agent export examples from another shell:"
Write-Host '  python scripts/agent_export.py --task task276 --color-remap {"6":2}'
Write-Host "  python scripts/agent_export.py --task task010 --graph graph.json"
Write-Host ""

python -m uvicorn server:app --host $hostname --port $port
