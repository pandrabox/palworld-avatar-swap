# -*- coding: utf-8 -*-
"""UE内Pythonで実行(再インポート前の掃除): 既存のPGF由来アセットを削除する。
FBX再出力(ウェイト修正等)後に01を再実行すると、既存アセットとの二重化や
「find_assetが古い方を掴む」事故が起きるため、先に消す(HANDOFF記載のハマり対策)。

消すもの: 衣装/Head001/Hair001/マテリアルの各ディレクトリ、スケルトンSK、物理SK、
02_duplicate_tiersの複製先ディレクトリ(CSV記載の全て)。
消さないもの: chunk隔離用のPrimaryAssetLabel(Skeleton/とPlayer/Body/直下のラベルは
ディレクトリごと消さないことで温存する)。
"""

import csv
import sys

import unreal

sys.path.insert(0, r"C:\P\Work\PalMod\ue_scripts")
import pgf_config as C

EAL = unreal.EditorAssetLibrary

# ディレクトリごと消してよいもの(中身は全てPGF由来)
DIRS = [C.DIR_OUTFIT, C.DIR_HEAD, C.DIR_HAIR, C.DIR_MATERIALS]
for csv_path in (C.CSV_OUTFIT, C.CSV_HEAD, C.CSV_HAIR):
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        DIRS.extend(sorted({row["Folder"].strip() for row in csv.DictReader(f)}))

for d in DIRS:
    if EAL.does_directory_exist(d):
        if EAL.delete_directory(d):
            unreal.log(f"[06_clean] deleted dir: {d}")
        else:
            unreal.log_error(f"[06_clean] delete failed: {d}")

# アセット単体で消すもの(親ディレクトリにはchunk901隔離ラベルが同居しており温存する)
ASSETS = [
    f"{C.DIR_SKELETON}/{C.NAME_SKELETON}",
    f"{C.DIR_PHYSICS}/{C.NAME_PHYSICS}",
]
for a in ASSETS:
    if EAL.does_asset_exist(a):
        if EAL.delete_asset(a):
            unreal.log(f"[06_clean] deleted asset: {a}")
        else:
            unreal.log_error(f"[06_clean] delete failed: {a}")

unreal.log("[06_clean_for_reimport] done")
