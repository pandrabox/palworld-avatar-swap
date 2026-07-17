# -*- coding: utf-8 -*-
"""PGF差し替えMOD UE自動化 共通設定。全スクリプトがここを参照する。"""

# ディスク側(この作業PCのパス)
WORK_ROOT = r"C:\P\Work\PalMod"
FBX_MAIN = WORK_ROOT + r"\assets\converted\PGF_on_pal_skeleton.fbx"
FBX_DUMMY_HEAD = WORK_ROOT + r"\assets\converted\Dummy_Head.fbx"
# 2026-07-18: 尻尾Hairスロット化は失敗(hairボーンは物理が頭位置で駆動)→
# ダミーに戻した(検査⑪、ぱん裁定)
FBX_DUMMY_HAIR = WORK_ROOT + r"\assets\converted\Dummy_Hair.fbx"
TEX_DIR = WORK_ROOT + r"\assets\for_ue\textures"
# 2026-07-17: Male化に伴いCSVもMale用へ(Female用のままだったのを修正)
CSV_OUTFIT = WORK_ROOT + r"\ue_scripts\OutfitDuplicationList_Male.csv"
CSV_HEAD = WORK_ROOT + r"\ue_scripts\HeadDuplicationList_Male.csv"
CSV_HAIR = WORK_ROOT + r"\ue_scripts\HairDuplicationList.csv"

# プロジェクト側(パルワールドの実パス構造に一致させる。pak_player_assets.txtで実測済み)
# 2026-07-17改訂: ぱんのキャラは男性型なのでMale用に変更。
# スケルトン・物理はプロジェクト内には必要だがpakには同梱しない(05のchunk901隔離)
DIR_OUTFIT = "/Game/Pal/Model/Character/Player/Outfit/SK_Player_Male_Outfit_OldCloth001"
DIR_SKELETON = "/Game/Pal/Model/Character/Skeleton/Human"
DIR_PHYSICS = "/Game/Pal/Model/Character/Player/Body/Female"  # 男性用物理はバニラに無い(女性用のみ)
DIR_HEAD = "/Game/Pal/Model/Character/Player/Head/Head001"
DIR_HAIR = "/Game/Pal/Model/Character/Player/Hair/Hair001"
DIR_MATERIALS = "/Game/Pal/Model/Character/Player/ModelMaterials/MainShader"

NAME_SK_MAIN = "SK_Player_Male_Outfit_OldCloth001"
NAME_SKELETON = "SK_PalHuman_Skeleton"
NAME_PHYSICS = "SK_Player_Female_PhysicsAsset"
NAME_SK_HEAD = "SK_Player_Male_Head001"
NAME_SK_HAIR = "SK_Player_Hair001"

# マテリアルスロット名 → テクスチャファイル名(Noneならテクスチャ無しの単色)
# スロット名はstep02出力のBlender実測: Body=[0body,0karada,0mofu,EPTopaz,EPMetal], PanCloth=[APanCloth]
SLOT_TEXTURES = {
    "0body": "body.png",
    "0karada": "karada.png",
    "0mofu": "mohu.png",
    "APanCloth": "APanCloth.png",
    "EPTopaz": None,   # 宝石(単色: 山吹)
    "EPMetal": None,   # 金属(単色: 銀灰)
}
SLOT_COLORS = {  # テクスチャ無しスロットのベースカラー(RGBA)
    "EPTopaz": (0.85, 0.65, 0.13, 1.0),
    "EPMetal": (0.65, 0.66, 0.70, 1.0),
}
