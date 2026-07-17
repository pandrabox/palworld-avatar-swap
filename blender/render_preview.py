# -*- coding: utf-8 -*-
"""step02_retarget.blend の正面/側面プレビューをPNGで出す(検証用)。"""

import math
import os
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config


def scene_bounds():
    lo = Vector((1e9, 1e9, 1e9))
    hi = Vector((-1e9, -1e9, -1e9))
    for obj in bpy.data.objects:
        if obj.type != "MESH":
            continue
        for corner in obj.bound_box:
            w = obj.matrix_world @ Vector(corner)
            lo = Vector(map(min, lo, w))
            hi = Vector(map(max, hi, w))
    return lo, hi


def add_cam_and_render(name, cam_dir, out_path, center, size):
    cam_data = bpy.data.cameras.new(name)
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = size * 1.25
    cam = bpy.data.objects.new(name, cam_data)
    bpy.context.scene.collection.objects.link(cam)
    cam.location = center + cam_dir * size * 3
    direction = center - cam.location
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = cam
    bpy.context.scene.render.filepath = out_path
    bpy.ops.render.render(write_still=True)
    print(f"[preview] {out_path}")


def main():
    blend = os.path.join(config.OUT_DIR, "step02_retarget.blend")
    bpy.ops.wm.open_mainfile(filepath=blend)
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.display.shading.light = "STUDIO"
    sc.display.shading.color_type = "MATERIAL"
    sc.render.resolution_x = 900
    sc.render.resolution_y = 1200
    sc.render.film_transparent = False

    lo, hi = scene_bounds()
    center = (lo + hi) / 2
    size = max(hi.x - lo.x, hi.y - lo.y, hi.z - lo.z)
    print(f"[preview] bounds lo={tuple(round(v,1) for v in lo)} hi={tuple(round(v,1) for v in hi)}")

    add_cam_and_render("CamFront", Vector((0, -1, 0)), os.path.join(config.OUT_DIR, "preview_front.png"), center, size)
    add_cam_and_render("CamSide", Vector((-1, 0, 0)), os.path.join(config.OUT_DIR, "preview_side.png"), center, size)


if __name__ == "__main__":
    main()
