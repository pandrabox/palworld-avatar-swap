# UE工程まるごと無人実行: アセット構築(Pythonスクリプト3本) → クック&pak化 → MOD pak生成
# 実行: pwsh -File run_ue_build.ps1     (アセット構築をスキップしてpak化だけ再実行: -SkipAssets)
param([switch]$SkipAssets)

$UE_ROOT  = "C:\Program Files\Epic Games\UE_5.1"
# 注: プロジェクト名は必ず「Pal」。pakのマウントパスにプロジェクト名が焼き込まれ、
# ゲームは Pal/Content/... しか読まないため(2026-07-17に実測で確認した罠)
$PROJECT  = "C:\UnrealProjects\Pal\Pal.uproject"
$OUT      = "C:\P\Work\PalMod\build"
$LOG_DIR  = "C:\P\Work\PalMod\build\logs"
New-Item -ItemType Directory -Force $LOG_DIR | Out-Null

$EDITOR_CMD = "$UE_ROOT\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"

if (-not $SkipAssets) {
    Write-Host "=== Phase 1: アセット構築(ヘッドレス) ==="
    & $EDITOR_CMD $PROJECT -run=pythonscript -script="C:\P\Work\PalMod\ue_scripts\run_all_headless.py" `
        -stdout -unattended -nopause -nosplash 2>&1 | Tee-Object "$LOG_DIR\assets.log" | Select-String "RUN |OK |FAILED|ALL_SCRIPTS_DONE|LogPython.*Error"
    if ($LASTEXITCODE -ne 0) { Write-Error "アセット構築失敗 (exit=$LASTEXITCODE) — logs\assets.log 参照"; exit 1 }
}

Write-Host "=== Phase 2: クック&パッケージ ==="
& "$UE_ROOT\Engine\Build\BatchFiles\RunUAT.bat" BuildCookRun `
    -project="$PROJECT" `
    -platform=Win64 -clientconfig=Shipping `
    -cook -stage -pak -package `
    -archive -archivedirectory="$OUT" `
    -nodebuginfo -utf8output -unattended 2>&1 | Tee-Object "$LOG_DIR\cook.log" | Select-String "BUILD SUCCESSFUL|BUILD FAILED|Error:" | Select-Object -First 30
if ($LASTEXITCODE -ne 0) { Write-Error "パッケージ失敗 (exit=$LASTEXITCODE) — logs\cook.log 参照"; exit 1 }

Write-Host "=== Phase 3: MOD pak抽出+不要物除去 ==="
$pak = Get-ChildItem $OUT -Recurse -Filter "pakchunk900*.pak" | Select-Object -First 1
if (-not $pak) { Write-Error "pakchunk900が見つからない(Collectionのチャンク設定を確認)"; exit 1 }
$modPak = "C:\P\Work\PalMod\build\PGF_PlayerSwap_P.pak"

# スケルトン・物理アセットは絶対に同梱しない(共有資産の置換が全人型を破壊する。2026-07-17の実害で確認)
# UEのチャンク分けでは依存が引き込まれるため、pakを展開→削除→再パックで物理的に排除する
$upak = "$UE_ROOT\Engine\Binaries\Win64\UnrealPak.exe"
$ex = "C:\P\Work\PalMod\build\pak_extract"
Remove-Item $ex -Recurse -Force -ErrorAction SilentlyContinue
& $upak $pak.FullName -Extract $ex | Out-Null
Remove-Item "$ex\Skeleton","$ex\Player\Body" -Recurse -Force -ErrorAction SilentlyContinue
# バインドポーズをバニラ1.0値に補正(ベータ期PSK由来の肩10°ズレ対策、2026-07-17)
python "C:\P\Work\PalMod\scripts\patch_refskeleton.py" $ex
if ($LASTEXITCODE -ne 0) { Write-Error "RefSkeletonパッチ失敗"; exit 1 }
$rsp = "C:\P\Work\PalMod\build\repack_list.txt"
# 罠その1: rspの "src\*.*" "dest\*.*" 形式はディレクトリ構造を保存せず全ファイルを
# マウント直下に平坦化する(2026-07-17検査②失敗の真因: 全アセットパス不正で何も
# 差し替わらなかった)。必ずファイル1件ずつ相対パス付きで列挙する
# 罠その2: マウントは全エントリの共通ディレクトリまで潜る。アンカーファイルで
# 実績ある深さ(Character/)に固定する。圧縮もバニラ/UAT産と同じOodleに合わせる
Set-Content "$ex\_PGF_mount_anchor.txt" "PGF PlayerSwap MOD - mount anchor" -Encoding ascii
$lines = Get-ChildItem $ex -Recurse -File | ForEach-Object {
    $rel = $_.FullName.Substring($ex.Length + 1)
    "`"$($_.FullName)`" `"..\..\..\Pal\Content\Pal\Model\Character\$rel`""
}
Set-Content $rsp $lines
& $upak $modPak -Create="$rsp" -compress -compressionformats=Oodle | Out-Null
if ($LASTEXITCODE -ne 0) { Write-Error "再パック失敗"; exit 1 }
Write-Host "MOD pak: $modPak ($([math]::Round((Get-Item $modPak).Length/1MB,1)) MB, skeleton/physics除去済み)"

Write-Host "=== Phase 4: オフライン全数検品(preflight) ==="
# ぱんの官能検査より前に機械で全ゲートを通す(2026-07-17ぱん指示)。落ちたら配布禁止
python "C:\P\Work\PalMod\scripts\preflight_pak.py"
if ($LASTEXITCODE -ne 0) { Write-Error "preflight FAIL — このpakを配布してはならない"; exit 1 }
