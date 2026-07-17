# -*- coding: utf-8 -*-
"""MOD pakのオフライン全数検品(ゲーム非起動)。ぱんに官能検査を頼む前に必ず通す。

これまでゲーム内テストで発覚した敗因は全て機械検証可能だった:
  平坦化パス(検査②-1) / SM6欠落(検査③) / バインドポーズずれ(検査③) /
  スケルトン同梱(検査①) / 性別違い(検査①)
本スクリプトはそれら全クラスの再発を検知するゲート集。1つでも落ちたら配布禁止。

使い方: python preflight_pak.py
  対象: build/PGF_PlayerSwap_P.pak + build/pak_extract + build/logs/cook.log
  基準: バニラPal-Windows.pakのインデックス + build/vanilla_refskel_male_1_0.json
"""

import glob
import io
import json
import os
import re
import struct
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from refskel_diff import read_names, find_refskeleton, quat_angle_deg

WORK = r"C:\P\Work\PalMod"
MOD_PAK = os.path.join(WORK, "build", "PGF_PlayerSwap_P.pak")
EXTRACT = os.path.join(WORK, "build", "pak_extract")
COOK_LOG = os.path.join(WORK, "build", "logs", "cook.log")
VANILLA_PAK = r"C:\Program Files (x86)\Steam\steamapps\common\Palworld\Pal\Content\Paks\Pal-Windows.pak"
VANILLA_JSON = os.path.join(WORK, "build", "vanilla_refskel_male_1_0.json")
UNREALPAK = r"C:\Program Files\Epic Games\UE_5.1\Engine\Binaries\Win64\UnrealPak.exe"

MAGIC = 0x5A6F12E1

# 期待収録数(CSV+本体)
EXPECT = {"outfit_sk": 30, "head_sk": 26, "hair_sk": 37, "materials": 6, "textures": 4}

results = []


def gate(name, ok, detail=""):
    results.append((name, ok, detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


def read_fstring(f):
    (n,) = struct.unpack("<i", f.read(4))
    if n == 0:
        return ""
    if n > 0:
        return f.read(n)[:-1].decode("ascii", errors="replace")
    return f.read(-n * 2)[:-2].decode("utf-16-le", errors="replace")


def read_pak_index(path):
    """pak v11のFullDirectoryIndexから (mount, [entry...]) を返す。"""
    with open(path, "rb") as f:
        f.seek(0, 2)
        size = f.tell()
        f.seek(size - min(4096, size))
        tail = f.read()
        i = tail.rfind(struct.pack("<I", MAGIC))
        off = size - len(tail) + i
        f.seek(off + 8)
        index_offset, index_size = struct.unpack("<qq", f.read(16))
        f.seek(index_offset)
        idx = io.BytesIO(f.read(index_size))
        mount = read_fstring(idx)
        idx.read(4 + 8)  # num_entries, seed
        (has_phi,) = struct.unpack("<i", idx.read(4))
        if has_phi:
            idx.read(36)
        (has_fdi,) = struct.unpack("<i", idx.read(4))
        if not has_fdi:
            raise RuntimeError("FullDirectoryIndexなし")
        fdi_offset, fdi_size = struct.unpack("<qq", idx.read(16))
        f.seek(fdi_offset)
        fdi = io.BytesIO(f.read(fdi_size))
        (num_dirs,) = struct.unpack("<i", fdi.read(4))
        paths = []
        for _ in range(num_dirs):
            d = read_fstring(fdi)
            (n_files,) = struct.unpack("<i", fdi.read(4))
            for _ in range(n_files):
                fn = read_fstring(fdi)
                fdi.read(4)
                paths.append(d + fn)
        return mount, paths


def main():
    print("=== preflight: MOD pakオフライン検品 ===")
    if not os.path.exists(MOD_PAK):
        gate("pak存在", False, MOD_PAK)
        return finish()

    mount, entries = read_pak_index(MOD_PAK)
    _, vanilla_entries = read_pak_index(VANILLA_PAK)
    vanilla_set = set(vanilla_entries)

    # G1: マウントポイント
    gate("G1 マウントポイント", mount == "../../../Pal/Content/Pal/Model/Character/",
         mount)

    # G2: パス整合(平坦化検知)。新規アセット(ModelMaterials)以外の全エントリは
    # バニラに同一パスが存在しなければならない(=正しく上書きされる証拠)
    full = [mount.replace("../../../", "") + e for e in entries]
    new_asset_ok = re.compile(r".*/ModelMaterials/MainShader/[^/]+$")
    anchor_ok = re.compile(r".*_PGF_mount_anchor\.txt$")
    bad = [p for p in full
           if not (p in vanilla_set or new_asset_ok.match(p) or anchor_ok.match(p))]
    gate("G2 全エントリのパスがバニラと一致(平坦化なし)", not bad,
         f"不一致{len(bad)}件 例:{bad[:3]}" if bad else f"{len(full)}件OK")

    # G3: 禁止物(共有スケルトン・素体・Female・ubulk)
    forbidden = [p for p in entries
                 if "Skeleton/" in p or "/Body/" in p or "Female" in p
                 or p.endswith(".ubulk")]
    gate("G3 禁止物ゼロ(Skeleton/Body/Female/ubulk)", not forbidden,
         str(forbidden[:3]) if forbidden else "")

    # G4: 収録数
    n_outfit = len([p for p in entries if "/Outfit/" in p and p.endswith(".uasset")])
    n_head = len([p for p in entries if "/Head/" in p and p.endswith(".uasset")])
    n_hair = len([p for p in entries if "/Hair/" in p and p.endswith(".uasset")])
    n_mat = len([p for p in entries
                 if "MainShader/M_" in p and p.endswith(".uasset")])
    n_tex = len([p for p in entries
                 if "MainShader/" in p and "/M_" not in p and p.endswith(".uasset")])
    counts = (n_outfit, n_head, n_hair, n_mat, n_tex)
    expect = tuple(EXPECT.values())
    gate("G4 収録数(衣装/頭/髪/マテリアル/テクスチャ)", counts == expect,
         f"実測{counts} 期待{expect}")

    # G5: バインド回転=バニラ1.0(全衣装SK)。
    # 2026-07-18 CHIBI_SKELETON化により位置はチビ骨格独自値が正 → 回転のみ照合
    with open(VANILLA_JSON, encoding="utf-8") as f:
        vanilla_ref = json.load(f)
    sk_files = glob.glob(os.path.join(EXTRACT, "Player", "Outfit", "**", "SK_*.uasset"),
                         recursive=True)
    worst = (0.0, "")
    n_checked = 0
    for sk in sk_files:
        names = read_names(sk)
        bones, transforms, _ = find_refskeleton(sk[:-7] + ".uexp", names)
        for (bname, _p), t in zip(bones, transforms):
            vb = vanilla_ref.get(bname)
            if vb is None:
                continue
            dr = quat_angle_deg(t[0:4], vb["quat"])
            if dr > worst[0]:
                worst = (dr, f"{os.path.basename(sk)}:{bname}")
        n_checked += 1
    gate("G5 バインド回転=バニラ1.0(全衣装SK、位置はチビ骨格)",
         n_checked == EXPECT["outfit_sk"] and worst[0] < 0.1,
         f"{n_checked}体検証 最大回転差 {worst[0]:.3f}deg ({worst[1]})")

    # G6: 参照の閉包性(cook済みアセットが参照する/Game/パスが自pak∪バニラに実在)
    own_pkgs = {p.rsplit(".", 1)[0] for p in full}
    vanilla_pkgs = {p.rsplit(".", 1)[0] for p in vanilla_entries if p.endswith(".uasset")}
    dangling = set()
    for ua in glob.glob(os.path.join(EXTRACT, "**", "*.uasset"), recursive=True):
        with open(ua, "rb") as f:
            s = f.read().decode("latin-1")
        for m in re.finditer(r"/Game/[A-Za-z0-9_/.]+", s):
            pkg = "Pal/Content/" + m.group(0)[len("/Game/"):]
            if pkg not in own_pkgs and pkg not in vanilla_pkgs:
                dangling.add(m.group(0))
    gate("G6 参照の閉包性(宙ぶらりん参照なし)", not dangling,
         str(sorted(dangling)[:3]) if dangling else "")

    # G7: シェーダー(SM5+SM6両対応でcookされたか)
    ok_log = False
    if os.path.exists(COOK_LOG):
        with open(COOK_LOG, encoding="utf-8", errors="replace") as f:
            log = f.read()
        ok_log = "PCD3D_SM6" in log and "PCD3D_SM5" in log
    mat_sizes = [os.path.getsize(p) for p in glob.glob(
        os.path.join(EXTRACT, "Player", "ModelMaterials", "MainShader", "M_*.uexp"))]
    ok_size = mat_sizes and min(mat_sizes) > 60_000  # SM5のみ時代は最小35KB
    gate("G7 シェーダーSM5+SM6", bool(ok_log and ok_size),
         f"log(SM5&SM6)={ok_log} マテリアルuexp最小={min(mat_sizes) // 1024 if mat_sizes else 0}KB")

    # G8: テクスチャのミップ焼き込み(uexpに実体、最低サイズ)
    tex_sizes = {os.path.basename(p): os.path.getsize(p) for p in glob.glob(
        os.path.join(EXTRACT, "Player", "ModelMaterials", "MainShader", "*.uexp"))
        if "M_" not in os.path.basename(p)}
    ok_tex = tex_sizes and min(tex_sizes.values()) > 100_000
    gate("G8 テクスチャ実体(NeverStream焼き込み)", bool(ok_tex),
         f"最小={min(tex_sizes.values()) // 1024 if tex_sizes else 0}KB / {len(tex_sizes)}枚")

    # G9: マテリアルがスケルタルメッシュ用シェーダーを持つか(使用フラグの物証)。
    # used_with_skeletal_mesh無しでcookするとGPUSkin系permutationが入らず、
    # シップビルドでWorldGridMaterial(チェッカー)に差し替えられる(検査④の敗因)
    no_skin = []
    for p in glob.glob(os.path.join(EXTRACT, "Player", "ModelMaterials",
                                    "MainShader", "M_*.uexp")):
        with open(p, "rb") as f:
            if b"GPUSkin" not in f.read():
                no_skin.append(os.path.basename(p))
    gate("G9 マテリアルにGPUSkinシェーダー(used_with_skeletal_mesh)", not no_skin,
         str(no_skin) if no_skin else "全マテリアルOK")

    return finish()


def finish():
    n_fail = sum(1 for _, ok, _ in results if not ok)
    print(f"\n=== preflight結果: {'全ゲートPASS — 配布可' if n_fail == 0 else f'{n_fail}件FAIL — 配布禁止'} ===")
    sys.exit(1 if n_fail else 0)


if __name__ == "__main__":
    main()
