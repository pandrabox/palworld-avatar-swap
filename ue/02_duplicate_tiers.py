# -*- coding: utf-8 -*-
"""UE内Pythonで実行(3本目・ゲーム内で無装備状態の動作確認が取れた後に!):
本体/ダミーHead/ダミーHairを、1.0実データ由来のCSVに従って全ティアへ複製する。
"""

import csv
import sys

import unreal

sys.path.insert(0, r"C:\P\Work\PalMod\ue_scripts")
import pgf_config as C

JOBS = [
    (f"{C.DIR_OUTFIT}/{C.NAME_SK_MAIN}", C.CSV_OUTFIT),
    (f"{C.DIR_HEAD}/{C.NAME_SK_HEAD}", C.CSV_HEAD),
    (f"{C.DIR_HAIR}/{C.NAME_SK_HAIR}", C.CSV_HAIR),
]

for source_path, csv_path in JOBS:
    if not unreal.EditorAssetLibrary.does_asset_exist(source_path):
        unreal.log_error(f"複製元が無い: {source_path}")
        continue
    ok = ng = 0
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            dest = f"{row['Folder'].strip()}/{row['Name'].strip()}"
            if unreal.EditorAssetLibrary.does_asset_exist(dest):
                continue
            if unreal.EditorAssetLibrary.duplicate_asset(source_path, dest):
                ok += 1
            else:
                ng += 1
                unreal.log_error(f"複製失敗: {dest}")
    unreal.EditorAssetLibrary.save_directory("/Game/Pal", recursive=True)
    unreal.log(f"[02_duplicate_tiers] {source_path}: ok={ok} ng={ng}")

unreal.log("[02_duplicate_tiers] done — 新規フォルダをCollectionに追加して再パッケージを忘れずに")
