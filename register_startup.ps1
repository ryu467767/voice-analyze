# register_startup.ps1
# Windows タスクスケジューラにアプリの自動起動を登録するスクリプト
# 管理者権限で実行してください:
#   右クリック → 「PowerShellで実行」

$TaskName = "KaraokeVoiceApp"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BatchFile = Join-Path $ScriptDir "start.bat"

# 既存のタスクがあれば削除
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "既存タスクを削除しました。"
}

# アクション: start.bat を実行
$Action = New-ScheduledTaskAction `
    -Execute "cmd.exe" `
    -Argument "/c `"$BatchFile`"" `
    -WorkingDirectory $ScriptDir

# トリガー: ログオン時に実行
$Trigger = New-ScheduledTaskTrigger -AtLogOn

# 設定: 最高権限で実行、バックグラウンド継続
$Settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Hours 0) `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1)

$Principal = New-ScheduledTaskPrincipal `
    -UserId $env:USERNAME `
    -LogonType Interactive `
    -RunLevel Highest

# タスクを登録
Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Principal $Principal `
    -Description "カラオケ声分析アプリの自動起動" | Out-Null

Write-Host ""
Write-Host "登録完了: タスク名 '$TaskName'"
Write-Host "次回Windowsログイン時から自動起動します。"
Write-Host ""
Write-Host "手動で今すぐ起動したい場合:"
Write-Host "  Start-ScheduledTask -TaskName '$TaskName'"
Write-Host ""
Write-Host "登録を解除したい場合:"
Write-Host "  Unregister-ScheduledTask -TaskName '$TaskName'"
