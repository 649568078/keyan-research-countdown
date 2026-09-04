$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "未找到 Python，请先安装 Python 3.10 或更高版本。"
}

python -c "import flask" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "首次运行，正在安装依赖……"
    python -m pip install -r requirements.txt
}

Write-Host "科研倒计时已启动：http://127.0.0.1:5000"
python run.py
