# -*- coding: utf-8 -*-
"""ガイド同梱のベータ期PSKのREFSKELT(ボーン基準ポーズ)をバニラ1.0の値に書き換える。

背景(2026-07-17 検査⑤): ベータ→1.0で肩まわりの基準ポーズが変更されており
(clavicle/upperarm 10.1°・4.9cm)、ベータPSK基準でフィット・バインドした腕は
実行時に背中側へ埋まる。cook後のバイナリパッチではバインドしか直らず、
「幾何がベータ基準の位置で焼かれている」ことは直せない → 源流のPSKを直す。

座標系の符号規約(PSK⇔UE JSON)は、ベータ/1.0で差が無いと計測済みのボーン群を
使って自動較正する(候補マッピング総当たりで残差最小を採用)。

使い方: python patch_psk_to_1_0.py
  入力: assets/from_palworld/SK_Player_Female_Outfit_OldCloth001.psk
        build/vanilla_refskel_male_1_0.json
  出力: assets/from_palworld/SK_Player_OldCloth001_1_0patched.psk
"""

import json
import math
import os
import struct
import sys

PSK_IN = r"C:\P\Work\PalMod\assets\from_palworld\SK_Player_Female_Outfit_OldCloth001.psk"
PSK_OUT = r"C:\P\Work\PalMod\assets\from_palworld\SK_Player_OldCloth001_1_0patched.psk"
VANILLA_JSON = r"C:\P\Work\PalMod\build\vanilla_refskel_male_1_0.json"

# 較正から除外(ベータ→1.0で実差があると計測済みの腕チェーン+目)
KNOWN_DIFF = {"clavicle_l", "clavicle_r", "upperarm_l", "upperarm_r",
              "lowerarm_l", "lowerarm_r", "hand_l", "hand_r", "eyes_l", "eyes_r"}

BONE_SIZE = 120  # name[64] + flags(4) + numchildren(4) + parent(4) + quat(16) + pos(12) + length(4) + size(12)


def read_chunks(data):
    chunks = []
    off = 0
    while off + 32 <= len(data):
        cid = data[off:off + 20].split(b"\x00")[0].decode("ascii", errors="replace")
        typeflag, dsize, dcount = struct.unpack_from("<iii", data, off + 20)
        chunks.append((cid, off + 32, dsize, dcount))
        off += 32 + dsize * dcount
    return chunks


def quat_angle(q1, q2):
    dot = abs(sum(a * b for a, b in zip(q1, q2)))
    return math.degrees(2 * math.acos(min(1.0, dot)))


# 候補マッピング: PSK(quat,pos) -> UE(quat,pos)
# ActorX系PSKは「rootは素のまま・子はW反転(=共役相当)」等の流儀差があるため
# root/非rootそれぞれ独立に較正する
# 符号16通り総当たり(q≡-qなので実質8通りだが列挙が簡単なので全部)
QUAT_MAPS = {
    f"s{sx}{sy}{sz}{sw}": (lambda sx=sx, sy=sy, sz=sz, sw=sw:
                           lambda q: (sx * q[0], sy * q[1], sz * q[2], sw * q[3]))()
    for sx in (1, -1) for sy in (1, -1) for sz in (1, -1) for sw in (1, -1)
}
POS_MAPS = {
    "id": lambda p: p,
    "negy": lambda p: (p[0], -p[1], p[2]),
}


def main():
    with open(PSK_IN, "rb") as f:
        data = bytearray(f.read())
    with open(VANILLA_JSON, encoding="utf-8") as f:
        vanilla = json.load(f)

    chunks = read_chunks(bytes(data))
    ref = next((c for c in chunks if c[0].startswith("REFSKEL")), None)
    if ref is None:
        print("[FATAL] REFSKELTチャンクが無い", [c[0] for c in chunks])
        sys.exit(1)
    _, base, dsize, count = ref
    if dsize != BONE_SIZE:
        print(f"[FATAL] ボーンレコード長が想定外: {dsize}")
        sys.exit(1)

    bones = []
    for i in range(count):
        o = base + i * BONE_SIZE
        name = data[o:o + 64].split(b"\x00")[0].decode("ascii", errors="replace")
        parent = struct.unpack_from("<i", data, o + 72)[0]
        quat = struct.unpack_from("<4f", data, o + 76)
        pos = struct.unpack_from("<3f", data, o + 92)
        bones.append({"name": name, "parent": parent, "quat": quat, "pos": pos, "off": o})

    # --- 較正(root / 非root別) ---
    def calibrate(group):
        best = None
        for qname, qmap in QUAT_MAPS.items():
            for pname, pmap in POS_MAPS.items():
                qerr = perr = n = 0.0
                for b in group:
                    v = vanilla.get(b["name"])
                    if v is None or b["name"] in KNOWN_DIFF:
                        continue
                    qerr += quat_angle(qmap(b["quat"]), v["quat"])
                    perr += math.dist(pmap(b["pos"]), v["pos"])
                    n += 1
                if n == 0:
                    continue
                score = qerr / n + perr / n * 10
                if best is None or score < best[0]:
                    best = (score, qname, pname, qerr / n, perr / n, int(n))
        return best

    roots = [b for b in bones if b["parent"] == 0 and bones.index(b) == 0]
    children = [b for b in bones if b not in roots]
    cal_child = calibrate(children)
    print(f"[calibrate] 非root: map=({cal_child[1]},{cal_child[2]}) "
          f"平均回転残差={cal_child[3]:.3f}deg 平均位置残差={cal_child[4]:.4f}cm n={cal_child[5]}")
    if cal_child[3] > 1.0 or cal_child[4] > 0.1:
        print("[FATAL] 較正残差が大きすぎる — 符号規約の候補を増やすこと")
        sys.exit(1)

    qmap = QUAT_MAPS[cal_child[1]]
    pmap = POS_MAPS[cal_child[2]]
    # 逆写像(候補は全て対合=自身が逆写像)
    inv_qmap, inv_pmap = qmap, pmap

    # --- 書き換え(非rootの共通ボーン全部) ---
    patched = []
    for b in children:
        v = vanilla.get(b["name"])
        if v is None:
            continue
        old_q, old_p = b["quat"], b["pos"]
        new_q = inv_qmap(tuple(v["quat"]))
        new_p = inv_pmap(tuple(v["pos"]))
        struct.pack_into("<4f", data, b["off"] + 76, *new_q)
        struct.pack_into("<3f", data, b["off"] + 92, *new_p)
        dq = quat_angle(old_q, new_q)
        dp = math.dist(old_p, new_p)
        if dq > 0.5 or dp > 0.1:
            patched.append((b["name"], dq, dp))

    with open(PSK_OUT, "wb") as f:
        f.write(bytes(data))

    print(f"[patch_psk] {count}ボーン中、実移動があったのは{len(patched)}本:")
    for name, dq, dp in sorted(patched, key=lambda x: -x[1]):
        print(f"  {name:24s} 回転{dq:6.2f}deg 位置{dp:6.2f}cm")
    print(f"[patch_psk] saved: {PSK_OUT}")


if __name__ == "__main__":
    main()
