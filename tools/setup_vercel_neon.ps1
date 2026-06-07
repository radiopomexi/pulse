# Создаёт Neon Postgres для pulse-xav2 на Vercel и подключает DATABASE_URL.
# Запуск из корня проекта: powershell -ExecutionPolicy Bypass -File tools/setup_vercel_neon.ps1

$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

Write-Host "Проверка входа в Vercel..."
vercel whoami | Out-Null

Write-Host "Привязка к проекту pulse-xav2..."
if (-not (Test-Path ".vercel\project.json")) {
    vercel link --yes --project pulse-xav2 | Out-Null
}

$cmd = @(
    "vercel", "integration", "add", "neon",
    "--name", "pulse-db",
    "--plan", "free_v3",
    "-m", "region=fra1",
    "-m", "auth=false",
    "-e", "production",
    "-e", "preview"
)

Write-Host "Установка Neon (бесплатный план, регион Frankfurt)..."
& $cmd[0] $cmd[1..($cmd.Length-1)]
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Если просят принять условия — откройте в браузере:"
    Write-Host "https://vercel.com/radiopomexis-projects/~/integrations/accept-terms/neon?source=cli"
    Write-Host "После принятия запустите этот скрипт снова."
    exit 1
}

Write-Host ""
Write-Host "Готово. Переменные DATABASE_URL добавлены в Vercel."
Write-Host "Сделайте Redeploy: https://vercel.com/radiopomexis-projects/pulse-xav2"
