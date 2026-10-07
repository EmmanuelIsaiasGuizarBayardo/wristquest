<#
.SYNOPSIS
    Lanzador de la demostración: motor SynapVolit, servidor web de WristQuest y navegador.

.DESCRIPTION
    Arranca los dos procesos a la vez, espera a que ambos acepten conexiones y abre el juego en la
    URL correcta. Al cerrar (Enter o Ctrl+C) apaga el motor de forma ordenada, para que exporte la
    sesión abierta, y después detiene el servidor web. Los registros de cada proceso quedan en la
    carpeta temporal wristquest_demo.

.PARAMETER Fuente
    Obligatorio y sin valor por defecto: quien opera declara si la señal es simulada o del brazalete.

.EXAMPLE
    .\scripts\iniciar_demo.ps1 -Fuente simulada
    .\scripts\iniciar_demo.ps1 -Fuente serie -PuertoSerie COM3
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][ValidateSet("simulada", "serie")][string] $Fuente,
    [string] $PuertoSerie = "",
    [int] $PuertoMotor = 8765,
    [int] $PuertoWeb = 8000,
    [string] $SynapVolit = (Join-Path $PSScriptRoot "..\..\SynapVolit"),
    [int] $Segundos = 0  # mayor que 0: se cierra solo tras ese tiempo (para pruebas)
)
$ErrorActionPreference = "Stop"
$enWindows = [System.Environment]::OSVersion.Platform -eq "Win32NT"
$WristQuest = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if (-not (Test-Path (Join-Path $SynapVolit "pyproject.toml"))) {
    Write-Host "No encuentro el repositorio de SynapVolit en $SynapVolit" -ForegroundColor Red
    Write-Host "Indícalo con -SynapVolit <ruta>"
    exit 1
}
$SynapVolit = (Resolve-Path $SynapVolit).Path
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "No encuentro uv en el PATH: instálalo antes de usar el lanzador." -ForegroundColor Red
    exit 1
}
if ($Fuente -eq "serie" -and -not $PuertoSerie) {
    Write-Host "Con -Fuente serie hace falta -PuertoSerie (por ejemplo COM3)." -ForegroundColor Red
    exit 1
}
$logs = Join-Path ([System.IO.Path]::GetTempPath()) "wristquest_demo"
New-Item -ItemType Directory -Force $logs | Out-Null

function Test-Puerto([int] $puerto) {
    $cliente = New-Object System.Net.Sockets.TcpClient
    try { return $cliente.ConnectAsync("127.0.0.1", $puerto).Wait(250) -and $cliente.Connected }
    catch { return $false }
    finally { $cliente.Dispose() }
}

function Iniciar([string] $nombre, [string] $carpeta, [string[]] $argumentos) {
    Start-Process -FilePath "uv" -ArgumentList $argumentos -WorkingDirectory $carpeta -PassThru -NoNewWindow `
        -RedirectStandardOutput (Join-Path $logs "$nombre.log") -RedirectStandardError (Join-Path $logs "$nombre.err")
}

function Detener([System.Diagnostics.Process] $proceso) {
    # uv lanza a Python como proceso hijo: hay que detener el árbol completo
    if ($null -eq $proceso -or $proceso.HasExited) { return }
    if ($enWindows) { & taskkill /PID $proceso.Id /T /F 2>&1 | Out-Null }
    else { & pkill -TERM -P $proceso.Id 2>&1 | Out-Null; Stop-Process -Id $proceso.Id -ErrorAction SilentlyContinue }
}

function Apagar-Motor {
    # orden "apagar" por WebSocket: el motor cierra y exporta la sesión antes de salir.
    # Un programa local no envía Origin, por eso el motor la acepta; una página web no podría.
    $ws = New-Object System.Net.WebSockets.ClientWebSocket
    try {
        if (-not $ws.ConnectAsync([Uri]"ws://127.0.0.1:$PuertoMotor", [Threading.CancellationToken]::None).Wait(3000)) { return }
        $bytes = [System.Text.Encoding]::UTF8.GetBytes('{"cmd":"apagar"}')
        $segmento = New-Object System.ArraySegment[byte] -ArgumentList (, $bytes)
        $ws.SendAsync($segmento, [System.Net.WebSockets.WebSocketMessageType]::Text, $true, [Threading.CancellationToken]::None).Wait(3000) | Out-Null
    } catch { } finally { $ws.Dispose() }
}

foreach ($p in $PuertoMotor, $PuertoWeb) {
    if (Test-Puerto $p) {
        Write-Host "El puerto $p ya está en uso: ¿quedó abierto otro motor, servidor o el puente viejo?" -ForegroundColor Red
        exit 1
    }
}

$env:PYTHONUNBUFFERED = "1"  # registros al momento, no al cerrar
$argsMotor = @("run", "python", "-m", "synapvolit.servidor", "--fuente", $Fuente, "--puerto", "$PuertoMotor")
if ($Fuente -eq "serie") { $argsMotor += @("--puerto-serie", $PuertoSerie) }
$argsWeb = @("run", "python", "-m", "http.server", "$PuertoWeb", "--bind", "127.0.0.1", "--directory", "web")

Write-Host "Iniciando motor y servidor web..."
$motor = Iniciar "motor" $SynapVolit $argsMotor
$web = Iniciar "web" $WristQuest $argsWeb
try {
    # los dos arrancan a la vez; se espera a que ambos acepten conexiones (la primera vez uv puede
    # tardar en preparar el entorno, por eso el límite es amplio)
    $limite = (Get-Date).AddSeconds(90)
    while (-not ((Test-Puerto $PuertoMotor) -and (Test-Puerto $PuertoWeb))) {
        if ($motor.HasExited) { throw "El motor se cerró al arrancar. Revisa $logs\motor.log y motor.err" }
        if ($web.HasExited) { throw "El servidor web se cerró al arrancar. Revisa $logs\web.err" }
        if ((Get-Date) -gt $limite) { throw "Tiempo agotado esperando al motor o al servidor web (registros en $logs)" }
        Start-Sleep -Milliseconds 250
    }
    $url = "http://127.0.0.1:$PuertoWeb/wristquest.html?motor=ws://127.0.0.1:$PuertoMotor"
    Write-Host ""
    if ($Fuente -eq "simulada") { Write-Host "  FUENTE SIMULADA: paciente simulado con sEMG real de GRABMyo" -ForegroundColor Yellow }
    else { Write-Host "  BRAZALETE en $PuertoSerie" -ForegroundColor Green }
    Write-Host "  Juego: $url"
    Write-Host "  Registros: $logs"
    Write-Host ""
    try { Start-Process $url } catch { Write-Host "  Abre esa dirección en el navegador." }
    if ($Segundos -gt 0) { Start-Sleep -Seconds $Segundos }
    else { Read-Host "Pulsa Enter para cerrar el demo (o Ctrl+C)" | Out-Null }
}
catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
}
finally {
    Write-Host "Cerrando: el motor exporta la sesión abierta..."
    Apagar-Motor
    if (-not $motor.HasExited -and -not $motor.WaitForExit(10000)) { Detener $motor }
    Detener $web
    Write-Host "Demo cerrado."
}
