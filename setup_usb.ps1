$ErrorActionPreference = "Stop"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$RootDir = $PSScriptRoot
if (-not $RootDir) {
    $RootDir = (Get-Location).Path
}

$PythonVersion = "3.12.8"
$PythonZipUrl = "https://www.python.org/ftp/python/$PythonVersion/python-$PythonVersion-embed-amd64.zip"
$GetPipUrl = "https://bootstrap.pypa.io/get-pip.py"

$PythonDir = Join-Path $RootDir "python"
$PythonZipPath = Join-Path $RootDir "python-embed.zip"
$GetPipPath = Join-Path $RootDir "get-pip.py"
$PythonExe = Join-Path $PythonDir "python.exe"

Write-Host "[1/5] Dang tai Python $PythonVersion Embeddable (64-bit)..." -ForegroundColor Cyan
Invoke-WebRequest -Uri $PythonZipUrl -OutFile $PythonZipPath

Write-Host "[2/5] Dang giai nen vao thu muc python\..." -ForegroundColor Cyan
if (Test-Path $PythonDir) {
    Remove-Item -Path $PythonDir -Recurse -Force
}
Expand-Archive -Path $PythonZipPath -DestinationPath $PythonDir -Force
Remove-Item -Path $PythonZipPath -Force

Write-Host "[3/5] Dang mo khoa site-packages trong python312._pth..." -ForegroundColor Cyan
$PthFile = Join-Path $PythonDir "python312._pth"
if (-not (Test-Path $PthFile)) {
    throw "Khong tim thay file $PthFile"
}
$PthContent = Get-Content -Path $PthFile -Raw
$PthContent = $PthContent -replace "(?m)^#\s*import site\s*$", "import site"
Set-Content -Path $PthFile -Value $PthContent -Encoding ASCII

Write-Host "[4/5] Dang tai va cai dat pip..." -ForegroundColor Cyan
Invoke-WebRequest -Uri $GetPipUrl -OutFile $GetPipPath
try {
    & $PythonExe $GetPipPath --no-warn-script-location
    if ($LASTEXITCODE -ne 0) {
        throw "Cai dat pip that bai (exit code: $LASTEXITCODE)"
    }
}
finally {
    if (Test-Path $GetPipPath) {
        Remove-Item -Path $GetPipPath -Force
    }
}

Write-Host "[5/5] Dang cai dat google-genai, openai, watchdog..." -ForegroundColor Cyan
& $PythonExe -m pip install --upgrade pip --no-warn-script-location
& $PythonExe -m pip install --no-warn-script-location google-genai openai watchdog
if ($LASTEXITCODE -ne 0) {
    throw "Cai dat thu vien that bai (exit code: $LASTEXITCODE)"
}

Write-Host "[Kiem tra] Dang kiem tra import thu vien..." -ForegroundColor Yellow
& $PythonExe -c "import google.genai, openai, watchdog; print('Import thanh cong: google-genai, openai, watchdog')"
if ($LASTEXITCODE -ne 0) {
    throw "Kiem tra import that bai!"
}

Write-Host ""
Write-Host "HOAN TAT! Moi truong Python Portable da san sang trong: $PythonDir" -ForegroundColor Green
Write-Host "Hay dien API key vao config.json roi chay run.bat." -ForegroundColor Green
