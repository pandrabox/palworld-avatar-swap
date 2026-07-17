@echo off
setlocal

set "SRC=C:\P\Work\PalMod\build\PGF_PlayerSwap_P.pak"
set "PAKS=C:\Program Files (x86)\Steam\steamapps\common\Palworld\Pal\Content\Paks"
set "DST=%PAKS%\PGF_PlayerSwap_P.pak"

echo ============================================
echo  PGF Player Swap MOD - INSTALL
echo ============================================

rem 注意: このbatでは ( ) ブロックを使わないこと。
rem パスに含まれる "(x86)" の閉じ括弧がブロックを破壊するため、goto構造で書く。

tasklist /FI "IMAGENAME eq Palworld-Win64-Shipping.exe" | find /I "Palworld-Win64-Shipping.exe" >nul
if not errorlevel 1 goto game_running
if not exist "%SRC%" goto no_src
if not exist "%PAKS%\Pal-Windows.pak" goto no_paks

rem --- インストール前にセーブを自動バックアップ ---
set "TS=%DATE:/=-%_%TIME::=-%"
set "TS=%TS: =0%"
set "SAVEDIR=%LOCALAPPDATA%\Pal\Saved\SaveGames"
set "BKDIR=C:\P\Work\PalMod\backup\SaveGames_auto_%TS:~0,19%"
if not exist "%SAVEDIR%" goto do_copy
robocopy "%SAVEDIR%" "%BKDIR%" /E /R:1 /W:1 /NFL /NDL /NP >nul
echo [OK] セーブを自動バックアップ: %BKDIR%

:do_copy
copy /Y "%SRC%" "%DST%" >nul
if errorlevel 1 goto copy_fail
echo [OK] インストール完了: %DST%
echo      ゲームを起動して確認してください。おかしければ uninstall_mod.bat で即戻せます。
goto end

:game_running
echo [NG] パルワールドが起動中です。ゲームを終了してから実行してください。
goto end

:no_src
echo [NG] MOD pakがまだありません: %SRC%
echo      先にビルド run_ue_build.ps1 を完了させてください。
goto end

:no_paks
echo [NG] ゲームのPaksフォルダが見つかりません: %PAKS%
goto end

:copy_fail
echo [NG] コピーに失敗しました。管理者権限で実行してみてください。
goto end

:end
echo.
pause
