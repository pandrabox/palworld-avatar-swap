# -*- coding: utf-8 -*-
"""診断: M_PGFマテリアルの使用フラグ(used_with_skeletal_mesh等)を読むだけ。
スケルタルメッシュ上でWorldGridMaterial(チェッカー)化する定番原因の確認。
注: commandletではAssetRegistryが未スキャンなので直接ロードする。"""

import sys

import unreal

sys.path.insert(0, r"C:\P\Work\PalMod\ue_scripts")
import pgf_config as C

EAL = unreal.EditorAssetLibrary
lines = []
for slot in C.SLOT_TEXTURES:
    path = f"{C.DIR_MATERIALS}/M_PGF_{slot}"
    if not EAL.does_asset_exist(path):
        lines.append(f"missing: {path}")
        continue
    obj = EAL.load_asset(path)
    flags = {p: obj.get_editor_property(p) for p in
             ("used_with_skeletal_mesh", "used_with_morph_targets")}
    lines.append(f"{obj.get_name()}: {flags}")

# UEのstdoutログはリダイレクトで欠落する環境のため、結果はファイル直書き
with open(r"C:\P\Work\PalMod\build\logs\diag_usage_result.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
unreal.log("[diag_material_usage] done")
