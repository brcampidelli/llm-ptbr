# Status do treino em andamento. Rode a qualquer momento:
#   .\train\status.ps1
#
# Mostra progresso, ETA, estado da GPU e checkpoints salvos.

param(
    [string]$Out = "models\qwen3.5-4b-ptbr-sft-v1"
)

$taskDir = "C:\Users\brcam\AppData\Local\Temp\claude\C--Users-brcam-Desktop-Desenvolvendo-Projetos-Desenvolvendo-LLM\b2b71105-2feb-424d-9bad-556c9b0c2a86\tasks"
$log = Get-ChildItem "$taskDir\*.output" -ErrorAction SilentlyContinue |
       Sort-Object LastWriteTime -Descending | Select-Object -First 1

Write-Host "=== PROGRESSO ===" -ForegroundColor Cyan
if ($log) {
    $line = Get-Content $log.FullName | Select-String -Pattern '\d+/\d+ \[' | Select-Object -Last 1
    if ($line) { Write-Host "  $($line.Line.Trim())" } else { Write-Host "  (ainda carregando o modelo)" }
} else { Write-Host "  (log nao encontrado)" }

Write-Host "`n=== GPU ===" -ForegroundColor Cyan
nvidia-smi --query-gpu=memory.used,memory.total,utilization.gpu,temperature.gpu,power.draw --format=csv,noheader

Write-Host "`n=== CHECKPOINTS ===" -ForegroundColor Cyan
$ck = Get-ChildItem $Out -Directory -ErrorAction SilentlyContinue
if ($ck) { $ck | Select-Object Name, LastWriteTime | Format-Table -AutoSize }
else { Write-Host "  (nenhum ainda)" }

Write-Host "`n=== ADAPTER FINAL ===" -ForegroundColor Cyan
if (Test-Path "$Out\adapter_model.safetensors") {
    Write-Host "  PRONTO — treino concluido" -ForegroundColor Green
} else {
    Write-Host "  ainda treinando"
}
