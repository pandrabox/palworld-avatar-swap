# PalMod Blenderパイプライン実行ランチャー
# 使い方:  .\run_pipeline.ps1            → step01のみ(現状はここまで無人実行可)
#          .\run_pipeline.ps1 -All       → step01→02→03を通す(BONE_MAP確定後)
param([switch]$All)

# ガイド(Nexus #2826)準拠のBlender 4.3.2ポータブル版(tools配下、blender.org公式から取得)
$blender = "C:\P\Work\PalMod\tools\blender-4.3.2-windows-x64\blender.exe"
$here = $PSScriptRoot

# 注意: --python-exit-code 1 が無いとPythonエラーでもBlenderはexit 0を返し、
# 失敗が握り潰される(2026-07-18に実害を確認)
& $blender --background --python-exit-code 1 --python "$here\step01_import_clean.py"
if ($LASTEXITCODE -ne 0) { Write-Error "step01 failed"; exit 1 }

if ($All) {
    & $blender --background --python-exit-code 1 --python "$here\step02_retarget_to_pal.py"
    if ($LASTEXITCODE -ne 0) { Write-Error "step02 failed"; exit 1 }
    & $blender --background --python-exit-code 1 --python "$here\step03_export_fbx.py"
    if ($LASTEXITCODE -ne 0) { Write-Error "step03 failed"; exit 1 }
    & $blender --background --python-exit-code 1 --python "$here\step04_make_dummies.py"
    if ($LASTEXITCODE -ne 0) { Write-Error "step04 failed"; exit 1 }
    & $blender --background --python-exit-code 1 --python "$here\render_preview.py"
    Write-Host ""
    Write-Host "★ 官能検査ポイント①: assets\converted\preview_front.png / preview_side.png を目視確認せよ"
    Write-Host "   シルエットが崩れていたらUE工程に進まないこと(検査②はゲーム内: テクスチャ+アニメ変形)"
}
Write-Host "pipeline done"
