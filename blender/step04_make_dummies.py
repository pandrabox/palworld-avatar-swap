# -*- coding: utf-8 -*-
"""Step04: Head/Hair置き換え用のダミー(極小)スケルタルメッシュFBXを生成する。

PGFは頭ごと一体のモデルなので、素のプレイヤーの顔・髪は非表示にしたい。
パル骨格に極小三角形(headボーンに100%ウェイト)を付けたメッシュを
SK_Player_Female_Head001 / SK_Player_Hair001 の置き換え用としてFBX出力する。

実行: blender --background --python step04_make_dummies.py
出力: assets/converted/Dummy_Head.fbx, Dummy_Hair.fbx
"""

import os
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config

PSK_ADDON_ZIP = os.path.join(config.WORK_ROOT, "tools", "io_scene_psk_psa_v7.1.0.zip")


def die(msg):
    print(f"[step04][FATAL] {msg}")
    sys.exit(1)


def ensure_psk_addon():
    try:
        bpy.ops.import_scene.psk.get_rna_type()
        return
    except Exception:
        pass
    bpy.ops.extensions.package_install_files(
        repo="user_default", filepath=PSK_ADDON_ZIP, enable_on_install=True)


def build_dummy(out_name):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    ensure_psk_addon()
    before = set(bpy.data.objects)
    bpy.ops.import_scene.psk(filepath=config.PAL_PLAYER_MODEL, scale=1.0)
    new_objs = set(bpy.data.objects) - before
    arm = next((o for o in new_objs if o.type == "ARMATURE"), None)
    if arm is None:
        die("Armatureが無い")
    for o in [o for o in new_objs if o.type == "MESH"]:
        bpy.data.objects.remove(o, do_unlink=True)

    head = arm.data.bones.get("head")
    if head is None:
        die("headボーンが無い")
    pos = arm.matrix_world @ head.head_local

    mesh = bpy.data.meshes.new(out_name)
    s = 0.1  # 0.1cm の極小三角形
    mesh.from_pydata([pos + Vector((0, 0, 0)), pos + Vector((s, 0, 0)), pos + Vector((0, s, 0))],
                     [], [(0, 1, 2)])
    obj = bpy.data.objects.new(out_name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    vg = obj.vertex_groups.new(name="head")
    vg.add([0, 1, 2], 1.0, "REPLACE")
    obj.parent = arm
    mod = obj.modifiers.new(name="Armature", type="ARMATURE")
    mod.object = arm

    arm.name = "Armature"
    arm.data.name = "Armature"

    out = os.path.join(config.OUT_DIR, f"{out_name}.fbx")
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.export_scene.fbx(
        filepath=out, use_selection=True, global_scale=0.01,
        apply_scale_options="FBX_SCALE_NONE", add_leaf_bones=False,
        armature_nodetype="NULL", bake_anim=False, mesh_smooth_type="FACE",
        path_mode="COPY", embed_textures=False)
    print(f"[step04] exported: {out}")


def main():
    build_dummy("Dummy_Head")
    build_dummy("Dummy_Hair")


if __name__ == "__main__":
    main()
