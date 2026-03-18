param(
  [string]$BindHost = "127.0.0.1",
  [int]$Port = 8010,
  [switch]$Reload
)

$ErrorActionPreference = "Stop"

& (Join-Path $PSScriptRoot "local_web_portal\start_local.ps1") -BindHost $BindHost -Port $Port -Reload:$Reload
