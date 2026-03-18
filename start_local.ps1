$ErrorActionPreference = "Stop"

param(
  [string]$Host = "127.0.0.1",
  [int]$Port = 8010,
  [switch]$Reload
)

& (Join-Path $PSScriptRoot "local_web_portal\start_local.ps1") -Host $Host -Port $Port -Reload:$Reload
