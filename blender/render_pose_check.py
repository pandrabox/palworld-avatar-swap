# -*- coding: utf-8 -*-
"""オフライン官能検査: step02_retarget.blend にゲーム相当のポーズを付けて
変形品質をレンダリングで確認する(ゲーム非起動、2026-07-17ぱん指示の一環)。

ポーズ2種:
  idle   — 腕を体側へ下ろす(立ち/歩きで腕肩が崩れる報告の再現系)
  crouch — 股関節・膝を曲げる(しゃがみで脚が崩れる報告の再現系)

回転の与え方はstep02のauto_fitと同じ「子関節方向を目標方向へ回す」方式。
出力: assets/converted/posecheck_<pose>_{front,side}.png
"""

import os
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config
from render_preview import scene_bounds, add_cam_and_render

# ポーズ定義: (ボーン, 子関節, 目標方向(ワールド)) を階層順に適用
# 座標系はPSKインポート後のBlenderワールド(Z上)。方向はレンダで目視検証する
POSES = {
    "idle": [
        ("upperarm_l", "lowerarm_l", Vector((0.25, 0.0, -0.97))),
        ("upperarm_r", "lowerarm_r", Vector((-0.25, 0.0, -0.97))),
        ("lowerarm_l", "hand_l", Vector((0.3, -0.2, -0.93))),
        ("lowerarm_r", "hand_r", Vector((-0.3, -0.2, -0.93))),
    ],
    "tailtest": [
        # 尻尾の揺れ確認: hair_02(根本)を横上へ倒す → 尻尾だけが曲がれば合格
        ("hair_02", "hair_03", Vector((0.6, 0.3, 0.74))),
    ],
    "crouch": [
        # 実ゲームのしゃがみ相当: 骨盤降下+太もも前方~55°+軽い前傾。
        # 剛体脚なのでcalfの回転は無効(ウェイトなし)
        ("@translate", "pelvis", Vector((0, 0, -22))),
        ("thigh_l", "calf_l", Vector((0.08, -0.72, -0.69))),
        ("thigh_r", "calf_r", Vector((-0.08, -0.72, -0.69))),
        ("spine_01", "spine_02", Vector((0, -0.15, 0.99))),
    ],
}


def apply_pose(arm, steps):
    for bone_name, child_name, target in steps:
        if bone_name == "@translate":
            pb = arm.pose.bones.get(child_name)
            if pb is not None:
                from mathutils import Matrix
                cur = arm.matrix_world @ pb.matrix
                new_m = Matrix.Translation(target) @ cur
                pb.matrix = arm.matrix_world.inverted() @ new_m
                bpy.context.view_layer.update()
            continue
        pb = arm.pose.bones.get(bone_name)
        cb = arm.pose.bones.get(child_name)
        if pb is None or cb is None:
            print(f"[posecheck][WARN] bone missing: {bone_name}/{child_name}")
            continue
        head = arm.matrix_world @ pb.head
        child = arm.matrix_world @ cb.head
        cur_dir = (child - head).normalized()
        rot = cur_dir.rotation_difference(target.normalized()).to_matrix().to_4x4()
        cur = arm.matrix_world @ pb.matrix
        trans = cur.translation.copy()
        new_m = rot @ cur
        new_m.translation = trans
        pb.matrix = arm.matrix_world.inverted() @ new_m
        bpy.context.view_layer.update()


def reset_pose(arm):
    for pb in arm.pose.bones:
        pb.matrix_basis.identity()
    bpy.context.view_layer.update()


def main():
    blend = os.path.join(config.OUT_DIR, "step02_retarget.blend")
    bpy.ops.wm.open_mainfile(filepath=blend)
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.display.shading.light = "STUDIO"
    sc.display.shading.color_type = "MATERIAL"
    sc.render.resolution_x = 900
    sc.render.resolution_y = 1200

    arm = next((o for o in bpy.data.objects if o.type == "ARMATURE"), None)
    if arm is None:
        print("[posecheck][FATAL] armature not found")
        sys.exit(1)

    lo, hi = scene_bounds()
    center = (lo + hi) / 2
    size = max(hi.x - lo.x, hi.y - lo.y, hi.z - lo.z)

    for pose_name, steps in POSES.items():
        reset_pose(arm)
        apply_pose(arm, steps)
        for cam_name, cam_dir in (("front", Vector((0, -1, 0))),
                                  ("side", Vector((-1, 0, 0)))):
            out = os.path.join(config.OUT_DIR, f"posecheck_{pose_name}_{cam_name}.png")
            add_cam_and_render(f"Cam_{pose_name}_{cam_name}", cam_dir, out, center, size)
    print("[render_pose_check] done")


if __name__ == "__main__":
    main()
