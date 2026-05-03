# Restore a PostgreSQL custom-format dump (e.g. latest.dmp) into Railway Postgres.
# Prerequisites: Railway CLI logged in; pg_restore on PATH, or set PG_RESTORE_EXE to pg_restore.exe.
# Usage (from Backend):  .\scripts\restore-local-dump-to-railway.ps1 [-DumpPath latest.dmp]
param(
  [string] $DumpPath = "latest.dmp"
)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot)

if (-not (Test-Path $DumpPath)) {
  Write-Error "Dump not found: $DumpPath"
}

$pgRestore = $env:PG_RESTORE_EXE
if (-not $pgRestore) {
  $cand = Get-Command pg_restore -ErrorAction SilentlyContinue
  if ($cand) { $pgRestore = $cand.Source }
}
if (-not $pgRestore) {
  Write-Error "pg_restore not found. Install PostgreSQL client tools or set PG_RESTORE_EXE to pg_restore.exe."
}

$j = railway variable list -s Postgres --json | ConvertFrom-Json
$url = $j.DATABASE_PUBLIC_URL
if (-not $url) {
  Write-Error "DATABASE_PUBLIC_URL missing. Link project and ensure Postgres service exists."
}
if ($url -notmatch 'sslmode=') {
  $url += $(if ($url -match '\?') { '&' } else { '?' }) + 'sslmode=require'
}

$dumpFull = (Resolve-Path $DumpPath).Path
Write-Host "Restoring $dumpFull to Railway Postgres..."
& $pgRestore --verbose --no-acl --no-owner --clean --if-exists -d $url $dumpFull
exit $LASTEXITCODE
