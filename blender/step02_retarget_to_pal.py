# -*- coding: utf-8 -*-
"""Step02: パルワールドのプレイヤースケルトンへ自動載せ替え(オートフィット付き)。

実行: blender --background --python step02_retarget_to_pal.py
入力: step01_clean.blend + パル側プレイヤーPSK(config.PAL_PLAYER_MODEL)
出力: assets/converted/step02_retarget.blend

処理:
  1. io_scene_psk_psa拡張を(未導入なら)インストールしてPSKをインポート(cm単位のまま)
  2. アバターを全体スケール(体幹長の比で自動算出)でcm系へ持ち上げ
  3. 【オートフィット】BONE_MAPの各ボーンについて、パル側ボーンの位置・向きへ
     ポーズを寄せる(階層順)。ガイドp.7-12の手作業ポーズ合わせの自動化
  4. フィット後の形状をメッシュへ焼き込み(Armatureモディファイア適用)
  5. 頂点グループをパル名にリネーム。マップ外は最寄りのマップ済み祖先へ統合
  6. パル側Armatureへバインドし直し、"Armature"に改名して保存

注意: PGF(チビ体型)はパル骨格の比率に合わせて頭身が変わる。程度はゲーム内で目視判断。
"""

import os
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config

PSK_IMPORT_SCALE = 1.0   # UE素のcm単位のまま
OFFSET_Z = 0.0           # 接地の追い込み用(通常0)
AUTO_FIT = True          # Falseで旧来のリネーム+バインドのみ(手動フィット派向け)
PSK_ADDON_ZIP = os.path.join(config.WORK_ROOT, "tools", "io_scene_psk_psa_v7.1.0.zip")


def die(msg):
    print(f"[step02][FATAL] {msg}")
    sys.exit(1)


def _psk_op_available():
    try:
        bpy.ops.import_scene.psk.get_rna_type()
        return True
    except Exception:
        return False


def ensure_psk_addon():
    if _psk_op_available():
        return
    if not os.path.exists(PSK_ADDON_ZIP):
        die(f"PSKアドオンzipが無い: {PSK_ADDON_ZIP}")
    bpy.ops.extensions.package_install_files(
        repo="user_default", filepath=PSK_ADDON_ZIP, enable_on_install=True)
    if not _psk_op_available():
        die("PSK拡張を入れたのに import_scene.psk が生えていない")
    print("[step02] psk extension installed+enabled")


def load_step01():
    blend = os.path.join(config.OUT_DIR, "step01_clean.blend")
    if not os.path.exists(blend):
        die(f"step01の出力が無い: {blend}")
    bpy.ops.wm.open_mainfile(filepath=blend)


def import_pal_psk():
    if not os.path.exists(config.PAL_PLAYER_MODEL):
        die(f"パル側PSKが無い: {config.PAL_PLAYER_MODEL}")
    before = set(bpy.data.objects)
    bpy.ops.import_scene.psk(filepath=config.PAL_PLAYER_MODEL, scale=PSK_IMPORT_SCALE)
    new_objs = set(bpy.data.objects) - before
    pal_arm = next((o for o in new_objs if o.type == "ARMATURE"), None)
    pal_meshes = [o for o in new_objs if o.type == "MESH"]
    if pal_arm is None:
        die("パル側Armatureが見つからない(PSKインポート失敗?)")
    print(f"[step02] pal skeleton imported: {pal_arm.name}, bones={len(pal_arm.data.bones)}")
    return pal_arm, pal_meshes


# ---------- オートフィット ----------

def _bone_world(arm, bone_name):
    b = arm.data.bones[bone_name]
    mw = arm.matrix_world
    return mw @ b.head_local, mw @ b.tail_local


def global_scale_and_place(avatar_arm, pal_arm):
    """体幹長(Hips頭→Head頭)の比で全体スケールを決め、腰位置を合わせる。"""
    av_hips, _ = _bone_world(avatar_arm, "Hips")
    av_head, _ = _bone_world(avatar_arm, "Head")
    pal_pelvis, _ = _bone_world(pal_arm, config.BONE_MAP["Hips"])
    pal_head, _ = _bone_world(pal_arm, config.BONE_MAP["Head"])
    av_len = (av_head - av_hips).length
    pal_len = (pal_head - pal_pelvis).length
    if av_len < 1e-6:
        die("アバターの体幹長が測れない")
    s = pal_len / av_len
    avatar_arm.scale = (s, s, s)
    bpy.context.view_layer.update()
    av_hips2, _ = _bone_world(avatar_arm, "Hips")
    avatar_arm.location += pal_pelvis - av_hips2
    bpy.context.view_layer.update()
    # スケール・位置をアバター(と子メッシュ)にApplyして以後の計算を素直にする
    bpy.ops.object.select_all(action="DESELECT")
    avatar_arm.select_set(True)
    for child in avatar_arm.children_recursive:
        child.select_set(True)
    bpy.context.view_layer.objects.active = avatar_arm
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    print(f"[step02] global fit: scale x{s:.3f}, pelvis aligned")


# 回転で寄せるのは腕チェーンのみ(A→Tポーズ化)。体型(頭身)は保存する。
# 方向の基準はボーンのテールではなく「関節(子ボーンのhead)位置」から計算する
# (PSKインポータの合成テールは向きの根拠にならないため)。
ROTATE_CHAINS = [
    ("Shoulder.L", "Upper Arm.L"), ("Upper Arm.L", "Lower Arm.L"),
    ("Lower Arm.L", "Hand.L"), ("Hand.L", "Middle Proximal.L"),
    ("Shoulder.R", "Upper Arm.R"), ("Upper Arm.R", "Lower Arm.R"),
    ("Lower Arm.R", "Hand.R"), ("Hand.R", "Middle Proximal.R"),
]


def _pose_head_world(arm, name):
    return arm.matrix_world @ arm.pose.bones[name].head


def auto_fit_pose(avatar_arm, pal_arm):
    """腕チェーンだけ、パル骨格の関節方向へ回転(A→Tポーズ化)。"""
    pal_mw = pal_arm.matrix_world
    done = 0
    for bone_name, child_name in ROTATE_CHAINS:
        if bone_name not in avatar_arm.pose.bones or child_name not in avatar_arm.pose.bones:
            print(f"[step02][WARN] chain skip: {bone_name}->{child_name}")
            continue
        pal_bone = config.BONE_MAP.get(bone_name)
        pal_child = config.BONE_MAP.get(child_name)
        if pal_bone is None or pal_child is None:
            continue
        pal_dir = (pal_mw @ pal_arm.data.bones[pal_child].head_local
                   - pal_mw @ pal_arm.data.bones[pal_bone].head_local).normalized()
        cur_head = _pose_head_world(avatar_arm, bone_name)
        cur_dir = (_pose_head_world(avatar_arm, child_name) - cur_head).normalized()
        rot = cur_dir.rotation_difference(pal_dir).to_matrix().to_4x4()

        pb = avatar_arm.pose.bones[bone_name]
        cur = avatar_arm.matrix_world @ pb.matrix
        trans = cur.translation.copy()
        new_m = rot @ cur
        new_m.translation = trans
        pb.matrix = avatar_arm.matrix_world.inverted() @ new_m
        bpy.context.view_layer.update()
        done += 1
    print(f"[step02] auto-fit: arm chains rotated ({done} bones)")


LIMB_CHAINS = [
    ("Upper Arm.L", "Lower Arm.L"), ("Lower Arm.L", "Hand.L"),
    ("Upper Arm.R", "Lower Arm.R"), ("Lower Arm.R", "Hand.R"),
    ("Upper Leg.L", "Lower Leg.L"), ("Lower Leg.L", "Foot.L"),
    ("Upper Leg.R", "Lower Leg.R"), ("Lower Leg.R", "Foot.R"),
]
END_BONES = ["Hand.L", "Hand.R", "Foot.L", "Foot.R"]


def fit_limb_lengths(avatar_arm, pal_arm):
    """手足の各セグメントをパル骨格の関節間距離まで伸縮する(検査⑦の教訓:
    チビ体型の短い手足はバニラ骨のアニメで引き伸ばされ、腕は細長く・脚は風船化する。
    肘・手首・膝・足首をバニラ位置に合わせて焼き込めば伸縮が起きない)。
    末端(Hand/Foot)は累積スケールを打ち消してパウの大きさを保つ。"""
    if not getattr(config, "FIT_LIMB_LENGTHS", True):
        return
    pal_mw = pal_arm.matrix_world
    for bone_name, child_name in LIMB_CHAINS:
        pb = avatar_arm.pose.bones.get(bone_name)
        cb = avatar_arm.pose.bones.get(child_name)
        pal_bone = config.BONE_MAP.get(bone_name)
        pal_child = config.BONE_MAP.get(child_name)
        if pb is None or cb is None or pal_bone is None or pal_child is None:
            print(f"[step02][WARN] limb-fit skip: {bone_name}")
            continue
        av_len = ((avatar_arm.matrix_world @ cb.head)
                  - (avatar_arm.matrix_world @ pb.head)).length
        pal_len = (pal_mw @ pal_arm.data.bones[pal_child].head_local
                   - pal_mw @ pal_arm.data.bones[pal_bone].head_local).length
        if av_len < 1e-4:
            continue
        k = pal_len / av_len
        pb.scale.y *= k
        bpy.context.view_layer.update()
        print(f"[step02] limb-fit: {bone_name} x{k:.3f} ({av_len:.1f}->{pal_len:.1f}cm)")
    # 末端のワールドスケールを1に戻す(パウ・足先の大きさ維持)
    for name in END_BONES:
        pb = avatar_arm.pose.bones.get(name)
        if pb is None:
            continue
        w = (avatar_arm.matrix_world @ pb.matrix).to_scale()
        pb.scale = (pb.scale[0] / w[0], pb.scale[1] / w[1], pb.scale[2] / w[2])
    bpy.context.view_layer.update()
    print("[step02] limb-fit: end bones normalized")


def pose_arms_reference(avatar_arm):
    """胸固定モード用: Tポーズの腕をconfig.CHEST_ARM_POSEの方向へ下ろす
    (ぱん提示の参照画像準拠。焼き込み後は常時このポーズ)。"""
    chains = [("Upper Arm", "Lower Arm"), ("Lower Arm", "Hand")]
    for side, sx in ((".L", 1.0), (".R", -1.0)):
        for bone_base, child_base in chains:
            bone_name, child_name = bone_base + side, child_base + side
            pb = avatar_arm.pose.bones.get(bone_name)
            cb = avatar_arm.pose.bones.get(child_name)
            if pb is None or cb is None:
                print(f"[step02][WARN] ref-pose skip: {bone_name}")
                continue
            t = config.CHEST_ARM_POSE[bone_base]
            target = Vector((sx * t[0], t[1], t[2])).normalized()
            head = avatar_arm.matrix_world @ pb.head
            child = avatar_arm.matrix_world @ cb.head
            cur_dir = (child - head).normalized()
            rot = cur_dir.rotation_difference(target).to_matrix().to_4x4()
            cur = avatar_arm.matrix_world @ pb.matrix
            trans = cur.translation.copy()
            new_m = rot @ cur
            new_m.translation = trans
            pb.matrix = avatar_arm.matrix_world.inverted() @ new_m
            bpy.context.view_layer.update()
    print("[step02] reference arm pose applied (arms down)")


def apply_arm_spread(avatar_arm):
    """腕を外側(上方)へ開く(config.ARM_SPREAD_DEG)。ポンチョ・尻尾への埋没対策。
    フィット後の焼き込み前に適用。回転軸はワールドY(前後軸)。"""
    import math

    from mathutils import Matrix
    deg = getattr(config, "ARM_SPREAD_DEG", 0.0)
    if abs(deg) < 0.01:
        return
    for bone_name, sign in (("Upper Arm.L", -1.0), ("Upper Arm.R", 1.0)):
        pb = avatar_arm.pose.bones.get(bone_name)
        if pb is None:
            print(f"[step02][WARN] spread skip: {bone_name}")
            continue
        rot = Matrix.Rotation(math.radians(sign * deg), 4, "Y")
        cur = avatar_arm.matrix_world @ pb.matrix
        trans = cur.translation.copy()
        new_m = rot @ cur
        new_m.translation = trans
        pb.matrix = avatar_arm.matrix_world.inverted() @ new_m
        bpy.context.view_layer.update()
    print(f"[step02] arm spread: ±{deg}deg")


def bake_pose_into_meshes(avatar_arm, mesh_objs):
    """フィット後の変形をメッシュに焼き込む(Armatureモディファイア適用)。"""
    for obj in mesh_objs:
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        for mod in list(obj.modifiers):
            if mod.type == "ARMATURE":
                bpy.ops.object.modifier_apply(modifier=mod.name)
        print(f"[step02] baked: {obj.name}")


def snap_to_ground(mesh_objs):
    """メッシュ最下点をz=0(パルの地面)へ揃える。適用したdzを返す。"""
    min_z = min((obj.matrix_world @ Vector(c)).z
                for obj in mesh_objs for c in obj.bound_box)
    for obj in mesh_objs:
        obj.location.z -= min_z
    bpy.ops.object.select_all(action="DESELECT")
    for obj in mesh_objs:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = mesh_objs[0]
    bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)
    print(f"[step02] ground snap: dz={-min_z:.1f}")
    return -min_z


def add_hair_bones(pal_arm):
    """衣装PSK由来のアーマチュアには無い hair_01..09 ボーンをバニラの
    位置・向きで新造する(尻尾のHairスロット化に必要)。
    バニラ値は build/vanilla_refskel_hair.json(髪メッシュから抽出)。
    UE→Blender空間の符号規約は既存ボーンのワールド値で自動較正する。"""
    import json
    import math

    from mathutils import Matrix, Quaternion
    if not getattr(config, "TAIL_TO_HAIR", False):
        return
    with open(r"C:\P\Work\PalMod\build\vanilla_refskel_hair.json",
              encoding="utf-8") as f:
        van = json.load(f)

    # UEローカル → UEワールドへ連鎖合成
    world = {}

    def ue_world(name):
        if name in world:
            return world[name]
        b = van[name]
        q = Quaternion((b["quat"][3], b["quat"][0], b["quat"][1], b["quat"][2]))
        p = Vector(b["pos"])
        if b["parent"] is None:
            world[name] = (q, p)
        else:
            pq, pp = ue_world(b["parent"])
            world[name] = (pq @ q, pp + pq @ p)
        return world[name]

    # 較正: UEワールド→Blenderワールドの変換行列Mを符号付き置換48通りから同定。
    # 回転は行列共役 R_b = M R_ue M^-1 で写す(鏡映を含んでも正しい)
    def blender_world(bone):
        m = pal_arm.matrix_world @ pal_arm.data.bones[bone].matrix_local
        return m.to_3x3(), m.to_translation()

    import itertools
    common = [n for n in van if n in pal_arm.data.bones and "hair" not in n]
    candidates = []
    for perm in itertools.permutations(range(3)):
        for signs in itertools.product((1, -1), repeat=3):
            M = Matrix.Identity(3)
            for row in range(3):
                for col in range(3):
                    M[row][col] = signs[row] if col == perm[row] else 0.0
            candidates.append(M)
    best = None
    for M in candidates:
        Minv = M.inverted()
        perr = rerr = 0.0
        for n in common[:20]:
            uq, up = ue_world(n)
            bR, bp = blender_world(n)
            mp = M @ up
            mR = M @ uq.to_matrix() @ Minv
            perr += (mp - bp).length
            rerr += mR.to_quaternion().rotation_difference(
                bR.to_quaternion()).angle
        score = perr + rerr * 10
        if best is None or score < best[0]:
            best = (score, M, perr / 20, rerr / 20)
    _, Mconv, perr, rerr = best
    print(f"[step02] hair-bone calib: M={[list(r) for r in Mconv]} "
          f"残差 {perr:.3f}cm/{math.degrees(rerr):.2f}deg")
    if perr > 1.0 or rerr > 0.05:
        print("[step02][WARN] hair較正残差が大きい — 尻尾の向きに注意")

    def to_blender(name):
        uq, up = ue_world(name)
        p = Mconv @ up
        q = (Mconv @ uq.to_matrix() @ Mconv.inverted()).to_quaternion()
        return q, p

    bpy.ops.object.select_all(action="DESELECT")
    pal_arm.select_set(True)
    bpy.context.view_layer.objects.active = pal_arm
    bpy.ops.object.mode_set(mode="EDIT")
    eb = pal_arm.data.edit_bones
    inv_arm = pal_arm.matrix_world.inverted()
    order = ["hair_01", "hair_02", "hair_03", "hair_04", "hair_05",
             "hair_06", "hair_07", "hair_08", "hair_09"]
    made = 0
    for name in order:
        if name in eb or name not in van:
            continue
        q, p = to_blender(name)
        b = eb.new(name)
        m = inv_arm @ Matrix.LocRotScale(p, q, Vector((1, 1, 1)))
        b.head = (0, 0, 0)
        b.tail = (0, 4, 0)
        b.matrix = m
        parent_name = van[name]["parent"]
        if parent_name in eb:
            b.parent = eb[parent_name]
        made += 1
    bpy.ops.object.mode_set(mode="OBJECT")
    print(f"[step02] hair bones created: {made}")


def chibi_fit_armature(pal_arm, avatar_arm, dz):
    """【チビ骨格】パル骨格の手足関節をアバターの(フィット・接地後の)関節位置へ
    移動する。ボーンの向き(tail-head方向・roll)は変えず、位置だけ動かす。
    - CHIBI_JOINTS: 明示移動(アバター関節ワールド+dz)
    - CHIBI_TWIST_BONES: 区間比率でスケール配置
    - その他の子孫(指・ソケット・ball等): 最寄りの明示移動祖先のデルタで平行移動
    """
    if not getattr(config, "CHIBI_SKELETON", False):
        return
    # アバター関節のワールド位置(ポーズ済み armatureから; 接地dzを加算)
    joint_map = dict(config.CHIBI_JOINTS)
    if getattr(config, "TAIL_TO_HAIR", False):
        joint_map.update(config.TAIL_HAIR_JOINTS)  # hairボーンを尻尾位置へ移住
    targets = {}
    for pal_name, av_name in joint_map.items():
        pb = avatar_arm.pose.bones.get(av_name)
        if pb is None:
            print(f"[step02][WARN] chibi: avatar bone missing {av_name}")
            continue
        w = avatar_arm.matrix_world @ pb.head
        targets[pal_name] = Vector((w.x, w.y, w.z + dz))

    inv_pal = pal_arm.matrix_world.inverted()
    bpy.ops.object.select_all(action="DESELECT")
    pal_arm.select_set(True)
    bpy.context.view_layer.objects.active = pal_arm
    bpy.ops.object.mode_set(mode="EDIT")
    eb = pal_arm.data.edit_bones

    old_head = {b.name: b.head.copy() for b in eb}
    moved_delta = {}

    # 1) 明示移動(親→子の順で処理されるようボーン階層順に)
    ordered = [b.name for b in pal_arm.data.bones]  # data.bonesは階層順
    for name in ordered:
        if name not in targets or name not in eb:
            continue
        b = eb[name]
        new_head = inv_pal @ targets[name]
        delta = new_head - b.head
        b.tail = b.tail + delta  # 向き・長さ維持で平行移動
        b.head = new_head
        moved_delta[name] = delta

    # 2) twist: 区間比率で配置
    for name, (p_name, c_name) in config.CHIBI_TWIST_BONES.items():
        if name not in eb or p_name not in old_head or c_name not in old_head:
            continue
        b = eb[name]
        old_seg = old_head[c_name] - old_head[p_name]
        new_seg = eb[c_name].head - eb[p_name].head
        if old_seg.length < 1e-6:
            continue
        t = (old_head[name] - old_head[p_name]).length / old_seg.length
        new_head = eb[p_name].head + new_seg * t
        delta = new_head - b.head
        b.tail = b.tail + delta
        b.head = new_head
        moved_delta[name] = delta

    # 3) その他の子孫: 最寄りの移動済み祖先のデルタで平行移動
    def nearest_moved_ancestor(bone):
        p = bone.parent
        while p is not None:
            if p.name in moved_delta:
                return p.name
            p = p.parent
        return None

    for b in eb:
        if b.name in moved_delta:
            continue
        anc = nearest_moved_ancestor(b)
        if anc is None:
            continue
        delta = moved_delta[anc]
        b.tail = b.tail + delta
        b.head = b.head + delta

    bpy.ops.object.mode_set(mode="OBJECT")
    n_arm = sum(1 for k in moved_delta if "arm" in k or "hand" in k)
    n_leg = sum(1 for k in moved_delta if "thigh" in k or "calf" in k or "foot" in k)
    print(f"[step02] chibi skeleton: joints moved arm={n_arm} leg={n_leg} "
          f"(+descendants translated)")


# ---------- 尻尾→Hairスロット(2026-07-18) ----------

def split_tail(body_obj):
    """Bodyから尻尾頂点(Tail系ウェイト合計>閾値)を分離し、TailHairメッシュを返す。
    尻尾グループはhair_02/03へ統合(バニラ髪の2連鎖に載せる)。"""
    if not getattr(config, "TAIL_TO_HAIR", False):
        return None
    tail_idx = {vg.index for vg in body_obj.vertex_groups
                if vg.name in config.TAIL_VGROUPS}
    if not tail_idx:
        print("[step02][WARN] tail groups not found — 分離スキップ")
        return None
    sel = [v.index for v in body_obj.data.vertices
           if sum(g.weight for g in v.groups if g.group in tail_idx)
           > config.TAIL_SPLIT_THRESHOLD]
    if not sel:
        print("[step02][WARN] tail vertices not found")
        return None

    bpy.ops.object.select_all(action="DESELECT")
    body_obj.select_set(True)
    bpy.context.view_layer.objects.active = body_obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="DESELECT")
    bpy.ops.object.mode_set(mode="OBJECT")
    for i in sel:
        body_obj.data.vertices[i].select = True
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_mode(type="VERT")
    bpy.ops.mesh.separate(type="SELECTED")
    bpy.ops.object.mode_set(mode="OBJECT")

    tail_obj = next((o for o in bpy.data.objects
                     if o.name.startswith(body_obj.name + ".")), None)
    if tail_obj is None:
        print("[step02][WARN] 分離オブジェクトが見つからない")
        return None
    tail_obj.name = "TailHair"

    # 尻尾グループ → hair_02/03 へ統合(remapより先。Tailは BONE_MAP外なので
    # 放置すると祖先(pelvis)へ吸われる)
    for src_name, dst_name in config.TAIL_HAIR_MAP.items():
        vg = tail_obj.vertex_groups.get(src_name)
        if vg is None:
            continue
        dst = tail_obj.vertex_groups.get(dst_name)
        if dst is None:
            dst = tail_obj.vertex_groups.new(name=dst_name)
        src_idx = vg.index
        weights = [(v.index, g.weight) for v in tail_obj.data.vertices
                   for g in v.groups if g.group == src_idx and g.weight > 0.0]
        for idx, w in weights:
            dst.add([idx], w, "ADD")
        tail_obj.vertex_groups.remove(vg)
    print(f"[step02] tail split: {len(sel)} verts -> TailHair (hair_02/hair_03)")
    return tail_obj


# ---------- 頂点グループ処理(従来通り) ----------

def build_ancestor_map(avatar_arm):
    result = {}
    for bone in avatar_arm.data.bones:
        if bone.name in config.BONE_MAP:
            continue
        override = next((t for p, t in config.MERGE_TARGET_OVERRIDES.items()
                         if bone.name.startswith(p)), None)
        if override is not None:
            result[bone.name] = override
            continue
        anc = bone.parent
        while anc is not None and anc.name not in config.BONE_MAP:
            anc = anc.parent
        if anc is not None:
            result[bone.name] = config.BONE_MAP[anc.name]
    return result


def remap_vertex_groups(obj, ancestor_map):
    # hair系(尻尾の載せ先)はパル側実在ボーンなので保護する
    protected = set(config.BONE_MAP.values()) | set(
        getattr(config, "TAIL_HAIR_MAP", {}).values())
    for vg in list(obj.vertex_groups):
        if vg.name in config.BONE_MAP:
            vg.name = config.BONE_MAP[vg.name]
    merged = []
    for vg in list(obj.vertex_groups):
        if vg.name in protected:
            continue
        target_name = ancestor_map.get(vg.name)
        if target_name is None:
            print(f"[step02][WARN] 祖先不明のグループを放置: {obj.name}/{vg.name}")
            continue
        target = obj.vertex_groups.get(target_name)
        if target is None:
            target = obj.vertex_groups.new(name=target_name)
        src_idx = vg.index
        for v in obj.data.vertices:
            for g in v.groups:
                if g.group == src_idx and g.weight > 0.0:
                    target.add([v.index], g.weight, "ADD")
        merged.append(vg.name)
        obj.vertex_groups.remove(vg)
    if merged:
        print(f"[step02] merged into ancestors: {obj.name}: {merged}")


def post_merge_groups(obj):
    """パル名リマップ後の統合(指→hand、目→head)。バインド微差の爆発対策。"""
    merged = []
    for src_name, dst_name in config.POST_MERGE_GROUPS.items():
        vg = obj.vertex_groups.get(src_name)
        if vg is None:
            continue
        dst = obj.vertex_groups.get(dst_name)
        if dst is None:
            dst = obj.vertex_groups.new(name=dst_name)
        src_idx = vg.index
        weights = [(v.index, g.weight) for v in obj.data.vertices
                   for g in v.groups if g.group == src_idx and g.weight > 0.0]
        for idx, w in weights:
            dst.add([idx], w, "ADD")
        obj.vertex_groups.remove(vg)
        merged.append(src_name)
    if merged:
        print(f"[step02] post-merge: {obj.name}: {len(merged)} groups folded "
              f"(fingers->hand, eyes->head)")


def rescue_zero_weight_vertices(obj):
    """未塗装頂点にフォールバックボーンを割り当てる(汎用の吹っ飛び対策)。"""
    if not config.ZERO_WEIGHT_FALLBACK_BONE:
        return
    orphans = [v.index for v in obj.data.vertices
               if sum(g.weight for g in v.groups) < 0.01]
    if not orphans:
        return
    vg = obj.vertex_groups.get(config.ZERO_WEIGHT_FALLBACK_BONE)
    if vg is None:
        vg = obj.vertex_groups.new(name=config.ZERO_WEIGHT_FALLBACK_BONE)
    vg.add(orphans, 1.0, "REPLACE")
    print(f"[step02] zero-weight rescue: {obj.name}: {len(orphans)} verts -> "
          f"{config.ZERO_WEIGHT_FALLBACK_BONE}")


def rebind(mesh_objs, pal_arm):
    for obj in mesh_objs:
        obj.location.z += OFFSET_Z
        for mod in list(obj.modifiers):
            if mod.type == "ARMATURE":
                obj.modifiers.remove(mod)
        obj.parent = pal_arm
        obj.matrix_parent_inverse.identity()
        mod = obj.modifiers.new(name="Armature", type="ARMATURE")
        mod.object = pal_arm
        print(f"[step02] rebound: {obj.name} -> {pal_arm.name}")


def main():
    ensure_psk_addon()
    load_step01()

    avatar_arm = next((o for o in bpy.data.objects if o.type == "ARMATURE"), None)
    if avatar_arm is None:
        die("アバターArmatureが見つからない")
    avatar_meshes = [bpy.data.objects[n] for n in config.AVATAR_BODY_MESHES
                     if n in bpy.data.objects]
    if not avatar_meshes:
        die("アバターメッシュが見つからない(step01の出力を確認)")

    ancestor_map = build_ancestor_map(avatar_arm)

    pal_arm, pal_meshes = import_pal_psk()

    pal_bones = {b.name for b in pal_arm.data.bones}
    missing = sorted(set(config.BONE_MAP.values()) - pal_bones)
    if missing:
        die(f"パル側に存在しないボーンがBONE_MAPにある: {missing}")

    dz = 0.0
    if AUTO_FIT:
        global_scale_and_place(avatar_arm, pal_arm)
        if getattr(config, "RIGID_ARMS_TO_CHEST", False):
            # 腕は胸固定。FBXレストはTポーズなので参照ポーズ(腕下ろし)へ回して焼く
            pose_arms_reference(avatar_arm)
            print("[step02] arms->chest mode: 参照ポーズへ回して焼き込み(アニメ非追従)")
        else:
            auto_fit_pose(avatar_arm, pal_arm)
            fit_limb_lengths(avatar_arm, pal_arm)
            apply_arm_spread(avatar_arm)
        bake_pose_into_meshes(avatar_arm, avatar_meshes)
        dz = snap_to_ground(avatar_meshes)
        body = next((o for o in avatar_meshes if o.name == "Body"), None)
        if body is not None:
            tail_obj = split_tail(body)
            if tail_obj is not None:
                avatar_meshes.append(tail_obj)
        add_hair_bones(pal_arm)
        chibi_fit_armature(pal_arm, avatar_arm, dz)

    for obj in avatar_meshes:
        remap_vertex_groups(obj, ancestor_map)
        post_merge_groups(obj)
        rescue_zero_weight_vertices(obj)

    rebind(avatar_meshes, pal_arm)

    bpy.data.objects.remove(avatar_arm, do_unlink=True)
    for o in pal_meshes:
        bpy.data.objects.remove(o, do_unlink=True)

    # ガイドp.20: アーマチュア名は必ず "Armature"
    pal_arm.name = "Armature"
    if pal_arm.data:
        pal_arm.data.name = "Armature"

    out = os.path.join(config.OUT_DIR, "step02_retarget.blend")
    bpy.ops.wm.save_as_mainfile(filepath=out)
    print(f"[step02] saved: {out}")


if __name__ == "__main__":
    main()
