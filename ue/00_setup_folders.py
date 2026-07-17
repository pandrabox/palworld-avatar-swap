# -*- coding: utf-8 -*-
"""UE内Pythonで実行(1本目): パルワールド互換のフォルダ構造を作る。
実行方法: UEエディタ下部のコンソールをPythonに切替 → このファイルのパスを貼ってEnter
"""

import sys

import unreal

sys.path.insert(0, r"C:\P\Work\PalMod\ue_scripts")
import pgf_config as C

DIRS = [C.DIR_OUTFIT, C.DIR_SKELETON, C.DIR_PHYSICS, C.DIR_HEAD, C.DIR_HAIR, C.DIR_MATERIALS]

for d in DIRS:
    if unreal.EditorAssetLibrary.does_directory_exist(d):
        unreal.log(f"exists: {d}")
    else:
        unreal.EditorAssetLibrary.make_directory(d)
        unreal.log(f"created: {d}")
unreal.log("[00_setup_folders] done")
