"""Build the standalone Windows recovery BAT from its readable Python source."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
header=r'''@echo off
chcp 65001 >nul
set "FLY_RECOVERY_SELF=%~f0"
set "FLY_RECOVERY_DIR=%~dp0"
set "PYTHONIOENCODING=utf-8"
title Fly Ideas - recovery
powershell.exe -NoProfile -Command "$ErrorActionPreference='Stop'; $tmp=$null; try { $app=$env:FLY_RECOVERY_DIR; if (-not (Test-Path -LiteralPath (Join-Path $app 'START.bat'))) { Add-Type -AssemblyName System.Windows.Forms; $dlg=New-Object System.Windows.Forms.FolderBrowserDialog; $dlg.Description='Select the Fly Ideas folder containing START.bat'; if ($dlg.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK) { Write-Host 'Cancelled'; exit 0 }; $app=$dlg.SelectedPath }; $pending=Join-Path $app 'workspace\.app-updates\pending.json'; $m=Get-Content -LiteralPath $pending -Raw -Encoding UTF8 | ConvertFrom-Json; $py=[string]$m.python; if (-not [IO.Path]::IsPathRooted($py) -or -not (Test-Path -LiteralPath $py -PathType Leaf)) { throw 'Python from pending.json not found' }; $all=[IO.File]::ReadAllText($env:FLY_RECOVERY_SELF,[Text.Encoding]::UTF8); $marker='#<'+'FLY_RECOVERY_PY'+'>'; $ix=$all.IndexOf($marker); if ($ix -lt 0) { throw 'Recovery payload missing' }; $code=$all.Substring($ix+$marker.Length).TrimStart([char[]]@([char]13,[char]10)); $tmp=Join-Path ([IO.Path]::GetTempPath()) ('fly-recovery-'+[Guid]::NewGuid().ToString('N')+'.py'); $fs=[IO.File]::Open($tmp,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None); try { $b=[Text.Encoding]::UTF8.GetBytes($code); $fs.Write($b,0,$b.Length) } finally { $fs.Dispose() }; & $py -X utf8 $tmp $app; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } } catch { Write-Host ('ERROR: '+$_.Exception.Message); exit 1 } finally { if ($tmp -and (Test-Path -LiteralPath $tmp)) { Remove-Item -LiteralPath $tmp -Force } }"
set "FLY_RECOVERY_CODE=%errorlevel%"
echo.
pause
exit /b %FLY_RECOVERY_CODE%
#<FLY_RECOVERY_PY>
'''
(root/'experiments'/'PAUSE-FAILED-UPDATE.bat').write_text(header+(root/'electron/update-recovery.py').read_text(encoding='utf8'),encoding='utf8',newline='\n')
