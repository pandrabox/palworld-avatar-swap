# -*- coding: utf-8 -*-
"""UE内Pythonで実行(01の後): PGFテクスチャを全てNeverStream化する。

検査②-2(2026-07-17)でモデルが白チェッカー(UEデフォルトテクスチャ)になった対策。
ストリーミングテクスチャはミップ実体が.ubulkに分離され、手詰めMOD pakからの
ロードに失敗しやすい(MODシーンの定番トラブル)。NeverStreamにすると全ミップが
.uexpに焼き込まれ、.ubulk自体が消えて依存が断てる。
"""

import sys

import unreal

sys.path.insert(0, r"C:\P\Work\PalMod\ue_scripts")
import pgf_config as C

EAL = unreal.EditorAssetLibrary
ar = unreal.AssetRegistryHelpers.get_asset_registry()

count = 0
for ad in ar.get_assets_by_path(C.DIR_MATERIALS, recursive=True):
    obj = ad.get_asset()
    if isinstance(obj, unreal.Texture2D):
        obj.set_editor_property("never_stream", True)
        EAL.save_asset(obj.get_path_name().split(".")[0])
        unreal.log(f"[07_never_stream] {obj.get_name()}")
        count += 1

if count == 0:
    unreal.log_error("[07_never_stream] テクスチャが1枚も見つからない(01の実行順を確認)")
    raise SystemExit(1)
unreal.log(f"[07_never_stream_textures] done ({count} textures)")
