# -*- coding: utf-8 -*-
"""UE内Pythonで実行(2本目): FBX・テクスチャのインポート、マテリアル生成・割当、
スケルトン/物理アセットのバニラパス化、ダミーHead/Hairの配置まで全自動。

前提: 00_setup_folders.py 実行済み。
"""

import os
import sys

import unreal

sys.path.insert(0, r"C:\P\Work\PalMod\ue_scripts")
import pgf_config as C

ASSET_TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary


def import_fbx(fbx_path, dest_dir, skeleton=None):
    opts = unreal.FbxImportUI()
    opts.import_mesh = True
    opts.import_as_skeletal = True
    opts.import_materials = False
    opts.import_textures = False
    opts.import_animations = False
    opts.create_physics_asset = skeleton is None  # 本体のみ物理アセット生成
    if skeleton is not None:
        opts.skeleton = skeleton
    opts.skeletal_mesh_import_data.set_editor_property("import_morph_targets", False)
    opts.skeletal_mesh_import_data.set_editor_property("convert_scene", True)

    task = unreal.AssetImportTask()
    task.filename = fbx_path
    task.destination_path = dest_dir
    task.automated = True
    task.save = True
    task.options = opts
    ASSET_TOOLS.import_asset_tasks([task])
    paths = list(task.imported_object_paths)
    unreal.log(f"imported: {paths}")
    return paths


def find_asset(dest_dir, cls):
    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    for ad in ar.get_assets_by_path(dest_dir, recursive=False):
        obj = ad.get_asset()
        if isinstance(obj, cls):
            return obj
    return None


def rename_asset(obj, new_dir, new_name):
    old_path = obj.get_path_name().split(".")[0]
    new_path = f"{new_dir}/{new_name}"
    if old_path == new_path:
        return obj
    if not EAL.rename_asset(old_path, new_path):
        unreal.log_error(f"rename failed: {old_path} -> {new_path}")
        return obj
    unreal.log(f"renamed: {old_path} -> {new_path}")
    return EAL.load_asset(new_path)


def import_textures():
    result = {}
    for name in set(v for v in C.SLOT_TEXTURES.values() if v):
        task = unreal.AssetImportTask()
        task.filename = os.path.join(C.TEX_DIR, name)
        task.destination_path = C.DIR_MATERIALS
        task.automated = True
        task.save = True
        ASSET_TOOLS.import_asset_tasks([task])
        if task.imported_object_paths:
            result[name] = EAL.load_asset(task.imported_object_paths[0])
            unreal.log(f"texture: {name}")
        else:
            unreal.log_error(f"texture import failed: {name}")
    return result


def make_material(slot, tex_asset, color):
    name = f"M_PGF_{slot}"
    path = f"{C.DIR_MATERIALS}/{name}"
    if EAL.does_asset_exist(path):
        return EAL.load_asset(path)
    mat = ASSET_TOOLS.create_asset(name, C.DIR_MATERIALS, unreal.Material,
                                   unreal.MaterialFactoryNew())
    mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_MASKED)
    mat.set_editor_property("two_sided", False)
    # 検査④(2026-07-17)の教訓: 使用フラグ無しだとシップビルドのスケルタルメッシュ上で
    # デフォルトマテリアル(チェッカー)に差し替えられる。エディタは自動付与するが
    # cookは付与しないので明示必須
    mat.set_editor_property("used_with_skeletal_mesh", True)
    if tex_asset is not None:
        node = MEL.create_material_expression(
            mat, unreal.MaterialExpressionTextureSample, -400, 0)
        node.texture = tex_asset
        MEL.connect_material_property(node, "RGB", unreal.MaterialProperty.MP_BASE_COLOR)
        MEL.connect_material_property(node, "A", unreal.MaterialProperty.MP_OPACITY_MASK)
    else:
        node = MEL.create_material_expression(
            mat, unreal.MaterialExpressionConstant4Vector, -400, 0)
        node.set_editor_property("constant", unreal.LinearColor(*color))
        MEL.connect_material_property(node, "", unreal.MaterialProperty.MP_BASE_COLOR)
    MEL.recompile_material(mat)
    EAL.save_asset(mat.get_path_name().split(".")[0])
    unreal.log(f"material: {name}")
    return mat


def assign_materials(sk_mesh, materials_by_slot):
    mats = list(sk_mesh.materials)
    new_mats = []
    for m in mats:
        slot = str(m.material_slot_name)
        replacement = materials_by_slot.get(slot)
        if replacement is not None:
            new_mats.append(unreal.SkeletalMaterial(
                material_interface=replacement, material_slot_name=slot))
            unreal.log(f"slot '{slot}' -> {replacement.get_name()}")
        else:
            new_mats.append(m)
            unreal.log_warning(f"slot '{slot}' に対応マテリアル無し(そのまま)")
    sk_mesh.set_editor_property("materials", new_mats)
    EAL.save_asset(sk_mesh.get_path_name().split(".")[0])


def main():
    # 1) 本体FBX
    import_fbx(C.FBX_MAIN, C.DIR_OUTFIT)
    sk = find_asset(C.DIR_OUTFIT, unreal.SkeletalMesh)
    if sk is None:
        unreal.log_error("本体SkeletalMeshが見つからない")
        return
    sk = rename_asset(sk, C.DIR_OUTFIT, C.NAME_SK_MAIN)

    skel = find_asset(C.DIR_OUTFIT, unreal.Skeleton)
    if skel is not None:
        skel = rename_asset(skel, C.DIR_SKELETON, C.NAME_SKELETON)
    phys = find_asset(C.DIR_OUTFIT, unreal.PhysicsAsset)
    if phys is not None:
        phys = rename_asset(phys, C.DIR_PHYSICS, C.NAME_PHYSICS)

    # 2) テクスチャ+マテリアル
    textures = import_textures()
    mats = {}
    for slot, tex_name in C.SLOT_TEXTURES.items():
        tex = textures.get(tex_name) if tex_name else None
        mats[slot] = make_material(slot, tex, C.SLOT_COLORS.get(slot, (1, 1, 1, 1)))
    assign_materials(sk, mats)

    # 3) ダミーHead/Hair(本体と同じスケルトンを割り当ててインポート)
    if skel is not None:
        import_fbx(C.FBX_DUMMY_HEAD, C.DIR_HEAD, skeleton=skel)
        head = find_asset(C.DIR_HEAD, unreal.SkeletalMesh)
        if head:
            rename_asset(head, C.DIR_HEAD, C.NAME_SK_HEAD)
        import_fbx(C.FBX_DUMMY_HAIR, C.DIR_HAIR, skeleton=skel)
        hair = find_asset(C.DIR_HAIR, unreal.SkeletalMesh)
        if hair:
            hair = rename_asset(hair, C.DIR_HAIR, C.NAME_SK_HAIR)
            # 尻尾メッシュ化(2026-07-18)に伴い、Hairにもマテリアルを割り当てる
            assign_materials(hair, mats)

    unreal.log("[01_import_and_setup] done — 目視確認: SKを開いてメッシュ・マテリアル・スケルトンを確認せよ")


main()
