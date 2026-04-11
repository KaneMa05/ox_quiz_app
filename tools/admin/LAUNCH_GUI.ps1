# UTF-8. PowerShell에서 실행: 우클릭 -> PowerShell에서 실행
Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"
Set-Location (Join-Path $PSScriptRoot "..\..")
$env:OX_QUIZ_ADMIN_TOOLS = "1"
$script = Join-Path $PSScriptRoot "quiz_image_gui.py"
$req = Join-Path $PSScriptRoot "requirements-ocr.txt"
$reqv = Join-Path $PSScriptRoot "requirements-vision.txt"

Write-Host "Installing Python packages if needed..."
if (Get-Command py -ErrorAction SilentlyContinue) {
    py -3 -m pip install -r $req
    if (Test-Path $reqv) { py -3 -m pip install -r $reqv }
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    python -m pip install -r $req
    if (Test-Path $reqv) { python -m pip install -r $reqv }
}

if (Get-Command py -ErrorAction SilentlyContinue) {
    py -3 $script
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    python $script
} elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
    python3 $script
} else {
    Write-Host "Python(py / python / python3)을 찾을 수 없습니다."
}
if ($LASTEXITCODE -ne 0) {
    Write-Host "실패 시: pip install -r tools\admin\requirements-ocr.txt"
    Read-Host "Enter 키를 누르면 종료"
}
