# -*- coding: utf-8 -*-
"""PalMod Blenderパイプライン共通設定。

全スクリプトがここを参照する。パスやボーンマップの変更はこのファイルだけで済ませる。
"""

import os

WORK_ROOT = r"C:\P\Work\PalMod"

# 入力(2026-07-17夜: ぱん指定で原本FBXに差し替え。構造は旧版と同一と棚卸し確認済み)
AVATAR_FBX = r"C:\P\VRC\Project\PPal\PGF.fbx"
# パル側プレイヤーモデル。ガイド#2826同梱PSKはベータ期抽出で、1.0とは肩の基準
# ポーズが違う(clavicle/upperarm 10.1°・4.93cm — 検査⑤で腕が背中に埋まった真因)。
# scripts/patch_psk_to_1_0.py でREFSKELTをバニラ1.0値に書き換えた版を使うこと
PAL_PLAYER_MODEL = os.path.join(
    WORK_ROOT, "assets", "from_palworld", "SK_Player_OldCloth001_1_0patched.psk")

# 出力
OUT_DIR = os.path.join(WORK_ROOT, "assets", "converted")
OUT_FBX = os.path.join(OUT_DIR, "PGF_on_pal_skeleton.fbx")

# PGF.fbx 側の既知情報(research/avatar-inventory.md より)
AVATAR_ARMATURE_NAME = "Armature"      # ノードスケール0.74012613が焼き込まれている → step01でApply済み
AVATAR_BODY_MESHES = ["Body", "PanCloth"]  # 素体+衣装(同一FBX内)

# 捨てるもの(品質ライン: 表情は捨てる)
DROP_SHAPE_KEYS = True
# Humanoid外の追加ボーン(ギミック)。前方一致でstep01が削除する。
# 2026-07-18: 尻尾の揺れ実装(TAIL_TO_HAIR)のためTailは温存に変更
DROP_BONE_PREFIXES = ["Wisker"]

# 【尻尾の揺れ 2026-07-18ぱん依頼「しっぽやわらかくできる? Hairにするんだっけ」】
# バニラ髪メッシュ解剖の結果: hair_01(単独)+2連鎖×4(hair_02→03等)が
# head配下に実在。最長の2連鎖 hair_02→03 に尻尾を載せ、Hairスロットの
# メッシュとして出力する(ゲーム側が髪ボーンを揺らす仕組みに乗る)。
# 関節位置はメッシュRefSkeleton側が勝つ(チビ骨格で実証済み)ので、
# hair_02/03を尻尾の位置へ移住させる
# 2026-07-18検査⑪: 失敗判明 → False固定。hairボーンは物理がアニメ側の位置
# (頭)で駆動するため、尻尾が頭に付いて体からちぎれた。手足(Skeleton mode)と
# 違いhairボーンの位置はメッシュ側が勝てない。ぱん裁定「もどそう」
TAIL_TO_HAIR = False
# 尻尾頂点の判定: これらのグループの合計ウェイトが閾値超の頂点を分離
TAIL_VGROUPS = ["Tail Root", "Tail.001", "Tail.002", "Tail.003", "Tail.004", "Tail.005"]
TAIL_SPLIT_THRESHOLD = 0.5
# 尻尾ボーン → hairボーンのウェイト統合先(根本半分=hair_02、先端半分=hair_03)
TAIL_HAIR_MAP = {
    "Tail Root": "hair_02", "Tail.001": "hair_02", "Tail.002": "hair_02",
    "Tail.003": "hair_03", "Tail.004": "hair_03", "Tail.005": "hair_03",
}
# hairボーンの移住先(チビ位置化と同じ仕組み。アバターの尻尾ボーン位置を使う)
TAIL_HAIR_JOINTS = {"hair_02": "Tail Root", "hair_03": "Tail.003"}
# 出力先(HairスロットFBX)
OUT_TAIL_FBX = os.path.join(OUT_DIR, "PGF_tail_hair.fbx")

# PGFの実ボーン名(step01_clean.blendから実測) → パル骨格の実ボーン名
# パル側の名前はガイド#2826同梱のWeightTransferMap.csv(Xianyun実例)で確認したUEマネキン風命名。
# 注: PGFにはつま先ボーンが無い → ball_l/r は未使用のまま(実害なし)
BONE_MAP = {
    "Hips": "pelvis",
    "Spine": "spine_01",
    "Chest": "spine_02",
    "Neck": "neck_01",
    "Head": "head",
    "EyeLeft": "eyes_l",
    "EyeRight": "eyes_r",
    "Shoulder.L": "clavicle_l", "Shoulder.R": "clavicle_r",
    "Upper Arm.L": "upperarm_l", "Upper Arm.R": "upperarm_r",
    "Lower Arm.L": "lowerarm_l", "Lower Arm.R": "lowerarm_r",
    "Hand.L": "hand_l", "Hand.R": "hand_r",
    "Upper Leg.L": "thigh_l", "Upper Leg.R": "thigh_r",
    "Lower Leg.L": "calf_l", "Lower Leg.R": "calf_r",
    "Foot.L": "foot_l", "Foot.R": "foot_r",
    "Thumb Proximal.L": "thumb_01_l", "Thumb Intermediate.L": "thumb_02_l", "Thumb Distal.L": "thumb_03_l",
    "Thumb Proximal.R": "thumb_01_r", "Thumb Intermediate.R": "thumb_02_r", "Thumb Distal.R": "thumb_03_r",
    "Index Proximal.L": "index_01_l", "Index Intermediate.L": "index_02_l", "Index Distal.L": "index_03_l",
    "Index Proximal.R": "index_01_r", "Index Intermediate.R": "index_02_r", "Index Distal.R": "index_03_r",
    "Middle Proximal.L": "middle_01_l", "Middle Intermediate.L": "middle_02_l", "Middle Distal.L": "middle_03_l",
    "Middle Proximal.R": "middle_01_r", "Middle Intermediate.R": "middle_02_r", "Middle Distal.R": "middle_03_r",
    "Ring Proximal.L": "ring_01_l", "Ring Intermediate.L": "ring_02_l", "Ring Distal.L": "ring_03_l",
    "Ring Proximal.R": "ring_01_r", "Ring Intermediate.R": "ring_02_r", "Ring Distal.R": "ring_03_r",
    "Little Proximal.L": "pinky_01_l", "Little Intermediate.L": "pinky_02_l", "Little Distal.L": "pinky_03_l",
    "Little Proximal.R": "pinky_01_r", "Little Intermediate.R": "pinky_02_r", "Little Distal.R": "pinky_03_r",
}

# BONE_MAPに無い頂点グループ(cheek/mohu/Pira/Head_L等の装飾ボーン)の扱い:
# アーマチュアの親を遡り、最初にBONE_MAPに載っている祖先ボーンへウェイトを統合する
MERGE_UNMAPPED_TO_ANCESTOR = True

# 汎用安全網: 合計ウェイトがほぼ0の頂点(未塗装・ParentConstraint頼みの飾り等)に
# このボーンを1.0で自動割当する。Noneで無効。PGFでは該当0個だが、
# 他モデルを通す際の「吹っ飛び対策」(2026-07-17ぱん発案)
ZERO_WEIGHT_FALLBACK_BONE = "pelvis"

# 祖先統合の上書き(前方一致 → パル側ボーン名)。
# Pira/PanAcc/Magatamaは胸元の飾り(実測z≈1.0、Chest高さ)なので、
# 祖先(Hips→pelvis)ではなくchest相当のspine_02に固定する(2026-07-17ぱん承認)
MERGE_TARGET_OVERRIDES = {
    "Pira": "spine_02",
    "PanAcc": "spine_02",
    "Magatama": "spine_02",
}

# リマップ後の統合(パル側ボーン名 → パル側ボーン名)。
# 検査②-2(2026-07-17)で手指が破裂した対策: PSK再構築スケルトンと実行時の
# バニラ1.0スケルトンは末端ボーン(指・目)の向き・位置が厳密一致する保証がなく、
# バインドの微差が細ボーンで爆発する。PGFはミトン型パウなので指ボーンは不要、
# 目もHead追従で十分 → ウェイトごと親に畳んでバインド精度依存を断つ
POST_MERGE_GROUPS = {}
for _finger in ("thumb", "index", "middle", "ring", "pinky"):
    for _seg in ("01", "02", "03"):
        for _side in ("l", "r"):
            POST_MERGE_GROUPS[f"{_finger}_{_seg}_{_side}"] = f"hand_{_side}"
POST_MERGE_GROUPS["eyes_l"] = "head"
POST_MERGE_GROUPS["eyes_r"] = "head"

# 手足の剛体化(検査⑦の応急案)。CHIBI_SKELETON方式の導入(2026-07-18未明、
# ぱん「バニラモデルの関節の角度だけもってこれないの?」)に伴い既定False。
# CHIBI_SKELETONが失敗した場合のフォールバックとして残す
RIGID_LIMBS = False

# 腕の胸固定(検査⑦bの応急案)。同上の理由で既定False
RIGID_ARMS_TO_CHEST = False

# 【本命 2026-07-18】チビ骨格方式: パル骨格の手足関節(肘・手首・膝・足首等)を
# アバターのフィット後の関節位置へ移動してからバインドする。
# UEのアニメ再生は「回転=アニメ由来、関節位置=メッシュ側RefSkeleton由来」に
# なり得る(Translation Retargeting)ため、これが効けば
# 『バニラの関節角度×チビの関節位置』= 腕脚が動き、かつ伸びない。
# 効かない(=位置もアニメ由来)ならゲーム内で再び伸びが出る → その時は
# RIGID_LIMBS系へ戻す。どちらかはゲーム内テスト1回で確定する
CHIBI_SKELETON = True

# パル骨格ボーン → アバター関節(フィット後のワールド位置の供給元)。
# 検査⑨で「動く・伸びない」実証(Translation Retargeting=メッシュ位置採用)。
# 同⑨で頭が外れて見えた対策: 首・頭・背骨・鎖骨のピボットもチビ位置へ移動する
# (頭の回転がバニラの高い首ピボット中心に回っていたのが頭外れの正体)
CHIBI_JOINTS = {
    "spine_01": "Spine", "spine_02": "Chest",
    "neck_01": "Neck", "head": "Head",
    "clavicle_l": "Shoulder.L", "clavicle_r": "Shoulder.R",
    "upperarm_l": "Upper Arm.L", "lowerarm_l": "Lower Arm.L", "hand_l": "Hand.L",
    "upperarm_r": "Upper Arm.R", "lowerarm_r": "Lower Arm.R", "hand_r": "Hand.R",
    "thigh_l": "Upper Leg.L", "calf_l": "Lower Leg.L", "foot_l": "Foot.L",
    "thigh_r": "Upper Leg.R", "calf_r": "Lower Leg.R", "foot_r": "Foot.R",
}
# セグメント中間のtwistボーンは区間比率でスケール配置する
CHIBI_TWIST_BONES = {
    "upperarm_twist_01_l": ("upperarm_l", "lowerarm_l"),
    "upperarm_twist_01_r": ("upperarm_r", "lowerarm_r"),
    "lowerarm_twist_01_l": ("lowerarm_l", "hand_l"),
    "lowerarm_twist_01_r": ("lowerarm_r", "hand_r"),
    "thigh_twist_01_l": ("thigh_l", "calf_l"),
    "thigh_twist_01_r": ("thigh_r", "calf_r"),
    "calf_twist_01_l": ("calf_l", "foot_l"),
    "calf_twist_01_r": ("calf_r", "foot_r"),
}

# 剛体化の統合は「指→hand」の後に処理される必要がある(dictの挿入順=処理順)
if RIGID_LIMBS:
    _arm_target = {"l": "spine_02", "r": "spine_02"} if RIGID_ARMS_TO_CHEST \
        else {"l": "upperarm_l", "r": "upperarm_r"}
    for _side in ("l", "r"):
        POST_MERGE_GROUPS[f"hand_{_side}"] = _arm_target[_side]
        POST_MERGE_GROUPS[f"lowerarm_{_side}"] = _arm_target[_side]
        if RIGID_ARMS_TO_CHEST:
            POST_MERGE_GROUPS[f"upperarm_{_side}"] = "spine_02"
            POST_MERGE_GROUPS[f"clavicle_{_side}"] = "spine_02"
        POST_MERGE_GROUPS[f"foot_{_side}"] = f"thigh_{_side}"
        POST_MERGE_GROUPS[f"calf_{_side}"] = f"thigh_{_side}"

# 手足セグメントをバニラ骨格の関節間距離に合わせて伸縮する。
# 2026-07-18未明ぱん裁定により False 固定(伸縮も伸びも許さない。剛体化は
# RIGID_LIMBS 側で対処 — POST_MERGE_GROUPSの手前で定義)
FIT_LIMB_LENGTHS = False

# 腕の外開き角(度)。検査⑤⑥で「腕がポンチョと尻尾に埋まって見えない」対策。
# フィット後にUpper Armをこの角度だけ外側(上方)へ開いてから焼き込む。
# バインドはバニラ1.0のままなのでアニメ互換は崩れない(全ポーズが一律この分開く)。
# 0で無効。埋まりが残るなら増やし、開きすぎ(万歳気味)なら減らす
# (CHIBI_SKELETON方式では腕がアニメ追従するため0に戻す。焼き込みバイアスは
#  全アニメにオフセットが乗るので、埋まりが再発した場合のみ小さく試す)
ARM_SPREAD_DEG = 0.0

# (廃止 2026-07-18: RIGID_ARMS_TO_CHESTにより腕はアニメ非追従になったため
#  前傾・開き角の調整は不要。ARM_SPREAD_DEGも同モードでは無視される)

# 胸固定モードの腕ポーズ(ワールド方向ベクトル、左側。右はxを反転)。
# FBXレストはTポーズなので、焼き込み前にこの方向へ下ろす。
# ぱん提示の参照画像(腕を体側に下ろしパウがポンチョ脇)に合わせて
# posecheck/previewレンダで目視調整する
CHEST_ARM_POSE = {
    "Upper Arm": (0.50, -0.04, -0.87),   # 肩→肘: 下・外(体側の輪郭に沿わせる)
    "Lower Arm": (0.12, -0.08, -0.99),   # 肘→手首: ほぼ真下・体に寄せる
}
