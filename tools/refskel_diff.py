# -*- coding: utf-8 -*-
"""cook済みSkeletalMesh(uasset+uexp)からRefSkeleton(バインドポーズ)を抽出し、
2つのメッシュ間で骨ごとの位置・回転差を出す。usmap不要(ネイティブ直列化部を
フィンガープリント走査で特定する)。

使い方: python refskel_diff.py <A.uasset> <B.uasset> [出力json]
  それぞれ同名の .uexp が隣にある前提。AとBのRefSkeletonを比較して差分表を出す。
  1引数ならそのメッシュのボーン一覧を表示するだけ。

背景(2026-07-17 検査③): 立ち/歩きで腕肩・しゃがみで脚が崩れ、攻撃は正常。
メッシュのバインドポーズと実行時スケルトン(バニラ1.0)の差が原因と推定され、
その差を定量化するために作成。
"""

import json
import struct
import sys


def read_names(uasset_path):
    """cooked uassetのNameMapを読む。"""
    with open(uasset_path, "rb") as f:
        data = f.read()
    if struct.unpack_from("<I", data, 0)[0] != 0x9E2A83C1:
        raise RuntimeError("uasset magic不一致")
    off = 4
    legacy_ver = struct.unpack_from("<i", data, off)[0]
    off += 4
    if legacy_ver != -4:
        off += 4  # LegacyUE3Version
    off += 4  # FileVersionUE4
    if legacy_ver <= -8:
        off += 4  # FileVersionUE5
    off += 4  # FileVersionLicenseeUE
    # CustomVersions
    (cv_count,) = struct.unpack_from("<i", data, off)
    off += 4 + cv_count * 20
    off += 4  # TotalHeaderSize
    # FolderName (FString)
    (slen,) = struct.unpack_from("<i", data, off)
    off += 4
    off += slen if slen >= 0 else -slen * 2
    off += 4  # PackageFlags
    name_count, name_offset = struct.unpack_from("<ii", data, off)

    names = []
    off = name_offset
    for _ in range(name_count):
        (slen,) = struct.unpack_from("<i", data, off)
        off += 4
        if slen >= 0:
            s = data[off:off + slen - 1].decode("ascii", errors="replace")
            off += slen
        else:
            n = -slen * 2
            s = data[off:off + n - 2].decode("utf-16-le", errors="replace")
            off += n
        off += 4  # 2x uint16 precalc hash
        names.append(s)
    return names


def find_refskeleton(uexp_path, names):
    """uexp内のFMeshBoneInfo配列+FTransform配列をフィンガープリントで探す。"""
    with open(uexp_path, "rb") as f:
        data = f.read()
    n_names = len(names)

    for off in range(0, len(data) - 16):
        (count,) = struct.unpack_from("<i", data, off)
        if not (40 <= count <= 400):
            continue
        # FMeshBoneInfo: FName(idx,num) + int32 parent
        pos = off + 4
        if pos + count * 12 > len(data):
            continue
        ok = True
        bones = []
        for i in range(count):
            idx, num, parent = struct.unpack_from("<iii", data, pos + i * 12)
            if not (0 <= idx < n_names) or num != 0:
                ok = False
                break
            if i == 0 and parent != -1:
                ok = False
                break
            if i > 0 and not (0 <= parent < i):
                ok = False
                break
            bones.append((names[idx], parent))
        if not ok:
            continue
        # 直後にTArray<FTransform>: count一致
        tpos = pos + count * 12
        (tcount,) = struct.unpack_from("<i", data, tpos)
        if tcount != count:
            continue
        tpos += 4
        for fmt, size in (("<10d", 80), ("<10f", 40)):
            if tpos + count * size > len(data):
                continue
            vals0 = struct.unpack_from(fmt, data, tpos)
            qn = sum(v * v for v in vals0[0:4])
            if 0.99 < qn < 1.01:
                transforms = [struct.unpack_from(fmt, data, tpos + i * size)
                              for i in range(count)]
                return bones, transforms, size
        continue
    raise RuntimeError(f"RefSkeletonが見つからない: {uexp_path}")


def load_mesh(uasset_path):
    names = read_names(uasset_path)
    uexp = uasset_path[:-7] + ".uexp"
    bones, transforms, tsize = find_refskeleton(uexp, names)
    print(f"[refskel] {uasset_path}: bones={len(bones)} transform={'double' if tsize == 80 else 'float'}")
    out = {}
    for (name, parent), t in zip(bones, transforms):
        # FTransform: FQuat(x,y,z,w) + Trans(x,y,z) + Scale(x,y,z)
        out[name] = {"parent": bones[parent][0] if parent >= 0 else None,
                     "quat": t[0:4], "pos": t[4:7], "scale": t[7:10]}
    return out


def quat_angle_deg(q1, q2):
    import math
    dot = abs(sum(a * b for a, b in zip(q1, q2)))
    dot = min(1.0, max(-1.0, dot))
    return math.degrees(2 * math.acos(dot))


def main():
    a = load_mesh(sys.argv[1])
    if len(sys.argv) < 3:
        for n, b in a.items():
            print(f"  {n}: pos=({b['pos'][0]:.3f},{b['pos'][1]:.3f},{b['pos'][2]:.3f})")
        return
    b = load_mesh(sys.argv[2])

    rows = []
    for name in a:
        if name not in b:
            rows.append((name, None, None, "Bに無い"))
            continue
        dp = sum((x - y) ** 2 for x, y in zip(a[name]["pos"], b[name]["pos"])) ** 0.5
        dr = quat_angle_deg(a[name]["quat"], b[name]["quat"])
        rows.append((name, dp, dr, ""))
    only_b = [n for n in b if n not in a]

    rows.sort(key=lambda r: -(r[1] or 0))
    print(f"\n{'bone':32s} {'d_pos(cm)':>10s} {'d_rot(deg)':>10s}")
    for name, dp, dr, note in rows:
        if dp is None:
            print(f"{name:32s} {'-':>10s} {'-':>10s} {note}")
        elif dp > 0.01 or dr > 0.1:
            print(f"{name:32s} {dp:10.3f} {dr:10.2f}")
    print(f"\nAのみ: {sum(1 for r in rows if r[1] is None)}本 / Bのみ: {len(only_b)}本 {only_b[:10]}")

    if len(sys.argv) > 3:
        with open(sys.argv[3], "w", encoding="utf-8") as f:
            json.dump({"A": a, "B": b}, f, indent=1)
        print(f"saved: {sys.argv[3]}")


if __name__ == "__main__":
    main()
