# -*- coding: utf-8 -*-
"""既存のM_PGFマテリアルに used_with_skeletal_mesh=True を付与して保存する。
(01_import_and_setup.py には恒久修正済み。これは再インポート無しで直す即時版)"""

import sys

import unreal

sys.path.insert(0, r"C:\P\Work\PalMod\ue_scripts")
import pgf_config as C

EAL = unreal.EditorAssetLibrary
lines = []
for slot in C.SLOT_TEXTURES:
    path = f"{C.DIR_MATERIALS}/M_PGF_{slot}"
    if not EAL.does_asset_exist(path):
        lines.append(f"MISSING: {path}")
        continue
    mat = EAL.load_asset(path)
    mat.set_editor_property("used_with_skeletal_mesh", True)
    unreal.MaterialEditingLibrary.recompile_material(mat)
    EAL.save_asset(path)
    lines.append(f"{mat.get_name()}: used_with_skeletal_mesh -> "
                 f"{mat.get_editor_property('used_with_skeletal_mesh')}")

with open(r"C:\P\Work\PalMod\build\logs\fix_usage_result.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
unreal.log("[09_fix_material_usage] done")
