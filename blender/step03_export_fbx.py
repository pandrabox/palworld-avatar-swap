# -*- coding: utf-8 -*-
"""Step03: UE5取り込み用FBXをエクスポートする。

実行: blender --background --python step03_export_fbx.py
入力: assets/converted/step02_retarget.blend
出力: config.OUT_FBX

エクスポート設定はUE向け定番(Leaf Bone付加なし、スケール適用)。
細部はNexus #2826ガイド入手後に突き合わせて調整する。
"""

import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config


def _export(filepath, mesh_names):
    """指定メッシュ+アーマチュアだけを選択してFBX出力する。"""
    arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    bpy.ops.object.select_all(action="DESELECT")
    arm.select_set(True)
    n = 0
    for name in mesh_names:
        obj = bpy.data.objects.get(name)
        if obj is not None:
            obj.select_set(True)
            n += 1
    if n == 0:
        return False
    bpy.context.view_layer.objects.active = arm
    # ガイドp.24: Scale=0.01、Add Leaf Bonesオフ(cm系で作業しているため)
    bpy.ops.export_scene.fbx(
        filepath=filepath,
        use_selection=True,
        global_scale=0.01,
        apply_scale_options="FBX_SCALE_NONE",
        add_leaf_bones=False,
        armature_nodetype="NULL",
        bake_anim=False,
        mesh_smooth_type="FACE",
        use_tspace=True,
        path_mode="COPY",
        embed_textures=False,
    )
    print(f"[step03] exported: {filepath} ({n} meshes)")
    return True


def main():
    blend = os.path.join(config.OUT_DIR, "step02_retarget.blend")
    if not os.path.exists(blend):
        print(f"[step03][FATAL] step02の出力が無い: {blend}")
        sys.exit(1)
    bpy.ops.wm.open_mainfile(filepath=blend)

    os.makedirs(config.OUT_DIR, exist_ok=True)
    _export(config.OUT_FBX, config.AVATAR_BODY_MESHES)
    if getattr(config, "TAIL_TO_HAIR", False):
        if not _export(config.OUT_TAIL_FBX, ["TailHair"]):
            print("[step03][FATAL] TailHairが無い(step02のTAIL_TO_HAIRを確認)")
            sys.exit(1)


if __name__ == "__main__":
    main()
