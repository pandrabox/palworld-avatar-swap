# -*- coding: utf-8 -*-
"""Step01: PGF.fbx を読み込み、移植に不要なものを落として正規化する。

実行: blender --background --python step01_import_clean.py
出力: assets/converted/step01_clean.blend

やること:
  1. PGF.fbx をインポート
  2. Armatureの焼き込みスケール(0.74)をApply(これをやらないとウェイト転送・UE取込で事故る)
  3. シェイプキー全削除(品質ライン: 表情は捨てる)
  4. 揺れもの・Humanoid外ボーン(Tail/Wisker等)を削除し、ウェイトを親ボーンへ統合
  5. アバター本体メッシュ(Body/PanCloth)以外のオブジェクトを削除
"""

import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config


def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def import_avatar():
    bpy.ops.import_scene.fbx(filepath=config.AVATAR_FBX)


def find_armature():
    for obj in bpy.data.objects:
        if obj.type == "ARMATURE":
            return obj
    raise RuntimeError("Armatureが見つからない")


def apply_transforms(arm):
    bpy.ops.object.select_all(action="DESELECT")
    arm.select_set(True)
    for child in arm.children_recursive:
        child.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    print(f"[step01] transform applied: {arm.name} scale={tuple(arm.scale)}")


def drop_shape_keys():
    if not config.DROP_SHAPE_KEYS:
        return
    for obj in bpy.data.objects:
        if obj.type == "MESH" and obj.data.shape_keys:
            n = len(obj.data.shape_keys.key_blocks)
            obj.shape_key_clear()
            print(f"[step01] shape keys dropped: {obj.name} ({n})")


def _is_doomed(name):
    return any(name.startswith(p) for p in config.DROP_BONE_PREFIXES)


def drop_extra_bones(arm):
    """Tail/Wisker系ボーンを削除する。削除前に、各メッシュの該当頂点グループの
    ウェイトを「生き残る最寄りの祖先ボーン」のグループへ統合してからグループも消す。
    (これをしないと後段でウェイトが宙に浮く)"""
    # 1) 削除対象ごとに生存祖先を確定(アーマチュアが無傷のうちに)
    survivor = {}
    for b in arm.data.bones:
        if not _is_doomed(b.name):
            continue
        anc = b.parent
        while anc is not None and _is_doomed(anc.name):
            anc = anc.parent
        survivor[b.name] = anc.name if anc is not None else None

    # 2) メッシュ側: 頂点グループを祖先へ統合して削除
    for obj in bpy.data.objects:
        if obj.type != "MESH":
            continue
        for vg in list(obj.vertex_groups):
            if vg.name not in survivor:
                continue
            target_name = survivor[vg.name]
            if target_name is not None:
                target = obj.vertex_groups.get(target_name)
                if target is None:
                    target = obj.vertex_groups.new(name=target_name)
                src_idx = vg.index
                for v in obj.data.vertices:
                    for g in v.groups:
                        if g.group == src_idx and g.weight > 0.0:
                            target.add([v.index], g.weight, "ADD")
            obj.vertex_groups.remove(vg)
        print(f"[step01] weights merged & groups removed on {obj.name}")

    # 3) ボーン削除
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    doomed = [b for b in arm.data.edit_bones if _is_doomed(b.name)]
    names = [b.name for b in doomed]
    for b in doomed:
        arm.data.edit_bones.remove(b)
    bpy.ops.object.mode_set(mode="OBJECT")
    print(f"[step01] bones dropped: {names}")


def drop_non_body_objects(arm):
    keep = set(config.AVATAR_BODY_MESHES)
    for obj in list(bpy.data.objects):
        if obj.type == "MESH" and obj.name not in keep:
            print(f"[step01] object dropped: {obj.name}")
            bpy.data.objects.remove(obj, do_unlink=True)


def main():
    clear_scene()
    import_avatar()
    arm = find_armature()
    apply_transforms(arm)
    drop_shape_keys()
    drop_extra_bones(arm)
    drop_non_body_objects(arm)

    os.makedirs(config.OUT_DIR, exist_ok=True)
    out = os.path.join(config.OUT_DIR, "step01_clean.blend")
    bpy.ops.wm.save_as_mainfile(filepath=out)
    print(f"[step01] saved: {out}")


if __name__ == "__main__":
    main()
