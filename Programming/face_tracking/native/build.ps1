param([Parameter(Mandatory=$true)][string]$MaxineSource)
$ErrorActionPreference = 'Stop'
$sourceRoot = (Resolve-Path -LiteralPath $MaxineSource).Path
& cmake -S $PSScriptRoot -B "$PSScriptRoot/build" -A x64 "-DMAXINE_SOURCE=$sourceRoot"
if ($LASTEXITCODE -ne 0) { throw 'CMake configuration failed' }
& cmake --build "$PSScriptRoot/build" --config Release
if ($LASTEXITCODE -ne 0) { throw 'Bridge build failed' }
