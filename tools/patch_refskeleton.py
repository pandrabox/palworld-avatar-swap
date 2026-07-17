# -*- coding: utf-8 -*-
"""cook済み衣装SKのRefSkeleton(バインドポーズ)をバニラ1.0の値に上書きする。

背景(2026-07-17 検査③): ガイド同梱PSKはベータ期抽出で、1.0では肩まわりの
基準ポーズが変更されていた(clavicle/upperarm 10.1°、upperarm位置4.9cm)。
メッシュのバインドポーズが実行時スケルトンとズレると、立ち/歩き等の
アニメで腕肩の位置が崩れる。Blender側で直すと座標系変換の沼なので、
Phase 3のpak展開後にuexpを直接バイナリパッチして共通ボーンの
FTransformを全てバニラ値に置換する。

使い方: python patch_refskeleton.py <pak_extractルート>
  build/vanilla_refskel_male_1_0.json をバニラ基準として、
  <ルート>/Player/Outfit 配下の全 SK_*.uexp を patch する。
"""

import glob
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from refskel_diff import read_names, find_refskeleton

VANILLA_JSON = r"C:\P\Work\PalMod\build\vanilla_refskel_male_1_0.json"


def find_transform_offset(uexp_path, names):
    """find_refskeletonと同じ走査で、transform配列の先頭オフセットも返す。"""
    with open(uexp_path, "rb") as f:
        data = f.read()
    n_names = len(names)
    for off in range(0, len(data) - 16):
        (count,) = struct.unpack_from("<i", data, off)
        if not (40 <= count <= 400):
            continue
        pos = off + 4
        if pos + count * 12 > len(data):
            continue
        ok = True
        bones = []
        for i in range(count):
            idx, num, parent = struct.unpack_from("<iii", data, pos + i * 12)
            if not (0 <= idx < n_names) or num != 0 or \
               (i == 0 and parent != -1) or (i > 0 and not (0 <= parent < i)):
                ok = False
                break
            bones.append(names[idx])
        if not ok:
            continue
        tpos = pos + count * 12
        (tcount,) = struct.unpack_from("<i", data, tpos)
        if tcount != count:
            continue
        tpos += 4
        vals0 = struct.unpack_from("<10d", data, tpos)
        qn = sum(v * v for v in vals0[0:4])
        if 0.99 < qn < 1.01:
            return data, bones, tpos
    raise RuntimeError(f"RefSkeletonが見つからない: {uexp_path}")


def patch_file(uasset_path, vanilla):
    names = read_names(uasset_path)
    uexp_path = uasset_path[:-7] + ".uexp"
    data, bones, tpos = find_transform_offset(uexp_path, names)
    buf = bytearray(data)
    patched = 0
    for i, bone in enumerate(bones):
        vb = vanilla.get(bone)
        if vb is None:
            continue  # PSK由来の追加ボーン(Socket等)はバニラに無いので触らない
        # 2026-07-18 CHIBI_SKELETON化: 回転のみバニラへ補正する。
        # 位置(translation)はチビ骨格の値を保持する(UEのTranslation Retargetingが
        # メッシュ側の関節位置を採用することに期待する方式。位置まで上書きすると
        # チビ骨格が消えて元の木阿弥になる)
        struct.pack_into("<4d", buf, tpos + i * 80, *vb["quat"])
        patched += 1
    if bytes(buf) != data:
        with open(uexp_path, "wb") as f:
            f.write(bytes(buf))
    print(f"[patch_refskel] {os.path.basename(uexp_path)}: {patched}/{len(bones)} bones rot->vanilla (pos=chibi維持)")
    return patched


def main():
    root = sys.argv[1]
    with open(VANILLA_JSON, encoding="utf-8") as f:
        vanilla = json.load(f)
    targets = glob.glob(os.path.join(root, "Player", "Outfit", "**", "SK_*.uasset"),
                        recursive=True)
    if not targets:
        print("[patch_refskel][FATAL] 対象が無い")
        sys.exit(1)
    for t in targets:
        patch_file(t, vanilla)
    print(f"[patch_refskeleton] done ({len(targets)} meshes)")


if __name__ == "__main__":
    main()
