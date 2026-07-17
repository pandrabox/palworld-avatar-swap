@echo off
setlocal

set "PAKS=C:\Program Files (x86)\Steam\steamapps\common\Palworld\Pal\Content\Paks"
set "DST=%PAKS%\PGF_PlayerSwap_P.pak"

echo ============================================
echo  PGF Player Swap MOD - UNINSTALL
echo ============================================

rem 注意: このbatでは ( ) ブロックを使わないこと("(x86)"問題)。goto構造で書く。

tasklist /FI "IMAGENAME eq Palworld-Win64-Shipping.exe" | find /I "Palworld-Win64-Shipping.exe" >nul
if not errorlevel 1 goto game_running
if not exist "%DST%" goto not_installed

rem 消すのは自分のMOD pak 1ファイルだけ。他には一切触らない
del /F "%DST%"
if exist "%DST%" goto del_fail
echo [OK] アンインストール完了。バニラ状態に戻りました。
goto end

:game_running
echo [NG] パルワールドが起動中です。ゲームを終了してから実行してください。
goto end

:not_installed
echo [OK] MODは入っていません。すでにバニラ状態です。
goto end

:del_fail
echo [NG] 削除に失敗しました。管理者権限で実行してみてください。
goto end

:end
echo.
pause
